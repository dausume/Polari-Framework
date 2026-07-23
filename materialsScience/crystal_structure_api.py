"""
@cross-cutting
@module materialsScience.crystal_structure_api
@tags @xc:bindings

HTTP surface for crystal structures (ssp-1; PeersAPI pattern —
self-registering falcon routes):

  GET /api/msci/structures            every structure with headline
                                      facts (built on the fly; build
                                      refusals reported per row, never
                                      hidden)
  GET /api/msci/structures/{name}     one structure: row fields +
                                      facts + full atom list + bonds

Reads are pure except the lazy cache: a successful detail build
refreshes the row's built_facts_json (object coherence — the built
structure is inspectable AT the row via CRUDE).

@consumers
  - the crystal-structure frontend view (ssp-2)
@see /OVERLAP_MAP.md
"""

from objectTreeDecorators import treeObject, treeObjectInit
from materialsScience import crystal_ops


def _structure_rows(manager):
    table = (getattr(manager, 'objectTables', None) or {}).get(
        'CrystalStructureDefinition', {})
    rows = table.values() if isinstance(table, dict) else (table or [])
    return [row for row in rows if getattr(row, 'enabled', True)]


def find_structure(manager, name):
    for row in _structure_rows(manager):
        if getattr(row, 'name', '') == name:
            return row
    return None


class CrystalStructureAPI(treeObject):
    """Crystal-structure list + detail endpoints."""

    @treeObjectInit
    def __init__(self, polServer):
        self.polServer = polServer
        self.apiName = '/api/msci/structures'
        if polServer is not None:
            polServer.falconServer.add_route(
                '/api/msci/structures', self)
            polServer.falconServer.add_route(
                '/api/msci/structures/{name}', self, suffix='detail')

    def on_get(self, request, response):
        structures = []
        for row in _structure_rows(self.manager):
            entry = {
                'name': getattr(row, 'name', ''),
                'displayName': getattr(row, 'display_name', ''),
                'materialName': getattr(row, 'material_name', ''),
                'spaceGroup': getattr(row, 'space_group', 0),
                'description': getattr(row, 'description', ''),
            }
            verdict = crystal_ops.structure_facts(row)
            if verdict['ok']:
                entry['facts'] = verdict['facts']
            else:
                entry['buildError'] = verdict.get('error', '')
                entry['suggestion'] = verdict.get('suggestion')
            structures.append(entry)
        structures.sort(key=lambda s: s['name'])
        response.media = {'ok': True, 'count': len(structures),
                          'structures': structures}

    def on_get_detail(self, request, response, name):
        row = find_structure(self.manager, name)
        if row is None:
            response.status = '404 Not Found'
            response.media = {
                'ok': False,
                'error': f"no CrystalStructureDefinition named "
                         f"'{name}'"}
            return
        report = crystal_ops.refresh_built_facts(row, self.manager)
        if not report['ok']:
            response.media = {'ok': False, 'name': name, **{
                k: v for k, v in report.items() if k != 'ok'}}
            return
        response.media = {
            'ok': True,
            'name': getattr(row, 'name', ''),
            'displayName': getattr(row, 'display_name', ''),
            'description': getattr(row, 'description', ''),
            'materialName': getattr(row, 'material_name', ''),
            'spaceGroup': getattr(row, 'space_group', 0),
            'spaceGroupSetting': getattr(row, 'space_group_setting', 1),
            'bondCutoffScale': getattr(row, 'bond_cutoff_scale', 1.15),
            'provenance': getattr(row, 'provenance_id', ''),
            'notes': getattr(row, 'notes', ''),
            'facts': report['facts'],
            'cell': report['cell'],
            'atoms': report['atoms'],
            'bonds': report['bonds'],
        }
