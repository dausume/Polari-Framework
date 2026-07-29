"""In-process live-boot PROBE of magnetics Section A: boot the real
polariServer with supplychain+magnetics (+materialsScience) enabled,
then hit the /api/magnetics routes — proving the guarded import,
defClassList wiring, seed_pairs seeding, and route registration work
outside selftest fixtures.

Run from a THROWAWAY working directory (the boot writes a sqlite DB
into cwd):  cd /tmp/somewhere && \
  PYTHONPATH=<framework>:<framework>/modules python3 \
  <framework>/tests/magnetics_liveboot_probe.py
"""

import os
import sys

os.environ['POLARI_MODULES'] = (
    'materialsScience,supplychain,magnetics')
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


roles = manager.objectTables.get('MaterialUseRole', {})
options = manager.objectTables.get('MagneticMaterialOption', {})
powders = manager.objectTables.get('MagneticPowderDefinition', {})
check('10 MaterialUseRole rows seeded by polariServer',
      len(roles) == 10, extra=str(len(roles)))
check('31 MagneticMaterialOption rows seeded',
      len(options) == 31, extra=str(len(options)))
check('7 MagneticPowderDefinition rows seeded',
      len(powders) == 7, extra=str(len(powders)))

r = client.simulate_get('/api/magnetics/catalog')
check('GET /api/magnetics/catalog 200 + 31 options with gates',
      r.status_code == 200 and r.json.get('count') == 31
      and all('costing' in o for o in r.json['options']),
      extra=r.status)
r = client.simulate_get('/api/magnetics/roles')
check('GET /api/magnetics/roles 200 + Earnshaw note present',
      r.status_code == 200
      and any('EARNSHAW' in x.get('honestyNote', '')
              for x in r.json['roles']))
r = client.simulate_get('/api/magnetics/search',
                        params={'role': 'magnetic-conductor',
                                'form': 'mortar'})
check('search mortar+magnetic-conductor 200, sol-gel-ferrite viable',
      r.status_code == 200
      and any(row['option'] == 'opt-solgel-ferrite'
              and row['verdict'] == 'viable'
              for row in r.json['rows']))
r = client.simulate_get('/api/magnetics/viability/opt-srfe12o19')
check('viability/opt-srfe12o19 200 + torque-magnet viable',
      r.status_code == 200
      and any(v['role'] == 'torque-magnet'
              and v['verdict'] == 'viable'
              for v in r.json['roles']))
r = client.simulate_get('/api/magnetics/predict',
                        params={'powder': 'magnetite-powder-def',
                                'matrix': 'geopolymer',
                                'volPct': '35'})
check('predict magnetite/geopolymer@35 200: mu + cost-if-real',
      r.status_code == 200 and r.json.get('ok')
      and r.json['costing']['allowed']
      and 5.5 < r.json['costing']['usdPerKg'] < 6.5,
      extra=str(r.json.get('costing')))
r = client.simulate_get('/api/magnetics/predict',
                        params={'powder': 'fe16n2-theoretical',
                                'matrix': 'geopolymer',
                                'volPct': '35'})
check('predict theoretical powder: watermark + costing refusal',
      r.status_code == 200 and 'THEORETICAL' in r.json['watermark']
      and not r.json['costing']['allowed'])
r = client.simulate_get('/api/magnetics/ladder',
                        params={'role': 'torque-magnet'})
check('ladder torque-magnet 200: recipe-seeded rung = SrFe12O19',
      r.status_code == 200
      and any(x['level'] == 'recipe-seeded'
              and x['option'] == 'opt-srfe12o19'
              for x in r.json['ladder']))
r = client.simulate_get('/api/magnetics/powders')
check('powders route 200: 7 rows, theoretical flagged',
      r.status_code == 200 and r.json['count'] == 7
      and sum(1 for p in r.json['powders']
              if p['isTheoretical']) == 2)
# the mag-1 layer through the live app
r = client.simulate_get(
    '/api/supplychain/sourcing/cascaded-cost/'
    'magnetic-geopolymer-35vol-v0')
check('mag-1 cascade route answers (~6.09/kg) on the live app',
      r.status_code == 200 and r.json.get('ok')
      and abs(r.json['usdPerKg'] - 6.0898) < 0.05,
      extra=str(r.json.get('usdPerKg')))

# mag-3: circuits seeded + solved through the live app
circuits = manager.objectTables.get('MagneticCircuitDefinition', {})
elements = manager.objectTables.get('MagneticElementDefinition', {})
check('3 MagneticCircuitDefinition + 11 element rows seeded',
      len(circuits) == 3 and len(elements) == 11,
      extra=f'{len(circuits)}/{len(elements)}')
r = client.simulate_get('/api/magnetics/circuits')
check('GET /api/magnetics/circuits 200 with element lists',
      r.status_code == 200 and r.json['count'] == 3
      and all(c['elements'] for c in r.json['circuits']))
r = client.simulate_get('/api/magnetics/solve/gapped-toroid-demo')
ops = [a for a in r.json.get('analyses', [])
       if a.get('type') == 'op']
check('solve route answers: op + sweep, flux ~1.35e-7 Wb, '
      'validity sentence riding',
      r.status_code == 200 and r.json.get('ok') and ops
      and abs(next(e for e in ops[0]['result']['elements']
                   if e['element'] == 'core1')['fluxWb']
              - 1.3501e-7) < 1e-10
      and 'linear magnetostatics'
      in ops[0]['result']['validity'])
r = client.simulate_get('/api/magnetics/solve/nope')
check('solve of unknown circuit = 404 refusal',
      r.status_code == 404 and not r.json.get('ok'))

failed = results.count(False)
print(f'\n{len(results) - failed}/{len(results)} live-boot checks '
      'passed')
sys.exit(1 if failed else 0)
