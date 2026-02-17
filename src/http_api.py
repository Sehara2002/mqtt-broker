from aiohttp import web
from .metrics import METRICS

async def stats(request):
    return web.json_response(METRICS.snapshot())

async def metrics_prom(request):
    snap = METRICS.snapshot()
    lines = []
    lines.append(f"broker_uptime_sec {snap['uptime_sec']}")
    lines.append(f"broker_connects_total {snap['connects_total']}")
    lines.append(f"broker_disconnects_total {snap['disconnects_total']}")
    lines.append(f"broker_subscribes_total {snap['subscribes_total']}")
    lines.append(f"broker_publishes_total {snap['publishes_total']}")
    lines.append(f"broker_bytes_in_total {snap['bytes_in_total']}")
    lines.append(f"broker_bytes_out_total {snap['bytes_out_total']}")
    for k, v in snap["packet_count"].items():
        lines.append(f'broker_packet_count{{type="{k}"}} {v}')
    for k, v in snap["packet_avg_ms"].items():
        lines.append(f'broker_packet_avg_ms{{type="{k}"}} {v}')
    for k, v in snap["packet_max_ms"].items():
        lines.append(f'broker_packet_max_ms{{type="{k}"}} {v}')
    return web.Response(text="\n".join(lines) + "\n", content_type="text/plain")

def make_app():
    app = web.Application()
    app.router.add_get("/stats", stats)
    app.router.add_get("/metrics", metrics_prom)
    return app