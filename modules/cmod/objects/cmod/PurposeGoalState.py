"""
@module cmod.objects.cmod.PurposeGoalState

PurposeGoalState — one class per file (design §7). Node kind 1 of 11 of a Purpose drawing (FIRMWARE_GENERATION_MODULE_PLAN.md §8).
"""
from objectTreeDecorators import treeObject, treeObjectInit
from cmod.custom.purpose_palette import palette


class PurposeGoalState(treeObject):
    """What it is: the `purpose-goal` NODE KIND, category **Purpose** — The Purpose itself: its name, the one sentence that says why this is in the firmware, and where it is in its life (draft, enabled, suspended or retired). Edit the goal or the life stage here and the Purpose changes.
    Authored: it reads and writes the Purpose row's own fields through `cmod.custom.purpose_nocode`; the drawing is never a second copy.
    Related concepts: `CapabilityDefinition` (the Purpose row), `cmod.custom.purpose_nocode` (render / validate / write_back).
    """

    plain_words = 'The Purpose itself: its name, the one sentence that says why this is in the firmware, and where it is in its life (draft, enabled, suspended or retired). Edit the goal or the life stage here and the Purpose changes.'

    statePalette = palette('purpose-goal', 'Purpose',
                           plain_words,
                           [('title', 'Name'),
                 ('goal', 'Why this is in the firmware'),
                 ('lifecycle', 'Life stage')],
                           derived=False, multiple=False)

    @treeObjectInit
    def __init__(self, name: str = '', title: str = '', goal: str = '', lifecycle: str = '', manager=None):
        self.name = name
        self.title = title
        self.goal = goal
        self.lifecycle = lifecycle
