"""nav-6 (NAVIGATION_REVAMP_PLAN): the ABSENT-MODULE MAP probe.

Boot the real polariServer with the ENTIRE magnetics chain gated
OFF (no magnetics, motors, composition, gears) and prove the
navigation still carries the map:

- /api/apps/nav answers with ALL apps, including app-magnetics;
- every gated item of the magnetics app renders ABSENT — kept, with
  the /modules/bringup affordance and its requires chain — never
  hidden;
- the tech-node item stays available (trees are core-bootable, the
  abstract map survives the missing territory);
- the CONTRAST case: scoring is ON, so the scorecards app's items
  are enabled in the same payload;
- with composition off, the polariapps rows arrive via the LEGACY
  insert pass — the no-composition fallback is a real path, proven.

Run from a THROWAWAY working directory (the boot writes a sqlite DB
into cwd):  cd /tmp/somewhere && \
  PYTHONPATH=<framework>:<framework>/modules python3 \
  <framework>/tests/apps_nav_probe.py
"""

import os
import sys

os.environ['POLARI_MODULES'] = (
    'polariapps,techtree,scoring,dmvdata')
os.environ.setdefault('POLARI_DB_BACKEND', 'sqlite')
# In-process probe: seed synchronously — the container's lazy-boot
# knob would defer everything to an admission worker and 503 us.
os.environ['POLARI_LAZY_BOOT'] = 'off'

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


check('polariapps rows seeded WITHOUT composition (legacy '
      'insert fallback)',
      len(manager.objectTables.get('PolariAppDefinition', {}))
      == 11,
      extra=str(len(manager.objectTables.get(
          'PolariAppDefinition', {}))))

r = client.simulate_get('/api/apps/nav')
check('/api/apps/nav 200, all 11 apps, gating readable',
      r.status_code == 200 and r.json.get('ok')
      and r.json.get('gatingReadable')
      and len(r.json.get('apps', [])) == 11, extra=r.status)

r = client.simulate_get('/api/apps/nav/app-magnetics')
ok = r.status_code == 200 and r.json.get('ok')
check('magnetics app answers while its every module is OFF', ok,
      extra=r.status)
if ok:
    nav = r.json['nav']
    items = [it for g in nav for it in g['items']]
    gated = [it for it in items if it.get('requiresModule')]
    check('the FULL nav renders: both groups, all six items — '
          'nothing hidden',
          len(nav) == 2 and len(items) == 6,
          extra=f'{len(nav)} groups {len(items)} items')
    check('every gated item is ABSENT with the bringup affordance',
          gated and all(
              it['availability'] == 'absent'
              and it['bringup']['route'] == '/modules/bringup'
              for it in gated),
          extra=str([it['availability'] for it in gated]))
    check('absent items carry their requires chain from the '
          'registry',
          any(it['bringup'].get('requires') for it in gated),
          extra=str([it.get('bringup') for it in gated])[:200])
    check('the tech-node item survives ungated (the abstract map)',
          any(it['kind'] == 'tech-node'
              and it['availability'] == 'enabled'
              and it.get('ref')
              == 'electronics/electromagnetic-systems'
              for it in items))
    check('module strip: all four magnetics-chain modules absent',
          r.json['moduleStates'] == {
              'magnetics': 'absent', 'motors': 'absent',
              'composition': 'absent', 'gears': 'absent'},
          extra=str(r.json.get('moduleStates')))

check('the tech tree the ref points at is BOOTED (core-bootable '
      'map)',
      any(getattr(n, 'name', '')
          == 'electronics/electromagnetic-systems'
          for n in manager.objectTables.get('TechNode',
                                            {}).values()))

r = client.simulate_get('/api/apps/nav/app-scorecards-data-analysis')
check('CONTRAST: scoring app fully enabled in the same boot',
      r.status_code == 200 and r.json.get('ok')
      and all(it['availability'] == 'enabled'
              for g in r.json['nav'] for it in g['items']),
      extra=str([(it['label'], it['availability'])
                 for g in r.json.get('nav', [])
                 for it in g['items']])[:200])

r = client.simulate_get('/api/apps/nav/nope')
check('unknown app refuses honestly with 404',
      r.status_code == 404 and not r.json.get('ok'))

total, passed = len(results), sum(results)
print(f'\n{passed}/{total} probe checks passed')
sys.exit(0 if passed == total else 1)
