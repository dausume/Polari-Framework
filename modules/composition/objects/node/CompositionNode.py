"""
@module composition.objects.node.CompositionNode

Row class CompositionNode of the composition module — one class per file (design §7), split
from node_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit
from composition.objects.node._shared import DECLARED_LEVELS

class CompositionNode(treeObject):
    """One node of the composition tree: members + (via back-ref)
    the interfaces it owns. Level is DERIVED by derive_level()."""

    @treeObjectInit
    def __init__(self, name='', display_name='', declared_level='',
                 members_json='[]', functional_ref='',
                 genealogy_ref='', bulk_failure_mode_refs_json='[]',
                 is_prior=True, provenance_id='', notes='',
                 manager=None):
        self.name = name
        self.display_name = display_name
        self.declared_level = (declared_level
                               if declared_level in DECLARED_LEVELS
                               else '')
        #: [{'ref': name, 'kind': 'component'|'node',
        #:   'quantity': n}] — components are
        #: PartComponentDefinition rows, nodes nest.
        self.members_json = members_json
        #: FunctionalPartDefinition this node realizes (arch-3).
        self.functional_ref = functional_ref
        #: The node this identity was PROMOTED from (arch-4) — a
        #: promoted part is a NEW identity with its history named.
        self.genealogy_ref = genealogy_ref
        #: BULK-locus FailureModeDefinition names carried by this
        #: body (what a promotion bought it with).
        self.bulk_failure_mode_refs_json = bulk_failure_mode_refs_json
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
