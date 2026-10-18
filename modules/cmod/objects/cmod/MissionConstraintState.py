"""
@module cmod.objects.cmod.MissionConstraintState

MissionConstraintState - one class per file (design section 7). Node kind 5 of 6 of a Hardware Mission drawing (MISSION_PROFILE_SOLVER_PLAN.md section 5).
"""
from objectTreeDecorators import treeObject, treeObjectInit
from cmod.custom.mission_palette import palette


class MissionConstraintState(treeObject):
    """What it is: the `mission-constraint` NODE KIND, category **Mission** - The limits on any solution: how far the hardware has got (from a breadboard to a custom chip) and, if you want, the only boards that may be used. Leave a limit empty to leave it open.
    Authored: it reads and writes the Hardware Mission row's own fields through `cmod.custom.mission_nocode`; the drawing is never a second copy.
    Related concepts: `HardwareMission` (the Mission row), `CapabilityDefinition` (a Purpose), `cmod.custom.mission_nocode` (render / validate / write_back).
    """

    plain_words = 'The limits on any solution: how far the hardware has got (from a breadboard to a custom chip) and, if you want, the only boards that may be used. Leave a limit empty to leave it open.'

    statePalette = palette('mission-constraint', 'Limits',
                           plain_words,
                           [('stage', 'Stage of the hardware'),
                 ('allowed_boards', 'Only these boards')],
                           derived=False, multiple=False)

    @treeObjectInit
    def __init__(self, name: str = '', stage: str = '', allowed_boards: str = '', manager=None):
        self.name = name
        self.stage = stage
        self.allowed_boards = allowed_boards
