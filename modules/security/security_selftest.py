"""security_selftest — the module constructs, the three views build for every scenario, the simulation and
the comparison answer, the seed is well-formed, the pages have no raw JSON, and the facts hold:
stock docker blocks module loading / mount / ptrace / userns; stock docker ALLOWS writing the image, raw
sockets and chroot (Polari's rings remove them); a guest cannot escape; the lean profile's API is open."""
import sys

passed = total = 0


def check(label, cond, extra=''):
    global passed, total
    total += 1
    passed += bool(cond)
    print('  [%s] %s %s' % ('PASS' if cond else 'FAIL', label, extra if not cond else ''))


def _claims_checks(api, m, O, _Res, _types, check):
    """SELF-CLAIMABLE ROLES (his words 2026-09-18) — the rule, the refusals, and the two Keycloak calls.

    Runs inside the observe block, so the posture is dev and the knob is a temporary file. `m` already carries the
    prototype role `data-scientist`; this adds the rest. The Keycloak half is proven against a fake `_http`: the
    point is that claim/release hit the RIGHT endpoints with the right method, not that urllib works."""
    import os
    from security.custom import kc_admin as KC
    from security.custom import security_claims as C

    O.create_prototype(m, 'journalist', title='Journalist', description='reporter-facing pages')
    O.create_prototype(m, 'polari-ops', title='Polari Ops')          # a reserved-looking name: never claimable unflagged
    O.create_prototype(m, 'auditor', title='Auditor', self_claimable=True)
    u = {'sub': 'u-1', 'preferred_username': 'demo-viewer', 'roles': ['polari-viewer'], 'raw_claims': {'groups': []}}
    u_held = {'sub': 'u-1', 'preferred_username': 'demo-viewer', 'roles': ['polari-viewer'], 'raw_claims': {'groups': ['journalist']}}
    u_admin = {'sub': 'u-9', 'preferred_username': 'demo-admin', 'roles': ['polari-admin'], 'raw_claims': {'groups': []}}
    dev_names = [r['role'] for r in C.claimable_roles(m, u)]
    check('claimable roles in DEV: every prototype role is claimable whatever its state (data-scientist is `enforced`), '
          'but NEVER an admin role, never "Polari Administrators"/"Polari Developers", never a reserved polari-* name '
          'that was not flagged',
          dev_names == ['auditor', 'data-scientist', 'journalist']
          and not ({'admin', 'polari-admin', 'polari-ops', 'Polari Administrators', 'Polari Developers'} & set(dev_names)), dev_names)
    check('held: the caller\'s own token groups mark the roles they already have',
          [r['held'] for r in C.claimable_roles(m, u)] == [False, False, False]
          and [r['role'] for r in C.claimable_roles(m, u_held) if r['held']] == ['journalist'])
    check('an UNAUTHENTICATED caller may claim nothing (no `sub`, no claim)',
          C.claimable_roles(m, None) == [] and C.claimable_roles(m, {'roles': ['journalist']}) == []
          and C.may_claim(m, None, 'journalist')[0] is False)
    O.set_claim_denied('journalist', True, by='demo-admin')
    check('an admin\'s explicit NO removes a role from the dev free-for-all (the bool column cannot hold "never '
          'decided" vs "decided no", so the NO lives in the knob)',
          'journalist' not in [r['role'] for r in C.claimable_roles(m, u)] and O.claim_denied_roles() == ['journalist'])
    O.set_claim_denied('journalist', False, by='demo-admin')
    O.set_claimable_groups(['operators', 'polari-admin'], by='demo-admin')
    knob = {r['role']: r for r in C.claimable_roles(m, u) if r['source'] == 'knob'}
    check('the claimable_groups knob adds plain KC groups beside the prototypes — and still refuses an admin one',
          list(knob) == ['operators'] and O.claimable_groups() == ['operators', 'polari-admin'], list(knob))
    prod = [r['role'] for r in C.claimable_roles(m, u, env={})]
    check('in PRODUCTION posture only the roles FLAGGED self_claimable plus the knob list may be taken — nothing is '
          'claimable by default', prod == ['auditor', 'operators'], prod)
    check('the refusal names the rule: an admin role, the instance-administration groups, a reserved polari-* name',
          'administrator role' in C.may_claim(m, u, 'polari-admin')[1]
          and 'administers this instance' in C.may_claim(m, u, 'Polari Administrators')[1]
          and 'reserved Polari group name' in C.may_claim(m, u, 'polari-ops')[1]
          and 'not self-claimable' in C.may_claim(m, u, 'data-scientist', env={})[1])
    # ---- the Keycloak half, against a fake _http: the right endpoints, the right methods
    calls = []
    real_http = KC._http
    old_env = dict(os.environ)
    try:
        os.environ['POLARI_KEYCLOAK_ADMIN_URL'] = 'http://pol-keycloak:8080'
        os.environ['POLARI_KEYCLOAK_REALM'] = 'Polari'
        os.environ['POLARI_KEYCLOAK_ISSUER_URI'] = 'https://auth.example.invalid/realms/Polari'
        os.environ['KEYCLOAK_POLARI_BACKEND_CLIENT_SECRET'] = 'sekrit'
        state = {'exists': False}

        def _fake(method, url, headers=None, data=None, form=False):
            calls.append((method, url.split('/realms/')[-1]))
            if url.endswith('/protocol/openid-connect/token'):
                return 200, {'access_token': 'TOK', 'expires_in': 300}
            if '/groups?search=' in url:
                return (200, [{'id': 'g1', 'name': 'journalist', 'path': '/journalist'}]) if state['exists'] else (200, [])
            if method == 'POST' and url.endswith('/groups'):
                state['exists'] = True
                return 201, None
            if method in ('PUT', 'DELETE') and '/users/u-1/groups/g1' in url:
                return 204, None
            return 404, 'unexpected'
        KC._http = _fake
        KC._TOKEN.update({'value': '', 'expires': 0})
        no_kc = C.claim(m, u, 'journalist', env={'POLARI_POSTURE': 'dev', 'POLARI_KEYCLOAK_ADMIN_URL': 'http://pol-keycloak:8080',
                                                 'POLARI_KEYCLOAK_REALM': 'Polari', 'KEYCLOAK_POLARI_BACKEND_CLIENT_SECRET': ''})
        r_claim = C.claim(m, u, 'journalist')
        r_again = C.claim(m, u, 'journalist')
        r_rel = C.release(m, u, 'journalist')
        r_admin = C.claim(m, u, 'polari-admin')
    finally:
        KC._http = real_http; KC._TOKEN.update({'value': '', 'expires': 0})
        os.environ.clear(); os.environ.update(old_env)
    check('claiming a role CREATES the Keycloak group when a prototype role has none yet, then PUTs the caller into '
          'it; a second claim finds the group instead of making it; releasing DELETEs the membership',
          r_claim['ok'] and r_claim['group_id'] == 'g1' and r_claim['group_created'] is True
          and r_again['ok'] and r_again['group_created'] is False
          and r_rel['ok'] and r_rel['released'] is True
          and ('POST', 'Polari/protocol/openid-connect/token') in calls
          and ('POST', 'Polari/groups') in [(m_, u_.split('/admin/realms/')[-1]) for m_, u_ in calls]
          and ('PUT', 'Polari/users/u-1/groups/g1') in [(m_, u_.split('/admin/realms/')[-1]) for m_, u_ in calls]
          and ('DELETE', 'Polari/users/u-1/groups/g1') in [(m_, u_.split('/admin/realms/')[-1]) for m_, u_ in calls], calls)
    check('a claim with no Keycloak credential in the environment answers 503 with the env var to set, not a stack trace',
          no_kc['ok'] is False and no_kc['status'] == 503 and 'KEYCLOAK_POLARI_BACKEND_CLIENT_SECRET' in no_kc['refusal'], no_kc)
    check('an admin role is refused (403) before Keycloak is touched at all',
          r_admin['ok'] is False and r_admin['status'] == 403 and 'administrator role' in r_admin['refusal'])
    ev = {e['action']: e for e in O.events(m) if e['control'] == 'role-claim'}
    check('every claim and release lands in the SecurityEvent ledger — identified ONLY by the opaque Keycloak `sub` '
          '(his PII rule 2026-09-18: Keycloak exists to keep names and e-mails out of Polari), never by the username',
          set(ev) == {'claim journalist', 'release journalist'} and ev['claim journalist']['count'] == 2
          and ev['claim journalist']['actor'] == 'u-1' and ev['claim journalist']['source'] == 'self-claim'
          and ev['claim journalist']['would_deny'] is False
          and 'demo-viewer' not in repr(O.events(m)), sorted(ev))
    # ---- the routes
    class _ReqC:
        def __init__(self, ui, media=None, **params):
            self.params = params; self.media = media or {}
            self.context = _types.SimpleNamespace(user_info=ui, roleplay='')
    api.manager = m
    r = _Res(); api.on_get_roles_claimable(_ReqC(u), r)
    check('GET /api/security/roles/claimable: the posture, the roles, what is held, the Keycloak account console URL '
          'and how to use it', r.media['ok'] and r.media['posture'] == 'dev' and r.media['authenticated'] is True
          and [x['role'] for x in r.media['roles']] == ['auditor', 'data-scientist', 'journalist', 'operators']
          and r.media['sub'] == 'u-1' and 'who' not in r.media
          and r.media['account_url'] == '' and 'never self-claimable' in r.media['how'], r.media.get('roles'))
    r = _Res(); api.on_post_roles_claim(_ReqC(None, media={'role': 'journalist'}), r)
    check('POST /api/security/roles/claim without a bearer is 401, not 403 (there is nobody to claim FOR)',
          r.status.startswith('401') and 'sign in first' in r.media['refusal'])
    r = _Res(); api.on_post_roles_claim(_ReqC(u, media={'role': 'polari-admin'}), r)
    check('POST /api/security/roles/claim {"role": "polari-admin"} is 403 with the rule that refused',
          r.status.startswith('403') and 'administrator role' in r.media['refusal'])
    check('the account console URL is the realm\'s own /account, from POLARI_KEYCLOAK_ISSUER_URI',
          __import__('security.custom.kc_admin', fromlist=['x']).account_url(
              env={'POLARI_KEYCLOAK_ISSUER_URI': 'https://auth.example.invalid/realms/Polari'})
          == 'https://auth.example.invalid/realms/Polari/account')
    before_flag = {p['name']: p['self_claimable'] for p in O.prototypes(m)}
    r = _Res(); api.on_post_observe_role(_ReqC(u, media={'self_claimable': True}), r, 'data-scientist')
    check('POST /api/security/observe/roles/<name> {"self_claimable": true} from a NON-admin is refused (403) and '
          'changes nothing: a self-claimed role must not be able to widen its own claimability',
          r.status.startswith('403') and 'administrator' in r.media['refusal']
          and {p['name']: p['self_claimable'] for p in O.prototypes(m)} == before_flag)
    r = _Res(); api.on_post_observe_role(_ReqC(u_admin, media={'self_claimable': False}), r, 'data-scientist')
    after = {p['name']: p for p in O.prototypes(m)}
    check('...and an ADMIN may set it: the row records the flag and the explicit NO reaches the knob, so dev posture '
          'honours it too', r.media['ok'] and after['data-scientist']['self_claimable'] is False
          and 'data-scientist' in O.claim_denied_roles()
          and 'data-scientist' not in [x['role'] for x in C.claimable_roles(m, u)], O.claim_denied_roles())
    O.set_claim_denied('data-scientist', False); O.set_claimable_groups([])


def _pii_checks(api, O, _Res, _types, check):
    """THE PII BOUNDARY (his rule D18-1, 2026-09-18) — rg-0a.

    Keycloak exists to keep personal data AWAY from Polari, so every person in a row, an event or a log line is the
    opaque Keycloak `sub` and nothing else. Three halves are proven here: the four ledgers store the sub even when
    the token carries a name; the one-shot scrub clears the names that earlier builds wrote; and the single gated
    door resolves a sub to a name LIVE, for the callers allowed to ask and nobody else."""
    import os
    import tempfile
    from security.custom import kc_admin as KC
    from security.custom import security_claims as C          # noqa: F401  (the door's admin test uses its is_admin)

    class _M:
        pass

    class _Req:
        def __init__(self, ui, media=None, **params):
            self.params = params
            self.media = media or {}
            self.context = _types.SimpleNamespace(user_info=ui, roleplay='')

    SUB_J = '3f2b1c8a-9d4e-4a71-8b2c-5e6f7a8b9c0d'      # a Keycloak sub is an opaque UUID, as the scrub's regex knows
    named = {'preferred_username': 'demo-journalist', 'email': 'demo-journalist@example.invalid',
             'username': 'demo-journalist', 'sub': SUB_J, 'roles': ['journalist']}
    old_env = dict(os.environ)
    with tempfile.TemporaryDirectory() as td:
        os.environ['POLARI_OBSERVE_KNOB'] = os.path.join(td, 'observe.json')
        os.environ['POLARI_POSTURE'] = 'dev'
        try:
            m = _M(); m.objectTables = {'PermissionObservation': {}, 'SecurityEvent': {}, 'UsageObservation': {}, 'ObservationSession': {}}
            m.persistTree = lambda: None
            O.observe_permission(m, named, 'Article', 'read', verdict={'allowed': True, 'why': 'granted by profile(s)', 'via': ['journalist']}, roleplay='journalist')
            O.record(m, 'authz', 'update Article', 'Article', actor=O.actor_of(named), reason='no verb grant')
            O.observe_usage(m, 'journalist', 'page', '/journalist/articles', actor=O.actor_of(named))
            O.start_session(m, 'journalist', actor=O.actor_of(named))
            blob = repr(O.observations(m)) + repr(O.events(m)) + repr(O.usages(m)) + repr(O.sessions(m))
            check('the four ledgers store the caller\'s opaque Keycloak `sub`, never the name the token also carries '
                  '(his rule D18-1: Keycloak exists to keep PII away from Polari)',
                  O.observations(m)[0]['actor'] == SUB_J and O.events(m)[0]['actor'] == SUB_J
                  and O.usages(m)[0]['actor'] == SUB_J and O.sessions(m)[0]['actor'] == SUB_J
                  and 'demo-journalist' not in blob and 'example.invalid' not in blob, blob[:300])
            check('actor_of() is the one resolution: a sub when there is one, \'\' otherwise — never a fallback to '
                  'preferred_username / username / e-mail',
                  O.actor_of(named) == SUB_J and O.actor_of({'preferred_username': 'x'}) == ''
                  and O.actor_of(None) == '' and O.actor_of({'sub': 'u-2'}) == 'u-2')
            rv = O.review(m, 'journalist')
            check('the review counts DISTINCT subs and names none of them beyond the sub',
                  rv['actors'] == [SUB_J] and rv['actor_count'] == 1 and 'demo-journalist' not in repr(rv), rv['actors'])
            der = O.derive_profiles(m)
            check('the derived profile counts distinct subjects, not people',
                  der and der[0]['evidence']['actors'] == [SUB_J] and der[0]['evidence']['actor_count'] == 1
                  and 'distinct Keycloak subject' in der[0]['description'], der and der[0]['description'])
            # ---- the scrub: rows written before the rule existed
            real_sub = '11111111-2222-3333-4444-555555555555'
            m.objectTables['PermissionObservation']['x1'] = _types.SimpleNamespace(
                name='journalist|Terms|read', actor='demo-journalist', groups='journalist', profiles='', verb='read',
                class_name='TermsDocument', app='', verdict='would-deny', count=1, first_seen='', last_seen='', posture='dev')
            m.objectTables['SecurityEvent']['x2'] = _types.SimpleNamespace(
                name='authz|read Terms|Terms', control='authz', action='read Terms', target='Terms',
                actor=real_sub, app='', outcome='observed', would_deny=True, reason='', posture='dev', count=1,
                first_seen='', last_seen='', source='')
            m.objectTables['UsageObservation']['x3'] = _types.SimpleNamespace(
                name='journalist|page|/x', role='journalist', kind='page', item='/x', app='', page='', detail='',
                actor='someone@example.invalid', count=1, first_seen='', last_seen='')
            n = O.scrub_actor_pii(m)
            check('the PII scrub clears every actor that is NOT a Keycloak subject id (a username, an e-mail) and '
                  'leaves a real sub alone — and running it again clears nothing (idempotent)',
                  n == 2 and m.objectTables['PermissionObservation']['x1'].actor == ''
                  and m.objectTables['UsageObservation']['x3'].actor == ''
                  and m.objectTables['SecurityEvent']['x2'].actor == real_sub
                  and O.scrub_actor_pii(m) == 0, n)
            check('looks_like_sub: 8-4-4-4-12 hex only', O.looks_like_sub(real_sub) and not O.looks_like_sub('demo-admin')
                  and not O.looks_like_sub('') and not O.looks_like_sub('u-1'))
            # ---- the one gated door: GET /api/security/people/{sub}
            os.environ['POLARI_KEYCLOAK_ADMIN_URL'] = 'http://pol-keycloak:8080'
            os.environ['POLARI_KEYCLOAK_REALM'] = 'Polari'
            os.environ['KEYCLOAK_POLARI_BACKEND_CLIENT_SECRET'] = 'sekrit'
            asked = []
            real_get_user = KC.get_user

            def _fake_get_user(sub, env=None):
                asked.append(sub)
                return {'ok': True, 'user': {'id': sub, 'username': 'demo-journalist', 'first_name': 'Demo',
                                             'last_name': 'Journalist', 'enabled': True}}
            KC.get_user = _fake_get_user
            api.manager = m
            try:
                r = _Res(); api.on_get_people(_Req(None), r, 'u-2')
                check('the people door without an identity is 401 — resolving somebody\'s name needs one of your own',
                      r.status.startswith('401') and not asked, r.media)
                r = _Res(); api.on_get_people(_Req({'sub': 'u-9', 'roles': ['polari-viewer']}), r, 'u-2')
                check('a stranger is 403, and the refusal explains the boundary and how an operator opens it',
                      r.status.startswith('403') and 'people_viewers' in r.media['refusal'] and not asked, r.media)
                r = _Res(); api.on_get_people(_Req(named), r, SUB_J)
                check('your OWN sub resolves: {ok, sub, display_name, username} straight from Keycloak',
                      r.media['ok'] and r.media['sub'] == SUB_J and r.media['display_name'] == 'Demo Journalist'
                      and r.media['username'] == 'demo-journalist' and r.media['why'] == 'your own account'
                      and asked == [SUB_J], r.media)
                r = _Res(); api.on_get_people(_Req({'sub': 'u-9', 'roles': ['polari-admin']}), r, SUB_J)
                check('an ADMIN resolves anyone\'s sub', r.media['ok'] and r.media['display_name'] == 'Demo Journalist'
                      and r.media['why'] == 'administrator', r.media)
                O.set_people_viewers(['approvers'], by='u-9')
                r = _Res(); api.on_get_people(_Req({'sub': 'u-7', 'roles': ['approvers']}), r, SUB_J)
                check('a member of a group named in the people_viewers knob resolves it too, and the answer says which '
                      'group granted it', r.media['ok'] and 'approvers' in r.media['why'] and O.people_viewers() == ['approvers'], r.media)
                r = _Res(); api.on_get_people(_Req({'sub': 'u-8', 'roles': ['nobody']}), r, SUB_J)
                check('...and nobody else: a group NOT on the list is still 403', r.status.startswith('403'))
                os.environ['KEYCLOAK_POLARI_BACKEND_CLIENT_SECRET'] = ''
                r = _Res(); api.on_get_people(_Req(named), r, SUB_J)
                check('on a stack with no Keycloak credential the door is 503 "no identity provider" — it never falls '
                      'back to a stored name, because there is none', r.status.startswith('503')
                      and r.media['refusal'].startswith('no identity provider'), r.media)
                check('the door is never a write: nothing it returned reached a row',
                      'Demo Journalist' not in (repr(O.observations(m)) + repr(O.events(m)) + repr(O.usages(m)) + repr(O.sessions(m))))
            finally:
                KC.get_user = real_get_user
                O.set_people_viewers([])
        finally:
            os.environ.clear(); os.environ.update(old_env)


def _people_batch_checks(api, O, _Res, _types, check):
    """THE BATCH DOOR (§54) — `POST /api/security/people {subs: [...]}`.

    §53 owed "a batch form and a per-caller rate limit before any page resolves names in bulk"; the security-events
    page now does exactly that, one call per table render. Proven here against a fake `kc_admin.get_user`: the gate
    is applied PER SUB, an unknown sub is null rather than an error, the memory cache spares the second Keycloak
    round trip, and the 61st call in a minute is refused."""
    import os
    import tempfile
    from security.custom import kc_admin as KC
    from security.custom import security_people as P

    class _M:
        pass

    class _Req:
        def __init__(self, ui, media=None, **params):
            self.params = params
            self.media = media or {}
            self.context = _types.SimpleNamespace(user_info=ui, roleplay='')

    A = 'aaaaaaaa-1111-4111-8111-aaaaaaaaaaaa'      # the caller
    B = 'bbbbbbbb-2222-4222-8222-bbbbbbbbbbbb'      # somebody else
    GHOST = 'cccccccc-3333-4333-8333-cccccccccccc'  # a sub this realm has never heard of
    me = {'sub': A, 'preferred_username': 'demo-viewer', 'roles': ['polari-viewer'], 'raw_claims': {'groups': []}}
    admin = {'sub': 'admin-0', 'preferred_username': 'demo-admin', 'roles': ['polari-admin'], 'raw_claims': {'groups': []}}
    # ---- every route this module registers must HAVE its responder.
    # Falcon resolves `on_<method>_<suffix>` and RAISES SuffixedMethodNotFoundError from add_route() itself when it
    # finds none — so a suffix that has drifted from its method name does not degrade to a 405, it takes the whole
    # backend down at boot. Seen live: `add_route(..., suffix='people_batch')` beside `def on_post_people` put
    # prf-backend into a crash loop, and every selftest passed because they call the method directly.
    class _Falcon:
        def __init__(self): self.routes = []
        def add_route(self, uri, resource, suffix=None): self.routes.append((uri, suffix))

    class _Srv:
        def __init__(self): self.falconServer = _Falcon()
    srv = _Srv()
    from security.security_api import SecurityAPI as _API
    _API(polServer=srv, manager=None)
    orphans = [uri for uri, suffix in srv.falconServer.routes
               if not any(hasattr(api, 'on_%s%s' % (m, ('_' + suffix) if suffix else ''))
                          for m in ('get', 'post', 'put', 'delete', 'patch'))]
    check('every /api/security route registered has a responder named for its suffix — Falcon RAISES from '
          'add_route() when the suffix and the on_<method>_<suffix> name drift apart, taking the backend down at '
          'boot rather than answering 405',
          orphans == [] and ('/api/security/people', 'people_batch') in srv.falconServer.routes, orphans)

    old_env = dict(os.environ)
    asked = []
    real_get_user = KC.get_user

    def _fake_get_user(sub, env=None):
        asked.append(sub)
        if sub == GHOST:
            return {'ok': False, 'status': 404, 'refusal': 'that user does not exist in this realm'}
        names = {A: ('Ada', 'Viewer', 'demo-viewer'), B: ('Bo', 'Journalist', 'demo-journalist')}
        f, l, u = names.get(sub, ('', '', ''))
        return {'ok': True, 'user': {'id': sub, 'username': u, 'first_name': f, 'last_name': l, 'enabled': True}}

    with tempfile.TemporaryDirectory() as td:
        os.environ['POLARI_OBSERVE_KNOB'] = os.path.join(td, 'observe.json')
        os.environ['POLARI_POSTURE'] = 'dev'
        os.environ['POLARI_KEYCLOAK_ADMIN_URL'] = 'http://pol-keycloak:8080'
        os.environ['POLARI_KEYCLOAK_REALM'] = 'Polari'
        os.environ['KEYCLOAK_POLARI_BACKEND_CLIENT_SECRET'] = 'sekrit'
        os.environ.pop('POLARI_PEOPLE_CACHE_SECONDS', None)
        KC.get_user = _fake_get_user
        m = _M(); m.objectTables = {}; m.persistTree = lambda: None
        api.manager = m
        P.cache_clear(); P.rate_clear()
        try:
            r = _Res(); api.on_post_people_batch(_Req(None, {'subs': [A]}), r)
            check('the batch door without an identity is 401, exactly as the single door is',
                  r.status.startswith('401') and not asked, r.media)
            r = _Res(); api.on_post_people_batch(_Req(me, {'subs': []}), r)
            r2 = _Res(); api.on_post_people_batch(_Req(me, {'subs': ['x'] * (P.MAX_SUBS + 1)}), r2)
            check('the batch refuses an empty body and more than %d subject ids in one call, naming the limit' % P.MAX_SUBS,
                  r.media['ok'] is False and 'subs' in r.media['error']
                  and r2.media['ok'] is False and str(P.MAX_SUBS) in r2.media['error'], (r.media, r2.media))
            r = _Res(); api.on_post_people_batch(_Req(me, {'subs': [A, B, GHOST]}), r)
            check('a plain signed-in caller resolves their OWN sub and no other: B is denied per sub (not a failed '
                  'call), and a denied sub never appears in `people`',
                  r.media['ok'] and r.media['people'] == {A: 'Ada Viewer'} and r.media['denied'] == [B, GHOST]
                  and asked == [A], r.media)
            r = _Res(); api.on_post_people_batch(_Req(admin, {'subs': [A, B, GHOST, B, '']}), r)
            check('an ADMIN resolves the whole batch in ONE call: known subs → names, a sub this realm does not know '
                  '→ null (never an error for the batch), duplicates and blanks collapsed',
                  r.media['ok'] and r.media['people'] == {A: 'Ada Viewer', B: 'Bo Journalist', GHOST: None}
                  and r.media['denied'] == [] and r.media['resolved'] == 2, r.media)
            before = len(asked)
            r = _Res(); api.on_post_people_batch(_Req(admin, {'subs': [A, B]}), r)
            check('the memory cache spares the second Keycloak round trip: the same subs answer with the same names '
                  'and kc_admin.get_user is not called again (TTL %d s, memory only — it dies with the process)' % P.cache_seconds(),
                  r.media['people'] == {A: 'Ada Viewer', B: 'Bo Journalist'} and len(asked) == before
                  and r.media['keycloak_calls'] == 0 and r.media['cache']['entries'] >= 2, (len(asked), before, r.media.get('cache')))
            os.environ['POLARI_PEOPLE_CACHE_SECONDS'] = '0'
            P.cache_clear(); before = len(asked)
            r = _Res(); api.on_post_people_batch(_Req(admin, {'subs': [A]}), r)
            r2 = _Res(); api.on_post_people_batch(_Req(admin, {'subs': [A]}), r2)
            check('POLARI_PEOPLE_CACHE_SECONDS=0 turns the cache off entirely — every lookup goes back to Keycloak and '
                  'no name is held anywhere', len(asked) == before + 2 and P.cache_state()['entries'] == 0, len(asked) - before)
            os.environ.pop('POLARI_PEOPLE_CACHE_SECONDS', None)
            O.set_people_viewers(['approvers'], by='admin-0')
            viewer = {'sub': 'v-1', 'preferred_username': 'x', 'roles': ['approvers'], 'raw_claims': {'groups': []}}
            r = _Res(); api.on_post_people_batch(_Req(viewer, {'subs': [A, B]}), r)
            check('a member of a group named in the people_viewers knob resolves the whole batch too, and the answer '
                  'says which group granted it',
                  r.media['ok'] and set(r.media['people']) == {A, B} and 'approvers' in r.media['why'], r.media)
            O.set_people_viewers([])
            # ---- the rate limit: 60 calls a minute per caller
            P.rate_clear()
            last = None
            for _ in range(P.RATE_LIMIT_CALLS):
                last = _Res(); api.on_post_people_batch(_Req(admin, {'subs': [A]}), last)
            over = _Res(); api.on_post_people_batch(_Req(admin, {'subs': [A]}), over)
            other = _Res(); api.on_post_people_batch(_Req(me, {'subs': [A]}), other)
            check('the rate limit: %d calls a minute per caller pass, the next is 429 with a plain sentence and a '
                  'Retry-After — and it is PER CALLER, so a different signed-in person is unaffected' % P.RATE_LIMIT_CALLS,
                  last.media['ok'] and over.status.startswith('429') and over.media['ok'] is False
                  and 'calls a minute' in over.media['refusal'] and int(getattr(over, 'headers', {}).get('Retry-After', 0)) > 0
                  and other.media['ok'] is True, (over.status, over.media))
            # ---- 503: a stack with no Keycloak credential has nothing to fall back on
            os.environ['KEYCLOAK_POLARI_BACKEND_CLIENT_SECRET'] = ''
            P.rate_clear(); P.cache_clear()
            r = _Res(); api.on_post_people_batch(_Req(admin, {'subs': [B]}), r)
            r2 = _Res(); api.on_post_people_batch(_Req(me, {'subs': [B]}), r2)
            check('with no Keycloak credential the batch is 503 "no identity provider" — but a batch in which every '
                  'sub was DENIED never touches Keycloak at all, so it still answers 200 with the denials',
                  r.status.startswith('503') and r.media['refusal'].startswith('no identity provider')
                  and r2.media['ok'] is True and r2.media['denied'] == [B] and r2.media['people'] == {}, (r.media, r2.media))
            check('the batch is never a write: it took no manager table and left none behind',
                  m.objectTables == {} and 'Ada' not in repr(m.objectTables))
        finally:
            KC.get_user = real_get_user
            P.cache_clear(); P.rate_clear()
            os.environ.clear(); os.environ.update(old_env)


def _owned_checks(api, O, _Res, _types, check):
    """OWNER-DEFINED PERMISSIONS (op-0) — the policy, the stamp, the gate.

    His ask 2026-09-18: *"other people do not have the permission to alter the data on their vote, they only
    have partial read access and only to the contents of the vote and groups the vote corresponds to, not who
    specifically made that vote."* Everything below is that sentence, proven: the owner's floor on their own
    row, others' ceiling with the projection, the owner column dropped, the unreadable row OMITTED from a list
    rather than 403-ing it, and the three modes (off / advisory / enforce) behaving as the class gate does."""
    import os
    from security.custom import security_owned as W
    from accessControl.owner_gate import (owner_gate_read, owner_gate_stamp, owner_gate_write,
                                          ADVISORY_HEADER)

    SUB_A = 'aaaaaaaa-0000-4000-8000-aaaaaaaaaaaa'      # the owner
    SUB_B = 'bbbbbbbb-0000-4000-8000-bbbbbbbbbbbb'      # somebody else
    owner_ui = {'sub': SUB_A, 'preferred_username': 'demo-owner', 'roles': ['voters'], 'raw_claims': {'groups': ['voters']}}
    other_ui = {'sub': SUB_B, 'preferred_username': 'demo-other', 'roles': ['voters'], 'raw_claims': {'groups': ['voters']}}
    admin_ui = {'sub': 'admin-0', 'preferred_username': 'demo-admin', 'roles': ['polari-admin'], 'raw_claims': {'groups': []}}

    # real classes, not SimpleNamespace: the verdict keys off type(instance).__name__
    class Ballot:
        def __init__(self, **kw): self.__dict__.update(kw)

    class VoteRecord:
        def __init__(self, **kw): self.__dict__.update(kw)

    class UserAppPreference:
        def __init__(self, **kw): self.__dict__.update(kw)

    class _M:
        pass

    class _R:
        """A response double: status, media and the headers the advisory mode writes."""
        def __init__(self): self.status = '200 OK'; self.media = None; self.headers = {}
        def set_header(self, k, v): self.headers[k] = v

    class _Q:
        def __init__(self, ui): self.context = _types.SimpleNamespace(user_info=ui, roleplay='')

    def _mode(m):
        os.environ['POLARI_APP_PERMISSIONS'] = m

    # ---- the seed: op-0 seeded UserAppPreference here; op-4 moved that declaration to the manifest of the
    # module that OWNS the class, so the security module now seeds NO policy at all and opts in nobody else's
    # classes. One source of truth, and it is the module that defines the class.
    import json as _json_owned
    from security.security_seed import SEED_OWNED_CLASS_POLICIES
    _apps_owned = _json_owned.load(open('modules/polariapps/polari-app.json', encoding='utf-8'))['app']['owned']
    _pref = next((e for e in _apps_owned if e['class'] == 'UserAppPreference'), None)
    check('op-4 replaces the op-0 seed with a DECLARATION: `security` seeds no OwnedClassPolicy at all (it '
          'ships the mechanism and opts in nobody else\'s classes), and `polariapps` — the module that defines '
          'UserAppPreference — declares it in `app.owned`. Owner reads/updates/deletes; others_verbs [] so '
          'nobody else sees the row at all; owner_field `sub`, the column that class already keys its person '
          'by (the per-class schema freeze)',
          SEED_OWNED_CLASS_POLICIES == [] and _pref is not None and _pref['enabled'] is True
          and _pref['owner_field'] == 'sub' and _pref['others_verbs'] == []
          and _pref['owner_visible'] is False and _pref['owner_may_grant'] is False
          and _pref['transfer'] == 'nobody', (SEED_OWNED_CLASS_POLICIES, _pref))

    old_env = dict(os.environ)
    try:
        m = _M()
        m.objectTables = {'OwnedClassPolicy': {}, 'SecurityEvent': {}, 'Ballot': {}, 'VoteRecord': {},
                          'UserAppPreference': {}}
        m.persistTree = lambda: None
        vr = VoteRecord(id='vr-1', name='election-1', state='open')
        m.objectTables['VoteRecord']['vr-1'] = vr

        # ---- a class with NO policy pays nothing and changes nothing
        loose = Ballot(id='b-0', owner='', choice='yes')
        v0 = W.owner_verdict(m, other_ui, 'update', loose)
        st0 = W.stamp_owner(m, loose, owner_ui)
        check('a class with NO enabled policy: the verdict is `no-policy` and allowed (the class gate\'s answer '
              'stands), and nothing is stamped — an instance of a class nobody opted in carries no owner',
              W.policy_for(m, 'Ballot') is None and v0['rule'] == 'no-policy' and v0['allowed'] is True
              and v0['projected_fields'] is None and st0['stamped'] is False and st0['refused'] is False
              and loose.owner == '', (v0['rule'], st0))

        # ---- the admin door writes the policy (and a disabled row is the same as no row)
        r = W.set_policy(m, 'Ballot', {'enabled': False, 'owner_verbs': ['read', 'update', 'delete']}, by='admin-0')
        check('a DISABLED policy row is the same as no policy at all', r['ok'] and W.policy_for(m, 'Ballot') is None)
        r = W.set_policy(m, 'Ballot', {
            'enabled': True, 'owner_verbs': ['read', 'update', 'delete'], 'others_verbs': ['read'],
            'others_fields': ['election_id', 'choice', 'groups'], 'owner_visible': False,
            'frozen_when': 'VoteRecord.state in (tallied, certified) via vote_record_id',
            'transfer': 'nobody', 'anonymised': True}, by='admin-0')
        pol = W.policy_for(m, 'Ballot')
        check('POST /api/security/owned/<Class> stores the policy the design\'s vote example asks for: owner '
              'read+update+delete, others read only, others see election_id/choice/groups, the owner column '
              'hidden, frozen once the record is certified, transfer nobody',
              r['ok'] and pol and pol['owner_verbs'] == ['read', 'update', 'delete']
              and pol['others_verbs'] == ['read'] and pol['others_fields'] == ['election_id', 'choice', 'groups']
              and pol['owner_visible'] is False and pol['transfer'] == 'nobody' and pol['anonymised'] is True, pol)
        bad = W.set_policy(m, 'Ballot', {'owner_verbs': ['create']})
        check('owner_verbs may not name `create`: an instance has no owner until it exists, so creation stays '
              'the class door\'s business — refused with the reason, not silently dropped',
              bad['ok'] is False and 'create' in bad['refusal'], bad)

        # ---- THE STAMP
        b1 = Ballot(id='b-1', owner='', election_id='e-1', choice='yes', groups='voters',
                    cast_at='2026-09-18T10:00:00Z', vote_record_id='vr-1')
        st = W.stamp_owner(m, b1, owner_ui)
        check('the owner stamp is the caller\'s opaque Keycloak `sub` and NOTHING else (D18-1): the token also '
              'carried preferred_username, and it reaches no column',
              st['stamped'] is True and b1.owner == SUB_A and st['owner'] == SUB_A
              and 'demo-owner' not in repr(st) + repr(b1.__dict__), (st, b1.__dict__))
        b_anon = Ballot(id='b-x', owner='', election_id='e-1', choice='no', groups='voters', vote_record_id='vr-1')
        st_anon = W.stamp_owner(m, b_anon, None)
        check('an ANONYMOUS create on an owned class is refused with a stated reason — an instance with no owner '
              'has no owner-defined rule to apply — and the knob that would change it is named',
              st_anon['stamped'] is False and st_anon['refused'] is True
              and 'no identity' in st_anon['why'] and 'OwnedClassPolicy' in st_anon['knob'], st_anon)

        # ---- THE OWNER FLOOR, and frozen_when
        vo = W.owner_verdict(m, owner_ui, 'update', b1)
        check('the OWNER FLOOR: the owner may update their own row, and the verdict says which rule decided and '
              'which knob would change it', vo['allowed'] is True and vo['rule'] == 'owner-floor'
              and vo['projected_fields'] is None and 'OwnedClassPolicy[Ballot]' in vo['knob'], vo)
        vr.state = 'certified'
        vf = W.owner_verdict(m, owner_ui, 'update', b1)
        vfr = W.owner_verdict(m, owner_ui, 'read', b1)
        check('frozen_when: once the related VoteRecord is certified the OWNER loses update and delete on their '
              'own ballot (the vote is over) but keeps READ — the verdict names the frozen condition',
              vf['allowed'] is False and vf['rule'] == 'frozen' and 'certified' in vf['why']
              and vfr['allowed'] is True, (vf, vfr['allowed']))
        vr.state = 'open'
        W.set_policy(m, 'Ballot', {**{k: pol[k] for k in ('owner_verbs', 'others_verbs', 'others_fields',
                                                          'owner_visible', 'transfer', 'anonymised')},
                                   'enabled': True, 'frozen_when': 'this is not( an expression'}, by='admin-0')
        evs_before = len(O.events(m))
        vbad = W.owner_verdict(m, owner_ui, 'update', b1)
        check('a MALFORMED frozen_when is NOT frozen — a policy typo must never lock every owner out of their '
              'own rows — and it lands in the SecurityEvent ledger so the typo is visible',
              vbad['allowed'] is True and vbad['rule'] == 'owner-floor'
              and len(O.events(m)) == evs_before + 1
              and any('frozen_when' in (e['action'] + e['reason']) for e in O.events(m)), vbad)
        W.set_policy(m, 'Ballot', {'enabled': True, 'owner_verbs': ['read', 'update', 'delete'],
                                   'others_verbs': ['read'],
                                   'others_fields': ['election_id', 'choice', 'groups'],
                                   'owner_visible': False, 'anonymised': True}, by='admin-0')

        # ---- OTHERS' CEILING: partial read, the owner dropped, no writes
        vothers = W.owner_verdict(m, other_ui, 'read', b1)
        vwrite = W.owner_verdict(m, other_ui, 'update', b1)
        row = {'id': 'b-1', 'owner': SUB_A, 'election_id': 'e-1', 'choice': 'yes', 'groups': 'voters',
               'cast_at': '2026-09-18T10:00:00Z'}
        projected = W.project(row, vothers['projected_fields'])
        check('OTHERS\' CEILING (his sentence, exactly): another voter READS the ballot, projected to its '
              'contents and groups — the owner is dropped, and so is cast_at, because a timestamp beside a '
              '"who was online" signal unmasks a voter',
              vothers['allowed'] is True and vothers['rule'] == 'others-ceiling'
              and vothers['projected_fields'] == ['election_id', 'choice', 'groups']
              and set(projected) == {'id', 'election_id', 'choice', 'groups'}
              and 'owner' not in projected and SUB_A not in repr(projected), projected)
        check('...and another voter may NOT alter it: others_verbs is read only, and the refusal says so',
              vwrite['allowed'] is False and vwrite['rule'] == 'others-ceiling'
              and "belongs to somebody else" in vwrite['why'], vwrite)
        W.set_policy(m, 'Ballot', {'enabled': True, 'owner_verbs': ['read', 'update', 'delete'],
                                   'others_verbs': ['read'], 'others_fields': ['election_id', 'choice', 'groups'],
                                   'owner_visible': True}, by='admin-0')
        check('owner_visible true is the one way the owner column survives a projection (a ballot never sets it)',
              W.owner_verdict(m, other_ui, 'read', b1)['projected_fields'] == ['election_id', 'choice', 'groups', 'owner'])
        W.set_policy(m, 'Ballot', {'enabled': True, 'owner_verbs': ['read', 'update', 'delete'],
                                   'others_verbs': ['read'], 'others_fields': ['election_id', 'choice', 'groups'],
                                   'owner_visible': False, 'anonymised': True}, by='admin-0')
        check('an ADMIN is outside the owner rules: allowed, whole row, rule `admin`',
              W.owner_verdict(m, admin_ui, 'delete', b1)['rule'] == 'admin'
              and W.owner_verdict(m, admin_ui, 'read', b1)['projected_fields'] is None)

        # ---- THE GATE at the CRUDE layer: lists, the three modes
        b2 = Ballot(id='b-2', owner=SUB_B, election_id='e-1', choice='no', groups='voters',
                    cast_at='2026-09-18T11:00:00Z', vote_record_id='vr-1')
        m.objectTables['Ballot'] = {'b-1': b1, 'b-2': b2}
        instances = {'b-1': b1, 'b-2': b2}

        def _payload():
            return [{'dataType': 'Ballot', 'data': [
                {'id': 'b-1', 'owner': SUB_A, 'election_id': 'e-1', 'choice': 'yes', 'groups': 'voters', 'cast_at': 'x'},
                {'id': 'b-2', 'owner': SUB_B, 'election_id': 'e-1', 'choice': 'no', 'groups': 'voters', 'cast_at': 'y'}]}]

        _mode('enforce')
        res = _R(); out = owner_gate_read(m, _Q(owner_ui), res, 'Ballot', instances, _payload())
        data = {d['id']: d for d in out[0]['data']}
        check('ENFORCE, a list read: the caller\'s OWN row comes back whole, the other person\'s row is '
              'PROJECTED — one response, two different shapes, no 403 anywhere',
              set(data) == {'b-1', 'b-2'} and data['b-1']['owner'] == SUB_A and 'cast_at' in data['b-1']
              and set(data['b-2']) == {'id', 'election_id', 'choice', 'groups'} and SUB_B not in repr(data['b-2']),
              data)
        W.set_policy(m, 'Ballot', {'enabled': True, 'owner_verbs': ['read', 'update', 'delete'],
                                   'others_verbs': [], 'others_fields': [], 'owner_visible': False}, by='admin-0')
        res = _R(); out = owner_gate_read(m, _Q(owner_ui), res, 'Ballot', instances, _payload())
        check('ENFORCE, others_verbs []: a row the caller may not read at all is OMITTED from the list — never a '
              '403 for the whole list because one row is private (design §3.4)',
              [d['id'] for d in out[0]['data']] == ['b-1'], [d['id'] for d in out[0]['data']])
        _mode('advisory')
        res = _R(); out = owner_gate_read(m, _Q(owner_ui), res, 'Ballot', instances, _payload())
        adv = res.headers.get(ADVISORY_HEADER, '')
        check('ADVISORY (the DEPLOYED mode — dev warns, never blocks): the whole list comes back UNCHANGED and '
              'the header says what enforcement would have hidden',
              len(out[0]['data']) == 2 and out[0]['data'][1]['owner'] == SUB_B
              and 'would-deny Ballot:b-2:read' in adv, adv)
        W.set_policy(m, 'Ballot', {'enabled': True, 'owner_verbs': ['read', 'update', 'delete'],
                                   'others_verbs': ['read'], 'others_fields': ['election_id', 'choice', 'groups'],
                                   'owner_visible': False}, by='admin-0')
        res = _R(); out = owner_gate_read(m, _Q(owner_ui), res, 'Ballot', instances, _payload())
        check('ADVISORY, a projected read: the whole row is still returned and the header says would-project',
              len(out[0]['data'][1]) == 6 and 'would-project Ballot:b-2' in res.headers.get(ADVISORY_HEADER, ''),
              res.headers)
        _mode('off')
        res = _R(); out = owner_gate_read(m, _Q(owner_ui), res, 'Ballot', instances, _payload())
        check('OFF: nothing happens at all — no filtering, no projection, no header',
              len(out[0]['data']) == 2 and res.headers == {}, res.headers)

        # ---- writes: advisory header vs enforce 403 vs off
        _mode('advisory')
        res = _R(); g_adv = owner_gate_write(m, _Q(other_ui), res, 'Ballot', 'update', b1)
        _mode('enforce')
        res2 = _R(); g_enf = owner_gate_write(m, _Q(other_ui), res2, 'Ballot', 'update', b1)
        res3 = _R(); g_own = owner_gate_write(m, _Q(owner_ui), res3, 'Ballot', 'update', b1)
        _mode('off')
        res4 = _R(); g_off = owner_gate_write(m, _Q(other_ui), res4, 'Ballot', 'update', b1)
        check('update on somebody else\'s ballot: ADVISORY runs it with a would-deny header, ENFORCE is 403 '
              'carrying the evidence dict, OFF does nothing — and the OWNER passes in every mode',
              g_adv is True and 'would-deny Ballot:b-1:update' in res.headers.get(ADVISORY_HEADER, '')
              and g_enf is False and res2.status.startswith('403')
              and res2.media['verdict']['rule'] == 'others-ceiling' and res2.media['why']
              and g_own is True and g_off is True and res4.headers == {},
              (res.headers, res2.status, res2.media))

        # ---- the create path: the stamp, and the rollback of an ownerless row under enforce
        _mode('enforce')
        fresh = Ballot(id='b-3', owner='', election_id='e-1', choice='yes', groups='voters', vote_record_id='vr-1')
        m.objectTables['Ballot']['b-3'] = fresh
        res = _R(); ok_anon, refusal = owner_gate_stamp(m, _Q(None), res, 'Ballot', [fresh])
        check('ENFORCE + an anonymous create on an owned class: 403, and the row the create loop had already '
              'built is taken back out of the tree — a refusal must not leave the ownerless instance it exists '
              'to prevent', ok_anon is False and res.status.startswith('403')
              and 'b-3' not in m.objectTables['Ballot'], sorted(m.objectTables['Ballot']))
        fresh2 = Ballot(id='b-4', owner='', election_id='e-1', choice='no', groups='voters', vote_record_id='vr-1')
        res = _R(); ok_stamp, _ = owner_gate_stamp(m, _Q(owner_ui), res, 'Ballot', [fresh2])
        check('...and a signed-in create stamps the owner and proceeds', ok_stamp is True and fresh2.owner == SUB_A)
        _mode('advisory')
        fresh3 = Ballot(id='b-5', owner='', election_id='e-1', choice='no', groups='voters', vote_record_id='vr-1')
        res = _R(); ok_adv, _ = owner_gate_stamp(m, _Q(None), res, 'Ballot', [fresh3])
        check('ADVISORY + an anonymous create: the create still happens (unstamped) and the header says what '
              'production would have refused', ok_adv is True and fresh3.owner == ''
              and 'would-deny Ballot::create' in res.headers.get(ADVISORY_HEADER, ''), res.headers)

        # ---- UserAppPreference: the first class to opt in, through its own `sub` column
        W.set_policy(m, 'UserAppPreference', {
            'enabled': True, 'owner_verbs': ['read', 'update', 'delete'], 'others_verbs': [],
            'others_fields': [], 'owner_visible': False, 'owner_field': 'sub'}, by='admin-0')
        pref = UserAppPreference(id='p-1', name='', sub='', primary_role='', added_apps_json='[]')
        st_pref = W.stamp_owner(m, pref, owner_ui)
        vp_own = W.owner_verdict(m, owner_ui, 'update', pref)
        vp_other = W.owner_verdict(m, other_ui, 'read', pref)
        check('UserAppPreference opts in through `owner_field: sub` — the column it already has, rather than a '
              'duplicate `owner` one (the per-class schema freeze): the stamp writes the sub there, the owner '
              'may update it, and nobody else may even read it',
              st_pref['stamped'] is True and st_pref['field'] == 'sub' and pref.sub == SUB_A
              and vp_own['allowed'] is True and vp_own['rule'] == 'owner-floor'
              and vp_other['allowed'] is False and vp_other['rule'] == 'others-ceiling', (st_pref, vp_other))

        # ---- the verdict door
        api.manager = m
        class _ReqO:
            def __init__(self, ui, media=None, **p):
                self.params = p; self.media = media or {}
                self.context = _types.SimpleNamespace(user_info=ui, roleplay='')
        r = _Res(); api.on_get_owned(_ReqO(owner_ui), r)
        check('GET /api/security/owned lists the opted-in classes, the mode in force and how the knob reads',
              r.media['ok'] and 'Ballot' in r.media['enabled'] and 'UserAppPreference' in r.media['enabled']
              and r.media['mode'] in ('off', 'advisory', 'enforce') and 'OPT-IN' in r.media['how'], r.media.get('enabled'))
        r = _Res(); api.on_get_owned_class(_ReqO(owner_ui), r, 'NoSuchClass')
        check('GET /api/security/owned/<Class> for a class nobody opted in says so plainly, and is not an error',
              r.media['ok'] and r.media['owned'] is False and 'not an owned class' in r.media['why'], r.media)
        r = _Res(); api.on_post_owned_class(_ReqO(owner_ui, media={'enabled': True}), r, 'Ballot')
        check('POST /api/security/owned/<Class> from a NON-admin is 403: opting a class in changes what every '
              'caller may do to every instance of it', r.status.startswith('403') and 'administrator' in r.media['refusal'])
        r = _Res(); api.on_get_owned_instance(_ReqO(other_ui), r, 'Ballot', 'b-1')
        check('GET /api/security/owned/<Class>/<id> is the caller\'s own verdict on ONE instance: what they may '
              'do, which fields they would see, and the rule that decided each',
              r.media['ok'] and r.media['may'] == ['read'] and r.media['you_are_the_owner'] is False
              and r.media['fields_you_see'] == ['election_id', 'choice', 'groups']
              and r.media['verdicts']['update']['rule'] == 'others-ceiling', r.media.get('may'))
        r = _Res(); api.on_get_owned_instance(_ReqO(owner_ui), r, 'Ballot', 'b-1')
        check('...and for the OWNER: every owner verb, the whole row, you_are_the_owner true',
              r.media['ok'] and r.media['you_are_the_owner'] is True and r.media['fields_you_see'] is None
              and set(r.media['may']) == {'read', 'update', 'delete'}, r.media.get('may'))
        r = _Res(); api.on_get_owned_instance(_ReqO(owner_ui), r, 'Ballot', 'nope')
        check('an instance that does not exist is an honest 404, not a stack trace', r.status.startswith('404'))

        # ---- §54 guard: the three new routes register against a fake falconServer
        class _Falcon:
            def __init__(self): self.routes = []
            def add_route(self, uri, resource, suffix=None): self.routes.append((uri, suffix))

        class _Srv:
            def __init__(self): self.falconServer = _Falcon()
        srv = _Srv()
        from security.security_api import SecurityAPI as _API
        probe = _API(polServer=srv, manager=None)
        owned_routes = [(u, s) for u, s in srv.falconServer.routes if u.startswith('/api/security/owned')]
        check('§54 guard: the FIVE owner doors register and each has its on_<method>_<suffix> responder — a '
              'suffix that has drifted from its method name RAISES from add_route() and takes the backend down '
              'at boot, so it is proven here rather than in a browser',
              owned_routes == [('/api/security/owned', 'owned'),
                               ('/api/security/owned/{class_name}', 'owned_class'),
                               ('/api/security/owned/{class_name}/{object_id}', 'owned_instance'),
                               ('/api/security/owned/{class_name}/{object_id}/grants', 'owned_grants'),
                               ('/api/security/owned/{class_name}/{object_id}/transfer', 'owned_transfer')]
              and all(any(hasattr(probe, 'on_%s_%s' % (mm, s)) for mm in ('get', 'post', 'put', 'delete'))
                      for _u, s in owned_routes)
              and all(hasattr(probe, 'on_%s_owned_grants' % mm) for mm in ('get', 'post', 'delete')),
              owned_routes)
    finally:
        os.environ.clear(); os.environ.update(old_env)


def _grant_checks(api, O, _Res, _types, check):
    """op-1 — OWNER GRANTS: one owner sharing ONE of their own instances, inside the bounds the class set.

    Design §2 (the row), §3 step 3 (the verdict), §6 (the doors and the Sharing tab). The proof the design asks
    for is *a meal plan shared with one person by sub; expiry removes it* — which is what the middle of this
    function is, with MealPlan standing in for any class an app opts in."""
    import os
    import time
    from security.custom import security_owned as W
    from security.custom import security_owner_grants as G

    OWNER = 'aaaaaaaa-1111-4111-8111-aaaaaaaaaaaa'
    FRIEND = 'bbbbbbbb-1111-4111-8111-bbbbbbbbbbbb'
    STRANGER = 'cccccccc-1111-4111-8111-cccccccccccc'
    owner_ui = {'sub': OWNER, 'preferred_username': 'demo-owner', 'roles': ['household'], 'raw_claims': {'groups': ['household']}}
    friend_ui = {'sub': FRIEND, 'preferred_username': 'demo-friend', 'roles': ['household'], 'raw_claims': {'groups': ['household']}}
    stranger_ui = {'sub': STRANGER, 'roles': ['household'], 'raw_claims': {'groups': ['household']}}
    admin_ui = {'sub': 'dddddddd-1111-4111-8111-dddddddddddd', 'roles': ['polari-admin'], 'raw_claims': {'groups': []}}

    class MealPlan:
        def __init__(self, **kw): self.__dict__.update(kw)

    class _M:
        pass

    class _ReqG:
        def __init__(self, ui, media=None, **p):
            self.params = p; self.media = media or {}
            self.context = _types.SimpleNamespace(user_info=ui, roleplay='')

    old_env = dict(os.environ)
    try:
        os.environ['POLARI_APP_PERMISSIONS'] = 'enforce'
        m = _M()
        m.objectTables = {'OwnedClassPolicy': {}, 'OwnerGrant': {}, 'SecurityEvent': {}, 'MealPlan': {}}
        m.persistTree = lambda: None
        plan = MealPlan(id='mp-1', name='week-40', owner=OWNER, title='Week 40', notes='private',
                        servings=4, cost='42.00')
        other = MealPlan(id='mp-2', name='week-41', owner=STRANGER, title='Week 41', notes='theirs',
                         servings=2, cost='19.00')
        m.objectTables['MealPlan'] = {'mp-1': plan, 'mp-2': other}
        W.set_policy(m, 'MealPlan', {
            'enabled': True, 'owner_verbs': ['read', 'update', 'delete'], 'others_verbs': [],
            'others_fields': [], 'owner_visible': False, 'owner_may_grant': True,
            'grantable_verbs': ['read', 'update'], 'grantee_kinds': ['person', 'group']}, by='admin-0')
        pol = W.policy_for(m, 'MealPlan')

        # ---- a class that forbids sharing has no tab and no grant
        W.set_policy(m, 'Ballot', {'enabled': True, 'owner_verbs': ['read'], 'others_verbs': ['read'],
                                   'others_fields': ['choice'], 'anonymised': True}, by='admin-0')
        sh_ballot = G.sharing(m, owner_ui, 'Ballot', 'nope')
        check('a class whose policy forbids grants has NO Sharing tab (design §6: "a ballot\'s page has no '
              'Sharing tab because its policy forbids grants") — and asking for one is an honest 404 on the '
              'instance, not a silent empty list',
              sh_ballot.get('ok') is False and sh_ballot.get('status') == 404, sh_ballot)

        # ---- THE PROOF: one meal plan, shared with ONE person, by sub
        before = W.owner_verdict(m, friend_ui, 'read', plan)
        r = G.grant(m, owner_ui, 'MealPlan', 'mp-1', {
            'grantee_kind': 'person', 'grantee': FRIEND, 'verbs': ['read'],
            'fields': ['title', 'servings']})
        after = W.owner_verdict(m, friend_ui, 'read', plan)
        check('THE op-1 PROOF: a meal plan the owner shares with ONE person BY SUB. Before the grant that '
              'person may not read the row at all (others_verbs []); after it they may, PROJECTED to the '
              'fields the grant named, and the verdict names the grant that decided — `grant:<id>`, not a '
              'blanket allow',
              before['allowed'] is False and r['ok'] is True and after['allowed'] is True
              and after['rule'].startswith('grant:') and after['projected_fields'] == ['title', 'servings']
              and 'owner' not in (after['projected_fields'] or []), (before['rule'], r.get('refusal'), after))
        check('...and NOBODY ELSE gains anything by it: a third person in the same Keycloak group is still '
              'refused, because a grant names ONE grantee and is not a class-level widening',
              W.owner_verdict(m, stranger_ui, 'read', plan)['allowed'] is False)
        check('the grant is stored with the sub in its OWN column (`grantee_sub`), never in the one that holds '
              'a group name — the `person` column format shortens a cell to 8 characters to resolve it live, '
              'and a group name in that column would render as `househol`',
              r['grant']['grantee_sub'] == FRIEND and r['grant']['grantee_group'] == ''
              and r['grant']['grantee'] == FRIEND and r['grant']['granted_by'] == OWNER, r['grant'])

        # ---- EXPIRY REMOVES IT (design §9 op-1: "expiry removes it")
        past = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(time.time() - 60))
        soon = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(time.time() + 1))
        r_past = G.grant(m, owner_ui, 'MealPlan', 'mp-1', {'grantee_kind': 'person', 'grantee': FRIEND,
                                                           'verbs': ['read'], 'valid_until': past})
        r_soon = G.grant(m, owner_ui, 'MealPlan', 'mp-1', {'grantee_kind': 'person', 'grantee': FRIEND,
                                                           'verbs': ['read'], 'fields': ['title'],
                                                           'valid_until': soon})
        live = W.owner_verdict(m, friend_ui, 'read', plan)['allowed']
        time.sleep(1.2)
        dead = W.owner_verdict(m, friend_ui, 'read', plan)
        listed = G.grants_for(m, 'MealPlan', 'mp-1')
        check('EXPIRY removes it: a `valid_until` already in the past is refused at the door (that is a revoke, '
              'not a grant); a grant that expires while it is held stops deciding the INSTANT it expires — the '
              'verdict checks the clock, it does not wait for housekeeping — and reading the instance\'s '
              'grants then PRUNES the dead row rather than leaving a tail of dead permissions',
              r_past['ok'] is False and 'past' in r_past['refusal'] and r_soon['ok'] is True
              and live is True and dead['allowed'] is False and listed == [],
              (r_past.get('refusal'), live, dead['rule'], listed))

        # ---- THE BOUNDS, each refused with the reason
        G.grant(m, owner_ui, 'MealPlan', 'mp-1', {'grantee_kind': 'person', 'grantee': FRIEND, 'verbs': ['read']})
        refusals = {
            'verb outside the bounds': G.grant(m, owner_ui, 'MealPlan', 'mp-1', {
                'grantee_kind': 'person', 'grantee': FRIEND, 'verbs': ['delete']}),
            'a kind the class does not allow': G.grant(m, owner_ui, 'MealPlan', 'mp-1', {
                'grantee_kind': 'nobody', 'grantee': FRIEND, 'verbs': ['read']}),
            'a username instead of a sub': G.grant(m, owner_ui, 'MealPlan', 'mp-1', {
                'grantee_kind': 'person', 'grantee': 'demo-friend', 'verbs': ['read']}),
            'a grant to yourself': G.grant(m, owner_ui, 'MealPlan', 'mp-1', {
                'grantee_kind': 'person', 'grantee': OWNER, 'verbs': ['read']}),
            'a field the class has not got': G.grant(m, owner_ui, 'MealPlan', 'mp-1', {
                'grantee_kind': 'person', 'grantee': FRIEND, 'verbs': ['read'], 'fields': ['salary']}),
            'somebody else\'s row': G.grant(m, friend_ui, 'MealPlan', 'mp-1', {
                'grantee_kind': 'person', 'grantee': STRANGER, 'verbs': ['read']}),
            'an unreadable expiry': G.grant(m, owner_ui, 'MealPlan', 'mp-1', {
                'grantee_kind': 'person', 'grantee': FRIEND, 'verbs': ['read'], 'valid_until': 'next tuesday'}),
        }
        check('every bound the class set is refused AT THE DOOR with the reason, never stored and quietly '
              'ignored: a verb outside grantable_verbs, a grantee_kind the class does not allow, a USERNAME '
              'where a Keycloak sub belongs (D18-1), a grant to yourself (the owner floor written twice), a '
              'field the class has not got, a grant made by somebody who does not own the row, and an expiry '
              'that is not an instant',
              all(v['ok'] is False and v['refusal'] for v in refusals.values())
              and 'grantable_verbs' in refusals['verb outside the bounds']['refusal']
              and 'subject id' in refusals['a username instead of a sub']['refusal']
              and 'YOURSELF' in refusals['a grant to yourself']['refusal']
              and refusals['somebody else\'s row']['status'] == 403,
              {k: v.get('refusal', '')[:50] for k, v in refusals.items()})

        # ---- a GROUP grant, and the union of fields
        W.set_policy(m, 'MealPlan', {**{k: pol[k] for k in ('owner_verbs', 'grantable_verbs', 'grantee_kinds',
                                                            'owner_may_grant', 'owner_visible')},
                                     'enabled': True, 'others_verbs': ['read'], 'others_fields': ['title']},
                     by='admin-0')
        G.grant(m, owner_ui, 'MealPlan', 'mp-1', {'grantee_kind': 'group', 'grantee': 'household',
                                                  'verbs': ['update'], 'fields': ['notes', 'cost']})
        v_group = W.owner_verdict(m, stranger_ui, 'read', plan)
        v_upd = W.owner_verdict(m, stranger_ui, 'update', plan)
        check('a GROUP grant reaches everyone in that Keycloak group, and a read is projected to others_fields '
              'UNIONED with the grant\'s fields (design §3 step 3) — the class shows `title` to anybody who '
              'passed the class door, and this one row additionally shows `notes` and `cost` to the group the '
              'owner shared it with. The `update` the grant carries is allowed by `grant:<id>`',
              v_group['allowed'] is True and v_group['projected_fields'] == ['title', 'notes', 'cost']
              and v_upd['allowed'] is True and v_upd['rule'].startswith('grant:'), (v_group, v_upd['rule']))
        check('a group grant NEVER widens the class door: the gate runs first and this only decides inside its '
              'answer — and the owner column is still dropped, because a grant cannot name a field the '
              'policy hides (owner_visible false)',
              'owner' not in (v_group['projected_fields'] or []))

        # ---- revoke
        rev = G.revoke(m, owner_ui, 'MealPlan', 'mp-1', {'grantee_kind': 'group', 'grantee': 'household'})
        check('the owner takes a grant back and it stops deciding immediately; the remaining grants come back '
              'with the answer so nobody has to ask twice',
              rev['ok'] is True and W.owner_verdict(m, stranger_ui, 'update', plan)['allowed'] is False
              and all(g['grantee_kind'] != 'group' for g in rev['remaining']), rev.get('refusal'))
        check('an ADMIN may act on the grants of a row they do not own (they are outside the owner rules '
              'anyway), and revoking a grant that is not there is an honest 404',
              G.may_grant(m, admin_ui, 'MealPlan', plan)[0] is True
              and G.revoke(m, owner_ui, 'MealPlan', 'mp-1', {'grantee_kind': 'group',
                                                             'grantee': 'nobody'})['status'] == 404)

        # ---- THE SHARING TAB (design §6): a configured table, not a component
        sh = G.sharing(m, owner_ui, 'MealPlan', 'mp-1')
        tab = sh['table']
        check('THE SHARING TAB is DATA, not a component (his rule: no new component, nothing raw): one '
              'CONFIGURED `class-rows-table` over OwnerGrant, filtered to THIS instance by object_id, with the '
              'policy\'s bounds beside it. Both `person`-formatted columns hold a Keycloak sub and nothing '
              'else — `grantee_group` is deliberately not one of them',
              sh['ok'] and sh['show_tab'] is True and sh['you_may_share'] is True
              and tab['componentProps']['componentName'] == 'class-rows-table'
              and tab['componentProps']['inputs']['className'] == 'OwnerGrant'
              and tab['componentProps']['inputs']['filterField'] == 'object_id'
              and tab['componentProps']['inputs']['filterValue'] == 'mp-1'
              and tab['componentProps']['inputs']['columnFormats'] == 'granted_by:person,grantee_sub:person'
              and 'grantee_group:person' not in tab['componentProps']['inputs']['columnFormats'],
              tab['componentProps']['inputs'])
        check('...and the tab does not show for somebody who may not share: the grants are still listed (they '
              'are the owner\'s decisions about a row this caller can see), but `you_may_share` is false with '
              'the reason',
              G.sharing(m, friend_ui, 'MealPlan', 'mp-1')['you_may_share'] is False
              and 'OWNER' in G.sharing(m, friend_ui, 'MealPlan', 'mp-1')['why'])

        # ---- the doors
        api.manager = m
        r = _Res(); api.on_get_owned_grants(_ReqG(owner_ui), r, 'MealPlan', 'mp-1')
        check('GET /api/security/owned/<Class>/<id>/grants answers the tab whole: the grants, the bounds, '
              'whether this caller may share, and the configured table',
              r.media['ok'] and 'grants' in r.media and 'bounds' in r.media and 'table' in r.media)
        r = _Res(); api.on_post_owned_grants(_ReqG(friend_ui, media={'grantee_kind': 'person',
                                                                     'grantee': STRANGER, 'verbs': ['read']}),
                                             r, 'MealPlan', 'mp-1')
        check('POST from somebody who is not the owner is 403 with the rule that refused, not a 400',
              r.status.startswith('403') and 'OWNER' in r.media['refusal'], r.media)
        r = _Res(); api.on_delete_owned_grants(_ReqG(owner_ui, grantee_kind='person', grantee=FRIEND),
                                               r, 'MealPlan', 'mp-1')
        check('DELETE takes the grantee from the QUERY STRING as well as the body — a revoke is a link on a '
              'page, and a link carries no body', r.media['ok'] and r.media['revoked']['grantee'] == FRIEND)
        r = _Res(); api.on_get_owned_instance(_ReqG(owner_ui), r, 'MealPlan', 'mp-1')
        check('the per-instance verdict door carries the Sharing tab\'s whole answer too (design §6): one '
              'door, because a tab that asked twice would show the verdict and the grants from two different '
              'moments', r.media['ok'] and 'sharing' in r.media and 'grants' in r.media
              and r.media['sharing']['table']['componentProps']['inputs']['filterValue'] == 'mp-1')
    finally:
        os.environ.clear(); os.environ.update(old_env)


def _anonymised_checks(api, O, _Res, _types, check):
    """op-2 — ANONYMISED classes, frozen_when's structured form, and TRANSFER.

    Design §5 names three side channels that name the person even when the owner column is hidden: the change
    BROADCAST, the trace JOURNAL's actor/object pairing, and `SecurityEvent.target`. Two of them were closed by
    ct-2 and ct-1 as they were built; this proves all three together, because "closed" is only true of the
    three at once."""
    import os
    import tempfile
    from security.custom import security_owned as W

    VOTER = 'eeeeeeee-2222-4222-8222-eeeeeeeeeeee'
    OTHER = 'ffffffff-2222-4222-8222-ffffffffffff'
    voter_ui = {'sub': VOTER, 'roles': ['voters'], 'raw_claims': {'groups': ['voters']}}
    admin_ui = {'sub': 'aaaa0000-2222-4222-8222-aaaa00000000', 'roles': ['polari-admin'], 'raw_claims': {'groups': []}}

    class Ballot:
        def __init__(self, **kw): self.__dict__.update(kw)

    class VoteRecord:
        def __init__(self, **kw): self.__dict__.update(kw)

    class MealPlan:
        def __init__(self, **kw): self.__dict__.update(kw)

    class _M:
        pass

    class _ReqA:
        def __init__(self, ui, media=None, **p):
            self.params = p; self.media = media or {}
            self.context = _types.SimpleNamespace(user_info=ui, roleplay='')

    old_env = dict(os.environ)
    try:
        os.environ['POLARI_APP_PERMISSIONS'] = 'enforce'
        m = _M()
        m.objectTables = {'OwnedClassPolicy': {}, 'OwnerGrant': {}, 'SecurityEvent': {}, 'Ballot': {},
                          'VoteRecord': {}, 'MealPlan': {}}
        m.persistTree = lambda: None
        vr = VoteRecord(id='vr-9', name='election-9', state='open')
        m.objectTables['VoteRecord']['vr-9'] = vr
        b = Ballot(id='b-9', owner=VOTER, election_id='e-9', choice='yes', groups='voters',
                   cast_at='2026-09-19T09:00:00Z', vote_record_id='vr-9')
        m.objectTables['Ballot']['b-9'] = b

        # ---- `anonymised` IS owner_visible false, whatever the row says beside it
        W.set_policy(m, 'Ballot', {'enabled': True, 'owner_verbs': ['read', 'update'], 'others_verbs': ['read'],
                                   'others_fields': ['election_id', 'choice', 'groups'],
                                   'owner_visible': True, 'anonymised': True, 'transfer': 'owner'},
                     by='admin-0')
        pol = W.policy_for(m, 'Ballot')
        check('op-2: `anonymised` is SHORTHAND (design §2) and is normalised where the policy is READ, not at '
              'each of the half-dozen places that consume it — a row saying anonymised AND owner_visible AND '
              'transfer: owner comes back with owner_visible FALSE and transfer NOBODY, so the owner cannot '
              'leak through whichever half of the pair somebody forgot to check',
              pol['anonymised'] is True and pol['owner_visible'] is False and pol['transfer'] == 'nobody'
              and pol['transfer_declared'] == 'owner', pol)
        check('...and the projection follows: another voter sees the contents and the groups of the ballot and '
              'never the owner column, exactly as his sentence asks',
              W.owner_verdict(m, {'sub': OTHER, 'roles': ['voters'], 'raw_claims': {'groups': ['voters']}},
                              'read', b)['projected_fields'] == ['election_id', 'choice', 'groups'])

        # ---- side channel 1: the change BROADCAST carries no ids (ct-2 built it; proven here)
        import types as _t
        from grpcbridge.custom import transport_mux as TM
        published = []
        fmt = _t.SimpleNamespace(polariTreeWsEnabled=True, flatJsonWsEnabled=False, nestedJsonWsEnabled=False,
                                 polariTreeGrpcEnabled=False)
        m.objectTypingDict = {'Ballot': _t.SimpleNamespace(apiFormatConfig=fmt),
                              'MealPlan': _t.SimpleNamespace(apiFormatConfig=fmt)}
        real_publish = TM.publish_change
        TM.publish_change = lambda mgr, cls, topic, note: published.append((cls, topic, dict(note)))
        try:
            TM.publish_crude_change(m, 'Ballot', 'create', ['b-9'])
            W.set_policy(m, 'MealPlan', {'enabled': True, 'owner_verbs': ['read'], 'others_verbs': ['read'],
                                         'others_fields': ['title']}, by='admin-0')
            TM.publish_crude_change(m, 'MealPlan', 'create', ['mp-1'])
        finally:
            TM.publish_change = real_publish
        by_class = {c: n for c, _t_, n in published}
        check('op-2 SIDE CHANNEL 1, the change BROADCAST (design §5): an ANONYMISED class publishes its class '
              'and operation with NO instance ids, so "a Ballot was created at 14:02:07" cannot be paired with '
              '"that person was on the page at 14:02:07". The broadcast is not dropped — subscribers still '
              'need to know to re-read — and a NON-anonymised owned class keeps its ids',
              by_class['Ballot']['instanceIds'] == [] and by_class['Ballot']['className'] == 'Ballot'
              and by_class['Ballot']['operation'] == 'create'
              and by_class['MealPlan']['instanceIds'] == ['mp-1'], by_class)

        # ---- side channel 2: the trace JOURNAL drops the actor/object pairing (ct-1 built it; proven here)
        from accessControl import cause_context as CC
        from security.custom import security_trace as T
        with tempfile.TemporaryDirectory() as td:
            _trace_env(td)
            T._STATE.update({'armed': False, 'name': '', 'class_name': '', 'resumed': False,
                             'stopped_name': '', 'stopped_until': 0.0})
            T._TRACED.clear(); T._CREATED.clear()
            m.objectTables['TraceTarget'] = {}
            m.objectTables['WriteJournalEntry'] = {}
            T.arm(m, 'Ballot', user_info=admin_ui)
            tok = CC.root_cause('api', 'POST /api/Ballot', actor=VOTER)
            try:
                T.touch(m, 'Ballot', 'create')
                T.record_effect(m, 'Ballot', 'b-9', 'create', fields_changed=['choice'])
            finally:
                CC.pop_cause(tok)
            rows = T.journal(m)
            T.disarm(m, 'manual')
        check('op-2 SIDE CHANNEL 2, the TRACE JOURNAL (design §5): a journal row normally pairs the cause\'s '
              'ACTOR with the effect\'s OBJECT ID — for a ballot that pairing IS "who voted". On an anonymised '
              'class the row keeps the class and the verb and drops BOTH, so arming the class to study it '
              'cannot re-link what the policy hid',
              len(rows) == 1 and rows[0]['className'] == 'Ballot' and rows[0]['verb'] == 'create'
              and rows[0]['objectId'] == '' and rows[0]['actor'] == '', rows)

        # ---- side channel 3: SecurityEvent.target is the CLASS (op-2 built it here)
        from accessControl.owner_gate import owner_gate_write

        class _R:
            def __init__(self): self.status = '200 OK'; self.media = None; self.headers = {}
            def set_header(self, k, v): self.headers[k] = v

        class _Q:
            def __init__(self, ui): self.context = _types.SimpleNamespace(user_info=ui, roleplay='')

        other_ui = {'sub': OTHER, 'roles': ['voters'], 'raw_claims': {'groups': ['voters']}}
        plan = MealPlan(id='mp-7', owner=VOTER, title='Week 41')
        m.objectTables['MealPlan']['mp-7'] = plan
        owner_gate_write(m, _Q(other_ui), _R(), 'Ballot', 'update', b)
        owner_gate_write(m, _Q(other_ui), _R(), 'MealPlan', 'update', plan)
        targets = {e['target'] for e in O.events(m) if e['source'] == 'accessControl.owner_gate'}
        check('op-2 SIDE CHANNEL 3, the SECURITY EVENT (design §5): a refused act on an ANONYMISED class is '
              'recorded with the CLASS NAME as its target — never `Ballot:b-9`. An id beside a timestamp in a '
              'readable ledger is the third way to name the person, after the owner column and the broadcast. '
              'A non-anonymised owned class keeps `Class:id`, which is what somebody debugging it needs',
              'Ballot' in targets and 'MealPlan:mp-7' in targets and not any(t.startswith('Ballot:') for t in targets),
              sorted(targets))
        check('...and the owner gate records NO actor on those rows: the person refused is the one the owner '
              'rules protect the row FROM, and who performed which class × verb is already counted by '
              'PermissionObservation — one ledger per question',
              all(not e['actor'] for e in O.events(m) if e['source'] == 'accessControl.owner_gate'))

        # ---- frozen_when, the STRUCTURED form (design §2's shape)
        W.set_policy(m, 'Ballot', {'enabled': True, 'owner_verbs': ['read', 'update', 'delete'],
                                   'others_verbs': ['read'], 'others_fields': ['choice'], 'anonymised': True,
                                   'frozen_when': '{"class": "VoteRecord", "field": "state", '
                                                  '"in": ["tallied", "certified"], "via": "vote_record_id"}'},
                     by='admin-0')
        open_v = W.owner_verdict(m, voter_ui, 'update', b)
        vr.state = 'certified'
        shut_v = W.owner_verdict(m, voter_ui, 'update', b)
        read_v = W.owner_verdict(m, voter_ui, 'read', b)
        W.set_policy(m, 'Ballot', {'enabled': True, 'owner_verbs': ['read', 'update'], 'others_verbs': [],
                                   'anonymised': True,
                                   'frozen_when': '{"class": "VoteRecord", "field": "state"}'}, by='admin-0')
        vague = W.owner_verdict(m, voter_ui, 'update', b)
        check('op-2 frozen_when, the STRUCTURED shape the design writes ({"class": "VoteRecord", "field": '
              '"state", "in": [...]}) shares the column with op-0\'s sentence grammar — JSON is what a '
              'MANIFEST can declare, and a person can still type the sentence. Certifying the record freezes '
              'every ballot for its owner too (the vote is over) and READ survives; a spec missing its '
              'operator is NOT frozen, exactly as a malformed sentence is not',
              open_v['allowed'] is True and shut_v['allowed'] is False and shut_v['rule'] == 'frozen'
              and 'certified' in shut_v['why'] and read_v['allowed'] is True and vague['allowed'] is True,
              (open_v['rule'], shut_v['rule'], vague['rule']))
        vr.state = 'open'

        # ---- TRANSFER (design §8)
        api.manager = m
        W.set_policy(m, 'MealPlan', {'enabled': True, 'owner_verbs': ['read', 'update', 'delete'],
                                     'others_verbs': [], 'transfer': 'nobody'}, by='admin-0')
        t_nobody = W.transfer_owner(m, voter_ui, 'MealPlan', 'mp-7', OTHER)
        t_nobody_admin = W.transfer_owner(m, admin_ui, 'MealPlan', 'mp-7', OTHER)
        W.set_policy(m, 'MealPlan', {'enabled': True, 'owner_verbs': ['read', 'update', 'delete'],
                                     'others_verbs': [], 'transfer': 'owner'}, by='admin-0')
        t_name = W.transfer_owner(m, voter_ui, 'MealPlan', 'mp-7', 'demo-other')
        t_self = W.transfer_owner(m, voter_ui, 'MealPlan', 'mp-7', VOTER)
        t_wrong = W.transfer_owner(m, {'sub': OTHER}, 'MealPlan', 'mp-7', OTHER)
        t_ok = W.transfer_owner(m, voter_ui, 'MealPlan', 'mp-7', OTHER)
        t_ballot = W.transfer_owner(m, admin_ui, 'Ballot', 'b-9', OTHER)
        check('op-2 TRANSFER (design §8): `nobody` is the default and even an ADMINISTRATOR does not move an '
              'owner past the class\'s own rule — change the policy first, on the record. Under `owner` the '
              'owner hands the row on and the column really moves; a USERNAME instead of a sub, a transfer to '
              'the current owner, and a transfer by somebody who does not own the row are each refused with '
              'the reason',
              t_nobody['ok'] is False and t_nobody_admin['ok'] is False
              and 'administrator' in t_nobody_admin['refusal']
              and t_name['ok'] is False and 'subject id' in t_name['refusal']
              and t_self['ok'] is False and t_wrong['ok'] is False and t_wrong['status'] == 403
              and t_ok['ok'] is True and plan.owner == OTHER and t_ok['from'] == VOTER,
              (t_nobody.get('refusal', '')[:40], t_ok.get('refusal', ''), plan.owner))
        check('...and NEVER for an ANONYMISED class, whatever its transfer column says: a transfer names the '
              'old owner and the new one in one act, which is exactly what anonymised exists to prevent',
              t_ballot['ok'] is False and t_ballot['status'] == 403 and 'ANONYMISED' in t_ballot['refusal'],
              t_ballot.get('refusal', '')[:80])
        r = _Res(); api.on_post_owned_transfer(_ReqA(voter_ui, media={'to': VOTER}), r, 'Ballot', 'b-9')
        check('POST /api/security/owned/<Class>/<id>/transfer refuses on its OWN authority in every gate mode '
              '— advisory means the CRUDE gate warns instead of blocking an app doing its job, and a transfer '
              'is not that: its only effect IS to move the ownership the gate reads, so a warning that '
              'proceeded would have done the thing it warned about',
              r.status.startswith('403') and r.media['ok'] is False)
    finally:
        os.environ.clear(); os.environ.update(old_env)


def _owned_manifest_checks(_Res, _types, check):
    """op-4 — the `app.owned` manifest stanza: validation, the hand-set survival, and the convergence."""
    from moduleService import manifests as MF
    from security.custom import security_owned as W
    from security.custom import security_owned_manifest as OM

    good = [{'class': 'Ballot', 'enabled': True, 'owner_verbs': ['read', 'update', 'delete'],
             'others_verbs': ['read'], 'others_fields': ['election_id', 'choice', 'groups'],
             'owner_visible': False, 'owner_may_grant': False, 'anonymised': True, 'transfer': 'nobody',
             'frozen_when': {'class': 'VoteRecord', 'field': 'state', 'in': ['tallied', 'certified'],
                             'via': 'vote_record_id'}}]
    check('op-4: a well-formed `app.owned` stanza passes, and its vocabulary is exactly the row class\'s — a '
          'manifest that could declare something `set_policy` refuses would be a stanza that lies',
          MF.owned_findings(good) == [] and MF.owned_findings(None) == []
          and set(MF.OWNED_VERBS) == set(__import__('security.objects.security.OwnedClassPolicy',
                                                    fromlist=['OwnedClassPolicy']).OwnedClassPolicy.OWNER_VERBS)
          and set(MF.OWNED_TRANSFER) == set(__import__('security.objects.security.OwnedClassPolicy',
                                                       fromlist=['OwnedClassPolicy']).OwnedClassPolicy.TRANSFER_MODES),
          MF.owned_findings(good))
    bad = {
        'not a list': MF.owned_findings({'class': 'Ballot'}),
        'no class': MF.owned_findings([{'owner_verbs': ['read']}]),
        'create as a verb': MF.owned_findings([{'class': 'Ballot', 'owner_verbs': ['create']}]),
        'an invented key': MF.owned_findings([{'class': 'Ballot', 'ownerVerbs': ['read']}]),
        'anonymised + owner_visible': MF.owned_findings([{'class': 'Ballot', 'anonymised': True,
                                                          'owner_visible': True}]),
        'anonymised + transfer': MF.owned_findings([{'class': 'Ballot', 'anonymised': True,
                                                     'transfer': 'owner'}]),
        'grant with nothing to give': MF.owned_findings([{'class': 'Plan', 'owner_may_grant': True,
                                                          'grantee_kinds': ['person']}]),
        'bounds on a forbidden sharing': MF.owned_findings([{'class': 'Plan', 'grantable_verbs': ['read']}]),
        'a grantee kind nobody has': MF.owned_findings([{'class': 'Plan', 'owner_may_grant': True,
                                                         'grantable_verbs': ['read'],
                                                         'grantee_kinds': ['everyone']}]),
        'a frozen_when with no operator': MF.owned_findings([{'class': 'Ballot',
                                                              'frozen_when': {'class': 'V', 'field': 'state'}}]),
        'the same class twice': MF.owned_findings([{'class': 'Ballot'}, {'class': 'Ballot'}]),
    }
    check('op-4: every way a stanza can be wrong is a NAMED finding, not a silent default — including the two '
          'contradictions the runtime would otherwise resolve quietly in the anonymity\'s favour (anonymised '
          'beside owner_visible, anonymised beside a transfer) and the two halves of sharing declared apart',
          all(v for v in bad.values()) and any('create' in f for f in bad['create as a verb'])
          and any('anonymised IS owner_visible false' in f for f in bad['anonymised + owner_visible']),
          {k: (v[0][:40] if v else 'NO FINDING') for k, v in bad.items()})
    check('op-4: `validate()` carries the findings, so `manifests conform` reports a bad stanza; and `owned` '
          'joins the HAND-SET keys a regeneration preserves, beside `roles` and `flows` — nothing can derive '
          'which of a module\'s classes belong to the person who created the row, so a refresh must never '
          'silently un-opt a class',
          any('app.owned' in p for p in MF.validate({'schema': MF.SCHEMA, 'app': {'kind': 'polari-app',
                                                                                  'agentTier': 'member',
                                                                                  'owned': [{'class': 'B',
                                                                                             'transfer': 'x'}]}}))
          and "'owned'" in open('moduleService/manifests.py').read().split('_preserve_hand_set')[2])

    # ---- the ONE real declaration, and the convergence
    decls = {d['class']: d for d in OM.declarations()}
    check('op-4: the ONE real declaration on this instance is `polariapps` opting `UserAppPreference` in — the '
          'module that DEFINES the class declares the policy, beside the thing it describes. The security '
          'module ships the mechanism and opts in nobody else\'s classes (its own seed list is empty)',
          'UserAppPreference' in decls and decls['UserAppPreference']['module'] == 'polariapps'
          and not decls['UserAppPreference']['duplicate_of'], sorted(decls))

    class _M:
        pass

    m = _M(); m.objectTables = {'OwnedClassPolicy': {}, 'SecurityEvent': {}}; m.persistTree = lambda: None
    first = OM.ensure_policies(m)
    second = OM.ensure_policies(m)
    pol = W.policy_for(m, 'UserAppPreference')
    check('op-4 CONVERGENCE: the declaration becomes an OwnedClassPolicy row with NOBODY touching an admin '
          'door — the proof design §9 asks op-4 for — and running it again changes nothing (idempotent, which '
          'is what lets it run on every read of the door, the RoleAppBinding discipline from §57)',
          first['created'] == ['UserAppPreference'] and second['created'] == []
          and second['kept'] == ['UserAppPreference'] and pol is not None
          and pol['source'] == 'manifest' and pol['derived_from'] == 'polariapps'
          and pol['owner_field'] == 'sub' and pol['others_verbs'] == [], (first, second, pol))
    W.set_policy(m, 'UserAppPreference', {'enabled': True, 'owner_verbs': ['read'], 'others_verbs': ['read'],
                                          'others_fields': ['primary_role'], 'owner_field': 'sub'},
                 by='admin-0')
    third = OM.ensure_policies(m)
    after = W.policy_for(m, 'UserAppPreference')
    check('op-4: a policy an ADMINISTRATOR set is NEVER overwritten by the derivation (design §7) — the '
          'manifest declaration becomes a named CONFLICT instead of applying, so a deployment that decided '
          'something about its own data keeps its decision and can still see what the app asked for',
          third['created'] == [] and third['updated'] == [] and third['kept'] == ['UserAppPreference']
          and len(third['conflicts']) == 1 and third['conflicts'][0]['class'] == 'UserAppPreference'
          and after['source'] == 'admin' and after['others_verbs'] == ['read'], third)
    check('...and an op-0 SEEDED row (source \'\', written before the stanza existed) IS re-derived: the seed '
          'was this derivation\'s earlier spelling of the same sentence, not somebody\'s decision, so a live '
          'instance converges in place instead of growing a second row for one class',
          W.set_policy(m, 'UserAppPreference', {'enabled': True, 'owner_field': 'sub'}, source='manifest')['ok']
          and [setattr(r, 'source', '') for r in m.objectTables['OwnedClassPolicy'].values()] is not None
          and OM.ensure_policies(m)['updated'] == ['UserAppPreference']
          and len(W._rows(m, 'OwnedClassPolicy')) == 1, len(W._rows(m, 'OwnedClassPolicy')))


def _trace_checks(api, _Res, _types, check):
    """ct-1 — CAUSAL TRACING: the one armed target, the causal map, the effect journal.

    Everything runs against a manager DOUBLE with a temporary knob file and dev posture, exactly as the observe
    checks do: `security_observe._new_row` keeps plain rows in `_FALLBACK` when the manager cannot construct a
    tree object, and `_all_rows` answers them, so the model is exercised end to end without a server."""
    import os
    import tempfile
    from accessControl import cause_context as CC
    from security.custom import security_trace as T

    class _M:
        def __init__(self):
            self.objectTables = {'TraceTarget': {}, 'CausalEdge': {}, 'WriteJournalEntry': {},
                                 'SecurityEvent': {}, 'OwnedClassPolicy': {}}
            self.persistTree = lambda: None

        def noteTreeDeletion(self, className, instanceId):
            return 0

    class _Req:
        def __init__(self, ui=None, media=None, **params):
            self.params = params
            self.media = media or {}
            self.context = _types.SimpleNamespace(user_info=ui, roleplay='')

    SUB = 'dddddddd-4444-4444-8444-dddddddddddd'
    admin = {'sub': SUB, 'roles': ['polari-admin'], 'raw_claims': {'groups': []}}
    old_env = dict(os.environ)
    with tempfile.TemporaryDirectory() as td:
        try:
            os.environ['POLARI_TRACE_KNOB'] = os.path.join(td, 'trace.json')
            os.environ['POLARI_OBSERVE_KNOB'] = os.path.join(td, 'observe.json')
            os.environ['POLARI_PERSIST_DEBOUNCE_SECONDS'] = '0'
            os.environ['POLARI_POSTURE'] = 'production'
            T._STATE.update({'armed': False, 'name': '', 'class_name': '', 'resumed': False,
                             'stopped_name': '', 'stopped_until': 0.0})
            T._TRACED.clear(); T._CREATED.clear()
            m = _M()
            prod = T.arm(m, 'Ballot', user_info=admin)
            check('ct-1: PRODUCTION arms nothing — the refusal names the rule (his ruling 2026-09-18: tracing '
                  'does not occur in production, only the finalized posture rows derived from it)',
                  prod['ok'] is False and 'dev-posture' in prod['refusal'] and T._targets(m) == []
                  and T.tracing_enabled() is False, prod.get('refusal'))

            os.environ['POLARI_POSTURE'] = 'dev'
            a1 = T.arm(m, 'Ballot', user_info=admin)
            a2 = T.arm(m, 'Recipe', user_info=admin)
            import objectTreeDecorators as _otd
            check('ct-1: arming one class works, records the arming `sub` alone (D18-1) and flips the '
                  '__setattr__ seam on; a SECOND arm while one is active is REFUSED naming the active one',
                  a1['ok'] and a1['target']['class_name'] == 'Ballot' and a1['target']['started_by'] == SUB
                  and _otd._TRACE_ARMED is True and _otd._TRACE_CLASS == 'Ballot'
                  and a2['ok'] is False and 'already armed: Ballot' in a2['refusal']
                  and len(T._targets(m)) == 1, a2.get('refusal'))

            # ---- THE SCOPE RULE: a chain that never touches the target writes nothing
            tok = CC.root_cause('api', 'PUT /api/Recipe/{id}', actor=SUB)
            try:
                traced_other = T.touch(m, 'Recipe', 'update')
                T.record_edge(m, 'endpoint:PUT /api/Recipe/{id}', 'object:Recipe:update', 'crude')
                T.record_effect(m, 'Recipe', 'r-1', 'update', ['title'])
            finally:
                CC.pop_cause(tok)
            check('ct-1 THE SCOPE RULE: a chain on ANOTHER class is not traced and writes nothing — neither '
                  'ledger, no counter moved (the cause is still minted; it is simply ignored)',
                  traced_other is False and T.edges(m) == [] and T.journal(m) == []
                  and T.status(m)['target']['traces_opened'] == 0, (len(T.edges(m)), len(T.journal(m))))

            # ---- counted, deduped, and the budget that disarms itself
            tok = CC.root_cause('api', 'PUT /api/Ballot/{id}', actor=SUB)
            try:
                traced = T.touch(m, 'Ballot', 'update')
                for _ in range(3):
                    T.record_edge(m, 'endpoint:PUT /api/Ballot/{id}', 'object:Ballot:update', 'crude')
                T.record_edge(m, 'object:Ballot:update', 'event:trigger:tally', 'trigger-fire')
                over = T.record_edge(m, 'event:trigger:tally', 'solution:tally-votes', 'solution-run',
                                     run_as='definer')
                after = T.record_edge(m, 'object:Ballot:update', 'event:topic:Ballot', 'ws-publish')
            finally:
                CC.pop_cause(tok)
            rows = {e['name']: e for e in T.edges(m)}
            check('ct-1: edges are COUNTED and never duplicated — the same crossing three times is ONE row with '
                  'count 3 — and the chain is traced from the first touch of the target class',
                  traced is True and len(rows) == 4 and over is not None and after is not None
                  and rows['endpoint:PUT /api/Ballot/{id}|object:Ballot:update|crude']['count'] == 3
                  and rows['object:Ballot:update|event:trigger:tally|trigger-fire']['count'] == 1
                  and rows['event:trigger:tally|solution:tally-votes|solution-run']['run_as'] == 'definer'
                  and rows['endpoint:PUT /api/Ballot/{id}|object:Ballot:update|crude']['sample_trace_id'],
                  sorted(rows))
            T.disarm(m, 'manual')

            # ---- THE BUDGET RULE, on its own target: the first hit disarms, states why, and is not silent
            mb = _M()
            T.arm(mb, 'Ballot', max_edges=2, user_info=admin)
            tok = CC.root_cause('api', 'PUT /api/Ballot/{id}', actor=SUB)
            try:
                T.touch(mb, 'Ballot', 'update')
                T.record_edge(mb, 'endpoint:PUT /api/Ballot/{id}', 'object:Ballot:update', 'crude')
                T.record_edge(mb, 'object:Ballot:update', 'event:trigger:tally', 'trigger-fire')
                hit = T.record_edge(mb, 'event:trigger:tally', 'solution:tally-votes', 'solution-run')
                nxt = T.record_edge(mb, 'object:Ballot:update', 'event:topic:Ballot', 'ws-publish')
            finally:
                CC.pop_cause(tok)
            target = T.status(mb)['coverage'][0]
            ev = [e for e in O_events(mb) if e['control'] == 'trace']
            check('ct-1 THE BUDGET RULE: the third edge hits max_edges=2 — the target DISARMS itself, stamps '
                  'stopped_because=budget-edges, writes ONE SecurityEvent, and every write declined afterwards '
                  'inside the window increments `dropped` (2: the one that hit it and the one after)',
                  hit is None and nxt is None and T.status(mb)['armed'] is False
                  and target['stopped_because'] == 'budget-edges' and target['active'] is False
                  and target['dropped'] == 2 and target['edges_written'] == 2 and len(T.edges(mb)) == 2
                  and len(ev) == 1 and ev[0]['count'] == 1 and _otd._TRACE_ARMED is False,
                  (target, [e['name'] for e in ev]))

            # ---- the effect journal, the anonymised rule, and clearing on the next arm
            m2 = _M()
            T.arm(m2, 'Ballot', user_info=admin)
            tok = CC.root_cause('api', 'PUT /api/Ballot/{id}', actor=SUB)
            try:
                T.touch(m2, 'Ballot', 'update')
                T.record_effect(m2, 'Ballot', 'b-1', 'update', ['choice'])
                T.record_effect(m2, 'Ballot', 'b-2', 'delete')
                trace_id = CC.current_cause()['trace_id']
            finally:
                CC.pop_cause(tok)
            jr = T.journal(m2)
            check('ct-1 LEDGER B: a local write under a traced chain journals class, verb, instance, the field '
                  'NAMES (never a value), the trace id, the door it came from, origin=local and the target',
                  len(jr) == 2 and jr[0]['className'] == 'Ballot' and jr[0]['verb'] == 'update'
                  and jr[0]['objectId'] == 'b-1' and jr[0]['fieldsChanged'] == '["choice"]'
                  and jr[0]['traceId'] == trace_id and jr[0]['causeRef'] == 'PUT /api/Ballot/{id}'
                  and jr[0]['origin'] == 'local' and jr[0]['actor'] == SUB and jr[0]['target'] == 'Ballot'
                  and T.journal(m2, trace_id='nope') == [], jr)
            from security.objects.security.OwnedClassPolicy import OwnedClassPolicy as _OCP
            from security.custom.security_observe import _new_row as _nr
            _nr(m2, m2.objectTables, 'OwnedClassPolicy', _OCP,
                {'name': 'Ballot', 'class_name': 'Ballot', 'enabled': True, 'anonymised': True})
            tok = CC.root_cause('api', 'PUT /api/Ballot/{id}', actor=SUB)
            try:
                T.touch(m2, 'Ballot', 'update')
                T.record_effect(m2, 'Ballot', 'b-3', 'update', ['choice'])
            finally:
                CC.pop_cause(tok)
            anon = T.journal(m2)[-1]
            check('ct-1 (design §5): for a class whose OwnedClassPolicy is ANONYMISED the journal row keeps the '
                  'class and the verb and drops BOTH the actor and the object id — tracing a deliberately '
                  'unlinkable class must not re-link it',
                  anon['className'] == 'Ballot' and anon['verb'] == 'update'
                  and anon['objectId'] == '' and anon['actor'] == '' and anon['fieldsChanged'] == '["choice"]',
                  anon)
            T.disarm(m2, 'manual')
            armed_again = T.arm(m2, 'Recipe', user_info=admin)
            check('ct-1: arming the NEXT target CLEARS the journal (evidence for the current question) while the '
                  'map is kept, and the previous target stays as a coverage row',
                  armed_again['ok'] and armed_again['journal_cleared'] == 3 and T.journal(m2) == []
                  and [c['class_name'] for c in T.coverage(m2)] == ['Ballot', 'Recipe'],
                  armed_again.get('journal_cleared'))

            # ---- the window, and the restart rule
            row = T.active_target(m2)
            row.started_at = '2020-01-01T00:00:00Z'
            row.window_seconds = 60
            check('ct-1: `window_seconds` disarms LAZILY on the next write or status read, stamped `window`',
                  T.active_target(m2) is None and T.status(m2)['armed'] is False
                  and [c for c in T.coverage(m2) if c['class_name'] == 'Recipe'][0]['stopped_because'] == 'window')
            m3 = _M()
            T.arm(m3, 'Ballot', user_info=admin)
            T._STATE.update({'armed': False, 'name': '', 'class_name': '', 'resumed': False})
            T._TRACED.clear()
            st = T.status(m3)
            check('ct-1 SURVIVE A RESTART: a knob naming a target that THIS process did not arm is a restart — '
                  'the row is stopped with stopped_because=restart and the knob cleared, so the counters read '
                  'honestly instead of a target resuming with its live state gone',
                  st['armed'] is False and T.coverage(m3)[0]['stopped_because'] == 'restart'
                  and T.knob_state()['target'] == '', (st['armed'], T.coverage(m3)))

            # ---- the map ceiling
            m4 = _M()
            T.arm(m4, 'Ballot', user_info=admin)
            tok = CC.root_cause('api', 'PUT /api/Ballot/{id}', actor=SUB)
            try:
                T.touch(m4, 'Ballot', 'update')
                for i in range(4):
                    T.record_edge(m4, 'endpoint:PUT /api/Ballot/{id}', 'object:Ballot:v%d' % i, 'crude')
            finally:
                CC.pop_cause(tok)
            for i, e in enumerate(sorted(T._edges(m4), key=lambda r: r.effect)):
                e.last_seen = '2026-09-1%dT00:00:00Z' % i
            pruned = T.prune_map(m4, limit=2)
            kept = sorted(e['effect'] for e in T.edges(m4))
            check('ct-1: the map has its OWN ceiling (POLARI_TRACE_MAP_MAX_ROWS, default 5000) — the oldest '
                  '`last_seen` rows are pruned so twenty targets over a year cannot grow it without bound',
                  pruned == 2 and kept == ['object:Ballot:v2', 'object:Ballot:v3'], (pruned, kept))
            T.disarm(m4, 'manual')

            # ---- the __setattr__ seam itself (design §3c): the field NAME, never the value, and only the
            # target class; and the assignments a CONSTRUCTOR makes belong to the create row, not to N updates.
            m6 = _M()
            T.arm(m6, 'Ballot', user_info=admin)
            fake = type('Ballot', (object,), {})()
            fake.__dict__.update({'manager': m6, 'id': 'b-9'})
            other = type('Recipe', (object,), {})()
            other.__dict__.update({'manager': m6, 'id': 'r-9'})
            tok = CC.root_cause('api', 'PUT /api/Ballot/{id}', actor=SUB)
            try:
                T.touch(m6, 'Ballot', 'update')
                _otd._trace_setattr(fake, 'choice')
                _otd._trace_setattr(fake, 'manager')        # the tree's own plumbing, never a field somebody set
                _otd._trace_setattr(other, 'title')         # another class: the seam stops at the name check
                T.record_effect(m6, 'Ballot', 'b-8', 'create', [])
                _otd._trace_setattr(fake, 'choice')
            finally:
                CC.pop_cause(tok)
            j6 = T.journal(m6)
            m6created = _M()
            T.arm(m6created, 'Ballot', user_info=admin)
            tok = CC.root_cause('api', 'POST /api/Ballot', actor=SUB)
            try:
                T.touch(m6created, 'Ballot', 'create')
                T.record_effect(m6created, 'Ballot', 'b-7', 'create', [])
                T.record_effect(m6created, 'Ballot', 'b-7', 'update', ['choice'])
                T.record_effect(m6created, 'Ballot', 'b-7', 'update', ['election_id'])
            finally:
                CC.pop_cause(tok)
            check('ct-1 the __setattr__ seam: an update on the TARGET class journals the FIELD NAME (never the '
                  'value); the tree\'s own plumbing attributes and every other class write nothing; and the '
                  'assignments a constructor makes are the CREATE row, not N update rows after it',
                  [(r['objectId'], r['verb'], r['fieldsChanged']) for r in j6]
                  == [('b-9', 'update', '["choice"]'), ('b-8', 'create', '[]'), ('b-9', 'update', '["choice"]')]
                  and [(r['objectId'], r['verb']) for r in T.journal(m6created)] == [('b-7', 'create')],
                  [(r['objectId'], r['verb'], r['fieldsChanged']) for r in j6])
            T.disarm(m6, 'manual')
            T.disarm(m6created, 'manual')

            # ---- the doors, and the §54 route guard for the three new suffixes
            class _Falcon:
                def __init__(self): self.routes = []
                def add_route(self, uri, resource, suffix=None): self.routes.append((uri, suffix))

            class _Srv:
                def __init__(self): self.falconServer = _Falcon()
            srv = _Srv()
            from security.security_api import SecurityAPI as _API
            probe = _API(polServer=srv, manager=None)
            trace_routes = [(u, sfx) for u, sfx in srv.falconServer.routes
                            if u.startswith('/api/security/trace') or u.endswith('/observe/trace')]
            check('§54 guard: the three ct-1 doors register and each has its on_<method>_<suffix> responder — a '
                  'drifted suffix RAISES from add_route() and takes the backend down at boot',
                  trace_routes == [('/api/security/observe/trace', 'observe_trace'),
                                   ('/api/security/trace/edges', 'trace_edges'),
                                   ('/api/security/trace/journal', 'trace_journal')]
                  and all(any(hasattr(probe, 'on_%s_%s' % (mm, sfx)) for mm in ('get', 'post', 'delete'))
                          for _u, sfx in trace_routes), trace_routes)
            m5 = _M()
            from security.custom.security_observe import set_roleplay_groups
            set_roleplay_groups(['developers'], by=SUB)
            api.manager = m5
            r = _Res(); api.on_post_observe_trace(_Req({'roles': ['journalist']}, {'class_name': 'Ballot'}), r)
            check('ct-1: arming is a permissions-administration act — a caller without the role-play permission '
                  'is 403 with the reason, and nothing is armed',
                  r.status.startswith('403') and T._targets(m5) == [], r.media.get('refusal'))
            r = _Res(); api.on_post_observe_trace(_Req(admin, {'class_name': 'Ballot', 'max_edges': 9}), r)
            r2 = _Res(); api.on_post_observe_trace(_Req(admin, {'class_name': 'Ballot'}), r2)
            r3 = _Res(); api.on_get_observe_trace(_Req(admin), r3)
            r4 = _Res(); api.on_delete_observe_trace(_Req(admin), r4)
            r5 = _Res(); api.on_get_trace_edges(_Req(admin), r5)
            r6 = _Res(); api.on_get_trace_journal(_Req(admin), r6)
            check('ct-1: the doors answer — POST arms (409 on the second), GET carries the target, the counters '
                  'and the COVERAGE block, DELETE disarms, and both ledger doors list with their reading',
                  r.media['ok'] and r.media['target']['max_edges'] == 9 and r2.status.startswith('409')
                  and r3.media['armed'] is True and r3.media['target']['class_name'] == 'Ballot'
                  and r3.media['coverage'][0]['class_name'] == 'Ballot'
                  and r4.media['ok'] and r4.media['armed'] is False
                  and r5.media['ok'] and 'NOT been traced' in r5.media['how']
                  and r6.media['ok'] and 'anonymised' in r6.media['how'],
                  (r2.status, r3.media.get('armed')))
        finally:
            T._STATE.update({'armed': False, 'name': '', 'class_name': '', 'resumed': True,
                             'stopped_name': '', 'stopped_until': 0.0})
            T._set_armed_flag(False, '')
            os.environ.clear(); os.environ.update(old_env)


class _TraceM:
    """The manager DOUBLE the ct-2/ct-4 checks run against — `security_observe._new_row` keeps plain rows in
    `_FALLBACK` when the manager cannot construct a tree object, and `_all_rows` answers them, so the whole
    model is exercised end to end without a server."""

    def __init__(self):
        self.objectTables = {'TraceTarget': {}, 'CausalEdge': {}, 'WriteJournalEntry': {}, 'SecurityEvent': {},
                             'OwnedClassPolicy': {}, 'AppPermissionProfile': {}, 'PermissionObservation': {},
                             'UsageObservation': {}, 'ObservationSession': {},
                             'OutboundPolicy': {}, 'InboundPolicy': {}}
        self.persistTree = lambda: None

    def noteTreeDeletion(self, className, instanceId):
        return 0


def _trace_env(td):
    import os
    os.environ['POLARI_TRACE_KNOB'] = os.path.join(td, 'trace.json')
    os.environ['POLARI_OBSERVE_KNOB'] = os.path.join(td, 'observe.json')
    os.environ['POLARI_PERSIST_DEBOUNCE_SECONDS'] = '0'
    os.environ['POLARI_POSTURE'] = 'dev'


def _ct9_checks(_types, check):
    """ct-9 — THE TRAFFIC POLICIES (design §5a): closed by default, suggested from dev monitoring, confirmed by
    a person, enforced in production.

    Everything runs against a manager DOUBLE with dev posture and a temporary knob, exactly as the ct-1 checks
    do. The two halves are proven at their real seams: the OUTBOUND half through `polariApiServer.outbound`
    (the wrapper every send passes) and the INBOUND half through `accessControl.traffic_middleware` (the
    middleware every request passes), so what is proven is the ladder as it actually runs."""
    import json
    import os
    import tempfile

    import falcon

    from accessControl import traffic_middleware as TM
    from polariApiServer import outbound as OB
    from security.custom import security_traffic as TR

    class _M:
        def __init__(self):
            self.objectTables = {'OutboundPolicy': {}, 'InboundPolicy': {}, 'SecurityEvent': {},
                                 'PeerNode': {}}
            self.persistTree = lambda: None

        def noteTreeDeletion(self, className, instanceId):
            return 0

    class _Req:
        """The half of a falcon request the gate touches — headers, path, method, template, context."""

        def __init__(self, headers=None, path='/api/MealEntry/m-1', method='GET', template=''):
            self._h = {k.lower(): v for k, v in (headers or {}).items()}
            self.path = path
            self.method = method
            self.uri_template = template
            self.params = {}
            self.media = {}
            self.context = _types.SimpleNamespace(user_info=None, roleplay='')

        def get_header(self, name):
            return self._h.get(str(name).lower())

    class _Resp:
        def __init__(self):
            self.h = {}
            self.status = '200 OK'
            self.media = None

        def set_header(self, k, v):
            self.h[k] = v

    class _ApiReq:
        def __init__(self, ui=None, media=None, **params):
            self.params = params
            self.media = media or {}
            self.context = _types.SimpleNamespace(user_info=ui, roleplay='')

    from security.custom.security_observe import _all_rows as _TRrows   # tree rows + the test fallback

    SUB = 'eeeeeeee-5555-4555-8555-eeeeeeeeeeee'
    admin = {'sub': SUB, 'roles': ['polari-admin'], 'raw_claims': {'groups': []}}
    plain = {'sub': 'ffffffff-6666-4666-8666-ffffffffffff', 'roles': ['polari-viewer'],
             'raw_claims': {'groups': []}}
    old_env = dict(os.environ)
    with tempfile.TemporaryDirectory() as td:
        try:
            os.environ['POLARI_OBSERVE_KNOB'] = os.path.join(td, 'observe.json')
            os.environ['POLARI_TRACE_KNOB'] = os.path.join(td, 'trace.json')
            os.environ['POLARI_PERSIST_DEBOUNCE_SECONDS'] = '0'
            os.environ['POLARI_POSTURE'] = 'dev'
            os.environ['POLARI_APP_PERMISSIONS'] = 'advisory'

            # ---- THE MONITORING: one observed send with no row writes ONE suggested row; the second bumps it
            m = _M()
            TM.drain_advisories()
            r1 = OB.send('odoo', 'main', 'json-rpc', lambda: 'ok',
                         payload_classes=('ProductOrder',), manager=m)
            r2 = OB.send('odoo', 'main', 'json-rpc', lambda: 'ok',
                         payload_classes=('StockMove',), manager=m)
            rows = TR.policies(m)['outbound']
            check('ct-9 THE MONITORING: an observed send with NO policy row writes ONE `suggested` row from the '
                  'observation itself (his "suggest outbound and inbounds based on our monitoring of traffic in '
                  'and out of polari"); the SECOND send of the same edge bumps the count instead of duplicating, '
                  'and the payload CLASSES accumulate — never a payload, never a URL',
                  r1 == 'ok' and r2 == 'ok' and len(rows) == 1 and rows[0]['name'] == 'odoo|main|json-rpc'
                  and rows[0]['state'] == 'suggested' and rows[0]['count'] == 2
                  and json.loads(rows[0]['payload_classes_json']) == ['ProductOrder', 'StockMove']
                  and rows[0]['confirmed_by'] == '', rows)
            adv = TM.advisories()
            check('ct-9 ADVISORY: an unconfirmed send under `advisory` goes through and parks its would-deny for '
                  'the response (dev warns, never blocks — §17); the line names the system, never the URL',
                  r1 == 'ok' and adv == ['would-deny outbound odoo:main'], adv)

            # ---- the advisory reaches the caller through the ONE header, drained by the cause middleware
            from accessControl.cause_middleware import CauseContextMiddleware
            hdr_req, hdr_resp = _Req(), _Resp()
            CauseContextMiddleware().process_response(hdr_req, hdr_resp, None, True)
            check('ct-9: `CauseContextMiddleware.process_response` drains the parked lines into ONE header, '
                  'X-Polari-Traffic-Advisory, and the drain empties them so nothing leaks into the next response',
                  hdr_resp.h.get(TM.TRAFFIC_ADVISORY_HEADER) == 'would-deny outbound odoo:main'
                  and TM.advisories() == [], hdr_resp.h)

            # ---- ENFORCE: the same unconfirmed send is REFUSED before `fn` runs
            os.environ['POLARI_APP_PERMISSIONS'] = 'enforce'
            ran = {'n': 0}

            def _fn():
                ran['n'] += 1
                return 'should not happen'

            try:
                OB.send('odoo', 'main', 'json-rpc', _fn, payload_classes=('ProductOrder',), manager=m)
                refused = None
            except OB.OutboundRefused as exc:
                refused = exc
            check('ct-9 CLOSED BY DEFAULT under `enforce`: an unconfirmed send raises OutboundRefused and the '
                  'call NEVER runs; the refusal names the policy row, its state and the door that confirms it',
                  refused is not None and ran['n'] == 0 and 'odoo|main|json-rpc' in str(refused)
                  and 'suggested' in str(refused) and '/api/security/traffic/outbound/' in str(refused),
                  str(refused))

            # ---- A PERSON RULES: 401 without a sub, 403 without an admin role, the `sub` alone is stored
            no_sub = TR.confirm_outbound(m, 'odoo|main|json-rpc', None, 'confirmed')
            not_admin = TR.confirm_outbound(m, 'odoo|main|json-rpc', plain, 'confirmed')
            bad = TR.confirm_outbound(m, 'odoo|main|json-rpc', admin, 'maybe')
            missing = TR.confirm_outbound(m, 'nope|nope|nope', admin, 'confirmed')
            ok = TR.confirm_outbound(m, 'odoo|main|json-rpc', admin, 'confirmed')
            row = TR.policies(m)['outbound'][0]
            check('ct-9 NOTHING CONFIRMS ITSELF: confirming needs a signed-in PERSON (401 without a `sub`) who '
                  'is an administrator (403 otherwise); the decision must be confirmed|denied (400); a row '
                  'nothing proposed is 404; and the row stores the opaque Keycloak `sub` ALONE (D18-1)',
                  no_sub['status'] == 401 and not_admin['status'] == 403 and bad['status'] == 400
                  and missing['status'] == 404 and ok['ok'] and row['state'] == 'confirmed'
                  and row['confirmed_by'] == SUB and row['confirmed_at']
                  and 'preferred_username' not in json.dumps(row),
                  (no_sub.get('status'), not_admin.get('status'), row))

            went = OB.send('odoo', 'main', 'json-rpc', lambda: 'through', payload_classes=('ProductOrder',),
                           manager=m)
            v_ok = TR.outbound_verdict(m, 'odoo', 'main', 'json-rpc', ['ProductOrder'])
            check('ct-9: once a person has CONFIRMED it, the same send goes through under `enforce` and the '
                  'verdict says which rule allowed it', went == 'through' and v_ok['allowed'] is True
                  and v_ok['rule'] == 'confirmed', v_ok)

            # ---- DENIED: refused under enforce, advisory-only under advisory, untouched under off
            TR.confirm_outbound(m, 'odoo|main|json-rpc', admin, 'denied')
            try:
                OB.send('odoo', 'main', 'json-rpc', lambda: 'x', manager=m)
                den_enf = None
            except OB.OutboundRefused as exc:
                den_enf = exc
            os.environ['POLARI_APP_PERMISSIONS'] = 'advisory'
            TM.drain_advisories()
            den_adv = OB.send('odoo', 'main', 'json-rpc', lambda: 'still sent', manager=m)
            adv2 = TM.advisories()
            os.environ['POLARI_APP_PERMISSIONS'] = 'off'
            TM.drain_advisories()
            den_off = OB.send('odoo', 'main', 'json-rpc', lambda: 'sent', manager=m)
            off_adv = TM.advisories()
            v_off = TR.outbound_verdict(m, 'odoo', 'main', 'json-rpc')
            check('ct-9 THE LADDER, one knob (POLARI_APP_PERMISSIONS, the same one every other gate reads): a '
                  'DENIED policy refuses under `enforce`, warns-and-proceeds under `advisory`, and under `off` '
                  'the verdict is still computed (so the monitoring never stops) and NOTHING acts on it',
                  den_enf is not None and den_adv == 'still sent' and adv2 == ['would-deny outbound odoo:main']
                  and den_off == 'sent' and off_adv == [] and v_off['allowed'] is False
                  and v_off['rule'] == 'denied' and v_off['knob'] == 'off', (adv2, off_adv, v_off['rule']))
            os.environ['POLARI_APP_PERMISSIONS'] = 'enforce'

            # ---- NO TRACING IN PRODUCTION: a missing row is refused, and no row is written
            mp = _M()
            os.environ['POLARI_POSTURE'] = 'production'
            try:
                OB.send('livekit', 'meetings', 'rest', lambda: 'x', manager=mp)
                prod_refused = None
            except OB.OutboundRefused as exc:
                prod_refused = exc
            prod_rows = TR.policies(mp)['outbound']
            prod_events = [e for e in O_events(mp) if e['control'] == 'traffic']
            check('ct-9 NO TRACING IN PRODUCTION (his ruling 2026-09-18): a send with no confirmed row is simply '
                  'REFUSED under enforce — no `suggested` row is derived there, because production carries the '
                  'finalized rows and derives nothing; the refusal is still accountable as a counted SecurityEvent',
                  prod_refused is not None and prod_rows == [] and len(prod_events) == 1
                  and prod_events[0]['outcome'] == 'denied' and prod_events[0]['target'] == 'livekit|meetings|rest',
                  (len(prod_rows), prod_events))
            os.environ['POLARI_POSTURE'] = 'dev'

            # ---- an instance with NO security rows is never blocked by a policy it does not have
            class _NoTables:
                objectTables = None
            v_none = TR.outbound_verdict(_NoTables(), 'odoo', 'main', 'json-rpc')
            check('ct-9: an instance with no security rows answers `no-security` and ALLOWS — a guard that '
                  'cannot be consulted must not be able to take the outbound path down (outbound.py rule 3)',
                  v_none['allowed'] is True and v_none['rule'] == 'no-security', v_none)

            # ---- THE INBOUND HALF: the classification, and never an address
            mi = _M()
            # a PeerNode row straight on the table: the gate is CORE-resident and reads the manager's own
            # tables, never the security module's test fallback
            mi.objectTables['PeerNode']['p-1'] = _types.SimpleNamespace(
                name='kitchen-node', base_url='http://kitchen-node:3000')
            os.environ['POLARI_APP_PERMISSIONS'] = 'off'
            mw = TM.TrafficPolicyMiddleware(_types.SimpleNamespace(manager=mi))
            origin_req = _Req({'Origin': 'https://app.example:4200/some/path?token=sekrit'})
            anon_req = _Req({})
            peer_req = _Req({'X-Polari-Trace': 'abc/def'})
            named_peer = _Req({'Origin': 'http://kitchen-node:3000'})
            ip_req = _Req({'Origin': 'http://192.168.7.9:4200'})
            for q in (origin_req, anon_req, peer_req, named_peer, ip_req):
                mw.process_request(q, _Resp())
            names = sorted(r['name'] for r in TR.policies(mi)['inbound'])
            sources = {r['name']: (r['source_kind'], r['source']) for r in TR.policies(mi)['inbound']}
            check('ct-9 INBOUND CLASSIFICATION: an Origin becomes `origin:<scheme>://<host>` with the port, the '
                  'path and the query STRIPPED; a registered peer is its NAME; an `X-Polari-Trace` with no '
                  'registered sender is still a peer (`unregistered`); no Origin at all is the class '
                  '`anonymous`; and an IP-LITERAL Origin collapses to the class `ip-literal` — a raw address '
                  'NEVER lands in a row',
                  names == ['anonymous|anonymous', 'origin|https://app.example', 'origin|ip-literal',
                            'peer|kitchen-node', 'peer|unregistered']
                  and sources['origin|https://app.example'] == ('origin', 'https://app.example')
                  and sources['origin|ip-literal'] == ('origin', 'ip-literal')
                  and not any('192.168' in v[1] for v in sources.values()),
                  names)
            check('ct-9: the normaliser itself — scheme + host only, a bare IPv4 or IPv6 host is `ip-literal`, '
                  'and a `null` Origin is nothing at all',
                  TM.normalise_origin('https://App.Example:8443/x?y=1') == 'https://app.example'
                  and TM.normalise_origin('http://10.0.0.4') == 'ip-literal'
                  and TM.normalise_origin('http://[fe80::1]:80') == 'ip-literal'
                  and TM.normalise_origin('null') == '' and TM.normalise_origin('') == '',
                  TM.normalise_origin('https://App.Example:8443/x?y=1'))

            # ---- the paths are TEMPLATES, refined in process_resource, and capped at 50
            res_req = _Req({'Origin': 'https://app.example'}, path='/api/MealEntry/m-1')
            mw.process_request(res_req, _Resp())     # falcon has not routed yet: no template, no path recorded
            res_req.uri_template = '/api/MealEntry/{id}'
            mw.process_resource(res_req, _Resp(), None, {})
            for i in range(60):
                TR.note_inbound_path(mi, 'origin|https://app.example', 'GET /api/Thing%d/{id}' % i)
            paths = json.loads([r for r in TR.policies(mi)['inbound']
                                if r['name'] == 'origin|https://app.example'][0]['paths_json'])
            check('ct-9: an inbound row remembers the endpoint TEMPLATE falcon resolved (refined in '
                  '`process_resource`, exactly as ct-0 refines the cause), never the real path — and the list '
                  'is capped at 50 so a crawler cannot grow a row without bound',
                  paths[0] == 'GET /api/MealEntry/{id}' and not any('m-1' in p for p in paths)
                  and len(paths) == TR.MAX_PATHS, (len(paths), paths[:3]))

            # ---- the inbound ladder at the middleware: advisory warns, enforce refuses BEFORE the responder
            os.environ['POLARI_APP_PERMISSIONS'] = 'advisory'
            TM.drain_advisories()
            adv_req, adv_resp = _Req({'Origin': 'https://app.example'}), _Resp()
            mw.process_request(adv_req, adv_resp)
            in_adv = TM.advisories()
            os.environ['POLARI_APP_PERMISSIONS'] = 'enforce'
            enf_req = _Req({'Origin': 'https://app.example'})
            try:
                mw.process_request(enf_req, _Resp())
                in_refused = None
            except falcon.HTTPForbidden as exc:
                in_refused = exc
            health_req = _Req({'Origin': 'https://app.example'}, path='/api/health')
            door_req = _Req({'Origin': 'https://app.example'}, path='/api/security/traffic')
            never = []
            for q in (health_req, door_req):
                try:
                    mw.process_request(q, _Resp())
                except falcon.HTTPForbidden:
                    never.append(q.path)
            check('ct-9 THE INBOUND LADDER: `advisory` lets the caller in and parks the would-deny; `enforce` is '
                  'a 403 raised from `process_request`, BEFORE the responder runs, with the evidence — and two '
                  'doors are never refused whatever the mode, so an enforcing instance cannot lock its own '
                  'administrator out of the door that confirms the policy',
                  in_adv == ['would-deny inbound origin:https://app.example'] and in_refused is not None
                  and 'would-deny inbound origin:https://app.example' in str(in_refused.description)
                  and '/api/security/traffic/inbound/' in str(in_refused.description) and never == [],
                  (in_adv, never))

            # ---- confirming an inbound source, and the DECLARED flows the topology draws
            TR.confirm_inbound(mi, 'origin|https://app.example', admin, 'confirmed')
            allowed_req = _Req({'Origin': 'https://app.example'})
            mw.process_request(allowed_req, _Resp())
            flows = TR.declared_flows(mi)
            out_flows = TR.declared_flows(m)
            check('ct-9: a CONFIRMED inbound source is let in under `enforce`, and `declared_flows` answers the '
                  'topology (design §7) one entry per confirmed row — direction, the counterpart, the wire, the '
                  'classes and the §2 node string; an inbound entry carries its templates and an honestly EMPTY '
                  'class list, because what a caller sends is an object edge, not traffic',
                  allowed_req.context.traffic['allowed'] is True and len(flows) == 1
                  and flows[0]['direction'] == 'inbound' and flows[0]['source'] == 'origin:https://app.example'
                  and flows[0]['node'] == 'inbound:origin:https://app.example' and flows[0]['classes'] == []
                  and 'GET /api/MealEntry/{id}' in flows[0]['paths'] and flows[0]['confirmed_by'] == SUB
                  and out_flows == [], (flows, out_flows))
            TR.confirm_outbound(m, 'odoo|main|json-rpc', admin, 'confirmed')
            of = TR.declared_flows(m)
            check('ct-9: a confirmed OUTBOUND row declares its edge with the system, the wire and the payload '
                  'CLASSES that were observed crossing it — the `declared` half of the §7 drift report',
                  len(of) == 1 and of[0]['direction'] == 'outbound' and of[0]['system'] == 'odoo:main'
                  and of[0]['node'] == 'external:odoo:main' and of[0]['means'] == 'json-rpc'
                  and of[0]['classes'] == ['ProductOrder', 'StockMove'] and of[0]['provenance'] == 'declared',
                  of)

            # ---- the suggestion list IS the monitoring
            sug = TR.suggestions(mi)
            check('ct-9: `suggestions` is the monitoring — every row nobody has ruled on, busiest first, with '
                  'its count and what derived it, and it does NOT list the one already confirmed',
                  all(r['state'] == 'suggested' for r in sug['inbound'])
                  and 'origin|https://app.example' not in [r['name'] for r in sug['inbound']]
                  and sug['inbound'][0]['count'] >= sug['inbound'][-1]['count']
                  and 'dev posture' in sug['inbound'][0]['derived_from'], [r['name'] for r in sug['inbound']])

            # ---- the doors, and the §54 route guard for the four new suffixes
            class _Falcon:
                def __init__(self): self.routes = []
                def add_route(self, uri, resource, suffix=None): self.routes.append((uri, suffix))

            class _Srv:
                def __init__(self): self.falconServer = _Falcon()
            srv = _Srv()
            from security.security_api import SecurityAPI as _API
            probe = _API(polServer=srv, manager=None)
            traffic_routes = [(u, sfx) for u, sfx in srv.falconServer.routes
                              if u.startswith('/api/security/traffic')]
            check('§54 guard: the four ct-9 doors register and each has its on_<method>_<suffix> responder — a '
                  'drifted suffix RAISES from add_route() and takes the backend down at boot',
                  traffic_routes == [('/api/security/traffic', 'traffic'),
                                     ('/api/security/traffic/declared', 'traffic_declared'),
                                     ('/api/security/traffic/outbound', 'traffic_outbound_body'),
                                     ('/api/security/traffic/inbound', 'traffic_inbound_body'),
                                     ('/api/security/traffic/outbound/{name}', 'traffic_outbound'),
                                     ('/api/security/traffic/inbound/{name}', 'traffic_inbound')]
                  and all(any(hasattr(probe, 'on_%s_%s' % (mm, sfx)) for mm in ('get', 'post'))
                          for _u, sfx in traffic_routes), traffic_routes)
            probe.manager = mi
            anon_r = _Resp(); probe.on_get_traffic(_ApiReq(), anon_r)
            get_r = _Resp(); probe.on_get_traffic(_ApiReq(admin), get_r)
            dec_r = _Resp(); probe.on_get_traffic_declared(_ApiReq(admin), dec_r)
            no_r = _Resp(); probe.on_post_traffic_inbound(_ApiReq(plain, {'decision': 'confirmed'}),
                                                         no_r, 'anonymous|anonymous')
            yes_r = _Resp(); probe.on_post_traffic_inbound(_ApiReq(admin, {'decision': 'denied'}),
                                                          yes_r, 'anonymous|anonymous')
            check('ct-9 THE DOORS: GET /api/security/traffic needs a signed-in caller (401) and answers the '
                  'policies, the suggestions, the declared flows and the mode; POST .../inbound/<name> is an '
                  'administrator\'s ruling (403 otherwise) and lands the state with the person on it',
                  anon_r.status.startswith('401') and get_r.media['ok']
                  and get_r.media['mode'] == 'enforce' and 'suggestions' in get_r.media
                  and 'closed by default' in get_r.media['how'] and dec_r.media['ok']
                  and no_r.status.startswith('403') and yes_r.media['ok']
                  and yes_r.media['policy']['state'] == 'denied'
                  and yes_r.media['policy']['confirmed_by'] == SUB,
                  (anon_r.status, no_r.status, yes_r.media))

            # ---- §66a, found by the LIVE PROOF on `polari-lean`: a name a URL path cannot carry
            web = TR.inbound_name('origin', 'https://prf.example')
            TR.inbound_verdict(mi, 'origin', 'https://prf.example', '')   # the row the live stack had
            router = falcon.routing.CompiledRouter()
            router.add_route('/api/security/traffic/inbound/{name}', probe)
            router.add_route('/api/security/traffic/inbound', probe)
            routed_path = router.find('/api/security/traffic/inbound/' + web)
            routed_body = router.find('/api/security/traffic/inbound')
            body_anon = _Resp(); probe.on_post_traffic_inbound_body(
                _ApiReq(None, {'name': web, 'decision': 'confirmed'}), body_anon)
            body_403 = _Resp(); probe.on_post_traffic_inbound_body(
                _ApiReq(plain, {'name': web, 'decision': 'confirmed'}), body_403)
            body_400 = _Resp(); probe.on_post_traffic_inbound_body(
                _ApiReq(admin, {'decision': 'confirmed'}), body_400)
            body_ok = _Resp(); probe.on_post_traffic_inbound_body(
                _ApiReq(admin, {'name': web, 'decision': 'confirmed'}), body_ok)
            out_body = _Resp(); probe.manager = m
            probe.on_post_traffic_outbound_body(
                _ApiReq(admin, {'name': 'odoo|main|json-rpc', 'decision': 'denied'}), out_body)
            probe.manager = mi
            check('ct-9 §66a (found by the live proof on polari-lean): an inbound row is named '
                  '`origin|https://host`, and falcon percent-DECODES before routing, so no encoding can carry '
                  '`://` through the /{name} door — it 404s. The BODY door rules on exactly that name, with '
                  'every refusal unchanged: 401 anonymous, 403 for a non-admin, 400 with no name at all',
                  '://' in web and routed_path is None and routed_body is not None
                  and body_anon.status.startswith('401') and body_403.status.startswith('403')
                  and body_400.status.startswith('400') and body_ok.media['ok']
                  and body_ok.media['policy']['name'] == web
                  and body_ok.media['policy']['state'] == 'confirmed'
                  and body_ok.media['policy']['confirmed_by'] == SUB
                  and out_body.media['ok'] and out_body.media['policy']['state'] == 'denied',
                  (routed_path, body_anon.status, body_403.status, body_400.status))

            # ---- §66a: the sends that happen BEFORE the manager exists (live: outbound rows were empty)
            TR._PENDING.clear()
            mb = _M()
            boot = OB.send('keycloak', 'Polari', 'rest', lambda: 'jwks', manager=None)
            OB.send('keycloak', 'Polari', 'rest', lambda: 'jwks', payload_classes=('Token',), manager=None)
            parked = dict(TR._PENDING)
            flushed = TR.policies(mb)['outbound']
            check('ct-9 §66a: a send before `process_manager()` answers (boot: polariServer injects the manager '
                  'at :780, and the EARLIEST sends — Keycloak, JWKS — run before that) is PARKED, counted, and '
                  'becomes a row at the first verdict or door read with a real tree; it is allowed meanwhile, '
                  'because a guard with nowhere to write must not block a boot',
                  boot == 'jwks' and list(parked) == [('outbound', 'keycloak|Polari|rest')]
                  and TR._PENDING == {} and len(flushed) == 1 and flushed[0]['count'] == 2
                  and json.loads(flushed[0]['payload_classes_json']) == ['Token']
                  and flushed[0]['state'] == 'suggested' and '§66a' in flushed[0]['derived_from'],
                  (parked, flushed))
            os.environ['POLARI_POSTURE'] = 'production'
            OB.send('keycloak', 'Polari', 'rest', lambda: 'jwks', manager=None)
            prod_flush = TR.policies(_M())['outbound']
            os.environ['POLARI_POSTURE'] = 'dev'
            check('ct-9 §66a: in PRODUCTION the parked sends are DROPPED, never written — the buffer is cleared '
                  'either way so it cannot grow across a long run, and production still derives nothing',
                  prod_flush == [] and TR._PENDING == {}, (prod_flush, TR._PENDING))

            # ---- §66b: THE RESTORE RACE. Found live on polari-lean: a CONFIRMED InboundPolicy row came
            # back `suggested` after a redeploy, while SecurityDecision and TraceTarget rows survived the same
            # one. Cause: lazy boot serves requests while the tree is restoring, and
            # `_restoreDefinitionInstances` SKIPS a class that already has instances — so the first request of
            # a boot created row 1 and restore then discarded everything InboundPolicy had persisted.
            TR._PENDING.clear()
            booting = _M()
            booting.definitionsRestored = False          # exactly what polariServer sets in its constructor
            boot_mw = TM.TrafficPolicyMiddleware(_types.SimpleNamespace(manager=booting))
            os.environ['POLARI_APP_PERMISSIONS'] = 'enforce'
            boot_req = _Req({'Origin': 'https://app.example'})
            boot_mw.process_request(boot_req, _Resp())    # a request served DURING lazy boot
            during = TR._rows(booting, 'inbound')
            parked_in = dict(TR._PENDING)
            # restore now lands the persisted row, the way it would have if nothing had raced it
            from security.objects.security.InboundPolicy import InboundPolicy as _IP
            from security.custom.security_observe import _new_row as _nr2
            _nr2(booting, booting.objectTables, 'InboundPolicy', _IP,
                 {'name': 'origin|https://app.example', 'source_kind': 'origin',
                  'source': 'https://app.example', 'paths_json': '[]', 'state': 'confirmed',
                  'derived_from': 'restored', 'confirmed_by': SUB, 'confirmed_at': '2026-09-19T00:00:00Z',
                  'count': 50, 'first_seen': '', 'last_seen': ''})
            booting.definitionsRestored = True
            after_req = _Req({'Origin': 'https://app.example'})
            boot_mw.process_request(after_req, _Resp())   # the first request AFTER restore
            restored = {r['name']: r for r in TR._rows(booting, 'inbound')}
            kept = restored['origin|https://app.example']
            check('ct-9 §66b (found live on polari-lean: a confirmed row came back `suggested` after a '
                  'redeploy): a request served DURING lazy boot writes NOTHING — restore skips a class that '
                  'already has instances, so writing early would discard everything that class had persisted, '
                  'a person\'s ruling included. The observation is parked, the caller is let in, and once the '
                  'tree is restored the parked count lands ON the restored row instead of replacing it',
                  during == [] and list(parked_in) == [('inbound', 'origin|https://app.example')]
                  and boot_req.context.traffic['rule'] == 'no-security'
                  and boot_req.context.traffic['allowed'] is True
                  and kept['state'] == 'confirmed' and kept['confirmed_by'] == SUB
                  and kept['count'] == 52 and TR._PENDING == {},
                  (during, list(parked_in), kept.get('state'), kept.get('count')))
            check('ct-9 §66b: `tree_ready` is False ONLY for a manager that says so — a manager with no '
                  '`definitionsRestored` attribute at all (a test double, a module holding its own) is ready '
                  'by definition, so nothing outside a polariServer boot is ever parked forever',
                  TR.tree_ready(_M()) is True and TR.tree_ready(booting) is True
                  and TR.tree_ready(_types.SimpleNamespace(objectTables={}, definitionsRestored=False)) is False
                  and TR.tree_ready(None) is False)

            # ---- §66d: ONE ROW PER NAME. Found live after a restart: `anonymous|anonymous` existed TWICE,
            # ('confirmed', 14) beside ('suggested', 7) — the boot-time flush found no restored row YET (the
            # class's own restore had not run) and made its own. The readiness flag cannot be trusted to be
            # per-class, so the name is enforced as the key at every lookup and every read instead.
            TR._PENDING.clear()
            mr = _M()
            mr.definitionsRestored = False
            heal_mw = TM.TrafficPolicyMiddleware(_types.SimpleNamespace(manager=mr))
            for _ in range(7):
                heal_mw.process_request(_Req({}, path='/api/health'), _Resp())   # boot-time: 7 parked
            # the class's OWN restore lands afterwards — the order the live stack hit
            mr.definitionsRestored = True
            _nr2(mr, mr.objectTables, 'InboundPolicy', _IP,
                 {'name': 'anonymous|anonymous', 'source_kind': 'anonymous', 'source': 'anonymous',
                  'paths_json': '[]', 'state': 'confirmed', 'derived_from': 'restored',
                  'confirmed_by': SUB, 'confirmed_at': '2026-09-19T00:00:00Z', 'count': 14,
                  'first_seen': '2026-09-18T00:00:00Z', 'last_seen': ''})
            healed = TR.policies(mr)['inbound']
            check('ct-9 §66d (found live after a restart: two rows named `anonymous|anonymous`, confirmed 14 '
                  'beside suggested 7): after a restore that lands AFTER the flush there is exactly ONE row per '
                  'name — the person\'s ruling wins, the parked counts are SUMMED onto it (14 + 7 = 21), and '
                  'the confirmer is untouched',
                  len(healed) == 1 and healed[0]['name'] == 'anonymous|anonymous'
                  and healed[0]['state'] == 'confirmed' and healed[0]['count'] == 21
                  and healed[0]['confirmed_by'] == SUB
                  and len(_TRrows(mr, 'InboundPolicy')) == 1, healed)

            # an instance that ALREADY has duplicates heals on the next read, whichever order they are in
            md = _M()
            for state, cnt, first in (('suggested', 7, '2026-09-19T00:00:00Z'),
                                      ('confirmed', 14, '2026-09-18T00:00:00Z'),
                                      ('suggested', 3, '2026-09-20T00:00:00Z')):
                md.objectTables['InboundPolicy']['id-%s-%d' % (state, cnt)] = _types.SimpleNamespace(
                    name='anonymous|anonymous', source_kind='anonymous', source='anonymous',
                    paths_json='["GET /api/%s/{id}"]' % state, state=state, derived_from='x',
                    confirmed_by=SUB if state == 'confirmed' else '',
                    confirmed_at='2026-09-19T00:00:00Z' if state == 'confirmed' else '',
                    count=cnt, first_seen=first, last_seen=first)
            removed = TR.heal_duplicates(md, 'inbound')
            one = TR.policies(md)['inbound']
            check('ct-9 §66d: an instance that ALREADY carries duplicates heals itself on the next door read — '
                  'no migration: the confirmed row survives, the counts are summed, the paths are unioned, the '
                  'first_seen is the oldest, and the extra rows are deleted from the tree',
                  removed == 2 and len(one) == 1 and one[0]['state'] == 'confirmed'
                  and one[0]['count'] == 24 and one[0]['first_seen'] == '2026-09-18T00:00:00Z'
                  and len(json.loads(one[0]['paths_json'])) == 2
                  and len(_TRrows(md, 'InboundPolicy')) == 1
                  and TR.heal_duplicates(md, 'inbound') == 0, (removed, one))

            # ---- §66c: kc_admin is through the seam, so the Keycloak calls that REALLY happen are governed
            import security.custom.kc_admin as _KCA
            import inspect as _inspect
            src = _inspect.getsource(_KCA._http)
            check('ct-9 §66c: `kc_admin._http` goes through the ONE outbound seam — it was the last straggler '
                  'of design §5, and it is what a live instance actually calls Keycloak WITH (resolving a sub '
                  'to a name, claiming a role), so unwrapped it left OutboundPolicy empty while Keycloak '
                  'traffic flowed',
                  'outbound.urlopen(' in src and 'urllib.request.urlopen(' not in src, src[-200:])

            # ---- the CORS expose list (a browser cannot READ a header that is not exposed — §51)
            from polariApiServer.polariServer import CORSExtraHeadersMiddleware
            cors = _Resp()
            CORSExtraHeadersMiddleware().process_response(None, cors, None, True)
            exposed = [h.strip() for h in cors.h.get('Access-Control-Expose-Headers', '').split(',')]
            check('ct-9: the traffic advisory header is on the CORS EXPOSE list — a browser cannot read a '
                  'response header cross-origin unless it is exposed, so an advisory nobody can read is no '
                  'advisory at all (§51, the same reason the permission and owner advisories are there)',
                  TM.TRAFFIC_ADVISORY_HEADER in exposed, exposed)
        finally:
            TM.drain_advisories()
            os.environ.clear(); os.environ.update(old_env)


def _ct2_checks(_types, check):
    """ct-2 — THE REMAINING EVENT EDGES (design §3): emit, nested solution → solution, ws-publish, shared-db,
    bundle-export / bundle-install. Every hook is proven twice: it records under a TRACED chain, and records
    NOTHING under a chain that never touched the armed class (the scope rule holds at every new seam too)."""
    import os
    import tempfile
    from accessControl import cause_context as CC
    from security.custom import security_trace as T

    SUB = 'cccccccc-2222-4222-8222-cccccccccccc'
    admin = {'sub': SUB, 'roles': ['polari-admin'], 'raw_claims': {'groups': []}}
    old_env = dict(os.environ)
    with tempfile.TemporaryDirectory() as td:
        try:
            _trace_env(td)
            T._STATE.update({'armed': False, 'name': '', 'class_name': '', 'resumed': False,
                             'stopped_name': '', 'stopped_until': 0.0})
            T._TRACED.clear(); T._CREATED.clear()

            from polariNoCode.event_dispatcher import _trace_emits
            from polariNoCode.SolutionExecutionEngine import _trace_nested_solution
            from grpcbridge.custom.transport_mux import _trace_publish
            from polariRefs.remote_hydration import _trace_shared_db
            from polariPeers.module_exporter import trace_bundle

            def _all_five(manager, class_name, endpoint):
                tok = CC.root_cause('api', endpoint, actor=SUB)
                try:
                    T.touch(manager, class_name, 'update')
                    _trace_emits(manager, _types.SimpleNamespace(solution_name='tally-votes'),
                                 [{'name': 'tallied', 'channel': 'backend'}, 'not-a-dict', {'name': ''}])
                    _trace_nested_solution(manager, 'tally-votes', 'notify-voters', 'definer')
                    _trace_publish(manager, class_name, '/topic/%s' % class_name, {'operation': 'update'})
                    _trace_shared_db(manager, class_name, 'kitchen-node')
                    trace_bundle(manager, 'bundle-export', 'votes', {class_name: 'f1', 'Tally': 'f2'})
                    trace_bundle(manager, 'bundle-install', 'kitchen-node', {class_name: 'f1'})
                finally:
                    CC.pop_cause(tok)

            m = _TraceM()
            T.arm(m, 'Ballot', user_info=admin)
            _all_five(m, 'Ballot', 'PUT /api/Ballot/{id}')
            rows = {e['name']: e for e in T.edges(m)}
            check('ct-2: the five remaining seams each record their edge under a traced chain — `emit` from a '
                  'solution\'s emitted events, `solution-run` for a NESTED solution with the authority it runs '
                  'with, `ws-publish` for the change broadcast (count only, no ids), `shared-db` for a peer '
                  'hydration and `bundle-export` / `bundle-install` for a module bundle, each carrying the '
                  'CLASSES it moved in `detail` and never a row',
                  rows.get('solution:tally-votes|event:tallied|emit', {}).get('count') == 1
                  and rows['solution:tally-votes|solution:notify-voters|solution-run']['run_as'] == 'definer'
                  and 'object:Ballot:update|event:topic:Ballot|ws-publish' in rows
                  and rows['endpoint:PUT /api/Ballot/{id}|peer:kitchen-node:shared-db|shared-db']['detail'] == 'Ballot'
                  and rows['endpoint:PUT /api/Ballot/{id}|peer:votes:bundle-export|bundle-export']['detail'] == 'Ballot,Tally'
                  and rows['endpoint:PUT /api/Ballot/{id}|peer:kitchen-node:bundle-install|bundle-install']['detail'] == 'Ballot'
                  and len(rows) == 6, sorted(rows))
            T.disarm(m, 'manual')

            m2 = _TraceM()
            T.arm(m2, 'Ballot', user_info=admin)
            _all_five(m2, 'Recipe', 'PUT /api/Recipe/{id}')
            check('ct-2 THE SCOPE RULE AT THE NEW SEAMS: the same five hooks on a chain that never touches the '
                  'armed class write NOTHING — an emit, a nested run, a broadcast, a peer read and a bundle are '
                  'all silent unless the chain reached the ONE class being traced',
                  T.edges(m2) == [] and T.status(m2)['target']['traces_opened'] == 0, len(T.edges(m2)))
            T.disarm(m2, 'manual')

            # ---- design §5: the ANONYMISED broadcast drops the instance ids
            import grpcbridge.custom.transport_mux as TM
            from security.objects.security.OwnedClassPolicy import OwnedClassPolicy as _OCP
            from security.custom.security_observe import _new_row as _nr
            m3 = _TraceM()
            _nr(m3, m3.objectTables, 'OwnedClassPolicy', _OCP,
                {'name': 'Ballot', 'class_name': 'Ballot', 'enabled': True, 'anonymised': True})
            fmt = _types.SimpleNamespace(polariTreeWsEnabled=True, flatJsonWsEnabled=False,
                                         d3ColumnWsEnabled=False, geoJsonWsEnabled=False)
            m3.objectTypingDict = {'Ballot': _types.SimpleNamespace(apiFormatConfig=fmt),
                                   'Recipe': _types.SimpleNamespace(apiFormatConfig=fmt)}
            sent = []
            real_publish = TM.publish_change
            TM.publish_change = lambda manager, class_name, topic, notification: sent.append(
                (class_name, topic, dict(notification)))
            try:
                TM.publish_crude_change(m3, 'Ballot', 'update', ['b-1', 'b-2'])
                TM.publish_crude_change(m3, 'Recipe', 'update', ['r-1'])
            finally:
                TM.publish_change = real_publish
            anon = [n for c, _t, n in sent if c == 'Ballot'][0]
            plain = [n for c, _t, n in sent if c == 'Recipe'][0]
            check('ct-2 (design §5): the CHANGE BROADCAST of a class whose OwnedClassPolicy is ANONYMISED drops '
                  'its `instanceIds` — subscription to /topic/<Class> is unauthenticated until ct-6, so a '
                  'deliberately unlinkable class must not announce exactly which rows a person just wrote; the '
                  'class and the operation stay, which is all a subscriber needs to know it should re-read, and '
                  'an ordinary class is untouched',
                  anon['instanceIds'] == [] and anon['className'] == 'Ballot' and anon['operation'] == 'update'
                  and plain['instanceIds'] == ['r-1'], (anon, plain))
        finally:
            T._STATE.update({'armed': False, 'name': '', 'class_name': '', 'resumed': True,
                             'stopped_name': '', 'stopped_until': 0.0})
            T._set_armed_flag(False, '')
            os.environ.clear(); os.environ.update(old_env)


def _closure_checks(api, O, _Res, _types, check):
    """ct-4 — THE CLOSURE (design §6): the walk, the three start sets, the review/verify integration and the
    door. Nothing here enforces or widens: a closure is DISCLOSURE, and the person's confirmation is ct-8's."""
    import os
    import tempfile
    from accessControl import cause_context as CC
    from security.custom import security_closure as C
    from security.custom import security_trace as T

    class _Req:
        def __init__(self, ui=None, **params):
            self.params = params
            self.media = {}
            self.context = _types.SimpleNamespace(user_info=ui, roleplay='')

    SUB = 'eeeeeeee-5555-4555-8555-eeeeeeeeeeee'
    admin = {'sub': SUB, 'roles': ['polari-admin'], 'raw_claims': {'groups': []}}
    journalist = {'sub': SUB, 'roles': ['journalist'], 'raw_claims': {'groups': ['journalist']}}
    old_env = dict(os.environ)
    with tempfile.TemporaryDirectory() as td:
        try:
            _trace_env(td)
            T._STATE.update({'armed': False, 'name': '', 'class_name': '', 'resumed': False,
                             'stopped_name': '', 'stopped_until': 0.0})
            T._TRACED.clear(); T._CREATED.clear()
            m = _TraceM()
            T.arm(m, 'Ballot', user_info=admin)
            tok = CC.root_cause('api', 'PUT /api/Ballot/{id}', actor=SUB)
            try:
                T.touch(m, 'Ballot', 'update')
                T.record_edge(m, 'endpoint:PUT /api/Ballot/{id}', 'object:Ballot:update', 'crude')
                T.record_edge(m, 'object:Ballot:update', 'event:trigger:tally', 'trigger-fire')
                T.record_edge(m, 'event:trigger:tally', 'solution:tally-votes', 'solution-run', run_as='definer')
                T.record_edge(m, 'solution:tally-votes', 'object:Tally:update', 'crude')
                T.record_edge(m, 'solution:tally-votes', 'event:tallied', 'emit')
                T.record_edge(m, 'object:Ballot:update', 'event:topic:Ballot', 'ws-publish')
                T.record_edge(m, 'solution:tally-votes', 'peer:kitchen-node:shared-db', 'shared-db',
                              detail='Tally')
                T.record_edge(m, 'object:Tally:update', 'object:Ballot:update', 'crude')     # the cycle
            finally:
                CC.pop_cause(tok)
            walk = C.closure(m, ['object:Ballot:update'])
            objects = {o['node']: o for o in walk['objects']}
            shallow = C.closure(m, ['object:Ballot:update'], max_depth=1)
            check('ct-4 THE WALK: the closure follows cause → effect TRANSITIVELY (an update reaches the trigger, '
                  'its solution and everything that solution writes), is CYCLE-SAFE (a write that loops back to '
                  'the start terminates), respects `max_depth` in hops, and marks a node `definer_only` when '
                  'EVERY path that reaches it crossed a trigger running as definer',
                  set(objects) == {'object:Ballot:update', 'object:Tally:update'}
                  and objects['object:Ballot:update']['origin'] == 'observed'
                  and objects['object:Tally:update']['origin'] == 'closure'
                  and objects['object:Tally:update']['definer_only'] is True
                  and objects['object:Ballot:update']['definer_only'] is False
                  and walk['solutions'][0]['run_as'] == 'definer'
                  and walk['peers'][0]['classes'] == 'Tally'
                  and walk['truncated'] is False and len(walk['edges']) == 7
                  and [e['event'] for e in shallow['events']] == ['topic:Ballot', 'trigger:tally'],
                  (sorted(objects), walk['counts']))
            check('ct-4 COVERAGE, NOT SILENCE: a class the closure reaches that has never been armed as a '
                  'TraceTarget is named in `not_traced` — the answer for it is NOT TRACED, never "nothing '
                  'reaches it"; the armed class is not in the list',
                  walk['not_traced'] == ['Tally'] and 'NOT TRACED' in C.reading(walk, 'x')
                  and [c['class_name'] for c in walk['coverage']] == ['Ballot'], walk['not_traced'])

            # ---- ?profile= : implicit = reachable − explicit
            m.objectTables['AppPermissionProfile']['p1'] = _types.SimpleNamespace(
                name='ballots', app_name='', published=True, kc_groups_json='["journalist"]',
                verbs_json='["read", "update"]', extra_classes_json='["Ballot"]')
            api.manager = m
            r = _Res(); api.on_get_observe_closure(_Req(admin, profile='ballots'), r)
            implicit = {(i['class'], i['verb']) for i in r.media['implicit']}
            check('ct-4 ?profile=: the start is the profile\'s EXPLICIT class × verb grants (origin `declared`) '
                  'and `implicit` = reachable − explicit — what publishing that profile is REALLY granting. '
                  'Here an update on Ballot silently reaches Tally:update through a definer-run trigger',
                  r.media['ok'] and {(e['class'], e['verb']) for e in r.media['explicit']}
                  == {('Ballot', 'read'), ('Ballot', 'update')}
                  and implicit == {('Tally', 'update')}
                  and r.media['implicit'][0]['definer_only'] is True
                  and {o['origin'] for o in r.media['closure']['objects'] if o['class'] == 'Ballot'} == {'declared'}
                  and 'Tally' in r.media['reading'] and r.media['closure']['not_traced'] == ['Tally'],
                  (sorted(implicit), r.media.get('reading')))
            r = _Res(); api.on_get_observe_closure(_Req(admin, profile='nope'), r)
            check('ct-4: a profile that is not on this instance is an honest 404 that names the ones that are',
                  r.status.startswith('404') and 'ballots' in r.media['refusal'], r.media.get('refusal'))

            # ---- ?event= : the solution it runs and AS WHOM
            r = _Res(); api.on_get_observe_closure(_Req(admin, event='tally'), r)
            check('ct-4 ?event=: what an event permission MEANS — the start is the event node, and the answer '
                  'names the solution the trigger runs, the authority it runs with (definer: somebody else\'s), '
                  'and every class × verb that follows',
                  r.media['ok'] and r.media['start'] == 'event:trigger:tally'
                  and r.media['solutions'] == [{'name': 'tally-votes', 'run_as': 'definer', 'origin': 'closure',
                                                'definer_only': True, 'count': 1}]
                  and {(o['class'], o['verb']) for o in r.media['closure']['objects']}
                  == {('Tally', 'update'), ('Ballot', 'update')}
                  and 'DEFINER' in r.media['reading'], r.media.get('solutions'))

            # ---- the review and the verify
            O.observe_permission(m, journalist, 'Ballot', 'update', roleplay='journalist')
            rev = O.review(m, 'journalist')
            ver = O.verify(m, 'journalist', 'journalist')
            check('ct-4: `review(role)` gains a CLOSURE block started from what the role was OBSERVED doing, so '
                  'the permissions admin sees the transitive effects beside the direct list — and it never '
                  'raises: a role with no map still reviews',
                  rev['ok'] and rev['closure']['counts']['objects'] == 2
                  and [s['name'] for s in rev['closure']['solutions']] == ['tally-votes']
                  and rev['closure']['not_traced'] == ['Tally']
                  and O.review(_TraceM(), 'nobody')['closure']['counts']['objects'] == 0,
                  rev['closure']['counts'])
            check('ct-4: `verify(role, group)` gains the TRANSITIVE verdict — N of M transitively-touched class '
                  '× verb pairs covered, K reached only through triggers running as definer, and the classes '
                  'that have never been traced named rather than passed over in silence. The published '
                  '`ballots` profile covers the DIRECT act and not the one its trigger reaches — which is '
                  'exactly the gap the transitive verdict exists to show',
                  ver['ok'] and ver['transitive']['total'] == 2 and ver['transitive']['covered'] == 1
                  and ver['transitive']['definer_only'] == 1
                  and ver['transitive']['not_traced'] == ['Tally']
                  and 'covers 1 of 2' in ver['transitive']['reading']
                  and 'definer' in ver['transitive']['reading']
                  and {(u['class'], u['verb']) for u in ver['transitive']['uncovered']}
                  == {('Tally', 'update')}, ver.get('transitive'))

            # ---- ?role=, the page's default (the armed class), and the refusals
            r = _Res(); api.on_get_observe_closure(_Req(admin, role='journalist'), r)
            rd = _Res(); api.on_get_observe_closure(_Req(admin), rd)
            rc = _Res(); api.on_get_observe_closure(_Req(admin, **{'class': 'Tally'}), rc)
            ra = _Res(); api.on_get_observe_closure(_Req(None), ra)
            rb = _Res(); api.on_get_observe_closure(_Req(admin, max_depth='soon'), rb)
            check('ct-4 the door: ?role= answers the role closure; NO parameter falls back to the ONE armed '
                  'class (what the page asks for) and hands the panels `objects`, `solutions`, `events`, '
                  '`flows` and `not_traced_detail`; ?class= reads any class, armed or not; an anonymous caller '
                  'is 401 and a non-numeric max_depth is a 400 that says what it wants. A start node the map has '
                  'never recorded still appears, with `seen` false — "no edges yet" is an answer, not a gap',
                  r.media['ok'] and r.media['asked'] == {'role': 'journalist'}
                  and rd.media['ok'] and rd.media['armed'] == 'Ballot'
                  and {o['node'] for o in rd.media['objects']}
                  == {'object:Ballot:%s' % v for v in ('read', 'create', 'update', 'delete', 'events')}
                  | {'object:Tally:update'}
                  and [o['evidence']['seen'] for o in rd.media['objects'] if o['node'] == 'object:Ballot:read']
                  == [False]
                  and [f['peer'] for f in rd.media['flows']] == ['kitchen-node']
                  and rd.media['not_traced_detail'][0]['class_name'] == 'Tally'
                  and rc.media['ok'] and rc.media['armed'] == 'Tally'
                  and ra.status.startswith('401') and rb.status.startswith('400'),
                  (rd.media.get('armed'), [o['node'] for o in rd.media.get('objects', [])]))
            T.disarm(m, 'manual')
            rn = _Res(); api.manager = _TraceM(); api.on_get_observe_closure(_Req(admin), rn)
            check('ct-4: with nothing armed and nothing asked for, the door says how to ask instead of '
                  'pretending an empty closure is an answer',
                  rn.media['ok'] and rn.media['closure'] is None and 'Arm one class' in rn.media['reading'],
                  rn.media.get('reading'))

            # ---- §54 guard: the new suffix registers against a fake falconServer
            class _Falcon:
                def __init__(self): self.routes = []
                def add_route(self, uri, resource, suffix=None): self.routes.append((uri, suffix))

            class _Srv:
                def __init__(self): self.falconServer = _Falcon()
            srv = _Srv()
            from security.security_api import SecurityAPI as _API
            probe = _API(polServer=srv, manager=None)
            closure_routes = [(u, s) for u, s in srv.falconServer.routes if u.endswith('/observe/closure')]
            check('§54 guard: the ct-4 closure door registers and has its on_get_<suffix> responder — a suffix '
                  'that has drifted from its method name RAISES from add_route() and takes the backend down at '
                  'boot, so it is proven here rather than in a browser',
                  closure_routes == [('/api/security/observe/closure', 'observe_closure')]
                  and hasattr(probe, 'on_get_observe_closure'), closure_routes)
        finally:
            T._STATE.update({'armed': False, 'name': '', 'class_name': '', 'resumed': True,
                             'stopped_name': '', 'stopped_until': 0.0})
            T._set_armed_flag(False, '')
            os.environ.clear(); os.environ.update(old_env)


def _ct5_checks(api, _Res, _types, check):
    """ct-5 — THE `objects` TOPOLOGY VIEW (design §7): the fourth view, the only one with a PAYLOAD column.

    Everything runs against the same manager double the ct-4 checks use, with dev posture and a temporary knob,
    so the declared half (manifest `app.flows` + confirmed traffic policy rows) and the observed half (the causal
    map) are both exercised through their real readers."""
    import json
    import os
    import tempfile

    from accessControl import cause_context as CC
    from security.custom import security_objects_view as OV
    from security.custom import security_topology as TP
    from security.custom import security_trace as T

    class _Req:
        def __init__(self, ui=None, **params):
            self.params = params
            self.media = {}
            self.context = _types.SimpleNamespace(user_info=ui, roleplay='')

    SUB = 'cccccccc-5555-4555-8555-cccccccccccc'
    admin = {'sub': SUB, 'roles': ['polari-admin'], 'raw_claims': {'groups': []}}
    old_env = dict(os.environ)
    with tempfile.TemporaryDirectory() as td:
        try:
            _trace_env(td)
            T._STATE.update({'armed': False, 'name': '', 'class_name': '', 'resumed': False,
                             'stopped_name': '', 'stopped_until': 0.0})
            T._TRACED.clear(); T._CREATED.clear()

            # ---- the view is the FOURTH one, and it is deliberately not in the seeded three
            from security.security_basis import SecurityTopologyEdge
            built = {m: TP.build('objects', 'dev', m) for m in TP.MODES}
            check('ct-5: `objects` is a FOURTH security topology view — accepted by the doors (`ALL_VIEWS`), '
                  'built for every mode, and deliberately NOT in `VIEWS`, which is what the seed walks: this '
                  'view is derived from the INSTANCE (its manifests, its confirmed policies, its causal map), so '
                  'seeding it once per scenario would be four copies of one answer taken from an empty tree. '
                  'The one schema change is `SecurityTopologyEdge.payload` — what crosses, which no other view '
                  'can say',
                  TP.OBJECT_VIEW == 'objects' and 'objects' not in TP.VIEWS
                  and TP.ALL_VIEWS == TP.VIEWS + ('objects',)
                  and all(b['view'] == 'objects' and b['payload_column'] for b in built.values())
                  and SecurityTopologyEdge(name='x').payload == ''
                  and hasattr(SecurityTopologyEdge(name='x', payload='MealEntry×3'), 'payload'),
                  (TP.ALL_VIEWS, sorted(built)))

            # ---- DECLARED half A: the modules' manifest app.flows (ct-7's stanza, read here)
            flows = OV.manifest_flows()
            by_module = {f['module']: f for f in flows}
            check('ct-5 DECLARED (the app author): every module manifest\'s `app.flows` stanza is read as a '
                  'declared flow — a system KIND and a direction, never a host. `security` declares it talks to '
                  'Keycloak carrying NO Polari rows (names live in Keycloak and stay there, D18-1) and '
                  '`odooconnect` declares the Odoo wire',
                  {'security', 'odooconnect'} <= set(by_module)
                  and by_module['security']['kind'] == 'keycloak'
                  and by_module['security']['classes'] == []
                  and by_module['odooconnect']['kind'] == 'odoo'
                  and all('://' not in (f.get('name') or '') for f in flows)
                  and all(f['provenance'] == 'declared' and f['origin'] == 'app.flows' for f in flows),
                  sorted(by_module))

            # ---- DECLARED half B: the CONFIRMED traffic policy rows (ct-9's declared_flows, which waited for this)
            m = _TraceM()
            m.objectTables['OutboundPolicy']['o1'] = _types.SimpleNamespace(
                name='odoo|main|json-rpc', system_kind='odoo', system_name='main', means='json-rpc',
                payload_classes_json='["MealEntry"]', state='confirmed', derived_from='observed send',
                confirmed_by=SUB, confirmed_at='2026-09-19T00:00:00Z', count=7,
                first_seen='2026-09-19T00:00:00Z', last_seen='2026-09-19T00:00:00Z')
            m.objectTables['OutboundPolicy']['o2'] = _types.SimpleNamespace(
                name='s3|appstore|s3', system_kind='s3', system_name='appstore', means='s3',
                payload_classes_json='["Artifact"]', state='suggested', derived_from='observed send',
                confirmed_by='', confirmed_at='', count=2,
                first_seen='2026-09-19T00:00:00Z', last_seen='2026-09-19T00:00:00Z')
            policy = OV.policy_flows(m)
            check('ct-5 DECLARED (the deployment): a traffic policy row a PERSON confirmed becomes a declared '
                  'flow with its payload classes; a `suggested` row does NOT — a proposal nobody ruled on is '
                  'never a declaration (design §5a, closed by default)',
                  [(p['kind'], p['name'], p['classes']) for p in policy] == [('odoo', 'main', ['MealEntry'])],
                  [(p['kind'], p['name']) for p in policy])

            # ---- OBSERVED half: the causal map's peer / external / broadcast edges, and nothing else
            T.arm(m, 'MealEntry', user_info=admin)
            tok = CC.root_cause('api', 'PUT /api/MealEntry/{id}', actor=SUB)
            try:
                T.touch(m, 'MealEntry', 'update')
                T.record_edge(m, 'endpoint:PUT /api/MealEntry/{id}', 'object:MealEntry:update', 'crude')
                T.record_outbound(m, 'odoo', 'main', 'json-rpc', ['MealEntry'])
                T.record_outbound(m, 'peer', 'kitchen-node', 'shared-db', ['MealEntry'])
                T.record_outbound(m, 's3', 'appstore', 's3', ['Artifact'])
                T.record_edge(m, 'object:MealEntry:update', 'event:topic:MealEntry', 'ws-publish')
            finally:
                CC.pop_cause(tok)
            obs = OV.observed(m)
            seen = {(o['kind'], o['name'], o['means'], tuple(o['classes'])) for o in obs}
            check('ct-5 OBSERVED: the causal map\'s `external:` / `peer:` edges and the two `ws-*` means become '
                  'flows whose PAYLOAD is the classes the wrapper recorded; a `crude` edge does NOT — causation '
                  'INSIDE the instance is the closure\'s answer (ct-4) and this view deliberately does not repeat '
                  'it',
                  seen == {('odoo', 'main', 'json-rpc', ('MealEntry',)),
                           ('peer', 'kitchen-node', 'shared-db', ('MealEntry',)),
                           ('s3', 'appstore', 's3', ('Artifact',)),
                           ('broadcast', 'stomp', 'ws-publish', ('MealEntry',))}
                  and all(o['provenance'] == 'observed' for o in obs), sorted(seen))

            # ---- the MODES mean the traffic policy's ladder for this view
            edges = {m_: {(e['target'], e['payload']): e['verdict'] for e in TP.build('objects', 'dev', m_,
                                                                                      manager=m)['edges']}
                     for m_ in TP.MODES}
            odoo_key = ('external:odoo:main', 'MealEntry×1')
            s3_key = ('external:s3:appstore', 'Artifact×1')
            check('ct-5 THE MODES, for THIS view: `stock` is an instance with no traffic policy at all (every '
                  'flow leaves), `complain` is dev (a confirmed flow is allowed, everything else is LOGGED and '
                  'proceeds — warn, never block) and `enforce` is production, closed by default (only a '
                  'CONFIRMED row allows). The confirmed Odoo flow is allowed in all three; the unconfirmed S3 '
                  'one is not',
                  edges['stock'][odoo_key] == 'allowed' and edges['stock'][s3_key] == 'allowed'
                  and edges['complain'][odoo_key] == 'allowed' and edges['complain'][s3_key] == 'logged'
                  and edges['enforce'][odoo_key] == 'allowed' and edges['enforce'][s3_key] == 'blocked',
                  {k: {kk: vv for kk, vv in v.items() if kk in (odoo_key, s3_key)} for k, v in edges.items()})

            # ---- the DRIFT report
            d = OV.drift(m)
            undeclared = {(u['kind'], u['name']) for u in _drift_items(d, 'observed_not_declared')}
            unexercised = {(u['kind'], u['name']) for u in _drift_items(d, 'declared_not_observed')}
            check('ct-5 DRIFT (design §7): observed − declared names what flows with NOTHING declaring it — the '
                  'S3 send (its policy row is only `suggested`) and the peer read — as a FINDING, never a block '
                  '(dev warns, §17); declared − observed names what somebody declared and the map has never '
                  'seen. The Odoo flow is in neither: a manifest declares the kind AND a person confirmed the '
                  'row',
                  ('s3', 'appstore') in undeclared and ('peer', 'kitchen-node') in undeclared
                  and ('odoo', 'main') not in undeclared
                  and ('keycloak', 'realm') in unexercised
                  and all('FINDING' in u['finding'].upper() for u in _drift_items(d, 'observed_not_declared')),
                  (sorted(undeclared), sorted(unexercised)))
            by_app = {a['app']: a for a in d['by_app']}
            check('ct-5 COVERAGE, NOT SILENCE (design §2): the drift is grouped PER APP with the trace coverage '
                  'of the classes involved — `Artifact` has never been armed as a TraceTarget, so it is named in '
                  '`not_traced` and its app reads coverage `none`, while `MealEntry` (the armed class) does not. '
                  'An untraced class answers NOT TRACED, never "nothing flows"',
                  d['not_traced'] == ['Artifact'] and 'MealEntry' not in d['not_traced']
                  and d['not_traced_detail'][0]['class_name'] == 'Artifact'
                  and 'NOT TRACED' in d['not_traced_detail'][0]['reading']
                  and any(a['coverage'] == 'none' and 'Artifact' in a['not_traced'] for a in by_app.values())
                  and 'NEVER been traced' in d['reading'], (d['not_traced'], sorted(by_app)))

            # ---- no instance ids, no addresses, anywhere on the view (design §7's last line)
            g = TP.build('objects', 'dev', 'today', manager=m)
            blob = json.dumps({'nodes': g['nodes'], 'summary': g['summary']})
            check('ct-5 NO INSTANCE IDS: the object topology is CLASSES AND COUNTS. Nothing on it carries an '
                  'instance id, a raw address or a hostname — an instance is looked up in the effect journal, '
                  'which is dev-only and cleared on the next arm (design §7)',
                  'm-1' not in blob and '://' not in blob and '192.168' not in blob
                  and all(':' not in (e['payload'] or '') for e in g['edges'])
                  and all('×' in e['payload'] or not e['payload'] for e in g['edges']))

            # ---- simulate, incl. the per-profile reading design §7 asks for
            m.objectTables['AppPermissionProfile']['p1'] = _types.SimpleNamespace(
                name='kitchen', app_name='', published=True, kc_groups_json='["operator"]',
                verbs_json='["read", "update"]', extra_classes_json='["MealEntry"]')
            s_all = TP.simulate('objects', 'dev', 'this instance', 'today', manager=m)
            s_cls = TP.simulate('objects', 'dev', 'class:MealEntry', 'today', manager=m)
            s_prof = TP.simulate('objects', 'dev', 'profile:kitchen', 'enforce', manager=m)
            s_bad = TP.simulate('objects', 'dev', 'nobody', 'today', manager=m)
            check('ct-5 SIMULATE: what can leave from `this instance`, from one `class:<C>`, and — the reading '
                  'design §7 asks for — from a person holding an `AppPermissionProfile`, whose classes are '
                  'expanded to their flows. An actor the view does not have is an honest refusal that lists the '
                  'ones it does',
                  s_all['ok'] and s_cls['ok'] and s_prof['ok'] and s_bad['ok'] is False
                  and {st['target'] for st in s_cls['steps']}
                  == {'external:odoo:main', 'peer:kitchen-node:shared-db', 'subscribers (STOMP)'}
                  and {st['target'] for st in s_prof['steps']} == {st['target'] for st in s_cls['steps']}
                  and 'kitchen' in s_prof['note']
                  # under ENFORCE the profile's own classes reach exactly the CONFIRMED flow; the peer read has
                  # no confirmed row and is blocked, the broadcast is the permission gate's per-subscriber call,
                  # and the S3 send belongs to a class this profile does not grant at all
                  and s_prof['reach']['allowed'] == ['external:odoo:main']
                  and s_prof['reach']['blocked'] == ['peer:kitchen-node:shared-db']
                  and 'external:s3:appstore' not in sum(s_prof['reach'].values(), [])
                  and {st['target'] for st in s_all['steps']} > {st['target'] for st in s_cls['steps']},
                  (s_cls.get('reading'), s_prof.get('note'), s_prof.get('reach')))
            check('ct-5 SIMULATE, the refusals and the honesty: an unknown actor names the ones that exist and '
                  'says a profile may be asked for; a profile nothing has published is a refusal, not an empty '
                  'answer; and a class that has never been traced is named in the answer',
                  'profile:' in s_bad['error'] and 'this instance' in s_bad['actors']
                  and TP.simulate('objects', 'dev', 'profile:nope', 'today', manager=m)['ok'] is False
                  and s_all['not_traced'] == ['Artifact'], (s_bad.get('error'), s_all.get('not_traced')))

            # ---- compare puts the MODES on the columns, and says so
            c = TP.compare('objects', 'today', manager=m)
            check('ct-5 COMPARE: the other three views compare MACHINES (a column per scenario); this one '
                  'compares POSTURES, because what may leave an instance is decided by its policies and its '
                  'manifests, not by the machine layout a scenario describes. `axis` says so rather than leaving '
                  'four identical columns to be misread',
                  c['axis'] == 'mode' and c['scenarios'] == list(TP.MODES)
                  and all(all(mm in row for mm in TP.MODES) for row in c['rows']) and c['rows'],
                  (c['axis'], len(c['rows'])))

            # ---- the doors
            api.manager = m
            r_top = _Res(); api.on_get_topology(_Req(admin, view='objects'), r_top)
            r_dr = _Res(); api.on_get_objects_drift(_Req(admin), r_dr)
            r_fl = _Res(); api.on_get_objects_flows(_Req(admin), r_fl)
            r_an = _Res(); api.on_get_objects_drift(_Req(None), r_an)
            r_sim = _Res(); api.on_get_simulate(_Req(admin, view='objects'), r_sim)
            check('ct-5 THE DOORS: `?view=objects` builds through the SAME /topology, /simulate and /compare '
                  'doors as the other three views (the manager is handed through for this one); '
                  '/api/security/objects/drift and /flows are the two readings a person acts on, and both refuse '
                  'an anonymous caller — where this instance\'s rows go is not an anonymous question',
                  r_top.media['ok'] and r_top.media['view'] == 'objects' and r_top.media['summary']
                  and r_dr.media['ok'] and r_dr.media['counts']['observed'] == 4
                  and r_fl.media['ok'] and r_fl.media['counts']['manifests'] >= 2
                  and r_an.status.startswith('401')
                  and r_sim.media['ok'] and r_sim.media['actor'] == 'this instance',
                  (r_top.media.get('view'), r_dr.media.get('counts')))

            class _Falcon:
                def __init__(self): self.routes = []
                def add_route(self, uri, resource, suffix=None): self.routes.append((uri, suffix))

            class _Srv:
                def __init__(self): self.falconServer = _Falcon()
            srv = _Srv()
            from security.security_api import SecurityAPI as _API
            probe = _API(polServer=srv, manager=None)
            obj_routes = [(u, s) for u, s in srv.falconServer.routes if '/objects/' in u]
            check('§54 guard: the two ct-5 doors register and have their on_get_<suffix> responders — a suffix '
                  'that has drifted from its method name RAISES from add_route() and takes the backend down at '
                  'boot, so it is proven here rather than in a browser',
                  obj_routes == [('/api/security/objects/drift', 'objects_drift'),
                                 ('/api/security/objects/flows', 'objects_flows')]
                  and hasattr(probe, 'on_get_objects_drift') and hasattr(probe, 'on_get_objects_flows'),
                  obj_routes)
            T.disarm(m, 'manual')
        finally:
            T._STATE.update({'armed': False, 'name': '', 'class_name': '', 'resumed': True,
                             'stopped_name': '', 'stopped_until': 0.0})
            T._set_armed_flag(False, '')
            os.environ.clear(); os.environ.update(old_env)


def _drift_items(drift_report, key):
    """One side of ct-5's drift report (`observed_not_declared` / `declared_not_observed`), defended."""
    return drift_report.get(key) or []


def _ct7_checks(api, O, _Res, _types, check):
    """ct-7 — TASKS AND NEEDS (design §8/§9): the session's task, the acts that carry it, the review grouped by
    task, the per-task verify verdict, and the `app.flows` manifest stanza with its validation."""
    import os
    import tempfile

    from moduleService import manifests as M
    from security.custom import security_tasks as TK

    class _Req:
        def __init__(self, ui=None, body=None, **params):
            self.params = params
            self.media = body or {}
            self.context = _types.SimpleNamespace(user_info=ui, roleplay='')

    # ---- app.flows: the vocabulary, the validation, and the hand-set survival
    from polariApiServer.outbound import SYSTEM_KINDS
    good = [{'to': 'odoo', 'classes': ['MealEntry'], 'direction': 'push'},
            {'to': 'peer', 'name': 'kitchen-node', 'classes': [], 'direction': 'both'}]
    check('ct-7 `app.flows` (design §9): a well-formed stanza passes, and the `to` vocabulary is exactly the '
          'outbound wrapper\'s `SYSTEM_KINDS` — a manifest that could not name a kind the wrapper records would '
          'make a real flow undeclarable, which is the one way this stanza could lie',
          M.flow_findings(None) == [] and M.flow_findings([]) == [] and M.flow_findings(good) == []
          and set(M.FLOW_TARGETS) == set(SYSTEM_KINDS)
          and M.FLOW_DIRECTIONS == ('push', 'pull', 'both'),
          (M.flow_findings(good), sorted(set(M.FLOW_TARGETS) ^ set(SYSTEM_KINDS))))
    bad = {
        'not a list': 'odoo',
        'unknown kind': [{'to': 'hadoop', 'classes': []}],
        'a URL, not a configured name': [{'to': 'odoo', 'name': 'https://odoo.example/jsonrpc', 'classes': []}],
        'a direction nobody defined': [{'to': 'odoo', 'classes': [], 'direction': 'sideways'}],
        'classes that are not class names': [{'to': 'odoo', 'classes': ['Meal Entry']}],
        'the same flow twice': [{'to': 'odoo', 'classes': ['A']}, {'to': 'odoo', 'classes': ['B']}],
        'too many classes': [{'to': 'odoo', 'classes': ['C%d' % i for i in range(M.FLOW_CLASSES_MAX + 1)]}],
    }
    results = {label: M.flow_findings(v) for label, v in bad.items()}
    check('ct-7 `app.flows` refuses, each with the reason: a bare string, a system kind nobody can record, a URL '
          'where a CONFIGURED name belongs (a URL can carry a credential), an invented direction, something that '
          'is not a class name, one flow declared twice, and more classes than a declaration may name',
          all(results.values()) and 'not one of' in results['unknown kind'][0]
          and 'URL' in results['a URL, not a configured name'][0]
          and 'twice' in results['the same flow twice'][0],
          {k: v[:1] for k, v in results.items()})
    check('ct-7: `validate()` carries the findings, so `manifests conform` reports a bad stanza; and the two '
          'manifests that DO declare a flow today (security → keycloak carrying no rows, odooconnect → odoo) are '
          'valid and survive a regeneration — `flows` is HAND-SET, like `roles` and the security stanza, because '
          'nothing can derive where an app\'s rows are MEANT to go',
          any('app.flows' in p for p in M.validate({'schema': M.SCHEMA, 'id': 'x', 'package': 'x', 'title': 'x',
                                                    'requires': [], 'files': {}, 'classes': [],
                                                    'app': {'kind': 'library', 'agentTier': 'core',
                                                            'flows': 'odoo'}}))
          and M.flow_findings((M.load('security') or {}).get('app', {}).get('flows')) == []
          and M.flow_findings((M.load('odooconnect') or {}).get('app', {}).get('flows')) == []
          and (M.load('security') or {})['app']['flows'][0]['to'] == 'keycloak')

    # ---- the session's task, and the acts that carry it
    old_env = dict(os.environ)
    with tempfile.TemporaryDirectory() as td:
        try:
            _trace_env(td)
            m = _TraceM()
            SUB = 'dddddddd-5555-4555-8555-dddddddddddd'
            journalist = {'sub': SUB, 'roles': ['journalist'], 'raw_claims': {'groups': ['journalist']}}
            s1 = O.start_session(m, 'journalist', actor=SUB, task='  publish   an article ')
            s2 = O.start_session(m, 'journalist', actor=SUB, task='score a source')
            sess = O.sessions(m, 'journalist')[0]
            check('ct-7 THE TASK (design §8): a role-play session states the task being performed, cleaned to one '
                  'line; posting to the SAME door again with a different task CHANGES it mid-session (it does not '
                  'open a second session) and the history keeps the one before, so a changed task never erases '
                  'what was done under it',
                  s1['ok'] and s1['task'] == 'publish an article' and s1['already_open'] is False
                  and s2['already_open'] is True and s2['task_changed'] is True
                  and s2['task'] == 'score a source'
                  and [t['task'] for t in sess['tasks']] == ['publish an article', 'score a source']
                  and sess['task'] == 'score a source' and sess['actor'] == SUB,
                  (s1.get('task'), s2.get('task'), sess.get('tasks')))

            # acts under task 1
            O.start_session(m, 'journalist', actor=SUB, task='publish an article')
            O.observe_permission(m, journalist, 'Article', 'update', roleplay='journalist')
            O.observe_permission(m, journalist, 'Article', 'update', roleplay='journalist')
            O.observe_usage(m, 'journalist', 'endpoint', 'PUT /api/Article/{id}', actor=SUB)
            O.observe_usage(m, 'journalist', 'page', 'article-editor', actor=SUB)
            # the SAME act under task 2 — one row, two tasks, not two rows
            O.start_session(m, 'journalist', actor=SUB, task='score a source')
            O.observe_permission(m, journalist, 'Article', 'update', roleplay='journalist')
            O.observe_permission(m, journalist, 'Source', 'read', roleplay='journalist')
            O.observe_usage(m, 'journalist', 'endpoint', 'PUT /api/Article/{id}', actor=SUB)
            # an act with NO session open at all
            O.end_session(m, role='journalist')
            O.observe_permission(m, journalist, 'Article', 'read', roleplay='journalist')
            obs = {o['name']: o for o in O.observations(m)}
            use = {u['name']: u for u in O.usages(m, 'journalist')}
            article = obs['default-roles-polari,journalist,roleplay:journalist|Article|update'] \
                if 'default-roles-polari,journalist,roleplay:journalist|Article|update' in obs else \
                next(o for k, o in obs.items() if k.endswith('|Article|update'))
            door = next(u for k, u in use.items() if k.endswith('|endpoint|PUT /api/Article/{id}'))
            check('ct-7: every act and every door recorded while a session is open carries the TASK, as a counted '
                  '{task: count} map on the SAME row — the row\'s name is still groups|class|verb and '
                  'role|kind|item, so attributing tasks never multiplies the ledger. One act performed under two '
                  'tasks is ONE row that names both, with the evidence of how often',
                  article['tasks'] == {'publish an article': 2, 'score a source': 1}
                  and article['count'] == 3
                  and door['tasks'] == {'publish an article': 1, 'score a source': 1}
                  and TK.clean_task('  a\tb  ') == 'a b' and len(TK.clean_task('x' * 400)) == TK.TASK_MAX,
                  (article['tasks'], article['count'], door['tasks']))

            # ---- the review, grouped by task
            rev = O.review(m, 'journalist')
            tasks = {t['task']: t for t in rev['tasks']}
            check('ct-7 THE REVIEW (design §8): the recording reads as TASKS → doors → objects × verbs → closure '
                  'per task, which is the shape a profile is actually worked out from. Acts recorded with NO task '
                  'stated are their own bucket, shown last and as themselves — never folded into a task that did '
                  'not do them',
                  rev['ok'] and list(tasks) == ['publish an article', 'score a source', '']
                  and tasks['publish an article']['objects'] == {'Article': {'update': 2}}
                  and tasks['score a source']['objects'] == {'Article': {'update': 1}, 'Source': {'read': 1}}
                  and tasks['']['objects'] == {'Article': {'read': 1}}
                  and [d['item'] for d in tasks['publish an article']['doors']['endpoint']]
                  == ['PUT /api/Article/{id}']
                  and 'article-editor' in [d['item'] for d in tasks['publish an article']['doors']['page']]
                  and 'NO task stated' in tasks['']['reading'],
                  (list(tasks), {k: v['objects'] for k, v in tasks.items()}))
            check('ct-7: each task carries its own CLOSURE, reusing ct-4\'s walk from that task\'s own start '
                  'nodes (its class × verb acts and the endpoints it walked through) — so "what this task really '
                  'needs" is the transitive answer, and a class nobody has armed says NOT TRACED rather than '
                  'reading as an empty need',
                  tasks['publish an article']['closure'] is not None
                  and {s['node'] for s in tasks['publish an article']['closure']['start']}
                  == {'object:Article:update', 'endpoint:PUT /api/Article/{id}'}
                  and tasks['publish an article']['closure']['not_traced'] == ['Article']
                  and 'NOT TRACED' in tasks['publish an article']['reading']
                  and 'goes on to reach' in tasks['publish an article']['reading'],
                  tasks['publish an article'].get('closure', {}) and
                  [s['node'] for s in tasks['publish an article']['closure']['start']])

            # ---- verify: which TASKS would break
            m.objectTables['AppPermissionProfile']['p1'] = _types.SimpleNamespace(
                name='journalist', app_name='', published=True, kc_groups_json='["journalist"]',
                verbs_json='["read", "update"]', extra_classes_json='["Article"]')
            ver = O.verify(m, 'journalist', 'journalist')
            vt = {t['task']: t for t in ver['tasks']}
            check('ct-7 VERIFY, the sentence a person can act on: `verify` now says which TASKS enforcement would '
                  'BREAK, not only how many verbs it would take away. The published profile covers Article but '
                  'not Source, so "score a source" breaks and "publish an article" does not',
                  ver['ok'] and vt['score a source']['breaks'] is True
                  and vt['publish an article']['breaks'] is False
                  and [d['class'] for d in vt['score a source']['denied']] == ['Source']
                  and ver['tasks_broken'] == ['score a source']
                  and 'would BREAK' in ver['tasks_verdict'],
                  (ver.get('tasks_broken'), ver.get('tasks_verdict')))

            # ---- the door, and the PII rule
            api.manager = m
            r = _Res()
            api.on_post_observe_session(_Req(journalist, body={'role': 'journalist', 'task': 'file a correction',
                                                               'actor': 'not-a-sub'}), r)
            check('ct-7 THE DOOR: `POST /api/security/observe/session {"role", "task"}` states the task, and the '
                  'session\'s actor is still the CALLER\'S OWN Keycloak `sub` — a body-supplied `actor` is '
                  'ignored exactly as before (D18-1: a person is a sub and nothing else, and a task is a job, '
                  'never a who)',
                  r.media['ok'] and r.media['task'] == 'file a correction'
                  and all(s['actor'] in (SUB, '') for s in O.sessions(m, 'journalist'))
                  and not any('not-a-sub' == s['actor'] for s in O.sessions(m, 'journalist')),
                  r.media.get('task'))
        finally:
            os.environ.clear(); os.environ.update(old_env)


def O_events(manager):
    from security.custom.security_observe import events
    return events(manager)


def main():
    from security.security_basis import SECURITY_CLASSES, SecurityTopologyEdge
    from security.security_seed import SECURITY_SEED_PAIRS, SEED_SECURITY_EDGES
    from security.security_page import SEED_SECURITY_PAGE_DISPLAYS
    from security.custom.security_topology import MODES, VIEWS, build, compare, simulate
    from security.custom.security_facts import SYSTEMS, scenario_names
    check('thirty-seven row classes (op-1 added OwnerGrant)', len(SECURITY_CLASSES) == 37, str(len(SECURITY_CLASSES)))
    check('row class constructs', SecurityTopologyEdge(name='x').name == 'x')
    n = 0
    for scn in scenario_names():
        for v in VIEWS:
            for m in MODES:
                g = build(v, scn, m); n += 1
                assert g['edges'] and g['nodes'], (v, scn, m)
    check('every view × scenario × mode builds', n == len(scenario_names()) * 3 * 4, str(n))
    stock = {(e['means'], e['verdict']) for e in build('os', 'swarm-lean', 'stock')['edges'] if e['source'] == 'prf-backend'}
    check('stock docker blocks: module load, mount, ptrace, userns', all((m, 'blocked') in stock for m in ('load a kernel module', 'mount a filesystem / pivot_root', "ptrace another container's process", 'new user namespace (unshare -r), keyctl, bpf')))
    check('stock docker ALLOWS: image write, raw socket, chroot', all((m, 'allowed') in stock for m in ('write into /usr, /etc, /bin of its own image', 'open a raw socket (sniff / forge packets)', 'chroot')))
    enf = {(e['means'], e['verdict']) for e in build('os', 'swarm-lean', 'enforce')['edges'] if e['source'] == 'prf-backend'}
    check('enforce removes them', all((m, 'blocked') in enf for m in ('write into /usr, /etc, /bin of its own image', 'open a raw socket (sniff / forge packets)', 'chroot')))
    comp = {(e['means'], e['verdict']) for e in build('os', 'isle', 'today')['edges'] if e['source'] == 'prf-isle-backend'}
    check('today on the isle LOGS the image write (the union profile is loaded there)', ('write into /usr, /etc, /bin of its own image', 'logged') in comp)
    todl = {(e['means'], e['verdict']) for e in build('os', 'swarm-lean', 'today')['edges'] if e['source'] == 'prf-backend'}
    check('today on the swarm the image write is still ALLOWED (nothing loaded there)', ('write into /usr, /etc, /bin of its own image', 'allowed') in todl)
    check('the host-bind read is DAC\'s, not AppArmor\'s', any(e['means'].startswith("read the host's") and e['decided_by'] in ('mount-policy', 'userns') for e in build('os', 'isle', 'enforce')['edges']))
    g = build('os', 'isle', 'today')
    check('a guest cannot escape (qemu layers)', any(e['source'] == 'a guest' and e['means'] == 'escape the hypervisor' and e['verdict'] == 'blocked' for e in g['edges']))
    check('swarm folds modules into the backend', any(e['source'] == 'a module' and e['target'] == 'prf-backend' for e in build('os', 'swarm-lean')['edges']))
    lean = simulate('app', 'swarm-lean', 'visitor'); full = simulate('app', 'swarm-full', 'visitor')
    check('lean: the API is open to a visitor; full: refused without a token', 'api' in lean['reach']['allowed'] and 'api' in full['reach']['blocked'])
    check('simulate names an unknown actor honestly', simulate('os', 'dev', 'nobody')['ok'] is False)
    c = compare('network')
    check('compare has a column per scenario', all(scn in c['rows'][0] for scn in scenario_names()))
    row = [x for x in compare('os')['rows'] if x['means'].startswith('write into') and x['source'] == 'the Polari backend'][0]
    check('compare lines the backend up across routes', all(row[s] != '—' for s in ('isle', 'swarm-lean', 'swarm-full')), str(row))
    check('every system has a provenance', all(s['provenance'] in ('stock', 'qemu', 'polari') for s in SYSTEMS.values()))
    check('seed pairs: 37, all rows named', len(SECURITY_SEED_PAIRS) == 37 and all(r.get('name') for _, _, rows in SECURITY_SEED_PAIRS for r in rows))
    check('edge rows unique by name', len({r['name'] for r in SEED_SECURITY_EDGES}) == len(SEED_SECURITY_EDGES), str(len(SEED_SECURITY_EDGES)))
    check('ten pages (op-1 added security-owned), none with api-json-panel', len(SEED_SECURITY_PAGE_DISPLAYS) == 10 and all('api-json-panel' not in p['definition'] for p in SEED_SECURITY_PAGE_DISPLAYS))
    # ct-5: the `objects` page is configured panels and configured tables over the doors and the rows — no new
    # component, and every component it names is one that already exists on the other security pages.
    import json as _json_pages
    _objects_page = [p for p in SEED_SECURITY_PAGE_DISPLAYS if p['name'] == 'security-objects']
    _obj_def = _json_pages.loads(_objects_page[0]['definition']) if _objects_page else {'rows': []}
    _obj_items = [it for r in _obj_def['rows'] for it in r['items']]
    _obj_components = {(it.get('componentProps') or {}).get('componentName') for it in _obj_items}
    check('ct-5: the `security-objects` page is configured structured panels + configured class tables ONLY — '
          'the same two components every other security page uses, no new one, and the drift, the coverage and '
          'the NOT-TRACED list are each their own panel rather than a JSON wall',
          bool(_objects_page) and _objects_page[0]['pageRoute'] == 'security-objects'
          and _obj_components == {'api-structured-panel', 'class-rows-table'}
          and any('objects/drift' in (it['componentProps']['inputs'].get('path') or '') for it in _obj_items)
          and any(it['componentProps']['inputs'].get('className') == 'CausalEdge' for it in _obj_items),
          sorted(_obj_components))
    # §54: every `actor` column on the security-events page is marked `person`, and the pages CONVERGE.
    import json as _json_pages
    _ev = _json_pages.loads([p for p in SEED_SECURITY_PAGE_DISPLAYS if p['name'] == 'security-events'][0]['definition'])
    _tables = [it for r in _ev['rows'] for it in r['items']
               if (it.get('componentProps') or {}).get('componentName') == 'class-rows-table']
    _actor_tables = [it for it in _tables if 'actor' in it['componentProps']['inputs']['columns'].split(',')]
    check('§54: all four security-events tables (SecurityEvent, PermissionObservation, UsageObservation, '
          'ObservationSession) carry the `actor` column marked actor:person, so the page resolves subject ids to '
          'names at render time instead of showing bare UUIDs',
          len(_actor_tables) == 4
          and all(it['componentProps']['inputs'].get('columnFormats') == 'actor:person' for it in _actor_tables),
          [(it['id'], it['componentProps']['inputs'].get('columnFormats')) for it in _actor_tables])
    # ct-1: the Trace tables on the same page — configured tables, not a JSON dump, and the target's person
    # column is keyed the same way (`started_by` holds a `sub`, D18-1).
    _trace_tables = {it['id']: it['componentProps']['inputs'] for it in _tables if it['id'].startswith('security-trace-')}
    check('ct-1: the security-events page gains the Trace tables — TraceTarget (with started_by marked person) '
          'and CausalEdge — as CONFIGURED tables, no raw JSON and no new component',
          set(_trace_tables) == {'security-trace-targets', 'security-trace-edges'}
          and _trace_tables['security-trace-targets']['className'] == 'TraceTarget'
          and _trace_tables['security-trace-targets'].get('columnFormats') == 'started_by:person'
          and _trace_tables['security-trace-edges']['className'] == 'CausalEdge'
          and 'means' in _trace_tables['security-trace-edges']['columns'],
          sorted(_trace_tables))
    # ct-4: the closure panels on the same page — STRUCTURED panels over the closure door (never api-json-panel,
    # never a new component), including the not-traced list so the page says "not traced" rather than showing
    # an empty table that reads as "nothing reaches it".
    _panels = {it['id']: it['componentProps']['inputs'] for r in _ev['rows'] for it in r['items']
               if (it.get('componentProps') or {}).get('componentName') == 'api-structured-panel'}
    _closure_panels = {k: v for k, v in _panels.items() if k.startswith('security-closure-')}
    check('ct-4: the security-events page gains the closure panels — objects, solutions, events, flows and the '
          'NOT-TRACED list — all reading /api/security/observe/closure through the structured panel, so nothing '
          'raw lands on the screen and no new component is introduced',
          set(_closure_panels) == {'security-closure-objects', 'security-closure-solutions',
                                   'security-closure-events', 'security-closure-flows',
                                   'security-closure-not-traced'}
          and all(v['path'] == '/api/security/observe/closure' for v in _closure_panels.values())
          and {v['pick'] for v in _closure_panels.values()}
          == {'objects', 'solutions', 'events', 'flows', 'not_traced_detail'},
          sorted(_closure_panels))
    from security.security_page import seed_security_pages, start_page_converge
    check('§54: the pages are CONVERGED, not inserted-by-name — the core display seed only inserts a missing page, '
          'so without this an existing instance keeps serving the old definition for ever (seen live)',
          callable(seed_security_pages) and callable(start_page_converge)
          and 'start_page_converge' in open('modules/security/security_endpoints.py').read())
    from security.custom.security_threats import threats, threat_rows
    th = {t['name']: t for t in threats('swarm-lean', 'stock')['threats']}
    check('stock: the image backdoor, raw sniff AND the socket (if mounted) get THROUGH — docker alone stops none', th['image-backdoor']['verdict'] == 'allowed' and th['raw-sniff']['verdict'] == 'allowed' and th['docker-socket']['verdict'] == 'allowed')
    check('today: the socket threat is blocked by the mount policy', {t['name']: t for t in threats('swarm-lean', 'today')['threats']}['docker-socket']['blocked_by'] == 'mount-policy')
    te = {t['name']: t for t in threats('swarm-lean', 'enforce')['threats']}
    check('enforce: both blocked, with the blocking policy named', te['image-backdoor']['verdict'] == 'blocked' and te['image-backdoor']['blocked_by'] and te['raw-sniff']['verdict'] == 'blocked')
    check('every threat carries a counterexample path that reaches the target', all(t['counter']['path'][-1]['node'] == t['counter']['target'] for t in te.values()))
    ti = {t['name']: t for t in threats('isle', 'today')['threats']}
    check('isle: guest escape and the unassigned device are present; the device counterexample is open on the isle', 'guest-escape' in ti and ti['unassigned-device']['counter']['verdict'] == 'allowed')
    check('swarm: the device counterexample has NO legitimate path', te['unassigned-device']['counter']['verdict'] == 'blocked')
    check('lean: the anonymous API threat is ALLOWED and says so; full: blocked by keycloak', th['anonymous-api']['verdict'] == 'allowed' and {t['name']: t for t in threats('swarm-full', 'today')['threats']}['anonymous-api']['blocked_by'] == 'keycloak')
    check('the animation path stops at the block', all(t['path'][t['stops_at']]['decision'] == 'blocked' for t in te.values() if t['stops_at'] is not None))
    ph = {e['means']: e for e in build('os', 'isle', 'today')['edges'] if e['source'] == 'physical access'}
    check('physical access: with encryption off the drive is readable; Secure Boot stops a tampered kernel but not a live USB',
          ph['pull the drive and read it in another machine']['verdict'] == 'allowed' and ph['replace the boot loader or kernel on the disk with a tampered one']['decided_by'] == 'secure-boot'
          and ph['boot a live USB and read the files']['verdict'] == 'allowed')
    phe = {e['means']: e for e in build('os', 'isle', 'enforce')['edges'] if e['source'] == 'physical access'}
    check('enforce on a desktop profile: encryption on → the drive and the live USB are blocked', phe['pull the drive and read it in another machine']['decided_by'] == 'disk-encryption')
    phs = {e['means']: e for e in build('os', 'swarm-lean', 'enforce')['edges'] if e['source'] == 'physical access'}
    check('enforce on a headless profile: encryption stays OFF (never on headless) → the drive is still readable', phs['pull the drive and read it in another machine']['verdict'] == 'allowed')
    tt = {t['name']: t for t in threats('isle', 'today')['threats']}
    check('the two physical threats exist with counterexamples', 'stolen-drive' in tt and 'tampered-boot' in tt and tt['stolen-drive']['counter']['path'][-1]['node'] == 'the disk')
    from security.security_seed import SEED_SECURITY_LEDGER, SEED_SECURITY_TRUST_CHANNELS, SEED_SECURITY_MAC_PROFILES, SEED_SECURITY_SERVICE_IDENTITIES
    check('ledger: one row per app per scenario; nothing blocked at conform', len(SEED_SECURITY_LEDGER) > 200 and not any(r['blocking'] == 'stanza_conforms' for r in SEED_SECURITY_LEDGER))
    check('ledger: the isle backend is blocked at mac_enforced (loaded in complain today)', next(r for r in SEED_SECURITY_LEDGER if r['name'] == 'isle:prf-isle-backend')['blocking'] == 'mac_enforced')
    check('trust channels: public Keycloak clients are asymmetric, the confidential one symmetric, no symmetric USER channel', any(c['name'].endswith('polari-frontend') and c['key_kind'] == 'asymmetric' for c in SEED_SECURITY_TRUST_CHANNELS) and any(c['name'].endswith('polari-backend') and c['key_kind'] == 'symmetric' for c in SEED_SECURITY_TRUST_CHANNELS) and not any(c['finding'] for c in SEED_SECURITY_TRUST_CHANNELS))
    check('mac profiles: the isle union is complain today, the swarm union only rendered', {(r['scenario'], r['mode']) for r in SEED_SECURITY_MAC_PROFILES if r['app'] == 'docker-default'} == {('isle', 'complain'), ('swarm-lean', 'rendered'), ('swarm-full', 'rendered')})
    check('service identities: expired internal certs are reported as such (days_left < 0)', any(r['issued'] and r['days_left'] < 0 for r in SEED_SECURITY_SERVICE_IDENTITIES))
    from security.custom.security_proposals import propose_from_groups
    pr = propose_from_groups('gears', {'profile': 'web-app', 'writable': ['/data'], 'network': ['isle'], 'capabilities': []}, [
        {'class': 'file', 'object': '/app/data/gears/out.csv', 'mask': 'wc', 'count': 3}, {'class': 'file', 'object': '/usr/local/lib/python3.12/__pycache__/x.pyc', 'mask': 'w', 'count': 30},
        {'class': 'file', 'object': '/etc/hosts', 'mask': 'w', 'count': 1}, {'class': 'cap', 'object': 'capability chown', 'mask': ''}, {'class': 'cap', 'object': 'capability sys_admin', 'mask': ''},
        {'class': 'seccomp', 'object': 'syscall open', 'mask': ''}, {'class': 'mount', 'object': 'mount /mnt/ tmpfs', 'mask': ''}])
    check('proposal: writable /app/data + CHOWN + open proposed; pycache ignored; /etc write, sys_admin and mount NOT expressible',
          pr['add_writable'] == ['/app/data'] and pr['add_capabilities'] == ['CHOWN'] and pr['add_syscalls'] == ['open'] and pr['pycache_writes_ignored'] == 30 and len(pr['not_expressible']) == 3)
    from security.custom.security_audit_feed import applied_from_controls, physical_from_controls
    ctl = [{'ring': 'mac', 'control': 'per-app-profiles', 'status': 'pass'}, {'ring': 'mac', 'control': 'profiles-enforcing', 'status': 'fail'}, {'ring': 'network', 'control': 'ufw', 'status': 'pass'}, {'ring': 'physical', 'control': 'secure-boot', 'status': 'fail'}]
    check('audit feed: profiles loaded + not enforcing → apparmor complain; ufw pass → live; secure boot fail → off', applied_from_controls(ctl) == {'polari-apparmor': 'complain', 'ufw': 'live'} and physical_from_controls(ctl) == {'secure_boot': False})
    from security.custom.security_notices import notices_from
    nt = notices_from(probes=[{'host': 'prf.example', 'days_left': -3, 'not_after': '2026-09-10', 'issuer': 'x'}, {'host': 'api.prf.example', 'days_left': 9, 'not_after': '', 'issuer': ''}],
                      audit_controls=[{'control': 'auto-renew', 'status': 'fail'}], identities=[{'service': 'pol-kc', 'issued': True, 'days_left': -25, 'manifest': 'ca/cert-manifest.conf'}], hosts=['prf.example', 'api.prf.example', 'hub.example'])
    codes = [n['code'] for n in nt]
    check('notices: expired → error with the renew action; expiring → warning; auto-renew absent → info; internal expired → warning; unreachable host → info',
          codes == ['cert-expired', 'cert-expiring', 'auto-renew-absent', 'internal-cert-expired', 'host-unreachable'] and nt[0]['level'] == 'error' and 'pol cert renew' in nt[0]['action'])
    from security.custom.security_ssh import ssh_row_from_inventory, inventory_row, ssh_summary
    inv = {'os': 'Ubuntu', 'kernel': 'k', 'docker': {'version': '29', 'swarm': 'active/false', 'containers': [{'name': 'isle-vlan-agent'}], 'stacks': [], 'images': [], 'volumes': 1}, 'debs': ['polari-complete|0.1.33|ok'], 'checkouts': ['/x|dev|1G'], 'units': ['isle-host-agent.service|active|running'], 'guests': ['openwrt-isle-router'], 'etc_isle_mesh': True, 'apparmor_polari': 66,
           'ssh': {'listen': ['0.0.0.0:22'], 'password_auth': 'yes', 'pubkey_auth': 'yes', 'permit_root': 'without-password', 'kbd_interactive': 'no', 'authorized_keys': [{'user': 'u', 'type': 'ssh-ed25519', 'comment_kind': 'user@host'}], 'private_keys_present': ['u|id_ed25519'], 'ssh_config_hosts': ['u|lightweight'], 'fail2ban': 'inactive', 'recent_failed_logins_24h': 0}}
    r = ssh_row_from_inventory('isle-core', inv); ir = inventory_row('isle-core', inv)
    check('ssh: passwords + root login → exposed, with the vectors named; role isle-core; formats deb + containers + guests', r['verdict'] == 'exposed' and 'passwords accepted' in r['vector'] and 'root may log in' in r['vector'] and r['role'] == 'isle-core' and 'deb' in ir['formats'] and 'KVM guests' in ir['formats'])
    inv2 = dict(inv, ssh=dict(inv['ssh'], listen=[])); check('ssh: no sshd → closed', ssh_row_from_inventory('pol-core', inv2)['verdict'] == 'closed')
    inv3 = dict(inv, ssh=dict(inv['ssh'], password_auth='no', permit_root='no')); check('ssh: keys only + no root → keys-only', ssh_row_from_inventory('x', inv3)['verdict'] == 'keys-only')
    check('ssh summary reads', ssh_summary([r, ssh_row_from_inventory('pol-core', inv2)])['exposed'] == ['isle-core'])
    # his ask 2026-09-14: permission levels + assurance (secure | dev until | unsecured)
    from security.custom.security_ssh import permission_levels, ssh_assurance, assurance_summary
    inv_u = dict(inv, ssh=dict(inv['ssh'], password_auth='no', permit_root='without-password', allow_groups='', groups=['sudo|u', 'polari-ops|dev1'],
                               sudoers=['root ALL=(ALL:ALL) ALL', '%sudo ALL=(ALL:ALL) ALL', 'u ALL=(ALL) NOPASSWD: ALL', '%polari-ops ALL=(root) /usr/bin/pol, /usr/bin/systemctl']))
    a = ssh_assurance(inv_u)
    check('assurance: root with key + no AllowGroups + blanket sudo, no posture → UNSECURED with the three reasons', a[0] == 'unsecured' and 'root may log in' in a[1] and 'AllowGroups' in a[1] and 'blanket sudo for u' in a[1], a)
    lv = {r['principal']: r for r in permission_levels('n', inv_u)}
    check('levels: u = blanket-sudo (sudoers ALL), %polari-ops = scoped-sudo with its command list, dev1 scoped via the group, root allowed in',
          lv['u']['level'] == 'blanket-sudo' and lv['%polari-ops']['level'] == 'scoped-sudo' and '/usr/bin/pol' in lv['%polari-ops']['commands'] and lv['dev1']['level'] == 'scoped-sudo' and lv['root']['allowed_over_ssh'] is True, {k: (v['level'], v['allowed_over_ssh']) for k, v in lv.items()})
    inv_d = dict(inv_u, ssh=dict(inv_u['ssh'], posture={'posture': 'dev', 'until': '2999-01-01T00:00:00Z', 'relaxations': ['ssh.root-key-from-isle']}))
    a2 = ssh_assurance(inv_d)
    check('assurance: the same device under a declared, unexpired dev posture → DEV with the expiry', a2[0] == 'dev' and '2999' in a2[1], a2)
    inv_x = dict(inv_u, ssh=dict(inv_u['ssh'], posture={'posture': 'dev', 'until': '2020-01-01T00:00:00Z'}))
    check('assurance: an EXPIRED dev posture → UNSECURED', ssh_assurance(inv_x)[0] == 'unsecured' and 'EXPIRED' in ssh_assurance(inv_x)[1])
    inv_p = dict(inv_d, ssh=dict(inv_d['ssh'], password_auth='yes'))
    check('invariant: passwords accepted is UNSECURED even in dev posture', ssh_assurance(inv_p)[0] == 'unsecured')
    inv_s = dict(inv_u, ssh=dict(inv_u['ssh'], permit_root='no', allow_groups='polari-ops', sudoers=['root ALL=(ALL:ALL) ALL', '%sudo ALL=(ALL:ALL) ALL', '%polari-ops ALL=(root) /usr/bin/pol']))
    check('assurance: keys only + no root + AllowGroups + scoped sudo → SECURE; a keyed user outside AllowGroups is not allowed in', ssh_assurance(inv_s)[0] == 'secure' and {r['principal']: r['allowed_over_ssh'] for r in permission_levels('n', inv_s)}['u'] is False)
    rows = [ssh_row_from_inventory('a', inv_s), ssh_row_from_inventory('b', inv_d), ssh_row_from_inventory('c', inv_u)]
    summ = assurance_summary(rows)
    check('assurance summary: 1 secure, 1 dev (until), 1 unsecured → not assured', summ['secure'] == ['a'] and summ['dev'] and summ['dev'][0].startswith('b (until') and summ['unsecured'] == ['c'] and summ['assured'] is False, summ)
    check('assurance summary: secure + dev only → assured', assurance_summary(rows[:2])['assured'] is True)
    from security.custom.security_notices import posture_notices
    class _M:
        pass
    class _R:
        def __init__(self, **kw): self.__dict__.update(kw)
    m = _M(); m.objectTables = {'SshCapability': {'b': _R(device='b', assurance='dev', posture_until='2999-01-01T00:00:00Z', assurance_reasons=''), 'c': _R(device='c', assurance='unsecured', posture_until='', assurance_reasons='passwords accepted')}}
    pn = posture_notices(m, env={'POLARI_POSTURE': 'dev'})
    check('dev-mode notices: the install-level DEV MODE warning names the danger of connecting to systems that are not your own; dev devices warn; unsecured devices error',
          [n['code'] for n in pn] == ['dev-mode', 'dev-posture-devices', 'ssh-unsecured'] and 'not your own' in pn[0]['text'] and 'EXTREMELY DANGEROUS' in pn[0]['text'] and pn[2]['level'] == 'error' and 'passwords accepted' in pn[2]['text'], [n['code'] for n in pn])
    check('production install, every device secure → no posture notice', posture_notices(_M(), env={}) == [])
    # ---- ISLE_HARDENING_PLAN §17: OBSERVE MODE — one switch (posture), one ledger (SecurityEvent), one contract
    import os
    import tempfile
    from moduleService import posture as P
    from security.custom import security_observe as O
    with tempfile.TemporaryDirectory() as td:
        pf = os.path.join(td, 'posture.json')
        check('posture: nothing says dev → production (source default)', P.state(env={}, path=pf) == {'posture': 'production', 'until': '', 'source': 'default', 'expired': False, 'relaxations': [], 'applied_by': ''})
        check('posture: POLARI_POSTURE=dev wins (source env)', P.state(env={'POLARI_POSTURE': 'dev', 'POLARI_POSTURE_UNTIL': ''}, path=pf)['posture'] == 'dev' and P.is_dev(env={'POLARI_POSTURE': 'dev'}, path=pf))
        open(pf, 'w').write('{"posture": "dev", "until": "2999-01-01T00:00:00Z", "relaxations": ["ssh.root-key-from-isle"], "applied_by": "posture.sh"}')
        st = P.state(env={}, path=pf)
        check('posture: the machine\'s posture.json (mounted read-only) says dev with an expiry → dev, its relaxations read', st['posture'] == 'dev' and st['source'] == 'file' and st['relaxations'] == ['ssh.root-key-from-isle'])
        open(pf, 'w').write('{"posture": "dev", "until": "2020-01-01T00:00:00Z"}')
        st = P.state(env={}, path=pf)
        check('posture: an EXPIRED dev posture is production again (the revert timer\'s promise, kept here too)', st['posture'] == 'production' and st['expired'] is True)
    m2 = _M(); m2.objectTables = {'SecurityEvent': {}}
    m2.persistTree = lambda: None
    dev = {'POLARI_POSTURE': 'dev'}; prod = {}
    check('decide: an allowed act is allowed, nothing recorded', O.decide(m2, 'authz', 'update Person', 'Person', denied=False, env=dev) == (True, 'allowed') and O.events(m2) == [])
    ok, out = O.decide(m2, 'authz', 'update Person', 'Person', denied=True, reason='no verb grant', actor='dev1', env=dev, source='test')
    check('decide: DEV posture + an observable control → the act PROCEEDS as "observed" and a SecurityEvent counts it', ok is True and out == 'observed' and len(O.events(m2)) == 1 and O.events(m2)[0]['count'] == 1 and O.events(m2)[0]['would_deny'] is True)
    O.decide(m2, 'authz', 'update Person', 'Person', denied=True, reason='no verb grant', env=dev)
    check('the same decision again counts on the same row (control|action|target)', len(O.events(m2)) == 1 and O.events(m2)[0]['count'] == 2)
    check('decide: PRODUCTION posture → denied (the caller refuses as before), recorded as denied', O.decide(m2, 'authz', 'delete Person', 'Person', denied=True, env=prod)[1] == 'denied')
    check('decide: an INVARIANT (§16) refuses even in dev; an unknown control is treated as an invariant',
          O.decide(m2, 'ssh-password', 'password login', 'sshd', denied=True, env=dev) == (False, 'denied') and O.decide(m2, 'made-up', 'x', 'y', denied=True, env=dev) == (False, 'denied'))
    check('the contract: authz, peer admission, certificates, trust channels, content, browser, tier, posture relaxations OBSERVE; the six invariants + dev-variant-on-production + headless encryption REFUSE',
          set(O.OBSERVED_CONTROLS) >= {'authz', 'peer-admission', 'certificate', 'trust-channel', 'content', 'browser', 'tier', 'posture-relaxation'}
          and set(O.INVARIANT_CONTROLS) >= {'ssh-password', 'upstream-interface', 'production-route', 'dev-variant-on-production', 'iso-headless-encryption'} and not set(O.OBSERVED_CONTROLS) & set(O.INVARIANT_CONTROLS))
    s = O.summary(m2, env=dev)
    check('summary: observe on, the observed actions counted per control, the contract stated', s['observe'] is True and s['observed_actions'] == 2 and s['per_control'] == {'authz': 2} and s['contract']['observed'])
    on = O.observe_notice(m2, env=dev)
    check('the notice bar item (dev only): OBSERVE MODE with the count of what production would deny; absent in production',
          len(on) == 1 and on[0]['code'] == 'observe-mode' and on[0]['level'] == 'warning' and '2 action(s)' in on[0]['title'] and O.observe_notice(m2, env=prod) == [])
    from security.security_api import SecurityAPI
    class _Req:
        params = {}
    class _Res:
        media = None; status = '200 OK'
        def set_header(self, k, v):
            self.headers = dict(getattr(self, 'headers', {}), **{k: v})
    api = SecurityAPI(polServer=None, manager=None); api.manager = m2; r = _Res(); api.on_get_events(_Req(), r)
    check('/api/security/events answers with the summary, the events and the how', r.media['ok'] and r.media['summary']['observed_events'] == 1 and len(r.media['events']) >= 2 and 'observe' in r.media['how'],
          (r.media or {}).get('summary'))
    from accessControl.app_permissions_gate import crude_permission_gate
    import types as _types
    class _Hdr:
        def __init__(self): self.h = {}; self.status = ''; self.media = None
        def set_header(self, k, v): self.h[k] = v
    class _ReqU:
        # a REAL caller: Keycloak hands down both a name and a sub. Only the sub may ever reach a row (D18-1).
        context = _types.SimpleNamespace(user_info={'preferred_username': 'dev1', 'sub': 'u-dev1'})
    import sys as _sys, types as _t
    fake = _t.ModuleType('polariapps.apps_permissions_basis'); fake.permission_verdict = lambda *a, **k: {'allowed': False, 'reason': 'no grant'}
    pkg = _t.ModuleType('polariapps'); pkg.apps_permissions_basis = fake
    saved = {k: _sys.modules.get(k) for k in ('polariapps', 'polariapps.apps_permissions_basis')}
    _sys.modules['polariapps'] = pkg; _sys.modules['polariapps.apps_permissions_basis'] = fake
    m3 = _M(); m3.objectTables = {'AppPermissionProfile': {}, 'SecurityEvent': {}}; m3.persistTree = lambda: None
    old_env = dict(os.environ); os.environ['POLARI_APP_PERMISSIONS'] = 'enforce'; os.environ['POLARI_POSTURE'] = 'dev'
    try:
        h = _Hdr(); g1 = crude_permission_gate(m3, _ReqU(), h, 'update', 'Person')
        os.environ['POLARI_POSTURE'] = 'production'; h2 = _Hdr(); g2 = crude_permission_gate(m3, _ReqU(), h2, 'update', 'Person')
    finally:
        os.environ.clear(); os.environ.update(old_env)
        for k, v in saved.items():
            if v is None: _sys.modules.pop(k, None)
            else: _sys.modules[k] = v
    check('the CRUDE permission gate in ENFORCE: a dev build lets the refused act through with an "observed" header + a SecurityEvent; production still 403s',
          g1 is True and 'observed Person:update' in h.h.get('X-Polari-Permission-Advisory', '') and len(O.events(m3)) == 1 and O.events(m3)[0]['actor'] == 'u-dev1' and g2 is False and h2.status == '403 Forbidden')
    check('...and the event the gate wrote names the caller by their Keycloak `sub` ONLY (D18-1): the token\'s '
          'preferred_username reaches no column', 'dev1' not in repr([e for e in O.events(m3)]).replace('u-dev1', ''),
          O.events(m3))
    # ---- his ask 2026-09-15: in dev mode, log which roles / profiles perform which acts → the profiles are WORKED OUT from that
    import json
    m4 = _M(); m4.objectTables = {'PermissionObservation': {}}; m4.persistTree = lambda: None
    u_op = {'preferred_username': 'ops1', 'roles': ['operators']}; u_ad = {'preferred_username': 'root1', 'roles': ['admin']}
    O.observe_permission(m4, u_op, 'PrintJob', 'read', verdict={'allowed': True, 'why': 'granted by profile(s)', 'via': ['print-operator']})
    O.observe_permission(m4, u_op, 'PrintJob', 'read', verdict={'allowed': True, 'why': 'granted by profile(s)', 'via': ['print-operator']})
    O.observe_permission(m4, u_op, 'PrintJob', 'update', verdict={'allowed': False, 'why': 'no granted profile covers PrintJob:update', 'via': []})
    O.observe_permission(m4, u_ad, 'Person', 'delete', verdict={'allowed': True, 'why': 'admin role bypass', 'via': ['admin']})
    O.observe_permission(m4, None, 'Person', 'read', verdict=None)
    O.observe_permission(m4, u_op, 'MaterialLot', 'create', verdict=None)
    ob = {o['name']: o for o in O.observations(m4)}
    check('observations: one row per roles × class × verb, counted; the profile that granted; would-deny / admin / unauthenticated / ungated named',
          ob['operators|PrintJob|read']['count'] == 2 and ob['operators|PrintJob|read']['profiles'] == 'print-operator' and ob['operators|PrintJob|read']['verdict'] == 'granted-by-profile'
          and ob['operators|PrintJob|update']['verdict'] == 'would-deny' and ob['admin|Person|delete']['verdict'] == 'admin' and ob['-|Person|read']['verdict'] == 'unauthenticated'
          and ob['operators|MaterialLot|create']['verdict'] == 'ungated', sorted(ob))
    der = {d['name']: d for d in O.derive_profiles(m4)}
    check('derived: one proposed AppPermissionProfile per role set in the row\'s own shape — classes touched, verbs used, unpublished, with the evidence; unauthenticated acts derive nothing',
          set(der) == {'observed-operators', 'observed-admin'} and json.loads(der['observed-operators']['extra_classes_json']) == ['MaterialLot', 'PrintJob']
          and json.loads(der['observed-operators']['verbs_json']) == ['create', 'read', 'update'] and der['observed-operators']['published'] is False
          and der['observed-operators']['evidence']['acts'] == 4 and der['observed-operators']['evidence']['would_deny_today'] == 1 and json.loads(der['observed-operators']['kc_groups_json']) == ['operators'], sorted(der))
    m5 = _M(); m5.objectTables = {'PermissionObservation': {}}; m5.persistTree = lambda: None
    old_env = dict(os.environ); os.environ['POLARI_APP_PERMISSIONS'] = 'off'; os.environ['POLARI_POSTURE'] = 'dev'
    try:
        h = _Hdr(); g_off = crude_permission_gate(m5, _ReqU(), h, 'read', 'Person')
    finally:
        os.environ.clear(); os.environ.update(old_env)
    check('the gate records observations in dev EVEN WITH POLARI_APP_PERMISSIONS=off (no profile table → "ungated"), and still proceeds', g_off is True and len(O.observations(m5)) == 1 and O.observations(m5)[0]['verdict'] == 'ungated')
    # ---- his asks 2026-09-16: the knob on the fly; ROLE-PLAY a group → review everything it used → concrete → verify
    with tempfile.TemporaryDirectory() as td:
        old_env = dict(os.environ); os.environ['POLARI_OBSERVE_KNOB'] = os.path.join(td, 'observe.json'); os.environ['POLARI_POSTURE'] = 'dev'
        try:
            check('the knob: recording is ON by default in dev', O.recording_on(m4) is True and O.knob_state()['source'].startswith('default'))
            O.set_recording(False, by='admin1')
            m6 = _M(); m6.objectTables = {'PermissionObservation': {}, 'UsageObservation': {}, 'ObservationSession': {}}; m6.persistTree = lambda: None
            O.observe_permission(m6, u_op, 'PrintJob', 'read', verdict=None); O.observe_usage(m6, 'journalist', 'page', '/scorecard')
            check('the knob OFF on the fly: nothing is recorded (acts or usages), the state says who and when', O.recording_on(m6) is False and O.observations(m6) == [] and O.knob_state()['by'] == 'admin1')
            O.set_recording(True, by='admin1')
            os.environ['POLARI_POSTURE'] = 'production'
            check('production never records, knob or not', O.recording_on(m6) is False)
            os.environ['POLARI_POSTURE'] = 'dev'
            s1 = O.start_session(m6, 'Journalist', actor='dustin', note='acting as the journalist')
            check('a role-play session opens for the role (lower-cased), tells the header to send, is idempotent while open', s1['ok'] and s1['role'] == 'journalist' and s1['header'] == {'X-Polari-Roleplay': 'journalist'} and O.start_session(m6, 'journalist', actor='dustin')['already_open'] is True)
            u_j = {'preferred_username': 'dustin', 'roles': ['admin']}
            O.observe_permission(m6, u_j, 'Article', 'read', verdict={'allowed': True, 'why': 'admin role bypass', 'via': ['admin']}, roleplay='journalist')
            O.observe_permission(m6, u_j, 'Article', 'create', verdict={'allowed': True, 'why': 'admin role bypass', 'via': ['admin']}, roleplay='journalist')
            O.observe_permission(m6, u_j, 'Dataset', 'read', verdict={'allowed': True, 'why': 'admin role bypass', 'via': ['admin']}, roleplay='journalist')
            O.observe_permission(m6, u_j, 'Article', 'read', verdict={'allowed': True, 'why': 'admin role bypass', 'via': ['admin']}, roleplay='journalist')
            O.observe_usage(m6, 'journalist', 'app', 'journalist', actor='dustin'); O.observe_usage(m6, 'journalist', 'app', 'datascience'); O.observe_usage(m6, 'journalist', 'page', '/journalist/articles', app='journalist')
            O.observe_usage(m6, 'journalist', 'action', 'publish-article', app='journalist', page='/journalist/articles'); O.observe_usage(m6, 'journalist', 'endpoint', 'GET /api/scoring/{id}'); O.observe_usage(m6, 'journalist', 'page', '/journalist/articles', app='journalist')
            ob6 = {o['name']: o for o in O.observations(m6)}
            check('acts while role-playing are attributed to the role AND the real identity (groups carry roleplay:journalist beside admin)',
                  'admin,roleplay:journalist|Article|read' in ob6 and ob6['admin,roleplay:journalist|Article|read']['count'] == 2)
            rv = O.review(m6, 'journalist')
            check('the review of the role: the apps, pages, actions, endpoints it used (counted) and the objects × verbs; a proposed profile in the row\'s shape; the handoff',
                  [a['item'] for a in rv['apps']] == ['datascience', 'journalist'] or {a['item'] for a in rv['apps']} == {'journalist', 'datascience'}
                  and rv['pages'][0]['item'] == '/journalist/articles' and rv['pages'][0]['count'] == 2 and rv['actions'][0]['item'] == 'publish-article' and rv['endpoints'][0]['item'] == 'GET /api/scoring/{id}'
                  and rv['objects'] == {'Article': {'read': 2, 'create': 1}, 'Dataset': {'read': 1}} and json.loads(rv['proposed_profile']['kc_groups_json']) == ['journalist']
                  and json.loads(rv['proposed_profile']['extra_classes_json']) == ['Article', 'Dataset'] and json.loads(rv['proposed_profile']['verbs_json']) == ['create', 'read'] and rv['proposed_profile']['published'] is False, rv['objects'])
            sess = O.sessions(m6, 'journalist')[0]
            check('the session counts what was attributed to it (4 acts, 6 usages) and ends on request', sess['acts'] == 4 and sess['usages'] == 6 and O.end_session(m6, role='journalist')['ended'] and O.sessions(m6, 'journalist', active=True) == [])
            # verify: concrete the role into a profile, then replay — narrower than the job → the denied acts are named
            class _P:
                def __init__(self, **kw): self.__dict__.update(kw)
            m6.objectTables['AppPermissionProfile'] = {'p1': _P(name='journalist', published=True, kc_groups_json='["journalist"]', verbs_json='["read"]', app_name='', extra_classes_json='["Article", "Dataset"]')}
            vf = O.verify(m6, 'journalist')
            check('verify after enforcement: a read-only journalist profile → the recorded Article:create would now be DENIED, the reads allowed; the verdict says the profile is narrower than the job',
                  vf['ok'] and vf['recorded_acts'] == 3 and [d['class'] + ':' + d['verb'] for d in vf['denied']] == ['Article:create'] and len(vf['allowed']) == 2 and 'narrower' in vf['verdict'], vf)
            m6.objectTables['AppPermissionProfile']['p1'].verbs_json = '["read", "create"]'
            check('widen the profile to what the job needs → the role can still do everything it was recorded doing', O.verify(m6, 'journalist')['denied'] == [] and 'still do everything' in O.verify(m6, 'journalist')['verdict'])
            api.manager = m6; r = _Res(); api.on_get_observe(_Req(), r); ok_knob = r.media['recording'] is True and 'knob' in r.media
            class _ReqB:
                params = {}; context = _types.SimpleNamespace(user_info=None, roleplay='journalist')
                media = {'items': [{'kind': 'page', 'item': '/journalist/inbox', 'app': 'journalist'}, {'kind': 'bogus', 'item': 'x'}]}
            r = _Res(); api.on_post_observe_usage(_ReqB(), r)
            check('/api/security/observe answers the knob; /api/security/observe/usage takes a batch from the frontend, attributes it to the role-play header, skips unknown kinds',
                  ok_knob and r.media['recorded'] == 1 and any(u['item'] == '/journalist/inbox' and u['role'] == 'journalist' for u in O.usages(m6)))
            class _ReqR:
                params = {'role': 'journalist'}
            # prototype roles + the role-play permission
            pr = O.create_prototype(m6, 'Data Scientist', description='reads datasets, runs notebooks', by='dustin')
            check('a prototype role is created (lower-cased id, a title), idempotent, never an admin role', pr['ok'] and pr['role']['name'] == 'data-scientist' and pr['role']['state'] == 'prototype'
                  and O.create_prototype(m6, 'data-scientist')['existed'] is True and O.create_prototype(m6, 'admin')['ok'] is False)
            check('prototype → concreted (the profile named) → enforced, verified verdict kept',
                  O.mark_prototype(m6, 'data-scientist', 'concreted', profile='data-scientist')['role']['concreted_profile'] == 'data-scientist' and O.mark_prototype(m6, 'data-scientist', 'enforced', verdict='ok')['role']['state'] == 'enforced'
                  and O.prototypes(m6, state='enforced')[0]['name'] == 'data-scientist')
            check('the role-play permission: admins always; a dev instance with no list → everyone; with a list → only its groups; production → nobody',
                  O.can_roleplay({'roles': ['admin']})[0] and O.can_roleplay({'roles': ['nobody']})[0] and O.set_roleplay_groups(['developers'])['ok']
                  and O.can_roleplay({'roles': ['developers']})[0] and not O.can_roleplay({'roles': ['journalist']})[0] and not O.can_roleplay({'roles': ['admin']}, env={'POLARI_POSTURE': 'production'})[0])
            class _ReqNo:
                params = {}; context = _types.SimpleNamespace(user_info={'roles': ['journalist']}, roleplay=''); media = {'role': 'data-scientist'}
            r = _Res(); api.on_post_observe_session(_ReqNo(), r)
            check('a caller without the role-play permission cannot open a session (403 with the reason)', r.status.startswith('403') and 'role-play permission' in r.media['refusal'])
            r = _Res(); api.on_get_observe_roles(_ReqNo(), r)
            check('/api/security/observe/roles lists the prototypes and says whether the caller may role-play', r.media['ok'] and r.media['roles'][0]['name'] == 'data-scientist' and r.media['can_roleplay'] is False and r.media['roleplay_groups'] == ['developers'])
            check('the app column: a class maps back to the module that registers it (SecurityDomain → security; unknown → \'\')', O.app_of_class('SecurityDomain') == 'security' and O.app_of_class('NoSuchClass') == '')
            r = _Res(); api.on_get_observe_review(_ReqR(), r); r2 = _Res(); api.on_get_observe_verify(_ReqR(), r2)
            check('/api/security/observe/review + /verify answer for the role', r.media['ok'] and r.media['role'] == 'journalist' and r2.media['ok'] and r2.media['group'] == 'journalist')
            _claims_checks(api, m6, O, _Res, _types, check)
        finally:
            os.environ.clear(); os.environ.update(old_env)
    api.manager = m4; r = _Res(); api.on_get_observations(_Req(), r)
    check('/api/security/observations: the rows, the totals by verdict, the derived suggestions, the how', r.media['ok'] and r.media['count'] == 5 and r.media['by_verdict']['granted-by-profile'] == 2 and len(r.media['derived']) == 2 and 'never' in r.media['how'] or 'nothing is applied' in r.media['how'])
    # ---- ledger §51 defect 2: ?groups=<name> is a MEMBERSHIP test, not equality against the joined field.
    # A real login's row carries the whole KC group set (default-roles-polari,journalist,…,roleplay:journalist),
    # so exact equality could never match a filter naming one group — every filtered result in the §51 run had
    # to be computed client-side.
    m7 = _M(); m7.objectTables = {'PermissionObservation': {}}; m7.persistTree = lambda: None
    old_env = dict(os.environ); os.environ['POLARI_POSTURE'] = 'dev'; os.environ.pop('POLARI_OBSERVE_KNOB', None)
    try:
        u_real = {'preferred_username': 'demo-journalist', 'roles': ['journalist', 'polari-user', 'offline_access']}
        O.observe_permission(m7, u_real, 'TermsDocument', 'read', verdict={'allowed': False, 'why': 'no granted profile covers TermsDocument:read', 'via': []}, roleplay='journalist')
        O.observe_permission(m7, {'preferred_username': 'ops1', 'roles': ['operators']}, 'PrintJob', 'read', verdict=None)
        class _ReqF:
            def __init__(self, **p): self.params = p
        api.manager = m7
        r = _Res(); api.on_get_observations(_ReqF(groups='journalist'), r)
        rall = _Res(); api.on_get_observations(_ReqF(), rall)
        rno = _Res(); api.on_get_observations(_ReqF(groups='nobody'), rno)
        rboth = _Res(); api.on_get_observations(_ReqF(groups='journalist,roleplay:journalist'), rboth)
        rv = _Res(); api.on_get_observations(_ReqF(groups='journalist', verb='create'), rv)
        check('/api/security/observations?groups=<name> matches a row whose group SET contains it (§51: it was exact '
              'equality against the whole comma-joined field, so a real multi-group login could never match)',
              rall.media['count'] == 2 and r.media['count'] == 1 and 'journalist' in r.media['observations'][0]['groups']
              and rno.media['count'] == 0 and rboth.media['count'] == 1 and rv.media['count'] == 0,
              (rall.media['count'], r.media['count'], rno.media['count'], rboth.media['count'], rv.media['count']))
    finally:
        os.environ.clear(); os.environ.update(old_env)
    # ---- ledger §51 defect 3: an EXPIRED bearer must read as UNAUTHENTICATED, not as "would-deny everything"
    from accessControl.auth_middleware import AuthContextMiddleware
    class _HdrReq:
        def __init__(self, header=None):
            self._h = header; self.context = _types.SimpleNamespace()
        def get_header(self, name):
            return self._h if name.lower() == 'authorization' else None
    class _Stub:
        def validate(self, token):   # every token is expired/refused, as an expired one is
            return None
    mw = AuthContextMiddleware(validator=_Stub())
    q1 = _HdrReq('Bearer eyJhbGciOiJSUzI1NiJ9.expired.sig'); h1 = _Hdr()
    mw.process_request(q1, h1)
    q2 = _HdrReq(None); h2b = _Hdr()
    mw.process_request(q2, h2b)
    check('the auth middleware: a Bearer that failed validation answers X-Polari-Auth: invalid-or-expired and marks '
          'the request auth_failed; no bearer at all sets no header (anonymous is not an error)',
          q1.context.user_info is None and q1.context.auth_failed is True and h1.h.get('X-Polari-Auth') == 'invalid-or-expired'
          and q2.context.user_info is None and q2.context.auth_failed is False and 'X-Polari-Auth' not in h2b.h, (h1.h, h2b.h))
    class _ReqExp:
        context = _types.SimpleNamespace(user_info=None, auth_failed=True)
    class _ReqAnon:
        context = _types.SimpleNamespace(user_info=None, auth_failed=False)
    _sys.modules['polariapps'] = pkg; _sys.modules['polariapps.apps_permissions_basis'] = fake
    m8 = _M(); m8.objectTables = {'AppPermissionProfile': {}, 'SecurityEvent': {}}; m8.persistTree = lambda: None
    old_env = dict(os.environ); os.environ['POLARI_POSTURE'] = 'production'
    try:
        os.environ['POLARI_APP_PERMISSIONS'] = 'advisory'
        ha = _Hdr(); ga = crude_permission_gate(m8, _ReqExp(), ha, 'read', 'Person')
        hn = _Hdr(); gn = crude_permission_gate(m8, _ReqAnon(), hn, 'read', 'Person')
        hu = _Hdr(); gu = crude_permission_gate(m8, _ReqU(), hu, 'read', 'Person')
        os.environ['POLARI_APP_PERMISSIONS'] = 'enforce'
        he = _Hdr(); ge = crude_permission_gate(m8, _ReqExp(), he, 'read', 'Person')
    finally:
        os.environ.clear(); os.environ.update(old_env)
        for k, v in saved.items():
            if v is None: _sys.modules.pop(k, None)
            else: _sys.modules[k] = v
    check('the gate in ADVISORY: an expired/absent identity says "unauthenticated", NOT "would-deny" (§51: a stale '
          'token grew a would-deny header on every read — under enforce a 403 storm indistinguishable from a real '
          'permission problem); an authenticated caller without the grant still reads would-deny',
          ga is True and ha.h['X-Polari-Permission-Advisory'] == 'unauthenticated Person:read (token invalid or expired)'
          and ha.h.get('X-Polari-Auth') == 'invalid-or-expired'
          and gn is True and hn.h['X-Polari-Permission-Advisory'] == 'unauthenticated Person:read' and 'X-Polari-Auth' not in hn.h
          and gu is True and hu.h['X-Polari-Permission-Advisory'] == 'would-deny Person:read', (ha.h, hn.h, hu.h))
    check('the gate in ENFORCE: the refusal for a dead session says unauthenticated + "sign in again", with the '
          'evidence, instead of a bare permission refusal',
          ge is False and he.status == '403 Forbidden' and he.media['error'] == 'unauthenticated'
          and 'sign in again' in he.media['why'] and he.media['verdict']['auth'] == 'invalid-or-expired', he.media)
    m9 = _M(); m9.objectTables = {'PermissionObservation': {}}; m9.persistTree = lambda: None
    old_env = dict(os.environ); os.environ['POLARI_POSTURE'] = 'dev'
    try:
        O.observe_permission(m9, None, 'Person', 'read', verdict={'allowed': False, 'why': 'no authenticated identity — no profile can match', 'via': []})
    finally:
        os.environ.clear(); os.environ.update(old_env)
    check('the observation for an unauthenticated act is recorded as "unauthenticated", never "would-deny"',
          O.observations(m9)[0]['verdict'] == 'unauthenticated', O.observations(m9))
    from security.custom.security_ssh import permission_group_updates, merge_members
    pg = permission_group_updates('n', inv_u)
    check('permission groups: observed sudo + polari-ops members tied per device', pg['sudo']['members'] == 'n: u' and pg['polari-ops']['members'] == 'n: dev1')
    check('members merge per device (this device replaced, others kept)', merge_members('a: x; n: old', 'n', 'n: u') == 'a: x; n: u')
    _pii_checks(api, O, _Res, _types, check)
    _people_batch_checks(api, O, _Res, _types, check)
    _owned_checks(api, O, _Res, _types, check)
    _grant_checks(api, O, _Res, _types, check)              # op-1: the owner's per-instance grants
    _anonymised_checks(api, O, _Res, _types, check)         # op-2: the three side channels, frozen, transfer
    _owned_manifest_checks(_Res, _types, check)             # op-4: app.owned, validated and converged
    _trace_checks(api, _Res, _types, check)
    _ct2_checks(_types, check)
    _ct9_checks(_types, check)
    _closure_checks(api, O, _Res, _types, check)
    _ct5_checks(api, _Res, _types, check)
    _ct7_checks(api, O, _Res, _types, check)
    check('the password-guess threat exists on the isle with its counterexample', 'ssh-password-guess' in {t['name'] for t in threats('isle', 'today')['threats']})
    check('threat rows seed for every scenario', len([r for n in scenario_names() for r in threat_rows(n)]) >= 40)
    print('\n%d/%d checks passed' % (passed, total))
    return 0 if passed == total else 1


if __name__ == '__main__':
    sys.exit(main())
