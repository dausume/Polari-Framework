"""
@module cmod.cmod_seed

THE ATOMS AS ROWS (C_MODULARIZATION_PLAN.md §2): every TEMPLATE project's committed `polari-firmware.json` (the UNO:
board/custom/firmware/uno/polari-firmware.json) projected into CProject / CModule / CFunctionAtom / CPort rows by
custom/rows.py. The manifest is derived and committed, so a boot needs no parse and no engine; the rows are code-owned
(re-seed → they follow the manifest) except the hand-set `title` / `notes`, which stay as the instance has them.
cmod-1: the seeded graphs (custom/graph_seed.py) as CGraph / CGraphNode / CGraphEdge rows, and their committed glue-build record
(custom/glue_builds/<graph>.json) as the CGlueBuild row — derived fields from the manifest + the record, nothing built at boot.
demo-4: TargetDefinition rows derived over the seeded graph's nodes/ports (custom/targets.py) + the seeded
"temperature sensor solution" CapabilityDefinition and its two CapabilityInstance rows (his worked example).
"""
from cmod.cmod_basis import (CProject, CModule, CFunctionAtom, CPort, CGraph, CGraphNode, CGraphEdge, CGlueBuild,
                             TargetDefinition, CapabilityDefinition, CapabilityInstance, FirmwareExport,
                             FirmwareSolution, ScheduleSlot, RegisterAssignment, PinClaim, PeripheralClaim,
                             HardwareBinding)
from cmod.custom.rows import template_rows, graph_rows
from cmod.custom import targets as T
from cmod.custom import firmware as FW
from cmod.custom import capabilities as CAP
import json

from cmod.custom.graph_seed import GRAPH as _DEFAULT_GRAPH
from cmod.custom.graph_seed import BC_GRAPH as _BC_GRAPH

_HAND = ('title', 'notes')


def _owned(rows, keep=_HAND):
    return [dict(r, _converge=[k for k in r if k != 'name' and k not in keep]) for r in rows]


SEED_ROWS = template_rows()
GRAPH_ROWS = graph_rows()
TARGET_ROWS = T.derive(_DEFAULT_GRAPH) + T.derive(_BC_GRAPH)

# hw priorities P1 (AI-Notes/plans/HARDWARE_DEV_PRIORITIES.md §1/§4): the two widened-field seeds, over the SAME
# uno-sim-rig-graph as the demo-4 capability above (no new graph, no new canvas) — `status`/`last_proof` are DERIVED
# below (cmod.custom.capabilities.derive_status), never hand-set.
_HW_CAPS = [dict(c) for c in CAP.SEED_CAPABILITIES]
for _c in _HW_CAPS:
    _status, _proof, _, _ = CAP.derive_status(_c, manager=None)
    _c['status'], _c['last_proof'] = _status, _proof
_TEMP_TO_OS_INSTANCES = [
    {'name': 'temp-sensor-to-os#%d' % i, 'capability': 'temp-sensor-to-os', 'graph': _DEFAULT_GRAPH, 'index': i,
     'bindings': 'adc.channel=unbound, temp.return=unbound', 'status': 'unbound',
     'notes': 'instance %d of 2 (HARDWARE_DEV_PRIORITIES.md §1 seed 1 — "multiple temperature sensors")' % i}
    for i in (1, 2)]
_led_row = next((a for a in FW.assignments_for(_DEFAULT_GRAPH, 'uno-sim-rig') if a['task'] == 'led' and a['port'] == 'on'), {})
_BLINK_INSTANCES = [
    {'name': 'blink-on-command#1', 'capability': 'blink-on-command', 'graph': _DEFAULT_GRAPH, 'index': 1,
     'bindings': 'led.on=%s' % _led_row.get('lives_on', 'unbound'),
     'status': 'bound' if _led_row.get('status') == 'bound' else 'unbound',
     'notes': 'the one instance (HARDWARE_DEV_PRIORITIES.md §1 seed 2); D13 is already bound by uno-sim-rig\'s own register map'}]

CAPABILITY_ROWS = [T.temperature_sensor_capability(_DEFAULT_GRAPH)] + _HW_CAPS
CAPABILITY_INSTANCE_ROWS = T.temperature_sensor_instances(_DEFAULT_GRAPH) + _TEMP_TO_OS_INSTANCES + _BLINK_INSTANCES

# fs-0 (DEMONSTRABLES_PLAN.md §9): uno-sim-rig — the FIRST FirmwareSolution, over the EXISTING uno-sim-rig-graph +
# board arduino-uno-r3 (no new C, no new graph — the migration's firmware half, his §9(3)). Schedule + register map
# are DERIVED here at seed time (D-fs-1/D-fs-2), same posture as TARGET_ROWS above.
FIRMWARE_NAME = 'uno-sim-rig'
FIRMWARE_ROWS = [{
    'name': FIRMWARE_NAME, 'title': 'UNO sim-rig firmware', 'graph': _DEFAULT_GRAPH, 'board_definition': 'arduino-uno-r3',
    'board_variable': '', 'runtime': 'c-device', 'status': 'seeded', 'last_build': '', 'board_resolved': 'arduino-uno-r3',
    'board_exists': True, 'validation': '', 'validation_why': '', 'task_count': 0,
    'purpose': 'The firmware-only half of the sim-rig: tasks = the 13 atoms of uno-sim-rig-graph, scheduled by their own '
               'ISR/tick/loop/init annotations (never authored), registers bound to arduino-uno-r3\'s pin map (A0/D6/D13/D0/D1); '
               'temp_c and uptime_ms are memory-field targets, exposed unbound (fs-0, his message 2026-10-05).', 'notes': ''}]
SCHEDULE_ROWS = FW.schedule_for(_DEFAULT_GRAPH, FIRMWARE_NAME)
ASSIGNMENT_ROWS = FW.assignments_for(_DEFAULT_GRAPH, FIRMWARE_NAME)
_ok, _why, _ = FW.validate(FIRMWARE_ROWS[0], manager=None)
FIRMWARE_ROWS[0]['task_count'] = sum(1 for n in GRAPH_ROWS['CGraphNode'] if n['graph'] == _DEFAULT_GRAPH and n['kind'] == 'c-atom')
FIRMWARE_ROWS[0]['validation'] = 'ok' if _ok else 'refused'
FIRMWARE_ROWS[0]['validation_why'] = _why
FIRMWARE_ROWS[0]['status'] = 'validated' if _ok else 'refused'

# ucd-0e2b (UNO_CORE_DEMO_PLAN.md §1/§5f/§5g): uno-button-clock — the SECOND FirmwareSolution, over the NEW
# uno-button-clock-graph (ucd-0e2b's own graph, just seeded in custom/graph_seed.py) + board arduino-uno-r3.
# D2/D3's PinClaim mode/pull/edge are AUTHORED (never derivable from a register name, §5f point 1) — a person's
# choice, carried on the representative RegisterAssignment row's `config_json`, provenance='canvas' SAID so by the
# claim it produces (cmod.custom.claims.pin_claims: 'canvas' once config_json merges anything); D6/D13 (plain
# digital-out) carry their own config_json too, though it only restates `_defaults('digital-out')` — his choice,
# written down rather than left implicit. `keep=('notes', 'config_json')` (same as uno-sim-rig's own row below)
# means config_json SURVIVES every reseed/converge — only this first seed ever sets it.
BC_FIRMWARE_NAME = 'uno-button-clock'
BC_FIRMWARE_ROWS = [{
    'name': BC_FIRMWARE_NAME, 'title': 'UNO button-clock firmware', 'graph': _BC_GRAPH, 'board_definition': 'arduino-uno-r3',
    'board_variable': '', 'runtime': 'c-device', 'status': 'seeded', 'last_build': '', 'board_resolved': 'arduino-uno-r3',
    'board_exists': True, 'validation': '', 'validation_why': '', 'task_count': 0,
    'purpose': 'The firmware-only half of the core demo: a debounced D2 button (INT0, falling, pull-up) toggles D6+D13, a '
               'jumper D6->D3 (INT1, any-edge) independently witnesses the LED line, a software wall clock is synced by '
               'SET_TIME (drift from the 2nd sync on), every transition queues a ButtonClockEvent (UNO_CORE_DEMO_PLAN.md '
               '§1/§5f/§5g, ucd-0e2b).', 'notes': ''}]
BC_SCHEDULE_ROWS = FW.schedule_for(_BC_GRAPH, BC_FIRMWARE_NAME)
BC_ASSIGNMENT_ROWS = FW.assignments_for(_BC_GRAPH, BC_FIRMWARE_NAME)
#: the one source of truth for D2/D3/D6/D13's authored config (cmod.custom.claims.PURE_CONFIG_SEED — claims.py's
#: OWN pure/no-manager fallback reads the SAME constant, so an offline build/prove/selftest and this seed row agree
#: with no duplication); the representative (the '_init' task) of each claimed pin, exactly as
#: `cmod.custom.claims._representative` would itself pick (never a different row — a config_json elsewhere would
#: simply never be read, claims.py's own `cfg_source` search would skip it).
from cmod.custom.claims import PURE_CONFIG_SEED as _PURE_CONFIG_SEED
_BC_CONFIG = _PURE_CONFIG_SEED.get('%s@arduino-uno-r3' % BC_FIRMWARE_NAME, {})
for _a in BC_ASSIGNMENT_ROWS:
    if _a['name'] in _BC_CONFIG:
        _a['config_json'] = json.dumps(_BC_CONFIG[_a['name']])
_missed = set(_BC_CONFIG) - {_a['name'] for _a in BC_ASSIGNMENT_ROWS}
assert not _missed, 'cmod_seed: PURE_CONFIG_SEED names row(s) assignments_for never produced: %s' % sorted(_missed)
_bc_ok, _bc_why, _ = FW.validate(BC_FIRMWARE_ROWS[0], manager=None)
BC_FIRMWARE_ROWS[0]['task_count'] = sum(1 for n in GRAPH_ROWS['CGraphNode'] if n['graph'] == _BC_GRAPH and n['kind'] == 'c-atom')
BC_FIRMWARE_ROWS[0]['validation'] = 'ok' if _bc_ok else 'refused'
BC_FIRMWARE_ROWS[0]['validation_why'] = _bc_why
BC_FIRMWARE_ROWS[0]['status'] = 'validated' if _bc_ok else 'refused'

CMOD_SEED_PAIRS = [
    ('CProject', CProject, _owned(SEED_ROWS['CProject'], keep=('notes',))),
    ('CModule', CModule, _owned(SEED_ROWS['CModule'], keep=('notes',))),
    ('CFunctionAtom', CFunctionAtom, _owned(SEED_ROWS['CFunctionAtom'])),
    ('CPort', CPort, _owned(SEED_ROWS['CPort'], keep=())),
    ('CGraph', CGraph, _owned(GRAPH_ROWS['CGraph'], keep=('title', 'notes'))),
    ('CGraphNode', CGraphNode, _owned(GRAPH_ROWS['CGraphNode'], keep=('notes',))),
    ('CGraphEdge', CGraphEdge, _owned(GRAPH_ROWS['CGraphEdge'], keep=('notes',))),
    ('CGlueBuild', CGlueBuild, _owned(GRAPH_ROWS['CGlueBuild'], keep=('notes',))),
    ('TargetDefinition', TargetDefinition, _owned(TARGET_ROWS, keep=('notes',))),
    ('CapabilityDefinition', CapabilityDefinition, _owned(CAPABILITY_ROWS, keep=('notes',))),
    ('CapabilityInstance', CapabilityInstance, _owned(CAPABILITY_INSTANCE_ROWS, keep=('notes',))),
    ('FirmwareExport', FirmwareExport, []),   # ucd-0f: observed (created by the export door / pol firmware export), never seeded
    ('FirmwareSolution', FirmwareSolution, _owned(FIRMWARE_ROWS + BC_FIRMWARE_ROWS, keep=('title', 'notes'))),
    ('ScheduleSlot', ScheduleSlot, _owned(SCHEDULE_ROWS + BC_SCHEDULE_ROWS, keep=('notes',))),
    ('RegisterAssignment', RegisterAssignment, _owned(ASSIGNMENT_ROWS + BC_ASSIGNMENT_ROWS, keep=('notes', 'config_json'))),
    # ucd-0b: observed rows (materialized by cmod_firmware_api on every GET of a solution, upserted by name) —
    # never seeded, same posture as FirmwareExport above.
    ('PinClaim', PinClaim, []),
    ('PeripheralClaim', PeripheralClaim, []),
]

# ucd-0b2b (§5h, his ruling: "we should have hardware specific objects that are bindings or masks that bind to the
# solutions"): ONE default HardwareBinding per seeded FirmwareSolution, derived from its resolved board — converges
# at boot same as everything above (`_owned`'s keep list spares only `notes`); a person's own canvas-added binding
# is POST-created (cmod.custom.binding.create), never seeded, and is KEPT across a reseed (its own row is never in
# this list, so `_converge` never touches it).
from cmod.custom import binding as _BND
BINDING_ROWS = [_b for _b in (_BND.derive(FIRMWARE_NAME, manager=None), _BND.derive(BC_FIRMWARE_NAME, manager=None)) if _b is not None]
CMOD_SEED_PAIRS.append(('HardwareBinding', HardwareBinding, _owned(BINDING_ROWS, keep=('notes',))))
