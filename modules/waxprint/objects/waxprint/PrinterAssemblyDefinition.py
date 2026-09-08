"""
@module waxprint.objects.waxprint.PrinterAssemblyDefinition

Row class PrinterAssemblyDefinition of the waxprint module — one class per file (design §7), split
from waxprint_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class PrinterAssemblyDefinition(treeObject):
    """A pellet-fed auger-screw wax extruder with two thermal zones."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        display_name: str = '',
        description: str = '',

        # --- screw + barrel geometry (mm) ---
        bore_diameter_mm: float = 12.0,
        screw_core_diameter_mm: float = 6.0,
        screw_pitch_mm: float = 8.0,
        barrel_length_mm: float = 120.0,
        # Fraction of the barrel that is the AUGER (pre-heat) zone; the
        # rest is the HOTEND zone up to the nozzle.
        auger_zone_fraction: float = 0.6,

        # --- nozzle / spout (mm) ---
        nozzle_diameter_mm: float = 0.4,
        nozzle_land_mm: float = 0.8,

        # --- materials as objects (materialsScience refs by name) ---
        auger_material_ref: str = '',
        chamber_material_ref: str = '',
        nozzle_material_ref: str = '',
        bed_material_ref: str = '',

        # --- wall <-> pellet coupling + conveying ---
        # Effective wall-to-pellet heat-transfer coefficient (W/m^2.K).
        wall_h_w_m2k: float = 250.0,
        # Kinematic conveying efficiency of the single screw (magic feed).
        drag_efficiency: float = 0.6,

        # ONE size knob: multiplies every length (Dustin size->flow study).
        assembly_scale: float = 1.0,

        # Optional link to a mathshapes CSG row rendering this device.
        geometry_shape_ref: str = '',

        notes: str = '',
        provenance_id: str = '',
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.description = description
        self.bore_diameter_mm = bore_diameter_mm
        self.screw_core_diameter_mm = screw_core_diameter_mm
        self.screw_pitch_mm = screw_pitch_mm
        self.barrel_length_mm = barrel_length_mm
        self.auger_zone_fraction = auger_zone_fraction
        self.nozzle_diameter_mm = nozzle_diameter_mm
        self.nozzle_land_mm = nozzle_land_mm
        self.auger_material_ref = auger_material_ref
        self.chamber_material_ref = chamber_material_ref
        self.nozzle_material_ref = nozzle_material_ref
        self.bed_material_ref = bed_material_ref
        self.wall_h_w_m2k = wall_h_w_m2k
        self.drag_efficiency = drag_efficiency
        self.assembly_scale = assembly_scale
        self.geometry_shape_ref = geometry_shape_ref
        self.notes = notes
        self.provenance_id = provenance_id
