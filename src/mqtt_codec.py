import struct

def decode_remaining_length(buf: bytearray, start_index=1):
    multiplier = 1
    value = 0
    i = start_index
    while True:
        if i >= len(buf):
            return None, None
        encoded_byte = buf[i]
        value += (encoded_byte & 127) * multiplier
        multiplier *= 128
        i += 1
        if (encoded_byte & 128) == 0:
            break
        if multiplier > 128 * 128 * 128:
            raise ValueError("Malformed Remaining Length")
    return value, i

def encode_remaining_length(length: int) -> bytes:
    out = bytearray()
    while True:
        digit = length % 128
        length //= 128
        if length > 0:
            digit |= 0x80
        out.append(digit)
        if length == 0:
            break
    return bytes(out)

def read_u16(buf: bytes, i: int):
    return (buf[i] << 8) | buf[i + 1], i + 2

def read_utf8(buf: bytes, i: int):
    ln, i = read_u16(buf, i)
    s = buf[i:i + ln].decode("utf-8", errors="replace")
    return s, i + ln

def build_connack(return_code=0):
    # CONNACK: type=2
    return bytes([0x20, 0x02, 0x00, return_code])

def build_suback(packet_id: int, granted_qos_list: bytes):
    fixed = bytes([0x90]) + encode_remaining_length(2 + len(granted_qos_list))
    return fixed + bytes([(packet_id >> 8) & 0xFF, packet_id & 0xFF]) + granted_qos_list

def build_publish(topic: str, payload: bytes):
    # QoS0 publish
    topic_b = topic.encode("utf-8")
    var_hdr = struct.pack("!H", len(topic_b)) + topic_b
    body = var_hdr + payload
    return bytes([0x30]) + encode_remaining_length(len(body)) + body