"""board_pin_view_candidate_selftest - pv-5 (PIN_VIEW_PLAN.md 2.9, MISSION_PROFILE_SOLVER_PLAN.md 8.4-8.5): the pin view's CANDIDATE stage draws a solution the attempt engine found (a stored SolveRun), and the
"Configuration events" table page + `pol board events` CLI read the config-events door. The view only reads: the run is made here by solve() + SolveRun storage (the POST door's own steps), never by the view.
Run by board_selftest.run().
"""
import contextlib
import io
import json
import types

BOARD = 'arduino-uno-r3'
MISSION = 'uno-light-mission'


def run_pin_view_candidate(check):
    import falcon
    import falcon.testing as ft
    from board.board_endpoints import construct_board_endpoints
    from board.custom import config_events as CE
    from board.custom import pin_view as PV
    from board.custom import pin_view_candidate as CAND
    from cmod.custom import solve as S
    from cmod.custom import solve_record as REC
    from cmod.custom.selftest_purpose import _manager

    mgr = _manager()
    try:
        PV.build(BOARD, {'stage': 'candidate'}, mgr)
        none_msg = ''
    except PV.Refused as e:
        none_msg = '%s|%s' % (e.status, e)
    check('CANDIDATE: with no stored solution search the stage refuses 404 with the plain reason and the command that makes one (the view never runs the search itself)',
          none_msg.startswith('404|') and 'no solution search has been stored for board ' + BOARD in none_msg and 'pol capability solve mission' in none_msg, none_msg)

    res = S.solve(MISSION, boards=[BOARD], objective='fastest-cycle', limits={'prefer': 'bench-wiring', 'max_candidates': 60}, manager=mgr)
    row = REC.store(mgr, res, 'selftest')
    r = PV.build(BOARD, {'stage': 'candidate'}, mgr)
    c = r['candidate']
    by_role = {a['role']: a for a in c['assignment']}
    pads = {p['canonical']: p for p in r['pins'] if p['level'] == 'die' and p['canonical']}
    marked = {k for k, p in pads.items() if p['stage'] == 'proposed'}
    cons = lambda pin: next((x for x in pads[pin]['consumers'] if x['kind'] == 'task'), {})   # noqa: E731
    check('CANDIDATE: no run named -> the latest run for the board, its chosen candidate (the bench-preferred fastest-cycle run): the button is drawn on D2 (INT0), the LED on D6, the sense line on D3, all `proposed`',
          c['run'] == row.name and c['chosen'] and r['stage']['stage'] == 'candidate' and by_role['the button']['pin'] == 'D2' and by_role['the button']['function'] == 'INT0' and by_role['the LED']['pin'] == 'D6'
          and by_role['the sense line']['pin'] == 'D3' and {'D2', 'D6', 'D3'} <= marked, (c['run'], sorted(marked)))
    check('CANDIDATE: a marked pin carries the profile role as its consumer, the chosen route and the run\'s REASON for that pin, plus the Purposes it serves; a pin the plan leaves free keeps its base stage (not proposed)',
          cons('D2')['who'] == 'the button' and cons('D2')['route'] == 'ext-interrupt' and 'D2 as INT0' in cons('D2')['why'] and any(x['kind'] == 'purpose' for x in pads['D2']['consumers'])
          and pads['D4']['stage'] in ('available', 'unassigned') and 'D4' not in marked and all(p['stage'] != 'proposed' for p in r['pins'] if p['level'] == 'die' and p['canonical'] in ('D4', 'D5', 'D7', 'D8')),
          [pads[k]['stage'] for k in ('D4', 'D5')])
    check('CANDIDATE: the same line is marked at every level (die pad, package leg and header pin of D2 are all proposed), and the drive / signal summaries read the candidate\'s function (D2 activated as INT0)',
          sum(1 for p in r['pins'] if p['canonical'] == 'D2' and p['stage'] == 'proposed') >= 3 and (pads['D2']['activated'] or {}).get('function') == 'INT0', pads['D2']['activated'])
    lost = ' | '.join(c['what_lost'])
    check('CANDIDATE: the response carries the score (both objectives), tier, variants, the open ladder rungs (unchecked), and "what lost": D0 and D1 refused BY NAME at rung 8, and the runner-ups with their deciding differences',
          c['score']['objective'] == 'fastest-cycle' and c['score']['cycle'] and c['tier'] == 'bare-c' and 'read button via ext-interrupt' in c['variants_text'] and any('rung 9' in t for t in c['unchecked'])
          and 'Pin D0 was refused' in lost and 'Pin D1 was refused' in lost and 'rung 8' in lost and 'runner-up' in lost and c['links']['solutions_found'] == '/display/solutions-found' and len(c['candidates']) >= 10,
          lost[:200])
    # a different candidate: pick one whose pins differ from the chosen plan's
    summ = json.loads(row.candidates_json)
    chosen_pins = {k: v for k, v in next(s for s in summ if s['id'] == row.chosen)['pins'].items()}
    r2, pads2, m2, other = None, {}, set(), None
    for s_ in [s for s in summ if s['pins'] and s['pins'] != chosen_pins and s['placement'] == 'placed' and s['hardware'].startswith(BOARD)][:30]:     # the first other plan whose marks differ (some plans differ only in a route, not a pin)
        r2 = PV.build(BOARD, {'stage': 'candidate', 'run': row.name, 'candidate': s_['id']}, mgr)
        pads2 = {p['canonical']: p for p in r2['pins'] if p['level'] == 'die' and p['canonical']}
        m2 = {k for k, p in pads2.items() if p['stage'] == 'proposed'}
        other = s_
        if m2 != marked:
            break
    check('CANDIDATE: another candidate (by id) changes the marks and names why it ranks below the chosen plan; a rank number (candidate=2) works too',
          r2 is not None and not r2['candidate']['chosen'] and m2 != marked and 'ranks #' in ' | '.join(r2['candidate']['what_lost'])
          and PV.build(BOARD, {'stage': 'candidate', 'candidate': '2'}, mgr)['candidate']['rank'] == 2, (sorted(m2), sorted(marked)))
    bad = {}
    for key, prm in (('cand', {'candidate': 'zzz'}), ('run', {'run': 'no-such-run'}), ('mission', {'mission': 'no-such-mission'})):
        try:
            PV.build(BOARD, dict({'stage': 'candidate'}, **prm), mgr)
            bad[key] = 'accepted'
        except PV.Refused as e:
            bad[key] = '%s|%s' % (e.status, e)
    try:
        PV.build(BOARD, {'stage': 'banana'}, mgr)
        stg = ''
    except PV.Refused as e:
        stg = str(e)
    check('CANDIDATE: an unknown candidate / run / Mission is refused 404 BY NAME (listing what exists), and an unknown stage lists `candidate` among the stages',
          bad['cand'].startswith('404|') and 'zzz' in bad['cand'] and bad['run'].startswith('404|') and 'no-such-run' in bad['run'] and bad['mission'].startswith('404|') and 'candidate' in stg, str(bad))
    row.result_sha256 = '0' * 64   # a run the rules have moved on from: the recorded chosen plan still draws; another candidate is refused 409 (never a plan the run did not make)
    try:
        PV.build(BOARD, {'stage': 'candidate', 'candidate': other['id']}, mgr)
        st409 = 'accepted'
    except PV.Refused as e:
        st409 = e.status
    r3 = PV.build(BOARD, {'stage': 'candidate'}, mgr)
    check('CANDIDATE: when the stored run no longer replays to its recorded result, the chosen plan still draws as recorded (with that said) and any other candidate is refused 409',
          st409 == 409 and r3['candidate']['pins_marked'] and any('recorded' in n for n in r3['candidate']['notes']), (st409, r3['candidate']['notes']))
    row.result_sha256 = res['result_sha256']

    # ---- the door on a real falcon.App
    srv = types.SimpleNamespace(falconServer=falcon.App(), manager=mgr)
    with contextlib.redirect_stdout(io.StringIO()):
        construct_board_endpoints(srv)
    cl = ft.TestClient(srv.falconServer)
    ok = cl.simulate_get('/api/board/%s/pin-view?stage=candidate&run=%s' % (BOARD, row.name))
    rows = cl.simulate_get('/api/board/%s/pin-view/pins?stage=candidate' % BOARD)
    miss = cl.simulate_get('/api/board/%s/pin-view?stage=candidate&run=nope' % BOARD)
    check('DOOR: GET /api/board/{board}/pin-view?stage=candidate[&run=&candidate=] answers 200 with the candidate block, the flat pin rows show the proposed stage with the role as consumer, an unknown run is 404 with a reason',
          ok.status_code == 200 and ok.json['candidate']['run'] == row.name and rows.status_code == 200 and any(x['stage'] == 'proposed' and 'the button' in x['consumers'] for x in rows.json['rows'])
          and miss.status_code == 404 and 'nope' in miss.json['error'], (ok.status_code, rows.status_code, miss.status_code))

    # ---- the Configuration events page, door rows and CLI
    from board.board_page import SEED_BOARD_PAGE_DISPLAYS as PAGES
    page = next((p for p in PAGES if p['name'] == 'config-events'), None)
    d = json.loads(page['definition']) if page else {}
    items = [it for rw in d.get('rows', []) for it in rw['items']]
    inp = items[0]['componentProps']['inputs'] if items else {}
    seed = json.dumps(__import__('polariapps.apps_seed', fromlist=['x']).SEED_POLARI_APPS)
    check('PAGE: "Configuration events" (/display/config-events) is ONE configured class-rows-table over the config-events door (kind, when, who, cause, pins_changed) with a `view` link into /display/pin-view?event={id}; '
          'not a raw-JSON panel; reachable from the "Pin data views" nav group',
          d.get('title') == 'Configuration events' and len(items) == 1 and inp.get('dataPath') == '/api/board/%s/config-events' % BOARD and inp.get('columnFormats') == 'view:view:/display/pin-view?event={id}'
          and all(k in inp['columns'].split(',') for k in ('kind', 'when', 'who', 'cause', 'pins_changed', 'view')) and 'api-json-panel' not in page['definition'] and '/display/config-events' in seed
          and seed.index('Pin data views') < seed.index('/display/config-events'), inp.get('columns'))
    evs = [{'name': 'derived:InstallRecord:x', 'seq': 1, 'label': 'Firmware flashed', 'who': 'not recorded', 'cause': 'it was flashed', 'board_instance': '', 'provenance': 'derived', 'dated': False, 'when': '',
            'pins_changed': [{'pin': 'a', 'label': 'D2', 'what': ['drive: x']}, {'pin': 'b', 'label': 'D3', 'what': ['signal: y']}]},
           {'name': 'e2', 'seq': 2, 'label': 'Board reset', 'who': 'dustin', 'cause': 'pressed reset', 'board_instance': 'bench:1', 'provenance': 'recorded', 'dated': True, 'when': '2026-10-18T09:30:00', 'pins_changed': []}]
    rws = CE.event_rows(evs)
    status, payload = CE.get_door(None, BOARD, {'pins': '0'})
    check('ROWS: the config-events door adds a flat `rows` list (id = the event name for the view link, kind in words, when in words or "time not recorded", who, cause, pins_changed as a count, instance, source)',
          rws[0]['id'] == 'derived:InstallRecord:x' and rws[0]['when'] == 'time not recorded' and rws[0]['pins_changed'] == 2 and rws[0]['instance'] == 'the design' and rws[1]['when'] == '18 Oct 2026, 09:30'
          and rws[1]['pins_changed'] == 0 and rws[1]['source'].startswith('recorded') and status == 200 and payload['rows'] == [], rws)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = CE.main(['list', BOARD, '--no-pins'])
        rc_bad = CE.main(['list', 'no-such-board'])
        rc_json = CE.main(['list', BOARD, '--no-pins', '--json'])
    out = buf.getvalue()
    check('CLI: `python3 -m board.custom.config_events list <board> [--json] [--no-pins]` prints the timeline in words (or says none are recorded), --json prints the door\'s payload, an unknown board is refused (exit 1)',
          rc == 0 and rc_bad == 1 and rc_json == 0 and 'no real-world changes are recorded' in out and '"rows"' in out and 'refused:' in out and 'one event' not in out and 'Firmware flashed' in CE.render(
              dict(payload, events=evs, rows=rws, count=2, derived=1, recorded=1)), out[:120])
