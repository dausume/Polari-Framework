"""
@cross-cutting
@module waxprint.waxprint_basis
@tags @xc:bindings, @xc:render-3d

The persisted objects of the wax 3D-printer ("magic 3D printer")
simulation — object coherence: the printer, the wax it eats, and the
conditions it prints under are all first-class tunable rows, each auto
CRUDE + persisted (like aquaponics/pot_basis).

  PrinterAssemblyDefinition   the pellet-fed auger-screw extruder as a
      MATH-SHAPED device — a screw inside a barrel with two independently
      controlled thermal zones (auger + hotend/spout) feeding a nozzle.
      Every length scales by one `assembly_scale` knob (Dustin: study
      size -> flow). Screw / chamber / nozzle / bed MATERIALS are refs
      into materialsScience so their thermal conductivity is an object,
      not a magic number.

  WaxFeedstockDefinition      the engineered all-natural wax, fed as
      pellets. Carries the COMPUTED material properties the melt physics
      consumes and — critically — the thermal SAFETY window (a natural
      wax degrades / volatilizes above a ceiling). Links to a
      materialsScience wax material and a waxsupply source.

  PrintConditionDefinition    one point in the condition vector we sweep:
      the two zone temperatures, screw RPM, nozzle size, ambient / bed
      temperature, the fan wind vector, speed and layer height. This is
      the object the optimizer iterates over across many trials.

Geometry is millimetres, temperatures Celsius (converted to SI in
melt_analysis). Priors are flagged in `notes`; nothing here is measured
until Dustin's rig pins it (knobs-and-suggestions).

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence) + seed_pairs
  - waxprint.melt_analysis / bead_analysis / print_optimizer
  - waxprint.waxprint_api
@see /MVW_PRINT_SIM_PLAN.md, /WAX_PRINT_VOXEL_PLAN.md
"""

from objectTreeDecorators import treeObject, treeObjectInit

#: Convection presets shared with bead cooling (wp-2). Effective
#: still-air / enclosed / gently-ducted heat-transfer coefficients
#: (W/m^2.K). The fan question is answered by DATA, not assumption.
CONVECTION_PRESETS = {
    'still-air': 8.0,
    'fridge-still': 12.0,
    'gentle-ducted': 30.0,
    'strong-fan': 80.0,
}


#: Roles a DeviceMaterialDefinition can play in the assembly.
DEVICE_MATERIAL_ROLES = ('nozzle', 'auger', 'chamber', 'bed', 'multi')


class DeviceMaterialDefinition(treeObject):
    """A material a printer part is made of — nozzle / auger / chamber /
    bed. Lightweight and waxprint-local (a soft peer of a full
    materialsScience row, linked by material_ref): it carries just the
    handful of properties the print sim actually consumes — thermal
    conductivity (wall temperature uniformity), max service temperature
    (a SECOND safety axis: the part must tolerate its zone temperature),
    thermal mass (bed cooling, wp-2) and a bed adhesion factor (wp-3)."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        display_name: str = '',
        description: str = '',
        role: str = 'multi',
        # Optional link to the full materialsScience material.
        material_ref: str = '',
        thermal_conductivity_w_mk: float = 15.0,
        density_kg_m3: float = 7800.0,
        specific_heat_j_kgk: float = 500.0,
        # The part's own thermal limit (e.g. a PTFE-lined hotend ~260C).
        max_service_temp_c: float = 400.0,
        # For beds: 0..1 first-layer adhesion quality (wp-3).
        bed_adhesion_factor: float = 0.5,
        surface_note: str = '',
        notes: str = '',
        provenance_id: str = '',
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.description = description
        self.role = role
        self.material_ref = material_ref
        self.thermal_conductivity_w_mk = thermal_conductivity_w_mk
        self.density_kg_m3 = density_kg_m3
        self.specific_heat_j_kgk = specific_heat_j_kgk
        self.max_service_temp_c = max_service_temp_c
        self.bed_adhesion_factor = bed_adhesion_factor
        self.surface_note = surface_note
        self.notes = notes
        self.provenance_id = provenance_id


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


class WaxFeedstockDefinition(treeObject):
    """An all-natural engineered wax fed as pellets, with its computed
    material properties and thermal-safety window."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        display_name: str = '',
        description: str = '',

        # Links (object coherence).
        wax_material_ref: str = '',      # materialsScience material
        wax_source_ref: str = '',        # waxsupply WaxSourceDefinition

        # Pellet + thermophysical properties (SI-ish, mm for the pellet).
        pellet_diameter_mm: float = 3.0,
        density_kg_m3: float = 950.0,
        specific_heat_j_kgk: float = 2100.0,
        latent_heat_fusion_j_kg: float = 180000.0,
        thermal_conductivity_w_mk: float = 0.25,

        # Phase + SAFETY window (Celsius).
        melt_point_c: float = 82.0,
        # Below this the melt is too stiff to flow (informational).
        safe_melt_min_c: float = 85.0,
        # Thermal-degradation / volatilization ceiling — the HARD safety
        # limit the melt gate refuses to cross.
        safe_melt_max_c: float = 150.0,

        # Arrhenius melt viscosity eta(T)=eta_ref*exp(B(1/T-1/T_ref)).
        viscosity_ref_pa_s: float = 5.0,
        viscosity_ref_temp_c: float = 100.0,
        viscosity_activation_k: float = 6000.0,

        notes: str = '',
        provenance_id: str = '',
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.description = description
        self.wax_material_ref = wax_material_ref
        self.wax_source_ref = wax_source_ref
        self.pellet_diameter_mm = pellet_diameter_mm
        self.density_kg_m3 = density_kg_m3
        self.specific_heat_j_kgk = specific_heat_j_kgk
        self.latent_heat_fusion_j_kg = latent_heat_fusion_j_kg
        self.thermal_conductivity_w_mk = thermal_conductivity_w_mk
        self.melt_point_c = melt_point_c
        self.safe_melt_min_c = safe_melt_min_c
        self.safe_melt_max_c = safe_melt_max_c
        self.viscosity_ref_pa_s = viscosity_ref_pa_s
        self.viscosity_ref_temp_c = viscosity_ref_temp_c
        self.viscosity_activation_k = viscosity_activation_k
        self.notes = notes
        self.provenance_id = provenance_id


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
