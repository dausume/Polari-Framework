"""
@module composition.composition_api

/api/composition/* — the arch-7 surface: nodes with DERIVED levels,
one-functional-many-constructions reports, routings with derived
step counts, audited promotions, archetypes and design matrices.
Every endpoint returns the engines' refusals verbatim: the surface
never softens an "I do not know" into an answer.

@consumers polariServer (constructed when 'composition' is enabled)
"""

import json

from objectTreeDecorators import treeObject, treeObjectInit

from composition.archetype_basis import archetype_report
from composition.data_refs import rows
from composition.design_matrix import matrix_report
from composition.functional_basis import variant_report
from composition.node_basis import composition_report, derive_level
from composition.realization import node_realization
from composition.routing_basis import (
    audit_promotion, routing_report, variant_step_counts,
)


def _float(request, key):
    raw = request.params.get(key)
    if raw in (None, ''):
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


class CompositionAPI(treeObject):
    @treeObjectInit
    def __init__(self, polServer):
        self.polServer = polServer
        self.apiName = '/api/composition'
        if polServer is not None:
            add = polServer.falconServer.add_route
            add('/api/composition/nodes', self, suffix='nodes')
            add('/api/composition/node/{node_name}', self,
                suffix='node')
            add('/api/composition/functional/{functional_name}',
                self, suffix='functional')
            add('/api/composition/routing/{routing_name}', self,
                suffix='routing')
            add('/api/composition/promotion/{op_name}', self,
                suffix='promotion')
            add('/api/composition/step-counts/{functional_name}',
                self, suffix='step_counts')
            add('/api/composition/archetypes', self,
                suffix='archetypes')
            add('/api/composition/archetype/{archetype_name}', self,
                suffix='archetype')
            add('/api/composition/matrix/{matrix_name}', self,
                suffix='matrix')

    def on_get_nodes(self, request, response):
        response.media = composition_report(self.manager)

    def on_get_node(self, request, response, node_name):
        level = derive_level(self.manager, node_name)
        realization = node_realization(self.manager, node_name)
        response.media = {
            'ok': level.get('ok', False), 'node': node_name,
            'level': level, 'realization': realization}

    def on_get_functional(self, request, response,
                          functional_name):
        response.media = variant_report(
            self.manager, functional_name,
            wound_diameter_mm=_float(request, 'wound_diameter_mm'),
            wall_mm=_float(request, 'wall_mm'))

    def on_get_routing(self, request, response, routing_name):
        response.media = routing_report(self.manager, routing_name)

    def on_get_promotion(self, request, response, op_name):
        response.media = audit_promotion(self.manager, op_name)

    def on_get_step_counts(self, request, response,
                           functional_name):
        response.media = variant_step_counts(self.manager,
                                             functional_name)

    def on_get_archetypes(self, request, response):
        out = []
        for row in rows(self.manager, 'PartArchetypeDefinition'):
            try:
                roles = json.loads(
                    getattr(row, 'role_refs_json', '') or '[]')
            except ValueError:
                roles = []
            out.append({'name': getattr(row, 'name', ''),
                        'displayName': getattr(row, 'display_name',
                                               ''),
                        'summary': getattr(row, 'summary', ''),
                        'roles': roles,
                        'designMatrix': getattr(
                            row, 'design_matrix_ref', '')})
        out.sort(key=lambda r: r['name'])
        response.media = {'ok': True, 'archetypes': out,
                          'count': len(out)}

    def on_get_archetype(self, request, response, archetype_name):
        response.media = archetype_report(self.manager,
                                          archetype_name)

    def on_get_matrix(self, request, response, matrix_name):
        response.media = matrix_report(self.manager, matrix_name)
