"""board_hardware_system_selftest — hsp-1 (HARDWARE_SYSTEM_PINS_PLAN.md §3 hsp-1): the Hardware System, its seven links, its three derived signal paths, the doors on a REAL falcon.App
and the CLI. Run by board_selftest.run(). Every verdict asserted here is compared with the output of the code that OWNS the check (ladder, electrical rules, contract), never with a copy.
"""
import contextlib
import copy
import io
import json
import re
import types

BOARD = 'arduino-uno-r3'
SYSTEM = 'uno-light-system'
VERDICTS = ('ok', 'blocked', 'conditional', 'unchecked', 'not-yet', 'undetermined')


def _path(res, slug):
    return next(p for p in res['SignalPath'] if p['name'] == '%s:%s' % (SYSTEM, slug))


def _hops(p):
    return json.loads(p['hops_json'])


def run_hardware_system(check):
    from board import board_basis as B
    from board.board_seed import BOARD_SEED_PAIRS
    from board.custom import hardware_system as HS
    from board.custom import hwsys_links as HL
    from board.custom import hwsys_refs as R
    from board.custom import hwsys_system as SYS
    from board.custom import ladder as LD
    from board.custom import board_pin_nets as BPN
    from board.custom import compat
    from board.custom import electrical_check as EC
    from board.custom.hwsys_context import Ctx, SEV
    with contextlib.redirect_stdout(io.StringIO()):
        t = HS.default_tables()
    res = HS.build(t, strict=True)
    s = res['HardwareSystem'][0]
    links = {l['name'].partition(':')[2]: l for l in res['SystemLink']}
    xc = {c['name'] for c in t['EnclosureContact']}

    # ---- the classes and the seeds
    new = (B.HardwareSystem, B.SystemLink, B.SignalPath)
    check('hsp-1: HardwareSystem / SystemLink / SignalPath are BOARD_CLASSES members, each with plain_words', all(c in B.BOARD_CLASSES and getattr(c, 'plain_words', '') for c in new))
    seeded = {c: rows for c, _cls, rows in BOARD_SEED_PAIRS}
    quiet = contextlib.redirect_stdout(io.StringIO())
    quiet.__enter__()
    try:
        built = {n: [cls(**{k: v for k, v in r.items() if k != '_converge'}) for r in seeded[n]] for n, cls in zip(('HardwareSystem', 'SystemLink', 'SignalPath'), new)}
        built_links = [B.SystemLink(**l) for l in res['SystemLink']]
        built_paths = [B.SignalPath(**p) for p in res['SignalPath']]
    finally:
        quiet.__exit__(None, None, None)
    check('hsp-1: seeded code-owned (every row converges), 1 system + 7 links + 3 paths, every row constructs its class',
          all(seeded.get(n) and all('_converge' in r for r in seeded[n]) for n in ('HardwareSystem', 'SystemLink', 'SignalPath'))
          and (len(seeded['HardwareSystem']), len(seeded['SystemLink']), len(seeded['SignalPath'])) == (1, 7, 3)
          and all(built[n] for n in built))
    again = HS.build(t, strict=True)
    check('hsp-1: the seed rows are DERIVED and reproducible — two builds from the same rows are byte-identical', json.dumps(res, sort_keys=True) == json.dumps(again, sort_keys=True))

    # ---- L6 the system
    parts = json.loads(s['participants_json'])
    check('L6: uno-light-system at stage S1-breadboard, solution uno-light; participants have every kind (hardware, software, person) in the cmod Purpose participant shape {role, kind, ref[, variant]}',
          s['name'] == SYSTEM and s['stage'] == 'S1-breadboard' and s['solution'] == 'uno-light' and {p['kind'] for p in parts} == set(SYS.KINDS)
          and all(set(p) <= {'role', 'kind', 'ref', 'variant'} and {'role', 'kind', 'ref'} <= set(p) and ':' in p['ref'] for p in parts), str(sorted({p['kind'] for p in parts})))
    unres = [p['ref'] for p in parts if not R.resolves(p['ref'], t)[0]]
    check('L6: every participant ref resolves to a row — except the person (no Person class yet, said) ; the UNO, U1, U2, SW1, LED1, R1, the jumper, the bridge, the runtimes are all there',
          unres == ['Person:bench-operator'] and {'BoardDefinition:' + BOARD, 'BoardComponent:%s:U1' % BOARD, 'BoardComponent:%s:U2' % BOARD, 'CircuitComponentDefinition:ubc-sw1', 'CircuitComponentDefinition:ubc-led1',
                                                   'CircuitComponentDefinition:ubc-r1', 'Runtime:java-bridge', 'Runtime:python-backend'} <= {p['ref'] for p in parts}, str(unres))
    check('L6: the board, U1 and U2 are variant=pending (his ruling 2026-10-15) and the system row says so in `undetermined`',
          {p['ref'] for p in parts if p.get('variant') == 'pending'} >= {'BoardDefinition:' + BOARD, 'BoardComponent:%s:U1' % BOARD, 'BoardComponent:%s:U2' % BOARD} and 'PENDING' in s['undetermined'] and 'Person' in s['undetermined'])
    check('L6: links_refs_json is DERIVED from the links built (7 SystemLink refs) and every component ref in components_json resolves',
          len(json.loads(s['links_refs_json'])) == 7 and all(R.resolves(r, t)[0] for r in json.loads(s['components_json'])))

    # ---- L6 the seven links
    want = ('u1-usart0-u2-usart1', 'u2-usb-host', 'u2-dtr-u1-reset', 'd6-d3-jumper', 'button-d2', 'd6-r1-led1-gnd', 'bridge-backend-grpc')
    media = {'medium': {'trace', 'series-resistor', 'capacitor', 'jumper-wire', 'usb', 'serial-port', 'grpc', 'http'}, 'signal_kind': {'digital', 'analog', 'uart', 'usb', 'rpc', 'reset'}}
    check('L6: the seven links exist (a-g), every medium / signal_kind in its value set, each constructs SystemLink, endpoints are {participant, refs, what} with participants of the system',
          list(links) == list(want) and all(l['medium'] in media['medium'] and l['signal_kind'] in media['signal_kind'] and l['verification'] in ('verified', 'partial', 'unverified', 'conflicted') for l in links.values())
          and len(built_links) == 7
          and all({'participant', 'refs', 'what'} <= set(json.loads(l[e])) and json.loads(l[e])['participant'] in {p['role'] for p in parts} for l in links.values() for e in ('endpoint_a_json', 'endpoint_b_json')))
    ends = [r for l in links.values() for e in ('endpoint_a_json', 'endpoint_b_json') for r in json.loads(l[e])['refs']]
    check('L6: every endpoint ref resolves to a row (pins, package contacts, SoC pads, nets, bench wires, the bridge, the runtimes)', all(R.resolves(r, t, None, {'SystemLink': set()})[0] for r in ends),
          str([r for r in ends if not R.resolves(r, t)[0]]))
    via_ok = all(r.partition(':')[0] == 'EnclosureContact' and r.partition(':')[2] in xc for l in links.values() for r in json.loads(l['via_refs_json']))
    check('L6: each link\'s via refs are EnclosureContact rows (derived from the hsp-0 exposure maps, never retyped); a, b, c, d, e, f cross an enclosure and have at least one; g (software) none',
          via_ok and all(json.loads(links[k]['via_refs_json']) for k in want[:6]) and not json.loads(links['bridge-backend-grpc']['via_refs_json']))
    by = {c['name']: c for c in t['EnclosureContact']}
    vp = lambda k: {by[r.partition(':')[2]]['via_part'] for r in json.loads(links[k]['via_refs_json'])}   # noqa: E731
    check('L6: (a) rides RN4A + RN4B (series-resistor 1 kOhm, uart); (b) RN3A/RN3D USB; (c) C5 100 nF as signal_kind reset ("every serial reconnect reboots the UNO")',
          vp('u1-usart0-u2-usart1') == {'RN4A', 'RN4B'} and links['u1-usart0-u2-usart1']['medium'] == 'series-resistor' and links['u1-usart0-u2-usart1']['signal_kind'] == 'uart'
          and vp('u2-usb-host') <= {'RN3A', 'RN3D'} and links['u2-usb-host']['medium'] == 'usb' and vp('u2-dtr-u1-reset') == {'C5'} and links['u2-dtr-u1-reset']['signal_kind'] == 'reset'
          and links['u2-dtr-u1-reset']['medium'] == 'capacitor' and 'reboots the UNO' in links['u2-dtr-u1-reset']['notes'])
    c_pin, c_hash = compat.pinned_contract('LightState')[0]['contract_version'], compat.pinned_contract('LightState')[0]['contract_hash']
    check('L6: LightState v1 (the PINNED contract, hash read from board/custom/contracts) is the protocol on the board<->host link (b) and on the bridge<->backend link (g); (a) carries none',
          'LightState v%s' % c_pin in links['u2-usb-host']['protocol'] and c_hash in links['u2-usb-host']['protocol'] and links['bridge-backend-grpc']['protocol'] == links['u2-usb-host']['protocol']
          and not links['u1-usart0-u2-usart1']['protocol'])
    check('L6: (b) says the USB interface is PENDING — the 16U2 verified, the CH340 unverified — and is `partial`, not verified',
          links['u2-usb-host']['verification'] == 'partial' and 'PENDING' in links['u2-usb-host']['undetermined'] and 'atmega16u2-bridge verified' in links['u2-usb-host']['undetermined']
          and 'ch340-bridge unverified' in links['u2-usb-host']['undetermined'])
    jump = links['d6-d3-jumper']
    check('L6: (d) the D6 -> D3 jumper comes from the BoardPinNet rows (D6 driver, D3 input, one net LED_CONTROL), medium jumper-wire, unverified (design intent, not measured)',
          jump['medium'] == 'jumper-wire' and jump['verification'] == 'unverified' and 'BoardPinNet:%s' % BPN._name('D3', 'LED_CONTROL') in json.loads(jump['endpoint_b_json'])['refs']
          and 'BoardPinNet:%s' % BPN._name('D6', 'LED_CONTROL') in json.loads(jump['endpoint_a_json'])['refs'] and 'not measured' in jump['undetermined'])
    btn = links['button-d2']
    nofw = copy.deepcopy(s)
    nofw['participants_json'] = json.dumps([p for p in parts if not p['ref'].startswith('FirmwareSolution:')])
    ctx0 = Ctx(t, None, nofw)
    lk0 = {l['name'].partition(':')[2]: l for l in HL.links(ctx0, SYSTEM)}
    check('L6: (e) the button on D2 — the pull is defined (no undetermined) because the firmware\'s PinClaim pull=up exists (rule (e) pull_defined ok); without the firmware participant the SAME link says undetermined',
          btn['undetermined'] == '' and 'pull_defined' in btn['citations_json'] and 'not defined' in lk0['button-d2']['undetermined'] and lk0['button-d2']['verification'] == 'unverified', btn['undetermined'])
    check('L6: (f) D6 -> R1 220 ohm -> LED1 -> GND names R1 and LED1 and says the LED forward voltage is assumed (undetermined)',
          'ubc-r1' in links['d6-r1-led1-gnd']['endpoint_b_json'] and 'ubc-led1' in links['d6-r1-led1-gnd']['endpoint_b_json'] and 'assumed' in links['d6-r1-led1-gnd']['undetermined'])

    # ---- L7 the three paths
    paths = {p['name'].partition(':')[2]: p for p in res['SignalPath']}
    check('L7: the three paths exist — button-to-polari, polari-to-led, led-line-to-d3 — each constructs SignalPath, hops numbered 1..n, every verdict in the vocabulary, every hop has a check and a ref',
          list(paths) == ['button-to-polari', 'polari-to-led', 'led-line-to-d3'] and len(built_paths) == 3
          and all([h['n'] for h in _hops(p)] == list(range(1, p['hop_count'] + 1)) and all(h['verdict'] in VERDICTS and h['check'] and 'ref' in h and h['kind'] for h in _hops(p)) for p in paths.values()))
    check('L7: each path is GAP-FREE — every hop\'s ref resolves to a row or is an explicit blocked / undetermined hop naming what is missing (the person is the one undetermined origin)',
          all(p['gap_free'] for p in paths.values()) and all(h['resolved'] or (h['verdict'] in ('blocked', 'undetermined') and ('missing' in h['detail'] or h['detail'].startswith('unresolved'))) for p in paths.values() for h in _hops(p))
          and [h['ref'] for p in paths.values() for h in _hops(p) if not h['resolved']] == ['Person:bench-operator'])
    h1 = _hops(paths['button-to-polari'])
    kinds1 = [h['kind'] for h in h1]
    check('L7: button-to-polari walks person -> SW1 -> net -> D2 header -> E2 crossing -> PD2 leg -> SocPin PD2 -> INT0 -> firmware -> PD1 TXD -> RN4A -> U2 RXD1 -> U2 USB -> USB connector -> host port -> Java bridge -> gRPC -> LightState contract -> page (19 hops)',
          len(h1) == 19 and [h['ref'] for h in h1][3:8] == ['ConnectorPin:%s:DIGITAL_L:3' % BOARD, 'EnclosureContact:%s:board:atmega328p-28-spdip:4=%s:DIGITAL_L:3' % (BOARD, BOARD), 'PackageContact:atmega328p-28-spdip:4',
                                                           'SocPin:atmega328p:PD2', 'PinFunction:atmega328p:PD2:INT0'] and h1[8]['kind'] == 'firmware' and 'RN4A' in h1[10]['what'] and h1[16]['kind'] == 'link' and h1[17]['kind'] == 'contract'
          and 'participant' == kinds1[0], str(kinds1))
    # the D2 hop carries the ladder's verdicts: compare to the ladder itself
    ctx = Ctx(t, None, s)
    lad = LD.availability('D2', 'INT0', {'board': BOARD, 'circuit': 'uno-button-clock', 'binding': 'uno-light@%s' % BOARD, 'transport': 'usb-serial', 'variant_pending': True}, t)
    own = max(SEV[r['rungs'][i]['verdict']] for r in lad['results'] for i in (5, 6, 7, 8))
    d2 = h1[7]
    exp = [max((r['rungs'][i]['verdict'] for r in lad['results']), key=lambda v: SEV[v]) for i in range(10)]
    check('L7: button-to-polari\'s D2/INT0 hop carries the ladder\'s ten rung verdicts (equal to ladder.availability, worst over every allowed package) and its own verdict is the worst of rungs 6-9',
          [r['verdict'] for r in d2['rungs']] == exp and SEV[d2['verdict']] == own and h1[3]['rungs'][2]['verdict'] == exp[2] and h1[5]['rungs'][1]['verdict'] == exp[1] and h1[6]['rungs'][0]['verdict'] == exp[0]
          and d2['check'].startswith('ladder rungs 6-9'), str((d2['verdict'], exp)))
    check('L7: rung 7 on D2 reads the firmware\'s own PinClaim (pull=up): the net hop\'s rule (e) pull_defined is ok, the pressed-contact resistance (rule (h)) stays undetermined on the SW1 hop',
          'pull_defined [ok]' in h1[2]['detail'] and h1[1]['verdict'] == 'undetermined' and 'input_threshold' in h1[1]['detail'])
    check('L7: a hop whose check has not run says `unchecked`: the firmware hop reads the cmod Purpose proof (planned -> unchecked); host port, Java bridge, page have no owning check -> unchecked',
          h1[8]['verdict'] == 'unchecked' and 'ensure-button-controls-light' in h1[8]['check'] and 'planned' in h1[8]['detail'] and [h1[i]['verdict'] for i in (14, 15, 18)] == ['unchecked'] * 3)
    no_circuit = copy.deepcopy(s)
    no_circuit['participants_json'] = json.dumps([p for p in parts if not p['ref'].startswith('CircuitDefinition:') and not p['ref'].startswith('FirmwareSolution:')])
    nc = HP_build(t, no_circuit)
    nh = _hops(nc['button-to-polari'])
    check('L7: with no circuit / firmware among the participants the electrical and claim checks say `unchecked`, never ok (SW1, D2 function hop, rung 7 and 9)',
          nh[1]['verdict'] == 'unchecked' and nh[7]['verdict'] in ('unchecked', 'blocked') and nh[7]['rungs'][6]['verdict'] == 'unchecked' and nh[7]['rungs'][8]['verdict'] == 'unchecked' and nh[2]['verdict'] != 'ok')
    allh = [h for p in paths.values() for h in _hops(p)]
    check('L7: no hop says ok without a check (every `ok` hop names a check other than none, and nothing says ok that its owner did not)',
          all(h['check'] not in ('', 'none') for h in allh if h['verdict'] == 'ok') and not [h for h in allh if h['check'] in ('', 'none') and h['verdict'] == 'ok'])

    # ---- polari-to-led
    h2 = _hops(paths['polari-to-led'])
    d0 = next(h for h in h2 if h['ref'] == 'PinFunction:atmega328p:PD0:RXD')
    plain = LD.availability('D0', 'GPIO', {'board': BOARD, 'circuit': 'uno-button-clock', 'transport': 'usb-serial', 'package': 'atmega328p-28-spdip'}, t)
    purpose = LD.availability('D0', 'RXD', {'board': BOARD, 'circuit': 'uno-button-clock', 'transport': 'usb-serial', 'purpose': True, 'package': 'atmega328p-28-spdip'}, t)
    check('L7: polari-to-led\'s D0 hop is OK as the transport (not blocked): "reserved for the transport, used as the transport" — while a GPIO claim on D0 is STILL blocked at rung 8 by the ladder',
          d0['verdict'] == 'ok' and 'reserved for the transport, used as the transport' in d0['detail'] and d0.get('transport_satisfied') and plain['results'][0]['blocked_at'] == 8
          and purpose['results'][0]['rungs'][7]['verdict'] == 'ok' and 'still be blocked' in d0['detail'])
    led = h2[-1]
    ecs = [f for f in EC.check('uno-button-clock', 'uno-light@%s' % BOARD, EC.tables_for(None), context={'transport': 'usb-serial'}) if f['rule'] in ('led_current', 'voh_under_load')]
    check('L7: polari-to-led\'s LED hop reports the electrical rules\' REAL verdict — led_current (a) and voh_under_load (f) are undetermined (the red LED Vf is assumed, not cited) -> the hop is undetermined, never ok',
          {f['status'] for f in ecs} == {'undetermined'} and led['verdict'] == 'undetermined' and 'led_current' in led['detail'] and 'voh_under_load' in led['detail'] and h2[-2]['verdict'] == 'undetermined')
    cmd = next(h for h in h2 if h['kind'] == 'contract')
    check('L7: polari-to-led names the known gap honestly — LightState v1 has no command_id, confirmation is by correlated state only (fgm-6 adds v2): a `conditional` contract hop',
          cmd['verdict'] == 'conditional' and 'command_id' in cmd['detail'] and 'fgm-6' in cmd['detail'] and 'correlated state' in cmd['detail'])
    check('L7: polari-to-led walks page Toggle -> backend -> contract -> gRPC -> Java bridge -> port -> USB connector -> U2 -> RN4B -> PD0 RXD -> firmware handler -> PD6 -> D6 header -> net -> R1 -> LED1',
          [h['ref'] for h in h2][:2] == ['Runtime:typescript-browser', 'SolutionDefinition:light-toggle'] and 'RN4B' in h2[9]['what'] and h2[11]['kind'] == 'firmware'
          and h2[12]['ref'] == 'PinFunction:atmega328p:PD6:GPIO' and h2[16]['ref'] == 'ConnectorPin:%s:DIGITAL_L:7' % BOARD and h2[-1]['ref'] == 'CircuitComponentDefinition:ubc-led1')

    # ---- led-line-to-d3 and the removed jumper
    h3 = _hops(paths['led-line-to-d3'])
    check('L7: led-line-to-d3 walks D6 net -> jumper -> D3 -> INT1 (ladder) -> firmware sense counter -> state',
          [h['kind'] for h in h3][:3] == ['net', 'net', 'link'] and h3[7]['ref'] == 'PinFunction:atmega328p:PD3:INT1')
    check('L7: smp-2: the uno-light graph now has the sense node `apps/light.sense_poll` polling D3, so the sense-counter hop is `unchecked` (the sense nodes exist, no proof is read for them) and no longer `not-yet`',
          h3[8]['kind'] == 'firmware' and h3[8]['verdict'] == 'unchecked' and 'sense_poll' in h3[8]['detail'] and 'no proof is read' in h3[8]['detail'])
    check('L7: smp-2: the state hop stays `not-yet` — LightState v1 carries no sense counter (the sense line is polled in firmware but not yet on the wire contract)',
          h3[9]['kind'] == 'contract' and h3[9]['verdict'] == 'not-yet' and 'sense' in h3[9]['detail'] and paths['led-line-to-d3']['verdict'] == 'unchecked')
    t2 = copy.deepcopy(t)
    gone = BPN._name('D3', 'LED_CONTROL')
    t2['BoardPinNet'] = [n for n in t2['BoardPinNet'] if n['name'] != gone]
    bad = HS.build(t2, strict=True)
    bp = {p['name'].partition(':')[2]: p for p in bad['SignalPath']}
    bh = _hops(bp['led-line-to-d3'])
    miss = [h for h in bh if h['verdict'] == 'blocked']
    check('L7: REMOVING the D6 -> D3 BoardPinNet breaks led-line-to-d3 BY NAME — the path is blocked at the hop that names the missing BoardPinNet and the missing d6-d3-jumper SystemLink; the link is no longer listed',
          bp['led-line-to-d3']['verdict'] == 'blocked' and bp['led-line-to-d3']['blocked_at'] == miss[0]['n'] and miss[0]['ref'] == 'BoardPinNet:%s' % gone and gone in miss[0]['detail'] and 'missing' in miss[0]['detail']
          and any(h['ref'] == 'SystemLink:%s:d6-d3-jumper' % SYSTEM and gone in h['detail'] for h in miss) and not any(l['name'].endswith('d6-d3-jumper') for l in bad['SystemLink']) and len(bad['SystemLink']) == 6
          and gone in bp['led-line-to-d3']['summary'])
    check('L7: ... while button-to-polari and polari-to-led stay INTACT (hop for hop identical) and every path is still gap-free',
          bp['button-to-polari']['hops_json'] == paths['button-to-polari']['hops_json'] and bp['polari-to-led']['hops_json'] == paths['polari-to-led']['hops_json'] and all(p['gap_free'] for p in bad['SignalPath']))
    check('L7: the original wiring still verdicts led-line-to-d3 as NOT blocked (only conditional / undetermined / not-yet hops)', paths['led-line-to-d3']['verdict'] != 'blocked' and paths['led-line-to-d3']['blocked_at'] == 0)

    # ---- the ladder changes hsp-1 made
    own_claim = LD.availability('D2', 'INT0', {'board': BOARD, 'circuit': 'uno-button-clock', 'binding': 'uno-light@%s' % BOARD, 'package': 'atmega328p-28-spdip'}, t)['results'][0]['rungs']
    other_fn = LD.availability('D2', 'GPIO', {'board': BOARD, 'circuit': 'uno-button-clock', 'binding': 'uno-light@%s' % BOARD, 'package': 'atmega328p-28-spdip'}, t)['results'][0]['rungs']
    check('ladder (hsp-1): with a binding in the context rung 9 confirms the binding\'s OWN claim (INT0 on D2 = ok, not blocked) and rung 7 reads its pull=up; a DIFFERENT function on the claimed pin is still blocked at rung 9',
          own_claim[8]['verdict'] == 'ok' and 'pull_defined' not in own_claim[6]['detail'] and other_fn[8]['verdict'] == 'blocked')

    # ---- doors + CLI
    import falcon
    import falcon.testing as ft
    from board.board_endpoints import construct_board_endpoints
    tabs = {c: {r['name']: types.SimpleNamespace(**{f: r.get(f, '') for f in BO_fields(c)}) for r in rows} for c, rows in t.items() if c in LAYER()}
    _S = types.SimpleNamespace(falconServer=falcon.App(), manager=types.SimpleNamespace(objectTables=tabs, idList=[]))
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            construct_board_endpoints(_S)
        cl = ft.TestClient(_S.falconServer)
        a = cl.simulate_get('/api/hardware-systems').json
        one = cl.simulate_get('/api/hardware-systems/%s' % SYSTEM).json
        lk = cl.simulate_get('/api/hardware-systems/%s/links' % SYSTEM).json
        ps = cl.simulate_get('/api/hardware-systems/%s/paths' % SYSTEM).json
        p1 = cl.simulate_get('/api/hardware-systems/%s/paths?path=led-line-to-d3' % SYSTEM).json
        n1, n2 = cl.simulate_get('/api/hardware-systems/nope'), cl.simulate_get('/api/hardware-systems/%s/paths?path=zz' % SYSTEM)
        old = cl.simulate_get('/api/board/%s/exposure' % BOARD).json
        pins = cl.simulate_get('/api/board/%s/pins/D3' % BOARD).json
        ok = (a['ok'] and a['count'] == 1 and a['rows'][0]['link_count'] == 7 and len(a['rows'][0]['paths']) == 3 and one['ok'] and len(one['links']) == 7 and len(one['participants']) == len(parts)
              and lk['count'] == 7 and ps['count'] == 3 and len(ps['hops']) == sum(p['hop_count'] for p in paths.values()) and p1['count'] == 1 and p1['rows'][0]['name'].endswith('led-line-to-d3')
              and n1.status_code == 404 and n2.status_code == 404 and old['ok'] and pins['ok'])
        why = str((a.get('count'), lk.get('count'), ps.get('count')))
    except Exception as ex:   # a route clash raises UnacceptableRouteError at add time
        ok, why = False, repr(ex)
    check('DOORS: /api/hardware-systems, /{name}, /{name}/links and /{name}/paths[?path=] ADD on a real falcon.App next to every existing board route (no UnacceptableRouteError) and answer; unknown system / path is 404', ok, why)
    from board.custom.hardware_system import main as cli
    outs = []
    for argv in (['list'], ['show', SYSTEM], ['links', SYSTEM], ['paths', SYSTEM, 'led-line-to-d3'], ['paths', SYSTEM, '--json']):
        with contextlib.redirect_stdout(io.StringIO()) as o:
            rc = cli(argv)
        outs.append((rc, o.getvalue()))
    lines = [ln for ln in outs[3][1].splitlines() if re.match(r'^\s+\d+\. ', ln)]
    check('CLI: `list|show|links|paths <system> [<path>] [--json]` run; a path prints ONE HOP PER LINE with its verdict (10 hop lines for led-line-to-d3, each ends its first column with a verdict word)',
          all(rc == 0 for rc, _ in outs) and len(lines) == 10 and all(any(v in ln for v in VERDICTS) for ln in lines) and 'blocked' not in outs[3][1].split('\n')[1]
          and len(json.loads(outs[4][1])) == 3 and SYSTEM in outs[0][1])


def HP_build(t, system):
    """The three paths for a variant of the system row (the participants changed), keyed by slug."""
    from board.custom import hwsys_links as HL
    from board.custom import hwsys_paths as HP
    from board.custom.hwsys_context import Ctx
    ctx = Ctx(t, None, system)
    lk = HL.links(ctx, system['name'])
    links = {l['name'].partition(':')[2]: l for l in lk}
    ctx.extra = {'SystemLink': {l['name'] for l in lk}}
    out = {}
    for slug, fn in HP.PATHS:
        p = fn(ctx, links)
        out[slug] = {'hops_json': json.dumps(p['hops']), 'verdict': p['verdict']}
    return out


def BO_fields(c):
    from board.custom import board_object as BO
    return BO._fields(c)


def LAYER():
    from board.custom import board_object as BO
    return BO.LAYER_CLASSES
