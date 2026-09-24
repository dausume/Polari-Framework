"""In-process live-boot PROBE of tt-0: boot the REAL polariServer with tensormath + tensortree + computelod (+
techtree, microchip, matrices are core) enabled, then hit their routes — proving the guarded imports, defClassList
wiring, seed pairs (eleven rungs, 70 kinds, the compute-lod tree, the default discovery policy) and route
registration work outside the selftest fixtures. Also proves the dep-0/1 cicd rows now type (they were missing
from defClassList).
Run from a THROWAWAY working directory (the boot writes a sqlite DB into cwd):
  cd /tmp/somewhere && PYTHONPATH=<framework>:<framework>/modules python3 <framework>/tests/tensor_liveboot_probe.py
"""
import json
import os
import sys
os.environ['POLARI_MODULES'] = 'scoring,techtree,microchip,cntfet,electrodevice,sifet,hwfpga,tensormath,tensortree,computelod,cicd'
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
check('GET /api/tensormath answers (no tensors yet)', r.status_code == 200 and r.json['tensors'] == [])
r = client.simulate_get('/api/tensortree')
check('GET /api/tensortree answers (no trees yet)', r.status_code == 200 and r.json['count'] == 0)
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
pages = [d for d in tables.get('DisplayDefinition', {}).values() if getattr(d, 'pageRoute', '') in ('tensormath', 'tensortree', 'computelod')]
check('the three configured pages are seeded as DisplayDefinitions', len(pages) == 3, [getattr(d, 'pageRoute', '') for d in pages])
n_ok = sum(results); print(f'\n{n_ok}/{len(results)} checks passed'); sys.exit(0 if n_ok == len(results) else 1)
