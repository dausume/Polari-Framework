"""
@module aquaponics.objects.vermicompost.VermicompostProfile

Row class VermicompostProfile of the aquaponics module — one class per file (design §7), split
from vermicompost_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class VermicompostProfile(treeObject):
    """The soluble-nutrient RELEASE profile of mature castings.

    concentrations_json: {species_name: mg per kg of bed available to
    leach} — the POOL the bed can transfer into passing water. Distinct
    from aqp-2's NutrientProfile (a water solution); this is the source
    reservoir. Values are ABSTRACT PRIORS (literature range) until a
    bed is measured — priors_flagged carries that admission."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        display_name: str = '',
        description: str = '',
        # {species_name: mg soluble / kg bed} (JSON).
        concentrations_json: str = '{}',
        # First-order mineralization rate at 20 C (per day) — how fast
        # the bound pool becomes soluble. Abstract prior.
        k_min_per_day_20c: float = 0.03,
        # Q10 for the temperature response of k_min.
        q10: float = 2.0,
        # Mass-transfer coefficient (per hour of contact) — leaching
        # efficiency of the concentration gradient. Abstract prior.
        transfer_coeff_per_hr: float = 0.15,
        priors_flagged: bool = True,
        source: str = '',
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.description = description
        self.concentrations_json = concentrations_json
        self.k_min_per_day_20c = k_min_per_day_20c
        self.q10 = q10
        self.transfer_coeff_per_hr = transfer_coeff_per_hr
        self.priors_flagged = priors_flagged
        self.source = source
        self.provenance_id = provenance_id
        self.notes = notes
