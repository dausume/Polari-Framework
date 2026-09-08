"""
@module magnetics.objects.magnet_block.JointMortarAssignment

Row class JointMortarAssignment of the magnetics module — one class per file (design §7), split
from magnet_block_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class JointMortarAssignment(treeObject):
    """The mortar grade of ONE joint (adjacent slot pair) — the
    selective-mortar design knob the solver prices. thickness
    priors ride the §2c tolerance ladder (T0 ~0.5-1 mm cast-as-is,
    T1 ~0.1-0.3 mm lapped) and are ESTIMATES until measured joints
    (calipers, QA dimensional check) replace them."""

    @treeObjectInit
    def __init__(self, name='', layout_name='', from_placement='',
                 to_placement='', mortar_ref='',
                 thickness_m=0.001, contact_area_m2=0.0,
                 thickness_is_estimate=True,
                 is_prior=True, provenance_id='', notes='',
                 manager=None):
        self.name = name
        self.layout_name = layout_name
        self.from_placement = from_placement
        self.to_placement = to_placement
        #: MagneticMaterialOption.name of the MORTAR (e.g.
        #: opt-solgel-ferrite = flux passes, opt-plain-solgel-mortar
        #: = flux fence).
        self.mortar_ref = mortar_ref
        self.thickness_m = thickness_m
        #: Face contact area; 0.0 = derive from the smaller block
        #: face along the adjacency axis (v1 brick math).
        self.contact_area_m2 = contact_area_m2
        self.thickness_is_estimate = thickness_is_estimate
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
