"""
Selftest for Polari-Apps (tt-12).

Run from polari-framework/:  python3 -m polariapps.selftest_apps

Stdlib-only (SimpleNamespace rows). Covers: seed coherence, plan
computation (already-placed / needs-assignment / missing, honest
readiness), the exportable package + its validation, and the
rows-only idempotent apply.
"""

import json
import types

from polariapps.apps_analysis import (
    app_plan, apply_app, export_app, validate_app_document,
)
from polariapps.apps_seed import SEED_POLARI_APPS

_results = []


def check(label, cond, extra=''):
    _results.append((label, bool(cond)))
    print(f'{"PASS" if cond else "FAIL"}: {label}'
          + (f' — {extra}' if extra and not cond else ''))


def _ns(**fields):
    return types.SimpleNamespace(**fields)


def _mgr():
    return _ns(objectTables={
        'PolariAppDefinition': {
            s['name']: _ns(**s) for s in SEED_POLARI_APPS},
        'InstanceDefinition': {
            'prf-a': _ns(name='prf-a', kind='prf-backend',
                         topology_name='staging-a'),
            'engines': _ns(name='engines', kind='engines',
                           topology_name='staging-a'),
        },
        'ModuleAssignment': {
            'waxprint@prf-a': _ns(
                name='waxprint@prf-a', module_name='waxprint',
                instance_name='prf-a', state='enabled',
                topology_name='staging-a'),
            'materialsScience.fem@engines': _ns(
                name='materialsScience.fem@engines',
                module_name='materialsScience.fem',
                instance_name='engines', state='enabled',
                topology_name='staging-a'),
        },
        'PolariModule': {
            m: _ns(name=m, status='installed')
            for m in ('waxprint', 'materialsScience', 'mathshapes',
                      'simulations', 'waxsupply', 'supplychain',
                      'polariNoCode', 'scoring', 'dmvdata')},
    })


if __name__ == '__main__':
    print('== suite: seeds ==')
    check('three apps seeded (wax shop, judicial, dmv)',
          sorted(s['name'] for s in SEED_POLARI_APPS)
          == ['dmv-policy-analysis', 'judicial-lean',
              'wax-print-shop'])
    check('every seed carries modules + pages + use case',
          all(json.loads(s['modules_json'])
              and json.loads(s['pages_json']) and s['use_case']
              for s in SEED_POLARI_APPS))

    print('== suite: plan computation ==')
    mgr = _mgr()
    plan = app_plan(mgr, 'wax-print-shop', 'staging-a')
    by_module = {p['module']: p for p in plan['placements']}
    check('plan ok with per-module rows',
          plan.get('ok') and len(by_module) == 6)
    check('waxprint already placed on prf-a',
          by_module['waxprint']['status'] == 'already-placed'
          and by_module['waxprint']['instances'] == ['prf-a'])
    check('dotted assignment satisfies its top-level module',
          by_module['materialsScience']['status']
          == 'already-placed')
    needs = by_module['mathshapes']
    check('unplaced module suggests the backend instance + exact '
          'command', needs['status'] == 'needs-assignment'
          and needs['suggestedInstance'] == 'prf-a'
          and needs['suggestedCommand']
          == 'pol allocate mathshapes prf-a')
    check('readiness is the placed fraction',
          abs(plan['readiness'] - 2 / 6) < 1e-9,
          str(plan['readiness']))
    del mgr.objectTables['PolariModule']['mathshapes']
    plan = app_plan(mgr, 'wax-print-shop', 'staging-a')
    missing = [p for p in plan['placements']
               if p['module'] == 'mathshapes'][0]
    check('module absent from the image is honestly MISSING',
          missing['status'] == 'missing'
          and 'not in this image' in missing['suggestedCommand'])
    check('unknown app refused honestly',
          not app_plan(mgr, 'nope', 'staging-a').get('ok'))
    check('unknown topology refused honestly',
          not app_plan(mgr, 'judicial-lean', 'nope').get('ok'))

    print('== suite: exportable package ==')
    mgr = _mgr()
    exported = export_app(mgr, 'wax-print-shop', 'staging-a')
    doc = exported['document']
    check('package kind + schema + app + plan',
          doc['kind'] == 'polari-app-package'
          and doc['schema_version'] == '1'
          and doc['app']['name'] == 'wax-print-shop'
          and doc['plan']['topology'] == 'staging-a'
          and len(doc['plan']['placements']) == 6)
    check('package is credential-free (no secret-shaped keys)',
          not any(k in json.dumps(doc).lower()
                  for k in ('password', 'secret', 'token')))
    check('document validation accepts the export',
          validate_app_document(doc) == '')
    check('non-app document refused honestly',
          validate_app_document({'kind': 'nope'}) != '')
    check('wrong schema refused honestly',
          validate_app_document({'kind': 'polari-app-package',
                                 'schema_version': '99',
                                 'app': {'name': 'x'}}) != '')

    print('== suite: rows-only apply ==')
    mgr = _mgr()
    created_rows = []
    result = apply_app(
        mgr, 'wax-print-shop', 'staging-a',
        assignment_factory=lambda **f: created_rows.append(
            _ns(**f)) or created_rows[-1])
    check('apply creates rows for needs-assignment modules only',
          sorted(c['module'] for c in result['created'])
          == ['mathshapes', 'simulations', 'supplychain',
              'waxsupply'])
    check('already-placed modules skipped with reasons',
          any('already placed' in s['reason']
              for s in result['skipped']))
    check('rows carry the app provenance note',
          all('wax-print-shop' in r.notes for r in created_rows))
    check('apply suggests the human deploy command',
          result['suggestedCommand'] == 'pol topology apply --plan')
    # Idempotence: absorb the created rows, re-apply => no new rows.
    for row in created_rows:
        mgr.objectTables['ModuleAssignment'][row.name] = row
    again = apply_app(mgr, 'wax-print-shop', 'staging-a',
                      assignment_factory=lambda **f: _ns(**f))
    check('re-apply is idempotent (everything already placed)',
          again['created'] == [] and len(again['skipped']) == 6)

    failed = [label for label, ok in _results if not ok]
    print(f'\n{len(_results) - len(failed)}/{len(_results)} checks '
          f'passed' + (f'; FAILED: {failed}' if failed else ''))
    raise SystemExit(1 if failed else 0)
