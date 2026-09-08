"""
@module magnetics.magnet_api

/api/magnetics/* — the Section-A surface: option catalog with
realization gates, role vocabulary, derived viability + the casual
role+form search, the powder designer's composite predictor, and the
laddered best-per-realization answer.

@consumers polariServer (constructed when 'magnetics' is enabled)
"""

from objectTreeDecorators import treeObject, treeObjectInit

from magnetics.custom.magnet_analysis import (
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
            add('/api/magnetics/circuits', self, suffix='circuits')
            add('/api/magnetics/solve/{circuit_name}', self,
                suffix='solve')
            add('/api/magnetics/parity/{circuit_name}', self,
                suffix='parity')
            add('/api/magnetics/layouts', self, suffix='layouts')
            add('/api/magnetics/layout/{layout_name}/network', self,
                suffix='layout_network')
            add('/api/magnetics/layout/{layout_name}/cost', self,
                suffix='layout_cost')
            add('/api/magnetics/layout/{layout_name}/dryfit', self,
                suffix='layout_dryfit')
            add('/api/magnetics/fieldviews', self,
                suffix='fieldviews')
            add('/api/magnetics/fieldview/{view_name}', self,
                suffix='fieldview')
            add('/api/magnetics/fieldview-group/{group_name}', self,
                suffix='fieldview_group')
            # mag-12: what measured evidence WOULD support — a
            # suggestion surface, never a mutation.
            add('/api/magnetics/promotion', self,
                suffix='promotion')
            add('/api/magnetics/promotion/{option_name}', self,
                suffix='promotion_one')

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
        from magnetics.custom.magnet_analysis import role_viability
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

    def on_get_promotion(self, request, response):
        from magnetics.custom.realization_promotion import promotion_report
        response.media = promotion_report(self.manager)

    def on_get_promotion_one(self, request, response, option_name):
        from magnetics.custom.realization_promotion import promotion_report
        out = promotion_report(self.manager,
                               option_name=option_name)
        if not out.get('ok'):
            response.status = '404 Not Found'
        response.media = out

    def on_get_circuits(self, request, response):
        rows = []
        for c in _rows(self.manager, 'MagneticCircuitDefinition'):
            name = getattr(c, 'name', '')
            rows.append({
                'name': name,
                'description': getattr(c, 'description', ''),
                'analyses': getattr(c, 'analyses_json', '[]'),
                'elements': [getattr(e, 'name', '') for e in _rows(
                    self.manager, 'MagneticElementDefinition')
                    if getattr(e, 'circuit_name', '') == name],
            })
        response.media = {'ok': True, 'circuits': rows,
                          'count': len(rows)}

    def on_get_solve(self, request, response, circuit_name):
        from magnetics.magnetic_netlist_seed import run_analyses
        out = run_analyses(self.manager, circuit_name)
        if not out.get('ok'):
            response.status = '404 Not Found'
        response.media = out

    def on_get_parity(self, request, response, circuit_name):
        from magnetics.magnetic_netlist_seed import parity_run
        out = parity_run(self.manager, circuit_name)
        if not out.get('ok'):
            response.status = '409 Conflict'
        response.media = out

    def on_get_layouts(self, request, response):
        rows = []
        for lay in _rows(self.manager, 'BlockLayoutDefinition'):
            name = getattr(lay, 'name', '')
            rows.append({
                'name': name,
                'displayName': getattr(lay, 'display_name', ''),
                'description': getattr(lay, 'description', ''),
                'grid': getattr(lay, 'grid_json', '{}'),
                'placements': [getattr(p, 'name', '') for p in
                               _rows(self.manager, 'BlockPlacement')
                               if getattr(p, 'layout_name', '')
                               == name],
            })
        response.media = {'ok': True, 'layouts': rows,
                          'count': len(rows)}

    def on_get_layout_network(self, request, response, layout_name):
        from magnetics.custom.magnet_layout import solve_layout
        try:
            out = solve_layout(self.manager, layout_name)
        except ValueError as exc:
            out = {'ok': False, 'refusal': str(exc)}
        if not out.get('ok'):
            response.status = '404 Not Found'
        response.media = out

    def on_get_layout_cost(self, request, response, layout_name):
        from magnetics.custom.magnet_layout import layout_cost
        out = layout_cost(self.manager, layout_name,
                          policy_name=request.params.get('policy',
                                                         ''))
        if not out.get('ok'):
            response.status = '404 Not Found'
        response.media = out

    def on_get_layout_dryfit(self, request, response, layout_name):
        from magnetics.custom.magnet_layout import dry_fit_report
        try:
            out = dry_fit_report(self.manager, layout_name)
        except ValueError as exc:
            out = {'ok': False, 'refusal': str(exc)}
        if not out.get('ok'):
            response.status = '404 Not Found'
        response.media = out

    def on_get_fieldviews(self, request, response):
        rows = []
        for v in _rows(self.manager, 'FieldViewDefinition'):
            rows.append({
                'name': getattr(v, 'name', ''),
                'displayName': getattr(v, 'display_name', ''),
                'fieldKind': getattr(v, 'field_kind', ''),
                'sourceKind': getattr(v, 'source_kind', ''),
                'displayMode': getattr(v, 'display_mode', ''),
                'deviceKind': getattr(v, 'device_kind', ''),
                'deviceRef': getattr(v, 'device_ref', ''),
            })
        groups = [{'name': getattr(g, 'name', ''),
                   'displayName': getattr(g, 'display_name', ''),
                   'order': getattr(g, 'view_refs_json', '[]')}
                  for g in _rows(self.manager, 'FieldViewGroup')]
        response.media = {'ok': True, 'views': rows,
                          'groups': groups}

    def on_get_fieldview(self, request, response, view_name):
        from magnetics.custom.field_views import view_payload
        out = view_payload(self.manager, view_name)
        if not out.get('ok'):
            response.status = '404 Not Found'
        response.media = out

    def on_get_fieldview_group(self, request, response,
                               group_name):
        from magnetics.custom.field_views import group_payload
        out = group_payload(self.manager, group_name)
        if not out.get('ok'):
            response.status = '404 Not Found'
        response.media = out
