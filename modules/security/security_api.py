"""
@module security.security_api

/api/security            the taxonomy, the scenario in force here, the systems with provenance
/api/security/scenarios  every scenario (route, attach, rings, fixed pieces)
/api/security/topology   ?view=os|network|app|objects [&scenario=…] [&mode=stock|today|complain|enforce] — one view
/api/security/simulate   ?view=… &actor=… [&scenario=…] [&mode=…] — everything one actor can reach, hop by hop
                         (view=objects: actor is `this instance`, `class:<C>` or `profile:<AppPermissionProfile>`)
/api/security/compare    ?view=… [&mode=…] — the same view across every scenario, verdict per scenario
                         (view=objects: across every MODE instead — an object flow belongs to the instance, not
                          to the machine layout a scenario describes)
/api/security/objects/drift   ct-5, design §7 — declared − observed and observed − declared, per app, with the
                              coverage block: an untraced class reads NOT TRACED, never "nothing flows"
/api/security/objects/flows   ct-5 — both halves as lists: every DECLARED flow (the modules' manifest `app.flows`
                              stanzas + the CONFIRMED traffic policy rows) and every OBSERVED one (the causal map)
/api/security/ssh        ssh capabilities across Polari devices (exposed / keys-only / closed, who reaches whom) — the isle topology shows it
/api/security/inventory  GET each device's installed footprint (deb / images / stacks / checkouts / guests / units); POST inventory.sh JSON
/api/security/notices    what a user should be told now: expired / expiring certificates (live TLS probe of this instance's hosts),
                         auto-renew absent (from the last audit run); the frontends' system-notice bar polls it
/api/security/ledger     [?scenario=…] — AppSecurityRecord per app: steps complete / total, the blocking step (the per-app ledger)
/api/security/audit      GET the latest posted audit runs + what 'today' reads from them; POST an audit.sh --json payload
/api/security/propose    POST {app, groups} (allowed.py --json groups) → a SecurityProposal: the stanza change the harvest asks for
/api/security/threats    [?scenario=…] [&mode=…] — the threat simulations: each threat's path through the systems, the policy that
                         blocked it, and the counterexample (the actor/group/permission that legitimately reaches the same target)
/api/security/observe/trace    GET the armed causal-trace target (counters + coverage); POST {class_name, verbs?, max_*?, window_seconds?}
                               arms ONE class (dev posture only, a second arm is refused naming the active one); DELETE disarms it
/api/security/observe/closure  ct-4, design §6 — what a grant REALLY reaches, walked from the causal map:
                               ?profile=<name> start = that AppPermissionProfile's explicit class × verb grants;
                                               the answer carries `explicit`, `reachable` and `implicit` = reachable − explicit
                               ?event=<trigger name | topic:Class> start = one event: the solution it runs, as whom, and onward
                               ?role=<role>    start = the role-play recording's observed endpoints and objects
                               (no parameter = the ONE armed target's class). Every item carries its `origin`
                               (observed | closure | declared) and its evidence, and the answer carries the
                               coverage block + `not_traced`: a class nobody armed answers NOT TRACED, never "nothing".
/api/security/trace/edges      [?target=|cause=|effect=|means=] Ledger A — the causal MAP: cause → effect by means, counted, class-level only
/api/security/trace/journal    [?trace_id=|class=] Ledger B — the effect JOURNAL: which instances a traced chain wrote, cleared on the next arm
/api/security/traffic          ct-9, design §5a — the traffic policies, CLOSED BY DEFAULT: `OutboundPolicy`
                               (what may leave, per system × wire) and `InboundPolicy` (who may call), each
                               suggested | confirmed | denied, plus the `suggestions` derived from dev-posture
                               monitoring and the gate mode that decides what they mean. Signed in to read.
/api/security/traffic/outbound/{name}   POST {"decision": "confirmed"|"denied"} — a PERSON rules (admins only;
/api/security/traffic/inbound/{name}    the `sub` alone is stored; nothing confirms itself, 401 without one)
/api/security/traffic/outbound          POST {"name": …, "decision": …} — the SAME ruling with the name in the
/api/security/traffic/inbound           BODY, for the names a URL path cannot carry: an inbound origin name
                                        holds `://`, and falcon decodes before routing, so the `/{name}` form
                                        answers 404 for it however it is encoded (§66a, found live 2026-09-19)
/api/security/traffic/declared ct-9 — the confirmed rows as DECLARED flows for the object topology (§7)
/api/security/roles/claimable  GET the roles THIS caller may take for themselves (a role = a Keycloak group) + the account console URL
/api/security/roles/claim      POST {role} join that group; DELETE ?role= leave it — self-service, never an admin role (§17b D17-5)
/api/security/people/{sub}     GET a Keycloak subject id → {display_name, username}, resolved LIVE from Keycloak and never stored.
                               THE ONE DOOR through the PII boundary (his rule D18-1, 2026-09-18: Polari rows key a person by
                               `sub` alone). Gated: an admin, or your own sub, or a group named in the `people_viewers` knob.
/api/security/people           POST {subs: [...]} (max 200) → {ok, people: {sub: display_name|null}, denied, how} — the same
                               door and the same gate, applied per sub, so a table of actors resolves in ONE call. Names are
                               held in memory for POLARI_PEOPLE_CACHE_SECONDS (300 s) and nowhere else; 60 calls/min/caller.
The scenario defaults to the one this deployment is (POLARI_DEPLOY_ROUTE: isle → isle, swarm → lean/full by
profile, else dev). Pure reads over security_topology; nothing here changes the machine.
"""
import os

from objectTreeDecorators import treeObject, treeObjectInit

from security.custom.security_facts import SYSTEMS, load_scenario, scenario_names
from security.custom.security_topology import MODES, VIEWS, build, compare, simulate  # noqa: F401 (VIEWS: the module's stated vocabulary)
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


#: the actor `?view=` simulates when none is asked for. ct-5's `objects` view has no people on it — its nodes are
#: classes and systems — so its default is THIS INSTANCE: everything that leaves, whoever asked for it.
DEFAULT_ACTOR = {'os': 'prf-backend', 'network': 'internet', 'app': 'visitor', 'objects': 'this instance'}

#: ct-4: the reading every closure answer carries. A module constant, not a class attribute — the tree's
#: identifier scan walks a treeObject's attributes and logs anything it cannot type as an invalid instance value.
HOW_CLOSURE = ('every item carries its ORIGIN (declared = the profile says so; observed = the recording saw it; '
               'closure = the map reached it) and its evidence (counts, first/last seen, the sample trace id to '
               'look the instances up with in the journal). `not_traced` names the classes in this answer that '
               'have never been a TraceTarget — for those the honest answer is NOT TRACED, which is not the same '
               'as nothing reaching them. Nothing is enforced or widened here: a person confirms.')


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
            add('/api/security/objects/drift', self, suffix='objects_drift')    # ct-5: declared − observed and observed − declared, per app, with coverage
            add('/api/security/objects/flows', self, suffix='objects_flows')    # ct-5: both halves as lists — the raw material behind the drift
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
            add('/api/security/observe/session', self, suffix='observe_session')    # POST {role, note, task} start role-playing (ct-7: `task` states the job, and posting again changes it mid-session); DELETE ?role= (or ?name=) end it
            add('/api/security/observe/usage', self, suffix='observe_usage')        # POST {role, kind: app|page|component|action|object, item, app, page, detail} from the frontend
            add('/api/security/observe/review', self, suffix='observe_review')      # GET ?role= everything the role used + the proposed profile (the handoff)
            add('/api/security/observe/verify', self, suffix='observe_verify')      # GET ?role=&group= replay the recording against the enforced profiles
            add('/api/security/observe/trace', self, suffix='observe_trace')        # ct-1: GET the armed trace target + counters + coverage; POST {class_name,…} arm ONE class; DELETE disarm
            add('/api/security/observe/closure', self, suffix='observe_closure')    # ct-4: GET ?profile= | ?event= | ?role= | ?class= — what a grant REALLY reaches, with the evidence and the coverage
            add('/api/security/trace/edges', self, suffix='trace_edges')            # ct-1: Ledger A, the causal MAP — cause → effect by means, counted [?target=|cause=|effect=|means=]
            add('/api/security/trace/journal', self, suffix='trace_journal')        # ct-1: Ledger B, the effect JOURNAL — the instances a traced chain wrote [?trace_id=|class=]
            add('/api/security/observe/roles', self, suffix='observe_roles')        # GET the prototype roles + whether the caller may role-play; POST {name, title, description} a new prototype
            add('/api/security/observe/roles/{name}', self, suffix='observe_role')  # POST {state, profile, verdict} mark prototype → concreted → enforced; {self_claimable} admin-only
            add('/api/security/roles/claimable', self, suffix='roles_claimable')    # GET the roles THIS caller may take for themselves (his ask 2026-09-18)
            add('/api/security/roles/claim', self, suffix='roles_claim')            # POST {role} join the KC group; DELETE ?role= leave it
            add('/api/security/people', self, suffix='people_batch')                # the SAME door, for a page: POST {subs: [...]} (max 200), the gate applied per sub
            add('/api/security/people/{sub}', self, suffix='people')                # THE ONE GATED DOOR: a Keycloak `sub` → a display name, resolved LIVE, never stored (D18-1)
            add('/api/security/traffic', self, suffix='traffic')                    # ct-9: the traffic policies + the suggestions derived from dev monitoring + the mode
            add('/api/security/traffic/declared', self, suffix='traffic_declared')  # ct-9: the CONFIRMED rows as declared flows (the §7 topology's declared edges)
            add('/api/security/traffic/outbound', self, suffix='traffic_outbound_body')    # ct-9 §66a: POST {name, decision} — the door for a name a URL cannot carry
            add('/api/security/traffic/inbound', self, suffix='traffic_inbound_body')      # ct-9 §66a: the same, for who may call this instance
            add('/api/security/traffic/outbound/{name}', self, suffix='traffic_outbound')  # ct-9: POST {decision: confirmed|denied} — a PERSON rules (admins only)
            add('/api/security/traffic/inbound/{name}', self, suffix='traffic_inbound')    # ct-9: the same, for who may call this instance
            add('/api/security/owned', self, suffix='owned')                        # op-0: the classes whose OWNER defines the rules, and their policies
            add('/api/security/owned/{class_name}', self, suffix='owned_class')     # GET one policy; POST (ADMIN_ROLES) set or replace it; DELETE (ADMIN_ROLES) remove it — refused while a manifest declares the class
            add('/api/security/owned/{class_name}/{object_id}', self, suffix='owned_instance')   # GET the CALLER's verdict on one instance (+ the Sharing tab's answer)
            add('/api/security/owned/{class_name}/{object_id}/grants', self, suffix='owned_grants')      # op-1: GET the instance's grants + bounds; POST one; DELETE one (the OWNER, or an admin)
            add('/api/security/owned/{class_name}/{object_id}/transfer', self, suffix='owned_transfer')  # op-2: POST {"to": "<sub>"} hand the row to somebody else, inside the policy's transfer mode

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
                ('app', 'who gets access to what, through which means'),
                ('objects', 'where do the ROWS go — which classes cross to which system, declared vs observed'))],
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
            # ct-5: the `objects` view is built from THIS instance (its manifests, its confirmed traffic
            # policies, its causal map), so it needs the manager; the three scenario views ignore it.
            response.media = {'ok': True, **build(view, scn, mode, manager=self.manager)}
        except ValueError as exc:
            self._bad(response, str(exc))

    def on_get_simulate(self, request, response):
        view = request.params.get('view', 'os'); scn = request.params.get('scenario') or default_scenario(); mode = request.params.get('mode', 'today')
        actor = request.params.get('actor') or DEFAULT_ACTOR.get(view, 'prf-backend')
        try:
            response.media = simulate(view, scn, actor, mode, manager=self.manager)
        except ValueError as exc:
            self._bad(response, str(exc))

    def on_get_threats(self, request, response):
        scn = request.params.get('scenario') or default_scenario(); mode = request.params.get('mode', 'today')
        try:
            response.media = {'ok': True, **threats(scn, mode)}
        except ValueError as exc:
            self._bad(response, str(exc))

    def _upsert(self, class_name, cls, row):
        """Converge ONE derived row by name the way the seed does (`moduleService.seed_upsert`); returns the live
        object, or None without a manager.

        §71 review: this used to import a `polariApiServer.seed_upsert` that never existed, so every call fell to
        the except branch and CONSTRUCTED a new row — a duplicate per posted audit / inventory / ssh row instead of
        a convergence. The upsert helper returns a report, not the row, so the live row is looked up by name after
        it; a class with no table yet is created once."""
        if self.manager is None:
            return None
        try:
            from moduleService.seed_upsert import upsert_seed_rows
            upsert_seed_rows(self.manager, class_name, cls, [row], tag='SecurityPost')
        except Exception:
            pass
        try:
            for obj in (self.manager.objectTables.get(class_name, {}) or {}).values():
                if getattr(obj, 'name', None) == row.get('name'):
                    return obj
        except Exception:
            pass
        try:
            return cls(manager=self.manager, **row)
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

    def on_get_observe(self, request, response):
        from security.custom.security_observe import knob_state, recording_on, sessions, summary, roleplay_groups_allowed, claimable_groups, claim_denied_roles, people_viewers
        s = summary(self.manager)
        response.media = {'ok': True, 'posture': s['posture'], 'recording': recording_on(self.manager), 'knob': knob_state(), 'open_sessions': sessions(self.manager, active=True),
                          'roleplay_groups': roleplay_groups_allowed(), 'claimable_groups': claimable_groups(), 'claim_denied': claim_denied_roles(),
                          'people_viewers': people_viewers(),
                          'how': 'POST {"recording": false} here turns the observation ledgers off on the fly (and true back on); recording never happens outside dev posture. '
                                 '{"claimable_groups": [...]} names KC groups anyone signed in may claim at /api/security/roles/claim; '
                                 '{"people_viewers": [...]} names KC groups that may resolve any `sub` to a name at /api/security/people/{sub}'}

    def on_post_observe(self, request, response):
        from security.custom.security_observe import set_recording, recording_on
        from security.custom.security_observe import set_roleplay_groups, set_claimable_groups, set_people_viewers
        body = self._body(request)
        out = {}
        if 'people_viewers' in body:
            # the PII boundary's allow-list (D18-1): KC groups whose members may resolve ANY sub to a name
            out['people_viewers'] = set_people_viewers(body.get('people_viewers') or [], by=self._sub(request))
        if 'roleplay_groups' in body:
            out['roleplay'] = set_roleplay_groups(body.get('roleplay_groups') or [], by=self._sub(request))
        if 'claimable_groups' in body:
            # the knob beside roleplay_groups: KC groups anyone signed in may take for themselves, in ANY posture
            out['claimable'] = set_claimable_groups(body.get('claimable_groups') or [], by=self._sub(request))
        if 'recording' in body:
            out.update(set_recording(bool(body['recording']), by=self._sub(request)))
        if not out:
            return self._bad(response, 'body: {"recording": true|false} and/or {"roleplay_groups": [...]} and/or {"claimable_groups": [...]} and/or {"people_viewers": [...]}')
        response.media = {**out, 'ok': True, 'recording_now': recording_on(self.manager)}

    def on_post_observe_session(self, request, response):
        from security.custom.security_observe import start_session
        from security.custom.security_observe import can_roleplay
        body = self._body(request)
        ok, why = can_roleplay(getattr(getattr(request, 'context', None), 'user_info', None))
        if not ok:
            response.status = '403 Forbidden'; response.media = {'ok': False, 'refusal': why}; return
        # D18-1: the session's actor is the CALLER'S OWN Keycloak `sub`, never a name and never something the body
        # supplied — a body-supplied `actor` used to be able to write any string (a username) into the ledger.
        # ct-7 (design §8): `task` is the free-text job the role-player states ("publish an article"). Posting
        # here again with the same role and a different task CHANGES it mid-session — the same door, as designed.
        r = start_session(self.manager, body.get('role', ''), actor=self._sub(request), note=body.get('note', ''),
                          task=body.get('task', ''))
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
            if observe_usage(self.manager, it.get('role') or role, it['kind'], it['item'], app=it.get('app', ''), page=it.get('page', ''), detail=it.get('detail', ''), actor=self._sub(request)) is not None:
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
        r = create_prototype(self.manager, body.get('name', ''), title=body.get('title', ''), description=body.get('description', ''), by=self._sub(request))
        if not r.get('ok'):
            return self._bad(response, r.get('refusal', ''))
        response.media = r

    def on_post_observe_role(self, request, response, name):
        """{state, profile, verdict} moves the prototype along its ladder (as before).
        {self_claimable: true|false} decides whether anyone signed in may take the role for themselves — that one is
        ADMIN-ONLY: letting a self-claimed role widen its own claimability would close the loop on itself."""
        from security.custom.security_observe import mark_prototype
        body = self._body(request)
        sc = body.get('self_claimable', None)
        if sc is not None:
            from security.custom.security_claims import is_admin
            ui = self._user_info(request)
            if not is_admin(ui):
                return self._refuse(response, '403 Forbidden',
                                    'only an administrator may change whether a role is self-claimable '
                                    '(ADMIN_ROLES: admin, polari-admin)')
            sc = bool(sc)
        r = mark_prototype(self.manager, name, body.get('state', ''), profile=body.get('profile', ''), verdict=body.get('verdict', ''),
                           self_claimable=sc, by=self._sub(request))
        if not r.get('ok'):
            return self._bad(response, r.get('refusal', ''))
        response.media = r

    # ---- SELF-CLAIMABLE ROLES (his words 2026-09-18) -------------------------------------------------------------
    # "It should not be the case all roles can be taken by anyone, but self-proclaimable roles should be a thing,
    # especially in dev mode." A role is a Keycloak GROUP; claiming one puts the caller's `sub` into it through the
    # polari-backend service account. The POLICY lives in security.custom.security_claims, the mechanism in kc_admin.

    def _user_info(self, request):
        return getattr(getattr(request, 'context', None), 'user_info', None)

    def _sub(self, request):
        """The caller's opaque Keycloak id. The ONLY identifier this arc writes into a Polari row, event or knob —
        his PII rule (2026-09-18): Keycloak exists to keep names and e-mails out of Polari."""
        ui = self._user_info(request)
        return str(ui.get('sub') or '') if isinstance(ui, dict) else ''

    @staticmethod
    def _refuse(response, status, why, **extra):
        response.status = status
        response.media = {'ok': False, 'refusal': why, **extra}

    def on_get_roles_claimable(self, request, response):
        from security.custom.security_claims import claimable_roles, caller, how
        from security.custom.kc_admin import account_url, configured
        from moduleService import posture as _posture
        ui = self._user_info(request)
        # PII rule (his, 2026-09-18): Polari never handles the person's name here — the answer echoes the caller's
        # own opaque Keycloak `sub` and nothing else. The browser already has the display name in its own token.
        sub, _username, groups = caller(ui)
        roles = claimable_roles(self.manager, ui)
        kc_ok, kc_why = configured()
        response.media = {'ok': True, 'posture': _posture.posture(), 'authenticated': bool(sub), 'sub': sub,
                          'roles': roles, 'held': sorted(r['role'] for r in roles if r['held']),
                          'groups': sorted(groups), 'account_url': account_url(),
                          'keycloak': {'ready': kc_ok, 'why': kc_why},
                          'how': how(self.manager, ui)}

    def on_post_roles_claim(self, request, response):
        from security.custom.security_claims import claim, caller
        ui = self._user_info(request)
        sub, _u, _g = caller(ui)
        if not sub:
            return self._refuse(response, '401 Unauthorized',
                                'sign in first: a role is claimed for a Keycloak account, and this request carries none')
        role = (self._body(request).get('role') or request.params.get('role') or '')
        if not role:
            return self._bad(response, 'body: {"role": "<the role you want>"} — GET /api/security/roles/claimable lists them')
        r = claim(self.manager, ui, role)
        if not r.get('ok'):
            return self._refuse(response, self._status_of(r), r.get('refusal', ''), role=role)
        response.media = r

    def on_delete_roles_claim(self, request, response):
        from security.custom.security_claims import release, caller
        ui = self._user_info(request)
        sub, _u, _g = caller(ui)
        if not sub:
            return self._refuse(response, '401 Unauthorized',
                                'sign in first: a role is released from a Keycloak account, and this request carries none')
        role = request.params.get('role') or (self._body(request).get('role') or '')
        if not role:
            return self._bad(response, '?role=<the role you want to give up>')
        r = release(self.manager, ui, role)
        if not r.get('ok'):
            return self._refuse(response, self._status_of(r), r.get('refusal', ''), role=role)
        response.media = r

    @staticmethod
    def _status_of(result):
        return {401: '401 Unauthorized', 403: '403 Forbidden', 502: '502 Bad Gateway',
                503: '503 Service Unavailable'}.get(int(result.get('status') or 403), '403 Forbidden')

    # ---- THE PII BOUNDARY'S ONE DOOR (his rule D18-1, 2026-09-18) -------------------------------------------------
    # Polari rows key a person by their opaque Keycloak `sub`, never by a name. A page that must show a human-
    # readable name asks HERE, at render time, and the answer is never written back into the tree.

    def _may_see_people(self, request, sub):
        """(allowed, why) — admin, or asking about your own sub, or a member of a `people_viewers` group."""
        from security.custom.security_claims import is_admin, caller
        from security.custom.security_observe import people_viewers
        ui = self._user_info(request)
        caller_sub, _username, groups = caller(ui)
        if not caller_sub:
            return False, 'sign in first: resolving a Keycloak subject id to a name needs an identity of your own'
        if caller_sub == str(sub or ''):
            return True, 'your own account'
        if is_admin(ui):
            return True, 'administrator'
        viewers = people_viewers() or []
        hit = sorted(groups & set(viewers))
        if hit:
            return True, f'granted by group(s) {", ".join(hit)}'
        return False, ('names are behind the PII boundary: Polari stores only the opaque Keycloak subject id. You may '
                       'resolve your own, an administrator may resolve any, and so may a member of a group named in '
                       'the people_viewers knob (POST /api/security/observe {"people_viewers": [...]}). '
                       f'You are in {sorted(groups) or "no group"}.')

    def on_get_people(self, request, response, sub):
        """GET /api/security/people/{sub} → {ok, sub, display_name, username}. Resolved LIVE from Keycloak through
        the polari-backend service account (view-users), and stored NOWHERE."""
        from security.custom import kc_admin
        allowed, why = self._may_see_people(request, sub)
        if not allowed:
            status = '401 Unauthorized' if 'sign in first' in why else '403 Forbidden'
            return self._refuse(response, status, why, sub=str(sub or ''))
        ok, kc_why = kc_admin.configured()
        if not ok:
            return self._refuse(response, '503 Service Unavailable', f'no identity provider: {kc_why}', sub=str(sub or ''),
                                how='names live in Keycloak; without a Keycloak credential this instance cannot resolve one, '
                                    'and it will not keep a copy to fall back on')
        r = kc_admin.get_user(sub)
        if not r.get('ok'):
            return self._refuse(response, '404 Not Found' if int(r.get('status') or 0) == 404 else '502 Bad Gateway',
                                r.get('refusal', 'could not resolve that subject id'), sub=str(sub or ''))
        user = r['user']
        response.media = {'ok': True, 'sub': str(sub or ''), 'display_name': kc_admin.display_name(user),
                          'username': user.get('username') or '', 'why': why,
                          'how': 'resolved live from Keycloak for this request only — Polari rows key a person by `sub` '
                                 'alone (D18-1) and never cache a name'}

    def _people_gate(self, request):
        """(caller_sub, may_resolve_anyone, why) — the gate computed ONCE for a batch, exactly the rule the
        single door applies per call: your own sub always, an admin or a `people_viewers` member for anyone."""
        from security.custom.security_claims import is_admin, caller
        from security.custom.security_observe import people_viewers
        ui = self._user_info(request)
        caller_sub, _username, groups = caller(ui)
        if not caller_sub:
            return '', False, ''
        if is_admin(ui):
            return caller_sub, True, 'administrator'
        hit = sorted(groups & set(people_viewers() or []))
        if hit:
            return caller_sub, True, f'granted by group(s) {", ".join(hit)}'
        return caller_sub, False, 'your own account'

    def on_post_people_batch(self, request, response):
        """POST /api/security/people {subs: [...]} → {ok, people: {sub: display_name|null}, denied, how}.

        One call for a whole table of actors. The gate is per sub (a stranger's sub lands in `denied`, never in
        `people`), an unresolvable sub answers null rather than failing the batch, and the names live only in
        security_people's in-memory cache — see that module: it is the one place a name exists in this backend and
        it dies with the process."""
        from security.custom import kc_admin
        from security.custom import security_people as P
        body = self._body(request)
        subs = body.get('subs')
        if not isinstance(subs, list) or not subs:
            return self._bad(response, 'body: {"subs": ["<keycloak sub>", …]} — at most %d per call' % P.MAX_SUBS)
        if len(subs) > P.MAX_SUBS:
            return self._bad(response, 'too many subject ids in one call: %d asked, %d is the most this door will '
                                       'resolve at once — page the table.' % (len(subs), P.MAX_SUBS))
        caller_sub, may_all, why = self._people_gate(request)
        if not caller_sub:
            return self._refuse(response, '401 Unauthorized',
                                'sign in first: resolving Keycloak subject ids to names needs an identity of your own')
        ok_rate, retry = P.rate_ok(caller_sub)
        if not ok_rate:
            response.status = '429 Too Many Requests'
            response.set_header('Retry-After', str(retry))
            response.media = {'ok': False, 'refusal': 'too many name lookups: this door answers %d calls a minute per '
                                                      'caller, and you have used them. Try again in %d seconds — one '
                                                      'call may carry up to %d subject ids, so batch them.'
                                                      % (P.RATE_LIMIT_CALLS, retry, P.MAX_SUBS),
                              'retry_after': retry}
            return
        wanted, denied = [], []
        for s in subs:
            s = str(s or '')
            if not s or s in wanted or s in denied:
                continue
            (wanted if (may_all or s == caller_sub) else denied).append(s)
        if wanted:
            kc_ok, kc_why = kc_admin.configured()
            if not kc_ok:
                return self._refuse(response, '503 Service Unavailable', f'no identity provider: {kc_why}',
                                    denied=denied,
                                    how='names live in Keycloak; without a Keycloak credential this instance cannot '
                                        'resolve one, and it keeps no copy to fall back on')
        people, stats = P.resolve(wanted)
        response.media = {
            'ok': True, 'people': people, 'denied': denied, 'why': why,
            'asked': len(subs), 'resolved': sum(1 for v in people.values() if v), 'cache': P.cache_state(),
            'keycloak_calls': stats['calls'],
            'how': ('the same gate as GET /api/security/people/{sub}, applied per subject id: your own always, any '
                    'other only for an administrator or a member of a group named in the people_viewers knob. A sub '
                    'this realm does not know answers null. Names are held in memory for %d s and written to no row, '
                    'no log and no disk (D18-1).' % P.cache_seconds()),
        }

    # ---- CAUSAL TRACING (ct-1, his ask 2026-09-18) ----------------------------------------------------------
    # "trace different events and functions … and track the kinds of changes that occur due to those events."
    # ONE class at a time, dev posture only, budgets that disarm themselves and say so. Arming is a
    # permissions-administration act (ADMIN_ROLES, or a holder of the role-play permission); reading the status
    # is not, so anyone signed in can see whether their instance is recording and what it has cost.

    def on_get_observe_trace(self, request, response):
        from security.custom.security_trace import status
        if not self._sub(request):
            return self._refuse(response, '401 Unauthorized',
                                'sign in first: anyone with an account may see what this instance is recording, '
                                'but an anonymous caller has no business asking')
        response.media = status(self.manager)

    def on_post_observe_trace(self, request, response):
        from security.custom.security_observe import can_roleplay
        from security.custom.security_trace import arm
        ui = self._user_info(request)
        ok, why = can_roleplay(ui)
        if not ok:
            return self._refuse(response, '403 Forbidden', why)
        body = self._body(request)
        r = arm(self.manager, body.get('class_name') or body.get('class') or '',
                verbs=body.get('verbs'), max_traces=body.get('max_traces'), max_edges=body.get('max_edges'),
                max_journal_rows=body.get('max_journal_rows'), max_depth=body.get('max_depth'),
                window_seconds=body.get('window_seconds'), user_info=ui)
        if not r.get('ok'):
            return self._refuse(response, '409 Conflict' if r.get('active') else '400 Bad Request',
                                r.get('refusal', ''), **{k: v for k, v in r.items() if k == 'active'})
        response.media = r

    def on_delete_observe_trace(self, request, response):
        from security.custom.security_observe import can_roleplay
        from security.custom.security_trace import disarm
        ui = self._user_info(request)
        ok, why = can_roleplay(ui)
        if not ok:
            return self._refuse(response, '403 Forbidden', why)
        response.media = disarm(self.manager, because='manual', user_info=ui)

    def on_get_trace_edges(self, request, response):
        from security.custom.security_trace import coverage, edges, status
        rows = edges(self.manager, target=request.params.get('target', ''), cause=request.params.get('cause', ''),
                     effect=request.params.get('effect', ''), means=request.params.get('means', ''))
        st = status(self.manager)
        response.media = {'ok': True, 'count': len(rows), 'edges': rows[:1000], 'coverage': coverage(self.manager),
                          'armed': st['armed'], 'target': st['target'],
                          'how': ('one counted row per cause → effect by means; an instance id never appears here. '
                                  'A class with no coverage row has NOT been traced — that is not the same as '
                                  'nothing reaching it.')}

    def on_get_trace_journal(self, request, response):
        from security.custom.security_trace import journal, status
        rows = journal(self.manager, trace_id=request.params.get('trace_id', ''),
                       class_name=request.params.get('class', '') or request.params.get('class_name', ''))
        st = status(self.manager)
        response.media = {'ok': True, 'count': len(rows), 'journal': rows[:1000], 'target': st['target'],
                          'how': ('the instance-level evidence behind a map edge, for the CURRENT question: it is '
                                  'cleared when the next target is armed. A class whose OwnedClassPolicy is '
                                  'anonymised keeps its class and verb here and drops both the actor and the '
                                  'object id.')}

    # ---- THE CLOSURE (ct-4, design §6) -----------------------------------------------------------------
    # "This way we can see what implicit permissions we may be granting by granting event permissions."
    # The map (ct-1/ct-2) holds every crossing that was recorded; this door reads it from one of three start
    # sets and says what is really being granted. DISCLOSURE ONLY: nothing here writes a row, widens a
    # profile or flips a mode — a person confirms, and ct-8 records the decision.

    def on_get_observe_closure(self, request, response):
        from security.custom import security_closure as C
        if not self._sub(request):
            return self._refuse(response, '401 Unauthorized',
                                'sign in first: the closure says what a grant really reaches, which is a '
                                'permissions-administration reading')
        params = request.params
        depth = params.get('max_depth') or params.get('depth')
        try:
            depth = int(depth) if depth not in (None, '') else None
        except (TypeError, ValueError):
            return self._bad(response, 'max_depth must be a whole number of hops')

        profile = params.get('profile')
        event = params.get('event')
        role_name = params.get('role')
        class_name = params.get('class') or params.get('class_name')
        if profile:
            start = C.profile_start(self.manager, profile)
            if not start.get('ok'):
                return self._refuse(response, '404 Not Found', start.get('refusal', ''))
            result = C.closure(self.manager, start['nodes'], max_depth=depth)
            C.mark_origin(result, start['nodes'], 'declared')
            explicit = {(c, v) for c, v in start['explicit']}
            reachable = sorted({(o['class'], o['verb']) for o in result['objects'] if o['class'] and o['verb']})
            implicit = [{'class': c, 'verb': v,
                         'definer_only': next((o['definer_only'] for o in result['objects']
                                               if o['class'] == c and o['verb'] == v), False)}
                        for c, v in reachable if (c, v) not in explicit]
            response.media = {
                'ok': True, 'asked': {'profile': profile}, 'profile': start,
                'explicit': [{'class': c, 'verb': v} for c, v in start['explicit']],
                'reachable': [{'class': c, 'verb': v} for c, v in reachable],
                'implicit': implicit, 'closure': result,
                'reading': ('publishing %s grants %d class × verb pair(s) explicitly and reaches %d more '
                            'through what those acts cause — that difference IS the implicit permission. %s'
                            % (profile, len(start['explicit']), len(implicit),
                               ('%d class(es) in this answer have never been traced (%s).'
                                % (len(result['not_traced']), ', '.join(result['not_traced']))
                                if result['not_traced'] else 'Every class in this answer has been traced.'))),
                'how': HOW_CLOSURE}
            return
        if event:
            node = C.event_start(event)
            result = C.closure(self.manager, [node], max_depth=depth)
            solutions = [{'name': s['name'], 'run_as': s['run_as'], 'origin': s['origin'],
                          'definer_only': s['definer_only'], 'count': s['evidence']['count']}
                         for s in result['solutions']]
            response.media = {
                'ok': True, 'asked': {'event': event}, 'start': node, 'closure': result,
                'solutions': solutions,
                'reading': ('granting %s runs %s and reaches %d class × verb pair(s). %s'
                            % (node,
                               ', '.join('%s (as %s)' % (s['name'], s['run_as']) for s in solutions)
                               or 'no solution the map has seen',
                               result['counts']['objects'],
                               ('%d of them only through a trigger running as DEFINER — somebody else\'s '
                                'authority.' % result['counts']['definer_only'])
                               if result['counts']['definer_only'] else
                               'None of them is reached only through a definer-run trigger.')),
                'how': HOW_CLOSURE}
            return
        if role_name:
            result = C.role_closure(self.manager, role_name, max_depth=depth)
            response.media = {'ok': True, 'asked': {'role': role_name}, 'closure': result,
                              'reading': result.get('reading', ''), 'how': HOW_CLOSURE}
            return
        # No start asked for: the page's default — the ONE armed target's class. `?class=` asks for any class,
        # armed or not (an unarmed one answers honestly: its coverage row is missing and `not_traced` says so).
        from security.custom.security_trace import TRACE_VERBS, coverage
        if class_name:
            subject = class_name
            nodes = ['object:%s:%s' % (class_name, v) for v in TRACE_VERBS]
        else:
            subject, nodes = C.target_start(self.manager)
        if not nodes:
            return self._json_ok(response, {
                'ok': True, 'asked': {}, 'armed': '', 'closure': None, 'coverage': coverage(self.manager),
                'objects': [], 'events': [], 'solutions': [], 'flows': [],
                'not_traced': [], 'not_traced_detail': [],
                'reading': ('nothing is armed and no start was asked for. Arm one class '
                            '(POST /api/security/observe/trace {"class_name": "<Class>"}), or ask for a '
                            '?profile=, ?event=, ?role= or ?class=.'),
                'how': HOW_CLOSURE})
        result = C.closure(self.manager, nodes, max_depth=depth)
        response.media = {'ok': True, 'asked': {'class': subject}, 'armed': subject, 'closure': result,
                          'objects': result['objects'], 'events': result['events'],
                          'solutions': result['solutions'],
                          'flows': result['peers'] + result['external'],
                          'not_traced': result['not_traced'],
                          'not_traced_detail': [{'class_name': c,
                                                 'reading': 'never armed as a TraceTarget — NOT TRACED, which '
                                                            'is not the same as nothing reaching it'}
                                                for c in result['not_traced']],
                          'reading': C.reading(result, 'everything %s reaches, from the map as it stands'
                                               % subject),
                          'how': HOW_CLOSURE}

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

    # ---- OWNER-DEFINED PERMISSIONS (op-0, his ask 2026-09-18) ------------------------------------------------
    # "Owner defined permissions would be something we typically want specifically enabled per object though,
    # not something we enable by default." So: nothing is owned until a policy row here says so, and the
    # verdict door explains, per instance, what the caller may do and which fields they would see.

    # ---- THE TRAFFIC POLICIES (ct-9, design §5a) ---------------------------------------------------------
    # "Outbound guard should be tracked in dev as well, and it should be closed by default; we should suggest
    # outbound and inbounds based on our monitoring of traffic in and out of polari" (2026-09-18). Reading is
    # for anyone signed in; RULING is an administrator's act and stores their `sub` alone — nothing confirms
    # itself, and a `suggested` row is a proposal, never a grant.

    def on_get_traffic(self, request, response):
        from security.custom.security_traffic import summary
        if not self._sub(request):
            return self._refuse(response, '401 Unauthorized',
                                'sign in first: the traffic policies say what may leave this instance and who '
                                'may call it, which is not an anonymous question')
        response.media = summary(self.manager)

    def on_get_traffic_declared(self, request, response):
        """The CONFIRMED rows as declared flows — what the §7 object topology draws as `declared` edges beside
        the `observed` ones from the causal map, and what ct-8 rules on as `flow-declared` / `inbound`."""
        from security.custom.security_traffic import declared_flows, mode
        rows = declared_flows(self.manager)
        response.media = {
            'ok': True, 'mode': mode(), 'count': len(rows), 'flows': rows,
            'how': ('one entry per CONFIRMED policy row: outbound entries carry the system and the payload '
                    'CLASSES that were observed crossing; inbound entries carry the source and the endpoint '
                    'templates it was seen at, and their `classes` are honestly empty — what a caller sends is '
                    'known only once it reaches a class, and the causal map records that as an object edge, '
                    'not as traffic. Nothing here is observed: an observed flow with no confirmed row is drift, '
                    'and the topology says so by comparing this list with the map.')}

    def _rule_traffic(self, request, response, direction, name):
        from security.custom import security_traffic as TR
        fn = TR.confirm_outbound if direction == 'outbound' else TR.confirm_inbound
        r = fn(self.manager, name, self._user_info(request), (self._body(request).get('decision') or ''))
        if not r.get('ok'):
            status = {400: '400 Bad Request', 401: '401 Unauthorized', 403: '403 Forbidden',
                      404: '404 Not Found'}.get(int(r.get('status') or 403), '403 Forbidden')
            return self._refuse(response, status, r.get('refusal', ''), **{'policy': name})
        response.media = r

    def on_post_traffic_outbound(self, request, response, name):
        """POST {"decision": "confirmed"|"denied"} — a person rules on what may leave, on the record."""
        self._rule_traffic(request, response, 'outbound', name)

    def on_post_traffic_inbound(self, request, response, name):
        """POST {"decision": "confirmed"|"denied"} — a person rules on who may call."""
        self._rule_traffic(request, response, 'inbound', name)

    # §66a, found by the live proof on `polari-lean` (2026-09-19): an inbound row's name is
    # `origin|https://prf.<host>`, and a name with `://` in it CANNOT be carried in a URL path — falcon
    # percent-decodes before routing, so `%2F%2F` becomes `//` and the route never matches (404). Percent-
    # encoding is not a fix; the name simply does not belong in a path. These two doors take it in the BODY,
    # which has no such problem, and the `{name}` form stays for the simple names (`anonymous|anonymous`,
    # `odoo|main|json-rpc`) that a person can type. Same function, same refusals, one extra 400 for a missing
    # name — nothing about who may rule changes.

    def _rule_traffic_body(self, request, response, direction):
        name = str((self._body(request).get('name') or '')).strip()
        if not name:
            return self._bad(response, ('body: {"name": "<the policy row\'s name>", "decision": '
                                        '"confirmed"|"denied"}. Use THIS door for any name a URL path cannot '
                                        'carry — an inbound origin name holds "://", which falcon decodes '
                                        'before routing, so the /{name} form answers 404 for it.'))
        self._rule_traffic(request, response, direction, name)

    def on_post_traffic_outbound_body(self, request, response):
        """POST {"name": ..., "decision": "confirmed"|"denied"} — the body form of the outbound ruling."""
        self._rule_traffic_body(request, response, 'outbound')

    def on_post_traffic_inbound_body(self, request, response):
        """POST {"name": ..., "decision": "confirmed"|"denied"} — the body form of the inbound ruling."""
        self._rule_traffic_body(request, response, 'inbound')

    def on_get_owned(self, request, response):
        from security.custom.security_owned import policies
        from security.custom.security_owned_manifest import summary as owned_manifest_summary
        from accessControl.app_permissions_gate import gate_mode
        # op-4: the manifest summary CONVERGES `app.owned` into the rows (admin rows untouched), so the
        # policies are read AFTER it and with `converge=False` — one derivation per request, not two.
        manifest = owned_manifest_summary(self.manager)
        rows = policies(self.manager, converge=False)
        response.media = {
            'ok': True, 'mode': gate_mode(), 'count': len(rows),
            'enabled': sorted(p['class_name'] for p in rows if p['enabled']),
            'policies': rows,
            'manifest': manifest,
            'how': ('owner-defined permissions are OPT-IN per class: a class behaves exactly as it always did '
                    'until an enabled policy names it. A module DECLARES its own classes in `app.owned` '
                    '(polari-app.json) and the rows converge from it on every read of this door; POST '
                    '/api/security/owned/<Class> sets one by hand (admins only) and is never overwritten by a '
                    'derivation. The gate follows POLARI_APP_PERMISSIONS (off | advisory | enforce) — the same '
                    'knob as the class gate; advisory returns the whole row and says would-deny / '
                    'would-project in the X-Polari-Owner-Advisory header.')}

    def on_get_owned_class(self, request, response, class_name):
        from security.custom.security_owned import policies, policy_for
        pol = policy_for(self.manager, class_name)
        if pol is None:
            stored = next((p for p in policies(self.manager) if p['class_name'] == class_name), None)
            return self._json_ok(response, {
                'ok': True, 'class': class_name, 'owned': False, 'policy': stored,
                'why': ('a policy row exists but is disabled — a disabled policy is the same as no policy'
                        if stored else '%s is not an owned class: no OwnedClassPolicy row enables it' % class_name)})
        response.media = {'ok': True, 'class': class_name, 'owned': True, 'policy': pol}

    def on_post_owned_class(self, request, response, class_name):
        """Set or replace one class's owner policy. ADMIN_ROLES only: opting a class in changes what every
        caller may do to every instance of it, which is exactly a permissions-administration act."""
        from security.custom.security_claims import is_admin
        from security.custom.security_owned import set_policy
        if not is_admin(self._user_info(request)):
            return self._refuse(response, '403 Forbidden',
                                'only an administrator may opt a class into owner-defined permissions '
                                '(ADMIN_ROLES: admin, polari-admin)', **{'class': class_name})
        r = set_policy(self.manager, class_name, self._body(request), by=self._sub(request))
        if not r.get('ok'):
            return self._bad(response, r.get('refusal', ''))
        response.media = {**r, 'how': 'GET /api/security/owned/%s/<id> answers what a caller may do to one '
                                      'instance, and why' % class_name}

    def on_delete_owned_class(self, request, response, class_name):
        """REMOVE one class's owner policy — the way back out of an opt-in (round-5 live proof, N-6).

        The door offered POST only, so a throwaway policy was permanent: `DELETE` answered 405 and the best a
        person could do was set `enabled: false`, leaving the row in the listing's count for good. ADMIN_ROLES,
        like the POST, and refused for a class a manifest still declares — op-4's convergence would re-create
        that row on the very next read of `GET /api/security/owned`, so a delete there would look like it
        worked and silently come back."""
        from security.custom.security_claims import is_admin
        from security.custom.security_owned import delete_policy
        if not is_admin(self._user_info(request)):
            return self._refuse(response, '403 Forbidden',
                                'only an administrator may remove a class from owner-defined permissions '
                                '(ADMIN_ROLES: admin, polari-admin)', **{'class': class_name})
        r = delete_policy(self.manager, class_name, by=self._sub(request))
        if not r.get('ok'):
            return self._refuse(response,
                                {400: '400 Bad Request', 404: '404 Not Found',
                                 409: '409 Conflict'}.get(int(r.get('status') or 400), '400 Bad Request'),
                                r.get('refusal', ''), **{'class': class_name})
        response.media = r

    def on_get_owned_instance(self, request, response, class_name, object_id):
        """The CALLER's verdict on ONE instance: what they may do, which fields they see, which rule decided.

        op-1 (design §6): the same answer carries `sharing` — the instance's grants, the policy's bounds, and
        the CONFIGURED table definition a Sharing tab renders. One door, because a tab that had to ask twice
        would show the verdict and the grants from two different moments."""
        from security.custom.security_owned import verdict_for_id
        r = verdict_for_id(self.manager, self._user_info(request), class_name, object_id)
        if not r.get('ok'):
            return self._refuse(response, '404 Not Found', r.get('refusal', ''))
        response.media = r

    # ---- op-1: THE OWNER'S OWN GRANTS (design §2, §3 step 3, §6) ---------------------------------------------
    # The OWNER of one instance widening access to it, inside the bounds the class set. Never the class door:
    # `crude_permission_gate` decided C × V for the grantee's groups long before a grant is read.

    def _owned_status(self, result):
        return {400: '400 Bad Request', 401: '401 Unauthorized', 403: '403 Forbidden',
                404: '404 Not Found'}.get(int(result.get('status') or 400), '400 Bad Request')

    def on_get_owned_grants(self, request, response, class_name, object_id):
        """The instance's live grants, the policy's bounds, whether THIS caller may share, and the configured
        table the Sharing tab renders. Expired grants are pruned on the way through (design §2)."""
        from security.custom.security_owner_grants import sharing
        r = sharing(self.manager, self._user_info(request), class_name, object_id)
        if not r.get('ok'):
            return self._refuse(response, self._owned_status(r), r.get('refusal', ''),
                                **{'class': class_name, 'id': str(object_id)})
        response.media = r

    def on_post_owned_grants(self, request, response, class_name, object_id):
        """POST {"grantee_kind": "person"|"group", "grantee": "<sub or group>", "verbs": [...], "fields": [...],
        "valid_until": "2026-10-01T00:00:00Z"} — the OWNER shares ONE of their own rows."""
        from security.custom.security_owner_grants import grant
        r = grant(self.manager, self._user_info(request), class_name, object_id, self._body(request))
        if not r.get('ok'):
            return self._refuse(response, self._owned_status(r), r.get('refusal', ''),
                                **{'class': class_name, 'id': str(object_id),
                                   'knownFields': r.get('knownFields')})
        response.media = r

    def on_delete_owned_grants(self, request, response, class_name, object_id):
        """DELETE ?grantee_kind=&grantee= (or ?name=) — the owner takes one grant back."""
        body = dict(self._body(request))
        for key in ('grantee_kind', 'grantee', 'name', 'id'):
            if not body.get(key) and request.params.get(key):
                body[key] = request.params.get(key)
        from security.custom.security_owner_grants import revoke
        r = revoke(self.manager, self._user_info(request), class_name, object_id, body)
        if not r.get('ok'):
            return self._refuse(response, self._owned_status(r), r.get('refusal', ''),
                                **{'class': class_name, 'id': str(object_id)})
        response.media = r

    def on_post_owned_transfer(self, request, response, class_name, object_id):
        """POST {"to": "<Keycloak sub>"} — hand ONE instance to somebody else, inside the policy's `transfer`
        mode (nobody | admin | owner) and NEVER for an anonymised class (design §8).

        This door refuses on its own authority in every gate mode: advisory means the CRUDE gate warns instead
        of blocking an app doing its job, and a transfer is not that — it is a permissions-administration act
        whose only effect is to move the ownership the gate reads."""
        from security.custom.security_owned import transfer_owner
        r = transfer_owner(self.manager, self._user_info(request), class_name, object_id,
                           self._body(request).get('to'))
        if not r.get('ok'):
            return self._refuse(response, self._owned_status(r), r.get('refusal', ''),
                                **{'class': class_name, 'id': str(object_id)})
        response.media = r

    def on_get_compare(self, request, response):
        view = request.params.get('view', 'os'); mode = request.params.get('mode', 'today')
        try:
            response.media = {'ok': True, **compare(view, mode, manager=self.manager)}
        except ValueError as exc:
            self._bad(response, str(exc))

    # ---- ct-5: the `objects` view's own reading — the DRIFT report (design §7) --------------------------
    # "a class that flows with no knob declaring it is a finding; a knob that declares a flow never seen is
    # noise to prune." Same data as ?view=objects, said as the two differences instead of as a graph, because
    # that is what a person acts on. Signed in to read: what leaves this instance is not an anonymous question.

    def on_get_objects_drift(self, request, response):
        from security.custom.security_objects_view import drift
        if not self._sub(request):
            return self._refuse(response, '401 Unauthorized',
                                'sign in first: where this instance\'s rows go, and what nothing declares, is a '
                                'permissions-administration reading')
        response.media = {'ok': True, **drift(self.manager)}

    def on_get_objects_flows(self, request, response):
        """Both halves in one list — every DECLARED flow (manifest `app.flows` + confirmed traffic policies) and
        every OBSERVED one (the causal map), each with its classes. The raw material behind the drift."""
        from security.custom.security_objects_view import declared, manifest_flows, observed
        if not self._sub(request):
            return self._refuse(response, '401 Unauthorized',
                                'sign in first: the object flows say what leaves this instance and with which '
                                'classes aboard')
        decl, obs = declared(self.manager), observed(self.manager)
        response.media = {
            'ok': True, 'declared': decl, 'observed': obs,
            'counts': {'declared': len(decl), 'observed': len(obs), 'manifests': len(manifest_flows())},
            'how': ('declared = what somebody SAID may flow: a module manifest\'s `app.flows` stanza (the app '
                    'author, at the level an author can honestly speak — a system KIND, never a host) and a '
                    'traffic policy row a PERSON confirmed (the deployment). observed = what the causal map '
                    'recorded while a TraceTarget was armed. Neither is the whole truth on its own, and the '
                    'difference between them is GET /api/security/objects/drift.')}
