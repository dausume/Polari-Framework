"""
Self-test for the materials basis: identities + scale definitions +
presence gates + rules-of-mixtures math + FEM/DFT engine capability
contracts.

Run from polari-framework/:
    python3 -m materialsScience.selftest_materials_basis
"""

import sys
from types import SimpleNamespace

from materialsScience.materials_basis_seed import (
    SEED_MS_MATERIALS, SEED_MS_SCALE_DEFINITIONS,
)
from materialsScience.scale_presence import (
    scale_profile, require_scale_levels,
)
from materialsScience.formulation_math import (
    predict_formulation_properties, mixture_bounds, score_against_targets,
)
from materialsScience.engines import fem_engine, dft_engine

PASS = 0
FAIL = 0


def check(label, condition):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f'  ok: {label}')
    else:
        FAIL += 1
        print(f'  FAIL: {label}')


def _fake_manager():
    """objectTables shaped like the live tree, from the seed rows."""
    rows = {
        seed['name']: SimpleNamespace(**{
            'scale_level': 0, 'status': 'defined', 'material_name': '',
            **seed})
        for seed in SEED_MS_SCALE_DEFINITIONS
    }
    return SimpleNamespace(objectTables={'MaterialScaleDefinition': rows})


def test_seeds():
    print('[seeds]')
    names = [m['name'] for m in SEED_MS_MATERIALS]
    check('5 material identities', len(names) == 5)
    check('names unique', len(set(names)) == len(names))
    check('waxes bridge RawMaterial rows', all(
        m.get('raw_material_name') for m in SEED_MS_MATERIALS
        if m['name'] in ('beeswax', 'carnauba-wax', 'soy-wax')))
    scaleNames = [s['name'] for s in SEED_MS_SCALE_DEFINITIONS]
    check('scale rows follow <material>@L<level>', all(
        '@L' in n for n in scaleNames))
    check('every scale row targets a seeded material', all(
        s['material_name'] in names for s in SEED_MS_SCALE_DEFINITIONS))
    check('paraffin L0 bridges the condensation sim', any(
        s['definition_class'] == 'SimulationDefinition'
        and s['definition_ref'] == 'material-condensation'
        for s in SEED_MS_SCALE_DEFINITIONS))
    check('blend row carries lineage', any(
        s.get('derived_from_name') and
        s.get('derivation_method') == 'rules-of-mixtures'
        for s in SEED_MS_SCALE_DEFINITIONS))


def test_presence_and_gates():
    print('[scale presence + gates]')
    manager = _fake_manager()

    profile = scale_profile(manager, 'beeswax')
    check('beeswax: L0 defined, L1 partial (executable seed), rest missing',
          profile['defined'] == [0] and profile['partial'] == [1]
          and profile['missing'] == [2, 3, 4])

    blend = scale_profile(manager, 'beeswax-carnauba-blend')
    check("partial rows aren't 'defined'",
          blend['defined'] == [] and blend['partial'] == [0, 1])

    gate = require_scale_levels(manager, 'beeswax', [0])
    check('L0 gate passes for beeswax', gate['ok'])

    gate = require_scale_levels(manager, 'beeswax', [0, 4])
    check('L4 gate refuses honestly',
          not gate['ok'] and gate['blocking'] == [4])
    sugg = gate['suggestions'][0]
    check('refusal carries evidence + knob + action', all(
        sugg.get(k) for k in ('evidence', 'knob', 'action')))
    check('suggestion names the knob class',
          sugg['knob'] == 'MaterialScaleDefinition')

    gate = require_scale_levels(manager, 'beeswax-carnauba-blend', [0])
    check('partial blocks by default', not gate['ok'])
    check("partial suggestion says 'complete it'",
          'PARTIAL' in gate['suggestions'][0]['evidence'])
    gate = require_scale_levels(manager, 'beeswax-carnauba-blend', [0],
                                accept_partial=True)
    check('accept_partial knob admits partial', gate['ok'])

    gate = require_scale_levels(manager, 'unobtainium', [0])
    check('unknown material refuses all levels',
          not gate['ok'] and gate['blocking'] == [0])


def test_formulation_math():
    print('[formulation math]')
    result = predict_formulation_properties(
        components=[{'materialId': 'carnauba', 'weightPercent': 20.0},
                    {'materialId': 'cork', 'weightPercent': 5.0}],
        effects=[
            {'additiveId': 'carnauba', 'propertyName': 'ShoreHardness',
             'effectPerWeightPercent': 0.9},
            {'additiveId': 'carnauba', 'propertyName': 'Viscosity',
             'effectPerWeightPercent': 0.3},
            {'additiveId': 'cork', 'propertyName': 'ShoreHardness',
             'effectPerWeightPercent': -0.4},
        ],
        base_properties={'ShoreHardness': 30.0})
    predicted = result['predicted']
    check('linear blend sums contributions',
          abs(predicted['ShoreHardness'] - (30 + 20*0.9 - 5*0.4)) < 1e-9)
    check('delta-only property blends from 0',
          abs(predicted['Viscosity'] - 6.0) < 1e-9)
    check('contributions are inspectable',
          len(result['contributions']['ShoreHardness']) == 2)

    bounds = mixture_bounds([10.0, 100.0], [0.5, 0.5], rule='hybrid')
    check('Voigt is arithmetic mean', abs(bounds['voigt'] - 55.0) < 1e-9)
    check('Reuss is harmonic mean',
          abs(bounds['reuss'] - (1/(0.05 + 0.005))) < 1e-9)
    check('hybrid = Hill average',
          abs(bounds['value'] - (bounds['voigt'] + bounds['reuss'])/2) < 1e-9)
    check('voigt >= reuss (bounds ordered)',
          bounds['voigt'] >= bounds['reuss'])
    try:
        mixture_bounds([1.0], [0.5])
        check('fraction-sum validation', False)
    except ValueError:
        check('fraction-sum validation', True)

    verdict = score_against_targets(
        predicted={'ShoreHardness': 46.0, 'Viscosity': 6.0},
        targets=[
            {'propertyName': 'ShoreHardness', 'optimumValue': 46.0,
             'hardMinimum': 40.0, 'weight': 2.0},
            {'propertyName': 'Viscosity', 'optimumRangeMin': 5.0,
             'optimumRangeMax': 8.0, 'weight': 1.0},
        ])
    check('meets when in-range and no violations',
          verdict['meets'] and abs(verdict['score'] - 1.0) < 1e-9)

    verdict = score_against_targets(
        predicted={'ShoreHardness': 30.0},
        targets=[{'propertyName': 'ShoreHardness', 'optimumValue': 46.0,
                  'hardMinimum': 40.0, 'weight': 1.0},
                 {'propertyName': 'MeltingPoint', 'optimumValue': 62.0,
                  'weight': 1.0}])
    check('hard-minimum breach is a violation',
          not verdict['meets'] and
          verdict['violations'][0]['bound'] == 'hardMinimum')
    check('unpredicted target reported honestly',
          verdict['unpredicted'] == ['MeltingPoint'])


def test_engines():
    print('[engines]')
    femCap = fem_engine.capability()
    check('FEM capability reports without raising',
          isinstance(femCap, dict) and 'available' in femCap)
    if femCap['available']:
        result = fem_engine.solve_steady_conduction(
            thermal_conductivity=1.0, heat_source=1.0, refine=4)
        check('FEM solve runs', result['ok'])
        # Analytic max T for -∇²T = 1 on unit square ≈ 0.07367
        check('FEM matches analytic peak (±2%)',
              abs(result['maxTemperature'] - 0.07367) < 0.0015)
        doubled = fem_engine.solve_steady_conduction(
            thermal_conductivity=2.0, heat_source=1.0, refine=4)
        check('T scales as q/k',
              abs(doubled['maxTemperature'] * 2
                  - result['maxTemperature']) < 1e-9)
    else:
        check('FEM refusal carries suggestion',
              bool(femCap['suggestion'] and femCap['suggestion']['action']))
        result = fem_engine.solve_steady_conduction(1.0)
        check('FEM solve refuses honestly', result['ok'] is False)
    badK = fem_engine.solve_steady_conduction(0.0)
    check('k<=0 rejected', badK['ok'] is False)

    dftCap = dft_engine.capability()
    check('DFT capability has two layers',
          'structureLayer' in dftCap and 'executionLayer' in dftCap)
    if dftCap['structureLayer']['available']:
        structure = dft_engine.build_bulk_structure('Cu')
        check('ASE builds bulk Cu', structure['ok'])
        check('Cu electron count = 29 per atom',
              structure['electronCount']
              == 29 * structure['atomCount'])
    else:
        check('structure-layer refusal carries suggestions',
              any(s['action'] for s in dftCap['suggestions']))
        structure = dft_engine.build_bulk_structure('Cu')
        check('build refuses honestly', structure['ok'] is False)
    if not dftCap['executionLayer']['available']:
        energy = dft_engine.total_energy('Cu')
        check('SCF refuses honestly without pw.x',
              energy['ok'] is False and 'suggestions' in energy)
    else:
        check('pw.x present (execution layer up)', True)

    # Molecular layer: local pyscf OR delegation to the engines worker.
    check('capability reports molecular layer', 'molecularLayer' in dftCap)
    if dftCap['molecularLayer']['available']:
        h2 = dft_engine.molecular_energy('H 0 0 0; H 0 0 0.74',
                                         basis='sto-3g', xc='lda')
        check('molecular energy runs (H2)', h2['ok'] and h2['converged'])
        check('H2 energy physically sane (-1.3 < E < -0.8 Ha)',
              -1.3 < h2['totalEnergyHa'] < -0.8)
    else:
        result = dft_engine.molecular_energy('H 0 0 0; H 0 0 0.74')
        check('molecular refusal carries the worker knob',
              result['ok'] is False
              and 'MSCI_ENGINES_URL' in result['suggestion']['knob'])
    from materialsScience.engines.remote import remote_post, engines_url
    if not engines_url():
        refusal = remote_post('/dft/molecular-energy', {})
        check('remote_post refuses honestly when unset',
              refusal['ok'] is False and refusal['suggestion']['action'])


def main():
    test_seeds()
    test_presence_and_gates()
    test_formulation_math()
    test_engines()
    print(f'\n{PASS} passed, {FAIL} failed')
    return 1 if FAIL else 0


if __name__ == '__main__':
    sys.exit(main())
