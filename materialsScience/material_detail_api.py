"""
@cross-cutting
@module materialsScience.material_detail_api
@tags @xc:bindings

HTTP surface for the per-material detail view (PeersAPI pattern —
self-registering falcon route):

  GET /api/msci/materials/{name}/detail   one material's full picture:
                                          identity, properties with
                                          meanings + scenario context,
                                          thermal window, blend
                                          effects, per-level rows

Pure read over material_detail — no side effects.

@consumers
  - material-detail frontend component
@see /OVERLAP_MAP.md
"""

from objectTreeDecorators import treeObject, treeObjectInit
from materialsScience.material_detail import build_material_detail


class MaterialDetailAPI(treeObject):
    """Per-material detail endpoint."""

    @treeObjectInit
    def __init__(self, polServer):
        self.polServer = polServer
        self.apiName = '/api/msci/materials'
        if polServer is not None:
            polServer.falconServer.add_route(
                '/api/msci/materials/{name}/detail', self,
                suffix='detail')

    def on_get_detail(self, request, response, name):
        report = build_material_detail(self.manager, name)
        if not report.get('ok'):
            response.status = '404 Not Found'
        response.media = report
