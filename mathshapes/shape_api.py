"""
@cross-cutting
@module mathshapes.shape_api
@tags @xc:bindings

HTTP surface for math-defined shapes:

  GET  /api/shapes                         the catalogue (name, family,
                                           kind, display name).
  GET  /api/shapes/{name}/properties       volume / area / bbox /
                                           centroid + the method used.
  POST /api/shapes/{name}/evaluate  {x,y,z}  inside/outside + value.
  GET  /api/shapes/{name}/surface?n=       surface mesh points (+ tris).
  GET  /api/shapes/{name}/classify         the quadric surface type.
  POST /api/shapes/from-pot/{potName}      derive/refresh a pot's math
                                           shape (hollow wall + bottom
                                           slab + holes) from its aqp-1
                                           PotDefinition + PotHole rows
                                           (shape_modify.
                                           pot_shape_from_definition),
                                           ALSO derives its soil fill
                                           (soil_modify.
                                           soil_shape_from_definition —
                                           phase 4), AND ensures a
                                           `{potName}-viz`
                                           SimSpaceDefinition scene
                                           listing wall + bottom +
                                           soil + holes (mathshapes.
                                           pot_scene). Re-run after
                                           editing hole/pot CRUDE fields
                                           (incl. soil_fill_height_mm)
                                           to refresh all of it.

Shapes themselves are edited through CRUDE (object-coherence). Pot
holes/dimensions are edited through CRUDE on PotDefinition/PotHole
(aquaponics.pot_api) — from-pot re-derives from whatever is currently
persisted there, it never edits pot fields itself.

@consumers
  - mathshapes frontend / SimSpace3D rendering (later)
@see /MATH_SHAPES_PLAN.md
"""

import json

from objectTreeDecorators import treeObject, treeObjectInit
from mathshapes.shape_analysis import (
    evaluate_point, quadric_classify, sample_surface, shape_properties,
)
from mathshapes.shape_modify import modify_parameter, pot_shape_from_definition
from mathshapes.soil_modify import soil_shape_from_definition
from mathshapes.pot_scene import ensure_pot_viz_scene


class MathShapesAPI(treeObject):
    """Math-defined shape endpoints."""

    @treeObjectInit
    def __init__(self, polServer):
        self.polServer = polServer
        self.apiName = '/api/shapes'
        if polServer is not None:
            polServer.falconServer.add_route(
                '/api/shapes', self, suffix='catalogue')
            polServer.falconServer.add_route(
                '/api/shapes/{name}/properties', self, suffix='properties')
            polServer.falconServer.add_route(
                '/api/shapes/{name}/evaluate', self, suffix='evaluate')
            polServer.falconServer.add_route(
                '/api/shapes/{name}/surface', self, suffix='surface')
            polServer.falconServer.add_route(
                '/api/shapes/{name}/classify', self, suffix='classify')
            polServer.falconServer.add_route(
                '/api/shapes/{name}/modify', self, suffix='modify')
            polServer.falconServer.add_route(
                '/api/shapes/from-pot/{pot_name}', self, suffix='from_pot')

    def _shapes(self):
        table = (getattr(self.manager, 'objectTables', None) or {}).get(
            'MathShapeDefinition', {})
        return list(table.values()) if isinstance(table, dict) \
            else list(table)

    def on_get_catalogue(self, request, response):
        catalogue = [{
            'name': getattr(s, 'name', ''),
            'displayName': getattr(s, 'display_name', ''),
            'family': getattr(s, 'family', ''),
            'primitiveKind': getattr(s, 'primitive_kind', ''),
            'provenanceId': getattr(s, 'provenance_id', ''),
        } for s in self._shapes()]
        response.media = {'ok': True, 'count': len(catalogue),
                          'shapes': catalogue}

    def on_get_properties(self, request, response, name):
        params = request.params or {}
        try:
            resolution = int(params.get('resolution', 32))
        except (TypeError, ValueError):
            resolution = 32
        result = shape_properties(self.manager, name, resolution=resolution)
        if not result.get('ok'):
            response.status = '404 Not Found'
        response.media = result

    def on_post_evaluate(self, request, response, name):
        try:
            body = json.load(request.bounded_stream) \
                if request.content_length else {}
        except Exception as e:
            response.status = '400 Bad Request'
            response.media = {'ok': False, 'error': f'bad JSON payload: {e}'}
            return
        try:
            x, y, z = (float(body.get('x', 0.0)), float(body.get('y', 0.0)),
                       float(body.get('z', 0.0)))
        except (TypeError, ValueError):
            response.status = '400 Bad Request'
            response.media = {'ok': False,
                              'error': 'x, y, z must be numbers'}
            return
        result = evaluate_point(self.manager, name, x, y, z)
        if not result.get('ok'):
            response.status = '404 Not Found'
        response.media = result

    def on_get_surface(self, request, response, name):
        params = request.params or {}
        try:
            n = int(params.get('n', 24))
        except (TypeError, ValueError):
            n = 24
        result = sample_surface(self.manager, name, n=n)
        if not result.get('ok'):
            response.status = '404 Not Found'
        response.media = result

    def on_get_classify(self, request, response, name):
        result = quadric_classify(self.manager, name)
        if not result.get('ok'):
            response.status = '400 Bad Request'
        response.media = result

    def on_post_modify(self, request, response, name):
        body = request.media or {}
        param = body.get('param')
        if not param or 'value' not in body:
            response.status = '400 Bad Request'
            response.media = {'ok': False,
                              'error': 'body needs {param, value}'}
            return
        result = modify_parameter(self.manager, name, param, body['value'])
        if not result.get('ok'):
            response.status = '400 Bad Request'
        response.media = result

    def on_post_from_pot(self, request, response, pot_name):
        result = pot_shape_from_definition(self.manager, pot_name)
        if not result.get('ok'):
            response.status = '404 Not Found'
            response.media = result
            return
        # Soil (phase 4) is derived FROM the wall/bottom this just
        # built (same _pot_core_dimensions numbers) — never fails the
        # whole re-derive; an honest gap (e.g. soil_fill_height_mm
        # resolves to ~0) is surfaced in the response, not silently
        # dropped.
        soil = soil_shape_from_definition(self.manager, pot_name)
        result['soil'] = soil
        soil_shape_name = soil.get('soilShape') if soil.get('ok') else None
        result['simSpace'] = ensure_pot_viz_scene(
            self.manager, pot_name, result['wallShape'],
            result['bottomShape'], soil_shape_name, result['holeShapes'],
            wall_transparent=result.get('wallTransparent', False),
            soil_transparent=result.get('soilTransparent', False))
        response.media = result
