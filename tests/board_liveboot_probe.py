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
from objectTreeManagerDecorators import managerObject  # noqa: E402
manager = managerObject(hasServer=True, hasDB=True)
client = testing.TestClient(manager.polServer.falconServer)
results = []


def check(label, cond, extra=''):
    results.append(bool(cond)); print(('PASS' if cond else 'FAIL') + f': {label}' + (f'  [{extra}]' if extra and not cond else ''))


tables = manager.objectTables
typed = {(k if isinstance(k, str) else getattr(k, '__name__', str(k))) for k in manager.objectTypingDict.keys()} \
        | {getattr(v, 'className', '') for v in manager.objectTypingDict.values()}
for cls in ('BoardDefinition', 'BoardInstance', 'FirmwareBuild', 'ProgrammerKind', 'AdapterDefinition', 'DatasheetFact', 'BoardSimCost', 'Road'):
    check('class %s is typed after boot' % cls, cls in typed)
n = lambda c: len(tables.get(c, {}) or {})  # noqa: E731
check('33 devices seeded', n('BoardDefinition') == 33, n('BoardDefinition'))
check('13 adapters seeded', n('AdapterDefinition') == 13, n('AdapterDefinition'))
check('9 programmer kinds seeded', n('ProgrammerKind') == 9, n('ProgrammerKind'))
check('24 UNO facts seeded (19 brd-0 + 5 brd-1: USART UBRR x2, ADC formula, TMP36 x2)', n('DatasheetFact') == 24, n('DatasheetFact'))
check('brd-1: ONE measured BoardSimCost row seeded (the UNO twin)', n('BoardSimCost') == 1, n('BoardSimCost'))
check('33 roads seeded', n('Road') == 33, n('Road'))
tn = [x for x in (tables.get('TechNode', {}) or {}).values() if getattr(x, 'tree_name', '') == 'board-roads']
check('the board-roads tech tree has 33 concept nodes', len(tn) == 33, len(tn))
r = client.simulate_get('/api/board')
check('GET /api/board answers: simulated = [the UNO], no RULE 2 violation',
      r.status_code == 200 and r.json['simulated'] == ['arduino-uno-r3'] and r.json['rule2Violations'] == [], r.text[:200])
r = client.simulate_get('/api/board/facts', params={'board': 'arduino-uno-r3'})
check('GET /api/board/facts?board=arduino-uno-r3 → 24 cited facts', r.status_code == 200 and len(r.json['facts']) == 24, r.text[:200])
r = client.simulate_get('/api/board/roads')
check('GET /api/board/roads → 33 roads, one in progress', r.status_code == 200 and len(r.json['roads']) == 33
      and [x['board'] for x in r.json['roads'] if x['status'] != 'todo'] == ['arduino-uno-r3'], r.text[:200])
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
check('brd-1: GET /api/board/sim-costs → the UNO twin\'s measured cost (rows, state bytes, cycles/s)',
      r.status_code == 200 and len(r.json['costs']) == 1 and r.json['costs'][0]['twin'] == 'simavr:atmega328p' and r.json['costs'][0]['cycles_per_s'] > 1e6, r.text[:300])
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
check('the /display/boards page is seeded as a DisplayDefinition with six configured tables',
      len(pages) == 1 and json.loads(pages[0].definition)['rows'] and sum(len(r['items']) for r in json.loads(pages[0].definition)['rows']) == 6, len(pages))
print('\n%d/%d checks passed' % (sum(results), len(results)))
sys.exit(0 if all(results) else 1)
