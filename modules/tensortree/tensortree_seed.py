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
# tt-7: the bob is a real node in its own tree (one root, one parent: the bob is not a child of the wind grid),
# so the cross-tree coupling mapping lands on something a coupling can be DERIVED from
_B = 'bob-motion'
SEED_TENSOR_TREES += [{'name': _B, 'description': 'the Newtonian pendulum bob: its trajectory and the wind force sampled onto it (the target side of the wind coupling)',
                       'tensor': 'bob-state', 'root_node': 'pendulum-bob', 'view_kind': 'spatial', 'status': 'partial', 'notes': 'tt-7'}]
_lb = lambda dim, ch, rng='[]': {'name': 'pendulum-bob.%s' % dim, 'description': '', 'node': 'pendulum-bob', 'dimension': 'bob-state.' + dim, 'range_json': rng, 'channel': ch, 'scale_json': '{}', 'coherent': False, 'notes': ''}
SEED_LOCALIZED_DIMENSIONS += [_lb('px', 'position.x'), _lb('py', 'position.y'), _lb('pz', 'position.z'), _lb('fwind', 'vector', rng='[6,9]')]
SEED_TENSOR_NODES += [
    {'name': 'pendulum-bob', 'description': '', 'tree': _B, 'parent': '', 'title': 'the bob, with the wind force on it', 'tensor': 'bob-state',
     'dims_json': json.dumps(['pendulum-bob.px', 'pendulum-bob.py', 'pendulum-bob.pz', 'pendulum-bob.fwind']),
     'binding_ref': 'NewtonianPendulumBobSimState-wind-arrow-3d', 'global_params_json': json.dumps({'sim_space': 'newtonian-pendulum-viz'}), 'status': 'unresolved', 'notes': 'status is set by the validator'},
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
    # tt-7: the same physics DECLARED FROM THE TREE with no coupling row yet — `POST /api/tensortree/mappings/
    # wind-grid→bob-wind/couple` derives and writes the SimulationCouplingDefinition (proposed → implemented;
    # evidence stays none until a run pairs to it and steps)
    _M(name='wind-grid→bob-wind', kind='coupling', source_node='wind-grid', source_dims_json='["x","y","z","component"]', target_node='pendulum-bob', target_dims_json='["wind_vx","wind_vy","wind_vz"]',
       expression_ref='wind-sample-at-bob', validity_json=json.dumps({'speed': [0, 30]}), units='m/s', loss_note='the field is SAMPLED at the bob: one cell\'s velocity is injected as wind_vx/vy/vz',
       mapping_status='proposed', evidence_level='none', evidence_ref='', provenance='declared from the tree (tt-7); no coupling row until a person creates it'),
    _M(name='wind-grid→spectrum', kind='decomposition', source_node='wind-grid', source_dims_json='["x","y","z","speed"]', target_node='wind-turbulence', target_dims_json='["mode"]',
       validity_json=json.dumps({'speed': [0, 5]}), loss_note='a proposed low-rank decomposition — valid only for calm wind until proven',
       mapping_status='proposed', evidence_level='none', evidence_ref='', provenance='tt-1 (a hypothesis, on purpose)'),
]
# ---- tt-2: the MECHANICS tree over the plate — displacement → strain → stress → force balance as mappings.
# tt-6 RESOLVED the root: the σ field is written down as an FEMFieldState row (tensormath.custom.fem_field) and a
# 2-D `field` binding `FEMFieldState-2d` in scene `plate-mechanics-2d` colours one cell per element by σ_vm over
# the SAME domain the dimension plate.sigma declares (PLATE_SIGMA_DOMAIN — one constant on both sides). What is
# still NOT seen is u per node (2-D has no vector channel): that lives on plate-displacement as the tree's
# remaining, truthfully typed visualization space. Nothing is pretended.
try:
    from tensormath.tensormath_seed import PLATE_SIGMA_DOMAIN as _SIGMA_DOMAIN
except Exception:   # pragma: no cover - tensortree without tensormath
    _SIGMA_DOMAIN = [0.8e6, 1.1e6]
_P = 'plate-mechanics'
SEED_TENSOR_TREES += [{'name': _P, 'description': 'continuum mechanics of the tt-2 plate: u → ε → σ = C:ε → ∂σ/∂x + f = 0 (Validation B)',
                       'tensor': 'tt2-sigma', 'root_node': 'plate', 'view_kind': 'operator', 'status': 'partial', 'notes': ''}]
SEED_LOCALIZED_DIMENSIONS += [
    _ld('plate', 'x', 'position.x') | {'dimension': 'tt2-centroids.xy'}, _ld('plate', 'y', 'position.y') | {'dimension': 'tt2-centroids.xy'},
    _ld('plate', 'sigma', 'color', sc=json.dumps({'kind': 'continuous', 'domain': _SIGMA_DOMAIN, 'unit': 'Pa', 'field': 'von Mises'})) | {'dimension': 'tt2-sigma'},
    _ld('plate', 'element', 'shape') | {'dimension': 'tt2-mesh.triangles'},
    _ld('plate-displacement', 'x', 'position.x') | {'dimension': 'tt2-u'}, _ld('plate-displacement', 'y', 'position.y') | {'dimension': 'tt2-u'},
    _ld('plate-displacement', 'u', 'vector') | {'dimension': 'tt2-u'},
    _ld('plate-mesh', 'x', 'position.x') | {'dimension': 'tt2-u'}, _ld('plate-mesh', 'y', 'position.y') | {'dimension': 'tt2-u'},
    _ld('plate-mesh', 'edge', 'shape') | {'dimension': 'tt2-mesh.edges'},
]
SEED_TENSOR_NODES += [
    {'name': 'plate', 'description': '', 'tree': _P, 'parent': '', 'title': 'the plate: σ per element', 'tensor': 'tt2-sigma',
     'dims_json': json.dumps(['plate.x', 'plate.y', 'plate.sigma', 'plate.element']), 'binding_ref': 'FEMFieldState-2d',
     'global_params_json': json.dumps({'case': 'tt2-plate-tension', 'sim_space': 'plate-mechanics-2d', 'field_row': 'tt2-plate-tension-field'}),
     'status': 'unresolved', 'notes': 'tt-6: x/y → position, σ_vm → color through the 2-D field binding FEMFieldState-2d; tt-11: element → shape (each cell is its own triangle: a polygon MathShapeDefinition → a Shape2DDefinition in space units, referenced per cell) — filled cells THROUGH the shape library (status is set by the validator)'},
    {'name': 'plate-strain', 'description': '', 'tree': _P, 'parent': 'plate', 'title': 'ε per element', 'tensor': 'tt2-eps', 'dims_json': '[]', 'binding_ref': '', 'global_params_json': '{}', 'status': 'unresolved', 'notes': ''},
    {'name': 'plate-displacement', 'description': '', 'tree': _P, 'parent': 'plate', 'title': 'u per node', 'tensor': 'tt2-u',
     'dims_json': json.dumps(['plate-displacement.x', 'plate-displacement.y', 'plate-displacement.u']), 'binding_ref': 'FEMFieldState-u-2d',
     'global_params_json': json.dumps({'sim_space': 'plate-mechanics-2d', 'exaggeration': 20000.0}),
     'status': 'unresolved', 'notes': 'tt-8: u → vector through the 2-D `vectorfield` binding (node → node + k·u on the CONNECTIONS channel; k = 20000 is a stated knob, the raw u rides each line). The former visualization space\'s question — what exaggeration is honest? — is answered: the one that is written down.'},
    {'name': 'plate-mesh', 'description': '', 'tree': _P, 'parent': 'plate', 'title': 'the mesh: P1 triangles as their edges', 'tensor': 'tt2-u',
     'dims_json': json.dumps(['plate-mesh.x', 'plate-mesh.y', 'plate-mesh.edge']), 'binding_ref': 'FEMFieldState-mesh-2d', 'global_params_json': json.dumps({'sim_space': 'plate-mechanics-2d'}),
     'status': 'unresolved', 'notes': 'tt-9: the triangles SEEN as a wireframe (each edge once, on the CONNECTIONS channel). The former plate-geometry question is answered: the 2-D shape library takes a shapeRef, not vertices — so edges now, filled cells only with a renderer change (kept as the tree\'s open space).'},
]
# tt-8 resolved the former `plate-displacement-visualization` space (its question is answered by the knob); a
# tree with no unresolved space is allowed — nothing is kept unresolved for show. What remains open on the plate
# is the geometry itself (cells are markers at centroids, not the triangles) — a visualization space on the root.
SEED_UNRESOLVED += [
    # tt-11 resolved `plate-filled-cells` through the math-shape library (his ruling: our own library carries it) — the
    # plate tree now has NO unresolved space, which is allowed: nothing is kept unresolved for show
]
SEED_TENSOR_MAPPINGS += [
    _M(name='u→eps', kind='operator', source_node='plate-displacement', source_dims_json='["node","i"]', target_node='plate-strain', target_dims_json='["n","k","l"]',
       validity_json=json.dumps({'strain': [0, 0.002]}), units='1', loss_note='the symmetric gradient: rotation is dropped (small strain)',
       mapping_status='validated', evidence_level='simulated', evidence_ref='materialsScience.engines.fem_engine solve_elasticity_2d (P1 gradient, scikit-fem)', provenance='the engine\'s own strain recovery'),
    _M(name='eps→sigma', kind='operator', source_node='plate-strain', source_dims_json='["n","k","l"]', target_node='plate', target_dims_json='["n","i","j"]',
       expression_ref='tt2-sigma-from-C', validity_json=json.dumps({'strain': [0, 0.002]}), units='Pa', conservation_json='[]',
       loss_note='none: C is invertible for -1 < ν < 0.5', mapping_status='validated', evidence_level='simulated',
       evidence_ref='tensormath selftest: σ = C:ε by named contraction equals the engine\'s σ (rtol 1e-9)', provenance='Hooke, with E/ν from opt-electrical-steel (literature-est)'),
    _M(name='sigma→balance', kind='operator', source_node='plate', source_dims_json='["n","i","j"]', target_node='plate', target_dims_json='["node","i"]',
       validity_json=json.dumps({'strain': [0, 0.002]}), units='N/m³', conservation_json='["linear momentum"]', loss_note='',
       mapping_status='implemented', evidence_level='analytical', evidence_ref='∂σ_ij/∂x_j + f_i = ρ ü_i holds weakly by construction of the FEM solve (static: ü = 0); a residual reading is not computed here',
       provenance='the balance the solve enforces'),
]
SEED_TENSOR_SELECTIONS = [{'name': 'plate-strain-all', 'description': 'every element\'s strain', 'node': 'plate-strain', 'ranges_json': json.dumps({'n': [0, 64], 'k': [0, 2], 'l': [0, 2], 'strain': [0, 0.001]}), 'created_from': 'seed (tt-2)', 'created_at': '2026-09-23', 'notes': ''},
                          {'name': 'gust-corner', 'description': 'a gusty corner of the grid', 'node': 'wind-grid',
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
