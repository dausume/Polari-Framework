"""
Selftest for Polari-Apps (tt-12).

Run from polari-framework/:  python3 -m polariapps.apps_selftest

Stdlib-only (SimpleNamespace rows). Covers: seed coherence, plan
computation (already-placed / needs-assignment / missing, honest
readiness), the exportable package + its validation, and the
rows-only idempotent apply.
"""

import json
import types

from polariapps.custom.apps_analysis import (
    app_plan, apply_app, export_app, validate_app_document,
)
from polariapps.custom.apps_nav import app_nav_report, apps_nav
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
    check('use-case apps seeded (wax shop, judicial, dmv, nutrition + the '
          'sep-4 engine tiles + the ai-4 linkage apps)',
          sorted(s['name'] for s in use_case_apps)
          == ['ai-assistant-reasoning', 'ai-voice',
              'dmv-policy-analysis', 'engine-cad', 'engine-msci',
              'judicial-lean', 'nutrition-planner', 'wax-print-shop'])
    check('ten discipline apps seeded (nav-1 + mtg-3 collaboration '
          '+ ret-1b archipelago)',
          sorted(s['name'] for s in discipline_apps)
          == ['app-archipelago', 'app-business', 'app-collaboration',
              'app-magnetics', 'app-materials-science',
              'app-mechanical', 'app-policy',
              'app-scorecards-data-analysis',
              'app-software-engineering', 'app-topology-network'])
    # ai-4: the two linkage apps ride the CORE seam — an empty
    # modules list is their honest shape, not an omission.
    check('every seed carries modules + pages + use case '
          '(ai-4 linkage apps: core seam, modules honestly empty)',
          all((json.loads(s['modules_json'])
               or s['name'].startswith('ai-'))
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
                  and it['ref'] == 'electronics/electromagnetic-systems'
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
    check('every discipline app promotes at least one group to the '
          'top bar, and none promotes all of them (the side map '
          'stays the complete map)',
          all(0 < sum(1 for g in json.loads(s['nav_json'])
                      if g.get('top_menu'))
              <= max(1, len(json.loads(s['nav_json'])) - 1)
              for s in discipline_apps))
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
        from moduleService.seed_upsert import upsert_seed_pairs
    except ImportError:
        upsert_seed_pairs = None
    if upsert_seed_pairs is None:
        check('moduleService.seed_upsert importable for the nav-1 '
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
        # The live legacy rows restore with is_prior=None (NULL —
        # they predate the column); None is a backfill, not a
        # human's mark, so the row must still converge.
        stale['wax-print-shop'].is_prior = None
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

    print('== suite: nav-2 tri-state availability ==')
    navmgr = _ns(objectTables={
        'PolariAppDefinition': {
            s['name']: _ns(**s) for s in SEED_POLARI_APPS}})
    # Fake gating: composition absent, everything else enabled.
    gate = lambda m: m != 'composition'
    reqs = {'composition': ['mathshapes']}
    result = apps_nav(navmgr, feature_check=gate, requires_map=reqs)
    napps = {a['name']: a for a in result['apps']}
    check('nav payload covers all 18 apps (14 + sep-4 engine '
          'tiles + ai-4 linkage apps), gating readable',
          result['ok'] and result['gatingReadable']
          and len(napps) == 18)
    check('discipline apps sort before use-case apps',
          [a['discipline'] != '' for a in result['apps']].index(False)
          == 10)
    mag = napps['app-magnetics']
    mag_items = [it for g in mag['nav'] for it in g['items']]
    absent = [it for it in mag_items
              if it['availability'] == 'absent']
    check('absent module item KEPT with bringup affordance + '
          'requires chain (m1-8: the M1 view joins the goals '
          'view behind composition; m2-8 adds the M2 rotation '
          'view — three now, and the count is pinned on purpose '
          'so a new gated item cannot slip in unnoticed)',
          len(absent) == 3
          and all(it['requiresModule'] == 'composition'
                  and it['bringup']['route'] == '/modules/bringup'
                  and it['bringup']['requires'] == ['mathshapes']
                  for it in absent))
    check('ungated + enabled-module items are enabled',
          all(it['availability'] == 'enabled'
              for it in mag_items if it not in absent))
    check('topMenu placement carried through',
          [g['topMenu'] for g in mag['nav']] == [True, False])
    check('persona index maps EE to app-magnetics',
          result['personas']['electrical-engineer']
          == ['app-magnetics'])
    check('per-module tri-state strip computed server-side',
          mag['moduleStates'] == {'magnetics': 'enabled',
                                  'motors': 'enabled',
                                  'composition': 'absent',
                                  'gears': 'enabled'})
    check('use-case app gets a SYNTHESIZED pages group',
          napps['wax-print-shop']['navSynthesized']
          and napps['wax-print-shop']['nav'][0]['group'] == 'Pages'
          and napps['wax-print-shop']['nav'][0]['items'][0]['route']
          == '/wax-print-sim')
    # Gating machinery unavailable => tri-state unknown, never
    # guessed; ungated core items stay enabled.
    unknown = apps_nav(navmgr, feature_check=None, requires_map={})
    uit = [it for a in unknown['apps'] for g in a['nav']
           for it in g['items']]
    check('gating unreadable => gated items unknown, core items '
          'still enabled, flagged in payload',
          not unknown['gatingReadable']
          and all(it['availability'] == 'unknown'
                  for it in uit if it.get('requiresModule'))
          and all(it['availability'] == 'enabled'
                  for it in uit if not it.get('requiresModule')))
    one = app_nav_report(navmgr, 'app-software-engineering',
                         feature_check=lambda m: m != 'testing',
                         requires_map={})
    check('single-app report works; testing item absent, no chain '
          'when registry unreadable, and dyn-6 offers the admit act',
          one['ok'] and any(
              it.get('requiresModule') == 'testing'
              and it['availability'] == 'absent'
              and it['bringup']['route'] == '/modules/bringup'
              and 'requires' not in it['bringup']
              and it['bringup']['admit']['withDeps']
              == 'POST /modules/testing/admit?withDeps=true'
              for g in one['nav'] for it in g['items']))
    check('unknown app refused honestly',
          not app_nav_report(navmgr, 'nope',
                             feature_check=gate)['ok'])

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
    check('sep-2: export carries the MENU fields the apply side '
          'reads (nav_json/personas_json/discipline)',
          all(k in doc['app'] for k in
              ('nav_json', 'personas_json', 'discipline')))
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

    print('== suite: sep-7 per-app permission profiles ==')
    import os
    from polariapps.apps_permissions_basis import (
        AppPermissionProfile, SEED_PERMISSION_PROFILES,
        classes_for_app, permission_verdict, resolve_grants)
    from accessControl.app_permissions_gate import (
        ADVISORY_HEADER, crude_permission_gate)

    mgr = _mgr()
    # Seeds are UNPUBLISHED templates bound to NO groups (never
    # invent groups). First pin that they grant nothing as-seeded,
    # then do what authoring does: bind EXISTING group names +
    # publish.
    profiles = {}
    for seed in SEED_PERMISSION_PROFILES:
        row = AppPermissionProfile(**seed)
        profiles[row.name] = row
    mgr.objectTables['AppPermissionProfile'] = profiles
    check('sep-7: template seeds are unpublished + group-less — '
          'they grant NOTHING until bound to real groups',
          all(not s['published']
              and json.loads(s['kc_groups_json']) == []
              for s in SEED_PERMISSION_PROFILES)
          and resolve_grants(mgr, {'roles': ['anything'],
                                   'raw_claims': {}})['profiles']
          == [])
    # bind-and-publish (what the auth section does with a KNOWN
    # group picked from /api/groups):
    profiles['wax-print-shop-operator'].kc_groups_json = \
        '["wax-print-shop-operators"]'
    profiles['wax-print-shop-operator'].published = True
    profiles['app-climate-viewer'].kc_groups_json = \
        '["climate-viewers"]'
    profiles['app-climate-viewer'].published = True

    wax_classes = classes_for_app(mgr, 'wax-print-shop')
    check('sep-7: app -> modules -> classes derivation yields real '
          'class names', 'WaxPrintSimState' in wax_classes
          and 'MathShapeDefinition' in wax_classes)

    operator = {'roles': [], 'raw_claims':
                {'groups': ['/wax-print-shop-operators']}}
    grants = resolve_grants(mgr, operator)
    check('sep-7: KC groups claim grants the profile (leading / '
          'stripped; source stamped)',
          grants['profiles'][0]['profile']
          == 'wax-print-shop-operator'
          and grants['apps'] == ['wax-print-shop']
          and 'jwt-groups-claim' in grants['groupSources'])
    check('sep-7: granted classes carry the profile verbs, not more',
          set(grants['classes'].get('WaxPrintSimState', []))
          == {'create', 'read', 'update'})

    verdict = permission_verdict(mgr, operator,
                                 'WaxPrintSimState', 'update')
    refusal = permission_verdict(mgr, operator,
                                 'WaxPrintSimState', 'delete')
    anon = permission_verdict(mgr, None, 'WaxPrintSimState', 'read')
    check('sep-7: verdicts are evidence-bearing, never bare booleans',
          verdict['allowed'] and verdict['via']
          and not refusal['allowed'] and refusal['suggestion']
          and not anon['allowed'] and 'identity' in anon['why'])
    check('sep-7: roles also grant (ungroomed realms work) + admin '
          'bypass stated',
          resolve_grants(mgr, {'roles':
              ['climate-viewers']})['apps'] == ['app-climate']
          and permission_verdict(mgr, {'roles': ['polari-admin']},
                                 'Anything', 'delete')['allowed'])

    class _Resp:
        def __init__(self):
            self.status = '200 OK'
            self.media = None
            self.headers = {}
        def set_header(self, k, v):
            self.headers[k] = v
    req = _ns(context=_ns(user_info=operator, roles=[]))
    saved_mode = os.environ.pop('POLARI_APP_PERMISSIONS', None)
    try:
        resp = _Resp()
        check('sep-7 gate: mode OFF (default) never checks',
              crude_permission_gate(mgr, req, resp, 'delete',
                                    'WaxPrintSimState') is True
              and resp.headers == {})
        os.environ['POLARI_APP_PERMISSIONS'] = 'advisory'
        resp = _Resp()
        check('sep-7 gate: ADVISORY proceeds but says would-deny',
              crude_permission_gate(mgr, req, resp, 'delete',
                                    'WaxPrintSimState') is True
              and 'would-deny' in resp.headers.get(
                  ADVISORY_HEADER, ''))
        os.environ['POLARI_APP_PERMISSIONS'] = 'enforce'
        resp = _Resp()
        check('sep-7 gate: ENFORCE refuses with the verdict (403)',
              crude_permission_gate(mgr, req, resp, 'delete',
                                    'WaxPrintSimState') is False
              and resp.status.startswith('403')
              and resp.media['verdict']['suggestion'])
        resp = _Resp()
        check('sep-7 gate: ENFORCE passes granted verbs',
              crude_permission_gate(mgr, req, resp, 'read',
                                    'WaxPrintSimState') is True)
        bare = _ns(objectTables={}, idList=[])
        resp = _Resp()
        check('sep-7 gate: no profile table -> proceed (module '
              'absent = today\'s behavior, stated)',
              crude_permission_gate(bare, req, resp, 'delete',
                                    'X') is True)
    finally:
        if saved_mode is None:
            os.environ.pop('POLARI_APP_PERMISSIONS', None)
        else:
            os.environ['POLARI_APP_PERMISSIONS'] = saved_mode

    # ------------------------------------------------------------------
    print('\n== suite: roles -> apps + my apps (his ask 2026-09-18) ==')
    import io
    from polariapps.apps_api import AppsAPI
    from polariapps.custom import apps_roles as R

    # A caller is a Keycloak token, nothing more: `sub` is who they are,
    # the `groups` claim is which roles they hold.
    def _who(sub, *groups, username=''):
        claims = {'groups': list(groups)}
        info = {'sub': sub, 'raw_claims': claims, 'roles': []}
        if username:   # present on a real token; must never reach a row
            info['preferred_username'] = username
            claims['preferred_username'] = username
        return info

    class _Req:
        """The shape falcon hands a responder: context.user_info + a body."""
        def __init__(self, user_info=None, body=None):
            self.context = _ns(user_info=user_info)
            self.bounded_stream = io.BytesIO(
                json.dumps(body if body is not None else {}).encode())
            self.params = {}

    class _Rsp:
        def __init__(self):
            self.status = '200 OK'
            self.media = None

    class _Api:
        """The real responders over a test double manager (constructing a
        treeObject AppsAPI needs a whole server)."""
        def __init__(self, manager):
            self.manager = manager
        _payload = AppsAPI._payload
        _refuse = AppsAPI._refuse
        _user_info = AppsAPI._user_info
        _status = AppsAPI._status
        on_get_roles = AppsAPI.on_get_roles
        on_post_role = AppsAPI.on_post_role
        on_get_role_suggested = AppsAPI.on_get_role_suggested
        on_get_mine = AppsAPI.on_get_mine
        on_post_mine = AppsAPI.on_post_mine

    def _call(api, method, *args, user=None, body=None):
        req, rsp = _Req(user, body), _Rsp()
        getattr(api, method)(req, rsp, *args)
        return rsp

    # ---- bindings: what the MODULES declare, personas as the fallback
    roles_mgr = _mgr()            # held: the fallback table is keyed by id()
    api = _Api(roles_mgr)
    derived = R.derive_bindings(roles_mgr)
    check('roles->apps: a manifest `app.roles` binds every app carrying '
          'the module (scoring -> the political/scorecard apps)',
          derived.get('journalist', {}).get('derived_from') == 'app.roles'
          and {'app-policy', 'app-scorecards-data-analysis',
               'dmv-policy-analysis', 'judicial-lean'}
          <= set(derived.get('journalist', {}).get('apps', [])),
          str(derived.get('journalist')))
    check('roles->apps: demo roles stay inside the 3-6 app budget',
          all(3 <= len(derived.get(r, {}).get('apps', [])) <= 6
              for r in ('journalist', 'data-scientist', 'operators')),
          str({r: len(derived.get(r, {}).get('apps', []))
               for r in ('journalist', 'data-scientist', 'operators')}))
    check('roles->apps: PERSONA FALLBACK — a persona name that no '
          'manifest declares still becomes a binding, marked as derived '
          'from personas',
          derived.get('materials-scientist', {}).get('derived_from')
          == 'personas'
          and derived['materials-scientist']['apps']
          == ['app-materials-science'])
    check('roles->apps: a declared role BEATS the persona of the same '
          'name (declaration wins, fallback fills gaps)',
          all(info['derived_from'] in ('app.roles', 'personas')
              for info in derived.values())
          and 'app.roles' == derived['operators']['derived_from'])

    rsp = _call(api, 'on_get_roles')
    listed = {b['role']: b for b in rsp.media['bindings']}
    check('GET /api/apps/roles: every binding, resolved to app '
          'name/title/route, source manifest',
          rsp.media['ok'] and listed['journalist']['source'] == 'manifest'
          and all(a['route'] == '/app/' + a['name']
                  for a in listed['journalist']['apps']))
    check('GET /api/apps/roles: converging twice changes nothing '
          '(idempotent derivation)',
          R.ensure_bindings(roles_mgr)['created'] == []
          and R.ensure_bindings(roles_mgr)['updated'] == [])

    # ---- POST /api/apps/roles/{role}: administrators only
    rsp = _call(api, 'on_post_role', 'journalist',
                body={'apps': ['app-policy']})
    check('POST /api/apps/roles/{role}: anonymous is refused 401',
          rsp.status.startswith('401') and not rsp.media['ok'])
    rsp = _call(api, 'on_post_role', 'journalist',
                user=_who('sub-j', 'journalist'),
                body={'apps': ['app-policy']})
    check('POST /api/apps/roles/{role}: a signed-in NON-admin is '
          'refused 403 and pointed at /api/apps/mine',
          rsp.status.startswith('403')
          and '/api/apps/mine' in rsp.media['error'])
    rsp = _call(api, 'on_post_role', 'journalist',
                user=_who('sub-admin', 'polari-admin'),
                body={'apps': ['app-policy', 'nope-not-an-app']})
    check('POST /api/apps/roles/{role}: an unknown app name is refused '
          'WITH the known list, not silently dropped',
          not rsp.media['ok'] and 'nope-not-an-app' in rsp.media['error']
          and rsp.media['knownApps'])
    rsp = _call(api, 'on_post_role', 'journalist',
                user=_who('sub-admin', 'polari-admin'),
                body={'apps': ['judicial-lean', 'app-policy']})
    check('POST /api/apps/roles/{role}: an admin binds an ORDERED list; '
          'source becomes admin',
          rsp.media['ok'] and rsp.media['source'] == 'admin'
          and [a['name'] for a in rsp.media['apps']]
          == ['judicial-lean', 'app-policy'])
    R.ensure_bindings(roles_mgr)
    check('roles->apps: the manifest derivation NEVER overwrites an '
          "admin's binding (a decision outranks a derivation)",
          R.binding_apps(roles_mgr, 'journalist')
          == ['judicial-lean', 'app-policy'])

    # ---- suggestions: what a role-play review SAW, never auto-bound
    def _review_double(_manager, role):
        return {'ok': True, 'role': role, 'apps': [
            {'item': 'app-scorecards-data-analysis', 'count': 7,
             'last_seen': 'now'},
            {'item': 'judicial-lean', 'count': 2, 'last_seen': 'then'},
            {'item': 'not-an-app', 'count': 99, 'last_seen': 'never'}]}
    import security.custom.security_observe as _so_mod  # noqa: F401
    _saved_review = _so_mod.review
    try:
        _so_mod.review = _review_double
        rsp = _call(api, 'on_get_role_suggested', 'journalist')
    finally:
        _so_mod.review = _saved_review
    sug = rsp.media
    check('GET /api/apps/roles/{role}/suggested: the review\'s apps come '
          'back ordered by use, unknown names dropped, already-bound '
          'flagged — and nothing was bound',
          sug['ok']
          and [s['name'] for s in sug['suggested']]
          == ['app-scorecards-data-analysis', 'judicial-lean']
          and sug['suggested'][1]['bound'] is True
          and sug['suggested'][0]['bound'] is False
          and R.binding_apps(roles_mgr, 'journalist')
          == ['judicial-lean', 'app-policy']
          and 'SUGGESTION ONLY' in sug['note'])

    # ---- /api/apps/mine
    mine_mgr = _mgr()
    api2 = _Api(mine_mgr)
    rsp = _call(api2, 'on_get_mine')
    check('GET /api/apps/mine: anonymous is 401 (this answer is about '
          'ONE person, and a person is a Keycloak sub)',
          rsp.status.startswith('401') and not rsp.media['ok'])

    kc_noise = _who('sub-noise', 'journalist', 'offline_access',
                    'uma_authorization', 'default-roles-polari')
    rsp = _call(api2, 'on_get_mine', user=kc_noise)
    check('GET /api/apps/mine: Keycloak\'s own plumbing is not a role — '
          'offline_access / uma_authorization / default-roles-* never '
          'reach the menu',
          rsp.media['held_roles'] == ['journalist']
          and rsp.media['primary_role'] == 'journalist')

    viewer = _who('sub-viewer', 'viewers')
    rsp = _call(api2, 'on_get_mine', user=viewer)
    check('GET /api/apps/mine: a caller whose roles bind nothing gets an '
          'empty list and NO error (the catalogue is still there)',
          rsp.media['ok'] and rsp.media['apps'] == []
          and rsp.media['primary_role'] == ''
          and rsp.media['unboundRoles'] == ['viewers'])

    two = _who('sub-two', 'data-scientist', 'journalist',
               username='demo-journalist')
    rsp = _call(api2, 'on_get_mine', user=two)
    mine = rsp.media
    first_bound = next(r for r in mine['held_roles']
                       if R.binding_apps(mine_mgr, r))
    check('GET /api/apps/mine: two held roles — primary defaults to the '
          'FIRST held role that has a binding; the rest are additional',
          mine['ok'] and mine['held_roles'] == ['data-scientist', 'journalist']
          and mine['primary_role'] == first_bound == 'data-scientist'
          and mine['additional_roles'] == ['journalist'])
    check('GET /api/apps/mine: the primary role\'s apps come FIRST, then '
          "the additional role's; every app carries a route",
          [a['via'] for a in mine['apps']][:1] == ['primary']
          and {a['via'] for a in mine['apps']} == {'primary', 'additional'}
          and all(a['route'] and a['removable'] for a in mine['apps'])
          and [a['via'] for a in mine['apps']]
          == sorted((a['via'] for a in mine['apps']), reverse=True))

    rsp = _call(api2, 'on_post_mine', user=two,
                body={'primary_role': 'operators'})
    check('POST /api/apps/mine: a primary role the caller does NOT hold '
          'is refused 400, naming the roles they do hold',
          rsp.status.startswith('400') and not rsp.media['ok']
          and rsp.media['held_roles'] == ['data-scientist', 'journalist'])
    rsp = _call(api2, 'on_post_mine', user=two,
                body={'primary_role': 'journalist'})
    check('POST /api/apps/mine: switching the primary to a HELD role '
          'reorders the list',
          rsp.media['ok'] and rsp.media['primary_role'] == 'journalist'
          and rsp.media['additional_roles'] == ['data-scientist']
          and rsp.media['apps'][0]['role'] == 'journalist')

    # ---- add / remove / restore round trip
    hidden = rsp.media['apps'][0]['name']
    rsp = _call(api2, 'on_post_mine', user=two, body={'remove': [hidden]})
    check('POST /api/apps/mine {remove}: the app leaves the list, shows '
          'under `removed`, and is offered back as a suggestion',
          rsp.media['ok']
          and hidden not in [a['name'] for a in rsp.media['apps']]
          and hidden in [a['name'] for a in rsp.media['removed']]
          and hidden in [s['name'] for s in rsp.media['suggestions']])
    rsp = _call(api2, 'on_post_mine', user=two,
                body={'add': ['app-topology-network']})
    added = next((a for a in rsp.media['apps']
                  if a['name'] == 'app-topology-network'), None)
    check('POST /api/apps/mine {add}: an app NO role of theirs binds '
          'joins the list marked via=added',
          added is not None and added['via'] == 'added')
    rsp = _call(api2, 'on_post_mine', user=two, body={'restore': [hidden]})
    check('POST /api/apps/mine {restore}: the hidden app comes back via '
          'its role, and `removed` is empty again',
          rsp.media['ok'] and rsp.media['removed'] == []
          and rsp.media['suggestions'] == []
          and hidden in [a['name'] for a in rsp.media['apps']])
    rsp = _call(api2, 'on_post_mine', user=two,
                body={'add': ['not-a-real-app']})
    check('POST /api/apps/mine: an unknown app name is refused 400 with '
          'the known list',
          rsp.status.startswith('400') and not rsp.media['ok']
          and rsp.media['knownApps'])

    # ---- D18-1: a person in a Polari row is a Keycloak sub and nothing else
    pref_rows = R._rows(mine_mgr, R.PREFERENCE_TABLE)
    bind_rows = R._rows(roles_mgr, R.BINDING_TABLE)
    def _values(rows):
        out = []
        for row in rows:
            out += [str(v) for v in vars(row).values()]
        return out
    blob = ' '.join(_values(pref_rows) + _values(bind_rows))
    check('D18-1: the rows key the person by the Keycloak sub ALONE — no '
          'username, e-mail or display name in any field',
          pref_rows and 'demo-journalist' not in blob and '@' not in blob
          and all(getattr(r, 'name', '') == getattr(r, 'sub', None)
                  for r in pref_rows),
          blob[:300])
    check('D18-1: an admin binding records WHO by sub only',
          all(getattr(r, 'updated_by', '') in ('', 'sub-admin')
              for r in bind_rows))

    failed = [label for label, ok in _results if not ok]
    print(f'\n{len(_results) - len(failed)}/{len(_results)} checks '
          f'passed' + (f'; FAILED: {failed}' if failed else ''))
    raise SystemExit(1 if failed else 0)
