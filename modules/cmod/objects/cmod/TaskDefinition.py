"""
@module cmod.objects.cmod.TaskDefinition

TaskDefinition - one class per file (design section 7). FIRMWARE_GENERATION_MODULE_PLAN.md section 9 (fgm-3).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class TaskDefinition(treeObject):
    """What it is: one TASK of a Task Plan - a named piece of firmware work that runs on ONE processor, is started by ONE trigger, and is made of ordered steps (C atoms). It is DERIVED by
    code from the Hardware Mission's Purposes, their graph's atoms and criteria, and the chosen solver candidate; nothing on this row is typed. A person's correction of the priority, the
    trigger, the order of the steps, the deadline or the context is a `DerivedOverride` (who, when, why) shown BESIDE the derived value, never written over it.
    `deadline_ms` / `period_ms` come from a Purpose criterion or from rt-0's labelled estimate (-1 = undetermined, said in `deadline_basis`). `priority` is deadline-monotonic (a shorter deadline is a
    higher priority; equal deadlines: the more important Purpose wins; still equal: the Mission's Purpose order, marked as a tie); 1 is the highest and 0 means the task runs once at boot before
    any scheduling. `context` is where the task runs: init | isr | loop | task (a thread on an RTOS). `agreement` compares that context with the schedule lane the task's own atoms derive
    (`cmod.custom.firmware.schedule_for`): agrees | disagrees | unchecked, each with its reason - never silently re-labelled.
    Related concepts: `TaskPlan` (the whole set for one Hardware System), `TaskTrigger`, `TaskStructBinding`, `HardwareMission`, `CapabilityDefinition` (the Purposes), `ScheduleSlot`, `DerivedOverride`.
    """

    plain_words = ('A task is one job the board does: what starts it, what steps it takes, how soon it must be done, and how urgent it is. '
                   'The computer works it out from the Mission; a person can change it, and the change is kept beside the worked-out value.')

    @treeObjectInit
    def __init__(self, name: str = '', plan: str = '', task: str = '', title: str = '', processor: str = '', purposes_json: str = '[]', steps_json: str = '[]',
                 steps_order: str = '', trigger: str = '', trigger_what: str = '', deadline_ms: float = -1.0, deadline_basis: str = '', period_ms: float = -1.0, priority: int = 0,
                 priority_basis: str = '', importance: str = '', context: str = '', routes_json: str = '[]', pins_json: str = '[]', agreement: str = '', agreement_why: str = '',
                 source: str = 'derived', notes: str = '', manager=None):
        self.name = name                          # '<plan>:<task>'
        self.plan = plan                          # the TaskPlan name
        self.task = task                          # the short name: init | handle-button-press | relay-state | receive-command | sense
        self.title = title
        self.processor = processor                # ONE processor ('arduino-uno-r3:U1')
        self.purposes_json = purposes_json        # [Purpose names it serves]
        self.steps_json = steps_json              # [{n, instance, atom, lane, role}] in order (C atom refs)
        self.steps_order = steps_order            # the instance names, comma separated - the field a person edits to reorder
        self.trigger = trigger                    # boot | edge | period | command | message
        self.trigger_what = trigger_what
        self.deadline_ms = deadline_ms            # -1 = undetermined
        self.deadline_basis = deadline_basis
        self.period_ms = period_ms                # -1 = not periodic / undetermined
        self.priority = priority                  # 1 = highest; 0 = runs once at boot
        self.priority_basis = priority_basis
        self.importance = importance              # safety | required | important | desired
        self.context = context                    # init | isr | loop | task
        self.routes_json = routes_json            # [{job, route, status}] the chosen candidate's way of doing each job this task needs
        self.pins_json = pins_json                # [{role, pin, function}] profile -> pin from the candidate
        self.agreement = agreement                # agrees | disagrees | unchecked
        self.agreement_why = agreement_why
        self.source = source                      # derived | edited (edited = a DerivedOverride is active on this task)
        self.notes = notes
