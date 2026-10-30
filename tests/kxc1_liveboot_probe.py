"""In-process live-boot PROBE of kxc-1 (KICAD_INTERCHANGE_PLAN.md): boot the REAL polariServer with pcb (+ board), POST the complex_hierarchy demo to
/api/pcb/ingest and check the three new classes are typed and stored: one KiCadArtifact per file, a KiCadCoverage row per element kind, 119 SchematicSymbol
rows (both instances of the reused sheet), BoardNet volts unknown. The engine step refuses here (no kicad-cli) - returned, not raised.
Run from a THROWAWAY working directory (the boot writes its sqlite DB into ./data/ of the cwd):
  cd /tmp/somewhere && PYTHONPATH=<framework>:<framework>/modules python3 <framework>/tests/kxc1_liveboot_probe.py
"""
import os
import sys
os.environ['POLARI_MODULES'] = 'techtree,hwmap,hardwareapps,islemesh,board,pcb'
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
for cls in ('KiCadArtifact', 'KiCadCoverage', 'SchematicSymbol'):
    check('class %s is typed after boot' % cls, cls in typed)
demo = os.path.join(FRAMEWORK, 'modules', 'pcb', 'custom', 'upstream', 'kicad-demos-9.0.2', 'complex_hierarchy')
r = client.simulate_post('/api/pcb/ingest', json={'path': demo, 'board': 'complex_hierarchy'})
st = (r.json or {}).get('stored', {})
check('POST /api/pcb/ingest complex_hierarchy -> 201, stored 17 KiCadArtifact, 119 SchematicSymbol, a KiCadCoverage row per element kind',
      r.status_code == 201 and st.get('KiCadArtifact') == 17 and st.get('SchematicSymbol') == 119 and st.get('KiCadCoverage', 0) > 30, (r.status_code, st, r.text[:300]))
n = lambda c: len(tables.get(c, {}) or {})  # noqa: E731
check('the rows are in the tables', (n('KiCadArtifact'), n('SchematicSymbol')) == (17, 119), (n('KiCadArtifact'), n('SchematicSymbol')))
nets = [o for o in (tables.get('BoardNet') or {}).values() if getattr(o, 'board', '') == 'complex_hierarchy']
check('ingested BoardNet rows carry volts -1 (unknown)', nets and all(getattr(o, 'volts', None) == -1.0 for o in nets), [getattr(o, 'volts', None) for o in nets[:3]])
u = [o for o in (tables.get('SchematicSymbol') or {}).values() if getattr(o, 'ref', '') in ('U201', 'U301')]
check('the dual op-amp in both sheet instances: U201 + U301, two units each, distinct instance paths',
      len(u) == 4 and len({getattr(o, 'instance_path', '') for o in u}) == 2, [(getattr(o, 'ref', ''), getattr(o, 'unit', '')) for o in u])
check('bob-0: the ingest stored the PCB\'s footholds (connector pads P101..P302) as BoardFoothold rows of kind layers',
      st.get('BoardFoothold') == 12 and n('BoardFoothold') == 12, (st.get('BoardFoothold'), n('BoardFoothold')))
r = client.simulate_get('/api/board/footholds/layers/complex_hierarchy')
check('bob-0: GET /api/board/footholds/layers/complex_hierarchy serves those stored rows (12, nodes by net)', r.status_code == 200 and r.json['count'] == 12, r.text[:300])
r = client.simulate_get('/api/board/footholds/datasheet/arduino-uno-r3')
check('bob-0: GET /api/board/footholds/datasheet/arduino-uno-r3 derives 38 header-pin footholds from the live rows', r.status_code == 200 and r.json['count'] == 38, r.text[:300])
r = client.simulate_get('/api/board/footholds/geometry/breadboard-half')
check('bob-0: GET /api/board/footholds/geometry/breadboard-half -> 400 footholds, 64 nodes', r.status_code == 200 and (r.json['count'], r.json['nodes']) == (400, 64), r.text[:300])
r = client.simulate_get('/api/board/footholds/geometry/pcb')
check('bob-0: the reserved pcb model is refused in words (404)', r.status_code == 404 and 'no drawable geometry' in r.json['error'], r.text[:300])
check('kxc-2: the ingest stored the schematic\'s own nets - 52 SchematicNet, 164 NetEndpoint (KiCad\'s own netlist has the same 52 nets / 164 pins)',
      (st.get('SchematicNet'), st.get('NetEndpoint')) == (52, 164), (st.get('SchematicNet'), st.get('NetEndpoint')))
for cls in ('SchematicNet', 'NetEndpoint'):
    check('class %s is typed after boot' % cls, cls in typed)
r = client.simulate_post('/api/board/benches/home-bench/pcbs', json={'pcb': 'complex_hierarchy', 'label': 'the KiCad demo board'})
check('bob-1: POST /api/board/benches/home-bench/pcbs puts the ingested PCB on the bench (201)', r.status_code == 201, r.text[:300])
r = client.simulate_get('/api/board/benches/home-bench/all-boards')
pcb = [x for x in (r.json or {}).get('rows', []) if x['board_kind'] == 'pcb']
check('bob-1: GET /api/board/benches/home-bench/all-boards lists it beside the dev boards and breadboards - one pcb row, layers definition, its 12 footholds',
      r.status_code == 200 and len(pcb) == 1 and pcb[0]['definition_kind'] == 'layers' and pcb[0]['footholds'] == 12 and r.json['kinds'].get('dev-board') == 4, r.text[:400])
r = client.simulate_post('/api/board/benches/home-bench/pcbs', json={'pcb': 'never-ingested'})
check('bob-1: a PCB never ingested is refused in words (404)', r.status_code == 404 and 'ingest it first' in r.json['error'], r.text[:200])
r = client.simulate_get('/api/board/details/layers/complex_hierarchy/nets')
check('bob-3: GET /api/board/details/layers/complex_hierarchy/nets -> the 52 nets Polari worked out', r.status_code == 200 and r.json['count'] == 52, r.text[:200])
r = client.simulate_get('/api/board/details/layers/complex_hierarchy/layers')
check('bob-3: .../layers -> the PCB\'s layer stack (copper, mask, silk ...)', r.status_code == 200 and any(x['layer'] == 'F.Cu' for x in r.json['rows']), r.text[:200])
check('kxc-4: the ingest stored the PCB complete - 165 PcbPad, 49 NetGeometry, 166 PcbZone rows', (st.get('PcbPad'), st.get('NetGeometry'), st.get('PcbZone')) == (165, 49, 166),
      (st.get('PcbPad'), st.get('NetGeometry'), st.get('PcbZone')))
r = client.simulate_get('/api/board/benches/home-bench/all-boards')
ids = {x['definition']: x['id'] for x in r.json['rows']}
pcb_id, bud_id = ids['complex_hierarchy'], ids['bud-bb-32650-w']
r = client.simulate_post('/api/board/benches/home-bench/connections', json={'connections': [
    {'from_board': 'boards_json#1', 'from_foothold': 'POWER:5', 'to_board': bud_id, 'to_foothold': 'r1a', 'kind': 'wire', 'colour': 'red'},
    {'from_board': 'boards_json#1', 'from_foothold': 'POWER:6', 'to_board': bud_id, 'to_foothold': 'r1b', 'kind': 'wire', 'colour': 'black'},
    {'from_board': 'boards_json#1', 'from_foothold': 'DIGITAL_L:7', 'to_board': pcb_id, 'to_foothold': 'P101:1', 'kind': 'wire'}]})
check('bob-2: POST /api/board/benches/home-bench/connections stores three wires (UNO 5V and GND into one BUD strip, UNO D6 to the PCB pad P101:1)',
      r.status_code == 201 and len(r.json['added']) == 3, r.text[:300])
r = client.simulate_get('/api/board/benches/home-bench/nets')
kinds = [f['kind'] for n in (r.json or {}).get('nets', []) for f in n['findings']]
check('bob-2: GET /api/board/benches/home-bench/nets -> the UNO 5 V and GND on one breadboard strip is a supply-to-ground finding; the nets cross dev board, '
      'breadboard and the KiCad PCB', r.status_code == 200 and 'supply-to-ground' in kinds and any(pcb_id in n['boards'] for n in r.json['nets']), r.text[:400])
r = client.simulate_post('/api/board/benches/home-bench/connections', json={'connections': [{'from_board': 'boards_json#1', 'from_foothold': 'NOPE', 'to_board': bud_id, 'to_foothold': 'r1a'}]})
check('bob-2: a wire to a foothold that does not exist is refused (422) and nothing is stored', r.status_code == 422 and 'no foothold' in r.json['error'], r.text[:200])
r = client.simulate_post('/api/pcb/export/bench/home-bench')
d = (r.json or {}).get('design') or {}
check('kxc-5: POST /api/pcb/export/bench/home-bench builds the design from the bench (UNO headers + the PCB connectors as generic KiCad headers, the wires as '
      'nets) and, with no KiCad libraries on this host, refuses the writing in words (503) - or writes it where KiCad is installed',
      (r.status_code == 503 and 'no KiCad libraries' in r.json.get('refused', '') and any(c['lib_id'].startswith('Connector_Generic:') for c in d.get('components', [])))
      or (r.status_code == 200 and r.json['text'].startswith('(kicad_sch')), r.text[:300])
r = client.simulate_get('/api/board/details/layers/complex_hierarchy/copper')
cu = (r.json or {}).get('rows', [])
check('bob-3b: GET /api/board/details/layers/complex_hierarchy/copper -> 49 nets, each with its DC resistance from the copper (stackup thickness, IEC 60028 rho)',
      r.status_code == 200 and len(cu) == 49 and all(x['dc_ohm_upper_bound'] > 0 for x in cu if x['segments']), r.text[:300])
r = client.simulate_get('/KiCadCoverage')
check('CRUDE GET /KiCadCoverage answers 200', r.status_code == 200, r.status_code)
print('\n%d/%d checks passed' % (sum(results), len(results)))
sys.exit(0 if all(results) else 1)
