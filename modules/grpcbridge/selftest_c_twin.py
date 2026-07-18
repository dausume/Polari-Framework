"""
Selftest for grpcbridge.c_twin (grpc-j3 sliver, hwsim-1).

Run from polari-framework/:
  python3 -m grpcbridge.selftest_c_twin

Compiles the GENERATED header with the host C compiler (cc/gcc —
honest skip when absent) and proves byte-parity with the documented
wire spec via an independent Python reference: C-encoded packets
parse in Python (header, CRC32, tag-ordered payload) and a
Python-encoded packet survives the C rx parser + decoder, including
resync after garbage and a corrupted-CRC rejection. String truncation
at the C_STR_MAX bound is asserted honest (truncated, NUL-terminated,
stream not desynced).
"""

import json
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import zlib

from grpcbridge.c_twin import render_c_header, payload_max, C_STR_MAX

_results = []


def check(label, cond, extra=''):
    _results.append((label, bool(cond)))
    print(f'{"PASS" if cond else "FAIL"}: {label}'
          + (f' — {extra}' if extra and not cond else ''))


FIELD_MAP = {'fields': {
    'name': {'tag': 1, 'proto_type': 'string', 'comment': ''},
    'uptime_ms': {'tag': 2, 'proto_type': 'int64', 'comment': ''},
    'temp_c': {'tag': 3, 'proto_type': 'double', 'comment': ''},
    'led_on': {'tag': 4, 'proto_type': 'bool', 'comment': ''},
    'extras': {'tag': 5, 'proto_type': 'string',
               'comment': 'JSON-encoded (python dict)'},
}, 'reserved': []}

MSG_TYPE = 3
FIELDS_TAG_ORDER = ['name', 'uptime_ms', 'temp_c', 'led_on', 'extras']


def py_encode_payload(values):
    """Independent reference: tag order, LE, u16-len strings."""
    out = b''
    for f in FIELDS_TAG_ORDER:
        v = values[f]
        ptype = FIELD_MAP['fields'][f]['proto_type']
        if ptype == 'int64':
            out += struct.pack('<q', v)
        elif ptype == 'double':
            out += struct.pack('<d', v)
        elif ptype == 'bool':
            out += struct.pack('<B', 1 if v else 0)
        else:
            b = v.encode()
            out += struct.pack('<H', len(b)) + b
    return out


def py_frame(msg_type, device_id, seq, payload):
    hdr = struct.pack('<HBBHIH', 0x504C, 1, msg_type, device_id, seq,
                      len(payload))
    body = hdr + payload
    return body + struct.pack('<I', zlib.crc32(body))


def py_parse(wire):
    magic, ver, mt, dev, seq, plen = struct.unpack('<HBBHIH', wire[:12])
    payload = wire[12:12 + plen]
    crc = struct.unpack('<I', wire[12 + plen:16 + plen])[0]
    assert magic == 0x504C and ver == 1
    assert crc == zlib.crc32(wire[:12 + plen]), 'CRC mismatch'
    values = {}
    p = 0
    for f in FIELDS_TAG_ORDER:
        ptype = FIELD_MAP['fields'][f]['proto_type']
        if ptype == 'int64':
            values[f] = struct.unpack_from('<q', payload, p)[0]; p += 8
        elif ptype == 'double':
            values[f] = struct.unpack_from('<d', payload, p)[0]; p += 8
        elif ptype == 'bool':
            values[f] = payload[p] != 0; p += 1
        else:
            n = struct.unpack_from('<H', payload, p)[0]; p += 2
            values[f] = payload[p:p + n].decode(); p += n
    return mt, dev, seq, values


HARNESS_C = r'''
#include <stdio.h>
#include <stdlib.h>
#include "rigdemo_packets.h"

static void emit(const uint8_t *b, size_t n) {
    size_t i;
    for (i = 0; i < n; i++) printf("%02x", b[i]);
    printf("\n");
}

int main(int argc, char **argv) {
    if (argc > 1) {  /* decode mode: hex packet stream on argv[1] */
        polari_rx_t rx = {0};
        const char *hex = argv[1];
        size_t i, len = strlen(hex) / 2;
        int got = 0;
        for (i = 0; i < len; i++) {
            unsigned v;
            sscanf(hex + 2 * i, "%2x", &v);
            if (polari_rx_feed(&rx, (uint8_t)v)) {
                RigDemo_t s;
                if (rx.msg_type != RIGDEMO_MSG_TYPE) continue;
                if (RigDemo_decode(rx.payload, rx.payload_len, &s))
                    continue;
                got++;
                printf("decoded name=%s uptime=%lld temp=%.3f "
                       "led=%d extras=%s seq=%u\n",
                       s.name, (long long)s.uptime_ms, s.temp_c,
                       (int)s.led_on, s.extras,
                       (unsigned)rx.sequence);
            }
        }
        printf("packets=%d\n", got);
        return 0;
    }
    RigDemo_t s;
    memset(&s, 0, sizeof s);
    snprintf(s.name, sizeof s.name, "rig-c");
    s.uptime_ms = 123456789012345LL;
    s.temp_c = -21.375;
    s.led_on = 1;
    snprintf(s.extras, sizeof s.extras, "{\"sim\": 7}");
    uint8_t payload[RIGDEMO_PAYLOAD_MAX];
    uint16_t plen = RigDemo_encode(&s, payload);
    uint8_t wire[POLARI_HEADER_LEN + RIGDEMO_PAYLOAD_MAX + 4];
    size_t n = polari_packet_encode(wire, RIGDEMO_MSG_TYPE, 9,
                                    424242, payload, plen);
    emit(wire, n);
    return 0;
}
'''


def main():
    cc = shutil.which('cc') or shutil.which('gcc')
    if cc is None:
        print('SKIP: no host C compiler (cc/gcc) — the C-twin '
              'selftest needs one. Honest skip, not a pass.')
        return 0

    header = render_c_header('RigDemo', FIELD_MAP, MSG_TYPE,
                             version=1, contract_hash='cafe')
    check('header names the contract + msg_type',
          'contract v1' in header
          and f'RIGDEMO_MSG_TYPE {MSG_TYPE}u' in header)
    check('payload bound covers worst case',
          payload_max(FIELD_MAP) == 8 + 8 + 1 + 2 * (2 + C_STR_MAX))

    with tempfile.TemporaryDirectory() as td:
        with open(os.path.join(td, 'rigdemo_packets.h'), 'w') as f:
            f.write(header)
        with open(os.path.join(td, 'harness.c'), 'w') as f:
            f.write(HARNESS_C)
        exe = os.path.join(td, 'harness')
        comp = subprocess.run(
            [cc, '-std=c99', '-Wall', '-Werror', '-o', exe,
             os.path.join(td, 'harness.c')],
            capture_output=True, text=True)
        check('generated header compiles clean (-Wall -Werror)',
              comp.returncode == 0, comp.stderr[:400])
        if comp.returncode != 0:
            return 1

        # --- C encode -> Python parse --------------------------------
        out = subprocess.run([exe], capture_output=True, text=True)
        wire = bytes.fromhex(out.stdout.strip())
        mt, dev, seq, values = py_parse(wire)
        check('C-encoded packet parses in Python (header + CRC32)',
              mt == MSG_TYPE and dev == 9 and seq == 424242)
        check('C-encoded fields byte-match the reference layout',
              values == {'name': 'rig-c',
                         'uptime_ms': 123456789012345,
                         'temp_c': -21.375, 'led_on': True,
                         'extras': '{"sim": 7}'}, str(values))

        # --- Python encode -> C rx/decode (with resync + bad CRC) ----
        good = py_frame(MSG_TYPE, 2, 77, py_encode_payload({
            'name': 'rig-py', 'uptime_ms': -5, 'temp_c': 2.5,
            'led_on': False, 'extras': '{}'}))
        bad = bytearray(good)
        bad[-1] ^= 0xFF  # corrupt CRC
        garbage = b'\x4c\x00\xff\x4c\x50'  # fake magic starts
        stream = (garbage + bytes(bad) + good).hex()
        out = subprocess.run([exe, stream], capture_output=True,
                             text=True)
        check('C parser: resyncs past garbage, rejects bad CRC, '
              'decodes the good frame',
              'packets=1' in out.stdout
              and 'name=rig-py' in out.stdout
              and 'uptime=-5' in out.stdout
              and 'temp=2.500' in out.stdout
              and 'seq=77' in out.stdout, out.stdout[:300])

        # --- oversize string truncates honestly ----------------------
        # 100 chars: fits the frame bound (POLARI_RX_PAYLOAD_MAX) but
        # not the char[64] field — must truncate WITHOUT desyncing.
        # (A string blowing the frame bound itself is rejected whole
        # by the rx parser — that path is the resync case above.)
        long_note = 'x' * 100
        oversize = py_frame(MSG_TYPE, 2, 78, py_encode_payload({
            'name': long_note, 'uptime_ms': 1, 'temp_c': 0.0,
            'led_on': True, 'extras': '{}'}))
        out = subprocess.run([exe, oversize.hex()],
                             capture_output=True, text=True)
        check('oversize string truncates at the embed bound without '
              'desync',
              'packets=1' in out.stdout
              and f'name={"x" * (C_STR_MAX - 1)} ' in out.stdout
              and 'uptime=1' in out.stdout, out.stdout[:300])

    passed = sum(1 for _, ok in _results if ok)
    print(f'\n{passed}/{len(_results)} checks passed')
    return 0 if passed == len(_results) else 1


if __name__ == '__main__':
    sys.exit(main())
