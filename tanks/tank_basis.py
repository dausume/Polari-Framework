"""
@cross-cutting
@module tanks.tank_basis
@tags @xc:bindings

Freshwater + saltwater TANK ecosystem models (tank-1) — the alternate
nutrient source from Dustin's food-forest specs. Own module + own data,
framework-core only. Models the modular 30-gallon interconnected tank
system as objects, so the ecosystem's nutrient CYCLING and harvestable
YIELD can be simulated (tank_analysis) — especially the iodine / sodium
/ chloride the hydroponic garden CANNOT supply (closing the nut-5 gap).

Three treeObjects (auto-CRUDE + persisted — object-coherence):

  TankDefinition        one vessel: volume, water type, ecological role,
                        room-temperature target.
  AquacultureSpecies    one organism in the roster — its ecological
                        ROLE(s) (nutrient regulator, filter feeder,
                        detritus eater, glass cleaner, nutrient
                        replenisher, oxygenator), whether it is edible /
                        wax-use, its per-individual daily N/P water flux
                        (+ adds, − removes), and its harvestable
                        biomass + the DietaryNutrients that biomass
                        yields (seaweed → iodine/sodium/chloride).
  TankSystemDefinition  an interconnected set of tanks + the species
                        stock → one runnable, rankable ecosystem
                        (mirrors PotSystemDefinition).

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - tanks.tank_analysis (nutrient balance, harvest yield, regulation)
@see /SALTWATER_FOOD_FOREST_SPEC.md, /HOUSEHOLD_NUTRITION_PLAN.md
"""

from objectTreeDecorators import treeObject, treeObjectInit

WATER_TYPES = ('fresh', 'salt')

#: Tank roles from the spec's phased build.
TANK_ROLES = ('general', 'macroalgae', 'filter-feeder', 'plankton',
              'open-swim', 'hiding-breeding', 'starch')

#: Ecological roles a species fills (drives balance + gap analysis).
SPECIES_ROLES = ('nutrient-regulator', 'filter-feeder', 'detritus-eater',
                 'glass-cleaner', 'nutrient-replenisher',
                 'substrate-oxygenator', 'macroalgae-food',
                 'starch-producer', 'protein-source')


class TankDefinition(treeObject):
    """One tank in the modular food-forest system."""

    @treeObjectInit
    def __init__(
        self,
        # kebab-case unique key ('saltwater-tank-1').
        name: str = '',
        display_name: str = '',
        # WATER_TYPES entry.
        water_type: str = 'salt',
        volume_gal: float = 30.0,
        # TANK_ROLES entry.
        role: str = 'general',
        # Room-temperature target (the whole design premise).
        temperature_c: float = 22.0,
        # Connector bore (in) — >=3in for sardine/anchovy schools.
        connector_diameter_in: float = 3.0,
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.water_type = water_type
        self.volume_gal = volume_gal
        self.role = role
        self.temperature_c = temperature_c
        self.connector_diameter_in = connector_diameter_in
        self.provenance_id = provenance_id
        self.notes = notes


class AquacultureSpecies(treeObject):
    """One organism in the tank roster + its ecosystem contribution."""

    @treeObjectInit
    def __init__(
        self,
        # kebab-case unique key ('sea-lettuce').
        name: str = '',
        display_name: str = '',
        common_name: str = '',
        water_type: str = 'salt',
        # JSON list of SPECIES_ROLES.
        roles_json: str = '[]',
        edible: bool = True,
        wax_use: bool = False,
        # Per-individual (or per-100g-biomass for algae) DAILY water
        # nutrient flux (mg/day): POSITIVE adds to the water (fish
        # waste, replenishers), NEGATIVE removes (algae uptake).
        daily_n_flux_mg: float = 0.0,
        daily_p_flux_mg: float = 0.0,
        # Per-day particulate/detritus removal (mg/day) for filter
        # feeders + detritus eaters (always >= 0; the self-cleaning term).
        daily_detritus_removal_mg: float = 0.0,
        # Harvestable edible biomass per individual per harvest (g).
        harvest_biomass_g: float = 0.0,
        # DietaryNutrients that biomass yields (JSON {nutrient: mg per
        # 100 g edible}) — seaweed carries iodine/sodium/chloride.
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
        self.roles_json = roles_json
        self.edible = edible
        self.wax_use = wax_use
        self.daily_n_flux_mg = daily_n_flux_mg
        self.daily_p_flux_mg = daily_p_flux_mg
        self.daily_detritus_removal_mg = daily_detritus_removal_mg
        self.harvest_biomass_g = harvest_biomass_g
        self.harvest_nutrients_json = harvest_nutrients_json
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes


class TankSystemDefinition(treeObject):
    """An interconnected tank system + its species stock."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        display_name: str = '',
        description: str = '',
        water_type: str = 'salt',
        # JSON list of TankDefinition names.
        tank_names_json: str = '[]',
        # JSON {species_name: count} — the stocked population.
        species_stock_json: str = '{}',
        # Persisted balance/yield snapshot (JSON) for scoring.
        ecosystem_result_json: str = '',
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.description = description
        self.water_type = water_type
        self.tank_names_json = tank_names_json
        self.species_stock_json = species_stock_json
        self.ecosystem_result_json = ecosystem_result_json
        self.provenance_id = provenance_id
        self.notes = notes
