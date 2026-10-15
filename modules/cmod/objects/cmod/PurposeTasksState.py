"""
@module cmod.objects.cmod.PurposeTasksState

PurposeTasksState — one class per file (design §7). Node kind 8 of 11 of a Purpose drawing (FIRMWARE_GENERATION_MODULE_PLAN.md §8).
"""
from objectTreeDecorators import treeObject, treeObjectInit
from cmod.custom.purpose_palette import palette


class PurposeTasksState(treeObject):
    """What it is: the `purpose-tasks` NODE KIND, category **Purpose** — The tasks that do the work. Click one to open the firmware drawing at that task.
    Authored: it reads and writes the Purpose row's own fields through `cmod.custom.purpose_nocode`; the drawing is never a second copy.
    Related concepts: `CapabilityDefinition` (the Purpose row), `cmod.custom.purpose_nocode` (render / validate / write_back).
    """

    plain_words = 'The tasks that do the work. Click one to open the firmware drawing at that task.'

    statePalette = palette('purpose-tasks', 'Done by',
                           plain_words,
                           [('tasks', 'Tasks'),
                 ('count', 'How many')],
                           derived=False, multiple=False)

    @treeObjectInit
    def __init__(self, name: str = '', tasks: str = '', count: str = '', manager=None):
        self.name = name
        self.tasks = tasks
        self.count = count
