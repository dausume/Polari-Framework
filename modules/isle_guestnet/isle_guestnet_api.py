"""@module isle_guestnet.isle_guestnet_api — /api/isle-guestnet/summary: networks, exposures, guest readiness."""
import falcon  # noqa: F401
from objectTreeDecorators import treeObject, treeObjectInit


class IsleGuestnetAPI(treeObject):
    @treeObjectInit
    def __init__(self, polServer=None, manager=None):
        self.polServer = polServer
        self.manager = manager
        if polServer is not None and getattr(polServer, 'falconServer', None) is not None:
            polServer.falconServer.add_route('/api/isle-guestnet/summary', self, suffix='summary')

    def _rows(self, class_name):
        return list(((self.manager.objectTables or {}).get(class_name, {}) or {}).values())

    def on_get_summary(self, request, response):
        apps = {getattr(a, 'name', ''): a for a in self._rows('HardwareAppDefinition')}
        exp = self._rows('GuestNetworkExposure')
        out = []
        for n in self._rows('GuestNetworkDefinition'):
            app = apps.get(n.hardware_app)
            allowed = [e.isle_host for e in exp if e.network == n.name and e.enabled]
            out.append({'network': n.name, 'ssid': n.ssid, 'vlan': n.vlan, 'cidr': n.cidr, 'clientIsolation': n.client_isolation,
                        'internet': n.internet, 'allowedIsleHosts': allowed, 'guest': n.hardware_app,
                        'guestDefined': app is not None, 'imagePinned': bool(app and app.image_sha256_raw)})
        response.media = {'ok': True, 'networks': out, 'exposures': len(exp), 'states': len(self._rows('GuestNetworkState')),
                          'note': 'no exposure rows = guests reach nothing on the isle; render verdicts at /api/hardwareapps/render/isle-guestnet'}
