"""
Selftest — MultiScaleSimulationProfile (families) + conformance.

Run from polari-framework/:  python3 -m simulations.selftest_msim_profile

Covers:
  - both profile seeds parse and their taxonomy anchors hold
    (materials-science levels mirror materials_basis.SCALE_LEVELS,
    ladder engines exist in scale_execution.ENGINE_REGISTRY);
  - the pendulum-in-wind msim seed CONFORMS to its declared family
    (the retrofit generalization proof);
  - a deliberately stripped msim yields evidence-bearing gap findings
    + suggestions;
  - deviations from the family's default search policy are notes,
    never failures;
  - the checker never mutates either object.
"""

import copy
import json
from types import SimpleNamespace

from simulations.multi_scale_profile_seed import SEED_MSIM_PROFILES
from simulations.multi_scale_seed import SEED_MULTI_SCALE_SIMS
from simulations.multi_scale_profile_conformance import (
    check_profile_conformance,
)
from materialsScience.materials_basis import SCALE_LEVELS
from materialsScience.scale_execution import ENGINE_REGISTRY

PASS, FAIL = '\033[0;32mPASS\033[0m', '\033[0;31mFAIL\033[0m'
_results = []


def check(label, cond, extra=''):
    _results.append(bool(cond))
    print(f'  [{PASS if cond else FAIL}] {label}'
          f'{("  " + extra) if extra else ""}')


def _profile(name):
    seed = next(p for p in SEED_MSIM_PROFILES if p['name'] == name)
    return SimpleNamespace(**seed)


def _seeds():
    print('\nProfile seeds\n')
    names = [p['name'] for p in SEED_MSIM_PROFILES]
    check('both families seeded', names
          == ['pendulum-in-wind', 'materials-science'], f'names={names}')
    for seed in SEED_MSIM_PROFILES:
        for key in ('scale_levels_json', 'stage_templates_json',
                    'fidelity_ladder_json', 'panel_roster_json',
                    'coupling_shapes_json', 'default_search_policy_json'):
            json.loads(seed[key])
    check('every profile JSON blob parses', True)

    msci = next(p for p in SEED_MSIM_PROFILES
                if p['name'] == 'materials-science')
    levels = json.loads(msci['scale_levels_json'])
    check('materials-science levels mirror materials_basis.SCALE_LEVELS '
          '(one taxonomy home)',
          [(l['order'], l['key']) for l in levels]
          == sorted(SCALE_LEVELS.items()),
          f'levels={[l["key"] for l in levels]}')
    ladder = json.loads(msci['fidelity_ladder_json'])
    named_engines = [e for rung in ladder for e in rung['engines']
                     if e != 'rules-of-mixtures']
    check('ladder engines all exist in ENGINE_REGISTRY',
          all(e in ENGINE_REGISTRY for e in named_engines),
          f'engines={named_engines}')
    check('ladder is ordered screening -> verification -> evidence',
          [r['purpose'] for r in ladder]
          == ['screening', 'verification', 'evidence'])
    check('rungs carry cost classes',
          [r['costClass'] for r in ladder]
          == ['cheap', 'moderate', 'expensive'])


def _conformance():
    print('\nConformance — pendulum retrofit + gap detection\n')
    msim_seed = SEED_MULTI_SCALE_SIMS[0]
    msim = SimpleNamespace(**msim_seed)
    profile = _profile('pendulum-in-wind')

    check('pendulum msim declares its family',
          msim_seed.get('profile_ref') == 'pendulum-in-wind')

    before_msim = copy.deepcopy(vars(msim))
    before_profile = copy.deepcopy(vars(profile))
    report = check_profile_conformance(None, msim, profile)
    check('pendulum msim CONFORMS to its family (retrofit proof)',
          report['conforms'] is True,
          f"gaps={[f['message'] for f in report['findings'] if f['level'] == 'gap']}")
    check('every finding carries evidence',
          all('evidence' in f and f['evidence'] is not None
              for f in report['findings']))
    check('required stage templates + panels all ok',
          all(f['level'] == 'ok' for f in report['findings']
              if f['slot'].startswith(('stage-template:', 'panel:'))
              and f['level'] != 'note'),
          f"levels={[(f['slot'], f['level']) for f in report['findings']]}")
    check('checker never mutates the msim or profile',
          vars(msim) == before_msim and vars(profile) == before_profile)

    # Strip the msim: no stages, no panels — every required slot gaps.
    stripped = SimpleNamespace(**{**msim_seed, 'stages_json': '[]',
                                  'panels_json': '[]'})
    report2 = check_profile_conformance(None, stripped, profile)
    gaps = [f for f in report2['findings'] if f['level'] == 'gap']
    check('stripped msim does NOT conform', report2['conforms'] is False)
    check('each required family slot yields a gap',
          len(gaps) == 2 + 5,  # 2 required stage templates + 5 required panels
          f'gaps={len(gaps)}')
    check('gaps come with actionable suggestions',
          len(report2['suggestions']) == len(gaps)
          and all(s.get('action') and s.get('reason')
                  for s in report2['suggestions']))

    # Deviating search policy is a NOTE, not a failure.
    stages = json.loads(msim_seed['stages_json'])
    for s in stages:
        if s.get('search') is not None:
            s['search']['stopPolicy'] = 'exhaustive'  # family default: firstValid
    deviant = SimpleNamespace(**{**msim_seed,
                                 'stages_json': json.dumps(stages)})
    report3 = check_profile_conformance(None, deviant, profile)
    notes = [f for f in report3['findings']
             if f['slot'].endswith(':search-policy')]
    check('search-policy deviation is a note, conformance still holds',
          report3['conforms'] is True and len(notes) == 1
          and notes[0]['level'] == 'note',
          f'notes={[n["evidence"] for n in notes]}')


if __name__ == '__main__':
    _seeds()
    _conformance()
    total, passed = len(_results), sum(_results)
    print(f'\n{passed}/{total} checks passed')
    raise SystemExit(0 if passed == total else 1)
