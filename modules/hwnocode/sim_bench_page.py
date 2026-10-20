"""
@module hwnocode.sim_bench_page

sim-3 (HARDWARE_BENCH_CONVERGENCE_PLAN.md section 3): `/display/sim-bench?config=&session=` - the INTERACTIVE SIMULATED BENCH. The layout renderer (`hardware-layout-view`, lay-2) in BENCH
mode, bound to a TwinSession, with every table configured (no raw JSON, no new component beyond the sanctioned renderer):

    Bench tab     the picture (press / turn / set a temperature on the parts; the LED follows the board) |
                  firmware you can run (row action: start a session) | the sessions (click one to bind the picture) |
                  the firmware panel of the picked session: config, the LOCKED hex sha256, board, ports, time left, row action: stop |
                  the bridge for the picked session (row action: attach a bridge; the bridge worker's refusal is said in words) |
                  THE APP UI: the demo page's own LightState table and its "Turn the light on / off" action (reused from hwnocode.light_page, not copied) |
                  what was done on the bench (BenchInteraction rows) | row action: record this session as evidence (a ScenarioRun of kind attested, never auto-promoted)
    Evidence tab  every BenchInteraction row and every attested bench ScenarioRun, read-only

Page scope: `session` (a click on a session row, or the session just started), `rev` (bumped by row actions and by the picture after every action and every pin edge, so the tables
beside it fetch again). On a tabbed page a scope change is applied IN PLACE, so the picture keeps its zoom and its live stream.
"""
from board.custom.sim_gate import ATTEST   # ins-1: the tick's words, one place
from hwnocode.light_page import light_state_table
from polariApiServer.module_pages_seed import _layout_view, _page, _row, _tab, _table

ROUTE = 'sim-bench'

_TEXT = ('Sim bench - a simulated board you can touch. Start a session of a firmware below (it is built once; the program is then LOCKED into the simulated board - no edits, no reflash from here), '
         'click the session to bind the picture to it, and use the parts as you would on a real bench: hold the pushbutton (mouse down is a press, mouse up a release; Space does the same when it has '
         'focus), turn the potentiometer, set the TMP36\'s temperature. What the board does shows on the picture: the LED lights when the board drives its pin high. Beside the picture is the App UI - '
         'the same rows the demo page shows: press "Turn the light on / off" there and the LED on the picture follows; press the pushbutton on the picture and the row reads source = button. '
         'That second path needs a bridge attached to the session (see "Bridge"). Every action you take is kept as a row (who, what, when, and the simulated board\'s own clock cycle); "Record this session '
         'as evidence" saves them as a ScenarioRun that a person attests - it is never turned into a proof by itself. A session that nobody stops ends by itself when its time is up.')

_SESSION_COLS = 'name,config,participant,state,remaining_s,owner'
_PANEL_COLS = 'config,hex_sha256,locked_text,board,ports,remaining_s,state,owner'
_BRIDGE_COLS = 'name,session,state,grpc_target,remaining_s,end_reason'
_INTERACTION_COLS = 'seq,at_text,who,part,what,twin_cycle_text,ok,reply'
LIGHT_DOOR = '/api/board/twins/light-state?rev=r{scope:rev}'


def _bench_rows():
    return [
        _row(0, [_layout_view('sim-view', 0, 12, 'The bench - parts you can touch, outputs that follow the board', _TEXT, mode='bench', config='uno-light', session='{scope:session}')], min_height=640),
        _row(1, [
            _table('sim-firmwares', 0, 5, 'Firmware you can run', '', data_path='/api/board/variants',
                   description='What this is for: the firmware configurations a simulated board can run. One row = one firmware variant (a config). Press "Start a session" to build it and switch on a '
                               'simulated board running exactly that program; the new session is picked for you. If no engines worker is reachable the refusal says so in words.',
                   columns='name,title,purpose',
                   row_action={'label': 'Start a session', 'method': 'POST', 'path': '/api/board/twins', 'body_template': {'config': '{name}'}, 'then_scope': {'key': 'session', 'from': 'name'}},
                   max_height=300),
            _table('sim-sessions', 1, 7, 'Sessions - click one to bind the picture to it', '', data_path='/api/board/twins?rev=r{scope:rev}',
                   select_field='name', select_scope='session', selected_value='{scope:session}',
                   description='What this is for: the simulated boards that are switched on. One row = one session. name is its name, config the firmware it runs, participant the name the Hardware System '
                               'lists it under, state running or ended, remaining_s the seconds left before it stops by itself. Click a running session to bind the picture to it (click again, or '
                               'press Escape, to unbind).',
                   columns=_SESSION_COLS, max_height=300)], css_class='side-by-side', min_height=260),
        _row(2, [_table('sim-firmware-panel', 0, 12, 'Firmware panel - what the picked session is running', '', data_path='/api/board/twins?name={scope:session}&rev=r{scope:rev}',
                        empty_text='Pick a session above to see its firmware.',
                        description='What this is for: what is loaded into the picked simulated board. One row = the picked session. config is the firmware variant; hex_sha256 is the fingerprint of the exact '
                                    'program loaded (locked: it cannot be edited or reflashed from this page); board is the board design; ports are where the board listens (the serial report '
                                    'and the control channel); remaining_s the seconds left. Press "Stop session" to switch it off.',
                        columns=_PANEL_COLS,
                        row_action={'label': 'Stop session', 'method': 'POST', 'path': '/api/board/twins/{name}/stop', 'show_when_field': 'running_now',
                                    'body_template': {}})], min_height=160),
        _row(3, [
            _table('sim-bridge-attach', 0, 6, 'Bridge - lets the App UI reach the picked session', '', data_path='/api/board/twins?name={scope:session}&rev=r{scope:rev}',
                   empty_text='Pick a session above, then attach a bridge to it.',
                   description='What this is for: the App UI path needs a bridge running beside the session, so the light row on the server follows the simulated board and "Turn the light on / off" '
                               'reaches it. One row = the picked session. Press "Attach a bridge" to start one; if the bridge worker cannot be reached the words say so (nothing else is affected).',
                   columns='name,config,state',
                   row_action={'label': 'Attach a bridge', 'method': 'POST', 'path': '/api/grpc/hosted-bridges', 'body_template': {'session': '{name}'}}, max_height=160),
            _table('sim-bridges', 1, 6, 'Bridges - which are attached', '', data_path='/api/grpc/hosted-bridges?rev=r{scope:rev}',
                   description='What this is for: whether a bridge is attached to the picked session. One row = one hosted bridge: the session it serves, its state (building, running, ended), where it sends '
                               'the board\'s reports (grpc_target) and why it ended. A row whose session is the picked one means the App UI path is live.',
                   columns=_BRIDGE_COLS, max_height=200)], css_class='side-by-side', min_height=200),
        _row(4, [light_state_table('sim-light-state', 0, 12, data_path=LIGHT_DOOR)], min_height=200),
        _row(5, [
            _table('sim-interactions', 0, 8, 'What was done on the bench - the picked session', '', data_path='/api/board/twins/interactions?session={scope:session}&rev=r{scope:rev}',
                   empty_text='Pick a session above to see what was done on it.',
                   description='What this is for: the record of a manual test. One row = one thing you did to the simulated board (a press, a release, a turn of the knob, a reset). seq is its number, at_text '
                               'the time, who the person (blank when the request carried no sign-in), part the part on the picture, what the action in words, twin_cycle_text the simulated '
                               'board\'s own clock cycle when it took effect ("not reported" for an analog input: the twin\'s acknowledgement carries no cycle), ok whether the board accepted it.',
                   columns=_INTERACTION_COLS, max_height=360),
            _table('sim-record', 1, 4, 'Record this session as evidence', '', data_path='/api/board/twins?name={scope:session}&rev=r{scope:rev}',
                   empty_text='Pick a session above, do something on the bench, then record it.',
                   description='What this is for: keeping a manual test. One row = the picked session. "Record this session as evidence" saves its interactions as a ScenarioRun of kind attested - '
                               'a person\'s own record, with the firmware fingerprint and every action. It says undetermined: nobody has judged pass or fail, and it is never turned into a proof '
                               'by itself. See the Evidence tab.',
                   columns='name,config,hex_sha256',
                   row_action={'label': 'Record this session as evidence', 'method': 'POST', 'path': '/api/board/twins/{name}/record', 'body_template': {}})], css_class='side-by-side', min_height=240),
        # ins-1: the installer's confirmed-sim tick, from the bench — the same SimInstallConfirmation row the installer page writes
        _row(6, [_table('sim-confirm', 0, 12, 'Confirm the sim install - "%s"' % ATTEST, '', data_path='/api/board/twins?name={scope:session}&rev=r{scope:rev}',
                        empty_text='Pick a session above; once you have watched it do what the firmware says, confirm it here.',
                        description='What this is for: the step between a sim install and a real install (the installer page, /display/firmware-installer, offers the real board '
                                    'only after it). One row = the picked session. Pressing the button records YOUR tick for this config at exactly this program (hex_sha256): who, when, '
                                    'and the four Purposes as they stand. A new build of the config voids it. It is your own record; the installer still needs the four Purposes '
                                    'passed on the twin before it offers the real board.',
                        columns='name,config,hex_sha256',
                        row_action={'label': ATTEST + ' - confirm', 'method': 'POST', 'path': '/api/board/installer/sim-confirmations',
                                    'body_template': {'config': '{config}', 'hex_sha256': '{hex_sha256}', 'session': '{name}', 'source': 'sim-bench'}})], min_height=160),
    ]


def _evidence_rows():
    return [
        _row(0, [_table('sim-ev-recorded', 0, 12, 'Evidence recorded from the bench', 'ScenarioRun', data_path='/api/board/twins/evidence',
                        empty_text='No bench session has been recorded as evidence yet.',
                        description='What this is for: the manual tests people have kept. One row = one ScenarioRun of kind attested made from a bench session. outcome is undetermined until a person '
                                    'judges it; verdict_words says who recorded it and lists what was done; firmware_sha256 is the locked program; board_instance the session\'s participant name. '
                                    'An attested run is a person\'s record - it never counts as a measured proof on its own.',
                        columns='name,scenario,outcome,kind,attested_by,firmware_sha256,board_instance,ran_at,verdict_words', max_height=420)], min_height=260),
        _row(1, [_table('sim-ev-all', 0, 12, 'Every bench interaction', 'BenchInteraction', data_path='/api/board/twins/interactions?session=all',
                        description='What this is for: the full log of bench actions across sessions. One row = one action; session names which simulated board, the other columns are as on the Bench tab.',
                        columns='session,seq,at_text,who,part,what,twin_cycle_text,ok', max_height=420)], min_height=260),
    ]


SIM_BENCH_PAGES = [
    _page(ROUTE, ROUTE, _TEXT, 'TwinSession', [], title='Sim bench',
          tabs=[_tab('bench', 'Bench', _bench_rows(), 'Start or pick a session, then use the parts on the picture and the App UI beside it.'),
                _tab('evidence', 'Evidence', _evidence_rows(), 'What was recorded from bench sessions.')]),
]
