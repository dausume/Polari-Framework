"""
@module cmod.objects.cmod.StructNodeConfirmation

StructNodeConfirmation - one class per file (design section 7); bss-3 (AI-Notes/plans/BENCH_SOLUTION_SIM_PLAN.md section 2 "Confirmation").
"""
from objectTreeDecorators import treeObject, treeObjectInit


class StructNodeConfirmation(treeObject):
    """What it is: ONE CONFIRMATION that a node was reached - for one path and one build - BY whom: the twin (a `StructNodeRun` that met the
    requirements with every edge check passing), hardware (a record from a real board read in and judged against the same requirements) or a person
    (attested, in words). The user (2026-11-02): "we will need confirmations of things being completed." A confirmation is VOIDED, never deleted, when
    the build's sha256 changes or the node's definition changes; `voided_why` says which. A node confirmed by hardware is the strongest word the
    topology has.
    Related concepts: `StructNode`, `StructNodePath`, `StructNodeRun`, board `SimInstallConfirmation` (the same shape for a flash).
    """

    plain_words = ('A confirmation is one record that the bench really arrived at a situation - in the simulator, on a real board, or on a '
                   'person\'s word - and on which build; it is marked void, not erased, when the firmware changes.')

    @treeObjectInit
    def __init__(self, name: str = '', node: str = '', path: str = '', by: str = 'twin', run: str = '', hex_sha256: str = '', state: str = 'confirmed',
                 voided_why: str = '', who: str = '', words: str = '', at: str = '', manager=None):
        self.name = name                # '<node>#conf<n>'
        self.node = node                # a StructNode name
        self.path = path                # a StructNodePath name ('' for a person's attestation of the node as such)
        self.by = by                    # twin | hardware | person
        self.run = run                  # the StructNodeRun name when by == twin
        self.hex_sha256 = hex_sha256    # the build it holds for
        self.state = state              # confirmed | voided
        self.voided_why = voided_why
        self.who = who                  # the person or the record's source
        self.words = words
        self.at = at
