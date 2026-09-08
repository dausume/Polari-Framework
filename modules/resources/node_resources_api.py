"""
@cross-cutting
@module resources.node_resources_api

NodeResourcesAPI (res-1): the /api/topology/resources* surface.
Reads serve the Topology tab and the admission advisor (res-4);
writes are observations only — refresh (this backend observes
itself, or pulls a node's system_info_url) and ingest (a node
pushes its own specs, pol-CLI idiom). The API never guesses:
un-observed nodes stay resource_source='unknown' with the reason
and the knob to fix it.

@consumers
  - polariServer (instantiated next to TopologyAPI)
  - polari-platform-angular /topology page
  - resources.node_resources_selftest (handler-level, fake manager)
"""

import json

from objectTreeDecorators import treeObject, treeObjectInit

from resources.custom.node_resources import (
    fetch_remote_specs, ingest_node_specs, inventory,
    machine_resources_dict, refresh_local_machine,
)


class NodeResourcesAPI(treeObject):
    """Node resource inventory endpoints."""

    @treeObjectInit
    def __init__(self, polServer):
        self.polServer = polServer
        self.apiName = '/api/topology/resources'
        if polServer is not None:
            add = polServer.falconServer.add_route
            add('/api/topology/resources', self, suffix='inventory')
            add('/api/topology/nodes/{node_name}/resources', self,
                suffix='node')
            add('/api/topology/nodes/{node_name}/refresh-resources',
                self, suffix='refresh')

    # ---- helpers ----------------------------------------------------

    def _machine(self, node_name):
        tables = getattr(self.manager, 'objectTables', None) or {}
        for row in (tables.get('PolariNodeMachine') or {}).values():
            if getattr(row, 'name', '') == node_name:
                return row
        return None

    def _payload(self, request):
        try:
            raw = request.bounded_stream.read()
            return (json.loads(raw) if raw else {}), None
        except Exception as e:
            return None, f'bad JSON payload: {e}'

    def _refuse(self, response, error, status='400 Bad Request'):
        response.status = status
        response.media = {'ok': False, 'error': error}

    # ---- reads ------------------------------------------------------

    def on_get_inventory(self, request, response):
        response.media = inventory(self.manager)

    def on_get_node(self, request, response, node_name):
        machine = self._machine(node_name)
        if machine is None:
            return self._refuse(
                response,
                f'no PolariNodeMachine named "{node_name}"',
                '404 Not Found')
        response.media = {'ok': True,
                          'node': machine_resources_dict(machine)}

    # ---- observations -----------------------------------------------

    def on_post_refresh(self, request, response, node_name):
        """Re-observe a node: the local host reads its own isoSys;
        a remote node is pulled from its system_info_url knob."""
        machine = self._machine(node_name)
        if machine is None:
            return self._refuse(
                response,
                f'no PolariNodeMachine named "{node_name}"',
                '404 Not Found')
        if getattr(machine, 'ssh_alias', ''):
            report = fetch_remote_specs(self.manager, node_name)
        else:
            report = refresh_local_machine(self.manager, node_name)
        if not report.get('ok'):
            response.status = '409 Conflict'
        response.media = report

    def on_post_node(self, request, response, node_name):
        """Ingest specs a node reported about itself (push path)."""
        payload, err = self._payload(request)
        if err:
            return self._refuse(response, err)
        report = ingest_node_specs(self.manager, node_name, payload)
        if not report.get('ok'):
            response.status = '400 Bad Request'
        response.media = report
