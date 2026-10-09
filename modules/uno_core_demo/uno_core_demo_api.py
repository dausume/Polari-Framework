"""
@module uno_core_demo.uno_core_demo_api

GET /api/uno-core-demo/readiness   computes DemoReadiness fresh (`uno_core_demo.custom.readiness.readiness`),
                                   upserts the rows by name, and returns {ok, rows, composition: {status, weakest}}
                                   — a door, never boot: nothing is seeded with a claim.
"""
from objectTreeDecorators import treeObject, treeObjectInit

from uno_core_demo.custom import readiness as RD


def _manifest_parts():
    """The manifest's `parts` block (uno_core_demo's own polari-app.json) — falls back to
    `readiness.DEFAULT_PARTS` so the door still answers from a `pol project` checkout with no manifest loader."""
    try:
        from moduleService.manifests import load
        m = load('uno_core_demo')
        return (m or {}).get('parts') or RD.DEFAULT_PARTS
    except Exception:
        return RD.DEFAULT_PARTS


class UnoCoreDemoAPI(treeObject):
    @treeObjectInit
    def __init__(self, polServer=None, manager=None):
        self.polServer = polServer
        self.manager = manager
        if polServer is not None and getattr(polServer, 'falconServer', None) is not None:
            add = polServer.falconServer.add_route
            add('/api/uno-core-demo/readiness', self, suffix='readiness')

    def _upsert(self, cls_name, cls, rows):
        """Same idiom as `cmod.cmod_firmware_api.CModFirmwareAPI._upsert` — update an existing row's fields in
        place by `name`, construct+register a new one otherwise (treeObjectInit auto-registers it)."""
        table = (self.manager.objectTables or {}).setdefault(cls_name, {})
        by_name = {getattr(r, 'name', ''): r for r in table.values()}
        for row in rows:
            existing = by_name.get(row['name'])
            if existing is not None:
                for k, v in row.items():
                    setattr(existing, k, v)
            else:
                cls(manager=self.manager, **row)

    def on_get_readiness(self, request, response):
        from uno_core_demo.objects.uno_core_demo.DemoReadiness import DemoReadiness
        rows = RD.readiness(self.manager, _manifest_parts())
        if self.manager is not None:
            self._upsert('DemoReadiness', DemoReadiness, rows)
        composition = next((r for r in rows if r['part'] == 'composition'), None)
        response.status = '200 OK'
        response.media = {'ok': True, 'rows': rows,
                          'composition': {'status': (composition or {}).get('status', ''),
                                          'weakest': (composition or {}).get('why', '')}}
