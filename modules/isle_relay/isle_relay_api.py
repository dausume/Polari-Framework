"""@module isle_relay.isle_relay_api — /api/isle-relay/summary: segments + their guest render verdicts."""
import falcon  # noqa: F401
from objectTreeDecorators import treeObject, treeObjectInit


class IsleRelayAPI(treeObject):
    @treeObjectInit
    def __init__(self, polServer=None, manager=None):
        self.polServer = polServer
        self.manager = manager
        if polServer is not None and getattr(polServer, 'falconServer', None) is not None:
            polServer.falconServer.add_route('/api/isle-relay/summary', self, suffix='summary')

    def _rows(self, class_name):
        return list(((self.manager.objectTables or {}).get(class_name, {}) or {}).values())

    def on_get_summary(self, request, response):
        apps = {getattr(a, 'name', ''): a for a in self._rows('HardwareAppDefinition')}
        out = []
        for r in self._rows('RelayNodeDefinition'):
            app = apps.get(r.hardware_app)
            out.append({'relay': r.name, 'vlan': r.vlan, 'cidr': r.cidr, 'bearer': r.bearer, 'ssid': r.ssid,
                        'reticulumBearer': r.reticulum_bearer, 'guest': r.hardware_app,
                        'guestDefined': app is not None, 'imagePinned': bool(app and app.image_sha256_raw),
                        'passthrough': (app.passthrough_json if app else '[]')})
        response.media = {'ok': True, 'relays': out, 'states': len(self._rows('RelayNodeState')),
                          'note': 'render verdicts: /api/hardwareapps/render/isle-relay; the isle applies them with isle vm'}
