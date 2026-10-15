"""
@module cmod.objects.cmod.PurposeObservedState

PurposeObservedState — one class per file (design §7). Node kind 11 of 11 of a Purpose drawing (FIRMWARE_GENERATION_MODULE_PLAN.md §8).
"""
from objectTreeDecorators import treeObject, treeObjectInit
from cmod.custom.purpose_palette import palette


class PurposeObservedState(treeObject):
    """What it is: the `purpose-observed` NODE KIND, category **Purpose** — Worked out from what each deployed board has reported: whether it is doing what the Purpose says, and how healthy it is. The weakest device is shown. Cannot be edited here.
    Worked out, never stored: it reads and writes the Purpose row's own fields through `cmod.custom.purpose_nocode`; the drawing is never a second copy.
    Related concepts: `CapabilityDefinition` (the Purpose row), `cmod.custom.purpose_nocode` (render / validate / write_back).
    """

    plain_words = 'Worked out from what each deployed board has reported: whether it is doing what the Purpose says, and how healthy it is. The weakest device is shown. Cannot be edited here.'

    statePalette = palette('purpose-observed', 'On each device',
                           plain_words,
                           [('summary', 'Weakest device'),
                 ('devices', 'Devices')],
                           derived=True, multiple=False)

    @treeObjectInit
    def __init__(self, name: str = '', summary: str = '', devices: str = '', manager=None):
        self.name = name
        self.summary = summary
        self.devices = devices
