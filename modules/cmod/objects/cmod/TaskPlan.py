"""
@module cmod.objects.cmod.TaskPlan

TaskPlan - one class per file (design section 7). FIRMWARE_GENERATION_MODULE_PLAN.md section 9 (fgm-3); SYSTEM_HIERARCHY_TERMINOLOGY.md section 8.
"""
from objectTreeDecorators import treeObject, treeObjectInit


class TaskPlan(treeObject):
    """What it is: the set of Tasks derived for ONE Hardware System from a Hardware Mission - how the Mission's work splits across the system's processors (each Task on exactly one), which runtime tier
    and which isotope variants (routes) it was worked out with, and on which pins (`pins_json`: profile -> pin, from the solver candidate it was seeded from). The Tasks are DERIVED and editable
    (`source` says derived or edited; an edit is a DerivedOverride, never a rewrite). `designed_for_json` is the origin context - the Hardware System, processors, tier, variants and the solver run's
    sha256 - written ONCE and never changed. `also_runs_on_json` lists every other hardware the plan was carried to, each with HOW WE KNOW (resolver-valid, which only means every checkable requirement
    is met; then proven-on-twin; then proven-on-hardware) and what had to change.
    Related concepts: `TaskDefinition`, `TaskTrigger`, `TaskStructBinding`, `HardwareMission`, `SolveRun` (the attempt that seeded it), `HardwareSystem`.
    """

    plain_words = ('A task plan is the list of jobs the board does for one Mission on one hardware system, worked out by the computer and editable by a person. '
                   'It keeps what it was designed for, and every other hardware it is known to work on, with how we know.')

    @treeObjectInit
    def __init__(self, name: str = '', mission: str = '', hardware_system: str = '', processors_json: str = '[]', solve_run: str = '', candidate: str = '', tier: str = '',
                 variants_json: str = '{}', pins_json: str = '[]', designed_for_json: str = '{}', also_runs_on_json: str = '[]', source: str = 'derived', task_count: int = 0,
                 derived_at: str = '', who: str = '', notes: str = '', manager=None):
        self.name = name                          # '<mission>:<hardware system>'
        self.mission = mission                    # the HardwareMission name
        self.hardware_system = hardware_system    # the HardwareSystem name
        self.processors_json = processors_json    # [{name, board, soc, role}] the processors of the system that run Tasks
        self.solve_run = solve_run                # the SolveRun it was seeded from ('' = no run existed: variants and pins undetermined)
        self.candidate = candidate                # the solver candidate id
        self.tier = tier                          # bare-c | freertos | zephyr
        self.variants_json = variants_json        # {job: route}
        self.pins_json = pins_json                # [{role, kind, job, route, pin, function}] profile -> pin
        self.designed_for_json = designed_for_json   # IMMUTABLE once written: {hardware_system, processors, tier, variants, pins, solve_run, result_sha256, by, at}
        self.also_runs_on_json = also_runs_on_json   # [{hardware, tier, how_we_know: resolver-valid|proven-on-twin|proven-on-hardware, what_changed, at}]
        self.source = source                      # derived | edited
        self.task_count = task_count
        self.derived_at = derived_at
        self.who = who
        self.notes = notes
