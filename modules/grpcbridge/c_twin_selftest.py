"""
Selftest for grpcbridge.custom.c_twin (grpc-j3 sliver, hwsim-1).

Run from polari-framework/:
  python3 -m grpcbridge.c_twin_selftest

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

from grpcbridge.custom.c_twin import render_c_header, payload_max, C_STR_MAX

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


#: brd-0: the default (host) header, pinned — the AVR mode must not move a byte of it
DEFAULT_HEADER_SHA256 = 'cb1ea28cf28e26d7093ed0b002dadcdb02a0c1d091fc4d0b75215d2fbf1391de'

AVR_HARNESS_C = r'''
#include <stdio.h>
#include <stdlib.h>
#include "rigdemo_packets.h"

static void emit(const uint8_t *b, size_t n) {
    size_t i;
    for (i = 0; i < n; i++) printf("%02x", b[i]);
    printf("\n");
}

int main(int argc, char **argv) {
    int a;
    if (argc < 2) return 2;
    if (argv[1][0] == 'e') {      /* e <f32 bits hex>... : one frame per value */
        for (a = 2; a < argc; a++) {
            RigDemo_t s;
            uint32_t bits = (uint32_t)strtoul(argv[a], 0, 16);
            uint8_t payload[RIGDEMO_PAYLOAD_MAX];
            uint8_t wire[POLARI_HEADER_LEN + RIGDEMO_PAYLOAD_MAX + 4];
            uint16_t plen;
            memset(&s, 0, sizeof s);
            snprintf(s.name, sizeof s.name, "avr");
            s.uptime_ms = 1;
            memcpy(&s.temp_c, &bits, 4);
            s.led_on = 1;
            snprintf(s.extras, sizeof s.extras, "{}");
            plen = RigDemo_encode(&s, payload);
            emit(wire, polari_packet_encode(wire, RIGDEMO_MSG_TYPE, 5,
                                            (uint32_t)a, payload, plen));
        }
        return 0;
    } else {                      /* d <hex stream> : temp bits per frame */
        polari_rx_t rx;
        const char *hex = argv[2];
        size_t i, len = strlen(hex) / 2;
        memset(&rx, 0, sizeof rx);
        for (i = 0; i < len; i++) {
            unsigned v;
            sscanf(hex + 2 * i, "%2x", &v);
            if (polari_rx_feed(&rx, (uint8_t)v)) {
                RigDemo_t s;
                uint32_t bits;
                if (RigDemo_decode(rx.payload, rx.payload_len, &s)) continue;
                memcpy(&bits, &s.temp_c, 4);
                printf("%08x\n", (unsigned)bits);
            }
        }
        return 0;
    }
}
'''

#: binary32 bit patterns encoded by the AVR header: normal, 0.1f, +-0, subnormals, the extremes, inf, nan
AVR_ENCODE_BITS = ['c1ab0000', '3dcccccd', '00000000', '80000000', '00000001', '007fffff', '00800000',
                   '7f7fffff', 'ff7fffff', '7f800000', 'ff800000', '7fc00001', '40490fdb']
#: binary64 values decoded to binary32: rounding ties both ways, underflow, overflow, subnormal results
AVR_DECODE_VALUES = [2.5, 0.1, -21.375, 1e-300, -1e-300, 1e300, -1e300, 1 + 2 ** -24, 1 + 3 * 2 ** -24,
                     1 + 2 ** -24 + 2 ** -50, 3.4028235677973366e38, 1e-40, 2 ** -149, 2 ** -150, 1.5 * 2 ** -150,
                     2 ** -126 * (1 - 2 ** -25), float('inf'), float('-inf'), float('nan'), 0.0, -0.0, 3.141592653589793]


def _f32_bits_to_f64_bits(bits):
    """The python reference for encode: exact widening (NaN payload shifted, as IEEE does)."""
    if (bits >> 23) & 0xFF == 0xFF and bits & 0x7FFFFF:
        return ((bits & 0x80000000) << 32) | (0x7FF << 52) | ((bits & 0x7FFFFF) << 29)
    return struct.unpack('<Q', struct.pack('<d', struct.unpack('<f', struct.pack('<I', bits))[0]))[0]


def _f64_to_f32_bits(x):
    """The python reference for decode: C's (float) cast = round to nearest even; overflow = inf."""
    if x != x:
        return 0x7FC00000
    try:
        return struct.unpack('<I', struct.pack('<f', x))[0]
    except OverflowError:
        return 0xFF800000 if x < 0 else 0x7F800000


def avr_checks(cc):
    """brd-0: the AVR mode — default header untouched, the wire unchanged, round trips exact against python."""
    import hashlib
    host = render_c_header('RigDemo', FIELD_MAP, MSG_TYPE, version=1, contract_hash='cafe')
    check('target=host (default) header is byte-identical to the pre-brd-0 header',
          hashlib.sha256(host.encode()).hexdigest() == DEFAULT_HEADER_SHA256)
    check('target=host spelled out == the default',
          render_c_header('RigDemo', FIELD_MAP, MSG_TYPE, version=1, contract_hash='cafe', target='host') == host)
    avr = render_c_header('RigDemo', FIELD_MAP, MSG_TYPE, version=1, contract_hash='cafe', target='avr')
    check('target=avr: double fields become polari_avr_double_t, no 8-byte memcpy of a double',
          'polari_avr_double_t temp_c;' in avr and 'memcpy(p, &s->temp_c, 8)' not in avr and 'target avr' in avr)
    try:
        render_c_header('RigDemo', FIELD_MAP, MSG_TYPE, target='pdp11')
        check('an unknown target is refused', False)
    except ValueError:
        check('an unknown target is refused', True)
    no_double = {'fields': {k: v for k, v in FIELD_MAP['fields'].items() if v['proto_type'] != 'double'}}
    check('target=avr on a class with no double emits no conversion block',
          'POLARI_AVR_DOUBLE_H' not in render_c_header('NoDbl', no_double, 1, target='avr'))
    with tempfile.TemporaryDirectory() as td:
        open(os.path.join(td, 'rigdemo_packets.h'), 'w').write(avr)
        open(os.path.join(td, 'harness.c'), 'w').write(AVR_HARNESS_C)
        exe = os.path.join(td, 'avr_harness')
        src = os.path.join(td, 'harness.c')
        bad = subprocess.run([cc, '-std=c99', '-Wall', '-Werror', '-o', exe, src], capture_output=True, text=True)
        check('the AVR header REFUSES to compile where double is 8 bytes (host without the shim)',
              bad.returncode != 0 and 'polari_avr_double_is_4_bytes' in bad.stderr, bad.stderr[:200])
        comp = subprocess.run([cc, '-std=c99', '-Wall', '-Wextra', '-Werror', '-DPOLARI_AVR_DOUBLE_TEST', '-o', exe, src],
                              capture_output=True, text=True)
        check('the AVR header compiles clean with the 4-byte float shim (-Wall -Wextra -Werror)', comp.returncode == 0, comp.stderr[:400])
        if comp.returncode != 0:
            return
        out = subprocess.run([exe, 'e'] + AVR_ENCODE_BITS, capture_output=True, text=True).stdout.split()
        got, want, wire_ok = [], [], True
        for bits_hex, frame in zip(AVR_ENCODE_BITS, out):
            wire = bytes.fromhex(frame)
            try:
                _mt, _dev, _seq, values = py_parse(wire)   # the UNCHANGED binary64 wire parser
                wire_ok = wire_ok and values['name'] == 'avr' and values['uptime_ms'] == 1 and values['extras'] == '{}'
            except AssertionError:
                wire_ok = False
            plen = struct.unpack_from('<H', wire, 10)[0]
            off = 12 + 2 + 3 + 8                            # name (u16 + 'avr') + uptime int64
            got.append(struct.unpack_from('<Q', wire, off)[0])
            want.append(_f32_bits_to_f64_bits(int(bits_hex, 16)))
            wire_ok = wire_ok and plen == 2 + 3 + 8 + 8 + 1 + 2 + 2
        check('AVR encode: frames parse with the unchanged python wire parser (header, CRC, binary64 slot)',
              wire_ok and len(out) == len(AVR_ENCODE_BITS))
        bad_enc = [(b, hex(g), hex(w)) for b, g, w in zip(AVR_ENCODE_BITS, got, want) if g != w]
        check('AVR encode: binary32 -> binary64 bit-exact for %d values (normal, +-0, subnormals, max, inf, nan)' % len(want),
              not bad_enc, str(bad_enc[:3]))
        stream = b''.join(py_frame(MSG_TYPE, 1, i, py_encode_payload({'name': 'py', 'uptime_ms': i, 'temp_c': v, 'led_on': True, 'extras': ''}))
                          for i, v in enumerate(AVR_DECODE_VALUES))
        dec = subprocess.run([exe, 'd', stream.hex()], capture_output=True, text=True).stdout.split()
        want_d = ['%08x' % _f64_to_f32_bits(v) for v in AVR_DECODE_VALUES]
        bad_dec = [(v, g, w) for v, g, w in zip(AVR_DECODE_VALUES, dec, want_d) if g != w]
        check('AVR decode: binary64 -> binary32 equals C\'s round-to-nearest-even for %d values (ties, underflow, overflow, subnormal results)' % len(want_d),
              len(dec) == len(want_d) and not bad_dec, str(bad_dec[:3]) or 'got %d of %d' % (len(dec), len(want_d)))
        import random
        rng = random.Random(20261001)   # seeded: the sweep is reproducible
        sweep = []
        for _ in range(1000):           # binary64 patterns around binary32's whole exponent range (incl. both edges)
            e = rng.randint(1023 - 160, 1023 + 130)
            sweep.append(struct.unpack('<d', struct.pack('<Q', (rng.getrandbits(1) << 63) | (e << 52) | rng.getrandbits(52)))[0])
        stream = b''.join(py_frame(MSG_TYPE, 1, i, py_encode_payload({'name': '', 'uptime_ms': 0, 'temp_c': v, 'led_on': False, 'extras': ''}))
                          for i, v in enumerate(sweep))
        dec = subprocess.run([exe, 'd', stream.hex()], capture_output=True, text=True).stdout.split()
        bad_sw = [(v, g) for v, g in zip(sweep, dec) if g != '%08x' % _f64_to_f32_bits(v)]
        check('AVR decode sweep: 1000 seeded random binary64 values round exactly as C does', len(dec) == 1000 and not bad_sw, str(bad_sw[:3]))
        rt = subprocess.run([exe, 'd', ''.join(out)], capture_output=True, text=True).stdout.split()
        check('AVR round trip: every binary32 survives encode -> wire -> decode unchanged (nan stays nan)',
              rt[:len(AVR_ENCODE_BITS) - 2] + rt[-1:] == AVR_ENCODE_BITS[:-2] + AVR_ENCODE_BITS[-1:]
              and int(rt[-2], 16) & 0x7FC00000 == 0x7FC00000, str(rt))


# brd-fi: a SECOND class beside SimRigState-like rigs — the UNO's UnoAnalogState (contract v1 as a fresh server makes
# it: alphabetical tags). Its AVR header must compile next to another class's header in ONE translation unit (the
# shared framing block is guarded) and round-trip with the independent Python wire reference both ways.
ANALOG_MAP = {'fields': {
    'a0': {'tag': 1, 'proto_type': 'int64', 'comment': ''}, 'a1': {'tag': 2, 'proto_type': 'int64', 'comment': ''},
    'a2': {'tag': 3, 'proto_type': 'int64', 'comment': ''}, 'name': {'tag': 4, 'proto_type': 'string', 'comment': ''},
    'status': {'tag': 5, 'proto_type': 'string', 'comment': ''}, 'uptime_ms': {'tag': 6, 'proto_type': 'int64', 'comment': ''}},
    'reserved': []}
ANALOG_ORDER = ['a0', 'a1', 'a2', 'name', 'status', 'uptime_ms']

ANALOG_HARNESS_C = r"""
#include <stdio.h>
#include <stdlib.h>
#include "rigdemo_packets.h"
#include "unoanalogstate_packets.h"

int main(int argc, char **argv) {
    uint8_t pl[UNOANALOGSTATE_PAYLOAD_MAX], w[POLARI_HEADER_LEN + UNOANALOGSTATE_PAYLOAD_MAX + 4];
    size_t i, n;
    if (argc > 1) {
        polari_rx_t rx = {0};
        size_t len = strlen(argv[1]) / 2;
        for (i = 0; i < len; i++) {
            unsigned v; sscanf(argv[1] + 2 * i, "%2x", &v);
            if (polari_rx_feed(&rx, (uint8_t)v) && rx.msg_type == UNOANALOGSTATE_MSG_TYPE) {
                UnoAnalogState_t s;
                if (UnoAnalogState_decode(rx.payload, rx.payload_len, &s) == 0)
                    printf("a0=%ld a1=%ld a2=%ld name=%s status=%s uptime=%ld\n", (long)s.a0, (long)s.a1, (long)s.a2, s.name, s.status, (long)s.uptime_ms);
            }
        }
        return 0;
    }
    {
        UnoAnalogState_t s;
        memset(&s, 0, sizeof s);
        s.a0 = 153; s.a1 = 307; s.a2 = 614; strcpy(s.name, "uno-analog"); strcpy(s.status, "ok"); s.uptime_ms = 4321;
        n = polari_packet_encode(w, UNOANALOGSTATE_MSG_TYPE, 3, 7, pl, UnoAnalogState_encode(&s, pl));
        for (i = 0; i < n; i++) printf("%02x", w[i]);
        printf("\n");
    }
    return 0;
}
"""


def _analog_py(values):
    out = b''
    for f in ANALOG_ORDER:
        if ANALOG_MAP['fields'][f]['proto_type'] == 'int64':
            out += struct.pack('<q', values[f])
        else:
            b = values[f].encode()
            out += struct.pack('<H', len(b)) + b
    return out


def second_class_checks(cc):
    analog = render_c_header('UnoAnalogState', ANALOG_MAP, 1, version=1, contract_hash='078e20a0f939956b', target='avr')
    rig = render_c_header('RigDemo', FIELD_MAP, MSG_TYPE, version=1, contract_hash='cafe', target='avr')
    check('brd-fi second class: UnoAnalogState renders (target avr) with its fields in tag order and no double block',
          'int64_t a0;' in analog and analog.index('int64_t a0;') < analog.index('char name[') < analog.index('int64_t uptime_ms;')
          and 'POLARI_AVR_DOUBLE_H' not in analog)
    with tempfile.TemporaryDirectory() as td:
        open(os.path.join(td, 'rigdemo_packets.h'), 'w').write(rig)
        open(os.path.join(td, 'unoanalogstate_packets.h'), 'w').write(analog)
        open(os.path.join(td, 'h.c'), 'w').write(ANALOG_HARNESS_C)
        exe = os.path.join(td, 'h')
        comp = subprocess.run([cc, '-std=c99', '-Wall', '-Wextra', '-Werror', '-Wno-unused-function', '-DPOLARI_AVR_DOUBLE_TEST', '-o', exe,
                               os.path.join(td, 'h.c')], capture_output=True, text=True)
        check('brd-fi second class: its header compiles in ONE translation unit beside another class\'s (the framing block is shared)',
              comp.returncode == 0, comp.stderr[:400])
        if comp.returncode != 0:
            return
        wire = bytes.fromhex(subprocess.run([exe], capture_output=True, text=True).stdout.strip())
        mt, dev, seq, plen = struct.unpack('<BHIH', wire[3:12])
        payload = wire[12:12 + plen]
        p, vals = 0, {}
        for f in ANALOG_ORDER:
            if ANALOG_MAP['fields'][f]['proto_type'] == 'int64':
                vals[f] = struct.unpack_from('<q', payload, p)[0]; p += 8
            else:
                n = struct.unpack_from('<H', payload, p)[0]; p += 2
                vals[f] = payload[p:p + n].decode(); p += n
        crc_ok = struct.unpack('<I', wire[12 + plen:16 + plen])[0] == zlib.crc32(wire[:12 + plen])
        check('brd-fi second class: C-encoded UnoAnalogState parses in the Python reference (msg_type 1, CRC, every field)',
              crc_ok and mt == 1 and dev == 3 and seq == 7 and vals == {'a0': 153, 'a1': 307, 'a2': 614, 'name': 'uno-analog', 'status': 'ok', 'uptime_ms': 4321},
              str(vals))
        good = py_frame(1, 3, 9, _analog_py({'a0': 1, 'a1': 1023, 'a2': 512, 'name': 'py', 'status': 'ok', 'uptime_ms': -2}))
        out = subprocess.run([exe, (b'\x00\xffjunk\x4c\x00' + good).hex()], capture_output=True, text=True).stdout
        check('brd-fi second class: a Python-encoded frame survives the C parser (after garbage) and decodes',
              'a0=1 a1=1023 a2=512 name=py status=ok uptime=-2' in out, out[:200])


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

    avr_checks(cc)
    second_class_checks(cc)
    from grpcbridge.c_twin_wire_selftest import wire_v2_checks
    wire_v2_checks(cc, check)   # grpc-j4: the wire v2 header

    passed = sum(1 for _, ok in _results if ok)
    print(f'\n{passed}/{len(_results)} checks passed')
    return 0 if passed == len(_results) else 1


if __name__ == '__main__':
    sys.exit(main())
