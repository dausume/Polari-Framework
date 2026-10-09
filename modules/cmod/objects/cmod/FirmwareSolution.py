"""
@module cmod.objects.cmod.FirmwareSolution

FirmwareSolution — one class per file (design §7).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class FirmwareSolution(treeObject):
    """What it is: fs-0 (DEMONSTRABLES_PLAN.md §9, his message 2026-10-05: "What I want to be able to do is define tasks
    ... and then define register assignments, and what the solution does is take in a Board Definition and puts out a
    finished firmware to be flashed or simulated"). A FirmwareSolution takes a `CGraph` (its TASKS = the graph's c-atom
    `CGraphNode`s) and a board — EITHER a fixed `board_definition` (a `BoardDefinition` row name) OR a `board_variable`
    (a free name resolved at RUN TIME from the known/usable boards, his words exactly: "validated when running that it
    still exists") — and produces a `FirmwareBuild` (board's existing row; `cmod-glue` already renders + builds the C
    project, unchanged). `runtime` is c-device (flash a real board) or c-digital-twin (run the SAME image on simavr) —
    never anything else (RULE 2: the graph is C by construction). The SCHEDULE (`ScheduleSlot`) and REGISTER MAP
    (`RegisterAssignment`) are DERIVED from this row's graph + board, never authored (D-fs-1/D-fs-2, his picks
    2026-10-05) — see `cmod.custom.firmware.schedule_for` / `assignments_for`. This row holds no compute of its own;
    `validate()` refuses a stale `board_variable`, an unresolved required target, or a pin conflict, naming which.
    Related concepts: `CGraph`, `CGraphNode`, `TargetDefinition`, board's `BoardDefinition` / `BoardPin` / `FirmwareBuild`,
    hwnocode's Cross-Domain `FirmwareRunState` (the ONE place that calls `validate -> build -> run` on this row).
    """

    plain_words = ('A firmware solution takes a C task graph and a board (fixed or chosen at run time) and produces a '
                   'real firmware image to flash or simulate — the schedule and the pin assignments are derived, never typed in.')

    @treeObjectInit
    def __init__(self, name: str = '', title: str = '', graph: str = '', board_definition: str = '', board_variable: str = '',
                 runtime: str = 'c-device', status: str = 'seeded', last_build: str = '', board_resolved: str = '',
                 board_exists: bool = True, validation: str = '', validation_why: str = '', task_count: int = 0,
                 purpose: str = '', notes: str = '', proof_status: str = 'planned', proof_why: str = '', purposes_total: int = 0,
                 purposes_proven_twin: int = 0, purposes_proven_hardware: int = 0, manager=None):
        self.name = name
        self.title = title
        self.graph = graph                        # the CGraph whose c-atom nodes ARE the tasks
        self.board_definition = board_definition    # a fixed BoardDefinition row name ('' when using board_variable)
        self.board_variable = board_variable        # a free name resolved at run time from the known/usable boards
        self.runtime = runtime                      # c-device | c-digital-twin
        self.status = status                        # seeded | validated | built | run | refused
        self.last_build = last_build                # the CGlueBuild / FirmwareBuild this solution last produced
        self.board_resolved = board_resolved        # the board name validate()/run() actually resolved to
        self.board_exists = board_exists            # false when board_variable named something no longer in the register
        self.validation = validation                # ok | refused
        self.validation_why = validation_why
        self.task_count = task_count
        self.purpose = purpose
        self.notes = notes
        # his ruling 2026-10-09: the firmware's state is a SUMMARY of its Purposes (the weakest on the ladder failing < planned <
        # proven-on-twin < proven-on-hardware), the way a Purpose summarizes its tasks — derived (capabilities.purpose_summary)
        self.proof_status = proof_status
        self.proof_why = proof_why
        self.purposes_total = purposes_total
        self.purposes_proven_twin = purposes_proven_twin
        self.purposes_proven_hardware = purposes_proven_hardware
