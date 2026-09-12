"""
@module security.security_api

/api/security            the taxonomy, the scenario in force here, the systems with provenance
/api/security/scenarios  every scenario (route, attach, rings, fixed pieces)
/api/security/topology   ?view=os|network|app [&scenario=…] [&mode=stock|today|complain|enforce] — one view, one scenario
/api/security/simulate   ?view=… &actor=… [&scenario=…] [&mode=…] — everything one actor can reach, hop by hop
/api/security/compare    ?view=… [&mode=…] — the same view across every scenario, verdict per scenario
The scenario defaults to the one this deployment is (POLARI_DEPLOY_ROUTE: isle → isle, swarm → lean/full by
profile, else dev). Pure reads over security_topology; nothing here changes the machine.
"""
import os

from objectTreeDecorators import treeObject, treeObjectInit

from security.custom.security_facts import SYSTEMS, load_scenario, scenario_names
from security.custom.security_topology import MODES, VIEWS, build, compare, simulate


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

    def on_get_compare(self, request, response):
        view = request.params.get('view', 'os'); mode = request.params.get('mode', 'today')
        try:
            response.media = {'ok': True, **compare(view, mode)}
        except ValueError as exc:
            self._bad(response, str(exc))
