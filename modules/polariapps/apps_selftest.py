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
    check('§58 the tailored home: every app the answer names carries the '
          'title, the useCase line and the route a CARD needs — so the '
          'tailored home renders from this one call',
          all(a['name'] and a['title'] and a['route']
              and 'useCase' in a and isinstance(a['useCase'], str)
              for a in mine['apps'])
          and any(a['useCase'] for a in mine['apps']))

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
    check('§58: a hidden app and its suggestion carry the SAME card shape '
          '{name,title,useCase,route} the live apps do',
          rsp.media['removed'] and rsp.media['suggestions']
          and all(e['name'] and e['title'] and e['route']
                  and isinstance(e.get('useCase'), str)
                  for e in rsp.media['removed'] + rsp.media['suggestions']))
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

    # ------------------------------------------------------------------
    print('\n== suite: ct-8 security decisions per app x version '
          '(design CAUSAL_TRACE_OBJECT_FLOW_DESIGN.md §6) ==')
    import sys
    from polariapps.custom import security_decisions as D
    from polariapps.custom import security_subjects as S
    from polariapps.custom.security_confirm import (
        confirm_profile, proposal_hash)
    from polariapps.custom.security_coverage import coverage

    CT8_CLASSES = {'MealEntry', 'Ballot'}

    def _ct8_mgr(**extra):
        """One app carrying one module, with a row of every source the
        enumeration reads — including the three that live in the
        SECURITY module (OwnedClassPolicy, TraceTarget, CausalEdge) and
        the one that does not exist yet (InboundPolicy, ct-9). They are
        plain namespaces in the manager's tables, which is exactly how
        polariapps reads them on a live instance: by table name, never
        by importing security."""
        tables = {
            'PolariAppDefinition': {'ct8-app': _ns(
                name='ct8-app', title='CT8 app', use_case='proving ct-8',
                modules_json='["polariapps"]', pages_json='[]',
                nav_json='[]', personas_json='["kitchen-operator"]',
                discipline='', engine_page='', is_prior=True, notes='')},
            'AppPermissionProfile': {'ct8-operator': _ns(
                name='ct8-operator', app_name='ct8-app',
                kc_groups_json='["operators"]',
                verbs_json='["read", "update"]',
                extra_classes_json='[]', published=True)},
            'PermissionObservation': {'obs': _ns(
                name='operators|MealEntry|delete', groups='operators',
                class_name='MealEntry', verb='delete', count=4)},
            'OwnedClassPolicy': {'MealEntry': _ns(
                name='MealEntry', class_name='MealEntry', enabled=True,
                owner_field='sub')},
            'EventTrigger': {'daily-rollup': _ns(
                name='daily-rollup', solution_name='roll-up',
                source_json='{"class": "MealEntry"}', inputs_json='{}',
                description='', notes='', run_as='definer',
                enabled=True, fire_count=3)},
            'CausalEdge': {'edge': _ns(
                name='e', cause='object:MealEntry:update',
                effect='external:odoo:main', means='send',
                detail='json-rpc', count=12, last_seen='2026-09-18',
                target='MealEntry', sample_trace_id='trace-1')},
            'TraceTarget': {'MealEntry': _ns(
                name='MealEntry', class_name='MealEntry',
                traces_opened=3, edges_written=5,
                stopped_because='window')},
            'InboundPolicy': {'anon': _ns(
                name='anonymous', source_kind='anonymous',
                source='anonymous', state='suggested',
                paths_json='["GET /api/MealEntry"]')},
            'MealEntry': {'m1': _ns(name='m1'), 'm2': _ns(name='m2')},
        }
        tables.update(extra)
        return _ns(objectTables=tables)

    ct8 = _ct8_mgr()
    report = S.enumerate_subjects(ct8, 'ct8-app', classes=CT8_CLASSES)
    kinds = {s['kind'] for s in report['subjects']}
    by_subject = {(s['kind'], s['subject']): s for s in report['subjects']}
    check('ct-8: the enumeration covers ALL EIGHT kinds for one app — '
          'class x verb x group, owner policy, trigger run-as, declared '
          'flow, role binding, outbound, inbound, trace coverage',
          kinds == set(D.DECISION_KINDS), sorted(kinds))
    check('ct-8: subjects come FROM THE APP, not from what was observed '
          '— every class x every CRUDE verb is enumerated, including '
          'the verbs nobody has ever used',
          all(('profile-verb', f'{cls}:{verb}@operators') in by_subject
              for cls in CT8_CLASSES
              for verb in ('read', 'create', 'update', 'delete',
                           'events')))
    check('ct-8: `open` is a REAL GAP — a class with no owner policy '
          'and no trace target is open, while the ones with evidence '
          'are suggested (never confirmed: evidence never confirms)',
          not by_subject[('owner-policy', 'Ballot')]['suggested']
          and not by_subject[('trace-coverage', 'trace:Ballot')]['suggested']
          and by_subject[('owner-policy', 'MealEntry')]['suggested']
          and by_subject[('trace-coverage', 'trace:MealEntry')]['suggested'])
    check('ct-8: an observed send nothing declares is a flow-declared '
          'FINDING (design §9), open rather than suggested',
          ('flow-declared', 'flow:undeclared:odoo') in by_subject
          and not by_subject[('flow-declared',
                              'flow:undeclared:odoo')]['suggested'])
    check('ct-8: the trigger subject carries the AUTHORITY the solution '
          'runs with — a definer-run trigger is the implicit permission '
          'the person confirming has to see',
          by_subject[('trigger-run-as', 'trigger:daily-rollup')]
          ['evidence']['run_as'] == 'definer')
    bare_sources = S.enumerate_subjects(
        _ns(objectTables={'PolariAppDefinition':
                          ct8.objectTables['PolariAppDefinition']}),
        'ct8-app', classes=CT8_CLASSES)['sources']
    check('ct-8: every kind names the SOURCE it read, and a kind with '
          'no rows says WHY rather than reading as "nothing there" — '
          'inbound rows are ct-9, the app.flows stanza is designed and '
          'not yet written by any manifest, and the outbound wrapper '
          'publishes no registry of known sites',
          set(report['sources']) == set(D.DECISION_KINDS)
          and 'InboundPolicy' in report['sources']['inbound']
          and 'ct-9' in bare_sources['inbound']
          and 'not yet written by any manifest' in
          bare_sources['flow-declared']
          and 'no registry of known sites' in
          report['sources']['outbound'])
    check('ct-8: the app VERSION is derived from its module set (a '
          'Polari-App is a configuration of modules, so it rarely has a '
          'manifest of its own) and the source says so; the release is '
          'honestly unstamped rather than invented',
          report['app_version'].startswith('set-')
          and report['app_version_source'].startswith('module-set:polariapps@')
          and report['release'] == ''
          and 'ReleaseManifest' in report['release_source'],
          report['app_version_source'])

    # ---- converge: idempotent, and a person's ruling outranks it
    first = D.converge(ct8, 'ct8-app', classes=CT8_CLASSES)
    version = first['app_version']
    rows = {r.name: r for r in D._rows(ct8, D.DECISION_TABLE)}
    check('ct-8 converge: one row per enumerated subject, keyed '
          '`app|app_version|kind|subject` so the same subject at two '
          'versions is deliberately two rows',
          len(first['created']) == len(report['subjects'])
          and len(rows) == len(report['subjects'])
          and all(r.name == '|'.join([r.app, r.app_version, r.kind,
                                      r.subject]) for r in rows.values()))
    check('ct-8 converge: evidence makes a row `suggested`; nothing '
          'else is written — no row is created confirmed',
          {r.state for r in rows.values()} == {'open', 'suggested'}
          and len(first['suggested']) == sum(
              1 for s in report['subjects'] if s['suggested']))
    second = D.converge(ct8, 'ct8-app', classes=CT8_CLASSES)
    check('ct-8 converge is IDEMPOTENT: a second pass creates nothing '
          'and keeps every row (the RoleAppBinding discipline)',
          second['created'] == []
          and len(second['kept']) == len(rows)
          and len(D._rows(ct8, D.DECISION_TABLE)) == len(rows))

    ct8_admin = {'sub': 'sub-admin', 'raw_claims':
                 {'groups': ['polari-admin'],
                  'preferred_username': 'the-admin'}, 'roles': []}
    ct8_plain = {'sub': 'sub-operator',
                 'raw_claims': {'groups': ['operators']}, 'roles': []}
    check('ct-8 confirm: ANONYMOUS is 401 — a ruling nobody is '
          'accountable for is not a ruling',
          D.confirm(ct8, 'ct8-app', 'owner-policy', 'MealEntry', None,
                    classes=CT8_CLASSES)['status'] == 401)
    check('ct-8 confirm: a signed-in NON-ADMIN is 403 — confirming what '
          'an analysis proposed is an administrative act',
          D.confirm(ct8, 'ct8-app', 'owner-policy', 'MealEntry',
                    ct8_plain, classes=CT8_CLASSES)['status'] == 403)
    confirmed = D.confirm(ct8, 'ct8-app', 'owner-policy', 'MealEntry',
                          ct8_admin, proposal_hash='sha256:deadbeef',
                          classes=CT8_CLASSES)
    denied = D.confirm(ct8, 'ct8-app', 'trigger-run-as',
                       'trigger:daily-rollup', ct8_admin,
                       decision='denied', classes=CT8_CLASSES)
    check('ct-8 confirm: an admin writes `confirmed` / `denied` with '
          'the proposal HASH and the timestamp — the hash is what makes '
          'a later change visible',
          confirmed['ok'] and confirmed['decision']['state'] == 'confirmed'
          and confirmed['decision']['evidence']['proposal_hash']
          == 'sha256:deadbeef' and confirmed['decision']['confirmedAt']
          and denied['decision']['state'] == 'denied')
    check('ct-8 / D18-1: the decision records the confirmer by Keycloak '
          '`sub` ALONE — the username on the token never reaches a row',
          confirmed['decision']['confirmedBy'] == 'sub-admin'
          and 'the-admin' not in ' '.join(
              str(v) for r in D._rows(ct8, D.DECISION_TABLE)
              for v in vars(r).values()))
    third = D.converge(ct8, 'ct8-app', classes=CT8_CLASSES)
    ruled = {r.name: r for r in D._rows(ct8, D.DECISION_TABLE)}
    check('ct-8 converge NEVER overwrites a person: the confirmed and '
          'denied rows are skipped whole — state, evidence and hash '
          'intact (an admin RoleAppBinding follows the same rule)',
          len(third['skipped_human']) == 2
          and ruled[confirmed['decision']['name']].state == 'confirmed'
          and json.loads(ruled[confirmed['decision']['name']].evidence_json)
          ['proposal_hash'] == 'sha256:deadbeef'
          and ruled[denied['decision']['name']].state == 'denied')

    # ---- the version bump: inherited, and stale for what changed
    ct8.objectTables['EventTrigger']['daily-rollup'].run_as = 'caller'
    changed = D.changed_subjects(ct8, 'ct8-app', version,
                                 classes=CT8_CLASSES)
    check('ct-8 bump: the CHANGED set is computed from the evidence '
          'diff — a trigger that changed the authority it runs with is '
          'a different thing to rule on (counts and timestamps are not)',
          changed == {'trigger:daily-rollup'}, str(changed))
    bumped = D.bump_version(ct8, 'ct8-app', version, 'v2',
                            classes=CT8_CLASSES | {'NewThing'})
    v2 = {(r.kind, r.subject): r for r in D._rows(ct8, D.DECISION_TABLE)
          if r.app_version == 'v2'}
    check('ct-8 bump: every unchanged subject carries forward as '
          '`inherited`, keeping the confirmer — that IS the ruling '
          'being carried',
          len(bumped['inherited']) == len(rows) - 1
          and v2[('owner-policy', 'MealEntry')].state == 'inherited'
          and v2[('owner-policy', 'MealEntry')].confirmed_by == 'sub-admin')
    check('ct-8 bump: the changed subject is `stale` with the confirmer '
          'CLEARED — a release never ships on last version\'s ruling '
          'for something it changed',
          bumped['stale'] and v2[('trigger-run-as',
                                  'trigger:daily-rollup')].state == 'stale'
          and v2[('trigger-run-as',
                  'trigger:daily-rollup')].confirmed_by == ''
          and 'confirmed_by_previously' in json.loads(
              v2[('trigger-run-as',
                  'trigger:daily-rollup')].evidence_json))
    check('ct-8 bump: a class ADDED in the new version shows `open` — '
          'its subjects were enumerated from the app, so nobody has '
          'ruled on them rather than nobody having noticed',
          all(v2[(k, s)].state == 'open' for k, s in
              (('owner-policy', 'NewThing'),
               ('trace-coverage', 'trace:NewThing'),
               ('profile-verb', 'NewThing:delete@operators'))))

    # ---- coverage: none / partial / full, and the instance counts
    cov = coverage(ct8, 'ct8-app', converge_first=False,
                   classes=CT8_CLASSES | {'NewThing'})
    at = {a['appVersion']: a for a in cov['apps']}
    check('ct-8 coverage: per app x version, counted by kind AND by '
          'state, with the LIVE instance count under each class — '
          '"how many objects" answered in rows of data, not only in '
          'classes',
          at[version]['instances']['MealEntry'] == 2
          and at[version]['instances']['Ballot'] == 0
          and at[version]['instanceTotal'] == 2
          and at[version]['byKind']['owner-policy']['confirmed'] == 1)
    check('ct-8 coverage: a version with open and stale rows reads '
          'PARTIAL; `full` requires no open and no stale row of any '
          'kind (the only state a release gate may treat as covered)',
          at[version]['coverage'] == 'partial'
          and at['v2']['coverage'] == 'partial'
          and at['v2']['unruled']['stale'] == 1)
    fresh = _ct8_mgr()
    D.converge(fresh, 'ct8-app', classes={'Ballot'})
    none_cov = coverage(fresh, 'ct8-app', converge_first=False,
                        classes={'Ballot'})['apps'][0]
    for row in D._rows(fresh, D.DECISION_TABLE):
        D.confirm(fresh, 'ct8-app', row.kind, row.subject, ct8_admin,
                  classes={'Ballot'})
    full_cov = coverage(fresh, 'ct8-app', converge_first=False,
                        classes={'Ballot'})['apps'][0]
    check('ct-8 coverage: an app version nobody has ruled on at all '
          'reads NONE (suggestions are not rulings); confirming every '
          'subject reads FULL',
          none_cov['coverage'] == 'none' and none_cov['byState']['open']
          and full_cov['coverage'] == 'full'
          and full_cov['byState']['open'] == 0
          and full_cov['byState']['confirmed'] == full_cov['total'])

    # ---- the ONE human confirmation on the concrete step
    marks = []
    fake_observe = types.ModuleType('security.custom.security_observe')

    def _mark_prototype(manager, name, state, profile='', verdict='',
                        self_claimable=None, by=''):
        marks.append((name, state, profile, by))
        return {'ok': True, 'role': {'name': name, 'state': state}}

    fake_observe.mark_prototype = _mark_prototype
    saved_observe = sys.modules.get('security.custom.security_observe')
    sys.modules['security.custom.security_observe'] = fake_observe
    try:
        concrete_mgr = _ct8_mgr()
        result = confirm_profile(concrete_mgr, 'ct8-operator', ct8_admin,
                                 role='operators', classes=CT8_CLASSES)
        rows_c = {r.name: r for r in D._rows(concrete_mgr, D.DECISION_TABLE)}
        expected = proposal_hash({
            'profile': 'ct8-operator', 'app': 'ct8-app',
            'groups': ['operators'], 'verbs': ['read', 'update'],
            'extraClasses': [], 'published': True})
        check('ct-8 confirm-profile: the proposal is HASHED and the hash '
              'lands on every decision it confirmed — what was agreed '
              'to can be shown to have changed since',
              result['ok'] and result['proposalHash'] == expected
              and all(json.loads(rows_c[n].evidence_json)['proposal_hash']
                      == expected for n in result['confirmed']))
        check('ct-8 confirm-profile: ONE decision per class x verb x '
              'group of the profile, all `confirmed` by the person\'s '
              'sub — a published profile is a PROPOSAL until then',
              len(result['confirmed']) == len(CT8_CLASSES) * 2
              and all(rows_c[n].state == 'confirmed'
                      and rows_c[n].confirmed_by == 'sub-admin'
                      for n in result['confirmed'])
              and result['refused'] == [])
        check('ct-8 confirm-profile: the security module\'s EXISTING '
              'concrete mark is called AFTER the decisions are recorded '
              '(mark_prototype(role, "concreted", profile, by=sub)) — '
              'this slice does not change that function',
              marks == [('operators', 'concreted', 'ct8-operator',
                         'sub-admin')]
              and result['securityMark']['ok'] is True)
        check('ct-8 confirm-profile: anonymous 401, non-admin 403 — the '
              'concrete step is the ONE human confirmation, so it is '
              'the one act that cannot happen without a person',
              confirm_profile(concrete_mgr, 'ct8-operator', None)['status']
              == 401
              and confirm_profile(concrete_mgr, 'ct8-operator',
                                  ct8_plain)['status'] == 403)
    finally:
        if saved_observe is None:
            sys.modules.pop('security.custom.security_observe', None)
        else:
            sys.modules['security.custom.security_observe'] = saved_observe

    # the security module may be absent entirely: the decisions still land
    broken = types.ModuleType('security.custom.security_observe')
    sys.modules['security.custom.security_observe'] = broken
    try:
        absent_mgr = _ct8_mgr()
        absent = confirm_profile(absent_mgr, 'ct8-operator', ct8_admin,
                                 role='operators', classes=CT8_CLASSES)
        check('ct-8 confirm-profile: with the security module\'s mark '
              'unavailable the decisions are STILL recorded and the '
              'answer says the mark could not run — never a pretended '
              'success (polariapps works without security at all)',
              absent['ok'] and absent['confirmed']
              and absent['securityMark']['ok'] is False
              and 'unavailable' in absent['securityMark']['why'])
    finally:
        if saved_observe is None:
            sys.modules.pop('security.custom.security_observe', None)
        else:
            sys.modules['security.custom.security_observe'] = saved_observe

    # ---- ct-4's closure is read through a guarded import: absent is fine
    fake_trace = types.ModuleType('security.custom.security_trace')
    fake_trace.closure = lambda manager, start: {
        'objects': [1, 2, 3], 'events': [1], 'solutions': [],
        'peers': [], 'external': [1]}
    saved_trace = sys.modules.get('security.custom.security_trace')
    sys.modules['security.custom.security_trace'] = fake_trace
    try:
        traced = S.trace_subjects(_ct8_mgr(), {'MealEntry'})[0]
        check('ct-8: when the security module offers ct-4\'s closure, a '
              'traced class carries what it REACHES as evidence; when '
              'it does not, the subject is still enumerated (the '
              'guarded-import rule — a missing security module means '
              'less evidence, never a crash)',
              traced['evidence']['closure']['objects'] == 3
              and S._closure_size(_ct8_mgr(), 'MealEntry') is not None)
    finally:
        if saved_trace is None:
            sys.modules.pop('security.custom.security_trace', None)
        else:
            sys.modules['security.custom.security_trace'] = saved_trace
    no_closure = types.ModuleType('security.custom.security_trace')
    sys.modules['security.custom.security_trace'] = no_closure
    try:
        check('ct-8: a security module with NO closure function yet '
              '(ct-4 has not landed) simply contributes no reach '
              'evidence — tolerated, not caught as an error',
              S._closure_size(_ct8_mgr(), 'MealEntry') is None
              and 'closure' not in S.trace_subjects(
                  _ct8_mgr(), {'MealEntry'})[0]['evidence'])
    finally:
        if saved_trace is None:
            sys.modules.pop('security.custom.security_trace', None)
        else:
            sys.modules['security.custom.security_trace'] = saved_trace

    # ---- the doors
    class _ApiS:
        """The ct-8 responders over a test double manager."""
        def __init__(self, manager):
            self.manager = manager
        _payload = AppsAPI._payload
        _refuse = AppsAPI._refuse
        _user_info = AppsAPI._user_info
        _status = AppsAPI._status
        _signed_in = AppsAPI._signed_in
        on_get_security_decisions = AppsAPI.on_get_security_decisions
        on_post_security_decisions_confirm = \
            AppsAPI.on_post_security_decisions_confirm
        on_post_security_confirm_profile = \
            AppsAPI.on_post_security_confirm_profile
        on_post_security_bump = AppsAPI.on_post_security_bump
        on_get_security_coverage = AppsAPI.on_get_security_coverage

    door_mgr = _ct8_mgr()
    apis = _ApiS(door_mgr)

    class _ReqQ(_Req):
        def __init__(self, user_info=None, body=None, params=None):
            _Req.__init__(self, user_info, body)
            self.params = params or {}

    def _callq(method, user=None, body=None, params=None):
        req, rsp = _ReqQ(user, body, params), _Rsp()
        getattr(apis, method)(req, rsp)
        return rsp

    rsp = _callq('on_get_security_decisions', params={'app': 'ct8-app'})
    check('GET /api/apps/security/decisions: anonymous is 401 — a '
          'ledger of who confirmed what cannot tell an anonymous '
          'caller what THEY still owe',
          rsp.status.startswith('401') and not rsp.media['ok'])
    rsp = _callq('on_get_security_decisions', user=ct8_plain,
                 params={'app': 'ct8-app', 'state': 'open'})
    check('GET /api/apps/security/decisions?app=&state=: a signed-in '
          'caller reads the ledger, converged first and filtered by '
          'state, with the vocabulary beside it',
          rsp.media['ok'] and rsp.media['decisions']
          and {d['state'] for d in rsp.media['decisions']} == {'open'}
          and rsp.media['kinds'] == list(D.DECISION_KINDS)
          and rsp.media['appVersion'].startswith('set-'))
    rsp = _callq('on_get_security_decisions', user=ct8_plain,
                 params={'app': 'ct8-app', 'kind': 'not-a-kind'})
    check('GET /api/apps/security/decisions: an unknown kind is refused '
          '400 with the vocabulary, never silently empty',
          rsp.status.startswith('400') and not rsp.media['ok'])
    rsp = _callq('on_post_security_decisions_confirm',
                 body={'app': 'ct8-app', 'kind': 'owner-policy',
                       'subject': 'MealEntry'})
    check('POST /api/apps/security/decisions/confirm: anonymous 401',
          rsp.status.startswith('401'))
    rsp = _callq('on_post_security_decisions_confirm', user=ct8_plain,
                 body={'app': 'ct8-app', 'kind': 'owner-policy',
                       'subject': 'MealEntry'})
    check('POST /api/apps/security/decisions/confirm: signed-in '
          'non-admin 403', rsp.status.startswith('403'))
    rsp = _callq('on_post_security_decisions_confirm', user=ct8_admin,
                 body={'app': 'ct8-app', 'kind': 'outbound',
                       'subject': 'nothing:enumerates:this'})
    check('POST /api/apps/security/decisions/confirm: a subject nothing '
          'ENUMERATES is a 404 naming the enumeration — a row is never '
          'invented to match a request',
          rsp.status.startswith('404') and 'enumerates' in
          rsp.media['error'])
    rsp = _callq('on_post_security_bump', user=ct8_plain,
                 params={'app': 'ct8-app', 'from': 'a', 'to': 'b'})
    check('POST /api/apps/security/bump: administrators only (403) — '
          'bumping rewrites what the release owes',
          rsp.status.startswith('403'))
    rsp = _callq('on_get_security_coverage', user=ct8_admin,
                 params={'app': 'ct8-app'})
    check('GET /api/apps/security/coverage?app=: per app x version plus '
          'the totals across apps, with none/partial/full stated',
          rsp.media['ok'] and rsp.media['apps']
          and rsp.media['apps'][0]['coverage'] in ('none', 'partial',
                                                   'full')
          and sum(rsp.media['totals'].values())
          == rsp.media['apps'][0]['total'])
    rsp = _callq('on_get_security_coverage')
    check('GET /api/apps/security/coverage: anonymous 401',
          rsp.status.startswith('401'))

    # §54 guard: the five ct-8 routes register and each has its responder
    class _FalconS:
        def __init__(self):
            self.routes = []

        def add_route(self, uri, resource, suffix=None):
            self.routes.append((uri, suffix))

    class _SrvS:
        def __init__(self):
            self.falconServer = _FalconS()

    srv = _SrvS()
    probe = AppsAPI(polServer=srv, manager=None)
    ct8_routes = [(u, s) for u, s in srv.falconServer.routes
                  if u.startswith('/api/apps/security')]
    check('§54 guard: the five ct-8 doors register and each has its '
          'on_<method>_<suffix> responder — a drifted suffix RAISES '
          'from add_route() and takes the backend down at boot, so it '
          'is proven here rather than in a browser',
          ct8_routes == [
              ('/api/apps/security/decisions', 'security_decisions'),
              ('/api/apps/security/decisions/confirm',
               'security_decisions_confirm'),
              ('/api/apps/security/confirm-profile',
               'security_confirm_profile'),
              ('/api/apps/security/bump', 'security_bump'),
              ('/api/apps/security/coverage', 'security_coverage')]
          and all(any(hasattr(probe, f'on_{verb}_{suffix}')
                      for verb in ('get', 'post', 'put', 'delete'))
                  for _u, suffix in ct8_routes), ct8_routes)

    # the page: configured tables only, converged rather than inserted
    from polariapps.apps_page import (
        SEED_APPS_PAGE_DISPLAYS, seed_apps_pages, start_page_converge)
    page = SEED_APPS_PAGE_DISPLAYS[0]
    check('ct-8 page: /display/apps-security is a CONFIGURED page — no '
          'api-json-panel, no new component, and the confirmer column '
          'renders through the `person` format so a sub is resolved on '
          'screen and never stored as a name',
          len(SEED_APPS_PAGE_DISPLAYS) == 1
          and page['pageRoute'] == 'apps-security'
          and 'api-json-panel' not in page['definition']
          and 'confirmed_by:person' in page['definition']
          and 'class-rows-table' in page['definition'])
    check('ct-8 page: it CONVERGES (§54 gotcha — the core seed only '
          'inserts a missing page, so an edited definition never '
          'reaches a live instance) and the converge is started from '
          'the polariapps endpoint constructor',
          callable(seed_apps_pages) and callable(start_page_converge)
          and 'start_page_converge' in open(
              'polariApiServer/module_endpoints.py').read())

    failed = [label for label, ok in _results if not ok]
    print(f'\n{len(_results) - len(failed)}/{len(_results)} checks '
          f'passed' + (f'; FAILED: {failed}' if failed else ''))
    raise SystemExit(1 if failed else 0)
