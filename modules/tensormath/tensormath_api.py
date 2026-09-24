"""
@module tensormath.tensormath_api

  GET  /api/tensormath                 the tensors (rank, shape, storage, semantics), expressions, operators
  GET  /api/tensormath/tensors/{name}  one tensor + its dimensions + the trees that view it
  POST /api/tensormath/evaluate        {"expression": "<TensorMathExpression.name>"} → values/dims/einsum, or the
                                       delegation to the matrix module, or the reason it cannot (storage kind)
  GET  /api/tensormath/operators/{name}  the operator + its ComputeImplementation rows (the bridge, plan §F8)
  POST /api/tensormath/benchmark         {"implementation": "<ComputeImplementation.name>", "repeats": 20}
                                         RUNS the numpy implementation of its operator here, repeats times, and WRITES
                                         the reading into the row: latency_s (median), throughput (elements/s),
                                         evidence_level=measured, evidence_ref = when/where/how many. A person's
                                         action; the conditions (this node, numpy, float64, n elements) go in the
                                         evidence, because a latency without them is misleading (plan §F2).
"""
from objectTreeDecorators import treeObject, treeObjectInit

from tensormath.custom.tensor_ops import evaluate, dim_names, TensorOpsError, fem_case_solution
from tensormath.custom.fem_field import field_row_from_solution


class TensorMathAPI(treeObject):
    @treeObjectInit
    def __init__(self, polServer):
        self.polServer = polServer
        self.apiName = '/api/tensormath'
        if polServer is not None:
            add = polServer.falconServer.add_route
            add('/api/tensormath', self)
            add('/api/tensormath/tensors/{name}', self, suffix='tensor')
            add('/api/tensormath/evaluate', self, suffix='evaluate')
            add('/api/tensormath/operators/{name}', self, suffix='operator')
            add('/api/tensormath/benchmark', self, suffix='benchmark')
            add('/api/tensormath/fem/{case}', self, suffix='fem')
            add('/api/tensormath/fem/{case}/materialise', self, suffix='fem_materialise')
            add('/api/tensormath/fem/{case}/shapes', self, suffix='fem_shapes')

    def _rows(self, cls):
        return list((getattr(self.manager, 'objectTables', {}) or {}).get(cls, {}).values())

    def on_get(self, request, response):
        response.media = {'ok': True,
                          'tensors': [{'name': str(t.name), 'rank': int(getattr(t, 'rank', 0) or 0), 'shape': str(getattr(t, 'shape_json', '')),
                                       'storage': '%s:%s' % (getattr(t, 'storage_kind', ''), getattr(t, 'storage_ref', '')),
                                       'semantics': str(getattr(t, 'semantics', ''))} for t in self._rows('Tensor')],
                          'expressions': [str(e.name) for e in self._rows('TensorMathExpression')],
                          'operators': [str(o.name) for o in self._rows('TensorOperator')],
                          'storage_kinds': 'matrix (a rank-N MatrixDefinition) | dataset | engine | claim — values live where they already can'}

    def on_get_tensor(self, request, response, name):
        t = next((x for x in self._rows('Tensor') if str(x.name) == name), None)
        if t is None:
            response.status = '404 Not Found'; response.media = {'ok': False, 'error': 'no Tensor %r' % name}; return
        response.media = {'ok': True, 'tensor': {'name': name, 'rank': getattr(t, 'rank', 0), 'shape': getattr(t, 'shape_json', ''), 'dims': dim_names(t),
                                                 'semantics': getattr(t, 'semantics', ''), 'storage_kind': getattr(t, 'storage_kind', ''), 'storage_ref': getattr(t, 'storage_ref', '')},
                          'dimensions': [{'name': str(d.name), 'index': getattr(d, 'index', 0), 'kind': getattr(d, 'kind', ''), 'unit': getattr(d, 'unit', '')}
                                         for d in self._rows('TensorDimension') if str(getattr(d, 'tensor', '')) == name],
                          'trees': [str(tr.name) for tr in self._rows('TensorTreeDefinition') if str(getattr(tr, 'tensor', '')) == name]}

    def on_post_evaluate(self, request, response):
        body = request.media if isinstance(request.media, dict) else {}
        e = next((x for x in self._rows('TensorMathExpression') if str(x.name) == str(body.get('expression', ''))), None)
        if e is None:
            response.status = '404 Not Found'; response.media = {'ok': False, 'error': 'no TensorMathExpression %r' % body.get('expression')}; return
        try:
            response.media = {'ok': True, 'expression': str(e.name), 'result': evaluate(self.manager, e)}
        except TensorOpsError as err:
            response.status = '422 Unprocessable Entity'; response.media = {'ok': False, 'error': str(err)}

    def on_post_benchmark(self, request, response):
        import datetime, json as _json, platform, statistics, time
        body = request.media if isinstance(request.media, dict) else {}
        impl = next((i for i in self._rows('ComputeImplementation') if str(i.name) == str(body.get('implementation', ''))), None)
        if impl is None:
            response.status = '404 Not Found'; response.media = {'ok': False, 'error': 'no ComputeImplementation %r' % body.get('implementation')}; return
        if 'numpy' not in str(getattr(impl, 'target_ref', '')).lower() and str(getattr(impl, 'target_kind', '')) != 'in-order':
            response.status = '422 Unprocessable Entity'
            response.media = {'ok': False, 'error': 'only a numpy implementation runs HERE; an FPGA/ASIC row is measured by its own flow (fpga_kernel.py) or on the part'}; return
        op = next((o for o in self._rows('TensorOperator') if str(o.name) == str(getattr(impl, 'operator', ''))), None)
        e = next((x for x in self._rows('TensorMathExpression') if op is not None and str(x.name) == str(getattr(op, 'expression_ref', ''))), None)
        if e is None:
            response.status = '422 Unprocessable Entity'; response.media = {'ok': False, 'error': 'the implementation\'s operator has no expression to run'}; return
        repeats = max(3, min(int(body.get('repeats', 20) or 20), 200))
        try:
            first = evaluate(self.manager, e)          # warms the engine cache (a FEM solve is not the operator)
            times = [evaluate(self.manager, e)['elapsed_s'] for _ in range(repeats)]
        except TensorOpsError as err:
            response.status = '422 Unprocessable Entity'; response.media = {'ok': False, 'error': str(err)}; return
        n = (first.get('shape') or [0])[-1] if first.get('dims', [''])[-1] == 'n' else (first.get('shape') or [0])[0]
        med = statistics.median(times)
        impl.latency_s = float(med); impl.throughput = float(n / med) if med > 0 and n else 0.0
        impl.mapping_status = 'validated'; impl.evidence_level = 'measured'
        impl.evidence_ref = 'benchmark %s on %s (%s): numpy einsum float64, n=%s elements, %d repeats, median %.3e s (min %.3e, max %.3e)' % (
            datetime.datetime.now().isoformat(timespec='seconds'), platform.node(), platform.machine(), n, repeats, med, min(times), max(times))
        db = getattr(self.manager, 'db', None)
        if db is not None and hasattr(db, 'saveInstanceInDB'):
            db.saveInstanceInDB(impl)
        response.media = {'ok': True, 'implementation': str(impl.name), 'latency_s': impl.latency_s, 'throughput': impl.throughput, 'elements': n,
                          'repeats': repeats, 'evidence_ref': impl.evidence_ref, 'note': 'the reading is now the row\'s; compare with the FPGA row on the same operator'}

    # ---- tt-6: the σ field as a row a binding can see -------------------------------------------------------
    def _field_row(self, case):
        return next((f for f in self._rows('FEMFieldState') if str(getattr(f, 'case', '')) == case), None)

    def on_get_fem(self, request, response, case):
        """What this instance holds for an FEM case: the FEMFieldState row (summary, never the matrices), the scene and
        binding that render it, and whether it is drawable right now."""
        if not any(str(c.name) == case for c in self._rows('FEMModelDefinition')):
            response.status = '404 Not Found'; response.media = {'ok': False, 'error': 'no FEMModelDefinition %r' % case}; return
        f = self._field_row(case)
        bindings = [{'name': str(b.name), 'dimensionality': getattr(b, 'dimensionality', ''), 'enabled': bool(getattr(b, 'enabled', False))}
                    for b in self._rows('SimSpaceBindingDefinition') if str(getattr(b, 'class_name', '')) == 'FEMFieldState']
        scenes = [str(sd.name) for sd in self._rows('SimSpaceDefinition') if 'FEMFieldState' in str(getattr(sd, 'bound_classes_json', ''))]
        response.media = {'ok': True, 'case': case,
                          'field': None if f is None else {'name': str(f.name), 'n_elements': getattr(f, 'n_elements', 0), 'n_nodes': getattr(f, 'n_nodes', 0),
                                                            'sigma_vm_min': getattr(f, 'sigma_vm_min', 0.0), 'sigma_vm_max': getattr(f, 'sigma_vm_max', 0.0), 'u_max': getattr(f, 'u_max', 0.0),
                                                            'assumption': getattr(f, 'assumption', ''), 'material_provenance': getattr(f, 'material_provenance', ''),
                                                            'columns': getattr(f, 'columns_json', ''), 'node_columns': getattr(f, 'node_columns_json', ''), 'computed_at': getattr(f, 'computed_at', '')},
                          'bindings': bindings, 'scenes': scenes,
                          'drawable': f is not None and any(b['enabled'] for b in bindings) and bool(scenes),
                          'why': '' if f is not None else 'no FEMFieldState row for this case yet — POST …/materialise solves it and writes one'}

    def on_post_fem_materialise(self, request, response, case):
        """Solve the case (once per process) and write/refresh its FEMFieldState row — a person's action, like a scale tree."""
        try:
            sol = fem_case_solution(self.manager, case)
        except TensorOpsError as err:
            response.status = '422 Unprocessable Entity'; response.media = {'ok': False, 'error': str(err)}; return
        fields = field_row_from_solution(sol, case)
        row = self._field_row(case)
        created = row is None
        if created:
            from tensormath.tensormath_basis import FEMFieldState
            row = FEMFieldState(manager=self.manager, **fields)
        else:
            for k, v in fields.items():
                setattr(row, k, v)
        db = getattr(self.manager, 'db', None)
        if db is not None and hasattr(db, 'saveInstanceInDB'):
            db.saveInstanceInDB(row)
        response.status = '201 Created' if created else '200 OK'
        response.media = {'ok': True, 'case': case, 'field': str(row.name), 'created': created, 'n_elements': fields['n_elements'], 'n_nodes': fields['n_nodes'],
                          'sigma_vm': [fields['sigma_vm_min'], fields['sigma_vm_max']], 'u_max': fields['u_max'], 'material_provenance': fields['material_provenance']}

    def on_post_fem_shapes(self, request, response, case):
        """tt-11: write (or refresh) the element shapes of the case's field row — a polygon MathShapeDefinition and a space-unit
        Shape2DDefinition per triangle, through the math-shape library — so the field binding can paint each cell as itself."""
        from tensormath.custom.fem_shapes import element_shapes
        f = self._field_row(case)
        if f is None:
            response.status = '422 Unprocessable Entity'; response.media = {'ok': False, 'error': 'no FEMFieldState row for %r — POST …/materialise first' % case}; return
        maths, shapes = element_shapes(f)
        from simSpace2D.shape_2d_definition import Shape2DDefinition
        try:
            from mathshapes.objects.shape.MathShapeDefinition import MathShapeDefinition
        except Exception:
            MathShapeDefinition = None
        db = getattr(self.manager, 'db', None)
        def upsert(cls, cls_name, fields):
            row = next((r for r in self._rows(cls_name) if str(getattr(r, 'name', '')) == fields['name']), None)
            created = row is None
            if created:
                row = cls(manager=self.manager, **fields)
            else:
                for k, v in fields.items():
                    setattr(row, k, v)
            if db is not None and hasattr(db, 'saveInstanceInDB'):
                db.saveInstanceInDB(row)
            return created
        n_created = sum(upsert(Shape2DDefinition, 'Shape2DDefinition', s) for s in shapes)
        n_math = sum(upsert(MathShapeDefinition, 'MathShapeDefinition', m) for m in maths) if MathShapeDefinition else None
        response.status = '201 Created' if n_created else '200 OK'
        response.media = {'ok': True, 'case': case, 'field': str(f.name), 'elements': len(shapes), 'shapes_2d_created': n_created, 'math_shapes_created': n_math,
                          'shape_ref_pattern': '%s-el-{i}' % f.name, 'units': 'space', 'note': 'mathshapes absent → geometry rows skipped, the 2-D shapes still written' if MathShapeDefinition is None else ''}

    def on_get_operator(self, request, response, name):
        o = next((x for x in self._rows('TensorOperator') if str(x.name) == name), None)
        if o is None:
            response.status = '404 Not Found'; response.media = {'ok': False, 'error': 'no TensorOperator %r' % name}; return
        impls = [{'name': str(i.name), 'target_rung': getattr(i, 'target_rung', ''), 'target_kind': getattr(i, 'target_kind', ''), 'target_ref': getattr(i, 'target_ref', ''),
                  'precision': getattr(i, 'precision', ''), 'latency_s': getattr(i, 'latency_s', 0.0), 'throughput': getattr(i, 'throughput', 0.0),
                  'mapping_status': getattr(i, 'mapping_status', ''), 'evidence_level': getattr(i, 'evidence_level', ''), 'evidence_ref': getattr(i, 'evidence_ref', '')}
                 for i in self._rows('ComputeImplementation') if str(getattr(i, 'operator', '')) == name]
        response.media = {'ok': True, 'operator': {'name': name, 'semantics': getattr(o, 'semantics', ''), 'expression_ref': getattr(o, 'expression_ref', '')},
                          'implementations': impls, 'bridge': 'TensorOperator → ComputeImplementation → ComputeLOD (plan §F8)'}
