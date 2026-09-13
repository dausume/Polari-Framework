"""
@module security.security_api

/api/security            the taxonomy, the scenario in force here, the systems with provenance
/api/security/scenarios  every scenario (route, attach, rings, fixed pieces)
/api/security/topology   ?view=os|network|app [&scenario=…] [&mode=stock|today|complain|enforce] — one view, one scenario
/api/security/simulate   ?view=… &actor=… [&scenario=…] [&mode=…] — everything one actor can reach, hop by hop
/api/security/compare    ?view=… [&mode=…] — the same view across every scenario, verdict per scenario
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
            add('/api/security/audit', self, suffix='audit')          # POST an audit.sh --json payload; GET the latest runs
            add('/api/security/propose', self, suffix='propose')      # POST {app, stanza, groups} → a proposal row

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
