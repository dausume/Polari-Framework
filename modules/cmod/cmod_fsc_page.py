"""
@module cmod.cmod_fsc_page

/display/firmware-scores (fsc-3): the Firmware Scores page, as a TABBED configured page (the generic tabs feature of module_pages_seed: `_tab` / `_tabs_from`).
No raw JSON, no custom component: configured tables over the fsc doors (cmod.custom.fsc_doors) and one configured bar graph (named-graph-panel -> the graph home).

    tab "Top scorers"     the landing tab: one row per profile - its top solution, the runner-up, the compared set. Click a row -> that profile's tab.
    one tab per profile   GENERATED from GET /api/firmware-score-profiles (his own saved profiles add tabs): every non-failed solution ranked top (100) to bottom (0);
                          click a row -> how its score was worked out (term by term); click it again, or press Escape, to close; a bar graph of the best twelve.
    tab "Failures"        the solutions that do not fulfil every Purpose, with the Purpose and why. They get no score.
    tab "Profile editor"  every profile and its weights; editing is the CLI (`pol firmware profile create|weight`) - see the table's description.

The selected solution is the page SCOPE key `solution` ({scope:solution}): the ranking table sets it, the breakdown table reads it.
"""
import json

from polariApiServer.module_pages_seed import _page, _row, _table, _tab, _tabs_from

MISSION = 'uno-light-mission'
GRAPH = 'firmware-score-top'

_COMPETITIVE = ('Scores are competitive: for each measured term the best of the compared set gets 100 and the worst 0, and then each profile is scaled the same way, '
                'so the top solution reads 100 and the bottom reads 0. A failed solution is never scored.')
_STATE = 'finished (built and every Purpose proven) or plan (a possible solution, estimated, not built yet)'


def _graph_panel(item_id, index, segments, title, graph_name, data_path, description=''):
    return {'id': item_id, 'index': index, 'type': 'component', 'rowSegmentsUsed': segments, 'gridColumnStart': None, 'title': title, 'description': description,
            'visible': True, 'collapsed': False, 'cssClass': '',
            'componentProps': {'componentName': 'named-graph-panel', 'inputs': {'graphName': graph_name, 'dataPath': data_path}},
            'item': None, 'nestedRows': []}


FSC_GRAPHS = [{
    'name': GRAPH, 'source_class': 'ScoreConcept',
    'description': 'The twelve best solutions for one firmware score profile, as bars (score 0-100, rank 1 is the best). The twelve are the top of the ranked table beside it.',
    'definition': json.dumps({'graphConfig': {
        'renderStyle': 'barX', 'xDimension': 'rank', 'yDimensions': ['score'], 'seriesColors': [],
        'options': {'width': 800, 'height': 320, 'marginTop': 20, 'marginRight': 30, 'marginBottom': 40, 'marginLeft': 60, 'showLegend': False, 'showGrid': True,
                    'xLabel': 'score (best = 100)', 'yLabel': 'rank (1 = best)'},
        'aggregation': {'enabled': False, 'strategy': 'average'}}})}]


def _top_tab():
    return _tab('top', 'Top scorers', [
        _row(0, [_table('fsc-top', 0, 12, 'The top scorer of each profile', '',
                        description='What this is for: the winner of every way of scoring a firmware solution, side by side. One row = one profile (a profile is a set of weights, such as '
                                    'Fastest or Cheapest). Columns: profile title; top solution (the routes it uses for each job) and whether it is finished or only a plan; score (the top '
                                    'always reads 100); runner up and runner up score (how close the second best is); compared set (which solutions competed); failed count (solutions '
                                    'kept out because they do not fulfil every Purpose). ' + _COMPETITIVE + ' Click a row to open that profile\'s tab.',
                        columns='profile_title,top_solution,top_state,score,runner_up,runner_up_score,compared_set,failed_count',
                        data_path='/api/firmware-scores/top?mission=%s' % MISSION, row_link_tab_field='profile')], min_height=260),
    ])


def _profile_rows():
    """The rows of ONE profile tab; `{key}` is the profile's name (templated by the page), `{scope:solution}` the picked solution."""
    ranked = '/api/firmware-scores?mission=%s&profile={key}' % MISSION
    return [
        _row(0, [_table('fsc-ranked', 0, 12, 'Every solution, best to worst', '',
                        description='What this is for: the full ranking under this profile. One row = one non-failed solution. Columns: rank (1 = best); label (the routes chosen for each '
                                    'job); solution (its name); score (0-100, competitive); state (' + _STATE + '); deciding terms (what earned most of its points). ' + _COMPETITIVE +
                                    ' Click a row to see how its score was worked out below; click it again, or press Escape, to close.',
                        columns='rank,label,solution,score,state,deciding_terms',
                        data_path=ranked, filter_field='state', filter_value='finished,plan',
                        select_field='solution', select_scope='solution', selected_value='{scope:solution}',
                        empty_text='No solution can be scored yet.')], min_height=300),
        _row(1, [_table('fsc-breakdown', 0, 12, 'How the picked solution\'s score was worked out', '',
                        description='What this is for: the term-by-term working behind one score. One row = one term of this profile (for example cycle time or cost). Columns: label (the term); '
                                    'value and unit (what was measured, estimated or cited); kind (measured | cited | estimated | undetermined); normalized (0-100 among the compared set: best 100, '
                                    'worst 0); weight (how much this profile cares); points (normalized x weight share, summing to the raw score); basis (where the value comes from).',
                        columns='label,value,unit,kind,normalized,weight,points,basis',
                        data_path='/api/firmware-scores/breakdown?mission=%s&solution={scope:solution}&profile={key}' % MISSION,
                        empty_text='Click a solution in the table above to see how its score was worked out.')], min_height=200),
        _row(2, [_graph_panel('fsc-bars', 0, 12, 'The twelve best, as bars',
                              GRAPH, '/api/firmware-scores?mission=%s&profile={key}&limit=12' % MISSION,
                              description='What this is for: how far apart the leaders are. One bar = one solution, longest = rank 1 (score 100). The numbers are the ranked table\'s score column.')],
             min_height=360),
    ]


def _failures_tab():
    return _tab('failures', 'Failures', [
        _row(0, [_table('fsc-failures', 0, 12, 'Solutions that do not fulfil every Purpose', '',
                        description='What this is for: the solutions kept out of every ranking. One row = one failed solution. Columns: label (its routes); failed purpose (the Purpose it does not '
                                    'fulfil, such as a safety-critical deadline it misses); reason (why, in words); hardware (the board). A failed solution gets no score: it never enters the '
                                    'compared set.',
                        columns='label,failed_purpose,reason,hardware',
                        data_path='/api/firmware-scores?mission=%s' % MISSION, filter_field='state', filter_value='failed',
                        empty_text='No solution fails a Purpose right now.')], min_height=220),
    ])


def _editor_tab():
    return _tab('profile-editor', 'Profile editor', [
        _row(0, [_table('fsc-profiles', 0, 12, 'Profiles and their weights', '',
                        description='What this is for: see every way of scoring and what each one cares about. One row = one profile. Columns: display name; description; seeded (shipped with '
                                    'Polari: never edited in place); weights text (each term and its weight - a higher weight means that term decides more); edit words (what you may do). '
                                    'To make your own, copy a profile and set its weights from the command line: `pol firmware profile create my-profile --copy-of fsc-fastest --weight '
                                    'mission-cycle=0.7 --weight confidence=0.3`, then change them later with `pol firmware profile weight my-profile mission-cycle=0.5`. A new profile gets '
                                    'its own tab here.',
                        columns='display_name,description,seeded,weights_text,edit_words,hardware',
                        data_path='/api/firmware-score-profiles')], min_height=260),
    ])


FSC_PAGES = [
    _page('firmware-scores', 'firmware-scores',
          'Firmware Scores - which firmware solution wins, under each way of scoring. The first tab shows the top scorer of every profile; each profile has its own tab ranking '
          'every solution from 100 down to 0; Failures lists the solutions that do not fulfil every Purpose; Profile editor lists the weights. The doors: GET /api/firmware-scores, '
          '/api/firmware-scores/top, /api/firmware-scores/breakdown, /api/firmware-score-profiles. From the command line: pol firmware scores.',
          'ScoreConcept', [],
          title='Firmware Scores',
          tabs=[_top_tab(), _failures_tab(), _editor_tab()],
          tabs_from=_tabs_from('/api/firmware-score-profiles', 'name', 'display_name', _profile_rows(), insert_at=1)),
]
