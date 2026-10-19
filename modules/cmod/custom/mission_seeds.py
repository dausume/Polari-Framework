"""
@module cmod.custom.mission_seeds

The seeded Hardware Mission (mis-0, MISSION_PROFILE_SOLVER_PLAN.md section 2.1): `uno-light-mission`, the light test as a Mission
above its four Purposes. Every Purpose name is a real CapabilityDefinition seed (`cmod.custom.purpose_seeds`); the participants use
the same shape as a Purpose's (role / kind / ref / variant) with kind hardware | software | person. The board's package and USB
interface are PENDING identification (his ruling 2026-10-15), so that variant says so. Nothing here is a number.
"""
import json

LIGHT_MISSION = 'uno-light-mission'

#: smp-0 (FIRMWARE_SCORE_PROFILES_PLAN.md section 13): the curated sample of the light Mission - five successes (four UNO, one ESP32-C3) and two failures, each a real firmware config. S5's config is
#: named here before it exists on purpose: until it is built the scores page says "not built yet" (never a failure). F2's safety deadline is THIS entry's own flag on the Purpose's real deadline.
SAMPLE_SOLUTIONS = [
    {'id': 'S1', 'config': 'uno-light', 'kind': 'success', 'device': 'Arduino UNO (ATmega328P)',
     'components': 'button on the external interrupt INT0 (D2) · LED on a plain output pin (D6) · sense line polled in the main loop (D3, jumper from D6)',
     'why': 'the core demo and the baseline: the simplest route for every job. The struct decides the light (led_follow_state is the only pin writer) and the report\'s led_on is what the sense line reads.'},
    {'id': 'S2', 'config': 'uno-light-all-pcint', 'kind': 'success', 'device': 'Arduino UNO (ATmega328P)',
     'components': 'button on a pin-change interrupt (D4) · sense line on a pin-change interrupt (D8) · LED on a plain output pin (D6)',
     'why': 'both inputs on pin-change interrupts, so neither external-interrupt pin is used and the two inputs sit in different pin-change banks.'},
    {'id': 'S3', 'config': 'uno-light-pwm-analog', 'kind': 'success', 'device': 'Arduino UNO (ATmega328P)',
     'components': 'button read as a voltage on A0 (analog threshold) · LED on Timer0\'s PWM output (D6) · sense line polled (D3)',
     'why': 'a button with no digital pin at all, and an LED driven by a timer output (held at 100 % duty for on, disconnected for off) - both still decided by the struct.'},
    {'id': 'S4', 'config': 'uno-light-transistor', 'kind': 'success', 'device': 'Arduino UNO (ATmega328P)',
     'components': 'LED switched through one of the kit\'s transistors (D6 drives its base) · button on INT0 (D2) · sense line polled (D3)',
     'why': 'a driver stage for a load a pin could not drive. The twin runs the same C as S1 and cannot show the transistor switching: that is wiring, documented in the config.'},
    {'id': 'S5', 'config': 'c3-light-freertos', 'kind': 'success', 'device': 'ESP32-C3 (FreeRTOS)', 'twin_only': True,
     'components': 'the same Mission as FreeRTOS tasks on the ESP32-C3 (twin only: no C3 on the bench)',
     'why': 'the same light, struct-controlled, on a second kind of device and a second kind of runtime.'},
    {'id': 'F1', 'config': 'uno-light-unsensed', 'kind': 'failure', 'device': 'Arduino UNO (ATmega328P)',
     'components': 'button on INT0 (D2) · LED on a plain output pin (D6) · NO sense line',
     'why': 'the light as it was before the sense line: it works, but the board reports what it commanded and Polari cannot observe the hardware state, which the Mission\'s observe Purpose needs.'},
    {'id': 'F2', 'config': 'uno-light-slow-loop', 'kind': 'failure', 'device': 'Arduino UNO (ATmega328P)',
     'components': 'uno-light with every main-loop pass held for 250 ms (button on INT0 · LED on D6 · sense line polled on D3)',
     'safety_deadline': {'purpose': 'ensure-button-controls-light', 'key': 'max_latency_ms', 'safety_critical': True},
     'why': 'a deliberately slow loop against a button deadline flagged safety-critical for this sample (the real Purpose is not changed): shows the safety-critical failure rule.'},
]

MISSION_SEEDS = [{
    'name': LIGHT_MISSION,
    'title': 'Prove Polari and one board can control and observe one light in both directions',
    'goal': 'Prove Polari and one board can control and observe one light in both directions',
    'purposes_json': json.dumps([
        {'purpose': 'initialization', 'importance': 'required'},
        {'purpose': 'ensure-button-controls-light', 'importance': 'required'},
        {'purpose': 'ensure-polari-can-control-light', 'importance': 'required'},
        {'purpose': 'ensure-polari-observes-hardware-state', 'importance': 'required'}]),
    'participants_json': json.dumps([
        {'role': 'board', 'kind': 'hardware', 'ref': 'arduino-uno-r3', 'variant': 'pending'},
        {'role': 'chip', 'kind': 'hardware', 'ref': 'atmega328p'},
        {'role': 'host bridge', 'kind': 'software', 'ref': 'uno-light-bridge'},
        {'role': 'Polari', 'kind': 'software', 'ref': 'polari'},
        {'role': 'person pressing the button', 'kind': 'person', 'ref': 'bench-operator'}]),
    'settings_json': json.dumps({'objective': 'minimum-resources'}),
    'constraints_json': json.dumps({'stage': 'S1-breadboard'}),
    'lifecycle': 'enabled',
    'notes': 'mis-0 seed: the light test as a Mission above its Purposes.',
    'sample_solutions': json.dumps(SAMPLE_SOLUTIONS),
}]
