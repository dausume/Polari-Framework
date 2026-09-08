"""
@module aquaponics.objects.plant_growth_normalized.PotPlanting

Row class PotPlanting of the aquaponics module — one class per file (design §7), split
from plant_growth_normalized_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class PotPlanting(treeObject):
    """ONE specific plant, in ONE specific pot, tracked over time — the
    instance-level state nothing in aqp-4/aqp-8/plant_morphology had
    before (those are all species catalog or one-shot calculations).
    partGrowth (JSON {partName: normalizedGrowth}) replaces age as the
    progress measure, PER PART (Dustin, 2026-07-15: "defining vector
    growth per unit time based on the plant part the vector defines")
    — see advance_growth()."""

    @treeObjectInit
    def __init__(
        self,
        # unique key ('demo-herb-pot-basil-1').
        name: str = '',
        pot_name: str = '',
        plant_name: str = '',
        planted_at: str = '',
        # Optional aquaponics.pot_system_basis.PotSystemDefinition name — the
        # SAME pot can have more than one bound system (e.g. demo-herb-
        # pot has both a healthy ventilated-tent and a failing sealed-
        # chamber system in the real seed data), so this can't be
        # inferred from pot_name alone. When set, advance_growth()
        # auto-computes PER-PART stress factors from the system's real
        # atmosphere/water/soil rows (aquaponics.plant_stress_basis, phase 7)
        # instead of requiring a manually-supplied factor. Empty =
        # no stress-equation linkage; manual factors (or none, i.e.
        # 1.0) are used instead.
        system_name: str = '',
        # Reproducible procedural generation seed — the SAME pot
        # always renders the SAME branching pattern until replanted,
        # never a different random plant on every page load.
        random_seed: int = 0,
        # JSON {partName: normalizedGrowth}, e.g.
        # {"root": 0.31, "stem": 0.28, "leaf": 0.40}. 0 = just
        # germinated, 1 = fully mature relative to that part's
        # free-soil reference (or its constrained ceiling if confined).
        # Parts absent from this dict are treated as GROWTH_SEED_EPSILON
        # (not yet advanced) — never a silent 0 (a logistic ODE started
        # at 0 never leaves 0).
        part_growth_json: str = '{}',
        # healthy | stressed | senescing | failed — same vocabulary as
        # aqp-8's per-part condition, applied whole-plant here (worst
        # of any part's condition — see advance_growth).
        condition: str = 'healthy',
        last_advanced_at: str = '',
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.pot_name = pot_name
        self.plant_name = plant_name
        self.planted_at = planted_at
        self.system_name = system_name
        self.random_seed = random_seed
        self.part_growth_json = part_growth_json
        self.condition = condition
        self.last_advanced_at = last_advanced_at
        self.provenance_id = provenance_id
        self.notes = notes
