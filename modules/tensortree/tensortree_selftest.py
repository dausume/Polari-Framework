"""
Selftest for tensortree (tt-0). Run from polari-framework/:
  PYTHONPATH=.:modules python3 modules/tensortree/tensortree_selftest.py
Fake manager; exercises: the seven classes, the six structural rules, LOCAL validity, typed unresolvedness,
discovery = hard filters then the configured score, the graph view, the manifest.
"""
import json
import sys
import types

from tensortree.tensortree_basis import (TENSORTREE_CLASSES, TensorTreeDefinition, TensorNode, UnresolvedTensorSpace,
                                         LocalizedDimension, TensorMapping, TensorSelection, TensorDiscoveryPolicy)
from tensortree.tensortree_seed import TENSORTREE_SEED_PAIRS, SEED_DISCOVERY_POLICIES
from tensortree.custom.tensortree_validate import validate_tree, CHANNELS, UNRESOLVED_KINDS, dimension_coherent
from tensortree.custom.tensortree_discover import discover, policy, DEFAULT_POLICY
from tensortree.custom.tensortree_graph import tree_graph

_results = []


def check(label, cond, extra=''):
    _results.append((label, bool(cond)))
    print(f'{"PASS" if cond else "FAIL"}: {label}' + (f' — {extra}' if extra and not cond else ''))


def _mgr():
    tables = {c.__name__: {} for c in TENSORTREE_CLASSES}
    return types.SimpleNamespace(objectTables=tables, db=None)


def _add(mgr, cls, **kw):
    row = types.SimpleNamespace(**kw); mgr.objectTables[cls][id(row)] = row; return row


check('the module registers exactly SEVEN row classes (the count is asserted so a class cannot ride in unnoticed)',
      len(TENSORTREE_CLASSES) == 7, [c.__name__ for c in TENSORTREE_CLASSES])
check('every class is one file under objects/tensortree/', all(c.__module__ == 'tensortree.objects.tensortree.%s' % c.__name__ for c in TENSORTREE_CLASSES))
check('seed pairs cover every class, and the ONE seeded row is the default discovery policy',
      [p[0] for p in TENSORTREE_SEED_PAIRS] == [c.__name__ for c in TENSORTREE_CLASSES] and SEED_DISCOVERY_POLICIES[0]['is_default'])
check('the visual channel vocabulary is the eleven of plan §F4', set(CHANNELS) == {'position.x', 'position.y', 'position.z', 'color', 'opacity', 'size', 'shape', 'orientation', 'vector', 'label', 'time'})
check('unresolvedness is TYPED by the five research tasks (plan §F6.2)', UNRESOLVED_KINDS == ('semantic', 'structural', 'visualization', 'mapping', 'validation'))

# ---- a tree: T(x,y,z) with a resolved root, a resolved child, an unresolved space BETWEEN two resolved nodes
m = _mgr()
_add(m, 'TensorTreeDefinition', name='thermal', tensor='T-field', root_node='field', view_kind='spatial', status='partial')
for n, ch, sc in (('x', 'position.x', {}), ('y', 'position.y', {}), ('z', 'position.z', {}), ('T', 'color', {'kind': 'continuous', 'domain': [300, 900]})):
    _add(m, 'LocalizedDimension', name='field.' + n, node='field', dimension=n, range_json='[]', channel=ch, scale_json=json.dumps(sc), coherent=False)
_add(m, 'TensorNode', name='field', tree='thermal', parent='', title='T(x,y,z)', tensor='T-field', dims_json=json.dumps(['field.x', 'field.y', 'field.z', 'field.T']), binding_ref='thermal-field-3d', status='unresolved')
_add(m, 'LocalizedDimension', name='slice.x', node='slice', dimension='x', range_json='[12,16]', channel='position.x', scale_json='{}', coherent=False)
_add(m, 'LocalizedDimension', name='slice.T', node='slice', dimension='T', range_json='[]', channel='colour', scale_json='{}', coherent=False)   # a typo channel
_add(m, 'TensorNode', name='slice', tree='thermal', parent='field', title='a slice', tensor='T-field', dims_json=json.dumps(['slice.x', 'slice.T']), binding_ref='thermal-slice', status='unresolved')
_add(m, 'UnresolvedTensorSpace', name='grain', tree='thermal', parent='field', title='grain structure', unresolved_kind='mapping',
     known_dims_json='["x","y","z"]', open_questions_json='["how does T map to the grain boundary density?"]')
_add(m, 'LocalizedDimension', name='gb.x', node='gb', dimension='x', range_json='[]', channel='position.x', scale_json='{}', coherent=False)
_add(m, 'TensorNode', name='gb', tree='thermal', parent='grain', title='grain boundaries', tensor='GB-field', dims_json='["gb.x"]', binding_ref='gb-2d', status='unresolved')
rep = validate_tree(m, 'thermal')
check('a well-formed tree passes rules 1–3 (one root, parents exist, acyclic)', rep['ok'], rep['errors'])
check('the root node is RESOLVED: every localized dimension has a channel from the vocabulary + a binding', rep['nodes']['field']['status'] == 'resolved', rep['nodes']['field'])
check('  …a continuous colour scale with a numeric domain is coherent', 'field.T' in rep['nodes']['field']['coherent'])
check('a node with a channel outside the vocabulary is UNRESOLVED and the report names the dimension and why',
      rep['nodes']['slice']['status'] == 'unresolved' and 'slice.T' in rep['nodes']['slice']['incoherent'], rep['nodes']['slice'])
check('validity is LOCAL: the unresolved space + the unresolved child do not change the root\'s status (plan §F6.1)', rep['nodes']['field']['status'] == 'resolved')
check('a resolved node BELOW an unresolved space is still resolved (TensorNode → Unresolved → TensorNode is valid)', rep['nodes']['gb']['status'] == 'resolved', rep['nodes']['gb'])
check('the unresolved space is reported with its kind and its open questions', rep['unresolved']['grain']['kind'] == 'mapping' and rep['unresolved']['grain']['open_questions'])
_add(m, 'TensorNode', name='second-root', tree='thermal', parent='', title='', tensor='', dims_json='[]', binding_ref='', status='unresolved')
check('rule 1: a second root is an error', not validate_tree(m, 'thermal')['ok'] and any('rule 1' in e for e in validate_tree(m, 'thermal')['errors']))
del m.objectTables['TensorNode'][[k for k, v in m.objectTables['TensorNode'].items() if v.name == 'second-root'][0]]
_add(m, 'TensorNode', name='orphan', tree='thermal', parent='nope', title='', tensor='', dims_json='[]', binding_ref='', status='unresolved')
check('rule 2: a parent that is not in the tree is an error', any('rule 2' in e for e in validate_tree(m, 'thermal')['errors']))
del m.objectTables['TensorNode'][[k for k, v in m.objectTables['TensorNode'].items() if v.name == 'orphan'][0]]
a = _add(m, 'TensorNode', name='ca', tree='thermal', parent='cb', title='', tensor='', dims_json='[]', binding_ref='', status='unresolved')
b = _add(m, 'TensorNode', name='cb', tree='thermal', parent='ca', title='', tensor='', dims_json='[]', binding_ref='', status='unresolved')
check('rule 3: a cycle is an error', any('rule 3' in e for e in validate_tree(m, 'thermal')['errors']))
for k in [k for k, v in m.objectTables['TensorNode'].items() if v.name in ('ca', 'cb')]:
    del m.objectTables['TensorNode'][k]
bad = types.SimpleNamespace(channel='color', dimension='T', scale_json='{"kind": "continuous", "domain": [900]}')
check('a continuous scale without [lo, hi] is incoherent', not dimension_coherent(bad)[0])

# ---- mappings may cross; the graph view
_add(m, 'TensorMapping', name='T→gb', kind='kernel', source_node='field', source_dims_json='["x","y","z","T"]', target_node='gb', target_dims_json='["x"]',
     validity_json='{"T": [300, 1200]}', mapping_status='implemented', evidence_level='simulated', evidence_ref='run-7', uncertainty_json='{"relative": 0.2}', loss_note='')
_add(m, 'TensorMapping', name='T→slice', kind='restriction', source_node='field', source_dims_json='["x"]', target_node='slice', target_dims_json='["x","T"]',
     validity_json='{}', mapping_status='validated', evidence_level='measured', evidence_ref='bench-1', uncertainty_json='{}', loss_note='')
_add(m, 'TensorMapping', name='needs-t', kind='operator', source_node='field', source_dims_json='["x","t"]', target_node='gb', target_dims_json='[]',
     validity_json='{}', mapping_status='proposed', evidence_level='none', evidence_ref='', uncertainty_json='{}', loss_note='')
_add(m, 'TensorMapping', name='cold-only', kind='scale', source_node='field', source_dims_json='["T"]', target_node='gb', target_dims_json='[]',
     validity_json='{"T": [0, 250]}', mapping_status='validated', evidence_level='measured', evidence_ref='bench-2', uncertainty_json='{}', loss_note='')
g = tree_graph(m, 'thermal')
check('rule 4: mappings may cross branches — the graph view carries them as crossing edges', any(e['kind'] == 'mapping' and e['crosses'] for e in g['edges']))
check('the graph is a VIEW: structure edges + mapping edges, no rows written', g['structural'] == 3 and g['mappings'] == 4 and 'TensorGraph' not in m.objectTables)

# ---- discovery: hard filters, then the configured score
_add(m, 'TensorDiscoveryPolicy', name='default', is_default=True, **{k: v for k, v in SEED_DISCOVERY_POLICIES[0].items() if k not in ('name', 'is_default')})
sel = _add(m, 'TensorSelection', name='hot-corner', node='field', ranges_json=json.dumps({'x': [12, 16], 'y': [8, 11], 'z': [2, 4], 'T': [780, 820]}), created_from='sim-space-viewer')
d = discover(m, sel)
names = [c['mapping'] for c in d['candidates']]
check('discovery: a mapping needing a dim the selection lacks is REFUSED by name, never scored', 'needs-t' not in names and any(r['mapping'] == 'needs-t' and 'dims' in r['why'] for r in d['refused']))
check('discovery: a selection outside the validity domain is REFUSED — a score never rescues it', 'cold-only' not in names and any(r['mapping'] == 'cold-only' and 'validity' in r['why'] for r in d['refused']))
check('discovery: the valid candidates are ranked — and evidence does NOT dominate compatibility: the implemented mapping that '
      'uses all four selected dims inside a stated validity domain outranks the measured one that uses one dim and states no domain',
      names == ['T→gb', 'T→slice'], names)
check('  …every candidate carries its evidence and the score terms', all({'evidence', 'evidence_ref', 'terms', 'score'} <= set(c) for c in d['candidates']))
check('  …the score is the configured formula (0.30E + 0.25D + 0.25V + 0.10C + 0.10(1−U))',
      abs(d['candidates'][0]['score'] - (0.30 * 0.65 + 0.25 * 1.0 + 0.25 * 1.0 + 0.10 * 0.5 + 0.10 * 0.8)) < 1e-6
      and abs(d['candidates'][1]['score'] - (0.30 * 1.0 + 0.25 * 0.25 + 0.25 * 0.5 + 0.10 * 0.5 + 0.10 * 1.0)) < 1e-6, d['candidates'])
check('  …simulated + implemented scores as "implemented" (never as measured) — OpenSTA is not a bench', d['candidates'][0]['evidence'] == 'implemented')
check('the policy comes from the default row (knobs), with the built-in as the fallback', policy(m)['w_evidence'] == 0.30 and policy(_mgr()) == dict(DEFAULT_POLICY))
p = [r for r in m.objectTables['TensorDiscoveryPolicy'].values()][0]; p.w_evidence = 0.9; p.w_dims = 0.05
d2 = discover(m, sel)
check('  …changing the row changes the ranking: with evidence weighted 0.9 the MEASURED mapping now comes first — no constant in code',
      [c['mapping'] for c in d2['candidates']] == ['T→slice', 'T→gb'] and abs(d2['candidates'][0]['score'] - (0.9 * 1.0 + 0.05 * 0.25 + 0.25 * 0.5 + 0.05 + 0.10)) < 1e-6, d2['candidates'])
# ---- tt-13: discovery ACROSS trees — the units filter (§F3) is a hard one
from tensortree.custom.tensortree_discover import node_dim_units
m.objectTables.setdefault('Tensor', {}); m.objectTables.setdefault('TensorDimension', {})   # tensormath's tables, absent from this module's fixture
_add(m, 'Tensor', name='T-field', rank=4, dimensions_json=json.dumps([{'name': 'x', 'unit': 'm'}, {'name': 'y', 'unit': 'm'}, {'name': 'z', 'unit': 'm'}, {'name': 'T', 'unit': 'K'}]), units='K', storage_kind='matrix')
_add(m, 'Tensor', name='T-other', rank=2, dimensions_json=json.dumps([{'name': 'x', 'unit': 'm'}, {'name': 'T', 'unit': 'K'}]), units='K', storage_kind='matrix')
_add(m, 'Tensor', name='T-mm', rank=2, dimensions_json=json.dumps([{'name': 'x', 'unit': 'mm'}, {'name': 'T', 'unit': 'K'}]), units='K', storage_kind='matrix')
_add(m, 'TensorTreeDefinition', name='other', tensor='T-other', root_node='field2', view_kind='spatial', status='partial')
for nn, tt in (('field2', 'T-other'), ('field3', 'T-mm'), ('field4', 'T-nounits')):
    _add(m, 'TensorNode', name=nn, tree='other', parent='' if nn == 'field2' else 'field2', title=nn, tensor=tt, dims_json=json.dumps([nn + '.x', nn + '.T']), binding_ref='', status='unresolved')
    _add(m, 'LocalizedDimension', name=nn + '.x', node=nn, dimension='x', range_json='[]', channel='position.x', scale_json='{}', coherent=False)
    _add(m, 'LocalizedDimension', name=nn + '.T', node=nn, dimension='T', range_json='[]', channel='color', scale_json='{}', coherent=False)
_add(m, 'TensorMapping', name='other:T→x', kind='kernel', source_node='field2', source_dims_json='["x","T"]', target_node='field3', target_dims_json='["x"]', validity_json='{"T": [300, 1200]}', mapping_status='implemented', evidence_level='simulated', evidence_ref='run-9', uncertainty_json='{}', loss_note='')
_add(m, 'TensorMapping', name='mm:T→x', kind='kernel', source_node='field3', source_dims_json='["x","T"]', target_node='field2', target_dims_json='["x"]', validity_json='{}', mapping_status='validated', evidence_level='measured', evidence_ref='bench-3', uncertainty_json='{}', loss_note='')
_add(m, 'TensorMapping', name='nounits:T→x', kind='kernel', source_node='field4', source_dims_json='["x","T"]', target_node='field2', target_dims_json='[]', validity_json='{}', mapping_status='validated', evidence_level='measured', evidence_ref='bench-4', uncertainty_json='{}', loss_note='')
_add(m, 'TensorMapping', name='other:needs-w', kind='kernel', source_node='field2', source_dims_json='["x","w"]', target_node='field3', target_dims_json='[]', validity_json='{}', mapping_status='validated', evidence_level='measured', evidence_ref='', uncertainty_json='{}', loss_note='')
check('tt-13 units: a node\'s dim units come through its LocalizedDimensions → the tensor\'s dimensions (m, m, m, K on field; unknown = "" on a node whose tensor has no row)',
      node_dim_units(m, 'field') == {'x': 'm', 'y': 'm', 'z': 'm', 'T': 'K'} and node_dim_units(m, 'field4') == {'x': '', 'T': ''}, (node_dim_units(m, 'field'), node_dim_units(m, 'field4')))
d3 = discover(m, sel)
_cross = [c for c in d3['candidates'] if c.get('cross_tree')]
check('tt-13: a mapping written for ANOTHER tree\'s node is a candidate on this selection when every dim it needs exists here by name AND unit (other:T→x: x in m, T in K on both) — flagged cross_tree with its source node, the shared units, a lower context term (C 0.25) and a why_here',
      [c['mapping'] for c in _cross] == ['other:T→x'] and _cross[0]['source_node'] == 'field2' and _cross[0]['units'] == {'x': 'm', 'T': 'K'} and _cross[0]['terms']['C'] == 0.25 and 'same unit' in _cross[0]['why_here'] and d3['cross_tree_candidates'] == 1, _cross)
check('  …the same dim name in a DIFFERENT unit is INAPPLICABLE (x is m here, mm there), never scored; a dim with NO unit recorded on the other node is inapplicable and says which side is silent — compatibility is never assumed',
      any(r['mapping'] == 'mm:T→x' and r['kind'] == 'units-incompatible' and 'm here, mm there' in r['why'] for r in d3['inapplicable'])
      and any(r['mapping'] == 'nounits:T→x' and r['kind'] == 'units-unknown' and 'field4' in r['why'] for r in d3['inapplicable']) and not any(c['mapping'] in ('mm:T→x', 'nounits:T→x') for c in d3['candidates']), d3['inapplicable'])
check('  …a cross-tree mapping whose dims are NOT all here is simply not a candidate (no refusal row per foreign mapping); own-node candidates are unchanged and still rank by the configured score (the 0.9-evidence policy set just above: measured first); the response says the units of this node',
      not any(r['mapping'] == 'other:needs-w' for r in d3['inapplicable'] + d3['candidates']) and [c['mapping'] for c in d3['candidates'] if not c.get('cross_tree')] == ['T→slice', 'T→gb'] and d3['units_here']['T'] == 'K', [c['mapping'] for c in d3['candidates']])

# ---- tt-1: the SEEDED tree over the real wind field validates, and discovery works on the seeded selection
from tensortree.tensortree_seed import (SEED_TENSOR_TREES, SEED_TENSOR_NODES, SEED_UNRESOLVED, SEED_LOCALIZED_DIMENSIONS, SEED_TENSOR_MAPPINGS, SEED_TENSOR_SELECTIONS)
m2 = _mgr()
for cls, rows in (('TensorTreeDefinition', SEED_TENSOR_TREES), ('TensorNode', SEED_TENSOR_NODES), ('UnresolvedTensorSpace', SEED_UNRESOLVED),
                  ('LocalizedDimension', SEED_LOCALIZED_DIMENSIONS), ('TensorMapping', SEED_TENSOR_MAPPINGS), ('TensorSelection', SEED_TENSOR_SELECTIONS),
                  ('TensorDiscoveryPolicy', SEED_DISCOVERY_POLICIES)):
    for r in rows:
        _add(m2, cls, **r)
rep = validate_tree(m2, 'wind-spatial')
check('seeded tree: passes the structural rules', rep['ok'], rep['errors'])
check('seeded tree: the root wind-grid is RESOLVED — x/y/z → position, speed → color (0–12 m/s), w → vector, bound to the proven WindFieldGridState-3d binding',
      rep['nodes']['wind-grid']['status'] == 'resolved' and rep['nodes']['wind-grid']['binding_ref'] == 'WindFieldGridState-3d', rep['nodes']['wind-grid'])
check('  …and the z=0 slice is resolved too', rep['nodes']['wind-slice-z0']['status'] == 'resolved')
check('  …the unresolved sub-grid space is typed semantic and keeps its open question', rep['unresolved']['wind-turbulence']['kind'] == 'semantic' and rep['unresolved']['wind-turbulence']['open_questions'])
gsel = next(s for s in m2.objectTables['TensorSelection'].values() if s.name == 'gust-corner')
d = discover(m2, gsel)
names = [c['mapping'] for c in d['candidates']]
check('discovery on the gusty selection: the REAL coupling (validated, simulated) ranks first, the restriction second',
      names == ['wind-grid→bob-drag', 'wind-grid→slice-z0'], (names, d['refused']))
check('  …and the calm-only spectrum hypothesis is REFUSED: speed 6–12 m/s lies outside its validity [0, 5]', any(r['mapping'] == 'wind-grid→spectrum' and 'validity' in r['why'] for r in d['refused']), d['refused'])
check('  …the coupling candidate names the live SimulationCouplingDefinition it is', next(mm for mm in m2.objectTables['TensorMapping'].values() if mm.name == 'wind-grid→bob-drag').coupling_ref == 'wind-to-newtonian-pendulum')
g = tree_graph(m2, 'wind-spatial')
check('the graph view of the seeded tree: 2 structural edges (slice, turbulence) + 4 mappings (tt-7 added the proposed coupling), two crossing to the bob\'s tree', g['structural'] == 2 and g['mappings'] == 4, g)

# ---- tt-7: a SimulationCouplingDefinition CREATED FROM a kind=coupling mapping — derived, refused by name, then written
from tensortree.custom.tensortree_couple import propose as propose_coupling, couple as create_coupling
from tensormath.tensormath_seed import SEED_TENSORS, SEED_TENSOR_EXPRESSIONS
m2.objectTables['Tensor'] = {}; m2.objectTables['TensorMathExpression'] = {}; m2.objectTables['SimulationCouplingDefinition'] = {}; m2.objectTables['MatrixEquationDefinition'] = {}
for r in SEED_TENSORS: _add(m2, 'Tensor', **r)
for r in SEED_TENSOR_EXPRESSIONS: _add(m2, 'TensorMathExpression', **r)
p0 = propose_coupling(m2, 'wind-grid→bob-wind')
check('propose: with no sim-state classes loaded the door REFUSES and names both missing simulation definitions (never guesses)',
      not p0['ok'] and p0['status'] == 422 and sum('declares no simulation_definition_name' in x for x in p0['missing']) == 2, p0['missing'])
m2.objectTypingDict = {'WindFieldGridState': types.SimpleNamespace(classDefinition=types.SimpleNamespace(simulation_definition_name='wind-field-3d')),
                       'NewtonianPendulumBobSimState': types.SimpleNamespace(classDefinition=types.SimpleNamespace(simulation_definition_name='newtonian-pendulum-3d'))}
p1 = propose_coupling(m2, 'wind-grid→bob-wind')
_cfg = json.loads(p1['coupling']['config_json'])
check('propose: everything DERIVED — source wind-field-3d/WindFieldGridState (cells_json), target newtonian-pendulum-3d/NewtonianPendulumBobSimState, pos = [px, py, pz] from the bob\'s position dims, sampler from the expression\'s matrix_equation_ref, inject = the mapping\'s target_dims',
      p1['ok'] and p1['coupling']['source_simulation_ref'] == 'wind-field-3d' and p1['coupling']['target_class_name'] == 'NewtonianPendulumBobSimState' and p1['coupling']['sampler_equation_ref'] == 'field-sample-nearest'
      and _cfg['sampler']['operands']['cells'] == {'kind': 'source_field_json', 'field': 'cells_json'} and _cfg['sampler']['operands']['pos']['fields'] == ['px', 'py', 'pz']
      and list(_cfg['inject']) == ['wind_vx', 'wind_vy', 'wind_vz'] and _cfg['inject']['wind_vz'] == {'kind': 'sample_element', 'index': 2} and _cfg['defaults'] == {'wind_vx': 0.0, 'wind_vy': 0.0, 'wind_vz': 0.0}, p1)
check('  …a dry run writes nothing', m2.objectTables['SimulationCouplingDefinition'] == {} and next(mm for mm in m2.objectTables['TensorMapping'].values() if mm.name == 'wind-grid→bob-wind').coupling_ref == '')
_add(m2, 'MatrixEquationDefinition', name='some-other-equation')
p2 = propose_coupling(m2, 'wind-grid→bob-wind')
check('  …once the instance holds matrix equations, the sampler must be one of them (refused by name)', not p2['ok'] and any('field-sample-nearest' in x and 'not a saved' in x for x in p2['missing']), p2['missing'])
_add(m2, 'MatrixEquationDefinition', name='field-sample-nearest')
p3 = propose_coupling(m2, 'wind-grid→slice-z0')
check('  …a non-coupling mapping is refused as such (422)', not p3['ok'] and p3['status'] == 422 and 'kind=restriction' in p3['error'], p3)
p4 = create_coupling(m2, 'wind-grid→bob-drag')
check('  …a mapping that already names a coupling is a 409 that names it (force to add another)', p4['status'] == 409 and p4['coupling_ref'] == 'wind-to-newtonian-pendulum', p4)
_mk = lambda cls, **f: _add(m2, 'SimulationCouplingDefinition', **f)
p5 = create_coupling(m2, 'wind-grid→bob-wind', make=_mk)
_mp = next(mm for mm in m2.objectTables['TensorMapping'].values() if mm.name == 'wind-grid→bob-wind')
check('couple: CREATES the row tt-wind-grid-to-bob-wind, sets the mapping\'s coupling_ref, proposed → implemented, evidence STAYS none (nothing has run)',
      p5['status'] == 201 and p5['created'] == 'tt-wind-grid-to-bob-wind' and any(getattr(r, 'name', '') == 'tt-wind-grid-to-bob-wind' for r in m2.objectTables['SimulationCouplingDefinition'].values())
      and _mp.coupling_ref == 'tt-wind-grid-to-bob-wind' and _mp.mapping_status == 'implemented' and _mp.evidence_level == 'none' and 'tt-7' in _mp.provenance, p5)
p6 = create_coupling(m2, 'wind-grid→bob-wind', make=_mk)
check('  …and a second POST is a 409 (already coupled), not a second row', p6['status'] == 409 and len(m2.objectTables['SimulationCouplingDefinition']) == 1, p6)
rep_b = validate_tree(m2, 'bob-motion')
check('the bob\'s own tree validates with its root RESOLVED (px/py/pz → position, fwind → vector, the wind-arrow binding)', rep_b['ok'] and rep_b['nodes']['pendulum-bob']['status'] == 'resolved', rep_b)

# ---- tt-2: the mechanics tree — honest about its visualization, right about its mappings
rep2 = validate_tree(m2, 'plate-mechanics')
check('plate-mechanics passes the structural rules', rep2['ok'], rep2['errors'])
# tt-6: with no SimSpaceBindingDefinition rows in sight the validator trusts the name; once the instance holds
# bindings, the name must be one of them — a resolved node is one a viewer can draw
check('tt-6: the plate root is RESOLVED — x/y → position, σ_vm → color, bound to FEMFieldState-2d (the 2-D field binding)',
      rep2['nodes']['plate']['status'] == 'resolved' and rep2['nodes']['plate']['binding_ref'] == 'FEMFieldState-2d' and rep2['nodes']['plate']['coherent'] == ['plate.x', 'plate.y', 'plate.sigma', 'plate.element'], rep2['nodes']['plate'])
m2.objectTables['SimSpaceBindingDefinition'] = {}
_add(m2, 'SimSpaceBindingDefinition', name='WindFieldGridState-3d', class_name='WindFieldGridState')
rep2b = validate_tree(m2, 'plate-mechanics')
check('  …but NOT when the instance holds bindings and none is named FEMFieldState-2d: the reason names the missing binding',
      rep2b['nodes']['plate']['status'] == 'unresolved' and 'names no SimSpaceBindingDefinition' in rep2b['nodes']['plate']['why'], rep2b['nodes']['plate'])
_add(m2, 'SimSpaceBindingDefinition', name='FEMFieldState-2d', class_name='FEMFieldState')
_add(m2, 'SimSpaceBindingDefinition', name='FEMFieldState-u-2d', class_name='FEMFieldState')
_add(m2, 'SimSpaceBindingDefinition', name='FEMFieldState-mesh-2d', class_name='FEMFieldState')
rep2 = validate_tree(m2, 'plate-mechanics')
check('  …and resolves again once the binding row exists', rep2['nodes']['plate']['status'] == 'resolved')
check('  …tt-8: u per node is RESOLVED too (x/y → position, u → vector through the 2-D vectorfield binding FEMFieldState-u-2d, exaggeration a stated knob); the remaining space is the GEOMETRY (triangles, not markers)',
      rep2['nodes']['plate-displacement']['status'] == 'resolved' and rep2['nodes']['plate-displacement']['binding_ref'] == 'FEMFieldState-u-2d'
      and 'plate-displacement-visualization' not in rep2['unresolved'], (rep2['nodes']['plate-displacement'], list(rep2['unresolved'])))
check('  …tt-9: the mesh node is RESOLVED (edges as a wireframe via FEMFieldState-mesh-2d); tt-11: filled cells resolved THROUGH THE SHAPE LIBRARY (element → shape on the root) — the plate tree has NO unresolved space left, honestly',
      rep2['nodes']['plate-mesh']['status'] == 'resolved' and 'plate.element' in rep2['nodes']['plate']['coherent'] and list(rep2['unresolved']) == [], (rep2['nodes'].get('plate-mesh'), list(rep2['unresolved'])))
check('  …the σ colour domain of the dimension is the binding\'s (one constant: tensormath.PLATE_SIGMA_DOMAIN)',
      __import__('json').loads(next(d for d in SEED_LOCALIZED_DIMENSIONS if d['name'] == 'plate.sigma')['scale_json'])['domain'] == __import__('tensormath.tensormath_seed', fromlist=['x']).PLATE_SIGMA_DOMAIN)
psel = next(s for s in m2.objectTables['TensorSelection'].values() if s.name == 'plate-strain-all')
d2 = discover(m2, psel)
check('discovery from the strain node finds eps→sigma (validated, simulated, with the interop selftest as evidence)', [c['mapping'] for c in d2['candidates']] == ['eps→sigma'] and d2['candidates'][0]['evidence_ref'].startswith('tensormath selftest'), d2)
check('the chain u → ε → σ → balance is three operator mappings with validity 0–0.2 % strain and momentum conservation named on the balance',
      {mm.name for mm in m2.objectTables['TensorMapping'].values() if str(mm.kind) == 'operator'} >= {'u→eps', 'eps→sigma', 'sigma→balance'}
      and 'linear momentum' in next(mm for mm in m2.objectTables['TensorMapping'].values() if mm.name == 'sigma→balance').conservation_json)

# ---- tt-4 / Phase 7: the SCALE tree of a material is a READING of the materials model (msci + pspp)
from tensortree.custom.tensortree_scale import scale_tree, materialise
from materialsScience.materials_basis_seed import SEED_MS_SCALE_DEFINITIONS as SEED_MATERIAL_SCALES
from pspp.objects.scale_transfers._shared import SEED_SCALE_TRANSFERS
m4 = _mgr(); m4.objectTables.update({'MaterialScaleDefinition': {}, 'ScaleTransferDefinition': {}, 'MultiScaleSimulationProfile': {}})
for r in SEED_MATERIAL_SCALES:
    _add(m4, 'MaterialScaleDefinition', **r)
for r in SEED_SCALE_TRANSFERS:
    _add(m4, 'ScaleTransferDefinition', **r)
_add(m4, 'MultiScaleSimulationProfile', name='p', fidelity_ladder_json=json.dumps([{'rung': 1, 'level': 'L1', 'engines': ['fem'], 'costClass': 'cheap', 'purpose': 'screening'}, {'rung': 4, 'level': 'L4', 'engines': ['dft'], 'costClass': 'expensive', 'purpose': 'evidence'}]))
v = scale_tree(m4, 'paraffin-wax')
check('scale tree: paraffin wax is READ from the materials model — levels present become nodes, missing levels become STRUCTURAL unresolved spaces',
      v['ok'] and {n['level'] for n in v['nodes']} == {0, 4} and {u['level'] for u in v['unresolved']} == {1, 2, 3} and all(u['unresolved_kind'] == 'structural' for u in v['unresolved']), (v.get('error'), [n['level'] for n in v['nodes']]))
check('  …the root is the coarsest level present (experimental — what was measured)', v['root'] == 'paraffin-wax@L0')
check('  …the fidelity ladder rides on the levels it names (cost class, engines) — on nodes AND on gaps', next(n for n in v['nodes'] if n['level'] == 4)['fidelity'].get('costClass') == 'expensive' and next(u for u in v['unresolved'] if u['level'] == 1)['fidelity'].get('costClass') == 'cheap')
check('  …the pspp scale transfers become kind=scale mappings BY REFERENCE, status mapped to the two statuses (executed → implemented + simulated)',
      len(v['mappings']) == 2 and all(mp['kind'] == 'scale' and mp['scale_transfer_ref'] == mp['name'] for mp in v['mappings'])
      and all(mp['mapping_status'] == 'implemented' and mp['evidence_level'] == 'simulated' for mp in v['mappings']), v['mappings'])
check('  …L0 → L1 (thermal continuum, INTO a gap) and L0 → L4 (quantum) are the edges — a mapping may target an unresolved space — and the view writes NO rows',
      {(mp['source_node'], mp['target_node']) for mp in v['mappings']} == {('paraffin-wax@L0', 'paraffin-wax@L1'), ('paraffin-wax@L0', 'paraffin-wax@L4')} and not m4.objectTables['TensorTreeDefinition'])
check('an unknown material is refused by name', not scale_tree(m4, 'unobtainium')['ok'])
_fake = lambda cls, cls_name, **f: _add(m4, cls_name, **f)
w = materialise(m4, 'paraffin-wax', make=_fake)
check('materialise: writes the tree rows (1 tree, 2 nodes, 3 unresolved, 2 mappings)', w['ok'] and w['written'] == {'tree': 'paraffin-wax@scale', 'nodes': 2, 'unresolved': 3, 'mappings': 2}, w.get('written'))
rep4 = validate_tree(m4, 'paraffin-wax@scale')
check('  …and the materialised tree passes the structural rules with L0 as the one root', rep4['ok'] and len([n for n in m4.objectTables['TensorNode'].values() if getattr(n, 'tree', '') == 'paraffin-wax@scale' and not n.parent]) == 1, rep4['errors'])
w2 = materialise(m4, 'paraffin-wax', make=_fake)
check('  …idempotent: materialising again writes the same rows, never duplicates', w2['written'] == w['written'] and len([n for n in m4.objectTables['TensorNode'].values() if getattr(n, 'tree', '') == 'paraffin-wax@scale']) == 2)
g4 = tree_graph(m4, 'paraffin-wax@scale')
check('  …the graph view shows the two transfers as mapping edges between levels', g4['mappings'] == 2 and g4['structural'] == 4)

# ---- the manifest
man = json.load(open('modules/tensortree/polari-app.json'))
from moduleService.manifests import validate
check('the manifest is valid and declares the seven classes + the API', validate(man) == [] and len([c for c in man['classes'] if c != 'TensorTreeAPI']) == 7)
check('the manifest requires tensormath (a tree views a Tensor)', man['requires']['modules'] == ['tensormath'])

n_ok = sum(1 for _, ok in _results if ok)
print(f'\n{n_ok}/{len(_results)} checks passed')
sys.exit(0 if n_ok == len(_results) else 1)
