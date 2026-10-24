"""board_pin_view_selftest — pv-0 (PIN_VIEW_PLAN.md 2.1 / 2.2 / 2.5 / 2.8 / 2.9): the math-defined shapes, the protocol-family vocabulary, the pin-view door family, the composition stages, the three
data pages and the CLI. Run by board_selftest.run(). Every verdict asserted here is compared with the output of the code that OWNS the check (the ladder, the electrical rules, reachability, the
cmod claims), never with a copy.
"""
import contextlib
import io
import json
import re
import types

BOARD = 'arduino-uno-r3'
SYSTEM = 'uno-light-system'
BINDING = 'uno-light@arduino-uno-r3'
#: digits followed by an electrical unit: no connection payload may carry one (the numbers belong to the electrical view)
UNIT = re.compile(r'\d\s*(mA|V|ohm|Ohm|kOhm|MOhm|uA|nF|uF|pF|mV)\b')


def _line(res, canon):
    """Every pin id of one board line (die pad, leg(s), header pin(s)) by its canonical name."""
    return {p['id'] for p in res['pins'] if p['canonical'] == canon}


def run_pin_view(check):
    from board.custom import board_object as BO
    from board.custom import hardware_system as HS
    from board.custom import ladder as LD
    from board.custom import pin_view as PV
    from board.custom import pv_families as F
    from board.custom import pv_shapes as S
    from board.custom.hwsys_context import Ctx
    from board.custom import hwsys_system as SYS
    with contextlib.redirect_stdout(io.StringIO()):
        t = HS.default_tables()
    rows = S.shape_rows(t)
    by = {r['name']: r for r in rows}

    # ---- shapes: parametric generators compute the pins
    spdip, tqfp, qfn = (by['pv-pkg-atmega328p-28-spdip'], by['pv-pkg-atmega328p-32-tqfp'], by['pv-pkg-atmega16u2-32-qfn'])
    ls, lt, lq = S.layout(spdip), S.layout(tqfp), S.layout(qfn)
    soic = S.two_row({'pins': 8, 'pitch': 1.27, 'row_spacing': 5.4})
    qfp = S.quad({'pins': 44, 'pitch': 0.8, 'ring_side': 10.0})
    check('SHAPES: the generators compute the right pin count (SPDIP 28 from the 28 PackageContact rows, TQFP 32, QFN 32 + the exposed pad, a generic SOIC-8 and a QFP-44) and EVERY pin lies on its ring perimeter',
          [len(x['pins']) for x in (ls, lt, lq, soic, qfp)] == [28, 32, 32, 8, 44] and lq['pad'] is not None and lq['pad']['number'] == 33 and ls['pad'] is None and lt['pad'] is None
          and all(S.on_perimeter(p, x['ring']) for x in (ls, lt, lq, soic, qfp) for p in x['pins'])
          and sum(1 for c in t['PackageContact'] if c['package'] == 'atmega328p-28-spdip') == 28 and sum(1 for c in t['PackageContact'] if c['package'] == 'atmega16u2-32-qfn') == 33,
          [len(x['pins']) for x in (ls, lt, lq, soic, qfp)])
    leg12 = next(c for c in t['PackageContact'] if c['package'] == 'atmega328p-28-spdip' and c['number'] == 12)
    p12 = next(p for p in ls['pins'] if p['number'] == 12)
    span = 13 * (0.100 * 25.4)
    check('SHAPES: 328P SPDIP leg 12 is PD6 (the PackageContact row) and the generator puts it on the LEFT row at index 11 (y = -span/2 + 11 pitch, x = -row spacing/2); leg 15 is the first of the right row, leg 28 its last',
          leg12['label'] == 'PD6' and p12['side'] == 'left' and p12['index'] == 11 and abs(p12['y'] - (-span / 2 + 11 * 2.54)) < 1e-9 and abs(p12['x'] + 3.81) < 1e-9
          and next(p for p in ls['pins'] if p['number'] == 15)['side'] == 'right' and next(p for p in ls['pins'] if p['number'] == 28)['index'] == 13, str(p12))
    check('SHAPES: the QFN has its 32 legs on four sides (8 each, counter-clockwise from pin 1 at the top of the left side) and the exposed pad (leg 33) at the centre, 3.10 x 3.10 mm as cited',
          [sum(1 for p in lq['pins'] if p['side'] == s) for s in ('left', 'bottom', 'right', 'top')] == [8, 8, 8, 8] and lq['pins'][0]['side'] == 'left' and lq['pins'][8]['side'] == 'bottom'
          and lq['pad']['w'] == 3.10 and (lq['pad']['x'], lq['pad']['y']) == (0.0, 0.0), str(lq['pad']))
    cited = {n: json.loads(r['parameters_json']) for n, r in by.items()}
    check('SHAPES: every dimension is CITED (document + page / table) or listed as a DRAWING KNOB — the three packages and the board carry `cited`, every row carries `knobs`; the dies cite nothing (no die map) and say so; the TQFP pitch is 0.80 (p.636), the QFN pitch 0.50, the SPDIP 2.54, the board 66.04 x 50.80',
          all(cited[n]['cited'] and all('page_table' in v and v['document'] for v in cited[n]['cited'].values()) for n in ('pv-pkg-atmega328p-28-spdip', 'pv-pkg-atmega328p-32-tqfp', 'pv-pkg-atmega16u2-32-qfn', 'pv-board-arduino-uno-r3'))
          and all(cited[n]['cited'] == {} and any('no die map' in k for k in cited[n]['knobs']) for n in ('pv-die-atmega328p', 'pv-die-atmega16u2'))
          and all(p['knobs'] for p in cited.values()) and cited['pv-pkg-atmega328p-32-tqfp']['cited']['pitch']['value'] == 0.80 and cited['pv-pkg-atmega16u2-32-qfn']['cited']['pitch']['value'] == 0.50
          and cited['pv-pkg-atmega328p-28-spdip']['cited']['pitch']['value'] == 2.54 and cited['pv-board-arduino-uno-r3']['cited']['bbox']['value'] == [66.04, 50.80],
          sorted(cited))
    from mathshapes.shape_basis import MathShapeDefinition
    ok_rows = True
    for r in rows:
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                MathShapeDefinition(**r)
        except Exception as e:   # noqa: BLE001
            ok_rows = repr(e)
    from board.board_seed import BOARD_SEED_PAIRS
    pair = [p for p in BOARD_SEED_PAIRS if p[0] == 'MathShapeDefinition']
    check('SHAPES: every shape is a real MathShapeDefinition row (family primitive, kind polygon) and the board seed carries them code-owned (%d rows: 3 packages, 2 dies, 1 board, %d parts, %d bench parts)' % (len(rows), sum(1 for r in rows if r['name'].startswith('pv-part-') and 'bench-' not in r['name']), sum(1 for r in rows if 'bench-' in r['name'])),
          ok_rows is True and len(pair) == 1 and len(pair[0][2]) == len(rows) and all(r['family'] == 'primitive' and r['primitive_kind'] == 'polygon' for r in rows) and all('_converge' in r for r in pair[0][2]), str(ok_rows))

    # ---- the vocabulary
    soc_fns = {f for s in t['SocPin'] if s['soc'] in ('atmega328p', 'atmega16u2') for f in json.loads(s['functions_json'])}
    unmapped = sorted(f for f in soc_fns | {'GPIO'} if not F.families_of_function(f))
    check('FAMILIES: every one of the twelve families has a token name (--pin-<family>), a text pair and a fallback hex (the six ROLE_COLORS reused, the four others labelled drawing knobs); every function of both chips maps to a family; spi / i2c / uart / usb expand to their child signals',
          len(F.FAMILIES) == 12 and all(r['token'] == '--pin-' + r['family'] and r['text_token'] == r['token'] + '-text' and re.match(r'#[0-9a-f]{6}', r['fallback_hex']) for r in F.family_rows())
          and sum(1 for r in F.family_rows() if r['hex_is_drawing_knob']) == 4 and not unmapped and F.set_children('spi') == ['SCK', 'MOSI', 'MISO', 'SS'] and F.set_children('i2c') == ['SDA', 'SCL']
          and F.set_children('uart') == ['RXD', 'TXD'] and F.set_children('usb') == ['D+', 'D-'] and F.function_matches('spi', 'SCLK') == 'SCK' and F.function_matches('spi', 'MOSI') == 'MOSI' and F.function_matches('uart', 'TXD1') == 'TXD',
          str(unmapped))

    # ---- the structure
    base = PV.build(BOARD, {})
    pins = {p['id']: p for p in base['pins']}
    die_ids = {p['id'] for p in base['pins'] if p['level'] == 'die'}
    missing = [s['name'] for s in t['SocPin'] if s['soc'] in ('atmega328p', 'atmega16u2') and 'SocPin:%s' % s['name'] not in die_ids]
    check('MODEL: every SocPin of BOTH chips appears as a die pad (%d SocPins; the die pads also carry the supply / signal pads the package crossings name)' % sum(1 for s in t['SocPin'] if s['soc'] in ('atmega328p', 'atmega16u2')),
          not missing and sum(1 for s in t['SocPin'] if s['soc'] in ('atmega328p', 'atmega16u2')) == 46, str(missing))
    check('MODEL: a SoC surface carries the link to its register profile door (/api/board/socs/{soc}/register-profile)',
          all(s['links'].get('register_profile') == '/api/board/socs/%s/register-profile' % s['soc'] for s in base['surfaces'] if s['kind'] == 'soc') and sum(1 for s in base['surfaces'] if s['kind'] == 'soc') == 2, '')
    kinds = {s['kind'] for s in base['surfaces']}
    lv = base['counts']['by_level']
    check('MODEL: surfaces are the board, two enclosures (packages), two SoCs (dies), the board parts and the bench parts, each with its shape row; pins exist at every level (die %d, package %d, board %d, part %d, bench %d); every pin sits in a surface' % tuple(lv[k] for k in ('die', 'package', 'board', 'part', 'bench')),
          kinds == {'board', 'enclosure', 'soc', 'board-part', 'bench-part', 'bench-board'} and all(s['shape'] in base['shapes'] for s in base['surfaces']) and all(lv[k] > 0 for k in lv) and lv['board'] == 38 and lv['package'] == 28 + 33
          and all(p['surface'] in {s['id'] for s in base['surfaces']} for p in base['pins']) and {s['parent'] for s in base['surfaces'] if s['kind'] == 'soc'} == {'package:%s:U1' % BOARD, 'package:%s:U2' % BOARD}
          and all(s['parent'] == 'board:%s' % BOARD for s in base['surfaces'] if s['kind'] == 'enclosure'), str(lv))
    # ---- pv-6: the bench parts sit on the breadboard the layout engine places them on (his 2026-10-23: "the breadboard visualization does not show up and the button and other pieces appear to be in the middle of nowhere")
    from board.custom import pin_view_model as PVM
    from board import layout_page as LPG
    bb = [s for s in base['surfaces'] if s['kind'] == 'bench-board']
    bench = base['bench']
    lay = PV.bench_layout('', BOARD)[0]
    bshape = base['shapes'].get(bb[0]['shape'], {}).get('parameters', {}) if bb else {}
    check('pv-6 BENCH BOARD: without a binding the pin view lays the bench out from the Layout page\'s default config (%s == board.layout_page.DEFAULT_CONFIG); ONE breadboard surface (kind bench-board, level bench) whose shape row '
          '(generator breadboard, pitch cited) carries the layout\'s rows / rail holes and is in the payload\'s shapes; the payload\'s `bench` block names the config, the board and the placed parts' % bench['config'],
          lay is not None and bench['config'] == PVM.BENCH_LAYOUT_DEFAULT[BOARD] == LPG.DEFAULT_CONFIG and len(bb) == 1 and bb[0]['level'] == 'bench' and bshape.get('generator') == 'breadboard'
          and bshape.get('rows') == lay['board']['rows'] == bench['board']['rows'] and bshape.get('rail_holes') == lay['board']['rail_holes'] and 'pitch' in bshape.get('cited', {}) and bench['why'] == ''
          and bench['board']['surface'] == bb[0]['id'], str(bench))
    geo = S.breadboard_geometry(lay['board']['rows'], lay['board']['rail_holes'])
    bx0, by0 = bb[0]['x'] - bb[0]['w'] / 2, bb[0]['y'] - bb[0]['h'] / 2
    parts = {s['ref'].partition(':')[2]: s for s in base['surfaces'] if s['kind'] == 'bench-part'}
    inside = all(bx0 <= s['x'] <= bx0 + bb[0]['w'] and by0 <= s['y'] <= by0 + bb[0]['h'] for s in parts.values())
    in_holes, seen = True, 0
    for pl in lay['placements']:
        s = parts[pl['row']]
        for leg in pl['legs']:
            pin = next((p for p in base['pins'] if p['surface'] == s['id'] and p['label'] == leg['net']), None)
            if pin is None:
                continue   # a leg on an internal net (LED_ANODE) is not a pin of the pin view
            first = next(x for x in pl['legs'] if x['net'] == leg['net'])   # the first hole of a net stands for it
            hx, hy = S.hole_xy(geo, first['hole'])
            in_holes = in_holes and abs(s['x'] + pin['x'] - (bx0 + hx)) < 1e-3 and abs(s['y'] + pin['y'] - (by0 + hy)) < 1e-3
            seen += 1
    check('pv-6 BENCH PARTS: every bench part the layout places (%d: %s) sits INSIDE the breadboard with its frame at the centre of its legs and each of its pins (%d checked) in the hole the layout gives that leg; the surface names the holes' % (
          len(lay['placements']), ', '.join(p['row'] for p in lay['placements']), seen),
          inside and in_holes and seen >= 4 and set(parts) == {p['row'] for p in lay['placements']} and all('holes' in s['notes'] for s in parts.values()) and {p['part'] for p in bench['placed']} == set(parts)
          and bb[0]['x'] - bb[0]['w'] / 2 >= 66.04 + 2.54, str([(k, s['x'], s['y']) for k, s in parts.items()]))
    hole_geo = S.breadboard_geometry(30, 25)
    check('pv-6 GEOMETRY: the hole grammar of the layout view resolves (r1a = the first strip\'s top hole at the margin, r30j = the last, rail:top:+:1 and rail:bottom:-:25) and anything else (a header label) is None; the half board is 32 x 20.4 pitches',
          S.hole_xy(hole_geo, 'r1a') == (1.5 * 2.54, (1.5 + 1 + 2.2) * 2.54) and abs(S.hole_xy(hole_geo, 'r30j')[0] - (1.5 + 29) * 2.54) < 1e-9 and S.hole_xy(hole_geo, 'rail:top:+:1')[1] == 1.5 * 2.54
          and S.hole_xy(hole_geo, 'rail:bottom:-:25')[0] > S.hole_xy(hole_geo, 'rail:bottom:-:1')[0] and S.hole_xy(hole_geo, 'D6') is None and S.hole_xy(hole_geo, 'GND') is None
          and abs(hole_geo['w'] - 32 * 2.54) < 1e-9 and abs(hole_geo['h'] - 20.4 * 2.54) < 1e-9, str((hole_geo['w'], hole_geo['h'])))
    plain = PVM.build(t, BOARD)
    col = all(S.BENCH_REGION['x0'] <= s['x'] <= S.BENCH_REGION['x1'] for s in plain.surfaces if s['kind'] == 'bench-part')
    refused = PV.bench_layout('no-such-config@%s' % BOARD, BOARD)
    check('pv-6 FALLBACK: the model built without a layout has no breadboard surface and packs the bench parts into the bench column as before; a binding whose config the placer refuses yields no layout and says why in words (never a 500)',
          not any(s['kind'] == 'bench-board' for s in plain.surfaces) and col and refused[0] is None and refused[1].startswith('no layout for no-such-config'), refused[1])
    pos_ok = all(abs(pins['PackageContact:atmega328p-28-spdip:%d' % n]['x'] - next(q for q in ls['pins'] if q['number'] == n)['x']) < 1e-3 for n in (1, 12, 15, 28))
    check('MODEL: a package leg\'s position IS the generator\'s (surface-local mm), the die pads ring the die in the order of the legs they bond to, and the header pins come from the board shape\'s header rows at the cited 2.54 mm pitch (the top headers numbered right-to-left: D0 at the right edge)',
          pos_ok and abs(abs(pins['ConnectorPin:%s:DIGITAL_L:2' % BOARD]['x'] - pins['ConnectorPin:%s:DIGITAL_L:1' % BOARD]['x']) - 2.54) < 1e-3 and pins['ConnectorPin:%s:DIGITAL_L:1' % BOARD]['x'] > pins['ConnectorPin:%s:DIGITAL_H:1' % BOARD]['x'] and all(S.on_perimeter(p, {'w': 3.0, 'h': 3.0}) for p in base['pins'] if p['surface'].startswith('die:%s:U1' % BOARD)), '')
    ends_ok = all(c['a'] in pins and c['b'] in pins and c['a'] != c['b'] for c in base['connections'])
    check('CONNECTIONS: every connection is pin to pin — both ends resolve to a pin id (%d connections: %s); what ends nowhere (not-bonded pads, unused or consumed-only lines, the exposed pad) is listed in `unresolved` WITH its reason, never as a half connection' % (
          len(base['connections']), ', '.join('%d %s' % (v, k) for k, v in base['counts']['by_kind'].items())),
          ends_ok and base['unresolved'] and all(u['reason'] for u in base['unresolved']) and {c['kind'] for c in base['connections']} == {'pad-to-leg', 'to-header', 'on-board', 'chip-to-chip', 'to-board-part', 'to-bench'}
          and any('ADC6' in u['source'] or 'ADC6' in u['a'] for u in base['unresolved']), str(len(base['unresolved'])))
    d0 = _line(base, 'D0')
    d0c = [c for c in base['connections'] if c['a'] in d0 or c['b'] in d0]
    u2 = [c for c in d0c if c['kind'] == 'chip-to-chip']
    check('D0: its connections are the pad-to-leg, the leg-to-header and the U2 one — chip-to-chip to U2 leg 9 (PD3 / TXD1) with via "series resistor" through part RN4B (the value is NOT carried)',
          len(u2) == 1 and u2[0]['via'] == 'series resistor' and u2[0]['via_part'] == 'RN4B' and 'atmega16u2-32-qfn:9' in u2[0]['b'] and {c['kind'] for c in d0c} == {'pad-to-leg', 'to-header', 'chip-to-chip'}, str([c['kind'] for c in d0c]))
    sc = PV.build(BOARD, {'system': SYSTEM})
    leaks = [c['id'] for c in sc['connections'] if UNIT.search(json.dumps(c))]
    d0c2 = [c for c in sc['connections'] if c['a'] in _line(sc, 'D0') or c['b'] in _line(sc, 'D0')]
    check('NO NUMBERS: not one connection payload (all %d, with the light system\'s circuit checked) carries a number followed by mA / V / ohm / kOhm / nF ...; D0\'s connections especially' % len(sc['connections']),
          not leaks and d0c2 and not any(UNIT.search(json.dumps(c)) for c in d0c2), str(leaks[:3]))
    check('DRIVE vs SIGNAL: every connection has SEPARATE `drive`, `signal` and `use` keys; drive carries the electrical roles / rail / domain / pull / limit class (within-recommended | undetermined | over | unchecked), the signal carries outputs / inputs / bidirectional / passes and the family; the word "driv" appears in NO signal summary',
          all({'drive', 'signal', 'use'} <= set(c) for c in sc['connections']) and all(c['drive']['limit_verdict'] in ('within-recommended', 'undetermined', 'over', 'unchecked') for c in sc['connections'])
          and all(c['signal']['a'] in ('outputs', 'inputs', 'bidirectional', 'passes', 'none', 'undetermined') and 'driv' not in json.dumps(c['signal']).lower() for c in sc['connections'])
          and all({'a', 'b', 'rail', 'domain', 'pull', 'limit_verdict'} <= set(c['drive']) for c in sc['connections']) and not any(k in c['signal'] for c in sc['connections'] for k in ('rail', 'domain', 'pull', 'limit_verdict')), '')
    uart = [c for c in sc['connections'] if c['kind'] == 'chip-to-chip' and c['via_part'] == 'RN4B'][0]
    d6 = next(c for c in sc['connections'] if c['kind'] == 'to-header' and c['b'].endswith('DIGITAL_L:7'))
    check('SIGNAL: U1 RXD <-> U2 TXD1 reads "inputs / outputs" in the uart family with the signal pair named; the drive side of the same connection is a different object (both ends sources-and-sinks, logic-io domain)',
          uart['signal']['a'] == 'inputs' and uart['signal']['b'] == 'outputs' and uart['signal']['family'] == 'uart' and uart['signal']['function_a'] == 'RXD' and uart['signal']['function_b'] == 'TXD1'
          and uart['drive']['a'] == 'sources-and-sinks' and uart['drive']['domain'] == 'logic-io', str(uart['signal']))
    check('DRIVE: the limit class is READ from the electrical rules\' own findings — D6 (the LED line) is `undetermined` (the LED forward voltage is assumed, not cited: rule led_current), a pin no drive rule names is `unchecked`, and with NO system (no circuit) every connection is `unchecked` — never a silent ok',
          d6['drive']['limit_verdict'] == 'undetermined' and 'led_current' in d6['drive']['limit_basis'] and all(c['drive']['limit_verdict'] == 'unchecked' for c in base['connections']) and d6['drive']['a'] == 'sources-and-sinks',
          d6['drive']['limit_basis'])

    # ---- stages
    nproposed = lambda r: [p for p in r['pins'] if p['stage'] in ('proposed', 'committed')]   # noqa: E731
    check('STAGE base: zero proposed or committed pins and no task or Purpose consumer anywhere (everything is unassigned or available; available = reaches a header, from hsp-0 reachability); the stage block says what base means',
          not nproposed(base) and not [c for p in base['pins'] for c in p['consumers'] if c['kind'] in ('task', 'purpose')] and any(p['stage'] == 'available' for p in base['pins']) and base['stage']['stage'] == 'base'
          and any(p['stage'] == 'unassigned' for p in base['pins']) and 'chip blank' in base['stage']['notes'][0], str(len(nproposed(base))))
    ta = PV.build(BOARD, {'system': SYSTEM, 'binding': BINDING, 'stage': 'tasks-assigned'})
    prop = {p['canonical'] for p in ta['pins'] if p['stage'] == 'proposed' and p['canonical']}
    d2, d6l = _line(ta, 'D2'), _line(ta, 'D6')
    d3 = _line(ta, 'D3')
    check('STAGE tasks-assigned (binding %s): D2, D3 and D6 (and D0 / D1) are PROPOSED at every level (die pad, leg, header pin), with the claiming task and its Purpose as consumers; D3 is claimed by sense_init for the observe Purpose (smp-2: the sense line is in uno-light-graph); the response says it reads today\'s graph-node claims' % BINDING,
          prop == {'D0', 'D1', 'D2', 'D3', 'D6'} and all(ta['pins'][[p['id'] for p in ta['pins']].index(i)]['stage'] == 'proposed' for i in d2 | d6l | d3) and len(d2) == 3 and len(d6l) == 3 and len(d3) == 3
          and any(c['kind'] == 'task' and c['who'] == 'button_init' for p in ta['pins'] if p['canonical'] == 'D2' for c in p['consumers']) and any(c['kind'] == 'purpose' for p in ta['pins'] if p['canonical'] == 'D6' for c in p['consumers'])
          and all(any(c['kind'] == 'task' and c['who'] == 'sense_init' for c in p['consumers']) for p in ta['pins'] if p['canonical'] == 'D3') and 'graph-node claims' in ta['stage']['notes'][0] and ta['stage']['claims'] == 5, str(sorted(prop)))
    ai = PV.build(BOARD, {'system': SYSTEM, 'binding': BINDING, 'stage': 'after-init'})
    init_names = {c['who'] for p in ai['pins'] for c in p['consumers'] if c['kind'] == 'task'}
    fc = PV.build(BOARD, {'system': SYSTEM, 'binding': BINDING, 'stage': 'firmware-committed'})
    check('STAGE after-init / firmware-committed: after-init keeps only the claims of the Initialization Purpose\'s tasks (separable today: the Purpose names its tasks) and is a subset of tasks-assigned; firmware-committed marks as COMMITTED exactly the claims the binding\'s generated RegisterFieldSetting / SignalRoute rows cite (%d of %d), the rest stay proposed' % (fc['stage']['committed_claims'], fc['stage']['claims']),
          ai['stage']['claims'] > 0 and init_names <= {'usart_init', 'button_init', 'led_init', 'tick_init', 'boot_session_mint'} and {p['id'] for p in nproposed(ai)} <= {p['id'] for p in nproposed(ta)} and not ai['stage']['undetermined']
          and fc['stage']['committed_claims'] == 5 and {p['canonical'] for p in fc['pins'] if p['stage'] == 'committed' and p['canonical']} == {'D0', 'D1', 'D2', 'D3', 'D6'} and not nproposed(PV.build(BOARD, {'stage': 'base'})), str(init_names))
    nob = PV.build(BOARD, {'stage': 'tasks-assigned'})
    check('STAGE honesty: a stage that needs a binding asked without one says so (`undetermined` with the reason) and shows the base pins — never an invented assignment; a mission is echoed as undetermined (Task definitions on a Mission arrive with fgm-3)',
          nob['stage']['undetermined'] and not nproposed(nob) and PV.build(BOARD, {'mission': 'm1'})['mission']['status'] == 'undetermined', str(nob['stage']['undetermined']))

    # ---- the protocol filter (ladder-backed)
    sp = PV.build(BOARD, {'system': SYSTEM, 'protocol': 'spi'})
    lit_board = {p['canonical'] for p in sp['pins'] if p['level'] == 'board' and p['lit'] and p['canonical']}
    dim_board = {p['canonical'] for p in sp['pins'] if p['level'] == 'board' and p['dim'] and p['canonical']}
    d13 = [p for p in sp['pins'] if p['canonical'] == 'D13' and p['lit']]
    sys_row = SYS.rows(t)[0]
    ctx = Ctx(t, None, sys_row)
    ref = ctx.ladder('PB5', 'SCK', chip='atmega328p')
    ref_cond = {r['rung'] for r in ref['rungs'] if r['verdict'] == 'conditional'}
    got_cond = {c['rung'] for p in d13 for ch in p['lit']['children'] for c in ch['conditions'] if c['verdict'] == 'conditional'}
    check('PROTOCOL spi: lights D10 (SS), D11 (MOSI), D12 (MISO), D13 (SCK) on the board and DIMS the rest (D0-D9, A0-A5 ...); the lit pins carry the LADDER\'s verdict per child signal',
          {'D10', 'D11', 'D12', 'D13'} <= lit_board and not ({'D0', 'D1', 'D2', 'D3', 'D4', 'D5', 'D6', 'D7', 'D8', 'D9', 'A0', 'A1', 'A5'} & lit_board) and {'D0', 'D2', 'D9', 'A0'} <= dim_board
          and sp['protocol']['children'] == ['SCK', 'MOSI', 'MISO', 'SS'] and all(ch['verdict'] in ('available', 'conditional', 'blocked', 'undetermined') for p in sp['pins'] if p['lit'] for ch in p['lit']['children']), str(sorted(lit_board)))
    check('PROTOCOL spi: D13\'s condition is CARRIED from the ladder — the L LED buffer (rung 4 conditional) is the ladder\'s own answer for PB5 SCK (the same rungs, compared with the ladder run directly), not re-derived',
          d13 and 4 in ref_cond and ref_cond <= got_cond and any('L LED' in c['detail'] for p in d13 for ch in p['lit']['children'] for c in ch['conditions'])
          and all(ch['headline'].startswith('available with conditions') for p in d13 for ch in p['lit']['children']), str((sorted(ref_cond), sorted(got_cond))))
    u2lit = [p for p in sp['pins'] if p['soc'] == 'atmega16u2' and p['level'] == 'die' and p['lit']]
    blocked = [ch for p in u2lit for ch in p['lit']['children'] if ch['verdict'] == 'blocked']
    check('PROTOCOL spi: the 16U2\'s own SPI pins are lit too (able) and one that no header reaches shows WHY (blocked at the ladder\'s rung, with the reason) — a pin that cannot is dimmed, a pin that is able but blocked says where; an unknown protocol is refused',
          len(u2lit) >= 4 and blocked and all(ch['blocked_at'] > 0 and ch['blocked_why'] for ch in blocked) and _refuses(lambda: PV.build(BOARD, {'protocol': 'nope'})), str(len(u2lit)))
    ur = PV.build(BOARD, {'protocol': 'uart'})
    check('PROTOCOL family without children (uart is a set; analog is a family): analog lights A0-A5 (ADC) and dims D13; i2c lights SDA / SCL (A4 / A5 on both headers)',
          {'A0', 'A1', 'A2', 'A3', 'A4', 'A5'} <= {p['canonical'] for p in PV.build(BOARD, {'protocol': 'analog'})['pins'] if p['lit'] and p['canonical']} and 'D13' not in {p['canonical'] for p in PV.build(BOARD, {'protocol': 'analog'})['pins'] if p['lit']}
          and {'D0', 'D1'} <= {p['canonical'] for p in ur['pins'] if p['lit'] and p['canonical']}
          and {'A4', 'A5'} <= {p['canonical'] for p in PV.build(BOARD, {'protocol': 'i2c'})['pins'] if p['lit'] and p['canonical']}, '')

    # ---- the row views + pages + doors
    pr, cr, sr = PV.rows_payload(base, 'pins'), PV.rows_payload(base, 'connections'), PV.rows_payload(base, 'surfaces')
    check('ROWS: the three table views return rows with the same filters — pins %d, connections %d, surfaces %d (one row per pin / connection / surface); the level / surface / kind filters narrow them' % (pr['count'], cr['count'], sr['count']),
          pr['count'] == len(base['pins']) and cr['count'] == len(base['connections']) and sr['count'] == len(base['surfaces']) and PV.rows_payload(base, 'pins', {'level': 'board'})['count'] == 38
          and PV.rows_payload(base, 'connections', {'kind': 'chip-to-chip'})['count'] == 3 and all({'id', 'label', 'stage', 'families', 'drive_class'} <= set(r) for r in pr['rows']), '')
    check('ROWS: a pin row carries its pad class by NAME only (atmega328p:io-standard — no limit numbers), its families and its stage; a die pad\'s drive class is the SocPin\'s electrical_class',
          next(r for r in pr['rows'] if r['id'] == 'SocPin:atmega328p:PD6')['drive_class'] == 'atmega328p:io-standard' and 'pwm-timer' in next(r for r in pr['rows'] if r['id'] == 'SocPin:atmega328p:PD6')['families']
          and not any(UNIT.search(json.dumps(r['drive_class'])) for r in pr['rows']), '')
    from board.board_page import SEED_BOARD_PAGE_DISPLAYS as PAGES
    from board.pin_view_page import PIN_VIEW_PAGES
    mine = [p for p in PAGES if p['name'] in ('pin-view-pins', 'pin-view-connections', 'pin-view-surfaces')]
    items = [it for p in mine for r in json.loads(p['definition'])['rows'] for it in r['items']]
    check('PAGES: the three DisplayDefinitions exist (Pins, Connections, Surfaces) and are configured tables only — every item is a class-rows-table over a pin-view row door, none is an api-json-panel or a new component; their text says what a row is',
          len(mine) == 3 and len(PIN_VIEW_PAGES) == 5 and items and all(it['componentProps']['componentName'] == 'class-rows-table' for it in items)
          and all(it['componentProps']['inputs']['dataPath'].startswith('/api/board/%s/pin-view/' % BOARD) and it['description'].startswith('What this is for') for it in items)
          and not any('api-json-panel' in json.dumps(p['definition']) for p in mine), str(len(items)))
    view = next((p for p in PAGES if p['name'] == 'pin-view'), None)
    vitems = [it for r in json.loads(view['definition'])['rows'] for it in r['items']] if view else []
    check('PAGES (pv-1): /display/pin-view mounts exactly ONE item, the registered component hardware-pin-view (his explicit exception), with board / system / binding / stage inputs; it names its three table pages; no api-json-panel',
          view is not None and view['pageRoute'] == 'pin-view' and PIN_VIEW_PAGES[0] is view and len(vitems) == 1 and vitems[0]['componentProps']['componentName'] == 'hardware-pin-view'
          and set(vitems[0]['componentProps']['inputs']) == {'board', 'system', 'binding', 'stage'} and vitems[0]['componentProps']['inputs']['board'] == BOARD
          and all(r in view['description'] for r in ('/display/pin-view-pins', '/display/pin-view-connections', '/display/pin-view-surfaces')) and 'api-json-panel' not in view['definition'], '')
    from polariapps.apps_seed import SEED_POLARI_APPS as APPS
    nav = json.dumps([a for a in APPS if a['name'] == 'app-hardware'], default=str)
    check('NAV (pv-1): the Hardware home lists the Pin view FIRST in the "Pin data views" group, before the Pins table page',
          '/display/pin-view\\"' in nav and nav.index('/display/pin-view\\"') < nav.index('/display/pin-view-pins') and nav.index('Pin data views') < nav.index('/display/pin-view\\"'), '')
    check('NAV: the Hardware home links the three data pages in their own group ("Pin data views")', all(r in nav for r in ('/display/pin-view-pins', '/display/pin-view-connections', '/display/pin-view-surfaces', 'Pin data views')), '')

    # ---- the doors on a real falcon.App
    import falcon
    import falcon.testing as ft
    from board.board_endpoints import construct_board_endpoints
    tabs = {c: {r['name']: types.SimpleNamespace(**{f: r.get(f, '') for f in BO._fields(c)}) for r in rs} for c, rs in t.items() if c in BO.LAYER_CLASSES}
    _S = types.SimpleNamespace(falconServer=falcon.App(), manager=types.SimpleNamespace(objectTables=tabs, idList=[]))
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            construct_board_endpoints(_S)
        cl = ft.TestClient(_S.falconServer)
        v = cl.simulate_get('/api/board/%s/pin-view' % BOARD)
        v2 = cl.simulate_get('/api/board/%s/pin-view?system=%s&binding=%s&stage=tasks-assigned&protocol=spi' % (BOARD, SYSTEM, BINDING)).json
        rp = cl.simulate_get('/api/board/%s/pin-view/pins?level=board' % BOARD).json
        rc = cl.simulate_get('/api/board/%s/pin-view/connections?stage=base' % BOARD).json
        rs = cl.simulate_get('/api/board/%s/pin-view/surfaces' % BOARD).json
        bad_stage = cl.simulate_get('/api/board/%s/pin-view?stage=zz' % BOARD)
        bad_board = cl.simulate_get('/api/board/no-such-board/pin-view')
        bad_sys = cl.simulate_get('/api/board/%s/pin-view?system=nope' % BOARD)
        old = [cl.simulate_get(u).status_code for u in ('/api/board/%s/pins' % BOARD, '/api/board/%s/pins/D3' % BOARD, '/api/board/%s/exposure' % BOARD, '/api/board/%s/reachability' % BOARD,
                                                         '/api/board/%s/chain/D3' % BOARD, '/api/board/kit-parts', '/api/hardware-systems')]
        ok = v.status_code == 200 and v.json['ok'] and v.json['counts']['pins'] == len(base['pins']) and v2['ok'] and v2['stage']['stage'] == 'tasks-assigned' and v2['protocol']['protocol'] == 'spi' \
            and rp['ok'] and rp['count'] == 38 and rc['ok'] and rc['count'] == len(base['connections']) and rs['ok'] and rs['count'] == len(base['surfaces']) \
            and bad_stage.status_code == 400 and bad_board.status_code == 404 and bad_sys.status_code == 404 and old == [200] * 7
        why = str((v.status_code, old))
    except Exception as ex:   # a route clash raises UnacceptableRouteError at add time
        ok, why = False, repr(ex)
    check('DOORS: pin-view, pin-view/pins, /connections and /surfaces ADD on a real falcon.App beside every existing board route (pins, pins/{pin}, exposure, reachability, chain, kit-parts, hardware-systems — no UnacceptableRouteError) and answer; a bad stage is 400, an unknown board or system 404', ok, why)

    # ---- the CLI
    from board.custom.pin_view import main as cli
    with contextlib.redirect_stdout(io.StringIO()) as o1:
        a = cli(['surfaces', BOARD])
    with contextlib.redirect_stdout(io.StringIO()) as o2:
        b = cli(['pins', BOARD, '--stage', 'tasks-assigned', '--system', SYSTEM, '--binding', BINDING, '--json'])
    with contextlib.redirect_stdout(io.StringIO()) as o3:
        c = cli(['connections', BOARD, '--protocol', 'spi', '--system', SYSTEM])
    with contextlib.redirect_stdout(io.StringIO()):
        d = cli(['pins', BOARD, '--stage', 'bogus'])
    pj = json.loads(o2.getvalue())
    check('CLI: `python3 -m board.custom.pin_view surfaces|pins|connections <board> [--system --binding --stage --protocol] [--json]` run; --json is the row payload; a bad stage exits 1',
          a == b == c == 0 and d == 1 and 'board:%s' % BOARD in o1.getvalue() and pj['ok'] and any(r['stage'] == 'proposed' for r in pj['rows']) and 'chip-to-chip' in o3.getvalue(), '')


def _refuses(fn):
    try:
        fn()
    except ValueError:
        return True
    return False
