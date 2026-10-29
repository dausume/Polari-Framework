"""In-process live-boot PROBE of hsp-3a (HARDWARE_SYSTEM_PINS_PLAN.md §7): boot the REAL polariServer with grpcbridge + cmod (+ board and what it needs) and
check the four new classes are typed, their seeds land (7 catom assertions, 1 struct-object map, 2 bridge paths, 1 bridge), the CRUDE routes answer and the
two doors serve the stored rows (status recomputed from the uno-light record; the UNO bridge bound to polari-pol).
Run from a THROWAWAY working directory (the boot writes its sqlite DB into ./data/ of the cwd):
  cd /tmp/somewhere && PYTHONPATH=<framework>:<framework>/modules python3 <framework>/tests/hsp3a_liveboot_probe.py
"""
import os
import sys
os.environ['POLARI_MODULES'] = 'techtree,hwmap,hardwareapps,islemesh,grpcbridge,board,cmod,hwnocode'
os.environ.setdefault('POLARI_DB_BACKEND', 'sqlite')
FRAMEWORK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, FRAMEWORK); sys.path.insert(0, os.path.join(FRAMEWORK, 'modules'))
results = []


def check(label, cond, extra=''):
    results.append(bool(cond)); print(('PASS' if cond else 'FAIL') + f': {label}' + (f'  [{extra}]' if extra and not cond else ''))


from falcon import testing  # noqa: E402
sys.path.insert(0, os.path.join(FRAMEWORK, 'tests'))
from board_probe_boot import boot  # noqa: E402
manager = boot(FRAMEWORK)
client = testing.TestClient(manager.polServer.falconServer)
tables = manager.objectTables
typed = {(k if isinstance(k, str) else getattr(k, '__name__', str(k))) for k in manager.objectTypingDict.keys()}
for cls in ('CatomAssertion', 'StructObjectMap', 'BridgePath', 'PolariBridgeInstance', 'CatomVariable'):
    check('class %s is typed after boot' % cls, cls in typed)
n = lambda c: len(tables.get(c, {}) or {})  # noqa: E731
check('seeds landed: 7 catom assertions, 1 struct-object map, 2 bridge paths, 1 Polari bridge',
      (n('CatomAssertion'), n('StructObjectMap'), n('BridgePath'), n('PolariBridgeInstance')) == (7, 1, 2, 1),
      (n('CatomAssertion'), n('StructObjectMap'), n('BridgePath'), n('PolariBridgeInstance')))
for cls in ('CatomAssertion', 'PolariBridgeInstance'):
    r = client.simulate_get('/' + cls)
    check('CRUDE GET /%s answers 200' % cls, r.status_code == 200, r.status_code)
r = client.simulate_get('/api/cmod/catom-assertions/uno-light')
st = {(a['atom'], a['kind']): a['status'] for a in (r.json or {}).get('assertions', [])}
check('GET /api/cmod/catom-assertions/uno-light: the stored rows, telemetry_send sends-to-bridge verified, field changes unverified, gaps named',
      r.status_code == 200 and st.get(('apps/light.telemetry_send', 'sends-to-bridge')) == 'verified'
      and st.get(('apps/light.led_toggle', 'changes-field')) == 'unverified' and len(r.json['gaps']) == 6, (r.status_code, st))
r = client.simulate_get('/api/grpc/bench-bridges/home-bench', params={'view': 'bridges'})
check('GET /api/grpc/bench-bridges/home-bench?view=bridges: the UNO bridge bound to https://api.polari-pol.isle',
      r.status_code == 200 and r.json['rows'][0]['status'] == 'bound' and r.json['rows'][0]['polari_node_url'] == 'https://api.polari-pol.isle', r.text[:300])
check('hsp-3d seeds landed: 11 catom variables (uno-light 6 + esp32c3-light 5)', n('CatomVariable') == 11, n('CatomVariable'))
r = client.simulate_get('/api/cmod/catom-variables/uno-light', params={'view': 'header'})
check('GET /api/cmod/catom-variables/uno-light?view=header carries UART0_TX_PIN PD1 from the stored rows', r.status_code == 200 and '#define UART0_TX_PIN   PD1' in r.json['text'], r.text[:300])
r = client.simulate_post('/api/cmod/catom-variables/uno-light/check', json={'variable': 'UART0_TX_PIN', 'value': 'PD2'})
check('POST /api/cmod/catom-variables/uno-light/check {UART0_TX_PIN: PD2} -> refused naming PD1 (TXD)', r.status_code == 200 and r.json['verdict'] == 'refused'
      and 'PD1 (TXD)' in r.json['why'][0], r.text[:300])
print('\n%d/%d passed' % (sum(results), len(results)))
sys.exit(0 if all(results) else 1)
