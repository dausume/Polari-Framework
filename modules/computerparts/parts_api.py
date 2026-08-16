"""
@module computerparts.parts_api

GET /api/computerparts            -> parts + builds (derived
                                     totals + assembly checks)
GET /api/computerparts/{build}    -> one build's full report

Thin Falcon shell — logic lives in parts_basis / parts_assembly.

@consumers
  - polariServer via module_endpoints
  - polari-platform-angular /ai-hosting (buy section detail)
"""

from objectTreeDecorators import treeObject, treeObjectInit

from computerparts.parts_assembly import assembly_check
from computerparts.parts_basis import build_report


class ComputerPartsAPI(treeObject):
    @treeObjectInit
    def __init__(self, polServer):
        self.polServer = polServer
        self.apiName = '/api/computerparts'
        if polServer is not None:
            add = polServer.falconServer.add_route
            add('/api/computerparts', self, suffix='catalog')
            add('/api/computerparts/{build}', self, suffix='build')

    def _table(self, class_name):
        return (getattr(self.manager, 'objectTables', None)
                or {}).get(class_name, {})

    def _parts_by_name(self):
        return {getattr(r, 'name', ''): r
                for r in self._table(
                    'ComputerPartDefinition').values()
                if getattr(r, 'published', True)}

    def on_get_catalog(self, request, response):
        parts_by_name = self._parts_by_name()
        parts = []
        for r in parts_by_name.values():
            parts.append({
                'name': r.name, 'title': r.title, 'kind': r.kind,
                'model': getattr(r, 'model', ''),
                'condition': getattr(r, 'condition', ''),
                'specs_json': getattr(r, 'specs_json', '{}'),
                'price_amount': getattr(r, 'price_amount', 0.0),
                'price_unit': getattr(r, 'price_unit', 'USD'),
                'price_as_of': getattr(r, 'price_as_of', ''),
                'price_source': getattr(r, 'price_source', ''),
                'price_note': getattr(r, 'price_note', ''),
                'notes': getattr(r, 'notes', ''),
            })
        parts.sort(key=lambda p: (p['kind'], p['name']))
        builds = []
        for b in self._table('ComputerBuildDefinition').values():
            if not getattr(b, 'published', True):
                continue
            report = build_report(b, parts_by_name)
            report['assembly'] = assembly_check(b, parts_by_name)
            builds.append(report)
        builds.sort(key=lambda b: b['total_usd'])
        response.media = {'ok': True, 'parts': parts,
                          'builds': builds}

    def on_get_build(self, request, response, build):
        parts_by_name = self._parts_by_name()
        for b in self._table('ComputerBuildDefinition').values():
            if getattr(b, 'name', '') == build:
                report = build_report(b, parts_by_name)
                report['assembly'] = assembly_check(b,
                                                    parts_by_name)
                response.media = {'ok': True, 'build': report}
                return
        response.status = '404 Not Found'
        response.media = {'ok': False,
                          'error': f'no build {build!r}'}
