"""
@cross-cutting
@module waxprint.waxprint_seed

Seed rows for the wax 3D-printer sim — plain lists of dicts keyed by a
kebab-case `name` (idempotent-by-name; the central seed loop does the
CRUDE create). Parents before children is enforced by seed_pairs
ordering in polariServer.

Everything thermophysical is a LABELLED PRIOR (literature / worksheet)
until Dustin's rig measures it — flagged in each row's `notes` and
carried through to the sim results (knobs-and-suggestions).

@consumers
  - polariServer seed_pairs (DeviceMaterial + Feedstock before Assembly;
    Assembly + Condition any order)
"""

_PRIOR = 'PRIOR (literature/worksheet) — pending rig measurement.'

import json as _json

# --------------------------------------------------------------------------
# first-class Polari Module identity (a PolariModule registry row) — makes
# "Wax-3D-Printing" a named module surfaced via GET /api/modules, alongside
# its FRAMEWORK_BOUNDARIES entry in the module-dependency explorer.
# --------------------------------------------------------------------------
SEED_WAXPRINT_MODULES = [{
    'name': 'Wax-3D-Printing',
    'version': '',
    'source_kind': 'file',
    'source_ref': 'waxprint',
    'status': 'installed',
    'manifest_json': _json.dumps({
        'displayName': 'Wax-3D-Printing',
        'summary': 'Pellet-fed auger-screw wax 3D-printer: simulate the '
                   'melt/bead/voxel physics, optimize print recipes, view '
                   'it in 3D, evaluate condition gates, and drive it via '
                   'no-code wax-printer commands.',
        'noCodeCommands': ['melt', 'bead-voxel', 'movement', 'print-step'],
        'plannedPrinterControl': ['move-to', 'set-temp', 'extrude'],
        'simSpace': 'wax-print-wall', 'page': 'wax-print-sim',
        'noCodeOperation': 'WaxPrintOperation'}),
    'bundle_json': '',
    # tt-5/tt-8: self-declared tech-tree placement (theory segment of
    # the Electronics-tree 3D-printing node reads this module's
    # installed status).
    'data_only': False,
    'tech_node_ref': 'electronics/3d-printing',
}]

# --------------------------------------------------------------------------
# device part materials
# --------------------------------------------------------------------------
SEED_DEVICE_MATERIALS = [
    # --- nozzles / hotend ---
    {'name': 'brass-nozzle', 'display_name': 'Brass nozzle', 'role': 'nozzle',
     'material_ref': 'brass', 'thermal_conductivity_w_mk': 110.0,
     'density_kg_m3': 8500.0, 'specific_heat_j_kgk': 380.0,
     'max_service_temp_c': 500.0,
     'surface_note': 'High-k → very uniform tip temperature; low cost.',
     'notes': _PRIOR},
    {'name': 'hardened-steel-nozzle', 'display_name': 'Hardened steel nozzle',
     'role': 'nozzle', 'material_ref': 'tool-steel',
     'thermal_conductivity_w_mk': 24.0, 'density_kg_m3': 7800.0,
     'specific_heat_j_kgk': 460.0, 'max_service_temp_c': 600.0,
     'surface_note': 'Wear-resistant for filled/gritty waxes (grog); '
                     'lower-k so tip temperature is less uniform.',
     'notes': _PRIOR},
    {'name': 'ptfe-lined-nozzle', 'display_name': 'PTFE-lined nozzle',
     'role': 'nozzle', 'material_ref': 'ptfe',
     'thermal_conductivity_w_mk': 0.25, 'density_kg_m3': 2200.0,
     'specific_heat_j_kgk': 1000.0, 'max_service_temp_c': 240.0,
     'surface_note': 'Non-stick low-friction bore — but a HARD service '
                     'ceiling that the safety gate enforces.',
     'notes': _PRIOR + ' Service ceiling exercises material-safety gate.'},

    # --- auger / screw ---
    {'name': 'stainless-auger', 'display_name': 'Stainless-steel auger',
     'role': 'auger', 'material_ref': 'stainless-304',
     'thermal_conductivity_w_mk': 16.0, 'density_kg_m3': 8000.0,
     'specific_heat_j_kgk': 500.0, 'max_service_temp_c': 800.0,
     'surface_note': 'Corrosion-resistant standard screw stock.',
     'notes': _PRIOR},

    # --- melt chamber / barrel ---
    {'name': 'aluminum-chamber', 'display_name': 'Aluminum melt chamber',
     'role': 'chamber', 'material_ref': 'aluminum-6061',
     'thermal_conductivity_w_mk': 167.0, 'density_kg_m3': 2700.0,
     'specific_heat_j_kgk': 900.0, 'max_service_temp_c': 400.0,
     'surface_note': 'High-k → tight, uniform barrel temperature control.',
     'notes': _PRIOR},

    # --- print beds ---
    {'name': 'glass-bed', 'display_name': 'Borosilicate glass bed',
     'role': 'bed', 'material_ref': 'borosilicate-glass',
     'thermal_conductivity_w_mk': 1.1, 'density_kg_m3': 2230.0,
     'specific_heat_j_kgk': 830.0, 'max_service_temp_c': 500.0,
     'bed_adhesion_factor': 0.45,
     'surface_note': 'Smooth flat bottom; moderate wax adhesion.',
     'notes': _PRIOR},
    {'name': 'aluminum-bed', 'display_name': 'Aluminum bed',
     'role': 'bed', 'material_ref': 'aluminum-6061',
     'thermal_conductivity_w_mk': 167.0, 'density_kg_m3': 2700.0,
     'specific_heat_j_kgk': 900.0, 'max_service_temp_c': 400.0,
     'bed_adhesion_factor': 0.4,
     'surface_note': 'Fast, even heat spreading; chills wax quickly.',
     'notes': _PRIOR},
    {'name': 'pei-bed', 'display_name': 'PEI-coated bed', 'role': 'bed',
     'material_ref': 'pei', 'thermal_conductivity_w_mk': 0.25,
     'density_kg_m3': 1270.0, 'specific_heat_j_kgk': 1100.0,
     'max_service_temp_c': 250.0, 'bed_adhesion_factor': 0.8,
     'surface_note': 'Strong first-layer grip; insulating so slower chill.',
     'notes': _PRIOR},
]

# --------------------------------------------------------------------------
# wax feedstocks (all-natural)
# --------------------------------------------------------------------------
SEED_FEEDSTOCKS = [
    {'name': 'mvw-natural-blend', 'display_name': 'MVW natural blend',
     'description': 'Minimum-viable printable wax: beeswax base + carnauba '
                    '10% + pine rosin 17.5% + grog 1µm 2.5% (fossil-free '
                    'MVW, score 0.610).',
     'wax_material_ref': 'beeswax', 'wax_source_ref': 'beeswax',
     'pellet_diameter_mm': 3.0, 'density_kg_m3': 965.0,
     'specific_heat_j_kgk': 2100.0, 'latent_heat_fusion_j_kg': 180000.0,
     'thermal_conductivity_w_mk': 0.27,
     'melt_point_c': 90.0, 'safe_melt_min_c': 95.0, 'safe_melt_max_c': 160.0,
     'viscosity_ref_pa_s': 0.6, 'viscosity_ref_temp_c': 100.0,
     'viscosity_activation_k': 6500.0,
     'notes': _PRIOR + ' Blend melt point is the ~90-120C eutectic prior; '
              'rosin sets the ~160C degradation ceiling.'},
    {'name': 'beeswax-pure', 'display_name': 'Pure beeswax',
     'description': 'Unfilled beeswax pellets — soft, low melt.',
     'wax_material_ref': 'beeswax', 'wax_source_ref': 'beeswax',
     'pellet_diameter_mm': 3.0, 'density_kg_m3': 960.0,
     'specific_heat_j_kgk': 2100.0, 'latent_heat_fusion_j_kg': 175000.0,
     'thermal_conductivity_w_mk': 0.25,
     'melt_point_c': 64.0, 'safe_melt_min_c': 70.0, 'safe_melt_max_c': 150.0,
     'viscosity_ref_pa_s': 0.02, 'viscosity_ref_temp_c': 80.0,
     'viscosity_activation_k': 5500.0,
     'notes': _PRIOR + ' Very low melt viscosity — a stringing/sag risk.'},
    {'name': 'carnauba-rich', 'display_name': 'Carnauba-rich blend',
     'description': 'Hard carnauba-dominant blend — high melt, dimensionally '
                    'stable, the mold/mask workhorse.',
     'wax_material_ref': 'carnauba-wax', 'wax_source_ref': 'carnauba',
     'pellet_diameter_mm': 3.0, 'density_kg_m3': 997.0,
     'specific_heat_j_kgk': 2000.0, 'latent_heat_fusion_j_kg': 195000.0,
     'thermal_conductivity_w_mk': 0.30,
     'melt_point_c': 84.0, 'safe_melt_min_c': 90.0, 'safe_melt_max_c': 200.0,
     'viscosity_ref_pa_s': 1.2, 'viscosity_ref_temp_c': 110.0,
     'viscosity_activation_k': 7000.0,
     'notes': _PRIOR + ' Carnauba is stable to ~200C — the widest safe '
              'window here.'},
    {'name': 'candelilla-blend', 'display_name': 'Candelilla blend',
     'description': 'Hydroponic-feasible shrub wax, moderate hardness.',
     'wax_material_ref': 'candelilla-wax', 'wax_source_ref': 'candelilla',
     'pellet_diameter_mm': 3.0, 'density_kg_m3': 983.0,
     'specific_heat_j_kgk': 2050.0, 'latent_heat_fusion_j_kg': 185000.0,
     'thermal_conductivity_w_mk': 0.26,
     'melt_point_c': 70.0, 'safe_melt_min_c': 76.0, 'safe_melt_max_c': 180.0,
     'viscosity_ref_pa_s': 0.4, 'viscosity_ref_temp_c': 95.0,
     'viscosity_activation_k': 6200.0,
     'notes': _PRIOR},
]

# --------------------------------------------------------------------------
# printer assemblies (the math-shaped device)
# --------------------------------------------------------------------------
SEED_ASSEMBLIES = [
    {'name': 'demo-auger-extruder', 'display_name': 'Demo auger extruder',
     'description': 'Reference pellet-fed auger-screw wax extruder, brass '
                    'nozzle + aluminum chamber + stainless auger.',
     'bore_diameter_mm': 12.0, 'screw_core_diameter_mm': 6.0,
     'screw_pitch_mm': 8.0, 'barrel_length_mm': 120.0,
     'auger_zone_fraction': 0.6, 'nozzle_diameter_mm': 0.4,
     'nozzle_land_mm': 0.8,
     'auger_material_ref': 'stainless-auger',
     'chamber_material_ref': 'aluminum-chamber',
     'nozzle_material_ref': 'brass-nozzle', 'bed_material_ref': 'glass-bed',
     'wall_h_w_m2k': 250.0, 'drag_efficiency': 0.6, 'assembly_scale': 1.0,
     'notes': 'Reference geometry; wall_h is a prior coupling coefficient.'},
    {'name': 'ptfe-hotend-extruder',
     'display_name': 'PTFE-lined hotend extruder',
     'description': 'Same body but a PTFE-lined nozzle (240C service '
                    'ceiling) — exercises the material-safety gate.',
     'bore_diameter_mm': 12.0, 'screw_core_diameter_mm': 6.0,
     'screw_pitch_mm': 8.0, 'barrel_length_mm': 120.0,
     'auger_zone_fraction': 0.6, 'nozzle_diameter_mm': 0.4,
     'nozzle_land_mm': 0.8,
     'auger_material_ref': 'stainless-auger',
     'chamber_material_ref': 'aluminum-chamber',
     'nozzle_material_ref': 'ptfe-lined-nozzle', 'bed_material_ref': 'pei-bed',
     'wall_h_w_m2k': 250.0, 'drag_efficiency': 0.6, 'assembly_scale': 1.0,
     'notes': 'PTFE liner limits the hotend.'},
    {'name': 'fine-nozzle-extruder',
     'display_name': 'Fine-nozzle extruder (0.25mm)',
     'description': 'Hardened-steel 0.25mm nozzle for the finest voxels.',
     'bore_diameter_mm': 12.0, 'screw_core_diameter_mm': 6.0,
     'screw_pitch_mm': 8.0, 'barrel_length_mm': 140.0,
     'auger_zone_fraction': 0.55, 'nozzle_diameter_mm': 0.25,
     'nozzle_land_mm': 0.6,
     'auger_material_ref': 'stainless-auger',
     'chamber_material_ref': 'aluminum-chamber',
     'nozzle_material_ref': 'hardened-steel-nozzle',
     'bed_material_ref': 'glass-bed',
     'wall_h_w_m2k': 250.0, 'drag_efficiency': 0.6, 'assembly_scale': 1.0,
     'notes': 'Longer barrel to keep melt complete at the finer orifice.'},
]

# --------------------------------------------------------------------------
# print conditions (the sweep vector)
# --------------------------------------------------------------------------
SEED_CONDITIONS = [
    {'name': 'room-baseline', 'display_name': 'Room baseline',
     'description': 'Nominal room-temperature print.',
     'auger_temp_c': 95.0, 'hotend_temp_c': 115.0, 'rpm': 25.0,
     'nozzle_diameter_mm': 0.0, 'ambient_temp_c': 22.0, 'bed_temp_c': 22.0,
     'convection_preset': 'still-air', 'print_speed_mm_s': 30.0,
     'layer_height_mm': 0.2, 'notes': 'Default operating point.'},
    {'name': 'fridge-print', 'display_name': 'Chilled (fridge) print',
     'description': 'Printing inside a fridge — physically doable, so '
                    'simulate it: cold ambient + chilled bed for fast set.',
     'auger_temp_c': 95.0, 'hotend_temp_c': 115.0, 'rpm': 25.0,
     'nozzle_diameter_mm': 0.0, 'ambient_temp_c': 4.0, 'bed_temp_c': 4.0,
     'convection_preset': 'fridge-still', 'print_speed_mm_s': 30.0,
     'layer_height_mm': 0.2, 'notes': 'Cold-chamber scenario.'},
    {'name': 'hot-unsafe', 'display_name': 'Over-ceiling (unsafe) demo',
     'description': 'Hotend pushed above the wax safety ceiling — the melt '
                    'gate must REFUSE with evidence.',
     'auger_temp_c': 120.0, 'hotend_temp_c': 175.0, 'rpm': 25.0,
     'nozzle_diameter_mm': 0.0, 'ambient_temp_c': 22.0, 'bed_temp_c': 22.0,
     'convection_preset': 'still-air', 'print_speed_mm_s': 30.0,
     'layer_height_mm': 0.2, 'notes': 'Deliberately unsafe fixture.'},
    {'name': 'cold-undermelt', 'display_name': 'Under-melt demo',
     'description': 'Hotend below melt margin / screw too fast — should flag '
                    'under-melted.',
     'auger_temp_c': 60.0, 'hotend_temp_c': 88.0, 'rpm': 120.0,
     'nozzle_diameter_mm': 0.0, 'ambient_temp_c': 22.0, 'bed_temp_c': 22.0,
     'convection_preset': 'still-air', 'print_speed_mm_s': 60.0,
     'layer_height_mm': 0.2, 'notes': 'Deliberately under-melted fixture.'},
    {'name': 'ducted-fan', 'display_name': 'Gentle ducted fan',
     'description': 'Controlled ducted airflow — the fan question, as a '
                    'wind vector, answered with data (wp-2).',
     'auger_temp_c': 95.0, 'hotend_temp_c': 115.0, 'rpm': 25.0,
     'nozzle_diameter_mm': 0.0, 'ambient_temp_c': 22.0, 'bed_temp_c': 22.0,
     'convection_preset': 'gentle-ducted',
     'fan_wind_vx_mm_s': 800.0, 'fan_wind_vy_mm_s': 0.0,
     'fan_wind_vz_mm_s': 0.0, 'print_speed_mm_s': 30.0,
     'layer_height_mm': 0.2, 'notes': 'Directional cooling airflow.'},
    {'name': 'fine-voxel', 'display_name': 'Fine-voxel recipe',
     'description': 'Slower + thinner layers for the finest voxels.',
     'auger_temp_c': 92.0, 'hotend_temp_c': 108.0, 'rpm': 12.0,
     'nozzle_diameter_mm': 0.25, 'ambient_temp_c': 18.0, 'bed_temp_c': 18.0,
     'convection_preset': 'fridge-still', 'print_speed_mm_s': 15.0,
     'layer_height_mm': 0.1, 'notes': 'Fine-resolution operating point.'},
]
