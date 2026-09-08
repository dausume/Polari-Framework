"""
Self-test for pspp-9 exposure + performance scenarios: descriptor
gates, the two v1 engines (bounds math + water transport), honest
notes/refusals, exposure vocabulary.

Run from polari-framework/ (modules/ on the path):
    python3 -m pspp.performance_scenarios_selftest
"""

import json
import sys
from types import SimpleNamespace

from pspp.exposure_scenarios_basis import SEED_EXPOSURE_SCENARIOS
from pspp.performance_scenarios_basis import run_performance_scenario

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


GP = 'metakaolin-geopolymer#cured-solid'


def _structure_row(name, **descriptors):
    return SimpleNamespace(
        name=name, state_key=GP, scale_level=0, domain_type='',
        descriptors_json=json.dumps(descriptors), status='defined')


def _manager(with_permeability=True):
    descriptors = {'bulkDensity': 1850.0, 'totalPorosity': 0.28,
                   'openPorosity': 0.19, 'connectedPorosity': 0.11,
                   'moistureState': 'saturated',
                   'reactionExtent': 0.85,
                   'phaseFractions': {'gel': 0.6, 'quartz': 0.4}}
    if with_permeability:
        descriptors['hydraulicPermeability'] = 2.1e-14
    return SimpleNamespace(objectTables={
        'ScaleStructureDefinition': {
            f'{GP}@L0': _structure_row(f'{GP}@L0', **descriptors)},
    })


def _scenario(engine, exposure='hydroponic', params=None):
    return {'name': f'test-{engine}', 'initial_state_key': GP,
            'exposure_scenario': exposure,
            'performance_engine': engine,
            'parameters_json': params or {}}


def test_exposures():
    print('[exposure vocabulary]')
    names = [e['name'] for e in SEED_EXPOSURE_SCENARIOS]
    check('book-relevant exposures seeded (hydroponic, freeze-thaw, '
          'acid, fire, marine, outdoor)', all(
              n in names for n in ('hydroponic', 'freeze-thaw',
                                   'acid', 'fire', 'marine',
                                   'outdoor')))


def test_water_transport():
    print('[water-transport engine]')
    ok = run_performance_scenario(
        _manager(), _scenario('water-transport'))
    check('hydroponic scenario claims connected porosity + '
          'permeability', ok['ok'] and len(ok['claims']) == 2
          and any(c['property'] == 'hydraulicPermeability'
                  for c in ok['claims']))
    check('permeability claim points at the live Darcy engine', any(
        'darcy' in a.lower() for c in ok['claims']
        for a in c['assumptions']))

    noK = run_performance_scenario(
        _manager(with_permeability=False),
        _scenario('water-transport'))
    check('missing permeability yields the porosity claim + a '
          'refusal-shaped note naming the descriptor',
          noK['ok'] and len(noK['claims']) == 1
          and 'hydraulicPermeability' in noK['note'])

    dry = run_performance_scenario(
        _manager(), _scenario('water-transport', exposure='fire'))
    check('no-water exposure honestly reports nothing to transport',
          dry['ok'] and dry['claims'] == []
          and 'no water contact' in dry['note'])


def test_elastic_bounds():
    print('[elastic-bounds engine]')
    params = {'phases': [
        {'name': 'gel', 'modulus_gpa': 3.0, 'volume_fraction': 0.7},
        {'name': 'quartz', 'modulus_gpa': 70.0,
         'volume_fraction': 0.3}]}
    result = run_performance_scenario(
        _manager(), _scenario('elastic-bounds', params=params))
    voigt = 0.7 * 3.0 + 0.3 * 70.0
    reuss = 1.0 / (0.7 / 3.0 + 0.3 / 70.0)
    values = {c['property']: c['value'] for c in result['claims']}
    check('Voigt/Reuss bounds match hand math (23.1 / ~4.21)',
          result['ok']
          and abs(values['elasticModulusVoigtUpper'] - voigt) < 1e-9
          and abs(values['elasticModulusReussLower'] - reuss) < 1e-6)
    check('claims are labeled rules-of-mixtures BOUNDS with the '
          'porosity named gap', all(
              c['evidenceMethod'] == 'rules-of-mixtures'
              and any('named gap' in a for a in c['assumptions'])
              for c in result['claims']))

    noPhases = run_performance_scenario(
        _manager(), _scenario('elastic-bounds'))
    check('undeclared constituents refused (never guessed)',
          noPhases['ok'] is False
          and 'DECLARED' in noPhases['suggestion'])


def test_refusals():
    print('[gates + refusals]')
    bare = SimpleNamespace(objectTables={})
    gated = run_performance_scenario(
        bare, _scenario('water-transport'))
    check('state with no structure rows refused via the descriptor '
          'gate', gated['ok'] is False
          and 'openPorosity' in str(gated.get('missing', '')))
    unknown = run_performance_scenario(
        _manager(), _scenario('carbonation'))
    check('unknown engine refused, names the registry AND the '
          'degradation gaps', unknown['ok'] is False
          and 'elastic-bounds' in unknown['suggestion']
          and 'carbonation' in unknown['suggestion'])
    badExposure = run_performance_scenario(
        _manager(), _scenario('water-transport', exposure='moon'))
    check('unknown exposure refused listing the vocabulary',
          badExposure['ok'] is False
          and 'hydroponic' in str(badExposure['suggestion']))


def main():
    test_exposures()
    test_water_transport()
    test_elastic_bounds()
    test_refusals()
    print(f'\n{PASS} passed, {FAIL} failed')
    return 1 if FAIL else 0


if __name__ == '__main__':
    sys.exit(main())
