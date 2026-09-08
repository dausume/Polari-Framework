"""
@module aquaponics.objects.vermicompost.CompostBinDefinition

Row class CompostBinDefinition of the aquaponics module — one class per file (design §7), split
from vermicompost_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class CompostBinDefinition(treeObject):
    """One worm-compost bin the aquaponic water is routed through."""

    @treeObjectInit
    def __init__(
        self,
        # kebab-case unique key ('kitchen-worm-bin').
        name: str = '',
        display_name: str = '',
        description: str = '',
        # Vessel + bed.
        volume_l: float = 40.0,
        bed_mass_kg: float = 12.0,
        # kg worms / kg bed (Eisenia fetida beds run ~0.05-0.15).
        worm_density: float = 0.1,
        # FEEDSTOCK_KINDS entry.
        feedstock_kind: str = 'mixed',
        c_to_n_ratio: float = 25.0,
        # 0-1 gravimetric moisture (worm beds want ~0.7-0.85).
        moisture_target: float = 0.8,
        temperature_c: float = 20.0,
        # How cured the castings are (days) — maturity gates release.
        maturity_days: float = 60.0,
        # The release profile this bed leaches (a VermicompostProfile).
        release_profile_name: str = '',
        # Flow-coupling mode + schedule (schedule used in periodic only).
        mode: str = 'direct',
        on_minutes: float = 20.0,
        cycle_hours: float = 6.0,
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.description = description
        self.volume_l = volume_l
        self.bed_mass_kg = bed_mass_kg
        self.worm_density = worm_density
        self.feedstock_kind = feedstock_kind
        self.c_to_n_ratio = c_to_n_ratio
        self.moisture_target = moisture_target
        self.temperature_c = temperature_c
        self.maturity_days = maturity_days
        self.release_profile_name = release_profile_name
        self.mode = mode
        self.on_minutes = on_minutes
        self.cycle_hours = cycle_hours
        self.provenance_id = provenance_id
        self.notes = notes
