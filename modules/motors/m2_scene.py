"""
@module motors.m2_scene

m2-3: scene layers for the M2 views on base `motor-m2-viz`. The
viz-1 machinery again, unchanged: same ClockSceneLayerDefinition
class, same assembler, same layer KINDS. No new kind is invented
here, deliberately — if the second rung needed new rendering
machinery, the first rung's machinery was not general.

The rotation layer reuses `phase-replay` (M1's kind) with ALL SIX
coils in one phase group: M2's three phases carry current
continuously rather than one-at-a-time, so lighting them by turn
would be a lie about the drive. What the layer animates is the
ROTOR — driven from the m2-1 history at runtime, as always, never
baked into the scene.

The part-coloring layers take the M2 part→body map, which is the
reuse story again: four of the six mapped parts are M1's, and the
bodies they color are the same bodies motor-m1-viz colors.

@consumers motors.m2_views (scene_json per view), motor_api via
clock_scene_payload, polariServer seed pass (seed_m2_scene)
"""

import json

from composition.seed_upsert import upsert_seed_pairs

from motors.clock_scene import ClockSceneLayerDefinition

M2_DESIGN = 'ferrite-pm-m2'
M2_BASE = 'motor-m2-viz'
PROV = 'm2-3'

#: The one part→scene-body map for motor-m2-viz. The four M1
#: entries are the SAME part rows the M1 map uses (PART_REUSE),
#: pointing at the same body ids — guarded by selftest against
#: both the part rows and the sim-space bodies.
M2_PART_BODIES = {
    'm2-magnet-ring': ['magnet-ring'],
    'm2-rotor-carrier': ['rotor-carrier'],
    'm1-shaft': ['shaft'],
    'm1-stator-yoke': ['yoke'],
    'm1-stator-teeth': ['stator-tooth-0', 'stator-tooth-1',
                        'stator-tooth-2', 'stator-tooth-3',
                        'stator-tooth-4', 'stator-tooth-5'],
    'm1-coils': ['coil-A0', 'coil-B0', 'coil-C0',
                 'coil-A1', 'coil-B1', 'coil-C1'],
}

#: ALL SIX COILS AS ONE GROUP: a synchronous drive energises every
#: phase at once (they differ in phase, not in on/off), so the
#: honest picture lights them together and lets the ROTOR carry
#: the motion. M1's map lights one pair at a time because that is
#: literally what its drive does — the difference between the two
#: maps IS the difference between the two machines.
M2_PHASE_COILS = {
    '0': ['coil-A0', 'coil-B0', 'coil-C0',
          'coil-A1', 'coil-B1', 'coil-C1'],
}

M2_ROTOR_BODIES = ['shaft', 'rotor-carrier', 'magnet-ring']


def _j(o):
    return json.dumps(o)


SEED_M2_SCENE_LAYERS = [
    {'name': 'layer-m2-rotation-replay',
     'display_name': 'Rotation — the magnet following the field',
     'kind': 'phase-replay', 'source': 'm2-rotation',
     'params_json': _j({
         'design': M2_DESIGN,
         'rotorBodies': M2_ROTOR_BODIES,
         'rotorAxis': [0, 0, 1],
         'phaseCoils': M2_PHASE_COILS,
         'coilStyles': {'idle': 'motor-coil-idle',
                        'excited': 'motor-coil-pos'},
         'historySource': 'm2-rotation'}),
     'style_json': '{}',
     'description': 'The ring turns because the magnet chases the '
                    'rotating field, lagging by whatever angle '
                    'makes the torque the load asks for — driven '
                    'from the m2-1 history at runtime. All six '
                    'coils stay lit together: a synchronous drive '
                    'energises every phase at once, and showing '
                    'them take turns would be a lie about the '
                    'drive.',
     'is_prior': True, 'provenance_id': PROV, 'notes': ''},
    {'name': 'layer-m2-stress-coloring',
     'display_name': 'Stress — governing safety factor',
     'kind': 'part-coloring', 'source': 'part-stress',
     'params_json': _j({'design': M2_DESIGN,
                        'part_bodies': M2_PART_BODIES}),
     'style_json': _j({'failBelow': 1.5, 'warnBelow': 4.0}),
     'description': 'M2 bodies color by static SF under the '
                    'criterion their failure class demands — and '
                    'the ring is the interesting one: a sintered '
                    'ceramic ring spun on a bonded joint.',
     'is_prior': True, 'provenance_id': PROV, 'notes': ''},
    {'name': 'layer-m2-mass-coloring',
     'display_name': 'Mass — share of the bill',
     'kind': 'part-coloring', 'source': 'mass-bill',
     'params_json': _j({'design': M2_DESIGN,
                        'part_bodies': M2_PART_BODIES}),
     'style_json': '{}',
     'description': 'Bodies ramp green→red by mass share from the '
                    'same shape rows the scene draws — including '
                    'the four parts M2 inherits from M1, whose '
                    'mass is real because they are really there.',
     'is_prior': True, 'provenance_id': PROV, 'notes': ''},
    {'name': 'layer-m2-material-coloring',
     'display_name': 'Materials — what each part is made of',
     'kind': 'part-coloring', 'source': 'materials',
     'params_json': _j({'design': M2_DESIGN,
                        'part_bodies': M2_PART_BODIES}),
     'style_json': '{}',
     'description': 'One color per material option — and unlike '
                    'M1\'s legend, this one has a HARD magnetic '
                    'material on it. That single new swatch is '
                    'the whole rung.',
     'is_prior': True, 'provenance_id': PROV, 'notes': ''},
    {'name': 'layer-m2-interface-markers',
     'display_name': 'Interfaces — joints, gaps & failure modes',
     'kind': 'markers', 'source': 'composition-interfaces',
     'params_json': _j({
         'design': M2_DESIGN, 'positions_derived': True,
         'markers': [
             {'interface': name, 'position': pos,
              'radius': (2.0 if name == 'ifm2-working-gap'
                         else 2.4)}
             for name, pos in sorted(
                 __import__(
                     'motors.m2_composition',
                     fromlist=['derived_m2_marker_positions'])
                 .derived_m2_marker_positions().items())]}),
     'style_json': '{}',
     'description': 'A sphere per M2 joint. There is exactly ONE '
                    'designed non-contact gap here where M1 had '
                    'two — the round rotor has no coil clearance '
                    'to keep, which is one less thing to get '
                    'wrong. Positions DERIVE from the shape rows.',
     'is_prior': True, 'provenance_id': PROV, 'notes': ''},
]

M2_ALL_LAYERS = [layer['name'] for layer in SEED_M2_SCENE_LAYERS]

#: defaultOn per M2 view — the discipline's opening statement.
M2_VIEW_SCENES = {
    'view-m2-rotation': ['layer-m2-rotation-replay'],
    'view-m2-magnetics': ['layer-m2-rotation-replay'],
    'view-m2-electrical': ['layer-m2-rotation-replay'],
    'view-m2-mechanical': ['layer-m2-stress-coloring',
                           'layer-m2-interface-markers'],
    'view-m2-materials-sourcing': ['layer-m2-material-coloring'],
    'view-m2-lift': ['layer-m2-rotation-replay'],
}


def m2_scene_json_for_view(view_name):
    default_on = M2_VIEW_SCENES.get(view_name)
    if default_on is None:
        return ''
    return _j({'base': M2_BASE, 'layers': M2_ALL_LAYERS,
               'defaultOn': default_on})


def seed_m2_scene(manager):
    """M2 layer rows via the upsert path (converge live rows)."""
    return upsert_seed_pairs(
        manager,
        [('ClockSceneLayerDefinition', ClockSceneLayerDefinition,
          SEED_M2_SCENE_LAYERS)],
        tag='M2SceneSeed')
