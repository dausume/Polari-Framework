"""
@module gears.gear_scene

gr-4 (Dustin 2026-08-01): "make the gear assembly isolatable and
renderable separate from the motor — the driving gear is the only
piece visible from the motor portion, but we will be able to see
all of the math defined gears moving."

THE SCENE: 'gear-train-m0-viz' — its OWN SimSpaceDefinition, not a
layer on the motor. The only body shared with the motor is the
DRIVING pinion (the rotor's gear); every wheel after it is a
family-'gear' MathShapeDefinition with real involute teeth, placed
at the SOLVED centre distances ((z1+z2)·m/2 — the same numbers
gear_kinematics derives), stacked in mesh planes like a movement.

THE MOTION: gear_scene_replay reads solve_train's signed shaft
speeds — the same solve the duty checks use — and emits per-body
rotation rates. The display runs TIME-SCALED (a 1/60 rpm minute
wheel is honest but invisible); the scale is a knob and the payload
names it, so the picture is a kinematic replay of the solved
ratios, never an animation someone drew.

TWO-MODULES-AGREE guard: the gear SHAPES restate teeth/module from
the GearDefinition rows (geometry needs them at seed time); the
selftest pins shape == gear row for every pair, so the drawn train
and the solved train cannot drift apart silently.

@consumers motors.clock_scene (the gear-replay layer),
polariServer seed pass (GearSceneSeed, upsert),
gears.selftest_gears
"""

import json

from composition.seed_upsert import upsert_seed_pairs

PROV = 'gr-4'
TRAIN = 'clock-train-m0'
MODULE_MM = 0.3

#: Shaft x-positions from the solved centre distances:
#: rotor at 0; seconds shaft (8+240)m/2 = 37.2 away; minute shaft
#: (10+600)m/2 = 91.5 beyond that.
SHAFT_X = {'shaft-rotor': 0.0, 'shaft-second': 37.2,
           'shaft-minute': 128.7}

#: body id -> (shape row, shaft, mesh plane z)
TRAIN_BODIES = {
    'driving-pinion': ('clock-gear-rotor-pinion', 'shaft-rotor',
                       0.0),
    'second-wheel': ('clock-gear-second-wheel', 'shaft-second',
                     0.0),
    'second-pinion': ('clock-gear-second-pinion', 'shaft-second',
                      1.4),
    'minute-wheel': ('clock-gear-minute-wheel', 'shaft-minute',
                     1.4),
    # as-2: the HANDS ride their shafts — they are what the whole
    # machine exists to move, so they rotate in the same replay.
    'second-hand': ('clock-hand-second', 'shaft-second', 2.6),
    'minute-hand': ('clock-hand-minute', 'shaft-minute', 3.1),
}

#: as-2: hand orientation VECTORS — each hand carries an arrow at
#: its shaft showing where it points (the rotor-orientation idiom).
HAND_VECTORS = [
    {'key': 'vec-second-hand', 'body': 'second-hand',
     'origin': [37.2, 0.0, 3.2], 'length': 85.0,
     'color': '#d33340'},
    {'key': 'vec-minute-hand', 'body': 'minute-hand',
     'origin': [128.7, 0.0, 3.7], 'length': 70.0,
     'color': '#5b7fd4'},
]


def _gear_shape(name, teeth, center, *, shift=0.0, addendum=1.0,
                bore, flank_samples=None, note=''):
    params = {'module': MODULE_MM, 'teeth': teeth,
              'pressure_angle_deg': 20.0,
              'profile_shift': shift, 'addendum_coeff': addendum,
              'face_width': 1.0, 'bore_radius': bore,
              'center': center, 'axis': 'z'}
    if flank_samples:
        params['flank_samples'] = flank_samples
    return {'name': name,
            'display_name': f'{teeth}t clock gear ({name})',
            'family': 'gear',
            'parameters_json': json.dumps(params),
            'notes': note, 'provenance_id': PROV}


SEED_TRAIN_GEAR_SHAPES = [
    _gear_shape('clock-gear-rotor-pinion', 8,
                [SHAFT_X['shaft-rotor'], 0.0, 0.0],
                shift=0.55, addendum=0.6, bore=0.25,
                note='THE motor piece: the rotor pinion, and the '
                     'only body this scene shares with the motor '
                     'scene. Same tooth math as '
                     'motor-m0v2-pinion-gear.'),
    _gear_shape('clock-gear-second-wheel', 240,
                [SHAFT_X['shaft-second'], 0.0, 0.0],
                bore=1.0, flank_samples=2,
                note='8->240 = 30:1 — the 30 rpm rotor lands at '
                     'exactly 1 rpm.'),
    _gear_shape('clock-gear-second-pinion', 10,
                [SHAFT_X['shaft-second'], 0.0, 1.4],
                shift=0.45, addendum=0.7, bore=0.5,
                note='Rides the seconds shaft (same speed as the '
                     'wheel) in the upper mesh plane.'),
    _gear_shape('clock-gear-minute-wheel', 600,
                [SHAFT_X['shaft-minute'], 0.0, 1.4],
                bore=1.0, flank_samples=2,
                note='10->600 = 60:1 more: once per hour. 180 mm '
                     'across — the size finding of gr-6, drawn.'),
]

#: as-1/2: the hands as geometry — thin boxes reaching from their
#: shaft with a short counter-tail, in planes above the wheels.
#: Real parts: the clock_assembly bill derives their MASS from
#: these very shapes.
SEED_HAND_SHAPES = [
    {'name': 'clock-hand-second',
     'display_name': 'Seconds hand (95 mm, thin)',
     'family': 'primitive', 'primitive_kind': 'box',
     'parameters_json': json.dumps(
         {'size': [1.4, 95.0, 0.5],
          'center': [SHAFT_X['shaft-second'], 37.5, 2.6]}),
     'notes': 'Extends -10..+85 about the seconds shaft (10 mm '
              'counter-tail). Mass and imbalance derive from this '
              'geometry in the assembly bill.',
     'provenance_id': 'as-2'},
    {'name': 'clock-hand-minute',
     'display_name': 'Minute hand (80 mm)',
     'family': 'primitive', 'primitive_kind': 'box',
     'parameters_json': json.dumps(
         {'size': [2.6, 80.0, 0.6],
          'center': [SHAFT_X['shaft-minute'], 30.0, 3.1]}),
     'notes': 'Extends -10..+70 about the minute shaft. Mass and '
              'imbalance derive from this geometry in the '
              'assembly bill.',
     'provenance_id': 'as-2'},
]

#: What each gear row of the TRAIN must agree with (the guard's
#: source of truth is the GearDefinition rows themselves).
SHAPE_OF_GEAR = {
    'clock-rotor-pinion': 'clock-gear-rotor-pinion',
    'clock-second-wheel': 'clock-gear-second-wheel',
    'clock-second-pinion': 'clock-gear-second-pinion',
    'clock-minute-wheel': 'clock-gear-minute-wheel',
}

SEED_GEAR_SIM_SPACES = [
    {'name': 'gear-train-m0-viz',
     'description': 'The M0 clock gear train, ISOLATED from the '
                    'motor: the driving pinion is the only motor '
                    'piece; every wheel is a math-defined gear at '
                    'the solved centre distances. Motion overlays '
                    'the solved shaft speeds (time-scaled, and the '
                    'scale is said).',
     'dimensionality': '3d',
     'coordinate_system': 'math',
     'unit_scale': 1.0,
     'viewport_json': json.dumps(
         {'center': [80.0, 0.0, 0.7], 'extent': [240, 200, 30]}),
     'bound_classes_json': '[]',
     'definition': json.dumps({
         'freestandingOnly': True,
         'freestanding': [
             {'id': body,
              'shapeRef': f'mathshape:{shape}',
              'styleRef': ('motor-shaft-steel'
                           if body == 'driving-pinion'
                           else 'motor-pointer-red'
                           if body == 'second-hand'
                           else 'motor-shaft-steel'
                           if body == 'minute-hand'
                           else 'motor-rotor-dark'
                           if body.endswith('wheel')
                           else 'motor-part-gray'),
              'position': [0.0, 0.0, 0.0]}
             for body, (shape, _, _) in TRAIN_BODIES.items()]}),
     'axis_labels_json': '{}',
     'camera_json': '',
     'category': 'gears',
     'owning_module': 'gears'},
]


def gear_scene_replay(manager, train_name=TRAIN, time_scale=60.0):
    """Per-body rotation rates from the SOLVED train — the display
    is a kinematic replay of the ratios, sped up by a named
    time_scale so sub-rpm wheels visibly turn."""
    from gears.gear_kinematics import solve_train
    solved = solve_train(manager, train_name)
    if not solved.get('ok'):
        return {'ok': False,
                'refusal': solved.get('refusal',
                                      f'train "{train_name}" did '
                                      f'not solve')}
    rpm_of = {s['shaft']: s.get('speedRpm')
              for s in solved.get('shafts', [])}
    bodies = []
    for body, (shape, shaft, plane_z) in TRAIN_BODIES.items():
        rpm = rpm_of.get(shaft)
        if not isinstance(rpm, (int, float)):
            continue
        bodies.append({
            'body': body, 'shaft': shaft,
            'center': [SHAFT_X[shaft], 0.0, plane_z],
            'axis': 'z',
            'trueRpm': rpm,
            'displayRevPerSec': rpm / 60.0 * time_scale,
        })
    return {
        'ok': True, 'train': train_name,
        'timeScale': time_scale,
        'bodies': bodies,
        'handVectors': HAND_VECTORS,
        'totalRatio': solved.get('totalRatio'),
        'outputSpeedRpm': solved.get('outputSpeedRpm'),
        'note': f'kinematic replay of the SOLVED shaft speeds at '
                f'{time_scale:g}x time (the minute wheel really '
                f'turns 1/60 rpm — honest but invisible); '
                f'direction signs come from the solve, never '
                f'hand-set',
    }


def seed_gear_scene(manager):
    """gr-4 rows via the upsert path (shapes then the scene)."""
    from mathshapes.shape_basis import MathShapeDefinition
    reports = upsert_seed_pairs(
        manager,
        [('MathShapeDefinition', MathShapeDefinition,
          SEED_TRAIN_GEAR_SHAPES + SEED_HAND_SHAPES)],
        tag='GearSceneSeed')
    try:
        from simSpace.sim_space_definition import SimSpaceDefinition
    except Exception:
        SimSpaceDefinition = None
    if SimSpaceDefinition is not None:
        reports += upsert_seed_pairs(
            manager,
            [('SimSpaceDefinition', SimSpaceDefinition,
              SEED_GEAR_SIM_SPACES)],
            tag='GearSceneSeed')
    return reports
