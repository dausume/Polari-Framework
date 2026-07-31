"""In-process live-boot PROBE of the composition module (arch-7):
boot the real polariServer with composition (+its requires and the
magnetics chain for material resolution) enabled, then hit the
/api/composition routes — proving the guarded import, defClassList
wiring, the arch-1 UPSERT seed path, and route registration work
outside selftest fixtures.

Run from a THROWAWAY working directory (the boot writes a sqlite DB
into cwd):  cd /tmp/somewhere && \
  PYTHONPATH=<framework>:<framework>/modules python3 \
  <framework>/tests/composition_liveboot_probe.py
"""

import os
import sys

os.environ['POLARI_MODULES'] = (
    'materialsScience,supplychain,magnetics,motors,'
    'scoring,plant_morphology,aquaponics,mathshapes,techtree,'
    'composition')
os.environ.setdefault('POLARI_DB_BACKEND', 'sqlite')

FRAMEWORK = os.path.dirname(os.path.dirname(os.path.abspath(
    __file__)))
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


EXPECTED_COUNTS = {
    'FailureModeDefinition': 10, 'PartComponentDefinition': 4,
    'CompositionNode': 3, 'InterfaceDefinition': 5,
    'FunctionalPartDefinition': 1,
    'ConstructionVariantDefinition': 3, 'RoutingDefinition': 3,
    'RoutingOperation': 8, 'DesignMatrixDefinition': 2,
    'PartArchetypeDefinition': 5,
}
for class_name, expected in EXPECTED_COUNTS.items():
    got = len(manager.objectTables.get(class_name, {}))
    check(f'{expected} {class_name} rows seeded (via UPSERT path)',
          got == expected, extra=str(got))

r = client.simulate_get('/api/composition/nodes')
check('GET /api/composition/nodes 200, 3 nodes, no refusals',
      r.status_code == 200 and r.json.get('count') == 3
      and not r.json.get('refusals'), extra=r.status)

r = client.simulate_get('/api/composition/node/stator-layered')
check('layered stator: level part-with-separable-sub-parts, '
      'realization theoretical (derived live)',
      r.status_code == 200
      and r.json['level'].get('derived')
      == 'part-with-separable-sub-parts'
      and r.json['realization'].get('level') == 'theoretical',
      extra=str(r.json)[:200])

r = client.simulate_get(
    '/api/composition/functional/fp-m0-stator'
    '?wound_diameter_mm=0.2269&wall_mm=0.05')
if r.status_code == 200 and r.json.get('ok'):
    by = {v['variant']: v for v in r.json['variants']}
    check('variant report live: 0.5274 grooved vs 0.600 scramble '
          'at 50um wall (mag-26 intact through the API)',
          by['cv-stator-layered-bound']['fill'] == 0.5274
          and by['cv-stator-simple']['fill'] == 0.6)
else:
    check('variant report live', False, extra=r.status)

r = client.simulate_get('/api/composition/step-counts/fp-m0-stator')
counts = {v['variant']: v.get('stepCount')
          for v in r.json.get('variants', [])}
check('step counts 1/3/4 derive from routings, live',
      counts == {'cv-stator-simple': 1, 'cv-stator-bound': 3,
                 'cv-stator-layered-bound': 4}, extra=str(counts))

r = client.simulate_get('/api/composition/promotion/op-bound-cure')
check('bound-stator promotion audits clean through the API',
      r.status_code == 200 and r.json.get('ok') is True,
      extra=str(r.json.get('problems'))[:200])

r = client.simulate_get('/api/composition/archetype/at-coil-winding')
check('coil archetype live: matrix DECOUPLED, order '
      'gauge->window->turns',
      r.status_code == 200
      and r.json['designMatrix'].get('classification') == 'decoupled'
      and r.json['designMatrix'].get('tuningOrder')
      == ['gauge', 'window', 'turns'])

r = client.simulate_get('/api/composition/matrix/dm-lavet-magnet')
check('ratio-trap finding surfaces live (stronger magnet != '
      'better motor)',
      any(f.get('kind') == 'ratio-trap'
          for f in r.json.get('findings', [])))

# goal-1..3 live: the scale study runs off composition's matrix +
# equation rows through the real server.
r = client.simulate_get('/api/motors/goal/goal-local-wall-clock')
check('wall-clock goal live: zero blockers, the SrFe12O19 gap, '
      'order from the matrix',
      r.status_code == 200 and r.json.get('verdict') == 'unassessed'
      and not r.json.get('blockers')
      and r.json.get('tuningOrder') == ['gauge', 'window', 'turns'],
      extra=str(r.json.get('blockers'))[:200])
r = client.simulate_get('/api/motors/goal/goal-local-watch')
check('watch goal live: BLOCKED with named blockers',
      r.status_code == 200 and r.json.get('verdict') == 'blocked'
      and len(r.json.get('blockers', [])) == 2)
r = client.simulate_get(
    '/api/motors/scale-study?policy=local-plus-imported-wire')
check('scale study live: five scales swept',
      r.status_code == 200
      and len(r.json.get('summary', [])) == 5)
check('goal seed rows landed via the upsert path',
      len(manager.objectTables.get('ClockScaleDefinition', {})) == 5
      and len(manager.objectTables.get('MotorGoalSpec', {})) == 6)

# THE arch-1 live proof: drift a prior row, re-seed, watch it
# converge — the ten-strikes gotcha ending on a LIVE table.
node = next(iter(
    n for n in manager.objectTables['CompositionNode'].values()
    if getattr(n, 'name', '') == 'stator-bound'))
node.notes = 'DRIFTED BY PROBE'
from composition.composition_seed import seed_composition  # noqa: E402
reports = seed_composition(manager)
node_report = next(r for r in reports
                   if r.get('class') == 'CompositionNode')
check('UPSERT converges a drifted prior row live (no CRUDE PUT '
      'needed)',
      'DRIFTED' not in getattr(node, 'notes', '')
      and any(u['name'] == 'stator-bound'
              for u in node_report.get('updated', [])),
      extra=str(node_report)[:200])
node.is_prior = False
node.notes = 'CUSTOMIZED BY HUMAN'
seed_composition(manager)
check('is_prior=False row survives re-seed untouched (knobs '
      'ethos, live)',
      getattr(node, 'notes', '') == 'CUSTOMIZED BY HUMAN')
node.is_prior = True
seed_composition(manager)

total, passed = len(results), sum(results)
print(f'\n{passed}/{total} probe checks passed')
sys.exit(0 if passed == total else 1)
