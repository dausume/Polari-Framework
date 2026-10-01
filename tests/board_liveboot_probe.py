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
check('19 UNO facts seeded', n('DatasheetFact') == 19, n('DatasheetFact'))
check('33 roads seeded', n('Road') == 33, n('Road'))
tn = [x for x in (tables.get('TechNode', {}) or {}).values() if getattr(x, 'tree_name', '') == 'board-roads']
check('the board-roads tech tree has 33 concept nodes', len(tn) == 33, len(tn))
r = client.simulate_get('/api/board')
check('GET /api/board answers: simulated = [the UNO], no RULE 2 violation',
      r.status_code == 200 and r.json['simulated'] == ['arduino-uno-r3'] and r.json['rule2Violations'] == [], r.text[:200])
r = client.simulate_get('/api/board/facts', params={'board': 'arduino-uno-r3'})
check('GET /api/board/facts?board=arduino-uno-r3 → 19 cited facts', r.status_code == 200 and len(r.json['facts']) == 19, r.text[:200])
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
pages = [d for d in (tables.get('DisplayDefinition', {}) or {}).values() if getattr(d, 'pageRoute', '') == 'boards']
check('the /display/boards page is seeded as a DisplayDefinition with six configured tables',
      len(pages) == 1 and json.loads(pages[0].definition)['rows'] and sum(len(r['items']) for r in json.loads(pages[0].definition)['rows']) == 6, len(pages))
print('\n%d/%d checks passed' % (sum(results), len(results)))
sys.exit(0 if all(results) else 1)
