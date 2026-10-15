"""
@module cmod.objects.cmod.PurposeOutcomeState

PurposeOutcomeState — one class per file (design §7). Node kind 5 of 11 of a Purpose drawing (FIRMWARE_GENERATION_MODULE_PLAN.md §8).
"""
from objectTreeDecorators import treeObject, treeObjectInit
from cmod.custom.purpose_palette import palette


class PurposeOutcomeState(treeObject):
    """What it is: the `purpose-outcome` NODE KIND, category **Purpose** — The result you can observe when it has worked: a state field that changes, or a physical output that follows.
    Authored: it reads and writes the Purpose row's own fields through `cmod.custom.purpose_nocode`; the drawing is never a second copy.
    Related concepts: `CapabilityDefinition` (the Purpose row), `cmod.custom.purpose_nocode` (render / validate / write_back).
    """

    plain_words = 'The result you can observe when it has worked: a state field that changes, or a physical output that follows.'

    statePalette = palette('purpose-outcome', 'Then',
                           plain_words,
                           [('what', 'What you will see')],
                           derived=False, multiple=False)

    @treeObjectInit
    def __init__(self, name: str = '', what: str = '', manager=None):
        self.name = name
        self.what = what
