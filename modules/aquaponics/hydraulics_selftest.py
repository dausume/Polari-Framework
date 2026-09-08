"""
Selftest — aqp-3: pot hydraulics (payload builder, reservoir model,
findings mapping, fidelity ladder).

Run from polari-framework/:
    python3 -m aquaponics.hydraulics_selftest

The FEM engine is MOCKED here (selftests stay stdlib-only + fast; the
real skfem solve is validated separately where the library exists —
worker or dev machine). Covers: payload built in SI from mm rows;
missing pot/soil/holes refuse honestly; reservoir model drains vs
doesn't by head; K/head scaling; fem fidelity uses the engine; engine
refusal falls back to reservoir WITH a fidelityNote carrying the
suggestion; findings name evidence + knobs.
"""

from types import SimpleNamespace

from aquaponics.custom.hydraulics import (
    build_darcy_payload, reservoir_model, run_hydraulics,
    soil_conductivity_m_per_s, water_slice_mesh,
)
from aquaponics.pot_seed import SEED_POTS, SEED_POT_HOLES

PASS, FAIL = '\033[0;32mPASS\033[0m', '\033[0;31mFAIL\033[0m'
_results = []


def check(label, cond, extra=''):
    _results.append(bool(cond))
    print(f'  [{PASS if cond else FAIL}] {label}'
          f'{("  " + extra) if extra else ""}')


def _rows(seed_list):
    return {i: SimpleNamespace(**r) for i, r in enumerate(seed_list)}


SOILS = [{'name': 'potting-mix', 'hydraulic_conductivity_mm_hr': 25.0}]


def _mgr():
    return SimpleNamespace(objectTables={
        'PotDefinition': _rows(SEED_POTS),
        'PotHole': _rows(SEED_POT_HOLES),
        'SoilDefinition': _rows(SOILS),
    })


if __name__ == '__main__':
    manager = _mgr()

    print('payload builder')
    built = build_darcy_payload(manager, 'demo-herb-pot', 'potting-mix')
    check('builds ok from seeds', built.get('ok'))
    payload = built['payload']
    pot = next(p for p in SEED_POTS if p['name'] == 'demo-herb-pot')
    expected_width = (pot['outer_base_diameter_mm']
                      - 2 * pot['wall_thickness_mm']) / 1000.0
    check('width converted mm->m (inner)',
          abs(payload['geometry']['width_m'] - expected_width) < 1e-9)
    check('K converted mm/hr -> m/s',
          abs(payload['k_m_per_s'] - 25.0 / 1000 / 3600) < 1e-12)
    check('conductivity source labeled',
          'SoilDefinition' in built['conductivitySource'])
    check('inputs left / outputs right, all holes present',
          {h['side'] for h in payload['holes']} == {'left', 'right'}
          and len(payload['holes'])
          == sum(1 for h in SEED_POT_HOLES
                 if h['pot_name'] == 'demo-herb-pot'))
    check('default water level = highest input',
          abs(payload['water_level_m'] * 1000
              - max(h['height_mm'] for h in SEED_POT_HOLES
                    if h['pot_name'] == 'demo-herb-pot'
                    and h['kind'] == 'input')) < 1e-6)

    print('honest refusals')
    check('unknown pot refuses',
          not build_darcy_payload(manager, 'nope', '').get('ok'))
    check('unknown soil refuses',
          not build_darcy_payload(manager, 'demo-herb-pot',
                                  'nope').get('ok'))
    holeless = SimpleNamespace(objectTables={
        'PotDefinition': _rows(SEED_POTS), 'PotHole': {},
        'SoilDefinition': _rows(SOILS)})
    refusal = build_darcy_payload(holeless, 'demo-herb-pot', '')
    check('no holes -> refusal with suggestion knob',
          not refusal.get('ok')
          and 'PotHole' in refusal['suggestion']['knob'])

    print('reservoir model (reduced fidelity)')
    result = reservoir_model(payload)
    check('drains under positive head',
          result['ok'] and result['drains']
          and result['outflowRateMlS'] > 0)
    check("names its fidelity 'reservoir'",
          result['fidelity'] == 'reservoir')
    check('evidence carries the formula + upgrade knob',
          'Q = K' in result['evidence']
          and 'fem' in result['evidence'])
    low = reservoir_model(dict(payload, water_level_m=0.001))
    check('water below output lip -> does not drain',
          low['ok'] and not low['drains']
          and low['outflowRateMlS'] == 0.0
          and 'below' in low['limitingFactor'])
    double_k = reservoir_model(
        dict(payload, k_m_per_s=2 * payload['k_m_per_s']))
    check('outflow scales linearly with K',
          abs(double_k['outflowRateMlS']
              / result['outflowRateMlS'] - 2.0) < 1e-9)

    print('fidelity ladder (engine mocked)')
    canned = {'ok': True, 'drains': True, 'fidelity': 'fem',
              'outflowRateMlS': 3.2, 'limitingFactor': None,
              'evidence': 'mocked steady Darcy solve',
              'meshMeta': {'elements': 8192}}
    seen = {}

    def mock_engine(pay, want_field):
        seen['payload'] = pay
        return dict(canned)

    fem = run_hydraulics(manager, 'demo-herb-pot', 'potting-mix',
                         engine=mock_engine)
    check('fem fidelity returns the engine result + context',
          fem['ok'] and fem['fidelity'] == 'fem'
          and fem['outflowRateMlS'] == 3.2
          and fem['pot'] == 'demo-herb-pot'
          and 'fidelityNote' not in fem)
    check('engine got the built payload',
          seen['payload']['k_m_per_s'] == payload['k_m_per_s'])
    check('drains finding carries rate + fidelity',
          fem['findings'][0]['kind'] == 'drains-by-gravity'
          and '3.2' in fem['findings'][0]['evidence']
          and 'fem' in fem['findings'][0]['evidence'])

    def refusing_engine(pay, want_field):
        return {'ok': False, 'error': 'no engines worker configured',
                'suggestion': {'knob': 'MSCI_ENGINES_URL',
                               'action': 'start the worker',
                               'evidence': 'unset + no provider'}}

    fallen = run_hydraulics(manager, 'demo-herb-pot', 'potting-mix',
                            engine=refusing_engine)
    check('engine refusal falls back to reservoir',
          fallen['ok'] and fallen['fidelity'] == 'reservoir'
          and fallen['drains'])
    note = fallen.get('fidelityNote', {})
    check('fidelityNote says requested fem, used reservoir, keeps '
          'the suggestion',
          note.get('requested') == 'fem'
          and note.get('used') == 'reservoir'
          and note.get('suggestion', {}).get('knob')
          == 'MSCI_ENGINES_URL')
    explicit = run_hydraulics(manager, 'demo-herb-pot', 'potting-mix',
                              fidelity='reservoir',
                              engine=refusing_engine)
    check('explicit reservoir fidelity never calls the engine '
          '(no fidelityNote)',
          explicit['ok'] and 'fidelityNote' not in explicit)
    check('bad fidelity refuses',
          not run_hydraulics(manager, 'demo-herb-pot', '',
                             fidelity='navier-stokes').get('ok'))

    print('does-not-drain findings')
    dry = run_hydraulics(manager, 'demo-herb-pot', 'potting-mix',
                         water_level_mm=5.0, fidelity='reservoir')
    finding = dry['findings'][0]
    check('non-draining pot names the knob + action',
          not dry['drains']
          and finding['kind'] == 'does-not-drain'
          and 'height_mm' in finding['knob']
          and 'lower the output' in finding['action'])

    print('water_slice_mesh — 3-D-positioned Darcy cross-section '
          '(phase 3, engine mocked)')
    WIDTH_M = 0.184  # demo-herb-pot inner width (200 - 2*8mm)
    field_canned = {
        'ok': True, 'engine': 'scikit-fem', 'fidelity': 'fem',
        'headField': [[0.0, 0.0, 0.05], [WIDTH_M, 0.0, 0.02],
                      [WIDTH_M / 2, 0.2, 0.04]],
        'headFieldColumns': ['x_m', 'z_m', 'head_m'],
        'headFieldTriangles': [[0, 1, 2]],
        'outflowRateMlS': 1.5, 'inflowRateM3s': 0.0, 'outflowRateM3s': 0.0,
        'fluxStats': {'maxDarcySpeedMs': 1e-6, 'meanDarcySpeedMs': 5e-7},
        'meshMeta': {'elements': 1, 'nodes': 3, 'refine': 6,
                     'spacingM': 0.01, 'widthM': WIDTH_M, 'heightM': 0.2},
        'note': 'mocked field solve',
    }

    def mock_field_engine(pay, want_field):
        return dict(field_canned)

    slice_result = water_slice_mesh(manager, 'demo-herb-pot',
                                    'potting-mix',
                                    engine=mock_field_engine)
    check('ok, one point per headField row, one triangle carried through',
          slice_result['ok']
          and len(slice_result['points']) == 3
          and slice_result['triangles'] == [[0, 1, 2]])
    check('headValuesM is exactly the head_m column',
          slice_result['headValuesM'] == [0.05, 0.02, 0.04])

    # demo-herb-pot outputs sit at azimuth 170/190 -> circular mean 180deg
    # -> slice direction (-1, 0). H = 250mm/10 = 25cm -> floor_z = -12.5cm.
    import math
    x0, y0, z0 = slice_result['points'][0]  # x_m=0 (input wall), z_m=0
    check('input-wall point maps to +width/2 along the output-azimuth '
          'line (180deg direction => world_x = +width_cm/2)',
          abs(x0 - (WIDTH_M * 100 / 2)) < 1e-6 and abs(y0) < 1e-6)
    check('z_m=0 maps to the pot floor (outer-base bottom, -H/2 in cm)',
          abs(z0 - (-12.5)) < 1e-6)
    x1, y1, z1 = slice_result['points'][1]  # x_m=width (output wall)
    check('output-wall point maps to -width/2 along the same line',
          abs(x1 - (-WIDTH_M * 100 / 2)) < 1e-6 and abs(y1) < 1e-6)
    check('note states the flat-slice + repeated-steady-state '
          'approximation plainly',
          'VISUAL APPROXIMATION' in slice_result['note']
          and 'not a true transient' in slice_result['note'])

    def mock_no_field_engine(pay, want_field):
        return {'ok': False, 'error': 'no engines worker configured',
                'suggestion': {'knob': 'MSCI_ENGINES_URL',
                               'action': 'start the worker',
                               'evidence': 'unset'}}

    no_field = water_slice_mesh(manager, 'demo-herb-pot', 'potting-mix',
                                engine=mock_no_field_engine)
    check('no reachable field solver -> honest refusal naming the '
          'fem requirement, never a silent reservoir-model substitute',
          not no_field['ok'] and 'fem field solve' in no_field['error'])
    check('unknown pot still refuses cleanly through the same path',
          not water_slice_mesh(manager, 'nope', '',
                               engine=mock_field_engine).get('ok'))

    print('units helper')
    check('soil K helper: 3600 mm/hr == 1e-3 m/s',
          abs(soil_conductivity_m_per_s(SimpleNamespace(
              hydraulic_conductivity_mm_hr=3600.0)) - 1e-3) < 1e-12)

    failed = _results.count(False)
    print(f'\n{len(_results) - failed}/{len(_results)} passed')
    raise SystemExit(1 if failed else 0)
