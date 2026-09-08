"""
@module gears.gear_seed

gr-1 seeds: the GEAR TYPE TAXONOMY (GEARS_PLAN §2) as rows, plus two
hand-checkable sample trains.

Efficiency bands are LITERATURE PRIORS with both ends stated — a
report may never quietly pick the flattering end, and the worm row
(0.30-0.90) exists precisely because that spread decides whether a
design is sane. Every type also states how it would be MADE in our
stack: a gear we cannot mold, print or cut is a simulation toy.

@consumers polariServer (seed_pairs), gears.gears_selftest
"""

PROV = 'gr-1'

SEED_GEAR_TYPES = [
    {
        'name': 'spur',
        'display_name': 'Spur gear (straight teeth, parallel axes)',
        'description': 'The default. Straight teeth on parallel '
                       'shafts: no thrust, simplest geometry, and '
                       'the only type that is genuinely easy to '
                       'cast — a 2.5D shape a wax mold pulls '
                       'straight out of.',
        'axis_relation': 'parallel',
        'ratio_law': 'n_driven / n_driving',
        'efficiency_prior_min': 0.96, 'efficiency_prior_max': 0.99,
        'reverses_direction': True, 'profile_family': 'involute',
        'geometry_generator': 'involute-spur',
        'produces_thrust': False, 'can_self_lock': False,
        'makeability_note': 'EASIEST in our stack: flat 2.5D, '
                            'wax-printed mold -> cast geopolymer, '
                            'T0 viable (backlash large but a '
                            'reduction drive tolerates it).',
        'tolerance_tier_min': 'T0',
        'is_prior': True, 'provenance_id': PROV, 'notes': '',
    },
    {
        'name': 'helical',
        'display_name': 'Helical gear (angled teeth, parallel axes)',
        'description': 'Teeth cut on a helix: more than one tooth '
                       'pair in contact at a time, so quieter and '
                       'higher load capacity — paid for with axial '
                       'THRUST that the bearings must take.',
        'axis_relation': 'parallel',
        'ratio_law': 'n_driven / n_driving',
        'efficiency_prior_min': 0.94, 'efficiency_prior_max': 0.98,
        'reverses_direction': True, 'profile_family': 'involute',
        'geometry_generator': '',
        'produces_thrust': True, 'can_self_lock': False,
        'makeability_note': 'Castable but the mold must TWIST to '
                            'release (or split) — a real T1 step '
                            'up from spur. Thrust means the shaft '
                            'needs a bearing that takes axial load.',
        'tolerance_tier_min': 'T1',
        'is_prior': True, 'provenance_id': PROV,
        'notes': 'geometry generator NOT built (gr-3 follow-up) — '
                 'the abstract sim runs, the 3D view refuses.',
    },
    {
        'name': 'internal',
        'display_name': 'Internal (ring) gear',
        'description': 'Teeth on the INSIDE of a ring. The mesh '
                       'does NOT reverse direction and the centre '
                       'distance is a DIFFERENCE of pitch radii — '
                       'both are classic silent-bug sources, so '
                       'both are row fields here.',
        'axis_relation': 'parallel',
        'ratio_law': 'n_driven / n_driving (same direction)',
        'efficiency_prior_min': 0.96, 'efficiency_prior_max': 0.99,
        'reverses_direction': False, 'profile_family': 'involute',
        'geometry_generator': '',
        'produces_thrust': False, 'can_self_lock': False,
        'makeability_note': 'Moldable, but the inner tooth cavity '
                            'is the hard pull — the wax mold '
                            'becomes the sacrificial pattern '
                            '(mold-1 rules apply).',
        'tolerance_tier_min': 'T1',
        'is_prior': True, 'provenance_id': PROV,
        'notes': 'The planetary prerequisite.',
    },
    {
        'name': 'planetary',
        'display_name': 'Planetary (epicyclic) set',
        'description': 'Sun + planets on a carrier + ring. High '
                       'ratio in a short COAXIAL envelope with the '
                       'load shared over several planets. Which '
                       'member is held decides the ratio — that '
                       'table is data (gr-6), not a formula buried '
                       'in code.',
        'axis_relation': 'coaxial',
        'ratio_law': 'ring fixed: 1 + N_ring/N_sun (carrier out); '
                     'carrier fixed: -N_ring/N_sun; '
                     'sun fixed: 1 + N_sun/N_ring',
        'efficiency_prior_min': 0.95, 'efficiency_prior_max': 0.98,
        'reverses_direction': False, 'profile_family': 'involute',
        'geometry_generator': '',
        'produces_thrust': False, 'can_self_lock': False,
        'makeability_note': 'The flagship hard case: a carrier plus '
                            '3 planets that must MATCH each other '
                            'in tooth spacing — mismatch means one '
                            'planet carries everything. Cast T0 is '
                            'optimistic; this wants T2/T3.',
        'tolerance_tier_min': 'T2',
        'is_prior': True, 'provenance_id': PROV,
        'notes': 'gr-6: the ratio TABLE lands as rows; the solver '
                 'refuses planetary chaining until then.',
    },
    {
        'name': 'bevel-straight',
        'display_name': 'Straight bevel gear (intersecting axes)',
        'description': 'Turns the axis, usually 90 degrees. Teeth '
                       'on a cone.',
        'axis_relation': 'intersecting',
        'ratio_law': 'n_driven / n_driving',
        'efficiency_prior_min': 0.93, 'efficiency_prior_max': 0.97,
        'reverses_direction': True, 'profile_family': 'involute',
        'geometry_generator': '',
        'produces_thrust': True, 'can_self_lock': False,
        'makeability_note': 'Conical mold, harder pull than spur; '
                            'tooth height varies along the cone so '
                            'a cast T0 part meshes unevenly.',
        'tolerance_tier_min': 'T1',
        'is_prior': True, 'provenance_id': PROV, 'notes': '',
    },
    {
        'name': 'worm',
        'display_name': 'Worm + worm wheel (skew 90 degrees)',
        'description': 'A screw driving a wheel: enormous single-'
                       'stage reduction, and possibly SELF-LOCKING '
                       '(the load cannot back-drive it). Efficiency '
                       'is the catch — it spans 0.30 to 0.90 with '
                       'lead angle and friction, so the band is '
                       'wide ON PURPOSE.',
        'axis_relation': 'skew',
        'ratio_law': 'n_wheel / starts',
        'efficiency_prior_min': 0.30, 'efficiency_prior_max': 0.90,
        'reverses_direction': False, 'profile_family': 'involute',
        'geometry_generator': '',
        'produces_thrust': True, 'can_self_lock': True,
        'makeability_note': 'The worm is a SCREW — hardest thing '
                            'here to cast, easiest to BUY. Honest '
                            'answer for v1: buy the worm, cast the '
                            'wheel.',
        'tolerance_tier_min': 'T2',
        'is_prior': True, 'provenance_id': PROV,
        'notes': 'Self-locking is DERIVED (tan(lead) vs friction '
                 'coefficient) and our cast composites have no '
                 'measured friction pair data — the solve answers '
                 '"unassessed" with the ask, never "no".',
    },
    {
        'name': 'rack-pinion',
        'display_name': 'Rack + pinion (rotary to linear)',
        'description': 'A pinion rolling on a straight rack: '
                       'rotation becomes travel. Output is a '
                       'VELOCITY and a FORCE, not a speed and a '
                       'torque — the report must not print RPM for '
                       'a rack.',
        'axis_relation': 'rotary-linear',
        'ratio_law': 'v = omega * r_pitch; F = T / r_pitch',
        'efficiency_prior_min': 0.90, 'efficiency_prior_max': 0.98,
        'reverses_direction': False, 'profile_family': 'involute',
        'geometry_generator': '',
        'produces_thrust': False, 'can_self_lock': False,
        'makeability_note': 'A flat rack casts WELL (straight pull, '
                            'no curvature) — the accessible half of '
                            'a linear actuator; the BLCNC/tower '
                            'seam.',
        'tolerance_tier_min': 'T0',
        'is_prior': True, 'provenance_id': PROV, 'notes': '',
    },
    {
        'name': 'cycloidal',
        'display_name': 'Cycloidal drive (eccentric lobes + pins)',
        'description': 'A lobed disc wobbling against a pin ring: '
                       'very high ratio, high shock tolerance, and '
                       'ROLLING rather than sliding contact — which '
                       'is genuinely interesting for brittle cast '
                       'materials that hate point loads.',
        'axis_relation': 'coaxial',
        'ratio_law': '(n_pins - n_lobes) / n_lobes',
        'efficiency_prior_min': 0.85, 'efficiency_prior_max': 0.95,
        'reverses_direction': True, 'profile_family': 'cycloidal',
        'geometry_generator': '',
        'produces_thrust': False, 'can_self_lock': False,
        'makeability_note': 'No involute teeth to get right — the '
                            'lobe curve is a smooth cast shape and '
                            'the pins are dowels. Plausibly the '
                            'BEST high-ratio type for our cast '
                            'stack; unproven, so it is a candidate, '
                            'not a claim.',
        'tolerance_tier_min': 'T1',
        'is_prior': True, 'provenance_id': PROV,
        'notes': 'gr-6 candidate worth real attention.',
    },
]

# ------------------------------------------------------------------ #
# Sample trains. Numbers are HAND-CHECKABLE and pinned in the
# selftest — the two-stage reduction below is exactly 3:1 x 4:1.
# ------------------------------------------------------------------ #

SEED_GEAR_TRAINS = [
    {
        'name': 'two-stage-spur-demo',
        'display_name': 'Two-stage spur reduction (12:1) — the '
                        'hand-checkable case',
        'description': 'Motor shaft -> 3:1 -> compound shaft -> '
                       '4:1 -> output. Every number here is worked '
                       'by hand in the selftest: ratio 12, two '
                       'direction reversals (so output turns the '
                       'SAME way as input), efficiency 0.975^2.',
        'input_shaft': 'shaft-in', 'output_shaft': 'shaft-out',
        'input_torque_nm': 0.01, 'input_speed_rpm': 600.0,
        'motor_design_ref': '', 'tolerance_tier': 'T0',
        'is_prior': True, 'provenance_id': PROV,
        'notes': 'Input drive stated directly (0.01 Nm at 600 rpm '
                 '~ a small hobby motor); the gr-5 splice replaces '
                 'it with a real motor curve.',
    },
    {
        'name': 'clock-train-m0',
        'display_name': 'M0 clock reduction — seconds to minutes '
                        'to hours',
        'description': 'The Lavet stepper (1 step/second, 180 deg '
                       'per step = 0.5 rev/s at the rotor) driving '
                       'the real clock reduction. THE acceptance '
                       'case: the output shaft must turn once per '
                       'hour, verified against time itself — the '
                       'same trick that made M0 the motor control '
                       'case.',
        'input_shaft': 'shaft-rotor', 'output_shaft': 'shaft-minute',
        'input_torque_nm': 1e-6, 'input_speed_rpm': 30.0,
        'motor_design_ref': 'clock-lavet-m0', 'tolerance_tier': 'T0',
        'is_prior': True, 'provenance_id': PROV,
        'notes': 'Rotor 0.5 rev/s = 30 rpm; the seconds hand turns '
                 'at 1 rpm (30:1) and the minute hand at 1/60 rpm '
                 '(60:1 more). Hour hand = gr-5 extension.',
    },
]

SEED_SHAFT_NODES = [
    {'name': 'demo-shaft-in', 'train_ref': 'two-stage-spur-demo',
     'shaft': 'shaft-in', 'is_input': True, 'is_output': False,
     'is_fixed': False, 'bearing_item_ref': 'bearing-608',
     'description': 'Driven shaft (motor side).',
     'is_prior': True, 'provenance_id': PROV, 'notes': ''},
    {'name': 'demo-shaft-mid', 'train_ref': 'two-stage-spur-demo',
     'shaft': 'shaft-mid', 'is_input': False, 'is_output': False,
     'is_fixed': False, 'bearing_item_ref': 'bearing-608',
     'description': 'Compound shaft: TWO gears ride it, so they '
                    'share one speed — that is what makes the '
                    'stages multiply.',
     'is_prior': True, 'provenance_id': PROV, 'notes': ''},
    {'name': 'demo-shaft-out', 'train_ref': 'two-stage-spur-demo',
     'shaft': 'shaft-out', 'is_input': False, 'is_output': True,
     'is_fixed': False, 'bearing_item_ref': 'bearing-608',
     'description': 'Output shaft.',
     'is_prior': True, 'provenance_id': PROV, 'notes': ''},
    {'name': 'clock-shaft-rotor', 'train_ref': 'clock-train-m0',
     'shaft': 'shaft-rotor', 'is_input': True, 'is_output': False,
     'is_fixed': False, 'bearing_item_ref': '',
     'description': 'The Lavet rotor itself (30 rpm).',
     'is_prior': True, 'provenance_id': PROV, 'notes': ''},
    {'name': 'clock-shaft-second', 'train_ref': 'clock-train-m0',
     'shaft': 'shaft-second', 'is_input': False, 'is_output': False,
     'is_fixed': False, 'bearing_item_ref': '',
     'description': 'Seconds hand: must land at exactly 1 rpm.',
     'is_prior': True, 'provenance_id': PROV, 'notes': ''},
    {'name': 'clock-shaft-minute', 'train_ref': 'clock-train-m0',
     'shaft': 'shaft-minute', 'is_input': False, 'is_output': True,
     'is_fixed': False, 'bearing_item_ref': '',
     'description': 'Minute hand: 1 turn per hour = 1/60 rpm.',
     'is_prior': True, 'provenance_id': PROV, 'notes': ''},
]

#: Module 1.0 mm throughout the demo (a size a wax printer can
#: actually resolve); the clock train uses 0.3 mm module, which is
#: FLAGGED in gr-2 as below what our cast tolerance can hold — an
#: honest "buy this one" pointer, exactly like the worm.
SEED_GEARS = [
    # --- two-stage spur demo: 3:1 then 4:1 ---
    {'name': 'demo-pinion-a', 'display_name': 'Stage 1 pinion (12t)',
     'train_ref': 'two-stage-spur-demo', 'gear_type_ref': 'spur',
     'teeth': 12, 'module_mm': 1.0, 'face_width_mm': 6.0,
     'pressure_angle_deg': 20.0, 'shaft_ref': 'shaft-in',
     'material_ref': 'geopolymer-mix', 'backlash_mm_prior': 0.15,
     'is_input': True, 'is_output': False,
     'is_prior': True, 'provenance_id': PROV, 'notes': ''},
    {'name': 'demo-wheel-a', 'display_name': 'Stage 1 wheel (36t)',
     'train_ref': 'two-stage-spur-demo', 'gear_type_ref': 'spur',
     'teeth': 36, 'module_mm': 1.0, 'face_width_mm': 6.0,
     'pressure_angle_deg': 20.0, 'shaft_ref': 'shaft-mid',
     'material_ref': 'geopolymer-mix', 'backlash_mm_prior': 0.15,
     'is_input': False, 'is_output': False,
     'is_prior': True, 'provenance_id': PROV, 'notes': ''},
    {'name': 'demo-pinion-b', 'display_name': 'Stage 2 pinion (12t)',
     'train_ref': 'two-stage-spur-demo', 'gear_type_ref': 'spur',
     'teeth': 12, 'module_mm': 1.0, 'face_width_mm': 6.0,
     'pressure_angle_deg': 20.0, 'shaft_ref': 'shaft-mid',
     'material_ref': 'geopolymer-mix', 'backlash_mm_prior': 0.15,
     'is_input': False, 'is_output': False,
     'is_prior': True, 'provenance_id': PROV,
     'notes': 'Shares shaft-mid with the stage-1 wheel — the '
              'compound.'},
    {'name': 'demo-wheel-b', 'display_name': 'Stage 2 wheel (48t)',
     'train_ref': 'two-stage-spur-demo', 'gear_type_ref': 'spur',
     'teeth': 48, 'module_mm': 1.0, 'face_width_mm': 6.0,
     'pressure_angle_deg': 20.0, 'shaft_ref': 'shaft-out',
     'material_ref': 'geopolymer-mix', 'backlash_mm_prior': 0.15,
     'is_input': False, 'is_output': True,
     'is_prior': True, 'provenance_id': PROV, 'notes': ''},
    # --- clock train: 30:1 then 60:1 ---
    {'name': 'clock-rotor-pinion',
     'display_name': 'Rotor pinion (8t)',
     'train_ref': 'clock-train-m0', 'gear_type_ref': 'spur',
     'teeth': 8, 'module_mm': 0.3, 'face_width_mm': 1.0,
     'pressure_angle_deg': 20.0, 'shaft_ref': 'shaft-rotor',
     'material_ref': 'geopolymer-mix', 'backlash_mm_prior': 0.05,
     'is_input': True, 'is_output': False,
     'is_prior': True, 'provenance_id': PROV, 'notes': ''},
    {'name': 'clock-second-wheel',
     'display_name': 'Seconds wheel (240t)',
     'train_ref': 'clock-train-m0', 'gear_type_ref': 'spur',
     'teeth': 240, 'module_mm': 0.3, 'face_width_mm': 1.0,
     'pressure_angle_deg': 20.0, 'shaft_ref': 'shaft-second',
     'material_ref': 'geopolymer-mix', 'backlash_mm_prior': 0.05,
     'is_input': False, 'is_output': False,
     'is_prior': True, 'provenance_id': PROV,
     'notes': '8 -> 240 = 30:1, taking the 30 rpm rotor to exactly '
              '1 rpm: the seconds hand.'},
    {'name': 'clock-second-pinion',
     'display_name': 'Seconds pinion (10t)',
     'train_ref': 'clock-train-m0', 'gear_type_ref': 'spur',
     'teeth': 10, 'module_mm': 0.3, 'face_width_mm': 1.0,
     'pressure_angle_deg': 20.0, 'shaft_ref': 'shaft-second',
     'material_ref': 'geopolymer-mix', 'backlash_mm_prior': 0.05,
     'is_input': False, 'is_output': False,
     'is_prior': True, 'provenance_id': PROV, 'notes': ''},
    {'name': 'clock-minute-wheel',
     'display_name': 'Minute wheel (600t)',
     'train_ref': 'clock-train-m0', 'gear_type_ref': 'spur',
     'teeth': 600, 'module_mm': 0.3, 'face_width_mm': 1.0,
     'pressure_angle_deg': 20.0, 'shaft_ref': 'shaft-minute',
     'material_ref': 'geopolymer-mix', 'backlash_mm_prior': 0.05,
     'is_input': False, 'is_output': True,
     'is_prior': True, 'provenance_id': PROV,
     'notes': '10 -> 600 = 60:1 more, so the minute hand turns '
              'once per hour. A 600-tooth 0.3-module wheel is 180 '
              'mm across — REAL clocks use several smaller stages; '
              'this seed keeps the arithmetic legible and gr-2 '
              'flags the size.'},
]

SEED_GEAR_MESHES = [
    {'name': 'demo-mesh-1', 'train_ref': 'two-stage-spur-demo',
     'driving_gear_ref': 'demo-pinion-a',
     'driven_gear_ref': 'demo-wheel-a',
     'efficiency_override': 0.975,
     'center_distance_mm_override': None, 'is_internal': False,
     'is_prior': True, 'provenance_id': PROV,
     'notes': 'Efficiency pinned mid-band so the selftest math is '
              'exact; a measured run replaces it.'},
    {'name': 'demo-mesh-2', 'train_ref': 'two-stage-spur-demo',
     'driving_gear_ref': 'demo-pinion-b',
     'driven_gear_ref': 'demo-wheel-b',
     'efficiency_override': 0.975,
     'center_distance_mm_override': None, 'is_internal': False,
     'is_prior': True, 'provenance_id': PROV, 'notes': ''},
    {'name': 'clock-mesh-1', 'train_ref': 'clock-train-m0',
     'driving_gear_ref': 'clock-rotor-pinion',
     'driven_gear_ref': 'clock-second-wheel',
     'efficiency_override': None,
     'center_distance_mm_override': None, 'is_internal': False,
     'is_prior': True, 'provenance_id': PROV,
     'notes': 'No override: the type prior band midpoint is used '
              'and FLAGGED as a prior.'},
    {'name': 'clock-mesh-2', 'train_ref': 'clock-train-m0',
     'driving_gear_ref': 'clock-second-pinion',
     'driven_gear_ref': 'clock-minute-wheel',
     'efficiency_override': None,
     'center_distance_mm_override': None, 'is_internal': False,
     'is_prior': True, 'provenance_id': PROV, 'notes': ''},
]
