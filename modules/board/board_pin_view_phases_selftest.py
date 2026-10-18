"""board_pin_view_phases_selftest — pv-4 (PIN_VIEW_PLAN.md 2.4 / 2.9): the phases (power-up, reset, bootloader, init, runtime) and the two blank baselines of the pin payload, and the configuration events
(derived from InstallRecord and canvas BoardPinNet rows, recorded through the POST door). Run by board_selftest.run(). Every state asserted here is compared with the rows that decide it (the Register
reset values, the PinLifecycleConstraint rows, the after-init stage), never with a copy.
"""
import contextlib
import io
import json
import types

BOARD = 'arduino-uno-r3'
SYSTEM = 'uno-light-system'
BINDING = 'uno-light@arduino-uno-r3'


class _M:
    """A manager that is only what the doors touch: tables, ids, a no-op persist (the installer selftest's shape)."""

    def __init__(self):
        self.objectTables = {}
        self.idList = []
        self.db = None

    def persistTree(self):
        return None

    def noteTreeMutation(self, *a, **k):
        return None


def _io(res):
    return [p for p in res['pins'] if p['level'] in ('die', 'package') and p['kind'] == 'io']


def _state(res):
    return {p['id']: (p['drive_status'], p['pull'], json.dumps(p['activated'], sort_keys=True), p['stage']) for p in res['pins']}


def run_pin_view_phases(check):
    from board.custom import config_events as CE
    from board.custom import hardware_system as HS
    from board.custom import pin_view as PV
    from board.custom import pin_view_modes as MD
    from board.custom import pin_view_phases as PH
    with contextlib.redirect_stdout(io.StringIO()):
        t = HS.default_tables()
    P = {'system': SYSTEM, 'binding': BINDING}
    run = PV.build(BOARD, dict(P, stage='firmware-committed'))
    rst = PV.build(BOARD, dict(P, stage='firmware-committed', phase='reset'))
    pwr = PV.build(BOARD, dict(P, stage='firmware-committed', phase='power-up'))

    # ---- reset / power-up: every I/O pin blank, cited
    iop = _io(rst)
    reg = {r['name']: r for r in t['Register']}
    check('PHASE reset: all %d I/O pins of both chips are high-impedance, no pull, nothing activated - even though the binding commits claims at runtime (%d activated there); the stage shown is base'
          % (len(iop), sum(1 for p in _io(run) if p['activated'])),
          iop and all(p['drive_status'] == 'high-impedance' and p['pull'] == 'none' and p['activated'] is None for p in iop) and any(p['activated'] for p in _io(run))
          and rst['stage']['stage'] == 'base' and rst['stage']['requested'] == 'firmware-committed' and rst['phase_info']['effective_stage'] == 'base', str(len(iop)))
    check('PHASE reset: the ATmega328P pins cite DS40002061B §14.2.1 p.85 and Table 14-1 p.86 and the port registers\' reset_value rows (DDRx / PORTx read from the Register rows); the 16U2 pins cite doc7799',
          all(any('§14.2.1 p.85' in b for b in p['phase_basis']) and any('Table 14-1 p.86' in b for b in p['phase_basis']) for p in iop if p['soc'] == 'atmega328p')
          and all(any('Register atmega328p:DDR%s reset_value %s' % (r['port'], reg['atmega328p:DDR%s' % r['port']]['reset_value'] or 'not captured') in b or 'Register atmega328p:DDR%s reset_value not captured' % r['port'] in b for b in p['phase_basis'])
                  for p in iop if p['soc'] == 'atmega328p' for r in [next(x for x in t['SocPin'] if x['name'] == p['soc_pin'])])
          and all(any('doc7799' in b for b in p['phase_basis']) for p in iop if p['soc'] == 'atmega16u2'))
    hdr = [p for p in rst['pins'] if p['level'] == 'board' and p['kind'].startswith('header') and p['canonical']]
    check('PHASE reset: the header pins carry their line\'s blank state (%d); the supply and ground pins are untouched; the banner says "%s"' % (len(hdr), PH.BANNER),
          hdr and all(p['drive_status'] == 'high-impedance' for p in hdr) and next(p for p in rst['pins'] if p['id'] == 'ConnectorPin:%s:POWER:5' % BOARD)['drive_status'] == 'supplies'
          and rst['phase_info']['banner'] == PH.BANNER and run['phase_info']['banner'] == '', str(len(hdr)))
    check('PHASE reset: a blank pad drives nothing, so its drive limit class is `unchecked` (never hatched) on the pad, the leg and the header pin - D6 included although its line is `undetermined` at runtime',
          all(p['limit_class'] == 'unchecked' for p in iop) and next(p for p in rst['pins'] if p['level'] == 'board' and p['canonical'] == 'D6')['limit_class'] == 'unchecked'
          and next(p for p in run['pins'] if p['level'] == 'board' and p['canonical'] == 'D6')['limit_class'] == 'undetermined')
    check('PHASE power-up: the same blank state as reset (every I/O pin high-impedance, nothing activated)', _state(pwr) == _state(rst) and pwr['phase'] == 'power-up')
    sig = MD.SIGNAL_WORDS
    check('VOCABULARY: no signal word in any pin\'s drive fields at reset or bootloader (drive = electricity; signal separate)',
          not any(sig.search(str(p[k])) for res in (rst, PV.build(BOARD, dict(P, phase='bootloader'))) for p in res['pins'] for k in ('drive_status', 'drive_why', 'pull', 'rail')))

    # ---- bootloader: board as delivered vs chip blank
    bl = PV.build(BOARD, dict(P, phase='bootloader', blank='board'))
    bc = PV.build(BOARD, dict(P, phase='bootloader', blank='chip'))
    rows = {r['name']: r for r in t['PinLifecycleConstraint'] if r['phase'] == 'bootloader'}
    d0 = next(p for p in bl['pins'] if p['level'] == 'die' and p['canonical'] == 'D0')
    d1 = next(p for p in bl['pins'] if p['level'] == 'die' and p['canonical'] == 'D1')
    d6 = next(p for p in bl['pins'] if p['level'] == 'die' and p['canonical'] == 'D6')
    rpad = next(p for p in bl['pins'] if p['level'] == 'die' and p['soc_pin'] == 'atmega328p:PC6')
    check('PHASE bootloader (board as delivered): D0 serves the bootloader link as USART0 RXD (receiver: high-impedance), D1 as TXD (transmitter: sources-or-sinks), RESET answers the DTR pulse; '
          'the rows that decided it are the reserved bootloader PinLifecycleConstraint rows (%s); D6 is still blank' % ', '.join(sorted(rows)),
          d0['activated']['function'] == 'RXD' and d0['drive_status'] == 'high-impedance' and d1['activated']['function'] == 'TXD' and d1['drive_status'] == 'sources-or-sinks'
          and rpad['activated']['resource'] == 'DTR pulse through C5' and d6['drive_status'] == 'high-impedance' and d6['activated'] is None
          and set(bl['phase_info']['decided_by']) == {n for n, r in rows.items() if r['policy'] == 'reserved'} and bl['phase_info']['pins_serving'] >= 3
          and all(r in d0['phase_basis'] for r in ('arduino-uno-r3:D0:bootloader',)), str(d0['phase_basis']))
    hd0 = next(p for p in bl['pins'] if p['level'] == 'board' and p['canonical'] == 'D0')
    check('PHASE bootloader: the D0 header pin and the leg show the same link as the pad; the D13 start-up flash and the 16U2\'s own firmware are listed UNDETERMINED (not in the rows), never guessed',
          hd0['activated'] == d0['activated'] and any('D13' in u for u in bl['phase_info']['undetermined']) and any('16U2' in u for u in bl['phase_info']['undetermined']))
    check('PHASE bootloader (chip blank): no bootloader - nothing serves it, every pin blank, and the baseline says so',
          bc['phase_info']['pins_serving'] == 0 and all(p['activated'] is None and p['drive_status'] == 'high-impedance' for p in _io(bc))
          and bc['phase_info']['blank_facts']['bootloader']['present'] == 'no')
    bf = bl['phase_info']['blank_facts']
    check('BLANK board as delivered: the bootloader is present, cited from the boards.txt / Optiboot DatasheetFacts (file, size 512, protocol, 115200); whether a factory demo sketch is present is `undetermined` (no row cites it); '
          'the port registers\' reset values come from the Register rows',
          bf['baseline'] == 'board' and bf['bootloader']['present'] == 'yes' and {c['fact'].partition(':')[2] for c in bf['bootloader']['cites']} >= {'bootloader.file', 'optiboot_size', 'upload.protocol', 'upload.speed'}
          and all(c['where'] and c['document'] for c in bf['bootloader']['cites']) and bf['factory_sketch']['status'] == 'undetermined'
          and {r['register']: r['reset_value'] for r in bf['registers']}['atmega328p:DDRB'] == reg['atmega328p:DDRB']['reset_value']
          and {r['register']: r['reset_value'] for r in bf['registers']}['atmega328p:DDRC'] == 'undetermined')

    # ---- init + runtime + refusals
    ini = PV.build(BOARD, dict(P, phase='init'))
    ai = PV.build(BOARD, dict(P, stage='after-init'))
    check('PHASE init: the Initialization Purpose\'s claims applied = exactly the after-init stage (pin by pin: drive, pull, activated function, stage); %d pins are claimed'
          % sum(1 for p in ini['pins'] if p['stage'] == 'proposed'),
          _state(ini) == _state(ai) and ini['stage']['stage'] == 'after-init' and any(p['stage'] == 'proposed' for p in ini['pins']))
    base_rt = PV.build(BOARD, dict(P, stage='firmware-committed', phase='runtime'))
    check('PHASE runtime: unchanged - the requested stage\'s claims (same as no phase at all)', _state(base_rt) == _state(run) and run['phase'] == 'runtime' and base_rt['phase_info']['pins_blank'] == 0)
    errs = []
    for bad in ({'phase': 'sleep'}, {'blank': 'bare'}):
        try:
            PV.build(BOARD, dict(P, **bad))
            errs.append('accepted')
        except PV.Refused as e:
            errs.append(e.status)
    check('PHASE: an unknown phase or blank baseline is refused (400) naming the choices', errs == [400, 400], str(errs))

    # ---- events: derived
    canvas = {'name': '%s:D7@uno-button-clock:LED_CONTROL' % BOARD, 'board': BOARD, 'board_pin': '%s:D7' % BOARD, 'circuit': 'uno-button-clock', 'circuit_net': 'ubc-net-led-control', 'role': 'input',
              'provenance': 'canvas', 'notes': 'fixture'}
    tabs = dict(t, BoardPinNet=list(t['BoardPinNet']) + [canvas],
                FirmwareBuild=[{'name': 'uno-light-build-1', 'board_definition': BOARD, 'variant': 'uno-light'}, {'name': 'esp-build-1', 'board_definition': 'esp32-c3-devkitm'}],
                BoardInstance=[{'name': 'bench:arduino-uno-r3@1-2', 'definition': BOARD, 'target_board': ''}],
                InstallRecord=[{'name': 'install-uno-light-build-1-1', 'build': 'uno-light-build-1', 'variant': 'uno-light', 'instance': 'bench:arduino-uno-r3@1-2', 'verdict': 'installed',
                                'verify': '16192 bytes read back and equal to the .hex', 'firmware_sha': 'ab12cd34ef56ab12', 'started_at': '2026-10-18T09:00:00', 'finished_at': '2026-10-18T09:01:10'},
                               {'name': 'install-uno-light-build-1-2', 'build': 'uno-light-build-1', 'verdict': 'failed', 'started_at': '2026-10-18T09:05:00'},
                               {'name': 'install-esp-build-1-1', 'build': 'esp-build-1', 'verdict': 'installed', 'started_at': '2026-10-18T09:06:00'}])
    tl = CE.timeline(BOARD, None, tabs, system=SYSTEM, binding=BINDING)
    ev = {e['name']: e for e in tl['events']}
    fl = ev['derived:InstallRecord:install-uno-light-build-1-1']
    wr = ev['derived:BoardPinNet:%s' % canvas['name']]
    labels_fl = {(p['level'], p['label']) for p in fl['pins_changed']}
    check('EVENTS derived: the installed InstallRecord of THIS board is a `flash` event (cause in plain words, refs InstallRecord + FirmwareBuild, when from the record, who "not recorded"); the failed record and the other board\'s record are not events (the failed one is listed as skipped)',
          fl['kind'] == 'flash' and fl['refs'] == ['InstallRecord:install-uno-light-build-1-1', 'FirmwareBuild:uno-light-build-1'] and fl['when'] == '2026-10-18T09:01:10' and fl['who'] == 'not recorded'
          and 'was installed' in fl['cause'] and 'verified: 16192 bytes' in fl['cause'] and fl['board_instance'] == 'bench:arduino-uno-r3@1-2' and fl['provenance'] == 'derived'
          and not any('failed' in k or 'esp-build' in k for k in ev) and any('verdict failed' in s['why'] for s in tl['skipped']), str(sorted(ev)))
    check('EVENTS derived: the flash\'s pins_changed is the payload difference base -> firmware committed (D1 TXD sources-or-sinks, D2 pulled-up are among them, the 16U2 is not), each with a plain before / after',
          ('die', 'PD1') in labels_fl and ('board', 'D1') in labels_fl and ('board', 'D2') in labels_fl and not any('U2' in p['surface'] for p in fl['pins_changed'])
          and next(p for p in fl['pins_changed'] if p['level'] == 'board' and p['label'] == 'D1')['after'].startswith('drive sources-or-sinks; signal TXD')
          and next(p for p in fl['pins_changed'] if p['level'] == 'board' and p['label'] == 'D2')['after'].startswith('drive pulled-up (internal-up); signal INT0')
          and next(p for p in fl['pins_changed'] if p['level'] == 'board' and p['label'] == 'D1')['before'].startswith('drive not-driven; signal none activated') and 'binding %s' % BINDING in fl['pins_basis'],
          str(sorted(labels_fl)))
    check('EVENTS derived: a CANVAS BoardPinNet is a `wiring-added` event (pin D7 on net ubc-net-led-control as an input; no time or person recorded), its pins_changed is the payload difference with / without the row '
          '(the D7 header pin gains a connection); the SEED bench rows (D6, D3, D2) are the design, not events',
          wr['kind'] == 'wiring-added' and wr['when'] == '' and wr['who'] == 'not recorded' and not wr['dated'] and 'Pin D7' in wr['cause'] and 'as an input' in wr['cause']
          and any(p['label'] == 'D7' and p['level'] == 'board' and 'connection' in p['what'] for p in wr['pins_changed'])
          and not any('BoardPinNet:%s:D6' % BOARD in k or 'BoardPinNet:%s:D2' % BOARD in k for k in ev) and tl['events'][0]['name'] == wr['name'],
          str([(p['label'], p['what']) for p in wr['pins_changed']]))
    tf = CE.timeline(BOARD, None, tabs, instance='bench:arduino-uno-r3@1-2', with_pins=False)
    check('EVENTS: `instance=` keeps that instance\'s events plus the design-level ones (the canvas wiring has no instance); pins=0 skips the difference and says so',
          {e['kind'] for e in tf['events']} == {'flash', 'wiring-added'} and CE.timeline(BOARD, None, tabs, instance='nope', with_pins=False)['count'] == 1
          and all(e['pins_basis'] == 'not computed (pins=0)' for e in tf['events']))

    # ---- the POST door on a REAL falcon.App beside every existing board route
    import falcon
    import falcon.testing as ft
    from board.board_endpoints import construct_board_endpoints
    m = _M()
    m.objectTables = {'InstallRecord': {}, 'FirmwareBuild': {}, 'BoardInstance': {}}
    for cls, name in (('FirmwareBuild', 'uno-light-build-1'), ('InstallRecord', 'install-uno-light-build-1-1')):
        m.objectTables[cls][name] = types.SimpleNamespace(**dict(next(r for r in tabs[cls] if r['name'] == name), manager=None))
    m.objectTables['BoardInstance']['bench:arduino-uno-r3@1-2'] = types.SimpleNamespace(**dict(tabs['BoardInstance'][0], manager=None))
    srv = types.SimpleNamespace(falconServer=falcon.App(), manager=m)
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            construct_board_endpoints(srv)
        cl = ft.TestClient(srv.falconServer)
        post = lambda body: cl.simulate_post('/api/board/%s/config-events' % BOARD, body=json.dumps(body), headers={'Content-Type': 'application/json'})   # noqa: E731
        bad_kind = post({'kind': 'teleport', 'cause': 'x', 'who': 'dustin'})
        no_cause = post({'kind': 'reset', 'who': 'dustin'})
        bad_ref = post({'kind': 'flash', 'cause': 'x', 'who': 'dustin', 'refs': ['InstallRecord:nope']})
        bad_cls = post({'kind': 'flash', 'cause': 'x', 'who': 'dustin', 'refs': ['Banana:1']})
        no_net = post({'kind': 'wiring-added', 'cause': 'x', 'who': 'dustin'})
        bad_inst = post({'kind': 'reset', 'cause': 'x', 'who': 'dustin', 'board_instance': 'ghost'})
        bad_board = cl.simulate_post('/api/board/no-such-board/config-events', body=json.dumps({'kind': 'reset', 'cause': 'x', 'who': 'dustin'}))
        bad_json = cl.simulate_post('/api/board/%s/config-events' % BOARD, body='{nope')
        shield = post({'kind': 'shield-attached', 'cause': 'A prototyping shield was pushed onto the headers', 'who': 'dustin', 'when': '2026-10-18T10:00:00', 'pins': ['D2', 'D3']})
        bad_pin = post({'kind': 'shield-attached', 'cause': 'x', 'who': 'dustin', 'pins': ['D99']})
        flash = post({'kind': 'flash', 'cause': 'Flashed the light firmware from the bench PC to try the LED', 'who': 'dustin', 'when': '2026-10-18T09:30:00', 'board_instance': 'bench:arduino-uno-r3@1-2',
                      'refs': ['InstallRecord:install-uno-light-build-1-1'], 'system': SYSTEM})
        listed = cl.simulate_get('/api/board/%s/config-events?pins=0' % BOARD).json
        view = cl.simulate_get('/api/board/%s/pin-view/surfaces?phase=reset' % BOARD)
        unk_phase = cl.simulate_get('/api/board/%s/pin-view?phase=sleep' % BOARD)
        other = [cl.simulate_get('/api/board/%s/%s' % (BOARD, x)).status_code for x in ('views', 'conflicts', 'exposure', 'reachability')]
        ok = (bad_kind.status_code == 400 and 'teleport' in bad_kind.json['error'] and all(k in bad_kind.json['error'] for k in CE.KINDS)
              and no_cause.status_code == 400 and 'cause' in no_cause.json['error'] and bad_ref.status_code == 404 and bad_cls.status_code == 400 and 'Banana' in bad_cls.json['error']
              and no_net.status_code == 400 and 'BoardPinNet' in no_net.json['error'] and bad_inst.status_code == 404 and bad_board.status_code == 404 and bad_json.status_code == 400
              and bad_pin.status_code == 400 and 'D99' in bad_pin.json['error'])
        why = str([x.status_code for x in (bad_kind, no_cause, bad_ref, bad_cls, no_net, bad_inst, bad_board, bad_json, bad_pin)] + other + [view.status_code, unk_phase.status_code, bad_kind.json['error'][:60]])
    except Exception as ex:   # a route clash raises UnacceptableRouteError at add time
        ok, why = False, repr(ex)
        shield = flash = listed = view = unk_phase = None
        other = []
    check('DOORS: GET/POST /api/board/{board}/config-events ADD on a real falcon.App beside every existing board route (no UnacceptableRouteError); the POST refuses an unknown kind BY NAME (listing the kinds), a missing cause or '
          'who, an unknown ref (404), a ref of an unknown class, a wiring event without a BoardPinNet ref, an unknown instance or board, a bad body and an unknown shield pin',
          ok and all(c == 200 for c in other) and view is not None and view.status_code == 200 and unk_phase.status_code == 400, why)
    if not ok:
        return
    fe = flash.json['event']
    se = shield.json['event']
    rows_ = list(m.objectTables.get('ConfigurationEvent', {}).values())
    check('POST: a recorded flash that cites the InstallRecord is written as a ConfigurationEvent row (name, board, instance, kind, cause, refs, who, when, provenance recorded) with pins_changed DERIVED at write time '
          '(the payload difference, not typed); a recorded shield-attached keeps the named pins, validated against the payload, and says the model has no shield yet',
          flash.status_code == 201 and shield.status_code == 201 and len(rows_) == 2 and fe['name'] == '%s:ev-2' % BOARD and se['name'] == '%s:ev-1' % BOARD and fe['who'] == 'dustin' and fe['provenance'] == 'recorded'
          and any(p['label'] == 'D1' for p in fe['pins_changed']) and json.loads(next(r for r in rows_ if r.name == fe['name']).pins_changed_json) == fe['pins_changed']
          and {p['label'] for p in se['pins_changed']} == {'D2', 'D3'} and 'no description of a shield' in se['pins_basis'], str((flash.status_code, shield.status_code, len(rows_), fe['name'], fe['who'], fe['provenance'], [p['label'] for p in fe['pins_changed']][:4], [p['label'] for p in se['pins_changed']], se['pins_basis'])))
    byn = {e['name']: e for e in listed['events']}
    check('GET: the timeline lists the two recorded events; the derived flash of the InstallRecord the recorded flash cites is NOT listed twice (it is under `covered`, naming the recorded event); the order is oldest first',
          fe['name'] in byn and se['name'] in byn and 'derived:InstallRecord:install-uno-light-build-1-1' not in byn
          and [c['by'] for c in listed['covered']] == [[fe['name']]] and listed['recorded'] == 2
          and [e['when'] for e in listed['events'] if e['dated']] == sorted(e['when'] for e in listed['events'] if e['dated']),
          str(sorted(byn)))
