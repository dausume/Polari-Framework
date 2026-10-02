"""
grpc-j4 checks for the c_twin selftest (called from grpcbridge.c_twin_selftest.main; runnable alone:
`python3 -m grpcbridge.c_twin_wire_selftest`): the WIRE V2 header
(grpcbridge.custom.c_twin_v2) against the independent Python reference (grpcbridge.custom.wire_ref) and the spec rules
(grpcbridge.custom.wire_contract): the index-width rule, hash v2 vs v1, the prelude (index + presence) both ways, a
present default value, partial decode, enum tables, the v1-frame refusal, the resync fix (brd-fi finding (3)) shown
against the v1 parser on the same bytes, and one-wire-version-per-unit.
"""
import os
import struct
import subprocess
import tempfile
import zlib

from grpcbridge.custom import wire_contract as W
from grpcbridge.custom import wire_ref as R
from grpcbridge.custom.c_twin import render_c_header
from grpcbridge.custom.proto_gen import contract_hash

WIRE_MAP = {'fields': {
    'name': {'tag': 1, 'proto_type': 'string', 'comment': ''},
    'uptime_ms': {'tag': 2, 'proto_type': 'int64', 'comment': ''},
    'temp_c': {'tag': 3, 'proto_type': 'double', 'comment': ''},
    'led_on': {'tag': 4, 'proto_type': 'bool', 'comment': ''},
    'status': {'tag': 5, 'proto_type': 'string', 'comment': ''},
}, 'reserved': []}
ENUMS = {'status': {'labels': ['boot', 'ok', 'fault'], 'unknown': 'unknown'}}
MSG = 4

HARNESS = r'''
#include <stdio.h>
#include <stdlib.h>
#include "rigwire_packets.h"

static void emit(const uint8_t *b, size_t n) { size_t i; for (i = 0; i < n; i++) printf("%02x", b[i]); printf("\n"); }

int main(int argc, char **argv) {
    if (argc < 2) return 2;
    if (argv[1][0] == 'e') {   /* e <index> <mask>: encode the fixed values */
        RigWire_t s;
        uint8_t payload[RIGWIRE_PAYLOAD_MAX], wire[POLARI_HEADER_LEN + RIGWIRE_PAYLOAD_MAX + 4];
        memset(&s, 0, sizeof s);
        snprintf(s.name, sizeof s.name, "rig-v2");
        s.uptime_ms = 987654321LL; s.temp_c = -3.25; s.led_on = 0; s.status = RIGWIRE_STATUS_FAULT;
        emit(wire, RigWire_frame(wire, 6, 99, payload,
             RigWire_encode(&s, payload, (RigWire_index_t)atoi(argv[2]), (RigWire_mask_t)strtoul(argv[3], 0, 0))));
        return 0;
    } else {                   /* d <hex>: every frame, decoded over a sentinel struct */
        polari_rx_t rx;
        const char *hex = argv[2];
        size_t i, len = strlen(hex) / 2;
        int frames = 0;
        memset(&rx, 0, sizeof rx);
        for (i = 0; i < len; i++) {
            unsigned v;
            sscanf(hex + 2 * i, "%2x", &v);
            if (polari_rx_feed(&rx, (uint8_t)v)) {
                RigWire_t s;
                RigWire_index_t idx = 255;
                RigWire_mask_t m = 0;
                int rc;
                memset(&s, 0, sizeof s);
                snprintf(s.name, sizeof s.name, "keep"); s.uptime_ms = 7; s.temp_c = 1.5; s.led_on = 1; s.status = RIGWIRE_STATUS_OK;
                rc = RigWire_decode_rx(&rx, &s, &idx, &m);
                frames++;
                printf("frame v=%u seq=%u rc=%d idx=%u mask=%u name=%s uptime=%lld temp=%.3f led=%d status=%s\n",
                       (unsigned)rx.version, (unsigned)rx.sequence, rc, (unsigned)idx, (unsigned)m, s.name,
                       (long long)s.uptime_ms, s.temp_c, (int)s.led_on, RigWire_status_name(s.status));
            }
        }
        printf("frames=%d\n", frames);
        return 0;
    }
}
'''

#: the v1 parser on the same bytes (finding (3) shown, not assumed)
V1_HARNESS = r'''
#include <stdio.h>
#include "rigwire_packets.h"
int main(int argc, char **argv) {
    polari_rx_t rx; size_t i, len; int frames = 0;
    (void)argc; memset(&rx, 0, sizeof rx); len = strlen(argv[1]) / 2;
    for (i = 0; i < len; i++) { unsigned v; sscanf(argv[1] + 2 * i, "%2x", &v); if (polari_rx_feed(&rx, (uint8_t)v)) frames++; }
    printf("frames=%d\n", frames);
    { RigWire_t s; uint8_t b[RIGWIRE_PAYLOAD_MAX], w[POLARI_HEADER_LEN + RIGWIRE_PAYLOAD_MAX + 4]; memset(&s, 0, sizeof s);
      (void)polari_packet_encode(w, 1, 1, 1, b, RigWire_encode(&s, b)); (void)RigWire_decode(b, 0, &s); }
    return 0;
}
'''


def _run(cc, td, src, header, flags=('-std=gnu99', '-Wall', '-Wextra', '-Werror')):
    open(os.path.join(td, 'rigwire_packets.h'), 'w').write(header)
    open(os.path.join(td, 'h.c'), 'w').write(src)
    exe = os.path.join(td, 'h')
    comp = subprocess.run([cc, *flags, '-o', exe, os.path.join(td, 'h.c')], capture_output=True, text=True)
    return comp, exe


def _frames(out):
    return [dict(kv.split('=', 1) for kv in line.split()[1:]) for line in out.splitlines() if line.startswith('frame ')]


def wire_v2_checks(cc, check):
    # ---- the rules
    ns = (1, 2, 3, 4, 5, 8, 9, 16, 17, 20, 256, 257)
    widths = {n: W.index_width(n) for n in ns}
    check('grpc-j4 index width (the suggestion) = f(n): 0 bits for 1, 1 for 2, 2 for 3-4, 3 for 5-8, ceil(log2 n) in general',
          widths == {1: 0, 2: 1, 3: 2, 4: 2, 5: 3, 8: 3, 9: 4, 16: 4, 17: 5, 20: 5, 256: 8, 257: 9}, str(widths))
    reps = {n: (W.index_repr(n)['repr'], W.index_repr(n)['version'], W.index_repr(n)['packed_bits'], W.index_repr(n)['index_bytes'])
            for n in ns}
    check('grpc-j4 index REPRESENTATION at n = %s (packed_max_bits 4): none → packed bits (v2) up to 16 → an explicit index '
          'byte (v3) for 17..256 → a 16-bit index (v4) at 257' % ', '.join(map(str, ns)),
          reps == {1: ('none', 2, 0, 0), 2: ('bits', 2, 1, 0), 3: ('bits', 2, 2, 0), 4: ('bits', 2, 2, 0), 5: ('bits', 2, 3, 0),
                   8: ('bits', 2, 3, 0), 9: ('bits', 2, 4, 0), 16: ('bits', 2, 4, 0), 17: ('byte', 3, 0, 1), 20: ('byte', 3, 0, 1),
                   256: ('byte', 3, 0, 1), 257: ('u16', 4, 0, 2)}, str(reps))
    sizes = {n: W.spec('RigWire', WIRE_MAP, ENUMS, n)['prelude_bytes'] for n in ns}
    check('grpc-j4 prelude bytes for 5 fields by n: 1 up to n=8 (index + presence share a byte), 2 at 9-16, 2 with the index '
          'byte, 3 with the u16 index — %s' % sizes,
          sizes == {1: 1, 2: 1, 3: 1, 4: 1, 5: 1, 8: 1, 9: 2, 16: 2, 17: 2, 20: 2, 256: 2, 257: 3})
    k5 = W.spec('RigWire', WIRE_MAP, ENUMS, 20, packed_max_bits=5)
    try:
        W.spec('X', WIRE_MAP, {}, 65537)
        too_many = False
    except W.WireRefused:
        too_many = True
    check('grpc-j4 the threshold is a KNOB in the hash: packed_max_bits 5 packs n=20 into 5 bits (v2) and changes hash v2; '
          'past 65536 instances is refused',
          k5['index_repr'] == 'bits' and k5['index_width'] == 5 and k5['hash_v2'] != W.spec('RigWire', WIRE_MAP, ENUMS, 20)['hash_v2']
          and too_many)
    v2_map = {'fields': {'name': {'tag': 1, 'proto_type': 'string'}, 'led_on': {'tag': 2, 'proto_type': 'bool'}}}
    alpha = {'fields': {'led_on': {'tag': 1, 'proto_type': 'bool'}, 'name': {'tag': 2, 'proto_type': 'string'}}}
    snap = {'name': {'dominantType': 'str', 'dominantAffinity': 'TEXT'}, 'led_on': {'dominantType': 'bool'}}
    a, b = W.spec('X', v2_map), W.spec('X', alpha)
    check('grpc-j4 hash v2 sees field ORDER (brd-1\'s case: v1 cannot — one snapshot, one v1 hash %s; two orders, v2 %s ≠ %s)'
          % (contract_hash(snap), a['hash_v2'], b['hash_v2']), a['hash_v2'] != b['hash_v2'])
    base = W.spec('RigWire', WIRE_MAP, ENUMS, 4)
    moved = {W.spec('RigWire', WIRE_MAP, ENUMS, 2)['hash_v2'], W.spec('RigWire', WIRE_MAP, {}, 4)['hash_v2'],
             W.spec('RigWire', WIRE_MAP, {'status': ['boot', 'fault', 'ok']}, 4)['hash_v2']}
    check('grpc-j4 hash v2 moves with the index width, with an enum table and with the enum ORDER', base['hash_v2'] not in moved and len(moved) == 3)
    try:
        W.spec('RigWire', WIRE_MAP, {'uptime_ms': ['a']}, 1)
        refused = False
    except W.WireRefused:
        refused = True
    check('grpc-j4 an enum mapping on a non-string field is refused with the reason', refused)
    s = base
    check('grpc-j4 prelude: 2 index bits + 5 presence bits = 1 byte; payload bound = prelude + fields (enum 1 B)',
          s['prelude_bytes'] == 1 and s['present_all'] == 31)

    with tempfile.TemporaryDirectory() as td:
        host = render_c_header('RigWire', WIRE_MAP, MSG, version=3, contract_hash='beef', wire=s)
        comp, exe = _run(cc, td, HARNESS, host)
        check('grpc-j4 the v2 header compiles clean (-Wall -Wextra -Werror), the hash2 line names hash v2',
              comp.returncode == 0 and 'hash2 %s' % s['hash_v2'] in host and 'contract v3   hash beef' in host, comp.stderr[:400])
        if comp.returncode != 0:
            return
        # C encode → Python: index 3, led_on present AS FALSE, status enum, temp_c / name absent
        mask = (1 << 1) | (1 << 3) | (1 << 4)        # uptime_ms, led_on, status (bit positions = field order)
        out = subprocess.run([exe, 'e', '3', str(mask)], capture_output=True, text=True).stdout.strip()
        (ver, mt, dev, seq, payload), = R.parse_frames(bytes.fromhex(out))
        idx, present, vals = R.decode(s, payload)
        check('grpc-j4 C → Python: version 2, index 3 in the prelude, ONLY the present fields, led_on present AS false, status '
              'enum fault (1 B), %d-byte payload' % len(payload),
              ver == 2 and mt == MSG and idx == 3 and present == ['uptime_ms', 'led_on', 'status']
              and vals == {'uptime_ms': 987654321, 'led_on': False, 'status': 'fault'} and payload[0] == (3 | mask << 2)
              and len(payload) == 1 + 8 + 1 + 1, (ver, idx, present, vals))
        # Python encode → C: a partial command writes only what it carries
        part = R.frame(MSG, 1, 41, R.encode(s, {'led_on': False, 'status': 'boot'}, index=2, present=['led_on', 'status']))
        f, = _frames(subprocess.run([exe, 'd', part.hex()], capture_output=True, text=True).stdout)
        check('grpc-j4 Python → C: index 2, the two present fields applied (led_on → 0, status boot), the absent ones untouched',
              f['idx'] == '2' and f['led'] == '0' and f['status'] == 'boot' and f['name'] == 'keep' and f['uptime'] == '7'
              and f['temp'] == '1.500' and f['rc'] == '0', f)
        unk = R.frame(MSG, 1, 42, bytes([0b0000001 << 6]) + bytes([9]))   # status present, wire value 9 (no label)
        f2, = _frames(subprocess.run([exe, 'd', unk.hex()], capture_output=True, text=True).stdout)
        check('grpc-j4 enum: an out-of-table value decodes to the unknown slot\'s name (C) / label (Python)',
              f2['status'] == 'unknown' and R.decode(s, bytes([1 << 6, 9]))[2]['status'] == 'unknown', f2)
        v1 = R.frame(MSG, 1, 43, b'\x00' * 4, version=1)
        f3, = _frames(subprocess.run([exe, 'd', v1.hex()], capture_output=True, text=True).stdout)
        check('grpc-j4 a v1 frame still PARSES on the v2 parser (version 1) and its decode is refused (-2), never misread',
              f3['v'] == '1' and f3['rc'] == '-2' and f3['name'] == 'keep', f3)
        # finding (3): garbage ending in the start byte; a frame cut short by a lost tail followed by a good one
        pl = R.encode(s, {'uptime_ms': 5, 'led_on': True}, index=1, present=['uptime_ms', 'led_on'])
        cut_pl = R.encode(s, {'name': 'x' * 40}, present=['name'])

        def stream_of(version):
            g = [R.frame(MSG, 1, q, pl, version=version) for q in (50, 51, 52)]
            return b'\x00\xff\x4c' + g[0] + R.frame(MSG, 1, 49, cut_pl, version=version)[:30] + g[1] + b'\x00' * 40 + g[2]
        fs = _frames(subprocess.run([exe, 'd', stream_of(2).hex()], capture_output=True, text=True).stdout)
        v1h = render_c_header('RigWire', WIRE_MAP, MSG, version=3, contract_hash='beef')
        td1 = os.path.join(td, 'v1')
        os.makedirs(td1)
        c1, exe1 = _run(cc, td1, V1_HARNESS, v1h)
        old = subprocess.run([exe1, stream_of(1).hex()], capture_output=True, text=True).stdout
        check('grpc-j4 resync (brd-fi finding (3)): garbage ending in 0x4C + frame 50 + a frame cut short + frame 51 + noise + '
              'frame 52 → the v2 parser keeps all three; the v1 parser on the same bytes (version 1) keeps %s' % old.strip(),
              [x['seq'] for x in fs] == ['50', '51', '52'] and c1.returncode == 0 and 'frames=1' in old,
              (fs, old, c1.stderr[:200]))
        # the explicit index representations through the C: n=20 → an index byte (v3), n=257 → a 16-bit index (v4)
        for n, idx, ver in ((20, 19, 3), (257, 300, 4)):
            sn = W.spec('RigWire', WIRE_MAP, ENUMS, n)
            tdn = os.path.join(td, 'n%d' % n)
            os.makedirs(tdn)
            cn, exn = _run(cc, tdn, HARNESS, render_c_header('RigWire', WIRE_MAP, MSG, version=3, contract_hash='beef', wire=sn))
            outn = subprocess.run([exn, 'e', str(idx), str(mask)], capture_output=True, text=True).stdout.strip() if cn.returncode == 0 else ''
            fr = R.parse_frames(bytes.fromhex(outn)) if outn else []
            back = R.decode(sn, fr[0][4]) if fr else (None, None, None)
            inn = R.frame(MSG, 1, 61, R.encode(sn, {'led_on': False}, index=n - 1, present=['led_on']), version=ver)
            fc = _frames(subprocess.run([exn, 'd', inn.hex()], capture_output=True, text=True).stdout) if cn.returncode == 0 else []
            check('grpc-j4 n=%d → %s: C encodes index %d with version byte %d (Python reads index %d); Python index %d → C reads %d'
                  % (n, sn['index_repr'], idx, ver, back[0] if back[0] is not None else -1, n - 1, int(fc[0]['idx']) if fc else -1),
                  cn.returncode == 0 and fr and fr[0][0] == ver and back[0] == idx and back[2]['status'] == 'fault'
                  and fc and fc[0]['idx'] == str(n - 1) and fc[0]['v'] == str(ver) and fc[0]['led'] == '0', cn.stderr[:300])
        # AVR target compiles with the 4-byte double shim; two v2 classes in one unit; v1 + v2 refused in one unit
        avr = render_c_header('RigWire', WIRE_MAP, MSG, version=3, contract_hash='beef', target='avr', wire=s)
        c2, _ = _run(cc, os.path.join(td), HARNESS.replace('%.3f', '%.3f').replace('s.temp_c = -3.25', 's.temp_c = -3.25f'),
                     avr, ('-std=gnu99', '-Wall', '-Wextra', '-Werror', '-DPOLARI_AVR_DOUBLE_TEST'))
        check('grpc-j4 target=avr v2 header compiles with the 4-byte double shim', c2.returncode == 0, c2.stderr[:300])
        other = W.spec('RigOther', {'fields': {'a0': {'tag': 1, 'proto_type': 'int64'}}}, {}, 1)
        both = host + '\n' + render_c_header('RigOther', {'fields': {'a0': {'tag': 1, 'proto_type': 'int64'}}}, 5, wire=other)
        lax = ('-std=gnu99', '-Wall', '-Wno-unused-function', '-Werror')
        c3, _ = _run(cc, os.path.join(td), HARNESS, both, lax)
        mixed = host + '\n' + render_c_header('RigOld', {'fields': {'a0': {'tag': 1, 'proto_type': 'int64'}}}, 5)
        c4, _ = _run(cc, os.path.join(td), HARNESS, mixed, lax)
        check('grpc-j4 two v2 class headers share one translation unit; a v1 + a v2 header in one unit FAIL to compile',
              c3.returncode == 0 and c4.returncode != 0 and 'redefinition' in c4.stderr, (c3.stderr[:200], c4.stderr[:200]))
    big = {'fields': {'f%d' % i: {'tag': i + 1, 'proto_type': 'int64'} for i in range(9)}}
    bs = W.spec('Big', big, {}, 2)
    p = R.encode(bs, {'f8': -1, 'f0': 3}, index=1, present=['f0', 'f8'])
    check('grpc-j4 a 10-bit prelude spans 2 bytes, LSB first (index bit 0, f0 bit 1, f8 bit 9)',
          bs['prelude_bytes'] == 2 and p[:2] == bytes([0b11, 0b10]) and R.decode(bs, p) == (1, ['f0', 'f8'], {'f0': 3, 'f8': -1}))
    _ = struct, zlib


def main():
    import shutil
    import sys
    results = []

    def check(label, cond, extra=''):
        results.append(bool(cond))
        print(f'{"PASS" if cond else "FAIL"}: {label}' + (f' — {extra}' if extra and not cond else ''))
    cc = shutil.which('cc') or shutil.which('gcc')
    if cc is None:
        print('SKIP: no host C compiler — honest skip, not a pass')
        return 0
    wire_v2_checks(cc, check)
    print(f'\n{sum(results)}/{len(results)} checks passed')
    sys.stdout.flush()
    return 0 if all(results) else 1


if __name__ == '__main__':
    raise SystemExit(main())
