"""
@module composition.objects.routing.RoutingDefinition

Row class RoutingDefinition of the composition module — one class per file (design §7), split
from routing_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class RoutingDefinition(treeObject):
    """The ordered process that builds one construction variant."""

    @treeObjectInit
    def __init__(self, name='', display_name='', variant_ref='',
                 per_unit='part', is_prior=True, provenance_id='',
                 notes='', manager=None):
        self.name = name
        self.display_name = display_name
        #: ConstructionVariantDefinition this routing builds.
        self.variant_ref = variant_ref
        #: What one pass of the routing produces ('part' | 'layer'
        #: — the layered stator runs its routing PER LAYER).
        self.per_unit = per_unit
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
