"""
@module cmod.objects.cmod.PurposeObservesState

PurposeObservesState — one class per file (design §7). Node kind 7 of 11 of a Purpose drawing (FIRMWARE_GENERATION_MODULE_PLAN.md §8).
"""
from objectTreeDecorators import treeObject, treeObjectInit
from cmod.custom.purpose_palette import palette


class PurposeObservesState(treeObject):
    """What it is: the `purpose-observes` NODE KIND, category **Purpose** — Something Polari has to be able to observe for the Purpose to count as done: a state field, an event, or the command number a command is confirmed by.
    Authored: it reads and writes the Purpose row's own fields through `cmod.custom.purpose_nocode`; the drawing is never a second copy.
    Related concepts: `CapabilityDefinition` (the Purpose row), `cmod.custom.purpose_nocode` (render / validate / write_back).
    """

    plain_words = 'Something Polari has to be able to observe for the Purpose to count as done: a state field, an event, or the command number a command is confirmed by.'

    statePalette = palette('purpose-observes', 'Polari must see',
                           plain_words,
                           [('item', 'What Polari sees'),
                 ('kind', 'Kind'),
                 ('delivery', 'How it arrives')],
                           derived=False, multiple=True)

    @treeObjectInit
    def __init__(self, name: str = '', item: str = '', kind: str = '', delivery: str = '', manager=None):
        self.name = name
        self.item = item
        self.kind = kind
        self.delivery = delivery
