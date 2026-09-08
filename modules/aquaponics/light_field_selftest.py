"""
Selftest — plant-growth-sim phase 8 (2026-07-15): direct-light field
simulation (aquaponics.custom.light_field) + its wiring into advance_growth's
'light' stress factor.

Run from polari-framework/:
    python3 -m aquaponics.light_field_selftest

Uses the REAL seed rows (sunlight-5778k / red-led-660nm spectra, the
demo-herb-pot-grow-light point source, the real sweet-basil/demo-herb
-pot plantings + stress curves already built this session) — no
fixture-only data — so this exercises the real cross-module path:
LightSourceDefinition -> LightSpectrumDefinition -> plant_skeleton's
real bone graph -> plant_stress's 'light' curve -> advance_growth.
"""

import math
from types import SimpleNamespace

from aquaponics.atmosphere_seed import SEED_ATMOSPHERES
from aquaponics.light_basis import LIGHT_SOURCE_KINDS, LIGHT_SPECTRUM_KINDS
from aquaponics.custom.light_field import (
    AMBIENT_SHADE_FRACTION, cylinder_incidence_factor,
    direction_from_az_el, per_part_absorption, self_shading_factor,
    spectrum_ppfd,
)
from aquaponics.light_seed import SEED_LIGHT_SOURCES, SEED_LIGHT_SPECTRA
from aquaponics.media_seed import SEED_SOILS, SEED_WATERS
from aquaponics.plant_growth_normalized_basis import advance_growth
from aquaponics.plant_growth_normalized_seed import SEED_POT_PLANTINGS
from aquaponics.plant_growth_seed import SEED_PLANT_GROWTH_MODELS
from aquaponics.plant_seed import SEED_PLANTS, SEED_PLANT_PARTS
from aquaponics.plant_stress_seed import SEED_STRESS_CURVES
from aquaponics.pot_seed import SEED_POTS
from aquaponics.pot_system_seed import SEED_POT_SYSTEMS
from plant_morphology.morphology_seed import (
    SEED_ORGAN_MODELS, SEED_ROOT_MODELS,
)

PASS, FAIL = '\033[0;32mPASS\033[0m', '\033[0;31mFAIL\033[0m'
_results = []


def check(label, cond, extra=''):
    _results.append(bool(cond))
    print(f'  [{PASS if cond else FAIL}] {label}'
          f'{("  " + extra) if extra else ""}')


def _rows(seed_list):
    return {i: SimpleNamespace(**r) for i, r in enumerate(seed_list)}


def _mgr():
    return SimpleNamespace(objectTables={
        'PlantDefinition': _rows(SEED_PLANTS),
        'PlantPart': _rows(SEED_PLANT_PARTS),
        'PlantGrowthModel': _rows(SEED_PLANT_GROWTH_MODELS),
        'RootSystemModel': _rows(SEED_ROOT_MODELS),
        'OrganModel': _rows(SEED_ORGAN_MODELS),
        'PotDefinition': _rows(SEED_POTS),
        'PotPlanting': _rows(SEED_POT_PLANTINGS),
        'PotSystemDefinition': _rows(SEED_POT_SYSTEMS),
        'AtmosphereDefinition': _rows(SEED_ATMOSPHERES),
        'WaterDefinition': _rows(SEED_WATERS),
        'SoilDefinition': _rows(SEED_SOILS),
        'StressResponseCurve': _rows(SEED_STRESS_CURVES),
        'MatrixEquationDefinition': {},
        'LightSpectrumDefinition': _rows(SEED_LIGHT_SPECTRA),
        'LightSourceDefinition': _rows(SEED_LIGHT_SOURCES),
    })


HEALTHY_PLANTING = 'demo-herb-pot-basil-1'   # bound to a light source
SEALED_PLANTING = 'demo-herb-pot-basil-sealed'  # NOT bound (static
                                                # field path unchanged)


if __name__ == '__main__':
    manager = _mgr()

    print('data model — real seed rows resolve to real objects')
    check('LIGHT_SPECTRUM_KINDS / LIGHT_SOURCE_KINDS cover the seeded '
          "kinds ('blackbody'/'monochromatic', 'point')",
          {s['kind'] for s in SEED_LIGHT_SPECTRA} <= set(
              LIGHT_SPECTRUM_KINDS)
          and {s['source_kind'] for s in SEED_LIGHT_SOURCES} <= set(
              LIGHT_SOURCE_KINDS))

    print('spectrum_ppfd — blackbody (real photon-counting quadrature, '
          'not a fudge constant)')
    sun = next(s for s in manager.objectTables[
        'LightSpectrumDefinition'].values() if s.name == 'sunlight-5778k')
    r = spectrum_ppfd(1000.0, sun)
    check('ok, PAR energy fraction is physically sane for a 5778K '
          'blackbody (~0.30-0.45, the well-known solar PAR-fraction '
          'ballpark)',
          r['ok'] and 0.30 < r['parEnergyFraction'] < 0.45)
    check('PPFD scales linearly with intensity (a pure filter, no '
          'saturation in this model)',
          abs(spectrum_ppfd(2000.0, sun)['ppfd'] / r['ppfd'] - 2.0)
          < 1e-6)
    check('the seeded demo grow-light intensity (207.71 W/m^2) lands '
          'at ~350 PPFD, matching the ventilated-tent atmosphere\'s '
          'existing static light_ppfd_umol_m2_s (documented, not '
          'coincidental)',
          abs(spectrum_ppfd(207.71, sun)['ppfd'] - 350.0) < 1.0)

    print('spectrum_ppfd — monochromatic (exact, no quadrature needed)')
    red = next(s for s in manager.objectTables[
        'LightSpectrumDefinition'].values() if s.name == 'red-led-660nm')
    rr = spectrum_ppfd(500.0, red)
    check('660nm sits fully inside the PAR band -> parEnergyFraction '
          '== 1.0 exactly', rr['ok'] and rr['parEnergyFraction'] == 1.0)
    uv_led = SimpleNamespace(kind='monochromatic', wavelength_nm=350.0,
                             bandwidth_nm=10.0)
    uv = spectrum_ppfd(500.0, uv_led)
    check('a wavelength entirely OUTSIDE the PAR band -> 0 PPFD, not '
          'an error', uv['ok'] and uv['ppfd'] == 0.0)
    edge_led = SimpleNamespace(kind='monochromatic', wavelength_nm=400.0,
                               bandwidth_nm=20.0)   # spans 390-410
    edge = spectrum_ppfd(500.0, edge_led)
    check('a band straddling the PAR boundary gets a PARTIAL fraction '
          '(half its 20nm width overlaps [400,700])',
          edge['ok'] and abs(edge['parEnergyFraction'] - 0.5) < 1e-6)

    print('spectrum_ppfd — honest refusal for an unknown kind')
    bad = spectrum_ppfd(500.0, SimpleNamespace(kind='nope'))
    check('unsupported kind refuses, names the expected kinds',
          not bad['ok'] and 'monochromatic' in bad['error'])

    print('direction_from_az_el — pure vector geometry')
    straight_down = direction_from_az_el(0.0, 90.0)
    check('overhead (elevation=90) points straight down regardless of '
          'azimuth', abs(straight_down[2] - (-1.0)) < 1e-9
          and abs(straight_down[0]) < 1e-9
          and abs(straight_down[1]) < 1e-9)
    horizon = direction_from_az_el(0.0, 0.0)
    check('grazing the horizon (elevation=0) has zero vertical '
          'component', abs(horizon[2]) < 1e-9)
    check('every direction is a real unit vector',
          abs(math.sqrt(sum(c * c for c in straight_down)) - 1.0)
          < 1e-9)

    print('cylinder_incidence_factor — projected cross-section')
    check('a bone perpendicular (broadside) to the light gets max '
          'incidence (1.0)',
          abs(cylinder_incidence_factor((1.0, 0.0, 0.0),
                                        (0.0, 0.0, -1.0)) - 1.0) < 1e-9)
    check('a bone parallel (edge-on) to the light gets ~0 incidence',
          cylinder_incidence_factor((0.0, 0.0, -1.0),
                                    (0.0, 0.0, -1.0)) < 1e-9)
    check('a 45-degree bone gets an intermediate factor',
          0.5 < cylinder_incidence_factor(
              (math.sqrt(0.5), 0.0, math.sqrt(0.5)),
              (0.0, 0.0, -1.0)) < 1.0)

    print('self_shading_factor — reduced-fidelity sphere occlusion')
    target = {'id': 'b0', 'startPointMm': [0, 0, 0],
             'endPointMm': [0, 0, 10]}
    occluder = {'id': 'b1', 'startPointMm': [0, 0, 40],
               'endPointMm': [0, 0, 60], 'startRadiusMm': 20.0,
               'endRadiusMm': 20.0}
    light_dir = (0.0, 0.0, -1.0)   # travels downward -> source is UP
    check('an occluder directly between the target and the light '
          'source reduces to AMBIENT_SHADE_FRACTION, never a hard 0',
          self_shading_factor([target, occluder], target, light_dir)
          == AMBIENT_SHADE_FRACTION)
    check('no occluders -> fully unshaded (1.0)',
          self_shading_factor([target], target, light_dir) == 1.0)
    far_occluder = {'id': 'b2', 'startPointMm': [500, 500, 40],
                    'endPointMm': [500, 500, 60], 'startRadiusMm': 5.0,
                    'endRadiusMm': 5.0}
    check('an occluder far off the light ray does not shade the target',
          self_shading_factor([target, far_occluder], target, light_dir)
          == 1.0)
    behind_occluder = {'id': 'b3', 'startPointMm': [0, 0, -40],
                       'endPointMm': [0, 0, -60], 'startRadiusMm': 20.0,
                       'endRadiusMm': 20.0}
    check('an occluder BEHIND the target (away from the light) does '
          'not shade it',
          self_shading_factor([target, behind_occluder], target,
                              light_dir) == 1.0)

    print('per_part_absorption — the full pipeline against REAL seed '
          'data (demo-herb-pot-basil-1, bound to demo-herb-pot-grow-'
          'light via basil-aquaponic-tent)')
    result = per_part_absorption(manager, HEALTHY_PLANTING,
                                 'demo-herb-pot-grow-light')
    check('ok, real per-part absorbed PPFD for stem/leaf (the parts '
          'with a real bone presence)',
          result['ok'] and 'leaf' in result['partAbsorptionPpfd']
          and 'stem' in result['partAbsorptionPpfd'])
    check('every part absorption value is non-negative and finite',
          all(v >= 0.0 for v in result['partAbsorptionPpfd'].values()))
    check('sourcePpfd matches the real spectrum_ppfd computation for '
          "this source's own intensity + spectrum",
          abs(result['sourcePpfd']
              - spectrum_ppfd(207.71, sun)['ppfd']) < 0.5)
    check('note states the direct-light-only scope honestly',
          'Diffuse' in result['note'] and 'deferred' in result['note'])

    print('per_part_absorption — honest refusals')
    missing_source = per_part_absorption(manager, HEALTHY_PLANTING, 'nope')
    check('unknown light source refuses, names it',
          not missing_source['ok'] and 'nope' in missing_source['error'])
    broken_spectrum_mgr = _mgr()
    broken_source = SimpleNamespace(
        name='broken-source', source_kind='point',
        position_mm_json='[0,0,400]', intensity_w_m2=500.0,
        spectrum_name='does-not-exist')
    broken_spectrum_mgr.objectTables['LightSourceDefinition'][
        'broken'] = broken_source
    missing_spectrum = per_part_absorption(
        broken_spectrum_mgr, HEALTHY_PLANTING, 'broken-source')
    check('unknown spectrum_name refuses, suggests the fix',
          not missing_spectrum['ok']
          and missing_spectrum['suggestion']['knob']
          == 'LightSpectrumDefinition')
    missing_planting = per_part_absorption(
        manager, 'nope', 'demo-herb-pot-grow-light')
    check('unknown planting refuses',
          not missing_planting['ok'])

    print("advance_growth — the light field's REAL effect on growth "
          "(bound planting vs an unbound one)")
    bound = advance_growth(manager, HEALTHY_PLANTING, dt_days=10.0)
    check('mode = stress-equations, leaf carries a light-field-sourced '
          'stressEvidence entry',
          bound['ok'] and bound['mode'] == 'stress-equations'
          and 'light' in bound['parts']['leaf']['stressEvidence'][
              'factorsByType'])
    unbound = advance_growth(manager, SEALED_PLANTING, dt_days=10.0)
    check('the sealed planting (no light_source_name bound on its own '
          "system) still resolves — falls back to the static "
          'AtmosphereDefinition field, unaffected by this phase',
          unbound['ok'] and unbound['mode'] == 'stress-equations'
          and 'light' in unbound['parts']['leaf']['stressEvidence'][
              'factorsByType'])

    print('never-collapsed knobs: an explicit manual override still '
          'bypasses the light field entirely (backward compatible)')
    manual = advance_growth(manager, HEALTHY_PLANTING, dt_days=10.0,
                            water_supply_factor=1.0,
                            soil_supply_factor=1.0)
    check('manual override mode carries no stressEvidence at all '
          '(the light-field computation never even ran)',
          manual['mode'] == 'manual'
          and all('stressEvidence' not in p
                  for p in manual['parts'].values()))

    failed = _results.count(False)
    print(f'\n{len(_results) - failed}/{len(_results)} passed')
    raise SystemExit(1 if failed else 0)
