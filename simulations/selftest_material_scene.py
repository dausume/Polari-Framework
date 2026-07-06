"""
Selftest: the material-condensation 3D scene + per-phase appearance
(Phase B of solid-materials-selection). No server, no sudo.

Run from polari-framework/:
    python3 -m simulations.selftest_material_scene

Covers:
  - resolve_ref's {fromField, map, default} variant (the per-phase
    appearance primitive) incl. numeric-key normalization + fallbacks
  - the uniform field scale with factor (ball sized by ball_radius)
  - the seeded material-condensation-viz scene compiling against fake
    rows: liquid step wears the liquid material, solid step the solid
    one, scale tracks ball_radius, step-0 (no ball yet) scales to 0
  - appearance rows ↔ binding map coherence (binding_style_map)
  - texture/material/appearance seed cross-references all resolve
"""

import json
from types import SimpleNamespace

from simSpace.compilers.common import resolve_ref
from simSpace.compilers.compile_3d import compile_3d, _resolve_scale_3d
from simulations.material_space_scene_seed import (
    MATERIAL_SCENE, SELECTOR_SCENE,
    _MATERIAL_SIMSPACE, _MATERIAL_BINDINGS, _SELECTOR_SIMSPACE,
)
from simSpace3D.seed_data import (
    SEED_MATERIALS_3D, SEED_TEXTURES_3D, SEED_MATERIAL_PHASE_APPEARANCES,
)
from simSpace3D.material_phase_appearance import binding_style_map

PASS, FAIL = '\033[0;32mPASS\033[0m', '\033[0;31mFAIL\033[0m'
results = []


def check(label, cond, extra=''):
    results.append(bool(cond))
    print(f'  [{PASS if cond else FAIL}] {label}{("  " + extra) if extra else ""}')


def _mc_row(step, time, phase_solid, ball_radius):
    return SimpleNamespace(
        name=f'test-run-material-condensation-{step}',
        simulation_run_ref='test-run', step=step, time=time,
        temperature=300.0, melt_temp=327.0, phase_solid=phase_solid,
        density=900.0, ball_mass=1.93, ball_radius=ball_radius,
        id=f'mc-{step}',
    )


def _mgr(rows):
    m = SimpleNamespace()
    m.objectTypingDict = {}
    m.objectTables = {
        'MaterialCondensationState': {r.name: r for r in rows},
        'SimSpaceBindingDefinition': {
            b['name']: SimpleNamespace(**b) for b in _MATERIAL_BINDINGS
        },
    }
    return m


def _resolve_ref_variant():
    print('Per-phase appearance — resolve_ref map variant\n')
    spec = {'fromField': 'phase_solid',
            'map': {'1': 'wax-solid', '0': 'wax-liquid'},
            'default': 'matte-gray'}
    solid = SimpleNamespace(phase_solid=1.0)
    liquid = SimpleNamespace(phase_solid=0.0)
    missing = SimpleNamespace()
    odd = SimpleNamespace(phase_solid=0.5)
    check('numeric 1.0 maps through the "1" key (int-str normalization)',
          resolve_ref(spec, solid, 'x') == 'wax-solid')
    check('numeric 0.0 maps through the "0" key',
          resolve_ref(spec, liquid, 'x') == 'wax-liquid')
    check('missing field falls back to the spec default',
          resolve_ref(spec, missing, 'x') == 'matte-gray')
    check('unmapped value falls back to the spec default',
          resolve_ref(spec, odd, 'x') == 'matte-gray')
    no_default = {'fromField': 'phase_solid', 'map': {}}
    check('malformed/empty map falls back to the caller default',
          resolve_ref(no_default, solid, 'caller-default') == 'caller-default')
    check('plain {fromField} (no map) behavior unchanged',
          resolve_ref({'fromField': 'phase_solid'}, solid, 'x') == '1.0')
    check('bare string behavior unchanged',
          resolve_ref('matte-blue', solid, 'x') == 'matte-blue')


def _scale_variant():
    print('\nField-driven uniform scale (with factor)\n')
    inst = SimpleNamespace(ball_radius=0.08)
    check('uniform field scale × factor (radius → unit-sphere scale)',
          abs(_resolve_scale_3d({'kind': 'uniform', 'field': 'ball_radius',
                                 'factor': 2.0}, inst) - 0.16) < 1e-12)
    check('a genuine 0 stays 0 (no ball yet → nothing rendered)',
          _resolve_scale_3d({'kind': 'uniform', 'field': 'ball_radius',
                             'factor': 2.0},
                            SimpleNamespace(ball_radius=0.0)) == 0.0)
    check('missing field resolves to None (binding omits scale)',
          _resolve_scale_3d({'kind': 'uniform', 'field': 'nope'},
                            SimpleNamespace()) is None)
    check('constant scale unchanged',
          _resolve_scale_3d({'kind': 'constant', 'value': 0.24},
                            SimpleNamespace()) == 0.24)


def _scene_compile():
    print('\nmaterial-condensation-viz — compile against fake rows\n')
    rows = [
        _mc_row(0, 0.0, 0.0, 0.0),     # pre-step: no ball yet
        _mc_row(2, 0.2, 0.0, 0.08),    # cooling, still liquid
        _mc_row(9, 0.9, 1.0, 0.08),    # crossed the melt line: solid
    ]
    scene_row = SimpleNamespace(**_MATERIAL_SIMSPACE)
    warnings, resolved = [], []
    objects, _connections, _vectors = compile_3d(
        _mgr(rows), scene_row, warnings, resolved, run_filter='test-run')

    balls = {o['classRef']['instanceId']: o for o in objects
             if o.get('classRef', {}).get('className')
             == 'MaterialCondensationState'}
    check('one ball object per state row', len(balls) == 3,
          f'count={len(balls)}')
    check('liquid step wears the liquid material',
          balls.get('mc-2', {}).get('styleRef') == 'wax-liquid',
          f"styleRef={balls.get('mc-2', {}).get('styleRef')}")
    check('solid step wears the solid material',
          balls.get('mc-9', {}).get('styleRef') == 'wax-solid',
          f"styleRef={balls.get('mc-9', {}).get('styleRef')}")
    check('scale tracks ball_radius (0.08 m → 0.16 unit-sphere scale)',
          abs((balls.get('mc-9', {}).get('scale') or 0) - 0.16) < 1e-12,
          f"scale={balls.get('mc-9', {}).get('scale')}")
    check('step-0 ball scales to 0 (nothing proven yet)',
          balls.get('mc-0', {}).get('scale') == 0.0)
    check('temporal values ride along for the scrubber',
          balls.get('mc-9', {}).get('temporalValue') == 0.9)
    plate = [o for o in objects if o.get('label') == 'Chamber']
    check('freestanding chamber plate emitted', len(plate) == 1)
    check('scene compiled without warnings', not warnings,
          f'warnings={warnings}')


def _seed_coherence():
    print('\nSeed coherence — appearances ↔ materials ↔ textures\n')
    material_names = {m['name'] for m in SEED_MATERIALS_3D}
    texture_names = {t['name'] for t in SEED_TEXTURES_3D}
    appearance_rows = SEED_MATERIAL_PHASE_APPEARANCES

    check('an appearance row exists per picker substance',
          {r['substance_ref'] for r in appearance_rows}
          == {'paraffin-wax', 'water-ice', 'lead'})
    referenced = set()
    for row in appearance_rows:
        referenced.update(json.loads(row['appearance_map_json']).values())
        referenced.add(row['default_material_ref'])
    check('every appearance-referenced material is seeded',
          referenced <= material_names,
          f'missing={sorted(referenced - material_names)}')
    tex_refs = {m.get('map_texture_ref') for m in SEED_MATERIALS_3D
                if m.get('map_texture_ref')}
    check('every material texture ref resolves to a seeded texture',
          tex_refs <= texture_names,
          f'missing={sorted(tex_refs - texture_names)}')
    check('procedural texture params parse as JSON',
          all(isinstance(json.loads(t['procedural_params_json']), dict)
              for t in SEED_TEXTURES_3D))

    wax = next(r for r in appearance_rows
               if r['substance_ref'] == 'paraffin-wax')
    composed = binding_style_map(wax)
    binding = json.loads(_MATERIAL_BINDINGS[0]['binding_json'])
    check('scene binding style map IS the wax appearance row (no drift)',
          binding['visual']['styleRef'] == composed,
          f"binding={binding['visual']['styleRef']}")
    check('scene is registered under the expected name',
          _MATERIAL_SIMSPACE['name'] == MATERIAL_SCENE == 'material-condensation-viz')


def _selector_scene():
    print('\nsolid-material-selector — the fixed-camera selection space\n')
    camera = json.loads(_SELECTOR_SIMSPACE['camera_json'])
    check('camera is FIXED with an explicit pose',
          camera['mode'] == 'fixed'
          and len(camera['position']) == 3 and len(camera['target']) == 3)
    scene_row = SimpleNamespace(**_SELECTOR_SIMSPACE)
    warnings, resolved = [], []
    objects, _c, _v = compile_3d(_mgr([]), scene_row, warnings, resolved,
                                 run_filter=None)
    balls = {o['id']: o for o in objects if o['id'].startswith('choice-')}
    check('one selectable preview ball per substance',
          set(balls) == {'choice-paraffin-wax', 'choice-water-ice',
                         'choice-lead'})
    check('preview balls wear their SOLID-phase materials',
          balls['choice-paraffin-wax']['styleRef'] == 'wax-solid'
          and balls['choice-water-ice']['styleRef'] == 'ice-solid'
          and balls['choice-lead']['styleRef'] == 'lead-solid')
    from simulations.multi_scale_seed import SEED_MULTI_SCALE_SIMS
    panels = json.loads(SEED_MULTI_SCALE_SIMS[0]['panels_json'])
    selector = next(p for p in panels if p['kind'] == 'selector')
    check('selector panel items match the scene object ids',
          {i['objectId'] for i in selector['items']} == set(balls)
          and selector['simSpaceRef'] == SELECTOR_SCENE)
    ic = next(p for p in panels if p['kind'] == 'ic')
    check('IC picker follows the selector via the shared context key',
          ic.get('followContextKey') == selector.get('contextKey')
          == 'selectedMaterialKey')


def main():
    _resolve_ref_variant()
    _scale_variant()
    _scene_compile()
    _selector_scene()
    _seed_coherence()
    total, passed = len(results), sum(results)
    print(f'\n{passed}/{total} checks passed')
    return 0 if passed == total else 1


if __name__ == '__main__':
    raise SystemExit(main())
