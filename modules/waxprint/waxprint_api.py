"""
@cross-cutting
@module waxprint.waxprint_api

Thin Falcon HTTP shell over the wax-printer sim — list the rows, and run
the two-zone auger melt (wp-1). Business logic is in melt_analysis; this
file only parses requests and shapes JSON. Route/handler convention
mirrors aquaponics/hydraulics_api.

Routes:
  GET  /api/waxprint/capability
  GET  /api/waxprint/materials
  GET  /api/waxprint/assemblies
  GET  /api/waxprint/feedstocks
  GET  /api/waxprint/conditions
  POST /api/waxprint/melt          {assembly, feedstock, condition}
  GET  /api/waxprint/melt?assembly=&feedstock=&condition=
"""

import json

from objectTreeDecorators import treeObject, treeObjectInit
from waxprint.custom import melt_analysis
from waxprint.custom import bead_analysis
from waxprint.custom import movement_analysis
from waxprint.custom import print_optimizer

_INTERNAL_ATTRS = {
    'manager', 'id', 'branch', 'inTree', 'objectTyping', 'objectRefs',
    'isDeleted', 'polServer', 'apiName', 'falconServer',
}


def row_public(obj):
    """Serialize a treeObject row to a JSON-safe dict of its declared
    fields (drop framework internals + anything not a scalar/list/dict)."""
    out = {}
    for k, v in vars(obj).items():
        if k.startswith('_') or k in _INTERNAL_ATTRS:
            continue
        if isinstance(v, (str, int, float, bool)) or v is None:
            out[k] = v
        elif isinstance(v, (list, dict)):
            out[k] = v
    return out


def _list_rows(manager, class_name):
    table = (getattr(manager, 'objectTables', {}) or {}).get(class_name, {}) or {}
    return [row_public(o) for o in table.values()]


class WaxPrintAPI(treeObject):
    """Endpoints for the wax 3D-printer simulation (wp-1: melt)."""

    @treeObjectInit
    def __init__(self, polServer):
        self.polServer = polServer
        self.apiName = '/api/waxprint'
        if polServer is not None:
            add = polServer.falconServer.add_route
            add('/api/waxprint/capability', self, suffix='capability')
            add('/api/waxprint/materials', self, suffix='materials')
            add('/api/waxprint/assemblies', self, suffix='assemblies')
            add('/api/waxprint/feedstocks', self, suffix='feedstocks')
            add('/api/waxprint/conditions', self, suffix='conditions')
            add('/api/waxprint/melt', self, suffix='melt')
            add('/api/waxprint/commands', self, suffix='commands')
            add('/api/waxprint/voxel', self, suffix='voxel')
            add('/api/waxprint/resolution-profile', self,
                suffix='resolution_profile')
            add('/api/waxprint/movements', self, suffix='movements')
            add('/api/waxprint/optimize', self, suffix='optimize')

    # ---- lists ----
    def on_get_capability(self, request, response):
        response.media = {
            'ok': True,
            'module': 'waxprint',
            'phase': 'wp-1..4 (two-zone melt+safety, bead/voxel+fan, '
                     'movement patterns, optimizer/trials)',
            'endpoints': ['/melt', '/voxel', '/resolution-profile',
                          '/movements', '/optimize'],
            'counts': {
                'materials': len(_list_rows(self.manager,
                                            'DeviceMaterialDefinition')),
                'assemblies': len(_list_rows(self.manager,
                                             'PrinterAssemblyDefinition')),
                'feedstocks': len(_list_rows(self.manager,
                                             'WaxFeedstockDefinition')),
                'conditions': len(_list_rows(self.manager,
                                             'PrintConditionDefinition')),
            },
        }

    def on_get_commands(self, request, response):
        """The no-code WaxPrintOperation command vocabulary — each
        command's inputs, outputs, and whether it's computable, plus the
        scalar OVERRIDE inputs every physics command accepts. Lets an
        author discover what is manipulable from a solution graph."""
        from waxprint.custom.commands import COMMAND_SPECS, OVERRIDE_INPUTS
        response.media = {
            'ok': True, 'operation': 'WaxPrintOperation',
            'override_inputs': OVERRIDE_INPUTS, 'commands': COMMAND_SPECS}

    def on_get_materials(self, request, response):
        response.media = {'ok': True,
                          'materials': _list_rows(self.manager,
                                                  'DeviceMaterialDefinition')}

    def on_get_assemblies(self, request, response):
        response.media = {'ok': True,
                          'assemblies': _list_rows(self.manager,
                                                   'PrinterAssemblyDefinition')}

    def on_get_feedstocks(self, request, response):
        response.media = {'ok': True,
                          'feedstocks': _list_rows(self.manager,
                                                   'WaxFeedstockDefinition')}

    def on_get_conditions(self, request, response):
        response.media = {'ok': True,
                          'conditions': _list_rows(self.manager,
                                                   'PrintConditionDefinition')}

    # ---- melt (GET convenience + POST) ----
    def on_get_melt(self, request, response):
        params = request.params or {}
        self._do_melt(response, params.get('assembly', ''),
                      params.get('feedstock', ''), params.get('condition', ''))

    def on_post_melt(self, request, response):
        try:
            body = json.load(request.bounded_stream) if request.content_length \
                else {}
        except Exception as e:
            response.status = '400 Bad Request'
            response.media = {'ok': False, 'error': f'bad JSON payload: {e}'}
            return
        self._do_melt(response, body.get('assembly', ''),
                      body.get('feedstock', ''), body.get('condition', ''))

    def _do_melt(self, response, assembly, feedstock, condition):
        if not (assembly and feedstock and condition):
            response.status = '400 Bad Request'
            response.media = {
                'ok': False,
                'error': 'assembly, feedstock and condition are all required'}
            return
        out = melt_analysis.run_melt(self.manager, assembly, feedstock,
                                     condition)
        if not out.get('ok'):
            response.status = '404 Not Found'
        response.media = out

    # ---- voxel + resolution profile (wp-2) ----
    def _triple(self, request):
        p = request.params or {}
        return p.get('assembly', ''), p.get('feedstock', ''), \
            p.get('condition', '')

    def on_get_voxel(self, request, response):
        a, f, c = self._triple(request)
        if not (a and f and c):
            response.status = '400 Bad Request'
            response.media = {'ok': False,
                              'error': 'assembly, feedstock, condition required'}
            return
        out = bead_analysis.run_voxel(self.manager, a, f, c)
        if not out.get('ok'):
            response.status = '404 Not Found'
        response.media = out

    def on_get_resolution_profile(self, request, response):
        a, f, c = self._triple(request)
        if not (a and f and c):
            response.status = '400 Bad Request'
            response.media = {'ok': False,
                              'error': 'assembly, feedstock, condition required'}
            return
        heights = None
        raw = (request.params or {}).get('heights')
        if raw:
            try:
                heights = [float(x) for x in raw.split(',')]
            except ValueError:
                heights = None
        out = bead_analysis.run_resolution_profile(self.manager, a, f, c,
                                                   heights_mm=heights)
        if not out.get('ok'):
            response.status = '404 Not Found'
        response.media = out

    def on_get_movements(self, request, response):
        a, f, c = self._triple(request)
        if not (a and f and c):
            response.status = '400 Bad Request'
            response.media = {'ok': False,
                              'error': 'assembly, feedstock, condition required'}
            return
        height = (request.params or {}).get('height')
        try:
            height_mm = float(height) if height else None
        except ValueError:
            height_mm = None
        out = movement_analysis.run_movements(self.manager, a, f, c,
                                              height_mm=height_mm)
        if not out.get('ok'):
            response.status = '404 Not Found'
        response.media = out

    # ---- optimizer / trials sweep (wp-4) ----
    def on_post_optimize(self, request, response):
        try:
            body = json.load(request.bounded_stream) if request.content_length \
                else {}
        except Exception as e:
            response.status = '400 Bad Request'
            response.media = {'ok': False, 'error': f'bad JSON payload: {e}'}
            return
        assemblies = body.get('assemblies') or body.get('assembly_names')
        feedstocks = body.get('feedstocks') or body.get('feedstock_names')
        if not assemblies or not feedstocks:
            response.status = '400 Bad Request'
            response.media = {
                'ok': False,
                'error': 'assemblies[] and feedstocks[] are required'}
            return
        out = print_optimizer.optimize(
            self.manager, assemblies, feedstocks,
            spec=body.get('spec'), weights=body.get('weights'),
            top_n=int(body.get('top_n', 8)))
        if not out.get('ok'):
            response.status = '404 Not Found'
        response.media = out
