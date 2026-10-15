"""
@module cmod.objects.cmod.PurposeResolutionState

PurposeResolutionState — one class per file (design §7). Node kind 10 of 11 of a Purpose drawing (FIRMWARE_GENERATION_MODULE_PLAN.md §8).
"""
from objectTreeDecorators import treeObject, treeObjectInit
from cmod.custom.purpose_palette import palette


class PurposeResolutionState(treeObject):
    """What it is: the `purpose-resolution` NODE KIND, category **Purpose** — Worked out from the real hardware bindings: resolved when a valid binding exists for its tasks, unresolved when none does, blocked with the reason when a binding exists but is not valid. Never stored and cannot be edited.
    Worked out, never stored: it reads and writes the Purpose row's own fields through `cmod.custom.purpose_nocode`; the drawing is never a second copy.
    Related concepts: `CapabilityDefinition` (the Purpose row), `cmod.custom.purpose_nocode` (render / validate / write_back).
    """

    plain_words = 'Worked out from the real hardware bindings: resolved when a valid binding exists for its tasks, unresolved when none does, blocked with the reason when a binding exists but is not valid. Never stored and cannot be edited.'

    statePalette = palette('purpose-resolution', 'Can it run here?',
                           plain_words,
                           [('resolution', 'Can it run here'),
                 ('why', 'Why')],
                           derived=True, multiple=False)

    @treeObjectInit
    def __init__(self, name: str = '', resolution: str = '', why: str = '', manager=None):
        self.name = name
        self.resolution = resolution
        self.why = why
