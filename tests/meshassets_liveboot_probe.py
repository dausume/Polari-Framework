"""In-process live-boot PROBE of mesh-1: boot the REAL polariServer
with meshassets (+ plant_morphology, which owns the vector organ
definitions it fits against) and hit /api/meshassets/*.

Run from a THROWAWAY working directory:
  cd /tmp/somewhere && PYTHONPATH=<fw>:<fw>/modules python3 \
    <fw>/tests/meshassets_liveboot_probe.py
"""

import os
import sys

os.environ['POLARI_MODULES'] = 'plant_morphology,meshassets'
os.environ.setdefault('POLARI_DB_BACKEND', 'sqlite')

FRAMEWORK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, FRAMEWORK)
sys.path.insert(0, os.path.join(FRAMEWORK, 'modules'))

from falcon import testing  # noqa: E402

from objectTreeManagerDecorators import managerObject  # noqa: E402

manager = managerObject(hasServer=True, hasDB=True)
client = testing.TestClient(manager.polServer.falconServer)

results = []


def check(label, cond, extra=''):
    results.append(bool(cond))
    print(('PASS' if cond else 'FAIL') + f': {label}'
          + (f'  [{extra}]' if extra and not cond else ''))


check('7 MeshAssetSource + 5 MeshAssetReference rows seeded; ZERO '
      'OrganMeshChoice (choosing an approximation is a human act)',
      len(manager.objectTables.get('MeshAssetSource', {})) == 7
      and len(manager.objectTables.get('MeshAssetReference', {})) == 5
      and len(manager.objectTables.get('OrganMeshChoice', {})) == 0)

r = client.simulate_get('/api/meshassets/sources')
body = r.json
check('GET /api/meshassets/sources 200: every source carries a '
      'QUOTED licence statement and how it was verified',
      r.status_code == 200 and body['count'] == 7
      and all(s['license']['statement']
              and s['license']['verificationMethod'] != 'not-checked'
              for s in body['sources']),
      extra=r.status)
gates = {s['name']: s['license'] for s in body['sources']}
check('CC0 sources clear simulate AND redistribute on the live app',
      gates['polyhaven']['mayRedistribute']
      and gates['quaternius']['mayRedistribute'])
check('PlantMap3D is present and clears NOTHING — the negative '
      'finding survives a real boot',
      gates['plantmap3d']['grade'] == 'unverified'
      and not gates['plantmap3d']['maySimulate'])
check('copyleft gear libs are reference-only; public-domain '
      'pd-gears is unrestricted',
      gates['mcad-involute-gears']['grade'] == 'reference-only'
      and gates['pd-gears']['grade'] == 'unrestricted')

r = client.simulate_get(
    '/api/meshassets/fit/sweet-basil-leaf-organ/'
    'quat-plant-broadleaf')
body = r.json
check('LIVE fit: basil leaf vs broadleaf mesh = fidelity 0.6667, '
      'usable-with-distortion (hand-computed)',
      r.status_code == 200 and body.get('ok')
      and abs(body['shapeFidelity'] - 0.6667) < 1e-3
      and body['verdict'] == 'usable-with-distortion',
      extra=str(body.get('refusal') or body.get('shapeFidelity')))

r = client.simulate_get(
    '/api/meshassets/candidates/sweet-basil-leaf-organ')
body = r.json
check('LIVE pick-and-choose: candidates ranked subject-first, and '
      'rejects carry their reasons',
      r.status_code == 200 and body.get('ok')
      and body['candidates'][0]['subjectMatches'] is True
      and all(r_['reason'] for r_ in body['rejected']),
      extra=r.status)

r = client.simulate_get(
    '/api/meshassets/fit/sweet-basil-leaf-organ/'
    'oga-plants-unmeasured')
check('an UNMEASURED asset refuses live rather than inventing a '
      'size',
      r.status_code == 400
      and 'no measured bounding box' in r.json.get('refusal', ''),
      extra=r.status)

failed = results.count(False)
print(f'\n{len(results) - failed}/{len(results)} live-boot checks '
      'passed')
sys.exit(1 if failed else 0)
