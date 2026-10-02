"""
@module grpcbridge.custom.wire_ref

An INDEPENDENT Python reference of the wire v2..v4 payload (grpc-j4; GRPC_BRIDGE_PLAN.md §grpc-j4), written from the
spec, not from the C: prelude = [an explicit index: 1 byte (v3) | 2 bytes LE (v4)] + ceil((w + n) / 8) bitfield bytes,
little-endian bit order (bit 0 = LSB of byte 0) — bits 0..w-1 the packed index (v2 only), then presence of field i in
TAG order — then the present fields in tag order: int64 / double
LE 8 B, bool 1 B, enum 1 B (0 = unknown, labels[i] = i + 1), strings u16-length-prefixed UTF-8. Stdlib only.

  encode(spec, values, index=0, present=None)   → payload bytes (present: iterable of field names; None = every field)
  decode(spec, payload)                         → (index, present names, {field: value}) — enum fields as labels
  frame(msg_type, device_id, seq, payload, version=2) / parse_frames(data) → the 12-byte header + CRC32 (v1 and v2)

@consumers
  - grpcbridge.c_twin_selftest (C ⇄ Python parity), board.custom.packet_ref (the twin's stream), tests/board_pair_probe
"""
import struct
import zlib

from grpcbridge.custom.wire_contract import enum_from_wire, enum_to_wire

MAGIC = 0x504C
HEADER = struct.Struct('<HBBHIH')


def encode(spec, values, index=0, present=None):
    want = set(f['name'] for f in spec['fields']) if present is None else set(present)
    w, nb = spec['index_width'], spec['index_bytes']
    if index < 0 or index >= max(1, spec['instance_count']):
        raise ValueError('index %d: %d instance(s) bound' % (index, spec['instance_count']))
    bits = index if w else 0
    head = index.to_bytes(nb, 'little') if nb else b''
    body = b''
    for f in spec['fields']:
        if f['name'] not in want:
            continue
        bits |= 1 << f['bit']
        v = values.get(f['name'])
        if f['enum']:
            body += bytes([enum_to_wire(f['enum'], v)])
        elif f['ptype'] == 'int64':
            body += struct.pack('<q', int(v or 0))
        elif f['ptype'] == 'double':
            body += struct.pack('<d', float(v or 0.0))
        elif f['ptype'] == 'bool':
            body += b'\x01' if v else b'\x00'
        else:
            b = (v or '').encode() if isinstance(v or '', str) else bytes(v)
            body += struct.pack('<H', len(b)) + b
    return head + bits.to_bytes(spec['bitfield_bytes'], 'little') + body


def decode(spec, payload):
    nb, ib = spec['prelude_bytes'], spec['index_bytes']
    if len(payload) < nb:
        raise ValueError('payload shorter than the %d-byte prelude' % nb)
    bits = int.from_bytes(payload[ib:nb], 'little')
    w = spec['index_width']
    index = int.from_bytes(payload[:ib], 'little') if ib else bits & ((1 << w) - 1)
    p, present, values = nb, [], {}
    for f in spec['fields']:
        if not (bits >> f['bit']) & 1:
            continue
        present.append(f['name'])
        if f['enum']:
            values[f['name']] = enum_from_wire(f['enum'], payload[p]); p += 1
        elif f['ptype'] == 'int64':
            values[f['name']] = struct.unpack_from('<q', payload, p)[0]; p += 8
        elif f['ptype'] == 'double':
            values[f['name']] = struct.unpack_from('<d', payload, p)[0]; p += 8
        elif f['ptype'] == 'bool':
            values[f['name']] = payload[p] != 0; p += 1
        else:
            n = struct.unpack_from('<H', payload, p)[0]; p += 2
            values[f['name']] = payload[p:p + n].decode('utf-8', 'replace'); p += n
    if p != len(payload):
        raise ValueError('payload has %d trailing byte(s) after the present fields' % (len(payload) - p))
    return index, present, values


def frame(msg_type, device_id, seq, payload, version=2):
    """version: the spec's wire_version (2 packed / none, 3 an index byte, 4 a u16 index), or 1 for an old payload."""
    body = HEADER.pack(MAGIC, version, msg_type, device_id, seq, len(payload)) + payload
    return body + struct.pack('<I', zlib.crc32(body) & 0xFFFFFFFF)


def parse_frames(data, max_payload=1024):
    """Resync-safe reference parser (v1 and v2): → [(version, msg_type, device_id, seq, payload)]."""
    buf, out = bytearray(data), []
    while True:
        i = buf.find(b'\x4c\x50')
        if i < 0 or len(buf) - i < HEADER.size:
            return out
        del buf[:i]
        _, ver, mt, dev, seq, plen = HEADER.unpack_from(buf, 0)
        if ver not in (1, 2, 3, 4) or plen > max_payload:
            del buf[:1]
            continue
        total = HEADER.size + plen + 4
        if len(buf) < total:
            return out
        if struct.unpack_from('<I', buf, total - 4)[0] != (zlib.crc32(bytes(buf[:total - 4])) & 0xFFFFFFFF):
            del buf[:1]
            continue
        out.append((ver, mt, dev, seq, bytes(buf[HEADER.size:total - 4])))
        del buf[:total]
