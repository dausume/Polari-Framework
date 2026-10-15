"""
@module cmod.objects.cmod.PurposeProofState

PurposeProofState — one class per file (design §7). Node kind 9 of 11 of a Purpose drawing (FIRMWARE_GENERATION_MODULE_PLAN.md §8).
"""
from objectTreeDecorators import treeObject, treeObjectInit
from cmod.custom.purpose_palette import palette


class PurposeProofState(treeObject):
    """What it is: the `purpose-proof` NODE KIND, category **Purpose** — The test that proves it and how far it has got. The test is chosen by a person; how far it has got is worked out from the test runs and cannot be edited here.
    Worked out, never stored: it reads and writes the Purpose row's own fields through `cmod.custom.purpose_nocode`; the drawing is never a second copy.
    Related concepts: `CapabilityDefinition` (the Purpose row), `cmod.custom.purpose_nocode` (render / validate / write_back).
    """

    plain_words = 'The test that proves it and how far it has got. The test is chosen by a person; how far it has got is worked out from the test runs and cannot be edited here.'

    statePalette = palette('purpose-proof', 'Proved by',
                           plain_words,
                           [('scenario', 'Test'),
                 ('status', 'How far proven'),
                 ('last_proof', 'Last run')],
                           derived=True, multiple=False)

    @treeObjectInit
    def __init__(self, name: str = '', scenario: str = '', status: str = '', last_proof: str = '', manager=None):
        self.name = name
        self.scenario = scenario
        self.status = status
        self.last_proof = last_proof
