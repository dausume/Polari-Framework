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


NAV_KINDS = ('page', 'simspace', 'view', 'tech-node')


if __name__ == '__main__':
    print('== suite: seeds ==')
    use_case_apps = [s for s in SEED_POLARI_APPS if not s['discipline']]
    discipline_apps = [s for s in SEED_POLARI_APPS if s['discipline']]
    check('three use-case apps still seeded (wax shop, judicial, dmv)',
          sorted(s['name'] for s in use_case_apps)
          == ['dmv-policy-analysis', 'judicial-lean',
              'wax-print-shop'])
    check('eight discipline apps seeded (nav-1)',
          sorted(s['name'] for s in discipline_apps)
          == ['app-business', 'app-magnetics',
              'app-materials-science', 'app-mechanical',
              'app-policy', 'app-scorecards-data-analysis',
              'app-software-engineering', 'app-topology-network'])
    check('every seed carries modules + pages + use case',
          all(json.loads(s['modules_json'])
              and json.loads(s['pages_json']) and s['use_case']
              for s in SEED_POLARI_APPS))

    print('== suite: nav-1 menus ==')
    check('every discipline app carries personas + a nav menu',
          all(json.loads(s['personas_json'])
              and json.loads(s['nav_json'])
              for s in discipline_apps))
    items = [(s['name'], it)
             for s in SEED_POLARI_APPS
             for grp in json.loads(s['nav_json'])
             for it in grp['items']]
    check('every nav group has a name and items',
          all(grp['group'] and grp['items']
              for s in SEED_POLARI_APPS
              for grp in json.loads(s['nav_json'])))
    check('every nav item has a label and a known kind',
          all(it['label'] and it['kind'] in NAV_KINDS
              for _, it in items))
    check('routed kinds carry a rooted route; tech-node carries a '
          'ref and no route',
          all((it['kind'] == 'tech-node'
               and it.get('ref') and not it.get('route'))
              or (it['kind'] != 'tech-node'
                  and it.get('route', '').startswith('/'))
              for _, it in items))
    by_name = {s['name']: s for s in SEED_POLARI_APPS}
    mag_items = [it for grp in
                 json.loads(by_name['app-magnetics']['nav_json'])
                 for it in grp['items']]
    check('magnetics: clock-views is a composition-gated VIEW '
          'plus an electromagnetic-systems tree node',
          any(it['kind'] == 'view'
              and it['route'] == '/magnetics/clock-views'
              and it['requires_module'] == 'composition'
              for it in mag_items)
          and any(it['kind'] == 'tech-node'
                  and it['ref'] == 'electromagnetic-systems'
                  for it in mag_items))
    pspp_grps = [g for g in
                 json.loads(by_name['app-materials-science']
                            ['nav_json'])
                 if g['group'] == 'PSPP']
    check('materials-science: PSPP group holds the 11 pspp routes, '
          'all pspp-gated',
          len(pspp_grps) == 1 and len(pspp_grps[0]['items']) == 11
          and all(it['requires_module'] == 'pspp'
                  for it in pspp_grps[0]['items']))
    sw_items = [it for grp in
                json.loads(by_name['app-software-engineering']
                           ['nav_json'])
                for it in grp['items']]
    check('software-engineering: core no-code items carry no module '
          'gate; the test surface is gated on testing',
          all(not it.get('requires_module')
              for it in sw_items if it['route'] != '/testing')
          and any(it['route'] == '/testing'
                  and it['requires_module'] == 'testing'
                  for it in sw_items))
    personas = {p for s in SEED_POLARI_APPS
                for p in json.loads(s['personas_json'])}
    check('personas cover nav-0 §4.4 plus software + network/cloud',
          personas >= {'electrical-engineer', 'mechanical-engineer',
                       'materials-scientist', 'business-operator',
                       'policy-analyst', 'software-engineer',
                       'network-engineer', 'cloud-engineer'})

    print('== suite: upsert convergence (nav-1 seed path) ==')
    # The three live use-case rows predate the nav fields — prove the
    # composition upsert path DELIVERS them (the ten-strikes gotcha)
    # while honoring is_prior=False as a human's row.
    try:
        from composition.seed_upsert import upsert_seed_pairs
    except ImportError:
        upsert_seed_pairs = None
    if upsert_seed_pairs is None:
        check('composition.seed_upsert importable for the nav-1 '
              'seed pass', False)
    else:
        # Use-case rows are STALE (predate the nav fields, like the
        # three live rows); discipline rows are complete.
        stale = {}
        for s in SEED_POLARI_APPS:
            if s['discipline']:
                stale[s['name']] = _ns(**s)
            else:
                stale[s['name']] = _ns(**{
                    k: v for k, v in s.items()
                    if k not in ('nav_json', 'personas_json',
                                 'discipline')})
        stale['judicial-lean'].is_prior = False
        stale['judicial-lean'].use_case = 'human-edited'
        mgr = _ns(objectTables={'PolariAppDefinition': stale},
                  objectTypingDict={'PolariAppDefinition': object})

        class _FakeApp:
            def __init__(self, manager=None, **fields):
                self.__dict__.update(fields)

        [report] = upsert_seed_pairs(
            mgr, [('PolariAppDefinition', _FakeApp,
                   SEED_POLARI_APPS)], tag='SelftestAppsNav')
        updated = {u['name']: u['fields']
                   for u in report['updated']}
        check('stale prior rows gain exactly the missing nav fields',
              set(updated.get('wax-print-shop', []))
              == {'nav_json', 'personas_json', 'discipline'}
              and 'app-magnetics' not in updated)
        check('delivered fields now live on the stale row',
              stale['wax-print-shop'].nav_json == '[]'
              and stale['wax-print-shop'].discipline == ''
              and stale['dmv-policy-analysis'].personas_json == '[]')
        check('is_prior=False row is skipped as customized, '
              'edits intact',
              'judicial-lean' in report['skipped_custom']
              and stale['judicial-lean'].use_case == 'human-edited'
              and not hasattr(stale['judicial-lean'], 'nav_json'))
        check('no insert/update errors from the upsert pass',
              not report['errors'] and not report['inserted'])

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
