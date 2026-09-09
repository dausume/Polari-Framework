"""@module printcam.printcam_api — /api/printcam/summary: cameras, their guest, port readiness, timelapses."""
import falcon  # noqa: F401
from objectTreeDecorators import treeObject, treeObjectInit


class PrintcamAPI(treeObject):
    @treeObjectInit
    def __init__(self, polServer=None, manager=None):
        self.polServer = polServer
        self.manager = manager
        if polServer is not None and getattr(polServer, 'falconServer', None) is not None:
            polServer.falconServer.add_route('/api/printcam/summary', self, suffix='summary')

    def _rows(self, class_name):
        return list(((self.manager.objectTables or {}).get(class_name, {}) or {}).values())

    def on_get_summary(self, request, response):
        apps = {a.name: a for a in self._rows('HardwareAppDefinition')}
        out = []
        for c in self._rows('CameraDefinition'):
            ext = apps.get('printcam')
            out.append({'camera': c.name, 'guest': c.hardware_app, 'printer': c.printer, 'streamer': c.streamer, 'device': c.device,
                        'resolution': '%dx%d@%d' % (c.width, c.height, c.fps), 'webcam': c.webcam_name, 'timelapse': c.timelapse,
                        'extensionDefined': ext is not None, 'portAssigned': bool(ext and ext.passthrough_json not in ('', '[]'))})
        response.media = {'ok': True, 'cameras': out, 'timelapses': len(self._rows('TimelapseRecord')),
                          'note': 'render: /api/hardwareapps/render/printcam; apply: isle vm extend voron-printer --with printcam'}
