"""
@module board.bench_solutions_page

bss-6 owed piece (AI-Notes/plans/BENCH_SOLUTION_SIM_PLAN.md section 5b "see the bench here"): `/display/bench-solutions` - every Bench Solution, whether it is
whole and why not, and THE BENCH AT A NODE: pick a Bench Solution, a node of its topology and one of the node's runs (or arrive with
?bench_solution=...&node=...&run=... from a node's card on the canvas) and read what the run saw on arrival: every watched struct field's first and last
value and when it changed, every edge's stimulus and met cycle, its executions and collaterals. Configured tables only; no new component.

  Whole      the five legs of the chosen Bench Solution (system, hardware, firmware, thermal, conditions): ok or why not, in words
  At a node  the nodes of its topology (click one) -> the node's runs (click one) -> the run's signals and edges
Doors: /api/board/bench-solutions[/{name}/legs], /api/cmod/bench-topology/{bs}/coverage/nodes, /api/cmod/bench-topology/{bs}/nodes/{slug}/runs,
/api/cmod/bench-topology/{bs}/runs/{run}/signals|edges.
"""
from polariApiServer.module_pages_seed import _page, _row, _table, _tab

_BS = '{scope:bench_solution}'
_REV = 'rev=r{scope:rev}'
_T = '/api/cmod/bench-topology/%s' % _BS
_PICK = 'Pick a Bench Solution above first.'


def _picker_row():
    return _row(0, [_table('bsol-list', 0, 12, 'Bench Solutions - click one', '',
                           description='One row per Bench Solution: everything on a bench bound as a whole (its Bench System, Hardware, Firmware and Thermal Solutions and the '
                                       'conditions). whole = every leg exists, is complete and matches the Bench System. Click a row to choose it (click again to clear).',
                           columns='name,title,whole,missing', data_path='/api/board/bench-solutions?' + _REV,
                           select_field='name', select_scope='bench_solution', selected_value=_BS)], min_height=180)


def _whole_tab():
    return _tab('whole', 'Whole?', [
        _row(0, [_table('bsol-legs', 0, 12, 'The five legs', '',
                        description='One row per leg of the chosen Bench Solution: the Bench System it realises, its Hardware Solution (of the composed Hardware System, complete), '
                                    'its Firmware Solution (built on the composed graph), its Thermal Solution (following the composed Thermal System, with allowed mitigations '
                                    'only) and its conditions (inside the Thermal System\'s range). ok or the words saying why not.',
                        columns='leg,ref,ok,why', data_path='/api/board/bench-solutions/%s/legs?%s' % (_BS, _REV), empty_text=_PICK)], min_height=260)],
        description='Is this Bench Solution whole? Each leg says so, or says what is missing.')


def _node_tab():
    return _tab('node', 'At a node', [
        _row(0, [_table('bsol-nodes', 0, 12, 'Nodes of its topology - click one', '',
                        description='One row per node (a named situation of the bench: what certain struct fields must be) with its confirmation state and runs.',
                        columns='node,title,kind,state,runs,last_outcome,paths_tested,paths,confirmed_by', data_path=_T + '/coverage/nodes?' + _REV, empty_text=_PICK,
                        select_field='node', select_scope='node', selected_value='{scope:node}')], min_height=240),
        _row(1, [_table('bsol-runs', 0, 12, 'Its runs - click one', '',
                        description='The chosen node\'s runs from the root along a path: outcome, the duration of the last edge and what set it, the step and what asked for it.',
                        columns='name,outcome,path,duration_s,duration_set_by,step_s,step_set_by,hex_sha256,ran_at', data_path='/api/cmod/bench-topology/%s/nodes/{scope:node_slug}/runs?%s' % (_BS, _REV),
                        empty_text='Pick a node above.', select_field='name', select_scope='run', selected_value='{scope:run}')], min_height=220),
        _row(2, [_table('bsol-signals', 0, 6, 'The structs on arrival', '',
                        description='One row per watched struct field (and wired pin) in the chosen run: its first and last value, how many times it changed, the cycles of its '
                                    'first and last change. This is the bench\'s state at the node as the run saw it; the trace itself was the working buffer.',
                        columns='kind,signal,first,last,changes,first_change_cycle,last_change_cycle', data_path=_T + '/runs/{scope:run}/signals?' + _REV, empty_text='Pick a run above.'),
                 _table('bsol-edges', 6, 6, 'The edges as they ran', '',
                        description='One row per edge of the run: the cycle its trigger was applied, the cycle the next node\'s requirements were met, the duration, the executions '
                                    'observed and the collaterals measured, in words.',
                        columns='order,edge,outcome,stimulus_cycle,met_cycle,duration_s,executions,collaterals,words', data_path=_T + '/runs/{scope:run}/edges?' + _REV,
                        empty_text='Pick a run above.')], min_height=300)],
        description='The bench as one run saw it when it arrived at a node: struct values, pins, timings.')


BENCH_SOLUTIONS_PAGES = [
    _page('bench-solutions', 'bench-solutions',
          'Every Bench Solution: whole or what is missing, and the bench at a node of its topology as a run saw it. Doors: /api/board/bench-solutions[/{name}/legs], '
          '/api/cmod/bench-topology/{bs}/coverage/nodes, .../nodes/{slug}/runs, .../runs/{run}/signals|edges.',
          'BenchSolution', [_picker_row()], title='Bench solutions', tabs=[_whole_tab(), _node_tab()], scope_query=['bench_solution', 'node', 'node_slug', 'run']),
]
