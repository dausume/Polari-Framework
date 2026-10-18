"""
@module cmod.objects.cmod.MissionParticipantState

MissionParticipantState - one class per file (design section 7). Node kind 4 of 6 of a Hardware Mission drawing (MISSION_PROFILE_SOLVER_PLAN.md section 5).
"""
from objectTreeDecorators import treeObject, treeObjectInit
from cmod.custom.mission_palette import palette


class MissionParticipantState(treeObject):
    """What it is: the `mission-participant` NODE KIND, category **Mission** - One thing that takes part and the role it plays: a piece of hardware (the board, the chip), a piece of software (the host bridge, Polari) or a person (the one pressing the button). The board's package and USB-interface variant may still be pending.
    Authored: it reads and writes the Hardware Mission row's own fields through `cmod.custom.mission_nocode`; the drawing is never a second copy.
    Related concepts: `HardwareMission` (the Mission row), `CapabilityDefinition` (a Purpose), `cmod.custom.mission_nocode` (render / validate / write_back).
    """

    plain_words = "One thing that takes part and the role it plays: a piece of hardware (the board, the chip), a piece of software (the host bridge, Polari) or a person (the one pressing the button). The board's package and USB-interface variant may still be pending."

    statePalette = palette('mission-participant', 'Participant',
                           plain_words,
                           [('role', 'Role'),
                 ('kind', 'Kind'),
                 ('ref', 'Which one'),
                 ('variant', 'Variant')],
                           derived=False, multiple=True)

    @treeObjectInit
    def __init__(self, name: str = '', role: str = '', kind: str = '', ref: str = '', variant: str = '', manager=None):
        self.name = name
        self.role = role
        self.kind = kind
        self.ref = ref
        self.variant = variant
