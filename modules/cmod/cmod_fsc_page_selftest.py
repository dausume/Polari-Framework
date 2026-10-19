"""cmod_fsc_page_selftest - fsc-3: the tabbed Firmware Scores page (cmod.cmod_fsc_page) and the generic tabs helpers (polariApiServer.module_pages_seed `_tab` / `_tabs_from`).

Checks: a page WITHOUT tabs is unchanged (no `tabs` key; a table without the new options has the old inputs), the tab shape, the `{key}` template tokens, every table
column is a field of the row its door serves, every table has a plain-words description, the selection scope wiring (ranking sets `solution`, breakdown reads it), the
`limit` door option and the breakdown `rows` alias, the graph row, the nav entry, the manifest.

    PYTHONPATH=.:modules python3 -m cmod.cmod_fsc_page_selftest
"""
import contextlib
import io
import json
import os
import re
import sys
from types import SimpleNamespace

MISSION = 'uno-light-mission'


def _tables(rows):
    return [i for r in rows for i in r['items']]


def main():
    passed = total = 0
    failures = []

    def check(label, cond, detail=None):
        nonlocal passed, total
        total += 1
        if cond:
            passed += 1
        else:
            failures.append(label)
        print('  [%s] %s%s' % ('ok' if cond else 'FAIL', label, '' if cond else '  <- %s' % (str(detail)[:300],)))
    print('cmod fsc page selftest (fsc-3)')

    from polariApiServer.module_pages_seed import _page, _row, _table, _tab, _tabs_from
    print('-- helpers')
    plain = _page('x', 'x', 'd', 'C', [_row(0, [_table('t', 0, 12, 'T', 'C')])])
    d = json.loads(plain['definition'])
    check('a page without tabs has no `tabs` / `tabs_from` key (renders unchanged)', set(d) == {'rows'}, list(d))
    capped = _table('t2', 0, 12, 'T', 'C', max_height=300)['componentProps']['inputs']
    check('fsc-3b: `max_height` rides as maxHeight when set and is absent otherwise (older seeds converge unchanged)',
          capped.get('maxHeight') == 300 and 'maxHeight' not in _table('t3', 0, 12, 'T', 'C')['componentProps']['inputs'])
    check('fsc-3b: `_row(css_class=)` sets the row class (default empty)', _row(0, [], css_class='side-by-side')['cssClass'] == 'side-by-side' and _row(0, [])['cssClass'] == '')
    check('a table without the fsc-3 options has exactly the old inputs (older seeds converge unchanged)',
          set(d['rows'][0]['items'][0]['componentProps']['inputs']) == {'className', 'columns', 'maxRows', 'columnFormats', 'filterField', 'filterValue', 'dataPath'})
    t = _table('t', 0, 12, 'T', '', select_field='a', select_scope='b', selected_value='{scope:b}', empty_text='e', row_link_tab_field='p')['componentProps']['inputs']
    check('the row-interaction options ride in the inputs when set', (t['selectField'], t['selectScope'], t['selectedValue'], t['emptyText'], t['rowLinkTabField']) == ('a', 'b', '{scope:b}', 'e', 'p'))
    tf = _tabs_from('/api/x', 'name', 'title', [], insert_at=1)
    check('_tab / _tabs_from give {key,title,rows} and {data_path,key_field,title_field,rows_template,insert_at}',
          _tab('k', 'K', [])['key'] == 'k' and set(tf) == {'data_path', 'key_field', 'title_field', 'rows_template', 'insert_at'} and 'insert_at' not in _tabs_from('/a', 'n', 't', []))

    print('-- the page')
    from cmod.cmod_page import SEED_CMOD_PAGE_DISPLAYS as P
    pg = next((p for p in P if p['pageRoute'] == 'firmware-scores'), None)
    check('/display/firmware-scores is registered in SEED_CMOD_PAGE_DISPLAYS as a page', pg is not None and pg['isPage'] is True)
    d = json.loads(pg['definition'])
    keys = [x['key'] for x in d['tabs']]
    check('static tabs: Top scorers, Failures, Profile editor; generated profile tabs go in after the first (insert_at 1)',
          keys == ['top', 'failures', 'profile-editor'] and d['tabs_from']['insert_at'] == 1 and d['tabs_from']['key_field'] == 'name' and d['tabs_from']['data_path'] == '/api/firmware-score-profiles')
    tpl = d['tabs_from']['rows_template']
    all_tables = _tables(d['tabs'][0]['rows']) + _tables(d['tabs'][1]['rows']) + _tables(d['tabs'][2]['rows']) + _tables(tpl)
    names = {i['componentProps']['componentName'] for i in all_tables}
    check('only configured tables and the configured graph panel: class-rows-table + named-graph-panel (no JSON panel, no custom component)', names == {'class-rows-table', 'named-graph-panel'}, names)
    check('every table and graph carries a plain-words description that says what a row (or bar) is',
          all(i['description'] and ('One row' in i['description'] or 'One bar' in i['description']) for i in all_tables))
    check('the competitive reading (best = 100, worst = 0) is stated on the top and ranking tables',
          all('best' in i['description'] and '100' in i['description'] for i in all_tables if i['id'] in ('fsc-top', 'fsc-ranked')))
    top = _tables(d['tabs'][0]['rows'])[0]['componentProps']['inputs']
    check('the top table reads /api/firmware-scores/top and a row opens the tab named by the row\'s `profile`',
          top['dataPath'] == '/api/firmware-scores/top?mission=%s' % MISSION and top['rowLinkTabField'] == 'profile')
    ids = {i['id']: i['componentProps']['inputs'] for r in tpl for i in r['items']}
    check('profile tab: ranking sets the `solution` scope and shows it selected; the breakdown reads {scope:solution} + {key}',
          ids['fsc-ranked']['selectScope'] == 'solution' and ids['fsc-ranked']['selectedValue'] == '{scope:solution}' and ids['fsc-ranked']['selectField'] == 'solution'
          and '{scope:solution}' in ids['fsc-breakdown']['dataPath'] and '{key}' in ids['fsc-breakdown']['dataPath'] and '{key}' in ids['fsc-ranked']['dataPath'] and ids['fsc-breakdown']['emptyText'])
    ranked_row = [r for r in __import__('cmod.cmod_fsc_page', fromlist=['x'])._profile_rows() if any(i['id'] == 'fsc-ranked' for i in r['items'])][0]
    check('fsc-3b: the ranked list (capped 600 px, scrolls inside) and its breakdown sit in ONE row, 6 + 6 segments, marked side-by-side (stacks when narrow)',
          [i['id'] for i in ranked_row['items']] == ['fsc-ranked', 'fsc-breakdown'] and [i['rowSegmentsUsed'] for i in ranked_row['items']] == [6, 6] and ranked_row['cssClass'] == 'side-by-side'
          and ids['fsc-ranked']['maxHeight'] == 600)
    check('fsc-3b: scores read to one decimal through the table\'s fixed format (the data keeps its precision)',
          'score:fixed:1' in ids['fsc-ranked']['columnFormats'] and 'score:fixed:1' in top['columnFormats'] and 'points:fixed:1' in ids['fsc-breakdown']['columnFormats'])
    check('profile tab: the bar chart is a named-graph-panel on the scores door limited to the best twelve',
          ids['fsc-bars']['graphName'] == 'firmware-score-top' and '&profile={key}&limit=12' in ids['fsc-bars']['dataPath'])
    check('every {token} in the template is {key}, {scope:solution} or {scope:rev} (nothing else is left unresolved)',
          all(x in ('key', 'scope:solution', 'scope:rev') for x in re.findall(r'\{([a-z]+(?::[a-z]+)?)\}', json.dumps(tpl))))
    ed = {i['id']: i['componentProps']['inputs'] for i in _tables(d['tabs'][2]['rows'])}
    check('editor tab: step 1 picks a profile (scope `profile`) with a Copy-to-edit action shown for seeded rows; step 2 edits `weight` through POST /api/firmware-score-profiles for the picked profile; step 3 re-ranks',
          ed['fsc-profiles']['selectScope'] == 'profile' and ed['fsc-profiles']['rowAction']['show_when_field'] == 'seeded' and ed['fsc-profiles']['rowAction']['body_template']['copy_of'] == '{name}'
          and ed['fsc-terms']['editFields'] == 'weight' and ed['fsc-terms']['editEnabledField'] == 'editable' and ed['fsc-terms']['editAction']['path'] == '/api/firmware-score-profiles'
          and '{scope:profile}/terms' in ed['fsc-terms']['dataPath'] and 'rev=r{scope:rev}' in ed['fsc-terms']['dataPath'] and 'limit=10' in ed['fsc-reranked']['dataPath'])
    check('the top and ranked tables show the SHORT label; the chart axis is the short label too',
          'top_solution' in top['columns'] and 'label' in ids['fsc-ranked']['columns'] and 'long' not in ids['fsc-ranked']['columns'] and json.loads(__import__('cmod.cmod_fsc_page', fromlist=['x']).FSC_GRAPHS[0]['definition'])['graphConfig']['xDimension'] == 'short_label')

    print('-- the columns exist in the rows the doors serve')
    import falcon
    from falcon import testing
    from cmod.cmod_fsc_api import FscAPI
    app = falcon.App()

    class _FS:
        def add_route(self, path, res, suffix=None):
            app.add_route(path, res, suffix=suffix)
    from cmod.custom.selftest_purpose import _manager
    mgr = _manager()
    with contextlib.redirect_stdout(io.StringIO()):
        FscAPI(polServer=SimpleNamespace(falconServer=_FS()), manager=mgr)
    c = testing.TestClient(app)

    def get(path):
        base, _, q = path.partition('?')
        return c.simulate_get(base, query_string=q)
    prof = get('/api/firmware-score-profiles').json
    first = prof['rows'][0]['name']
    check('profiles door: plain-words weights_text and edit_words on every row (the editor table\'s columns)', all(r['weights_text'] and r['edit_words'] for r in prof['rows']))
    served = {'fsc-top': get('/api/firmware-scores/top?mission=%s' % MISSION).json['rows'][0],
              'fsc-ranked': get('/api/firmware-scores?mission=%s&profile=%s' % (MISSION, first)).json['rows'][0],
              'fsc-profiles': prof['rows'][0]}
    sol = served['fsc-top']['top_solution_name']
    bd = get('/api/firmware-scores/breakdown?mission=%s&solution=%s&profile=%s' % (MISSION, sol, first)).json
    served['fsc-breakdown'] = bd['rows'][0]
    check('breakdown door: `rows` mirrors `terms` (so a table can read it)', bd['rows'] == bd['terms'] and len(bd['rows']) > 0)
    allrows = get('/api/firmware-scores?mission=%s&profile=%s' % (MISSION, first)).json['rows']
    plan = next((r for r in allrows if r['state'] == 'plan'), None)
    if plan:
        pk = {x['label']: x['kind'] for x in get('/api/firmware-scores/breakdown?mission=%s&solution=%s&profile=%s' % (MISSION, plan['solution'], 'fsc-room-to-grow')).json['rows']}
        check('fsc-3b: a PLAN\'s flash / RAM / blocks left read "estimated" (route-sum sizes, never "measured"); pins left stay measured (counted from its assignment)',
              [pk.get('Flash left'), pk.get('RAM left'), pk.get('Chip blocks left'), pk.get('Pins left')] == ['estimated', 'estimated', 'estimated', 'measured'], pk)
    from cmod.custom import fsc_values as V
    done = {'flash-free': {'kind': 'measured', 'basis': 'b'}, 'pins-free': {'kind': 'measured', 'basis': 'b'}}
    V.honest_kinds(done, 'finished')
    check('fsc-3b: a finished solution\'s kinds are left as they are', done['flash-free']['kind'] == 'measured' and done['flash-free']['basis'] == 'b')
    pl = {'flash-free': {'kind': 'measured', 'basis': 'b'}, 'ram-free': {'kind': 'cited', 'basis': 'b'}, 'pins-free': {'kind': 'measured', 'basis': 'b'}}
    V.honest_kinds(pl, 'plan')
    check('fsc-3b: honest_kinds on a plan: measured sizes -> estimated (with the reason), a cited one untouched, pins stay measured and say they are counted from the plan\'s assignment',
          pl['flash-free']['kind'] == 'estimated' and 'PLAN' in pl['flash-free']['basis'] and pl['ram-free']['kind'] == 'cited' and pl['pins-free']['kind'] == 'measured' and 'pin assignment' in pl['pins-free']['basis'])
    lim = get('/api/firmware-scores?mission=%s&profile=%s&limit=12' % (MISSION, first)).json
    ranked = [r for r in lim['rows'] if r['state'] != 'failed']
    check('scores door: limit=12 keeps the 12 best ranked rows, the best first with score 100', len(ranked) == 12 and ranked[0]['rank'] == 1 and ranked[0]['score'] == 100.0)
    check('scores door: `rev` (the page cache-buster) is accepted and changes nothing', get('/api/firmware-scores?mission=%s&profile=%s&limit=12&rev=r5' % (MISSION, first)).json['rows'] == lim['rows'])

    print('-- short labels')
    r0 = lim['rows'][0]
    check('every row has a short label (`label`, also `short_label`): the varying jobs then the board, short, with the long route string kept in `long_label`',
          all(r['label'] == r['short_label'] and 0 < len(r['label']) < 80 and ':' not in r['label'] and '\u00b7' in r['label'] and ':' in r['long_label'] for r in lim['rows']), r0)
    labels = [r['short_label'] for r in get('/api/firmware-scores?mission=%s&profile=%s' % (MISSION, first)).json['rows']]
    check('...and the short labels tell the 380 plans apart well enough to read (%d distinct of %d; the same plan on two boards differs by the board word)' % (len(set(labels)), len(labels)), len(set(labels)) >= len(labels) * 0.9, (len(set(labels)), len(labels)))
    check('top door: top_solution / runner_up are short labels, the route strings are top_routes / runner_up_routes',
          ':' not in served['fsc-top']['top_solution'] and ':' in served['fsc-top']['top_routes'] and ':' not in served['fsc-top']['runner_up'] and ':' in served['fsc-top']['runner_up_routes'])
    from cmod.custom import fsc_doors as D
    from cmod.custom import fsc_run as R
    built = R.build(MISSION, mgr, None, None, 'block')
    fake = dict(built, failures=[{'id': 'x', 'solution': 'msol:x', 'routes': 'a:b', 'short_label': 'a b \u00b7 UNO', 'hardware': 'arduino-uno-r3', 'purpose': 'p', 'reason': 'why', 'state': 'failed'}])
    real = D._built
    D._built = lambda api, response, p: fake
    try:
        with_fail = get('/api/firmware-scores?mission=%s&profile=%s' % (MISSION, first)).json['rows']
        chart = get('/api/firmware-scores?mission=%s&profile=%s&limit=12' % (MISSION, first)).json['rows']
    finally:
        D._built = real
    check('chart call (limit set): failed rows are LEFT OUT (the plain call still lists them last)', with_fail[-1]['state'] == 'failed' and all(r['state'] != 'failed' for r in chart) and len(chart) == 12)

    print('-- the editor: terms door, editing, cache')
    tt = get('/api/firmware-score-profiles/%s/terms' % first).json
    from cmod.custom import fsc_terms as T
    check('terms door (seeded profile): one row per known term + plain words, every row editable:false, weighted terms first', tt['seeded'] and len([r for r in tt['rows'] if not r['purpose']]) == len(T.TERM_NAMES)
          and all(not r['editable'] and r['plain'] and r['label'] for r in tt['rows']) and tt['rows'][0]['in_profile'], tt['rows'][:1])
    check('terms door: an unknown profile is 404 naming the known ones', get('/api/firmware-score-profiles/nope/terms').status_code == 404)
    pp = get('/api/firmware-score-profiles/fsc-uno-r3-per-purpose/terms').json['rows']
    check('terms door: a per-Purpose entry is listed read-only with its Purpose', any(r['purpose'] and not r['editable'] and r['in_profile'] for r in pp))
    post = lambda body: c.simulate_post('/api/firmware-score-profiles', body=json.dumps(body))   # noqa: E731
    seeded_try = post({'name': first, 'weights': {'wires': 1}})
    cp = post({'name': 'my-' + first, 'copy_of': first})
    check('Copy to edit: a seeded profile edit is refused (409) and POST copy_of makes the person\'s own (201)', seeded_try.status_code == 409 and cp.status_code == 201, (seeded_try.status_code, cp.status_code))
    seeded_title = [r for r in prof['rows'] if r['name'] == first][0]['display_name']
    check('fsc-3b: an unnamed copy is titled "My <title>" (no second "%s" tab)' % seeded_title, cp.json['display_name'] == 'My ' + seeded_title, cp.json.get('display_name'))
    named = post({'name': 'named-' + first, 'copy_of': first, 'display_name': 'Chosen name'})
    check('fsc-3b: a copy the person names keeps their name', named.json['display_name'] == 'Chosen name')
    again = post({'name': 'again-' + first, 'copy_of': 'my-' + first})
    check('fsc-3b: a copy of a "My ..." profile is not titled "My My ..."', again.json['display_name'] == 'My ' + seeded_title, again.json.get('display_name'))
    mine = get('/api/firmware-score-profiles/my-%s/terms' % first).json
    check('terms door (own profile): rows are editable:true', not mine['seeded'] and all(r['editable'] for r in mine['rows'] if not r['purpose']))
    from cmod.custom import fsc_score as S
    calls = []
    orig = S.score_profile
    S.score_profile = lambda *a, **k: (calls.append(1), orig(*a, **k))[1]
    try:
        R.clear_scores()
        url = '/api/firmware-scores?mission=%s&profile=my-%s' % (MISSION, first)
        r1 = get(url).json
        n1 = len(calls)
        get(url)
        get(url + '&limit=5')
        get('/api/firmware-scores/breakdown?mission=%s&solution=%s&profile=my-%s' % (MISSION, r1['rows'][0]['solution'], first))
        check('cache: the second scores call, a limit call and a breakdown reuse the first result - the compared set is scored once (%d score_profile call)' % n1, n1 == 1 and len(calls) == 1, (n1, len(calls)))
        other = get('/api/firmware-scores?mission=%s&profile=%s' % (MISSION, first)).json['rows'][0]['solution']
        e = post({'name': 'my-' + first, 'weights': {'mission-cycle': 0.0, 'wires': 1.0, 'flash-free': 1.0}})
        r2 = get(url).json
        check('EDIT: a weight edit POST (200) is served as a fresh ranking at once - the cache key carries the weights, so nothing stale (top solution %s -> %s)' % (r1['rows'][0]['solution'][-10:], r2['rows'][0]['solution'][-10:]),
              e.status_code == 200 and [r['solution'] for r in r2['rows'][:15]] != [r['solution'] for r in r1['rows'][:15]] and len(calls) == 3, (e.status_code, len(calls)))
        check('...and the seeded profile\'s cached result was not disturbed', get('/api/firmware-scores?mission=%s&profile=%s' % (MISSION, first)).json['rows'][0]['solution'] == other and len(calls) == 3, (other[-8:], len(calls)))
        t2 = {r['term']: r['weight'] for r in get('/api/firmware-score-profiles/my-%s/terms' % first).json['rows'] if not r['purpose']}
        check('...and the terms door shows the edited weights (wires 1, mission-cycle 0)', t2['wires'] == 1.0 and t2['mission-cycle'] == 0)
    finally:
        S.score_profile = orig
    check('scores door: a bad limit is refused with words (422)', get('/api/firmware-scores?mission=%s&profile=%s&limit=zero' % (MISSION, first)).status_code == 422)
    allrows = get('/api/firmware-scores?mission=%s' % MISSION).json['rows']
    # the default Mission has no failure: the failed-row keys are fixed by the door (label, failed_purpose, reason, hardware)
    served['fsc-failures'] = next((r for r in allrows if r['state'] == 'failed'), {'label': 1, 'failed_purpose': 1, 'reason': 1, 'hardware': 1})
    served['fsc-terms'] = get('/api/firmware-score-profiles/%s/terms' % first).json['rows'][0]
    served['fsc-reranked'] = served['fsc-ranked']
    miss = {}
    for i in all_tables:
        if i['id'] in served and i['componentProps']['componentName'] == 'class-rows-table':
            gone = [x for x in i['componentProps']['inputs']['columns'].split(',') if x not in served[i['id']]]
            if gone:
                miss[i['id']] = gone
    check('every column a table asks for is a field of the row its door serves', not miss, miss)

    print('-- graph, nav, manifest')
    from cmod.cmod_fsc_page import FSC_GRAPHS
    gc = json.loads(FSC_GRAPHS[0]['definition'])['graphConfig']
    check('the graph row: barX, category = short_label, value = score, named like the panel\'s graphName',
          FSC_GRAPHS[0]['name'] == 'firmware-score-top' and gc['renderStyle'] == 'barX' and gc['xDimension'] == 'short_label' and gc['yDimensions'] == ['score'])
    from cmod.cmod_seed import CMOD_SEED_PAIRS
    check('the graph converges through CMOD_SEED_PAIRS as a GraphDefinition', any(n == 'GraphDefinition' and any(r['name'] == 'firmware-score-top' for r in rows) for n, _c, rows in CMOD_SEED_PAIRS))
    from polariapps.apps_seed import SEED_POLARI_APPS
    check('the page is in the app navigation', '/display/firmware-scores' in json.dumps(SEED_POLARI_APPS, default=str))
    m = json.load(open(os.path.join(os.path.dirname(__file__), 'polari-app.json')))['files']
    check('polari-app.json lists the page and this selftest', 'cmod_fsc_page' in m['page'] and 'cmod_fsc_page_selftest' in m['selftests'])
    print('\n%d/%d checks passed' % (passed, total))
    return 0 if passed == total else 1


if __name__ == '__main__':
    sys.exit(main())
