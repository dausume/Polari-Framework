"""
@module cmod.custom.firmware

FIRMWARE SOLUTIONS (fs-0, DEMONSTRABLES_PLAN.md §9; his message 2026-10-05, D-fs-1..3 ruled "go with your picks"): a
`FirmwareSolution` takes a `CGraph` (its tasks = the graph's c-atom `CGraphNode`s) and a board (fixed or a run-time
variable) and derives its SCHEDULE (`ScheduleSlot`, D-fs-1: from the atoms' own ISR/tick/loop/init annotations, never
authored) and its REGISTER MAP (`RegisterAssignment`, D-fs-2: the same binding a pin-map drag will set, built here as
rows + the `assign` door fs-1's drag calls). Everything below is PURE over rows already produced elsewhere (the
project's committed manifest, the graph's own nodes/edges, `cmod.custom.targets.derive`, the board register) — same
posture as `custom/targets.py`: no manager required to compute, a manager only to read/write FirmwareSolution rows.
"""
import json
import os

from cmod.custom import projects as P


def _manifest(project):
    spec = P.resolve(project)
    path = P.manifest_path(spec)
    if not os.path.isfile(path):
        return {}
    return json.load(open(path))


def _graph_rows(graph_name):
    from cmod.custom.graph_seed import seed_graph
    return seed_graph(graph_name)


def resolve_board(fs, manager=None):
    """(board_name, exists, why) for a FirmwareSolution dict/row: board_definition wins if set; else board_variable is
    looked up among the KNOWN boards (his words: "validated when running that it still exists" — a stale pick refuses
    loud, named). With no manager, a board_definition is trusted by name (pure path, seed time); a board_variable
    needs the live register and reports 'unknown without a live manager' rather than guessing."""
    bd = fs.get('board_definition') if isinstance(fs, dict) else getattr(fs, 'board_definition', '')
    bv = fs.get('board_variable') if isinstance(fs, dict) else getattr(fs, 'board_variable', '')
    if bd:
        if manager is None:
            return bd, True, 'fixed board_definition %r (not checked against a live register here)' % bd
        boards = list((manager.objectTables or {}).get('BoardDefinition', {}).values())
        hit = any(getattr(b, 'name', '') == bd for b in boards)
        return bd, hit, ('fixed board_definition %r' % bd) if hit else ('board_definition %r no longer exists in the register' % bd)
    if not bv:
        return '', False, 'neither board_definition nor board_variable is set'
    if manager is None:
        return bv, False, 'board_variable %r cannot be resolved without a live manager (run-time only, his rule)' % bv
    boards = list((manager.objectTables or {}).get('BoardDefinition', {}).values())
    hit = next((b for b in boards if getattr(b, 'name', '') == bv), None)
    if hit is None:
        return bv, False, 'board_variable %r names no BoardDefinition in the register — refused (his rule: validated at run time)' % bv
    from board.custom import readiness as RD
    variants = list((manager.objectTables or {}).get('FirmwareVariant', {}).values())
    sols = list((manager.objectTables or {}).get('HardwareSolution', {}).values())
    scens = list((manager.objectTables or {}).get('Scenario', {}).values())
    readi, why = RD.compute_readiness(hit, variants, sols, scens)
    if readi != 'usable':
        return bv, False, 'board_variable %r resolved to %s, but it is not usable yet (%s)' % (bv, bv, why)
    return bv, True, 'board_variable %r resolved to a usable board (%s)' % (bv, why)


# ------------------------------------------------------------------ D-fs-1: the DERIVED schedule
def schedule_for(graph_name, solution_name=None):
    """[ScheduleSlot dict, …] for one graph, DERIVED (D-fs-1) from: the project's own ISR atoms (isr lane — these are
    always linked into the glue, never wired as graph nodes), the graph's own 'tick' node(s) (tick lane), and every
    c-atom node's `stage` (init | loop | called — loop/init/called lanes). Never authored; re-running this on the same
    graph always gives the same rows (idempotent, same posture as cmod-1's render)."""
    rows = _graph_rows(graph_name)
    if rows is None:
        return []
    g, nodes = rows['graph'], rows['nodes']
    sol = solution_name or graph_name
    m = _manifest(g['project'])
    atoms = {a['name']: a for a in m.get('atoms', [])}
    out = []

    # isr lane: the project's own ISR atoms — always compiled in by the glue (hal.c), never a graph node
    isr_atoms = sorted((a for a in m.get('atoms', []) if a.get('kind') == 'isr'), key=lambda a: a['name'])
    for i, a in enumerate(isr_atoms):
        out.append({'name': '%s:isr:%s' % (sol, a['name']), 'solution': sol, 'task': a['name'], 'lane': 'isr',
                    'order': i, 'trigger': a.get('isr_vector', ''), 'period_ms': 0, 'measured_cycles': -1,
                    'isr_vector': a.get('isr_vector', ''), 'provenance': 'derived',
                    'notes': 'always linked into the glue (project-level ISR, not wired as a graph node); cost is '
                             'bytes/stack (CFunctionAtom.cost) — no per-atom cycle measurement exists yet'})

    for n in sorted(nodes, key=lambda n: n.get('order', 0)):
        if n.get('kind') == 'tick':
            params = n.get('params', '') or ''
            period = next((v for k, v in (p.split('=', 1) for p in params.split(';') if '=' in p) if k.strip() == 'period_ms'), '')
            out.append({'name': '%s:tick:%s' % (sol, n['instance']), 'solution': sol, 'task': n['instance'], 'lane': 'tick',
                        'order': n.get('order', 0), 'trigger': params, 'period_ms': 0, 'measured_cycles': -1, 'isr_vector': '',
                        'provenance': 'derived', 'notes': 'period macro %r (resolved in board_config.h, not re-typed here)' % period})
        elif n.get('kind') == 'c-atom':
            stage = n.get('stage', '') or 'loop'
            lane = stage if stage in ('init', 'loop', 'called') else 'loop'
            bare = (n.get('atom') or '').partition(':')[2]
            a = atoms.get(bare) or {}
            cost = (a.get('cost') or {})
            out.append({'name': '%s:%s:%s' % (sol, lane, n['instance']), 'solution': sol, 'task': n['instance'], 'lane': lane,
                        'order': n.get('order', 0), 'trigger': '' if lane != 'called' else 'called by another task (not scheduled directly)',
                        'period_ms': 0, 'measured_cycles': -1, 'isr_vector': a.get('isr_vector', '') or '',
                        'provenance': 'derived',
                        'notes': 'text_bytes_noinline=%s B, stack_bytes=%s (CFunctionAtom.cost; no per-atom cycle count yet)'
                                 % (cost.get('text_bytes_noinline', '?'), cost.get('stack_bytes', '?'))})
    return out


# ------------------------------------------------------------------ D-fs-2: the DERIVED register map
def assignments_for(graph_name, solution_name=None):
    """[RegisterAssignment dict, …] for one graph's targets (`cmod.custom.targets.derive`), re-homed per solution and
    re-checked for CONFLICT (two tasks resolving to the same BoardPin). fs-0 scope: the graph's own seeded board (the
    common case — a graph is authored against the board it is seeded with); re-matching against a DIFFERENT board a
    `board_variable` resolves to at run time is demo-5/fs-1 scope (the pin-map drag), not re-derived here."""
    from cmod.custom import targets as T
    sol = solution_name or graph_name
    targets = T.derive(graph_name)
    # nodes that themselves touch MORE THAN ONE pin (a dispatcher — e.g. `apply` calling hal_led + hal_pwm) are not
    # counted as a pin's OWNER for conflict purposes, same as an '*_init' setup task sharing its peripheral's pin
    # with the atom that actually drives it — both are legitimate COOPERATION within one graph, never a conflict.
    per_node_pins = {}
    for t in targets:
        if t['lives_on'] != 'unbound':
            per_node_pins.setdefault(t['node'], set()).add(t['lives_on'])
    dispatchers = {n for n, pins in per_node_pins.items() if len(pins) > 1}
    claimed = {}
    for t in targets:
        if t['lives_on'] != 'unbound':
            claimed.setdefault(t['lives_on'], []).append(t)
    out = []
    for t in targets:
        lives_on = t['lives_on']
        status = 'unbound'
        notes = ''
        if lives_on != 'unbound':
            owners = {x['node'] for x in claimed[lives_on]} - dispatchers - {n for n in per_node_pins if n.endswith('_init')
                                                                             and n in {x['node'] for x in claimed[lives_on]}
                                                                             and len(claimed[lives_on]) > 1}
            if len(owners) > 1:
                status = 'conflict'
                notes = 'conflict: also claimed by %s' % ', '.join(sorted(owners - {t['node']}))
            else:
                status = 'bound'
        out.append({'name': '%s:%s' % (sol, t['port_ref']), 'solution': sol, 'task': t['node'], 'port': t['port'],
                    'target_kind': t['kind'], 'controls': t['controls'], 'lives_on': lives_on, 'status': status,
                    'provenance': t['provenance'], 'notes': notes})
    return out


# ------------------------------------------------------------------ validation (board exists+usable, targets bound/named, no conflicts)
def validate(fs, manager=None):
    """(ok, why, details) for one FirmwareSolution dict/row: the board resolves and is usable (readiness), every
    required target is bound or explicitly named unbound (never silently missing), and no two tasks conflict on one
    pin. Never raises — a refusal is a returned, named reason (his posture, `knobs.check_runtime()`'s own idiom)."""
    name = fs.get('name') if isinstance(fs, dict) else getattr(fs, 'name', '')
    graph = fs.get('graph') if isinstance(fs, dict) else getattr(fs, 'graph', '')
    board, exists, why = resolve_board(fs, manager=manager)
    if not exists:
        return False, 'refused: %s' % why, {'board': board, 'assignments': []}
    assigns = assignments_for(graph, solution_name=name)
    conflicts = [a for a in assigns if a['status'] == 'conflict']
    if conflicts:
        names = ', '.join(sorted({a['lives_on'] for a in conflicts}))
        return False, 'refused: pin conflict on %s (%s)' % (names, '; '.join(a['notes'] for a in conflicts)), \
            {'board': board, 'assignments': assigns}
    unbound = [a['task'] + ('.' + a['port'] if a['port'] else '') for a in assigns if a['status'] == 'unbound']
    ok_why = 'ok: board %s resolved (%s); %d target(s), %d unbound (%s)' % (
        board, why, len(assigns), len(unbound), ', '.join(unbound) or 'none')
    return True, ok_why, {'board': board, 'assignments': assigns}


# ------------------------------------------------------------------ build / run — WIRE the existing verbs, never reimplement
def build(fs, manager=None):
    """-> the CGlueBuild/FirmwareBuild this solution's graph produces. Reuses cmod-glue entirely (`glue_build.build`) —
    fs-0 adds no new compiler. Refuses (raises GlueRefused, same type the caller already catches) if validate() fails."""
    from cmod.custom.glue import GlueRefused
    from cmod.custom import glue_build as GB
    name = fs.get('name') if isinstance(fs, dict) else getattr(fs, 'name', '')
    graph = fs.get('graph') if isinstance(fs, dict) else getattr(fs, 'graph', '')
    ok, why, _ = validate(fs, manager=manager)
    if not ok:
        raise GlueRefused('%s: %s' % (name, why))
    return GB.build(graph, manager=manager)


def run(fs, mode, manager=None):
    """-> {ok, route, ...}: mode 'digital-twin' proves the graph's glue on the simavr twin (`glue_build.prove` — the
    SAME twin equivalence proof cmod-1 already makes, reused as this solution's run); mode 'hardware' resolves the
    solution's board to a detected BoardInstance and reports the flash route through the EXISTING installer
    (`board.custom.installer.detected`) — never reimplementing flashing. validate() gates both; a validation refusal
    is returned (not raised) so a caller can show it beside the route, same posture as hwnocode's `_hardware_route`."""
    from cmod.custom import glue_build as GB
    name = fs.get('name') if isinstance(fs, dict) else getattr(fs, 'name', '')
    graph = fs.get('graph') if isinstance(fs, dict) else getattr(fs, 'graph', '')
    ok, why, details = validate(fs, manager=manager)
    if not ok:
        return {'ok': False, 'route': 'refused', 'why': why}
    if mode not in ('digital-twin', 'hardware'):
        return {'ok': False, 'route': 'refused', 'why': '%r is not digital-twin or hardware' % mode}
    if mode == 'digital-twin':
        try:
            p = GB.prove(graph, manager=manager)
        except Exception as e:  # noqa: BLE001 — a run refusal is reported, not raised
            return {'ok': False, 'route': 'digital-twin', 'why': str(e)}
        return {'ok': bool(p.get('equivalent')), 'route': 'digital-twin', 'why': why,
                'frames_compared': p.get('frames_compared', 0), 'how': 'glue_build.prove (simavr twin, same proof as pol cmod prove)'}
    try:
        from board.custom import installer as INST
        det = INST.detected(manager=manager)
        inst = next((i for i in (det.get('instances') or []) if i.get('definition') == details['board']), None)
    except Exception as e:  # noqa: BLE001
        return {'ok': False, 'route': 'hardware', 'why': 'detection failed: %s' % e}
    if inst is None:
        return {'ok': False, 'route': 'hardware', 'why': 'no %s detected on this host (board.custom.installer.detected) — '
                                                          'plug it in and `pol board detect --push`' % details['board']}
    return {'ok': True, 'route': 'hardware', 'why': why, 'board_instance': inst.get('name', ''), 'port': inst.get('port', ''),
            'how': 'board.custom.installer (detected instance); flashing itself is pol board flash / installer.run, not reimplemented here'}
