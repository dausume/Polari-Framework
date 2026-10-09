"""
@module hwnocode.custom.seed_rows

The code-owned rows of hn-0, as dicts (hwnocode_seed upserts them): the HardwareSolution `uno-temp-split`, its canvas
SolutionDefinition + the backend half hn-split derives, the AnalysisDefinition + EventTrigger that run the backend half per frame,
the HardwareInterfaceBinding that IS its hw-interface node (a grpcbridge row: SimRigState `uno-digital-twin` ↔ the UNO twin's pty
— or the detected board's serial port in hardware mode — on bridge `uno-temp-split`), and one HardwareNodePlacement row per node.
Derived fields come from the placement (pure Python — no engine) and the split's committed record
(custom/splits/<solution>.json); nothing is rendered or built at boot.
"""
import json

from hwnocode.custom import solutions as S

SOLUTIONS = [{
    'name': S.SOLUTION, 'title': 'UNO temperature, split across board, bridge, backend and screen',
    'purpose': ('Variant h over the existing peripheral (variant b): the sim-rig firmware (a cmod graph, byte-identical to the shipped '
                'app) sends SimRigState frames at 10 Hz; the bridge applies them to the uno-digital-twin row; a backend solution keeps '
                'a moving average of temp_c and flags it above a threshold on SimRigTempDerived; /display/hardware-solutions charts '
                'both. A PUT of led_on on the row rides the Commands stream back down to the firmware.'),
    'variant_kind': 'h', 'solution': S.SOLUTION, 'backend_solution': '%s.backend' % S.SOLUTION, 'cgraph': S.CGRAPH,
    'board_definition': S.BOARD, 'board_instance': S.ROUTE['board_instance'], 'interface': S.BINDING, 'displays': S.DISPLAY,
    'firmware_runtime': 'bare-c', 'hardware_mode': S.ROUTE['mode'], 'route_report': S.ROUTE['route_report'], 'notes': ''}, {
    # ucd-1 (UNO_CORE_DEMO_PLAN.md §3): the core demo's OWN HardwareSolution row, so `pol hwnocode solutions` /
    # /display/hardware-solutions list it beside uno-temp-split. Its `cgraph` names the FirmwareSolution's graph
    # ucd-0e2b has not built yet (its Firmware Run state is deliberately 'planned', solutions.py), so placement
    # REFUSES, named — the same honest-refusal path uno-temp-split would take if its own cgraph vanished; this row
    # never pretends the firmware half runs. The backend half (button-clock-ledger + the cross-domain canvas itself)
    # is NOT derived through hn-split's placement — hand-built (solutions.py's button_clock_backend_definition) and
    # appended unconditionally below, the same way temp-analysis is appended for uno-temp-split.
    'name': S.BC_SOLUTION, 'title': 'UNO button + clock, the core demo (ucd arc)',
    'purpose': ('UNO_CORE_DEMO_PLAN.md: a button on D2 toggles an LED on D6; a jumper D6→D3 lets the firmware witness its OWN LED '
                'line (sense_rises/sense_falls); a software clock is kept and synced from the host (SET_TIME). ButtonClockState is '
                'upserted (latest) and ButtonClockEvent appended (one per edge, retention-bounded) by the bridge; the backend '
                'solution button-clock-ledger computes presses_per_min and checks the sense/press/LED invariant onto '
                'ButtonClockDerived; /display/uno-core-demo tables + charts both. Firmware Run is PLANNED (ucd-0e2b not built).'),
    'variant_kind': 'h', 'solution': S.BC_SOLUTION, 'backend_solution': S.BC_BACKEND_SOLUTION, 'cgraph': '%s-graph' % S.BC_SOLUTION,
    'board_definition': S.BOARD, 'board_instance': S.BC_ROUTE['board_instance'], 'interface': S.BC_BINDING, 'displays': S.BC_DISPLAY,
    'firmware_runtime': 'bare-c', 'hardware_mode': S.BC_ROUTE['mode'], 'route_report': 'Firmware Run is planned (ucd-0e2b): '
    'FirmwareSolution %r does not exist yet; this row\'s own placement refuses honestly rather than assume it.' % S.BC_FIRMWARE_SOLUTION,
    'notes': ''}]


def definition_of(name):
    """The canvas definition dict of a seeded solution (by SolutionDefinition name)."""
    if name == S.SOLUTION:
        return S.split_app_definition(S.SOLUTION)
    if name == S.ANALYSIS_SOLUTION:
        from hwnocode.custom import temp_analysis as TA
        return TA.definition(TA.NAME)
    if name == S.BC_SOLUTION:
        return S.button_clock_definition(S.BC_SOLUTION)
    if name == S.BC_LEDGER_SOLUTION:
        from hwnocode.custom import button_clock_ledger as BCL
        return BCL.definition(BCL.NAME)
    return None


def _placement(hs):
    from hwnocode.custom import split as SP
    try:
        return SP.place_solution(hs['name'])
    except Exception as e:  # noqa: BLE001 — a seed never breaks the boot; the row says why
        return {'nodes': [], 'refusals': ['placement could not run: %s' % e], 'counts': {}, 'runtime': {'ok': False, 'why': str(e)}}


def solution_rows():
    """HardwareSolution + HardwareNodePlacement rows (derived fields filled)."""
    from hwnocode.custom import placement as PL
    from hwnocode.custom import split as SP
    sols, places = [], []
    for hs in SOLUTIONS:
        rep = _placement(hs)
        rec = SP.load_record(hs['name']) or {}
        b, pr = rec.get('build') or {}, rec.get('proof') or {}
        status = ('proven' if pr.get('ok') else 'built' if b.get('ok') else 'rendered' if rec.get('split_sha256') else
                  'refused' if rep['refusals'] else 'placed')
        sols.append(dict(hs, runtime_status=('supported — ' if rep['runtime']['ok'] else 'refused — ') + rep['runtime']['why'],
                         placement_summary=PL.summary(rep) if rep['counts'] else '', node_count=len(rep['nodes']),
                         refused='; '.join(rep['refusals']), split_sha256=rec.get('split_sha256', ''),
                         glue_files_sha256=(rec.get('board_half') or {}).get('files_sha256', ''),
                         glue_hex_sha256=b.get('hex_sha256', ''), status=status, proof=pr.get('summary', ''),
                         costs=json.dumps(rec.get('costs') or {}, sort_keys=True) if rec.get('costs') else ''))
        for i, n in enumerate(rep['nodes']):
            places.append({'name': '%s:%s:%s' % (hs['name'], n['layer'], n['node']), 'solution': hs['name'], 'node': n['node'],
                           'layer': n['layer'], 'kind': n['kind'], 'placement': n['placement'], 'language': n['language'],
                           'why': n['why'], 'refused': n['refused'], 'order': i, 'runtime': n.get('runtime', ''),
                           'purpose': n.get('purpose', ''), 'notes': ''})
    return sols, places


def solution_definitions():
    """The canvas SolutionDefinition (category='cross-domain', fs-1) + the backend half (as hn-split derives it — the
    placement is pure, so it is derived here without rendering the board half) + the backend solutions the
    Cross-Domain canvas calls OUT to (temp-analysis, category='', plain compute — fs-1)."""
    from hwnocode.custom import placement as PL
    out = []
    for hs in SOLUTIONS:
        d = definition_of(hs['solution'])
        out.append({'name': hs['solution'], 'function_name': hs['solution'].replace('-', '_'), 'target_runtime': 'python_backend',
                    'definition': json.dumps(d), 'contract_json': json.dumps(S.contract()), 'category': 'cross-domain'})
        rep = _placement(hs)
        if rep['nodes'] and not rep['refusals']:
            half = PL.backend_partition(d, rep, hs['backend_solution'])
            half['compiledBy'] = {'compiler': 'hn-split', 'sourceRows': ['HardwareSolution:%s' % hs['name']],
                                  'notes': 'the backend half (placement rule §2b)'}
            out.append({'name': hs['backend_solution'], 'function_name': hs['backend_solution'].replace('-', '_').replace('.', '_'),
                        'target_runtime': 'python_backend', 'definition': json.dumps(half), 'contract_json': json.dumps(S.contract()),
                        'category': ''})
    from hwnocode.custom import temp_analysis as TA
    out.append({'name': TA.NAME, 'function_name': TA.NAME.replace('-', '_'), 'target_runtime': 'python_backend',
               'definition': json.dumps(TA.definition()), 'contract_json': json.dumps(TA.contract()), 'category': ''})
    # ucd-1: button-clock-ledger (plain backend compute) + uno-button-clock.backend (the hand-built executable subset
    # of the cross-domain canvas — relay-in/call/relay-out/frontend-emit; see solutions.button_clock_backend_definition's
    # docstring for why this is NOT derived through hn-split's placement). Appended unconditionally, same as temp-analysis.
    from hwnocode.custom import button_clock_ledger as BCL
    out.append({'name': BCL.NAME, 'function_name': BCL.NAME.replace('-', '_'), 'target_runtime': 'python_backend',
               'definition': json.dumps(BCL.definition()), 'contract_json': json.dumps(BCL.contract()), 'category': ''})
    out.append({'name': S.BC_BACKEND_SOLUTION, 'function_name': S.BC_BACKEND_SOLUTION.replace('-', '_').replace('.', '_'),
               'target_runtime': 'python_backend', 'definition': json.dumps(S.button_clock_backend_definition()),
               'contract_json': json.dumps(S.button_clock_contract()), 'category': ''})
    return out


ANALYSES = [{
    'name': S.ANALYSIS, 'domain': 'hwnocode', 'callable_ref': 'hwnocode.custom.derive:temp_derive',
    'description': 'uno-temp-split\'s backend node: keep this frame\'s temp_c sample (a ring of `keep` per row) and return the moving '
                   'average over `window` samples. The threshold flag + the derived row are the engine\'s own nodes.',
    'params_json': json.dumps({'object': '', 'uptime_ms': 0, 'temp_c': 0.0, 'window': S.KNOBS['window'], 'keep': S.KNOBS['keep'],
                               'solution': S.SOLUTION}),
    'enabled': True, 'is_prior': True, 'provenance_id': '', 'notes': ''}, {
    # ucd-1
    'name': 'hwnocode-button-clock-derive', 'domain': 'hwnocode', 'callable_ref': 'hwnocode.custom.button_clock:button_clock_derive',
    'description': 'uno-button-clock\'s backend node: presses_per_min over the last minute of the device\'s own clock, and the '
                   'sense_rises/sense_falls/button_presses/led_on invariant (UNO_CORE_DEMO_PLAN.md §1), named on a break. '
                   'Retention pruning of ButtonClockEvent is a SEPARATE door (hwnocode.custom.button_clock.prune_events), never run here.',
    'params_json': json.dumps({'board_instance': S.BC_OBJECT_NAME, 'object': '', 'solution': S.BC_SOLUTION}),
    'enabled': True, 'is_prior': True, 'provenance_id': '', 'notes': ''}]

TRIGGERS = [{
    'name': S.TRIGGER, 'description': 'every frame the bridge applies to the uno-digital-twin SimRigState row → the backend half of uno-temp-split',
    'enabled': True, 'source_kind': 'object',
    'source_json': json.dumps({'class': S.OBJECT_CLASS, 'operations': ['update', 'create'], 'fieldFilter': {'name': S.OBJECT_NAME}}),
    'solution_name': '%s.backend' % S.SOLUTION,
    'inputs_json': json.dumps({'window': S.KNOBS['window'], 'threshold_c': S.KNOBS['threshold_c'], 'keep': S.KNOBS['keep']}),
    'cooldown_s': 0.0, 'max_depth': 8, 'run_as': 'definer', 'is_prior': True, 'notes': 'knobs: window, threshold_c, keep (inputs_json)'}, {
    # ucd-1
    'name': 'uno-button-clock-on-frame',
    'description': 'every ButtonClockState frame the bridge applies to uno-button-clock\'s own row → the backend half of uno-button-clock',
    'enabled': True, 'source_kind': 'object',
    'source_json': json.dumps({'class': S.BC_OBJECT_CLASS, 'operations': ['update', 'create'], 'fieldFilter': {'name': S.BC_OBJECT_NAME}}),
    'solution_name': S.BC_BACKEND_SOLUTION,
    'inputs_json': json.dumps({'retention': S.BC_KNOBS['retention'], 'sync_every_s': S.BC_KNOBS['sync_every_s']}),
    'cooldown_s': 0.0, 'max_depth': 8, 'run_as': 'definer', 'is_prior': True,
    'notes': 'knobs: retention (ButtonClockEvent prune bound, a door — hwnocode.custom.button_clock.prune_events — '
             'never run per-frame), sync_every_s (SET_TIME resync cadence, bridge/installer lifecycle, out of ucd-1\'s scope)'}]

BINDINGS = [{
    'name': S.BINDING, 'bridge_name': S.BRIDGE, 'object_class': S.OBJECT_CLASS, 'object_name': S.OBJECT_NAME,
    'board_instance': S.ROUTE['board_instance'], 'board_definition': S.BOARD, 'interface_kind': S.ROUTE['interface_kind'],
    'interface_name': 'usart0', 'port': S.ROUTE['port'], 'adapter': '', 'instance_index': 0, 'wire_version': 2, 'origin': 'seeded',
    'notes': 'uno-temp-split\'s hw-interface node (hn-0): the sim-rig glue on the simavr twin, USART0 at the twin\'s pty link '
             '(pol board twin uno up --work <hwnocode work>); one instance on the bridge → no index on the wire'}, {
    # ucd-1: ButtonClockEvent is deliberately NOT bound here — its Push rows must stay one-per-event (ButtonClockEvent's
    # own docstring: "never converged/reused across events"); a binding would upsert every event push onto this SAME
    # row (grpc_server._apply_push's binding-owns-identity rule), which is exactly the append-ledger behaviour D-ucd-5
    # refuses. Only the latest-state class is bound.
    'name': S.BC_BINDING, 'bridge_name': S.BC_BRIDGE, 'object_class': S.BC_OBJECT_CLASS, 'object_name': S.BC_OBJECT_NAME,
    'board_instance': S.BC_ROUTE['board_instance'], 'board_definition': S.BOARD, 'interface_kind': S.BC_ROUTE['interface_kind'],
    'interface_name': 'usart0', 'port': S.BC_ROUTE['port'], 'adapter': '', 'instance_index': 0, 'wire_version': 2, 'origin': 'seeded',
    'notes': 'uno-button-clock\'s hw-interface node (ucd-1): ButtonClockState only (latest-state, upserted); the twin\'s OWN '
             'pty link (never shares uno-temp-split\'s), one instance on the bridge → no index on the wire'}]
