"""
@module aquaponics.objects.plant.PlantPart

Row class PlantPart of the aquaponics module — one class per file (design §7), split
from plant_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

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
