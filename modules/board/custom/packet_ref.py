"""
@module board.custom.packet_ref

An INDEPENDENT Python reference of the PolariPacket wire (the same spec c_twin documents: 12-byte LE header — magic
0x504C u16, version 1 u8, msg_type u8, device_id u16, sequence u32, payload_len u16 — payload in TAG order, int64/double
LE 8 B, bool 1 B, strings u16-length-prefixed UTF-8, CRC32 (zlib) over header+payload appended LE), driven by a
contract field map. It reads the twin's (or a real UNO's) byte stream when no Java bridge runs, and frames commands.
Stdlib only.

brd-wire (grpc-j4): version 2 frames carry the prelude (instance index + presence bits) — `decode_any` reads either
version (v2 through grpcbridge.custom.wire_ref with the class's wire spec), `frame(..., version=2)` frames a v2 payload
(`wire_ref.encode`). StreamParser accepts both versions and yields (msg_type, device_id, seq, payload, version).
"""
import struct
import zlib

MAGIC = 0x504C
HEADER = struct.Struct('<HBBHIH')


def tag_order(field_map):
    f = field_map['fields']
    return [(n, f[n]['proto_type']) for n in sorted(f, key=lambda n: int(f[n]['tag']))]


def encode_payload(field_map, values):
    out = b''
    for name, ptype in tag_order(field_map):
        v = values.get(name)
        if ptype == 'int64':
            out += struct.pack('<q', int(v or 0))
        elif ptype == 'double':
            out += struct.pack('<d', float(v or 0.0))
        elif ptype == 'bool':
            out += b'\x01' if v else b'\x00'
        else:
            b = (v or '').encode() if isinstance(v or '', str) else bytes(v)
            out += struct.pack('<H', len(b)) + b
    return out


def frame(msg_type, device_id, seq, payload, version=1):
    body = HEADER.pack(MAGIC, version, msg_type, device_id, seq, len(payload)) + payload
    return body + struct.pack('<I', zlib.crc32(body) & 0xFFFFFFFF)


def decode_payload(field_map, payload):
    values, p = {}, 0
    for name, ptype in tag_order(field_map):
        if ptype == 'int64':
            values[name] = struct.unpack_from('<q', payload, p)[0]; p += 8
        elif ptype == 'double':
            values[name] = struct.unpack_from('<d', payload, p)[0]; p += 8
        elif ptype == 'bool':
            values[name] = payload[p] != 0; p += 1
        else:
            n = struct.unpack_from('<H', payload, p)[0]; p += 2
            values[name] = payload[p:p + n].decode('utf-8', 'replace'); p += n
    return values


def decode_any(field_map, payload, version=1, spec=None):
    """{field: value} of a v1 payload (every field) or a v2 payload (the present fields; spec = the wire spec), plus
    '_index' / '_present' for v2."""
    if int(version) < 2:
        return decode_payload(field_map, payload)
    from grpcbridge.custom.wire_ref import decode
    index, present, values = decode(spec, payload)
    return dict(values, _index=index, _present=present)


class StreamParser:
    """Resync-safe: bad magic / version / oversize / CRC restart the hunt one byte later (the C parser's behaviour).
    feed(bytes) → list of (msg_type, device_id, seq, payload); counters say what was skipped."""

    def __init__(self, max_payload=1024):
        self.buf = bytearray()
        self.max_payload = max_payload
        self.frames = self.bad_crc = self.skipped = 0

    def feed(self, data):
        self.buf += data
        out = []
        while True:
            i = self.buf.find(b'\x4c\x50')
            if i < 0:
                self.skipped += max(0, len(self.buf) - 1)
                del self.buf[:max(0, len(self.buf) - 1)]
                return out
            if i:
                self.skipped += i
                del self.buf[:i]
            if len(self.buf) < HEADER.size:
                return out
            magic, ver, mt, dev, seq, plen = HEADER.unpack_from(self.buf, 0)
            if ver not in (1, 2, 3, 4) or plen > self.max_payload:
                del self.buf[:1]; self.skipped += 1
                continue
            total = HEADER.size + plen + 4
            if len(self.buf) < total:
                return out
            body = bytes(self.buf[:HEADER.size + plen])
            crc = struct.unpack_from('<I', self.buf, HEADER.size + plen)[0]
            if crc != (zlib.crc32(body) & 0xFFFFFFFF):
                self.bad_crc += 1
                del self.buf[:1]
                continue
            del self.buf[:total]
            self.frames += 1
            out.append((mt, dev, seq, body[HEADER.size:], ver))
