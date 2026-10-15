"""
@module cmod.objects.cmod.PurposeDependsState

PurposeDependsState — one class per file (design §7). Node kind 2 of 11 of a Purpose drawing (FIRMWARE_GENERATION_MODULE_PLAN.md §8).
"""
from objectTreeDecorators import treeObject, treeObjectInit
from cmod.custom.purpose_palette import palette


class PurposeDependsState(treeObject):
    """What it is: the `purpose-depends` NODE KIND, category **Purpose** — The Purpose that must hold first. Every firmware Purpose depends on initialization, the board being set up and ready.
    Authored: it reads and writes the Purpose row's own fields through `cmod.custom.purpose_nocode`; the drawing is never a second copy.
    Related concepts: `CapabilityDefinition` (the Purpose row), `cmod.custom.purpose_nocode` (render / validate / write_back).
    """

    plain_words = 'The Purpose that must hold first. Every firmware Purpose depends on initialization, the board being set up and ready.'

    statePalette = palette('purpose-depends', 'Depends on',
                           plain_words,
                           [('depends_on', 'Must hold first')],
                           derived=False, multiple=False)

    @treeObjectInit
    def __init__(self, name: str = '', depends_on: str = '', manager=None):
        self.name = name
        self.depends_on = depends_on
