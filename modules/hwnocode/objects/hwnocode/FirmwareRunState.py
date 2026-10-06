"""
@module hwnocode.objects.hwnocode.FirmwareRunState

FirmwareRunState — one class per file (design §7).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class FirmwareRunState(treeObject):
    """What it is: the `firmware-run` NODE KIND, category **Cross-Domain** (fs-0/fs-2, DEMONSTRABLES_PLAN.md §9; his
    message 2026-10-05: "a state that takes a Firmware solution based on a C runtime, and accepts a board definition
    ... and validated when running that it still exists"). It names one `FirmwareSolution` (cmod) + a board (fixed or
    inherited from the solution's own `board_variable`) + `mode` (digital-twin | hardware — the ONE place
    `HWNOCODE_HARDWARE_MODE` is read, moved here from `hwnocode.custom.solutions._hardware_route`, D-fs-3's "Firmware
    Run" node). Executing it runs `cmod.custom.firmware.validate -> build -> run` (never reimplemented) and records
    which route was taken. A Cross-Domain Solution (D-fs-3: bridging/relay ONLY, no compute) may hold exactly this
    kind plus `HardwareInterface` (Bridge), `BackendStateChange`/`StateChangeCommit` (Relay) and the existing API-call/
    frontend-emit kinds — never an `AnalysisCall`/`ConditionalChain`/`VariableAssignment` (that is compute; it lives in
    a plain backend `SolutionDefinition` a Relay state calls OUT to, e.g. `temp-analysis`).
    Related concepts: cmod `FirmwareSolution`, `HardwareInterface` (Bridge), `HardwareSubgraph` (the firmware-only
    predecessor this supersedes inside a Cross-Domain canvas), `hwnocode.custom.cross_domain` (the validator).
    """

    plain_words = 'A firmware run block takes a firmware solution and a board, checks it still exists, and runs it — flashed or simulated — reporting which route it took.'

    statePalette = {
        'nodeKind': 'firmware-run', 'displayName': 'Firmware Run', 'category': 'Cross-Domain', 'icon': 'memory',
        'color': '#4527A0', 'placement': 'bridge', 'language': 'n/a (orchestrates cmod-glue + the installer/twin)',
        'overlay': 'firmware-run',
        'description': 'Takes a cmod FirmwareSolution + a board (fixed or variable, validated at run time) + mode '
                       '(digital-twin | hardware — the HARDWARE_MODE knob, read here); runs validate -> build -> run '
                       'and reports the build id + the route taken. No compute: this IS the Cross-Domain category\'s '
                       'only entry point into a firmware solution.',
        'displayFields': ['firmware_solution', 'mode'],
        'variables': [{'name': 'firmware_solution', 'displayName': 'Firmware solution', 'type': 'string', 'defaultValue': ''},
                      {'name': 'board_variable', 'displayName': 'Board (variable)', 'type': 'string', 'defaultValue': ''},
                      {'name': 'mode', 'displayName': 'Mode', 'type': 'string', 'defaultValue': 'digital-twin'}],
        'slots': {'inputs': 0, 'outputs': 1, 'outputLabels': ['frames']},
    }

    @treeObjectInit
    def __init__(self, name: str = '', firmware_solution: str = '', board_variable: str = '', mode: str = 'digital-twin',
                 last_build_id: str = '', route_taken: str = '', route_why: str = '', title: str = '', notes: str = '',
                 manager=None):
        self.name = name
        self.firmware_solution = firmware_solution   # a cmod FirmwareSolution row name
        self.board_variable = board_variable         # '' = use the solution's own board; else resolved at run time
        self.mode = mode                             # digital-twin | hardware (HWNOCODE_HARDWARE_MODE's new home)
        self.last_build_id = last_build_id           # the CGlueBuild / FirmwareBuild this run last produced
        self.route_taken = route_taken               # digital-twin | hardware | refused
        self.route_why = route_why
        self.title = title
        self.notes = notes
