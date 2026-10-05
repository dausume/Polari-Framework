"""In-process live-boot PROBE of hn-0 (HARDWARE_NOCODE_PLAN.md §7): boot the REAL polariServer with hwnocode (+ cmod, board, grpcbridge
and what they need) and hit its routes — the guarded imports, defClassList, the seeds (the HardwareSolution, its placements, the two
SolutionDefinitions, the trigger, the binding, the graph), the page, the node kinds on GET /stateSpaceClasses with their palette, the
hn-split compiler row, and the /api/hwnocode routes. No engine, no twin (that is tests/hwnocode_probe.py).

  cd /tmp/somewhere && PYTHONPATH=<fw>:<fw>/modules python3 <fw>/tests/hwnocode_liveboot_probe.py [--all-modules]
  --all-modules: POLARI_MODULES unset — every module boots (the core edits hn-0 made are exercised against all of them)
"""
import json
import os
import sys
import time

if '--all-modules' in sys.argv:
    os.environ.pop('POLARI_MODULES', None)
else:
    os.environ['POLARI_MODULES'] = 'hwmap,grpcbridge,board,cmod,hwnocode'
os.environ.setdefault('POLARI_DB_BACKEND', 'sqlite')
FRAMEWORK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, FRAMEWORK); sys.path.insert(0, os.path.join(FRAMEWORK, 'modules')); sys.path.insert(0, os.path.join(FRAMEWORK, 'tests'))
results = []


def check(label, cond, extra=''):
    results.append(bool(cond)); print(('PASS' if cond else 'FAIL') + f': {label}' + (f'  [{extra}]' if extra and not cond else ''), flush=True)


def main():
    from board_probe_boot import boot
    from falcon import testing
    t0 = time.time()
    m = boot(FRAMEWORK)
    boot_s = time.time() - t0
    t = m.objectTables
    n = lambda c: len(t.get(c) or {})  # noqa: E731
    check('booted in %.1f s (%s); hwnocode classes registered: %s' % (boot_s, 'ALL modules' if '--all-modules' in sys.argv else os.environ['POLARI_MODULES'],
          ', '.join(c for c in ('HardwareSolution', 'HardwareNodePlacement', 'HardwareSubgraph', 'HardwareInterface', 'CAtom', 'SimRigTempSample',
                                'SimRigTempDerived') if c in m.objectTypingDict)),
          all(c in m.objectTypingDict for c in ('HardwareSolution', 'HardwareNodePlacement', 'HardwareSubgraph', 'HardwareInterface', 'CAtom',
                                                 'SimRigTempSample', 'SimRigTempDerived')))
    check('seeds: HardwareSolution %d, HardwareNodePlacement %d, the canvas + backend SolutionDefinitions, the trigger, the binding, the graph'
          % (n('HardwareSolution'), n('HardwareNodePlacement')),
          n('HardwareSolution') == 1 and n('HardwareNodePlacement') == 27
          and {'uno-temp-split', 'uno-temp-split.backend'} <= {r.name for r in (t.get('SolutionDefinition') or {}).values()}
          and any(r.name == 'uno-temp-split-on-temp' for r in (t.get('EventTrigger') or {}).values())
          and any(r.name == 'uno-temp-split/SimRigState/0' for r in (t.get('HardwareInterfaceBinding') or {}).values())
          and any(r.name == 'hwnocode-uno-temp-split-temp' for r in (t.get('GraphDefinition') or {}).values()))
    check('the page /display/hardware-solutions is seeded', any(getattr(r, 'pageRoute', '') == 'hardware-solutions' for r in (t.get('DisplayDefinition') or {}).values()))
    check('the GraphCompilerDefinition row hn-split is seeded (domain hwnocode)',
          any(r.name == 'hn-split' and r.domain == 'hwnocode' for r in (t.get('GraphCompilerDefinition') or {}).values()))
    c = testing.TestClient(m.polServer.falconServer)
    r = c.simulate_get('/stateSpaceClasses')
    kinds = {x['className']: x['palette']['nodeKind'] for x in r.json.get('stateSpaceClasses', []) if x.get('palette')}
    check('GET /stateSpaceClasses: %d classes, the hardware node kinds with palette metadata %s' % (r.json.get('count', 0), kinds),
          r.status_code == 200 and kinds == {'HardwareSubgraph': 'hardware-subgraph', 'HardwareInterface': 'hw-interface', 'CAtom': 'c-atom'})
    r = c.simulate_get('/api/hwnocode')
    check('GET /api/hwnocode → uno-temp-split, 3 node kinds all on the palette', r.status_code == 200 and r.json['solutions'][0]['name'] == 'uno-temp-split'
          and all(k['on_palette'] for k in r.json['node_kinds']), r.text[:300])
    r = c.simulate_get('/api/hwnocode/solutions/uno-temp-split/placement')
    check('GET …/placement on the live rows → %s' % r.json.get('summary'), r.status_code == 200 and r.json.get('summary') == 'twin 19, bridge 1, backend 6, browser 1')
    r = c.simulate_get('/api/hwnocode/solutions/uno-temp-split/render')
    check('GET …/render → the board half unchanged vs cmod-1 (files_sha256 %s…)' % (r.json.get('board_half') or {}).get('files_sha256', '')[:12],
          r.status_code == 200 and r.json['board_half']['unchanged_output'])
    r = c.simulate_get('/api/hwnocode/solutions/uno-temp-split/suggest')
    check('GET …/suggest → bare-c, applied false', r.status_code == 200 and r.json['suggested'] == 'bare-c' and r.json['applied'] is False)
    r = c.simulate_get('/HardwareNodePlacement')
    check('CRUDE GET /HardwareNodePlacement answers (configured tables read it)', r.status_code == 200, r.status_code)
    # rtfix A: Runtime (demo-4b) must be registered (defClassList + feature_imports)
    # and its 6 rows seeded — the known new-treeObject-class gotcha hit here too.
    check('Runtime registered (defClassList/feature_imports)', 'Runtime' in m.objectTypingDict)
    r = c.simulate_get('/Runtime')
    rows = []
    if r.status_code == 200 and isinstance(r.json, list) and r.json and r.json[0].get('Runtime'):
        for block in r.json[0]['Runtime']:
            rows.extend(block.get('data') or [])
    names = sorted(x.get('name') for x in rows)
    check('GET /Runtime -> 6 rows %s' % names, r.status_code == 200 and n('Runtime') == 6 and len(rows) == 6
          and set(names) == {'python-backend', 'typescript-browser', 'c-device', 'c-twin', 'java-bridge', 'javafx-native'},
          'status=%s body=%s' % (r.status_code, r.text[:300]))
    # selfix 2026-10-05: the renamed state + its purposes on the LIVE payload (not just the seed dict in-process) — his
    # ask ("call it uno-digital-twin so it is clear" + the 8 states' plain-words purposes) must survive a real boot.
    r = c.simulate_get('/api/hwnocode/solutions/uno-temp-split/placement')
    live_nodes = {row['node']: row for row in (r.json or {}).get('nodes', []) if row.get('layer') == 'solution'}
    check('the live placement payload carries the renamed state `uno-digital-twin` (not `uno-twin`) as the bridge node',
          'uno-digital-twin' in live_nodes and 'uno-twin' not in live_nodes and live_nodes['uno-digital-twin']['placement'] == 'bridge',
          sorted(live_nodes))
    missing_purpose = [name for name, row in live_nodes.items() if not row.get('purpose')]
    check('every live solution-layer node (all 8 states) carries its purpose sentence', not missing_purpose, missing_purpose)
    hwi_binding = next((row for row in (t.get('HardwareInterfaceBinding') or {}).values() if row.name == 'uno-temp-split/SimRigState/0'), None)
    check('the live HardwareInterfaceBinding row is bound to the renamed object `uno-digital-twin`',
          hwi_binding is not None and hwi_binding.object_name == 'uno-digital-twin')
    hs_row = next(iter((t.get('HardwareSolution') or {}).values()), None)
    check('the live HardwareSolution row shows the HARDWARE_MODE knob (default digital-twin) and its route report',
          hs_row is not None and hs_row.hardware_mode == 'digital-twin' and 'pty' in hs_row.route_report)
    print('\n%d/%d hwnocode live-boot checks passed' % (sum(results), len(results)))
    return 0 if all(results) else 1


if __name__ == '__main__':
    sys.exit(main())
