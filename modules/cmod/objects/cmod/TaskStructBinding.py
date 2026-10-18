"""
@module cmod.objects.cmod.TaskStructBinding

TaskStructBinding - one class per file (design section 7). FIRMWARE_GENERATION_MODULE_PLAN.md section 9 (fgm-3).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class TaskStructBinding(treeObject):
    """What it is: one piece of shared data a Task reads or writes - a C global or a field of the class struct the frames carry (for example LightState.boot_session). It is derived from the atoms' own
    resources and the graph's field edges. `isr_shared` is true when a step that runs in an interrupt AND a step that runs in the main loop (or another task) touch the SAME piece: that is where the
    generator must later wrap the loop-side access so an interrupt cannot cut it in half (ATOMIC_BLOCK, fgm-5); `atomic_today` says whether the atom already does. Nothing here changes any code.
    Related concepts: `TaskDefinition`, `CFunctionAtom` (its resources), `CGraphEdge` (kind field).
    """

    plain_words = ('A struct binding says which shared piece of data a task touches, and whether an interrupt and the main loop both touch it - '
                   'that is the one place the generated code will later need protection.')

    @treeObjectInit
    def __init__(self, name: str = '', plan: str = '', task: str = '', target: str = '', kind: str = 'global', access: str = '', steps_json: str = '[]',
                 isr_shared: bool = False, isr_vectors: str = '', atomic_today: str = '', basis: str = '', notes: str = '', manager=None):
        self.name = name                # '<plan>:<task>:<target>'
        self.plan = plan
        self.task = task
        self.target = target            # 'g_toggle_pending' | 'LightState.boot_session' | 'state (LightState_t, whole struct)'
        self.kind = kind                # global | struct-field | struct
        self.access = access            # r | w | rw (the union over the task's steps)
        self.steps_json = steps_json    # [step instance names that touch it]
        self.isr_shared = isr_shared    # an interrupt step and a loop/task step touch it
        self.isr_vectors = isr_vectors  # the interrupt(s), comma separated
        self.atomic_today = atomic_today   # 'yes: inside ATOMIC_BLOCK in <atom>' | 'no' | 'not applicable'
        self.basis = basis              # where it was read from (the atom's resource row / the field edge)
        self.notes = notes
