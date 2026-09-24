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
check('the graph view of the seeded tree: 2 structural edges (slice, turbulence) + 3 mappings, one crossing to another tree\'s node', g['structural'] == 2 and g['mappings'] == 3)

# ---- tt-2: the mechanics tree — honest about its visualization, right about its mappings
rep2 = validate_tree(m2, 'plate-mechanics')
check('plate-mechanics passes the structural rules', rep2['ok'], rep2['errors'])
check('its root is UNRESOLVED for the stated reason: no binding (the element field has no sim-space binding yet) — not pretended', rep2['nodes']['plate']['status'] == 'unresolved' and rep2['nodes']['plate']['why'] == 'no binding_ref', rep2['nodes']['plate'])
check('  …and the unresolved VISUALIZATION space keeps the candidates (a 2-D field binding; a sci-xy-chart profile)', rep2['unresolved']['plate-visualization']['kind'] == 'visualization')
psel = next(s for s in m2.objectTables['TensorSelection'].values() if s.name == 'plate-strain-all')
d2 = discover(m2, psel)
check('discovery from the strain node finds eps→sigma (validated, simulated, with the interop selftest as evidence)', [c['mapping'] for c in d2['candidates']] == ['eps→sigma'] and d2['candidates'][0]['evidence_ref'].startswith('tensormath selftest'), d2)
check('the chain u → ε → σ → balance is three operator mappings with validity 0–0.2 % strain and momentum conservation named on the balance',
      {mm.name for mm in m2.objectTables['TensorMapping'].values() if str(mm.kind) == 'operator'} >= {'u→eps', 'eps→sigma', 'sigma→balance'}
      and 'linear momentum' in next(mm for mm in m2.objectTables['TensorMapping'].values() if mm.name == 'sigma→balance').conservation_json)

# ---- the manifest
man = json.load(open('modules/tensortree/polari-app.json'))
from moduleService.manifests import validate
check('the manifest is valid and declares the seven classes + the API', validate(man) == [] and len([c for c in man['classes'] if c != 'TensorTreeAPI']) == 7)
check('the manifest requires tensormath (a tree views a Tensor)', man['requires']['modules'] == ['tensormath'])

n_ok = sum(1 for _, ok in _results if ok)
print(f'\n{n_ok}/{len(_results)} checks passed')
sys.exit(0 if n_ok == len(_results) else 1)
