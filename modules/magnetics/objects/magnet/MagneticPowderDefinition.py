"""
@module magnetics.objects.magnet.MagneticPowderDefinition

Row class MagneticPowderDefinition of the magnetics module — one class per file (design §7), split
from magnet_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class MagneticPowderDefinition(treeObject):
    """One powder's intrinsic property set (mag-2t). Real powders
    cite; THEORETICAL powders are watermarked hypotheses — open in
    SIMULATION everywhere, REFUSED in cost/business (no citation can
    exist; the refusal names the sourcing hunt)."""

    @treeObjectInit
    def __init__(self, name='', display_name='', is_theoretical=False,
                 item_ref='', mu_i=None, b_sat_t=None, h_c_ka_m=None,
                 b_r_t=None, density_kg_m3=None, particle_size_um=None,
                 sigma_s_m=None, property_provenance='literature-est',
                 is_prior=True, provenance_id='', notes='',
                 manager=None):
        self.name = name
        self.display_name = display_name
        self.is_theoretical = is_theoretical
        #: supplychain item vocabulary ('' for theoretical powders —
        #: nothing to cite BY CONSTRUCTION).
        self.item_ref = item_ref
        #: Intrinsic relative permeability (linear small-signal).
        self.mu_i = mu_i
        self.b_sat_t = b_sat_t
        self.h_c_ka_m = h_c_ka_m
        self.b_r_t = b_r_t
        self.density_kg_m3 = density_kg_m3
        self.particle_size_um = particle_size_um
        self.sigma_s_m = sigma_s_m
        #: One tag for the numeric set ('theoretical' for designed
        #: powders; per-value nuance lives on the catalog option).
        self.property_provenance = property_provenance
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
