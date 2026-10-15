"""
@module cmod.objects.cmod.PurposeParticipantState

PurposeParticipantState — one class per file (design §7). Node kind 3 of 11 of a Purpose drawing (FIRMWARE_GENERATION_MODULE_PLAN.md §8).
"""
from objectTreeDecorators import treeObject, treeObjectInit
from cmod.custom.purpose_palette import palette


class PurposeParticipantState(treeObject):
    """What it is: the `purpose-participant` NODE KIND, category **Purpose** — One thing that takes part and the role it plays: the board (its package and USB-interface variant may still be pending), the chip on it, the computer it is plugged into, or Polari.
    Authored: it reads and writes the Purpose row's own fields through `cmod.custom.purpose_nocode`; the drawing is never a second copy.
    Related concepts: `CapabilityDefinition` (the Purpose row), `cmod.custom.purpose_nocode` (render / validate / write_back).
    """

    plain_words = 'One thing that takes part and the role it plays: the board (its package and USB-interface variant may still be pending), the chip on it, the computer it is plugged into, or Polari.'

    statePalette = palette('purpose-participant', 'Participant',
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
