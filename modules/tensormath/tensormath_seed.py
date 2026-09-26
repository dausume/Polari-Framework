"""
@module tensormath.tensormath_seed

tt-1: two tensors over REAL simulation state, read live (storage_kind=engine — values are never copied here):
  wind-field       the wind→pendulum coupling's 4×4×4 grid (WindFieldGridState.cells_json, [cx,cy,cz,wx,wy,wz] per
                   cell) as a rank-4 tensor [x,y,z,component] — the spatial field of Validation A (D3 asked for the
                   waxprint thermal field; WaxPrintSimState is per-step SCALARS, not a spatial field, so the wind
                   grid is the first real 3-D field and waxprint is the time-series case below)
  waxprint-series  WaxPrintSimState per step: [step, (exit_temp_c, melt_fraction, height_mm, warp_index)] — rank 2
and the expressions that read them (wind speed = the L2 norm over the velocity components).
"""
import json

from tensormath.tensormath_basis import (Tensor, TensorDimension, TensorMathExpression, TensorOperator,
                                         ComputeImplementation, TensorDecomposition, FEMFieldState)

SEED_TENSORS = [
    {'name': 'wind-field', 'description': 'the wind→pendulum coupling\'s grid, read live from the newest WindFieldGridState row',
     'rank': 4, 'shape_json': '[4,4,4,6]', 'dtype': 'float',
     'dimensions_json': json.dumps([{'name': 'x', 'size': 4, 'unit': 'm', 'semantics': 'grid x (cell centres −1.2…1.2 m)'},
                                    {'name': 'y', 'size': 4, 'unit': 'm', 'semantics': 'grid y (−1.3…0.2 m)'},
                                    {'name': 'z', 'size': 4, 'unit': 'm', 'semantics': 'grid z (−1.2…1.2 m)'},
                                    {'name': 'component', 'size': 6, 'unit': 'm | m/s', 'semantics': 'cx, cy, cz, wx, wy, wz'}]),
     'units': 'm, m/s', 'semantics': 'a wind velocity field sampled on a 4×4×4 grid of cell centres',
     'storage_kind': 'engine', 'storage_ref': 'matrixfield:WindFieldGridState:*:cells_json',
     'metadata_json': json.dumps({'grid_counts': [4, 4, 4], 'origin_cols': [0, 3], 'vector_cols': [3, 6],
                                  'binding': 'WindFieldGridState-3d', 'sim_space': 'newtonian-pendulum-viz'}), 'tags': 'wind,field,tt-1'},
    {'name': 'waxprint-series', 'description': 'the wax print simulation\'s per-step scalars as a time series, read live',
     'rank': 2, 'shape_json': '[]', 'dtype': 'float',
     'dimensions_json': json.dumps([{'name': 'step', 'unit': 'step', 'semantics': 'simulation step'},
                                    {'name': 'quantity', 'size': 4, 'unit': '°C | 1 | mm | 1', 'semantics': 'exit_temp_c, melt_fraction, height_mm, warp_index'}]),
     'units': 'mixed', 'semantics': 'the print\'s thermal/geometric state over time',
     'storage_kind': 'engine', 'storage_ref': 'simstate:WaxPrintSimState:*:exit_temp_c,melt_fraction,height_mm,warp_index',
     'metadata_json': '{}', 'tags': 'waxprint,series,tt-1'},
    # tt-7: the pendulum bob's state per step — the TARGET side of the wind coupling, so a coupling can be
    # DERIVED from a mapping (its class → its simulation definition; its position fields → the sampler's pos)
    {'name': 'bob-state', 'description': 'the Newtonian pendulum bob per step: position, velocity and the sampled wind force, read live',
     'rank': 2, 'shape_json': '[]', 'dtype': 'float',
     'dimensions_json': json.dumps([{'name': 'step', 'unit': 'step', 'semantics': 'simulation step'},
                                    {'name': 'quantity', 'size': 9, 'unit': 'm | m/s | N', 'semantics': 'px, py, pz, vx, vy, vz, fwind_x, fwind_y, fwind_z'}]),
     'units': 'mixed', 'semantics': 'the bob\'s trajectory with the wind force it felt',
     'storage_kind': 'engine', 'storage_ref': 'simstate:NewtonianPendulumBobSimState:*:px,py,pz,vx,vy,vz,fwind_x,fwind_y,fwind_z',
     'metadata_json': json.dumps({'binding': 'NewtonianPendulumBobSimState-wind-arrow-3d', 'sim_space': 'newtonian-pendulum-viz'}), 'tags': 'pendulum,tt-7'},
]
SEED_TENSOR_DIMENSIONS = [
    {'name': 'wind-field.%s' % n, 'tensor': 'wind-field', 'index': i, 'label': n, 'size': s, 'unit': u, 'kind': k, 'semantics': sem, 'coordinate_ref': '', 'notes': ''}
    for i, (n, s, u, k, sem) in enumerate((('x', 4, 'm', 'spatial', 'grid x'), ('y', 4, 'm', 'spatial', 'grid y'), ('z', 4, 'm', 'spatial', 'grid z'),
                                           ('component', 6, 'm | m/s', 'channel', 'cx cy cz wx wy wz')))]
SEED_TENSOR_EXPRESSIONS = [
    {'name': 'wind-speed', 'description': '|w| per cell: the L2 norm over the velocity components (cols 3..6 of the component axis)',
     'latex': '|w|_{xyz} = \\sqrt{w_x^2 + w_y^2 + w_z^2}', 'operation': 'norm',
     'operands_json': json.dumps([{'tensor': 'wind-field', 'ranges': {'component': [3, 6]}}]), 'dims_json': '["component"]',
     'matrix_equation_ref': '', 'result_shape_json': '[4,4,4]', 'tags': 'tt-1'},
    {'name': 'wind-slice-z0', 'description': 'the z=0 layer of the field (a restriction)', 'latex': 'w|_{k=0}', 'operation': 'slice',
     'operands_json': json.dumps([{'tensor': 'wind-field', 'ranges': {'z': [0, 1]}}]), 'dims_json': '[]', 'matrix_equation_ref': '', 'result_shape_json': '[4,4,1,6]', 'tags': 'tt-1'},
    {'name': 'wind-mean-over-y', 'description': 'the field averaged down the y axis', 'latex': '\\langle w \\rangle_y', 'operation': 'reduce',
     'operands_json': json.dumps([{'tensor': 'wind-field', 'how': 'mean'}]), 'dims_json': '["y"]', 'matrix_equation_ref': '', 'result_shape_json': '[4,4,6]', 'tags': 'tt-1'},
    # tt-7: the cross-space SAMPLER as a tensor expression that DELEGATES to the saved no-code matrix equation
    # (rank ≤ 2 → matrix_equation_ref); a coupling created from a mapping takes its sampler from here
    {'name': 'wind-sample-at-bob', 'description': 'w(p): the velocity of the grid cell nearest the bob — the saved no-code sampler field-sample-nearest, by reference',
     'latex': '\\mathbf{w}(\\mathbf{p}) = \\mathbf{w}_{\\arg\\min_i \\lVert\\mathbf{c}_i-\\mathbf{p}\\rVert}', 'operation': 'sample',
     'operands_json': json.dumps([{'tensor': 'wind-field', 'role': 'cells'}, {'tensor': 'bob-state', 'ranges': {'quantity': [0, 3]}, 'role': 'pos'}]), 'dims_json': '["x","y","z"]',
     'matrix_equation_ref': 'field-sample-nearest', 'result_shape_json': '[3]', 'tags': 'tt-7'},
]

# ---- tt-2: CONTINUUM MECHANICS on the FEM resolution (plan §C Phase 3, Validation B). One FEM case — a
# 2 m × 1 m electrical-steel plate, fixed on the left, 1 MPa traction on the right, plane stress — whose E and
# ν are the magnetics module's CITED material option (literature-est; the provenance travels). The tensors
# read the solve live: u (nodes×2), ε (elem×2×2), σ (elem×2×2), C (2×2×2×2 from the engine's own Lamé pair).
# σ = C:ε by NAMED contraction must equal the engine's σ — the interop proof.
SEED_FEM_CASES = [{
    'name': 'tt2-plate-tension', 'display_name': 'tt-2 plate in tension (electrical steel, plane stress)',
    'description': 'A 2 m × 1 m plate, left edge fixed (x and y), 1 MPa traction on the right edge, plane stress, refine 2. '
                   'E and ν from the cited material option opt-electrical-steel (literature-est). The tensor arc\'s Validation B.',
    'physics_ref': 'linear-elasticity', 'domain_json': json.dumps({'width': 2.0, 'height': 1.0}),
    'materials_json': json.dumps([{'material_option': 'opt-electrical-steel'}]),
    'boundary_conditions_json': json.dumps({'tractions': [{'edge': 'right', 'tx': 1.0e6, 'ty': 0.0}], 'fixed_edges': [{'edge': 'left', 'dof': 'xy'}]}),
    'source_terms_json': '{}', 'mesh_json': json.dumps({'refine': 2}), 'solver_json': json.dumps({'assumption': 'plane-stress', 'engine': 'materialsScience.engines.fem_engine.solve_elasticity_2d'}),
    'last_result_json': '{}', 'last_executed_at': '', 'notes': 'tt-2', 'enabled': True}]
_dims = lambda *ds: json.dumps([{'name': n, 'size': s, 'unit': u, 'semantics': sem} for n, s, u, sem in ds])
SEED_TENSORS += [
    {'name': 'tt2-u', 'description': 'nodal displacement u_i(x) of the plate', 'rank': 2, 'shape_json': '[]', 'dtype': 'float',
     'dimensions_json': _dims(('node', 0, '', 'mesh node'), ('i', 2, 'm', 'ux, uy')), 'units': 'm', 'semantics': 'displacement field',
     'storage_kind': 'engine', 'storage_ref': 'fem:tt2-plate-tension:displacement', 'metadata_json': '{}', 'tags': 'tt-2'},
    {'name': 'tt2-eps', 'description': 'element strain ε_ij = ½(∂u_i/∂x_j + ∂u_j/∂x_i)', 'rank': 3, 'shape_json': '[]', 'dtype': 'float',
     'dimensions_json': _dims(('n', 0, '', 'mesh element'), ('k', 2, '1', ''), ('l', 2, '1', '')), 'units': '1', 'semantics': 'small strain, element-constant (P1)',
     'storage_kind': 'engine', 'storage_ref': 'fem:tt2-plate-tension:strain', 'metadata_json': '{}', 'tags': 'tt-2'},
    {'name': 'tt2-sigma', 'description': 'element stress σ_ij as the engine computed it', 'rank': 3, 'shape_json': '[]', 'dtype': 'float',
     'dimensions_json': _dims(('n', 0, '', 'mesh element'), ('i', 2, 'Pa', ''), ('j', 2, 'Pa', '')), 'units': 'Pa', 'semantics': 'Cauchy stress, plane stress',
     'storage_kind': 'engine', 'storage_ref': 'fem:tt2-plate-tension:stress', 'metadata_json': '{}', 'tags': 'tt-2'},
    {'name': 'tt2-C', 'description': 'the stiffness tensor C_ijkl = λ δ_ij δ_kl + μ (δ_ik δ_jl + δ_il δ_jk) from the Lamé pair the engine used', 'rank': 4, 'shape_json': '[2,2,2,2]', 'dtype': 'float',
     'dimensions_json': _dims(('i', 2, 'Pa', ''), ('j', 2, 'Pa', ''), ('k', 2, '1', ''), ('l', 2, '1', '')), 'units': 'Pa', 'semantics': 'isotropic linear elastic stiffness (plane-stress reduced pair)',
     'storage_kind': 'engine', 'storage_ref': 'fem:tt2-plate-tension:stiffness', 'metadata_json': '{}', 'tags': 'tt-2'},
    {'name': 'tt2-centroids', 'description': 'element centroids (x, y)', 'rank': 2, 'shape_json': '[]', 'dtype': 'float',
     'dimensions_json': _dims(('n', 0, '', 'mesh element'), ('xy', 2, 'm', 'x, y')), 'units': 'm', 'semantics': 'where each element\'s ε and σ live',
     'storage_kind': 'engine', 'storage_ref': 'fem:tt2-plate-tension:centroids', 'metadata_json': '{}', 'tags': 'tt-2'},
]
SEED_TENSOR_EXPRESSIONS += [
    {'name': 'tt2-sigma-from-C', 'description': 'σ_ij = C_ijkl ε_kl — the rank-4 contraction over k,l; result dims [i, j, n] (the engine\'s σ is [n, i, j])',
     'latex': r'\sigma_{ij} = C_{ijkl}\,\epsilon_{kl}', 'operation': 'contract', 'operands_json': json.dumps([{'tensor': 'tt2-C'}, {'tensor': 'tt2-eps'}]),
     'dims_json': '["k","l"]', 'matrix_equation_ref': '', 'result_shape_json': '[2,2,n]', 'tags': 'tt-2'},
    {'name': 'tt2-trace-eps', 'description': 'the volumetric strain ε_kk per element', 'latex': r'\epsilon_{kk}', 'operation': 'reduce',
     'operands_json': json.dumps([{'tensor': 'tt2-eps', 'how': 'sum'}]), 'dims_json': '["k"]', 'matrix_equation_ref': '', 'result_shape_json': '[n,2]', 'tags': 'tt-2'},
]
SEED_TENSOR_OPERATORS = [{'name': 'stress-from-strain', 'description': 'Hooke\'s law for a linear elastic solid', 'expression_ref': 'tt2-sigma-from-C',
                          'input_tensors_json': '["tt2-C", "tt2-eps"]', 'output_tensor': 'tt2-sigma', 'semantics': 'the stress a linear elastic body carries for a given small strain (constitutive law)', 'tags': 'tt-2'}]
SEED_COMPUTE_IMPLEMENTATIONS = [{'name': 'stress-from-strain/numpy', 'description': 'np.einsum on the node\'s CPU (the matrix-module path generalised to rank 4)', 'operator': 'stress-from-strain',
                                 'target_rung': 'microarchitecture', 'target_kind': 'in-order', 'target_ref': 'this node\'s CPU (numpy einsum)', 'precision': 'float64',
                                 'shapes_json': json.dumps({'C': [2, 2, 2, 2], 'eps': ['n', 2, 2]}), 'latency_s': 0.0, 'throughput': 0.0, 'memory_bytes': 0, 'energy_j': 0.0, 'error': 0.0, 'config_overhead_s': 0.0,
                                 'mapping_status': 'implemented', 'evidence_level': 'none',
                                 'evidence_ref': '', 'notes': 'latency is READ per call (POST /api/tensormath/evaluate → elapsed_s), not stored: a stored benchmark row with its conditions is lad-5\'s. No number invented here.'}]

# ---- D5 (his word 2026-09-26): the SAME operator through PyTorch — resolved through the engines ladder (custom/torch_engine.py:
# TORCH_ENGINES_URL worker | import torch | topology provider | refusal); its numbers come from a benchmark WHERE it runs, never invented.
SEED_COMPUTE_IMPLEMENTATIONS.append({'name': 'stress-from-strain/torch', 'description': 'torch.einsum on the same operands and contraction spec as the numpy path — the third implementation of the bridge (D5); CPU wheel, float64, deterministic algorithms on',
                                     'operator': 'stress-from-strain', 'target_rung': 'microarchitecture', 'target_kind': 'in-order',
                                     'target_ref': 'torch engine: TORCH_ENGINES_URL worker (polari-rf-node/polari-torch-tools) | import torch | provider tensormath.engines', 'precision': 'float64',
                                     'shapes_json': json.dumps({'C': [2, 2, 2, 2], 'eps': ['n', 2, 2]}), 'latency_s': 0.0, 'throughput': 0.0, 'memory_bytes': 0, 'energy_j': 0.0, 'error': 0.0, 'config_overhead_s': 0.0,
                                     'mapping_status': 'implemented', 'evidence_level': 'none', 'evidence_ref': '',
                                     'notes': 'PyTorch BSD-3 (polari-torch-tools/LICENSES.md). No number until POST /api/tensormath/benchmark runs it where a torch engine resolves; then latency/throughput/error are MEASURED there and the evidence_ref records version, device, threads, n, repeats. The framework\'s Alpine image has no torch wheel: the worker is the normal way.'})

# ---- Phase 6: the SAME operator on an open FPGA — from the committed report of the real flow (custom/fpga_kernel.py)
from tensormath.custom.fpga_kernel import report as _fpga_report, implementation_row as _fpga_row
_fpga = _fpga_row(_fpga_report())
if _fpga:
    SEED_COMPUTE_IMPLEMENTATIONS.append(_fpga)

# ---- tt-6: the σ field WRITTEN DOWN so a binding can see it. The FEMFieldState row is solved at seed time (no
# manager: the seed case + the seed material option), a 2-D scene `plate-mechanics-2d` binds the class with a
# `field` binding coloured by σ_vm over PLATE_SIGMA_DOMAIN — the SAME domain the tensortree dimension
# plate.sigma declares (one constant, so dims → channel and the binding cannot drift apart).
from tensormath.custom.fem_field import LazySeedRows, seed_field_rows, SEED_FIELD_NAME  # noqa: E402
from tensormath.custom.fem_shapes import element_shapes  # noqa: E402

PLATE_SIGMA_DOMAIN = [0.8e6, 1.1e6]   # Pa — tight to the uniaxial 1 MPa field so its structure (the fixed edge's Poisson constraint) shows
SEED_FEM_FIELD_STATES = LazySeedRows(seed_field_rows)
# tt-11: every element of the seed field as a `polygon` MathShapeDefinition + a Shape2DDefinition in SPACE units
# (mathshapes.custom.shape2d_bridge) — the shape library carries the geometry; the field binding paints it by σ
SEED_FEM_ELEMENT_MATH_SHAPES = LazySeedRows(lambda: [m for f in SEED_FEM_FIELD_STATES for m in element_shapes(f)[0]])
SEED_FEM_ELEMENT_SHAPES_2D = LazySeedRows(lambda: [s for f in SEED_FEM_FIELD_STATES for s in element_shapes(f)[1]])
PLATE_U_EXAGGERATION = 20000.0   # unitless: |u| ≤ 1e-5 m on a 2 m plate → ~0.2 m arrows; the knob is DATA on the binding and in the legend
SEED_PLATE_SIMSPACES = [{
    'name': 'plate-mechanics-2d',
    'description': 'The tt-2 plate in tension: σ_vm per element as a coloured cell at each element centroid (2-D field binding over '
                   'FEMFieldState.elements_json). Colour = von Mises stress over %s Pa; hover a cell for its value. u per node is drawn as a '
                   'line node → node + %g·u (the exaggeration is a STATED knob on the binding FEMFieldState-u-2d; |u| ≤ 1e-5 m on the seed case).' % (PLATE_SIGMA_DOMAIN, PLATE_U_EXAGGERATION),
    'dimensionality': '2d', 'coordinate_system': 'math', 'unit_scale': 1.0,
    'viewport_json': json.dumps({'center': [1.0, 0.5], 'extent': [1.3, 0.8]}),
    'bound_classes_json': json.dumps([{'className': 'FEMFieldState'}]),
    'definition': json.dumps({'freestanding': []}),
}]
SEED_PLATE_BINDINGS = [{
    'name': 'FEMFieldState-mesh-2d', 'class_name': 'FEMFieldState', 'dimensionality': '2d', 'enabled': True,
    'binding_json': json.dumps({
        'enabled': True, 'dimensionality': '2d', 'kind': 'meshwire', 'nodesField': 'nodes_json', 'trianglesField': 'triangles_json',
        'layout': {'originCols': [0, 2]}, 'visual': {'styleRef': 'default'}, 'defaultVisible': True,
        'note': 'the P1 mesh as a wireframe (each edge once) — the triangles SEEN; filled cells would need a renderer change (shapeRef-only shape library), not pretended',
    }),
}, {
    'name': 'FEMFieldState-u-2d', 'class_name': 'FEMFieldState', 'dimensionality': '2d', 'enabled': True,
    'binding_json': json.dumps({
        'enabled': True, 'dimensionality': '2d', 'kind': 'vectorfield', 'matrixField': 'nodes_json',
        'layout': {'originCols': [0, 2], 'vectorCols': [2, 4]}, 'vectorScale': PLATE_U_EXAGGERATION, 'magnitudeMin': 0.0,
        'unit': 'm', 'field': 'u (displacement)', 'visual': {'styleRef': 'default'}, 'defaultVisible': True,
        'note': 'u per node drawn as node → node + %g·u (an honest exaggeration: the factor is this knob, stated; the raw u rides each connection)' % PLATE_U_EXAGGERATION,
    }),
}, {
    'name': 'FEMFieldState-2d', 'class_name': 'FEMFieldState', 'dimensionality': '2d', 'enabled': True,
    'binding_json': json.dumps({
        'enabled': True, 'dimensionality': '2d', 'kind': 'field', 'matrixField': 'elements_json',
        'layout': {'originCols': [0, 2], 'scalarCol': 2},
        'color': {'domain': PLATE_SIGMA_DOMAIN, 'ramp': 'stress', 'unit': 'Pa', 'field': 'von Mises'},
        'shapeRefPattern': SEED_FIELD_NAME + '-el-{i}', 'visual': {'shapeRef': 'rectangle', 'styleRef': 'default'}, 'defaultVisible': True,
        'note': 'tt-11: each cell is ITS OWN triangle (a polygon math shape → a 2-D shape in space units), painted by σ_vm — filled cells through the shape library; the rectangle is only the fallback when a shape row is missing',
    }),
}]

TENSORMATH_SEED_PAIRS = [
    ('Tensor', Tensor, SEED_TENSORS), ('TensorDimension', TensorDimension, SEED_TENSOR_DIMENSIONS),
    ('TensorMathExpression', TensorMathExpression, SEED_TENSOR_EXPRESSIONS),
    ('TensorOperator', TensorOperator, SEED_TENSOR_OPERATORS), ('ComputeImplementation', ComputeImplementation, SEED_COMPUTE_IMPLEMENTATIONS),
    ('TensorDecomposition', TensorDecomposition, []),
    ('FEMFieldState', FEMFieldState, SEED_FEM_FIELD_STATES),
]
try:   # the scene + binding are CORE simSpace rows, seeded here because they exist for this module's field
    from simSpace.sim_space_definition import SimSpaceDefinition
    from simSpace.sim_space_binding_definition import SimSpaceBindingDefinition
    TENSORMATH_SEED_PAIRS += [('SimSpaceDefinition', SimSpaceDefinition, SEED_PLATE_SIMSPACES),
                              ('SimSpaceBindingDefinition', SimSpaceBindingDefinition, SEED_PLATE_BINDINGS)]
    from simSpace2D.shape_2d_definition import Shape2DDefinition
    TENSORMATH_SEED_PAIRS += [('Shape2DDefinition', Shape2DDefinition, SEED_FEM_ELEMENT_SHAPES_2D)]
    try:   # the geometry rows belong to the mathshapes module; seeded only when it is present
        from mathshapes.objects.shape.MathShapeDefinition import MathShapeDefinition
        TENSORMATH_SEED_PAIRS += [('MathShapeDefinition', MathShapeDefinition, SEED_FEM_ELEMENT_MATH_SHAPES)]
    except Exception:   # pragma: no cover
        pass
except Exception:   # pragma: no cover
    pass
try:   # the FEM case is a CORE materialsScience row, seeded here so the tensors have something to read
    from materialsScience.fem_model_definition import FEMModelDefinition
    TENSORMATH_SEED_PAIRS.insert(0, ('FEMModelDefinition', FEMModelDefinition, SEED_FEM_CASES))
except Exception:   # pragma: no cover
    pass
