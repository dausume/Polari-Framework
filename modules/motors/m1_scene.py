"""
@module motors.m1_scene

m1-3: scene layers for the M1 views on base `motor-m1-viz` — the
viz-1 machinery reused: same ClockSceneLayerDefinition class, same
clock_scene_payload assembler, M1 rows in the same table.

One NEW layer kind, `phase-replay` (registered in clock_scene):
the flip that makes reluctance legible is WHICH COILS ARE LIT —
the layer carries the phase→coil-body map and the excited/idle
styles; the page drives rotor angle AND coil excitation from the
m1-1 sequence history (each entry names its excited phase). Motion
is runtime, never baked into the scene — the M0 rule.

Part-coloring layers reuse the existing kinds verbatim; only the
part→body map row differs (M1_PART_BODIES, the one copy — guarded
against both the part rows and the sim-space bodies by selftest,
the two-modules-agree rule). M1 layers PIN their design in params
so a caller's M0 default can never silently color M1 bodies from
the wrong bill.

Interface markers arrive with the m1-4 splice (markers need M1's
interfaces stated first) — absent here BY PLAN, not oversight.

@consumers motors.m1_views (scene_json per view), motor_api via
clock_scene_payload, polariServer seed pass (seed_m1_scene)
"""

import json

from composition.seed_upsert import upsert_seed_pairs

from motors.clock_scene import ClockSceneLayerDefinition

M1_DESIGN = 'reluctance-6s4p-m1'
M1_BASE = 'motor-m1-viz'
PROV = 'm1-3'

#: The one part→scene-body map for motor-m1-viz. Teeth, poles and
#: coils are single shape rows ARRAYED by scene rotation — every
#: arrayed body is listed, so coloring covers the full machine.
M1_PART_BODIES = {
    'm1-shaft': ['shaft'],
    'm1-rotor-core': ['rotor-core'],
    'm1-rotor-poles': ['rotor-pole-0', 'rotor-pole-1',
                       'rotor-pole-2', 'rotor-pole-3'],
    'm1-stator-yoke': ['yoke'],
    'm1-stator-teeth': ['stator-tooth-0', 'stator-tooth-1',
                        'stator-tooth-2', 'stator-tooth-3',
                        'stator-tooth-4', 'stator-tooth-5'],
    'm1-coils': ['coil-A0', 'coil-B0', 'coil-C0',
                 'coil-A1', 'coil-B1', 'coil-C1'],
}

#: Phase k excites the series pair on opposite teeth k and k+3 —
#: the SAME pairing m1_phase_electrics states (guarded by
#: selftest: two modules, one fact).
M1_PHASE_COILS = {
    '0': ['coil-A0', 'coil-A1'],
    '1': ['coil-B0', 'coil-B1'],
    '2': ['coil-C0', 'coil-C1'],
}


def _j(o):
    return json.dumps(o)


SEED_M1_SCENE_LAYERS = [
    {'name': 'layer-m1-sequence-replay',
     'display_name': 'Sequencing — the phase walk',
     'kind': 'phase-replay', 'source': 'm1-sequence',
     'params_json': _j({
         'design': M1_DESIGN,
         'rotorBodies': ['shaft', 'rotor-core', 'rotor-pole-0',
                         'rotor-pole-1', 'rotor-pole-2',
                         'rotor-pole-3'],
         'rotorAxis': [0, 0, 1],
         'phaseCoils': M1_PHASE_COILS,
         'coilStyles': {'idle': 'motor-coil-idle',
                        'excited': 'motor-coil-pos'},
         'historySource': 'm1-sequence'}),
     'style_json': '{}',
     'description': 'Coils light by WHICH PHASE IS EXCITED while '
                    'the rotor steps to it — the excitation '
                    'walking around the stator is the whole '
                    'reluctance story, driven from the m1-1 '
                    'sequence history at runtime.',
     'is_prior': True, 'provenance_id': PROV, 'notes': ''},
    {'name': 'layer-m1-stress-coloring',
     'display_name': 'Stress — governing safety factor',
     'kind': 'part-coloring', 'source': 'part-stress',
     'params_json': _j({'design': M1_DESIGN,
                        'part_bodies': M1_PART_BODIES}),
     'style_json': _j({'failBelow': 1.5, 'warnBelow': 4.0}),
     'description': 'M1 bodies color by static SF under the '
                    'criterion their failure class demands; a '
                    'refusing engine grays the part with its '
                    'reason kept.',
     'is_prior': True, 'provenance_id': PROV, 'notes': ''},
    {'name': 'layer-m1-mass-coloring',
     'display_name': 'Mass — share of the bill',
     'kind': 'part-coloring', 'source': 'mass-bill',
     'params_json': _j({'design': M1_DESIGN,
                        'part_bodies': M1_PART_BODIES}),
     'style_json': '{}',
     'description': 'Bodies ramp green→red by mass share from the '
                    'same shape rows the scene draws — bill and '
                    'picture cannot disagree.',
     'is_prior': True, 'provenance_id': PROV, 'notes': ''},
    {'name': 'layer-m1-material-coloring',
     'display_name': 'Materials — what each part is made of',
     'kind': 'part-coloring', 'source': 'materials',
     'params_json': _j({'design': M1_DESIGN,
                        'part_bodies': M1_PART_BODIES}),
     'style_json': '{}',
     'description': 'One color per material option — and the '
                    'legend of a machine with NO magnet is the '
                    'point of the rung, visible.',
     'is_prior': True, 'provenance_id': PROV, 'notes': ''},
]

M1_ALL_LAYERS = [l['name'] for l in SEED_M1_SCENE_LAYERS]

#: defaultOn per M1 view — the discipline's opening statement;
#: every view lists ALL M1 layers (overlap is the point).
M1_VIEW_SCENES = {
    'view-m1-sequencing': ['layer-m1-sequence-replay'],
    'view-m1-magnetics': ['layer-m1-sequence-replay'],
    'view-m1-electrical': ['layer-m1-sequence-replay'],
    'view-m1-mechanical': ['layer-m1-stress-coloring'],
    'view-m1-materials-sourcing': ['layer-m1-material-coloring'],
    'view-m1-positioning': ['layer-m1-sequence-replay'],
}


def m1_scene_json_for_view(view_name):
    default_on = M1_VIEW_SCENES.get(view_name)
    if default_on is None:
        return ''
    return _j({'base': M1_BASE, 'layers': M1_ALL_LAYERS,
               'defaultOn': default_on})


def seed_m1_scene(manager):
    """M1 layer rows via the upsert path (converge live rows)."""
    return upsert_seed_pairs(
        manager,
        [('ClockSceneLayerDefinition', ClockSceneLayerDefinition,
          SEED_M1_SCENE_LAYERS)],
        tag='M1SceneSeed')
