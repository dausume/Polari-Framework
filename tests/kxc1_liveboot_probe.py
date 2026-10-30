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
r = client.simulate_get('/KiCadCoverage')
check('CRUDE GET /KiCadCoverage answers 200', r.status_code == 200, r.status_code)
print('\n%d/%d checks passed' % (sum(results), len(results)))
sys.exit(0 if all(results) else 1)
