"""
@cross-cutting
@module aquaponics.hydraulics_api
@tags @xc:bindings

HTTP surface for aqp-3 pot hydraulics:

  GET  /api/aquaponics/hydraulics/capability
        engine presence (local skfem / worker / reservoir-only) —
        honest when absent.
  GET  /api/aquaponics/pots/{name}/drains
        the headline drains-by-gravity verdict + findings. Query:
        ?soil=<name>&water_level_mm=<mm>&fidelity=fem|reservoir
  POST /api/aquaponics/hydraulics/head-field
        {"pot", "soil", "water_level_mm"?, "refine"?} -> the full
        per-node head field (fem fidelity; refuses honestly when no
        solver is reachable — the reservoir model has no field).
  GET  /api/aquaponics/pots/{name}/water-slice
        aquaponics-pot-shape phase 3: a 3-D-positioned triangulated
        mesh of the steady head field, in the same coordinate frame
        the pot's own wall/soil/hole meshes render in — ready to feed
        straight into the frontend's water-flow visualization. Query:
        ?soil=<name>&waterLevelMm=<mm>&refine=<n>

@consumers
  - aquaponics frontend (later phase); aqp-7/aqp-8 couplings
@see /AQUAPONICS_PHASE2_PLAN.md, /AQUAPONICS_POT_SHAPE_PLAN.md (phase 3)
"""

import json

from objectTreeDecorators import treeObject, treeObjectInit
from aquaponics.custom.hydraulics import (
    build_darcy_payload, run_hydraulics, water_slice_mesh,
)


class AquaponicsHydraulicsAPI(treeObject):
    """aqp-3 hydraulics endpoints."""

    @treeObjectInit
    def __init__(self, polServer):
        self.polServer = polServer
        self.apiName = '/api/aquaponics/hydraulics'
        if polServer is not None:
            polServer.falconServer.add_route(
                '/api/aquaponics/hydraulics/capability', self,
                suffix='capability')
            polServer.falconServer.add_route(
                '/api/aquaponics/pots/{name}/drains', self,
                suffix='drains')
            polServer.falconServer.add_route(
                '/api/aquaponics/hydraulics/head-field', self,
                suffix='headfield')
            polServer.falconServer.add_route(
                '/api/aquaponics/pots/{name}/water-slice', self,
                suffix='water_slice')

    def on_get_capability(self, request, response):
        from materialsScience.engines import darcy_engine
        from materialsScience.engines.remote import remote_capability
        local = darcy_engine.capability()
        worker = remote_capability()
        response.media = {
            'ok': True,
            'localSkfem': local,
            'worker': {'reachable': worker is not None,
                       'skfem': (worker or {}).get('engines', {})
                       .get('skfem')},
            'reservoirModel': {'available': True,
                               'note': 'pure-python reduced model, '
                                       'always answers in-backend'},
            'fidelityKnob': "fidelity=fem|reservoir on /drains; fem "
                            'falls back to reservoir with a '
                            'fidelityNote when no solver is reachable',
        }

    def on_get_drains(self, request, response, name):
        params = request.params or {}
        water = params.get('water_level_mm')
        result = run_hydraulics(
            self.manager, name, params.get('soil', ''),
            water_level_mm=float(water) if water else None,
            fidelity=params.get('fidelity', 'fem'))
        if not result.get('ok'):
            response.status = '404 Not Found' \
                if 'no PotDefinition' in str(result.get('error', '')) \
                else '400 Bad Request'
        response.media = result

    def on_post_headfield(self, request, response):
        try:
            body = json.load(request.bounded_stream) \
                if request.content_length else {}
        except Exception as e:
            response.status = '400 Bad Request'
            response.media = {'ok': False,
                              'error': f'bad JSON payload: {e}'}
            return
        pot = body.get('pot', '')
        if not pot:
            response.status = '400 Bad Request'
            response.media = {'ok': False, 'error': "'pot' is required"}
            return
        built = build_darcy_payload(
            self.manager, pot, body.get('soil', ''),
            water_level_mm=body.get('water_level_mm'),
            refine=int(body.get('refine', 6) or 6))
        if not built.get('ok'):
            response.status = '400 Bad Request'
            response.media = built
            return
        from materialsScience.engines import darcy_engine
        result = darcy_engine.solve_head_field(built['payload'])
        if not result.get('ok'):
            response.status = '503 Service Unavailable'
        else:
            result['pot'] = pot
            result['conductivitySource'] = built['conductivitySource']
        response.media = result

    def on_get_water_slice(self, request, response, name):
        params = request.params or {}
        water = params.get('waterLevelMm')
        result = water_slice_mesh(
            self.manager, name, params.get('soil', ''),
            water_level_mm=float(water) if water else None,
            refine=int(params.get('refine', 6) or 6))
        if not result.get('ok'):
            response.status = '404 Not Found' \
                if 'no PotDefinition' in str(result.get('error', '')) \
                else '503 Service Unavailable'
        response.media = result
