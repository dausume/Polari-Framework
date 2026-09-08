"""
@module tanks.objects.tank.TankSubstrateDefinition

Row class TankSubstrateDefinition of the tanks module — one class per file (design §7), split
from tank_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class TankSubstrateDefinition(treeObject):
    """A tank substrate ("soil") — the NEW soil category for freshwater
    + saltwater tanks (distinct from the aquaponics pot SoilDefinition).

    Models the submerged bed: pH/alkalinity BUFFERING (saltwater
    aragonite holds Ca + carbonate hardness), nutrient STORAGE/RELEASE
    (aquasoil leaches nutrients; CEC-like), aerobic BIOFILTRATION in the
    upper layer, and anaerobic DENITRIFICATION deeper down (the spec's
    substrate-oxygenation idea — an oxygenated top over an anaerobic
    core that removes nitrate as N2). Every value is a flagged prior."""

    @treeObjectInit
    def __init__(
        self,
        # kebab-case unique key ('live-aragonite-sand').
        name: str = '',
        display_name: str = '',
        # WATER_TYPES entry — a substrate is fresh OR salt.
        water_type: str = 'salt',
        # SUBSTRATE_KINDS entry.
        kind: str = 'live-aragonite-sand',
        grain_size_mm: float = 1.0,
        # Does it buffer pH / hold alkalinity (aragonite, marine mud)?
        buffers_ph: bool = False,
        target_ph: float = 0.0,
        # Alkalinity contribution (dKH-ish, relative) — buffering
        # strength; 0 = inert.
        alkalinity_contribution: float = 0.0,
        # Nutrient storage capacity (CEC-like, relative 0-1).
        nutrient_storage: float = 0.0,
        # Does it LEACH nutrients into the water early (aquasoil)?
        releases_nutrients: bool = False,
        # Aerobic biofiltration capacity (0-1) — nitrifying surface.
        biofiltration_capacity: float = 0.3,
        # Anaerobic denitrification: nitrate-N removed per L of bed per
        # day (mg) in the deeper anaerobic layer.
        denitrification_mg_n_per_l_per_day: float = 0.0,
        # Keeps an oxygenated top over an anaerobic core (prevents the
        # smelly anoxic upper zone while allowing deep decomposition).
        supports_anaerobic_layer: bool = False,
        is_prior: bool = True,
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.water_type = water_type
        self.kind = kind
        self.grain_size_mm = grain_size_mm
        self.buffers_ph = buffers_ph
        self.target_ph = target_ph
        self.alkalinity_contribution = alkalinity_contribution
        self.nutrient_storage = nutrient_storage
        self.releases_nutrients = releases_nutrients
        self.biofiltration_capacity = biofiltration_capacity
        self.denitrification_mg_n_per_l_per_day = \
            denitrification_mg_n_per_l_per_day
        self.supports_anaerobic_layer = supports_anaerobic_layer
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
