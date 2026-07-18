"""
@cross-cutting
@module aquaponics.pot_api
@tags @xc:bindings

HTTP surface for pot geometry (aqp-1), PeersAPI pattern:

  GET  /api/aquaponics/pots                 every PotDefinition +
                                            its hole counts
  GET  /api/aquaponics/pots/{name}/validate the gravity + geometry
                                            report (findings name
                                            their knobs)
  POST /api/aquaponics/pots/{name}/generate-holes
                                            preview a valid hole set
                                            from tunable knobs (count,
                                            diameters, heights) — a
                                            PREVIEW, does not persist

Pots + holes are edited through standard CRUDE on PotDefinition /
PotHole rows (object-coherence).

@consumers
  - aquaponics frontend (later phase)
@see /AQUAPONICS_MODULE_PLAN.md
"""

import json

from objectTreeDecorators import treeObject, treeObjectInit
from aquaponics.pot_geometry import generate_holes, validate_pot


class AquaponicsPotAPI(treeObject):
    """Pot geometry endpoints."""

    @treeObjectInit
    def __init__(self, polServer):
        self.polServer = polServer
        self.apiName = '/api/aquaponics/pots'
        if polServer is not None:
            polServer.falconServer.add_route(
                '/api/aquaponics/pots', self, suffix='pots')
            polServer.falconServer.add_route(
                '/api/aquaponics/pots/{name}/validate', self,
                suffix='validate')
            polServer.falconServer.add_route(
                '/api/aquaponics/pots/{name}/generate-holes', self,
                suffix='generate')

    def _rows(self, class_name):
        table = (self.manager.objectTables or {}).get(class_name, {})
        return list(table.values()) if isinstance(table, dict) \
            else list(table)

    def on_get_pots(self, request, response):
        holes = self._rows('PotHole')
        out = []
        for pot in self._rows('PotDefinition'):
            name = getattr(pot, 'name', '')
            mine = [h for h in holes
                    if getattr(h, 'pot_name', '') == name]
            out.append({
                'name': name,
                'displayName': getattr(pot, 'display_name', ''),
                'shape': getattr(pot, 'shape', ''),
                'outerTopDiameterMm':
                    getattr(pot, 'outer_top_diameter_mm', None),
                'heightMm': getattr(pot, 'height_mm', None),
                'materialName': getattr(pot, 'material_name', ''),
                'holeCounts': {
                    'input': sum(1 for h in mine
                                 if getattr(h, 'kind', '') == 'input'),
                    'output': sum(1 for h in mine
                                  if getattr(h, 'kind', '')
                                  == 'output')},
            })
        response.media = {'ok': True, 'pots': out}

    def on_get_validate(self, request, response, name):
        report = validate_pot(self.manager, name)
        if not report.get('ok'):
            response.status = '404 Not Found'
        response.media = report

    def on_post_generate(self, request, response, name):
        try:
            payload = json.load(request.bounded_stream) \
                if request.content_length else {}
        except Exception as e:
            response.status = '400 Bad Request'
            response.media = {'ok': False,
                              'error': f'bad JSON payload: {e}'}
            return
        pots = {getattr(p, 'name', ''): p
                for p in self._rows('PotDefinition')}
        pot = pots.get(name)
        if pot is None:
            response.status = '404 Not Found'
            response.media = {'ok': False,
                              'error': f"no PotDefinition named "
                                       f"'{name}'"}
            return
        specs = generate_holes(
            pot,
            n_pairs=int(payload.get('n_pairs', 1) or 1),
            input_diameter_mm=float(
                payload.get('input_diameter_mm', 10.0)),
            output_diameter_mm=float(
                payload.get('output_diameter_mm', 12.0)),
            input_height_frac=float(
                payload.get('input_height_frac', 0.8)),
            output_height_frac=float(
                payload.get('output_height_frac', 0.15)))
        response.media = {
            'ok': True, 'pot': name, 'preview': specs,
            'note': 'preview only — create these as PotHole rows via '
                    'CRUDE to apply. Every generated set satisfies the '
                    'gravity self-watering invariant.'}
