"""
@cross-cutting
@module aquaponics.plant_basis
@tags @xc:bindings

Plant profile PER PART (aqp-4). Dustin 2026-07-08: "the plant should
have a profile per part of the plant that analyses the permanent
structure of the plant and its composition so we can assess its
capture of carbon and other nutrients permanently through the lifetime
by volume per part … needed and min-max nutrient input and output per
part … including carbon dioxide and oxygen."

Two classes, auto-CRUDE + persisted:

  PlantDefinition — the whole plant: species, lifetime, growth stages,
                    mature size.
  PlantPart       — one part (root/stem/leaf/flower/fruit): its mature
                    volume + dry density, what FRACTION is permanent
                    structure, its FATE (harvested / senesces / soil-
                    incorporated / standing) — the honesty seam that
                    separates biomass CAPTURED from carbon PERMANENTLY
                    sequestered — its dry composition (carbon +
                    nutrients by mass), and its per-species net daily
                    flux at maturity with needed + MIN-MAX bands
                    (nutrients, and the atmospheric gases CO2 and O2).

The capture + budget MATH lives in plant_analysis.py.

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - aquaponics.plant_analysis / aquaponics.plant_api
@see /AQUAPONICS_MODULE_PLAN.md
"""

from objectTreeDecorators import treeObject, treeObjectInit

PLANT_PARTS = ('root', 'stem', 'leaf', 'flower', 'fruit', 'seed',
               'tuber')

#: What ultimately happens to a part's biomass — decides whether its
#: carbon is PERMANENTLY sequestered or cycles back to the atmosphere.
#: harvested/senesces = the carbon returns (eaten, decomposes);
#: soil-incorporated/standing-permanent = it stays locked.
PART_FATES = ('harvested', 'senesces', 'soil-incorporated',
              'standing-permanent')


class PlantDefinition(treeObject):
    """One plant's whole-organism profile."""

    @treeObjectInit
    def __init__(
        self,
        # kebab-case unique key ('sweet-basil').
        name: str = '',
        display_name: str = '',
        species: str = '',
        common_name: str = '',
        description: str = '',
        # Annual / perennial — informs default part fates.
        life_cycle: str = 'annual',
        # Full lifecycle length (days).
        lifetime_days: float = 120.0,
        # Growth stages (JSON list): [{"stage","startDay","endDay",
        # "growthFraction"}] — growthFraction is the share of mature
        # size reached by endDay (drives the lifetime integral).
        growth_stages_json: str = '[]',
        mature_height_mm: float = 400.0,
        mature_canopy_mm: float = 300.0,
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.species = species
        self.common_name = common_name
        self.description = description
        self.life_cycle = life_cycle
        self.lifetime_days = lifetime_days
        self.growth_stages_json = growth_stages_json
        self.mature_height_mm = mature_height_mm
        self.mature_canopy_mm = mature_canopy_mm
        self.provenance_id = provenance_id
        self.notes = notes


class PlantPart(treeObject):
    """One part of a plant, with its permanent structure + flux."""

    @treeObjectInit
    def __init__(
        self,
        # unique key ('sweet-basil-leaf').
        name: str = '',
        plant_name: str = '',
        # PLANT_PARTS entry.
        part: str = 'leaf',
        display_name: str = '',
        # Size + dry-matter at maturity.
        mature_volume_cm3: float = 100.0,
        dry_density_g_cm3: float = 0.3,
        dry_matter_fraction: float = 0.12,
        # Fraction of the DRY mass that is permanent structure
        # (lignin/cellulose/wood) rather than transient tissue.
        permanent_fraction: float = 0.3,
        # PART_FATES entry — the sequestration honesty knob.
        fate: str = 'senesces',
        # Dry composition (JSON {element: mass fraction}), e.g.
        # {"carbon":0.45,"nitrogen":0.015,"potassium":0.01,...}.
        composition_json: str = '{}',
        # Per-species net daily flux AT MATURITY (JSON):
        # {species: {"direction":"in"|"out","needed":mg/day,
        #            "min":mg/day,"max":mg/day}} — nutrients plus the
        # atmospheric gases 'co2' and 'o2'. min/max = the survival
        # band (below min = deficiency, above max = toxicity).
        flux_json: str = '{}',
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.plant_name = plant_name
        self.part = part
        self.display_name = display_name
        self.mature_volume_cm3 = mature_volume_cm3
        self.dry_density_g_cm3 = dry_density_g_cm3
        self.dry_matter_fraction = dry_matter_fraction
        self.permanent_fraction = permanent_fraction
        self.fate = fate
        self.composition_json = composition_json
        self.flux_json = flux_json
        self.provenance_id = provenance_id
        self.notes = notes
