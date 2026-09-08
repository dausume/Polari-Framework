"""
@module composition.objects.functional.ConstructionVariantDefinition

Row class ConstructionVariantDefinition of the composition module — one class per file (design §7), split
from functional_basis.py (sap-2c). The class docstring below is the explanation.
"""
from composition.custom.fill_models import FILL_CLASSES, fill_for_class
from objectTreeDecorators import treeObject, treeObjectInit

class ConstructionVariantDefinition(treeObject):
    """One way of building a functional part — an MBOM realization,
    first-class alternative of the SAME functional part."""

    @treeObjectInit
    def __init__(self, name='', display_name='', functional_ref='',
                 node_ref='', routing_ref='', fill_factor_class='n/a',
                 selection_rationale='', is_prior=True,
                 provenance_id='', notes='', manager=None):
        self.name = name
        self.display_name = display_name
        self.functional_ref = functional_ref
        #: The CompositionNode this variant builds — level derives
        #: from ITS interface rows.
        self.node_ref = node_ref
        #: RoutingDefinition (arch-4); process step COUNT derives
        #: from the routing, it is not stamped here.
        self.routing_ref = routing_ref
        #: Fill is a property of the CONSTRUCTION (mag-26 req 2).
        self.fill_factor_class = (
            fill_factor_class if fill_factor_class in FILL_CLASSES
            else 'n/a')
        #: What this variant is FOR — inspectability, packing,
        #: step count, repairability. The choice must be knowing.
        self.selection_rationale = selection_rationale
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
