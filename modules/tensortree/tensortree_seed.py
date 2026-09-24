"""
@module tensortree.tensortree_seed

The default TensorDiscoveryPolicy (plan §F3) and, tt-1, ONE tree over a real tensor — `wind-spatial` over
tensormath's `wind-field` (read live from the wind→pendulum coupling's grid):

    wind-grid (root, RESOLVED: x/y/z → position, speed → color, w → vector; binding = the proven WindFieldGridState-3d)
    ├── wind-slice-z0 (RESOLVED restriction to the z=0 layer)
    └── wind-turbulence (UNRESOLVED, semantic: what the sub-grid structure is — kept as open questions)
    mappings: grid→slice (restriction) · grid→bob-drag (coupling = the REAL SimulationCouplingDefinition
    wind-to-newtonian-pendulum, by reference) · grid→spectrum (a PROPOSED decomposition valid only for calm
    wind, so a gusty selection refuses it — discovery proven live)
    selection: gust-corner (x/y/z ranges + speed 6–12 m/s)
"""
import json

from tensortree.tensortree_basis import (TensorTreeDefinition, TensorNode, UnresolvedTensorSpace, LocalizedDimension,
                                         TensorMapping, TensorSelection, TensorDiscoveryPolicy)

_T = 'wind-spatial'
SEED_TENSOR_TREES = [{'name': _T, 'description': 'the wind field as a navigable spatial view (tt-1, Validation A on real state)',
                      'tensor': 'wind-field', 'root_node': 'wind-grid', 'view_kind': 'spatial', 'status': 'partial', 'notes': ''}]
_ld = lambda node, dim, ch, rng='[]', sc='{}': {'name': '%s.%s' % (node, dim), 'description': '', 'node': node, 'dimension': 'wind-field.' + dim if dim != 'speed' else 'wind-speed',
                                                  'range_json': rng, 'channel': ch, 'scale_json': sc, 'coherent': False, 'notes': ''}
SEED_LOCALIZED_DIMENSIONS = [
    _ld('wind-grid', 'x', 'position.x'), _ld('wind-grid', 'y', 'position.y'), _ld('wind-grid', 'z', 'position.z'),
    _ld('wind-grid', 'speed', 'color', sc=json.dumps({'kind': 'continuous', 'domain': [0, 12], 'unit': 'm/s'})),
    _ld('wind-grid', 'component', 'vector', rng='[3,6]'),
    _ld('wind-slice-z0', 'x', 'position.x'), _ld('wind-slice-z0', 'y', 'position.y'), _ld('wind-slice-z0', 'z', 'position.z', rng='[0,1]'),
    _ld('wind-slice-z0', 'component', 'vector', rng='[3,6]'),
]
SEED_TENSOR_NODES = [
    {'name': 'wind-grid', 'description': '', 'tree': _T, 'parent': '', 'title': 'the wind field on its grid', 'tensor': 'wind-field',
     'dims_json': json.dumps(['wind-grid.x', 'wind-grid.y', 'wind-grid.z', 'wind-grid.speed', 'wind-grid.component']),
     'binding_ref': 'WindFieldGridState-3d', 'global_params_json': json.dumps({'sim_space': 'newtonian-pendulum-viz'}), 'status': 'unresolved', 'notes': 'status is set by the validator'},
    {'name': 'wind-slice-z0', 'description': '', 'tree': _T, 'parent': 'wind-grid', 'title': 'the z = 0 layer', 'tensor': 'wind-field',
     'dims_json': json.dumps(['wind-slice-z0.x', 'wind-slice-z0.y', 'wind-slice-z0.z', 'wind-slice-z0.component']),
     'binding_ref': 'WindFieldGridState-3d', 'global_params_json': '{}', 'status': 'unresolved', 'notes': ''},
]
SEED_UNRESOLVED = [
    {'name': 'wind-turbulence', 'description': '', 'tree': _T, 'parent': 'wind-grid', 'title': 'sub-grid structure of the wind', 'unresolved_kind': 'semantic',
     'known_dims_json': '["x","y","z"]', 'known_semantics_json': json.dumps({'field': 'the 4×4×4 grid is a sampled mean; what happens between cells is not modelled'}),
     'constraints_json': '[]', 'candidate_mappings_json': json.dumps(['a spectral decomposition of the sampled field']), 'candidate_bindings_json': '[]',
     'hypotheses_json': json.dumps(['a gust is coherent across neighbouring cells (see wind_amp / wind_freq in the sim parameters)']),
     'evidence_json': '[]', 'open_questions_json': json.dumps(['is the grid spacing below the gust\'s coherence length?']), 'notes': ''},
]
_M = lambda **k: dict({'description': '', 'expression_ref': '', 'coupling_ref': '', 'scale_transfer_ref': '', 'validity_json': '{}', 'units': '', 'conservation_json': '[]',
                       'loss_note': '', 'reconstruction_error': 0.0, 'error_method': '', 'uncertainty_json': '{}', 'evidence_ref': '', 'provenance': '', 'notes': ''}, **k)
SEED_TENSOR_MAPPINGS = [
    _M(name='wind-grid→slice-z0', kind='restriction', source_node='wind-grid', source_dims_json='["x","y","z"]', target_node='wind-slice-z0', target_dims_json='["x","y"]',
       expression_ref='wind-slice-z0', validity_json=json.dumps({'z': [-1.2, 1.2]}), loss_note='the other three z layers are dropped',
       mapping_status='implemented', evidence_level='simulated', evidence_ref='tensormath evaluate wind-slice-z0', provenance='tt-1'),
    _M(name='wind-grid→bob-drag', kind='coupling', source_node='wind-grid', source_dims_json='["x","y","z","speed"]', target_node='pendulum-bob', target_dims_json='["fwind_x","fwind_y","fwind_z"]',
       coupling_ref='wind-to-newtonian-pendulum', validity_json=json.dumps({'speed': [0, 30]}), units='N', loss_note='the field is SAMPLED at the bob: one cell\'s velocity becomes one force',
       mapping_status='validated', evidence_level='simulated', evidence_ref='simulations/selftest_wind_coupling.py (Milestone A)', provenance='the live SimulationCouplingDefinition, by reference'),
    _M(name='wind-grid→spectrum', kind='decomposition', source_node='wind-grid', source_dims_json='["x","y","z","speed"]', target_node='wind-turbulence', target_dims_json='["mode"]',
       validity_json=json.dumps({'speed': [0, 5]}), loss_note='a proposed low-rank decomposition — valid only for calm wind until proven',
       mapping_status='proposed', evidence_level='none', evidence_ref='', provenance='tt-1 (a hypothesis, on purpose)'),
]
SEED_TENSOR_SELECTIONS = [{'name': 'gust-corner', 'description': 'a gusty corner of the grid', 'node': 'wind-grid',
                           'ranges_json': json.dumps({'x': [0.4, 1.2], 'y': [-0.5, 0.2], 'z': [0.4, 1.2], 'speed': [6, 12]}),
                           'created_from': 'seed (tt-1)', 'created_at': '2026-09-23', 'notes': ''}]

SEED_DISCOVERY_POLICIES = [{
    'name': 'default', 'description': 'Score = 0.30·E + 0.25·D + 0.25·V + 0.10·C + 0.10·(1−U) after the hard filters (plan §F3)',
    'w_evidence': 0.30, 'w_dims': 0.25, 'w_validity': 0.25, 'w_context': 0.10, 'w_uncertainty': 0.10,
    'evidence_map_json': '{"measured": 1.0, "validated": 0.85, "implemented": 0.65, "analytical": 0.4, "proposed": 0.2, "none": 0.1}',
    'is_default': True, 'notes': 'weights are configuration, not scientific constants'}]

TENSORTREE_SEED_PAIRS = [
    ('TensorTreeDefinition', TensorTreeDefinition, SEED_TENSOR_TREES), ('TensorNode', TensorNode, SEED_TENSOR_NODES),
    ('UnresolvedTensorSpace', UnresolvedTensorSpace, SEED_UNRESOLVED), ('LocalizedDimension', LocalizedDimension, SEED_LOCALIZED_DIMENSIONS),
    ('TensorMapping', TensorMapping, SEED_TENSOR_MAPPINGS), ('TensorSelection', TensorSelection, SEED_TENSOR_SELECTIONS),
    ('TensorDiscoveryPolicy', TensorDiscoveryPolicy, SEED_DISCOVERY_POLICIES),
]
