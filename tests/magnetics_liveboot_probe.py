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
    'materialsScience,supplychain,magnetics,motors,'
    # mag-7 remainder: the mathshapes chain (its requires) so the
    # motor scene snapshot + the coil-ring tube surface are probed
    # through the same route the page uses.
    'scoring,plant_morphology,aquaponics,mathshapes')
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

# mag-4: slot-matrix seeded, generated network solves, bill prices
layouts = manager.objectTables.get('BlockLayoutDefinition', {})
placements = manager.objectTables.get('BlockPlacement', {})
mortars = manager.objectTables.get('JointMortarAssignment', {})
check('mag-4 seeds landed (1 layout, 5 placements, 5 joints, 4 '
      'variants)',
      len(layouts) == 1 and len(placements) == 5
      and len(mortars) == 5
      and len(manager.objectTables.get('BlockSizeVariant', {}))
      == 4)
r = client.simulate_get(
    '/api/magnetics/layout/ring-core-demo/network')
check('layout network route: generated + solved, dead-end seat '
      'branch ~zero flux',
      r.status_code == 200 and r.json.get('ok')
      and abs(next(e for e in r.json['elements']
                   if e['element'] == 'ring-joint-seat-mortar')
              ['fluxWb']) < 1e-12)
r = client.simulate_get('/api/magnetics/layout/ring-core-demo/cost')
check('layout cost route: 10 parts priced, exclusions stated',
      r.status_code == 200 and r.json.get('ok')
      and len(r.json['parts']) == 10 and 'excluded' in r.json)
r = client.simulate_get(
    '/api/magnetics/layout/ring-core-demo/dryfit')
check('dry-fit route: 5 adjacencies all mortared',
      r.status_code == 200 and r.json.get('mortaredJoints') == 5)

# mag-fv: field views seeded + all three payload modes answer
check('mag-fv seeds landed (3 views, 5 bands, 1 group)',
      len(manager.objectTables.get('FieldViewDefinition', {})) == 3
      and len(manager.objectTables.get('FieldThresholdBand', {}))
      == 5
      and len(manager.objectTables.get('FieldViewGroup', {})) == 1)
r = client.simulate_get('/api/magnetics/fieldview/'
                        'dipole-b-dispersion')
check('dispersion view: threshold-gated vectors + watermark',
      r.status_code == 200 and r.json.get('ok')
      and 0 < len(r.json['vectors']) < r.json['sampled']
      and 'EXACT' in r.json['watermark'])
r = client.simulate_get('/api/magnetics/fieldview/dipole-b-shells')
check('shells view: fit metrics measure the sphere-vs-dipole '
      'compromise',
      r.status_code == 200
      and r.json['shapes'][0]['fit']['precision'] is not None)
r = client.simulate_get('/api/magnetics/fieldview-group/'
                        'dipole-and-ring-group')
check('group route: 3 views in order, flux tubes included',
      r.status_code == 200 and len(r.json['views']) == 3
      and r.json['views'][2]['payload']['displayMode']
      == 'flux-tubes')

# motors (Section C): the ladder + the clock control case live
check('4 MotorDesignDefinition rows seeded (M0..M3), zero '
      'verification runs (observed state, never seeded)',
      len(manager.objectTables.get('MotorDesignDefinition', {}))
      == 4
      and len(manager.objectTables.get('MotorVerificationRun', {}))
      == 0)
r = client.simulate_get('/api/motors/designs')
check('GET /api/motors/designs 200, ladder ordered M0 first',
      r.status_code == 200 and r.json['count'] == 4
      and r.json['designs'][0]['ladderRung'] == 'M0')
r = client.simulate_get('/api/motors/clock-sim/clock-lavet-m0',
                        params={'pulses': '20'})
check('M0 clock sim on the live app: 20/20 steps, zero clock '
      'error vs time progression',
      r.status_code == 200 and r.json['stepsTaken'] == 20
      and r.json['clockComparison']['clockErrorS'] == 0.0)
r = client.simulate_get('/api/motors/torque/dual-stator-axial-m3')
check('M3 torque curve answers with dual-gap + validity honesty',
      r.status_code == 200 and r.json['dualGap']
      and 'QUASI-STATIC' in r.json['validity'])
r = client.simulate_get('/api/motors/parity',
                        params={'cheap':
                                'opt-sintered-hexaferrite',
                                'dualGap': 'true'})
check('torque_parity live: ~3.33x, dual gap ~1.67x, watermarks',
      r.status_code == 200
      and abs(r.json['areaMultiplierForParity'] - 3.333) < 0.01
      and abs(r.json['withDualGap'] - 1.667) < 0.01)
r = client.simulate_get('/api/motors/drive/reluctance-6s4p-m1')
check('mag-6 drive route: generated SimpleFOC config + 3 bindings',
      r.status_code == 200 and r.json.get('ok')
      and 'SimpleFOC.h' in r.json['configSnippet']
      and len(r.json['phaseBindings']) == 3)
r = client.simulate_get('/api/motors/drive/clock-lavet-m0')
check('mag-6: M0 FOC refusal live',
      r.status_code == 400 and 'pulse' in r.json['refusal'])
r = client.simulate_get('/api/motors/materials/clock-lavet-m0')
check('material accountability live: 3 slots, winding follows to '
      'dated citations, rotor filler trail to srfe recipes',
      r.status_code == 200 and r.json.get('ok')
      and len(r.json['slots']) == 3
      and any(s['slot'] == 'winding_material'
              and s['supply']['citations']
              for s in r.json['slots'])
      and any('fillerSupply' in s for s in r.json['slots']))

# mag-7 remainder: verification seam through the REAL create path
r = client.simulate_get('/api/motors/verify/clock-lavet-m0')
check('verify summary live: zero runs, made-and-measured honestly '
      'not earned',
      r.status_code == 200 and r.json['count'] == 0
      and r.json['madeAndMeasured'] is False)
r = client.simulate_post('/api/motors/verify/clock-lavet-m0',
                         json={'kind': 'sim-quasi-static',
                               'stepsCommanded': 60,
                               'stepsTaken': 60})
check('POST verify records through objectTypingDict (the real '
      'row-create path); sim honesty rider present',
      r.status_code == 200 and r.json.get('ok')
      and r.json['run']['clockErrorS'] == 0.0
      and 'not proof' in r.json['honesty'])
r = client.simulate_get('/api/motors/report/clock-lavet-m0')
check('design report live: verification block shows the sim run, '
      'made-and-measured still false',
      r.status_code == 200
      and r.json['verification']['simCount'] == 1
      and r.json['verification']['madeAndMeasured'] is False)
r = client.simulate_post('/api/motors/verify/clock-lavet-m0',
                         json={'kind': 'measured',
                               'stepsCommanded': 10,
                               'stepsTaken': 12})
check('impossible measured claim refuses live (422)',
      r.status_code == 422 and 'more steps' in r.json['refusal'])

# mag-7 remainder: the assembled motor as a real scene row
r = client.simulate_get('/api/simspace/motor-m0-viz/snapshot')
check('motor-m0-viz snapshot: six parts, coil references the CSG '
      'ring row',
      r.status_code == 200
      and len(r.json['data']['objects']) == 6
      and any(o['shapeRef'] == 'mathshape:motor-m0-coil-ring'
              for o in r.json['data']['objects']))
r = client.simulate_get('/api/shapes/motor-m0-coil-ring/surface')
check('coil ring surface: exact parametric TUBE mesh with '
      'triangles (the mag-7b triangulation gap, closed)',
      r.status_code == 200
      and 'parametric tube' in r.json['method']
      and len(r.json['triangles']) > 0)
r = client.simulate_get('/api/shapes/motor-m0-rotor-disc/surface')
check('rotor disc surface now carries end caps (closed solid, '
      'not a band): more triangles than the open lateral 2n',
      r.status_code == 200
      and len(r.json['triangles']) > 2 * 24)

failed = results.count(False)
print(f'\n{len(results) - failed}/{len(results)} live-boot checks '
      'passed')
sys.exit(1 if failed else 0)
