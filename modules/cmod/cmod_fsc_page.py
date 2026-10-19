"""
@module cmod.cmod_fsc_page

/display/firmware-scores (fsc-3): the Firmware Scores page, as a TABBED configured page (the generic tabs feature of module_pages_seed: `_tab` / `_tabs_from`).
No raw JSON, no custom component: configured tables over the fsc doors (cmod.custom.fsc_doors) and one configured bar graph (named-graph-panel -> the graph home).

    tab "Top scorers"     the landing tab: one row per profile - its top solution, the runner-up, the compared set. Click a row -> that profile's tab. Below it: the SAMPLE SET (smp-0), one row per
                          curated example (S = a success on some device / component, F = a failure) with its state read from the build: finished | built, not finished | not built yet | failed.
    one tab per profile   GENERATED from GET /api/firmware-score-profiles (his own saved profiles add tabs): the SAMPLE's finished solutions ranked top (100) to bottom (0) - the curated set, not hundreds of rows;
                          click a row -> how its score was worked out (term by term); click it again, or press Escape, to close; a bar graph of the best twelve.
    tab "Possible plans (not built)"   the solver's search, kept but out of the way: every enumerated plan nobody has built, ranked for ONE profile you pick (scope=plans). Estimates only.
    tab "Failures"        the sample's failure entries, with the Purpose and why. They get no score. Built configs outside the sample are kept as history (scope=all lists them).
    tab "Profile editor"  pick a profile (a seeded one is copied first), edit its term weights in the table, watch the ranking change. The CLI (`pol firmware profile create|weight`) does the same.

The selected solution is the page SCOPE key `solution` ({scope:solution}): the ranking table sets it, the breakdown table reads it. The editor uses scope `profile`; every edit or copy bumps scope `rev`, which the tables' `rev=r{scope:rev}` paths read so they fetch again.
"""
import json

from polariApiServer.module_pages_seed import _page, _row, _table, _tab, _tabs_from

MISSION = 'uno-light-mission'
GRAPH = 'firmware-score-top'
RANKED_MAX_HEIGHT = 600     # px: the ranked list (hundreds of rows) scrolls inside its own box, so the breakdown beside it stays in view

_COMPETITIVE = ('Scores are competitive: for each measured term the best of the compared set gets 100 and the worst 0, and then each profile is scaled the same way, '
                'so the top solution reads 100 and the bottom reads 0. A failed solution is never scored.')
_STATE = 'finished (built and every Purpose proven) or plan (a possible solution, estimated, not built yet)'
_SAMPLE = ('the curated SAMPLE of this Mission: its finished successes (S1, S2, ...) compete; its failure entries (F1, F2) are the only failures; every other built config is kept as history')


def _graph_panel(item_id, index, segments, title, graph_name, data_path, description=''):
    return {'id': item_id, 'index': index, 'type': 'component', 'rowSegmentsUsed': segments, 'gridColumnStart': None, 'title': title, 'description': description,
            'visible': True, 'collapsed': False, 'cssClass': '',
            'componentProps': {'componentName': 'named-graph-panel', 'inputs': {'graphName': graph_name, 'dataPath': data_path}},
            'item': None, 'nestedRows': []}


FSC_GRAPHS = [{
    'name': GRAPH, 'source_class': 'ScoreConcept',
    'description': 'The twelve best solutions for one firmware score profile, as bars (score 0-100, rank 1 is the best). Only scored solutions are drawn (never a failed one). The twelve are the top of the ranked table beside it.',
    'definition': json.dumps({'graphConfig': {
        'renderStyle': 'barX', 'xDimension': 'short_label', 'yDimensions': ['score'], 'seriesColors': [],
        'options': {'width': 1000, 'height': 360, 'marginTop': 20, 'marginRight': 30, 'marginBottom': 40, 'marginLeft': 420, 'showLegend': False, 'showGrid': True, 'categoryOrder': 'data',
                    'xLabel': 'score (best = 100)', 'yLabel': 'solution (best first)'},
        'aggregation': {'enabled': False, 'strategy': 'average'}}})}]


def _top_tab():
    return _tab('top', 'Top scorers', [
        _row(0, [_table('fsc-top', 0, 12, 'The top scorer of each profile', '',
                        description='What this is for: the winner of every way of scoring a firmware solution, side by side. One row = one profile (a profile is a set of weights, such as '
                                    'Fastest or Cheapest). Columns: profile title; top solution (S1.. = its place in the sample, then a short label: the route chosen for each job, then the board) and whether it is finished; score (the top '
                                    'always reads 100); runner up and runner up score (how close the second best is); compared set (' + _SAMPLE + '); failed count (the sample\'s failure entries, kept '
                                    'out because they do not fulfil every Purpose). ' + _COMPETITIVE + ' Click a row to open that profile\'s tab.',
                        columns='profile_title,top_solution,top_state,score,runner_up,runner_up_score,compared_set,failed_count',
                        column_formats='score:fixed:1,runner_up_score:fixed:1',
                        data_path='/api/firmware-scores/top?mission=%s' % MISSION, row_link_tab_field='profile')], min_height=260),
        _row(1, [_table('fsc-sample', 0, 12, 'The sample set: one example per kind of device and component', '',
                        description='What this is for: the curated examples this project uses to show how to use those components while managing the state of an LED through the struct. One row = one example. Columns: id (S = a '
                                    'success, F = a failure); device; config (the firmware build); components (what it shows); state (finished = built and every Purpose proven on its own build | built, not finished | not built yet, '
                                    'which is not a failure | failed); outcome (the proof, or the plain-words reason it fails). The successes that are finished compete on the profile tabs; the failures are listed on the Failures tab.',
                        columns='id,device,config,components,state,outcome',
                        data_path='/api/firmware-scores/sample?mission=%s' % MISSION,
                        empty_text='This Mission has no curated sample.')], min_height=300),
    ])


def _profile_rows():
    """The rows of ONE profile tab; `{key}` is the profile's name (templated by the page), `{scope:solution}` the picked solution."""
    ranked = '/api/firmware-scores?mission=%s&profile={key}&rev=r{scope:rev}' % MISSION
    return [
        _row(0, [_table('fsc-ranked', 0, 6, 'The sample, best to worst', '',
                        description='What this is for: the ranking of the sample under this profile (' + _SAMPLE + '). One row = one finished sample solution. Columns: rank (1 = best); label (S1.. its place in the sample, then the '
                                    'route chosen for each job and the board); score (0-100, competitive, shown to one decimal); state (' + _STATE + '); deciding terms (what earned most of its points); solution (its full name). ' + _COMPETITIVE +
                                    ' The list scrolls inside its own box. Click a row to see how its score was worked out beside it (below it on a narrow page); click it again, or press Escape, to close.',
                        columns='rank,label,score,state,deciding_terms,solution', column_formats='score:fixed:1', max_height=RANKED_MAX_HEIGHT,
                        data_path=ranked, filter_field='state', filter_value='finished,plan',
                        select_field='solution', select_scope='solution', selected_value='{scope:solution}',
                        empty_text='No sample solution is finished yet, so nothing can be scored.'),
                 _table('fsc-breakdown', 1, 6, 'How the picked solution\'s score was worked out', '',
                        description='What this is for: the term-by-term working behind one score. One row = one term of this profile (for example cycle time or cost). Columns: label (the term); '
                                    'value and unit (what was measured, estimated or cited); kind (measured | cited | estimated | undetermined); '
                                    'normalized (0-100 among the compared set: best 100, worst 0); weight (how much this profile cares); points (normalized x weight share, summing to the raw score); basis (where the value comes from).',
                        columns='label,value,unit,kind,normalized,weight,points,basis', column_formats='normalized:fixed:1,points:fixed:1', max_height=RANKED_MAX_HEIGHT,
                        data_path='/api/firmware-scores/breakdown?mission=%s&solution={scope:solution}&profile={key}' % MISSION,
                        empty_text='Click a solution in the ranked list to see how its score was worked out.')],
             min_height=300, css_class='side-by-side'),
        _row(1, [_graph_panel('fsc-bars', 0, 12, 'The twelve best, as bars',
                              GRAPH, '/api/firmware-scores?mission=%s&profile={key}&limit=12&rev=r{scope:rev}' % MISSION,
                              description='What this is for: how far apart the leaders are. One bar = one scored solution, labelled with its short label, longest = rank 1 (score 100). The numbers are the ranked table\'s score column.')],
             min_height=360),
    ]


def _plans_tab():
    """smp-0: the solver's search, kept but out of the way. Step 1 picks the profile, step 2 ranks the plans nobody built (scope=plans) under it, beside the term-by-term working of the picked plan."""
    ranked = '/api/firmware-scores?mission=%s&profile={scope:plansprofile}&scope=plans&rev=r{scope:rev}' % MISSION
    return _tab('plans', 'Possible plans (not built)', [
        _row(0, [_table('fsc-plans-profiles', 0, 12, 'Step 1: pick a profile to rank the plans by', '',
                        description='What this is for: the plans below are the SOLVER\'S SEARCH - every way the Mission\'s jobs could be done on the known boards, each an estimate that nobody has built or proven. They are kept out of the '
                                    'sample and out of the other tabs. Pick the way of scoring to rank them by. One row = one profile. Columns: display name; description; weights text. Click a row to pick it '
                                    '(click it again, or press Escape, to put it down).',
                        columns='display_name,description,weights_text',
                        data_path='/api/firmware-score-profiles?rev=r{scope:rev}', select_field='name', select_scope='plansprofile', selected_value='{scope:plansprofile}')], min_height=240),
        _row(1, [_table('fsc-plans-ranked', 0, 6, 'Step 2: the plans, best to worst under that profile', '',
                        description='What this is for: which UNBUILT plans the solver would favour under the picked profile. One row = one plan (never built, never proven: every number is an estimate). Columns: rank (1 = best); label (the '
                                    'route chosen for each job that varies, then the board); score (0-100 among these plans only: the best plan reads 100, the worst 0); state (plan); deciding terms; solution (its full name). '
                                    + _COMPETITIVE + ' Click a row to see how its score was worked out beside it.',
                        columns='rank,label,score,state,deciding_terms,solution', column_formats='score:fixed:1', max_height=RANKED_MAX_HEIGHT,
                        data_path=ranked, filter_field='state', filter_value='plan,finished',
                        select_field='solution', select_scope='plansolution', selected_value='{scope:plansolution}',
                        empty_text='Pick a profile in step 1 to rank the plans.'),
                 _table('fsc-plans-breakdown', 1, 6, 'How the picked plan\'s score was worked out', '',
                        description='What this is for: the term-by-term working behind one plan\'s score. One row = one term of the picked profile. Columns: label (the term); value and unit (a plan\'s sizes are estimates, its counted pins '
                                    'stay measured); kind (measured | cited | estimated | undetermined); normalized (0-100 among the plans: best 100, worst 0); weight; points (normalized x weight share, summing to the raw score); basis.',
                        columns='label,value,unit,kind,normalized,weight,points,basis', column_formats='normalized:fixed:1,points:fixed:1', max_height=RANKED_MAX_HEIGHT,
                        data_path='/api/firmware-scores/breakdown?mission=%s&solution={scope:plansolution}&profile={scope:plansprofile}&scope=plans' % MISSION,
                        empty_text='Click a plan in the ranked list to see how its score was worked out.')],
             min_height=300, css_class='side-by-side'),
    ])


def _failures_tab():
    return _tab('failures', 'Failures', [
        _row(0, [_table('fsc-failures', 0, 12, 'The sample\'s failures: solutions that do not fulfil every Purpose', '',
                        description='What this is for: the failure examples of the sample, kept out of every ranking. One row = one failed example (F1, F2). Columns: label (its routes); failed purpose (the Purpose it does not '
                                    'fulfil, such as a safety-critical deadline it misses); reason (why, in words, with the measured time and the deadline); hardware (the board). A failed solution gets no score: it never enters the '
                                    'compared set. Built configs that are not in the sample are kept as history, not listed here.',
                        columns='label,failed_purpose,reason,hardware',
                        data_path='/api/firmware-scores?mission=%s' % MISSION, filter_field='state', filter_value='failed',
                        empty_text='No solution fails a Purpose right now.')], min_height=220),
    ])


def _editor_tab():
    profiles = '/api/firmware-score-profiles?rev=r{scope:rev}'
    return _tab('profile-editor', 'Profile editor', [
        _row(0, [_table('fsc-profiles', 0, 12, 'Step 1: pick a profile', '',
                        description='What this is for: choose which way of scoring to look at or change. One row = one profile. Columns: display name; description; seeded (shipped with Polari: it is never '
                                    'edited in place - press "Copy to edit" to make your own copy, named my- followed by its name); weights text (each term and its weight). Click a row to pick it '
                                    '(click it again, or press Escape, to put it down).',
                        columns='display_name,description,seeded,weights_text',
                        data_path=profiles, select_field='name', select_scope='profile', selected_value='{scope:profile}',
                        row_action={'label': 'Copy to edit', 'method': 'POST', 'path': '/api/firmware-score-profiles', 'show_when_field': 'seeded',
                                    'body_template': {'name': 'my-{name}', 'copy_of': '{name}'}, 'then_scope': {'key': 'profile', 'from': 'name'}})], min_height=260),
        _row(1, [_table('fsc-terms', 0, 12, 'Step 2: set the weights', '',
                        description='What this is for: say how much each term decides, for the picked profile. One row = one term. Columns: label (the term); plain (what it measures); unit; purpose (set '
                                    'only when the weight applies to one Purpose; those rows are read-only here); weight (type a number of 0 or more and press Enter or leave the box: a bigger number '
                                    'means that term decides more; 0 takes the term out). A seeded profile\'s weights are read-only: copy it in step 1 first. Saving re-scores at once; see step 3.',
                        columns='label,plain,unit,purpose,weight',
                        data_path='/api/firmware-score-profiles/{scope:profile}/terms?rev=r{scope:rev}',
                        edit_fields='weight', edit_enabled_field='editable',
                        edit_action={'method': 'POST', 'path': '/api/firmware-score-profiles', 'body_template': {'name': '{profile}', 'weights': {'{term}': '{value}'}}},
                        empty_text='Pick a profile in step 1 to see its weights.')], min_height=300),
        _row(2, [_table('fsc-reranked', 0, 12, 'Step 3: the ten best under the picked profile', '',
                        description='What this is for: see a weight change take effect. One row = one of the ten best-scoring solutions under the picked profile, best first. Columns: rank; label (short); '
                                    'score (0-100, competitive: the best of the compared set reads 100, the worst 0); state (finished or plan); deciding terms. Change a weight in step 2 and this list '
                                    're-ranks.',
                        columns='rank,label,score,state,deciding_terms', column_formats='score:fixed:1',
                        data_path='/api/firmware-scores?mission=%s&profile={scope:profile}&limit=10&rev=r{scope:rev}' % MISSION,
                        empty_text='Pick a profile in step 1 to see how it ranks the solutions.')], min_height=260),
    ])


FSC_PAGES = [
    _page('firmware-scores', 'firmware-scores',
          'Firmware Scores - which firmware solution wins, under each way of scoring, among a curated SAMPLE of examples (successes on different devices and components, and two failures). The first tab shows the top scorer '
          'of every profile and the sample set; each profile has its own tab ranking the finished sample solutions from 100 down to 0; Possible plans (not built) is the solver\'s search, kept out of the way; Failures lists the '
          'sample\'s failures; Profile editor lists the weights. The doors: GET /api/firmware-scores (scope=sample|all|plans|finished), /api/firmware-scores/top, /api/firmware-scores/sample, '
          '/api/firmware-scores/breakdown, /api/firmware-score-profiles. From the command line: pol firmware scores.',
          'ScoreConcept', [],
          title='Firmware Scores',
          tabs=[_top_tab(), _plans_tab(), _failures_tab(), _editor_tab()],
          tabs_from=_tabs_from('/api/firmware-score-profiles', 'name', 'display_name', _profile_rows(), insert_at=1)),
]
