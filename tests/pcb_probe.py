"""pcb-0 PROBE: an in-process live boot of the REAL polariServer with `board` + `pcb` enabled (brd-bo unchanged), then the
REAL ingest/ERC/DRC/exports through the kicad-cli worker:

  PCB_ENGINES_URL=http://192.168.0.24:9860   `pol pcb ingest` on the stored ecc83-pp board (GPL-2.0-or-later,
                                             custom/upstream/kicad-demos-9.0.2/) runs every check/export on the WORKER
                                             (never locally — his rule: no KiCad on the editing box) and the rows land
                                             through POST /api/pcb/ingest; the UNO shield schematic skeleton (brd-bo's
                                             rows) is rendered and ERC'd through POST /api/pcb/render/uno-shield; a
                                             second ingest proves the exports are byte-stable (same shas).

A worker that does not answer /capability is SKIPPED and said so honestly — never a local fallback (no kicad-cli runs on
this box either way: the rung is always `remote` or the probe skips).

    cd polari-framework && PCB_ENGINES_URL=http://192.168.0.24:9860 PYTHONPATH=.:modules python3 tests/pcb_probe.py
"""
import json
import os
import sys

os.environ['POLARI_MODULES'] = 'techtree,hwmap,hardwareapps,islemesh,grpcbridge,board,pcb'
os.environ.setdefault('POLARI_DB_BACKEND', 'sqlite')
FW = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [FW, os.path.join(FW, 'modules')]
ECC83 = os.path.join(FW, 'modules', 'pcb', 'custom', 'upstream', 'kicad-demos-9.0.2', 'ecc83')
from falcon import testing  # noqa: E402
sys.path.insert(0, os.path.join(FW, 'tests'))
from board_probe_boot import boot  # noqa: E402 — the framework as cwd for the boot, the DB in ./data here
manager = boot(FW)
client = testing.TestClient(manager.polServer.falconServer)
results = []


def check(label, cond, extra=''):
    results.append(bool(cond))
    print(('PASS' if cond else 'FAIL') + ': ' + label + (('  [%s]' % extra) if extra and not cond else ''), flush=True)


tables = manager.objectTables
typed = {(k if isinstance(k, str) else getattr(k, '__name__', str(k))) for k in manager.objectTypingDict.keys()} \
        | {getattr(v, 'className', '') for v in manager.objectTypingDict.values()}
n = lambda c: len(tables.get(c, {}) or {})  # noqa: E731

# ---- boot wiring: pcb's classes typed, the fab rules seeded, board untouched beside it
for cls in ('Part', 'Symbol', 'Footprint', 'LandPattern', 'Schematic', 'SchematicSheet', 'PcbBoard', 'Placement', 'Route',
            'DrcResult', 'FabricationExport', 'FabRuleSet', 'FabRule'):
    check('pcb-0: class %s is typed after boot' % cls, cls in typed)
check('pcb-0: the 20 DKRed FabRule rows + 1 FabRuleSet row are seeded (code-owned)', n('FabRule') == 20 and n('FabRuleSet') == 1)
check('brd-bo UNCHANGED: 33 devices, 45 SoC pins, 32 board pins still seed beside pcb', n('BoardDefinition') == 33
      and n('SocPin') == 45 and n('BoardPin') == 32)
r = client.simulate_get('/api/board/arduino-uno-r3/pins')
check('brd-bo UNCHANGED: GET /api/board/arduino-uno-r3/pins still answers (D6 = PWM_LED)', r.status_code == 200
      and next(p for p in r.json['pins'] if p['canonical'] == 'D6')['net'] == 'PWM_LED', r.text[:200])
pages = {d.pageRoute for d in (tables.get('DisplayDefinition', {}) or {}).values()}
check('pcb-0: the four pages are seeded (board-schematic, board-layout, board-bom, board-fab)',
      {'board-schematic', 'board-layout', 'board-bom', 'board-fab'} <= pages, pages)

# ---- the engines ladder (no worker required to ANSWER this one)
r = client.simulate_get('/api/pcb/engines')
check('GET /api/pcb/engines answers the ladder (never runs anything)', r.status_code == 200 and r.json['knob'] == 'PCB_ENGINES_URL', r.text[:300])

url = os.environ.get('PCB_ENGINES_URL', '')
if not url:
    print('\nSKIPPED: PCB_ENGINES_URL is not set — the real ingest/ERC/DRC/export checks below did not run '
          '(set it to the isle-core worker, e.g. http://192.168.0.24:9860)')
else:
    import urllib.request
    try:
        with urllib.request.urlopen('%s/capability' % url, timeout=5) as resp:
            cap = json.load(resp)
        reachable = bool((cap.get('engines') or {}).get('kicad-cli', {}).get('available'))
    except Exception as e:  # noqa: BLE001
        cap, reachable = None, False
        print('\nSKIPPED: %s/capability did not answer (%s) — no local fallback' % (url, e))
    if reachable:
        check('the worker reports kicad-cli available', reachable, cap)
        r = client.simulate_post('/api/pcb/ingest', body=json.dumps({'path': ECC83, 'board': 'ecc83-pp'}),
                                 headers={'Content-Type': 'application/json'})
        check('POST /api/pcb/ingest on the real ecc83-pp board → 201, no refusal, rows stored',
              r.status_code == 201 and not r.json['refused'] and r.json['stored'].get('Part', 0) == 11, r.text[:400])
        check('the real schematic/board netlists agree (kicad-cli\'s own round trip)',
              r.json.get('netlistVsBoard', {}).get('equal') is True, r.json.get('netlistVsBoard'))
        check('eleven Part, eight Symbol, six Footprint, fifteen Placement, thirteen Route rows landed',
              (n('Part'), n('Symbol'), n('Footprint'), n('Placement'), n('Route')) == (11, 8, 6, 15, 13))
        drc = [d for d in (tables.get('DrcResult', {}) or {}).values() if d.board == 'ecc83-pp']
        check('DrcResult rows include a clean ERC and the DKRed fab-rule checks', any(d.kind == 'erc' and d.severity == 'none' for d in drc)
              and any(d.kind == 'fab-rule' for d in drc), len(drc))
        exports = [e for e in (tables.get('FabricationExport', {}) or {}).values() if e.board == 'ecc83-pp']
        check('thirty-four FabricationExport rows (protel + kicad-gbr gerbers, drill+map, pos/bom/netlist, 7 layer SVGs, STEP, job)',
              len(exports) == 34, len(exports))
        by_acc = {}
        for e in exports:
            by_acc[e.accepted] = by_acc.get(e.accepted, 0) + 1
        check('the fab naming verdict is honest: some yes, some no, some discrepancy (never all-accepted)',
              by_acc.get('yes', 0) > 0 and by_acc.get('no', 0) > 0 and by_acc.get('discrepancy', 0) > 0, by_acc)
        one = next(e for e in exports if e.export_set == 'protel' and e.kind == 'gerber')
        r2 = client.simulate_get('/api/pcb/artifacts/ecc83-pp/%s' % one.artifact_path.split('/', 1)[1])
        import hashlib
        check('GET /api/pcb/artifacts/<board>/<path> serves the exact bytes the row\'s sha256 names',
              r2.status_code == 200 and hashlib.sha256(r2.content).hexdigest() == one.sha256, r2.status_code)

        # byte-stability: ingest again, the sha of every export must be identical
        first_shas = {e.name: e.sha256 for e in exports}
        r = client.simulate_post('/api/pcb/ingest', body=json.dumps({'path': ECC83, 'board': 'ecc83-pp'}),
                                 headers={'Content-Type': 'application/json'})
        second = {e.name: e.sha256 for e in (tables.get('FabricationExport', {}) or {}).values() if e.board == 'ecc83-pp'}
        check('byte-stable: a second ingest (frozen clock) reproduces every export\'s sha256 exactly',
              r.status_code == 201 and second == first_shas, len(second))

        # the UNO shield schematic skeleton, rendered and ERC'd through the worker
        r = client.simulate_post('/api/pcb/render/uno-shield', body='{}', headers={'Content-Type': 'application/json'})
        check('POST /api/pcb/render/uno-shield → the skeleton renders, the worker runs sch erc on it',
              r.status_code == 201 and r.json['components'] == 7 and 'sheets' in r.json['erc'], r.text[:300])
        check('ERC is reported honestly: unconnected UNO header pins ERC flags are not hidden',
              r.json['ercViolations'] > 0 and r.json['unconnectedPins'] > 0, (r.json.get('ercViolations'), r.json.get('unconnectedPins')))
        sch = next((s for s in (tables.get('Schematic', {}) or {}).values() if s.board == 'uno-shield'), None)
        check('the Schematic row is stored with origin=rendered', sch is not None and sch.origin == 'rendered')

print('\n%d/%d checks passed' % (sum(results), len(results)))
sys.exit(0 if all(results) else 1)
