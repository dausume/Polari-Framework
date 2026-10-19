"""
Selftest — lay-0 / lay-1: the board family as objects, the extended tie-point grammar, wire colour schemes, the placer, THE NETLIST GATE and the build steps.

Run from polari-framework/:
    PYTHONPATH=.:modules python3 -m electrodevice.layout_selftest

THE ACCEPTANCE BAR (PROTOTYPING_VIEWS_PLAN section 3, BREADBOARD_BUILD_PLAN sections 3 and 6):
  - the half model has 400 ties and the full model 830, DERIVED from the geometry; protoboard and pcb are reserved; the older BreadboardDefinition rows are all still there and each has a BenchBoard;
  - the hole grammar r<N><a-j> and rail:<top|bottom>:<+|->:<N> compiles to the same nets as the older r<N>L/R; a devboard's header pins are its BoardPin rows;
  - the seeded wire colour scheme AGREES with the pin view's palette, a seeded scheme is copied before an edit, a wire's own colour is kept beside the derived one;
  - S1 (uno-light) lays out on the half breadboard and its layout nets EQUAL its design nets; a backwards LED and a missing series resistor are REFUSED in words naming the nets;
  - the steps are complete (every part and wire exactly once) and deterministic (same sha twice); a colour override shows in the step text.
Needs the board and cmod modules (the config, the BoardPin rows, the kit parts): without them the checks that read them SKIP honestly.
"""

import json
import os
import sys
import types

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

PASS, FAIL = '\033[0;32mPASS\033[0m', '\033[0;31mFAIL\033[0m'
_results = []


def check(label, cond, extra=''):
    _results.append(bool(cond))
    print(f'  [{PASS if cond else FAIL}] {label}{("  " + str(extra)[:300]) if (extra and not cond) else ""}')


def _manager():
    """A fake manager that holds real rows (the classes need idList + objectTables)."""
    return types.SimpleNamespace(objectTables={}, idList=[], db=None, noteTreeMutation=lambda *a, **k: None)


def _seeded_manager():
    """A manager holding the seeded layout rows, as the server's seed would."""
    from electrodevice import layout_basis as LB
    m = _manager()
    for cls, seeds in ((LB.BoardModel, LB.SEED_BOARD_MODELS), (LB.BenchBoard, LB.SEED_BENCH_BOARDS_ALL), (LB.WireColorScheme, LB.SEED_WIRE_COLOR_SCHEMES)):
        for s in seeds:
            cls(manager=m, **s)
    return m


def _have_board_modules():
    try:
        import board.custom.pv_families  # noqa: F401
        import cmod.custom.fsc_link  # noqa: F401
        return True
    except Exception:   # noqa: BLE001
        return False


# ------------------------------------------------------------------ lay-0 the family
def _family():
    print('lay-0: the board family')
    from electrodevice import layout_basis as LB
    from electrodevice.custom import board_family as BF
    from electrodevice.custom import layout_core as C
    from electrodevice.objects.breadboard._shared import SEED_BREADBOARDS
    models = BF.models()
    half, full = models['breadboard-half'], models['breadboard-full']
    check('half model: 30 rows x 10 holes + 4 rails x 25 = 400 ties, derived from the geometry', BF.derived_ties(half) == 400 == half.nominal_ties, BF.derived_ties(half))
    check('full model: 63 rows x 10 holes + 4 rails x 50 = 830 ties, derived from the geometry', BF.derived_ties(full) == 830 == full.nominal_ties, BF.derived_ties(full))
    check('pitch 2.54 mm on both (0.1 in)', half.pitch_mm == 2.54 == full.pitch_mm)
    check('only half and full breadboards exist for now (his answer)', sorted(m for m, r in models.items() if r.kind == 'breadboard') == ['breadboard-full', 'breadboard-half'])
    check('protoboard and pcb are RESERVED kinds with no geometry, said so', models['protoboard'].status == 'reserved' == models['pcb'].status
          and models['protoboard'].rows == 0 and 'no geometry' in models['pcb'].description)
    listing = C.boards_listing()
    check('the boards door lists models with derived ties agreeing', {m['name']: m['ties_agree'] for m in listing['models'] if m['kind'] == 'breadboard'} == {'breadboard-half': True, 'breadboard-full': True})
    names = {b['name'] for b in LB.SEED_BENCH_BOARDS_ALL}
    check('every older BreadboardDefinition seed has a BenchBoard of the same name (converged, no row lost)', {b['name'] for b in SEED_BREADBOARDS} <= names
          and all(b['migrated_from'] == 'BreadboardDefinition:%s' % b['name'] for b in LB.SEED_BENCH_BOARDS_ALL if b['name'] in {x['name'] for x in SEED_BREADBOARDS}))
    check('the default bench board is the half breadboard (the kit page does not say which)', LB.BENCH_DEFAULT == 'bench-half-1'
          and next(b for b in LB.SEED_BENCH_BOARDS_ALL if b['name'] == 'bench-half-1')['model_name'] == 'breadboard-half')
    m = _seeded_manager()
    check('the seeded rows build as real objects (BoardModel, BenchBoard, WireColorScheme)', len(m.objectTables['BoardModel']) == 5 and len(m.objectTables['WireColorScheme']) == 1
          and len(m.objectTables['BenchBoard']) == len(LB.SEED_BENCH_BOARDS_ALL))
    geo = BF.resolve(m, 'bb-demo-a')
    check('a migrated board resolves to the half geometry', geo is not None and geo.rows == 30 and geo.rail_holes == 25 and geo.kind == 'breadboard', vars(geo) if geo else None)
    check('a protoboard BenchBoard resolves as reserved', BF.resolve(_manager_with_board('b-proto', 'protoboard'), 'b-proto').reserved)


def _manager_with_board(name, model):
    from electrodevice import layout_basis as LB
    m = _seeded_manager()
    LB.BenchBoard(manager=m, name=name, model_name=model)
    return m


def _grammar():
    print('lay-0: the tie-point grammar')
    from electrodevice import breadboard_netlist_seed as bn
    from electrodevice.custom import board_family as BF
    board = BF.resolve(None, 'bench-half-1')
    net = lambda t: bn.tie_net(board, t)   # noqa: E731
    check('holes a-e of a strip are one net, the same as the older r<N>L', net('r5a') == net('r5e') == net('r5L') == 'bench_half_1_r5l')
    check('holes f-j of a strip are one net, the same as the older r<N>R, and not the left strip', net('r5f') == net('r5j') == net('r5R') == 'bench_half_1_r5r' and net('r5a') != net('r5f'))
    check('a rail hole is the net of the whole rail; top and bottom, + and - are four different nets', net('rail:top:-:1') == net('rail:top:-:25') and
          len({net('rail:top:+:1'), net('rail:top:-:1'), net('rail:bottom:+:1'), net('rail:bottom:-:1')}) == 4)
    check('the older vplus / gnd stay valid (gnd is SPICE ground 0)', net('gnd') == '0' and net('vplus') == 'bench_half_1_vplus')
    for bad, why in (('r31a', 'outside'), ('rail:top:-:26', 'outside'), ('r5k', 'tie point'), ('q9X', 'tie point')):
        try:
            bn._validate_tie(board, bad, "placement 'x'")
            ok = False
        except ValueError as exc:
            ok = why in str(exc) and "placement 'x'" in str(exc) or why == 'tie point'
        check('a bad tie %r is refused in words (%s)' % (bad, why), ok)
    full = BF.resolve(None, 'bench-full-1')
    try:
        bn._validate_tie(full, 'r63j', 'x')
        bn._validate_tie(full, 'rail:bottom:+:50', 'x')
        ok = True
    except ValueError:
        ok = False
    check('the full board reaches row 63 and rail hole 50', ok)
    if not _have_board_modules():
        print('  [SKIP] devboard header pins (the board module is not loaded)')
        return
    uno = BF.resolve(None, 'bench-uno-1')
    check('the UNO devboard: header pins are its BoardPin rows + the connector power labels', {'D6', 'D2', 'D3', 'A0', 'GND', '+5V'} <= set(uno.pins), sorted(uno.pins))
    check('a header pin is a net of the devboard, GND is ground 0, 5V and +5V are the same pin', bn.tie_net(uno, 'D6') == 'bench_uno_1_d6' and bn.tie_net(uno, 'GND') == '0'
          and bn.tie_net(uno, '5V') == bn.tie_net(uno, '+5V'))
    try:
        bn._validate_tie(uno, 'D99', "wire 'w'")
        ok = False
    except ValueError as exc:
        ok = "wire 'w'" in str(exc) and 'not a header pin' in str(exc)
    check('a pin the board does not have is refused naming the wire', ok)


# ------------------------------------------------------------------ colours
def _colours():
    print('lay-0: wire colour schemes')
    from electrodevice.custom import layout_colors as LCOL
    from electrodevice.layout_basis import SCHEME_DEFAULT, WIRE_COLOURS, colour_name_of_hex
    from electrodevice.custom.layout_words import LayoutRefused
    seeded = LCOL.get_scheme(None)
    check('the seeded default exists, is seeded, and says it is copied before an edit', seeded['name'] == SCHEME_DEFAULT and seeded['seeded'] and 'copy' in seeded['edit_words'])
    check('red = 5 V (supply) and black = GND', seeded['colors']['power'] == 'red' and seeded['colors']['ground'] == 'black')
    if _have_board_modules():
        fam = LCOL.families_table()
        derived = {f: colour_name_of_hex(h) for f, h in fam.items() if f not in ('power', 'ground')}
        check("every signal family's seeded colour equals the pin view's palette (pv_families.FALLBACK_HEX) named by its nearest wire colour", all(seeded['colors'][f] == c for f, c in derived.items()), derived)
        check("power and ground agree with the pin view too (its power red #c62828 -> red, its ground #424242 -> black)", colour_name_of_hex(fam['power']) == 'red' and colour_name_of_hex(fam['ground']) == 'black')
    else:
        print('  [SKIP] the agreement with the pin view palette (the board module is not loaded)')
    try:
        LCOL.set_colour(_seeded_manager(), SCHEME_DEFAULT, 'power', 'orange')
        ok = False
    except LayoutRefused as exc:
        ok = 'copy it first' in str(exc) and exc.status == 409
    check('editing the seeded scheme in place is refused with the copy words', ok)
    m = _seeded_manager()
    mine = LCOL.copy_scheme(m, 'my-bench', SCHEME_DEFAULT, {'power': 'orange'})
    check('a copy keeps every colour, takes the change, is yours (not seeded) and remembers its source', mine['colors']['power'] == 'orange' and mine['colors']['ground'] == 'black'
          and not mine['seeded'] and mine['copy_of'] == SCHEME_DEFAULT and mine['editable'])
    LCOL.set_colour(m, 'my-bench', 'ground', 'blue')
    check('a colour of your own scheme can be set in place; the seeded one is unchanged', LCOL.get_scheme(m, 'my-bench')['colors']['ground'] == 'blue' and LCOL.get_scheme(m)['colors']['ground'] == 'black')
    for bad in (lambda: LCOL.set_colour(m, 'my-bench', 'power', 'chartreuse'), lambda: LCOL.set_colour(m, 'my-bench', 'nonsense', 'red')):
        try:
            bad()
            ok = False
        except LayoutRefused as exc:
            ok = 'chartreuse' in str(exc) or 'not a colour key' in str(exc)
        check('a colour that is not a wire colour / a key that is not a key is refused in words', ok)
    wires = [{'name': 'a', 'class': 'ground'}, {'name': 'b', 'class': 'power'}, {'name': 'c', 'class': 'default'}]
    LCOL.colour_wires(wires, LCOL.get_scheme(m, 'my-bench'), {'b': 'yellow'})
    check("a wire's own colour is kept BESIDE the derived one: effective = override, else derived", (wires[0]['colour'], wires[0]['colour_effective']) == ('blue', 'blue')
          and (wires[1]['colour'], wires[1]['colour_override'], wires[1]['colour_effective']) == ('orange', 'yellow', 'yellow') and wires[1]['hex'] == WIRE_COLOURS['yellow'])


# ------------------------------------------------------------------ lay-1 S1
def _s1():
    print('lay-1: S1 (uno-light) on the half breadboard')
    from electrodevice.custom import layout_core as C
    from electrodevice.custom import layout_steps as LS
    r = C.layout_place('uno-light')
    v = r['verdict']
    print('  gate: ' + v['words'])
    check("S1's layout nets EQUAL its design nets (the gate verdict is OK, 4 nets compared)", v['ok'] and v['equal'] and v['nets_compared'] == 4 and not v['mismatches'], v['words'])
    check('the design nets are the circuit rows + the BoardPin refs: LED_CONTROL carries D6 and the sense pin, BUTTON_INPUT carries D2, GND carries the header GND',
          set(r['nets']) == {'LED_CONTROL', 'LED_ANODE', 'BUTTON_INPUT', 'GND'} and 'hdr:D6' in r['nets']['LED_CONTROL'] and 'hdr:D2' in r['nets']['BUTTON_INPUT'] and 'hdr:GND' in r['nets']['GND']
          and r['assignment']['sense'] in ('D3',) and 'hdr:%s' % r['assignment']['sense'] in r['nets']['LED_CONTROL'], r['nets'])
    sense = r['assignment']['sense']
    has_standin = bool(r['assignment']['standin'])
    print('  sense pin: %s (%s)' % (sense, 'STAND-IN from %s: uno-light has no sense line on this branch' % r['assignment']['standin'] if has_standin else "read from uno-light's own knobs"))
    check('the sense pin is read from the config at run time; a stand-in is named when the config has none yet', (not has_standin) or (r['assignment']['standin'] == 'uno-light-sense-poll'
          and any('STAND-IN' in n for n in r['notes'])), r['notes'])
    parts = {p['name']: p for p in r['placements']}
    check('the parts are the pushbutton, the 220 ohm series resistor and the LED', sorted(parts) == ['LED1', 'R1', 'SW1'] and parts['R1']['params'].get('ohms') == 220)
    sw = parts['SW1']
    check('the 4-leg pushbutton STRADDLES the trench: two legs left (a-e), two right (f-j), two rows apart', sw['straddles_trench'] and [l['side'] for l in sw['legs']] == ['L', 'L', 'R', 'R']
          and sw['legs'][1]['row'] - sw['legs'][0]['row'] == 2 and len(sw['internal']) == 2)
    led, res = parts['LED1'], parts['R1']
    check('the LED is anode-row -> series resistor -> cathode-row: the anode shares the resistor\'s far strip, the cathode is on the next row, both legs in one column',
          led['legs'][0]['row'] == res['legs'][1]['row'] and led['legs'][1]['row'] == led['legs'][0]['row'] + 1 and led['legs'][0]['col'] == led['legs'][1]['col'])
    check('the resistor spans rows (two leads, same column)', res['legs'][1]['row'] - res['legs'][0]['row'] == 4 and res['legs'][0]['col'] == res['legs'][1]['col'])
    by_w = {w['name']: w for w in r['wires']}
    check('rails first: the GND wire runs from the header GND to the top ground rail', r['wires'][0]['name'] == 'w-gnd-header' and r['wires'][0]['to']['tie'] == 'rail:top:-:1'
          and r['wires'][0]['from']['tie'] == 'GND')
    check('wires run header -> hole for D6, D2 and the sense pin, and strip -> rail for the two GND legs', {'w-d6', 'w-d2', 'w-%s' % sense.lower(), 'w-gnd-header'} <= set(by_w)
          and sum(1 for w in r['wires'] if w['name'].startswith('w-gnd-r')) == 2)
    check('colours come from the scheme: GND black; D6 takes the pin view colour of its family (orange)', by_w['w-gnd-header']['colour_effective'] == 'black' and by_w['w-d6']['colour_effective'] == 'orange'
          and by_w['w-d6']['colour_override'] == '', {k: w['colour_effective'] for k, w in by_w.items()})
    check('the electrical rules hold on S1 (polarity ok, series resistor ok)', {f['rule'] for f in v['findings'] if f['status'] == 'ok'} >= {'led-polarity', 'series-resistor'}
          and not [f for f in v['findings'] if f['status'] == 'refuse'])
    r2 = C.layout_place('uno-light')
    check('the layout is deterministic: the same sha twice', r['sha'] == r2['sha'] and r['steps_sha'] == r2['steps_sha'])
    steps = r['_steps']
    all_parts = [p for s in steps for p in s['adds']['parts']]
    all_wires = [w for s in steps for w in s['adds']['wires']]
    check('the steps are complete: every part and every wire appears in exactly one step', sorted(all_parts) == sorted(parts) and sorted(all_wires) == sorted(by_w)
          and len(set(all_parts)) == len(all_parts) and len(set(all_wires)) == len(all_wires))
    check('the steps run: 0 unplug, 1 the rails, then each part, then each wire, then the final check list',
          [s['kind'] for s in steps] == ['unplug', 'rails'] + ['part'] * 3 + ['wire'] * (len(by_w) - 1) + ['check'] and steps[-1]['checks'])
    grew = all(set(steps[i]['draw']['parts']) <= set(steps[i + 1]['draw']['parts']) and set(steps[i]['draw']['wires']) <= set(steps[i + 1]['draw']['wires']) for i in range(len(steps) - 1))
    union = all(steps[k]['draw']['parts'] == [p for s in steps[:k + 1] for p in s['adds']['parts']] and steps[k]['draw']['wires'] == [w for s in steps[:k + 1] for w in s['adds']['wires']] for k in range(len(steps)))
    check("step k's drawing data is steps 0..k (it only grows, and equals the union of what steps 0..k add)", grew and union)
    text = ' '.join(s['text'] for s in steps)
    check("the LED step says it in plain words: the longer leg (anode) in its row and hole", 'LONGER leg' in steps[4]['text'] and 'row %d, hole %s' % (led['legs'][0]['row'], led['legs'][0]['col']) in steps[4]['text'])
    check('the resistor step names its colour bands, computed from its value (220 -> red, red, brown)', 'red, red, brown' in text and LS.resistor_bands(4700) == ['yellow', 'violet', 'red'] and LS.resistor_bands(7) is None)
    print('  the walkthrough, first 6 lines:')
    for line in LS.walkthrough_lines(steps, 6):
        print('    ' + line)
    return r


# ------------------------------------------------------------------ the sense pin is read at run time
def _sense_at_runtime():
    print("lay-1: the sense pin is read from the config's knobs at run time (not hard-coded)")
    from electrodevice.custom import layout_core as C
    m = _manager()
    row = types.SimpleNamespace(name='uno-light-s8', title='test config', board_definition='arduino-uno-r3',
                                features_json=json.dumps({'led': True, 'pwm': False, 'adc': False, 'commands': True, 'button': True, 'sense': True}),
                                knobs_json=json.dumps({'rig_name': 'uno-light', 'led_pin': 6, 'button_pin': 2, 'sense_pin': 8, 'sense_route': 'pcint', 'debounce_ms': 30}))
    m.objectTables['FirmwareVariant'] = {'x': row}
    r = C.layout_place('uno-light-s8', manager=m)
    check("a config that carries the sense feature gets ITS OWN sense pin (D8), no stand-in", r['assignment']['sense'] == 'D8' and not r['assignment']['standin']
          and 'hdr:D8' in r['nets']['LED_CONTROL'] and any(w['name'] == 'w-d8' for w in r['wires']), r['assignment'])
    check('the layout nets still equal the design nets with the sense line on D8', r['verdict']['ok'], r['verdict']['words'])
    check('a difference from the circuit net rows (which list D3) is said, not silent', any('lists BoardPin(s)' in n and 'D8' in n for n in r['notes']), r['notes'])
    row.features_json = json.dumps({'led': True, 'pwm': False, 'adc': False, 'commands': True, 'button': True, 'sense': False})
    r2 = C.layout_place('uno-light-s8', manager=m)
    check('a config with no sense line and no stand-in has no sense wire (the unsensed build, F1)', r2['assignment']['sense'] is None and not any(w['name'] == 'w-d3' for w in r2['wires']) and r2['verdict']['ok'],
          r2['verdict']['words'])
    from electrodevice.custom.layout_words import LayoutRefused
    try:
        C.layout_place('uno-sim-rig')
        ok = False
    except LayoutRefused as exc:
        ok = 'circuit rows' in str(exc) or 'no part' in str(exc)
    check('a config whose parts have no circuit rows (the TMP36 rig) is refused in words, not guessed', ok)


# ------------------------------------------------------------------ the gate refuses
def _refusals():
    print('lay-1: the gate refuses a wrong build, in words')
    from electrodevice.custom import layout_core as C
    base = C.layout_place('uno-light')
    led = next(p for p in base['placements'] if p['name'] == 'LED1')
    a, c = led['legs'][0]['hole'], led['legs'][1]['hole']
    back = C.layout_place('uno-light', extra_edits=[{'name': 'e1', 'subject': 'part:LED1', 'field': 'holes', 'value': [c, a], 'who': 'test', 'note': '', 'created_at': ''}])
    print('  backwards LED: ' + back['verdict']['words'])
    check('a BACKWARDS LED is refused, the polarity named in words', not back['verdict']['ok'] and any(f['rule'] == 'led-polarity' and f['status'] == 'refuse' for f in back['verdict']['findings'])
          and 'IN BACKWARDS' in back['verdict']['words'] and 'anode' in back['verdict']['words'])
    check('...and the mismatching nets are named (LED_ANODE and GND)', {m['net'] for m in back['verdict']['mismatches']} >= {'LED_ANODE', 'GND'} and 'net LED_ANODE is wrong' in back['verdict']['words'],
          [m['net'] for m in back['verdict']['mismatches']])
    check("the edit sits BESIDE the derived value: the part says what the placer's holes were, the derived layout is unchanged", next(p for p in back['placements'] if p['name'] == 'LED1')['edit']['derived'] == [a, c]
          and C.layout_place('uno-light')['sha'] == base['sha'] and back['edits']['applied'] == ['e1'])
    ctl_row = int(base['strips']['LED_CONTROL'][1:-1])
    direct = C.layout_place('uno-light', extra_edits=[{'name': 'e2', 'subject': 'part:LED1', 'field': 'holes', 'value': ['r%dc' % ctl_row, c], 'who': 'test', 'note': '', 'created_at': ''}])
    print('  missing series resistor: ' + direct['verdict']['words'])
    check('a MISSING SERIES RESISTOR (the LED straight on the pin\'s strip) is refused in words', not direct['verdict']['ok'] and any(f['rule'] == 'series-resistor' and f['status'] == 'refuse' for f in direct['verdict']['findings'])
          and 'NO SERIES RESISTOR' in direct['verdict']['words'] and 'pin D6' in direct['verdict']['words'])
    check('...and it names the nets that no longer match (LED_ANODE, LED_CONTROL)', {m['net'] for m in direct['verdict']['mismatches']} >= {'LED_ANODE', 'LED_CONTROL'}, [m['net'] for m in direct['verdict']['mismatches']])
    off = C.layout_place('uno-light', extra_edits=[{'name': 'e3', 'subject': 'part:R1', 'field': 'holes', 'value': ['r99e', 'r11e'], 'who': 't', 'note': '', 'created_at': ''}])
    check('a hole off the board is refused in words, the layout still answers (not a 500)', not off['verdict']['ok'] and 'outside' in off['verdict']['words'], off['verdict']['words'])
    clash = C.layout_place('uno-light', extra_edits=[{'name': 'e4', 'subject': 'part:R1', 'field': 'holes', 'value': ['r11d', 'r12d'], 'who': 't', 'note': '', 'created_at': ''}])
    check('two legs in one hole is refused as HOLE IN USE', not clash['verdict']['ok'] and any(f['rule'] == 'hole-in-use' for f in clash['verdict']['findings']))
    shorted = C.layout_place('uno-light', extra_edits=[{'name': 'e5', 'subject': 'wire:w-d6', 'field': 'holes', 'value': ['D6', 'rail:top:-:2'], 'who': 't', 'note': '', 'created_at': ''}])
    check('a wire that puts the D6 output on the ground rail is refused as a SHORT', not shorted['verdict']['ok'] and 'SHORT' in shorted['verdict']['words'], shorted['verdict']['words'])
    for bad, why in ((dict(subject='part:ZZ9', field='holes', value=['r1a', 'r2a']), 'no part'), (dict(subject='part:LED1', field='holes', value=['r1a']), 'give 2 holes'),
                     (dict(subject='wire:w-d6', field='colour', value='mauve'), 'not a wire colour'), (dict(subject='thing:x', field='holes', value=[]), 'part:<ref> or wire:<name>')):
        from electrodevice.custom import layout_edits as LE
        from electrodevice.custom.layout_words import LayoutRefused
        try:
            LE.check_edit(base['_derived'], **bad)
            ok = False
        except LayoutRefused as exc:
            ok = why in str(exc)
        check('a malformed edit (%s) is refused in words' % why, ok)


# ------------------------------------------------------------------ edits kept, colour override in the steps, the doors
def _edits_and_doors():
    print('lay-1: edits kept beside the derived value, the doors')
    from electrodevice.custom import layout_core as C
    from electrodevice.custom import layout_edits as LE
    m = _seeded_manager()
    base = C.layout_place('uno-light', manager=m)
    LE.record(m, 'uno-light', 'bench-half-1', base['_derived'], 'wire:w-d6', 'colour', 'green', who='dustin', note='my orange ran out')
    r = C.layout_place('uno-light', manager=m)
    w6 = next(w for w in r['wires'] if w['name'] == 'w-d6')
    check('a wire colour override is kept beside the derived colour (orange derived, green effective)', (w6['colour'], w6['colour_override'], w6['colour_effective']) == ('orange', 'green', 'green'))
    step = next(s for s in r['_steps'] if 'w-d6' in s['adds']['wires'])
    check('the override shows in the step text, with the derived colour named beside it', 'a green wire' in step['text'] and 'would use orange' in step['text'], step['text'])
    check('a colour override does not change the nets: the gate still says OK, and the placement sha is the placer\'s', r['verdict']['ok'] and r['edits']['applied'])
    LE.record(m, 'uno-light', 'bench-half-1', base['_derived'], 'wire:w-d6', 'colour', None, clear=True)
    check('clearing the edit returns to the derived colour', next(w for w in C.layout_place('uno-light', manager=m)['wires'] if w['name'] == 'w-d6')['colour_effective'] == 'orange')
    from electrodevice.layout_api import LayoutAPI

    class Req:
        def __init__(self, params=None, body=None):
            self.params = params or {}
            self.bounded_stream = types.SimpleNamespace(read=lambda: json.dumps(body or {}).encode())

        def get_param(self, k):
            return self.params.get(k)
    api = LayoutAPI(polServer=None, manager=m)
    resp = lambda: types.SimpleNamespace(media=None, status='200 OK')   # noqa: E731
    r1 = resp()
    api.on_get_boards(Req(), r1)
    check('door GET /api/layout/boards: models, boards, defaults', r1.media['ok'] and len(r1.media['models']) == 5 and r1.media['default_board'] == 'bench-half-1')
    r2 = resp()
    api.on_get_layout(Req(), r2, 'uno-light')
    check('door GET /api/layout/<config>: placements, wires, nets and the verdict (no private keys sent)', r2.media['ok'] and r2.media['verdict']['ok'] and r2.media['placements'] and not any(k.startswith('_') for k in r2.media))
    r3 = resp()
    api.on_get_steps(Req({'board': 'bench-half-1'}), r3, 'uno-light')
    check('door GET /api/layout/<config>/steps: the steps and the walkthrough lines', r3.media['ok'] and len(r3.media['steps']) == len(r3.media['walkthrough']) and r3.media['sha'] == r2.media['steps_sha'])
    r4 = resp()
    api.on_post_edit(Req(body={'subject': 'part:LED1', 'field': 'holes', 'value': ['r12d', 'r11d'], 'who': 'dustin', 'dry_run': True}), r4, 'uno-light')
    check('door POST /edit dry_run: the verdict of the edit without keeping it', r4.media['ok'] and r4.media['dry_run'] and not r4.media['verdict']['ok'] and not any(e.subject == 'part:LED1' for e in m.objectTables.get('LayoutEdit', {}).values()))
    r5 = resp()
    api.on_post_edit(Req(body={'subject': 'part:LED1', 'field': 'holes', 'value': ['r12d', 'r11d'], 'who': 'dustin', 'note': 'testing'}), r5, 'uno-light')
    check('door POST /edit keeps the edit and re-gates (refused in words)', not r5.media['verdict']['ok'] and r5.media['edit']['subject'] == 'part:LED1' and 'IN BACKWARDS' in r5.media['verdict']['words'])
    r6 = resp()
    api.on_get_layout(Req(), r6, 'uno-light')
    check('the kept edit is applied on the next GET', not r6.media['verdict']['ok'] and r6.media['edits']['applied'])
    r7 = resp()
    api.on_post_edit(Req(body={'subject': 'part:LED1', 'field': 'holes', 'clear': True}), r7, 'uno-light')
    check('door POST /edit clear: back to the derived layout, gate OK', r7.media['verdict']['ok'] and not r7.media['edits']['applied'])
    r8 = resp()
    api.on_post_edit(Req(body={'subject': 'part:LED1', 'field': 'holes', 'value': 'nope'}), r8, 'uno-light')
    check('door POST /edit with a bad value: 422 in words', r8.status.startswith('422') and 'give 2 holes' in r8.media['error'], r8.media)
    r9 = resp()
    api.on_get_layout(Req(), r9, 'no-such-config')
    check('door GET with an unknown config: 404 naming the known configs', r9.status.startswith('404') and 'uno-light' in r9.media['error'])
    r10 = resp()
    api.on_get_layout(Req({'board': 'protoboard'}), r10, 'uno-light')
    check('door GET on a reserved board kind: refused in words', not r10.media['ok'] and ('reserved' in r10.media['error'] or 'no board' in r10.media['error']), r10.media)
    r11 = resp()
    api.on_get_colors(Req(), r11)
    check('door GET /wire-colors: the seeded scheme and the colour names', r11.media['ok'] and r11.media['rows'][0]['seeded'] and {c['name'] for c in r11.media['colours']} >= {'red', 'black'})
    r12 = resp()
    api.on_post_colors(Req(body={'name': 'wires-pin-view', 'set': {'power': 'blue'}}), r12)
    check('door POST /wire-colors on the seeded scheme: refused (copy first)', r12.status.startswith('409') and 'copy' in r12.media['error'])
    r13 = resp()
    api.on_post_colors(Req(body={'name': 'bench2', 'copy_of': 'wires-pin-view', 'colors': {'ground': 'brown'}}), r13)
    r14 = resp()
    api.on_get_layout(Req({'scheme': 'bench2'}), r14, 'uno-light')
    check('door POST /wire-colors copies, and the layout then draws in the copy\'s colours', r13.status.startswith('201') and r14.media['scheme'] == 'bench2'
          and next(w for w in r14.media['wires'] if w['name'] == 'w-gnd-header')['colour_effective'] == 'brown')


# ------------------------------------------------------------------ the placer on parts S1 does not use
def _three_lead():
    print('lay-1: the placer on a TMP36 and a transistor (a synthetic design, to prove the rules)')
    from electrodevice.custom import board_family as BF
    from electrodevice.custom import layout_gate as LG
    from electrodevice.custom import layout_place as LP
    geo = BF.resolve(None, 'bench-half-1')

    def comp(ref, kind, terms, **kw):
        return dict({'ref': ref, 'row': ref.lower(), 'kind': kind, 'kit_key': kind, 'kit_part': {}, 'params': {}, 'job': '', 'terminals': [{'id': '%s.%s' % (ref, n), 'name': n, 'net': net} for n, net in terms]}, **kw)
    design = {'config': 'synthetic', 'circuit': 'synthetic', 'ground_net': 'GND', 'supply_nets': ['5V'],
              'components': [comp('U1', 'tmp36', [('vs', '5V'), ('out', 'TEMP'), ('gnd', 'GND')]), comp('Q1', 'transistor', [('emitter', 'GND'), ('base', 'BASE'), ('collector', 'LOAD')])],
              'attach': {'TEMP': [{'pin': 'A0', 'role': 'input'}], 'BASE': [{'pin': 'D6', 'role': 'output'}], '5V': [{'pin': '+5V', 'role': 'supply'}], 'GND': [{'pin': 'GND', 'role': 'ground'}]}}
    design['nets'] = {'5V': ['U1.vs', 'hdr:+5V'], 'TEMP': ['U1.out', 'hdr:A0'], 'GND': ['U1.gnd', 'Q1.emitter', 'hdr:GND'], 'BASE': ['Q1.base', 'hdr:D6'], 'LOAD': ['Q1.collector']}
    laid = LP.place(design, geo, 'bench-uno-1')
    u1 = next(p for p in laid['placements'] if p['name'] == 'U1')
    q1 = next(p for p in laid['placements'] if p['name'] == 'Q1')
    rows = [l['row'] for l in u1['legs']]
    check('a TMP36 takes THREE adjacent rows of one column, +Vs / Vout / GND flat face toward the reader', rows == [rows[0], rows[0] + 1, rows[0] + 2] and len({l['col'] for l in u1['legs']}) == 1
          and [l['name'] for l in u1['legs']] == ['vs', 'out', 'gnd'])
    rows = [l['row'] for l in q1['legs']]
    check('a transistor goes E-B-C in three adjacent rows', rows == [rows[0], rows[0] + 1, rows[0] + 2] and [l['name'] for l in q1['legs']] == ['emitter', 'base', 'collector'])
    check('the supply rail is wired from the header +5V to the top + rail, rails first', laid['wires'][0]['name'] in ('w-5v-header', 'w-gnd-header') and any(w['name'] == 'w-5v-header' and w['to']['tie'] == 'rail:top:+:1' for w in laid['wires']))
    if _have_board_modules():
        v = LG.gate(None, design, laid, 'bench-half-1', 'bench-uno-1')
        check('the gate accepts it: the layout nets equal the design nets for the 3-lead parts (a kind "part" placement, no SPICE element)', v['equal'], v['words'])
    try:
        LP.place(design, BF.resolve(_manager_with_board('b-proto', 'protoboard'), 'b-proto'), 'bench-uno-1')
        ok = False
    except Exception as exc:   # noqa: BLE001
        ok = 'reserved' in str(exc) or 'breadboards' in str(exc)
    check('placing on a reserved board kind is refused in words', ok)


def run_checks():
    if not _have_board_modules():
        print('SKIP: the board / cmod modules are not importable here: the layout of a built config needs them')
    _family()
    _grammar()
    _colours()
    if _have_board_modules():
        _s1()
        _sense_at_runtime()
        _refusals()
        _edits_and_doors()
        _three_lead()


def main():
    run_checks()
    passed, total = sum(_results), len(_results)
    print(f'\n{passed}/{total} checks passed')
    return 0 if passed == total else 1


if __name__ == '__main__':
    sys.exit(main())
