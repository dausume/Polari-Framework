"""
@module hwnocode.custom.seed_rows

The code-owned rows of hn-0, as dicts (hwnocode_seed upserts them): the HardwareSolution `uno-temp-split`, its canvas
SolutionDefinition + the backend half hn-split derives, the AnalysisDefinition + EventTrigger that run the backend half per frame,
the HardwareInterfaceBinding that IS its hw-interface node (a grpcbridge row: SimRigState `uno-twin` ↔ the UNO twin's pty on bridge
`uno-temp-split`), and one HardwareNodePlacement row per node. Derived fields come from the placement (pure Python — no engine) and
the split's committed record (custom/splits/<solution>.json); nothing is rendered or built at boot.
"""
import json

from hwnocode.custom import solutions as S

SOLUTIONS = [{
    'name': S.SOLUTION, 'title': 'UNO temperature, split across board, bridge, backend and screen',
    'purpose': ('Variant h over the existing peripheral (variant b): the sim-rig firmware (a cmod graph, byte-identical to the shipped '
                'app) sends SimRigState frames at 10 Hz; the bridge applies them to the uno-twin row; a backend solution keeps a moving '
                'average of temp_c and flags it above a threshold on SimRigTempDerived; /display/hardware-solutions charts both. A PUT of '
                'led_on on the row rides the Commands stream back down to the firmware.'),
    'variant_kind': 'h', 'solution': S.SOLUTION, 'backend_solution': '%s.backend' % S.SOLUTION, 'cgraph': S.CGRAPH,
    'board_definition': S.BOARD, 'board_instance': S.TWIN_INSTANCE, 'interface': S.BINDING, 'displays': S.DISPLAY,
    'firmware_runtime': 'bare-c', 'notes': ''}]


def definition_of(name):
    """The canvas definition dict of a seeded solution (by SolutionDefinition name)."""
    if name == S.SOLUTION:
        return S.split_app_definition(S.SOLUTION)
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
                           'why': n['why'], 'refused': n['refused'], 'order': i, 'notes': ''})
    return sols, places


def solution_definitions():
    """The canvas SolutionDefinition + the backend half (as hn-split derives it — the placement is pure, so it is derived here
    without rendering the board half)."""
    from hwnocode.custom import placement as PL
    out = []
    for hs in SOLUTIONS:
        d = definition_of(hs['solution'])
        out.append({'name': hs['solution'], 'function_name': hs['solution'].replace('-', '_'), 'target_runtime': 'python_backend',
                    'definition': json.dumps(d), 'contract_json': json.dumps(S.contract())})
        rep = _placement(hs)
        if rep['nodes'] and not rep['refusals']:
            half = PL.backend_partition(d, rep, hs['backend_solution'])
            half['compiledBy'] = {'compiler': 'hn-split', 'sourceRows': ['HardwareSolution:%s' % hs['name']],
                                  'notes': 'the backend half (placement rule §2b)'}
            out.append({'name': hs['backend_solution'], 'function_name': hs['backend_solution'].replace('-', '_').replace('.', '_'),
                        'target_runtime': 'python_backend', 'definition': json.dumps(half), 'contract_json': json.dumps(S.contract())})
    return out


ANALYSES = [{
    'name': S.ANALYSIS, 'domain': 'hwnocode', 'callable_ref': 'hwnocode.custom.derive:temp_derive',
    'description': 'uno-temp-split\'s backend node: keep this frame\'s temp_c sample (a ring of `keep` per row) and return the moving '
                   'average over `window` samples. The threshold flag + the derived row are the engine\'s own nodes.',
    'params_json': json.dumps({'object': '', 'uptime_ms': 0, 'temp_c': 0.0, 'window': S.KNOBS['window'], 'keep': S.KNOBS['keep'],
                               'solution': S.SOLUTION}),
    'enabled': True, 'is_prior': True, 'provenance_id': '', 'notes': ''}]

TRIGGERS = [{
    'name': S.TRIGGER, 'description': 'every frame the bridge applies to the uno-twin SimRigState row → the backend half of uno-temp-split',
    'enabled': True, 'source_kind': 'object',
    'source_json': json.dumps({'class': S.OBJECT_CLASS, 'operations': ['update', 'create'], 'fieldFilter': {'name': S.OBJECT_NAME}}),
    'solution_name': '%s.backend' % S.SOLUTION,
    'inputs_json': json.dumps({'window': S.KNOBS['window'], 'threshold_c': S.KNOBS['threshold_c'], 'keep': S.KNOBS['keep']}),
    'cooldown_s': 0.0, 'max_depth': 8, 'run_as': 'definer', 'is_prior': True, 'notes': 'knobs: window, threshold_c, keep (inputs_json)'}]

BINDINGS = [{
    'name': S.BINDING, 'bridge_name': S.BRIDGE, 'object_class': S.OBJECT_CLASS, 'object_name': S.OBJECT_NAME,
    'board_instance': S.TWIN_INSTANCE, 'board_definition': S.BOARD, 'interface_kind': 'twin-pty', 'interface_name': 'usart0',
    'port': S.TWIN_LINK, 'adapter': '', 'instance_index': 0, 'wire_version': 2, 'origin': 'seeded',
    'notes': 'uno-temp-split\'s hw-interface node (hn-0): the sim-rig glue on the simavr twin, USART0 at the twin\'s pty link '
             '(pol board twin uno up --work <hwnocode work>); one instance on the bridge → no index on the wire'}]
