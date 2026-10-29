"""In-process live-boot PROBE of hsp-3a + hsp-3d + rm-0/rm-1 (HARDWARE_SYSTEM_PINS_PLAN.md §7): boot the REAL polariServer with grpcbridge + cmod (+ board and what it needs) and
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
reg = next((o for o in (tables.get('Register') or {}).values() if getattr(o, 'name', '') == 'atmega328p:DDRD'), None)
check('rm-0: the booted Register row atmega328p:DDRD carries domains_json mcu-pin/direction + its roles', reg is not None and 'mcu-pin/direction' in getattr(reg, 'domains_json', '')
      and 'control' in getattr(reg, 'roles_json', ''), getattr(reg, 'domains_json', None))
r = client.simulate_get('/api/board/arduino-uno-r3/pins/D0/stages', params={'claim': 'gpio-out'})
check('rm-1: GET /api/board/arduino-uno-r3/pins/D0/stages?claim=gpio-out -> two boot-critical conflicts', r.status_code == 200 and len(r.json['boot_critical']) == 2, r.text[:300])
check('hsp-3c: class HalVariableState is typed after boot', 'HalVariableState' in typed)
sols = {getattr(o, 'name', ''): o for o in (tables.get('SolutionDefinition') or {}).values()}
check('hsp-3c: the hal-uno-light + hal-esp32c3-light drawings are seeded SolutionDefinitions of category hal',
      all(getattr(sols.get(nm), 'category', '') == 'hal' for nm in ('hal-uno-light', 'hal-esp32c3-light')), sorted(nm for nm in sols if nm.startswith('hal')))
r = client.simulate_get('/api/cmod/catom-variables/uno-light/solution')
check('hsp-3c: GET /api/cmod/catom-variables/uno-light/solution -> 6 HAL cards', r.status_code == 200 and len(r.json['definition']['stateInstances']) == 6, r.text[:300])
r = client.simulate_post('/api/cmod/catom-variables/uno-light/set', json={'variable': 'LED_PIN', 'value': 'D2'})
check('hsp-3c: POST .../uno-light/set {LED_PIN: D2} -> 422 (BUTTON_PIN holds PD2), nothing written', r.status_code == 422 and r.json['written'] == [], r.text[:300])
r = client.simulate_post('/api/cmod/catom-variables/uno-light/set', json={'variable': 'LED_PIN', 'value': 'D7'})
fv = next((o for o in (tables.get('FirmwareVariant') or {}).values() if getattr(o, 'name', '') == 'uno-light'), None)
h = client.simulate_get('/api/cmod/catom-variables/uno-light', params={'view': 'header'})
check('hsp-3c: POST .../uno-light/set {LED_PIN: D7} writes the booted FirmwareVariant knob led_pin 7; the header then says LED_PIN 7',
      r.status_code == 200 and fv is not None and '"led_pin": 7' in fv.knobs_json and '#define LED_PIN        7' in h.json['text'], (r.text[:300], getattr(fv, 'knobs_json', None)))
r = client.simulate_get('/api/cmod/bench-structs/home-bench', params={'view': 'path', 'instance': 'uno-1-bridge/LightState_t[0]', 'field': 'led_on'})
check('hsp-3b: GET /api/cmod/bench-structs/home-bench?view=path (led_on) -> the routes from the booted rows, ending at the LightState object',
      r.status_code == 200 and r.json['count'] >= 15 and any(s['kind'] == 'object' for s in r.json['rows']), r.text[:300])
r = client.simulate_post('/api/grpc/bench-bridges/home-bench/mode', json={'bridge': 'uno-1-bridge'})
r2 = client.simulate_post('/api/grpc/bench-bridges/home-bench/mode', json={'bridge': 'uno-1-bridge'})
check('hsp-3c: POST /api/grpc/bench-bridges/home-bench/mode toggles the booted bridge serial -> simulated (twin worker hops) -> serial',
      r.status_code == 200 and r.json['mode'] == 'simulated' and 'board-engines' in r.json['hops'][-1]['what'] and r2.json['mode'] == 'serial', r.text[:300])
pages = {getattr(o, 'pageRoute', '') for o in (tables.get('DisplayDefinition') or {}).values()}
check('hsp-3b: the /display/bench-views page is a seeded DisplayDefinition', 'bench-views' in pages, sorted(p for p in pages if 'bench' in p))
acc = {getattr(o, 'name', ''): o for o in (tables.get('RegisterAccessKind') or {}).values()}
pf = next((o for o in (tables.get('RegisterField') or {}).values() if getattr(o, 'name', '') == 'atmega328p:MCUSR.PORF'), None)
check('rm-2a: the six RegisterAccessKind rows are seeded (w0c = UVM W0C) and the booted RegisterField MCUSR.PORF is w0c',
      set(acc) == {'rw', 'r', 'w1c', 'w0c', 'w-strobe', 'rw-toggle'} and acc['w0c'].uvm_policy == 'W0C' and pf is not None and pf.access == 'w0c', sorted(acc))
r = client.simulate_get('/RegisterAccessKind')
check('rm-2a: CRUDE GET /RegisterAccessKind answers 200', r.status_code == 200, r.status_code)
print('\n%d/%d passed' % (sum(results), len(results)))
sys.exit(0 if all(results) else 1)
