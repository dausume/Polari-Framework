"""@module kirimoto.kirimoto_api — /api/kirimoto/summary: instance, profiles, pin state, build command."""
import falcon  # noqa: F401
from objectTreeDecorators import treeObject, treeObjectInit


class KirimotoAPI(treeObject):
    @treeObjectInit
    def __init__(self, polServer=None, manager=None):
        self.polServer = polServer
        self.manager = manager
        if polServer is not None and getattr(polServer, 'falconServer', None) is not None:
            polServer.falconServer.add_route('/api/kirimoto/summary', self, suffix='summary')

    def _rows(self, class_name):
        return list(((self.manager.objectTables or {}).get(class_name, {}) or {}).values())

    def on_get_summary(self, request, response):
        from kirimoto.custom.build_image import build_command
        from kirimoto.kirimoto_basis import KIRIMOTO_UPSTREAM, KIRIMOTO_IMAGE
        cmd, refusals = build_command()
        response.media = {'ok': True, 'upstream': KIRIMOTO_UPSTREAM, 'image': KIRIMOTO_IMAGE, 'buildCommand': ' '.join(cmd), 'refusals': refusals,
                          'instances': [{'name': i.name, 'domain': i.domain, 'commit': i.upstream_commit, 'probeOk': i.probe_ok} for i in self._rows('SlicerInstance')],
                          'profiles': [{'name': p.name, 'printer': p.printer, 'bed': '%gx%gx%g' % (p.bed_x_mm, p.bed_y_mm, p.bed_z_mm), 'flavor': p.gcode_flavor} for p in self._rows('SlicerProfile')],
                          'sliceJobs': len(self._rows('SliceJob'))}
