"""
@module aquaponics.objects.pot.PotDefinition

Row class PotDefinition of the aquaponics module — one class per file (design §7), split
from pot_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class PotDefinition(treeObject):
    """One parametric self-watering pot."""

    @treeObjectInit
    def __init__(
        self,
        # kebab-case unique key ('demo-herb-pot').
        name: str = '',
        display_name: str = '',
        description: str = '',
        # POT_SHAPES entry.
        shape: str = 'cylinder',
        # Outer diameters (mm). Equal → cylinder; differ → tapered
        # frustum (top vs base).
        outer_top_diameter_mm: float = 200.0,
        outer_base_diameter_mm: float = 200.0,
        # Overall vessel height (mm), outer base to rim.
        height_mm: float = 250.0,
        # Wall + base thickness (mm) — the waterproof shell.
        wall_thickness_mm: float = 8.0,
        base_thickness_mm: float = 12.0,
        # The material this pot is made of — a MaterialsScienceMaterial
        # (a waterproof ceramic/geopolymer). '' = unassigned.
        material_name: str = '',
        # Optional bottom reservoir height (mm) — the self-watering
        # water store below the soil. 0 = the output holes alone set
        # the maintained level (aqp-3 hydraulics uses this).
        reservoir_height_mm: float = 0.0,
        # Soil fill height (mm), measured from the INTERIOR floor (the
        # top of the base slab) — an explicit knob, never a hidden
        # fraction (aquaponics-pot-shape phase 4). Clamped to the
        # usable interior height (height_mm - base_thickness_mm) by
        # mathshapes.custom.soil_modify.soil_shape_from_definition if it
        # would otherwise poke above the rim.
        soil_fill_height_mm: float = 180.0,
        # Per-layer transparency toggles (aquaponics-pot-shape phase 5)
        # — explicit knobs, never a hidden "make everything see-through"
        # switch. Each swaps that layer's render style between the
        # opaque seed material and its '-transparent' variant
        # (simSpace3D/seed_data.py) the next time the pot re-derives.
        # Default TRUE (2026-07-15, Dustin: "the pots and soil only
        # mostly transparent so we can see the water flow") — a fresh
        # pot is see-through by default now; flip to False for the
        # occasional fully-opaque render.
        wall_transparent: bool = True,
        soil_transparent: bool = True,
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.description = description
        self.shape = shape
        self.outer_top_diameter_mm = outer_top_diameter_mm
        self.outer_base_diameter_mm = outer_base_diameter_mm
        self.height_mm = height_mm
        self.wall_thickness_mm = wall_thickness_mm
        self.base_thickness_mm = base_thickness_mm
        self.material_name = material_name
        self.reservoir_height_mm = reservoir_height_mm
        self.soil_fill_height_mm = soil_fill_height_mm
        self.wall_transparent = wall_transparent
        self.soil_transparent = soil_transparent
        self.notes = notes
