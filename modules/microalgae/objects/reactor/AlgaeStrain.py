"""
@module microalgae.objects.reactor.AlgaeStrain

Row class AlgaeStrain of the microalgae module — one class per file (design §7), split
from reactor_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class AlgaeStrain(treeObject):
    """One microalga strain + its growth + stoichiometry priors."""

    @treeObjectInit
    def __init__(
        self,
        # kebab-case unique key ('chlorella-vulgaris').
        name: str = '',
        display_name: str = '',
        common_name: str = '',
        # WATER_TYPES entry.
        water_type: str = 'fresh',
        # Max specific growth rate (per day) — µmax, nutrient/light
        # replete.
        max_growth_rate_per_day: float = 0.9,
        # Dry-biomass carbon fraction (~0.5) — the CO2-fixation basis.
        carbon_fraction: float = 0.5,
        # Nutrient content of dry biomass (mg per g dry) — the DRAW
        # stoichiometry (how much N/P the algae pull to grow).
        n_per_biomass_mg_g: float = 80.0,
        p_per_biomass_mg_g: float = 12.0,
        # Carrying density (g dry / L) at which self-shading stalls
        # growth — the overgrowth/crash ceiling.
        optimal_density_g_l: float = 3.0,
        # Relative light response (informational; light enters via the
        # reactor's light_intensity).
        light_saturation: float = 1.0,
        edible: bool = True,
        # ALGAE_PRODUCTS entry.
        product: str = 'food-protein',
        # If edible: DietaryNutrients per 100 g dry (JSON) — spirulina/
        # chlorella are high protein.
        harvest_nutrients_json: str = '{}',
        is_prior: bool = True,
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.common_name = common_name
        self.water_type = water_type
        self.max_growth_rate_per_day = max_growth_rate_per_day
        self.carbon_fraction = carbon_fraction
        self.n_per_biomass_mg_g = n_per_biomass_mg_g
        self.p_per_biomass_mg_g = p_per_biomass_mg_g
        self.optimal_density_g_l = optimal_density_g_l
        self.light_saturation = light_saturation
        self.edible = edible
        self.product = product
        self.harvest_nutrients_json = harvest_nutrients_json
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
