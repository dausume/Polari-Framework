"""
@module mech.objects.assembly.MechPartInstance

Row class MechPartInstance of the mech module — one class per file (design §7); mxc-2.
The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit
from mech.objects.assembly._shared import INSTANCE_ROLES

class MechPartInstance(treeObject):
    """One placed occurrence of a catalogue variant inside an
    assembly (the KiCad reference analogue: B1, S1, T3)."""

    @treeObjectInit
    def __init__(self, name='', assembly_ref='', variant_ref='',
                 component_ref='', placement_json='{}',
                 material_option_ref='', quantity_role='body',
                 quantity=1, notes='', is_prior=True, provenance_id='',
                 manager=None):
        self.name = name
        self.assembly_ref = assembly_ref
        #: MechPartVariant by NAME (catalogue, mxc-1).
        self.variant_ref = variant_ref
        #: composition.PartComponentDefinition by NAME — the member the
        #: assembly's CompositionNode lists; material + shape live
        #: THERE (§9.1). '' = not yet spliced.
        self.component_ref = component_ref
        #: {'origin': [x, y, z] mm, 'rotation': [w, x, y, z]
        #: quaternion OR a 3x3 row-major matrix} in the assembly
        #: frame; placement_basis lives inside: 'given' | 'solved'.
        self.placement_json = placement_json
        #: MechMaterialOption by NAME; '' = the family's default
        #: preference (MechMaterialPreference), never a silent guess.
        self.material_option_ref = material_option_ref
        #: INSTANCE_ROLES: 'body' = a rigid body in the DOF graph;
        #: 'fastener' = hardware OF a joint (screw, T-nut), carried
        #: on that joint's fastener_refs_json and excluded from the
        #: Grübler count (a bolt is a constraint, not a body).
        self.quantity_role = (quantity_role
                              if quantity_role in INSTANCE_ROLES
                              else 'body')
        #: 1, or n for a set placed as one instance (12 identical bins).
        self.quantity = quantity
        self.notes = notes
        self.is_prior = is_prior
        self.provenance_id = provenance_id
