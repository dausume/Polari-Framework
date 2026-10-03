"""board_c3_selftest — sc-3: the ESP32-C3 template, its variants, gen (RULE 2, the target=host header speaking the UNO's
wire), build through the esp engines (REAL when prf-esp-engines is on this docker, else skipped and said so), the exact
esptool argv (DRY-RUN), the twin lifecycle against a FAKE polari-c3-run (the local-binary rung), the measured twin cost.

    PYTHONPATH=.:modules python3 -m board.board_c3_selftest      # from polari-framework/ (also run by board_selftest)
"""
import json
import os
import shutil
import socket
import sys
import tempfile
import time

_passed = _total = 0


def _check(label, cond, extra=''):
    global _passed, _total
    _total += 1
    _passed += bool(cond)
    print('  [%s] %s %s' % ('\033[0;32mPASS\033[0m' if cond else '\033[0;31mFAIL\033[0m', label, extra if not cond else ''))


SIZE_FIXTURE = {'version': '1.1', 'layout': [
    {'name': 'DRAM', 'total': 321296, 'used': 88408, 'free': 232888, 'parts': {'.text': {'size': 45452}, '.bss': {'size': 37768}, '.data': {'size': 5188}}},
    {'name': 'Flash Code', 'total': 0, 'used': 79424, 'free': 0, 'parts': {'.text': {'size': 79424}}},
    {'name': 'Flash Data', 'total': 0, 'used': 28972, 'free': 0, 'parts': {'.rodata': {'size': 28500}, '.appdesc': {'size': 256}, '.init_array': {'size': 216}}}]}
FLASH_ARGS = ('--flash_mode dio --flash_freq 80m --flash_size 4MB\n0x0 bootloader/bootloader.bin\n0x10000 polari_c3.bin\n'
              '0x8000 partition_table/partition-table.bin\n')

FAKE_RUN = r'''#!/usr/bin/env python3
# a FAKE polari-c3-run for the twin lifecycle check: --serve PORT → a TCP server that echoes (one select loop), a ready line, a trace file
import json, select, socket, sys
a = sys.argv[1:]
port = int(a[a.index('--serve') + 1]); trace = a[a.index('--trace') + 1]
open(trace, 'w').write('@BOOT app=fake\n')
s = socket.socket(); s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1); s.bind(('127.0.0.1', port)); s.listen(4)
print(json.dumps({'t': 'ready', 'tcp': port, 'fake': True}), flush=True)
conns = []
while True:
    r, _, _ = select.select([s] + conns, [], [], 1.0)
    for c in r:
        if c is s:
            conns.append(s.accept()[0])
            continue
        d = c.recv(4096)
        if not d:
            conns.remove(c); c.close()
        else:
            c.sendall(d)
'''


def variants(check):
    from board.custom import variants_c3 as V
    from board.board_basis import FirmwareVariant
    vs = V.SEED_C3_VARIANTS
    check('six C3 variants, all on board esp32-c3, each constructs a FirmwareVariant row',
          len(vs) == 6 and all(v['board_definition'] == 'esp32-c3' and FirmwareVariant(**v).name == v['name'] for v in vs))
    rs = {v['name']: V.resolve(v) for v in vs}
    check('every C3 variant resolves (app, SimRigState, knobs, flags)', all(r['classes'] == ['SimRigState'] for r in rs.values()))
    flags = {n: dict(r['flags']) for n, r in rs.items()}
    check('each scenario pair differs in exactly ONE build flag (the technique)',
          flags['c3-prio-inversion'] == {'SC_PI_MUTEX': 0} and flags['c3-prio-inversion-mutex'] == {'SC_PI_MUTEX': 1}
          and flags['c3-two-lock'] == {'SC_LOCK_ORDER': 0} and flags['c3-two-lock-ordered'] == {'SC_LOCK_ORDER': 1}
          and flags['c3-two-lock-backoff'] == {'SC_LOCK_ORDER': 0, 'SC_LOCK_TIMEOUT_MS': 5}, flags)
    bad = []
    for patch, why in (({'build_flags_json': '["SC_LOCK_ORDER=1"]'}, 'reads only'), ({'build_flags_json': '["SC_PI_MUTEX=2"]'}, 'outside'),
                       ({'app': 'blink'}, 'C3 template has'), ({'knobs_json': '{"telemetry_hz": 99}'}, 'telemetry_hz'),
                       ({'build_flags_json': '["-DX"]'}, 'NAME=integer')):
        try:
            V.resolve(dict(V.find('c3-prio-inversion'), **patch))
            bad.append(patch)
        except V.VariantRefused as e:
            if why not in str(e):
                bad.append((patch, str(e)))
    check('a bad C3 variant is REFUSED with the reason (another app\'s flag, a range, an unknown app, a knob, a raw compiler arg)', not bad, bad)
    cfg = V.render_config(rs['c3-two-lock-backoff'])
    check('board_config.h carries the app, the knobs and the flags', '#define POLARI_APP   "two_lock"' in cfg and '#define SC_LOCK_TIMEOUT_MS 5' in cfg
          and '#define FEATURE_VALUE 1' in cfg and '#define FEATURE_VALUE 0' in V.render_config(rs['c3-sim-rig']))


def gen_checks(check, work):
    from board.custom import gen, gen_c3
    row = gen_c3.gen_c3('c3-prio-inversion', work)
    files = gen_c3.project_files(row['project_dir'])
    check('gen c3 renders the ESP-IDF project: CMake + sdkconfig.defaults + partitions.csv + main/ (app.c = the variant\'s app)',
          files == ['CMakeLists.txt', 'main/CMakeLists.txt', 'main/app.c', 'main/board_config.h', 'main/polari_c3.c', 'main/polari_c3.h',
                    'main/polari_trace.c', 'main/polari_trace.h', 'main/simrigstate_packets.h', 'partitions.csv', 'sdkconfig.defaults'], files)
    app = open(os.path.join(row['project_dir'], 'main', 'app.c')).read()
    check('main/app.c is apps/prio_inversion.c verbatim', app == open(os.path.join(gen_c3.TEMPLATE, 'apps', 'prio_inversion.c')).read())
    h = open(os.path.join(row['project_dir'], 'main', 'simrigstate_packets.h')).read()
    uno_text, uno_prov = gen.header('SimRigState')
    c = json.loads(row['classes_json'])[0]
    check('the header is rendered target=host (8-byte double: no software conversion) and speaks the UNO\'s wire v2 (same hash2, same order)',
          'polari_avr_double_t' not in h and 'double temp_c;' in h and c['target'] == 'host' and c['hash_v2'] == uno_prov['hash_v2']
          and c['tag_order'] == uno_prov['tag_order'], (c['hash_v2'], uno_prov['hash_v2']))
    check('RULE 2 holds on the generated project (C + ESP-IDF\'s build files only)', gen_c3.rule2_violations(row['project_dir']) == [])
    row2 = gen_c3.gen_c3('c3-prio-inversion', work)
    check('gen is deterministic: the same variant → the same source sha (the build name)', row2['source_sha'] == row['source_sha'] and row2['name'] == row['name'])
    open(os.path.join(row['project_dir'], 'main', 'helper.py'), 'w').write('x = 1\n')
    check('a stray non-C file in a C3 project is a RULE 2 violation', gen_c3.rule2_violations(row['project_dir']) == ['main/helper.py'])
    os.remove(os.path.join(row['project_dir'], 'main', 'helper.py'))
    try:
        gen.gen('esp32-c3', None, work)
        check('the UNO generator refuses esp32-c3 and points at gen_c3', False)
    except gen.GenRefused as e:
        check('the UNO generator refuses esp32-c3 and points at gen_c3', 'gen_c3' in str(e), str(e))
    tpl = open(os.path.join(gen_c3.TEMPLATE, 'CMakeLists.txt')).read()
    check('the template force-includes the FreeRTOS trace hooks into every C file (C only, never the assembler)',
          '$<$<COMPILE_LANGUAGE:C>:-include;' in tpl and 'polari_trace.h' in tpl)
    th = open(os.path.join(gen_c3.TEMPLATE, 'main', 'polari_trace.h')).read()
    check('the trace header defines the FreeRTOS hook macros (switch-in, block, take, give, inherit, disinherit, timeout)',
          all(m in th for m in ('traceTASK_SWITCHED_IN()', 'traceBLOCKING_ON_QUEUE_RECEIVE(', 'traceQUEUE_RECEIVE(', 'traceQUEUE_SEMAPHORE_RECEIVE(', 'traceQUEUE_SEND(',
                                'traceTASK_PRIORITY_INHERIT(', 'traceTASK_PRIORITY_DISINHERIT(', 'traceQUEUE_RECEIVE_FAILED(')))
    sd = open(os.path.join(gen_c3.TEMPLATE, 'sdkconfig.defaults')).read()
    check('sdkconfig.defaults: 1 kHz tick, UART0 free of console + logs, reproducible builds, the custom partition table',
          all(x in sd for x in ('CONFIG_FREERTOS_HZ=1000', 'CONFIG_ESP_CONSOLE_NONE=y', 'CONFIG_BOOTLOADER_LOG_LEVEL_NONE=y',
                                'CONFIG_APP_REPRODUCIBLE_BUILD=y', 'CONFIG_PARTITION_TABLE_CUSTOM=y')))
    return row


def engines(check):
    from board.custom import board_engines as be
    check('the esp family: idf-build / c3-run / qemu-esp32c3 / esptool resolve on ESP_ENGINES_URL · prf-esp-engines:noble · board.esp-engines',
          all(be.family(e) == 'esp' for e in ('idf-build', 'c3-run', 'qemu-esp32c3', 'esptool')) and be.family('avr-gcc') == 'avr'
          and be.FAMILIES['esp']['knob'] == 'ESP_ENGINES_URL' and be.FAMILIES['esp']['default_image'] == 'prf-esp-engines:noble'
          and be.FAMILIES['esp']['provider'] == 'board.esp-engines')
    check('RULE 2: the esp engines are of admitted kinds (c-compiler, simulator, flasher)', all(be.rule2_ok(e) for e in be.ESP_IMAGE_ENGINES))
    old = os.environ.get('ESP_ENGINES_URL')
    os.environ['ESP_ENGINES_URL'] = 'http://127.0.0.1:9'
    try:
        be._CAP_CACHE.clear()
        r = be.resolve('idf-build')
        rf = be.resolve('esptool', flash=True)
        ra = be.resolve('avr-gcc')
        check('a declared esp worker that is unreachable is a REFUSAL naming ESP_ENGINES_URL (never a silent fallback)',
              r['how'] == 'refused' and 'ESP_ENGINES_URL' in r['why'], r)
        check('a flash is refused through the esp worker knob (only the USB host flashes)', rf['how'] == 'refused' and 'flash' in rf['why'], rf)
        check('the esp knob does not move the AVR family', ra['how'] != 'refused' or 'ESP_ENGINES_URL' not in ra['why'], ra)
    finally:
        if old is None:
            os.environ.pop('ESP_ENGINES_URL', None)
        else:
            os.environ['ESP_ENGINES_URL'] = old
        be._CAP_CACHE.clear()


def sizes_and_flash(check, tmp):
    from board.custom import build_c3, flash_c3, gen, gen_c3
    s = build_c3.parse_size(json.dumps(SIZE_FIXTURE))
    check('idf.py size json2 → the three columns (text = flash code + IRAM text, data = DRAM data + flash data, bss) + DRAM used/total',
          s['size_text'] == 79424 + 45452 and s['size_data'] == 5188 + 28972 and s['size_bss'] == 37768 and s['dram_used'] == 88408
          and s['dram_total'] == 321296, s)
    flags, pairs = flash_c3.parse_flash_args(FLASH_ARGS)
    check('idf.py\'s flash_args → flags + (offset, file) pairs sorted by offset',
          flags == ['--flash_mode', 'dio', '--flash_freq', '80m', '--flash_size', '4MB']
          and pairs == [(0, 'bootloader.bin'), (0x8000, 'partition-table.bin'), (0x10000, 'app.bin')], (flags, pairs))
    work = os.path.join(tmp, 'flashwork')
    store = gen.store_dir(work, 'c3-fake-000000000000')
    os.makedirs(store)
    open(os.path.join(store, 'flash_args.txt'), 'w').write(FLASH_ARGS)
    gen.write_record(work, {'name': 'c3-fake-000000000000', 'board_definition': gen_c3.BOARD, 'state': 'built', 'store_dir': store,
                            'artifact_sha256': 'f' * 64, 'app_sha256': 'a' * 64})
    p = flash_c3.flash(work, '/dev/serial/by-id/usb-Espressif_USB_JTAG_serial_debug_unit-if00')
    exp = ['esptool.py', '--chip', 'esp32c3', '--port', '/dev/serial/by-id/usb-Espressif_USB_JTAG_serial_debug_unit-if00', '--baud', '460800',
           'write_flash', '--flash_mode', 'dio', '--flash_freq', '80m', '--flash_size', '4MB',
           '0x0', os.path.join(store, 'bootloader.bin'), '0x8000', os.path.join(store, 'partition-table.bin'), '0x10000', os.path.join(store, 'app.bin')]
    check('flash c3 DRY-RUN renders the EXACT esptool argv from the esptool ProgrammerKind + idf.py\'s flash_args', p['dry_run'] and p['argv'] == exp, p['argv'])
    try:
        flash_c3.flash(work, '', yes=True, instances=[])
        check('a real C3 flash with no detected board is REFUSED', False)
    except flash_c3.F.FlashRefused as e:
        check('a real C3 flash with no detected board is REFUSED', 'no esp32-c3 is detected' in str(e), str(e))


def twin_fake(check, tmp):
    from board.custom import board_engines as be, gen, gen_c3, twin_c3
    bindir = os.path.join(tmp, 'bin')
    os.makedirs(bindir)
    fake = os.path.join(bindir, 'polari-c3-run')
    open(fake, 'w').write(FAKE_RUN)
    os.chmod(fake, 0o755)
    work = os.path.join(tmp, 'twinwork')
    os.makedirs(os.path.join(work, 'out'))
    img = os.path.join(work, 'out', 'flash_image.bin')
    open(img, 'wb').write(b'\xff' * 1024)
    gen.write_record(work, {'name': 'c3-fake-111111111111', 'board_definition': gen_c3.BOARD, 'state': 'built', 'image_path': img,
                            'artifact_sha256': 'b' * 64, 'variant': 'c3-sim-rig'})
    s = socket.socket()
    s.bind(('127.0.0.1', 0))
    port = s.getsockname()[1]
    s.close()
    link = os.path.join(tmp, 'c3-twin-uart')
    old_path = os.environ['PATH']
    os.environ['PATH'] = bindir + os.pathsep + old_path
    try:
        check('with polari-c3-run on the PATH the twin takes the local-binary rung', be.resolve('c3-run')['how'] == 'local-binary', be.resolve('c3-run'))
        st = twin_c3.up(work, tcp=port, link=link, wait_s=15)
        check('twin c3 up: the twin and the pty pump alive, the link present, the ready line read', st['alive'] and os.path.islink(link)
              and (st.get('ready') or {}).get('t') == 'ready', {k: st.get(k) for k in ('alive', 'twin_alive', 'pty_alive', 'ready')})
        fd = os.open(link, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
        os.write(fd, b'polari-c3')
        got, t0 = b'', time.time()
        while time.time() - t0 < 5 and got != b'polari-c3':
            try:
                got += os.read(fd, 64)
            except BlockingIOError:
                time.sleep(0.05)
        os.close(fd)
        check('bytes written to the link reach the twin\'s UART0 TCP and come back (the pty pump, both ways)', got == b'polari-c3', got)
        check('twin c3 status: up, with the trace tail', twin_c3.status(work)['state'] == 'up' and twin_c3.status(work)['trace_tail'] == ['@BOOT app=fake'])
        try:
            twin_c3.up(work, tcp=port, link=link)
            check('a second up while up is REFUSED', False)
        except twin_c3.TwinRefused:
            check('a second up while up is REFUSED', True)
        d = twin_c3.down(work)
        check('twin c3 down: the link removed, the state cleared, the trace tail returned', d['state'] == 'down' and not os.path.islink(link)
              and twin_c3.status(work)['state'] == 'down' and d['trace_tail'] == ['@BOOT app=fake'], d)
    finally:
        os.environ['PATH'] = old_path
        try:
            twin_c3.down(work)
        except Exception:
            pass


def cost(check):
    from board.custom import sim_cost_c3
    from board.board_seed import BOARD_SEED_PAIRS
    rows = next(r for n, _, r in BOARD_SEED_PAIRS if n == 'BoardSimCost')
    c3 = [r for r in rows if r['board'] == 'esp32-c3']
    m = json.loads(c3[0]['method']) if c3 else {}
    check('BoardSimCost esp32-c3:qemu:esp32c3 is seeded FROM the committed measurement (objects, state = QEMU peak RSS, speed, wall-time ratio)',
          len(c3) == 1 and c3[0]['twin'] == 'qemu:esp32c3' and c3[0]['object_count'] == sim_cost_c3.object_cost()['per_board_rows']
          and c3[0]['state_bytes'] > 0 and c3[0]['cycles_per_s'] > 0 and m.get('wall_time_ratio', 0) > 0, c3[0]['notes'] if c3 else 'none')


def real_build(check, tmp):
    """REAL when the esp engines image is on this docker (or a worker is named); otherwise skipped, and said so."""
    from board.custom import board_engines as be, build_c3, gen_c3
    if be.resolve('idf-build')['how'] == 'refused':
        print('  [SKIP] build c3 through the esp engines — no prf-esp-engines image / worker here (docker compose -f '
              'polari-rf-node/docker-compose.esp-engines.yml build)')
        return
    work = os.path.expanduser(os.path.join(os.environ.get('POLARI_BOARD_SELFTEST_HOME', '~/.cache/polari-board-selftest'), 'esp32-c3'))
    gen_c3.gen_c3('c3-sim-rig', work)
    t0 = time.time()
    row = build_c3.build('c3', work)
    check('build c3 (REAL, ESP-IDF v5.5.5 through %s): built, sizes measured, the merged image\'s sha256 recorded (%s, %.0f s)'
          % (be.resolve('idf-build')['how'], row.get('cache', '?'), time.time() - t0),
          row['state'] == 'built' and row['size_text'] > 0 and row['size_bss'] > 0 and len(row['artifact_sha256']) == 64
          and os.path.isfile(row['image_path']) and os.path.getsize(row['image_path']) == 4 * 1024 * 1024, row.get('notes'))
    again = build_c3.build('c3', work)
    check('a second build of the same sources + image is the CACHE (no rebuild), the same sha', again.get('cache') == 'hit'
          and again['artifact_sha256'] == row['artifact_sha256'])
    rep = json.loads(row['repro_json'])
    check('the C3 build\'s repro block: inputs by sha256 (project files + the tar), the engine + image, deterministic, how to rerun',
          rep['seeds']['deterministic'] and any(i['label'].startswith('project.tar') for i in rep['inputs'])
          and 'idf-build' in rep['tools'] and 'pol board build c3' in rep['how_to_rerun'])


def run_c3(check=_check):
    tmp = tempfile.mkdtemp(prefix='polari-c3-selftest-')
    try:
        variants(check)
        gen_checks(check, os.path.join(tmp, 'genwork'))
        engines(check)
        sizes_and_flash(check, tmp)
        twin_fake(check, tmp)
        cost(check)
        real_build(check, tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == '__main__':
    run_c3()
    print('\n%d/%d checks passed' % (_passed, _total))
    sys.exit(0 if _passed == _total else 1)
