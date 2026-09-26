"""
@module computelod.objects.computelod.ComputeMapping

Row class ComputeMapping of the computelod module — one class per file. The class docstring is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit


class ComputeMapping(treeObject):
    """DOWNWARD: how is this implemented (plan §5, §F2). One-to-one, one-to-many, many-to-one, approximate, alternative, unresolved or partial; adjacent rungs are not required (a tensor operation may map straight to an FPGA kernel). Two statuses: what the mapping is, and what evidence it has."""

    plain_words = ('A mapping between rungs says how something at one level is realised at the next level down (or summarised '
                   'at the next level up), and carries the evidence for that link and how far it has been checked.')

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        description: str = '',
        kind: str = 'one-to-one',
        source_rung: str = '',
        source_ref: str = '',
        target_rung: str = '',
        target_ref: str = '',
        validity_json: str = '{}',
        loss_note: str = '',
        uncertainty_json: str = '{}',
        mapping_status: str = 'proposed',
        evidence_level: str = 'none',
        evidence_ref: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.description = description
        self.kind = kind  # one-to-one | one-to-many | many-to-one | approximate | alternative | unresolved | partial
        self.source_rung = source_rung
        self.source_ref = source_ref  # the row at the source rung
        self.target_rung = target_rung
        self.target_ref = target_ref
        self.validity_json = validity_json
        self.loss_note = loss_note
        self.uncertainty_json = uncertainty_json
        self.mapping_status = mapping_status  # proposed | implemented | validated
        self.evidence_level = evidence_level  # none | analytical | simulated | measured
        self.evidence_ref = evidence_ref
        self.notes = notes
