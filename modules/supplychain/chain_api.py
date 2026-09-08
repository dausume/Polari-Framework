"""
@cross-cutting
@module supplychain.chain_api
@tags @xc:bindings

HTTP surface for chain-1 bio supply-chain accounting:

  GET /api/supplychain/chains                     the chains + node counts.
  GET /api/supplychain/chains/{name}/inventory    materials + food +
                                                  carbon + nutrient rollup.
  GET /api/supplychain/chains/{name}/carbon       carbon sinks vs sources.
  GET /api/supplychain/chains/{name}/dependencies unmet inputs (if any).

Nodes / flows / chains are edited through CRUDE (object-coherence).

@consumers
  - supplychain frontend (later)
@see nutrition/ aquaponics/ tanks/ microalgae/ biomining/ waxsupply/
"""

from objectTreeDecorators import treeObject, treeObjectInit
from supplychain.custom.chain_analysis import (
    carbon_balance, chain_inventory, dependency_check,
)


class SupplyChainAPI(treeObject):
    """chain-1 endpoints."""

    @treeObjectInit
    def __init__(self, polServer):
        self.polServer = polServer
        self.apiName = '/api/supplychain'
        if polServer is not None:
            polServer.falconServer.add_route(
                '/api/supplychain/chains', self, suffix='chains')
            polServer.falconServer.add_route(
                '/api/supplychain/chains/{name}/inventory', self,
                suffix='inventory')
            polServer.falconServer.add_route(
                '/api/supplychain/chains/{name}/carbon', self,
                suffix='carbon')
            polServer.falconServer.add_route(
                '/api/supplychain/chains/{name}/dependencies', self,
                suffix='dependencies')

    def _rows(self, class_name):
        table = (self.manager.objectTables or {}).get(class_name, {})
        return list(table.values()) if isinstance(table, dict) \
            else list(table)

    def on_get_chains(self, request, response):
        import json
        out = []
        for c in self._rows('SupplyChainDefinition'):
            try:
                nodes = json.loads(
                    getattr(c, 'node_names_json', '[]') or '[]')
            except Exception:
                nodes = []
            out.append({'name': getattr(c, 'name', ''),
                        'displayName': getattr(c, 'display_name', ''),
                        'nodeCount': len(nodes)})
        response.media = {'ok': True, 'chains': out}

    def on_get_inventory(self, request, response, name):
        result = chain_inventory(self.manager, name)
        if not result.get('ok'):
            response.status = '404 Not Found'
        response.media = result

    def on_get_carbon(self, request, response, name):
        result = carbon_balance(self.manager, name)
        if not result.get('ok'):
            response.status = '404 Not Found'
        response.media = result

    def on_get_dependencies(self, request, response, name):
        result = dependency_check(self.manager, name)
        if not result.get('ok'):
            response.status = '404 Not Found'
        response.media = result
