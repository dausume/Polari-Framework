"""
@module microalgae.objects.reactor.AlgaeReactorDefinition

Row class AlgaeReactorDefinition of the microalgae module — one class per file (design §7), split
from reactor_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

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
