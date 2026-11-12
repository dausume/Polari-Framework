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
  Measured    msv-0: built units, a node's measurement points (derived), manual readings judged against the prediction
  Test sheet  msv-0b: the generated step-by-step test (where to test on the left, the sheet on the right), priming
  Rulings     msv-2: what waits for a person, the fault ranking, rulings and rework (cmod.custom.rulings_tab)
Linkable: /display/hardware-events?bench_solution=uno-light-on-desk&node=... (scope_query). Doors: /api/board/bench-solutions, /api/cmod/bench-topology/{bs}/coverage[/...],
/api/cmod/bench-topology/{bs}/nodes/{slug}/runs|confirmations, /api/cmod/bench-topology/{bs}/profiles.
"""
from cmod.custom.rulings_tab import rulings_tab
from polariApiServer.module_pages_seed import _component, _page, _row, _table, _tab

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
                        columns='node,title,kind,expect,basis,state,runs,last_outcome,paths_tested,paths,confirmed_by,voided,blocked,collaterals_measured,stale',
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
                        empty_text=_PICK, select_field='name', select_scope='run', selected_value='{scope:run}')], min_height=320),
        # bss-10: the traces a run DID keep - on failure (the window around it) or pinned - and the osc arc's chart of the chosen acquisition
        _row(1, [_table('he-run-captures', 0, 12, 'The traces this run kept - click one acquisition', '',
                        description='One row per line of a capture the chosen run kept: on failure, the window around the failing edge (D-bss-6); pinned, the whole edge. '
                                    'The same rows a scope capture writes (instruments), source twin. Click a row to draw its acquisition below.',
                        columns='acquisition,kept,channel,line,points,sample_rate,span_s,v_min,v_max,source_ref', data_path=_T + '/runs/{scope:run}/captures?' + _REV,
                        select_field='acquisition', select_scope='acquisition', selected_value='{scope:acquisition}',
                        empty_text='Pick a run above; a reached run keeps no trace (the assessment is kept, the trace was the working buffer).')], min_height=220),
        _row(2, [_component('he-run-chart', 0, 12, 'The chosen acquisition - the lines over time', 'named-graph-panel',
                            {'graphName': 'instruments-capture', 'dataPath': '/api/instruments/captures/{scope:acquisition}/chart?max=4000&' + _REV},
                            description='Volts over seconds for every line of the chosen acquisition, recomputed from the stored block and preamble by the instruments arc\'s '
                                        'own chart (instruments-capture); every drawn point is a real sample.')], min_height=420),
        # bss-14: what changed since the previous run of the same node (a rebuild, a configuration change) - derived on read, nothing stored
        _row(3, [_table('he-run-diff', 0, 12, 'What changed against the previous run of this node', '',
                        description='One row per compared value of the chosen run against the previous run of the same node (its outcome, build, each edge\'s outcome '
                                    'and met cycle, each collateral and execution count, each signal\'s first / last / changes): a and b side by side, the delta '
                                    'where one exists. The VCD of a kept capture is at .../runs/{run}/vcd.',
                        columns='what,a,b,delta,changed', data_path=_T + '/runs/{scope:run}/diff?' + _REV,
                        empty_text='Pick a run above; the first run of a node has nothing to compare with.')], min_height=260)],
        description='The kept assessments of every run; a trace is kept only around a failure or when pinned, and drawn here; a run diffed against its predecessor.')


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


def _measured_tab():
    """msv-0 (MEASURED_VS_SIMULATED_PLAN.md): real readings off a built unit against the simulation's prediction at a node - manual entry first."""
    pts = '/api/cmod/bench-topology/%s/nodes/{scope:node_slug}/measurement-points?%s' % (_BS, _REV)
    form = {'fields': [{'name': 'point', 'label': 'Measurement point (click one above - its name)', 'required': True},
                       {'name': 'value', 'label': 'Value read, with its unit (e.g. 4.97 V, 14.2 mA)', 'required': True},
                       {'name': 'instrument', 'label': 'Instrument (an Instrument row: its cited accuracy gives the band)'},
                       {'name': 'range_max', 'label': 'Range used (optional, e.g. 20 V)'},
                       {'name': 'who', 'label': 'Who read it'},
                       {'name': 'note', 'label': 'Note', 'type': 'textarea'}],
            'action': {'label': 'Keep the reading', 'method': 'POST', 'path': _T + '/units/{scope:unit}/readings',
                       'body_template': {'point': '{point}', 'value': '{value}', 'instrument': '{instrument}', 'range_max': '{range_max}', 'who': '{who}',
                                         'note': '{note}', 'via': 'manual'}},
            'submit_label': 'Keep the reading', 'success_text': 'Kept - judged against the prediction in the table below.'}
    unit_form = {'fields': [{'name': 'name', 'label': 'Unit name (blank = <bench solution>-unit-<n>)'},
                            {'name': 'build_method', 'label': 'Built as: breadboard | perfboard | wire-wrap | pcb | other'},
                            {'name': 'hex_sha256', 'label': 'Build flashed on it (hex sha256)'},
                            {'name': 'built_by', 'label': 'Built by'}],
                 'action': {'label': 'Add', 'method': 'POST', 'path': _T + '/units',
                            'body_template': {'name': '{name}', 'build_method': '{build_method}', 'hex_sha256': '{hex_sha256}', 'built_by': '{built_by}'},
                            'then_scope': {'key': 'unit', 'from': 'name'}},
                 'submit_label': 'Add the built unit', 'success_text': 'Added - it is now the unit below.'}
    return _tab('measured', 'Measured', [
        _row(0, [_component('he-unit-form', 0, 4, 'A built unit', 'door-form', unit_form,
                            description='One physical copy of this Bench Solution that someone built (breadboard, perfboard, wire wrap, PCB) and the build flashed on it.'),
                 _table('he-units', 4, 8, 'Built units - click one', '',
                        description='One row per built unit of the Bench Solution. Click one to enter and read its measurements below.',
                        columns='name,build_method,hex_sha256,built_by,at,notes', data_path=_T + '/units?' + _REV, empty_text=_PICK,
                        select_field='name', select_scope='unit', selected_value='{scope:unit}')], min_height=220),
        _row(1, [_table('he-points', 0, 12, 'What to measure at the chosen node, and what the simulation says', '',
                        description='One row per measurement point of the node chosen on the Nodes tab, derived from the circuit state its latest reached run left '
                                    '(the ngspice .op over the bench circuit rows): the quantity, where the probes go, the predicted value and its basis. '
                                    'Click one to fill its name into the form.',
                        columns='name,quantity,where,nominal,band_lo,band_hi,si_unit,state,source,basis,band_basis,origin', data_path=pts,
                        select_field='name', select_scope='point', selected_value='{scope:point}', empty_text='Pick a node on the Nodes tab (it needs a reached run).')], min_height=240),
        _row(2, [_component('he-reading-form', 0, 4, 'Enter a reading (manual)', 'door-form', form,
                            description='Type what the meter shows. The reading is kept as typed and judged against the prediction and the instrument\'s cited accuracy.'),
                 _table('he-readings', 4, 8, 'Readings of the chosen unit, judged', '',
                        description='Every reading of the unit, newest first: in-band (matches the simulation within the instrument), in-tolerance (off the nominal but inside what the parts allow: tol_lo..tol_hi), unexplained (needs a person\'s look), '
                                    'unjudged (the instrument\'s accuracy is not cited yet), over-range; stale = read on another build than the prediction. current = '
                                    'the newest reading of its point. standing (msv-2) = counts, accepted, needs-ruling, mistake-open / closed, re-measure; click one to rule on it (the Rulings tab).',
                        columns='point,entered,verdict,standing,counts,expected,delta,band,tol_lo,tol_hi,loading,current,stale,instrument,via,who,at,words', data_path=_T + '/units/{scope:unit}/readings?' + _REV,
                        empty_text='Pick a built unit above.', select_field='name', select_scope='reading', selected_value='{scope:reading}')], min_height=300)],
        description='Real readings off a built unit against the simulation at a node: manual entry first (msv-0).')


def _sheet_tab():
    """msv-0b (MEASURED_VS_SIMULATED_PLAN.md section 5b): the GENERATED step-by-step test - LEFT where to test (drawn), RIGHT the sheet, judged as it is filled."""
    gen = {'fields': [{'name': 'hex_sha256', 'label': 'Build it is for (hex sha256; blank = the build its runs used)'}],
           'action': {'label': 'Generate', 'method': 'POST', 'path': _T + '/procedures', 'body_template': {'hex_sha256': '{hex_sha256}'},
                      'then_scope': {'key': 'procedure', 'from': 'name'}},
           'submit_label': 'Generate the procedure', 'success_text': 'Generated from the topology and the measurement points (unchanged = the one already frozen).'}
    start = {'fields': [{'name': 'mode', 'label': 'guided (the sheet) | touch (a device confirms; needs msv-3 - falls back to the sheet)'},
                        {'name': 'who', 'label': 'Who is testing'}],
             'action': {'label': 'Start', 'method': 'POST', 'path': _T + '/units/{scope:unit}/sessions',
                        'body_template': {'procedure': '{scope:procedure}', 'mode': '{mode}', 'who': '{who}'}, 'then_scope': {'key': 'session', 'from': 'name'}},
             'submit_label': 'Start a session on the chosen unit', 'success_text': 'Started - the sheet is below.'}
    ans = {'fields': [{'name': 'value', 'label': 'A measure step: the value read, with its unit (e.g. 4.97 V, 14.6 mA)'},
                      {'name': 'instrument', 'label': 'Instrument (e.g. tekpower-tp4000zc)'},
                      {'name': 'outcome', 'label': 'Any other step: done | skipped (setup, stimulus); beep | no-beep (continuity); yes | no (look)'},
                      {'name': 'note', 'label': 'Note', 'type': 'textarea'}],
           'action': {'label': 'Answer', 'method': 'POST', 'path': _T + '/sessions/{scope:session}/steps/{scope:step}',
                      'body_template': {'value': '{value}', 'instrument': '{instrument}', 'outcome': '{outcome}', 'note': '{note}'}},
           'submit_label': 'Answer the chosen step', 'success_text': 'Kept - its verdict is on the sheet.'}
    prime = {'fields': [{'name': 'endpoint', 'label': 'Meter endpoint (a sigrok InstrumentEndpoint, e.g. the TP4000ZC on its serial port)'},
                        {'name': 'window_s', 'label': 'Wait up to (seconds; blank = the session\'s, else 30)'},
                        {'name': 'chain', 'label': 'Then prime the next measure step too? (true / blank)'}],
             'action': {'label': 'Prime', 'method': 'POST', 'path': _T + '/sessions/{scope:session}/steps/{scope:step}/prime',
                        'body_template': {'endpoint': '{endpoint}', 'window_s': '{window_s}', 'chain': '{chain}'}},
             'submit_label': 'Prime the chosen measure step, then probe', 'success_text': 'Primed - probe the point (and press the button if the step says so); '
                                                                                      'it confirms by itself once the meter settles.'}
    resume = {'fields': [], 'action': {'label': 'Resume', 'method': 'POST', 'path': _T + '/sessions/{scope:session}/resume', 'body_template': {}},
              'submit_label': 'Resume the session (re-asks the presses that put the board back in its state)', 'success_text': 'Resumed.'}
    return _tab('sheet', 'Test sheet', [
        _row(0, [_component('he-proc-form', 0, 4, 'Generate the step-by-step test', 'door-form', gen,
                            description='Worked out from the topology (the fastest path to every node), the bench circuit and the measurement points - never typed. '
                                        'Power-off continuity checks first, then power on, then every node.'),
                 _table('he-procs', 4, 8, 'Procedures - click one', '', description='One frozen procedure per build. owed = what could not be generated yet.',
                        columns='name,hex_sha256,steps,owed,at', data_path=_T + '/procedures?' + _REV, empty_text='None yet: generate one.',
                        select_field='name', select_scope='procedure', selected_value='{scope:procedure}')], min_height=200),
        _row(1, [_component('he-session-form', 0, 4, 'Start a test session', 'door-form', start,
                            description='Pick the built unit on the Measured tab and a procedure above, then start.'),
                 _table('he-sessions', 4, 8, 'Sessions of the chosen unit - click one', '', columns='name,procedure,mode,who,state,at,resumed_at,notes',
                        data_path=_T + '/units/{scope:unit}/sessions?' + _REV, empty_text='Pick a built unit on the Measured tab.',
                        select_field='name', select_scope='session', selected_value='{scope:session}')], min_height=200),
        _row(2, [_component('he-step-picture', 0, 6, 'Where to test', 'api-svg-panel',
                            {'dataPath': _T + '/procedures/{scope:procedure}/steps/{scope:step}/picture?' + _REV, 'markersPath': ''},
                            description='The board\'s headers and the bench circuit: the red probe ringed red, the black ringed black, the part to press or look at lit.'),
                 _table('he-sheet', 6, 6, 'The sheet - click a step', '',
                        description='One row per step, judged as it is filled: pass, fail, unexplained (a reading outside the band), unjudged, over-range, done, '
                                    'skipped, pending; ask again = a press to repeat after a resume. The paper version: .../sessions/{session}/print.',
                        columns='order,kind,words,expect,answer,verdict,ask_again,judged', data_path=_T + '/sessions/{scope:session}?' + _REV,
                        empty_text='Start or pick a session above.', select_field='step', select_scope='step', selected_value='{scope:step}')], min_height=420,
             css_class='side-by-side'),
        _row(3, [_component('he-answer-form', 0, 4, 'Answer the chosen step', 'door-form', ans,
                            description='A measure step takes the value read; every other step takes its outcome.'),
                 _component('he-prime-form', 4, 3, 'Touch and confirm: prime, then probe (hands free)', 'door-form', prime,
                            description='Prime first, then put both hands on the work: the step waits for the meter and confirms once its value settles where a correct build reads. '
                                        'At the end of the window the last steady value is kept (a fault reads steady too); nothing at all = no data (the probe, cable or port).'),
                 _component('he-resume-form', 7, 2, 'Stopped and came back?', 'door-form', resume, description='Resume: the board may have lost its state.'),
                 _table('he-summary', 9, 3, 'Summary', '', columns='verdict,steps', data_path=_T + '/sessions/{scope:session}/summary?' + _REV,
                        empty_text='')], min_height=220),
        _row(4, [_table('he-primes', 0, 12, 'Primed steps - waiting for the meter, and how each ended', '',
                        description='armed = waiting; confirmed = the meter settled where a correct build reads; kept-last = the window ended, the last steady value kept; '
                                    'not-steady / wrong-mode / no-data = no reading kept, said why.',
                        columns='step,state,window_s,armed_at,ends_at,lines_seen,reading,chain,note', data_path=_T + '/sessions/{scope:session}/primes?' + _REV,
                        empty_text='Nothing primed in this session.')], min_height=180)],
        description='The generated step-by-step test of a built unit: the left pane shows where to test, the sheet on the right is judged as you fill it (msv-0b).')


HARDWARE_EVENTS_PAGES = [
    _page('hardware-events', 'hardware-events',
          'A Bench Solution\'s Hardware Event topology: what was tested and what was not (first), the nodes and their confirmations, the events offered, every run, '
          'the firmware\'s claims exercised, the test profiles. Doors: /api/board/bench-solutions, /api/cmod/bench-topology/{bs}/coverage[/untested|nodes|events|runs|assertions|strip-rows], '
          '/api/cmod/bench-topology/{bs}/nodes/{slug}/runs|confirmations, /api/cmod/bench-topology/{bs}/profiles, /api/cmod/bench-topology/{bs}/canvas.',
          'BenchSolution', [_picker_row()], title='Hardware events', tabs=[_overview_tab(), _nodes_tab(), _events_tab(), _runs_tab(), _assertions_tab(), _profiles_tab(), _measured_tab(), _sheet_tab(), rulings_tab()],
          scope_query=['bench_solution', 'node', 'node_slug', 'run', 'acquisition', 'unit', 'point', 'procedure', 'session', 'step', 'reading', 'ruling']),
]
