"""
@module cmod.objects.cmod.MissionGoalState

MissionGoalState - one class per file (design section 7). Node kind 1 of 6 of a Hardware Mission drawing (MISSION_PROFILE_SOLVER_PLAN.md section 5).
"""
from objectTreeDecorators import treeObject, treeObjectInit
from cmod.custom.mission_palette import palette


class MissionGoalState(treeObject):
    """What it is: the `mission-goal` NODE KIND, category **Mission** - The Mission itself: its name, the one sentence that says what it is for, and where it is in its life (draft, enabled, suspended or retired). Edit the goal or the life stage here and the Mission changes.
    Authored: it reads and writes the Hardware Mission row's own fields through `cmod.custom.mission_nocode`; the drawing is never a second copy.
    Related concepts: `HardwareMission` (the Mission row), `CapabilityDefinition` (a Purpose), `cmod.custom.mission_nocode` (render / validate / write_back).
    """

    plain_words = 'The Mission itself: its name, the one sentence that says what it is for, and where it is in its life (draft, enabled, suspended or retired). Edit the goal or the life stage here and the Mission changes.'

    statePalette = palette('mission-goal', 'Mission',
                           plain_words,
                           [('title', 'Name'),
                 ('goal', 'What it is for'),
                 ('lifecycle', 'Life stage')],
                           derived=False, multiple=False)

    @treeObjectInit
    def __init__(self, name: str = '', title: str = '', goal: str = '', lifecycle: str = '', manager=None):
        self.name = name
        self.title = title
        self.goal = goal
        self.lifecycle = lifecycle
