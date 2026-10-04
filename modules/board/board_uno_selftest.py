"""board_uno_selftest — brd-1's half of the board selftest (called by board.board_selftest): the UNO route in plain C.
gen renders a buildable, RULE-2-clean tree around the AVR header; build parses avr-size and REFUSES past the cited
limits; flash renders the exact avrdude argv, DRY-RUN by default, and a real flash needs a detected instance AND --yes
(proven with a FAKE avrdude on the PATH — no board is touched); the twin's up/status/down lifecycle (a FAKE
polari-avr-twin streaming real frames through the real pty pump); the measured BoardSimCost row; the packet reference.
The REAL toolchain + simavr path is tests/board_uno_twin_probe.py (and tests/board_uno_bridge_probe.py with the Java bridge).
"""
import json
import os
import shutil
import stat
import sys
import tempfile
import time

FAKE_AVRDUDE = r'''#!/usr/bin/env python3
import sys, os
a = sys.argv[1:]
open(os.environ['FAKE_AVRDUDE_LOG'], 'w').write(' '.join(a))
if os.environ.get('FAKE_AVRDUDE_FAIL'):
    sys.stderr.write("avrdude: stk500_recv(): programmer is not responding\n"); sys.exit(1)
hexf = [x for x in a if x.startswith('flash:w:')][0].split(':')[2]
n = sum(int(l[1:3], 16) for l in open(hexf) if l.startswith(':') and l[7:9] == '00')
sys.stderr.write("avrdude: writing flash (%d bytes)\navrdude: verifying ...\navrdude: %d bytes of flash verified\n" % (n, n))
'''

FAKE_TWIN = r'''#!/usr/bin/env python3
import json, os, socket, sys, time, signal
sys.path.insert(0, os.environ['FAKE_TWIN_FW']); sys.path.insert(0, os.path.join(os.environ['FAKE_TWIN_FW'], 'modules'))
from board.custom import packet_ref
fmap = json.loads(os.environ['FAKE_TWIN_FMAP'])
a = sys.argv[1:]
port = int(a[a.index('--tcp') + 1])
s = socket.socket(); s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1); s.bind(('127.0.0.1', port)); s.listen(1)
hexf = a[a.index('--hex') + 1]
n = sum(int(l[1:3], 16) for l in open(hexf) if l.startswith(':') and l[7:9] == '00')
print(json.dumps({'t': 'ready', 'fake': True, 'hex': hexf, 'flash_bytes_loaded': n}), flush=True)
run = [True]
signal.signal(signal.SIGTERM, lambda *x: run.__setitem__(0, False))
s.settimeout(0.5)
c = None
seq = 0
while run[0]:
    if c is None:
        try:
            c, _ = s.accept()
        except OSError:
            continue
    seq += 1
    c.sendall(packet_ref.frame(1, 3, seq, packet_ref.encode_payload(fmap, {'name': 'uno-rig', 'uptime_ms': seq * 100, 'temp_c': 24.5, 'status': 'ok'})))
    time.sleep(0.1)
print(json.dumps({'t': 'exit', 'frames': seq}), flush=True)
'''


def _exe(path, text):
    open(path, 'w').write(text)
    os.chmod(path, os.stat(path).st_mode | stat.S_IEXEC)


def _fake_runner(sizes_text, ok=True):
    """An engine runner that never runs a tool: avr-gcc 'writes' an elf, objcopy a hex, avr-size prints sizes_text."""
    def run(engine, args, files=None, flash=False, devices=(), timeout=300):
        out = {}
        if engine == 'avr-gcc':
            out = {'firmware.elf': b'\x7fELF fake'}
        elif engine == 'avr-objcopy':
            out = {'firmware.hex': b':100000000C9434000C9446000C9446000C9446006A\n:00000001FF\n'}
        return {'ok': ok, 'returncode': 0 if ok else 1, 'stdout': sizes_text if engine == 'avr-size' else '', 'stderr': '' if ok else 'boom',
                'files': out, 'how': 'fake', 'where': 'selftest', 'cost': {'wall_s': 0.0}}
    return run


def size_text(text, data, bss):
    return 'firmware.elf  :\nsection   size   addr\n.data   %d   8388864\n.text   %d   0\n.bss   %d   8388890\n.comment 18 0\nTotal 1\n' % (data, text, bss)


def run_uno(check):
    from board.custom import gen, build, flash, twin, packet_ref, sim_cost
    from board.custom import board_engines as be
    tmp = tempfile.mkdtemp(prefix='board-selftest-')
    old_path, old_knob = os.environ.get('PATH', ''), os.environ.pop(be.KNOB, None)
    try:
        # ---------------- gen
        work = os.path.join(tmp, 'w')
        row = gen.gen('uno', ['SimRigState'], work, rig_name='uno-rig', device_id=3)
        proj = row['project_dir']
        names = sorted(os.listdir(proj))
        check('gen: the project is main.c (the variant app) + hal.c/hal.h + Makefile + board_config.h + simrigstate_packets.h — RULE 2 clean',
              names == ['Makefile', 'board_config.h', 'hal.c', 'hal.h', 'main.c', 'simrigstate_packets.h'] and not gen.rule2_violations(proj), names)
        hdr = open(os.path.join(proj, 'simrigstate_packets.h')).read()
        cls = json.loads(row['classes_json'])[0]
        check('gen: the header is c_twin target=avr of SimRigState contract v2 (hash 2bcc9d1a2774ef33), its sha recorded',
              'target avr' in hdr and 'polari_avr_double_t temp_c;' in hdr and cls['contract_hash'] == '2bcc9d1a2774ef33'
              and cls['header_sha256'] == gen.sha256(hdr) and cls['source'] == 'pinned')
        from grpcbridge.custom.c_twin import render_c_header
        c = gen.pinned_contract('SimRigState')[0]
        host = render_c_header('SimRigState', c['field_map'], c['msg_type'], version=2, contract_hash=c['contract_hash'])
        renode = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'grpcbridge', 'custom', 'renode_twin', 'firmware', 'simrigstate_packets.h')
        if os.path.isfile(renode):
            body = lambda t: t.split('\n', 1)[1]  # noqa: E731 — the first line names the generator's module path (moved since)
            check('gen: the pinned snapshot is FAITHFUL — rendered for the host it is byte-identical to the Renode twin\'s committed v2 header (but its first line)',
                  body(host) == body(open(renode).read()))
        cfg = open(os.path.join(proj, 'board_config.h')).read()
        import re as _re
        defs = dict(_re.findall(r'#define (\w+)[ \t]+(\S+)', cfg))
        check('gen: the knobs land in board_config.h (RIG_NAME, DEVICE_ID, USART_U2X) and in the repro block',
              defs.get('RIG_NAME') == '"uno-rig"' and defs.get('DEVICE_ID') == '3u' and defs.get('USART_U2X') == '1'
              and json.loads(row['repro_json'])['knobs']['device_id'] == 3, defs)
        check('gen: a FirmwareBuild row in state generated, carrying the template + source sha',
              row['state'] == 'generated' and row['source_sha'] == gen.source_sha(proj) and row['template'] == 'board/custom/firmware/uno')
        from board.board_basis import FirmwareBuild
        check('gen: the record constructs a FirmwareBuild row (no stray field)', FirmwareBuild(**gen.row_fields(row)).state == 'generated')
        for bad, why in ((('esp32-c3', ['SimRigState']), 'no firmware template'), (('uno', ['LedMatrix4x4State']), 'its own template')):
            try:
                gen.gen(bad[0], bad[1], os.path.join(tmp, 'bad'))
                check('gen refuses %s/%s' % bad, False)
            except gen.GenRefused as e:
                check('gen REFUSES %s / %s (%s)' % (bad[0], bad[1][0], why), why in str(e))
        mk = open(os.path.join(gen.TEMPLATES['arduino-uno-r3'], 'Makefile')).read()
        check('build: the template Makefile carries the SAME flags build.py runs', ('CFLAGS = ' + ' '.join(build.CFLAGS).replace('atmega328p', '$(MCU)').replace('16000000UL', '$(F_CPU)')) in mk
              and 'LDFLAGS = ' + ' '.join(build.LDFLAGS) in mk)
        src = open(os.path.join(proj, 'main.c')).read() + open(os.path.join(proj, 'hal.c')).read()
        check('RULE 2: main.c + hal.c are plain avr-libc C — no Arduino core (no Arduino.h, setup()/loop(), Serial.)',
              '#include <avr/io.h>' in src and 'Arduino.h' not in src and 'void setup' not in src and 'Serial.' not in src)
        # ---------------- build (fake engines; the real toolchain is the probe)
        fmax, rmax, cite = build.limits('arduino-uno-r3')
        check('build: the limits come from the cited facts (32256 B flash / 2048 B RAM, boards.txt lines 89/90)',
              (fmax, rmax) == (32256, 2048) and '#L89' in cite and '#L90' in cite)
        check('build: avr-size -A is parsed per section', build.parse_size_A(size_text(4416, 26, 737)) == {'.data': 26, '.text': 4416, '.bss': 737, '.comment': 18})
        r = build.build('uno', work, run=_fake_runner(size_text(4416, 26, 737)))
        check('build: sizes recorded on the row (.text/.data/.bss), flash = text+data, RAM = data+bss, the .hex sha256, state built',
              r['state'] == 'built' and (r['size_text'], r['size_data'], r['size_bss']) == (4416, 26, 737) and r['flash_bytes'] == 4442
              and r['ram_bytes'] == 763 and len(r['artifact_sha256']) == 64 and os.path.isfile(r['hex_path']))
        rp = json.loads(r['repro_json'])
        try:
            from computelod.custom.repro import complete as _complete
        except Exception:   # computelod absent (a lean image): the same required keys, checked here
            def _complete(b):
                miss = [k for k in ('inputs', 'tools', 'knobs', 'conditions', 'generated_files', 'seeds', 'recorded_at', 'how_to_rerun') if k not in b]
                return not miss, miss
        check('build: the repro block is complete (the repro rule\'s required keys): inputs by sha256, tools, knobs, conditions, generated, seeds',
              _complete(rp)[0] and all(i.get('sha256') for i in rp['inputs']), _complete(rp)[1])
        r2 = build.build('uno', work, run=_fake_runner(size_text(32300, 26, 100)))
        check('build: REFUSED past 32256 B flash — state refused, no .hex left to flash', r2['state'] == 'refused' and 'flash 32326 B > 32256 B' in r2['notes']
              and not os.path.exists(os.path.join(work, 'out', 'firmware.hex')) and r2['artifact_sha256'] == '')
        r3 = build.build('uno', work, run=_fake_runner(size_text(4000, 100, 1990)))
        check('build: REFUSED past 2048 B static RAM', r3['state'] == 'refused' and 'static RAM 2090 B > 2048 B' in r3['notes'])
        try:
            flash.plan('uno', work)
            check('flash refuses a refused build', False)
        except flash.FlashRefused as e:
            check('flash: a refused build is never flashed', 'not built' in str(e))
        r = build.build('uno', work, run=_fake_runner(size_text(4416, 26, 737)))
        # ---------------- flash
        byid = '/dev/serial/by-id/usb-Arduino__www.arduino.cc__0043_X-if00'
        d = flash.flash('uno', work, port=byid)
        exp = 'avrdude -p atmega328p -c arduino -P %s -b 115200 -D -U flash:w:%s:i' % (byid, r['hex_path'])
        check('flash: DRY-RUN by default prints the EXACT plan §3 argv (from the ProgrammerKind row + the cited facts)', d['dry_run'] and d['text'] == exp, d['text'])
        inst = {'name': 'pol-core:arduino-uno-r3@001-1', 'definition': 'arduino-uno-r3', 'state': 'board present', 'by_id_path': byid, 'port': '/dev/ttyACM0'}
        check('flash: an instance without --yes is still a DRY-RUN', flash.flash('uno', work, instance=inst)['dry_run'])
        try:
            flash.flash('uno', work, yes=True, instances=[])
            check('flash --yes with no board refuses', False)
        except flash.FlashRefused as e:
            check('flash: --yes with NO detected board is REFUSED (a real flash needs the board present)', 'no arduino-uno-r3 is detected' in str(e))
        fake = os.path.join(tmp, 'bin')
        os.makedirs(fake)
        _exe(os.path.join(fake, 'avrdude'), FAKE_AVRDUDE)
        os.environ['PATH'] = fake + os.pathsep + old_path
        os.environ['FAKE_AVRDUDE_LOG'] = os.path.join(tmp, 'avrdude.args')
        res = flash.flash('uno', work, yes=True, instances=[inst])
        args = open(os.environ['FAKE_AVRDUDE_LOG']).read()
        rec = gen.read_record(work)
        check('flash --yes + a detected instance: avrdude (fake, local rung) gets the exact argv; read-back verified; firmware_sha + last_flash_at stamped; build flashed',
              not res['dry_run'] and args == '-p atmega328p -c arduino -P %s -b 115200 -D -U flash:w:firmware.hex:i' % byid
              and res['verified_bytes'] == 16 and res['instance']['firmware_sha'] == r['artifact_sha256'] and res['instance']['last_flash_at']
              and rec['state'] == 'flashed' and rec['flashed_to'] == inst['name'], args)
        check('flash: avrdude is never passed -V (its read-back verify stays on)', '-V' not in args.split())
        os.environ['FAKE_AVRDUDE_FAIL'] = '1'
        try:
            flash.flash('uno', work, yes=True, instances=[inst])
            check('a failing avrdude refuses', False)
        except flash.FlashRefused as e:
            check('flash: a failing avrdude is REFUSED and nothing is stamped', 'nothing stamped' in str(e))
        os.environ.pop('FAKE_AVRDUDE_FAIL')
        check('engines: a FLASH through a declared worker is refused (USB host only), whatever the build did',
              'USB port' in (os.environ.__setitem__(be.KNOB, 'http://127.0.0.1:9') or be.resolve('avrdude', flash=True))['why'])
        os.environ.pop(be.KNOB, None)
        # ---------------- twin lifecycle (fake simavr streaming real frames through the real pty pump)
        _exe(os.path.join(fake, 'polari-avr-twin'), FAKE_TWIN)
        fw = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        os.environ.update(FAKE_TWIN_FW=fw, FAKE_TWIN_FMAP=json.dumps(c['field_map']))
        build.build('uno', work, run=_fake_runner(size_text(4416, 26, 737)))
        link = os.path.join(tmp, 'uart')
        s = twin.up('uno', work, tcp=19831, link=link)
        check('twin up: the local polari-avr-twin rung (fake), the pty pump, the link present, state recorded',
              s['alive'] and s['how'] == 'local-binary' and os.path.islink(link) and twin.read_state(work)['hex_sha256'] == gen.read_record(work)['artifact_sha256'])
        import select
        import tty
        fd = os.open(link, os.O_RDWR | os.O_NOCTTY)
        tty.setraw(fd)
        p = packet_ref.StreamParser()
        got, t0 = [], time.time()
        while time.time() - t0 < 2.0 and len(got) < 5:
            if select.select([fd], [], [], 0.3)[0]:
                got += p.feed(os.read(fd, 4096))
        os.close(fd)
        vals = packet_ref.decode_payload(c['field_map'], got[-1][3]) if got else {}
        check('twin: frames arrive at the link through the pump and decode with the contract (%d)' % len(got), len(got) >= 3 and vals.get('name') == 'uno-rig')
        check('twin status: up, both processes alive', twin.status('uno', work)['state'] == 'up')
        try:
            twin.up('uno', work, tcp=19831, link=link)
            check('a second twin up refuses', False)
        except twin.TwinRefused as e:
            check('twin: a second `up` is refused while one runs', 'already up' in str(e))
        dn = twin.down('uno', work)
        time.sleep(0.3)
        check('twin down: both processes stopped, the link removed, the state cleared',
              dn['state'] == 'down' and not os.path.exists(link) and twin.read_state(work) is None and not twin._pid_alive(s['pty_pid']))
        os.environ['PATH'] = old_path
        # ---------------- packet reference, cost row
        f1 = packet_ref.frame(1, 3, 9, packet_ref.encode_payload(c['field_map'], {'name': 'x', 'led_on': True, 'pwm_duty': -2, 'temp_c': 1.5, 'uptime_ms': 7}))
        bad = bytearray(f1); bad[20] ^= 1
        p = packet_ref.StreamParser()
        out = p.feed(b'\x4c\x50\x01garbage' + bytes(bad) + f1)
        check('packet_ref: resync after garbage, a corrupted CRC rejected, the good frame decoded',
              len(out) == 1 and p.bad_crc >= 1 and packet_ref.decode_payload(c['field_map'], out[0][3])['pwm_duty'] == -2)
        sc = sim_cost.SEED_BOARD_SIM_COSTS
        check('§8a: ONE measured BoardSimCost row — the UNO twin (object rows, simavr state bytes, cycles/s on pol-core)',
              len(sc) == 1 and sc[0]['board'] == 'arduino-uno-r3' and sc[0]['twin'] == 'simavr:atmega328p' and sc[0]['object_count'] > 0
              and sc[0]['state_bytes'] > 0 and sc[0]['cycles_per_s'] > 1e6)
        oc = sim_cost.object_cost()
        check('§8a: the object count is derived from the seeds (not typed): definition + road + node + facts + programmer + run-time rows',
              oc['per_board_rows'] == sc[0]['object_count'] and oc['seeded']['DatasheetFact'] == len([x for x in __import__('board.custom.uno_facts', fromlist=['x']).SEED_UNO_FACTS]))
    finally:
        os.environ['PATH'] = old_path
        for k in ('FAKE_AVRDUDE_LOG', 'FAKE_AVRDUDE_FAIL', 'FAKE_TWIN_FW', 'FAKE_TWIN_FMAP'):
            os.environ.pop(k, None)
        if old_knob is not None:
            os.environ[be.KNOB] = old_knob
        try:
            twin.down('uno', os.path.join(tmp, 'w'))
        except Exception:
            pass
        shutil.rmtree(tmp, ignore_errors=True)
