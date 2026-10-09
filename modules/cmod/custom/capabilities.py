"""
@module cmod.custom.capabilities

CAPABILITIES, WIDENED (hw priorities P1, AI-Notes/plans/HARDWARE_DEV_PRIORITIES.md §1/§4): a CapabilityDefinition's
per-runtime task references (`tasks_by_runtime_json`), the validator that gates its DERIVED `status` past 'planned',
and the two seeds (temp-sensor-to-os, blink-on-command) — both over the ONE existing graph `uno-sim-rig-graph`
(cmod.custom.graph_seed), cmod's FirmwareSolution `uno-sim-rig`, the Cross-Domain Solution `uno-temp-split`
(hwnocode.custom.solutions) and the backend solution `temp-analysis` (hwnocode.custom.temp_analysis) — no new graph,
no new solution, no new canvas (the plan's own "must not add"). Pure over rows already produced elsewhere, same
posture as custom/targets.py and custom/firmware.py: no manager required to validate a SEEDED capability; a manager
only to read/write the live row and its acceptance Scenario's runs.

D-ucd-12 (his ruling): person-facing text (titles, descriptions, plain_words, CLI output) calls this grouping of
tasks a Purpose, and a task may be named by several Purposes — the classes/fields/routes below keep their
CapabilityDefinition/CapabilityInstance/`capability` names unchanged.
"""
import json

GRAPH = 'uno-sim-rig-graph'
RUNTIMES = ('c-device', 'java-bridge', 'python-backend', 'typescript-browser')


def _tasks(c_device=(), java_bridge=(), python_backend=(), typescript_browser=()):
    return json.dumps({'c-device': list(c_device), 'java-bridge': list(java_bridge),
                        'python-backend': list(python_backend), 'typescript-browser': list(typescript_browser)})


SEED_CAPABILITIES = [
    {'name': 'temp-sensor-to-os', 'graph': GRAPH, 'title': 'Temperature sensor to OS',
     'goal': 'data is retrieved from a temp sensor and gets sent back over USB to the OS',
     'purpose': "TMP36 on A0, read on the device, relayed over the UART/USB link, and received on the backend as "
                "temp_c (his worked example, HARDWARE_DEV_PRIORITIES.md §0: \"ensure data is being retrieved "
                "from a temp sensor and gets sent back over usb to the OS\").",
     'required_targets': 'adc_init, adc.channel, usart_init, send.b, temp.return',
     'exposes_fields': 'temp_c',
     'tasks_by_runtime_json': _tasks(
         c_device=['%s:adc_init' % GRAPH, '%s:adc' % GRAPH, '%s:temp' % GRAPH, '%s:telemetry' % GRAPH,
                   '%s:frame' % GRAPH, '%s:send' % GRAPH],
         java_bridge=['uno-temp-split:uno-digital-twin', 'uno-temp-split:relay-in'],
         python_backend=['temp-analysis:on-temp']),
     'acceptance_scenario': 'temp-sensor-to-os-acceptance', 'instance_count': 2, 'status': 'planned', 'last_proof': '',
     'notes': 'hw priorities P1 seed 1; its two CapabilityInstance rows (targets.temperature_sensor_instances) stay unbound templates'},
    {'name': 'blink-on-command', 'graph': GRAPH, 'title': 'Blink the LED on command',
     'goal': "the OS turns the board's LED on and off on command",
     'purpose': 'A command on the exposed led_on field is relayed down to the device and toggles D13 — his worked '
                'example #2 (HARDWARE_DEV_PRIORITIES.md §1, seed example 2).',
     'required_targets': 'led.on',
     'exposes_fields': 'led_on',
     'tasks_by_runtime_json': _tasks(
         c_device=['%s:rx_pop' % GRAPH, '%s:apply' % GRAPH, '%s:led' % GRAPH],
         java_bridge=['uno-temp-split:relay-out'],
         python_backend=['temp-analysis:flag-on', 'temp-analysis:flag-off', 'temp-analysis:commit']),
     'acceptance_scenario': 'blink-on-command-acceptance', 'instance_count': 1, 'status': 'planned', 'last_proof': '',
     'notes': 'hw priorities P1 seed 2; stays planned unless its own acceptance run also passes (never copies seed 1\'s proof)'},
    {'name': 'button-clock-to-os', 'graph': '', 'title': 'Button + clock to the OS',
     'goal': 'a button on the board turns the light on and off; the board keeps a clock the OS sets; every press and '
             'every light change, with its time, reaches the OS',
     'purpose': 'UNO_CORE_DEMO_PLAN.md §1 — the core demo/proof for a Polari Hardware App: a debounced D2 button '
                'toggles D6+D13, a jumper D6->D3 independently witnesses the LED line, a software clock is synced by '
                'SET_TIME (drift measured from the 2nd sync), and every transition is queued as a ButtonClockEvent.',
     'required_targets': '',
     'exposes_fields': 'button_presses,led_on,sense_rises,sense_falls,epoch_s,drift_ms',
     'tasks_by_runtime_json': _tasks(
         c_device=['uno-button-clock:clock_tick', 'uno-button-clock:clock_set', 'uno-button-clock:led_toggle',
                   'uno-button-clock:sense_isr', 'uno-button-clock:events_queue', 'uno-button-clock:telemetry_send'],
         # java-bridge / python-backend / typescript-browser: PLANNED — ucd-0e1 built the wire contract + the
         # HardwareBridgeDefinition dict (grpcbridge.mapping_basis.SEED_BUTTON_CLOCK_BRIDGE, not a live row) and
         # ucd-0e3 built the bridge's reconnect/snapshot lifecycle; there is no Cross-Domain Solution, backend
         # relay or display yet (ucd-1, out of scope here) — named honestly as planned, never a fabricated ref
         # (the empty lists below validate trivially, the same posture typescript-browser already uses).
         java_bridge=[], python_backend=[], typescript_browser=[]),
     'acceptance_scenario': 'button-clock-to-os-acceptance', 'instance_count': 1, 'status': 'planned', 'last_proof': '',
     'notes': 'ucd-0e2 seed. java-bridge: the generated bridge (grpcbridge.mapping_basis.BUTTON_CLOCK_BRIDGE) — '
              'planned/wired, not yet a resolvable task ref. python-backend: the relay (button-clock-ledger) — '
              'planned, not built. typescript-browser: the display — planned, not built. No CGraph/FirmwareSolution '
              'for uno-button-clock exists yet (0e2b); c-device tasks are validated directly against the atoms '
              'cmod\'s annotation parser finds in apps/button_clock.c + hal.c (cmod.custom.capabilities.'
              '_project_atom_exists), never hand-listed.'},
]


def find(name, rows=None):
    return next((dict(c) for c in (rows or SEED_CAPABILITIES) if c['name'] == name), None)


#: ucd-0e2: button-clock-to-os has NO CGraph/FirmwareSolution yet (0e2b's job — explicitly out of scope here), so its
#: c-device tasks cannot be 'graph:node' refs the way temp-sensor-to-os's are. Validated directly against the atoms
#: cmod's own annotation parser finds in the app's own source + the hal it uses — 'project:atom', never hand-listed.
_PROJECT_SOURCES = {
    'uno-button-clock': ('board/custom/firmware/uno/apps/button_clock.c', 'board/custom/firmware/uno/hal.c'),
}


def _project_atom_exists(ref):
    import os
    project, _, atom = ref.partition(':')
    files = _PROJECT_SOURCES.get(project)
    if files is None:
        return False, 'unknown c-device project %r (known: %s)' % (project, ', '.join(sorted(_PROJECT_SOURCES)))
    from cmod.custom import annotation
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # modules/
    for rel in files:
        path = os.path.join(root, rel)
        try:
            text = open(path).read()
        except OSError:
            continue
        if any(a['name'] == atom for a in annotation.find(text, rel)):
            return True, ''
    return False, 'no POLARI_NODE %r found in %s' % (atom, ', '.join(files))


def _c_device_task_exists(ref):
    if ref.partition(':')[0] in _PROJECT_SOURCES:
        return _project_atom_exists(ref)
    graph, _, node = ref.partition(':')
    from cmod.custom.graph_seed import seed_graph
    rows = seed_graph(graph)
    if rows is None:
        return False, 'graph %r does not exist' % graph
    hit = any(n['instance'] == node for n in rows['nodes'])
    return hit, '' if hit else 'graph %r has no node %r' % (graph, node)


def _uno_temp_split_definition():
    from hwnocode.custom import solutions as SOLU
    return SOLU.split_app_definition()


def _temp_analysis_definition():
    from hwnocode.custom import temp_analysis as TA
    return TA.definition()


_SOLUTION_DEFS = {'uno-temp-split': _uno_temp_split_definition, 'temp-analysis': _temp_analysis_definition}


def _state_task_exists(ref, manager=None):
    sol, _, state = ref.partition(':')
    if manager is not None:
        hit = next((r for r in (manager.objectTables or {}).get('SolutionDefinition', {}).values() if getattr(r, 'name', '') == sol), None)
        if hit is not None:
            try:
                defn = json.loads(hit.definition)
            except Exception:  # noqa: BLE001
                defn = {}
            ok = any(s.get('stateName') == state for s in defn.get('stateInstances', []))
            return ok, '' if ok else 'SolutionDefinition %r (live) has no state %r' % (sol, state)
    maker = _SOLUTION_DEFS.get(sol)
    if maker is None:
        return False, 'solution %r is not a known seed (uno-temp-split, temp-analysis) and no live row of that name exists' % sol
    try:
        defn = maker()
    except Exception as e:  # noqa: BLE001
        return False, 'solution %r failed to build: %s' % (sol, e)
    ok = any(s.get('stateName') == state for s in defn.get('stateInstances', []))
    return ok, '' if ok else 'solution %r has no state %r' % (sol, state)


def task_exists(runtime, ref, manager=None):
    """(ok, why) — whether ONE task reference resolves to a real row: a c-device ref is 'graph:node' (a CGraphNode
    the project's own parse produced); a java-bridge/python-backend ref is 'solution:state' (a SolutionDefinition's
    own state — the live row if a manager has it, else the seed function that builds the same definition).
    typescript-browser has no door yet — an empty list validates trivially; a non-empty one always refuses, named,
    rather than guessing at a frontend convention that does not exist."""
    if not ref:
        return False, 'empty task reference'
    if runtime == 'c-device':
        return _c_device_task_exists(ref)
    if runtime in ('java-bridge', 'python-backend'):
        return _state_task_exists(ref, manager=manager)
    return False, 'typescript-browser has no task door yet (hw priorities P1) — nothing can resolve %r' % ref


def _target_registered(graph, port_ref, manager=None):
    """(ok, why) for ONE required target: a memory-field target (cmod.custom.targets: always lives_on='unbound' BY
    DESIGN — a struct field, not a board pin, cmod.custom.targets module docstring) is 'registered' once its
    RegisterAssignment row exists at all; every other kind needs status == 'bound' (a real RegisterAssignment, not
    merely derived-and-unbound) — never silently waved through."""
    from cmod.custom import firmware as FW
    sol = 'uno-sim-rig'
    if manager is not None:
        rows = [{'task': getattr(r, 'task', ''), 'port': getattr(r, 'port', ''), 'status': getattr(r, 'status', ''),
                 'target_kind': getattr(r, 'target_kind', '')}
                for r in (manager.objectTables or {}).get('RegisterAssignment', {}).values() if getattr(r, 'solution', '') == sol]
    else:
        rows = FW.assignments_for(graph, solution_name=sol)
    for r in rows:
        ref = ('%s.%s' % (r['task'], r['port'])) if r.get('port') else r['task']
        if ref == port_ref:
            if r.get('target_kind') == 'memory-field':
                return True, ''
            if r.get('status') == 'bound':
                return True, ''
            return False, 'target %r is %s, not bound (RegisterAssignment on %s)' % (port_ref, r.get('status') or 'missing', sol)
    return False, 'target %r is not a registered RegisterAssignment on %s' % (port_ref, sol)


def validate(cap, manager=None):
    """(ok, why) — a capability may not leave 'planned' unless every task it names resolves to a real row AND every
    required target is registered (bound, or an inherently-unbound memory-field target) — refuses NAMING the first
    missing item, never a silent pass (same posture as hwnocode.custom.cross_domain.validate)."""
    tasks = json.loads(cap.get('tasks_by_runtime_json') or '{}')
    for runtime in RUNTIMES:
        for ref in tasks.get(runtime) or []:
            ok, why = task_exists(runtime, ref, manager=manager)
            if not ok:
                return False, 'refused: %s task %r does not exist — %s' % (runtime, ref, why)
    for port_ref in [t.strip() for t in (cap.get('required_targets') or '').split(',') if t.strip()]:
        ok, why = _target_registered(cap.get('graph', ''), port_ref, manager=manager)
        if not ok:
            return False, 'refused: %s' % why
    return True, 'ok: every task resolves and every required target is registered'


def derive_status(cap, manager=None):
    """(status, last_proof, why) — DERIVED, never hand-set (HARDWARE_DEV_PRIORITIES.md §1): 'failing' when the
    validator itself refuses (a named task/target is missing); otherwise read off the LATEST ScenarioRun of the
    capability's acceptance_scenario — none yet = 'planned'; a passing twin-mode run = 'proven-on-twin'; a passing
    hardware-mode run = 'proven-on-hardware'; anything else (failed/inapplicable) = 'planned' — never a stale pass
    carried forward once a newer run disagrees. 'undetermined' runs are an ENGINE REFUSAL (acceptance.run()'s own
    posture: the proof never actually ran, so nothing was observed to pass or fail) — they are not evidence either
    way and are skipped entirely when picking the latest verdict (proof-push rule, cmod_capability_api's honest
    /prove door writes none of these any more, but older rows and other callers still can)."""
    ok, why = validate(cap, manager=manager)
    if not ok:
        return 'failing', cap.get('last_proof', ''), why
    scen = cap.get('acceptance_scenario', '')
    if not scen:
        return 'planned', '', 'no acceptance_scenario set'
    if manager is None:
        return cap.get('status', 'planned'), cap.get('last_proof', ''), 'no live manager — status read back unchanged'
    runs = sorted((r for r in (manager.objectTables or {}).get('ScenarioRun', {}).values() if getattr(r, 'scenario', '') == scen),
                  key=lambda r: getattr(r, 'ran_at', ''))
    evidential = [r for r in runs if getattr(r, 'outcome', '') != 'undetermined']
    if not evidential:
        if runs:
            return 'planned', '', ('%d ScenarioRun(s) for %r, all undetermined (engine refusal — not evidence '
                                   'either way)' % (len(runs), scen))
        return 'planned', '', 'no ScenarioRun yet for %r' % scen
    latest = evidential[-1]
    proof = 'ScenarioRun %s @ %s' % (latest.name, latest.ran_at)
    if latest.outcome != 'passed':
        return 'planned', proof, 'latest run %s: %s (%s)' % (latest.name, latest.outcome, latest.verdict_words)
    try:
        mode = json.loads(getattr(latest, 'repro_json', '{}') or '{}').get('mode', 'digital-twin')
    except Exception:  # noqa: BLE001
        mode = 'digital-twin'
    return ('proven-on-hardware' if mode == 'hardware' else 'proven-on-twin'), proof, 'latest run %s: passed' % latest.name
