"""
Selftest — per-material detail (msci-28): the data behind the material
detail view (properties + meanings + scenario context + per-level rows).

Run from polari-framework/:
    python3 -m materialsScience.selftest_material_detail

Covers: meaning vocabulary integrity (aliases resolve, every seed key
canonical); detail payload for a real material (identity, thermal
window, worksheet priors labeled as priors, computed results carrying
level + engine source, meanings attached); the blend-effects scenario
block for an additive material; level scoping (L0/L1/L4 focus, L2/L3
hidden until rows exist, missing focus level carries the earn hint);
unknown material -> honest 404-shaped error naming known materials;
unmatched property keys -> knobs-and-suggestions (never auto-created).
"""

import json
from types import SimpleNamespace

from materialsScience.material_detail import (
    FOCUS_LEVELS, build_material_detail,
)
from materialsScience.materials_basis_seed import (
    SEED_MS_MATERIALS, SEED_MS_SCALE_DEFINITIONS,
)
from materialsScience.property_meanings import (
    PROPERTY_MEANING_VOCAB, SEED_PROPERTY_MEANINGS, meaning_index,
)
from materialsScience.thermal_windows import SEED_THERMAL_PROFILES

PASS, FAIL = '\033[0;32mPASS\033[0m', '\033[0;31mFAIL\033[0m'
_results = []


def check(label, cond, extra=''):
    _results.append(bool(cond))
    print(f'  [{PASS if cond else FAIL}] {label}'
          f'{("  " + extra) if extra else ""}')


def _rows(seed_list):
    return {i: SimpleNamespace(**r) for i, r in enumerate(seed_list)}


def _mgr(extra_scale_rows=(), searches=()):
    return SimpleNamespace(objectTables={
        'MaterialsScienceMaterial': _rows(SEED_MS_MATERIALS),
        'MaterialScaleDefinition': _rows(
            list(SEED_MS_SCALE_DEFINITIONS) + list(extra_scale_rows)),
        'ThermalProcessingProfile': _rows(SEED_THERMAL_PROFILES),
        'MaterialPropertyMeaning': _rows(SEED_PROPERTY_MEANINGS),
        'FormulationSearchDefinition': _rows(searches),
    })


if __name__ == '__main__':
    print('\nPer-material detail (msci-28)\n')

    print('meaning vocabulary')
    idx = meaning_index(_mgr())
    check('every canonical key resolves through the index',
          all(key.lower() in idx for key in PROPERTY_MEANING_VOCAB))
    check("engine result aliases resolve (effectiveK, gapEv, "
          "effectiveMu, effectiveSigma)",
          all(a in idx for a in
              ('effectivek', 'gapev', 'effectivemu', 'effectivesigma')))
    check("formulation keys resolve (ShoreHardness, Viscosity)",
          'shorehardness' in idx and 'viscosity' in idx)
    check('every seed row carries meaning + scenario context',
          all(s['meaning'] and s['scenario_context']
              for s in SEED_PROPERTY_MEANINGS))

    print('\ndetail payload — beeswax (thermal + priors + computed)')
    executed_row = {
        'name': 'beeswax@L1', 'material_name': 'beeswax',
        'scale_level': 1, 'scale_category': 'continuum',
        'definition_class': 'EngineComputation', 'definition_ref': '',
        'status': 'defined', 'derived_from_name': 'beeswax@L0',
        'derivation_method': 'homogenized',
        'parameters_json': json.dumps({
            'engine': 'fem.effective-conductivity',
            'inputs': {'matrixK': 0.25},
            'result': {'ok': True, 'effectiveK': 0.2593,
                       'withinBounds': True},
        }),
        'provenance_id': '', 'notes': '',
    }
    search = {
        'name': 'wax-derivation-screening',
        'base_material_name': 'beeswax',
        'base_properties_json': json.dumps({
            'ShrinkageRate': 3.0, 'ShoreHardness': 10.0}),
    }
    mgr = _mgr(extra_scale_rows=[executed_row], searches=[search])
    # The seed list also has a beeswax@L1 partial row; the executed one
    # is appended after it, so the level shows both — fine for a detail
    # view (variants are explicit rows by design).
    report = build_material_detail(mgr, 'beeswax')
    check('ok payload with identity', report['ok']
          and report['material']['displayName'] == 'Beeswax')
    keys = {p['key'] for p in report['properties']}
    check('thermal window properties present',
          {'meltRange', 'smokePoint'} <= keys, str(sorted(keys)))
    check('worksheet priors present and labeled as priors',
          any(p['key'] == 'ShrinkageRate'
              and 'prior' in p['provenance'] for p in report['properties']))
    check('computed effectiveK travels with level + engine source',
          any(p['key'] == 'effectiveK' and p['level'] == 1
              and 'fem.effective-conductivity' in p['source']
              for p in report['properties']))
    check('meanings attached (effectiveK -> thermal conductivity)',
          any(p['key'] == 'effectiveK'
              and p['label'] == 'Thermal conductivity'
              and p['scenarioContext']
              for p in report['properties']))
    check('withinBounds surfaces but has no meaning row -> suggestion',
          any(p['key'] == 'withinBounds' and p['meaning'] is None
              for p in report['properties'])
          and any('withinBounds' in s['evidence']
                  for s in report['suggestions'])
          and all(s['knob'] == 'MaterialPropertyMeaning'
                  for s in report['suggestions']))
    check('thermal scenario block present with no-volatiles note',
          report['thermal'] and 'no-volatiles'
          in report['thermal']['scenarioNote'])

    print('\nlevel scoping (Dustin 2026-07-07: FEM/DFT focus)')
    shown = [lvl['level'] for lvl in report['levels']]
    check('focus levels shown', shown == sorted(set(FOCUS_LEVELS)),
          str(shown))
    check('L2/L3 hidden with the engines-arrive note',
          report['hiddenLevels']
          and report['hiddenLevels']['levels'] == [2, 3])
    l4 = next(l for l in report['levels'] if l['level'] == 4)
    check('missing focus level carries the earn hint (knob + action)',
          l4['status'] == 'missing' and l4['earnHint']
          and l4['earnHint']['knob'] == 'MaterialScaleDefinition')
    l1 = next(l for l in report['levels'] if l['level'] == 1)
    check('level rows opened: parameters split from result',
          any(r['result'] and r['result'].get('effectiveK') == 0.2593
              and 'result' not in r['parameters']
              for r in l1['rows']))
    check('lineage travels on the level row',
          any(r['derivedFrom'] == 'beeswax@L0' for r in l1['rows']))

    print('\nblend effects (additive scenario)')
    report2 = build_material_detail(mgr, 'carnauba-wax')
    blend = report2['blendEffects']
    check('carnauba blend effects present', bool(blend
          and blend.get('available') and blend['effects']))
    if blend and blend.get('effects'):
        check('effects carry intent + per-wt% + provenance',
              all('intent' in e and 'perWtPercent' in e
                  and e['provenance'] for e in blend['effects']))
        check('effect properties gain meanings where the vocab knows '
              'them',
              any(e['meaning'] for e in blend['effects']))

    print('\nhonest errors')
    bad = build_material_detail(mgr, 'unobtainium')
    check('unknown material named + known list returned',
          not bad['ok'] and 'unobtainium' in bad['error']
          and 'beeswax' in bad['knownMaterials'])

    failed = _results.count(False)
    print(f'\n{len(_results) - failed}/{len(_results)} checks passed\n')
    raise SystemExit(1 if failed else 0)
