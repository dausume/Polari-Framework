"""In-process live-boot PROBE of gr-1: boot the REAL polariServer
with the gears module enabled, then hit /api/gears/* — proving the
guarded import, defClassList wiring, seed_pairs ordering and route
registration work outside the selftest fixtures (seeding is DB-gated
by design, so this boots with hasDB=True).

Run from a THROWAWAY working directory (the boot writes a sqlite DB
into cwd):  cd /tmp/somewhere && \
  PYTHONPATH=<framework>:<framework>/modules python3 \
  <framework>/tests/gears_liveboot_probe.py
"""

import os
import sys

os.environ['POLARI_MODULES'] = (
    # gears' registry `requires` names mathshapes, which pulls its
    # own chain — enable the lot so the probe exercises the real
    # dependency path rather than a convenient subset.
    'scoring,plant_morphology,aquaponics,mathshapes,gears')
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


types_tbl = manager.objectTables.get('GearTypeDefinition', {})
gears_tbl = manager.objectTables.get('GearDefinition', {})
runs_tbl = manager.objectTables.get('GearVerificationRun', {})
check('8 GearTypeDefinition rows seeded through the real seed path',
      len(types_tbl) == 8, extra=str(len(types_tbl)))
check('8 GearDefinition bodies seeded (2 trains)',
      len(gears_tbl) == 8, extra=str(len(gears_tbl)))
check('ZERO GearVerificationRun rows — observed state is never '
      'seeded (the motors rule)', len(runs_tbl) == 0,
      extra=str(len(runs_tbl)))

r = client.simulate_get('/api/gears/types')
check('GET /api/gears/types 200 with both prior-band ends and the '
      'geometry gate visible',
      r.status_code == 200 and r.json['count'] == 8
      and all(t['efficiencyPrior'][0] is not None
              for t in r.json['types'])
      and any(t['geometryGenerator'] is None
              for t in r.json['types']),
      extra=r.status)

r = client.simulate_get('/api/gears/trains')
check('GET /api/gears/trains 200: both seeded trains, the clock '
      'one naming its motor design',
      r.status_code == 200 and r.json['count'] == 2
      and any(t['motorDesignRef'] == 'clock-lavet-m0'
              for t in r.json['trains']),
      extra=r.status)

r = client.simulate_get('/api/gears/solve/two-stage-spur-demo')
body = r.json
check('LIVE solve: 12:1, output 50 rpm POSITIVE (two reversals '
      'cancel), torque 0.114075 Nm, power conserved',
      r.status_code == 200 and body.get('ok')
      and abs(body['totalRatio'] - 12.0) < 1e-9
      and abs(body['outputSpeedRpm'] - 50.0) < 1e-9
      and abs(body['outputTorqueNm'] - 0.114075) < 1e-9
      and body['power']['conserved'] is True,
      extra=str(body.get('refusal') or body.get('totalRatio')))

r = client.simulate_get('/api/gears/solve/clock-train-m0')
body = r.json
check('LIVE clock train: the minute shaft turns ONCE PER HOUR '
      '(1/60 rpm) — the gr-5 acceptance arithmetic, on the real '
      'app',
      r.status_code == 200 and body.get('ok')
      and abs(abs(body['outputSpeedRpm']) - (1.0 / 60.0)) < 1e-12,
      extra=str(body.get('outputSpeedRpm')))
check('clock efficiencies are honestly flagged PRIORS on the live '
      'app (no measured runs exist yet)',
      all(m['efficiencyIsPrior'] for m in body['meshes']))

r = client.simulate_get(
    '/api/gears/solve/two-stage-spur-demo?torqueNm=0.02&'
    'speedRpm=1200')
check('query overrides drive the solve (the door gr-5 pushes a '
      'motor torque curve through)',
      r.status_code == 200
      and abs(r.json['outputSpeedRpm'] - 100.0) < 1e-9,
      extra=str(r.json.get('outputSpeedRpm')))

r = client.simulate_get('/api/gears/solve/no-such-train')
check('unknown train = 400 + refusal sentence',
      r.status_code == 400 and r.json.get('refusal'),
      extra=r.status)

failed = results.count(False)
print(f'\n{len(results) - failed}/{len(results)} live-boot checks '
      'passed')
sys.exit(1 if failed else 0)
