"""
@module computers.computers_api

cmp-c-4 backend surface. GET-only v1 (assemblies/profiles are
CRUDE-editable rows; the derived payloads here are views):

  GET /api/computers                     taxonomy + profiles +
                                         assemblies + fit matrix
  GET /api/computers/assembly/{name}     gate report + composition
                                         view for one assembly
  GET /api/computers/fit/{assembly}/{profile}
                                         one evidence-bearing fit

Engine refusals pass through verbatim — the surface never softens
an 'I do not know'.

@consumers
  - polariServer (constructed behind _feature_available)
  - /display/computers page seeds (api-json-panel paths)
"""

import json

from objectTreeDecorators import treeObject, treeObjectInit

from computers.computers_basis import field_of
from computers.computers_fit import fit_matrix, fit_profile
from computers.computers_gates import (
    assembly_gate_report, composition_view,
)
from computers.computers_ports import (
    interconnect_matrix, port_budget_gates,
)


class ComputersAPI(treeObject):

    @treeObjectInit
    def __init__(self, polServer):
        self.polServer = polServer
        self.apiName = '/api/computers'
        if polServer is not None:
            add = polServer.falconServer.add_route
            add('/api/computers', self, suffix='catalog')
            add('/api/computers/assembly/{assembly_name}', self,
                suffix='assembly')
            add('/api/computers/fit/{assembly_name}'
                '/{profile_name}', self, suffix='fit')
            # cmp-c-6: interconnect vocabulary + per-build matrix.
            add('/api/computers/interconnects', self,
                suffix='interconnects')
            add('/api/computers/interconnects/build/{build_name}',
                self, suffix='build_matrix')

    def _table(self, class_name):
        tables = getattr(self.manager, 'objectTables', None) or {}
        return list((tables.get(class_name) or {}).values())

    def _published(self, class_name):
        return [r for r in self._table(class_name)
                if field_of(r, 'published', True)]

    def _parts_by_name(self):
        return {field_of(p, 'name'): p
                for p in self._table('ComputerPartDefinition')}

    def _build(self, name):
        for b in self._table('ComputerBuildDefinition'):
            if field_of(b, 'name') == name:
                return b
        return None

    def _assembly(self, name):
        for a in self._table('ComputerAssemblyDefinition'):
            if field_of(a, 'name') == name:
                return a
        return None

    def on_get_catalog(self, request, response):
        classes = sorted(
            self._published('ComputerPartClassDefinition'),
            key=lambda r: field_of(r, 'name'))
        profiles = sorted(
            self._published('ComputerProfileDefinition'),
            key=lambda r: field_of(r, 'name'))
        assemblies = self._published('ComputerAssemblyDefinition')
        parts_by_name = self._parts_by_name()
        builds = [self._build(field_of(a, 'build_ref'))
                  for a in assemblies]
        builds = [b for b in builds if b is not None]
        response.media = {
            'ok': True,
            'taxonomy': [{
                'kind': field_of(c, 'name'),
                'display_name': field_of(c, 'display_name'),
                'summary': field_of(c, 'summary'),
                'declared_specs': json.loads(
                    field_of(c, 'declared_specs_json', '[]')
                    or '[]'),
                'interface_specs': json.loads(
                    field_of(c, 'interface_specs_json', '[]')
                    or '[]'),
                'gaps_note': field_of(c, 'gaps_note'),
            } for c in classes],
            'profiles': [{
                'name': field_of(p, 'name'),
                'display_name': field_of(p, 'display_name'),
                'use_case': field_of(p, 'use_case'),
                'floors': json.loads(
                    field_of(p, 'floors_json', '{}') or '{}'),
                'db_binding': field_of(p, 'db_binding', 'none'),
                'planner_class': field_of(p, 'planner_class'),
                'rationale': field_of(p, 'rationale'),
            } for p in profiles],
            'assemblies': [{
                'name': field_of(a, 'name'),
                'display_name': field_of(a, 'display_name'),
                'build_ref': field_of(a, 'build_ref'),
                'notes': field_of(a, 'notes'),
            } for a in assemblies],
            'fitMatrix': fit_matrix(profiles, builds,
                                    parts_by_name),
        }

    def on_get_assembly(self, request, response, assembly_name):
        assembly = self._assembly(assembly_name)
        if assembly is None:
            response.status = '404 Not Found'
            response.media = {'ok': False,
                              'error': f'no assembly named '
                                       f'"{assembly_name}"'}
            return
        build = self._build(field_of(assembly, 'build_ref'))
        if build is None:
            response.status = '422 Unprocessable Entity'
            response.media = {
                'ok': False,
                'error': f'assembly "{assembly_name}" names '
                         f'build "{field_of(assembly, "build_ref")}"'
                         f' which does not exist — fix build_ref',
            }
            return
        parts_by_name = self._parts_by_name()
        response.media = {
            'ok': True,
            'gateReport': assembly_gate_report(assembly, build,
                                               parts_by_name),
            'compositionView': composition_view(assembly, build,
                                                parts_by_name),
        }

    def _interconnects_by_name(self):
        return {field_of(r, 'name'): r
                for r in self._published('InterconnectDefinition')}

    def on_get_interconnects(self, request, response):
        rows = sorted(self._interconnects_by_name().values(),
                      key=lambda r: field_of(r, 'name'))
        response.media = {
            'ok': True,
            'interconnects': [{
                'name': field_of(r, 'name'),
                'display_name': field_of(r, 'display_name'),
                'kind': field_of(r, 'kind'),
                'carries': field_of(r, 'carries'),
                'attachment': field_of(r, 'attachment'),
                'summary': field_of(r, 'summary'),
                'gaps_note': field_of(r, 'gaps_note'),
            } for r in rows],
            'note': 'tokens match parts\' ports_provided/'
                    'ports_required declarations (specs_json); '
                    'adding a connector standard is a row',
        }

    def on_get_build_matrix(self, request, response, build_name):
        build = self._build(build_name)
        if build is None:
            response.status = '404 Not Found'
            response.media = {'ok': False,
                              'error': f'no build named '
                                       f'"{build_name}"'}
            return
        from computers.computers_gates import _parts_of
        parts_by_name = self._parts_by_name()
        parts = _parts_of(build, parts_by_name)
        response.media = {
            'ok': True,
            'matrix': interconnect_matrix(
                parts, self._interconnects_by_name()),
            'portBudget': port_budget_gates(build, parts_by_name),
        }

    def on_get_fit(self, request, response, assembly_name,
                   profile_name):
        assembly = self._assembly(assembly_name)
        profile = None
        for p in self._table('ComputerProfileDefinition'):
            if field_of(p, 'name') == profile_name:
                profile = p
        missing = []
        if assembly is None:
            missing.append(f'assembly "{assembly_name}"')
        if profile is None:
            missing.append(f'profile "{profile_name}"')
        build = self._build(field_of(assembly, 'build_ref')) \
            if assembly is not None else None
        if assembly is not None and build is None:
            missing.append(f'build '
                           f'"{field_of(assembly, "build_ref")}"')
        if missing:
            response.status = '404 Not Found'
            response.media = {'ok': False,
                              'error': 'not found: '
                                       + ', '.join(missing)}
            return
        response.media = {
            'ok': True,
            'fit': fit_profile(profile, build,
                               self._parts_by_name()),
        }
