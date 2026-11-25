"""
@module hwnocode.hwnocode_seed

THE hn-0 ROWS (HARDWARE_NOCODE_PLAN.md §7 hn-0): the HardwareNoCodeSolution `uno-temp-split` + one HardwareNodePlacement per node (the
placement is derived here — pure Python, no engine), its canvas SolutionDefinition and the backend half hn-split derives
(`uno-temp-split.backend`), the AnalysisDefinition + EventTrigger that run that half on every SimRigState frame of `uno-digital-twin`, and
the grpcbridge HardwareInterfaceBinding that IS its hw-interface node, and the GraphDefinition the page's chart renders. Code-owned (re-seed → they follow the code) except the
hand-set fields: `firmware_runtime` (the person's knob, D-hn-3), titles and notes; the trigger's knobs (`inputs_json`) and
`enabled` stay as the instance has them.
"""
from hwnocode.hwnocode_basis import (HardwareNoCodeSolution, HardwareNodePlacement, Runtime, SchematicComponent, SchematicComponentPort,
                                     SchematicComponentPart, SchematicComponentCheck, HardwareFeature)
from hwnocode.custom import schematic_seed as SS
from hwnocode.custom import schematic_solve as _SOLVE
from hwnocode.custom import seed_rows as SR
from hwnocode.custom.runtimes import RUNTIME_ROWS


def _owned(rows, keep=('title', 'notes')):
    return [dict(r, _converge=[k for k in r if k != 'name' and k not in keep]) for r in rows]


def _pairs():
    SOLVED = _SOLVE.seed_rows()
    from polariApiServer.solutionDefinition import SolutionDefinition
    from polariNoCode.analysis_calls import AnalysisDefinition
    from polariNoCode.event_triggers import EventTrigger
    from grpcbridge.mapping_basis import HardwareInterfaceBinding
    from polariApiServer.graphDefinition import GraphDefinition
    from hwnocode.hwnocode_page import SEED_HWNOCODE_GRAPHS
    sols, places = SR.solution_rows()
    return [
        ('HardwareNoCodeSolution', HardwareNoCodeSolution, _owned(sols, keep=('title', 'notes', 'firmware_runtime'))),
        ('HardwareNodePlacement', HardwareNodePlacement, _owned(places, keep=('notes',))),
        ('SolutionDefinition', SolutionDefinition, _owned(SR.solution_definitions(), keep=())),
        ('AnalysisDefinition', AnalysisDefinition, _owned(SR.ANALYSES, keep=('notes', 'enabled'))),
        ('EventTrigger', EventTrigger, _owned(SR.TRIGGERS, keep=('notes', 'enabled', 'inputs_json', 'cooldown_s'))),
        ('HardwareInterfaceBinding', HardwareInterfaceBinding, _owned(SR.BINDINGS, keep=('notes', 'port'))),
        ('GraphDefinition', GraphDefinition, _owned(SEED_HWNOCODE_GRAPHS, keep=('description',))),
        ('Runtime', Runtime, _owned(RUNTIME_ROWS, keep=('notes',))),
        # cb-1 / cb-2 prototype (COMPONENT_BINDING_PLAN.md): the user's drawing as rows. A feature is a person's to edit, so
        # nothing on it converges; components, ports and parts follow the code except what a person fills in.
        # cb-3: the SOLVED rows of every recorded HardwareSolution (custom/solved/*.json, hwnocode.custom.schematic_solve) - derived, so
        # code-owned: re-solve and re-record, the rows follow (a person's notes stay)
        ('SchematicComponent', SchematicComponent, _owned(SS.COMPONENTS, keep=('title', 'notes', 'protocol')) + _owned(SOLVED['SchematicComponent'], keep=('notes',))),
        ('SchematicComponentPort', SchematicComponentPort, _owned(SS.PORTS, keep=('notes', 'chip', 'pin', 'pin_source'))
         + _owned(SOLVED['SchematicComponentPort'], keep=())),
        ('SchematicComponentPart', SchematicComponentPart, _owned(SS.PARTS, keep=('notes', 'value')) + _owned(SOLVED['SchematicComponentPart'], keep=())),
        ('SchematicComponentCheck', SchematicComponentCheck, _owned(SOLVED['SchematicComponentCheck'], keep=('notes',))),
        ('HardwareFeature', HardwareFeature, _owned(SS.FEATURES, keep=tuple(k for f in SS.FEATURES for k in f)) + _owned(SOLVED['HardwareFeature'], keep=('notes',))),
    ]


HWNOCODE_SEED_PAIRS = _pairs()
