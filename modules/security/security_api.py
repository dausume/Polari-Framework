"""
@module security.security_api

/api/security            the taxonomy, the scenario in force here, the systems with provenance
/api/security/scenarios  every scenario (route, attach, rings, fixed pieces)
/api/security/topology   ?view=os|network|app [&scenario=…] [&mode=stock|today|complain|enforce] — one view, one scenario
/api/security/simulate   ?view=… &actor=… [&scenario=…] [&mode=…] — everything one actor can reach, hop by hop
/api/security/compare    ?view=… [&mode=…] — the same view across every scenario, verdict per scenario
/api/security/ssh        ssh capabilities across Polari devices (exposed / keys-only / closed, who reaches whom) — the isle topology shows it
/api/security/inventory  GET each device's installed footprint (deb / images / stacks / checkouts / guests / units); POST inventory.sh JSON
/api/security/notices    what a user should be told now: expired / expiring certificates (live TLS probe of this instance's hosts),
                         auto-renew absent (from the last audit run); the frontends' system-notice bar polls it
/api/security/ledger     [?scenario=…] — AppSecurityRecord per app: steps complete / total, the blocking step (the per-app ledger)
/api/security/audit      GET the latest posted audit runs + what 'today' reads from them; POST an audit.sh --json payload
/api/security/propose    POST {app, groups} (allowed.py --json groups) → a SecurityProposal: the stanza change the harvest asks for
/api/security/threats    [?scenario=…] [&mode=…] — the threat simulations: each threat's path through the systems, the policy that
                         blocked it, and the counterexample (the actor/group/permission that legitimately reaches the same target)
The scenario defaults to the one this deployment is (POLARI_DEPLOY_ROUTE: isle → isle, swarm → lean/full by
profile, else dev). Pure reads over security_topology; nothing here changes the machine.
"""
import os

from objectTreeDecorators import treeObject, treeObjectInit

from security.custom.security_facts import SYSTEMS, load_scenario, scenario_names
from security.custom.security_topology import MODES, VIEWS, build, compare, simulate
from security.custom.security_threats import threats
from security.custom.security_ledger import app_security_records, ledger_summary
from security.custom.security_audit_feed import applied_for, run_row_from_audit, verdicts_for, latest_runs
from security.custom.security_proposals import propose_from_groups, proposal_row
from security.custom.security_notices import notices
from security.custom.security_ssh import inventory_row, ssh_row_from_inventory, ssh_rows, ssh_summary


def default_scenario():
    try:
        from moduleService.hardware_reach import deployment_route
        route = deployment_route()
    except Exception:
        route = 'dev'
    if route == 'isle':
        return 'isle'
    if route == 'swarm':
        return 'swarm-full' if os.environ.get('POLARI_AUTH', '').lower() == 'keycloak' or os.environ.get('KEYCLOAK_ISSUER') else 'swarm-lean'
    return 'dev'


class SecurityAPI(treeObject):
    @treeObjectInit
    def __init__(self, polServer=None, manager=None):
        self.polServer = polServer
        self.manager = manager
        if polServer is not None and getattr(polServer, 'falconServer', None) is not None:
            add = polServer.falconServer.add_route
            add('/api/security', self)
            add('/api/security/scenarios', self, suffix='scenarios')
            add('/api/security/topology', self, suffix='topology')
            add('/api/security/simulate', self, suffix='simulate')
            add('/api/security/compare', self, suffix='compare')
            add('/api/security/threats', self, suffix='threats')
            add('/api/security/ledger', self, suffix='ledger')
            add('/api/security/notices', self, suffix='notices')
            add('/api/security/ssh', self, suffix='ssh')              # ssh capabilities across devices (the isle topology shows it)
            add('/api/security/inventory', self, suffix='inventory')  # GET the devices' installed footprint; POST an inventory.sh payload   # what a user should be told: expired/expiring certs, auto-renew absent
            add('/api/security/audit', self, suffix='audit')          # POST an audit.sh --json payload; GET the latest runs
            add('/api/security/propose', self, suffix='propose')      # POST {app, stanza, groups} → a proposal row
            add('/api/security/events', self, suffix='events')        # observe mode (§17): what production would have denied, counted; the contract
            add('/api/security/observations', self, suffix='observations')   # dev mode: who (roles/profiles) did what (class × verb) + the DERIVED profile suggestions
            add('/api/security/observe', self, suffix='observe')                    # GET the recording knob + open sessions; POST {recording: true|false} — on/off on the fly
            add('/api/security/observe/session', self, suffix='observe_session')    # POST {role, actor, note} start role-playing; DELETE ?role= (or ?name=) end it
            add('/api/security/observe/usage', self, suffix='observe_usage')        # POST {role, kind: app|page|component|action|object, item, app, page, detail} from the frontend
            add('/api/security/observe/review', self, suffix='observe_review')      # GET ?role= everything the role used + the proposed profile (the handoff)
            add('/api/security/observe/verify', self, suffix='observe_verify')      # GET ?role=&group= replay the recording against the enforced profiles
            add('/api/security/observe/roles', self, suffix='observe_roles')        # GET the prototype roles + whether the caller may role-play; POST {name, title, description} a new prototype
            add('/api/security/observe/roles/{name}', self, suffix='observe_role')  # POST {state, profile, verdict} mark prototype → concreted → enforced

    def _rows(self, class_name):
        return list(((getattr(self.manager, 'objectTables', None) or {}).get(class_name, {}) or {}).values())

    @staticmethod
    def _bad(response, msg):
        import falcon
        response.status = falcon.HTTP_400
        response.media = {'ok': False, 'error': msg}

    def on_get(self, request, response):
        scn = default_scenario()
        sc = load_scenario(scn) or {}
        response.media = {
            'ok': True, 'scenario': scn, 'route': sc.get('route'), 'title': sc.get('title'),
            'views': [{'view': v, 'route': f'/display/security-{v}', 'question': q} for v, q in (
                ('os', 'what can a process touch on the machine, and which system stops it'),
                ('network', 'how do bytes get in, between and out'),
                ('app', 'who gets access to what, through which means'))],
            'modes': list(MODES),
            'systems': [{'system': k, 'title': v['title'], 'provenance': v['provenance'], 'domain': v['domain'], 'area': v['area']} for k, v in SYSTEMS.items()],
            'reading': 'stock = docker/the kernel already give it to every container; qemu = every guest has it; polari = rendered by Polari (mode says whether it is loaded)',
        }

    def on_get_scenarios(self, request, response):
        out = []
        for n in scenario_names():
            sc = load_scenario(n)
            if sc:
                out.append({'scenario': n, 'route': sc['route'], 'title': sc['title'], 'rings': sc['rings'], 'mac_attach': sc['mac_attach'],
                            'apps_run': sc['apps_run'], 'guests': sc.get('guests', False), 'hardware': sc.get('hardware', False),
                            'fixed_pieces': ', '.join(f['name'] for f in sc['fixed']), 'source': sc.get('source', '')})
        response.media = {'ok': True, 'default': default_scenario(), 'scenarios': out}

    def on_get_topology(self, request, response):
        view = request.params.get('view', 'os'); scn = request.params.get('scenario') or default_scenario(); mode = request.params.get('mode', 'today')
        try:
            response.media = {'ok': True, **build(view, scn, mode)}
        except ValueError as exc:
            self._bad(response, str(exc))

    def on_get_simulate(self, request, response):
        view = request.params.get('view', 'os'); scn = request.params.get('scenario') or default_scenario(); mode = request.params.get('mode', 'today')
        actor = request.params.get('actor') or ('prf-backend' if view != 'app' else 'visitor')
        try:
            response.media = simulate(view, scn, actor, mode)
        except ValueError as exc:
            self._bad(response, str(exc))

    def on_get_threats(self, request, response):
        scn = request.params.get('scenario') or default_scenario(); mode = request.params.get('mode', 'today')
        try:
            response.media = {'ok': True, **threats(scn, mode)}
        except ValueError as exc:
            self._bad(response, str(exc))

    def _upsert(self, class_name, cls, row):
        """Store a derived row the way the seed does (upsert by name); returns the object or None without a manager."""
        try:
            from polariApiServer.seed_upsert import seed_upsert
            return seed_upsert(self.manager, class_name, cls, row)
        except Exception:
            try:
                obj = cls(manager=self.manager, **row)
                return obj
            except Exception:
                return None

    def on_get_ssh(self, request, response):
        rows = ssh_rows(self.manager) if self.manager is not None else []
        from security.custom.security_ssh import level_rows, assurance_summary
        response.media = {'ok': True, **ssh_summary(rows), 'devices_detail': rows, 'assurance': assurance_summary(rows),
                          'levels_detail': level_rows(self.manager) if self.manager is not None else [],
                          'how': 'pol deploy inventory <node> --post <core url> refreshes a device; the audit\'s ssh ring scores it; '
                                 'assurance = secure | dev (declared, until) | unsecured — a device is assured only as one of the first two'}

    def on_get_inventory(self, request, response):
        tables = getattr(self.manager, 'objectTables', None) or {}
        rows = [{k: getattr(r, k, '') for k in ('device', 'role', 'os_release', 'kernel', 'docker_version', 'swarm', 'kvm', 'formats', 'debs', 'containers', 'stacks', 'checkouts', 'guests', 'rings_present', 'observed_at')}
                for r in (tables.get('DeviceInventory') or {}).values()]
        response.media = {'ok': True, 'devices': rows, 'how': 'pol deploy inventory <node> --post <core url>'}

    def on_post_inventory(self, request, response):
        try:
            body = request.media or {}
        except Exception:
            body = {}
        inv = body.get('inventory') or body
        device = body.get('device') or request.params.get('device') or ''
        if not device or 'ssh' not in inv:
            return self._bad(response, 'body: {device: <role name>, inventory: <os-security/inventory.sh JSON>}')
        from security.security_basis import DeviceInventory, SshCapability, SshPermissionLevel
        from security.custom.security_ssh import permission_levels
        r1 = inventory_row(device, inv); r2 = ssh_row_from_inventory(device, inv)
        o1 = self._upsert('DeviceInventory', DeviceInventory, r1); o2 = self._upsert('SshCapability', SshCapability, r2)
        lv = permission_levels(device, inv)
        stored_levels = sum(1 for row in lv if self._upsert('SshPermissionLevel', SshPermissionLevel, row))
        # the PermissionGroup rows (designed groups) learn their observed members per device
        from security.custom.security_ssh import permission_group_updates, merge_members
        from security.security_basis import PermissionGroup
        tables = getattr(self.manager, 'objectTables', None) or {}
        groups_touched = 0
        for gname, upd in permission_group_updates(device, inv).items():
            existing = next((r for r in (tables.get('PermissionGroup') or {}).values() if getattr(r, 'name', '') == gname), None)
            if existing is not None:
                existing.members = merge_members(getattr(existing, 'members', ''), device, upd['members']); existing.installed = 'yes'; groups_touched += 1
            elif gname.startswith('polari-'):
                if self._upsert('PermissionGroup', PermissionGroup, {'name': gname, 'purpose': 'observed on a device (not yet designed here)', 'verbs': '', 'sudoers_file': '', 'granted_by': 'observed', 'members': upd['members'], 'apps_needing': '', 'installed': 'yes'}):
                    groups_touched += 1
        response.media = {'ok': True, 'stored': bool(o1 and o2), 'device': device, 'role': r1['role'], 'formats': r1['formats'],
                          'ssh': {'verdict': r2['verdict'], 'vector': r2['vector'], 'assurance': r2['assurance'], 'reasons': r2['assurance_reasons'],
                                  'posture': r2['posture'], 'posture_until': r2['posture_until'], 'levels': r2['levels'], 'level_rows': stored_levels, 'groups_touched': groups_touched}}

    def on_get_events(self, request, response):
        from security.custom.security_observe import events, summary
        ev = events(self.manager)
        ctl = request.params.get('control')
        if ctl:
            ev = [e for e in ev if e['control'] == ctl]
        response.media = {'ok': True, 'summary': summary(self.manager), 'events': ev[:500],
                          'how': 'dev posture (POLARI_POSTURE=dev or /etc/polari/posture.json) = observe: every control evaluates, nothing observable is denied, each would-deny lands here'}

    def on_get_observations(self, request, response):
        """His ask 2026-09-15: in dev mode, which permission profiles and roles perform what actions — the primary
        route to working out app-level permission profiles. `derived` = one proposed AppPermissionProfile per role
        set, in the row's own shape, with the evidence; a suggestion, never applied here."""
        from security.custom.security_observe import observations, derive_profiles, summary
        obs = observations(self.manager)
        # §51: `groups` is a comma-joined SET on the row (a real login carries
        # default-roles-polari,journalist,…,roleplay:journalist), so exact
        # equality against the whole field could never match a filter naming
        # ONE group — ?groups=journalist returned 0 rows while the row plainly
        # contained it. Membership for `groups`; exact for the rest.
        gq = (request.params.get('groups') or '').strip()
        if gq:
            wanted = {g.strip() for g in gq.split(',') if g.strip()}
            obs = [o for o in obs
                   if wanted <= {g.strip() for g in str(o.get('groups') or '').split(',') if g.strip()}]
        for k in ('class_name', 'verb', 'verdict'):
            v = request.params.get(k)
            if v:
                obs = [o for o in obs if o.get(k) == v]
        s = summary(self.manager)
        response.media = {'ok': True, 'posture': s['posture'], 'recording': s['observe'], 'count': len(obs),
                          'by_verdict': {v: sum(int(o.get('count') or 0) for o in obs if o.get('verdict') == v) for v in ('granted-by-profile', 'admin', 'would-deny', 'unauthenticated', 'ungated')},
                          'observations': obs[:1000], 'derived': derive_profiles(self.manager),
                          'how': ('recorded only in dev posture, every CRUDE act, even with POLARI_APP_PERMISSIONS=off; derived = proposed AppPermissionProfile rows '
                                  '(kc_groups_json, verbs_json, extra_classes_json) — review, narrow, then create the row; nothing is applied automatically')}

    # ---- the recording knob + role-play (his asks 2026-09-16) --------------------------------------------------------
    @staticmethod
    def _body(request):
        try:
            return request.media or {}
        except Exception:
            return {}

    def _actor(self, request):
        ui = getattr(getattr(request, 'context', None), 'user_info', None)
        return ((ui.get('preferred_username') or ui.get('sub') or '') if isinstance(ui, dict) else '')

    def on_get_observe(self, request, response):
        from security.custom.security_observe import knob_state, recording_on, sessions, summary
        s = summary(self.manager)
        response.media = {'ok': True, 'posture': s['posture'], 'recording': recording_on(self.manager), 'knob': knob_state(), 'open_sessions': sessions(self.manager, active=True),
                          'how': 'POST {"recording": false} here turns the observation ledgers off on the fly (and true back on); recording never happens outside dev posture'}

    def on_post_observe(self, request, response):
        from security.custom.security_observe import set_recording, recording_on
        from security.custom.security_observe import set_roleplay_groups
        body = self._body(request)
        out = {}
        if 'roleplay_groups' in body:
            out['roleplay'] = set_roleplay_groups(body.get('roleplay_groups') or [], by=self._actor(request))
        if 'recording' in body:
            out.update(set_recording(bool(body['recording']), by=self._actor(request)))
        if not out:
            return self._bad(response, 'body: {"recording": true|false} and/or {"roleplay_groups": ["group", ...]}')
        response.media = {**out, 'ok': True, 'recording_now': recording_on(self.manager)}

    def on_post_observe_session(self, request, response):
        from security.custom.security_observe import start_session
        from security.custom.security_observe import can_roleplay
        body = self._body(request)
        ok, why = can_roleplay(getattr(getattr(request, 'context', None), 'user_info', None))
        if not ok:
            response.status = '403 Forbidden'; response.media = {'ok': False, 'refusal': why}; return
        r = start_session(self.manager, body.get('role', ''), actor=body.get('actor') or self._actor(request), note=body.get('note', ''))
        if not r.get('ok'):
            return self._bad(response, r.get('refusal', ''))
        response.media = r

    def on_delete_observe_session(self, request, response):
        from security.custom.security_observe import end_session
        response.media = end_session(self.manager, role=request.params.get('role'), name=request.params.get('name'))

    def on_post_observe_usage(self, request, response):
        from security.custom.security_observe import observe_usage, recording_on, USAGE_KINDS
        body = self._body(request)
        items = body.get('items') if isinstance(body.get('items'), list) else [body]
        if not recording_on(self.manager):
            return self._json_ok(response, {'ok': True, 'recorded': 0, 'note': 'not recording (production posture, or the knob is off)'})
        role = (body.get('role') or getattr(getattr(request, 'context', None), 'roleplay', '') or '')
        n = 0
        for it in items:
            if not isinstance(it, dict) or it.get('kind') not in USAGE_KINDS or not it.get('item'):
                continue
            if observe_usage(self.manager, it.get('role') or role, it['kind'], it['item'], app=it.get('app', ''), page=it.get('page', ''), detail=it.get('detail', ''), actor=self._actor(request)) is not None:
                n += 1
        response.media = {'ok': True, 'recorded': n, 'kinds': list(USAGE_KINDS)}

    @staticmethod
    def _json_ok(response, body):
        response.media = body

    def on_get_observe_roles(self, request, response):
        from security.custom.security_observe import prototypes, can_roleplay, roleplay_groups_allowed, sessions
        ui = getattr(getattr(request, 'context', None), 'user_info', None)
        ok, why = can_roleplay(ui)
        response.media = {'ok': True, 'roles': prototypes(self.manager, request.params.get('state')), 'can_roleplay': ok, 'why': why,
                          'roleplay_groups': roleplay_groups_allowed(), 'open_sessions': sessions(self.manager, active=True),
                          'how': 'POST {name, title, description} creates a prototype role; POST /api/security/observe/session {role} acts as it; the role-play permission = the KC groups in roleplay_groups (POST /api/security/observe {"roleplay_groups": [...]}); admins always may'}

    def on_post_observe_roles(self, request, response):
        from security.custom.security_observe import create_prototype, can_roleplay
        ui = getattr(getattr(request, 'context', None), 'user_info', None)
        ok, why = can_roleplay(ui)
        if not ok:
            return self._json(response, {'ok': False, 'refusal': why}, '403 Forbidden') if hasattr(self, '_json') else self._bad(response, why)
        body = self._body(request)
        r = create_prototype(self.manager, body.get('name', ''), title=body.get('title', ''), description=body.get('description', ''), by=self._actor(request))
        if not r.get('ok'):
            return self._bad(response, r.get('refusal', ''))
        response.media = r

    def on_post_observe_role(self, request, response, name):
        from security.custom.security_observe import mark_prototype
        body = self._body(request)
        r = mark_prototype(self.manager, name, body.get('state', ''), profile=body.get('profile', ''), verdict=body.get('verdict', ''))
        if not r.get('ok'):
            return self._bad(response, r.get('refusal', ''))
        response.media = r

    def on_get_observe_review(self, request, response):
        from security.custom.security_observe import review
        role = request.params.get('role', '')
        if not role:
            return self._bad(response, '?role=<the role-played group>')
        response.media = review(self.manager, role)

    def on_get_observe_verify(self, request, response):
        from security.custom.security_observe import verify
        role = request.params.get('role', '')
        if not role:
            return self._bad(response, '?role=<the role-played group>[&group=<the KC group it was concreted into>]')
        r = verify(self.manager, role, request.params.get('group'))
        if not r.get('ok'):
            return self._bad(response, r.get('refusal', ''))
        response.media = r

    def on_get_notices(self, request, response):
        response.media = notices(self.manager, do_probe=not request.get_param_as_bool('no_probe'))

    def on_get_ledger(self, request, response):
        applied = applied_for(self.manager); verdicts = verdicts_for(self.manager)
        rows = app_security_records(applied, verdicts)
        scn = request.params.get('scenario')
        if scn:
            rows = [r for r in rows if r['scenario'] == scn]
        response.media = {'ok': True, 'summary': ledger_summary(rows), 'applied_from': {k: v.get('_from', 'hand-kept table (no audit run posted yet)') for k, v in applied.items()},
                          'records': rows}

    def on_get_audit(self, request, response):
        runs = latest_runs(self.manager) if self.manager is not None else {}
        response.media = {'ok': True, 'latest': {k: {kk: vv for kk, vv in v.items() if kk != 'controls'} for k, v in runs.items()},
                          'applied': applied_for(self.manager), 'how': 'POST this endpoint with `pol security os audit --json --post <url>` (or pol deploy audit <node> --post <url>)'}

    def on_post_audit(self, request, response):
        try:
            payload = request.media or {}
        except Exception:
            payload = {}
        if not isinstance(payload, dict) or 'controls' not in payload:
            return self._bad(response, 'body must be the JSON of os-security/audit.sh --json (host, scenario, verdict, controls)')
        from security.security_basis import SecurityAuditRun
        row = run_row_from_audit(payload, source=request.remote_addr or '')
        obj = self._upsert('SecurityAuditRun', SecurityAuditRun, row)
        response.media = {'ok': True, 'stored': obj is not None, 'run': row['name'], 'applied_now': applied_for(self.manager).get(row['scenario'], {}),
                          'reading': f"{row['host']} / {row['scenario']}: {row['verdict']} ({row['pass_count']} pass, {row['fail_count']} fail) — the views now read this as today"}

    def on_post_propose(self, request, response):
        try:
            body = request.media or {}
        except Exception:
            body = {}
        app = body.get('app'); groups = body.get('groups')
        if not app or not isinstance(groups, list):
            return self._bad(response, 'body: {app, stanza?, groups: the groups array of allowed.py --json}')
        stanza = body.get('stanza')
        if stanza is None:
            try:
                from moduleService.manifests import manifest_path
                import json as _json
                stanza = _json.load(open(manifest_path(app), encoding='utf-8')).get('security')
            except Exception:
                stanza = {}
        prop = propose_from_groups(app, stanza, groups)
        from security.security_basis import SecurityProposal
        row = proposal_row(prop, harvest_source=body.get('source', ''))
        obj = self._upsert('SecurityProposal', SecurityProposal, row)
        response.media = {'ok': True, 'stored': obj is not None, **prop}

    def on_get_compare(self, request, response):
        view = request.params.get('view', 'os'); mode = request.params.get('mode', 'today')
        try:
            response.media = {'ok': True, **compare(view, mode)}
        except ValueError as exc:
            self._bad(response, str(exc))
