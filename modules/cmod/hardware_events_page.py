"""
@module cmod.hardware_events_page

bss-6 (AI-Notes/plans/BENCH_SOLUTION_SIM_PLAN.md section 5b): `/display/hardware-events` - a Bench Solution's Hardware Event topology as ONE page of configured
tables (no raw JSON; no new component): what was tested, and what was NOT, first. The Bench Solution picker sits above the tabs; every click sets the page
scope the tables below read.

  Overview    the untested list FIRST (an empty list is the only green), then the coverage strip as rows (its last row is the route to the drawing on the no-code canvas)
  Nodes       one row per node: its confirmation state, runs, paths tested / all, who confirmed it, voided confirmations, what blocks it, collaterals measured;
              click one -> its runs, its confirmations
  Events      the Hardware Events the Bench Solution offers (derived from the firmware's own assertions + a person's): used by an edge? ever run?
  Runs        every run across the topology, newest first: outcome, duration and what set it, step and what set it, the build
  Assertions  the firmware's own claims (Catom assertions): exercised by a run that met its node, or not, and how
  Profiles    the manual test profiles and their items
Linkable: /display/hardware-events?bench_solution=uno-light-on-desk&node=... (scope_query). Doors: /api/board/bench-solutions, /api/cmod/bench-topology/{bs}/coverage[/...],
/api/cmod/bench-topology/{bs}/nodes/{slug}/runs|confirmations, /api/cmod/bench-topology/{bs}/profiles.
"""
from polariApiServer.module_pages_seed import _page, _row, _table, _tab

_BS = '{scope:bench_solution}'
_REV = 'rev=r{scope:rev}'
_T = '/api/cmod/bench-topology/%s' % _BS
_PICK = 'Pick a Bench Solution above first.'


def _picker_row():
    return _row(0, [_table('he-bench-solutions', 0, 12, 'Bench Solutions - click one', '',
                           description='One row per Bench Solution (everything on a bench bound as a whole). whole = its Hardware, Firmware and Thermal Solutions all exist and '
                                       'match its Bench System; missing = how many things do not. Click a row to make it THE Bench Solution of every tab below (click again to clear).',
                           columns='name,title,whole,missing', data_path='/api/board/bench-solutions?' + _REV,
                           select_field='name', select_scope='bench_solution', selected_value=_BS)], min_height=180)


def _overview_tab():
    return _tab('overview', 'Overview', [
        _row(0, [_table('he-untested', 0, 12, 'Not tested yet - this list first', '',
                        description='One row per thing the topology has NOT shown: a node never tested, one with only voided confirmations (the build changed), one confirmed by '
                                    'fewer paths than it has, a blocked node and the field that blocks it, a collateral never measured, an event no edge uses, a claim of the '
                                    'firmware no run exercised, a proposed node not yet accepted. An empty list is the only green.',
                        columns='words', data_path=_T + '/coverage/untested?' + _REV, empty_text=_PICK)], min_height=220),
        _row(1, [_table('he-strip', 0, 12, 'What was tested', '',
                        description='The coverage strip as rows: nodes by confirmation state, paths tested, struct fields changed by a run that met its node, declared sample '
                                    'values used, the firmware\'s claims exercised, and the offered events by kind and source (used by an edge, ever run).',
                        columns='measure,value,words', data_path=_T + '/coverage/strip-rows?' + _REV, empty_text=_PICK)], min_height=260)],
        description='What this Bench Solution\'s topology has tested, and what it has not - the untested list comes first.')


def _nodes_tab():
    return _tab('nodes', 'Nodes', [
        _row(0, [_table('he-nodes', 0, 12, 'Nodes - click one', '',
                        description='One row per node of the topology (a named situation: what certain struct fields must be). state = confirmed by hardware / twin / person, '
                                    'checks-failed, diverged, not-reached, blocked, voided, never-tested, proposed, root. paths = tested / all (a node is tested along a path from '
                                    'the root). stale = its latest run is on another build than its confirmation.',
                        columns='node,title,kind,basis,state,runs,last_outcome,paths_tested,paths,confirmed_by,voided,blocked,collaterals_measured,stale',
                        data_path=_T + '/coverage/nodes?' + _REV, empty_text=_PICK, select_field='node', select_scope='node', selected_value='{scope:node}')], min_height=280),
        _row(1, [_table('he-node-runs', 0, 6, 'Its runs', '',
                        description='Every run of the chosen node, in order: outcome, how long the last edge took and what set it, the step and what asked for it, the build.',
                        columns='name,outcome,path,duration_s,duration_set_by,step_s,step_set_by,hex_sha256,profile,words', data_path='/api/cmod/bench-topology/%s/nodes/{scope:node_slug}/runs?%s' % (_BS, _REV),
                        empty_text='Pick a node above.'),
                 _table('he-node-confs', 6, 6, 'Its confirmations', '',
                        description='Who says this node was reached, on which build: the twin (a run), hardware (a record), a person (attested); voided ones kept and marked.',
                        columns='name,by,state,path,hex_sha256,who,words,voided_why,at', data_path='/api/cmod/bench-topology/%s/nodes/{scope:node_slug}/confirmations?%s' % (_BS, _REV),
                        empty_text='Pick a node above.')], min_height=280)],
        description='Every node, its confirmation state, and what has or has not been done to it.')


def _events_tab():
    return _tab('events', 'Events', [
        _row(0, [_table('he-events', 0, 12, 'Hardware Events this Bench Solution offers', '',
                        description='One row per Hardware Event: an actuation (a person, the environment or time) or an external signal (a command through a bridge, another '
                                    'board, a harness), derived from the firmware\'s own assertions and HAL values, or added by a person. used_by_an_edge / ever_run say whether '
                                    'the topology uses it and whether a run has applied it.',
                        columns='name,title,kind,source,what,value,origin,used_by_an_edge,ever_run', data_path=_T + '/coverage/events?' + _REV, empty_text=_PICK)], min_height=300)],
        description='What can happen to the bench from outside the code, and whether the topology has used it.')


def _runs_tab():
    return _tab('runs', 'Runs', [
        _row(0, [_table('he-runs', 0, 12, 'Every run, newest first', '',
                        description='One row per node run across the topology: the node, the path, the outcome, the duration of the last edge and what set it, the step and '
                                    'what asked for it, the build it ran on, the profile it watched with.',
                        columns='name,node,outcome,duration_s,duration_set_by,step_s,step_set_by,hex_sha256,profile,play_from,ran_at,words', data_path=_T + '/coverage/runs?' + _REV,
                        empty_text=_PICK)], min_height=320)],
        description='The kept assessments of every run; the traces themselves were the working buffer and are gone.')


def _assertions_tab():
    return _tab('assertions', 'Assertions', [
        _row(0, [_table('he-assertions', 0, 12, 'The firmware\'s own claims, exercised or not', '',
                        description='One row per Catom assertion of the firmware (a claim that a piece of code changes a struct field, drives a pin from one, or sends to / '
                                    'receives from a bridge): exercised when a run that met its node changed that field, read that pin or saw a frame; how says which.',
                        columns='assertion,atom,kind,exercised,how', data_path=_T + '/coverage/assertions?' + _REV, empty_text=_PICK)], min_height=300)],
        description='Coverage tied back to the code\'s own claims.')


def _profiles_tab():
    return _tab('profiles', 'Profiles', [
        _row(0, [_table('he-profiles', 0, 12, 'Test profiles', '',
                        description='One row per manual test profile (what a run watches beyond the node\'s own requirements and collaterals): its items are fields watched by '
                                    'address, pins read from the wire, timings. A run names the profile it used.',
                        columns='name,title,bench_solution,basis,notes', data_path=_T + '/profiles?' + _REV, empty_text=_PICK)], min_height=220)],
        description='What a test watches, named and reusable.')


HARDWARE_EVENTS_PAGES = [
    _page('hardware-events', 'hardware-events',
          'A Bench Solution\'s Hardware Event topology: what was tested and what was not (first), the nodes and their confirmations, the events offered, every run, '
          'the firmware\'s claims exercised, the test profiles. Doors: /api/board/bench-solutions, /api/cmod/bench-topology/{bs}/coverage[/untested|nodes|events|runs|assertions|strip-rows], '
          '/api/cmod/bench-topology/{bs}/nodes/{slug}/runs|confirmations, /api/cmod/bench-topology/{bs}/profiles, /api/cmod/bench-topology/{bs}/canvas.',
          'BenchSolution', [_picker_row()], title='Hardware events', tabs=[_overview_tab(), _nodes_tab(), _events_tab(), _runs_tab(), _assertions_tab(), _profiles_tab()],
          scope_query=['bench_solution', 'node', 'node_slug']),
]
