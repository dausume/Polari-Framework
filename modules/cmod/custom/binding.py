"""
@module cmod.custom.binding

HARDWARE BINDING (ucd-0b2b, UNO_CORE_DEMO_PLAN.md §5h, his ruling 2026-10-08: "Solutions should be separable from
specific hardware, we should have hardware specific objects that are bindings or masks that bind to the solutions to
combine into making a valid firmware, needing to meet the minimum requirements of the task for the hardware to be a
valid target"). A `HardwareBinding` ('<solution>@<board>') lays one `FirmwareSolution` over one board. Everything
here is PURE over rows already produced elsewhere (`cmod.custom.firmware`, `cmod.custom.targets`, `board.custom.
board_object`, `board.custom.target_compat`) — a manager is only needed to read/write LIVE rows, never to compute.

VALIDITY is computed from rows only: every `required` `TargetDefinition` row of the solution's graph needs this
binding's own `RegisterAssignment` bound to a resource THIS board actually has (`board.custom.target_compat.
compatible`, the same check fs-2a's drag already used — never re-typed). A board whose hardware CHAIN (PinFunction /
Peripheral / Register / RegisterField, ucd-0a) is not materialized yet (every board but the UNO's atmega328p, this
phase — the ESP32-C3 has BoardPin rows but no chain behind them) is reported `incomplete`, named, never a crash —
re-matching a solution's requirements against a second SoC's own chain is Phase 2 (§5h B3/B5), not this slice.
"""
import json

#: boards whose hardware chain (PinFunction / Peripheral / Register / RegisterField, ucd-0a) is MATERIALIZED this
#: phase — binding a solution to any OTHER board is honestly `incomplete` (Phase 2), never a crash, never a guess
CHAIN_MATERIALIZED_BOARDS = ('arduino-uno-r3',)


def binding_name(solution, board):
    return '%s@%s' % (solution, board)


def parse_target(name):
    """'<solution>' | '<solution>@<rest>' -> (solution, rest|''). `rest` is a board name for the common case, or a
    whole second binding's own name-after-'@' when a solution carries more than one binding to the same board
    (`#2` etc, see `create`) — callers that need the EXACT binding look it up by the full `name` they were given,
    never by re-parsing `rest` as a board alone."""
    if '@' in (name or ''):
        sol, _, rest = name.partition('@')
        return sol, rest
    return name or '', ''


def _solution_dict(solution_name, manager=None):
    """One FirmwareSolution as a dict — the live row when a manager has it, else the pure seed (same duality as
    `cmod.custom.firmware.solution_for_graph`). None when no such solution exists."""
    if manager is not None:
        rows = [r for r in (manager.objectTables or {}).get('FirmwareSolution', {}).values() if getattr(r, 'name', '') == solution_name]
        if rows:
            r = rows[0]
            keys = ('name', 'title', 'graph', 'board_definition', 'board_variable', 'runtime', 'purpose', 'last_build')
            return {k: getattr(r, k, '') for k in keys}
    from cmod.cmod_seed import CMOD_SEED_PAIRS
    rows = next((rs for n, _c, rs in CMOD_SEED_PAIRS if n == 'FirmwareSolution'), [])
    hit = next((r for r in rows if r['name'] == solution_name), None)
    return dict(hit) if hit is not None else None


def _soc_of(board, manager=None):
    from board.custom import board_object as BO
    t = BO.tables_from_manager(manager) if manager is not None else BO.seed_tables()
    ident = next((b for b in t.get('BoardDefinition', []) if b.get('name') == BO.board_name(board)), None)
    return (ident or {}).get('soc_definition', '')


def chain_materialized(board):
    from board.custom import board_object as BO
    return BO.board_name(board) in CHAIN_MATERIALIZED_BOARDS


def default_board(solution_name, manager=None):
    """(board, exists, why) — the solution's own resolved board (`cmod.custom.firmware.resolve_board`); this is
    "the default binding's board" FirmwareSolution.board_definition/board_variable is now read as (§5h ruling)."""
    from cmod.custom import firmware as FW
    sol = _solution_dict(solution_name, manager=manager)
    if sol is None:
        return '', False, 'no FirmwareSolution %r (GET /api/firmware/solutions lists them)' % solution_name
    return FW.resolve_board(sol, manager=manager)


def live_bindings(solution_name, manager=None):
    """[HardwareBinding dict, …] already materialized on a live manager for one solution — empty with no manager
    (the pure path always re-derives the one default binding fresh, below)."""
    if manager is None:
        return []
    from cmod.cmod_firmware_api import FirmwareAPI
    keys = ('name', 'solution', 'board', 'soc', 'is_default', 'status', 'why', 'requirements_total',
            'requirements_met', 'assignments_refs_json', 'claims_refs_json', 'settings_refs_json', 'routes_refs_json',
            'last_build', 'provenance', 'notes')
    return [{k: getattr(r, k, '') for k in keys} for r in (manager.objectTables or {}).get('HardwareBinding', {}).values()
            if getattr(r, 'solution', '') == solution_name]


def _rows_for_binding(name, graph, manager=None):
    """This binding's OWN RegisterAssignment rows — live (filtered by `configuration` == this binding's name) when
    a manager has them, else the pure re-derivation (`cmod.custom.firmware.assignments_for`), same pure/live duality
    the rest of cmod uses."""
    if manager is not None:
        rows = [{k: getattr(r, k, '') for k in ('name', 'task', 'port', 'target_kind', 'lives_on', 'status',
                                                 'provenance', 'controls', 'peripheral', 'signal', 'bus', 'notes')}
                for r in (manager.objectTables or {}).get('RegisterAssignment', {}).values()
                if getattr(r, 'configuration', '') == name]
        if rows:
            return rows
    from cmod.custom import firmware as FW
    sol = name.partition('@')[0]
    return FW.assignments_for(graph, solution_name=sol, binding_name=name)


def assignment_rows(name, graph, manager=None):
    """Public: this binding's own RegisterAssignment rows (dicts) — the SAME derivation `validity()` uses
    internally. The bindings-create door (`cmod_firmware_api`) upserts these into the manager's own table so a
    later `.../assign` call (which only ever UPDATES an existing row, fs-0's own rule) finds them."""
    return _rows_for_binding(name, graph, manager=manager)


def validity(name, graph, board, manager=None):
    """(status, why[list], total, met, assignment_refs[list]) for one binding's own RegisterAssignment rows against
    its OWN board's own pins/SoC facts. status: valid (every required row met, no conflict/incompatibility);
    incomplete (some unmet, the board's chain is not materialized, or the board has no pin map at all — never a
    refusal); invalid (a conflict, or a row bound to something the board cannot do)."""
    from cmod.custom import targets as T
    from cmod.custom import firmware as FW
    from board.custom import board_object as BO
    from board.custom import target_compat as TC

    required = [t for t in T.derive(graph) if t.get('required')]
    # a DISPATCHER task (touches MORE THAN ONE pin of the same peripheral, e.g. 'send' writing UDR0 whose two
    # rows both carry uart-tx per the atom-level heuristic even though D0 is really RXD — §5h B1's own documented
    # "loose peripheral-level match, pre-existing") is checked for EXISTENCE on the board only, never the exact
    # per-pin kind match TC.compatible() would apply to a single-pin task — the same cooperation exemption
    # `cmod.custom.firmware._cooperates`/`_dispatchers` already give it for CONFLICT purposes, reused here so a
    # binding is never marked invalid by a loose label the rest of cmod already tolerates.
    dispatchers = FW._dispatchers(graph)
    total = len(required)
    if not board:
        return 'incomplete', ['no board resolved for this binding'], total, 0, []
    if not chain_materialized(board):
        why = ['the %s chain is not materialized (Phase 2) — no peripheral/register facts to check requirements against yet'
               % BO.board_name(board)]
        return 'incomplete', why, total, 0, []
    try:
        r = BO.rows_for(board)
    except BO.BoardObjectRefused as e:
        return 'incomplete', ['%s has no pin map yet (%s)' % (board, e)], total, 0, []

    pins_by_canon = {p['canonical']: p for p in r['pins']}
    soc_by_pin = {s['pin']: s for s in r.get('soc_pins', [])}
    rows = _rows_for_binding(name, graph, manager=manager)
    # ucd-0b2d (§5h, the HardwareBinding fix): a required row of resource_kind peripheral/signal is never pin-bound
    # (targets.py never guesses one) — it is met through this binding's own PeripheralClaims, computed once here
    # (never per-row), from a minimal binding-shaped dict (the same shape `derive()`/`chain_refs()` already pass).
    from cmod.custom import claims as C
    sol_name = name.partition('@')[0]
    periph_claims = C.peripheral_claims({'name': name, 'solution': sol_name, 'board': board, 'is_default': True},
                                         graph, manager=manager)

    def _peripheral_met(pid):
        return next((c for c in periph_claims if c['peripheral'] == pid), None) if pid else None

    def _signal_met(sig):
        """A RegisterAssignment ref | PeripheralClaim ref | None — this binding's own assignment rows carrying
        `sig` (its signal_route, or the typed `signal` column), OR a PeripheralClaim on the signal's OWN
        peripheral (his wording: 'a pin assignment carrying the RXD signal ... or a PeripheralClaim on USART0')."""
        if not sig:
            return None
        sig_name = sig.rsplit(':', 1)[-1]
        for a in rows:
            if a.get('signal') == sig or (a.get('signal_route') or '').endswith(':%s' % sig_name):
                return 'RegisterAssignment:%s' % a['name']
        periph = sig.rsplit(':', 1)[0]
        c = _peripheral_met(periph)
        return ('PeripheralClaim:%s' % c['name']) if c else None

    def _ordinal_keys(items, task_key, port_key):
        """{(task, port, i): item} — the i-th occurrence of (task, port) IN THE ORDER GIVEN. A task may carry
        SEVERAL rows with the SAME (task, port) pair (usart_init's D0/uart-rx and D1/uart-tx rows both have
        port='' — a pre-existing ambiguity in TargetDefinition itself, not introduced here — ucd-0c (Part 0) fixed
        the RegisterAssignment row's own NAME for this case, '<binding>:<task>@<canonical>', but that `name` is not
        what pairs a requirement with its assignment below); both `required` and this binding's own assignment
        `rows` are produced from the SAME `targets.derive()` order per task, so matching by ordinal position (never
        by (task, port) alone, and never by `lives_on` — a forced/person-edited row's `lives_on` may legitimately
        disagree with what the requirement expected; THAT disagreement is what this function must still let
        `validity()` see and report invalid, not silently miss as 'no match') pairs each requirement with its OWN
        assignment, never collapsing two distinct rows into one."""
        counts, out = {}, {}
        for it in items:
            k = (it.get(task_key, ''), it.get(port_key, '') or '')
            i = counts.get(k, 0)
            out[(k[0], k[1], i)] = it
            counts[k] = i + 1
        return out

    assignment_by_key = _ordinal_keys(rows, 'task', 'port')
    required_counts = {}
    why, met, refs = [], 0, []
    invalid, incomplete = False, False
    for t in required:
        label = t['node'] + ('.' + t['port'] if t.get('port') else ' (%s)' % t.get('requirement_kind', ''))
        resource_kind = t.get('resource_kind', 'undetermined')
        if resource_kind == 'peripheral':
            hit = _peripheral_met(t.get('peripheral', ''))
            if hit is None:
                why.append('%s: no PeripheralClaim for %s' % (label, t.get('peripheral') or t.get('requirement_kind', '')))
                incomplete = True
            else:
                met += 1
                refs.append('PeripheralClaim:%s' % hit['name'])
            continue
        if resource_kind == 'signal':
            ref = _signal_met(t.get('signal', ''))
            if ref is None:
                why.append('%s: no assignment or PeripheralClaim carries %s' % (label, t.get('signal') or t.get('requirement_kind', '')))
                incomplete = True
            else:
                met += 1
                refs.append(ref)
            continue
        k = (t['node'], t.get('port', '') or '')
        i = required_counts.get(k, 0)
        required_counts[k] = i + 1
        a = assignment_by_key.get((k[0], k[1], i))
        if a is None or a.get('lives_on', 'unbound') in ('', 'unbound'):
            why.append('%s: unbound (%s)' % (label, t.get('controls', '') or t.get('requirement_kind', '')))
            incomplete = True
            continue
        if a.get('status') == 'conflict':
            why.append('%s: %s' % (label, a.get('notes') or 'conflict'))
            invalid = True
            continue
        canonical = a['lives_on'].rpartition(':')[2]
        pin = pins_by_canon.get(canonical)
        if pin is None:
            why.append('%s: bound to %s, which %s does not have' % (label, a['lives_on'], BO.board_name(board)))
            invalid = True
            continue
        if t['node'] not in dispatchers:
            soc_pin = soc_by_pin.get(pin.get('soc_pin') or '')
            kind = t.get('requirement_kind', 'undetermined')
            verdict, reason = TC.compatible(kind, pin, soc_pin)
            if verdict == 'no':
                why.append('%s: %s' % (label, reason))
                invalid = True
                continue
        met += 1
        refs.append('RegisterAssignment:%s' % a['name'])
    status = 'invalid' if invalid else ('incomplete' if incomplete or why else 'valid')
    return status, why, total, met, refs


def chain_refs(b, graph, manager=None):
    """{claims_refs_json, settings_refs_json, routes_refs_json} — every PinClaim/PeripheralClaim/RegisterSetting/
    RegisterFieldSetting/SignalRoute row THIS binding's own claims produce (`cmod.custom.claims`, binding-aware,
    ucd-0b2b). Pure (manager=None) or live — same duality `cmod.custom.claims` itself has. `b` is the binding dict
    ALREADY built (name/solution/board/is_default) — never re-resolved here (that would recurse through `derive`)."""
    from cmod.custom import claims as C
    pins = C.pin_claims(b, graph, manager=manager)
    periph = C.peripheral_claims(b, graph, manager=manager)
    gen = C.register_settings(b, graph, manager=manager)
    claims_refs = ['PinClaim:%s' % c['name'] for c in pins] + ['PeripheralClaim:%s' % p['name'] for p in periph]
    settings_refs = (['RegisterSetting:%s' % s['name'] for s in gen['RegisterSetting']]
                      + ['RegisterFieldSetting:%s' % s['name'] for s in gen['RegisterFieldSetting']])
    routes_refs = ['SignalRoute:%s' % s['name'] for s in gen['SignalRoute']]
    return {'claims_refs_json': json.dumps(claims_refs), 'settings_refs_json': json.dumps(settings_refs),
            'routes_refs_json': json.dumps(routes_refs)}


def derive(solution_name, board=None, manager=None, is_default=None, provenance='derived', with_chain=True, name=None):
    """Build (never persist) one HardwareBinding dict for `solution_name` over `board` (default: the solution's own
    resolved board — "the default binding"). None when the solution does not exist. `name` overrides the computed
    '<solution>@<board>' (used by `create` for a second binding to the SAME board, '<solution>@<board>#2')."""
    sol = _solution_dict(solution_name, manager=manager)
    if sol is None:
        return None
    graph = sol.get('graph', '')
    def_board, exists, _why_board = default_board(solution_name, manager=manager)
    target_board = board or def_board
    default_flag = (target_board == def_board) if is_default is None else is_default
    name = name or (binding_name(solution_name, target_board) if target_board else solution_name)
    soc = _soc_of(target_board, manager=manager) if target_board else ''
    status, why, total, met, refs = validity(name, graph, target_board, manager=manager)
    out = {'name': name, 'solution': solution_name, 'board': target_board, 'soc': soc, 'is_default': default_flag,
           'status': status, 'why': '; '.join(why), 'requirements_total': total, 'requirements_met': met,
           'assignments_refs_json': json.dumps(refs), 'claims_refs_json': '[]', 'settings_refs_json': '[]',
           'routes_refs_json': '[]', 'last_build': sol.get('last_build', ''), 'provenance': provenance, 'notes': ''}
    if with_chain and target_board and chain_materialized(target_board):
        out.update(chain_refs(out, graph, manager=manager))
    return out


def resolve(target, manager=None):
    """One HardwareBinding dict for `target` ('<solution>' | '<solution>@<board-or-binding-name>') — the LIVE row
    when a manager already materialized one of that exact name, else freshly DERIVED (never persisted here). None
    when the solution itself does not exist."""
    sol_name, rest = parse_target(target)
    live = live_bindings(sol_name, manager=manager)
    if rest:
        hit = next((b for b in live if b['name'] == target), None)
        if hit is not None:
            return hit
        # 'rest' may be a bare board name ('arduino-uno-r3') naming the DEFAULT binding spelled out in full, or a
        # board a canvas binding has not been created for yet — either way, derive it fresh (never persisted)
        board = rest.partition('#')[0]
        return derive(sol_name, board=board, manager=manager)
    default_live = next((b for b in live if b.get('is_default')), None)
    if default_live is not None:
        return default_live
    return derive(sol_name, manager=manager)


def bindings_for_solution(solution_name, manager=None):
    """Every HardwareBinding of one solution — the live rows when a manager has any, else just the one derived
    default (the pure/seed-time path only ever has the one converged binding)."""
    live = live_bindings(solution_name, manager=manager)
    if live:
        return sorted(live, key=lambda b: b['name'])
    d = derive(solution_name, manager=manager)
    return [d] if d is not None else []


def create(solution_name, board, manager=None):
    """POST .../bindings {board}: a NEW HardwareBinding (provenance='canvas') for `solution_name` over `board` — a
    person's own addition, KEPT across a reseed (never converged away, his ruling: "A person may add another
    binding ... and it is KEPT"). Auto-suffixes the name ('<solution>@<board>#2', …) when a binding to that exact
    (solution, board) pair already exists (the default, or an earlier canvas one) — '<solution>@<board>' names ONE
    binding by itself; two bindings to the SAME board are distinguished by the suffix, never by silently replacing
    the first. -> the new binding dict (not yet written to the manager's tables — the caller upserts it, same idiom
    as `cmod_firmware_api._upsert`)."""
    sol = _solution_dict(solution_name, manager=manager)
    if sol is None:
        raise ValueError('no FirmwareSolution %r (GET /api/firmware/solutions lists them)' % solution_name)
    from board.custom import board_object as BO
    board = BO.board_name(board)
    base_name = binding_name(solution_name, board)
    existing_names = {b['name'] for b in bindings_for_solution(solution_name, manager=manager)}
    name = base_name
    n = 2
    while name in existing_names:
        name = '%s#%d' % (base_name, n)
        n += 1
    # the FINAL name (possibly suffixed) is fixed BEFORE validity/claims are computed, so every row this binding's
    # own rows produce is named from it consistently (never computed against base_name then renamed)
    return derive(solution_name, board=board, manager=manager, is_default=False, provenance='canvas', name=name)
