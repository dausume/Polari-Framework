"""
@module cmod.objects.cmod.PurposeCriterionState

PurposeCriterionState — one class per file (design §7). Node kind 6 of 11 of a Purpose drawing (FIRMWARE_GENERATION_MODULE_PLAN.md §8).
"""
from objectTreeDecorators import treeObject, treeObjectInit
from cmod.custom.purpose_palette import palette


class PurposeCriterionState(treeObject):
    """What it is: the `purpose-criterion` NODE KIND, category **Purpose** — One measurable bound it must stay inside, such as the longest delay, the debounce time, how fresh a value must be, or how delivery is guaranteed.
    Authored: it reads and writes the Purpose row's own fields through `cmod.custom.purpose_nocode`; the drawing is never a second copy.
    Related concepts: `CapabilityDefinition` (the Purpose row), `cmod.custom.purpose_nocode` (render / validate / write_back).
    """

    plain_words = 'One measurable bound it must stay inside, such as the longest delay, the debounce time, how fresh a value must be, or how delivery is guaranteed.'

    statePalette = palette('purpose-criterion', 'Within',
                           plain_words,
                           [('key', 'Bound'),
                 ('value', 'Value'),
                 ('unit', 'Unit')],
                           derived=False, multiple=True)

    @treeObjectInit
    def __init__(self, name: str = '', key: str = '', value: str = '', unit: str = '', manager=None):
        self.name = name
        self.key = key
        self.value = value
        self.unit = unit
