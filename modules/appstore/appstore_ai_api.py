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

from objectTreeDecorators import treeObject, treeObjectInit

from appstore.appstore_ai import AI_LINKAGES, tool_report


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
