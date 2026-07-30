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
check('compatibility is judged against OUR GPL-3.0 licence on the '
      'live app', body['projectLicense'] == 'GPL-3.0-or-later')
check('CC0 sources are compatible with no obligations',
      gates['polyhaven']['compatible']
      and not gates['polyhaven']['attributionRequired'])
check('copyleft IS compatible for a GPLv3 project: CC-BY-SA-4.0 '
      'one-way into GPLv3, LGPL-2.1 via its section 3',
      gates['polygear']['compatible']
      and gates['polygear']['shareAlike']
      and gates['mcad-involute-gears']['compatible'])
check('PlantMap3D is present and still INCOMPATIBLE — no licence '
      'means no rights, and ours cannot invent them',
      not gates['plantmap3d']['compatible'])

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

r = client.simulate_get('/api/meshassets/citations')
body = r.json
check('LIVE citation manifest: every asset credited (TASL + terms '
      'link), naming our licence — the list a release ships',
      r.status_code == 200 and body.get('ok')
      and body['count'] == 5
      and body['projectLicense'] == 'GPL-3.0-or-later'
      and all(c['citationLine'] for c in body['citations']),
      extra=r.status)

r = client.simulate_get(
    '/api/meshassets/citation/quat-plant-broadleaf')
check('LIVE single citation is complete and paste-ready',
      r.status_code == 200 and r.json['complete'] is True
      and 'Quaternius' in r.json['citationLine'],
      extra=str(r.json.get('citationLine'))[:70])

failed = results.count(False)
print(f'\n{len(results) - failed}/{len(results)} live-boot checks '
      'passed')
sys.exit(1 if failed else 0)
