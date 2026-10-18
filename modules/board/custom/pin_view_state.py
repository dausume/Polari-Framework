"""
@module board.custom.pin_view_state

pv-0 (PIN_VIEW_PLAN.md 2.3 / 2.8 / 2.9): THE STATE the pin view paints on the structure of pin_view_model — the composition STAGE of every pin, the protocol FILTER, and the three SEPARATE summaries of
every connection (his correction 2.8: "drive means electricity flow and supply, signals are different"):

  DRIVE   (DrivePotential)   who is supplied / sources and sinks current / returns, the rail and domain as WORDS, the pull, and the verdict CLASS of the relevant limit
                             (within-recommended | undetermined | over | unchecked) — NO numbers; the numbers are the electrical view's. The class is read from the electrical rules'
                             own findings (board.custom.electrical_check, via hwsys_context.Ctx) — never re-implemented here.
  SIGNAL  (SignalPotential)  which end OUTPUTS and which INPUTS the signal, the protocol signal it carries and its family (the colour). Signal-direction words only.
  USE                        the tasks that claim the line, the Purposes they serve, the stage.

STAGES (2.9): `base` (nothing claimed: every pin unassigned or available — chip blank / board as delivered), `after-init` (only the Initialization Purpose's tasks' claims, as proposed),
`tasks-assigned` (a binding's PinClaims as proposed — today the graph-node claims; Task definitions on a Mission arrive with fgm-3), `firmware-committed` (the binding's committed
RegisterFieldSetting / SignalRoute rows make those claims committed). A pin's stage is one of unassigned | available | proposed | committed.

Everything is DERIVED on every read; nothing is stored. A check that has not run says `unchecked`.
"""
import json
import re

from board.custom import ladder as LD
from board.custom import pv_families as F
from board.custom import reachability as RA

STAGES = ('base', 'after-init', 'tasks-assigned', 'firmware-committed')
PIN_STAGES = ('unassigned', 'available', 'proposed', 'committed')
RANK = {s: i for i, s in enumerate(PIN_STAGES)}
DRIVE_RULES = ('led_current', 'voh_under_load', 'power_budget', 'abs_max_not_target')   # the electrical rules that are DRIVE (current and supply), not signal levels
CLASS = {'ok': 'within-recommended', 'undetermined': 'undetermined', 'blocked': 'over', 'conditional': 'over', 'unchecked': 'unchecked'}
SIGNAL_DIR = {'in': 'inputs', 'out': 'outputs', 'inout': 'bidirectional', 'undetermined': 'undetermined'}
POWER_LABEL_ROLE = {'+5V': 'supplies', '+3V3': 'supplies', 'VIN': 'supplies', 'IOREF': 'reference', 'AREF': 'reference', 'GND': 'returns', 'NC': 'unconnected'}
PRIORITY = ('uart', 'spi', 'i2c', 'usb', 'analog', 'clock', 'reset-programming', 'pwm-timer', 'interrupt', 'gpio')


class PinViewError(ValueError):
    pass


# ---------------------------------------------------------------- claims (the binding's, from cmod)
def claims_of(ctx, binding, tables):
    """-> (claims, committed_pin_claims, why): the binding's PinClaims, the PinClaim names its committed settings / routes cite, and a reason when something could not be read."""
    if not binding:
        return [], set(), 'no binding in the request or the system'
    from board.custom import electrical_check as EC
    et = LD._etables(tables, ctx.cache)
    _board, claims = ctx.cache.setdefault(('claims', binding), EC._resolve(binding, et))
    if not claims:
        return [], set(), 'binding %s resolved to no PinClaim (unknown binding, or a graph without pin tasks)' % binding
    committed, why = set(), ''
    try:
        from cmod.custom import binding as BND
        from cmod.custom import claims as C
        b = BND.resolve(binding, manager=tables.get('_manager'))
        graph = (BND._solution_dict(b['solution'], manager=tables.get('_manager')) or {}).get('graph', '')
        gen = C.register_settings(b, graph, manager=tables.get('_manager'))
        committed = {x['pin_claim'] for x in gen['RegisterFieldSetting'] if x.get('pin_claim')} | {x['pin_claim'] for x in gen['SignalRoute'] if x.get('pin_claim')}
    except Exception as e:   # noqa: BLE001 — a failing source says so; the stage then reads proposed only
        why = 'committed settings could not be read (%s: %s)' % (type(e).__name__, e)
    return claims, committed, why


def purposes_by_task(ctx, binding, tables):
    """{task name: [purpose names]} and the Initialization Purpose's task names, from the cmod Purposes of the binding's graph."""
    out, init, why = {}, set(), ''
    try:
        from cmod.custom import binding as BND
        from cmod.custom import capabilities as CAP
        b = BND.resolve(binding, manager=tables.get('_manager')) if binding else None
        graph = (BND._solution_dict(b['solution'], manager=tables.get('_manager')) or {}).get('graph', '') if b else ''
        if not graph:
            return out, init, 'no graph behind the binding: Purposes cannot be read'
        for p in CAP.purposes_for_graph(graph, tables.get('_manager')):
            if p.get('lifecycle') == 'retired':
                continue
            tasks = [t.rpartition(':')[2] for refs in json.loads(p.get('tasks_by_runtime_json') or '{}').values() for t in refs]
            for t in tasks:
                out.setdefault(t, []).append(p['name'])
            if p['name'] == 'initialization':
                init = set(tasks)
        if not init:
            why = 'no Initialization Purpose over graph %s: the init tasks cannot be separated' % graph
    except Exception as e:   # noqa: BLE001
        why = 'Purposes could not be read (%s: %s)' % (type(e).__name__, e)
    return out, init, why


# ---------------------------------------------------------------- stages
def _push(model, ref, stage, why, consumers):
    p = model.pins.get(ref)
    if p is None:
        return
    if RANK[stage] >= RANK[p['stage']]:
        if RANK[stage] > RANK[p['stage']] or not p['stage_why']:
            p['stage'], p['stage_why'] = stage, why
    for c in consumers:
        if c not in p['consumers']:
            p['consumers'].append(c)


def _outward(model, pad_ids):
    """die pad -> its legs -> the header pins of those legs (pad-to-leg, then to-header): the same line at every level."""
    legs = {pad: [c['b'] for c in model.connections if c['kind'] == 'pad-to-leg' and c['a'] == pad] for pad in pad_ids}
    out = {}
    for pad, ls in legs.items():
        refs = list(ls)
        for leg in ls:
            refs += [c['b'] for c in model.connections if c['kind'] == 'to-header' and c['a'] == leg and model.pins[c['b']]['level'] == 'board']
        out[pad] = refs
    return out


def apply_stage(model, tables, ctx, stage, binding, board):
    """Sets stage / consumers on every pin. Returns the response's `stage` block (what was read, what is undetermined and why)."""
    reach = {p['soc_pin']: p for p in RA.reach(board, tables)['pins']}
    pads = [p['id'] for p in model.pins.values() if p['level'] == 'die']
    line = _outward(model, pads)
    for pad in pads:   # base: available = the SoC pin reaches a header (reachability, hsp-0); everything else is unassigned
        p = model.pins[pad]
        r = reach.get(p['soc_pin'])
        st = 'available' if r and r['verdict'] == 'header' else 'unassigned'
        if not p['soc_pin']:
            r, st, why = None, 'unassigned', 'a supply or signal pad, not an I/O resource (nothing to claim)'
        elif st == 'available':
            why = 'reaches header pin(s) %s' % ', '.join(sorted(h.rpartition(':')[0].rpartition(':')[2] + ':' + h.rpartition(':')[2] for h in r['headers']))
        else:
            why = 'does not reach a header: %s' % (r['verdict'] if r else 'no reachability row')
        for ref in [pad] + line[pad]:
            _push(model, ref, st, why, [])
        model.pins[pad]['reach'] = r['verdict'] if r else ''
    info = {'stage': stage, 'binding': binding, 'claims': 0, 'committed_claims': 0, 'undetermined': [], 'notes': []}
    if stage == 'base':
        info['notes'].append('base composition: no claims read; "available" = the pin reaches a header (hsp-0 reachability), the chip blank / the board as delivered (whether a factory sketch is present is undetermined unless cited)')
        return info
    claims, committed, why = claims_of(ctx, binding, tables)
    if why:
        info['undetermined'].append(why)
    by_task, init_tasks, pwhy = purposes_by_task(ctx, binding, tables)
    if pwhy:
        info['undetermined'].append(pwhy)
    if stage == 'after-init':
        if not init_tasks:
            info['undetermined'].append('after-init cannot be separated today: %s; the pins stay at their base stage' % (pwhy or 'the Initialization Purpose names no tasks'))
            return info
        claims = [c for c in claims if c['task'] in init_tasks]
        info['notes'].append('after-init: only the claims of the Initialization Purpose\'s tasks (%s)' % ', '.join(sorted(init_tasks)))
    elif stage == 'tasks-assigned':
        info['notes'].append('tasks assigned: the binding\'s PinClaims as proposed — today the graph-node claims (Task definitions on a Mission arrive with fgm-3)')
    elif stage == 'firmware-committed':
        info['notes'].append('firmware committed: claims whose register settings or signal routes the binding generates are committed; the other claims stay proposed')
    info['claims'] = len(claims)
    for c in claims:
        pad = 'SocPin:%s' % c['soc_pin']
        if pad not in model.pins:
            info['undetermined'].append('claim %s names %s, which is not a die pad of this board' % (c['name'], c['soc_pin']))
            continue
        st = 'committed' if stage == 'firmware-committed' and c['name'] in committed else 'proposed'
        info['committed_claims'] += st == 'committed'
        cons = [{'kind': 'task', 'who': c['task'], 'solution': c['solution'], 'claim': c['name'], 'mode': c['mode'], 'function': (c.get('pin_function') or '').rpartition(':')[2], 'pull': c.get('pull', 'none')}]
        cons += [{'kind': 'purpose', 'who': p, 'task': c['task']} for p in by_task.get(c['task'], [])]
        for ref in [pad] + line[pad]:
            _push(model, ref, st, '%s by task %s of %s' % (st, c['task'], c['solution']), cons)
    return info


def rollup(model):
    """Each surface's pin count by stage; each connection's stage (the highest of its ends)."""
    for s in model.surfaces:
        cnt = {k: 0 for k in PIN_STAGES}
        for pid in s['pin_ids']:
            cnt[model.pins[pid]['stage']] += 1
        s['stage_counts'], s['pin_count'] = cnt, len(s['pin_ids'])
    for c in model.connections:
        a, b = model.pins[c['a']], model.pins[c['b']]
        c['stage'] = max((a['stage'], b['stage']), key=lambda x: RANK[x])


# ---------------------------------------------------------------- the protocol filter (ladder-backed)
def parse_protocols(protocol):
    """'i2c,spi' -> ['i2c', 'spi'] (several protocols or sets at once, in the order given, no duplicates); raises PinViewError on an unknown name."""
    out = []
    for name in (protocol or '').split(','):
        name = name.strip()
        if not name:
            continue
        if name not in F.FAMILIES:
            raise PinViewError('unknown protocol %r (families: %s)' % (name, ', '.join(F.FAMILIES)))
        if name not in out:
            out.append(name)
    return out


def _verdicts(ctx, pad, hit):
    """The ladder's verdict for each (child, function) the pad carries."""
    verdicts = []
    for child, fn in hit:
        try:
            lad = ctx.ladder(pad['label'], fn, chip=pad['soc'])
        except KeyError as e:
            verdicts.append({'child': child, 'function': fn, 'verdict': 'undetermined', 'blocked_at': 0, 'conditions': [], 'headline': 'the ladder cannot place it: %s' % e.args[0]})
            continue
        rungs = lad['rungs']
        blocked = next((r for r in rungs if r['verdict'] == 'blocked'), None)
        conds = [{'rung': r['rung'], 'name': r['name'], 'verdict': r['verdict'], 'detail': r['detail']} for r in rungs if r['verdict'] in ('conditional', 'undetermined', 'unchecked')]
        verdicts.append({'child': child, 'function': fn, 'verdict': 'blocked' if blocked else ('conditional' if any(c['verdict'] == 'conditional' for c in conds) else 'available'),
                         'blocked_at': blocked['rung'] if blocked else 0, 'blocked_why': blocked['detail'] if blocked else '', 'conditions': conds,
                         'headline': ('blocked at rung %d (%s): %s' % (blocked['rung'], blocked['name'], blocked['detail'])) if blocked else
                                     ('available with conditions (rungs %s)' % ', '.join(str(c['rung']) for c in conds if c['verdict'] == 'conditional')) if any(c['verdict'] == 'conditional' for c in conds) else 'available'})
    return verdicts


def apply_protocol(model, ctx, protocol, activated_only=False):
    """Lights every pin able to carry ANY of `protocol` (one family or set, or several: 'i2c,spi'; a set's child signals are expanded) with the LADDER's verdict for that kind in this context; dims the rest.
    activated_only keeps only the pads whose ACTIVATED function (pv-2: the claim's, null at stage base) is one of the asked signals."""
    protos = parse_protocols(protocol)
    if not protos:
        raise PinViewError('no protocol named (families: %s)' % ', '.join(F.FAMILIES))
    lit = {}
    pads = [p for p in model.pins.values() if p['level'] == 'die' and p['soc_pin']]
    for proto in protos:
        for pad in pads:
            if proto in F.SETS:   # one ladder question per child signal the pad carries
                hit = [(child, next(fn for fn in pad['functions'] if F.function_matches(proto, fn) == child)) for child in F.set_children(proto) if any(F.function_matches(proto, fn) == child for fn in pad['functions'])]
            else:   # a family without children: its first function on the pad
                fn = next((f for f in pad['functions'] if F.function_matches(proto, f)), None)
                hit = [('*', fn)] if fn else []
            if activated_only:   # only what the claim activated: its resource must be one of the asked signals
                act = pad.get('activated')
                match = F.function_matches(proto, act['resource']) if act else ''
                hit = [(match, act['resource'])] if match else []
            if not hit:
                continue
            kids = [dict(v, protocol=proto) for v in _verdicts(ctx, pad, hit)]
            if pad['id'] in lit:
                lit[pad['id']]['children'] += kids
                lit[pad['id']]['families'].append(proto)
            else:
                lit[pad['id']] = {'family': proto, 'families': [proto], 'children': kids}
    line = _outward(model, list(lit))
    for pad, res in lit.items():
        for ref in [pad] + line[pad]:
            model.pins[ref]['lit'] = res
    for p in model.pins.values():
        p['dim'] = p['lit'] is None
    for c in model.connections:   # a connection is lit when both ends are
        c['dim'] = model.pins[c['a']]['lit'] is None or model.pins[c['b']]['lit'] is None
    children = []
    for proto in protos:
        children += [c for c in F.set_children(proto) if c not in children]
    return {'protocol': ','.join(protos), 'protocols': protos, 'children': children, 'lit_pads': len(lit), 'activated_only': bool(activated_only),
            'ladder': 'every lit pad carries the availability ladder\'s verdict for the child signal in this context (rungs 7 and 9 say unchecked without a circuit / binding)',
            'note': ('activated only: just the pads whose claim activates one of the asked signals (nothing is activated at stage base)' if activated_only else 'capable: every pad able to carry one of the asked signals')}


# ---------------------------------------------------------------- the three summaries of a connection
def _header_roles(model):
    for p in model.pins.values():
        if p['level'] == 'board':
            p['drive_role'] = POWER_LABEL_ROLE.get(p['label'], '')
    for c in model.connections:
        if c['kind'] == 'to-header':
            h, leg = model.pins[c['b']], model.pins[c['a']]
            if not h['drive_role']:
                h['drive_role'] = leg['drive_role']
    for p in model.pins.values():
        if p['level'] == 'board' and not p['drive_role']:
            p['drive_role'] = 'undetermined'


RAIL = {'power': 'supply', 'analog-supply': 'supply', 'usb-supply': 'supply', 'regulator-output': 'regulated-output', 'ground': 'ground', 'usb-ground': 'ground', 'thermal-pad': 'ground',
        'analog-reference': 'analog-reference'}
DOMAIN = {'io': 'logic-io', 'power': 'logic-supply', 'analog-supply': 'analog', 'analog-reference': 'analog', 'analog-input': 'analog', 'usb-supply': 'usb', 'usb-ground': 'usb', 'usb-data': 'usb',
          'ground': 'ground', 'thermal-pad': 'ground', 'regulator-output': 'usb', 'clock-input': 'clock'}


def _canon_verdict(ctx, canon):
    """The class of the DRIVE rules' findings that name this board pin: (class, basis). unchecked when no circuit / no finding names it."""
    v, _ = ctx.findings(DRIVE_RULES)
    if v == 'unchecked' and not ctx.circuit:
        return 'unchecked', 'no circuit in the context: the electrical rules run on a circuit'
    fs = ctx.cache.get(('ec', ctx.circuit, ctx.binding)) or []
    mine = [f for f in fs if f['rule'] in DRIVE_RULES and re.search(r'(?<![A-Za-z0-9])%s(?![A-Za-z0-9])' % re.escape(canon), f['subject'] + ' ' + f['detail'])]
    if not mine:
        return 'unchecked', 'no drive rule of circuit %s names %s' % (ctx.circuit, canon)
    worst = 'undetermined' if any(f['status'] == 'undetermined' for f in mine) else 'ok'
    if any(f['status'] == 'warn' for f in mine):
        worst = 'conditional'
    if any(f['status'] == 'refuse' for f in mine):
        worst = 'blocked'
    return CLASS[worst], 'rule(s) ' + ', '.join(sorted({f['rule'] for f in mine}))


def _chip_behind(model, pid, adj):
    p = model.pins[pid]
    if p['level'] in ('die', 'package') and p['signals']:
        return p
    for n in adj.get(pid, []):
        q = model.pins[n]
        if q['level'] == 'package' and q['signals']:
            return q
    return p


def _pick(pa, pb, board_role_family, claim_fn):
    """The (family, function-on-a, function-on-b) a connection carries: the claim's function, else the board's designated role, else the first shared family by PRIORITY."""
    fa = {}   # signals_of lists a function once per family; keep the first function per family
    for s in pa['signals']:
        fa.setdefault(s['family'], s)
    fb = {}
    for s in pb['signals']:
        fb.setdefault(s['family'], s)
    if claim_fn:
        fam = F.family_of(claim_fn)
        if fam in fa or fam in fb:
            return fam, fa.get(fam), fb.get(fam)
    shared = [f for f in PRIORITY if f in fa and f in fb and f not in ('gpio', 'interrupt')]
    if shared:
        return shared[0], fa[shared[0]], fb[shared[0]]
    if board_role_family and (board_role_family in fa or board_role_family in fb):
        return board_role_family, fa.get(board_role_family), fb.get(board_role_family)
    for f in PRIORITY:
        if f in fa or f in fb:
            return f, fa.get(f), fb.get(f)
    return '', None, None


def summarise(model, ctx, tables, board):
    """Attaches `drive`, `signal`, `use` and `stage` to every connection (three SEPARATE summaries)."""
    _header_roles(model)
    adj = {}
    for c in model.connections:
        adj.setdefault(c['a'], []).append(c['b'])
        adj.setdefault(c['b'], []).append(c['a'])
    bp_role = {b['canonical']: b['function'] for b in tables.get('BoardPin', []) if b['board'] == board}
    # a header pin on a bench net carries the chip pin's SIGNAL role there (BoardPinNet: output | input — D-pv-7); without one it only passes the signal
    from board.custom import board_pin_nets as BPN
    net_role = {}
    for r in tables.get('BoardPinNet', []):
        if r.get('board') == board and r.get('board_pin'):
            canon_r = r['board_pin'].rpartition(':')[2]
            net_role[canon_r] = 'outputs' if BPN.is_output(r.get('role')) else 'inputs' if r.get('role') == 'input' else net_role.get(canon_r, '')
    for c in model.connections:
        a, b = model.pins[c['a']], model.pins[c['b']]
        # ---- signal (SignalPotential)
        ca, cb = _chip_behind(model, c['a'], adj), _chip_behind(model, c['b'], adj)
        canon = a['canonical'] or b['canonical'] or ca['canonical'] or cb['canonical']
        claim_fn = next((k['function'] for p in (a, b, ca, cb) for k in p['consumers'] if k['kind'] == 'task' and k['function']), '')
        mode = next((k['mode'] for p in (a, b, ca, cb) for k in p['consumers'] if k['kind'] == 'task'), '')
        if not claim_fn and mode in ('in', 'out'):   # a plain digital claim (no alternate function): the line is a GPIO
            claim_fn = 'GPIO'
        if a['level'] == 'die' and b['level'] == 'package':   # one line seen at two levels
            ca, cb = a, a
        # pv-2 (follow-up 1): a line no task claims does not NAME one protocol signal. Only a claim's function, or a family that is the ONLY one two different chips share (U1 RXD <-> U2 TXD1), is named;
        # otherwise the connection lists what both ends can carry (`capable`) and names none.
        fams_of = lambda x: {s['family'] for s in x['signals']}   # noqa: E731
        two_chips = bool(ca['soc'] and cb['soc'] and ca['soc'] != cb['soc'] and ca['signals'] and cb['signals'])
        shared_fams = [f for f in PRIORITY if f in fams_of(ca) and f in fams_of(cb) and f not in ('gpio', 'interrupt')]
        if claim_fn:
            fam, sa, sb = _pick(ca, cb, F.role_family(bp_role.get(canon, '')), claim_fn)
        elif two_chips and len(shared_fams) == 1:
            fam, sa, sb = _pick(ca, cb, '', '')
        else:
            fam, sa, sb = '', None, None
        capable_fams = [f for f in PRIORITY if f in fams_of(ca) | fams_of(cb)]
        kind_fam = F.family_of_kind(ca['kind']) or F.family_of_kind(cb['kind'])
        if not fam and kind_fam:
            fam = kind_fam

        def word(s, pin):
            if pin['level'] in ('die', 'package') and s:
                return 'outputs' if (mode == 'out' and s['family'] == 'gpio') else 'inputs' if (mode == 'in' and s['family'] == 'gpio') else SIGNAL_DIR.get(s['direction'], 'undetermined')
            if pin['level'] == 'board':
                return net_role.get(pin.get('canonical') or '', '') or 'passes'
            return 'undetermined'
        sig_a, sig_b = word(sa, a), word(sb, b)
        if fam in ('power', 'ground'):
            sig_a = sig_b = 'none'   # a supply or a return carries no signal
        names = [x['signal'].partition(':')[2] or x['function'] for x in (sa, sb) if x]
        c['signal'] = {'a': sig_a, 'b': sig_b, 'family': fam, 'token': F.token(fam) if fam else '', 'protocol_signal': ' <-> '.join(dict.fromkeys(names)) if names else '',
                       'function_a': sa['function'] if sa else '', 'function_b': sb['function'] if sb else '', 'capable': capable_fams if not fam else [], 'note': 'signal words only: outputs / inputs / bidirectional / passes (a header pin takes its bench-net role when it has one, else it only passes the signal)'}
        # ---- drive (DrivePotential): roles, rail and domain as words, the pull, the class of the limit
        kinds = [x['kind'] for x in (ca, cb) if x['level'] in ('die', 'package')]
        rail = next((RAIL[k] for k in kinds if k in RAIL), '')
        domain = next((DOMAIN[k] for k in kinds if k in DOMAIN), '')
        pull = next((k['pull'] for p in (a, b, ca, cb) for k in p['consumers'] if k['kind'] == 'task' and k.get('pull')), 'none')
        verdict, basis = _canon_verdict(ctx, canon) if canon else ('unchecked', 'not a board pin the electrical rules name')
        c['drive'] = {'a': a['drive_role'], 'b': b['drive_role'], 'rail': rail, 'domain': domain, 'pull': pull if pull and pull != 'none' else 'none assigned', 'via': c['via'], 'via_part': c['via_part'],
                      'limit_verdict': verdict, 'limit_basis': basis, 'note': 'electricity only (current and supply); the values are in the electrical view'}
        # ---- use
        tasks, purposes = [], []
        for p in (a, b, ca, cb):
            for k in p['consumers']:
                if k['kind'] == 'task' and k['claim'] not in {t['claim'] for t in tasks}:
                    tasks.append({kk: k[kk] for kk in ('who', 'solution', 'claim', 'mode', 'function')})
                if k['kind'] == 'purpose' and k['who'] not in purposes:
                    purposes.append(k['who'])
        c['use'] = {'tasks': tasks, 'purposes': purposes, 'stage': max((a['stage'], b['stage']), key=lambda x: RANK[x])}
    return model
