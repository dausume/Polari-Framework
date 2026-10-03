"""
@module firmwarefaults.custom.payloads

THE HOST SIDE OF A SCENARIO, as bytes (FIRMWARE_SCENARIO_PLAN.md §3a): what the scripted host sends to the board — an
ACK frame, SimRigState commands, the residual pattern of GRPC_BRIDGE_PLAN Finding (3), a seeded command stream for the
statistics tier — and what the EEPROM holds before a run. Every frame is built by the INDEPENDENT Python wire reference
(grpcbridge.custom.wire_ref + the pinned SimRigState contract), never by the firmware's own header; every builder is
deterministic (the bytes are recorded by sha256 on the run).
"""
import struct

ACK_MSG_TYPE = 0x7F


def _spec():
    from board.custom import gen
    from board.custom.compat import wire_spec
    fm = gen.pinned_contract('SimRigState')[0]['field_map']
    return wire_spec(None, 'SimRigState', fm)


def command(seq, pwm_duty, spec=None):
    """One host→board SimRigState command carrying only pwm_duty (wire v2, single instance → no index)."""
    from grpcbridge.custom.wire_ref import encode, frame
    spec = spec or _spec()
    return frame(1, 0, seq, encode(spec, {'pwm_duty': int(pwm_duty)}, present=['pwm_duty']), spec['wire_version'])


def ack():
    """The host's ACK: msg_type 0x7F, empty payload, version 2 (scenario_rig.c accepts any CRC-valid 0x7F frame)."""
    from grpcbridge.custom.wire_ref import frame
    return frame(ACK_MSG_TYPE, 0, 0, b'', 2)


def residual(trailing_bytes=10):
    """A false start (a 12-byte header claiming a length that reaches `trailing_bytes` into frame B) + command A + command B.
    The shipped parser rejects the false candidate at its CRC, rescues A from the held bytes and drops the B bytes that
    followed A in that span. → (bytes, {'sent': 2, 'pattern': …})"""
    spec = _spec()
    a, b = command(1, 1, spec), command(2, 2, spec)
    if not 0 < trailing_bytes < len(b):
        raise ValueError('trailing_bytes must be 1..%d (inside frame B)' % (len(b) - 1))
    length = len(a) + trailing_bytes - 4          # 12 (false header) + length + 4 (its CRC) = 12 + len(A) + trailing
    false = struct.pack('<HBBHIH', 0x504C, 2, 1, 0, 0, length)
    return false + a + b, {'sent': 2, 'false_header_len': length, 'frame_len': len(a), 'trailing_bytes': trailing_bytes}


#: the idle filler after a statistics stream: a corrupted length near the end would otherwise leave the board's parser waiting
#: for bytes that never come (a real host keeps sending); 128 > the longest candidate the board can hold (12 + 93 + 4)
FLUSH_TAIL = 128


def command_stream(n, start_seq=1, flush=FLUSH_TAIL):
    """n commands back to back (pwm_duty = 1..n) + `flush` zero bytes — the statistics tier's host→board traffic.
    → (bytes, {'sent': n, 'flush_bytes': flush})"""
    spec = _spec()
    return b''.join(command(start_seq + i, start_seq + i, spec) for i in range(n)) + b'\x00' * flush, {'sent': n, 'flush_bytes': flush}


def crc8(data):
    """CRC-8 poly 0x07 init 0 — the same as scenario_rig.c's crc8()."""
    c = 0
    for x in data:
        c ^= x
        for _ in range(8):
            c = ((c << 1) ^ 0x07) & 0xFF if c & 0x80 else (c << 1) & 0xFF
    return c


def eeprom_record(layout, value):
    """The EEPROM image of `value` in a variant's record layout → [(addr, bytes)]. layout: 1 = in place (4 bytes at 0);
    2 = two slots {value[4], seq, crc8} at 0 and 8 — slot 0 holds value with seq 1, slot 1 is erased (0xFF)."""
    v = struct.pack('<I', value & 0xFFFFFFFF)
    if int(layout) == 1:
        return [(0, v)]
    if int(layout) == 2:
        s0 = v + bytes([1])
        return [(0, s0 + bytes([crc8(s0)]) + b'\xff\xff'), (8, b'\xff' * 8)]
    raise ValueError('record layout %r: 1 (in place) | 2 (two slots + seq + crc)' % layout)


#: the generated header's POLARI_RX_PAYLOAD_MAX for SimRigState (a longer frame cannot be received by the board at all)
RX_PAYLOAD_MAX = 93


def ideal_frames(delivered, max_payload=RX_PAYLOAD_MAX):
    """Every CRC-valid frame in the bytes that actually reached the board, found OFFLINE with hindsight: a greedy left-to-right
    scan that, at each 0x4C 0x50, accepts a complete CRC-valid frame and jumps past it, else moves one byte on — a candidate
    that would run past the end is simply skipped, so nothing is lost to waiting (the reference StreamParser, max payload
    1024, waits for a corrupted length's bytes and so undercounts at the end of a stream). → [(offset, msg_type, seq)]"""
    import zlib
    d, i, out = bytes(delivered), 0, []
    while True:
        i = d.find(b'\x4c\x50', i)
        if i < 0 or len(d) - i < 12:
            return out
        _, ver, mt, dev, seq, plen = struct.unpack_from('<HBBHIH', d, i)
        total = 12 + plen + 4
        if 1 <= ver <= 4 and plen <= max_payload and i + total <= len(d) and \
                struct.unpack_from('<I', d, i + 12 + plen)[0] == (zlib.crc32(d[i:i + 12 + plen]) & 0xFFFFFFFF):
            out.append((i, mt, seq))
            i += total
        else:
            i += 1


def ideal_commands(delivered):
    """How many SimRigState commands (msg_type 1) an IDEAL receiver finds in the bytes that reached the board — the floor the
    line itself sets; anything the firmware applies below it is the parser's own loss (the residual)."""
    return sum(1 for f in ideal_frames(delivered) if f[1] == 1)


def delivered_from_rx_log(log):
    """The twin's --uart-rx-log (u64 cycle, u8 byte, u8 flags per record; flags 0x80 = lost on the line) → the bytes the
    UART received."""
    return bytes(log[i + 8] for i in range(0, len(log) - 9, 10) if not log[i + 9] & 0x80)


def first_line_error_cycle(log):
    """sc-2: the cycle of the first host→board byte the line damaged (flags != 0 in the --uart-rx-log: lost 0x80, framing 0x01,
    data bits 0x02), or None — the statistics tier's time to the stimulus's first hit."""
    for i in range(0, len(log) - 9, 10):
        if log[i + 9]:
            return int.from_bytes(log[i:i + 8], 'little')
    return None
