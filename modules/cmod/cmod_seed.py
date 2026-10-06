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
                             TargetDefinition, CapabilityDefinition, CapabilityInstance,
                             FirmwareSolution, ScheduleSlot, RegisterAssignment)
from cmod.custom.rows import template_rows, graph_rows
from cmod.custom import targets as T
from cmod.custom import firmware as FW
from cmod.custom.graph_seed import GRAPH as _DEFAULT_GRAPH

_HAND = ('title', 'notes')


def _owned(rows, keep=_HAND):
    return [dict(r, _converge=[k for k in r if k != 'name' and k not in keep]) for r in rows]


SEED_ROWS = template_rows()
GRAPH_ROWS = graph_rows()
TARGET_ROWS = T.derive(_DEFAULT_GRAPH)
CAPABILITY_ROWS = [T.temperature_sensor_capability(_DEFAULT_GRAPH)]
CAPABILITY_INSTANCE_ROWS = T.temperature_sensor_instances(_DEFAULT_GRAPH)

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
    ('FirmwareSolution', FirmwareSolution, _owned(FIRMWARE_ROWS, keep=('title', 'notes'))),
    ('ScheduleSlot', ScheduleSlot, _owned(SCHEDULE_ROWS, keep=('notes',))),
    ('RegisterAssignment', RegisterAssignment, _owned(ASSIGNMENT_ROWS, keep=('notes',))),
]
