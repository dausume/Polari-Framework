"""
@cross-cutting
@module biomining.biomining_api
@tags @xc:bindings

HTTP surface for biomine-1 bioextraction variants:

  GET /api/biomining/agents
        the bioextraction agent catalogue.
  GET /api/biomining/systems
        every specialized biomining variant + its target.
  GET /api/biomining/systems/{name}/yield?days=30
        element recovered + refined product over the period + risk.
  GET /api/biomining/systems/{name}/transfer?days=30
        nutrient-recovery: recovered nutrient available to supplement
        the lacking target system.
  GET /api/biomining/products/{name}/pathway
        the element→product refinement steps + material link.

Agents / products / systems are edited through CRUDE (object-coherence).

@consumers
  - biomining frontend (later); materialsScience (product targets)
@see materialsScience/
"""

from objectTreeDecorators import treeObject, treeObjectInit
from biomining.custom.biomining_analysis import (
    extraction_yield, recovery_transfer, refinement_pathway,
)


class BiomineAPI(treeObject):
    """biomine-1 endpoints."""

    @treeObjectInit
    def __init__(self, polServer):
        self.polServer = polServer
        self.apiName = '/api/biomining'
        if polServer is not None:
            polServer.falconServer.add_route(
                '/api/biomining/agents', self, suffix='agents')
            polServer.falconServer.add_route(
                '/api/biomining/systems', self, suffix='systems')
            polServer.falconServer.add_route(
                '/api/biomining/systems/{name}/yield', self,
                suffix='yield')
            polServer.falconServer.add_route(
                '/api/biomining/systems/{name}/transfer', self,
                suffix='transfer')
            polServer.falconServer.add_route(
                '/api/biomining/products/{name}/pathway', self,
                suffix='pathway')

    def _rows(self, class_name):
        table = (self.manager.objectTables or {}).get(class_name, {})
        return list(table.values()) if isinstance(table, dict) \
            else list(table)

    def on_get_agents(self, request, response):
        out = [{'name': getattr(a, 'name', ''),
                'displayName': getattr(a, 'display_name', ''),
                'agentType': getattr(a, 'agent_type', ''),
                'mechanism': getattr(a, 'mechanism', ''),
                'targetElement': getattr(a, 'target_element', ''),
                'selectivity': getattr(a, 'selectivity', 0)}
               for a in self._rows('BioextractionAgent')]
        response.media = {'ok': True, 'agents': out, 'count': len(out)}

    def on_get_systems(self, request, response):
        out = [{'name': getattr(s, 'name', ''),
                'displayName': getattr(s, 'display_name', ''),
                'variant': getattr(s, 'variant', ''),
                'product': getattr(s, 'product_name', ''),
                'source': getattr(s, 'source_system_name', '')}
               for s in self._rows('BiomineSystemDefinition')]
        response.media = {'ok': True, 'systems': out, 'count': len(out)}

    def on_get_yield(self, request, response, name):
        days = float((request.params or {}).get('days', 30.0) or 30.0)
        result = extraction_yield(self.manager, name, days=days)
        if not result.get('ok'):
            response.status = '404 Not Found'
        response.media = result

    def on_get_transfer(self, request, response, name):
        days = float((request.params or {}).get('days', 30.0) or 30.0)
        result = recovery_transfer(self.manager, name, days=days)
        if not result.get('ok'):
            response.status = '400 Bad Request'
        response.media = result

    def on_get_pathway(self, request, response, name):
        result = refinement_pathway(self.manager, name)
        if not result.get('ok'):
            response.status = '404 Not Found'
        response.media = result
