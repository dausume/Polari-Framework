"""
@module firmwarefaults.custom.acceptance

ACCEPTANCE SCENARIOS (hw priorities P1, AI-Notes/plans/HARDWARE_DEV_PRIORITIES.md §1/§4, D-hw-2): a Scenario
of kind='acceptance' proves a CapabilityDefinition's GOAL holds under NORMAL operation — no fault is forced. Its
steps drive the twin's EXISTING stimulus (board.custom.twin's --adc0-ramp, the same ramp tests/hwnocode_probe.py
already drives) and assert the capability's exposed field arrives, by reusing cmod-1's own twin-equivalence frame
comparison (cmod.custom.glue_build.prove, already wired as cmod.custom.firmware.run(mode='digital-twin')) — never a
second comparison engine. `pol faults run <acceptance scenario>` and `pol capability prove <name>` both land here.
"""
import datetime
import json

J = json.dumps


def _now():
    return datetime.datetime.now().isoformat(timespec='seconds')


ACCEPTANCE_SCENARIOS = [
    {'name': 'temp-sensor-to-os-acceptance', 'title': 'Acceptance — temp-sensor-to-os',
     'description': "A temp_c that left the twin's simulated ADC0 (700→800 mV ramp) arrives on the backend's "
                    "state within one frame period (~0.1 s at 10 Hz) — restates tests/hwnocode_probe.py's own "
                    "measured frame cadence as a named capability claim (HARDWARE_DEV_PRIORITIES.md §1).",
     'target_board': 'arduino-uno-r3', 'before_variant': 'uno-sim-rig', 'after_variant': '',
     'fault_class': '', 'fault': '', 'breaks': '', 'technique': '',
     'expected_observable': 'temp_c sampled by the twin arrives on the backend row within one frame period (~100 ms '
                            'at 10 Hz); the twin build reproduces the glue\'s reference frames field by field '
                            '(cmod-1 equivalence, glue_build.prove)',
     'observable_kind': 'field-arrival', 'window_cycles': int(0.3 * 16000000), 'run_seconds': 0.3,
     'seed_policy': 'fixed', 'seed': 0, 'simulator': 'avr-twin', 'status': 'runnable', 'kind': 'acceptance',
     'capability': 'temp-sensor-to-os', 'provenance': 'hw priorities P1 seed', 'notes': ''},
    {'name': 'blink-on-command-acceptance', 'title': 'Acceptance — blink-on-command',
     'description': 'A PUT led_on=1 (the same command path uno-sim-rig already exposes, hwnocode_probe\'s own PUT '
                    'check) is followed by the next frame reporting led_on true within one frame period.',
     'target_board': 'arduino-uno-r3', 'before_variant': 'uno-sim-rig', 'after_variant': '',
     'fault_class': '', 'fault': '', 'breaks': '', 'technique': '',
     'expected_observable': 'the frame immediately after the PUT reports led state 1 within one frame period (~100 ms at 10 Hz)',
     'observable_kind': 'command-echo', 'window_cycles': int(0.3 * 16000000), 'run_seconds': 0.3,
     'seed_policy': 'fixed', 'seed': 0, 'simulator': 'avr-twin', 'status': 'runnable', 'kind': 'acceptance',
     'capability': 'blink-on-command', 'provenance': 'hw priorities P1 seed', 'notes': ''},
    {'name': 'button-clock-to-os-acceptance', 'title': 'Acceptance — button-clock-to-os',
     'description': "N debounced presses on D2 + --wire PD6:PD3 (ucd-0d) -> button_presses == N, sense_rises + "
                    "sense_falls == N, led_on == (N odd), no dropped events; the SAME presses with NO --wire -> the "
                    "sense counters stay 0 (the probe's cases (a) and (f), UNO_CORE_DEMO_PLAN.md §1).",
     'target_board': 'arduino-uno-r3', 'before_variant': 'uno-button-clock', 'after_variant': '',
     'fault_class': '', 'fault': '', 'breaks': '', 'technique': '',
     'expected_observable': 'button_presses == N and sense_rises + sense_falls == N and led_on == (N odd) when wired; '
                            'sense_rises == sense_falls == 0 when not wired, in the SAME run of presses',
     'observable_kind': 'field-arrival', 'window_cycles': int(1.0 * 16000000), 'run_seconds': 1.0,
     'seed_policy': 'fixed', 'seed': 0, 'simulator': 'avr-twin', 'status': 'runnable', 'kind': 'acceptance',
     'capability': 'button-clock-to-os', 'provenance': 'ucd-0e2 seed', 'notes': ''},
]


#: the forcibility of these three kinds is also recorded in firmwarefaults.custom.scenarios.STEP_KINDS (the shared,
#: printable vocabulary `pol faults list` reads) — duplicated as plain True here, never imported from scenarios.py at
#: module load time, to avoid a load-order cycle: scenarios.py itself imports THIS module (to merge the acceptance
#: rows into SEED_SCENARIOS/SEED_STEPS), so acceptance.py must not need scenarios.py to finish loading first.
_FORCIBLE = {'drive-adc-ramp', 'assert-field-arrival', 'assert-command-echo', 'pin-at'}   # ucd-0e2: pin-at (ucd-0d), proven on the twin


def _step(scenario, position, kind, args, notes=''):
    ok = kind in _FORCIBLE
    return {'name': '%s#%d' % (scenario, position), 'scenario': scenario, 'position': position, 'kind': kind,
            'args_json': J(args), 'condition_json': '{}', 'forcible': ok,
            'not_forcible_reason': '' if ok else 'unknown acceptance step kind %r' % kind, 'notes': notes}


ACCEPTANCE_STEPS = [
    _step('temp-sensor-to-os-acceptance', 1, 'drive-adc-ramp', {'channel': 'A0', 'lo_mv': 700, 'hi_mv': 800, 'ms': 8000},
          notes='the exact ramp tests/hwnocode_probe.py drives (20→30 °C over 8 s)'),
    _step('temp-sensor-to-os-acceptance', 2, 'assert-field-arrival', {'field': 'temp_c', 'window_ms': 100},
          notes='glue_build.prove\'s frame-by-field equivalence, read for temp_c'),
    _step('blink-on-command-acceptance', 1, 'assert-command-echo', {'field': 'led_on', 'value': 1, 'window_ms': 100},
          notes='a PUT led_on=1 followed by the next frame reporting it'),
    _step('button-clock-to-os-acceptance', 1, 'pin-at', {'cycle': 1600000, 'pin': 'PD2', 'level': 0},
          notes='button-clock probe case (a): the first of N presses on D2 (board.board_button_clock_twin_selftest._press_pinat)'),
    _step('button-clock-to-os-acceptance', 2, 'assert-field-arrival',
          {'field': 'sense_rises+sense_falls==button_presses', 'window_ms': 100},
          notes='the wired invariant: sense_rises + sense_falls == button_presses, led_on == (presses odd)'),
    _step('button-clock-to-os-acceptance', 3, 'assert-field-arrival', {'field': 'sense_rises+sense_falls==0 (no --wire)', 'window_ms': 100},
          notes='probe case (f), the NEGATIVE: the same presses with no --wire -> sense counters stay 0'),
]


def find(name):
    return next((dict(s) for s in ACCEPTANCE_SCENARIOS if s['name'] == name), None)


def steps_of(scenario):
    return sorted([s for s in ACCEPTANCE_STEPS if s['scenario'] == scenario], key=lambda s: s['position'])


def run(scenario_name, mode='digital-twin', manager=None, sink=None):
    """Run one acceptance Scenario: resolve its `capability`, run the backing FirmwareSolution (the SAME door the
    firmware panel's Run button calls, cmod.custom.firmware.run) and turn the result into a ScenarioRun row. Never a
    second proof engine — reuses glue_build.prove (twin) / the installer's detected route (hardware), same posture as
    cmod_firmware_api.on_post_run. Returns the ScenarioRun dict (+'result': the raw FW.run() payload)."""
    from firmwarefaults.custom import sink as S
    sc = find(scenario_name)
    if sc is None:
        raise KeyError('no acceptance scenario %r' % scenario_name)
    from cmod.custom import capabilities as CAP
    cap = CAP.find(sc['capability'])
    if cap is None:
        raise KeyError('acceptance scenario %r names capability %r, which does not exist' % (scenario_name, sc['capability']))
    run_mode = 'hardware' if mode == 'hardware' else 'digital-twin'
    if sc['capability'] == 'button-clock-to-os':
        # ucd-0e2: no FirmwareSolution/CGraph for uno-button-clock yet (0e2b's job) — FW.run()'s glue-equivalence
        # proof has nothing to run against; a dedicated runner proves the GOAL directly instead (board.custom.
        # button_clock_acceptance), reusing the SAME twin + codec the probe/twin-selftest already prove with.
        from board.custom import button_clock_acceptance as BCA
        result = BCA.run_acceptance(run_mode)
    else:
        from cmod.custom import firmware as FW
        fs = {'name': 'uno-sim-rig', 'graph': cap['graph'], 'board_definition': sc['target_board']}
        if manager is not None:
            hit = next((r for r in (manager.objectTables or {}).get('FirmwareSolution', {}).values() if getattr(r, 'graph', '') == cap['graph']), None)
            if hit is not None:
                fs = hit
        result = FW.run(fs, run_mode, manager=manager)
    ran_at = _now()
    if result.get('ok'):
        outcome = 'passed'
    elif result.get('route') == 'refused':
        outcome = 'inapplicable'  # validate() itself refused (board does not resolve, conflict, ...)
    else:
        outcome = 'undetermined'  # the engine could not be reached (e.g. no docker permission here) — never 'failed':
        # the proof never actually ran, so nothing was observed to fail
    run_name = '%s@%s@%s' % (scenario_name, mode, ran_at)
    row = {'name': run_name, 'scenario': scenario_name, 'side': 'acceptance', 'variant': sc['before_variant'],
           'build_name': '', 'technique_applied': '', 'outcome': outcome, 'verdict_words': result.get('why', ''),
           'observed_json': J({k: v for k, v in result.items() if k != 'ok'}),
           'simulator_version': sc['simulator'] if run_mode == 'digital-twin' else 'hardware',
           'frames_seen': int(result.get('frames_compared') or 0), 'claim': '',
           'repro_json': J({'mode': run_mode, 'scenario': scenario_name, 'capability': sc['capability']}),
           'ran_at': ran_at, 'notes': 'acceptance run (hw priorities P1) — %s' % (result.get('how') or '')}
    sk = sink or S.LocalSink()
    sk.upsert('ScenarioRun', row)
    return dict(row, result=result)
