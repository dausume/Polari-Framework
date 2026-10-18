"""
@module cmod.custom.mission_seeds

The seeded Hardware Mission (mis-0, MISSION_PROFILE_SOLVER_PLAN.md section 2.1): `uno-light-mission`, the light test as a Mission
above its four Purposes. Every Purpose name is a real CapabilityDefinition seed (`cmod.custom.purpose_seeds`); the participants use
the same shape as a Purpose's (role / kind / ref / variant) with kind hardware | software | person. The board's package and USB
interface are PENDING identification (his ruling 2026-10-15), so that variant says so. Nothing here is a number.
"""
import json

LIGHT_MISSION = 'uno-light-mission'

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
}]
