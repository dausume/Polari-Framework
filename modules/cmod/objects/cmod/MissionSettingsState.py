"""
@module cmod.objects.cmod.MissionSettingsState

MissionSettingsState - one class per file (design section 7). Node kind 2 of 6 of a Hardware Mission drawing (MISSION_PROFILE_SOLVER_PLAN.md section 5).
"""
from objectTreeDecorators import treeObject, treeObjectInit
from cmod.custom.mission_palette import palette


class MissionSettingsState(treeObject):
    """What it is: the `mission-settings` NODE KIND, category **Mission** - What the Mission aims at when a solution is searched for: the fewest resources that still meet every required Purpose, or the fastest pass through every Purpose with the resources available. Pick one here.
    Authored: it reads and writes the Hardware Mission row's own fields through `cmod.custom.mission_nocode`; the drawing is never a second copy.
    Related concepts: `HardwareMission` (the Mission row), `CapabilityDefinition` (a Purpose), `cmod.custom.mission_nocode` (render / validate / write_back).
    """

    plain_words = 'What the Mission aims at when a solution is searched for: the fewest resources that still meet every required Purpose, or the fastest pass through every Purpose with the resources available. Pick one here.'

    statePalette = palette('mission-settings', 'Settings',
                           plain_words,
                           [('objective', 'Aims at'),
                 ('notes', 'Notes')],
                           derived=False, multiple=False)

    @treeObjectInit
    def __init__(self, name: str = '', objective: str = '', notes: str = '', manager=None):
        self.name = name
        self.objective = objective
        self.notes = notes
