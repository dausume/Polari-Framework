"""
@module composition.objects.routing.RoutingOperation

Row class RoutingOperation of the composition module — one class per file (design §7), split
from routing_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit
from composition.objects.routing._shared import OPERATION_KINDS, PURPOSE_CLASSES

class RoutingOperation(treeObject):
    """One step. kind='promote' carries the full promotion record."""

    @treeObjectInit
    def __init__(self, name='', display_name='', routing_ref='',
                 sequence=0, kind='shape', summary='',
                 capability_rung_ref='', purpose_class='physics',
                 consumes_interface_refs_json='[]',
                 fused_interface_refs_json='[]', emits_node_ref='',
                 modes_deleted_refs_json='[]',
                 modes_introduced_refs_json='[]',
                 reversibility_spent='',
                 dfa_justification_json='{}', qualifying_act='',
                 is_prior=True, provenance_id='', notes='',
                 manager=None):
        self.name = name
        self.display_name = display_name
        self.routing_ref = routing_ref
        self.sequence = sequence
        self.kind = kind if kind in OPERATION_KINDS else 'shape'
        self.summary = summary
        #: Techtree ladder rung this op ASSUMES (e.g. 'W2'). ''
        #: makes the whole routing inadmissible — loudly.
        self.capability_rung_ref = capability_rung_ref
        self.purpose_class = (purpose_class
                              if purpose_class in PURPOSE_CLASSES
                              else 'physics')
        # ---- promote-kind record (empty on other kinds) ----
        #: Source-assembly separable interfaces this promotion
        #: DELETES ([] when promoting an in-process winding that
        #: never existed as a separate assembly row).
        self.consumes_interface_refs_json = \
            consumes_interface_refs_json
        #: THE NAMED INTERFACE SET the promotion fuses — must be
        #: bound (designed_separable=False) rows on the emitted
        #: node. Promotion attaches HERE, never to a whole assembly.
        self.fused_interface_refs_json = fused_interface_refs_json
        #: The NEW identity (CompositionNode) this promotion mints.
        self.emits_node_ref = emits_node_ref
        self.modes_deleted_refs_json = modes_deleted_refs_json
        self.modes_introduced_refs_json = modes_introduced_refs_json
        #: What repairability the promotion spends, in words a
        #: lifecycle-cost model can act on.
        self.reversibility_spent = reversibility_spent
        #: {interface: {moves_relative, different_material,
        #:  separable_for_service, why}} — the Boothroyd-Dewhurst
        #: answers, per fused interface. The gate.
        self.dfa_justification_json = dfa_justification_json
        #: The named experiment that earns the promoted part its
        #: realization (never a relabelled row).
        self.qualifying_act = qualifying_act
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
