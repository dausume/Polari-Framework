"""board_installer_c3_selftest - ins-c3-1 (AI-Notes/plans/C3_INSTALL_PLAN.md): the firmware installer takes an ESP32-C3.

OFFLINE only, with made-up things: a C3 build store written by the shipped gen_c3 + build_c3.store from made-up files (three files, a merged image composed from them with 0xFF fill, a flash_args.txt),
a made-up esp-engines worker with a made-up C3 twin (twin_session_fakes*), and a made-up esptool runner that prints "Hash of data verified" as often as it is told to. No engine, no docker engine run,
no board, no flash, no network beyond the made-up worker on loopback. The REAL build, a REAL esptool and a REAL board are NOT tested here.

    PYTHONPATH=.:modules python3 -B -m board.board_installer_c3_selftest      # from polari-framework/
    (board.board_selftest calls run_installer_c3(check))
"""
import contextlib
import hashlib
import io
import json
import os
import tempfile

from board.board_installer_selftest import _M
from board.board_twin_session_selftest import _env

LIGHT = 'esp32c3-light'
FLASH_ARGS = '--flash_mode dio --flash_freq 80m --flash_size 4MB\n0x0 bootloader/bootloader.bin\n0x10000 polari_c3.bin\n0x8000 partition_table/partition-table.bin\n'
PORT = '/dev/serial/by-id/usb-made_up_c3-if00'
CLASSES = ('SimRigState', 'ButtonClockState', 'ButtonClockEvent')


def _sha(b):
    return hashlib.sha256(b).hexdigest()


def _make_build(work, shim, tag):
    """A made-up built C3 build of the light, stored the way build_c3 stores one: the generator's own record, made-up files, the merged image composed from them (0xFF elsewhere)."""
    from board.custom import build_c3, gen, gen_c3
    row = gen_c3.gen_c3(LIGHT, work, **({} if shim else {'pin_shim': 0}))
    out = os.path.join(work, 'out')
    os.makedirs(out, exist_ok=True)
    files = {'bootloader.bin': (b'BOOT%s' % tag) * 600, 'partition-table.bin': (b'PART%s' % tag) * 300, 'app.bin': (b'APP_%s' % tag) * 2500}
    image = bytearray(b'\xff' * 0x20000)
    for off, fn in ((0, 'bootloader.bin'), (0x8000, 'partition-table.bin'), (0x10000, 'app.bin')):
        image[off:off + len(files[fn])] = files[fn]
    files.update({'flash_image.bin': bytes(image), 'flash_args.txt': FLASH_ARGS.encode()})
    for fn, data in files.items():
        open(os.path.join(out, fn), 'wb').write(data)
    repro = json.loads(row['repro_json'])
    repro['conditions'] = {'limits': {'app_partition_b': build_c3.APP_PARTITION_BYTES, 'dram_total_b': 321296, 'cited': 'made up'}}
    row.update(state='built', artifact_sha256=_sha(bytes(image)), app_sha256=_sha(files['app.bin']), flash_bytes=len(files['app.bin']), ram_bytes=88408, built_at='2026-11-23T10:00:00',
               repro_json=json.dumps(repro), hex_path=os.path.join(out, 'flash_image.bin'), image_path=os.path.join(out, 'flash_image.bin'), engines_json='{}')
    gen.write_record(work, row)
    return build_c3.store(work, row)


def _runner(verified, log):
    def run(engine, args, files, flash=False, devices=(), timeout=0):
        log.append({'engine': engine, 'args': list(args), 'files': sorted(files), 'flash': flash})
        return {'ok': True, 'returncode': 0, 'stdout': 'Hash of data verified.\n' * verified, 'stderr': '', 'how': 'local-binary', 'where': 'made up', 'files': {}}
    return run


def run_installer_c3(check):
    with tempfile.TemporaryDirectory(prefix='installer-c3-test-') as td, \
            _env(POLARI_TWIN_TOKEN_FILE=os.path.join(td, 'secret'), POLARI_TWIN_TOKEN_SECRET=None, POLARI_BOARD_HOME=os.path.join(td, 'home'), BOARD_ENGINES_URL=None, ESP_ENGINES_URL=None):
        from board.custom import board_engines as be, installer as I, twin_sessions as TS
        from board.custom.twin_session_fakes import FakeWorker
        from board.custom.twin_session_fakes_c3 import FakeC3Twin
        esp = FakeWorker(kind='c3', twin=FakeC3Twin)
        real = (be.resolve, be.local_image)
        be.local_image = lambda fam='avr': ''
        be.resolve = lambda engine, flash=False: ({'how': 'local-binary', 'where': 'esptool.py (made up)', 'kind': 'flasher', 'why': 'made up for the test'} if engine == 'esptool' else real[0](engine, flash))
        m = _M('FirmwareVariant', 'FirmwareBuild', 'InstallPlan', 'InstallRecord', 'BoardInstance', 'GrpcExposure', 'ProtoContractVersion', 'ScenarioRun', 'SimInstallConfirmation')
        try:
            _kinds(check)
            uno_work = os.path.join(td, 'uno')
            scan = {'host': I.this_host(), 'observed_at': 'now', 'usb': [], 'serial': []}
            before = I.document(m, uno_work, scan=scan)
            ctx = _stores(check, td, m, I, uno_work, scan, before)
            _real_plans(check, m, I, ctx, scan)
            _real_run(check, m, I, ctx, scan)
            _sim(check, m, I, TS, be, esp, ctx)
            _build_door(check, m, I, ctx, td)
            _gate_and_cli(check, m, I, ctx, before, uno_work, scan)
        finally:
            be.resolve, be.local_image = real
            from board.custom import twin_sessions as TS2
            for s in list(TS2._rows(m)):
                if s.state == 'running':
                    with _env(ESP_ENGINES_URL=esp.url), contextlib.suppress(TS2.SessionRefused):
                        TS2.stop(m, s.name)
            esp.close()
            TS2.HUBS.clear()


def _kinds(check):
    from board.custom import gen_c3, install_kinds as IK, variants_c3 as V3
    check('ins-c3-1 table: kinds by board and alias - arduino-uno-r3 / uno -> UNO; esp32-c3 / c3 / esp32c3 -> C3; an unknown word is None',
          IK.of_board('arduino-uno-r3') is IK.UNO and IK.of_alias('uno') is IK.UNO and IK.of_alias('arduino-uno-r3') is IK.UNO and IK.of_board('esp32-c3') is IK.C3 and IK.of_alias('c3') is IK.C3
          and IK.of_alias('ESP32C3') is IK.C3 and IK.of_alias('esp32-c3') is IK.C3 and IK.of_board('nope') is None and IK.of_alias('nope') is None and IK.of_alias('') is None)
    check('ins-c3-1 table: the C3 row takes its names from the modules that own them (board, aliases, default variant) and says its artifact and programmer',
          IK.C3['board'] == V3.BOARD and IK.C3['aliases'] == tuple(gen_c3.ALIASES) and IK.C3['default_variant'] == V3.LIGHT_NAME == LIGHT and IK.C3['artifact'] == 'flash image'
          and IK.C3['programmer'] == 'esptool' and IK.UNO['artifact'] == '.hex' and IK.UNO['default_variant'] == 'uno-sim-rig' and IK.steps(IK.UNO) is None and IK.steps(IK.C3).__name__ == 'board.custom.install_c3')
    check('ins-c3-1 table: a twin name is a kind - twin:esp32-c3 -> C3, twin:arduino-uno-r3 -> UNO, "twin" alone is the UNO (the old spelling); anything else is None',
          IK.of_twin('twin:esp32-c3') is IK.C3 and IK.of_twin('twin:arduino-uno-r3') is IK.UNO and IK.of_twin('twin') is IK.UNO and IK.of_twin('twin:nope') is None and IK.of_twin('pol:esp32-c3@1') is None)
    check('ins-c3-1 table: a variant is a kind (esp32c3-light and every C3 variant -> C3, uno-light -> UNO), a build is a kind by its board_definition (an unknown one is the UNO)',
          IK.of_variant(LIGHT) is IK.C3 and all(IK.of_variant(v) is IK.C3 for v in V3.VARIANT_NAMES) and IK.of_variant('uno-light') is IK.UNO
          and IK.of_build({'board_definition': 'esp32-c3'}) is IK.C3 and IK.of_build({'board_definition': 'arduino-uno-r3'}) is IK.UNO and IK.of_build({}) is IK.UNO)


def _stores(check, td, m, I, uno_work, scan, before):
    from board.custom import gen, gen_c3, install_c3 as C
    work = C.work_dir()
    a = _make_build(work, False, b'a')
    shim = _make_build(work, True, b's')
    names = (a['name'], shim['name'])
    check('ins-c3-1 store: two made-up C3 builds are stored in the C3\'s own folder (%s), the chip-HAL one and the shim one, each with its own record, files and image'
          % os.path.relpath(work, td), a['name'] != shim['name'] and work == gen_c3.default_work() and os.path.basename(work) == 'esp32-c3'
          and all(os.path.isfile(os.path.join(a['store_dir'], f)) for f in ('firmware_build.json', 'flash_args.txt', 'flash_image.bin', 'app.bin')))
    b = I.find_build(m, a['name'])
    check('ins-c3-1 find_build: a C3 build is found by name in the C3 store (the UNO\'s store is not asked for it), as the C3 kind, and a UNO name that does not exist still refuses in words',
          b['artifact_sha256'] == a['artifact_sha256'] and I.IK.of_build(b) is I.IK.C3 and I.find_build(m, shim['name'])['name'] == shim['name']
          and _refuses(I, lambda: I.find_build(m, 'no-such-build'), 'no build named') and not I.all_builds(m, uno_work).get('nope'))
    doc = I.document(m, uno_work, scan=scan, board='c3')
    lb = {x['name']: x for x in doc['builds']}
    hal = lb[a['name']]
    check('ins-c3-1 document(board=c3): kind c3, board esp32-c3, both builds listed with the flash image sizes (app.bin %d B of the %d B partition, RAM %d of the build\'s own %d), percentages, '
          'compat, installable, the gate' % (hal['flash_bytes'], hal['flash_max'], hal['ram_bytes'], hal['ram_max']),
          doc['kind'] == 'c3' and doc['board'] == 'esp32-c3' and set(lb) == set(names) and hal['flash_bytes'] == 12500 and hal['flash_max'] == 0x100000 and hal['ram_bytes'] == 88408
          and hal['ram_max'] == 321296 and hal['flash_pct'] == 1.2 and hal['ram_pct'] == 27.5 and hal['compat'] == 'compatible' and hal['installable'] is True and hal['gate']['gated'] is True
          and doc['limits']['flash_b'] == 0x100000 and 'partitions.csv' in doc['limits']['cited'], (hal['compat'], hal['compat_why']))
    check('ins-c3-1 document(board=c3): the targets are the C3 twin (no port) - not the UNO\'s; the variants are the C3\'s (esp32c3-light is in, uno-light is not); the modes name the twin session and esptool; the kinds are listed',
          [t['name'] for t in doc['targets']] == ['twin:esp32-c3'] and doc['targets'][0]['port'] == '' and LIGHT in {v['name'] for v in doc['variants']} and 'uno-light' not in {v['name'] for v in doc['variants']}
          and 'twin session' in doc['modes'][0]['words'] and 'esptool' in doc['modes'][1]['words'] and [k['name'] for k in doc['kinds']] == ['uno', 'c3'] and doc['twin']['state'] == 'down'
          and 'UNO' not in json.dumps(doc['modes']) and '.hex' not in json.dumps(doc['modes']) and 'simavr' not in json.dumps(doc['modes']))
    pw = json.dumps(doc['page'])
    check('ins-c3-2 document(board=c3): the page words are the C3\'s (artifact "flash image", no bridge to attach) and name no UNO, .hex or simavr; '
          'the UNO document\'s page words are the ones the page showed before (.hex, the simavr twin, attach)',
          doc['page']['artifact'] == 'flash image' and doc['page']['attach'] is False and 'UNO' not in pw and '.hex' not in pw and 'simavr' not in pw
          and before['page']['artifact'] == '.hex' and before['page']['attach'] is True and 'simavr' in before['page']['twin_note'], pw[:200])
    nolimit = dict(a, repro_json='{}')
    lim = C.limits(nolimit)
    unstated = I.IK.steps(I.IK.C3).limits({})
    check('ins-c3-1 limits: a build that states no DRAM total has NO RAM limit (None - the page says "not stated", nothing is invented) and its percentage is None, not a crash',
          lim[1] is None and lim[0] == 0x100000 and unstated[1] is None and I._pct(5, None) is None and I._pct(None, 5) is None and I._pct(5, 10) == 50.0)
    uno_after = I.document(m, uno_work, scan=scan)
    check('ins-c3-1 document(): the UNO document does not list the C3 builds and is what it was apart from its two new keys (kind uno, kinds)',
          not (set(names) & {x['name'] for x in uno_after['builds']}) and uno_after['kind'] == 'uno' and [k['name'] for k in uno_after['kinds']] == ['uno', 'c3']
          and json.dumps({k: v for k, v in uno_after.items() if k not in ('kind', 'kinds')}, sort_keys=True) == json.dumps({k: v for k, v in before.items() if k not in ('kind', 'kinds')}, sort_keys=True))
    check('ins-c3-1 document(board=nope) refuses in words naming the boards it knows', _refuses(I, lambda: I.document(m, uno_work, scan=scan, board='nope'), "no installer board 'nope'"))
    return {'a': a, 'shim': shim, 'work': work, 'sha': a['artifact_sha256'], 'inst': 'pol:esp32-c3@001-3'}


def _state(m, I, name):
    r = I._by_name(m, 'FirmwareBuild', name)
    return getattr(r, 'state', '')


def _refuses(I, fn, words):
    try:
        fn()
    except I.InstallRefused as e:
        return words in str(e)
    return False


def _prove(m, sha, who_sha, runs_sha=None, tick=True, observed=None):
    """Four passed Purpose runs of the light (each naming `runs_sha` in what it observed, or `observed`), then (tick) a person's tick for `who_sha`."""
    from board.custom import sim_gate as G
    from firmwarefaults.custom.sink import ManagerSink
    sink = ManagerSink(m)
    for i, p in enumerate(G.purpose_runs(m, LIGHT)):
        sink.upsert('ScenarioRun', {'name': 'sr-c3-%s-%d' % (p['scenario'], i), 'scenario': p['scenario'], 'side': 'after', 'variant': LIGHT, 'outcome': 'passed', 'verdict_words': 'passed on the pin model',
                                    'repro_json': json.dumps({'mode': 'digital-twin'}), 'ran_at': '2026-11-23T10:%02d:00' % i,
                                    'observed_json': json.dumps(observed if observed is not None else {'sha256': runs_sha or sha})})
    if tick:
        G.confirm(m, LIGHT, who_sha, 'tester', 'installer')


def _plan(I, m, inst, build, scan, **kw):
    return I.plan(m, inst, build, scan=scan, **kw)


def _real_plans(check, m, I, ctx, scan):
    from board.custom import flash_c3, gen, install_c3 as C
    a, shim, sha = ctx['a'], ctx['shim'], ctx['sha']
    store = a['store_dir']
    flat = ' '.join(flash_c3.argv_for('{port}', store, FLASH_ARGS))
    p = _plan(I, m, 'undetected:esp32-c3', a['name'], scan)
    ck = {c['name']: c for c in p['checks']}
    check('ins-c3-1 REAL plan against `undetected:esp32-c3` (nothing nobody ever plugged in): REFUSED, in the gate\'s words (nothing proven, nobody ticked) and in words that no ESP32-C3 is detected - and it still '
          'carries esptool\'s EXACT command with {port} as the placeholder (flash_c3.argv_for); check image-is-the-files is ok',
          p['refused'] and 'no ESP32-C3 is detected on this host: nothing can be installed' in p['why'] and 'command that would run once one is plugged in' in p['why'] and 'REFUSED (sim not confirmed)' in p['why']
          and 'nobody has ticked' in p['why'] and p['argv_text'] == flat and '{port}' in p['argv_text'] and p['argv_text'].startswith('esptool.py --chip esp32c3 --port {port} --baud 460800 write_flash')
          and p['install_mode'] == 'real' and p['gate'] == 'not-offered' and p['engine'] == 'esptool' and p['programmer'] == 'esptool' and ck['image-is-the-files']['ok'] and ck['chip-hal']['ok']
          and ck['runs-on-this-image']['ok'] and I._by_name(m, 'InstallPlan', p['name']).state == 'refused', p['why'])
    check('ins-c3-1 the checks say what they found, in words: %s' % ck['image-is-the-files']['words'],
          'the 3 files esptool writes are the image the twin ran, byte for byte' in ck['image-is-the-files']['words'] and 'at 0x0, 0x8000, 0x10000' in ck['image-is-the-files']['words']
          and 'chip-HAL build of %s' % LIGHT in ck['chip-hal']['words'])
    try:
        I.run(m, p['name'], True, scan=scan)
        check('a run of an undetected plan refuses', False)
    except I.InstallRefused as e:
        check('ins-c3-1 a RUN of the `undetected:` plan is refused (the plan is refused; nothing is opened)', "is 'refused'" in str(e) and 'no ESP32-C3 is detected' in str(e) and e.code == 3)
    from board.board_basis import BoardInstance
    I.upsert(m, BoardInstance,
             {'name': ctx['inst'], 'definition': 'esp32-c3', 'definition_kind': 'board', 'state': 'board present', 'host': I.this_host(), 'by_id_path': PORT, 'port': '/dev/ttyACM9'})
    d = _plan(I, m, ctx['inst'], a['name'], scan)
    check('ins-c3-1 REAL plan against a made-up detected C3, nothing proven: REFUSED with the gate\'s words (0 of 4 Purposes, nobody ticked) and the sim-install offer; the command has the real port',
          d['refused'] and 'REFUSED (sim not confirmed)' in d['why'] and '0 of 4 passed' in d['why'] and 'Do the sim install first' in d['why'] and 'no ESP32-C3 is detected' not in d['why']
          and PORT in d['argv_text'] and '{port}' not in d['argv_text'] and d['gate'] == 'not-offered', d['why'])
    # negative controls: install anyway
    ay = _plan(I, m, ctx['inst'], a['name'], scan, install_anyway=True)
    check('ins-c3-1 "install anyway" with no reason is refused in words that ask for the reason', ay['refused'] and 'needs the reason' in ay['why'])
    ay = _plan(I, m, ctx['inst'], a['name'], scan, install_anyway=True, reason='bench check on a spare board')
    check('ins-c3-1 "install anyway" WITH a reason gets past the gate (planned, gate overridden, the reason on the row, notes say INSTALLED ANYWAY and quote what the gate said)',
          not ay['refused'] and ay['gate'] == 'overridden' and ay['override_reason'] == 'bench check on a spare board' and 'INSTALLED ANYWAY' in ay['notes'] and 'nobody has ticked' in ay['notes'], ay['why'])
    # a shim build: refused for a real board; install anyway does not pass it
    sh = _plan(I, m, ctx['inst'], shim['name'], scan, install_anyway=True, reason='bench check on a spare board')
    shc = {c['name']: c for c in sh['checks']}
    check('ins-c3-1 NEGATIVE a SHIM build (pin_shim 1) is refused for a real board in words - its pins are RAM, it drives no pad, a chip-HAL build is needed - and "install anyway" with a reason does NOT pass it',
          sh['refused'] and not shc['chip-hal']['ok'] and 'REFUSED (chip-hal): this is the shim build: its pins are RAM, it drives no pad. A real board needs the chip-HAL build of %s' % LIGHT in sh['why']
          and sh['gate'] == 'overridden' and shc['image-is-the-files']['ok'], sh['why'])
    # a file that differs from the image
    app = os.path.join(store, 'app.bin')
    orig = open(app, 'rb').read()
    open(app, 'wb').write(orig[:100] + bytes([orig[100] ^ 1]) + orig[101:])
    try:
        tp = _plan(I, m, ctx['inst'], a['name'], scan, install_anyway=True, reason='bench check on a spare board')
        tc = {c['name']: c for c in tp['checks']}
        check('ins-c3-1 NEGATIVE one byte of app.bin changed: REFUSED, the words name the file and its offset and say what was simulated is not what would be written; "install anyway" does NOT pass it',
              tp['refused'] and not tc['image-is-the-files']['ok'] and 'REFUSED (image-is-the-files): the file app.bin (esptool writes it at 0x10000) differs from the same place in the image the twin ran: '
              'what was simulated is not what would be written' in tp['why'] and tc['chip-hal']['ok'], tp['why'])
        os.remove(app)
        mp = _plan(I, m, ctx['inst'], a['name'], scan)
        check('ins-c3-1 NEGATIVE a missing file is refused in words naming it (and where esptool writes it)', mp['refused'] and 'the file app.bin that esptool writes at 0x10000 is missing' in mp['why'], mp['why'])
    finally:
        open(app, 'wb').write(orig)
    fa = os.path.join(store, 'flash_args.txt')
    fa_text = open(fa).read()
    os.remove(fa)
    try:
        fp = _plan(I, m, ctx['inst'], a['name'], scan)
        check('ins-c3-1 NEGATIVE a missing flash_args.txt is refused in words (it is not guessed), and no command is made', fp['refused'] and 'no flash_args.txt beside the build' in fp['why']
              and 'cannot be made' in fp['why'] and fp['argv_text'] == '', fp['why'])
    finally:
        open(fa, 'w').write(fa_text)
    check('ins-c3-1 the store is whole again after the negative controls (the image is the files)', C._check_files(I.find_build(m, a['name']))['ok'])
    # the Purposes ran ANOTHER image / no image
    _prove(m, sha, sha, runs_sha='b' * 64)
    other = _plan(I, m, ctx['inst'], a['name'], scan)
    check('ins-c3-1 NEGATIVE the four Purposes were proved on ANOTHER image (a tick for this one is on file): REFUSED, the words name the Purpose, both numbers and how to run them again',
          other['refused'] and 'REFUSED (runs-on-this-image)' in other['why'] and 'was proved on another image (bbbbbbbbbbbbbbbb…), not this one (%s…)' % sha[:16] in other['why']
          and 'pol firmware prove %s' % LIGHT in other['why'] and other['gate'] == 'offered' and 'REFUSED (sim not confirmed)' not in other['why'], other['why'])
    for r in I._rows(m, 'ScenarioRun'):
        r.observed_json = json.dumps({'note': 'a run that records no image'})
    none = _plan(I, m, ctx['inst'], a['name'], scan)
    check('ins-c3-1 NEGATIVE a Purpose run that names no image does not count for a C3: REFUSED in words ("names no image")', none['refused'] and 'names no image' in none['why'] and 'REFUSED (runs-on-this-image)' in none['why'], none['why'])
    for r in I._rows(m, 'ScenarioRun'):
        r.observed_json = json.dumps({'sha256': sha})
    ok = _plan(I, m, ctx['inst'], a['name'], scan)
    ok_ck = {c['name']: c for c in ok['checks']}
    check('ins-c3-1 four passed Purpose runs that name THIS image and a valid tick for this sha256: the REAL plan against the detected C3 is PLANNED, gate offered, all three checks ok, their words in the notes after the DRY-RUN sentence',
          not ok['refused'] and ok['state'] == 'planned' and ok['gate'] == 'offered' and all(c['ok'] for c in ok['checks']) and len(ok['checks']) == 3
          and ok['notes'].startswith('DRY-RUN: nothing was opened. Install needs this plan AND confirm.') and 'check image-is-the-files: the 3 files esptool writes' in ok['notes']
          and 'the 4 proving runs name this image (sha256 %s…)' % sha[:16] in ok_ck['runs-on-this-image']['words'] and ok['argv_text'].split()[4] == PORT, ok['why'])
    ctx['ok_plan'] = ok['name']


def _sim(check, m, I, TS, be, esp, ctx):
    from board.custom import twin_token
    a, sha = ctx['a'], ctx['sha']
    p = I.plan(m, 'twin:esp32-c3', a['name'])
    check('ins-c3-1 SIM plan with no ESP engines worker set: REFUSED in the resolver\'s own words (names ESP_ENGINES_URL and the worker); no command line is invented',
          p['refused'] and 'ESP_ENGINES_URL' in p['why'] and p['install_mode'] == 'sim' and p['argv_text'].startswith('no command line:') and p['engine_how'] == 'refused', p['why'])
    printed = io.StringIO()
    with _env(ESP_ENGINES_URL=esp.url):
        p = I.plan(m, 'twin:esp32-c3', a['name'])
        check('ins-c3-1 SIM plan: planned; there is no command line, and the words say the backend asks the ESP engines worker for a twin session with this image (sha256), the pin layout and the LED-to-sense wire; the engine is the worker',
              not p['refused'] and p['argv_json'] == '[]' and p['argv_text'].startswith('no command line: the backend asks the ESP engines worker for a twin session with this image (sha256 %s…)' % sha[:16])
              and "the chip's pin layout and the LED-to-sense wire" in p['argv_text'] and p['programmer'] == 'twin session (the pin-model QEMU)' and p['engine'] == 'qemu-esp32c3' and p['engine_how'] == 'remote'
              and p['engine_where'] == esp.url and p['gate'] == 'not-gated' and 'no BoardInstance is stamped' in p['will_stamp'], p['why'])
        with contextlib.redirect_stdout(printed):   # whatever the install prints (nothing is meant to) is kept and read for the token
            r = I.run(m, p['name'], True)
        rows = [s for s in TS._rows(m) if s.state == 'running']
        token = twin_token.derive(rows[0].name) if rows else 'no-session'
        blob = json.dumps({k: v for k, v in r.items() if k != 'row'}, default=str) + json.dumps(p, default=str) + json.dumps(TS.listing(m), default=str) + json.dumps(
            [vars(x) for x in I._rows(m, 'InstallRecord')], default=str) + json.dumps([vars(x) for x in I._rows(m, 'InstallPlan')], default=str)
        check('ins-c3-1 SIM run: installed; a running session row exists with THIS build\'s sha256 (%d bytes, the image), the record says twin and names the session, verify says the same number as the build'
              % len(open(a['hex_path'], 'rb').read()), r['verdict'] == 'installed' and len(rows) == 1 and rows[0].hex_sha256 == sha and rows[0].config == LIGHT and rows[0].board == 'esp32-c3'
              and rows[0].name in r['notes'] and r['target_kind'] == 'twin' and r['install_mode'] == 'sim' and r['firmware_sha'] == sha and r['verified_bytes'] == rows[0].hex_bytes
              and ('started twin session %s with this image' % rows[0].name) in r['verify'] and 'the same number as the build' in r['verify'] and 'set GPIO3 0' in r['notes'] and 'not a chip' in r['notes'], r.get('verify'))
        sent = next(iter(esp.twins.values()))['body']
        check('ins-c3-1 SIM run: the worker was sent the build\'s own image (image_b64 = the flash image, sha256 equal), the layout and the LED-to-sense wire; the FirmwareBuild row says flashed',
              _sha(__import__('base64').b64decode(sent['image_b64'])) == sha and sent['wires'] == '0-1' and sent['board'] == 'esp32-c3' and _state(m, I, a['name']) == 'flashed')
        check('ins-c3-1 SIM: NO token anywhere - not in the record, the plan, the returned dict, the session listing, any row, or what was printed', token not in blob and token not in printed.getvalue() and 'token' not in r
              and 'token' not in json.dumps(r.get('row') and vars(r['row']), default=str), token[:0])
        before = len(rows)
        with _env(ESP_ENGINES_URL=esp.url):
            r2 = I.run(m, I.plan(m, 'twin:esp32-c3', a['name'])['name'], True)
        check('ins-c3-1 SIM: a second install starts a second session and leaves the first alone (sessions are not stopped by the installer)',
              r2['verdict'] == 'installed' and len([s for s in TS._rows(m) if s.state == 'running']) == before + 1 and rows[0].state == 'running')
        st = I.document(m, board='c3', scan={'host': I.this_host(), 'usb': [], 'serial': []})['twin']
        check('ins-c3-1 document(board=c3): the twin status reads the running sessions (state up, the newest session, config, sha256)', st['state'] == 'up' and st['variant'] == LIGHT and st['hex_sha256'] == sha and st['session'])
        for s in [s for s in TS._rows(m) if s.state == 'running']:
            TS.stop(m, s.name)
    check('ins-c3-1 SIM: every session is stopped again at the end (the worker holds none)', not esp.twins and not [s for s in TS._rows(m) if s.state == 'running'])
    from board.custom import install_c3 as C
    bad = C.run_twin(m, dict(a, variant='c3-sim-rig'))
    check('ins-c3-1 SIM: a worker/kind refusal is a FAILED record in the refusal\'s words, never an exception or a half state (a C3 variant with no pads has nothing to press)',
          bad['verdict'] == 'failed' and 'uses no pad' in bad['notes'] and not bad['firmware_sha'])


def _real_run(check, m, I, ctx, scan):
    a, sha = ctx['a'], ctx['sha']
    p = I._by_name(m, 'InstallPlan', ctx['ok_plan'])
    log = []
    two = I.run(m, p.name, True, scan=scan, flash_run=_runner(2, log))
    inst = I._by_name(m, 'BoardInstance', ctx['inst'])
    check('ins-c3-1 REAL run, a made-up esptool that prints "Hash of data verified" TWICE: verdict failed, nothing stamped (the board keeps no firmware_sha, the build is not flashed, the record names the shortfall)',
          two['verdict'] == 'failed' and not inst.firmware_sha and _state(m, I, a['name']) != 'flashed' and '2 of 3 images hash-verified' in two['log_tail']
          and I.find_build(m, a['name'])['state'] == 'built' and log and log[0]['engine'] == 'esptool', two.get('log_tail'))
    p2 = I.plan(m, ctx['inst'], a['name'], scan=scan)
    log3 = []
    three = I.run(m, p2['name'], True, scan=scan, flash_run=_runner(3, log3))
    inst = I._by_name(m, 'BoardInstance', ctx['inst'])
    want = sum(os.path.getsize(os.path.join(a['store_dir'], f)) for f in ('bootloader.bin', 'partition-table.bin', 'app.bin'))
    args = log3[0]['args']
    check('ins-c3-1 REAL run, esptool prints it THREE times: verdict installed - esptool wrote 3 files and verified the hash of each (%d bytes); the build is stamped flashed, the BoardInstance is stamped with the '
          'firmware sha and the run time; the runner was handed the plan\'s port and the three files (no real process)' % want,
          three['verdict'] == 'installed' and three['verified_bytes'] == want and 'esptool wrote 3 files and verified the hash of each' in three['verify'] and three['install_mode'] == 'real'
          and I._by_name(m, 'FirmwareBuild', a['name']).state == 'flashed' and inst.firmware_sha == sha and inst.last_flash_at and I.find_build(m, a['name'])['state'] == 'flashed'
          and args[args.index('--port') + 1] == PORT and log3[0]['files'] == ['app.bin', 'bootloader.bin', 'partition-table.bin'] and log3[0]['flash'] is True, (three.get('verify'), args))
    # run-time re-check: a plan made while everything held is refused once a file no longer equals the image
    p3 = I.plan(m, ctx['inst'], a['name'], scan=scan)
    app = os.path.join(a['store_dir'], 'app.bin')
    orig = open(app, 'rb').read()
    open(app, 'wb').write(orig + b'x')
    try:
        I.run(m, p3['name'], True, scan=scan, flash_run=_runner(3, []))
        check('a run after the files changed refuses', False)
    except I.InstallRefused as e:
        check('ins-c3-1 REAL run RE-READS the checks: a plan made while the files were the image is REFUSED at run time once app.bin changed - in words, the plan row says refused and why',
              'REFUSED (image-is-the-files)' in str(e) and 'app.bin' in str(e) and I._by_name(m, 'InstallPlan', p3['name']).state == 'refused' and 'at run time' in I._by_name(m, 'InstallPlan', p3['name']).notes)
    finally:
        open(app, 'wb').write(orig)


def _build_door(check, m, I, ctx, td):
    from board.custom import gen, install_c3 as C, light_c3_run as R
    a = ctx['a']
    calls = []
    real = R.build
    R.build = lambda work, variant=None, **knobs: calls.append((work, variant, knobs)) or dict(a)
    try:
        rec = I.build_variant(m, LIGHT)
    finally:
        R.build = real
    fb = I._by_name(m, 'FirmwareBuild', a['name'])
    check('ins-c3-1 build_variant: a C3 variant goes to the C3 steps - exactly light_c3_run.build(work, variant, pin_shim=0) (the same call the twin session makes, so the sha256 is the same number) in the C3\'s own folder - '
          'and the FirmwareBuild row is written from the stored record', calls == [(C.work_dir(), LIGHT, {'pin_shim': 0})] and rec['name'] == a['name'] and fb is not None and fb.artifact_sha256 == a['artifact_sha256'])
    R.build = lambda work, variant=None, **knobs: (_ for _ in ()).throw(gen.GenRefused('made-up generator refusal'))
    try:
        refused = _refuses(I, lambda: I.build_variant(m, LIGHT), 'made-up generator refusal')
    finally:
        R.build = real
    check('ins-c3-1 build_variant: a generator refusal of a C3 variant is an InstallRefused (400) in its own words', refused)
    log = []

    def fake(engine, args, files, **kw):
        log.append((engine, args, sorted(files)))
        return {'ok': False, 'returncode': 1, 'stdout': '', 'stderr': 'made up', 'files': {'build.log': b'made-up build log'}, 'how': 'local-binary', 'where': 'made up'}
    row = C.build(m, 'c3-sim-rig', os.path.join(td, 'other-work'), run=fake)
    check('ins-c3-1 build of a C3 variant that is not the light: no knobs (the variant has no pads), the engine call is the shipped build_c3\'s (idf-build, project.tar) through the injected runner; a failed build is a refused row',
          row['state'] == 'refused' and 'idf.py build failed' in row['notes'] and log == [('idf-build', ['project.tar'], ['project.tar'])] and row['variant'] == 'c3-sim-rig')
    check('ins-c3-1 build of an unknown C3 variant name is a generator refusal in words', _raises(gen.GenRefused, lambda: C.build(m, 'c3-nope', os.path.join(td, 'x'))))
    import falcon
    import falcon.testing as ft
    from board.installer_api import BoardInstallerAPI
    app = falcon.App()
    api = BoardInstallerAPI(polServer=__import__('types').SimpleNamespace(falconServer=app), manager=m)
    cl = ft.TestClient(app)
    doc = cl.simulate_get('/api/board/installer?board=c3').json
    uno = cl.simulate_get('/api/board/installer').json
    check('ins-c3-1 DOOR GET /api/board/installer?board=c3 is the C3\'s document; with no board it is the UNO\'s (no new route)', doc['kind'] == 'c3' and doc['board'] == 'esp32-c3' and uno['kind'] == 'uno' and uno['board'] == 'arduino-uno-r3'
          and a['name'] in {x['name'] for x in doc['builds']} and a['name'] not in {x['name'] for x in uno['builds']})
    pl = cl.simulate_post('/api/board/installer/plan', json={'instance': 'undetected:esp32-c3', 'build': a['name']})
    check('ins-c3-1 DOOR POST .../plan of the undetected C3 answers 409 with the words, esptool\'s command and the checks (what the CLI prints)', pl.status_code == 409 and not pl.json['ok']
          and pl.json['argv_text'].startswith('esptool.py --chip esp32c3 --port {port}') and [c['name'] for c in pl.json['checks']] == ['chip-hal', 'image-is-the-files', 'runs-on-this-image'] and pl.json['exit'] == 3)
    del api


def _raises(exc, fn):
    try:
        fn()
    except exc:
        return True
    return False


def _gate_and_cli(check, m, I, ctx, before, uno_work, scan):
    from board.custom import install_cli as CLI, light_c3_run as R, light_twin as LT, sim_gate as G
    asked = []
    real = (LT.engine_ready, R.engine_ready)
    LT.engine_ready = lambda: asked.append('uno-twin') or (False, 'made up: no simavr here')
    R.engine_ready = lambda: asked.append('esp-engines') or (False, 'made up: no ESP engines here')
    try:
        c3 = _msg(I, lambda: G.sim_install(m, LIGHT))
        c3_asked, asked[:] = list(asked), []
        uno = _msg(I, lambda: G.sim_install(m, 'uno-light'))
        uno_asked = list(asked)
    finally:
        LT.engine_ready, R.engine_ready = real
    check('ins-c3-1 sim_install of a C3 config asks the C3 engines whether they are ready (not the UNO twin) and refuses in words for that board, with the `pol firmware prove` command',
          c3_asked == ['esp-engines'] and 'no ESP engines that can run the ESP32-C3 twin' in c3 and 'no ESP engines here' in c3 and 'pol firmware prove %s' % LIGHT in c3 and 'simavr' not in c3 and 'UNO' not in c3, c3)
    check('ins-c3-1 sim_install of a UNO config still asks the UNO twin, in its old words', uno_asked == ['uno-twin'] and 'this server cannot run the twin itself' in uno and 'a host with the simavr twin' in uno, uno)
    check('ins-c3-1 sim_install of the UNO\'s bench variant still refuses first, in the old words (no Purposes)', 'no Purposes to run' in _msg(I, lambda: G.sim_install(m, 'uno-echo')))
    g = G.verdict(m, LIGHT, ctx['sha'])
    check('ins-c3-1 gate / confirm-sim take a C3 config as they are: the gate holds %s (gated, 4 Purposes)' % LIGHT, g['gated'] and len(g['purposes']) == 4)
    check('ins-c3-1 CLI: the board word picks the kind (uno, arduino-uno-r3 -> UNO; c3, esp32c3, esp32-c3 -> C3; anything else none) and the default variant (uno-sim-rig | esp32c3-light); the twin target is the kind\'s',
          CLI.kind_of('uno')['name'] == 'uno' and CLI.kind_of('arduino-uno-r3')['name'] == 'uno' and all(CLI.kind_of(w)['name'] == 'c3' for w in ('c3', 'esp32c3', 'esp32-c3')) and CLI.kind_of('stm32') is None
          and CLI.kind_of('uno')['default_variant'] == 'uno-sim-rig' and CLI.kind_of('c3')['default_variant'] == LIGHT and CLI.kind_of('c3')['twin'] == 'twin:esp32-c3' and CLI.kind_of('uno')['twin'] == 'twin:arduino-uno-r3')
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        CLI._print_checks([{'name': 'chip-hal', 'ok': True, 'words': 'fine'}, {'name': 'image-is-the-files', 'ok': False, 'words': 'differs'}])
    check('ins-c3-1 CLI: each check is printed as a line, [ ok ] or [MISSING]', '[ ok ] chip-hal' in out.getvalue() and '[MISSING] image-is-the-files' in out.getvalue() and 'differs' in out.getvalue())
    with contextlib.redirect_stdout(out):
        rc = CLI.main(['install', 'stm32', '--sim', '--api', 'http://nowhere.invalid'])
    check('ins-c3-1 CLI: an unknown board word is refused in words naming uno and c3 (exit 3), before any call', rc == 3 and 'UNO (uno) and the ESP32-C3 (c3)' in out.getvalue())
    again = I.document(m, uno_work, scan=scan)
    check('ins-c3-1 after all of that - C3 plans, runs, ticks and sessions on the same manager - the UNO document is still what it was, apart from kind and kinds',
          json.dumps({k: v for k, v in again.items() if k not in ('kind', 'kinds')}, sort_keys=True) == json.dumps({k: v for k, v in before.items() if k not in ('kind', 'kinds')}, sort_keys=True))


def _msg(I, fn):
    try:
        fn()
    except I.InstallRefused as e:
        return str(e)
    return ''


if __name__ == '__main__':
    n = [0, 0]

    def _check(label, cond, extra=''):
        n[0] += 1
        n[1] += bool(cond)
        print('  [%s] %s %s' % ('PASS' if cond else 'FAIL', label, '' if cond else extra))
    run_installer_c3(_check)
    print('%d/%d checks passed' % (n[1], n[0]))
    raise SystemExit(0 if n[0] == n[1] else 1)
