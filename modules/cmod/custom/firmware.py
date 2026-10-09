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


def solution_for_graph(graph_name, manager=None):
    """The FirmwareSolution dict row over this graph, or None (a graph may predate fs-0, or carry no solution yet —
    legitimate, never refused). `cmod.custom.glue.render_files` asks this (ucd-0b) to decide whether a rendered
    project gains the GENERATED pin_config.h/.c; live rows win when a manager has them, else the pure seed."""
    if manager is not None:
        rows = [{k: getattr(r, k, '') for k in ('name', 'graph', 'board_definition', 'board_variable')}
                for r in (manager.objectTables or {}).get('FirmwareSolution', {}).values() if getattr(r, 'graph', '') == graph_name]
        if rows:
            return sorted(rows, key=lambda r: r['name'])[0]
    from cmod.cmod_seed import CMOD_SEED_PAIRS
    rows = next((rs for n, _c, rs in CMOD_SEED_PAIRS if n == 'FirmwareSolution'), [])
    return next((r for r in rows if r['graph'] == graph_name), None)


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


#: ucd-0b2a (§5h B2): the signal_route cache, one board_object lookup per board per assignments_for() call — never
#: per row (board.custom.board_object.rows_for rebuilds every row of the board)
def _signal_route_cache():
    cache = {}

    def route_for(board, canonical):
        if board not in cache:
            try:
                from board.custom import board_object as BO
                cache[board] = BO.rows_for(board)
            except Exception:
                cache[board] = None
        r = cache[board]
        if r is None:
            return ''
        from board.custom import board_object as BO
        from board.custom.soc_atmega328p import SOC
        pin = BO.pin_by_canonical(r, canonical)
        if pin and pin.get('signal') and pin.get('soc_pin'):
            return '%s:%s:%s' % (SOC, pin['soc_pin'], pin['signal'])
        return ''
    return route_for


# ------------------------------------------------------------------ D-fs-2: the DERIVED register map
def assignments_for(graph_name, solution_name=None, binding_name=None):
    """[RegisterAssignment dict, …] for one graph's targets (`cmod.custom.targets.derive`), re-homed per solution and
    re-checked for CONFLICT (two tasks resolving to the same BoardPin). fs-0 scope: the graph's own seeded board (the
    common case — a graph is authored against the board it is seeded with); re-matching against a DIFFERENT board a
    `board_variable` resolves to at run time is demo-5/fs-1 scope (the pin-map drag), not re-derived here.

    ucd-0b2a (§5h B2): every row also carries `peripheral`/`signal`/`bus` (the typed-resource binding modes beside
    `lives_on` — '' today: this deriver only ever binds by pin), `signal_route` (the PinFunction the bound pin's own
    alternate function activates, '' for plain GPIO or unbound).

    ucd-0b2b (§5h, the HardwareBinding): `configuration` is now the BINDING's own name (`cmod.custom.binding.
    binding_name`), not the bare solution — "a FirmwareSolution is hardware-agnostic; a HardwareBinding owns the
    assignments". `binding_name` defaults to the solution's OWN default binding ('<solution>@<board>', the graph's
    own recorded board) when not given — every pre-0b2b caller keeps the SAME row `name` prefix ('<solution>:...')
    for that default binding (D-ucd-8 posture: widen, never rename / never churn); only an EXPLICIT, non-default
    `binding_name` (a second binding, fs-2a's drag over a canvas-created one) renames the row prefix to the binding's
    own name, so two bindings' rows never collide.

    ucd-0c (Part 0, the naming fix): a task with SEVERAL whole-node targets (its atom's own ports never settle a
    single pin — usart_init: D0 and D1) used to collapse to ONE row because its name was '<prefix>:<task>' for
    every one of them; such a row is now named '<prefix>:<task>@<canonical>' (the pin — or the signal/peripheral it
    names when never pin-bound). A task with exactly one whole-node target is unaffected (keeps '<prefix>:<task>',
    every other id this arc already hands out stays stable)."""
    from cmod.custom import targets as T
    sol = solution_name or graph_name
    targets = T.derive(graph_name)
    board_for_cfg = targets[0]['board'] if targets and targets[0].get('board') else ''
    if not board_for_cfg:
        from cmod.custom.graph_seed import seed_graph
        _rows = seed_graph(graph_name)
        board_for_cfg = (_rows or {}).get('graph', {}).get('board', '')
    default_cfg = ('%s@%s' % (sol, board_for_cfg)) if board_for_cfg else sol
    cfg = binding_name or default_cfg
    name_prefix = sol if cfg == default_cfg else cfg
    route_for = _signal_route_cache()
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
    # ucd-0c (the naming fix, Part 0): a WHOLE-NODE target (port == '', so port_ref falls back to the bare node —
    # cmod.custom.targets.derive's `add()`) exists MORE THAN ONCE for one task when the atom's own ports cannot
    # settle a single pin (usart_init's two rows, D0 and D1 — the atom only touches UBRR0/UCSR0x, never a named
    # port): those rows would otherwise share the SAME un-suffixed name ('<binding>:<task>'), and a later one
    # SILENTLY OVERWRITES the earlier one wherever RegisterAssignment rows are keyed by name (the manager's own
    # table on upsert, and `cmod_firmware_api.on_get_solution_one`'s own `{name: row}` join) — collapsing two real,
    # distinct bindings (uart-rx on D0, uart-tx on D1) into one. Counted here so a task with exactly ONE whole-node
    # target keeps its old, stable id ('<binding>:<task>') — only a task with SEVERAL gets the '@<canonical>' suffix.
    whole_node_counts = {}
    for t in targets:
        if t['port'] == '':
            whole_node_counts[t['node']] = whole_node_counts.get(t['node'], 0) + 1
    out = []
    for t in targets:
        lives_on = t['lives_on']
        status = 'unbound'
        notes = ''
        signal_route = ''
        peripheral_val, signal_val = '', ''
        if lives_on != 'unbound':
            owners = {x['node'] for x in claimed[lives_on]} - dispatchers - {n for n in per_node_pins if n.endswith('_init')
                                                                             and n in {x['node'] for x in claimed[lives_on]}
                                                                             and len(claimed[lives_on]) > 1}
            if len(owners) > 1:
                status = 'conflict'
                notes = 'conflict: also claimed by %s' % ', '.join(sorted(owners - {t['node']}))
            else:
                status = 'bound'
            signal_route = route_for(t['board'], lives_on.rpartition(':')[2])
        # ucd-0b2d (§5h, the HardwareBinding fix): a TargetDefinition row of resource_kind peripheral/signal is
        # never pin-bound (lives_on stays 'unbound' above) — its typed `peripheral`/`signal` column (ucd-0b2a)
        # carries the resource instead, status 'bound' (it IS a real requirement this solution satisfies, just
        # not on a pin), provenance derived from the row (never a pin, never guessed).
        elif t.get('resource_kind') == 'peripheral' and t.get('peripheral'):
            peripheral_val, status = t['peripheral'], 'bound'
        elif t.get('resource_kind') == 'signal' and t.get('signal'):
            signal_val, status = t['signal'], 'bound'
        row_name = '%s:%s' % (name_prefix, t['port_ref'])
        if t['port'] == '' and whole_node_counts.get(t['node'], 0) > 1:
            # disambiguate by the pin this particular row resolved to (lives_on), falling back to the signal/
            # peripheral it names when it is never pin-bound (tick_init/rx_pop never collide today — they are the
            # sole row for their task — but the fallback keeps this safe if that ever changes), and, failing even
            # that, the row's own kind (never leaves two rows sharing one name).
            canonical = (lives_on.rpartition(':')[2] if lives_on != 'unbound' else '') \
                or (t.get('signal') or '').rpartition(':')[2] or (t.get('peripheral') or '').rpartition(':')[2] \
                or t['kind']
            row_name = '%s@%s' % (row_name, canonical)
        out.append({'name': row_name, 'solution': sol, 'task': t['node'], 'port': t['port'],
                    'target_kind': t['kind'], 'controls': t['controls'], 'lives_on': lives_on, 'status': status,
                    'provenance': t['provenance'], 'peripheral': peripheral_val, 'signal': signal_val, 'bus': '',
                    'signal_route': signal_route, 'configuration': cfg, 'notes': notes})
    return out


def resource_conflicts(assigns):
    """[name, …] of RegisterAssignment dicts naming MORE THAN ONE resource (lives_on-bound / peripheral / signal /
    bus) — AT MOST ONE is ever allowed per row (ucd-0b2a §5h B2); today's deriver never sets peripheral/signal/bus,
    so this only fires for a future/canvas-authored row, never the seeded ones."""
    out = []
    for a in assigns:
        count = sum(1 for v in (a.get('lives_on') if a.get('lives_on', 'unbound') != 'unbound' else '',
                                a.get('peripheral', ''), a.get('signal', ''), a.get('bus', '')) if v)
        if count > 1:
            out.append(a['name'])
    return out


# ------------------------------------------------------------------ fs-2a: valid targets + the /assign refusal (his ruling 2026-10-06)
def _occupants(graph_name, solution_name, manager=None, binding_name=None):
    """{lives_on: [task, ...]} — who currently claims each bound pin, from the LIVE RegisterAssignment rows when a
    manager is given (a prior POST .../assign may have moved things — the live rows are the truth then), else the
    pure re-derivation (assignments_for) for the no-manager / seed-time path.

    ucd-0b2b: filtered by `binding_name` (the HardwareBinding's own `configuration`) when given — so two bindings of
    the SAME solution never see each other's claims as a conflict; falls back to the old `solution`-wide filter
    only when no binding is named (every pre-0b2b caller)."""
    if manager is not None:
        if binding_name:
            rows = [{'task': getattr(r, 'task', ''), 'lives_on': getattr(r, 'lives_on', ''), 'status': getattr(r, 'status', '')}
                    for r in (manager.objectTables or {}).get('RegisterAssignment', {}).values() if getattr(r, 'configuration', '') == binding_name]
        else:
            rows = [{'task': getattr(r, 'task', ''), 'lives_on': getattr(r, 'lives_on', ''), 'status': getattr(r, 'status', '')}
                    for r in (manager.objectTables or {}).get('RegisterAssignment', {}).values() if getattr(r, 'solution', '') == solution_name]
    else:
        rows = assignments_for(graph_name, solution_name, binding_name=binding_name)
    out = {}
    for r in rows:
        if r['lives_on'] and r['lives_on'] != 'unbound':
            out.setdefault(r['lives_on'], []).append(r['task'])
    return out


def _dispatchers(graph_name):
    """fs-0's own exemption (assignments_for): a node touching MORE THAN ONE pin (a dispatcher — e.g. `apply`
    calling hal_led + hal_pwm_apply) is never counted as a pin's OWNER for conflict purposes. Reused here so a NEW
    candidate drop is judged by the SAME rule, not a second one."""
    from cmod.custom import targets as T
    per_node_pins = {}
    for t in T.derive(graph_name):
        if t['lives_on'] != 'unbound':
            per_node_pins.setdefault(t['node'], set()).add(t['lives_on'])
    return {n for n, pins in per_node_pins.items() if len(pins) > 1}


def _cooperates(graph_name, task, others):
    """fs-0's own exemption, generalized: a dispatcher (touches >1 pin), an '*_init' setup task sharing a pin with
    the atom that drives it, or a task re-claiming its OWN existing pin is cooperation, not a conflict — never a
    silent overwrite otherwise."""
    dispatchers = _dispatchers(graph_name)

    def exempt(t):
        return t in dispatchers or t.endswith('_init')

    return all(o == task or exempt(o) or exempt(task) for o in others)


def valid_targets_for_task(graph_name, solution_name, task, manager=None):
    """fs-2a: {kind, pins: [{pin, verdict, reason, registered_to, cooperating}, ...]} — for EVERY pin of the
    solution's board (board.custom.target_compat.valid_targets), PLUS whether it is already registered to another
    task and, if so, whether that is cooperation (fs-0's exemption, reused) or a conflict. 'valid' = compat ok AND
    (unclaimed OR cooperating); 'invalid' = compat no, OR claimed by a non-cooperating task; 'undetermined' = compat
    undetermined and unclaimed (a warning, not a refusal)."""
    from cmod.custom.graph_seed import seed_graph
    from cmod.custom.targets import requirement_kind
    from board.custom import board_object as BO
    from board.custom import target_compat as TC
    kind = requirement_kind(graph_name, task)
    rows = seed_graph(graph_name)
    board = (rows or {}).get('graph', {}).get('board', '')
    try:
        r = BO.rows_for(board)
    except BO.BoardObjectRefused as e:
        return {'kind': kind, 'pins': [], 'refused': str(e)}
    occupants = _occupants(graph_name, solution_name, manager)
    out = []
    for row in TC.valid_targets(kind, r):
        others = [o for o in occupants.get('%s:%s' % (board, row['pin']), []) if o != task]
        cooperating = _cooperates(graph_name, task, others) if others else True
        verdict = row['verdict']
        if verdict == 'ok' and others and not cooperating:
            verdict, reason = 'invalid', row['reason'] + '; already registered to %s (not cooperating) — conflict' % ', '.join(sorted(others))
        elif verdict == 'ok':
            verdict, reason = 'valid', row['reason']
        elif verdict == 'no':
            verdict, reason = 'invalid', row['reason']
        else:
            verdict, reason = 'undetermined', row['reason']
        out.append({'pin': row['pin'], 'verdict': verdict, 'reason': reason, 'registered_to': sorted(others), 'cooperating': cooperating})
    return {'kind': kind, 'pins': out}


def unregistered_tasks(assignment_rows):
    """fs-2a (his naming, verbatim): the 'Unregistered Tasks' — one row per RegisterAssignment with status='unbound'
    (a real target, just not placed on a pin yet), from a solution's own assignment rows (live or pure, caller's
    choice — same shape either way: dicts with task/port/target_kind/controls)."""
    return [a for a in assignment_rows if a.get('status') == 'unbound']


def registered_tasks_by_pin(assignment_rows):
    """fs-2a (his naming, verbatim): the 'Registered Tasks' per pin — {lives_on: [{task, port, status, cooperating},
    ...]}, from a solution's own assignment rows; 'cooperating' mirrors fs-0's exemption (status != 'conflict')."""
    out = {}
    for a in assignment_rows:
        if a.get('lives_on') and a['lives_on'] != 'unbound':
            out.setdefault(a['lives_on'], []).append({'task': a.get('task', ''), 'port': a.get('port', ''),
                                                       'status': a.get('status', ''), 'cooperating': a.get('status') != 'conflict'})
    return out


def check_drop(graph_name, solution_name, task, lives_on, manager=None, binding_name=None):
    """(ok, status, reason) for dragging `task`'s target onto `lives_on` (a '<board>:<canonical>' BoardPin name, or
    'unbound'/''). Refuses (ok=False) when board.custom.target_compat.compatible() says no, when the pin is
    power/ground (compatible() already covers this), or when it would conflict with a non-cooperating task;
    'undetermined' is allowed, with a warning (his ruling: never silently guessed, never silently refused either).
    ucd-0b2b: `binding_name` scopes the occupancy check to one HardwareBinding (never a false conflict against a
    DIFFERENT binding of the same solution) — omitted, it falls back to the old solution-wide check."""
    if lives_on in ('', 'unbound'):
        return True, 'unbound', 'unbound is always allowed — a real target, just not placed'
    board, _, canonical = lives_on.partition(':')
    from board.custom import board_object as BO
    from board.custom import target_compat as TC
    from cmod.custom.targets import requirement_kind
    try:
        r = BO.rows_for(board)
    except BO.BoardObjectRefused as e:
        return False, 'refused', str(e)
    pin = BO.pin_by_canonical(r, canonical)
    universe = {p['canonical']: p for p in TC.board_target_universe(r)}
    pin = pin or universe.get(canonical)
    if pin is None:
        return False, 'refused', '%s has no pin %s' % (board, canonical)
    soc_pin = next((s for s in r['soc_pins'] if s['pin'] == pin.get('soc_pin')), None) if pin.get('soc_pin') else None
    kind = requirement_kind(graph_name, task)
    verdict, reason = TC.compatible(kind, pin, soc_pin)
    if verdict == 'no':
        return False, 'refused', reason
    others = [o for o in _occupants(graph_name, solution_name, manager, binding_name=binding_name).get(lives_on, []) if o != task]
    if others and not _cooperates(graph_name, task, others):
        return False, 'refused', 'pin %s is already registered to %s (not a cooperating init/use pair) — conflict' % (lives_on, ', '.join(sorted(others)))
    if verdict == 'undetermined':
        return True, 'undetermined', reason
    return True, 'bound', reason


# ------------------------------------------------------------------ validation (board exists+usable, targets bound/named, no conflicts)
def validate(fs, manager=None):
    """(ok, why, details) for one FirmwareSolution dict/row: the board resolves and is usable (readiness), every
    required target is bound or explicitly named unbound (never silently missing), no two tasks conflict on one
    pin, and (ucd-0b) no two tasks conflict on one PinClaim or one exclusive PeripheralClaim — a claim 'incomplete'
    (e.g. an interrupt-in with no edge chosen yet) is NAMED in `why` but never refuses (same posture as an unbound
    target). Never raises — a refusal is a returned, named reason (his posture, `knobs.check_runtime()`'s own idiom)."""
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
    multi = resource_conflicts(assigns)
    if multi:
        return False, ('refused: %s names more than one resource — at most one of lives_on/peripheral/signal/bus '
                       'may be non-empty (ucd-0b2a §5h B2)' % ', '.join(sorted(multi))), {'board': board, 'assignments': assigns}
    from cmod.custom import claims as C
    # ucd-0b2b: pass `fs` itself (not just its name) — claims._as_binding resolves the board straight off this
    # dict/row, never through cmod.cmod_seed.CMOD_SEED_PAIRS (this runs AT SEED TIME, before that list is built —
    # a lookup there would be a circular import)
    pin_claims = C.pin_claims(fs, graph, manager=manager)
    pin_conflicts = [c for c in pin_claims if c['status'] == 'conflict']
    if pin_conflicts:
        return False, 'refused: pin claim conflict on %s (%s)' % (', '.join(c['name'] for c in pin_conflicts),
                                                                   '; '.join(c['why'] for c in pin_conflicts)), \
            {'board': board, 'assignments': assigns, 'claims': pin_claims}
    periph_claims = C.peripheral_claims(fs, graph, manager=manager)
    periph_conflicts = [p for p in periph_claims if p['status'] == 'conflict']
    if periph_conflicts:
        return False, 'refused: peripheral claim conflict on %s (%s)' % (', '.join(p['name'] for p in periph_conflicts),
                                                                          '; '.join(p['why'] for p in periph_conflicts)), \
            {'board': board, 'assignments': assigns, 'claims': pin_claims, 'peripheral_claims': periph_claims}
    unbound = [a['task'] + ('.' + a['port'] if a['port'] else '') for a in assigns if a['status'] == 'unbound']
    incomplete = [c['name'] for c in pin_claims if c['status'] == 'incomplete']
    ok_why = 'ok: board %s resolved (%s); %d target(s), %d unbound (%s)%s' % (
        board, why, len(assigns), len(unbound), ', '.join(unbound) or 'none',
        ('; %d pin claim(s) incomplete (%s)' % (len(incomplete), ', '.join(incomplete))) if incomplete else '')
    return True, ok_why, {'board': board, 'assignments': assigns, 'claims': pin_claims, 'peripheral_claims': periph_claims}


# ------------------------------------------------------------------ ucd-0b2b: accept a HardwareBinding, not just a bare solution
def as_solution_target(fs_or_binding, manager=None):
    """(solution dict/row, binding dict/row|None) — a `FirmwareSolution` (unchanged; `binding` is None) or a
    `HardwareBinding` (resolved to its underlying solution; `binding` carries it). Only the DEFAULT binding has a
    compiled project this phase (cmod-glue renders ONE project per graph, matched against the graph's own recorded
    board) — a non-default binding's build/run is refused, named 'Phase 2', never silently building the wrong
    board's firmware."""
    is_dict = isinstance(fs_or_binding, dict)
    has_board_def = ('board_definition' in fs_or_binding) if is_dict else hasattr(fs_or_binding, 'board_definition')
    if has_board_def:
        return fs_or_binding, None
    sol_name = fs_or_binding.get('solution') if is_dict else getattr(fs_or_binding, 'solution', '')
    from cmod.custom import binding as BND
    sol = BND._solution_dict(sol_name, manager=manager)
    return sol, fs_or_binding


def _binding_build_guard(bnd, sol):
    if bnd is None:
        return None
    is_default = bnd.get('is_default') if isinstance(bnd, dict) else getattr(bnd, 'is_default', False)
    if is_default:
        return None
    bname = bnd.get('name') if isinstance(bnd, dict) else getattr(bnd, 'name', '')
    sname = (sol or {}).get('name', '') if isinstance(sol, dict) else getattr(sol, 'name', '')
    return ('%s: building/running a non-default HardwareBinding is Phase 2 — only %s\'s default binding has a '
            'compiled project this phase (cmod-glue renders one project per graph, against the graph\'s own board)'
            % (bname, sname))


# ------------------------------------------------------------------ build / run — WIRE the existing verbs, never reimplement
def build(fs, manager=None):
    """-> the CGlueBuild/FirmwareBuild this solution's graph produces. Reuses cmod-glue entirely (`glue_build.build`) —
    fs-0 adds no new compiler. Refuses (raises GlueRefused, same type the caller already catches) if validate() fails.
    ucd-0b2b: `fs` may be a FirmwareSolution OR a HardwareBinding (`as_solution_target`) — only a DEFAULT binding is
    backed by a build this phase."""
    from cmod.custom.glue import GlueRefused
    from cmod.custom import glue_build as GB
    sol, bnd = as_solution_target(fs, manager=manager)
    guard = _binding_build_guard(bnd, sol)
    if guard:
        raise GlueRefused(guard)
    fs = sol
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
    is returned (not raised) so a caller can show it beside the route, same posture as hwnocode's `_hardware_route`.
    ucd-0b2b: `fs` may be a FirmwareSolution OR a HardwareBinding — only its DEFAULT binding runs this phase."""
    from cmod.custom import glue_build as GB
    sol, bnd = as_solution_target(fs, manager=manager)
    guard = _binding_build_guard(bnd, sol)
    if guard:
        return {'ok': False, 'route': 'refused', 'why': guard}
    fs = sol
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
