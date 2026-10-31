"""board_part_boards_selftest - drv-0 / drv-1 (AI-Notes/plans/DRIVERS_AND_ESD_PLAN.md; the user's words 2026-10-31: drivers "as a type of component we can put
into place to fix issues with drive" ... "that way we can define custom drivers like mini boards and enable placing boards with footprints onto other
boards"). Parts as Boards on the Bench: the cited ULN2003A, its footholds, mounting by position (a DIP across a breadboard's trench), custom parts, the
new drive checks (drive-shortfall / under-voltage / max-volts over-voltage), the fixes the catalogue suggests, the doors and the page.
The motor and the 4 V / 3.6 V parts below are SYNTHETIC test parts (no real product is named or implied). Run by board_selftest.main().
"""
import contextlib
import json
import os
import types

#: synthetic: a load that draws 300 mA from whatever drives it (a small motor's coil, say) - not a real part
MOTOR = {'name': 'test-motor-300ma', 'kind': 'load', 'draw_ma': 300.0, 'pins': [{'number': 1, 'name': 'M-', 'role': 'in', 'x_mm': 0, 'y_mm': 0},
                                                                                 {'number': 2, 'name': 'M+', 'role': 'nc', 'x_mm': 5.08, 'y_mm': 0}]}
STRADDLE = (3.81 + 2.54 * 9, 22.098)   # the ULN2003A's own origin on a half breadboard: pin 1 -> r10f, pin 16 -> r10e


def _fresh():
    from board.custom import part_boards as PB
    PB._MEM[PB.CLS].clear()
    return PB


def _feet(*keys):
    from board.custom import footholds as FH
    return [FH.for_definition(*k)[0] for k in keys]


def run_part_catalogue(check):
    PB = _fresh()
    from board.custom import footholds as FH
    uln = PB.part('uln2003a-n')
    pins = json.loads(uln['pins_json'])
    roles = [p['role'] for p in pins]
    check('DRV-0 THE CITED DRIVER: ULN2003A in PDIP-16 from TI SLRS027T - 7 inputs, 7 open-collector outputs, E (ground), COM (clamp diodes); on from 2.4 V '
          '(V_I(on) max at 200 mA, §5.6), draws 1.35 mA max at 3.85 V, takes 30 V; sinks 500 mA peak, sources nothing (0 is a real value), 50 V; total '
          '2.5 A across channels; rated -40 .. 70 C; its own ESD rating HBM 2 kV / CDM 500 V (§5.2)',
          len(pins) == 16 and roles.count('in') == 7 and roles.count('out') == 7 and roles.count('ground') == 1 and roles.count('common') == 1
          and (uln['on_volts'], uln['draw_ma'], uln['in_max_v'], uln['out_sink_ma'], uln['out_source_ma'], uln['out_max_v'], uln['total_ma'])
          == (2.4, 1.35, 30.0, 500.0, 0.0, 50.0, 2500.0) and (uln['t_min_c'], uln['t_max_c'], uln['esd_hbm_v'], uln['esd_cdm_v']) == (-40.0, 70.0, 2000.0, 500.0)
          and 'SLRS027T' in uln['document'] and '§5.6' in uln['page_table'] and uln['origin'] == 'cited', uln['contract'])
    feet = {f['foothold']: f for f in FH.for_definition('part', 'uln2003a-n')[0]}
    check('DRV-1 A PART IS A BOARD: definition kind part gives one foothold per pin - an input is direction in with what it draws, its on-level and its '
          'maximum; an output sinks 500 / sources 0; E is a 0 V supply (ground by use); COM is passive; positions from the N package drawing (2.54 mm '
          'pitch, rows 7.62 mm apart, pin 16 opposite pin 1); an unknown part is refused in words',
          len(feet) == 16 and feet['1']['direction'] == 'in' and (feet['1']['draw_ma'], feet['1']['on_volts'], feet['1']['max_volts']) == (1.35, 2.4, 30.0)
          and feet['16']['label'] == '1C' and (feet['16']['sink_ma'], feet['16']['source_ma']) == (500.0, 0.0) and feet['8']['rail_volts'] == 0.0
          and feet['9']['direction'] == 'passive' and feet['2']['x_mm'] - feet['1']['x_mm'] == 2.54 and feet['1']['y_mm'] - feet['16']['y_mm'] == 7.62
          and feet['1']['x_mm'] == feet['16']['x_mm'] and 'no part named' in FH.for_definition('part', 'nope')[1], {k: feet[k]['direction'] for k in ('1', '8', '9', '16')})


def run_mounting(check):
    from board.custom import bench_mount as M
    _fresh()
    uln, bb = _feet(('part', 'uln2003a-n'), ('geometry', 'breadboard-half'))
    good = M.landings(uln, bb, *STRADDLE)
    pairs = {c: p for c, p, _ in good['pairs']}
    check('DRV-1 MOUNTED BY POSITION: the ULN2003A across a half breadboard\'s trench - all 16 pins land (pin 1 r10f .. pin 8 r17f, pin 16 r10e .. pin 9 '
          'r17e, 0 mm off: the package\'s 7.62 mm rows = the breadboard\'s e-f spacing), none share a hole, and the breadboard joins no two of them',
          len(good['pairs']) == 16 and not good['unlanded'] and not good['shared'] and not good['joined'] and pairs['1'] == 'r10f' and pairs['8'] == 'r17f'
          and pairs['16'] == 'r10e' and pairs['9'] == 'r17e' and all(m == 0.0 for _, _, m in good['pairs']), good['pairs'][:4])
    flat = M.landings(uln, bb, STRADDLE[0], 11.938 - 7.62 + 7.62)
    off = M.landings(uln, bb, STRADDLE[0] + 1.27, STRADDLE[1])
    turned = M.landings(uln, bb, 3.81 + 2.54 * 16, 29.718, rotation=180)
    check('DRV-1 THE GEOMETRY SAYS WHAT IS WRONG: not straddling the trench (both rows on strips a-e) the breadboard shorts each pin to the one opposite '
          '(8 joined pairs, pin 1 with pin 16); half a pitch off, no pin lands; turned 180 degrees it straddles again with every pin landed',
          len(flat['joined']) == 8 and ('1', '16', 'strip:10:a-e') in flat['joined'] and len(off['unlanded']) == 16
          and len(turned['pairs']) == 16 and not turned['joined'] and not turned['unlanded'], (flat['joined'][:2], turned['pairs'][:2]))


def run_drive_checks(check):
    from board.custom import bench_mount as M
    from board.custom import bench_nets as BN
    PB = _fresh()
    st = PB.define(None, MOTOR)
    refused = [PB.define(None, dict(MOTOR, kind='thing')), PB.define(None, dict(MOTOR, name='uln2003a-n')), PB.define(None, dict(MOTOR, draw_ma=-5)),
               PB.define(None, dict(MOTOR, pins=MOTOR['pins'] + [MOTOR['pins'][0]]))]
    check('DRV-0 A CUSTOM PART (a person\'s mini board): defined with its pins and contract (201, origin custom); refused in words: an unknown kind, the name '
          'of a cited part (409), a negative number, a pin given twice',
          st[0] == 201 and st[1]['origin'] == 'custom' and [r[0] for r in refused] == [400, 409, 400, 400] and 'given twice' in refused[3][1]['error']
          and PB.part('test-motor-300ma')['draw_ma'] == 300.0, (st, [r[1]['error'] for r in refused]))
    uno, motor, uln, bb = _feet(('datasheet', 'arduino-uno-r3'), ('part', 'test-motor-300ma'), ('part', 'uln2003a-n'), ('geometry', 'breadboard-half'))
    d6 = next(f['foothold'] for f in uno if f['label'] == 'D6')
    gnd = next(f['foothold'] for f in uno if f['label'] == 'GND')
    boards = {'uno': uno, 'motor': motor, 'uln': uln, 'bb': bb}
    direct, _ = BN.nets(boards, [{'from_board': 'uno', 'from_foothold': d6, 'to_board': 'motor', 'to_foothold': '1'}])
    short = [f for n in direct for f in n['findings']]
    fixes = PB.suggestions(direct)
    check('DRV-1 DRIVE-SHORTFALL: the UNO\'s D6 (20 mA, its cited limit) wired straight to a load that draws 300 mA is a finding naming both numbers; the '
          'fix suggested is the ULN2003A - it sinks up to 500 mA, turns on from 2.4 V (the 5 V pin reaches it) and draws 1.35 mA',
          [f['kind'] for f in short] == ['drive-shortfall'] and short[0]['need_ma'] == 300.0 and short[0]['can_ma'] == 20.0 and '300 mA' in short[0]['words']
          and any(s['part'] == 'uln2003a-n' and s['fits'] and '500 mA' in s['why'] for s in fixes), (short, fixes))
    mounted = [{'from_board': 'uln', 'from_foothold': c, 'to_board': 'bb', 'to_foothold': p, 'kind': 'mounted'} for c, p, _ in M.landings(uln, bb, *STRADDLE)['pairs']]
    wires = [{'from_board': 'uno', 'from_foothold': d6, 'to_board': 'bb', 'to_foothold': 'r10j'},      # D6 -> the strip of 1B (pin 1)
             {'from_board': 'motor', 'from_foothold': '1', 'to_board': 'bb', 'to_foothold': 'r10a'},   # the load -> the strip of 1C (pin 16)
             {'from_board': 'uno', 'from_foothold': gnd, 'to_board': 'bb', 'to_foothold': 'r17j'}]     # GND -> the strip of E (pin 8)
    fixed, problems = BN.nets(boards, mounted + wires)
    by = {tuple(sorted((m['board'], m['foothold']) for m in n['members'] if m['board'] != 'bb')): n for n in fixed}
    in_net = next(n for k, n in by.items() if ('uln', '1') in k)
    out_net = next(n for k, n in by.items() if ('uln', '16') in k)
    check('DRV-1 THE DRIVER FIXES IT: with the ULN2003A mounted across the trench, D6 drives input 1B (draws 1.35 mA of its 20, on from 2.4 V of its 5) and '
          'output 1C sinks the 300 mA load (of its 500) - no finding on either net, E on the ground strip with the UNO\'s GND',
          not problems and not in_net['findings'] and not out_net['findings'] and ('uno', d6) in [(m['board'], m['foothold']) for m in in_net['members']]
          and ('motor', '1') in [(m['board'], m['foothold']) for m in out_net['members']], [(n['net'], n['findings']) for n in fixed])
    PB.define(None, {'name': 'test-4v-input', 'kind': 'module', 'on_volts': 4.0, 'in_max_v': 3.6,
                     'pins': [{'number': 1, 'name': 'IN', 'role': 'in', 'x_mm': 0, 'y_mm': 0}]})
    c3, part4 = _feet(('datasheet', 'esp32-c3'), ('part', 'test-4v-input'))
    io = next(f['foothold'] for f in c3 if f['direction'] == 'inout' and f['logic_volts'] == 3.3)
    five = next(f['foothold'] for f in uno if f['label'] == '+5V')
    under, _ = BN.nets({'c3': c3, 'p': part4}, [{'from_board': 'c3', 'from_foothold': io, 'to_board': 'p', 'to_foothold': '1'}])
    over, _ = BN.nets({'uno': uno, 'p': part4}, [{'from_board': 'uno', 'from_foothold': five, 'to_board': 'p', 'to_foothold': '1'}])
    check('DRV-1 UNDER- AND OVER-VOLTAGE FROM A PART\'S CONTRACT (synthetic part: on from 4 V, takes at most 3.6 V): a 3.3 V C3 pin cannot turn it on '
          '(under-voltage); the UNO\'s 5 V rail is above what it takes (over-voltage, "takes at most")',
          [f['kind'] for n in under for f in n['findings']] == ['under-voltage'] and any(f['kind'] == 'over-voltage' and 'takes at most 3.6 V' in f['words']
                                                                                        for n in over for f in n['findings']),
          ([f for n in under for f in n['findings']], [f for n in over for f in n['findings']]))
    _fresh()


def run_part_doors(check):
    import falcon
    import falcon.testing as ft
    from board.bench_parts_api import BenchPartsAPI
    from board.custom import board_details as BD
    from board.bench_page import BENCH_PAGES
    _fresh()
    app = falcon.App()
    with contextlib.redirect_stdout(open(os.devnull, 'w')):
        BenchPartsAPI(polServer=types.SimpleNamespace(falconServer=app), manager=None)
    cl = ft.TestClient(app)
    made = cl.simulate_post('/api/board/parts', json=MOTOR)
    cat = {r['name']: r for r in cl.simulate_get('/api/board/parts').json['rows']}
    bad = cl.simulate_post('/api/board/parts', json={'name': 'x', 'kind': 'load', 'pins': []})
    nobench = cl.simulate_post('/api/board/benches/nope/parts', json={'part': 'uln2003a-n'})
    nomount = cl.simulate_post('/api/board/benches/nope/mount', json={'child': 'a', 'parent': 'b', 'x_mm': 0, 'y_mm': 0})
    check('DRV-1 THE DOORS: POST a custom part (201) and it is in the catalogue beside the cited ULN2003A (contract in words, definition part/<name>); a part '
          'with no pins is refused (400); an unknown bench is 404 in words for placing and for mounting',
          made.status_code == 201 and {'uln2003a-n', 'test-motor-300ma'} <= set(cat) and cat['uln2003a-n']['definition'] == 'part/uln2003a-n'
          and 'sinks 500 mA' in cat['uln2003a-n']['contract'] and bad.status_code == 400 and nobench.status_code == 404 and nomount.status_code == 404,
          (made.json, bad.json, nobench.json))
    summary = BD.part('part', 'uln2003a-n', 'summary')[0]
    pins = BD.part('part', 'uln2003a-n', 'parts')[0]
    page = json.dumps(BENCH_PAGES)
    check('DRV-1 BOARD DETAILS + THE BENCH PAGE: a part\'s Board Details summary has its 16 footholds and its pins (role, the package); the Bench page has a '
          'Drivers and parts tab - the catalogue with Add to bench and the drive fixes of this bench',
          summary[0]['footholds'] == 16 and 'datasheet' in summary[0]['defined_by'] and len(pins) == 16 and pins[0]['role'] == 'in'
          and 'bench-parts' in page and 'drive-fixes' in page and 'benches/home-bench/parts' in page, (summary, pins[:1]))
    _fresh()
