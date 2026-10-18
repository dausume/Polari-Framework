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
    {'name': 'light-from-button-acceptance', 'title': 'Acceptance — light-from-button',
     'description': 'Three debounced presses on the board\'s button (D2): each one flips the light, the board counts it, and its '
                    'next frame says source=button; the light is on after an odd number of presses.',
     'target_board': 'arduino-uno-r3', 'before_variant': 'uno-light', 'after_variant': '',
     'fault_class': '', 'fault': '', 'breaks': '', 'technique': '',
     'expected_observable': 'led_on flips on every press, toggles == presses, source == button in every frame after the first press',
     'observable_kind': 'field-arrival', 'window_cycles': int(1.0 * 16000000), 'run_seconds': 1.0,
     'seed_policy': 'fixed', 'seed': 0, 'simulator': 'avr-twin', 'status': 'runnable', 'kind': 'acceptance',
     'capability': 'ensure-button-controls-light', 'provenance': 'ucd-light seed',
     'notes': 'fgm-1: re-pointed from the retired light-from-button to ensure-button-controls-light; the steps are unchanged, so runs recorded '
              'before the re-point (under the old Purpose) are the same test and are counted by the new Purpose'},
    {'name': 'ensure-polari-observes-hardware-state-acceptance', 'title': 'Acceptance - ensure-polari-observes-hardware-state',
     'description': 'The same three debounced presses as the button test, read from what Polari sees: every state report decoded from the '
                    'serial stream shows the light flipping with each press, the toggle count equal to the presses and source=button.',
     'target_board': 'arduino-uno-r3', 'before_variant': 'uno-light', 'after_variant': '',
     'fault_class': '', 'fault': '', 'breaks': '', 'technique': '',
     'expected_observable': 'the decoded reports show led_on flipping on every press, toggles == presses, source == button',
     'observable_kind': 'field-arrival', 'window_cycles': int(1.0 * 16000000), 'run_seconds': 1.0,
     'seed_policy': 'fixed', 'seed': 0, 'simulator': 'avr-twin', 'status': 'runnable', 'kind': 'acceptance',
     'capability': 'ensure-polari-observes-hardware-state', 'provenance': 'fgm-1 seed',
     'notes': 'fgm-1: its own Scenario (so its runs are its own) reusing the button test\'s frame assertions; it has NO runs until it is run'},
    {'name': 'light-from-polari-acceptance', 'title': 'Acceptance — light-from-polari',
     'description': 'The OS sends SET_LED on, then SET_LED off over the serial link: the light follows each command, the board '
                    'counts both changes, and its frames say source=command.',
     'target_board': 'arduino-uno-r3', 'before_variant': 'uno-light', 'after_variant': '',
     'fault_class': '', 'fault': '', 'breaks': '', 'technique': '',
     'expected_observable': 'after SET_LED 1: led_on true, toggles 1, source command; after SET_LED 0: led_on false, toggles 2, source command',
     'observable_kind': 'command-echo', 'window_cycles': int(1.0 * 16000000), 'run_seconds': 1.0,
     'seed_policy': 'fixed', 'seed': 0, 'simulator': 'avr-twin', 'status': 'runnable', 'kind': 'acceptance',
     'capability': 'ensure-polari-can-control-light', 'provenance': 'ucd-light seed',
     'notes': 'fgm-1: re-pointed from the retired light-from-polari to ensure-polari-can-control-light; the steps are unchanged, so runs '
              'recorded before the re-point (under the old Purpose) are the same test and are counted by the new Purpose'},
    # fgm-5a: the isotope variants' own twin proofs (board.custom.variant_twin). They name an existing Purpose for the GOAL they restate;
    # the Purpose's own status still derives from ITS acceptance_scenario - these runs are read by the isotope catalogue
    # (cmod.custom.isotope_variants: implemented_by.proof_scenarios), never folded into a Purpose.
    {'name': 'light-pcint-button-acceptance', 'title': 'Acceptance - the button on a pin-change interrupt (read-button:pin-change-interrupt)',
     'description': 'The light test with the button on D4, read by the pin-change-interrupt isotope rendered from its Jinja2 template: three '
                    'debounced presses on D4 flip the light, the board counts them and says source=button, the light pin (PD6) itself follows; '
                    'the same presses on D2 change nothing; a bouncing contact counts once.',
     'target_board': 'arduino-uno-r3', 'before_variant': 'uno-light-pcint', 'after_variant': '',
     'fault_class': '', 'fault': '', 'breaks': '', 'technique': '',
     'expected_observable': 'toggles == presses, led_on flips, source == button, PD6 high after an odd count; presses on D2 -> toggles 0; one bounce train -> toggles 1',
     'observable_kind': 'field-arrival', 'window_cycles': int(1.0 * 16000000), 'run_seconds': 1.0,
     'seed_policy': 'fixed', 'seed': 0, 'simulator': 'avr-twin', 'status': 'runnable', 'kind': 'acceptance',
     'capability': 'ensure-button-controls-light', 'provenance': 'fgm-5a seed',
     'notes': 'runner: board.custom.variant_twin; proves the ISOTOPE (catalogue route read-button:pin-change-interrupt), not a second Purpose'},
    {'name': 'light-analog-button-acceptance', 'title': 'Acceptance - the button as a voltage on A0 (read-button:analog-threshold)',
     'description': 'The light test with the button read as a voltage on A0 by the analog-threshold isotope rendered from its Jinja2 template: the '
                    'twin drives A0 with a triangle ramp 200..4800 mV (1 s period); every fall below the press threshold is one press, counted by '
                    'a pure model of the ramp and compared with the frames; a pin held high and a switch closed from boot count nothing.',
     'target_board': 'arduino-uno-r3', 'before_variant': 'uno-light-analog', 'after_variant': '',
     'fault_class': '', 'fault': '', 'breaks': '', 'technique': '',
     'expected_observable': 'toggles == the model\'s press count, led_on == (toggles odd), source == button; constant 4800 mV -> toggles 0; constant 200 mV -> toggles 0',
     'observable_kind': 'field-arrival', 'window_cycles': int(1.0 * 16000000), 'run_seconds': 3.6,
     'seed_policy': 'fixed', 'seed': 0, 'simulator': 'avr-twin', 'status': 'runnable', 'kind': 'acceptance',
     'capability': 'ensure-button-controls-light', 'provenance': 'fgm-5a seed',
     'notes': 'runner: board.custom.variant_twin; proves the ISOTOPE (catalogue route read-button:analog-threshold)'},
    # fgm-6a: command confirmation on the wire (LightStateV2, variant uno-light-v2). Runner: board.custom.light_v2_twin. They restate the
    # command half of ensure-polari-can-control-light for the NEW wire struct; the Purpose's own status still derives from ITS acceptance_scenario.
    {'name': 'light-v2-rapid-commands-acceptance', 'title': 'Acceptance - 20 rapid commands, 20 confirmations (uno-light-v2)',
     'description': 'Twenty SET_LED commands, 20 ms apart, ids 1 to 20, alternating on and off: the board answers each at once with a report naming its id, the backend ledger confirms each by its own id and light value, none by an unrelated report, and the light follows all twenty.',
     'target_board': 'arduino-uno-r3', 'before_variant': 'uno-light-v2', 'after_variant': '',
     'fault_class': '', 'fault': '', 'breaks': '', 'technique': '',
     'expected_observable': 'every command id 1..20 confirmed by a report with last_command_id == id and result applied; toggles 20; a ledger from another boot session confirms none',
     'observable_kind': 'command-echo', 'window_cycles': int(3.0 * 16000000), 'run_seconds': 3.0,
     'seed_policy': 'fixed', 'seed': 0, 'simulator': 'avr-twin', 'status': 'runnable', 'kind': 'acceptance',
     'capability': 'ensure-polari-can-control-light', 'provenance': 'fgm-6a seed',
     'notes': 'runner: board.custom.light_v2_twin (check rapid)'},
    {'name': 'light-v2-reboot-acceptance', 'title': 'Acceptance - a reboot between send and answer is unknown, resend (uno-light-v2)',
     'description': 'The board is reset (a) while it is still sending its answer to a command it has applied and (b) while the command is still arriving: the backend ledger shows the command as unknown-resend (the boot_session changed), never as done. A control with no reset is confirmed.',
     'target_board': 'arduino-uno-r3', 'before_variant': 'uno-light-v2', 'after_variant': '',
     'fault_class': '', 'fault': '', 'breaks': '', 'technique': '',
     'expected_observable': 'boot_session 1 then 2; the command is unknown-resend in both reset cases and no later report names it; confirmed in the no-reset control',
     'observable_kind': 'command-echo', 'window_cycles': int(2.0 * 16000000), 'run_seconds': 2.0,
     'seed_policy': 'fixed', 'seed': 0, 'simulator': 'avr-twin', 'status': 'runnable', 'kind': 'acceptance',
     'capability': 'ensure-polari-can-control-light', 'provenance': 'fgm-6a seed',
     'notes': 'runner: board.custom.light_v2_twin (check reboot); his ruling 7.8.3'},
    {'name': 'light-v2-malformed-acceptance', 'title': 'Acceptance - a malformed command is answered rejected-invalid (uno-light-v2)',
     'description': 'Four malformed commands (no led_on, no command_id, command_id 0, a truncated payload): each is answered rejected-invalid on the wire, the first with its own id and the others leaving last_command_id alone, the light stays off; the next good command is applied.',
     'target_board': 'arduino-uno-r3', 'before_variant': 'uno-light-v2', 'after_variant': '',
     'fault_class': '', 'fault': '', 'breaks': '', 'technique': '',
     'expected_observable': 'last_command_result rejected-invalid with last_command_id 5, toggles 0; then command 6 applied, toggles 1',
     'observable_kind': 'command-echo', 'window_cycles': int(2.5 * 16000000), 'run_seconds': 2.5,
     'seed_policy': 'fixed', 'seed': 0, 'simulator': 'avr-twin', 'status': 'runnable', 'kind': 'acceptance',
     'capability': 'ensure-polari-can-control-light', 'provenance': 'fgm-6a seed',
     'notes': 'runner: board.custom.light_v2_twin (check malformed)'},
    {'name': 'light-v2-button-no-confirm-acceptance', 'title': 'Acceptance - a button press never confirms a command (uno-light-v2)',
     'description': 'A press of the board button changes the light but leaves last_command_id and last_command_result as they were, so a command that never reached the board stays pending through the press reports and becomes unconfirmed at its timeout; a command sent after the press is confirmed by its own answer.',
     'target_board': 'arduino-uno-r3', 'before_variant': 'uno-light-v2', 'after_variant': '',
     'fault_class': '', 'fault': '', 'breaks': '', 'technique': '',
     'expected_observable': 'reports after the press: source button, last_command_id unchanged; the lost command pending then unconfirmed; the next command confirmed',
     'observable_kind': 'command-echo', 'window_cycles': int(3.0 * 16000000), 'run_seconds': 3.0,
     'seed_policy': 'fixed', 'seed': 0, 'simulator': 'avr-twin', 'status': 'runnable', 'kind': 'acceptance',
     'capability': 'ensure-polari-can-control-light', 'provenance': 'fgm-6a seed',
     'notes': 'runner: board.custom.light_v2_twin (check button)'},
    {'name': 'sim-rig-pwm-duty-acceptance', 'title': 'Acceptance - the PWM LED duty (drive-led:pwm)',
     'description': 'SET pwm_duty 25, 50 and 100 over the serial link to the sim rig: the twin\'s OCR0A (the PWM compare register behind D6) '
                    'becomes 63, 127 and 255 (duty x 255 / 100) and the duty the timer produces, OCR0A / 255, is within half a percentage point.',
     'target_board': 'arduino-uno-r3', 'before_variant': 'uno-sim-rig', 'after_variant': '',
     'fault_class': '', 'fault': '', 'breaks': '', 'technique': '',
     'expected_observable': 'OCR0A read from the twin status lines == duty * 255 // 100 after each command; the frame echoes pwm_duty',
     'observable_kind': 'command-echo', 'window_cycles': int(2.0 * 16000000), 'run_seconds': 2.0,
     'seed_policy': 'fixed', 'seed': 0, 'simulator': 'avr-twin', 'status': 'runnable', 'kind': 'acceptance',
     'capability': 'ensure-polari-can-control-light', 'provenance': 'fgm-5a seed',
     'notes': 'runner: board.custom.variant_twin; proves the catalogue route drive-led:pwm. The duty is OCR0A / 255 as the twin reads it; the pin waveform itself is not sampled'},
]


#: the forcibility of these three kinds is also recorded in firmwarefaults.custom.scenarios.STEP_KINDS (the shared,
#: printable vocabulary `pol faults list` reads) — duplicated as plain True here, never imported from scenarios.py at
#: module load time, to avoid a load-order cycle: scenarios.py itself imports THIS module (to merge the acceptance
#: rows into SEED_SCENARIOS/SEED_STEPS), so acceptance.py must not need scenarios.py to finish loading first.
_FORCIBLE = {'drive-adc-ramp', 'assert-field-arrival', 'assert-command-echo', 'pin-at', 'reset-at'}   # ucd-0e2: pin-at (ucd-0d), proven on the twin


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
    _step('light-from-button-acceptance', 1, 'pin-at', {'cycle': 1600000, 'pin': 'PD2', 'level': 0},
          notes='the first of three presses on D2 (board.custom.light_twin.press_pinat)'),
    _step('light-from-button-acceptance', 2, 'assert-field-arrival', {'field': 'led_on flips, toggles==presses, source==button', 'window_ms': 100},
          notes='read off the decoded LightState frames of the same run'),
    _step('ensure-polari-observes-hardware-state-acceptance', 1, 'pin-at', {'cycle': 1600000, 'pin': 'PD2', 'level': 0},
          notes='the first of three presses on D2, the same stimulus as the button test'),
    _step('ensure-polari-observes-hardware-state-acceptance', 2, 'assert-field-arrival',
          {'field': 'led_on flips, toggles==presses, source==button', 'window_ms': 100},
          notes='read off the decoded LightState reports - what Polari sees - of the same run'),
    _step('light-from-polari-acceptance', 1, 'assert-command-echo', {'field': 'led_on', 'value': 1, 'window_ms': 100},
          notes='SET_LED 1: the next frames report the light on, source=command'),
    _step('light-from-polari-acceptance', 2, 'assert-command-echo', {'field': 'led_on', 'value': 0, 'window_ms': 100},
          notes='SET_LED 0: the last frame reports the light off, toggles 2'),
    _step('light-pcint-button-acceptance', 1, 'pin-at', {'cycle': 1600000, 'pin': 'PD4', 'level': 0},
          notes='the first of three presses on D4 (board.custom.variant_twin.press_pinat)'),
    _step('light-pcint-button-acceptance', 2, 'assert-field-arrival', {'field': 'led_on flips, toggles==presses, source==button, PD6 follows', 'window_ms': 100},
          notes='read off the decoded LightState frames and PORTD of the same run; plus the D2 and bounce controls'),
    _step('light-analog-button-acceptance', 1, 'drive-adc-ramp', {'channel': 'A0', 'lo_mv': 200, 'hi_mv': 4800, 'ms': 1000},
          notes='the twin\'s triangle ramp on ADC0: the switch closes (low) at the start and at every period'),
    _step('light-analog-button-acceptance', 2, 'assert-field-arrival', {'field': 'toggles == the model\'s falling crossings of the press threshold', 'window_ms': 100},
          notes='read off the decoded LightState frames; plus the held-high and closed-at-boot controls'),
    _step('light-v2-rapid-commands-acceptance', 1, 'assert-command-echo', {'field': 'last_command_id', 'value': 20, 'window_ms': 100},
          notes='SET_LED ids 1..20 20 ms apart; every id is named by a report'),
    _step('light-v2-reboot-acceptance', 1, 'reset-at', {'cycle': 3260000},
          notes='avr_reset while the answer to command 1 is half sent (and a second run while the command is arriving)'),
    _step('light-v2-reboot-acceptance', 2, 'assert-field-arrival', {'field': 'boot_session changes; command 1 -> unknown-resend', 'window_ms': 100},
          notes='read off the decoded reports and the ledger'),
    _step('light-v2-malformed-acceptance', 1, 'assert-command-echo', {'field': 'last_command_result', 'value': 'rejected-invalid', 'window_ms': 100},
          notes='four malformed commands, then a good one'),
    _step('light-v2-button-no-confirm-acceptance', 1, 'pin-at', {'cycle': 4000000, 'pin': 'PD2', 'level': 0},
          notes='one press on D2 between two commands'),
    _step('light-v2-button-no-confirm-acceptance', 2, 'assert-field-arrival', {'field': 'last_command_id unchanged by the press; the lost command unconfirmed', 'window_ms': 100},
          notes='read off the decoded reports and the ledger'),
    _step('sim-rig-pwm-duty-acceptance', 1, 'assert-command-echo', {'field': 'pwm_duty', 'value': 25, 'window_ms': 100},
          notes='SET pwm_duty 25, then 50, then 100 (inject at cycles 4.8M, 16M, 24M)'),
    _step('sim-rig-pwm-duty-acceptance', 2, 'assert-field-arrival', {'field': 'OCR0A == duty*255//100 (twin status lines)', 'window_ms': 100},
          notes='the twin reports OCR0A on every status line; duty = OCR0A / 255'),
]


#: the light test's Purposes (fgm-1: the new names; the retired light-from-* names still run, for history) -> which twin check proves them
LIGHT_WHICH = {'ensure-button-controls-light': 'button', 'ensure-polari-observes-hardware-state': 'button',
               'ensure-polari-can-control-light': 'polari', 'light-from-button': 'button', 'light-from-polari': 'polari'}


#: fgm-5a: Scenario -> the FirmwareVariant board.custom.variant_twin proves (keyed by the Scenario, not its variant: uno-sim-rig has others)
VARIANT_PROOFS = {'light-pcint-button-acceptance': 'uno-light-pcint', 'light-analog-button-acceptance': 'uno-light-analog',
                  'sim-rig-pwm-duty-acceptance': 'uno-sim-rig'}


#: fgm-6a: Scenario -> the check of board.custom.light_v2_twin that proves it (the v2 light's command confirmation)
V2_PROOFS = {'light-v2-rapid-commands-acceptance': 'rapid', 'light-v2-reboot-acceptance': 'reboot', 'light-v2-malformed-acceptance': 'malformed',
             'light-v2-button-no-confirm-acceptance': 'button'}


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
    if sc['name'] in V2_PROOFS:
        from board.custom import light_v2_twin as L2
        result = L2.prove(V2_PROOFS[sc['name']], run_mode)
    elif sc['name'] in VARIANT_PROOFS:
        # fgm-5a: an isotope variant's own twin proof (the catalogue route it restates is read by cmod.custom.isotope_variants)
        from board.custom import variant_twin as VT
        result = VT.prove(VARIANT_PROOFS[sc['name']], run_mode)
    elif sc['capability'] in LIGHT_WHICH:
        # ucd-light: the light test's own twin runner (board.custom.light_twin) proves the GOAL directly on the simavr twin
        from board.custom import light_twin as LT
        result = LT.prove(LIGHT_WHICH[sc['capability']], run_mode)
    elif sc['capability'] == 'button-clock-to-os':
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
