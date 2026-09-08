"""
@module waxprint.objects.waxprint.PrintConditionDefinition

Row class PrintConditionDefinition of the waxprint module — one class per file (design §7), split
from waxprint_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class PrintConditionDefinition(treeObject):
    """One point in the condition vector the optimizer sweeps."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        display_name: str = '',
        description: str = '',

        # Two-zone thermal control (the new requirement).
        auger_temp_c: float = 90.0,
        hotend_temp_c: float = 110.0,
        rpm: float = 30.0,

        # 0 = use the assembly's nozzle; else override (mm).
        nozzle_diameter_mm: float = 0.0,

        # Environment.
        ambient_temp_c: float = 22.0,
        bed_temp_c: float = 22.0,
        convection_preset: str = 'still-air',

        # Fan as a WIND VECTOR (mm/s) — answers Dustin's "does a fan just
        # add instability?" with a directional forced-convection model
        # rather than an assumption (wp-2).
        fan_wind_vx_mm_s: float = 0.0,
        fan_wind_vy_mm_s: float = 0.0,
        fan_wind_vz_mm_s: float = 0.0,

        # Motion.
        print_speed_mm_s: float = 30.0,
        layer_height_mm: float = 0.2,

        notes: str = '',
        provenance_id: str = '',
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.description = description
        self.auger_temp_c = auger_temp_c
        self.hotend_temp_c = hotend_temp_c
        self.rpm = rpm
        self.nozzle_diameter_mm = nozzle_diameter_mm
        self.ambient_temp_c = ambient_temp_c
        self.bed_temp_c = bed_temp_c
        self.convection_preset = convection_preset
        self.fan_wind_vx_mm_s = fan_wind_vx_mm_s
        self.fan_wind_vy_mm_s = fan_wind_vy_mm_s
        self.fan_wind_vz_mm_s = fan_wind_vz_mm_s
        self.print_speed_mm_s = print_speed_mm_s
        self.layer_height_mm = layer_height_mm
        self.notes = notes
        self.provenance_id = provenance_id
