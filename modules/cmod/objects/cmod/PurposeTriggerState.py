"""
@module cmod.objects.cmod.PurposeTriggerState

PurposeTriggerState — one class per file (design §7). Node kind 4 of 11 of a Purpose drawing (FIRMWARE_GENERATION_MODULE_PLAN.md §8).
"""
from objectTreeDecorators import treeObject, treeObjectInit
from cmod.custom.purpose_palette import palette


class PurposeTriggerState(treeObject):
    """What it is: the `purpose-trigger` NODE KIND, category **Purpose** — What starts it: a button press, a command from Polari, a period of time, or the board starting up.
    Authored: it reads and writes the Purpose row's own fields through `cmod.custom.purpose_nocode`; the drawing is never a second copy.
    Related concepts: `CapabilityDefinition` (the Purpose row), `cmod.custom.purpose_nocode` (render / validate / write_back).
    """

    plain_words = 'What starts it: a button press, a command from Polari, a period of time, or the board starting up.'

    statePalette = palette('purpose-trigger', 'When',
                           plain_words,
                           [('kind', 'Kind'),
                 ('what', 'What starts it')],
                           derived=False, multiple=False)

    @treeObjectInit
    def __init__(self, name: str = '', kind: str = '', what: str = '', manager=None):
        self.name = name
        self.kind = kind
        self.what = what
