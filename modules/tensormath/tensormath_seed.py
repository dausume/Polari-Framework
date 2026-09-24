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
                                         ComputeImplementation, TensorDecomposition)

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
]

TENSORMATH_SEED_PAIRS = [
    ('Tensor', Tensor, SEED_TENSORS), ('TensorDimension', TensorDimension, SEED_TENSOR_DIMENSIONS),
    ('TensorMathExpression', TensorMathExpression, SEED_TENSOR_EXPRESSIONS),
    ('TensorOperator', TensorOperator, []), ('ComputeImplementation', ComputeImplementation, []),
    ('TensorDecomposition', TensorDecomposition, []),
]
