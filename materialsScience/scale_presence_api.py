"""
@cross-cutting
@module materialsScience.scale_presence_api
@tags @xc:bindings

HTTP surface for scale-presence accountability (PeersAPI pattern —
self-registering falcon routes):

  GET /api/msci/scale-presence              the full materials x levels
                                            matrix (absence is data)
  GET /api/msci/scale-presence/level/{level}  one level's page: who is
                                            defined/partial/MISSING
                                            here, each absence with the
                                            evidence-bearing suggestion

Pure reads over scale_presence — no side effects.

@consumers
  - materials-home + material-level-page components (msci-24 pages)
@see /OVERLAP_MAP.md
"""

from objectTreeDecorators import treeObject, treeObjectInit
from materialsScience.scale_presence import (
    level_accountability, presence_matrix,
)


class ScalePresenceAPI(treeObject):
    """Materials x scale-levels accountability endpoints."""

    @treeObjectInit
    def __init__(self, polServer):
        self.polServer = polServer
        self.apiName = '/api/msci/scale-presence'
        if polServer is not None:
            polServer.falconServer.add_route(
                '/api/msci/scale-presence', self, suffix='matrix')
            polServer.falconServer.add_route(
                '/api/msci/scale-presence/level/{level}', self,
                suffix='level')

    def on_get_matrix(self, request, response):
        response.media = presence_matrix(self.manager)

    def on_get_level(self, request, response, level):
        try:
            level = int(level)
        except ValueError:
            response.status = '400 Bad Request'
            response.media = {'ok': False,
                              'error': f"level must be an integer 0-4, "
                                       f"got '{level}'"}
            return
        report = level_accountability(self.manager, level)
        if not report.get('ok'):
            response.status = '404 Not Found'
        response.media = report
