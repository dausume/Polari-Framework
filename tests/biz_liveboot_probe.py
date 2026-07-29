"""In-process live-boot PROBE of the business stack (biz-4/od-4b/
biz-5 wiring): boot the
real polariServer with supplychain+bizops+odooconnect enabled, then
hit the new sellability/qa routes plus the embedded walkthrough —
proving the guarded imports, defClassList wiring, seed_pairs seeding,
and route registration all work outside selftest fixtures."""

import json
import os
import sys

os.environ['POLARI_MODULES'] = (
    'supplychain,bizops,odooconnect,waxprint,scoring')
os.environ.setdefault('POLARI_DB_BACKEND', 'sqlite')

# Run from a THROWAWAY working directory (the boot writes a sqlite
# DB into cwd):  cd /tmp/somewhere && \
#   PYTHONPATH=<framework>:<framework>/modules python3 \
#   <framework>/tests/biz_liveboot_probe.py
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


# seeds landed through the REAL seed_pairs path
reqs = manager.objectTables.get('ComplianceRequirement', {})
checks_tbl = manager.objectTables.get('QualityCheckDefinition', {})
check('6 ComplianceRequirement rows seeded by polariServer',
      len(reqs) == 6, extra=str(len(reqs)))
check('6 QualityCheckDefinition rows seeded by polariServer '
      '(5 biz-4 + wound-core-inductance mag-2)',
      len(checks_tbl) == 6, extra=str(len(checks_tbl)))
food = next((r for r in reqs.values()
             if getattr(r, 'name', '') == 'req-food-contact'), None)
check('food-contact row demands certified-third-party-pass',
      food is not None and food.required_level
      == 'certified-third-party-pass')

# the new routes, through the real falcon app
r = client.simulate_get('/api/bizops/sellability/wax-mold-goods')
body = r.json
check('GET /api/bizops/sellability/{biz} 200 + ok',
      r.status_code == 200 and body.get('ok'), extra=r.status)
check('plain goods start blocked (no records yet), hard rule + '
      'disclaimer present',
      body.get('canSellPlainGoods') is False
      and 'certified-third-party-pass' in body.get('hardRule', '')
      and 'NOT legal' in body.get('disclaimer', ''))
ctxs = {c['context']: c for c in body.get('contexts', [])}
check('food-contact context blocked at unassessed on the live app',
      not ctxs.get('sold-as-food-contact', {}).get('allowed', True))

r = client.simulate_get('/api/bizops/qa/wax-mold-goods')
body = r.json
check('GET /api/bizops/qa/{biz} 200 + 6 checks all honestly '
      'unmeasured',
      r.status_code == 200 and body.get('ok')
      and len(body.get('checks', [])) == 6
      and all(c['passRatePct'] is None for c in body['checks']),
      extra=r.status)

r = client.simulate_get('/api/bizops/sellability/nope')
check('unknown business = 404 + refusal sentence',
      r.status_code == 404 and r.json.get('refusal'), extra=r.status)

r = client.simulate_get(
    '/api/bizops/walkthrough/wax-mold-goods?budgetUsd=120')
body = r.json
sell = next((s for s in body.get('steps', [])
             if s.get('step') == 'sell-and-log'), {})
check('walkthrough sell-and-log embeds live sellability on the '
      'real app',
      body.get('ok') and sell.get('sellability', {}).get('ok'))

# neighboring routes still alive after the wiring edits
r = client.simulate_get('/api/bizops/deal-pricing')
body = r.json
check('GET /api/bizops/deal-pricing 200: 3 deals, biomass window '
      'suggests 2.40 on the live app',
      r.status_code == 200 and body.get('ok')
      and len(body.get('deals', [])) == 3
      and any(f.get('suggestedUsdPerKg') == 2.4
              for d in body['deals'] for f in d['flows']),
      extra=r.status)

r = client.simulate_get('/api/odoo/bindings')
names = [b['name'] for b in r.json.get('bindings', [])]
check('sim-sale-orders binding seeded on the live app',
      'sim-sale-orders' in names, extra=str(names))
r = client.simulate_post('/api/odoo/pull-orders',
                         json={'binding': 'nope'})
check('POST /api/odoo/pull-orders registered (unknown binding = '
      '400 refusal)',
      r.status_code == 400 and r.json.get('refusal'), extra=r.status)

for path in ('/api/bizops/economy', '/api/bizops/partnerships',
             '/api/supplychain/sourcing/sources',
             '/api/odoo/configs'):
    r = client.simulate_get(path)
    check(f'{path} still answers 200', r.status_code == 200,
          extra=r.status)

failed = results.count(False)
print(f'\n{len(results) - failed}/{len(results)} live-boot checks passed')
sys.exit(1 if failed else 0)
