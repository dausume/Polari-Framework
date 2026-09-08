"""
@cross-cutting
@module plant_morphology.morphology_api
@tags @xc:bindings

HTTP surface for the 3D stand-in morphology models:

  GET /api/morphology/plants/{name}/geometry
        per-organ 3D bounds + volume + canopy envelope.
  GET /api/morphology/plants/{name}/roots
        the unconfined root envelope + root-ball volume.
  GET /api/morphology/plants/{name}/confinement?pot=<pot>
      or ?container_volume_l=<L>
        can it be dwarfed + kept in the container indefinitely? +
        the dwarf factor, prune cadence, and limiting factor named.

Organ/root models are edited through CRUDE (object-coherence).

@consumers
  - morphology frontend / SimSpace3D stand-in rendering (later)
@see /AQUAPONICS_MODULE_PLAN.md
"""

from objectTreeDecorators import treeObject, treeObjectInit
from plant_morphology.custom.morphology_analysis import (
    confinement_assessment, organ_geometry, root_spread,
)


class PlantMorphologyAPI(treeObject):
    """3D stand-in morphology endpoints."""

    @treeObjectInit
    def __init__(self, polServer):
        self.polServer = polServer
        self.apiName = '/api/morphology'
        if polServer is not None:
            polServer.falconServer.add_route(
                '/api/morphology/plants/{name}/geometry', self,
                suffix='geometry')
            polServer.falconServer.add_route(
                '/api/morphology/plants/{name}/roots', self,
                suffix='roots')
            polServer.falconServer.add_route(
                '/api/morphology/plants/{name}/confinement', self,
                suffix='confinement')

    def on_get_geometry(self, request, response, name):
        result = organ_geometry(self.manager, name)
        if not result.get('ok'):
            response.status = '404 Not Found'
        response.media = result

    def on_get_roots(self, request, response, name):
        result = root_spread(self.manager, name)
        if not result.get('ok'):
            response.status = '404 Not Found'
        response.media = result

    def on_get_confinement(self, request, response, name):
        params = request.params or {}
        pot = params.get('pot')
        container = params.get('container_volume_l')
        result = confinement_assessment(
            self.manager, name, pot_name=pot,
            container_volume_l=float(container) if container else None)
        if not result.get('ok'):
            response.status = '400 Bad Request'
        response.media = result
