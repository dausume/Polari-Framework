"""
@module microchip.chip_api

The design-level traversal interface over HTTP:
  GET /api/microchip/levels            — the ladder + live/refusing
  GET /api/microchip/designs           — the design hierarchies
  GET /api/microchip/designs/{design}  — one design's full tree
  GET /api/microchip/nodes/{name}      — traverse: node + up chain
                                         + children + resolved
                                         artifact/citation links

Read-only at this stage — design nodes are rows, so CRUDE already
edits them; acts (e.g. 'synthesize') arrive with their S-phases.

@consumers
  - polariServer (route registration, gated on feature presence)
  - microchip.microchip_selftest (function level)
"""

from objectTreeDecorators import treeObject, treeObjectInit

from microchip.chip_families_basis import (
    families_report, family_report,
)
from microchip.custom.chip_traverse import (
    design_tree, levels_report, traverse,
)


class MicrochipAPI(treeObject):
    """The ladder-traversal read surface."""

    @treeObjectInit
    def __init__(self, polServer):
        self.polServer = polServer
        self.apiName = '/api/microchip'
        if polServer is not None:
            add = polServer.falconServer.add_route
            add('/api/microchip/levels', self, suffix='levels')
            add('/api/microchip/designs', self, suffix='designs')
            add('/api/microchip/designs/{design}', self,
                suffix='design')
            add('/api/microchip/nodes/{name}', self, suffix='node')
            # §2c rank-1 device families (fet live, shells honest)
            add('/api/microchip/families', self, suffix='families')
            add('/api/microchip/families/{name}', self,
                suffix='family')

    def on_get_levels(self, request, response):
        response.media = {'ok': True,
                          'levels': levels_report(self.manager)}

    def on_get_designs(self, request, response):
        tables = getattr(self.manager, 'objectTables', None) or {}
        designs = {}
        for row in (tables.get('MicrochipDesignNode')
                    or {}).values():
            design = getattr(row, 'design', '')
            entry = designs.setdefault(
                design, {'design': design, 'nodeCount': 0,
                         'statuses': {}})
            entry['nodeCount'] += 1
            status = getattr(row, 'status', '')
            entry['statuses'][status] = (
                entry['statuses'].get(status, 0) + 1)
        response.media = {'ok': True,
                          'designs': sorted(
                              designs.values(),
                              key=lambda d: d['design'])}

    def on_get_design(self, request, response, design):
        report = design_tree(self.manager, design)
        if not report.get('ok'):
            response.status = '404 Not Found'
        response.media = report

    def on_get_node(self, request, response, name):
        report = traverse(self.manager, name)
        if not report.get('ok'):
            response.status = '404 Not Found'
        response.media = report

    def on_get_families(self, request, response):
        response.media = families_report(self.manager)

    def on_get_family(self, request, response, name):
        report = family_report(self.manager, name)
        if not report.get('ok'):
            response.status = '404 Not Found'
        response.media = report
