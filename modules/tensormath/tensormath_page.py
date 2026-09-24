"""
@module tensormath.tensormath_page
/display/tensormath — tensors (values by reference), dimensions, expressions, operators and the compute
implementations each operator has (the bridge to the compute ladder). Configured tables only.
"""
from polariApiServer.module_pages_seed import _page, _row, _sapi, _table

SEED_TENSORMATH_PAGE_DISPLAYS = [
    _page('tensormath', 'tensormath',
          'Tensor math — arbitrary-rank tensors whose values live where they already can (a matrix row, a dataset, an '
          'engine state, a claim), named dimensions, expressions, operators, and how each operator is computed',
          'Tensor', [
              _row(0, [_sapi('tensormath-summary', 0, 12, 'Tensors, expressions, operators on this instance', '/api/tensormath', pick='tensors,expressions,operators')], min_height=220),
              _row(1, [_table('tensormath-tensors', 0, 7, 'Tensors — unknown semantics is valid', 'Tensor', columns='name,rank,shape_json,dtype,dimensions_json,units,semantics,storage_kind,storage_ref'),
                       _table('tensormath-dimensions', 1, 5, 'Named dimensions', 'TensorDimension', columns='tensor,index,name,kind,unit,size,semantics')]),
              _row(2, [_table('tensormath-expressions', 0, 6, 'Expressions — rank ≤ 2 delegates to the matrix module', 'TensorMathExpression', columns='name,operation,latex,operands_json,dims_json,matrix_equation_ref,result_shape_json'),
                       _table('tensormath-operators', 1, 6, 'Operators — the meaning, independent of the computation', 'TensorOperator', columns='name,semantics,expression_ref,input_tensors_json,output_tensor')]),
              _row(3, [_table('tensormath-implementations', 0, 8, 'Compute implementations — every number from a real run or a cited model', 'ComputeImplementation',
                              columns='operator,name,target_rung,target_kind,target_ref,precision,latency_s,throughput,memory_bytes,error,mapping_status,evidence_level,evidence_ref'),
                       _table('tensormath-decompositions', 1, 4, 'Decompositions and what they lost', 'TensorDecomposition', columns='tensor,name,method,rank,reconstruction_error,error_method,evidence_level')]),
              # tt-6: the σ field written down (one row per solved case) and SEEN through the existing 2-D viewer
              _row(4, [_table('tensormath-fem-fields', 0, 12, 'FEM element fields as rows — σ per element, u per node, with the material line E/ν came from', 'FEMFieldState',
                              columns='case,name,n_elements,n_nodes,sigma_vm_min,sigma_vm_max,u_max,assumption,material_provenance,computed_at')]),
              _row(5, [{'id': 'tensormath-plate-scene', 'index': 0, 'type': 'component', 'rowSegmentsUsed': 12, 'gridColumnStart': None,
                        'title': 'tt-2 plate in tension — σ_vm per element (FEMFieldState-2d, colour) and u per node (FEMFieldState-u-2d, lines ×20000; hover for values)',
                        'visible': True, 'collapsed': False, 'cssClass': '',
                        'componentProps': {'componentName': 'sim-space-viewer', 'inputs': {'simSpaceName': 'plate-mechanics-2d'}},
                        'item': None, 'nestedRows': []}], min_height=420),
          ]),
]
