"""In-process live-boot PROBE of tt-0: boot the REAL polariServer with tensormath + tensortree + computelod (+
techtree, microchip, matrices are core) enabled, then hit their routes — proving the guarded imports, defClassList
wiring, seed pairs (eleven rungs, 70 kinds, the compute-lod tree, the default discovery policy) and route
registration work outside the selftest fixtures. Also proves the dep-0/1 cicd rows now type (they were missing
from defClassList).
Run from a THROWAWAY working directory (the boot writes its sqlite DB into ./data/ of the cwd — remove that dir between runs, or a
previous run's rows come back through the restore):
  cd /tmp/somewhere && PYTHONPATH=<framework>:<framework>/modules python3 <framework>/tests/tensor_liveboot_probe.py
"""
import json
import os
import sys
os.environ['POLARI_MODULES'] = 'simulations,simSpace,materialsScience,pspp,magnetics,scoring,techtree,microchip,cntfet,electrodevice,sifet,hwfpga,tensormath,tensortree,computelod,cicd'
os.environ.setdefault('POLARI_DB_BACKEND', 'sqlite')
FRAMEWORK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, FRAMEWORK); sys.path.insert(0, os.path.join(FRAMEWORK, 'modules'))
from falcon import testing  # noqa: E402
from objectTreeManagerDecorators import managerObject  # noqa: E402
manager = managerObject(hasServer=True, hasDB=True)
client = testing.TestClient(manager.polServer.falconServer)
results = []


def check(label, cond, extra=''):
    results.append(bool(cond)); print(('PASS' if cond else 'FAIL') + f': {label}' + (f'  [{extra}]' if extra and not cond else ''))


tables = manager.objectTables
# a class is TYPED when the manager's typing dict knows it (objectTables gets a key only once an instance exists)
typed = {(k if isinstance(k, str) else getattr(k, '__name__', str(k))) for k in manager.objectTypingDict.keys()} \
        | {getattr(v, 'className', '') for v in manager.objectTypingDict.values()}
for cls in ('Tensor', 'TensorDimension', 'TensorMathExpression', 'TensorOperator', 'ComputeImplementation', 'TensorDecomposition',
            'TensorTreeDefinition', 'TensorNode', 'UnresolvedTensorSpace', 'LocalizedDimension', 'TensorMapping', 'TensorSelection', 'TensorDiscoveryPolicy',
            'ComputeLOD', 'ComputeKind', 'ComputeMapping', 'CharacterizationMapping', 'CompilerArtifact', 'DeployTarget', 'DeployRecord'):
    check('class %s is typed after boot (objectTypingDict)' % cls, cls in typed, sorted(typed)[:6])
lods = list(tables.get('ComputeLOD', {}).values())
check('eleven rungs seeded', len(lods) == 11, len(lods))
check('70 kinds seeded', len(tables.get('ComputeKind', {})) == 70, len(tables.get('ComputeKind', {})))
tn = [n for n in tables.get('TechNode', {}).values() if getattr(n, 'tree_name', '') == 'compute-lod']
check('the compute-lod tech tree has its eleven concept nodes', len(tn) == 11, len(tn))
check('the default discovery policy row is seeded', any(getattr(p, 'is_default', False) for p in tables.get('TensorDiscoveryPolicy', {}).values()))
r = client.simulate_get('/api/computelod')
check('GET /api/computelod answers the ladder', r.status_code == 200 and len(r.json['ladder']) == 11 and 'tensor-array' in r.json['ladder'][3]['kinds'], r.status_code)
r = client.simulate_get('/api/computelod/rungs/isa')
check('GET /api/computelod/rungs/isa carries recommended prerequisites from the tree', r.status_code == 200 and 'lod-logic-netlist' in r.json['learn']['recommended_prerequisites'], r.json if r.status_code != 200 else '')
r = client.simulate_get('/api/computelod/walk/c-source/x')
check('a walk with no mapping is an honest gap (200, unresolved)', r.status_code == 200 and r.json['walk']['unresolved'])
r = client.simulate_get('/api/tensormath')
check('GET /api/tensormath lists the two seeded engine-backed tensors', r.status_code == 200 and {'waxprint-series', 'wind-field'} <= {t['name'] for t in r.json['tensors']}, r.text[:200])
r = client.simulate_get('/api/tensortree')
check('GET /api/tensortree lists the seeded trees (wind-spatial, plate-mechanics)', r.status_code == 200 and {t['name'] for t in r.json['trees']} >= {'wind-spatial', 'plate-mechanics'}, r.text[:200])
r = client.simulate_post('/api/tensortree/discover', json={'selection': 'nope'})
check('discover on an unknown selection is a 404 with the reason', r.status_code == 404)
# CRUDE: make a Tensor through the standard door, read it back through the module API
# the real CRUDE write protocol: multipart form-data, initParamSets = a JSON list of constructor kwargs
boundary = 'probe-boundary'
fields = {'initParamSets': json.dumps([{'name': 'blob', 'rank': 4, 'shape_json': '[128,128,3,6]', 'semantics': 'unknown', 'dimensions_json': '[]'}])}
mp = ''.join(f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n' for k, v in fields.items()) + f'--{boundary}--\r\n'
r = client.simulate_post('/Tensor', body=mp.encode(), headers={'Content-Type': f'multipart/form-data; boundary={boundary}'})
check('POST (CRUDE) creates an UNINTERPRETED tensor', r.status_code in (200, 201), (r.status_code, r.text[:200]))
r = client.simulate_get('/api/tensormath/tensors/blob')
check('GET /api/tensormath/tensors/blob reads it back with unknown semantics', r.status_code == 200 and r.json['tensor']['semantics'] == 'unknown', r.text[:200])
# ---- tt-1: a REAL grid row through CRUDE, then the engine-backed tensor, the tree, select → discover
from simulations.wind_field_grid_sim_state import build_initial_cells
cells = build_initial_cells()
fields = {'initParamSets': json.dumps([{'name': 'probe-wind-field-grid-0', 'simulation_run_ref': 'probe', 'step': 0, 'time': 0.0, 'cells_json': json.dumps(cells)}])}
mp = ''.join(f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n' for k, v in fields.items()) + f'--{boundary}--\r\n'
r = client.simulate_post('/WindFieldGridState', body=mp.encode(), headers={'Content-Type': f'multipart/form-data; boundary={boundary}'})
check('tt-1: a WindFieldGridState row is created through CRUDE (64 cells)', r.status_code in (200, 201), (r.status_code, r.text[:160]))
r = client.simulate_get('/api/tensormath/tensors/wind-field')
check('the seeded wind-field tensor is engine-backed and lists its four named dims + the tree that views it',
      r.status_code == 200 and r.json['tensor']['storage_kind'] == 'engine' and r.json['tensor']['dims'] == ['x', 'y', 'z', 'component'] and 'wind-spatial' in r.json['trees'], r.text[:200])
r = client.simulate_post('/api/tensormath/evaluate', json={'expression': 'wind-speed'})
check('POST evaluate wind-speed reads the LIVE grid and returns |w| on [4,4,4]', r.status_code == 200 and r.json['result']['shape'] == [4, 4, 4], r.text[:200])
r = client.simulate_get('/api/tensortree/trees/wind-spatial/validate')
check('the seeded tree validates with the root RESOLVED (bound to WindFieldGridState-3d)', r.status_code == 200 and r.json['validation']['ok'] and r.json['validation']['nodes']['wind-grid']['status'] == 'resolved', r.text[:300])
r = client.simulate_get('/api/tensortree/trees/wind-spatial/graph')
check('the graph view carries the coupling as a crossing mapping edge', r.status_code == 200 and any(e['kind'] == 'mapping' and e['mapping'] == 'wind-grid→bob-drag' for e in r.json['graph']['edges']))
r = client.simulate_post('/api/tensortree/select', json={'node': 'wind-grid', 'ranges': {'x': [0.4, 1.2], 'y': [-0.5, 0.2], 'z': [0.4, 1.2], 'speed': [6, 12]}, 'created_from': 'probe'})
check('POST select CREATES the selection row and returns its discovery: the real coupling first, the calm-only hypothesis refused',
      r.status_code == 201 and [c['mapping'] for c in r.json['discovery']['candidates']] == ['wind-grid→bob-drag', 'wind-grid→slice-z0']
      and any(x['mapping'] == 'wind-grid→spectrum' for x in r.json['discovery']['refused']), r.text[:300])
check('  …and the selection persisted as a row', any(getattr(s, 'created_from', '') == 'probe' for s in tables.get('TensorSelection', {}).values()))
r = client.simulate_post('/api/tensortree/select', json={'node': 'wind-grid', 'ranges': {'x': [5, 1]}})
check('a malformed range is a 400 naming the dim', r.status_code == 400 and 'x' in r.json['error'])
# ---- lod-1: the teaching path, seeded from the committed report, walkable over HTTP
r = client.simulate_get('/api/computelod/lod1')
check('GET /api/computelod/lod1 serves the committed report (encoding 0x00b50533, cell counts, verdicts)', r.status_code == 200 and r.json['report'].get('compile', {}).get('encoding') == '0x00b50533', r.text[:200])
r = client.simulate_get('/api/computelod/path', params={'rung': 'c-source', 'ref': 'lod1/add.c: c = a + b'})
check('GET path from the C statement walks C → compiler → ISA → microarchitecture → RTL → netlist → (unresolved) standard cells',
      r.status_code == 200 and r.json['path']['rungs'] == ['c-source', 'compiler', 'isa', 'microarchitecture', 'rtl', 'logic-netlist', 'standard-cells'], r.text[:300])
check('  …each step names its evidence status', r.status_code == 200 and all(s.get('end') or s['evidence_level'] for s in r.json['path']['steps']))
check('the lod-1 rows are seeded: 7 ComputeMappings, 5 CharacterizationMappings, 3 CompilerArtifacts',
      len(tables.get('ComputeMapping', {})) == 7 and len(tables.get('CharacterizationMapping', {})) == 5 and len(tables.get('CompilerArtifact', {})) == 3)
# ---- tt-2: the FEM case is a seeded core row; the tensors solve it live; the tree is honest
check('the tt-2 FEM case is seeded as an FEMModelDefinition row', any(getattr(c, 'name', '') == 'tt2-plate-tension' for c in tables.get('FEMModelDefinition', {}).values()))
check('the cited material option opt-electrical-steel is present (magnetics admitted)', any(getattr(o, 'name', '') == 'opt-electrical-steel' for o in tables.get('MagneticMaterialOption', {}).values()))
r = client.simulate_post('/api/tensormath/evaluate', json={'expression': 'tt2-sigma-from-C'})
check('POST evaluate tt2-sigma-from-C SOLVES the plate live and contracts C:ε → σ on [2,2,n]', r.status_code == 200 and r.json['result']['dims'] == ['i', 'j', 'n'] and r.json['result']['shape'][2] > 0, r.text[:300])
r2 = client.simulate_get('/api/tensormath/tensors/tt2-sigma')
check('GET tensors/tt2-sigma names its engine storage and the plate-mechanics tree', r2.status_code == 200 and r2.json['tensor']['storage_ref'] == 'fem:tt2-plate-tension:stress' and 'plate-mechanics' in r2.json['trees'])
r = client.simulate_get('/api/tensormath/operators/stress-from-strain')
check('GET operators/stress-from-strain shows the bridge: the numpy implementation on the microarchitecture rung, evidence none until benchmarked, and the FPGA row beside it',
      r.status_code == 200 and r.json['implementations'][0]['target_rung'] == 'microarchitecture' and r.json['implementations'][0]['evidence_level'] == 'none' and len(r.json['implementations']) == 2, r.text[:300])
r = client.simulate_get('/api/tensortree/trees/plate-mechanics/validate')
check('plate-mechanics validates; its root is unresolved for the stated reason (no binding), its visualization space typed', r.status_code == 200 and r.json['validation']['ok'] and r.json['validation']['nodes']['plate']['why'] == 'no binding_ref'
      and r.json['validation']['unresolved']['plate-visualization']['kind'] == 'visualization', r.text[:300])
# ---- Phase 6: the bridge, live — benchmark numpy HERE, then read both implementations side by side
r = client.simulate_post('/api/tensormath/benchmark', json={'implementation': 'stress-from-strain/numpy', 'repeats': 10})
check('POST benchmark runs the numpy implementation here and writes the MEASURED reading into its row (median, repeats, node, n)',
      r.status_code == 200 and r.json['latency_s'] > 0 and 'median' in r.json['evidence_ref'] and r.json['elements'] > 0, r.text[:300])
r = client.simulate_post('/api/tensormath/benchmark', json={'implementation': 'stress-from-strain/fpga-stress-mac'})
check('  …the FPGA row cannot be benchmarked HERE (422: its flow measures it, or the part does)', r.status_code == 422)
r = client.simulate_get('/api/tensormath/operators/stress-from-strain')
impls = {i['name']: i for i in r.json['implementations']}
check('GET operators/stress-from-strain now shows BOTH: numpy measured on this node, the FPGA kernel simulated on an iCE40 — same operator, two rungs',
      r.status_code == 200 and impls['stress-from-strain/numpy']['evidence_level'] == 'measured' and impls['stress-from-strain/fpga-stress-mac']['evidence_level'] == 'simulated'
      and impls['stress-from-strain/fpga-stress-mac']['target_rung'] == 'rtl' and impls['stress-from-strain/numpy']['latency_s'] > 0, r.text[:400])
# ---- tt-4 / Phase 7: the scale tree of paraffin wax, read live from msci + pspp, then materialised
r = client.simulate_get('/api/tensortree/scale/paraffin-wax')
check('GET scale/paraffin-wax reads the material\'s levels as this instance holds them (L0 present), its gaps, and its two executed pspp transfers as scale mappings',
      r.status_code == 200 and 0 in {n['level'] for n in r.json['nodes']} and len(r.json['mappings']) == 2 and len(r.json['nodes']) + len(r.json['unresolved']) == 5, r.text[:300])
r = client.simulate_post('/api/tensortree/scale/paraffin-wax/materialise')
check('POST materialise persists it as tree rows (201)', r.status_code == 201 and r.json['written']['nodes'] >= 2 and r.json['written']['mappings'] == 2, r.text[:200])
r = client.simulate_get('/api/tensortree/trees/paraffin-wax@scale/validate')
check('  …and the materialised scale tree validates (one root, L0)', r.status_code == 200 and r.json['validation']['ok'], r.text[:200])
r = client.simulate_get('/api/tensortree/scale/unobtainium')
check('an unknown material is a 404 with the reason', r.status_code == 404)
pages = [d for d in tables.get('DisplayDefinition', {}).values() if getattr(d, 'pageRoute', '') in ('tensormath', 'tensortree', 'computelod')]
check('the three configured pages are seeded as DisplayDefinitions', len(pages) == 3, [getattr(d, 'pageRoute', '') for d in pages])
tt = next(d for d in pages if getattr(d, 'pageRoute', '') == 'tensortree')
check('the tensortree page hosts the existing sim-space viewer for the resolved node (no new renderer)', 'sim-space-viewer' in getattr(tt, 'definition', '') and 'newtonian-pendulum-viz' in getattr(tt, 'definition', ''))
n_ok = sum(results); print(f'\n{n_ok}/{len(results)} checks passed'); sys.exit(0 if n_ok == len(results) else 1)
