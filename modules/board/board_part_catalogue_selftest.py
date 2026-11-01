"""board_part_catalogue_selftest - drv-2 / drv-3 / drv-4 / drv-5 (AI-Notes/plans/DRIVERS_AND_ESD_PLAN.md; D-drv-2's order: a TTL-input 3.3 -> 5 V buffer, a constant-current
LED driver, an LDO, a buck). The four cited parts (TI SCLS264R SN74AHCT125, SLVS695D TLC5916, SNOS412Q LM1117, SNVS124G LM2596), pin-level numbers,
converters on the Bench (a regulated output is a supply; a regulator's input has a minimum), the fixes judged against every cited number, whole-part
budgets, and the clean placements the page's "Mount here" rows offer.
The loads below are SYNTHETIC test parts (no real product is named or implied). Run by board_selftest.main().
"""
import contextlib
import json
import os
import types


def _load(ma):
    """synthetic: a two-pin load that draws `ma` from whatever feeds pin 1 - not a real part."""
    return {'name': 'test-load-%gma' % ma, 'kind': 'load', 'draw_ma': float(ma),
            'pins': [{'number': 1, 'name': 'IN', 'role': 'in', 'x_mm': 0, 'y_mm': 0}, {'number': 2, 'name': 'RET', 'role': 'nc', 'x_mm': 2.54, 'y_mm': 0}]}


def _fresh():
    from board.custom import part_boards as PB
    PB._MEM[PB.CLS].clear()
    return PB


def _feet(*keys):
    from board.custom import footholds as FH
    return [FH.for_definition(*k)[0] for k in keys]


def _by(feet):
    return {f['foothold']: f for f in feet}


def run_cited_catalogue(check):
    PB = _fresh()
    cat = {r['name']: r for r in PB.catalogue()}
    ahct, tlc, ldo, buck = (_by(f) for f in _feet(('part', 'sn74ahct125-n'), ('part', 'tlc5916-n'), ('part', 'lm1117t-3.3'), ('part', 'lm2596t-5.0')))
    check('DRV-2 FOUR MORE CITED PARTS, D-drv-2\'s order: the SN74AHCT125 (SCLS264R: TTL inputs on from 2 V on a 4.5 - 5.5 V supply, drives 8 mA high to '
          '3.8 V), the TLC5916 (SLVS695D: eight 120 mA sinks, inputs on from 0.7 VDD = 3.5 V at 5 V, needs R-EXT), the LM1117-3.3 (SNOS412Q: 3.3 V at '
          '800 mA, input from 3.3 + 1.3 V dropout = 4.6 V) and the LM2596-5.0 (SNVS124G: 5 V at 3 A from 7 - 40 V) - every one cited, the LDO and buck '
          'described as converters',
          {'sn74ahct125-n', 'tlc5916-n', 'lm1117t-3.3', 'lm2596t-5.0', 'uln2003a-n'} <= set(cat) and all(cat[k]['origin'] == 'cited' for k in cat)
          and (cat['sn74ahct125-n']['on_volts'], cat['sn74ahct125-n']['out_volts'], cat['sn74ahct125-n']['out_source_ma']) == (2.0, 3.8, 8.0)
          and (cat['tlc5916-n']['on_volts'], cat['tlc5916-n']['out_sink_ma'], cat['tlc5916-n']['total_ma']) == (3.5, 120.0, 960.0)
          and 'R-EXT' in cat['tlc5916-n']['needs'] and cat['lm1117t-3.3']['contract'].startswith('out: 3.3 V at up to 800 mA; in: 4.6 V')
          and cat['lm2596t-5.0']['contract'].startswith('out: 5 V at up to 3000 mA; in: 7 V') and 'SNVS124G' in cat['lm2596t-5.0']['document'],
          {k: r['contract'][:60] for k, r in cat.items()})
    check('DRV-2 PIN-LEVEL NUMBERS: the TLC5916\'s SDO sources / sinks 1 mA, not its outputs\' 120 mA; the AHCT125\'s VCC turns on from 4.5 V and takes 7 V; '
          'the LM1117\'s VOUT is a 3.3 V supply giving 800 mA, its VIN needs 4.6 V and takes 20 V; the bare LM2596 has no regulated pin (Output is the '
          'switch node) and says what it needs; DIP pins sit on the 2.54 / 7.62 mm grid, the TO-220-5 on its 1.7 mm stagger',
          (tlc['14']['source_ma'], tlc['14']['sink_ma'], tlc['5']['sink_ma']) == (1.0, 1.0, 120.0) and (ahct['14']['on_volts'], ahct['14']['max_volts']) == (4.5, 7.0)
          and (ldo['2']['direction'], ldo['2']['rail_volts'], ldo['2']['source_ma']) == ('supply', 3.3, 800.0)
          and (ldo['3']['on_volts'], ldo['3']['max_volts'], ldo['3']['rail_volts']) == (4.6, 20.0, -1.0)
          and not any(f['direction'] == 'supply' and f['rail_volts'] > 0 for f in buck.values()) and buck['2']['direction'] == 'passive'
          and 'NO regulated pin' in cat['lm2596t-5.0']['needs'] and ahct['8']['x_mm'] == 15.24 and ahct['8']['y_mm'] == 0.0 and buck['2']['x_mm'] == 1.7,
          (tlc['14'], ldo['3']))


def run_converters_and_fixes(check):
    from board.custom import bench_nets as BN
    PB = _fresh()
    for ma in (300, 400):
        PB.define(None, _load(ma))
    PB.define(None, {'name': 'test-3v6-input', 'kind': 'module', 'on_volts': 1.0, 'in_max_v': 3.6,
                     'pins': [{'number': 1, 'name': 'IN', 'role': 'in', 'x_mm': 0, 'y_mm': 0}]})
    uno, c3, tlc, ldo, load300, part36 = _feet(('datasheet', 'arduino-uno-r3'), ('datasheet', 'esp32-c3'), ('part', 'tlc5916-n'), ('part', 'lm1117t-3.3'),
                                               ('part', 'test-load-300ma'), ('part', 'test-3v6-input'))
    io = next(f['foothold'] for f in c3 if f['direction'] == 'inout' and f['logic_volts'] == 3.3)
    v33 = next(f['foothold'] for f in uno if f['direction'] == 'supply' and f['rail_volts'] == 3.3)
    five = next(f['foothold'] for f in uno if f['label'] == '+5V')
    under, _ = BN.nets({'c3': c3, 'tlc': tlc}, [{'from_board': 'c3', 'from_foothold': io, 'to_board': 'tlc', 'to_foothold': '2'}])
    uv = [f for n in under for f in n['findings']]
    fix = {s['part']: s for s in PB.suggestions(under)}
    check('DRV-2 A 3.3 V PIN DOES NOT REACH A 5 V LED DRIVER: the C3\'s 3.3 V into the TLC5916\'s SDI (on from 3.5 V at VDD 5 V) is under-voltage, with '
          'both numbers; the fix is the AHCT125 - on from 2 V (reached), driving high to 3.8 V (above the 3.5 V needed) - and it fits',
          [f['kind'] for f in uv] == ['under-voltage'] and (uv[0]['on_volts'], uv[0]['driven_volts']) == (3.5, 3.3) and fix['sn74ahct125-n']['fits']
          and '3.8 V' in fix['sn74ahct125-n']['why'], (uv, fix))
    over, _ = BN.nets({'uno': uno, 'p': part36}, [{'from_board': 'uno', 'from_foothold': five, 'to_board': 'p', 'to_foothold': '1'}])
    ofix = PB.suggestions(over)
    check('DRV-2 THE FIX IS JUDGED, NOT LISTED: 5 V into a part that takes 3.6 V - the AHCT125 is an UP-shifter (it drives high to 3.8 V, above 3.6 V), so '
          'it is shown as NOT fitting; since drv-4 the LVC245A (5.5 V inputs on a 3.3 V supply) fits, so no "no part fits" row',
          any(s['part'] == 'sn74ahct125-n' and not s['fits'] and 'does NOT bring the level down' in s['why'] for s in ofix)
          and any(s['part'] == 'sn74lvc245a-n' and s['fits'] for s in ofix) and not any(s['part'] == '' for s in ofix), ofix)
    vin, _ = BN.nets({'uno': uno, 'ldo': ldo}, [{'from_board': 'uno', 'from_foothold': v33, 'to_board': 'ldo', 'to_foothold': '3'}])
    starve, _ = BN.nets({'uno': uno, 'm': load300}, [{'from_board': 'uno', 'from_foothold': v33, 'to_board': 'm', 'to_foothold': '1'}])
    sv = [f for n in starve for f in n['findings']]
    sfix = {s['part']: s for s in PB.suggestions(starve)}
    fed, _ = BN.nets({'ldo': ldo, 'm': load300}, [{'from_board': 'ldo', 'from_foothold': '2', 'to_board': 'm', 'to_foothold': '1'}])
    check('DRV-2 CONVERTERS ON THE BENCH: the UNO\'s 3.3 V into the LM1117\'s VIN is under-voltage (it needs 4.6 V); the UNO\'s 3V3 pin (50 mA, cited) '
          'feeding a 300 mA load is a drive-shortfall from a supply - the fix is the LM1117 (3.3 V, 800 mA: fits), the LM2596 shown as NOT fitting (5 V, '
          'and the bare chip needs its inductor); fed from the LM1117\'s VOUT the same load is clean',
          [f['kind'] for n in vin for f in n['findings']] == ['under-voltage'] and [f['kind'] for f in sv] == ['drive-shortfall'] and sv[0]['from_supply']
          and (sv[0]['need_ma'], sv[0]['can_ma']) == (300.0, 50.0) and sfix['lm1117t-3.3']['fits'] and not sfix['lm2596t-5.0']['fits']
          and 'NOT the net' in sfix['lm2596t-5.0']['why'] and not [f for n in fed for f in n['findings']], (sv, sfix, fed))
    _fresh()


def run_down_shift_and_module(check):
    from board.custom import bench_mount as M
    from board.custom import bench_nets as BN
    PB = _fresh()
    cat = {r['name']: r for r in PB.catalogue()}
    lvc_feet, mod_feet, bb = _feet(('part', 'sn74lvc245a-n'), ('part', 'lm2596-5.0-module'), ('geometry', 'breadboard-half'))
    lvc, mod = _by(lvc_feet), _by(mod_feet)
    check('DRV-4 THE DOWN-SHIFTER (TI SCAS218X SN74LVC245A, PDIP-20): inputs on from 2 V and taking 5.5 V on a 1.65 - 3.6 V supply, 24 mA out, high to '
          '2.1 V at 24 mA, never above VCC + 0.5 = 3.8 V; A1..A8 are pins 2..9 (in), B1..B8 pins 18..11 (out), DIR 1 / OE 19 control inputs, VCC 20 takes '
          '6.5 V - every number cited',
          cat['sn74lvc245a-n']['origin'] == 'cited' and 'SCAS218X' in cat['sn74lvc245a-n']['document']
          and (cat['sn74lvc245a-n']['on_volts'], cat['sn74lvc245a-n']['in_max_v'], cat['sn74lvc245a-n']['out_volts'], cat['sn74lvc245a-n']['out_max_v'])
          == (2.0, 5.5, 2.1, 3.8) and (lvc['2']['label'], lvc['2']['direction'], lvc['18']['label'], lvc['18']['direction']) == ('A1', 'in', 'B1', 'out')
          and lvc['11']['label'] == 'B8' and (lvc['20']['on_volts'], lvc['20']['max_volts']) == (1.65, 6.5) and lvc['19']['draw_ma'] == 0.01,
          (cat['sn74lvc245a-n']['contract'], lvc['20']))
    uno, c3 = _feet(('datasheet', 'arduino-uno-r3'), ('datasheet', 'esp32-c3'))
    io = next(f['foothold'] for f in c3 if f['direction'] == 'inout' and f['logic_volts'] == 3.3)
    over, _ = BN.nets({'uno': uno, 'c3': c3}, [{'from_board': 'uno', 'from_foothold': 'DIGITAL_L:7', 'to_board': 'c3', 'to_foothold': io}])
    fix = {s['part']: s for s in PB.suggestions(over)}
    check('DRV-4 A 5 V PIN INTO A 3.3 V ONE: the UNO\'s DIGITAL_L:7 into the ESP32-C3 is over-voltage (5 V on a 3.3 V pin); the LVC245A fits (takes 5.5 V, '
          'drives 2.1 V), the AHCT125 does not (it drives 3.8 V)',
          [f['kind'] for n in over for f in n['findings']] == ['over-voltage'] and fix['sn74lvc245a-n']['fits'] and not fix['sn74ahct125-n']['fits'],
          fix)
    PB.define(None, {'name': 'test-5v-500ma', 'kind': 'module', 'out_volts': 5.0, 'out_source_ma': 500.0,
                     'pins': [{'number': 1, 'name': 'OUT', 'role': 'regulated', 'x_mm': 0, 'y_mm': 0}]})
    PB.define(None, _load(2000))
    sup, load = _feet(('part', 'test-5v-500ma'), ('part', 'test-load-2000ma'))
    starve, _ = BN.nets({'s': sup, 'm': load}, [{'from_board': 's', 'from_foothold': '1', 'to_board': 'm', 'to_foothold': '1'}])
    sfix = {s['part']: s for s in PB.suggestions(starve)}
    fed, _ = BN.nets({'b': mod_feet, 'm': load}, [{'from_board': 'b', 'from_foothold': '4', 'to_board': 'm', 'to_foothold': '1'}])
    spots = M.placements(mod_feet, bb, limit=400)
    check('DRV-5 THE BUCK AS A BENCH BOARD (SNVS124G §9.2.1\'s own design round the LM2596-5.0: 33 uH, 330 uF, 1N5823, 680 uF): 5 V at 3 A from 7 - 12 V '
          '(the design\'s own maximum), VOUT a regulated supply; a 500 mA (synthetic) 5 V supply feeding a 2 A load is a shortfall whose fix is the '
          'module (fits) and not the bare chip (needs its inductor); fed from the module the load is clean; its chosen 2.54 mm header lands on the '
          'breadboard (Mount here offers spots)',
          (mod['4']['direction'], mod['4']['rail_volts'], mod['4']['source_ma'], mod['1']['on_volts'], mod['1']['max_volts']) == ('supply', 5.0, 3000.0, 7.0, 12.0)
          and cat['lm2596-5.0-module']['contract'].startswith('out: 5 V at up to 3000 mA; in: 7 V .. 12 V') and 'CHOSEN' in cat['lm2596-5.0-module']['position_basis']
          and sfix['lm2596-5.0-module']['fits'] and not sfix['lm2596t-5.0']['fits'] and not [f for n in fed for f in n['findings']] and len(spots) > 0,
          (sfix, fed, len(spots)))
    _fresh()


def run_budgets_and_placements(check):
    from board.custom import bench_mount as M
    from board.custom import bench_nets as BN
    PB = _fresh()
    PB.define(None, _load(400))
    uln, load, bb, buck = _feet(('part', 'uln2003a-n'), ('part', 'test-load-400ma'), ('geometry', 'breadboard-half'), ('part', 'lm2596t-5.0'))
    boards = dict({'uln': uln}, **{'m%d' % k: load for k in range(1, 8)})
    outs = sorted((f for f in uln if f['direction'] == 'out'), key=lambda f: int(f['foothold']))
    nets, _ = BN.nets(boards, [{'from_board': 'uln', 'from_foothold': f['foothold'], 'to_board': 'm%d' % k, 'to_foothold': '1'}
                               for k, f in enumerate(outs, 1)])
    b = PB.budgets(nets)
    rows = PB.suggestions(nets)
    check('DRV-3 A WHOLE-PART BUDGET: seven 400 mA loads on the ULN2003A\'s seven outputs are each fine pin by pin (400 of 500 mA) but 2800 mA in all is '
          'above its 2.5 A total emitter current (§5.1) - one budget row, over, and a group-budget fix (split the load) beside no per-net finding',
          not [f for n in nets for f in n['findings']] and len(b) == 1 and (b[0]['need_ma'], b[0]['total_ma'], b[0]['over']) == (2800.0, 2500.0, True)
          and [r['finding'] for r in rows] == ['group-budget'] and 'second uln2003a-n' in rows[0]['why'], (b, rows))
    spots = M.placements(uln, bb, limit=200)
    check('DRV-2 WHERE IT FITS (the page\'s Mount here rows): the ULN2003A on a half breadboard fits in 46 places - 23 columns straddling the trench, '
          'upright or turned 180 degrees - the selftest\'s hand-placed straddle among them, and no place with its rows on one side; the 1.7 mm-pitch '
          'LM2596 fits nowhere',
          len(spots) == 46 and {s['rotation'] for s in spots} == {0, 180} and any(abs(s['x_mm'] - 26.67) < 1e-6 and abs(s['y_mm'] - 22.098) < 1e-6 for s in spots)
          and all(not M.landings(uln, bb, s['x_mm'], s['y_mm'], s['rotation'])['joined'] for s in spots) and M.placements(buck, bb) == [],
          (len(spots), spots[:2]))
    _fresh()


def run_catalogue_doors(check):
    import falcon
    import falcon.testing as ft
    from board.bench_parts_api import BenchPartsAPI
    from board.bench_page import BENCH_PAGES
    _fresh()
    app = falcon.App()
    with contextlib.redirect_stdout(open(os.devnull, 'w')):
        BenchPartsAPI(polServer=types.SimpleNamespace(falconServer=app), manager=None)
    cl = ft.TestClient(app)
    pick = cl.simulate_get('/api/board/benches/home-bench/mount-options')
    unknown = cl.simulate_get('/api/board/benches/home-bench/mount-options', params={'child': 'nope'})
    nobench = cl.simulate_get('/api/board/benches/nope/part-budgets')
    budgets = cl.simulate_get('/api/board/benches/home-bench/part-budgets')
    page = json.dumps(BENCH_PAGES)
    check('DRV-2/3 THE DOORS AND THE PAGE: mount-options asks for a Board first, refuses an unknown one (422) in words; part-budgets 404 for an unknown '
          'bench, 200 with no parts on the bench; the Drivers and parts tab has the Board picker, Mount here (posting x, y, rotation to /mount) and the '
          'part budgets',
          pick.status_code == 200 and pick.json['rows'] == [] and unknown.status_code == 422 and nobench.status_code == 404 and budgets.status_code == 200
          and budgets.json['rows'] == [] and 'bench-mount-options' in page and 'Mount here' in page and 'part-budgets' in page
          and 'mount-options?child={scope:mountchild}' in page, (pick.json, unknown.json, budgets.json))
    _fresh()
