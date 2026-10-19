"""cmod.custom.selftest_light — ucd-light (UNO_CORE_DEMO_PLAN.md §5i): the light test's firmware side. light.c parses into its atoms,
uno-light-graph / the Firmware Solution `uno-light` / the Hardware Binding `uno-light@arduino-uno-r3` are valid, both Purposes resolve
every task they name, no task of any seeded graph is without a Purpose (and exactly ONE Purpose is titled "Un-used components on
board"), the committed glue record shows the generated glue equivalent to light.c on the twin. Run by cmod_selftest.main()."""
import json
import re

GRAPH = 'uno-light-graph'
PRINCIPAL = ('usart_init', 'led_init', 'button_init', 'rx_pop', 'apply', 'led_toggle', 'telemetry_send')


def light_parts(check):
    def light_atoms():
        _light_atoms(check)

    def light_graph_solution_binding():
        _graph_solution_binding(check)

    def light_purposes():
        _purposes(check)

    def coverage_everywhere():
        _coverage(check)

    def glue_record():
        _glue_record(check)

    return (light_atoms, light_graph_solution_binding, light_purposes, coverage_everywhere, glue_record)


def _light_nodes():
    from cmod.custom.graph_seed import seed_graph
    return seed_graph(GRAPH)


def _light_atoms(check):
    import os
    from cmod.custom import projects as P
    m = json.load(open(P.manifest_path(P.resolve('uno'))))
    names = {a['name'] for a in m['atoms']}
    own = sorted(n for n in names if n.startswith('apps/light.') and n != 'apps/light.main')
    check('light.c parses into its atoms: boot_session_mint, led_toggle, apply_command, led_follow_state (scl), telemetry_send (+ main)',
          own == ['apps/light.apply_command', 'apps/light.boot_session_mint', 'apps/light.led_follow_state', 'apps/light.led_toggle', 'apps/light.telemetry_send']
          and 'apps/light.main' in names, own)
    rows = _light_nodes()
    atoms = [n for n in rows['nodes'] if n['kind'] == 'c-atom']
    missing = [n['atom'] for n in atoms if n['atom'].replace('uno:', '') not in names]
    check('every c-atom of uno-light-graph (%d) resolves to an atom of the manifest' % len(atoms), not missing, missing)
    inst = {n['instance'] for n in atoms}
    check('the seven atoms of the light test are all in the graph: usart init, led init, button init, rx pop, apply, led toggle, telemetry send',
          set(PRINCIPAL) <= inst, sorted(set(PRINCIPAL) - inst))
    check('no clock, no SET_TIME, no sense pin, no event queue, no ADC anywhere in the graph (its atoms, by name)',
          not any(w in n['atom'] for n in atoms for w in ('clock_set', 'clock_tick', 'sense', 'events_', 'adc', 'queue')), [n['atom'] for n in atoms])
    src = open(os.path.join(P.UNO_ROOT, 'apps', 'light.c')).read()
    check('light.c has ONE command (SET_LED): no SET_TIME / SNAPSHOT in the source; its sense code (smp-1) exists only inside `#if HAL_INT1` blocks, so the graph\'s sense-less app (variant uno-light-unsensed) compiles none of it',
          'SET_LED' in src and 'SET_TIME' not in src and 'SNAPSHOT' not in src
          and all(m.start() > 0 for m in re.finditer('hal_sense', src))
          and len(re.findall(r'hal_sense', re.sub(r'#if HAL_INT1.*?#endif', '', src, flags=re.S))) == 0)


def _graph_solution_binding(check):
    from cmod.custom import firmware as FW, binding as BND
    from cmod import cmod_seed as S
    rows = _light_nodes()
    from cmod.custom import glue as GL
    from cmod.custom import graph as GR
    ctx = GL.context(rows['graph'])
    model = GR.resolve(rows, ctx)
    check('uno-light-graph resolves (the graph validator accepts it): %d nodes' % len(rows['nodes']), bool(model), '')
    fs = S.LIGHT_FIRMWARE_ROWS[0]
    ok, why, _ = FW.validate(fs, manager=None)
    check('FirmwareSolution uno-light validates (board arduino-uno-r3 resolves)', ok and fs['validation'] == 'ok', why)
    b = next(x for x in S.BINDING_ROWS if x['name'] == 'uno-light@arduino-uno-r3')
    claims = json.loads(b['claims_refs_json'])
    want = {'PinClaim:uno-light:D0', 'PinClaim:uno-light:D1', 'PinClaim:uno-light:D2', 'PinClaim:uno-light:D6'}
    check('HardwareBinding uno-light@arduino-uno-r3 is valid and claims D2 (INT0 button), D6 (the light), D0/D1 (the serial link)',
          b['status'] == 'valid' and want <= set(claims) and not any(c.endswith(':D3') or c.endswith(':D13') for c in claims), (b['status'], b['why'], claims))
    check('D2 carries INT0 in the register map (EICRA/EIMSK settings) and no INT1', any('EIMSK.INT0' in r for r in json.loads(b['settings_refs_json']))
          and not any('INT1' in r for r in json.loads(b['settings_refs_json'])))


def _purposes(check):
    from cmod.custom import capabilities as CAP
    for name in ('light-from-polari', 'light-from-button'):   # fgm-1: both retired, still valid and still naming their (now shared) scenario
        c = CAP.find(name)
        ok, why = CAP.validate(c)
        check('Purpose %s (retired) still resolves every task it names (c-device, bridge, backend)' % name, ok, why)
        check('Purpose %s names a goal and its acceptance scenario' % name, bool(c['goal']) and c['acceptance_scenario'] == name + '-acceptance'
              and c['lifecycle'] == 'retired')
    from firmwarefaults.custom import acceptance as ACC
    kinds = {n: [s['kind'] for s in ACC.steps_of(n)] for n in ('light-from-button-acceptance', 'light-from-polari-acceptance')}
    sc = [ACC.find(n) for n in kinds]
    check('both acceptance Scenarios are kind=acceptance and built from the EXISTING step kinds (pin-at / assert-field-arrival / assert-command-echo)',
          all(s and s['kind'] == 'acceptance' for s in sc) and all(set(k) <= {'pin-at', 'assert-field-arrival', 'assert-command-echo'} and k for k in kinds.values())
          and all(st['forcible'] for n in kinds for st in ACC.steps_of(n)), kinds)
    check('light-from-polari names the bridge relay-out and light-toggle; light-from-button names the bridge relay-in',
          'uno-light:relay-out' in json.loads(CAP.find('light-from-polari')['tasks_by_runtime_json'])['java-bridge']
          and 'uno-light:relay-in' in json.loads(CAP.find('light-from-button')['tasks_by_runtime_json'])['java-bridge'])
    summ = CAP.purpose_summary(GRAPH)
    check('purpose_summary over uno-light-graph: exactly the four Purposes decide the proof now that initialization has a Scenario (fsc-0b; planned until a run is recorded); the retired pair never does',
          summ['purposes_total'] == 4 and summ['proof_status'] == 'planned', summ['proof_why'])
    sim = CAP.purpose_summary('uno-sim-rig-graph')
    check('the plumbing/un-used Purposes of the sample graphs are LISTED but never decide the proof (sim-rig: 2 deciding of 5 listed)',
          sim['purposes_total'] == 2 and len(sim['purposes']) == 5, (sim['purposes_total'], len(sim['purposes'])))


def _coverage(check):
    from cmod.custom import capabilities as CAP
    from cmod.custom.graph_seed import SEED_GRAPHS, seed_graph
    for g in SEED_GRAPHS:
        nodes = {n['instance'] for n in seed_graph(g['name'])['nodes']}
        named = set()
        for p in CAP.purposes_for_graph(g['name']):
            named |= {r.rpartition(':')[2] for r in json.loads(p['tasks_by_runtime_json']).get('c-device', []) if r.rpartition(':')[0] == g['name']}
        check('every node of %s is named by at least one Purpose (%d nodes)' % (g['name'], len(nodes)), nodes <= named, sorted(nodes - named))
    check('every seeded Purpose validates (all task refs resolve)', all(CAP.validate(c)[0] for c in CAP.SEED_CAPABILITIES),
          [c['name'] for c in CAP.SEED_CAPABILITIES if not CAP.validate(c)[0]])
    unused = [c for c in CAP.SEED_CAPABILITIES if c['title'] == 'Un-used components on board']
    check('exactly ONE Purpose is titled "Un-used components on board", and it says why (the board offers it, no Purpose uses it)',
          len(unused) == 1 and 'pwm_init' in unused[0]['tasks_by_runtime_json'] and unused[0]['goal'], [u['name'] for u in unused])
    check('the Purpose goals answer "why is this in this firmware" in plain words: none empty, none naming a plan file',
          all(c['goal'] and '.md' not in c['goal'] for c in CAP.SEED_CAPABILITIES))


def _glue_record(check):
    from cmod.custom import glue as GL
    rec = GL.load_record(GRAPH) or {}
    pr = rec.get('proof') or {}
    check('the committed glue record of uno-light-graph: built by make alone, and the generated glue is EQUIVALENT to light.c on the twin '
          '(%s frames, both directions)' % pr.get('frames_compared'),
          bool(rec.get('build')) and pr.get('equivalent') is True and pr.get('frames_compared', 0) >= 8 and pr.get('n_differences') == 0, pr.get('differences'))
