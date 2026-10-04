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
                             TargetDefinition, CapabilityDefinition, CapabilityInstance)
from cmod.custom.rows import template_rows, graph_rows
from cmod.custom import targets as T
from cmod.custom.graph_seed import GRAPH as _DEFAULT_GRAPH

_HAND = ('title', 'notes')


def _owned(rows, keep=_HAND):
    return [dict(r, _converge=[k for k in r if k != 'name' and k not in keep]) for r in rows]


SEED_ROWS = template_rows()
GRAPH_ROWS = graph_rows()
TARGET_ROWS = T.derive(_DEFAULT_GRAPH)
CAPABILITY_ROWS = [T.temperature_sensor_capability(_DEFAULT_GRAPH)]
CAPABILITY_INSTANCE_ROWS = T.temperature_sensor_instances(_DEFAULT_GRAPH)

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
]
