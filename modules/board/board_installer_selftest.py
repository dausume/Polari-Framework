"""board_installer_selftest — brd-fi's half of the board selftest (called by board.board_selftest): the firmware_installer
section. Variants as rows (four DIFFERENT things to test on one UNO; knob refusals with the reason); gen per variant
captures header_sha256 + the wire (tag) order; the SECOND class's header round-trips through the Python wire reference;
compatibility judged on the header itself — a v1/v2 field-order difference with the SAME contract_hash is caught; the
installer flow over rows (document → build → plan = DRY-RUN → run needs the plan AND confirm AND this host → record),
into the twin (a FAKE polari-avr-twin) and onto a board (a FAKE avrdude + a faked scan); attach refuses without the
exposure; the page is configured tables + exactly ONE new component. The REAL avr-gcc + simavr + Java bridge path is
tests/board_installer_probe.py.
"""
import json
import os
import shutil
import tempfile
import types

V1_SIMRIG = {'fields': {'led_on': {'tag': 1, 'proto_type': 'bool', 'comment': ''}, 'name': {'tag': 2, 'proto_type': 'string', 'comment': ''},
                        'pwm_duty': {'tag': 3, 'proto_type': 'int64', 'comment': ''}, 'status': {'tag': 4, 'proto_type': 'string', 'comment': ''},
                        'temp_c': {'tag': 5, 'proto_type': 'double', 'comment': ''}, 'uptime_ms': {'tag': 6, 'proto_type': 'int64', 'comment': ''}},
             'reserved': []}   # what a FRESH server generates (brd-1's finding: alphabetical tags, hash 2bcc9d1a2774ef33 like v2)


class _M:
    """A manager that is only what the installer touches: the tables, ids, a no-op persist (the cicd selftest's shape)."""

    def __init__(self, *classes):
        self.objectTables = {c: {} for c in classes}
        self.idList = []
        self.db = None

    def persistTree(self):
        return None

    def noteTreeMutation(self, *a, **k):
        return None


def _expose(m, cls, version, fmap, chash, transport='both'):
    m.objectTables.setdefault('GrpcExposure', {})['e-' + cls] = types.SimpleNamespace(subject_class=cls, proto_version=version, contract_hash=chash,
                                                                                       transport_preference=transport)
    m.objectTables.setdefault('ProtoContractVersion', {})['v-%s-%d' % (cls, version)] = types.SimpleNamespace(
        subject_class=cls, version=version, field_map_json=json.dumps(fmap))


def variants(check):
    from board.custom import variants as V
    vs = V.SEED_FIRMWARE_VARIANTS
    check('firmware_installer: four seeded UNO variants — uno-sim-rig, uno-blink-only, uno-adc-sweep, uno-echo',
          [v['name'] for v in vs] == ['uno-sim-rig', 'uno-blink-only', 'uno-adc-sweep', 'uno-echo'])
    res = {v['name']: V.resolve(v) for v in vs}
    check('variants: four DIFFERENT apps; the adc sweep speaks a second class (UnoAnalogState)',
          len({r['app'] for r in res.values()}) == 4 and res['uno-adc-sweep']['classes'] == ['UnoAnalogState']
          and all(r['classes'] == ['SimRigState'] for n, r in res.items() if n != 'uno-adc-sweep'))
    check('variants: features differ — blink = LED only, echo = commands only, adc = ADC only, sim-rig = all four',
          res['uno-blink-only']['features'] == {'led': True, 'pwm': False, 'adc': False, 'commands': False}
          and res['uno-echo']['features'] == {'led': False, 'pwm': False, 'adc': False, 'commands': True}
          and res['uno-adc-sweep']['features'] == {'led': False, 'pwm': False, 'adc': True, 'commands': False}
          and all(res['uno-sim-rig']['features'].values()))
    check('variants: every one says what it tests and what to watch for (plain words)', all(v['purpose'] and v['what_to_watch'] for v in vs))
    from board.board_basis import FirmwareVariant
    check('variants: every seed constructs a FirmwareVariant row', all(FirmwareVariant(**v).name == v['name'] for v in vs))
    base = dict(vs[0])
    cases = [({'knobs_json': json.dumps({'pwm_pin': 3})}, 'Timer2'), ({'knobs_json': json.dumps({'led_pin': 1})}, 'USB serial'),
             ({'features_json': json.dumps({'led': True, 'pwm': True, 'adc': True, 'commands': True}), 'app': 'blink'}, 'cannot use'),
             ({'build_flags_json': json.dumps(['LED_PIN=3'])}, 'redefines a knob'), ({'build_flags_json': json.dumps(['X=$(rm -rf /)'])}, 'NAME=integer'),
             ({'knobs_json': json.dumps({'telemetry_hz': 200})}, '1..50'), ({'classes_json': json.dumps(['UnoAnalogState'])}, 'written for')]
    ok = []
    for over, why in cases:
        try:
            V.resolve(dict(base, **over))
            ok.append((why, 'accepted'))
        except V.VariantRefused as e:
            ok.append((why, why in str(e)))
    check('variants: bad knobs are REFUSED with the reason (PWM on Timer2, LED on D1, an app feature it has no code for, a flag '
          'redefining a knob, a flag that is not NAME=integer, 200 Hz, a class the app is not written for)', all(x is True for _, x in ok), ok)
    r = V.resolve(dict(base, build_flags_json=json.dumps(['MY_TRIM=7'])))
    check('variants: a legal build flag lands as a define in board_config.h (never a compiler argument)', '#define MY_TRIM 7' in V.render_config(r))


def gen_and_compat(check, tmp):
    from board.custom import gen, compat, packet_ref
    rows = {}
    for v in ('uno-sim-rig', 'uno-blink-only', 'uno-adc-sweep', 'uno-echo'):
        rows[v] = gen.gen('uno', work=os.path.join(tmp, v), variant=v)
    plain = gen.gen('uno', work=os.path.join(tmp, 'plain'))
    check('gen without --variant = uno-sim-rig (brd-1 unchanged)', plain['variant'] == 'uno-sim-rig')
    check('gen --class UnoAnalogState alone picks uno-adc-sweep', gen.gen('uno', ['UnoAnalogState'], os.path.join(tmp, 'cls'))['variant'] == 'uno-adc-sweep')
    a = rows['uno-adc-sweep']
    proj = a['project_dir']
    hdr = open(os.path.join(proj, 'unoanalogstate_packets.h')).read()
    check('gen uno-adc-sweep: the project carries unoanalogstate_packets.h (target avr, contract v1 hash 078e20a0f939956b) — the generator handles a second class',
          'UNOANALOGSTATE_MSG_TYPE' in hdr and 'target avr' in hdr and 'contract v1   hash 078e20a0f939956b' in hdr and 'int64_t a0;' in hdr
          and sorted(os.listdir(proj)) == ['Makefile', 'board_config.h', 'hal.c', 'hal.h', 'main.c', 'unoanalogstate_packets.h'])
    check('gen: header_sha256 + tag order captured on the row (the wire order, from the header itself)',
          all(r['header_sha256'] == json.loads(r['classes_json'])[0]['header_sha256'] for r in rows.values())
          and json.loads(a['tag_order_json']) == {'UnoAnalogState': ['a0', 'a1', 'a2', 'name', 'status', 'uptime_ms']}
          and json.loads(rows['uno-echo']['tag_order_json'])['SimRigState'] == ['name', 'pwm_duty', 'status', 'temp_c', 'uptime_ms', 'led_on'])
    cfg = open(os.path.join(rows['uno-blink-only']['project_dir'], 'board_config.h')).read()
    check('gen: the variant\'s features land in board_config.h (blink: LED on, ADC/PWM/commands off, BLINK_MS 500)',
          'FEATURE_LED  1' in cfg and 'FEATURE_ADC  0' in cfg and 'FEATURE_PWM  0' in cfg and 'FEATURE_COMMANDS 0' in cfg and 'BLINK_MS     500u' in cfg)
    c = gen.pinned_contract('UnoAnalogState')[0]
    vals = {'name': 'uno-analog', 'uptime_ms': 1234, 'a0': 153, 'a1': 307, 'a2': 614, 'status': 'ok'}
    f = packet_ref.frame(1, 3, 1, packet_ref.encode_payload(c['field_map'], vals))
    got = packet_ref.StreamParser().feed(b'junk' + f)
    check('UnoAnalogState round-trips through the independent wire reference (frame → resync → decode)',
          len(got) == 1 and packet_ref.decode_payload(c['field_map'], got[0][3]) == vals)
    # ---- compatibility: the header, never the hash alone
    sim = rows['uno-sim-rig']
    v2 = gen.pinned_contract('SimRigState')[0]
    from grpcbridge.custom.proto_gen import contract_hash  # noqa: F401 — the hash function the finding is about
    m2 = _M('GrpcExposure', 'ProtoContractVersion')
    _expose(m2, 'SimRigState', 2, v2['field_map'], v2['contract_hash'])
    r = compat.check(sim, m2)
    check('compat: the build vs a server whose SimRigState exposure is the same v2 → compatible (header byte-identical)', r['verdict'] == 'compatible', r['plain'])
    m1 = _M('GrpcExposure', 'ProtoContractVersion')
    _expose(m1, 'SimRigState', 1, V1_SIMRIG, '2bcc9d1a2774ef33')
    r = compat.check(sim, m1)
    check('compat: a server at v1 (alphabetical tags, the SAME contract_hash 2bcc9d1a2774ef33) → stale-header, both wire orders named',
          r['verdict'] == 'stale-header' and r['classes'][0]['now_order'][0] == 'led_on' and r['classes'][0]['built_order'][0] == 'name'
          and 'misread' in r['plain'] and v2['contract_hash'] == '2bcc9d1a2774ef33', r['plain'])
    r = compat.check(sim, None)
    check('compat: with no exposure the pinned snapshot stands in, labelled pinned → compatible', r['verdict'] == 'compatible' and r['classes'][0]['source'] == 'pinned')
    ghost = dict(sim, classes_json=json.dumps([dict(json.loads(sim['classes_json'])[0], **{'class': 'GhostState'})]))
    r = compat.check(ghost, None)
    check('compat: a class the server has no contract for → unknown-class', r['verdict'] == 'unknown-class' and 'GhostState' in r['plain'])
    check('compat: a build listing no classes is not Polari firmware → unknown-class', compat.check(dict(sim, classes_json='[]'))['verdict'] == 'unknown-class')
    return rows


def flow(check, tmp, fake_runner, size_text, fake_bin, old_path):
    from board.custom import installer as I, twin, attach
    from board import board_basis as BB
    m = _M('FirmwareVariant', 'FirmwareBuild', 'InstallPlan', 'InstallRecord', 'BoardInstance', 'GrpcExposure', 'ProtoContractVersion')
    work = os.path.join(tmp, 'srv')
    rec = I.build_variant(m, 'uno-echo', work, run=fake_runner(size_text(3220, 24, 739)))
    check('installer build: a variant generated against THIS server + built → a FirmwareBuild row; the .hex is in the build store',
          rec['state'] == 'built' and I._by_name(m, 'FirmwareBuild', rec['name']) is not None and os.path.isfile(rec['hex_path'])
          and '/builds/' in rec['hex_path'])
    blink = I.build_variant(m, 'uno-blink-only', work, run=fake_runner(size_text(1502, 18, 483)))
    doc = I.document(m, work, scan={'host': I.this_host(), 'usb': [], 'serial': []})
    names = {b['name']: b for b in doc['builds']}
    check('installer document: targets (the twin always), variants, builds with sizes vs the cited limits, sha, compat, installable',
          doc['targets'][0]['name'] == I.TWIN and len(doc['variants']) == 4 and rec['name'] in names and blink['name'] in names
          and names[rec['name']]['flash_bytes'] == 3244 and names[rec['name']]['flash_max'] == 32256 and names[rec['name']]['compat'] == 'compatible'
          and names[rec['name']]['installable'] is True and doc['host'] == I.this_host())
    p = I.plan(m, I.TWIN, rec['name'], work)
    argv = json.loads(p['argv_json'])
    check('installer plan (twin): an InstallPlan row — the exact argv (polari-avr-twin --hex <the stored .hex>), engine avr-twin, compat compatible, '
          'what will be stamped; nothing opened', not p['refused'] and argv[0] == 'polari-avr-twin' and argv[argv.index('--hex') + 1] == rec['hex_path']
          and p['engine'] == 'avr-twin' and p['compat'] == 'compatible' and 'no BoardInstance is stamped' in p['will_stamp']
          and I._by_name(m, 'InstallPlan', p['name']).state == 'planned' and twin.read_state(work) is None)
    for args, why, status in (((m, 'no-such-plan', True, work), 'no plan', '404'), ((m, p['name'], False, work), 'not confirmed', '400'),
                              ((m, p['name'], 'yes', work), 'not confirmed', '400')):
        try:
            I.run(*args)
            check('run refuses (%s)' % why, False)
        except I.InstallRefused as e:
            check('installer run REFUSES: %s (%s, exit 3)' % (why, status), why in str(e) and e.status.startswith(status) and e.code == 3)
    other = I._by_name(m, 'InstallPlan', p['name'])
    other.host = 'some-other-host'
    try:
        I.run(m, p['name'], True, work)
        check('run on another host refuses', False)
    except I.InstallRefused as e:
        check('installer run REFUSES a plan for another host, naming both hosts (the install runs on the machine holding the port)',
              'some-other-host' in str(e) and I.this_host() in str(e) and e.status.startswith('403'))
    other.host = I.this_host()
    # stale: the server's exposure moves to v1 AFTER the plan → run re-checks and refuses
    _expose(m, 'SimRigState', 1, V1_SIMRIG, '2bcc9d1a2774ef33')
    sp = I.plan(m, I.TWIN, blink['name'], work)
    check('installer plan: a stale-header build plans as REFUSED, the reason in plain words', sp['refused'] and sp['compat'] == 'stale-header' and 'misread' in sp['why'])
    try:
        I.run(m, p['name'], True, work)
        check('run of a now-stale build refuses', False)
    except I.InstallRefused as e:
        check('installer run RE-CHECKS compat at run time: the server moved to v1 → REFUSED (stale-header), plan marked refused',
              'stale-header' in str(e) and I._by_name(m, 'InstallPlan', p['name']).state == 'refused')
    m.objectTables['GrpcExposure'].clear()
    m.objectTables['ProtoContractVersion'].clear()
    p = I.plan(m, I.TWIN, rec['name'], work)
    os.environ['PATH'] = fake_bin + os.pathsep + old_path
    try:
        r = I.run(m, p['name'], True, work)
        st = twin.status('uno', work)
        check('installer run (twin, fake simavr): InstallRecord installed — loaded flash bytes == the .hex\'s data bytes, firmware sha, elapsed, the twin runs it',
              r['verdict'] == 'installed' and r['verified_bytes'] == twin.hex_data_bytes(rec['hex_path']) > 0 and r['firmware_sha'] == rec['artifact_sha256']
              and st['state'] == 'up' and st['build'] == rec['name'] and I._by_name(m, 'InstallRecord', r['name']).verdict == 'installed'
              and I._by_name(m, 'FirmwareBuild', rec['name']).state == 'flashed', r.get('verify'))
        check('installer record names the row the board will update (class + rig name) and says it was the twin',
              r['row_class'] == 'SimRigState' and r['row_name'] == 'uno-echo' and 'THE TWIN' in r['notes'])
        try:
            attach.attach(m, r['name'], work, grpc_target='127.0.0.1:1', background=False)
            check('attach without the exposure refuses', False)
        except attach.AttachRefused as e:
            check('attach REFUSES while the class\'s gRPC exposure is off — names the knob, never flips it', 'POST /api/grpc/exposures/SimRigState' in str(e)
                  and not m.objectTables['GrpcExposure'])
        twin.down('uno', work)
        # ---- a board target (a faked scan of THIS host + the fake avrdude)
        byid = '/dev/serial/by-id/usb-Arduino__www.arduino.cc__0043_X-if00'
        scan = {'host': I.this_host(), 'observed_at': 'now',
                'usb': [{'bus': '001', 'dev': '009', 'vendor_id': '2341', 'product_id': '0043', 'description': 'Uno R3', 'path': '001-1', 'usb_class': 'Communications'}],
                'serial': [{'by_id_path': byid, 'device': '/dev/ttyACM0', 'vendor_id': '2341', 'product_id': '0043', 'serial': 'X', 'bus': '001', 'dev': '009'}]}
        inst = '%s:arduino-uno-r3@001-1' % I.this_host()
        doc = I.document(m, work, scan=scan)
        check('installer document: a detected UNO on this host is a target beside the twin', [t['name'] for t in doc['targets']] == [I.TWIN, inst])
        bp = I.plan(m, inst, rec['name'], work, scan=scan)
        check('installer plan (board): the exact plan §3 avrdude argv at the by-id path; programmer avrdude-optiboot; stamp named',
              bp['argv_text'] == 'avrdude -p atmega328p -c arduino -P %s -b 115200 -D -U flash:w:%s:i' % (byid, rec['hex_path'])
              and bp['programmer'] == 'avrdude-optiboot' and 'firmware_sha' in bp['will_stamp'] and not bp['refused'], bp['argv_text'])
        os.environ['FAKE_AVRDUDE_LOG'] = os.path.join(tmp, 'avrdude.args')
        br = I.run(m, bp['name'], True, work, scan=scan)
        bi = I._by_name(m, 'BoardInstance', inst)
        check('installer run (board, fake avrdude): installed, avrdude\'s read-back verified, the BoardInstance stamped with the firmware sha',
              br['verdict'] == 'installed' and br['verified_bytes'] > 0 and 'read it back' in br['verify'] and bi is not None
              and bi.firmware_sha == rec['artifact_sha256'] and '-V' not in open(os.environ['FAKE_AVRDUDE_LOG']).read().split(), br.get('verify'))
        moved = dict(scan, serial=[dict(scan['serial'][0], by_id_path='/dev/serial/by-id/other')])
        bp2 = I.plan(m, inst, rec['name'], work, scan=scan)
        try:
            I.run(m, bp2['name'], True, work, scan=moved)
            check('a moved board refuses', False)
        except I.InstallRefused as e:
            check('installer run REFUSES when the board moved since the plan (plan again)', 'moved' in str(e))
    finally:
        os.environ['PATH'] = old_path
        os.environ.pop('FAKE_AVRDUDE_LOG', None)
        try:
            twin.down('uno', work)
        except Exception:  # noqa: BLE001
            pass
    check('installer rows construct: InstallPlan / InstallRecord carry argv_text / verify (the page\'s columns)',
          hasattr(BB.InstallPlan(name='x'), 'argv_text') and hasattr(BB.InstallRecord(name='x'), 'verify'))


def page(check):
    from board.board_page import INSTALLER_PAGES as P
    from board.board_page import SEED_BOARD_PAGE_DISPLAYS as ALL
    d = json.loads(P[0]['definition'])
    names = [it['componentProps']['componentName'] for row in d['rows'] for it in row['items']]
    check('/display/firmware-installer: configured tables + exactly ONE new component (firmware-installer-panel); no api-json-panel',
          P[0]['pageRoute'] == 'firmware-installer' and names.count('firmware-installer-panel') == 1
          and set(names) == {'firmware-installer-panel', 'class-rows-table'} and 'api-json-panel' not in P[0]['definition'], names)
    check('the installer page is exported with /display/boards (one manifest page list)', [p['pageRoute'] for p in ALL] == ['boards', 'firmware-installer'])
    tables = {it['componentProps']['inputs'].get('className') for row in d['rows'] for it in row['items'] if it['componentProps']['componentName'] == 'class-rows-table'}
    check('the installer page tables cover variants, builds, devices, programmer kinds, plans, records',
          tables == {'FirmwareVariant', 'FirmwareBuild', 'BoardInstance', 'ProgrammerKind', 'InstallPlan', 'InstallRecord'}, tables)


def run_installer(check):
    from board.board_uno_selftest import _fake_runner, size_text, _exe, FAKE_AVRDUDE, FAKE_TWIN
    from board.custom import board_engines as be, gen
    print('  -- firmware_installer (brd-fi)')
    tmp = tempfile.mkdtemp(prefix='board-installer-selftest-')
    old_path, old_knob = os.environ.get('PATH', ''), os.environ.pop(be.KNOB, None)
    try:
        variants(check)
        gen_and_compat(check, tmp)
        fake = os.path.join(tmp, 'bin')
        os.makedirs(fake)
        _exe(os.path.join(fake, 'avrdude'), FAKE_AVRDUDE)
        _exe(os.path.join(fake, 'polari-avr-twin'), FAKE_TWIN)
        fw = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        os.environ.update(FAKE_TWIN_FW=fw, FAKE_TWIN_FMAP=json.dumps(gen.pinned_contract('SimRigState')[0]['field_map']))
        from board.custom import installer as I
        saved = (I.TWIN_TCP, I.TWIN_LINK)
        I.TWIN_TCP, I.TWIN_LINK = 19841, os.path.join(tmp, 'uart')
        try:
            flow(check, tmp, _fake_runner, size_text, fake, old_path)
        finally:
            I.TWIN_TCP, I.TWIN_LINK = saved
        page(check)
    finally:
        os.environ['PATH'] = old_path
        for k in ('FAKE_TWIN_FW', 'FAKE_TWIN_FMAP'):
            os.environ.pop(k, None)
        if old_knob is not None:
            os.environ[be.KNOB] = old_knob
        shutil.rmtree(tmp, ignore_errors=True)
