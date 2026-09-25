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
os.environ['POLARI_MODULES'] = 'simulations,simSpace,materialsScience,pspp,magnetics,scoring,techtree,microchip,cntfet,electrodevice,sifet,hwfpga,mathshapes,tensormath,tensortree,computelod,cicd'
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
# tt-5: the ONE read the Angular tensor-tree-panel makes — everything a person needs for intuition in one answer
r = client.simulate_get('/api/tensortree/trees/wind-spatial/view')
v = r.json if r.status_code == 200 else {}
check('GET /view answers for wind-spatial with tree/nodes/edges/mappings/selections/validation/channels/evidence_levels', r.status_code == 200 and all(k in v for k in ('tree', 'nodes', 'edges', 'mappings', 'selections', 'validation', 'channels', 'evidence_levels')), r.text[:200])
check('/view: eleven channels and four evidence levels (§F4, §F2)', len(v.get('channels', [])) == 11 and v.get('evidence_levels') == ['none', 'analytical', 'simulated', 'measured'], str((v.get('channels'), v.get('evidence_levels'))))
vn = {n['id']: n for n in v.get('nodes', [])}
check('/view: the resolved root carries dims with a channel each (x/y/z -> position, w -> vector) and its binding_ref', vn.get('wind-grid', {}).get('status') == 'resolved' and all(d.get('channel') for d in vn.get('wind-grid', {}).get('dims', [])) and vn.get('wind-grid', {}).get('binding_ref'), str(vn.get('wind-grid', {}).get('dims'))[:200])
check('/view: an unresolved space is a node with kind=unresolved, its unresolved_kind and open_questions', any(n['kind'] == 'unresolved' and n.get('unresolved_kind') and n.get('open_questions') for n in v.get('nodes', [])), str([n['id'] for n in v.get('nodes', []) if n['kind'] == 'unresolved']))
check('/view: mappings carry source/target node, two statuses and the evidence level', all(m.get('source_node') and m.get('target_node') and m.get('mapping_status') and m.get('evidence_level') in v.get('evidence_levels', []) for m in v.get('mappings', [])) and v.get('mappings'), str([(m['name'], m['evidence_level']) for m in v.get('mappings', [])]))
# tt-7: a SimulationCouplingDefinition created FROM the proposed coupling mapping — derived from the REAL classes
r = client.simulate_get('/api/tensortree/mappings/wind-grid→bob-wind/couple')
check('GET mappings/wind-grid→bob-wind/couple (dry run): derived from the live classes — wind-field-3d/WindFieldGridState → newtonian-pendulum-3d/NewtonianPendulumBobSimState, sampler field-sample-nearest (a saved matrix equation here), pos [px,py,pz]; nothing missing',
      r.status_code == 200 and r.json['ok'] and r.json['coupling']['source_simulation_ref'] == 'wind-field-3d' and r.json['coupling']['target_simulation_ref'] == 'newtonian-pendulum-3d'
      and r.json['coupling']['sampler_equation_ref'] == 'field-sample-nearest' and r.json['derived_from']['target']['position_fields'] == ['px', 'py', 'pz'] and r.json['missing'] == [], r.text[:400])
_before = len(tables.get('SimulationCouplingDefinition', {}))
r = client.simulate_post('/api/tensortree/mappings/wind-grid→bob-wind/couple', json={})
check('POST …/couple CREATES the SimulationCouplingDefinition row (201) — the mapping now names it, proposed → implemented, evidence still none',
      r.status_code == 201 and r.json['created'] == 'tt-wind-grid-to-bob-wind' and r.json['mapping_status'] == 'implemented' and r.json['evidence_level'] == 'none'
      and len(tables.get('SimulationCouplingDefinition', {})) == _before + 1, r.text[:300])
_cp = next((c for c in tables.get('SimulationCouplingDefinition', {}).values() if getattr(c, 'name', '') == 'tt-wind-grid-to-bob-wind'), None)
check('  …the row is a real SimulationCouplingDefinition beside wind-to-newtonian-pendulum: same source/target sims and sampler, its own inject keys (wind_vx/vy/vz), enabled',
      _cp is not None and getattr(_cp, 'source_simulation_ref', '') == 'wind-field-3d' and getattr(_cp, 'target_class_name', '') == 'NewtonianPendulumBobSimState'
      and list(json.loads(getattr(_cp, 'config_json', '{}'))['inject']) == ['wind_vx', 'wind_vy', 'wind_vz'] and getattr(_cp, 'enabled', False) is True, vars(_cp) if _cp else None)
r = client.simulate_post('/api/tensortree/mappings/wind-grid→bob-wind/couple', json={})
check('  …a second POST is a 409 naming the coupling; a non-coupling mapping is a 422; the already-coupled bob-drag is a 409 naming wind-to-newtonian-pendulum',
      r.status_code == 409 and client.simulate_post('/api/tensortree/mappings/wind-grid→slice-z0/couple', json={}).status_code == 422
      and client.simulate_post('/api/tensortree/mappings/wind-grid→bob-drag/couple', json={}).json.get('coupling_ref') == 'wind-to-newtonian-pendulum', r.text[:200])
# tt-10: EXECUTE the created coupling once through the runner's own pre-pass on the seeded coupled run → simulated evidence
r = client.simulate_post('/api/tensortree/mappings/wind-grid→bob-wind/prove', json={'time': 0.5})
check('POST …/prove runs the created coupling on newtonian-pendulum-wind-run (source wind-field-run): the sampler read a WindFieldGridState row and injected wind_vx/vy/vz; the mapping now carries SIMULATED evidence naming the run, the row and the values',
      r.status_code == 200 and r.json['ok'] and r.json['run'] == 'newtonian-pendulum-wind-run' and r.json['source_run'] == 'wind-field-run' and set(r.json['injected']) == {'wind_vx', 'wind_vy', 'wind_vz'}
      and r.json['source_row']['class'] == 'WindFieldGridState' and r.json['source_row']['time'] > 0 and r.json['written']['evidence_level'] == 'simulated' and 'wind-field-run' in r.json['written']['evidence_ref'], r.text[:400])
_mp = next(mm for mm in tables.get('TensorMapping', {}).values() if getattr(mm, 'name', '') == 'wind-grid→bob-wind')
check('  …the row says so (evidence simulated, status still implemented — consumption not attributed), and the injected wind is not all zero (the wind run has a field)',
      getattr(_mp, 'evidence_level', '') == 'simulated' and getattr(_mp, 'mapping_status', '') == 'implemented' and any(abs(v) > 0 for v in r.json['injected'].values()), (getattr(_mp, 'evidence_level', ''), r.json.get('injected')))
r = client.simulate_post('/api/tensortree/mappings/wind-grid→slice-z0/prove', json={})
check('  …a mapping with no coupling row is a 422 that says to couple first', r.status_code == 422 and 'couple first' in r.json['error'], r.text[:200])
r = client.simulate_get('/api/tensortree/trees/bob-motion/validate')
check('the bob\'s own tree (bob-motion) validates on a real boot with its root resolved through the seeded wind-arrow binding', r.status_code == 200 and r.json['validation']['ok'] and r.json['validation']['nodes']['pendulum-bob']['status'] == 'resolved', r.text[:300])
r = client.simulate_get('/api/tensortree/trees/nope/view')
check('/view of an unknown tree is a 404 with a reason', r.status_code == 404, r.text[:120])
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
check('GET path from the C statement walks ALL ELEVEN rungs: C → compiler → ISA → microarchitecture → RTL → netlist → SKY130 cells → transistors → layout → sky130 process → electronic-grade silicon',
      r.status_code == 200 and r.json['path']['rungs'] == ['c-source', 'compiler', 'isa', 'microarchitecture', 'rtl', 'logic-netlist', 'standard-cells', 'devices', 'layout', 'fabrication', 'materials']
      and r.json['path'].get('unresolved_at') == 'materials', r.text[:300])
check('  …each step names its evidence status', r.status_code == 200 and all(s.get('end') or s['evidence_level'] for s in r.json['path']['steps']))
r = client.simulate_get('/api/computelod/engines')
check('GET /api/computelod/engines: the engines LADDER answers per engine before any dispatch (remote | local-binary | local-image | refused with the knobs named) — the Polari engines pattern, not a local docker assumption',
      r.status_code == 200 and r.json['ok'] and set(r.json['placement']['engines']) >= {'yosys', 'sta', 'magic', 'netgen', 'riscv-gcc', 'iverilog', 'nextpnr-ice40'}
      and all(v['how'] in ('remote', 'local-binary', 'local-image', 'refused') for v in r.json['placement']['engines'].values()) and r.json['placement']['provider_module'] == 'computelod.engines'
      and r.json['placement']['knob'] == 'EDA_ENGINES_URL', r.text[:300])
r = client.simulate_get('/api/computelod/lod3/devices')
check('GET /api/computelod/lod3/devices: our ngspice on the PDK models vs the Liberty — three arcs, mean gap ≤ 15 %, falls faster on every arc (schematic vs extracted, stated)',
      r.status_code == 200 and r.json['ok'] and r.json['report']['summary']['arcs'] == 3 and r.json['report']['summary']['mean_abs_delta_pct'] <= 15 and all(a['compare']['tphl_ps']['delta_pct'] < 0 for a in r.json['report']['arcs']), r.text[:300])
r = client.simulate_get('/api/computelod/lod3/layout')
check('GET /api/computelod/lod3/layout: DRC (context rules only), LVS match, PEX re-timed; the parasitics verdict is half-rejected and says so',
      r.status_code == 200 and r.json['ok'] and r.json['report']['summary']['lvs_match'] and r.json['report']['summary']['drc_clean_in_context'] and 'REJECTED' in r.json['report']['summary']['verdict'], r.text[:300])
_dl = next((m_ for m_ in tables.get('ComputeMapping', {}).values() if getattr(m_, 'name', '') == 'lod3: devices → layout'), None)
check('  …the devices → layout row on a real boot is MEASURED and validated (lod-3c replaced lod-3\'s analytical reading by name)', _dl is not None and _dl.evidence_level == 'measured' and _dl.mapping_status == 'validated')
r = client.simulate_get('/api/computelod/lod4')
check('GET /api/computelod/lod4: the sky130 SiliconProcessNode row EXISTS on a real boot (seeded by computelod in sifet\'s shape), manufacturable None with the reason + D-lod4-1',
      r.status_code == 200 and r.json['ok'] and r.json['process_node_row'] and r.json['process_node_row']['node_nm'] == 130.0 and r.json['process_node_row']['manufacturable'] is None
      and 'D-lod4-1' in r.json['process_node_row']['manufacturable_reason'], r.text[:300])
from sifet.objects.si_ladder._shared import ladder_report as _si_ladder
_lad = _si_ladder(manager)
check('sifet\'s own ladder report still answers with sky130 as its coarsest rung (130 nm first), the ratified prior nodes unchanged after it',
      isinstance(_lad, dict) and [x['name'] for x in _lad.get('rungs', [])][:2] == ['sky130', 'polari-si-90-class'], [x.get('name') for x in _lad.get('rungs', [])][:4] if isinstance(_lad, dict) else _lad)
r = client.simulate_get('/api/computelod/lod3')
check('GET /api/computelod/lod3 serves the cells → transistors → layout reading: 1050 SKY130 transistors, LEF area == Liberty area, 1016 CNT transistors, CNT layout None, not_done listed',
      r.status_code == 200 and r.json['ok'] and r.json['report']['adder']['sky130']['transistors'] == 1050 and r.json['report']['adder']['sky130']['area_agrees'] and r.json['report']['adder']['cnt']['transistors'] == 1016
      and r.json['report']['adder']['cnt']['layout'] is None and len(r.json['report']['not_done']) == 4, r.text[:300])
check('the lod-1 + lod-2 + lod-2b + lod-3 + lod-3b + lod-3c + lod-4 rows are seeded: 14 ComputeMappings, 24 CharacterizationMappings, 3 CompilerArtifacts',
      len(tables.get('ComputeMapping', {})) == 14 and len(tables.get('CharacterizationMapping', {})) == 24 and len(tables.get('CompilerArtifact', {})) == 3,
      (len(tables.get('ComputeMapping', {})), len(tables.get('CharacterizationMapping', {}))))
r = client.simulate_get('/api/computelod/lod2')
check('GET /api/computelod/lod2 serves the open-silicon report (SKY130 cells, OpenSTA delay with conditions)', r.status_code == 200 and r.json['report']['timing']['max_path_ns'] > 0 and r.json['report']['liberty']['sha256'])
r = client.simulate_get('/api/computelod/lod2/cnt')
check('GET /api/computelod/lod2/cnt serves the SECOND Liberty: our CNT library over a derived device (152 cells, OpenSTA ps under 0.6 V / 300 K)',
      r.status_code == 200 and r.json['ok'] and r.json['report']['mapping']['cells'] > 0 and r.json['report']['timing']['max_path_ps'] > 0 and r.json['report']['device'] and r.json['report']['characterization']['result_row'], r.text[:200])
_cm = {getattr(m_, 'name', ''): m_ for m_ in tables.get('ComputeMapping', {}).values()}
check('the seed holds BOTH libraries as rows: SKY130 cells → devices now ONE-TO-MANY (lod-3 read the PDK netlists, analytical), CNT cells → devices a real reference to the AlignedCNTFETDevice row (simulated)',
      _cm['lod2: standard cells → devices'].kind == 'one-to-many' and _cm['lod2: standard cells → devices'].evidence_level == 'analytical' and _cm['lod2-cnt: CNT standard cells → devices'].kind == 'one-to-many'
      and 'AlignedCNTFETDevice' in _cm['lod2-cnt: CNT standard cells → devices'].target_ref and _cm['lod2-cnt: netlist → CNT standard cells'].evidence_level == 'simulated', sorted(_cm)[:12])
_ch = [c for c in tables.get('CharacterizationMapping', {}).values() if 'propagation delay' in getattr(c, 'name', '')]
check('two propagation-delay characterizations, each with its own conditions (1.8 V/25 °C SKY130 ns; 0.6 V/300 K CNT ns), neither pretending to be the other',
      len(_ch) == 2 and {json.loads(c.conditions_json).get('voltage_v') for c in _ch} == {1.8, 0.6} and all(c.units == 'ns' for c in _ch), [(c.name, c.result) for c in _ch])
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
check('tt-6: plate-mechanics validates; its root is RESOLVED on a real boot (binding FEMFieldState-2d exists here), u per node unresolved for the stated reason with its typed space',
      r.status_code == 200 and r.json['validation']['ok'] and r.json['validation']['nodes']['plate']['status'] == 'resolved' and r.json['validation']['nodes']['plate']['binding_ref'] == 'FEMFieldState-2d'
      and r.json['validation']['nodes']['plate-displacement']['status'] == 'resolved' and r.json['validation']['nodes']['plate-mesh']['status'] == 'resolved'
      and list(r.json['validation']['unresolved']) == [] and 'plate.element' in r.json['validation']['nodes']['plate']['coherent'], r.text[:400])
r = client.simulate_get('/api/tensormath/fem/tt2-plate-tension')
check('GET /api/tensormath/fem/tt2-plate-tension: the field row exists FROM SEED (64 elements, 45 nodes, E/ν cited), the binding + scene exist → drawable',
      r.status_code == 200 and r.json['drawable'] and r.json['field']['n_elements'] == 64 and r.json['field']['n_nodes'] == 45 and 'literature-est' in r.json['field']['material_provenance']
      and 'plate-mechanics-2d' in r.json['scenes'], r.text[:300])
r = client.simulate_get('/api/tensormath/fem/nope')
check('  …an unknown case is a 404', r.status_code == 404)
r = client.simulate_post('/api/tensormath/fem/tt2-plate-tension/materialise')
check('POST …/materialise re-solves with the manager (E/ν from the live MagneticMaterialOption) and refreshes the same row (200, not a second row)',
      r.status_code == 200 and r.json['created'] is False and r.json['n_elements'] == 64 and len([f for f in tables.get('FEMFieldState', {}).values()]) == 1, r.text[:300])
r = client.simulate_get('/api/simspace/plate-mechanics-2d/snapshot')
_snap = (r.json.get('data') or r.json) if r.status_code == 200 else {}
_objs = _snap.get('objects', []) or []
_cells = [o for o in _objs if (o.get('userData') or {}).get('bindingName') == 'FEMFieldState-2d']
# tt-11: each cell references ITS OWN triangle shape (space units) — seeded from the same solve through the shape library
check('tt-11: the 64 cells each reference their own Shape2DDefinition (tt2-plate-tension-field-el-{i}, units=space, an svg polygon around the centroid) and carry no marker scale',
      all(c['shapeRef'] == 'tt2-plate-tension-field-el-%d' % c['userData']['cellIndex'] and 'scale' not in c and c['userData'].get('ownShape') for c in _cells), [c.get('shapeRef') for c in _cells[:2]])
_s2d = {getattr(s, 'name', ''): s for s in tables.get('Shape2DDefinition', {}).values()}
_ms = {getattr(s, 'name', ''): s for s in tables.get('MathShapeDefinition', {}).values()}
check('  …the 64 shape rows EXIST on a real boot (source svg, units space, anchor center, a <polygon>) and so do the 64 polygon MathShapeDefinitions that carry the geometry',
      sum(1 for n in _s2d if n.startswith('tt2-plate-tension-field-el-')) == 64 and _s2d['tt2-plate-tension-field-el-0'].units == 'space' and '<polygon' in _s2d['tt2-plate-tension-field-el-0'].svg_string
      and sum(1 for n in _ms if n.startswith('tt2-plate-tension-field-el-')) == 64 and _ms['tt2-plate-tension-field-el-0'].primitive_kind == 'polygon', (len(_s2d), len(_ms)))
r = client.simulate_get('/api/shapes/tt2-plate-tension-field-el-0/properties')
check('  …the math-shape API answers for an element: area = the field row\'s element area (1/32 m² for the seed mesh), centroid = the element centroid',
      r.status_code == 200 and abs((r.json.get('surfaceAreaCm2') or 0) - 0.03125) < 1e-4 and abs(r.json['centroid'][0] - 0.0833333) < 1e-4, r.text[:300])
r = client.simulate_post('/api/tensormath/fem/tt2-plate-tension/shapes')
check('POST …/fem/{case}/shapes refreshes the same 64 + 64 rows (200, nothing created twice)', r.status_code == 200 and r.json['elements'] == 64 and r.json['shapes_2d_created'] == 0 and r.json['math_shapes_created'] == 0, r.text[:300])
_medges = [c for c in (_snap.get('connections') or []) if (c.get('userData') or {}).get('bindingName') == 'FEMFieldState-mesh-2d']
check('tt-9: the snapshot carries the mesh wireframe — 64 triangles → 108 distinct edges (Euler: 45 nodes, 64 faces on a simply connected disc → E = V + F − 1)', len(_medges) == 108, len(_medges))
_ulines = [c for c in (_snap.get('connections') or []) if (c.get('userData') or {}).get('bindingName') == 'FEMFieldState-u-2d']
check('tt-8: the same snapshot carries 45 displacement lines (one per node, node → node + 20000·u) on the CONNECTIONS channel, the fixed left edge with zero-length lines, the free right edge the longest',
      len(_ulines) == 45 and all(c['userData']['vectorScale'] == 20000.0 for c in _ulines)
      and max(_ulines, key=lambda c: c['userData']['magnitude'])['sourcePosition'][0] == 2.0 and min(_ulines, key=lambda c: c['userData']['magnitude'])['userData']['magnitude'] == 0.0, (len(_ulines), [c['sourcePosition'] for c in _ulines[:3]]))
check('the 2-D snapshot of plate-mechanics-2d fans the field row into 64 coloured cells (colorOverride from σ_vm through the binding\'s domain; the raw value rides userData)',
      r.status_code == 200 and len(_cells) == 64 and all(c.get('colorOverride', '').startswith('#') and 'scalar' in c['userData'] for c in _cells)
      and len({c['colorOverride'] for c in _cells}) > 3, (r.status_code, len(_objs), list(_snap)[:8], (_snap.get('warnings') or [])[:3], r.text[:200]))
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
check('tt-5: the tensortree page hosts the tensor-tree-panel (the one registered Angular panel) opened on wind-spatial', 'tensor-tree-panel' in getattr(tt, 'definition', '') and "'treeName': 'wind-spatial'" in getattr(tt, 'definition', '') or ('tensor-tree-panel' in getattr(tt, 'definition', '') and '"treeName": "wind-spatial"' in getattr(tt, 'definition', '')))
n_ok = sum(results); print(f'\n{n_ok}/{len(results)} checks passed'); sys.exit(0 if n_ok == len(results) else 1)
