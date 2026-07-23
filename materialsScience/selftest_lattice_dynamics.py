"""
Self-test for the lattice-dynamics engine (ssp-4).

Physics invariants (generous bands, small samplings to stay fast):
acoustic sum rule at Gamma, stability of fitted-LJ fcc, sqrt(k/m)
mass scaling of spring phonons, Cauchy relation C12 = C44 (intrinsic
to pair potentials at equilibrium), bulk-modulus route consistency,
honest instability + refusal shapes.

Run from polari-framework/:
    python3 -m materialsScience.selftest_lattice_dynamics
"""

import json
import sys

from materialsScience.engines import lattice_dynamics_engine as lde
from materialsScience.crystal_structures_seed import (
    SEED_CRYSTAL_STRUCTURES,
)
from materialsScience.scale_execution import (
    ENGINE_REGISTRY, execute_scale_definition,
)

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


def _seed(name):
    return next(s for s in SEED_CRYSTAL_STRUCTURES
                if s['name'] == name)


def _fcc(element):
    return {'name': f'test-{element}', 'space_group': 225,
            'space_group_setting': 1,
            'cell_a': 4.05, 'cell_b': 4.05, 'cell_c': 4.05,
            'alpha': 90.0, 'beta': 90.0, 'gamma': 90.0,
            'basis_json': json.dumps(
                [{'element': element, 'frac': [0, 0, 0]}]),
            'bond_cutoff_scale': 1.2}


def test_capability_and_registry():
    print('[capability + registry]')
    cap = lde.capability()
    check('always available with named gaps',
          cap['available'] and not
          cap['gaps']['dftPhonons']['available'])
    check('ssp engines registered',
          {'ssp.phonon-dispersion', 'ssp.elastic-constants'}
          <= set(ENGINE_REGISTRY))


def test_fitted_lj_fcc_phonons():
    print('[LJ fcc phonons, fitted sigma]')
    result = lde.phonon_dispersion(
        _seed('aluminum-fcc'),
        {'kind': 'lennard-jones', 'epsilonEv': 0.39},
        fit_sigma=True, npoints=60, dos_grid=6)
    check('runs ok', result['ok'])
    if not result['ok']:
        return
    check('primitive fcc -> exactly 3 branches',
          result['branches'] == 3 and result['nAtoms'] == 1)
    check('acoustic sum rule at Gamma',
          result['acousticSumHolds']
          and result['gammaAcousticMaxThz'] < 0.02)
    check('fitted lattice is stable (no imaginary modes)',
          result['stable'])
    check('residual pressure ~ 0 after sigma fit',
          abs(result['residualPressureGpa']) < 0.5)
    check('fitted sigma reported as evidence',
          0.9 * 2.55 < result.get('fittedSigmaA', 0) < 1.1 * 2.7)
    check('standard fcc path labels (G, X, L present)',
          {'G', 'X', 'L'} <= set(result['pathLabels']))
    check('DOS histogram present',
          sum(result['dos']['counts']) > 0)
    check('validity names the DFPT gap',
          'DFPT' in result['validity'])


def test_spring_mass_scaling():
    print('[spring model: sqrt(k/m) scaling]')
    light = lde.phonon_dispersion(
        _fcc('Al'), {'kind': 'spring', 'stiffnessEvA2': 2.0},
        npoints=25, dos_grid=4)
    heavy = lde.phonon_dispersion(
        _fcc('Au'), {'kind': 'spring', 'stiffnessEvA2': 2.0},
        npoints=25, dos_grid=4)
    check('both spring runs ok', light['ok'] and heavy['ok'])
    if not (light['ok'] and heavy['ok']):
        return
    peak = lambda r: max(max(row) for row in r['frequenciesThz'])
    ratio = peak(light) / peak(heavy)
    expected = (196.966569 / 26.9815385) ** 0.5
    check(f'frequency ratio {ratio:.3f} matches sqrt(m_Au/m_Al) '
          f'{expected:.3f}', abs(ratio - expected) < 0.01)
    two_atom = lde.phonon_dispersion(
        _seed('silicon-diamond'),
        {'kind': 'spring', 'stiffnessEvA2': 6.0}, npoints=25,
        dos_grid=4)
    check('2-atom primitive -> 6 branches (3 acoustic + 3 optical)',
          two_atom['ok'] and two_atom['branches'] == 6)


def test_elastic_constants():
    print('[cubic elastic constants]')
    result = lde.elastic_constants(
        _seed('aluminum-fcc'),
        {'kind': 'lennard-jones', 'epsilonEv': 0.39},
        fit_sigma=True)
    check('runs ok', result['ok'])
    if not result['ok']:
        return
    check('C11 > C12 > 0 and C44 > 0',
          result['c11Gpa'] > result['c12Gpa'] > 0
          and result['c44Gpa'] > 0)
    check('Cauchy relation C12 = C44 (pair-potential signature)',
          abs(result['c12Gpa'] - result['c44Gpa'])
          < 0.02 * result['c44Gpa'] + 0.5)
    check('bulk modulus routes agree (EOS vs elastic)',
          result['bulkRoutesAgree'])
    check('clamped-ion honesty in validity',
          'clamped-ion' in result['validity'])


def test_instability_and_refusals():
    print('[instability + refusals]')
    squeezed = lde.phonon_dispersion(
        _seed('aluminum-fcc'),
        {'kind': 'lennard-jones', 'epsilonEv': 0.39,
         'sigmaA': 1.909}, npoints=25, dos_grid=4)
    check('far-off sigma -> honest instability verdict',
          squeezed['ok'] and not squeezed['stable']
          and squeezed['minFrequencyThz'] < -1.0)
    verdict = lde.phonon_dispersion(
        _seed('aluminum-fcc'), {'kind': 'unobtainium'})
    check('unknown potential kind refuses',
          not verdict['ok']
          and verdict['suggestion']['knob'] == 'potential.kind')
    verdict = lde.phonon_dispersion(
        _seed('aluminum-fcc'),
        {'kind': 'lennard-jones', 'epsilonEv': 0.39, 'sigmaA': 2.6},
        npoints=5)
    check('npoints out of range refuses',
          not verdict['ok'] and 'npoints' in verdict['error'])
    verdict = lde.elastic_constants(
        _seed('graphite-hexagonal'),
        {'kind': 'lennard-jones', 'epsilonEv': 0.01, 'sigmaA': 3.4})
    check('non-cubic elastic refuses honestly',
          not verdict['ok'] and 'CUBIC' in verdict['error'])
    verdict = lde.elastic_constants(
        _seed('aluminum-fcc'), {'kind': 'spring',
                                'stiffnessEvA2': 2.0})
    check('spring elastic refuses (no radial preload)',
          not verdict['ok'] and 'radial' in verdict['error'])
    verdict = lde.phonon_dispersion(
        _seed('aluminum-fcc'),
        {'kind': 'lennard-jones', 'epsilonEv': 0.0}, fit_sigma=True)
    check('fit without epsilon refuses naming the knob',
          not verdict['ok']
          and verdict['suggestion']['knob'] == 'potential.epsilonEv')


def test_scale_row_execution():
    print('[EngineComputation scale row -> ssp engine]')
    from types import SimpleNamespace

    class _FakeDB:
        def saveInstanceInDB(self, row):
            return True

    structure_row = SimpleNamespace(**_seed('aluminum-fcc'))
    scale_row = SimpleNamespace(
        name='test-al@L3-phonons', material_name='test-al',
        scale_level=3, status='partial',
        definition_class='EngineComputation',
        parameters_json=json.dumps({
            'engine': 'ssp.phonon-dispersion',
            'inputs': {'structureName': 'aluminum-fcc',
                       'potential': {'kind': 'lennard-jones',
                                     'epsilonEv': 0.39},
                       'fitSigmaToStructure': True,
                       'npoints': 25, 'dosGrid': 4}}))
    manager = SimpleNamespace(
        objectTables={
            'MaterialScaleDefinition': {scale_row.name: scale_row},
            'CrystalStructureDefinition': {
                'aluminum-fcc': structure_row}},
        db=_FakeDB())
    verdict = execute_scale_definition(manager,
                                       'test-al@L3-phonons')
    check('scale row executes through structureName resolution',
          verdict['ok'])
    if verdict['ok']:
        stored = json.loads(scale_row.parameters_json)
        check('phonon result stored ON the row',
              stored['result']['branches'] == 3)
        check('status partial -> defined',
              scale_row.status == 'defined')
    scale_row2 = SimpleNamespace(
        name='test-bad@L3', material_name='x', scale_level=3,
        status='partial', definition_class='EngineComputation',
        parameters_json=json.dumps({
            'engine': 'ssp.phonon-dispersion',
            'inputs': {'structureName': 'nope'}}))
    manager.objectTables['MaterialScaleDefinition'][
        'test-bad@L3'] = scale_row2
    verdict = execute_scale_definition(manager, 'test-bad@L3')
    check('unknown structureName refuses honestly',
          not verdict['ok'] and 'nope' in verdict['error'])


def main():
    test_capability_and_registry()
    test_fitted_lj_fcc_phonons()
    test_spring_mass_scaling()
    test_elastic_constants()
    test_instability_and_refusals()
    test_scale_row_execution()
    print(f'\n{PASS} passed, {FAIL} failed')
    return 1 if FAIL else 0


if __name__ == '__main__':
    sys.exit(main())
