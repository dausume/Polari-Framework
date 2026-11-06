"""
@module mech.custom.registry.material_properties

Textbook PRIOR property values for the registry materials — the numbers
`MechMaterialOption.properties_json` carries until a measured or vendor
value replaces them. Every value is tagged `provenance='textbook-prior'`
(handbook / datasheet-typical, NOT measured by us, NOT cited to a page);
the friction knobs the plan names (section 4, mxc-4) are tagged
`'plan-knob'`. A material with no row here, or a property left out,
is an honest unknown: `material_prop` returns (None, '') and
`role_viability` says UNASSESSED, never a pass.

Property names are the ones composition's `ROLE_REQUIREMENTS` reads:
  tensile_mpa          static-structural / press-fitted / moving ('present')
  hardness_hv          colliding ('present', min 100)
  friction_coefficient sliding ('present') — the HEADLINE pair, mu_kinetic,
                       the counter-material named in the note
  fatigue_class        moving ('present'; motors.motor_fatigue vocabulary:
                       ductile-endurance-limit | ductile-no-endurance-limit
                       | brittle-scg)
  b_r_t, h_c_ka_m      torque-magnet-active (the one magnet row, ndfeb)
plus the mech ones: density_kg_m3, youngs_modulus_gpa, poisson_ratio,
yield_mpa, hardness_shore_a / hardness_shore_d / hardness_rockwell_r
(scale in the name), and `friction_json` — the per-counter-material
table {counter_id: {mu_static, mu_kinetic, basis}}; a key may carry a
'@rolling' suffix for a rolling contact (ball slide) against the same
counter material.

Hardness: steels/aluminium/brass as HV; polymers as Shore D or
Rockwell R; elastomers as Shore A. No conversion between scales is
done here — a part role that wants HV on a polymer stays unassessed.

@consumers mech.custom.material_registry, mech.custom.registry.build_seed
"""

TB = 'textbook-prior'
PK = 'plan-knob'


def _f(mu_s, mu_k, basis, note=''):
    out = {'mu_static': mu_s, 'mu_kinetic': mu_k, 'basis': basis}
    if note:
        out['note'] = note
    return out


#: id -> {prop: (value, unit, provenance[, note])}; friction_json's
#: value is the per-counter dict. -1 = "no number held" (the seed
#: writes the entry with value -1 so a reader sees the gap by name).
PROPERTIES = {
    # ---------------- metals ----------------
    'al_6063': {
        'density_kg_m3': (2700.0, 'kg/m3', TB),
        'youngs_modulus_gpa': (68.9, 'GPa', TB),
        'poisson_ratio': (0.33, '', TB),
        'yield_mpa': (145.0, 'MPa', TB, '6063-T5; T6 ~214'),
        'tensile_mpa': (185.0, 'MPa', TB, '6063-T5; T6 ~241'),
        'hardness_hv': (63.0, 'HV', TB, '6063-T5 ~60 HB'),
        'fatigue_class': ('ductile-no-endurance-limit', '', TB,
                          'aluminium has no endurance limit'),
        'friction_coefficient': (0.15, '', PK,
                                 'against uhmwpe, dry: plan knob '
                                 '0.1-0.2, midpoint'),
        'friction_json': ({
            'uhmwpe': _f(0.2, 0.15, PK, 'UHMWPE-on-aluminium 0.1-0.2'),
            'steel_carbon': _f(0.61, 0.47, TB, 'dry, mild steel on Al'),
            'al_6063': _f(1.05, 1.4, TB, 'dry Al-on-Al galls; avoid'),
            'birch_plywood': _f(0.4, 0.3, TB, 'wood on metal, dry'),
        }, '', TB),
    },
    'al_6061': {
        'density_kg_m3': (2700.0, 'kg/m3', TB),
        'youngs_modulus_gpa': (68.9, 'GPa', TB),
        'poisson_ratio': (0.33, '', TB),
        'yield_mpa': (276.0, 'MPa', TB, 'T6'),
        'tensile_mpa': (310.0, 'MPa', TB, 'T6'),
        'hardness_hv': (107.0, 'HV', TB, 'T6 ~95 HB'),
        'fatigue_class': ('ductile-no-endurance-limit', '', TB),
        'friction_coefficient': (0.47, '', TB, 'against steel_carbon, dry'),
        'friction_json': ({
            'steel_carbon': _f(0.61, 0.47, TB, 'dry'),
            'uhmwpe': _f(0.2, 0.15, PK, 'UHMWPE-on-aluminium 0.1-0.2'),
            'tpu_mdi': _f(0.8, 0.6, TB, 'belt on pulley, dry; a knob'),
        }, '', TB),
    },
    'al_diecast': {
        'density_kg_m3': (2740.0, 'kg/m3', TB),
        'youngs_modulus_gpa': (71.0, 'GPa', TB),
        'poisson_ratio': (0.33, '', TB),
        'yield_mpa': (160.0, 'MPa', TB, 'ADC12 / A380 as-cast'),
        'tensile_mpa': (320.0, 'MPa', TB),
        'hardness_hv': (85.0, 'HV', TB, '~80 HB'),
        'fatigue_class': ('ductile-no-endurance-limit', '', TB),
    },
    'steel_carbon': {
        'density_kg_m3': (7850.0, 'kg/m3', TB),
        'youngs_modulus_gpa': (200.0, 'GPa', TB),
        'poisson_ratio': (0.29, '', TB),
        'yield_mpa': (370.0, 'MPa', TB,
                      '1018 cold drawn; class 8.8 bolt 640, 12.9 1100, '
                      '52100 hardened ~1400'),
        'tensile_mpa': (440.0, 'MPa', TB,
                        '1018 cold drawn; class 8.8 800, 12.9 1200, '
                        '52100 hardened ~2000'),
        'hardness_hv': (130.0, 'HV', TB,
                        '1018 cold drawn; class 12.9 ~390; 52100 '
                        'hardened 700-750 (bearing races)'),
        'fatigue_class': ('ductile-endurance-limit', '', TB,
                          'steel: endurance limit ~0.45-0.5 UTS'),
        'endurance_limit_ratio': (0.5, '', TB),
        'friction_coefficient': (0.57, '', TB,
                                 'against steel_carbon, dry sliding; '
                                 'the ball slide is the @rolling key'),
        'friction_json': ({
            'steel_carbon': _f(0.74, 0.57, TB, 'dry sliding'),
            'steel_carbon@rolling': _f(0.03, 0.02, PK,
                                       'ball slide 0.01-0.03: steel '
                                       'ball in steel raceway'),
            'al_6063': _f(0.61, 0.47, TB, 'dry'),
            'uhmwpe': _f(0.2, 0.15, TB, 'UHMWPE on steel dry 0.10-0.22'),
            'ptfe': _f(0.05, 0.05, PK, 'PTFE 0.04-0.1'),
            'pa66': _f(0.4, 0.3, TB, 'nylon on steel dry 0.25-0.4'),
            'pom': _f(0.3, 0.25, TB, 'acetal on steel dry 0.2-0.35'),
            'brass_lead_free': _f(0.51, 0.44, TB, 'brass on steel dry'),
            'birch_plywood': _f(0.5, 0.35, TB, 'wood on metal dry'),
        }, '', TB),
    },
    'stainless_a2_a4': {
        'density_kg_m3': (8000.0, 'kg/m3', TB),
        'youngs_modulus_gpa': (193.0, 'GPa', TB),
        'poisson_ratio': (0.29, '', TB),
        'yield_mpa': (215.0, 'MPa', TB, '304 annealed; A2-70 bolt 450'),
        'tensile_mpa': (505.0, 'MPa', TB, '304 annealed; A2-70 700'),
        'hardness_hv': (170.0, 'HV', TB, '304 annealed; 440C hardened ~600'),
        'fatigue_class': ('ductile-endurance-limit', '', TB),
        'endurance_limit_ratio': (0.4, '', TB, 'austenitic, lower ratio'),
        'friction_coefficient': (0.5, '', TB, 'against steel_carbon dry'),
        'friction_json': ({
            'steel_carbon': _f(0.6, 0.5, TB, 'dry'),
            'stainless_a2_a4': _f(0.7, 0.6, TB, 'dry; galls under load'),
            'uhmwpe': _f(0.2, 0.15, TB),
            'brass_lead_free': _f(0.5, 0.44, TB, 'lead-screw nut pair'),
            'pa66': _f(0.4, 0.3, TB),
        }, '', TB),
    },
    'brass_lead_free': {
        'density_kg_m3': (8280.0, 'kg/m3', TB, 'CuZn21Si3P'),
        'youngs_modulus_gpa': (104.0, 'GPa', TB),
        'poisson_ratio': (0.34, '', TB),
        'yield_mpa': (300.0, 'MPa', TB),
        'tensile_mpa': (550.0, 'MPa', TB),
        'hardness_hv': (160.0, 'HV', TB),
        'fatigue_class': ('ductile-no-endurance-limit', '', TB),
        'friction_coefficient': (0.44, '', TB, 'against steel dry'),
        'friction_json': ({
            'steel_carbon': _f(0.51, 0.44, TB, 'dry'),
            'stainless_a2_a4': _f(0.5, 0.44, TB, 'lead-screw nut pair'),
        }, '', TB),
    },
    'brass_leaded': {
        'density_kg_m3': (8500.0, 'kg/m3', TB, 'C36000'),
        'youngs_modulus_gpa': (97.0, 'GPa', TB),
        'poisson_ratio': (0.34, '', TB),
        'yield_mpa': (310.0, 'MPa', TB, 'half hard'),
        'tensile_mpa': (400.0, 'MPa', TB, 'half hard'),
        'hardness_hv': (110.0, 'HV', TB, 'half hard'),
        'fatigue_class': ('ductile-no-endurance-limit', '', TB),
        'friction_coefficient': (0.44, '', TB, 'against steel dry'),
        'friction_json': ({'steel_carbon': _f(0.51, 0.44, TB, 'dry')},
                          '', TB),
    },
    'zinc_alloy': {
        'density_kg_m3': (6600.0, 'kg/m3', TB, 'Zamak 3'),
        'youngs_modulus_gpa': (85.5, 'GPa', TB),
        'poisson_ratio': (0.27, '', TB),
        'yield_mpa': (221.0, 'MPa', TB),
        'tensile_mpa': (283.0, 'MPa', TB),
        'hardness_hv': (85.0, 'HV', TB, '~82 HB'),
        'fatigue_class': ('ductile-no-endurance-limit', '', TB),
    },
    'ndfeb': {
        'density_kg_m3': (7500.0, 'kg/m3', TB),
        'youngs_modulus_gpa': (160.0, 'GPa', TB),
        'poisson_ratio': (0.24, '', TB),
        'yield_mpa': (-1, 'MPa', TB, 'brittle: no yield point'),
        'tensile_mpa': (80.0, 'MPa', TB, 'brittle sintered magnet'),
        'hardness_hv': (600.0, 'HV', TB),
        'fatigue_class': ('brittle-scg', '', TB),
        'b_r_t': (1.2, 'T', TB, 'N35 grade 1.17-1.22 T; magnetics '
                               'opt-ndfeb is the magnetic row'),
        'h_c_ka_m': (900.0, 'kA/m', TB, 'N35 Hcb >= 868 kA/m'),
        'mu_r_eff': (1.05, '', TB, 'recoil permeability'),
    },
    # ---------------- fibres ----------------
    'glass_fibre_cord': {
        'density_kg_m3': (2540.0, 'kg/m3', TB, 'E-glass'),
        'youngs_modulus_gpa': (72.0, 'GPa', TB),
        'poisson_ratio': (0.22, '', TB),
        'yield_mpa': (-1, 'MPa', TB, 'brittle fibre'),
        'tensile_mpa': (2000.0, 'MPa', TB, 'strand; virgin filament 3400'),
        'fatigue_class': ('brittle-scg', '', TB),
    },
    'aramid_cord': {
        'density_kg_m3': (1440.0, 'kg/m3', TB, 'Kevlar 29'),
        'youngs_modulus_gpa': (70.0, 'GPa', TB, 'K29; K49 ~112'),
        'poisson_ratio': (0.36, '', TB),
        'tensile_mpa': (2900.0, 'MPa', TB),
    },
    'steel_cord': {
        'density_kg_m3': (7850.0, 'kg/m3', TB),
        'youngs_modulus_gpa': (200.0, 'GPa', TB),
        'poisson_ratio': (0.29, '', TB),
        'yield_mpa': (1800.0, 'MPa', TB, 'high-carbon drawn wire'),
        'tensile_mpa': (2000.0, 'MPa', TB, 'high-carbon drawn wire 2000-2800'),
        'fatigue_class': ('ductile-endurance-limit', '', TB),
    },
    # ---------------- rigid polymers ----------------
    'pla': {
        'density_kg_m3': (1240.0, 'kg/m3', TB),
        'youngs_modulus_gpa': (3.5, 'GPa', TB, 'moulded; FDM-printed ~2.5-3'),
        'poisson_ratio': (0.36, '', TB),
        'yield_mpa': (60.0, 'MPa', TB, 'moulded; printed XY ~45-55'),
        'tensile_mpa': (60.0, 'MPa', TB, 'moulded; printed ~50, Z weaker'),
        'hardness_shore_d': (83.0, 'Shore D', TB),
        'friction_coefficient': (0.35, '', TB, 'against steel dry; a knob'),
        'friction_json': ({'steel_carbon': _f(0.4, 0.35, TB, 'dry')}, '', TB),
    },
    'petg': {
        'density_kg_m3': (1270.0, 'kg/m3', TB),
        'youngs_modulus_gpa': (2.1, 'GPa', TB),
        'poisson_ratio': (0.38, '', TB),
        'yield_mpa': (50.0, 'MPa', TB),
        'tensile_mpa': (53.0, 'MPa', TB, 'moulded; printed ~45'),
        'hardness_shore_d': (76.0, 'Shore D', TB),
        'friction_coefficient': (0.35, '', TB, 'against steel dry; a knob'),
        'friction_json': ({'steel_carbon': _f(0.4, 0.35, TB, 'dry')}, '', TB),
    },
    'pp': {
        'density_kg_m3': (905.0, 'kg/m3', TB),
        'youngs_modulus_gpa': (1.5, 'GPa', TB),
        'poisson_ratio': (0.42, '', TB),
        'yield_mpa': (33.0, 'MPa', TB),
        'tensile_mpa': (35.0, 'MPa', TB),
        'hardness_shore_d': (70.0, 'Shore D', TB),
    },
    'uhmwpe': {
        'density_kg_m3': (940.0, 'kg/m3', TB),
        'youngs_modulus_gpa': (0.7, 'GPa', TB),
        'poisson_ratio': (0.46, '', TB),
        'yield_mpa': (21.0, 'MPa', TB),
        'tensile_mpa': (40.0, 'MPa', TB, 'at break 38-48'),
        'hardness_shore_d': (64.0, 'Shore D', TB),
        'friction_coefficient': (0.15, '', PK,
                                 'against al_6063, dry: plan knob '
                                 'UHMWPE-on-aluminium 0.1-0.2, midpoint'),
        'friction_json': ({
            'al_6063': _f(0.2, 0.15, PK, 'UHMWPE-on-aluminium 0.1-0.2'),
            'al_6061': _f(0.2, 0.15, PK, 'UHMWPE-on-aluminium 0.1-0.2'),
            'steel_carbon': _f(0.2, 0.15, TB, 'dry 0.10-0.22'),
            'stainless_a2_a4': _f(0.2, 0.15, TB),
            'uhmwpe': _f(0.12, 0.1, TB, 'self-mated'),
            'birch_plywood': _f(0.25, 0.2, TB, 'a knob'),
        }, '', TB),
    },
    'pa66': {
        'density_kg_m3': (1140.0, 'kg/m3', TB),
        'youngs_modulus_gpa': (2.8, 'GPa', TB, 'dry as moulded; 50 % RH ~1.2'),
        'poisson_ratio': (0.39, '', TB),
        'yield_mpa': (80.0, 'MPa', TB, 'dry; conditioned ~55'),
        'tensile_mpa': (82.0, 'MPa', TB, 'dry as moulded'),
        'hardness_rockwell_r': (120.0, 'Rockwell R', TB),
        'friction_coefficient': (0.3, '', TB, 'against steel dry 0.25-0.4'),
        'friction_json': ({
            'steel_carbon': _f(0.4, 0.3, TB, 'dry'),
            'stainless_a2_a4': _f(0.4, 0.3, TB, 'dry'),
            'al_6061': _f(0.4, 0.3, TB, 'dry; a knob'),
            'pa66': _f(0.5, 0.4, TB, 'self-mated, dry'),
        }, '', TB),
    },
    'pa6': {
        'density_kg_m3': (1130.0, 'kg/m3', TB),
        'youngs_modulus_gpa': (2.6, 'GPa', TB, 'dry'),
        'poisson_ratio': (0.39, '', TB),
        'yield_mpa': (70.0, 'MPa', TB, 'dry'),
        'tensile_mpa': (78.0, 'MPa', TB, 'dry'),
        'hardness_shore_d': (78.0, 'Shore D', TB),
        'friction_coefficient': (0.3, '', TB, 'against steel dry'),
        'friction_json': ({'steel_carbon': _f(0.4, 0.3, TB, 'dry')}, '', TB),
    },
    'pa11': {
        'density_kg_m3': (1040.0, 'kg/m3', TB),
        'youngs_modulus_gpa': (1.2, 'GPa', TB),
        'poisson_ratio': (0.4, '', TB),
        'yield_mpa': (40.0, 'MPa', TB),
        'tensile_mpa': (45.0, 'MPa', TB),
        'hardness_shore_d': (72.0, 'Shore D', TB),
        'friction_coefficient': (0.3, '', TB, 'against steel dry; a knob'),
        'friction_json': ({'steel_carbon': _f(0.4, 0.3, TB, 'dry; a knob')},
                          '', TB),
    },
    'peek': {
        'density_kg_m3': (1320.0, 'kg/m3', TB),
        'youngs_modulus_gpa': (3.6, 'GPa', TB),
        'poisson_ratio': (0.38, '', TB),
        'yield_mpa': (95.0, 'MPa', TB),
        'tensile_mpa': (100.0, 'MPa', TB),
        'hardness_shore_d': (85.0, 'Shore D', TB),
        'friction_coefficient': (0.35, '', TB, 'against steel dry, unfilled'),
        'friction_json': ({'steel_carbon': _f(0.4, 0.35, TB, 'dry, unfilled')},
                          '', TB),
    },
    'pom': {
        'density_kg_m3': (1410.0, 'kg/m3', TB),
        'youngs_modulus_gpa': (2.9, 'GPa', TB),
        'poisson_ratio': (0.35, '', TB),
        'yield_mpa': (65.0, 'MPa', TB),
        'tensile_mpa': (70.0, 'MPa', TB),
        'hardness_shore_d': (85.0, 'Shore D', TB, 'Rockwell M ~94'),
        'friction_coefficient': (0.25, '', TB, 'against steel dry 0.2-0.35'),
        'friction_json': ({
            'steel_carbon': _f(0.3, 0.25, TB, 'dry'),
            'al_6063': _f(0.3, 0.25, TB, 'V-wheel on extrusion; a knob'),
        }, '', TB),
    },
    'abs': {
        'density_kg_m3': (1050.0, 'kg/m3', TB),
        'youngs_modulus_gpa': (2.2, 'GPa', TB),
        'poisson_ratio': (0.35, '', TB),
        'yield_mpa': (40.0, 'MPa', TB),
        'tensile_mpa': (42.0, 'MPa', TB),
        'hardness_rockwell_r': (105.0, 'Rockwell R', TB),
    },
    'pc_bpa': {
        'density_kg_m3': (1200.0, 'kg/m3', TB),
        'youngs_modulus_gpa': (2.3, 'GPa', TB),
        'poisson_ratio': (0.37, '', TB),
        'yield_mpa': (62.0, 'MPa', TB),
        'tensile_mpa': (65.0, 'MPa', TB),
        'hardness_rockwell_r': (118.0, 'Rockwell R', TB, 'Rockwell M ~70'),
    },
    'pvc': {
        'density_kg_m3': (1400.0, 'kg/m3', TB, 'rigid'),
        'youngs_modulus_gpa': (3.0, 'GPa', TB, 'rigid'),
        'poisson_ratio': (0.38, '', TB),
        'yield_mpa': (50.0, 'MPa', TB, 'rigid'),
        'tensile_mpa': (52.0, 'MPa', TB, 'rigid'),
        'hardness_shore_d': (80.0, 'Shore D', TB, 'rigid'),
    },
    'ptfe': {
        'density_kg_m3': (2170.0, 'kg/m3', TB),
        'youngs_modulus_gpa': (0.5, 'GPa', TB),
        'poisson_ratio': (0.46, '', TB),
        'yield_mpa': (12.0, 'MPa', TB),
        'tensile_mpa': (25.0, 'MPa', TB),
        'hardness_shore_d': (55.0, 'Shore D', TB),
        'friction_coefficient': (0.05, '', PK,
                                 'against steel: plan knob PTFE 0.04-0.1'),
        'friction_json': ({
            'steel_carbon': _f(0.05, 0.05, PK, 'PTFE 0.04-0.1'),
            'stainless_a2_a4': _f(0.05, 0.05, PK, 'PTFE 0.04-0.1'),
            'al_6063': _f(0.06, 0.05, PK, 'PTFE 0.04-0.1'),
            'ptfe': _f(0.04, 0.04, TB, 'self-mated'),
        }, '', TB),
    },
    # ---------------- elastomers ----------------
    'tpu_mdi': {
        'density_kg_m3': (1210.0, 'kg/m3', TB, 'Shore 95A grade'),
        'youngs_modulus_gpa': (0.05, 'GPa', TB, 'Shore 95A; 85A ~0.02'),
        'poisson_ratio': (0.48, '', TB),
        'yield_mpa': (-1, 'MPa', TB, 'no yield point'),
        'tensile_mpa': (40.0, 'MPa', TB, 'Shore 95A, at break'),
        'hardness_shore_a': (95.0, 'Shore A', TB),
        'friction_coefficient': (0.6, '', TB, 'against aluminium/steel dry; '
                                              'a knob'),
        'friction_json': ({
            'al_6061': _f(0.8, 0.6, TB, 'belt on pulley; a knob'),
            'steel_carbon': _f(0.8, 0.6, TB, 'a knob'),
        }, '', TB),
    },
    'tpc_et': {
        'density_kg_m3': (1200.0, 'kg/m3', TB, 'Shore 40D grade'),
        'youngs_modulus_gpa': (0.1, 'GPa', TB, 'Shore 40D'),
        'poisson_ratio': (0.45, '', TB),
        'yield_mpa': (-1, 'MPa', TB, 'no sharp yield'),
        'tensile_mpa': (30.0, 'MPa', TB),
        'hardness_shore_d': (40.0, 'Shore D', TB),
        'friction_coefficient': (0.5, '', TB, 'against steel dry; a knob'),
        'friction_json': ({'steel_carbon': _f(0.7, 0.5, TB, 'a knob')},
                          '', TB),
    },
    'epdm_peroxide': {
        'density_kg_m3': (1100.0, 'kg/m3', TB, 'compound'),
        'youngs_modulus_gpa': (0.006, 'GPa', TB, 'Shore 70A ~5-6 MPa'),
        'poisson_ratio': (0.49, '', TB),
        'yield_mpa': (-1, 'MPa', TB, 'no yield point'),
        'tensile_mpa': (15.0, 'MPa', TB, 'compound, at break'),
        'hardness_shore_a': (70.0, 'Shore A', TB),
        'friction_coefficient': (0.7, '', TB, 'against steel dry 0.6-0.9'),
        'friction_json': ({
            'steel_carbon': _f(0.9, 0.7, TB, 'dry'),
            'stainless_a2_a4': _f(0.9, 0.7, TB, 'dry'),
            'al_6063': _f(0.9, 0.7, TB, 'dry; a knob'),
        }, '', TB),
    },
    'cm': {
        'density_kg_m3': (1250.0, 'kg/m3', TB),
        'tensile_mpa': (15.0, 'MPa', TB),
        'hardness_shore_a': (70.0, 'Shore A', TB),
    },
    'natural_rubber': {
        'density_kg_m3': (1100.0, 'kg/m3', TB, 'compound; gum 930'),
        'youngs_modulus_gpa': (0.004, 'GPa', TB, 'Shore 60A'),
        'poisson_ratio': (0.49, '', TB),
        'yield_mpa': (-1, 'MPa', TB, 'no yield point'),
        'tensile_mpa': (25.0, 'MPa', TB),
        'hardness_shore_a': (60.0, 'Shore A', TB),
        'friction_coefficient': (0.8, '', TB, 'against steel dry; a knob'),
        'friction_json': ({'steel_carbon': _f(1.0, 0.8, TB, 'dry; a knob'),
                           'birch_plywood': _f(0.8, 0.6, TB, 'foot pad on '
                                                            'floor; a knob')},
                          '', TB),
    },
    'silicone_vmq': {
        'density_kg_m3': (1150.0, 'kg/m3', TB),
        'youngs_modulus_gpa': (0.003, 'GPa', TB, 'Shore 60A'),
        'poisson_ratio': (0.48, '', TB),
        'tensile_mpa': (8.0, 'MPa', TB),
        'hardness_shore_a': (60.0, 'Shore A', TB),
        'friction_coefficient': (0.6, '', TB, 'against steel dry; a knob'),
        'friction_json': ({'steel_carbon': _f(0.8, 0.6, TB, 'a knob')},
                          '', TB),
    },
    'aem': {
        'density_kg_m3': (1100.0, 'kg/m3', TB),
        'tensile_mpa': (14.0, 'MPa', TB),
        'hardness_shore_a': (65.0, 'Shore A', TB),
        'friction_coefficient': (0.6, '', TB, 'against steel dry; a knob'),
        'friction_json': ({'steel_carbon': _f(0.8, 0.6, TB, 'a knob')},
                          '', TB),
    },
    'neoprene_cr': {
        'density_kg_m3': (1230.0, 'kg/m3', TB),
        'youngs_modulus_gpa': (0.004, 'GPa', TB, 'Shore 60A'),
        'poisson_ratio': (0.49, '', TB),
        'tensile_mpa': (20.0, 'MPa', TB),
        'hardness_shore_a': (60.0, 'Shore A', TB),
        'friction_coefficient': (0.7, '', TB, 'against steel dry; a knob'),
        'friction_json': ({'steel_carbon': _f(0.9, 0.7, TB, 'a knob')},
                          '', TB),
    },
    'sbr': {
        'density_kg_m3': (1100.0, 'kg/m3', TB, 'compound; gum 940'),
        'tensile_mpa': (20.0, 'MPa', TB),
        'hardness_shore_a': (65.0, 'Shore A', TB),
    },
    'nbr_hnbr': {
        'density_kg_m3': (1000.0, 'kg/m3', TB),
        'tensile_mpa': (20.0, 'MPa', TB),
        'hardness_shore_a': (70.0, 'Shore A', TB),
        'friction_coefficient': (0.7, '', TB, 'against steel dry; a knob'),
        'friction_json': ({'steel_carbon': _f(0.9, 0.7, TB, 'a knob')},
                          '', TB),
    },
    'acm': {
        'density_kg_m3': (1100.0, 'kg/m3', TB),
        'tensile_mpa': (12.0, 'MPa', TB),
        'hardness_shore_a': (65.0, 'Shore A', TB),
    },
    'sebs_sbs': {
        'density_kg_m3': (900.0, 'kg/m3', TB),
        'tensile_mpa': (15.0, 'MPa', TB),
        'hardness_shore_a': (50.0, 'Shore A', TB),
    },
    'tpu_tdi': {
        'density_kg_m3': (1200.0, 'kg/m3', TB),
        'tensile_mpa': (35.0, 'MPa', TB),
        'hardness_shore_a': (90.0, 'Shore A', TB),
    },
    'fkm': {
        'density_kg_m3': (1850.0, 'kg/m3', TB),
        'tensile_mpa': (12.0, 'MPa', TB),
        'hardness_shore_a': (75.0, 'Shore A', TB),
        'friction_coefficient': (0.6, '', TB, 'against steel dry; a knob'),
        'friction_json': ({'steel_carbon': _f(0.8, 0.6, TB, 'a knob')},
                          '', TB),
    },
    # ---------------- wood ----------------
    'birch_plywood': {
        'density_kg_m3': (680.0, 'kg/m3', TB, 'Baltic birch'),
        'youngs_modulus_gpa': (10.0, 'GPa', TB,
                               'parallel to face grain; ~7 perpendicular'),
        'poisson_ratio': (0.3, '', TB, 'in-plane, approximate'),
        'yield_mpa': (-1, 'MPa', TB, 'no yield point; use bending strength'),
        'tensile_mpa': (40.0, 'MPa', TB, 'parallel to face grain'),
        'bending_strength_mpa': (60.0, 'MPa', TB, 'parallel to face grain'),
        'friction_coefficient': (0.35, '', PK,
                                 'against birch_plywood, dry: plan knob '
                                 'wood-on-wood 0.25-0.5, midpoint'),
        'friction_json': ({
            'birch_plywood': _f(0.5, 0.35, PK, 'wood-on-wood 0.25-0.5'),
            'mdf': _f(0.5, 0.35, PK, 'wood-on-wood 0.25-0.5'),
            'uhmwpe': _f(0.25, 0.2, TB, 'a knob'),
            'steel_carbon': _f(0.5, 0.35, TB, 'wood on metal dry'),
            'al_6063': _f(0.4, 0.3, TB, 'wood on metal dry'),
        }, '', TB),
    },
    'mdf': {
        'density_kg_m3': (750.0, 'kg/m3', TB),
        'youngs_modulus_gpa': (3.5, 'GPa', TB),
        'poisson_ratio': (0.25, '', TB, 'approximate'),
        'yield_mpa': (-1, 'MPa', TB, 'no yield point'),
        'tensile_mpa': (18.0, 'MPa', TB),
        'bending_strength_mpa': (30.0, 'MPa', TB),
        'friction_coefficient': (0.35, '', PK,
                                 'against wood, dry: plan knob 0.25-0.5'),
        'friction_json': ({
            'mdf': _f(0.5, 0.35, PK, 'wood-on-wood 0.25-0.5'),
            'birch_plywood': _f(0.5, 0.35, PK, 'wood-on-wood 0.25-0.5'),
        }, '', TB),
    },
    # ---------------- coatings (surface values; the substrate carries the bulk) ----------------
    'zinc_trivalent': {
        'density_kg_m3': (7140.0, 'kg/m3', TB, 'zinc layer'),
        'hardness_hv': (50.0, 'HV', TB, 'electroplated zinc 40-60'),
    },
    'black_oxide': {},
    'anodise': {
        'hardness_hv': (350.0, 'HV', TB, 'Type II 300-400; Type III hard 400-600'),
    },
    'nitriding': {
        'hardness_hv': (900.0, 'HV', TB, 'nitrided case 700-1100'),
    },
    'nickel_plating': {
        'density_kg_m3': (8900.0, 'kg/m3', TB, 'nickel layer'),
        'hardness_hv': (500.0, 'HV', TB, 'electroless Ni as plated 450-550'),
    },
    'zinc_hexavalent': {
        'density_kg_m3': (7140.0, 'kg/m3', TB, 'zinc layer'),
        'hardness_hv': (50.0, 'HV', TB),
    },
    'hard_chrome': {
        'density_kg_m3': (7190.0, 'kg/m3', TB, 'chromium layer'),
        'hardness_hv': (950.0, 'HV', TB, '850-1050'),
    },
    'cadmium_plating': {
        'density_kg_m3': (8650.0, 'kg/m3', TB, 'cadmium layer'),
        'hardness_hv': (40.0, 'HV', TB, '30-50'),
    },
    # ---------------- additives ----------------
    'carbon_black': {
        'density_kg_m3': (1800.0, 'kg/m3', TB),
    },
}
