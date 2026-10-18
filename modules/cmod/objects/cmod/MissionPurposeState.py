"""
@module cmod.objects.cmod.MissionPurposeState

MissionPurposeState - one class per file (design section 7). Node kind 3 of 6 of a Hardware Mission drawing (MISSION_PROFILE_SOLVER_PLAN.md section 5).
"""
from objectTreeDecorators import treeObject, treeObjectInit
from cmod.custom.mission_palette import palette


class MissionPurposeState(treeObject):
    """What it is: the `mission-purpose` NODE KIND, category **Mission** - One Purpose the Mission needs, and how much it matters: safety, required, important or desired. The Purpose's own status and whether it can run here are shown beside it, worked out and never typed in. Each Purpose has its own drawing, linked from here.
    Authored: it reads and writes the Hardware Mission row's own fields through `cmod.custom.mission_nocode`; the drawing is never a second copy.
    Related concepts: `HardwareMission` (the Mission row), `CapabilityDefinition` (a Purpose), `cmod.custom.mission_nocode` (render / validate / write_back).
    """

    plain_words = "One Purpose the Mission needs, and how much it matters: safety, required, important or desired. The Purpose's own status and whether it can run here are shown beside it, worked out and never typed in. Each Purpose has its own drawing, linked from here."

    statePalette = palette('mission-purpose', 'Purpose needed',
                           plain_words,
                           [('purpose_name', 'Which Purpose'),
                 ('importance', 'How much it matters'),
                 ('title', 'Name'),
                 ('status', 'How far it is proven'),
                 ('resolution', 'Can it run here'),
                 ('why', 'Why')],
                           derived=False, multiple=True)

    @treeObjectInit
    def __init__(self, name: str = '', purpose_name: str = '', importance: str = '', title: str = '', status: str = '', resolution: str = '', why: str = '', manager=None):
        self.name = name
        self.purpose_name = purpose_name
        self.importance = importance
        self.title = title
        self.status = status
        self.resolution = resolution
        self.why = why
