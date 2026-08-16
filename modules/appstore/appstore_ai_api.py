"""
@module appstore.appstore_ai_api

ai-1: the honest readiness API — GET /api/appstore/ai-tools returns
the tools + the linkage vocabulary + per-tool LIVE readiness joined
from the managed reasoning config (sdk installed / credential
present / base_url set), so "feasibly map to and interact with
capably" is DATA, not prose. Read-only: selection, auth, and
validation stay on /ai/providers (providersAPI) — secrets never
transit this surface.

@consumers
  - polariServer via module_endpoints.construct_appstore_endpoints
  - polari-platform-angular (ai-2 store section detail pane)
  - appstore.selftest_appstore (function-level)
"""

import json

from objectTreeDecorators import treeObject, treeObjectInit

from appstore.appstore_ai import AI_LINKAGES, host_check, tool_report


def _reasoning_status():
    """(all_status dict, '') or (None, why) — the join source for
    live readiness. Absent outside the server context (host tools,
    standalone selftests): stated, never guessed."""
    try:
        from polariApiServer import reasoning_config
        return reasoning_config.all_status(), ''
    except Exception as e:  # noqa: BLE001 — import or config error
        return None, f'reasoning config unavailable: {e}'


def ai_tools_payload(rows, include_unpublished=False):
    """The one list payload. Pure over `rows` (objects or dicts);
    readiness joins live when reasoning_config imports."""
    status, why = _reasoning_status()
    by_provider = {}
    active = ''
    if status is not None:
        active = status.get('active', '')
        by_provider = {p['name']: p
                       for p in status.get('providers', [])}
    tools = []
    for row in rows:
        published = getattr(row, 'published', True) \
            if not isinstance(row, dict) \
            else row.get('published', True)
        if not published and not include_unpublished:
            continue
        provider = getattr(row, 'provider_name', '') \
            if not isinstance(row, dict) \
            else row.get('provider_name', '')
        tools.append(tool_report(
            row, provider_status=by_provider.get(provider),
            active_provider=active))
    tools.sort(key=lambda t: t['name'])
    payload = {
        'ok': True,
        'active_provider': active,
        'linkages': AI_LINKAGES,
        'count': len(tools),
        'tools': tools,
    }
    if status is None:
        payload['readiness_note'] = why
    return payload


class AiToolsAPI(treeObject):
    """GET /api/appstore/ai-tools (+ /{tool} detail)."""

    @treeObjectInit
    def __init__(self, polServer):
        self.polServer = polServer
        self.apiName = '/api/appstore/ai-tools'
        if polServer is not None:
            add = polServer.falconServer.add_route
            add('/api/appstore/ai-tools', self, suffix='ai_tools')
            add('/api/appstore/ai-tools/{tool}', self,
                suffix='ai_tool')
            # ai-6: the honest hosting gauge.
            add('/api/appstore/ai-tools/{tool}/host-check', self,
                suffix='host_check')
            # ai-7: remote-hosting suggestions with DATED prices
            # (static segment — wins over the {tool} template).
            add('/api/appstore/ai-tools/hosting-options', self,
                suffix='hosting_options')

    def _rows(self):
        return list((getattr(self.manager, 'objectTables', None)
                     or {}).get('AiToolDefinition', {}).values())

    def on_get_ai_tools(self, request, response):
        response.media = ai_tools_payload(self._rows())

    def on_get_ai_tool(self, request, response, tool):
        payload = ai_tools_payload(self._rows(),
                                   include_unpublished=True)
        match = [t for t in payload['tools'] if t['name'] == tool]
        if not match:
            response.status = '404 Not Found'
            response.media = {'ok': False,
                              'error': f'no AI tool {tool!r}'}
            return
        media = {'ok': True, 'tool': match[0],
                 'active_provider': payload['active_provider'],
                 'linkages': AI_LINKAGES}
        if 'readiness_note' in payload:
            media['readiness_note'] = payload['readiness_note']
        response.media = media

    def on_get_hosting_options(self, request, response):
        """ai-7: the rentable options + derived fit against the
        localai hosting profiles. Prices carry their as-of date —
        the payload's honesty note says exactly what to trust.
        ai-8: PLUS the buy-vs-rent advisory when the computerparts
        module is enabled (row reads + its own pure fns, gated on
        module_enabled — ImportError is NOT an absence check)."""
        from appstore.appstore_hosting import (
            hosting_options_payload)
        rows = list((getattr(self.manager, 'objectTables', None)
                     or {}).get('RemoteHostingOption', {}).values())
        profiles = []
        for r in self._rows():
            name = getattr(r, 'name', '') \
                if not isinstance(r, dict) else r.get('name', '')
            if name == 'localai':
                raw = getattr(r, 'requirements_json', '') \
                    if not isinstance(r, dict) \
                    else r.get('requirements_json', '')
                try:
                    profiles = json.loads(
                        raw or '{}').get('profiles', [])
                except ValueError:
                    profiles = []
        payload = hosting_options_payload(rows, profiles)
        payload['buy'] = self._buy_section(payload['options'],
                                           profiles)
        response.media = payload

    def _buy_section(self, rental_options, profiles):
        """ai-8: builds from the computerparts module joined with
        derived fit + break-even months against the USD rental
        options (monthly-ized; EUR options skipped rather than
        converted — currency math without a dated rate is a lie)."""
        try:
            from polariApiServer.module_gating import module_enabled
            enabled = module_enabled('computerparts')
        except ImportError:
            enabled = False
        if not enabled:
            return {'available': False,
                    'note': 'the computerparts module is not '
                            'enabled on this instance — bring it '
                            'online for the buy-vs-rent advisory'}
        try:
            from computerparts.parts_assembly import assembly_check
            from computerparts.parts_basis import (
                break_even_months, build_report)
        except ImportError:
            return {'available': False,
                    'note': 'computerparts code not present'}
        from appstore.appstore_hosting import option_fit
        tables = getattr(self.manager, 'objectTables', None) or {}
        parts_by_name = {
            getattr(p, 'name', ''): p
            for p in tables.get('ComputerPartDefinition',
                                {}).values()
            if getattr(p, 'published', True)}
        # monthly-ized USD rentals a GPU build competes with
        rentals = []
        for o in rental_options:
            if o['kind'] not in ('gpu-vps', 'gpu-dedicated'):
                continue
            if not o['price_unit'].startswith('USD'):
                continue
            monthly = o['price_amount'] if o['price_unit'].endswith(
                '/mo') else round(o['price_amount'] * 730, 0)
            rentals.append({'option': o['name'],
                            'monthly_usd': monthly})
        rentals.sort(key=lambda r: r['monthly_usd'])
        builds = []
        for b in tables.get('ComputerBuildDefinition', {}).values():
            if not getattr(b, 'published', True):
                continue
            report = build_report(b, parts_by_name)
            report['assembly'] = assembly_check(b, parts_by_name)
            report['fit'] = option_fit(
                dict(report['specs'], name=report['name']),
                profiles)
            report['break_even'] = [
                {'vs': r['option'],
                 'monthly_usd': r['monthly_usd'],
                 'months': break_even_months(report['total_usd'],
                                             r['monthly_usd'])}
                for r in rentals]
            builds.append(report)
        builds.sort(key=lambda x: x['total_usd'])
        return {
            'available': True,
            'builds': builds,
            'advisory': {
                'sparing': 'using this only occasionally? RENT '
                           'hourly — but remember the manual '
                           'teardown: on DigitalOcean a GPU '
                           'droplet BILLS even powered off; you '
                           'must DESTROY it after each session',
                'sustained': 'planning to use it for months? past '
                             'the break-even months shown, buying '
                             'one of these machines is cheaper '
                             'than renting — and it stays on the '
                             'isle (sovereign)',
            },
        }

    def on_get_host_check(self, request, response, tool):
        """ai-6: gauge whether THIS isle can realistically host the
        tool — per-machine verdicts from the res-1 inventory, and
        the remote-hosting options when it cannot. A REPORT, never
        an action (knob-and-suggestion)."""
        row = None
        for r in self._rows():
            name = getattr(r, 'name', '') \
                if not isinstance(r, dict) else r.get('name', '')
            if name == tool:
                row = r
                break
        if row is None:
            response.status = '404 Not Found'
            response.media = {'ok': False,
                              'error': f'no AI tool {tool!r}'}
            return
        raw = getattr(row, 'requirements_json', '') \
            if not isinstance(row, dict) \
            else row.get('requirements_json', '')
        try:
            requirements = json.loads(raw or '{}')
        except ValueError:
            requirements = {}
        if not (requirements.get('profiles') or []):
            hosting = getattr(row, 'hosting', '') \
                if not isinstance(row, dict) \
                else row.get('hosting', '')
            response.media = {
                'ok': True, 'tool': tool, 'nothing_to_host': True,
                'note': ('nothing to gauge — %s tools run no '
                         'local server' % (hosting or 'this')),
            }
            return
        # the res-1 inventory: refresh the LOCAL observation first
        # (cheap, keeps the verdict from riding stale numbers),
        # then read every machine. resources may be absent — say so.
        try:
            from resources.node_resources import (
                inventory, refresh_local_machine)
            try:
                refresh_local_machine(self.manager)
            except Exception:  # noqa: BLE001 — stale is stated
                pass
            nodes = inventory(self.manager).get('nodes', [])
        except ImportError:
            response.media = {
                'ok': True, 'tool': tool,
                'resources_unavailable': (
                    'the resources module is not loaded on this '
                    'instance — no inventory to gauge against'),
                'cloud': host_check(requirements, [])['cloud'],
            }
            return
        result = host_check(requirements, nodes)
        result['tool'] = tool
        response.media = result
