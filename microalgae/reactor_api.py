"""
@cross-cutting
@module microalgae.reactor_api
@tags @xc:bindings

HTTP surface for algae-1 microalgae reactors:

  GET /api/microalgae/strains
        the strain catalogue.
  GET /api/microalgae/reactors
        every reactor + its coupled system.
  GET /api/microalgae/reactors/{name}/sustainability
        can it run without collapsing the system? verdict + CO2 + draw
        vs surplus + regulation suggestions.
  GET /api/microalgae/reactors/{name}/decarbonization?days=365
        CO2 fixed + biomass over the period (caveated if not sustainable).
  GET /api/microalgae/recommend?kind=tank&system=<name>
        would a reactor HELP this system (spare N to consume + CO2)?

Strains / reactors are edited through CRUDE (object-coherence).

@consumers
  - microalgae frontend (later); tanks / aquaponics decarbonization
@see /SALTWATER_FOOD_FOREST_SPEC.md
"""

from objectTreeDecorators import treeObject, treeObjectInit
from microalgae.reactor_analysis import (
    decarbonization_yield, recommend_reactor_for,
    sustainability_assessment,
)


class MicroalgaeReactorAPI(treeObject):
    """algae-1 reactor endpoints."""

    @treeObjectInit
    def __init__(self, polServer):
        self.polServer = polServer
        self.apiName = '/api/microalgae'
        if polServer is not None:
            polServer.falconServer.add_route(
                '/api/microalgae/strains', self, suffix='strains')
            polServer.falconServer.add_route(
                '/api/microalgae/reactors', self, suffix='reactors')
            polServer.falconServer.add_route(
                '/api/microalgae/reactors/{name}/sustainability', self,
                suffix='sustainability')
            polServer.falconServer.add_route(
                '/api/microalgae/reactors/{name}/decarbonization', self,
                suffix='decarbonization')
            polServer.falconServer.add_route(
                '/api/microalgae/recommend', self, suffix='recommend')

    def _rows(self, class_name):
        table = (self.manager.objectTables or {}).get(class_name, {})
        return list(table.values()) if isinstance(table, dict) \
            else list(table)

    def on_get_strains(self, request, response):
        out = [{'name': getattr(s, 'name', ''),
                'displayName': getattr(s, 'display_name', ''),
                'waterType': getattr(s, 'water_type', ''),
                'product': getattr(s, 'product', ''),
                'edible': bool(getattr(s, 'edible', False)),
                'maxGrowthRatePerDay':
                    getattr(s, 'max_growth_rate_per_day', 0)}
               for s in self._rows('AlgaeStrain')]
        response.media = {'ok': True, 'strains': out, 'count': len(out)}

    def on_get_reactors(self, request, response):
        out = [{'name': getattr(r, 'name', ''),
                'displayName': getattr(r, 'display_name', ''),
                'strain': getattr(r, 'strain_name', ''),
                'volumeL': getattr(r, 'volume_l', 0),
                'coupledSystem': getattr(r, 'coupled_system_name', ''),
                'coupledKind': getattr(r, 'coupled_system_kind', '')}
               for r in self._rows('AlgaeReactorDefinition')]
        response.media = {'ok': True, 'reactors': out, 'count': len(out)}

    def on_get_sustainability(self, request, response, name):
        result = sustainability_assessment(self.manager, name)
        if not result.get('ok'):
            response.status = '404 Not Found'
        response.media = result

    def on_get_decarbonization(self, request, response, name):
        days = float((request.params or {}).get('days', 365.0) or 365.0)
        result = decarbonization_yield(self.manager, name, days=days)
        if not result.get('ok'):
            response.status = '404 Not Found'
        response.media = result

    def on_get_recommend(self, request, response):
        params = request.params or {}
        kind = params.get('kind', 'tank')
        system = params.get('system', '')
        if not system:
            response.status = '400 Bad Request'
            response.media = {'ok': False, 'error': "'system' is required"}
            return
        response.media = recommend_reactor_for(self.manager, kind, system)
