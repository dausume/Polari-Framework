"""board_enclosure_selftest — hsp-0 (HARDWARE_SYSTEM_PINS_PLAN.md §3): the enclosure kinds (tentative), the enclosures, the exposure maps (EnclosureContact), the 16U2 as
rows, reachability, the availability ladder, the chain's exposure hops and the doors on a REAL falcon.App. Run by board_selftest.run().
"""
import contextlib
import io
import json
import re

BOARD = 'arduino-uno-r3'
SPDIP, TQFP, QFN = 'atmega328p-28-spdip', 'atmega328p-32-tqfp', 'atmega16u2-32-qfn'


def _find(rows, **kw):
    return [r for r in rows if all(r.get(k) == v for k, v in kw.items())]


def run_enclosure(check):
    from board import board_basis as B
    from board.board_seed import BOARD_SEED_PAIRS
    from board.custom import board_object as BO
    from board.custom import enclosure_kinds as EK
    from board.custom import exposure_view as V
    from board.custom import reachability as RA
    from board.custom import ladder as LD
    from board.custom import hardware_chain as HC
    with contextlib.redirect_stdout(io.StringIO()):
        t = BO.seed_tables()
    kinds, encl, xc = t['EnclosureKind'], t['HardwareEnclosure'], t['EnclosureContact']
    E1 = [c for c in xc if c['level'] == 'E1']
    E2 = [c for c in xc if c['level'] == 'E2']

    # ---- the classes
    new = (B.EnclosureKind, B.HardwareEnclosure, B.EnclosureContact)
    check('hsp-0: the three classes are BOARD_CLASSES members, each with plain_words', all(c in B.BOARD_CLASSES and getattr(c, 'plain_words', '') for c in new))
    seeded = {c: rows for c, _cls, rows in BOARD_SEED_PAIRS}
    check('hsp-0: the three classes are seeded code-owned (every row converges) and every row constructs its class',
          all(seeded.get(n) and all('_converge' in r for r in seeded[n]) for n in ('EnclosureKind', 'HardwareEnclosure', 'EnclosureContact'))
          and all(cls(**r) for n, cls in zip(('EnclosureKind', 'HardwareEnclosure', 'EnclosureContact'), new) for r in t[n]))
    # ---- L1 kinds
    check('L1: every EnclosureKind is `tentative`', kinds and all(k['status'] == 'tentative' for k in kinds))
    check('L1: kinds cover E0..E5, names are <level>:<slug> (E1:dip exists), functions are a subset of the seven, pin_relevant is a bool',
          {k['level'] for k in kinds} == {'E0', 'E1', 'E2', 'E3', 'E4', 'E5'} and all(k['name'] == '%s:%s' % (k['level'], k['slug']) for k in kinds)
          and any(k['name'] == 'E1:dip' for k in kinds) and len({k['name'] for k in kinds}) == len(kinds)
          and all(set(json.loads(k['functions_json'])) <= set(EK.FUNCTIONS) and json.loads(k['functions_json']) for k in kinds)
          and all(isinstance(k['pin_relevant'], bool) for k in kinds))
    check('L1: pin_relevant is true for packages / the board / connector shells / carriers and false for heat sinks, gaskets, vents',
          all(_find(kinds, name=n)[0]['pin_relevant'] for n in ('E1:dip', 'E1:qfn', 'E1:tqfp', 'E2:board', 'E1:connector-shell', 'E3:shield-stack', 'E3:daughterboard', 'E2:test-pad'))
          and not any(_find(kinds, name=n)[0]['pin_relevant'] for n in ('E2:heat-sink', 'E4:gasket', 'E4:vent', 'E3:standoff')))
    check('L1: terminology only — no kind carries a digit in its words (no physics number lives in the catalogue)', not [k['name'] for k in kinds if re.search(r'\d', k['description'])])
    # ---- L2 enclosures
    names = {e['name']: e for e in encl}
    check('L2: six enclosures — U1 SPDIP (E1:dip), U2 QFN (E1:qfn), the TQFP variant (E1:tqfp), the UNO board (E2:board); c3pf: + the ESP32-C3 QFN32 (E1:qfn); c3-pv: '
          '+ the DevKitM-1 board (E2:board, now that J1/J3 are modelled), the QFN32 inside it',
          len(encl) == 6 and names['esp32-c3:U1:package']['kind'] == 'E1:qfn' and names['esp32-c3:U1:package']['parent'] == 'esp32-c3:board'
          and names['esp32-c3:board']['kind'] == 'E2:board' and names[BOARD + ':U1:package']['kind'] == 'E1:dip' and names[BOARD + ':U2:package']['kind'] == 'E1:qfn'
          and names[TQFP + ':variant']['kind'] == 'E1:tqfp' and names[BOARD + ':board']['kind'] == 'E2:board' and all(e['kind'] in {k['name'] for k in kinds} for e in encl))
    check('L2: the SPDIP and the QFN sit inside the board; the TQFP has no parent and no board; each E1 names its package and component',
          names[BOARD + ':U1:package']['parent'] == names[BOARD + ':U2:package']['parent'] == BOARD + ':board' and names[TQFP + ':variant']['parent'] == ''
          and names[TQFP + ':variant']['board'] == '' and names[BOARD + ':U1:package']['package'] == SPDIP and names[BOARD + ':U2:package']['component'] == BOARD + ':U2')
    check('L2: every enclosure has a verification and a citation', all(e['verification'] in ('verified', 'partial', 'unverified', 'conflicted') and e['document'] and e['page_table'] for e in encl))
    # ---- L5 the 16U2
    qc = [c for c in t['PackageContact'] if c['package'] == QFN]
    nums = {c['number']: c for c in qc}
    check('L5: every 16U2 contact exists — legs 1..32 plus the centre pad (33), each cited to Figure 1-1 p.2', set(nums) == set(range(1, 34)) and all(c['page_table'] for c in qc))
    check('L5: read from the figure — 1 XTAL1, 8 PD2, 9 PD3, 13 PD7, 24 PC1 (Reset), 27 UCAP, 29 D+, 30 D-, 32 AVCC, 33 PAD',
          [nums[i]['label'] for i in (1, 8, 9, 13, 24, 27, 29, 30, 32, 33)] == ['XTAL1', 'PD2', 'PD3', 'PD7', 'PC1', 'UCAP', 'D+', 'D-', 'AVCC', 'PAD'])
    u2pins = [s for s in t['SocPin'] if s['soc'] == 'atmega16u2']
    check('L5: the 16U2 has 23 SocPins, each with its QFN leg and a cited fact; PD2 carries RXD1, PD3 TXD1, PD7 CTS/HWB; the QFN PackageDefinition is 32M1-A',
          len(u2pins) == 23 and all(s['package_pin'] and s['fact'] for s in u2pins) and 'RXD1' in next(s for s in u2pins if s['pin'] == 'PD2')['functions_json']
          and 'TXD1' in next(s for s in u2pins if s['pin'] == 'PD3')['functions_json'] and {'CTS', 'HWB'} <= set(json.loads(next(s for s in u2pins if s['pin'] == 'PD7')['functions_json']))
          and _find(t['PackageDefinition'], name=QFN)[0]['code'] == '32M1-A' and all(json.loads(s['package_contacts_refs_json']) for s in u2pins))
    # ---- L3 the exposure maps
    check('L3: E1 — one crossing per contact of every package (60 + 33 = 93, the TQFP counted; c3pf: + 33 of the ESP32-C3 QFN32 = 126) plus two not-bonded rows (ADC6, ADC7) on the SPDIP',
          len([c for c in E1 if c['via'] != 'not-bonded']) == 126 and len(_find(E1, via='not-bonded')) == 2)
    ctr = {c['via'] for c in xc}
    check('L3: every via is one of the allowed kinds; every verification is one of the four; names are unique',
          ctr <= {'direct', 'series-resistor', 'buffer', 'capacitor', 'jumper', 'series-inductor', 'series-fuse', 'not-bonded', 'internal-only'}
          and {c['verification'] for c in xc} <= {'verified', 'partial', 'unverified', 'conflicted'} and len({c['name'] for c in xc}) == len(xc))

    def touching(label_leg):
        return [c for c in E2 if label_leg in (c['inner_ref'], c['outer_ref'])]
    d0, d1 = touching('PackageContact:%s:2' % SPDIP), touching('PackageContact:%s:3' % SPDIP)
    check('ACCEPT D0/D1: each shows the 1 kOhm series crossing to U2 (RN4B to leg 9 TXD1; RN4A to leg 8 RXD1) beside its header pin',
          any(c['via'] == 'series-resistor' and c['via_part'] == 'RN4B' and c['via_value'] == '1 kOhm' and c['outer_ref'] == 'PackageContact:%s:9' % QFN for c in d0)
          and any(c['via'] == 'series-resistor' and c['via_part'] == 'RN4A' and c['via_value'] == '1 kOhm' and c['outer_ref'] == 'PackageContact:%s:8' % QFN for c in d1)
          and any(c['via'] == 'direct' and c['outer_ref'].startswith('ConnectorPin:%s:DIGITAL_L' % BOARD) for c in d0 + d1))
    d13 = touching('PackageContact:%s:19' % SPDIP)
    check('ACCEPT D13: the LMV358 buffer crossing (U5B), consumed by the L LED, beside the DIGITAL_H and ICSP header pins',
          any(c['via'] == 'buffer' and 'LMV358' in c['via_part'] and 'L LED' in c['consumed_by'] and not c['exposed'] for c in d13)
          and {c['outer_ref'].split(':')[2] for c in d13 if c['outer_ref'].startswith('ConnectorPin')} >= {'DIGITAL_H', 'ICSP'})
    rs = touching('PackageContact:%s:1' % SPDIP) + touching('PackageContact:%s:13' % QFN)
    check('ACCEPT RESET: C5 100 nF from the 16U2 PD7 (DTR) into leg 1; the RESET rail reaches POWER and ICSP header pins; the button is a crossing too',
          any(c['via'] == 'capacitor' and c['via_part'] == 'C5' and c['via_value'] == '100 nF' and c['inner_ref'] == 'PackageContact:%s:13' % QFN and c['outer_ref'] == 'PackageContact:%s:1' % SPDIP for c in rs)
          and {h.rpartition(':')[0].rpartition(':')[2] for c in rs if c['outer_ref'] == 'BoardNet:%s:RESET' % BOARD for h in V.header_pins(c['outer_ref'], t)} >= {'POWER', 'ICSP'}
          and any('button' in c['outer_ref'] for c in rs))
    check('ACCEPT PB6/PB7: internal-only, consumed by the CSTCE16M0V53-R0 16 MHz part, exposed False, on no header',
          all(any(c['via'] == 'internal-only' and c['via_part'] == 'CSTCE16M0V53-R0' and '16 MHz' in c['consumed_by'] and not c['exposed'] for c in touching('PackageContact:%s:%d' % (SPDIP, n)))
              and not any(c['exposed'] for c in touching('PackageContact:%s:%d' % (SPDIP, n))) for n in (9, 10)))
    nb = _find(E1, via='not-bonded')
    adc = {c['enclosure']: c for c in E1 if 'ADC6' in c['inner_ref'] and c['via'] != 'not-bonded'}
    check('ACCEPT ADC6/ADC7: not-bonded on the SPDIP, bonded (direct, exposed) on the TQFP, and on no UNO header (no E2 crossing mentions them)',
          {c['inner_ref'] for c in nb} == {'SocSignal:atmega328p:ADC6', 'SocSignal:atmega328p:ADC7'} and all(c['enclosure'] == BOARD + ':U1:package' and not c['exposed'] for c in nb)
          and all(any(c['inner_ref'] == 'SocSignal:atmega328p:%s' % a and c['via'] == 'direct' and c['exposed'] and c['outer_ref'].startswith('PackageContact:' + TQFP) for c in E1) for a in ('ADC6', 'ADC7'))
          and not any('ADC6' in c['label'] or 'ADC7' in c['label'] for c in E2) and not any(cp['label'] in ('ADC6', 'ADC7') for cp in t['ConnectorPin']))
    check('L3: every SPDIP leg has at least one E2 crossing; every 16U2 contact appears in some E2 crossing (the unused ones as internal-only, consumed_by empty, partial)',
          all(touching('PackageContact:%s:%d' % (SPDIP, n)) for n in range(1, 29)) and all(touching('PackageContact:%s:%d' % (QFN, n)) for n in range(1, 34))
          and all(c['via'] == 'internal-only' and c['consumed_by'] == '' and c['verification'] == 'partial' and c['undetermined'] for n in (5, 6, 7, 12, 14, 22, 23, 25, 26) for c in touching('PackageContact:%s:%d' % (QFN, n))))
    check('L3: the USB pair — D+ / D- reach the USB connector through 22 Ohm series resistors (RN3D, RN3A), the VBUS through the F1 fuse; ICSP1 gets PB1/PB2/PB3/RESET',
          {(c['via_part'], c['via_value']) for c in E2 if c['outer_ref'].startswith('SchematicPart:X2')} >= {('RN3D', '22 Ohm'), ('RN3A', '22 Ohm'), ('F1 MF-MSMF050-2', '500 mA')}
          and len([c for c in E2 if c['outer_ref'].startswith('SchematicPart:ICSP1')]) == 4)
    check('L3 / L8: every row with a via_value (a number) carries a citation (page_table + document) or an `undetermined`; every row has a citation or `undetermined`',
          all((c['page_table'] and c['document']) or c['undetermined'] for c in xc) and all((c['page_table'] and c['document']) or c['undetermined'] for c in xc if c['via_value']))
    check('L3: every E1 die side is undetermined (no die-pad map is cited); every not-bonded row is exposed False', all('die pad' in c['undetermined'] for c in E1) and all(not c['exposed'] for c in xc if c['via'] in ('not-bonded', 'internal-only')))

    # ---- L4 reachability
    r = RA.reach(BOARD, t)
    u1 = [p for p in r['pins'] if p['component'].endswith(':U1') and p['soc_pin']]
    check('L4: every ATmega328P SocPin (23) has a verdict in header | internal | not-bonded | undetermined, plus ADC6/ADC7 as not-bonded on the SPDIP',
          len(u1) == 23 and all(p['verdict'] in RA.VERDICTS for p in r['pins']) and {p['pin'] for p in r['pins'] if p['verdict'] == 'not-bonded' and p['component'].endswith(':U1')} == {'ADC6', 'ADC7'})
    vd = {p['pin']: p for p in u1}
    check('L4: PB6/PB7 internal (the 16 MHz part), PD0/PD1 header (+ the 16U2 consumer), PB5 header, PC6 header (RESET); function on an internal pin is NOT reachable',
          vd['PB6']['verdict'] == vd['PB7']['verdict'] == 'internal' and 'CSTCE16M0V53-R0' in vd['PB6']['consumed_by'][0] and vd['PD0']['verdict'] == vd['PD1']['verdict'] == vd['PB5']['verdict'] == 'header'
          and vd['PC6']['verdict'] == 'header' and any('ATmega16U2' in x or 'U2' in x for x in vd['PD0']['consumed_by'])
          and not any(f['reachable'] for f in r['functions'] if f['soc_pin'] == 'atmega328p:PB6') and all(f['reachable'] for f in r['functions'] if f['soc_pin'] == 'atmega328p:PD3'))
    pf = [f for f in t['PinFunction'] if f['soc'] == 'atmega328p']
    check('L4: every PinFunction row of the 328P has a reachability entry (%d)' % len(pf), len([f for f in r['functions'] if f['component'].endswith(':U1')]) == len(pf))
    u2 = {p['pin']: p for p in r['pins'] if p['component'].endswith(':U2')}
    check('L4: the 16U2 — PD7 internal (C5 into RESET), PB1 header (ICSP1), PD0 internal and unconsumed, 23 verdicts',
          len(u2) == 23 and u2['PB1']['verdict'] == 'header' and u2['PD0']['verdict'] == 'internal' and u2['PD0']['consumed_by'] == [''] and u2['PD7']['verdict'] == 'internal')
    tr = r['headers']
    check('L4: per header pin the inward trace — DIGITAL_L pin 1 (D0) walks crossing -> leg 2 -> SocPin PD0 -> RXD; GND/+5V rails branch to the legs; IOREF has no chip leg (said)',
          tr[BOARD + ':DIGITAL_L:1']['inward'] and tr[BOARD + ':DIGITAL_L:1']['inward'][0]['inner'] == 'SocPin:atmega328p:PD0' and 'RXD' in tr[BOARD + ':DIGITAL_L:1']['inward'][0]['functions']
          and len(tr[BOARD + ':POWER:6']['inward']) >= 3 and not tr[BOARD + ':POWER:2']['inward'] and tr[BOARD + ':POWER:2']['note'])

    # ---- the ladder (Revision 2 §5.2)
    def res(pin, fn, **ctx):
        return LD.availability(pin, fn, dict({'board': BOARD}, **ctx), t)['results']
    d0l = res('D0', 'RXD', package=SPDIP, transport='usb-serial')[0]
    rg = {x['rung']: x for x in d0l['rungs']}
    check('LADDER: ten rungs in order, verdicts from the allowed set', [x['rung'] for x in d0l['rungs']] == list(range(1, 11)) and all(x['verdict'] in LD.VERDICTS for x in d0l['rungs']))
    check('LADDER: D0 RXD with transport=usb-serial blocked at rung 8; rung 4 names the 16U2 via RN4B 1 kOhm',
          d0l['blocked_at'] == 8 and rg[8]['verdict'] == 'blocked' and 'RN4B' in rg[4]['detail'] and '1 kOhm' in rg[4]['detail'] and 'ATmega16U2' in rg[4]['detail'] and rg[1]['verdict'] == rg[2]['verdict'] == rg[3]['verdict'] == 'ok')
    check('LADDER: the purpose=true claim (the transport itself on D0) is native: rung 8 ok', {x['rung']: x for x in res('D0', 'RXD', package=SPDIP, transport='usb-serial', purpose=True)[0]['rungs']}[8]['verdict'] == 'ok')
    a6 = res('ADC6', 'ADC6', package=SPDIP)[0]
    a6t = res('ADC6', 'ADC6', package=TQFP)[0]
    check('LADDER: ADC6 on the UNO SPDIP blocked at rung 2; on the TQFP context passes rung 2 and is blocked at rung 3 (no UNO header)',
          a6['blocked_at'] == 2 and a6t['blocked_at'] == 3 and {x['rung']: x for x in a6t['rungs']}[2]['verdict'] == 'ok' and 'no header' in {x['rung']: x for x in a6t['rungs']}[3]['detail'])
    pb6 = res('PB6', 'GPIO', package=SPDIP)[0]
    check('LADDER: PB6 GPIO blocked at rung 3 (internal) and rung 4 (the 16 MHz part)', pb6['blocked_at'] == 3 and {x['rung']: x for x in pb6['rungs']}[4]['verdict'] == 'blocked'
          and 'CSTCE16M0V53-R0' in {x['rung']: x for x in pb6['rungs']}[4]['detail'])
    d3 = res('D3', 'INT1', package=SPDIP, circuit='uno-button-clock')[0]
    g = {x['rung']: x for x in d3['rungs']}
    check('LADDER: D3 INT1 with circuit uno-button-clock passes rungs 1-8 (none blocked), rung 9 unchecked, rung 10 not-yet',
          d3['blocked_at'] == 0 and all(g[i]['verdict'] != 'blocked' for i in range(1, 9)) and g[9]['verdict'] == 'unchecked' and g[10]['verdict'] == 'not-yet' and g[7]['verdict'] != 'unchecked')
    check('LADDER: no circuit -> rung 7 unchecked; no binding -> rung 9 unchecked; none attached at rung 5', {x['rung']: x for x in d0l['rungs']}[7]['verdict'] == 'unchecked' and rg[9]['verdict'] == 'unchecked' and 'none attached' in rg[5]['detail'])
    pend = LD.availability('ADC6', 'ADC6', {'board': BOARD}, t)
    check('LADDER: a PENDING package variant computes every allowed package and shows the difference (SPDIP blocked at 2, TQFP at 3)',
          [x['package'] for x in pend['results']] == [SPDIP, TQFP] and pend['differs'] and pend['difference'])
    part = LD.availability('D0', 'RXD', {'participants': json.dumps([{'role': 'board', 'kind': 'board', 'ref': BOARD, 'variant': 'pending'}, {'role': 'chip', 'kind': 'soc', 'ref': 'atmega328p'}])}, t)
    check('LADDER: the participants_json shape of the cmod Purpose seeds names board + chip (+ pending variant)', part['board'] == BOARD and len(part['results']) == 2)
    check('LADDER: an unknown pin is refused by name', _refuses(lambda: LD.availability('D99', 'GPIO', {'board': BOARD}, t)))

    # ---- the chain's exposure hops
    h0 = HC.chain_for(BOARD, 'D0', t)
    h13 = HC.chain_for(BOARD, 'D13', t)
    ex0 = [h for h in h0 if h['kind'] == 'EnclosureContact']
    check('CHAIN: D0 gains the exposure hops next to the PackageContact hops (series-resistor RN4B 1 kOhm among them); D13 shows the buffer; hop order otherwise unchanged',
          any('series-resistor RN4B 1 kOhm' in h['detail'] for h in ex0) and any('buffer U5B' in h['detail'] for h in h13 if h['kind'] == 'EnclosureContact')
          and [h['kind'] for h in h0].index('EnclosureContact') > max(i for i, h in enumerate(h0) if h['kind'] == 'PackageContact')
          and [h['kind'] for h in h0][:2] == ['BoardPin', 'SocPin'])

    # ---- doors + CLI
    import falcon
    import falcon.testing as ft
    from board.board_endpoints import construct_board_endpoints

    import types
    tabs = {c: {r['name']: types.SimpleNamespace(**{f: r.get(f, '') for f in BO._fields(c)}) for r in rows} for c, rows in t.items() if c in BO.LAYER_CLASSES}
    _S = types.SimpleNamespace(falconServer=falcon.App(), manager=types.SimpleNamespace(objectTables=tabs, idList=[]))
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            construct_board_endpoints(_S)
        cl = ft.TestClient(_S.falconServer)
        e = cl.simulate_get('/api/board/%s/exposure' % BOARD).json
        ep = cl.simulate_get('/api/board/%s/exposure/D13' % BOARD).json
        er = cl.simulate_get('/api/board/%s/exposure/RESET' % BOARD).json
        rc = cl.simulate_get('/api/board/%s/reachability' % BOARD).json
        lad = cl.simulate_get('/api/board/%s/reachability?pin=D0&function=RXD&package=%s&transport=usb-serial' % (BOARD, SPDIP)).json
        chain = cl.simulate_get('/api/board/%s/chain/D3' % BOARD).json
        bad = cl.simulate_get('/api/board/%s/exposure/D99' % BOARD)
        pins = cl.simulate_get('/api/board/%s/pins/D3' % BOARD).json
        ok = (e['ok'] and e['count'] == len(V.board_rows(t, BOARD)) and ep['ok'] and any(c['via'] == 'buffer' for c in ep['rows'])
              and any(c['via'] == 'capacitor' for c in er['rows']) and rc['ok'] and len(rc['pins']) >= 46 and lad['results'][0]['blocked_at'] == 8 and chain['ok'] and pins['ok'] and bad.status_code == 404 and e['source'] == 'live' and any(h['kind'] == 'EnclosureContact' for h in chain['rows']))
        why = str((e.get('count'), len(xc)))
    except Exception as ex:   # a route clash raises UnacceptableRouteError at add time
        ok, why = False, repr(ex)
    check('DOORS: the exposure / exposure/{pin} / reachability routes ADD on a real falcon.App beside every existing board route (no UnacceptableRouteError) and answer; an unknown pin is 404', ok, why)
    from board.custom.reachability import main as cli
    with contextlib.redirect_stdout(io.StringIO()) as o1:
        a = cli(['exposure', BOARD, 'D0'])
    with contextlib.redirect_stdout(io.StringIO()) as o2:
        b = cli(['reach', BOARD, '--json'])
    with contextlib.redirect_stdout(io.StringIO()) as o3:
        c = cli(['ladder', BOARD, 'D0', 'RXD', '--package', SPDIP, '--transport', 'usb-serial'])
    from board.custom import reachability as RCH
    d13 = RCH.exposure(BOARD, 'D13', t)
    check('SCOPE: a board pin\'s exposure is its OWN SoC\'s pin only — D13 (328P PB5) never lists the 16U2\'s PB5 crossings',
          d13 and not any('atmega16u2' in (c['inner_ref'] + c['outer_ref']) for c in d13), str([c['name'] for c in d13 if 'atmega16u2' in c['inner_ref'] + c['outer_ref']]))
    check('CLI: `exposure <board> [<pin>]`, `reach <board> --json` and `ladder` run', a == b == c == 0 and 'RN4B' in o1.getvalue() and json.loads(o2.getvalue())['ok'] and 'blocked at rung 8' in o3.getvalue())


def _refuses(fn):
    try:
        fn()
    except (KeyError, ValueError):
        return True
    return False
