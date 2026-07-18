"""
@cross-cutting
@module microalgae.reactor_basis
@tags @xc:bindings

Microalgae photobioreactor models (algae-1) — the DE-CARBONIZATION
route for hydroponic + saltwater-food-forest systems. Own module + own
data, framework-core only (a lazy read of a coupled tank's balance is
the only cross-module touch, in reactor_analysis).

The core purpose (Dustin): hook a reactor to a parent system (aquaponics
pot loop / tank food forest / hydroponic reservoir) to FIX CO2 — but
SUSTAINABLY, so the reactor's nutrient draw never exceeds what the
parent can spare (else the parent depletes or the algae crash and the
whole system collapses). The nutrient_draw_cap knob is the model of the
spec's biochar passthrough limiter.

Two treeObjects (auto-CRUDE + persisted — object-coherence):

  AlgaeStrain             one microalga: growth rate, C/N/P
                          stoichiometry, carrying density, product, and
                          (if edible) its harvest nutrients.
  AlgaeReactorDefinition  one reactor: strain, volume, light, CO2
                          supply, the COUPLED parent system, and the
                          REGULATION knobs (draw cap, harvest cadence,
                          operating density) that keep it stable.

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - microalgae.reactor_analysis (growth, sustainability, decarbonization)
@see /SALTWATER_FOOD_FOREST_SPEC.md (biochar passthrough), tanks/
"""

from objectTreeDecorators import treeObject, treeObjectInit

WATER_TYPES = ('fresh', 'salt', 'both')
#: What the harvested biomass is for.
ALGAE_PRODUCTS = ('food-protein', 'starch', 'omega-oil', 'feed',
                  'biomass')
#: What kind of parent the reactor couples to (sets surplus resolution).
COUPLED_KINDS = ('aquaponics', 'tank', 'hydroponic')
CO2_SUPPLY_MODES = ('atmospheric', 'injected')


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


class AlgaeReactorDefinition(treeObject):
    """One photobioreactor coupled to a parent system for CO2 fixation."""

    @treeObjectInit
    def __init__(
        self,
        # kebab-case unique key ('chlorella-hydro-reactor').
        name: str = '',
        display_name: str = '',
        # The AlgaeStrain (by name).
        strain_name: str = '',
        water_type: str = 'fresh',
        volume_l: float = 20.0,
        # Relative light delivered (0-1 of the strain's saturation).
        light_intensity: float = 0.8,
        # CO2_SUPPLY_MODES entry + injection rate (g/day) when injected.
        co2_supply_mode: str = 'injected',
        co2_injection_g_per_day: float = 20.0,
        # The COUPLED parent system this draws nutrients from + fixes CO2
        # for: a name + COUPLED_KINDS entry.
        coupled_system_name: str = '',
        coupled_system_kind: str = 'hydroponic',
        # REGULATION KNOB (the biochar passthrough limiter): max N the
        # reactor may draw per day (mg). 0 = uncapped (risky — the
        # analysis flags over-draw). Keep <= the parent's surplus.
        nutrient_draw_cap_mg_n_per_day: float = 0.0,
        # For non-tank coupling (aquaponics/hydroponic) where the surplus
        # isn't computed live: an honest assumed daily N surplus (mg).
        assumed_parent_surplus_mg_n_per_day: float = 0.0,
        # Operating density as a fraction of optimal (0.5 = mid-log, the
        # productive sweet spot).
        target_density_fraction: float = 0.5,
        # Harvest cadence — remove harvest_fraction of biomass every
        # harvest_period_days (exports fixed carbon + holds density).
        harvest_fraction: float = 0.25,
        harvest_period_days: float = 7.0,
        # Persisted sustainability/decarbonization snapshot (JSON).
        decarbonization_result_json: str = '',
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.strain_name = strain_name
        self.water_type = water_type
        self.volume_l = volume_l
        self.light_intensity = light_intensity
        self.co2_supply_mode = co2_supply_mode
        self.co2_injection_g_per_day = co2_injection_g_per_day
        self.coupled_system_name = coupled_system_name
        self.coupled_system_kind = coupled_system_kind
        self.nutrient_draw_cap_mg_n_per_day = \
            nutrient_draw_cap_mg_n_per_day
        self.assumed_parent_surplus_mg_n_per_day = \
            assumed_parent_surplus_mg_n_per_day
        self.target_density_fraction = target_density_fraction
        self.harvest_fraction = harvest_fraction
        self.harvest_period_days = harvest_period_days
        self.decarbonization_result_json = decarbonization_result_json
        self.provenance_id = provenance_id
        self.notes = notes
