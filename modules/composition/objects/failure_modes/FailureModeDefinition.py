"""
@module composition.objects.failure_modes.FailureModeDefinition

Row class FailureModeDefinition of the composition module — one class per file (design §7), split
from failure_modes_basis.py (sap-2c). The class docstring below is the explanation.
"""
from composition.custom.part_roles import DOMAINS  # noqa: F401 — same axis
from objectTreeDecorators import treeObject, treeObjectInit
from composition.objects.failure_modes._shared import LOCI

class FailureModeDefinition(treeObject):
    """One way a part or an interface dies."""

    @treeObjectInit
    def __init__(self, name='', display_name='', domain='mechanical',
                 locus='bulk', summary='', equation_ref='',
                 evidence_note='', is_prior=True, provenance_id='',
                 notes='', manager=None):
        self.name = name
        self.display_name = display_name
        self.domain = domain if domain in DOMAINS else 'mechanical'
        self.locus = locus if locus in LOCI else 'bulk'
        self.summary = summary
        #: EquationDefinition name; '' = NOT MODELLED, stated.
        self.equation_ref = equation_ref
        #: What observation would confirm/deny this mode here.
        self.evidence_note = evidence_note
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
