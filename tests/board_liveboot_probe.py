"""In-process live-boot PROBE of brd-0: boot the REAL polariServer with board (+ hwmap, techtree, grpcbridge) enabled, then
hit its routes — proving the guarded imports, defClassList wiring, seed pairs (33 devices, 13 adapters, 9 programmer
kinds, the UNO's facts, 33 roads + the board-roads tree), the page seed and route registration outside the selftest.
Run from a THROWAWAY working directory (the boot writes its sqlite DB into ./data/ of the cwd):
  cd /tmp/somewhere && PYTHONPATH=<framework>:<framework>/modules python3 <framework>/tests/board_liveboot_probe.py
"""
import json
import os
import sys
os.environ['POLARI_MODULES'] = 'techtree,hwmap,hardwareapps,islemesh,grpcbridge,board'
os.environ.setdefault('POLARI_DB_BACKEND', 'sqlite')
FRAMEWORK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, FRAMEWORK); sys.path.insert(0, os.path.join(FRAMEWORK, 'modules'))
from falcon import testing  # noqa: E402
sys.path.insert(0, os.path.join(FRAMEWORK, 'tests'))
from board_probe_boot import boot  # noqa: E402 — brd-wire: the framework as cwd for the boot, the DB in ./data here
manager = boot(FRAMEWORK)
client = testing.TestClient(manager.polServer.falconServer)
results = []


def check(label, cond, extra=''):
    results.append(bool(cond)); print(('PASS' if cond else 'FAIL') + f': {label}' + (f'  [{extra}]' if extra and not cond else ''))


tables = manager.objectTables
typed = {(k if isinstance(k, str) else getattr(k, '__name__', str(k))) for k in manager.objectTypingDict.keys()} \
        | {getattr(v, 'className', '') for v in manager.objectTypingDict.values()}
for cls in ('BoardDefinition', 'BoardInstance', 'FirmwareBuild', 'ProgrammerKind', 'AdapterDefinition', 'DatasheetFact', 'BoardSimCost', 'Road',
            'FirmwareVariant', 'InstallPlan', 'InstallRecord', 'UnoAnalogState'):
    check('class %s is typed after boot' % cls, cls in typed)
n = lambda c: len(tables.get(c, {}) or {})  # noqa: E731
check('33 devices seeded', n('BoardDefinition') == 33, n('BoardDefinition'))
check('13 adapters seeded', n('AdapterDefinition') == 13, n('AdapterDefinition'))
check('9 programmer kinds seeded', n('ProgrammerKind') == 9, n('ProgrammerKind'))
check('24 UNO facts seeded (19 brd-0 + 5 brd-1: USART UBRR x2, ADC formula, TMP36 x2)', n('DatasheetFact') == 24, n('DatasheetFact'))
sim_cost_boards = sorted(getattr(c, 'board', '') for c in (tables.get('BoardSimCost', {}) or {}).values())
check('brd-1 + sc-3: two measured BoardSimCost rows seeded (the UNO twin + the C3 twin)',
      sim_cost_boards == ['arduino-uno-r3', 'esp32-c3'], sim_cost_boards)
check('33 roads seeded', n('Road') == 33, n('Road'))
tn = [x for x in (tables.get('TechNode', {}) or {}).values() if getattr(x, 'tree_name', '') == 'board-roads']
check('the board-roads tech tree has 33 concept nodes', len(tn) == 33, len(tn))
r = client.simulate_get('/api/board')
check('GET /api/board answers: simulated = [the UNO, the C3], no RULE 2 violation',
      r.status_code == 200 and r.json['simulated'] == ['arduino-uno-r3', 'esp32-c3'] and r.json['rule2Violations'] == [], r.text[:200])
r = client.simulate_get('/api/board/facts', params={'board': 'arduino-uno-r3'})
check('GET /api/board/facts?board=arduino-uno-r3 → 24 cited facts', r.status_code == 200 and len(r.json['facts']) == 24, r.text[:200])
r = client.simulate_get('/api/board/roads')
check('GET /api/board/roads → 33 roads, two in progress (the UNO + the C3)', r.status_code == 200 and len(r.json['roads']) == 33
      and sorted(x['board'] for x in r.json['roads'] if x['status'] != 'todo') == ['arduino-uno-r3', 'esp32-c3'], r.text[:200])
r = client.simulate_get('/api/board/engines')
check('GET /api/board/engines → the ladder for avr-gcc', r.status_code == 200 and 'avr-gcc' in r.json['engines'], r.text[:200])
snap = {'host': 'pol-core', 'observed_at': 'now', 'usb': [{'bus': '003', 'dev': '003', 'vendor_id': '10c4', 'product_id': 'ea60', 'description': 'CP210x', 'path': '003-5', 'usb_class': 'Vendor Specific Class'}],
        'serial': [{'by_id_path': '/dev/serial/by-id/usb-Silicon_Labs_CP2102_USB_to_UART_Bridge_Controller_0001-if00-port0', 'device': '/dev/ttyUSB0', 'vendor_id': '10c4', 'product_id': 'ea60', 'serial': '0001', 'bus': '003', 'dev': '003'}]}
r = client.simulate_post('/api/board/detect', body=json.dumps(snap), headers={'Content-Type': 'application/json'})
inst = list((tables.get('BoardInstance', {}) or {}).values())
check('POST /api/board/detect upserts the CP2102 as a BoardInstance (adapter present, target unknown)',
      r.status_code == 201 and r.json['stored'] == 1 and len(inst) == 1 and inst[0].state == 'adapter present, target unknown', r.text[:300])
r = client.simulate_post('/api/board/detect', body=json.dumps(snap), headers={'Content-Type': 'application/json'})
check('a second detect UPDATES the same row (no duplicate)', r.status_code == 201 and n('BoardInstance') == 1, n('BoardInstance'))
r = client.simulate_get('/api/board/sim-costs')
costs_by_board = {c['board']: c for c in (r.json.get('costs') or [])}
check('brd-1 + sc-3: GET /api/board/sim-costs → both twins\' measured cost (rows, state bytes, cycles/s)',
      r.status_code == 200 and len(r.json['costs']) == 2
      and costs_by_board.get('arduino-uno-r3', {}).get('twin') == 'simavr:atmega328p' and costs_by_board.get('arduino-uno-r3', {}).get('cycles_per_s', 0) > 1e6
      and costs_by_board.get('esp32-c3', {}).get('twin') == 'qemu:esp32c3' and costs_by_board.get('esp32-c3', {}).get('cycles_per_s', 0) > 1e6, r.text[:300])
b = {'build': {'name': 'arduino-uno-r3-probe', 'board_definition': 'arduino-uno-r3', 'state': 'built', 'size_text': 4416, 'size_data': 26, 'size_bss': 737,
               'artifact_sha256': 'ab' * 32, 'classes_json': '[]', 'repro_json': '{}'}}
r = client.simulate_post('/api/board/builds', body=json.dumps(b), headers={'Content-Type': 'application/json'})
r2 = client.simulate_get('/api/board/builds')
check('brd-1: POST /api/board/builds upserts a FirmwareBuild; GET lists it with its sizes',
      r.status_code == 201 and n('FirmwareBuild') == 1 and r2.json['builds'][0]['size_text'] == 4416, r.text[:300])
fl = dict(b['build'], state='flashed', flashed_to=inst[0].name)
r = client.simulate_post('/api/board/builds', body=json.dumps({'build': fl, 'instance': {'name': inst[0].name, 'firmware_sha': 'cd' * 32}}), headers={'Content-Type': 'application/json'})
check('brd-1: a flashed build whose stamp names a DIFFERENT firmware is refused (409)', r.status_code == 409, r.text[:200])
r = client.simulate_post('/api/board/builds', body=json.dumps({'build': fl, 'instance': {'name': inst[0].name, 'firmware_sha': 'ab' * 32, 'last_flash_at': '2026-10-01T17:00:00'}}), headers={'Content-Type': 'application/json'})
check('brd-1: a flashed build stamps BoardInstance.firmware_sha / last_flash_at; the row count stays one',
      r.status_code == 201 and inst[0].firmware_sha == 'ab' * 32 and inst[0].last_flash_at and n('FirmwareBuild') == 1, r.text[:200])
pages = [d for d in (tables.get('DisplayDefinition', {}) or {}).values() if getattr(d, 'pageRoute', '') == 'boards']
check('the /display/boards page is seeded as a DisplayDefinition with seven configured tables (brd-wire: + bindings)',
      len(pages) == 1 and json.loads(pages[0].definition)['rows'] and sum(len(r['items']) for r in json.loads(pages[0].definition)['rows']) == 7, len(pages))
# ---- brd-fi: the firmware installer
fv_rows = list((tables.get('FirmwareVariant', {}) or {}).values())
fv_uno = sorted(v.name for v in fv_rows if getattr(v, 'board_definition', '') == 'arduino-uno-r3')
fv_c3 = sorted(v.name for v in fv_rows if getattr(v, 'board_definition', '') == 'esp32-c3')
check('brd-fi: the five UNO FirmwareVariants + sc-3: the six ESP32-C3 FirmwareVariants are seeded (brd-wire: + uno-pair)',
      fv_uno == ['uno-adc-sweep', 'uno-blink-only', 'uno-echo', 'uno-pair', 'uno-sim-rig']
      and fv_c3 == ['c3-prio-inversion', 'c3-prio-inversion-mutex', 'c3-sim-rig', 'c3-two-lock', 'c3-two-lock-backoff', 'c3-two-lock-ordered'],
      (fv_uno, fv_c3))
r = client.simulate_get('/api/board/variants')
v_names = [v['name'] for v in r.json['variants']]
check('brd-fi: GET /api/board/variants → eleven (the five UNO + sc-3: the six C3), each with what to watch',
      r.status_code == 200 and len(v_names) == 11
      and sorted(x for x in v_names if x.startswith('uno-')) == ['uno-adc-sweep', 'uno-blink-only', 'uno-echo', 'uno-pair', 'uno-sim-rig']
      and sorted(x for x in v_names if x.startswith('c3-')) == ['c3-prio-inversion', 'c3-prio-inversion-mutex', 'c3-sim-rig', 'c3-two-lock', 'c3-two-lock-backoff', 'c3-two-lock-ordered']
      and all(v['what_to_watch'] for v in r.json['variants']), r.text[:200])
r = client.simulate_get('/api/board/installer')
check('brd-fi: GET /api/board/installer → this host, the twin as a target, the five variants, the cited limits',
      r.status_code == 200 and r.json['targets'][0]['name'] == 'twin:arduino-uno-r3' and len(r.json['variants']) == 5
      and r.json['limits']['flash_b'] == 32256, r.text[:300])
r = client.simulate_post('/api/board/installer/plan', body=json.dumps({'instance': 'twin:arduino-uno-r3', 'build': 'no-such-build'}), headers={'Content-Type': 'application/json'})
check('brd-fi: a plan for a build that does not exist → 404 in plain words', r.status_code == 404 and 'no build named' in r.json['error'], r.text[:200])
r = client.simulate_post('/api/board/installer/run', body=json.dumps({'plan': 'nope', 'confirm': True}), headers={'Content-Type': 'application/json'})
check('brd-fi: run with no such plan → 404, exit 3', r.status_code == 404 and r.json['exit'] == 3, r.text[:200])
r = client.simulate_get('/api/board/builds/arduino-uno-r3-probe/compat')
check('brd-fi: GET /api/board/builds/<b>/compat on a build listing no classes → unknown-class', r.status_code == 200 and r.json['verdict'] == 'unknown-class', r.text[:200])
fi = [d for d in (tables.get('DisplayDefinition', {}) or {}).values() if getattr(d, 'pageRoute', '') == 'firmware-installer']
names = [it['componentProps']['componentName'] for row in json.loads(fi[0].definition)['rows'] for it in row['items']] if fi else []
check('brd-fi: /display/firmware-installer is seeded — six configured tables + the ONE firmware-installer-panel',
      len(fi) == 1 and names.count('firmware-installer-panel') == 1 and names.count('class-rows-table') == 6, names)
# ---- brd-wire (grpc-j4): the mapping rows boot, seed, and the analysis door answers
for cls in ('HardwareInterfaceBinding', 'EnumMapping', 'WireContract'):
    check('brd-wire: class %s is typed after boot' % cls, cls in typed)
check('brd-wire: two EnumMappings + the two uno-pair bindings seeded (index 0 / 1)', n('EnumMapping') == 2
      and sorted((b.object_name, b.instance_index) for b in (tables.get('HardwareInterfaceBinding', {}) or {}).values())
      == [('uno-twin-0', 0), ('uno-twin-1', 1)], (n('EnumMapping'), n('HardwareInterfaceBinding')))
from urllib.parse import quote  # noqa: E402
r = client.simulate_get('/api/board/instances/%s/interface' % quote('twin:arduino-uno-r3#1', safe=''))
check('brd-wire: GET /api/board/instances/twin:arduino-uno-r3%231/interface → the chain: uno-twin-1, index 1, the UNO definition, its facts',
      r.status_code == 200 and r.json['links'][0]['binding']['instance_index'] == 1 and r.json['links'][0]['board_definition']['name'] == 'arduino-uno-r3'
      and len(r.json['links'][0]['datasheet_facts']) == 24, r.text[:300])
r = client.simulate_get('/api/board/instances/%s/interface' % quote('twin:nobody', safe=''))
check('brd-wire: an unbound instance → 404 naming the bound ones', r.status_code == 404 and 'twin:arduino-uno-r3#0' in r.json['error'], r.text[:200])
print('\n%d/%d checks passed' % (sum(results), len(results)))
sys.exit(0 if all(results) else 1)
