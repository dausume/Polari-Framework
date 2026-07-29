"""
@module magnetics.magnet_api

/api/magnetics/* — the Section-A surface: option catalog with
realization gates, role vocabulary, derived viability + the casual
role+form search, the powder designer's composite predictor, and the
laddered best-per-realization answer.

@consumers polariServer (constructed when 'magnetics' is enabled)
"""

from objectTreeDecorators import treeObject, treeObjectInit

from magnetics.magnet_analysis import (
    composite_predict, gates_for, laddered_answer, viability_matrix,
    _named, _rows,
)


class MagneticsAPI(treeObject):
    @treeObjectInit
    def __init__(self, polServer):
        self.polServer = polServer
        self.apiName = '/api/magnetics'
        if polServer is not None:
            add = polServer.falconServer.add_route
            add('/api/magnetics/catalog', self, suffix='catalog')
            add('/api/magnetics/roles', self, suffix='roles')
            add('/api/magnetics/viability/{option_name}', self,
                suffix='viability')
            add('/api/magnetics/search', self, suffix='search')
            add('/api/magnetics/powders', self, suffix='powders')
            add('/api/magnetics/predict', self, suffix='predict')
            add('/api/magnetics/ladder', self, suffix='ladder')

    def on_get_catalog(self, request, response):
        rows = []
        for opt in _rows(self.manager, 'MagneticMaterialOption'):
            gates = gates_for(self.manager, opt)
            rows.append({
                'name': getattr(opt, 'name', ''),
                'displayName': getattr(opt, 'display_name', ''),
                'family': getattr(opt, 'family', ''),
                'itemRef': getattr(opt, 'item_ref', ''),
                'msciMaterialRef': getattr(opt, 'msci_material_ref',
                                           ''),
                'forms': getattr(opt, 'forms_json', '[]'),
                'properties': getattr(opt, 'properties_json', '{}'),
                'referenceOnly': getattr(opt, 'is_reference_only',
                                         False),
                'notes': getattr(opt, 'notes', ''),
                **gates})
        rows.sort(key=lambda r: (r['family'], r['name']))
        response.media = {'ok': True, 'options': rows,
                          'count': len(rows)}

    def on_get_roles(self, request, response):
        rows = []
        for role in _rows(self.manager, 'MaterialUseRole'):
            rows.append({
                'name': getattr(role, 'name', ''),
                'displayName': getattr(role, 'display_name', ''),
                'description': getattr(role, 'description', ''),
                'predicates': getattr(role, 'predicates_json', '{}'),
                'applicableForms': getattr(
                    role, 'applicable_forms_json', '[]'),
                'honestyNote': getattr(role, 'honesty_note', ''),
            })
        response.media = {'ok': True, 'roles': rows,
                          'count': len(rows)}

    def on_get_viability(self, request, response, option_name):
        opt = _named(self.manager, 'MagneticMaterialOption',
                     option_name)
        if opt is None:
            response.status = '404 Not Found'
            response.media = {'ok': False,
                              'refusal': f'no MagneticMaterialOption '
                                         f'named "{option_name}"'}
            return
        from magnetics.magnet_analysis import role_viability
        verdicts = [role_viability(self.manager, opt, role)
                    for role in _rows(self.manager,
                                      'MaterialUseRole')]
        response.media = {'ok': True, 'option': option_name,
                          'gates': gates_for(self.manager, opt),
                          'roles': verdicts}

    def on_get_search(self, request, response):
        out = viability_matrix(
            self.manager,
            role_name=request.params.get('role', ''),
            form=request.params.get('form', ''))
        if not out.get('ok'):
            response.status = '404 Not Found'
        response.media = out

    def on_get_powders(self, request, response):
        rows = []
        for p in _rows(self.manager, 'MagneticPowderDefinition'):
            rows.append({
                'name': getattr(p, 'name', ''),
                'displayName': getattr(p, 'display_name', ''),
                'isTheoretical': getattr(p, 'is_theoretical', False),
                'itemRef': getattr(p, 'item_ref', ''),
                'muI': getattr(p, 'mu_i', None),
                'bSatT': getattr(p, 'b_sat_t', None),
                'hCkAm': getattr(p, 'h_c_ka_m', None),
                'bRT': getattr(p, 'b_r_t', None),
                'densityKgM3': getattr(p, 'density_kg_m3', None),
                'sigmaSM': getattr(p, 'sigma_s_m', None),
                'provenance': getattr(p, 'property_provenance', ''),
                'notes': getattr(p, 'notes', ''),
            })
        response.media = {'ok': True, 'powders': rows,
                          'count': len(rows)}

    def on_get_predict(self, request, response):
        p = request.params
        try:
            vol = float(p.get('volPct', 0)) / 100.0
        except ValueError:
            vol = 0.0
        out = composite_predict(
            self.manager, p.get('powder', ''),
            p.get('matrix', ''), vol)
        if not out.get('ok'):
            response.status = '400 Bad Request'
        response.media = out

    def on_get_ladder(self, request, response):
        role = request.params.get('role', '')
        if not role:
            response.status = '400 Bad Request'
            response.media = {'ok': False,
                              'refusal': '?role= is required '
                                         '(MaterialUseRole.name)'}
            return
        out = laddered_answer(self.manager, role,
                              form=request.params.get('form', ''))
        if not out.get('ok'):
            response.status = '404 Not Found'
        response.media = out
