"""board_bench_setup_selftest - bench-0 (MISSION_GENERIC_PLAN.md section 13.1): the Bench, its two selection lists, the testing words (HARDWARE ONLY
said loudly), the add / remove doors, the breadboard models' derived geometry and the page.

    PYTHONPATH=.:modules python3 -m board.board_bench_setup_selftest
"""
import json


def run_bench_setup(check):
    from board.custom import bench as B
    from board.custom import bench_seed as S
    from board.custom import chip_ladder as CL
    B._MEM.clear()
    # ---- the models
    ms = {m['name']: m for m in S.SEED_BREADBOARD_MODELS}
    check('bench-0 MODELS: five breadboard models; half-400 and full-830 and mini-170 have DERIVED geometry from pv_shapes; the BUD and the kit\'s are UNVERIFIED with no dimensions',
          len(ms) == 5 and all(ms[k]['geometry_known'] and ms[k]['width_mm'] > 0 and 'derived' in ms[k]['basis'] for k in ('half-400', 'full-830', 'mini-170'))
          and all(not ms[k]['geometry_known'] and ms[k]['width_mm'] == -1.0 for k in ('bud-bb-32650-w', 'starter-kit-breadboard')),
          {k: (m['geometry_known'], round(m['width_mm'], 1)) for k, m in ms.items()})
    check('bench-0 MODELS: the full board is wider than the half, the half than the mini (the geometry follows the row counts)',
          ms['full-830']['width_mm'] > ms['half-400']['width_mm'] > ms['mini-170']['width_mm'], (ms['full-830']['width_mm'], ms['half-400']['width_mm'], ms['mini-170']['width_mm']))
    # ---- the testing words (shared with the ladder)
    lb = B.ladder_boards(None)
    check('bench-0 TESTING: every ladder board has a testing group and a word; the UNO is "simulated: pins real"; the Arduino Zero and the Feather are "HARDWARE ONLY"; the C3 says STUB',
          all(r['testing_group'] in ('simulated', 'simulated-stub', 'hardware-only', 'planned') and r['testing'] for r in lb.values())
          and lb['arduino-uno-r3']['testing_group'] == 'simulated' and lb['arduino-uno-r3']['testing'].startswith('simulated: pins real')
          and lb['arduino-zero']['testing'].startswith('HARDWARE ONLY') and lb['adafruit-feather-m0-express']['testing'].startswith('HARDWARE ONLY')
          and 'STUB' in lb['esp32-c3-devkitm-1']['testing'], {k: v['testing'][:40] for k, v in lb.items() if k in ('arduino-uno-r3', 'arduino-zero', 'esp32-c3-devkitm-1')})
    check('bench-0 TESTING: the word names the software and how it simulates, and who drives the inputs (never blank)',
          all(r['software'] and r['how'] and r['inputs_driven_by'] for r in lb.values()), [k for k, r in lb.items() if not (r['software'] and r['how'] and r['inputs_driven_by'])])
    # ---- the seeded bench
    st, body = B.get_door(None, {}, 'benches')
    hb = next(r for r in body['rows'] if r['name'] == S.HOME_BENCH)
    check('bench-0 HOME: the seeded home bench holds the four boards he showed and three breadboards (2 BUD + the kit\'s); three of the four boards are HARDWARE ONLY or STUB and are NAMED',
          st == 200 and hb['boards'] == 4 and hb['breadboards'] == 3 and hb['simulated_real_pins'] == 1 and hb['hardware_only'] == 2 and hb['simulated_stub_pins'] == 1
          and 'Zero #1' in hb['hardware_only_boards'] and 'Feather M0 #1' in hb['hardware_only_boards'], hb)
    st, body = B.get_door(None, {}, 'boards', S.HOME_BENCH)
    check('bench-0 BOARDS: the bench\'s board rows carry label, testing, software, how, inputs_driven_by, section (RISC-V | convenience)',
          st == 200 and len(body['rows']) == 4 and all(k in body['rows'][0] for k in ('label', 'testing', 'software', 'how', 'inputs_driven_by', 'section'))
          and {r['section'] for r in body['rows']} == {'convenience'}, body['rows'][0] if body.get('rows') else body)
    st, body = B.get_door(None, {}, 'breadboards', S.HOME_BENCH)
    check('bench-0 BREADBOARDS: the BUD rows say UNVERIFIED geometry in capitals (cannot be drawn yet) and count 2',
          st == 200 and any(r['model'] == 'bud-bb-32650-w' and r['count'] == 2 and r['geometry'].startswith('UNVERIFIED') for r in body['rows']), body['rows'])
    # ---- the selection lists
    st, body = B.get_door(None, {'bench': S.HOME_BENCH}, 'options-boards')
    rows = body['rows']
    check('bench-0 OPTIONS boards: every ladder board once, RISC-V first then convenience, simulatable before HARDWARE ONLY within a section; on_bench counts the home bench; can_add on every row',
          st == 200 and len(rows) == len(lb) and rows[0]['section'] == 'RISC-V' and rows[-1]['section'] == 'convenience'
          and next(r for r in rows if r['board'] == 'arduino-uno-r3')['on_bench'] == 1 and all(r['can_add'] for r in rows), [(r['section'], r['testing_group']) for r in rows][:6])
    st, body = B.get_door(None, {'bench': S.HOME_BENCH}, 'options-breadboards')
    check('bench-0 OPTIONS breadboards: the five models, on_bench 2 for the BUD, geometry word on each',
          st == 200 and len(body['rows']) == 5 and next(r for r in body['rows'] if r['name'] == 'bud-bb-32650-w')['on_bench'] == 2 and all(r['geometry'] for r in body['rows']), body['rows'][0])
    # ---- add / remove
    st, body = B.post_door(None, S.HOME_BENCH, 'boards', {'board': 'rpi-pico2'})
    check('bench-0 ADD board: adding a Pico 2 answers 201 with its testing word (HARDWARE ONLY, no emulator) and the bench now lists five boards',
          st == 201 and body['testing'].startswith('HARDWARE ONLY') and len(body['rows']) == 5 and body['rows'][-1]['label'].endswith('#1'), body.get('testing'))
    st2, body2 = B.post_door(None, S.HOME_BENCH, 'boards', {'board': 'arduino-uno-r3'})
    check('bench-0 ADD board: a second UNO gets label "... #2"', st2 == 201 and body2['rows'][-1]['label'].endswith('#2'), body2['rows'][-1]['label'])
    st3, body3 = B.post_door(None, S.HOME_BENCH, 'boards', {'board': 'not-a-board'})
    check('bench-0 ADD board: an unknown board is 404 and names the known ones', st3 == 404 and 'known' in body3 and 'arduino-uno-r3' in body3['known'], body3.get('error'))
    st4, body4 = B.post_door(None, S.HOME_BENCH, 'breadboards', {'model': 'half-400', 'count': 2})
    st5, body5 = B.post_door(None, S.HOME_BENCH, 'breadboards', {'model': 'half-400'})
    check('bench-0 ADD breadboard: two half boards then one more make count 3 on one row; count 0 is 400; an unknown model 404',
          st4 == 201 and st5 == 201 and next(r for r in body5['rows'] if r['model'] == 'half-400')['count'] == 3
          and B.post_door(None, S.HOME_BENCH, 'breadboards', {'model': 'half-400', 'count': 0})[0] == 400
          and B.post_door(None, S.HOME_BENCH, 'breadboards', {'model': 'nope'})[0] == 404, body5['rows'])
    st6, body6 = B.post_door(None, S.HOME_BENCH, 'remove', {'kind': 'board', 'key': body2['rows'][-1]['label']})
    st7, body7 = B.post_door(None, S.HOME_BENCH, 'remove', {'kind': 'breadboard', 'key': 'half-400'})
    check('bench-0 REMOVE: removing the second UNO by label leaves five boards; removing one half board leaves count 2; an unknown key is 404; a bad kind 400',
          st6 == 200 and len(body6['rows']) == 5 and st7 == 200 and next(r for r in body7['rows'] if r['model'] == 'half-400')['count'] == 2
          and B.post_door(None, S.HOME_BENCH, 'remove', {'kind': 'board', 'key': 'ghost'})[0] == 404
          and B.post_door(None, S.HOME_BENCH, 'remove', {'kind': 'thing', 'key': 'x'})[0] == 400, (len(body6['rows']), body7['rows']))
    check('bench-0 DOORS: an unknown bench is 404 on boards, breadboards, add and remove',
          B.get_door(None, {}, 'boards', 'nowhere')[0] == 404 and B.post_door(None, 'nowhere', 'boards', {'board': 'arduino-uno-r3'})[0] == 404
          and B.post_door(None, 'nowhere', 'remove', {'kind': 'board', 'key': 'x'})[0] == 404, '')
    check('bench-0 PRIVACY: no e-mail, street or invoice number in the seeds', not any(s in json.dumps(S.SEED_BENCHES + S.SEED_BREADBOARD_MODELS) for s in ('@', 'Arrowhead', 'Fairfax', '3689309', '134236176')), '')
    # ---- the ladder's own split
    st, body = CL.door(None, {'section': 'convenience'}, 'chips')
    groups = {r['name']: r['testing_group'] for r in body['rows']}
    check('chp-1 SPLIT: every ladder row carries testing_group + testing + software + how + inputs_driven_by; the SAMD21 row is hardware-only and its word starts HARDWARE ONLY',
          all(k in body['rows'][0] for k in ('testing_group', 'testing', 'software', 'how', 'inputs_driven_by')) and groups['samd21g18a'] == 'hardware-only'
          and next(r for r in body['rows'] if r['name'] == 'samd21g18a')['testing'].startswith('HARDWARE ONLY'), groups)
    st, body = CL.door(None, {}, 'emulators')
    check('chp-1 EMULATORS: every emulator row says its method and what drives the inputs; the "none" row lists the HARDWARE ONLY chips',
          all(r['method'] and r['inputs_driven_by'] for r in body['rows']) and 'samd21g18a' in next(r for r in body['rows'] if r['kind'] == 'none')['chips_covered'], body['rows'][-1])
    # ---- the pages
    from board.bench_page import BENCH_PAGES as P
    from board.chip_ladder_page import CHIP_LADDER_PAGES as CP
    d = json.loads(P[0]['definition'])
    check('bench-0 PAGE: /display/bench has the benches table above three tabs - On the bench, Add a board, Add a breadboard - with Add to bench and Remove row actions',
          P[0]['pageRoute'] == 'bench' and [t['key'] for t in d['tabs']] == ['bench', 'add-board', 'add-breadboard']
          and all('"label": "Add to bench"' in json.dumps(d['tabs'][i]) for i in (1, 2)) and '"label": "Remove"' in json.dumps(d['tabs'][0]), [t['key'] for t in d['tabs']])
    cd = json.loads(CP[0]['definition'])
    check('chp-1 PAGE: each ladder section has the three testing tables - simulated with real pins, pins stub, HARDWARE ONLY - and the Emulators tab has the hardware-only table',
          all(w in json.dumps(cd['tabs'][i]) for i in (0, 1) for w in ('testing_group', 'hardware-only', 'simulated-stub'))
          and 'HARDWARE ONLY' in json.dumps(cd['tabs'][2]), '')


def main():
    fails = []

    def check(label, cond, extra=''):
        print('  [%s] %s%s' % ('PASS' if cond else 'FAIL', label, '' if cond else '  <- %r' % (extra,)))
        if not cond:
            fails.append(label)
    run_bench_setup(check)
    print('bench setup selftest: %d failure(s)' % len(fails))
    return 1 if fails else 0


if __name__ == '__main__':
    raise SystemExit(main())
