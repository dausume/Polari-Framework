"""
@module cmod.custom.pin_profiles

pp-0 (MISSION_PROFILE_SOLVER_PLAN.md §2.2, §7): PIN PROFILES PER PURPOSE - what a Purpose needs from one pin BEFORE any pin is chosen.
DERIVED every time, never stored; a person's correction is a `DerivedOverride` (who / when / why, cmod.custom.overrides) laid over the
derivation with the derived value kept beside it.

  Purpose -> its c-device tasks (graph nodes) -> each atom's targets (cmod.custom.targets.derive) -> a kind (board.custom.target_compat
  TASK_KINDS) -> grouped by the ROLE the pin serves (found on the bench circuit rows: cmod.custom.pin_profile_bench) -> a profile.

A profile = {id, purpose, task(s), kind, role, serves, signal {...}, drive {...}, timing {...}, lifecycle_phases, lifecycle, reserved, count,
origin, evidence, overrides}. VOCABULARY (PIN_VIEW_PLAN.md §2.8, his words 2026-10-17): DRIVE is electricity (current, supply, pulls, loads);
SIGNAL is what the pin carries (outputs/inputs, family). They are separate keys and neither uses the other's words.
Every number is cited (a Purpose criterion, a circuit row, a datasheet row) or `undetermined` with the reason; `evidence` names where each
field came from. A task that does not resolve to an atom target today is listed under `unresolved`, never invented a profile.

    python3 -m cmod.custom.pin_profiles purpose <name> [--json]
    python3 -m cmod.custom.pin_profiles mission <name> [--purposes a,b] [--json]
"""
import json
import re

from cmod.custom import pin_profile_bench as PB

IMPORTANCE = ('safety', 'required', 'important', 'desired')     # D-sys-2 (MISSION_PROFILE_SOLVER_PLAN.md §4 D-msp-1)
PHASE_ORDER = ('power-up', 'reset', 'bootloader', 'init', 'runtime', 'programming', 'debug')
#: words that belong to one side of the vocabulary and may not appear on the other (checked by the selftest)
SIGNAL_WORDS = ('output', 'outputs', 'input', 'inputs', 'uart', 'interrupt', 'edge', 'rx', 'tx', 'protocol', 'bidirectional')
DRIVE_WORDS = ('current', 'supply', 'source', 'sink', 'pull', 'load', 'ohm', 'resistor', 'ma')
#: the fields a DerivedOverride may correct (flat names -> where they live in the profile)
OVERRIDABLE = ('kind', 'role', 'count', 'drive_need', 'drive_load_class', 'drive_current_ma', 'signal_direction', 'debounce_ms', 'edge', 'latency_ms')


def undetermined(why):
    return {'value': 'undetermined', 'reason': why}


def _slug(text):
    return re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')


def _num(x):
    try:
        f = float(x)
        return int(f) if f == int(f) else f
    except (TypeError, ValueError):
        return x


# ------------------------------------------------------------------ rows
def find_purpose(name, manager=None):
    from cmod.custom import capabilities as CAP
    rows = PB.rows(manager, 'CapabilityDefinition', CAP.SEED_CAPABILITIES)
    return next((dict(c) for c in rows if c.get('name') == name), None)


def _criteria(cap):
    try:
        c = json.loads(cap.get('criteria_json') or '{}')
    except ValueError:
        c = {}
    return {x['key']: x for x in c.get('criteria', []) if isinstance(x, dict) and 'key' in x}, c.get('trigger') or {}


def _claims_by_pin(graph, manager):
    """{board pin canonical: PinClaim dict} for the graph's firmware solution binding (cmod.custom.claims - the pull / edge the firmware sets)."""
    try:
        from cmod.custom import binding as BND, claims as C, firmware as FW
        sol = FW.solution_for_graph(graph, manager=manager)
        if not sol:
            return {}
        b = next((b for b in BND.bindings_for_solution(sol['name'], manager=manager) if b.get('status') == 'valid'), None)
        return {c['board_pin'].rpartition(':')[2]: c for c in C.pin_claims(b, graph, manager=manager)} if b else {}
    except Exception:  # noqa: BLE001 - a missing claim chain is "undetermined", never a crash
        return {}


def _lifecycle(board, manager):
    from board.custom import lifecycle_uno as LU
    return [r for r in PB.rows(manager, 'PinLifecycleConstraint', LU.constraints()) if r.get('board') == board]


def _pin_dict(board, pin):
    from board.custom import board_object as BO
    r = BO.rows_for(board)
    p = next((x for x in r['pins'] if x['canonical'] == pin), None)
    return p, next((s for s in r['soc_pins'] if p and s['pin'] == p.get('soc_pin')), None), r


# ------------------------------------------------------------------ signal / drive / timing
def _signal(kind, bench_info):
    from board.custom import target_compat as TC
    from cmod.custom import targets as T
    role = T._ROLE_BY_KIND.get(kind, '')
    direction = {'input': 'inputs', 'receive': 'inputs', 'output': 'outputs', 'transmit': 'outputs'}.get(role)
    if direction is None and kind == 'i2c-sda':
        direction = 'bidirectional'
    sig = {'direction': direction or 'undetermined', 'family': kind.rsplit('-', 1)[0] if '-' in kind else kind}
    meta = next((r for r in TC.rows() if r['kind'] == kind), None)
    if meta:
        sig['detail'] = meta['description']
        sig['cite'] = meta['source_label']
    if bench_info and bench_info.get('signal_role') in ('input', 'output'):
        sig['bench_direction'] = 'inputs' if bench_info['signal_role'] == 'input' else 'outputs'
    return sig, ('target_compat kind %s (%s)' % (kind, meta['source_label'] if meta else 'no citation')
                 if direction else 'undetermined - the %s kind does not say which end carries the signal' % kind)


def _logic_volts(board):
    from board.custom import electrical_check as EC
    return EC.BOARD_LOGIC_LEVEL_V.get(board)


def _limit(board, pin):
    try:
        from board.custom import board_object as BO, electrical_hw as EH
        t = BO.seed_tables()
        pad, _sp = EH.pad_class_of(t, pin)
        ma, row = EH._recommended_ma(t, pad, EH.DEFAULT_VCC)
        return {'ma': ma, 'limit_class': 'recommended', 'cite': '%s, %s' % (row['document'], row['page_table'])} if row else None
    except Exception:  # noqa: BLE001
        return None


def _drive(kind, board, pin, info, claim, lifecycle_rows):
    """(drive dict, evidence string). need: source-current | sink-current | pull-up | pull-down | high-impedance | supply | none | undetermined."""
    d = {'need': 'undetermined', 'load_class': 'undetermined', 'current': undetermined('no current is cited for this pin')}
    ev = []
    if kind in ('digital-out', 'pwm-out'):
        if info and info.get('load', {}).get('part'):
            ld = info['load']
            d['load_class'] = info['load_class']
            d['need'] = 'source-current' if ld['terminal'] == 'anode' else 'sink-current'
            d['load'] = {'part': ld['part'], 'series_parts': ld['series_parts'], 'series_ohms': ld['series_ohms']}
            vf, basis, v = ld.get('v_forward'), ld.get('v_forward_basis'), _logic_volts(board)
            if vf is not None and basis not in ('assumed', 'undetermined', None) and ld['series_ohms'] and v:
                d['current'] = {'value': round((v - vf) / ld['series_ohms'] * 1000.0, 2), 'unit': 'mA',
                                'reason': '(%s V board rail - %s V cited forward voltage) / %s ohm' % (v, vf, ld['series_ohms'])}
            else:
                d['current'] = undetermined("the LED's forward voltage is only %s (%s V in %s), not cited, so the current is not worked out"
                                            % (basis or 'undetermined', vf, ld['part']))
                if v and ld['series_ohms']:
                    d['current']['ceiling_ma'] = round(v / ld['series_ohms'] * 1000.0, 1)
                    d['current']['ceiling_basis'] = ('board rail %s V / %s ohm in %s: a ceiling that needs no forward voltage, not a design target'
                                                     % (v, ld['series_ohms'], ', '.join(ld['series_parts'])))
            lim = _limit(board, pin)
            if lim:
                d['limit'] = lim
            ev.append('; '.join(info['evidence']))
        else:
            d['load_class'] = 'undetermined'
            d['current'] = undetermined('no circuit row describes what this pin feeds')
            ev.append('undetermined - no bench circuit row for pin %s' % (pin or '(not yet chosen)'))
    elif kind in ('interrupt-in', 'digital-in'):
        pull = (claim or {}).get('pull')
        if info:
            d['load_class'] = info['load_class']
        if pull in ('up', 'down'):
            d['need'] = 'pull-%s' % pull
            d['pull'] = {'where': 'on the chip (PinClaim %s)' % claim['name'], 'external_parts': (info or {}).get('load', {}).get('external_pull_parts', [])}
            d['current'] = undetermined('the pull current is not a Purpose criterion; the chip pull resistance is cited by the electrical rows, not worked out here')
            ev.append('PinClaim %s pull=%s%s' % (claim['name'], pull, '; ' + '; '.join(info['evidence']) if info else ''))
        elif pull == 'none':
            d['need'] = 'high-impedance'
            d['current'] = undetermined('no pull is claimed (PinClaim %s pull=none), so there is no pull current; the pin leakage is a datasheet row, not worked out here' % claim['name'])
            ev.append('PinClaim %s pull=none%s' % (claim['name'], '; ' + '; '.join(info['evidence']) if info else ''))
        else:
            d['current'] = undetermined('no PinClaim states a pull for this pin (%s)' % (pin or 'not yet chosen'))
            ev.append('undetermined - no PinClaim pull for %s' % (pin or 'the pin'))
    elif kind in ('uart-rx', 'uart-tx'):
        rows = [r for r in lifecycle_rows if r.get('policy') == 'reserved' and 'transport=' in (r.get('condition') or '')]
        d['need'] = 'high-impedance' if kind == 'uart-rx' else 'source-current'
        d['load_class'] = 'a line to the USB-serial bridge, through a series resistor' if rows else 'undetermined'
        d['current'] = undetermined('no current is cited for the serial line')
        ev.append(('PinLifecycleConstraint %s' % rows[0]['name']) if rows else 'undetermined - no lifecycle row describes the line')
    else:
        ev.append('undetermined - no drive rule written for kind %s' % kind)
    return d, '; '.join(ev) or 'undetermined'


def _field(criteria, key, applies, what, purpose):
    if not applies:
        return {'value': 'not applicable', 'reason': what}
    c = criteria.get(key)
    if c is None:
        return undetermined('Purpose %s has no %s criterion' % (purpose, key))
    return {'value': c.get('value'), 'unit': c.get('unit', ''), 'criterion': key, 'from': 'Purpose %s criteria' % purpose}


def _timing(kind, info, claim, criteria, trigger, purpose):
    is_switch = bool(info and info.get('role') == 'the button')
    edge = (claim or {}).get('edge')
    if kind != 'interrupt-in':
        t_edge = {'value': 'not applicable', 'reason': 'not an interrupt line'}
    elif edge and edge != 'undetermined':
        t_edge = {'value': edge, 'from': 'PinClaim %s' % claim['name']}
    else:
        t_edge = undetermined('no PinClaim states the edge')
    lat = 'max_latency_ms' if 'max_latency_ms' in criteria else ('freshness_ms' if 'freshness_ms' in criteria else 'max_latency_ms')
    t_lat = _field(criteria, lat, True, '', purpose)
    if 'criterion' in t_lat:
        t_lat['scope'] = 'the whole path from the trigger to the outcome, not this pin alone'
    t_rate = _field(criteria, 'rate_hz', True, '', purpose)
    if 'criterion' not in t_rate and trigger.get('kind') == 'period':
        t_rate['reason'] += ' (the trigger says "%s" in words only)' % trigger.get('what', '')
    return {'edge': t_edge, 'rate': t_rate, 'latency': t_lat,
            'debounce': _field(criteria, 'debounce_ms', is_switch, 'not a mechanical contact', purpose)}


def _timing_evidence(t):
    out = []
    for k, v in t.items():
        if v['value'] == 'undetermined':
            out.append('%s: undetermined - %s' % (k, v.get('reason', '')))
        elif v['value'] == 'not applicable':
            out.append('%s: not applicable (%s)' % (k, v.get('reason', '')))
        else:
            out.append('%s: %s %s (%s)' % (k, v['value'], v.get('unit', ''), v.get('criterion') and 'criterion ' + v['criterion'] or v.get('from', '')))
    return '; '.join(out)


# ------------------------------------------------------------------ the derivation
def _entries(cap, manager):
    """Walk the Purpose's c-device tasks into target entries + the tasks that gave none."""
    from board.custom import target_compat as TC
    from cmod.custom import targets as T
    from cmod.custom.graph_seed import seed_graph
    try:
        refs = json.loads(cap.get('tasks_by_runtime_json') or '{}')
    except ValueError:
        refs = {}
    entries, unresolved, other = [], [], []
    for runtime, lst in refs.items():
        if runtime != 'c-device':
            other += [{'task': t, 'why': 'runs in %s, on the host side: it takes no pin' % runtime} for t in lst]
    by_graph = {}
    for ref in refs.get('c-device') or []:
        g, _, n = ref.partition(':')
        by_graph.setdefault(g, []).append(n)
    for graph, nodes in by_graph.items():
        seed = seed_graph(graph) or {'graph': {}, 'nodes': []}
        board = seed['graph'].get('board', '')
        node_rows = {n['instance']: n for n in seed['nodes']}
        atoms = T._manifest_atoms(seed['graph'].get('project', ''))
        derived = T.derive(graph, manager)
        claims = _claims_by_pin(graph, manager)
        for node in nodes:
            nrow = node_rows.get(node)
            rows = [r for r in derived if r['node'] == node]
            if nrow is None:
                unresolved.append({'task': '%s:%s' % (graph, node), 'why': 'the graph has no node %s' % node})
            elif nrow.get('kind') != 'c-atom':
                unresolved.append({'task': '%s:%s' % (graph, node), 'why': 'a %s node, not a C atom: it takes no pin' % nrow.get('kind')})
            elif not rows:
                unresolved.append({'task': '%s:%s' % (graph, node), 'why': 'the atom touches no register, pin or declared resource'})
            atom = atoms.get((nrow or {}).get('atom', '').partition(':')[2]) if nrow else None
            atom_kind = T._atom_requirement_kind(atom) if atom else 'undetermined'
            for r in rows:
                e = {'graph': graph, 'board': board, 'task': node, 'row': r, 'kind': r['requirement_kind'], 'claims': claims,
                     'phase': 'init' if (nrow or {}).get('stage') == 'init' else 'runtime',
                     'stage': (nrow or {}).get('stage', ''), 'pin': r['lives_on'].rpartition(':')[2] if r['lives_on'] != 'unbound' else '',
                     'ignored': '', 'weak': False}
                if r['kind'] == 'memory-field':
                    unresolved.append({'task': '%s:%s' % (graph, node), 'why': 'writes a memory field of the generated glue, not a pin'})
                    continue
                if r.get('resource_kind') == 'peripheral':
                    unresolved.append({'task': '%s:%s' % (graph, node), 'why': 'needs the whole peripheral %s (kind %s), not a pin' % (r['peripheral'], r['requirement_kind'])})
                    continue
                if e['kind'] in ('', 'undetermined'):
                    unresolved.append({'task': '%s:%s' % (graph, node), 'why': 'its atom does not say which kind of pin it needs'})
                    continue
                if e['pin']:
                    pin, soc, _r = _pin_dict(board, e['pin'])
                    verdict, why = TC.compatible(e['kind'], pin, soc) if pin else ('undetermined', 'no BoardPin row')
                    if verdict == 'no':
                        e['ignored'] = why
                    # the kind came only from the pin's alternate function: the atom itself did not settle it
                    e['weak'] = atom_kind == 'undetermined' and (pin or {}).get('signal') not in T._SIGNAL_KIND and not node.endswith('_init')
                entries.append(e)
    return entries, unresolved, other


def _role_of(e, benches):
    info = benches.get((e['board'], e['pin'])) if e['pin'] else None
    if info and info['role']:
        return info['role'], info, 'bench circuit rows: %s' % '; '.join(info['evidence'][:2])
    if e['kind'] in ('uart-rx', 'uart-tx'):
        return 'the transport', info, 'kind %s is a serial line; the host participant reaches the board over it' % e['kind']
    return 'undetermined', info, 'undetermined - pin %s is on no bench circuit net' % (e['pin'] or '(not yet chosen)')


def derive_profiles(purpose, manager=None, apply_overrides=True):
    """-> {'purpose', 'profiles': [...], 'unresolved': [...], 'other_runtime': [...]} for one Purpose (a name or the Purpose dict)."""
    cap = purpose if isinstance(purpose, dict) else find_purpose(purpose, manager)
    if cap is None:
        raise ValueError('no Purpose named %r (pol capability list)' % purpose)
    name = cap['name']
    criteria, trigger = _criteria(cap)
    entries, unresolved, other = _entries(cap, manager)
    benches = {}
    for e in entries:
        if (e['board'], e['pin']) not in benches:
            b = PB.bench(e['board'], manager)
            benches.update({(e['board'], p): i for p, i in b.items()})
    groups, order = {}, []
    ignored = []
    for e in entries:
        if e['ignored']:
            ignored.append({'task': e['task'], 'pin': e['pin'], 'why': 'dropped: %s' % e['ignored']})
            continue
        role, info, role_ev = _role_of(e, benches)
        e['role'], e['info'], e['role_ev'] = role, info, role_ev
        key = (role, e['kind'])
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append(e)
    # a kind taken only from the pin's alternate function is folded into a settled kind of the same role
    for key in list(order):
        role, kind = key
        if all(e['weak'] for e in groups[key]) and any(k[0] == role and k != key and not all(x['weak'] for x in groups[k]) for k in order):
            host = next(k for k in order if k[0] == role and k != key and not all(x['weak'] for x in groups[k]))
            for e in groups[key]:
                e['folded_from'] = kind
            groups[host] += groups.pop(key)
            order.remove(key)
    profiles = []
    for key in order:
        profiles.append(_profile(name, key, groups[key], criteria, trigger, manager))
    profiles += _bench_observers(name, profiles, entries, benches, criteria, trigger, manager)
    # the sense line is wired to the LED line: only the bench observers need it, so they are added once per net
    if apply_overrides:
        profiles = [apply_corrections(p, manager) for p in profiles]
    return {'purpose': name, 'title': cap.get('title', ''), 'profiles': profiles, 'unresolved': _uniq(unresolved), 'ignored': _uniq(ignored),
            'other_runtime': other}


def _uniq(rows):
    seen, out = set(), []
    for r in rows:
        k = json.dumps(r, sort_keys=True)
        if k not in seen:
            seen.add(k)
            out.append(r)
    return out


def _profile(purpose, key, es, criteria, trigger, manager):
    role, kind = key
    first = next((e for e in es if not e['weak']), es[0])
    info = first['info']
    pin_hint = first['pin']
    claim = first['claims'].get(pin_hint) if pin_hint else None
    lifecycle_pins = [e['pin'] for e in es if e['pin']]
    board = first['board']
    life_rows = _lifecycle(board, manager)
    if kind in ('uart-rx', 'uart-tx'):       # the kind names no pin: every pin that can carry it
        from board.custom import board_object as BO, target_compat as TC
        r = BO.rows_for(board)
        lifecycle_pins = [v['pin'] for v in TC.valid_targets(kind, r) if v['verdict'] == 'ok']
    constraints = [{'name': r['name'], 'phase': r['phase'], 'policy': r['policy'], 'condition': r.get('condition', '')}
                   for r in life_rows if r.get('pin') in lifecycle_pins and r['policy'] != 'free']
    signal, sig_ev = _signal(kind, info)
    drive, drive_ev = _drive(kind, board, pin_hint, info, claim, [r for r in life_rows if r.get('pin') in lifecycle_pins])
    timing = _timing(kind, info, claim, criteria, trigger, purpose)
    phases = sorted({e['phase'] for e in es}, key=PHASE_ORDER.index)
    tasks = []
    for e in es:
        if e['task'] not in tasks:
            tasks.append(e['task'])
    task = next((e['task'] for e in es if e['phase'] == 'runtime' and not e['weak']), tasks[0])
    reserved = any(c['policy'] == 'reserved' and c['condition'] == 'transport=usb-serial' for c in constraints)
    folded = sorted({'%s (task %s touches the same pin; its atom does not settle a kind)' % (e['folded_from'], e['task']) for e in es if e.get('folded_from')})
    rows_ev = ['%s:%s%s' % (e['graph'], e['row']['port_ref'], (' -> ' + e['pin']) if e['pin'] else ' (no pin yet)') for e in es]
    settled = 'settled by the atom' if not first['weak'] else 'taken from the pin\'s alternate function only (the atom does not settle it)'
    return {
        'id': '%s:%s:%s' % (purpose, _slug(role), kind), 'purpose': purpose, 'task': task, 'tasks': tasks, 'kind': kind, 'role': role,
        'serves': 'the host and Polari, over the transport' if role == 'the transport' else ('the bench circuit %s' % info['circuit'] if info else 'undetermined'),
        'signal': signal, 'drive': drive, 'timing': timing, 'lifecycle_phases': phases, 'lifecycle': constraints, 'reserved': reserved, 'count': 1,
        'origin': 'task',
        'evidence': {'kind': 'target rows %s; %s; kind %s' % (', '.join(rows_ev), settled, kind) + ('; folded in: ' + ', '.join(folded) if folded else ''),
                     'role': first['role_ev'], 'signal': sig_ev, 'drive': drive_ev, 'timing': _timing_evidence(timing),
                     'lifecycle_phases': 'graph node stage of %s: %s' % (', '.join(tasks), ', '.join('%s=%s' % (e['task'], e['stage'] or '?') for e in es[:4])),
                     'lifecycle': ('PinLifecycleConstraint rows on %s' % ', '.join(sorted(set(lifecycle_pins)))) if constraints else 'no lifecycle constraint on the pins considered',
                     'count': 'one pin per role: tasks %s share it' % ', '.join(tasks)},
        'overrides': []}


def _bench_observers(purpose, profiles, entries, benches, criteria, trigger, manager):
    """The bench wires another pin to a line this Purpose drives at run time (D3 listens to D6): that listener is a profile of the
    Purpose too. Its task is undetermined - no task of the Purpose's own graph reads it."""
    out, seen = [], set()
    for p in profiles:
        if p['role'] != 'the LED' or 'runtime' not in p['lifecycle_phases']:
            continue
        e = next(x for x in entries if x['task'] in p['tasks'] and x['pin'])
        driver_info = benches.get((e['board'], e['pin']))
        for (board, pin), info in benches.items():
            if board != e['board'] or not info or info.get('observes') != e['pin'] or pin in seen:
                continue
            seen.add(pin)
            kind, ref, claim = _observer_kind(board, pin, manager)
            sig, sig_ev = _signal(kind, info) if kind != 'undetermined' else ({'direction': 'inputs', 'family': 'undetermined'}, 'undetermined - no atom target names a kind for %s' % pin)
            drive, drive_ev = _drive(kind, board, pin, info, claim, [])
            timing = _timing(kind, info, claim, criteria, trigger, purpose)
            out.append({
                'id': '%s:%s:%s' % (purpose, _slug(info['role']), kind), 'purpose': purpose,
                'task': 'undetermined - no task of this Purpose reads the line; the bench wires it', 'tasks': [], 'kind': kind, 'role': info['role'],
                'serves': 'the bench circuit %s (it listens to the line the %s drives)' % (info['circuit'], driver_info['role'] if driver_info else 'pin'),
                'signal': dict(sig, bench_direction='inputs'), 'drive': drive, 'timing': timing, 'lifecycle_phases': ['runtime'], 'lifecycle': [],
                'reserved': False, 'count': 1, 'origin': 'bench',
                'evidence': {'kind': ref or 'undetermined - no atom target names this pin', 'role': 'bench circuit rows: %s' % '; '.join(info['evidence']),
                             'signal': sig_ev, 'drive': drive_ev, 'timing': _timing_evidence(timing),
                             'lifecycle_phases': 'the line is driven at run time by %s (%s)' % (e['pin'], p['id']),
                             'lifecycle': 'no lifecycle row names pin %s' % pin, 'count': 'one pin: the bench wire lands on one pin'},
                'overrides': []})
    return out


def _observer_kind(board, pin, manager):
    """(kind, evidence, PinClaim) for a bench listener, from a graph whose atom already targets that pin (the bench graph's sense task)."""
    from cmod.custom import graph_seed as GS, targets as T
    for graph in (GS.BC_GRAPH, GS.GRAPH):
        for r in T.derive(graph, manager):
            if r['lives_on'].endswith(':' + pin) and r['requirement_kind'] not in ('', 'undetermined') and r['kind'] != 'memory-field':
                return r['requirement_kind'], 'target %s:%s -> %s (a task of graph %s, not of this Purpose)' % (graph, r['port_ref'], pin, graph), _claims_by_pin(graph, manager).get(pin)
    return 'undetermined', '', None


# ------------------------------------------------------------------ DerivedOverride corrections
def flat_view(p):
    """The overridable fields of one profile as a flat row {name: id, kind, role, ...} - what a DerivedOverride addresses."""
    cur = p['drive'].get('current', {})
    return {'name': p['id'], 'kind': p['kind'], 'role': p['role'], 'count': p['count'], 'drive_need': p['drive']['need'],
            'drive_load_class': p['drive']['load_class'], 'drive_current_ma': cur.get('value', 'undetermined'),
            'signal_direction': p['signal']['direction'], 'debounce_ms': p['timing']['debounce'].get('value', ''),
            'edge': p['timing']['edge'].get('value', ''), 'latency_ms': p['timing']['latency'].get('value', '')}


def apply_corrections(p, manager=None):
    """A copy of profile `p` with every ACTIVE DerivedOverride of class PinProfile laid over it (cmod.custom.overrides.apply_overrides is the one
    mechanism): the corrected value replaces the derived one, `derived_*` stays beside it in `overrides` with who / when / why."""
    if manager is None:
        return p
    from cmod.custom import overrides as OV
    hits = OV.active_overrides('PinProfile', manager).get(p['id'])
    if not hits:
        return p
    flat = OV.apply_overrides([flat_view(p)], 'PinProfile', manager)[0]
    q = json.loads(json.dumps(p))
    for o in sorted(hits, key=lambda x: getattr(x, 'when', '')):
        f = getattr(o, 'field', '')
        if f not in OVERRIDABLE or 'derived_%s' % f not in flat:
            continue
        v = _num(flat[f]) if f in ('count', 'drive_current_ma', 'debounce_ms', 'latency_ms') else flat[f]
        if f in ('kind', 'role', 'count'):
            q[f] = v
        elif f == 'drive_need':
            q['drive']['need'] = v
        elif f == 'drive_load_class':
            q['drive']['load_class'] = v
        elif f == 'drive_current_ma':
            q['drive']['current'] = {'value': v, 'unit': 'mA', 'reason': "corrected by a person (%s); the derivation said %s" % (getattr(o, 'who', '') or 'unauthenticated', flat['derived_%s' % f])}
        elif f == 'signal_direction':
            q['signal']['direction'] = v
        else:
            key = {'debounce_ms': 'debounce', 'edge': 'edge', 'latency_ms': 'latency'}[f]
            q['timing'][key] = {'value': v, 'unit': 'ms' if f != 'edge' else '', 'from': 'a person\'s correction', 'corrected': True}
        why = 'corrected by %s on %s: %s (derived: %s)' % (getattr(o, 'who', '') or 'an unauthenticated request', (getattr(o, 'when', '') or '')[:10],
                                                          getattr(o, 'why', ''), flat['derived_%s' % f])
        q['overrides'].append({'field': f, 'derived': flat['derived_%s' % f], 'corrected': v, 'who': getattr(o, 'who', ''), 'when': getattr(o, 'when', ''),
                               'why': getattr(o, 'why', ''), 'ref': 'DerivedOverride:%s' % getattr(o, 'name', '')})
        ev_key = {'kind': 'kind', 'role': 'role', 'count': 'count', 'drive_need': 'drive', 'drive_load_class': 'drive', 'drive_current_ma': 'drive',
                  'signal_direction': 'signal', 'debounce_ms': 'timing', 'edge': 'timing', 'latency_ms': 'timing'}[f]
        q['evidence'][ev_key] = '%s - %s: %s' % (q['evidence'].get(ev_key, ''), f, why)
    return q


# ------------------------------------------------------------------ table rows + CLI
def summary(p):
    """One plain-words row of a profile (no JSON): what the page tables and the CLI show."""
    d, t, s = p['drive'], p.get('timing'), p['signal']
    cur = d.get('current', {})
    cur_txt = ('%s %s' % (cur['value'], cur.get('unit', ''))).strip() if cur.get('value') != 'undetermined' else 'undetermined (%s)' % cur.get('reason', '')
    if cur.get('ceiling_ma') is not None and cur.get('value') == 'undetermined':
        cur_txt += '; ceiling %s mA' % cur['ceiling_ma']
    tm = []
    for k in ('edge', 'debounce', 'latency', 'rate'):
        vals = [t[k]] if 'timing' in p else [x[k] for x in p.get('timing_by_purpose', {}).values()]
        txt = []
        for v in vals:
            if v.get('value') == 'not applicable':
                continue
            one = 'undetermined' if v['value'] == 'undetermined' else ('%s %s' % (v['value'], v.get('unit', ''))).strip()
            if one not in txt:
                txt.append(one)
        if txt:
            tm.append('%s %s' % (k, ' / '.join(txt)))
    return {'profile': p['id'], 'purpose': p.get('purpose') or ', '.join(p.get('purposes', [])), 'role': p['role'], 'kind': p['kind'],
            'signal': '%s, %s' % (s['direction'], s['family']), 'drive': '%s; %s; current %s' % (d['need'], d['load_class'], cur_txt),
            'timing': '; '.join(tm) or 'none', 'phases': ', '.join(p['lifecycle_phases']), 'reserved': 'yes' if p.get('reserved') else 'no',
            'importance': p.get('importance', ''), 'origin': p.get('origin', ''), 'count': p['count'],
            'corrections': '; '.join('%s: %s -> %s (%s, %s)' % (o['field'], o['derived'], o['corrected'], o['who'] or 'unauthenticated', o['why'])
                                      for o in (p.get('overrides') or [])) or 'none',
            'evidence': ' | '.join('%s: %s' % (k, v) for k, v in p['evidence'].items() if isinstance(v, str)) if isinstance(p['evidence'], dict) and p.get('purpose') else
                        ' | '.join(p.get('evidence_summary', []))}


def _print_profiles(res):
    for p in res['profiles']:
        s = summary(p)
        print('  %-26s %-13s signal %-22s' % (s['role'], s['kind'], s['signal']))
        print('       drive     %s' % s['drive'])
        print('       timing    %s   phases: %s   reserved: %s   count %s' % (s['timing'], s['phases'] or '-', s['reserved'], s['count']))
        for k, v in p['evidence'].items():
            print('       evidence  %-16s %s' % (k, v))
        for o in p.get('overrides') or []:
            print('       corrected %s: %s -> %s by %s on %s: %s' % (o['field'], o['derived'], o['corrected'], o['who'] or '-', (o['when'] or '')[:10], o['why']))


def main(argv=None):
    import argparse
    import sys
    ap = argparse.ArgumentParser(prog='pol capability pins')
    sub = ap.add_subparsers(dest='cmd', required=True)
    sub.add_parser('purpose').add_argument('name')
    pm = sub.add_parser('mission')
    pm.add_argument('name')
    pm.add_argument('--purposes', default='', help='a,b - explicit Purposes when no HardwareMission row of that name exists')
    for p in sub.choices.values():
        p.add_argument('--json', action='store_true')
    a = ap.parse_args(argv)
    try:
        if a.cmd == 'purpose':
            res = derive_profiles(a.name)
            if a.json:
                print(json.dumps(res, indent=2))
                return 0
            print('Pin profiles of Purpose %s - %s' % (a.name, res['title']))
            _print_profiles(res)
            for u in res['unresolved'] + res['ignored']:
                print('  no profile: %s - %s' % (u['task'], u['why']))
            return 0
        from cmod.custom import pin_profile_mission as PM
        res = PM.mission_profiles(a.name, purposes=[x for x in a.purposes.split(',') if x] or None)
        if a.json:
            print(json.dumps(res, indent=2))
            return 0
        print('Pin profiles of Mission %s (%d Purposes, %d distinct profiles)' % (a.name, len(res['purposes']), len(res['profiles'])))
        for p in res['profiles']:
            s = summary(p)
            print('  %-16s %-13s %-9s %-22s reserved %-3s purposes: %s' % (s['role'], s['kind'], s['importance'], s['signal'], s['reserved'], s['purpose']))
        return 0
    except ValueError as e:
        print('[REFUSED] %s' % e)
        return 3


if __name__ == '__main__':
    import sys
    sys.exit(main(sys.argv[1:]))
