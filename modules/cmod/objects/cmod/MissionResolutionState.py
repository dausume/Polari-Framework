"""
@module cmod.objects.cmod.MissionResolutionState

MissionResolutionState - one class per file (design section 7). Node kind 6 of 6 of a Hardware Mission drawing (MISSION_PROFILE_SOLVER_PLAN.md section 5).
"""
from objectTreeDecorators import treeObject, treeObjectInit
from cmod.custom.mission_palette import palette


class MissionResolutionState(treeObject):
    """What it is: the `mission-resolution` NODE KIND, category **Mission** - Worked out from the Purposes the Mission needs: resolved when every required and safety Purpose can run on real bound hardware, unresolved (naming which) when one cannot, unbound when the Mission names no Purpose. Never stored and cannot be edited.
    Worked out, never stored: it reads and writes the Hardware Mission row's own fields through `cmod.custom.mission_nocode`; the drawing is never a second copy.
    Related concepts: `HardwareMission` (the Mission row), `CapabilityDefinition` (a Purpose), `cmod.custom.mission_nocode` (render / validate / write_back).
    """

    plain_words = 'Worked out from the Purposes the Mission needs: resolved when every required and safety Purpose can run on real bound hardware, unresolved (naming which) when one cannot, unbound when the Mission names no Purpose. Never stored and cannot be edited.'

    statePalette = palette('mission-resolution', 'Can it be done here?',
                           plain_words,
                           [('resolution', 'Can it be done here'),
                 ('why', 'Why'),
                 ('estimates', 'Cycle time and resources')],
                           derived=True, multiple=False)

    @treeObjectInit
    def __init__(self, name: str = '', resolution: str = '', why: str = '', estimates: str = '', manager=None):
        self.name = name
        self.resolution = resolution
        self.why = why
        self.estimates = estimates
