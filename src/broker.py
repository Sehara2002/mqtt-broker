import asyncio
import time
from .config import MQTT_HOST, MQTT_PORT, HTTP_HOST, HTTP_PORT, LOG_PACKET_TIMES
from .mqtt_codec import (
    decode_remaining_length, read_utf8, read_u16,
    build_connack, build_suback, build_publish
)
from .state import STATE
from .metrics import METRICS
from .http_api import make_app

def _log_packet(name: str, peer, ms: float):
    if LOG_PACKET_TIMES:
        print(f"[{name}] from={peer} cycle_ms={ms:.3f}")

async def handle_connect(body: bytes):
    # CONNECT variable header
    i = 0
    proto, i = read_utf8(body, i)
    level = body[i]; i += 1
    _flags = body[i]; i += 1
    _keep_alive = (body[i] << 8) | body[i+1]; i += 2

    if proto != "MQTT" or level != 4:
        return build_connack(return_code=1), None  # unacceptable protocol version

    client_id, i = read_utf8(body, i)
    return build_connack(0), client_id

async def handle_subscribe(body: bytes, writer):
    i = 0
    packet_id, i = read_u16(body, i)

    granted = []
    while i < len(body):
        topic, i = read_utf8(body, i)
        req_qos = body[i]; i += 1
        # force QoS0 only
        STATE.subscribers[topic].add(writer)
        STATE.client_topics[writer].add(topic)
        granted.append(0)

    METRICS.subscribes_total += 1
    return build_suback(packet_id, bytes(granted))

async def handle_publish(body: bytes):
    i = 0
    topic, i = read_utf8(body, i)
    payload = body[i:]
    return topic, payload

async def client_loop(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    peer = writer.get_extra_info("peername")
    buf = bytearray()

    METRICS.connects_total += 1
    print(f"[+] Client connected: {peer}")

    try:
        while True:
            chunk = await reader.read(4096)
            if not chunk:
                break

            METRICS.bytes_in_total += len(chunk)
            buf.extend(chunk)

            while True:
                if len(buf) < 2:
                    break

                packet_type = buf[0] >> 4
                remaining_length, idx = decode_remaining_length(buf, 1)
                if remaining_length is None:
                    break

                total_len = idx + remaining_length
                if len(buf) < total_len:
                    break

                body = bytes(buf[idx:total_len])
                del buf[:total_len]

                t0 = time.perf_counter()

                # CONNECT
                if packet_type == 1:
                    resp, cid = await handle_connect(body)
                    if cid:
                        STATE.client_ids[writer] = cid
                    writer.write(resp)
                    await writer.drain()
                    METRICS.bytes_out_total += len(resp)
                    METRICS.observe_packet("CONNECT", (time.perf_counter() - t0) * 1000)
                    _log_packet("CONNECT", peer, (time.perf_counter() - t0) * 1000)

                # SUBSCRIBE
                elif packet_type == 8:
                    resp = await handle_subscribe(body, writer)
                    writer.write(resp)
                    await writer.drain()
                    METRICS.bytes_out_total += len(resp)
                    METRICS.observe_packet("SUBSCRIBE", (time.perf_counter() - t0) * 1000)
                    _log_packet("SUBSCRIBE", peer, (time.perf_counter() - t0) * 1000)

                # PUBLISH
                elif packet_type == 3:
                    topic, payload = await handle_publish(body)

                    # route to exact-topic subscribers
                    out_msg = build_publish(topic, payload)
                    subs = list(STATE.subscribers.get(topic, []))

                    for w in subs:
                        try:
                            w.write(out_msg)
                        except Exception:
                            pass
                    for w in subs:
                        try:
                            await w.drain()
                        except Exception:
                            pass

                    METRICS.publishes_total += 1
                    METRICS.bytes_out_total += len(out_msg) * len(subs)
                    METRICS.observe_packet("PUBLISH", (time.perf_counter() - t0) * 1000)
                    _log_packet("PUBLISH", peer, (time.perf_counter() - t0) * 1000)

                # PINGREQ -> PINGRESP
                elif packet_type == 12:
                    resp = bytes([0xD0, 0x00])
                    writer.write(resp)
                    await writer.drain()
                    METRICS.bytes_out_total += len(resp)
                    METRICS.observe_packet("PINGREQ", (time.perf_counter() - t0) * 1000)

                # DISCONNECT
                elif packet_type == 14:
                    METRICS.observe_packet("DISCONNECT", (time.perf_counter() - t0) * 1000)
                    return

                else:
                    # ignore unknown packet types in this simple broker
                    METRICS.observe_packet(f"TYPE_{packet_type}", (time.perf_counter() - t0) * 1000)

    except Exception as e:
        print(f"[!] Client error {peer}: {e}")

    finally:
        # cleanup
        for topic in list(STATE.client_topics.get(writer, [])):
            STATE.subscribers[topic].discard(writer)
        STATE.client_topics.pop(writer, None)
        STATE.client_ids.pop(writer, None)

        METRICS.disconnects_total += 1
        try:
            writer.close()
            await writer.wait_closed()
        except Exception:
            pass
        print(f"[-] Client closed: {peer}")

async def start_mqtt():
    server = await asyncio.start_server(client_loop, MQTT_HOST, MQTT_PORT)
    addrs = ", ".join(str(s.getsockname()) for s in server.sockets)
    print(f"MQTT listening on {addrs}")
    async with server:
        await server.serve_forever()

async def start_http():
    from aiohttp import web
    app = make_app()
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, HTTP_HOST, HTTP_PORT)
    await site.start()
    print(f"HTTP stats listening on http://{HTTP_HOST}:{HTTP_PORT}/stats and /metrics")

async def run_all():
    await asyncio.gather(start_http(), start_mqtt())