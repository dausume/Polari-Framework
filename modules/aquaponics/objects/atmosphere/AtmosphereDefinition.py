"""
@module aquaponics.objects.atmosphere.AtmosphereDefinition

Row class AtmosphereDefinition of the aquaponics module — one class per file (design §7), split
from atmosphere_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class AtmosphereDefinition(treeObject):
    """One atmospheric environment (open or controlled)."""

    @treeObjectInit
    def __init__(
        self,
        # kebab-case unique key ('open-greenhouse').
        name: str = '',
        display_name: str = '',
        description: str = '',
        # Controlled/enclosed vs open air. Controlled + a finite
        # volume lets the plant measurably shift the CO2/O2.
        controlled: bool = False,
        # Enclosed air volume (m^3); ignored when not controlled.
        volume_m3: float = 0.0,
        # Composition + state.
        co2_ppm: float = 420.0,
        o2_pct: float = 20.95,
        temperature_c: float = 22.0,
        relative_humidity_pct: float = 60.0,
        pressure_kpa: float = 101.3,
        # Ambient CO2 the ventilation air brings in (ppm).
        outside_co2_ppm: float = 420.0,
        # Air changes per hour (ventilation); 0 = sealed.
        air_exchange_per_hour: float = 1.0,
        # Light: PAR photon flux + photoperiod.
        light_ppfd_umol_m2_s: float = 300.0,
        photoperiod_hours: float = 14.0,
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.description = description
        self.controlled = controlled
        self.volume_m3 = volume_m3
        self.co2_ppm = co2_ppm
        self.o2_pct = o2_pct
        self.temperature_c = temperature_c
        self.relative_humidity_pct = relative_humidity_pct
        self.pressure_kpa = pressure_kpa
        self.outside_co2_ppm = outside_co2_ppm
        self.air_exchange_per_hour = air_exchange_per_hour
        self.light_ppfd_umol_m2_s = light_ppfd_umol_m2_s
        self.photoperiod_hours = photoperiod_hours
        self.provenance_id = provenance_id
        self.notes = notes
