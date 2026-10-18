"""
@module cmod.objects.cmod.TaskTrigger

TaskTrigger - one class per file (design section 7). FIRMWARE_GENERATION_MODULE_PLAN.md section 9 (fgm-3); the design ancestor of FIRMWARE_FLOW_STATES_PLAN.md's trigger flow states.
"""
from objectTreeDecorators import treeObject, treeObjectInit


class TaskTrigger(treeObject):
    """What it is: what STARTS one Task - `boot` (the board starts or restarts), `edge` (a change on a line, such as a button press), `period` (every so many milliseconds), `command` (a command arrives
    from Polari) or `message` (a message from another part). It is derived from the Purpose's own trigger and the chosen solver candidate: `how` says whether the line is watched by an interrupt or
    polled in the main loop (the candidate's route), `source` names the line or interrupt, `debounce_ms` is the Purpose's own debounce criterion, and `period_ms` the report period. A Task has exactly one.
    Related concepts: `TaskDefinition`, `TaskPlan`, `IsotopeVariant` (the route), `CapabilityDefinition` (the Purpose's trigger).
    """

    plain_words = 'A trigger is what starts a task: the board starting up, a change on a wire, a timer, or a command from Polari.'

    @treeObjectInit
    def __init__(self, name: str = '', plan: str = '', task: str = '', kind: str = 'boot', what: str = '', source: str = '', how: str = '', route: str = '',
                 debounce_ms: float = -1.0, period_ms: float = -1.0, period_basis: str = '', notes: str = '', manager=None):
        self.name = name                # '<plan>:<task>' (one per task)
        self.plan = plan
        self.task = task
        self.kind = kind                # boot | edge | period | command | message
        self.what = what                # the Purpose's own words
        self.source = source            # the pin or interrupt that fires it ('A0', 'USART_RX_vect'), '' when none
        self.how = how                  # at boot | interrupt | polled in the main loop | on the 1 ms tick | ...
        self.route = route              # the chosen route of the job that notices it (gpio-poll, ext-interrupt ...)
        self.debounce_ms = debounce_ms  # -1 = none stated
        self.period_ms = period_ms      # -1 = not periodic
        self.period_basis = period_basis
        self.notes = notes
