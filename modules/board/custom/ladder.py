"""
@module board.custom.ladder

hsp-0 (Revision 2 §5.2, FIRMWARE_GENERATION_REVIEW_R2.md Part 2 item 9): THE AVAILABILITY LADDER — a COMPUTED view, never a stored row. For one
(SoC pin, function) in a CONTEXT it walks ten rungs, in order, and says which one blocks first:

  1 SoC capability        the SoC pin has the function (PinFunction / SocPin row)
  2 package exposure      the package in context brings the pin out (bonded; the exposure map of the package enclosure)
  3 board routing         the board crossing: a header (which), or internal / a part in the way
  4 connected components  onboard consumers of the line (the 16U2 on D0/D1 via 1 kOhm, the LMV358 on D13, C5 on RESET, the 16 MHz part on PB6/PB7);
                          + the bench BoardPinNet rows when a circuit is in context
  5 attached extensions   E3 enclosures (shield stacks ...) on the board — none seeded: `none attached`
  6 pin multiplexing      board.custom.target_compat.compatible (the SoC pin's alternate functions); PinFunction exclusivity is `undetermined` (not cited)
  7 electrical limits     board.custom.electrical_check.check on the circuit in context (else `unchecked`)
  8 lifecycle             board.custom.electrical_hw.rule_lifecycle over the PinLifecycleConstraint rows for the phase / condition in context
  9 existing claims       cmod PinClaim of the binding in context (else `unchecked`)
 10 CIsotope requirements `not-yet` (fgm-4)

Verdict per rung: ok | blocked | conditional | unchecked | not-yet | undetermined. `available` names the FIRST blocking rung; no blocking rung = available (with the
conditions listed). Rungs 6-9 CALL the existing code, never re-implement a rule; a call that lacks its input in the context says `unchecked`, never ok.

CONTEXT (dict): board · package (a PackageDefinition name; default the board's modelled package, and when the board's package variant is PENDING every
allowed package is computed so the difference shows) · circuit · binding · phase (default runtime) · transport · acknowledged (list) · icsp · chip (a SoC name) ·
purpose (true = the claim IS the pin's own purpose, e.g. the transport using USART0 on D0: the lifecycle rule then reads it as native; default false = a NEW claim) ·
participants (the cmod Purpose seed shape: [{role: board|chip, ref, variant}] — an alternative way to name board + chip + variant).
"""
import json
import re

from board.custom import exposure_view as V

RUNGS = ((1, 'soc-capability'), (2, 'package-exposure'), (3, 'board-routing'), (4, 'connected-components'), (5, 'attached-extensions'),
         (6, 'pin-multiplexing'), (7, 'electrical-limits'), (8, 'lifecycle'), (9, 'existing-claims'), (10, 'isotope-requirements'))
VERDICTS = ('ok', 'blocked', 'conditional', 'unchecked', 'not-yet', 'undetermined')
#: function -> the firmware task kind board.custom.target_compat rates it by ('' = no kind names it)
TASK_KIND = {'GPIO': 'digital-in', 'RXD': 'uart-rx', 'TXD': 'uart-tx', 'SDA': 'i2c-sda', 'SCL': 'i2c-scl', 'MOSI': 'spi-mosi', 'MISO': 'spi-miso', 'SCK': 'spi-sck',
             'SS': 'spi-ss', 'INT0': 'interrupt-in', 'INT1': 'interrupt-in', 'OC0A': 'pwm-out', 'OC0B': 'pwm-out', 'OC1A': 'pwm-out', 'OC1B': 'pwm-out', 'OC2A': 'pwm-out',
             'OC2B': 'pwm-out', **{'ADC%d' % i: 'analog-in' for i in range(8)}, **{'PCINT%d' % i: 'interrupt-in' for i in range(24)}}


def _r(rung, verdict, detail, cite='', **extra):
    assert verdict in VERDICTS
    return dict({'rung': rung, 'name': dict(RUNGS)[rung], 'verdict': verdict, 'detail': detail, 'cite': cite}, **extra)


def context_from(ctx):
    c = dict(ctx or {})
    parts = c.get('participants') or c.get('participants_json') or []
    if isinstance(parts, str):
        parts = json.loads(parts or '[]')
    for p in parts:
        if p.get('role') == 'board' and not c.get('board'):
            c['board'] = p.get('ref', '')
            if p.get('variant') == 'pending':
                c['variant_pending'] = True
        if p.get('role') == 'chip' and not c.get('chip'):
            c['chip'] = p.get('ref', '')
    c.setdefault('phase', 'runtime')
    return c


def _resolve(pin, tables, board, chip=''):
    """-> (component, SocPin or None, BoardPin or None, label) for a canonical (D0), a SoC pin (PD0 / atmega328p:PD0) or a package-only signal (ADC6)."""
    comps = [c for c in tables.get('BoardComponent', []) if c['board'] == board and c.get('package')]
    if chip:
        comps = [c for c in comps if c['soc'] == chip] or comps
    bp = next((b for b in tables.get('BoardPin', []) if b['board'] == board and b['canonical'] == pin), None)
    want = bp['soc_pin'] if bp else pin.rpartition(':')[2]
    for comp in sorted(comps, key=lambda c: c['ref']):
        sp = next((s for s in tables.get('SocPin', []) if s['soc'] == comp['soc'] and s['pin'] == want), None)
        if sp:
            bp = bp or next((b for b in tables.get('BoardPin', []) if b['board'] == board and b['soc_pin'] == sp['pin'] and comp['role'] == 'mcu'), None)
            return comp, sp, bp, want
    for comp in sorted(comps, key=lambda c: c['ref']):
        if any(c['soc'] == comp['soc'] or True for c in [comp]) and any(pc['label'] == want and pc.get('kind') != 'io' for pc in tables.get('PackageContact', [])
                                                                       if pc['package'] in {p['name'] for p in tables.get('PackageDefinition', []) if p['soc'] == comp['soc']}):
            return comp, None, None, want
    raise KeyError('%s has no pin %s' % (board, pin))


def _packages(comp, ctx, tables, board):
    if ctx.get('package'):
        return [ctx['package']]
    bd = next((b for b in tables.get('BoardDefinition', []) if b['name'] == board), {})
    pending = ctx.get('variant_pending') or bd.get('variant_status') == 'pending'
    pkgs = [comp['package']]
    if pending:
        allowed = json.loads(bd.get('allowed_packages_json') or '[]')
        soc_of = {p['name']: p['soc'] for p in tables.get('PackageDefinition', [])}
        pkgs += [p for p in allowed if soc_of.get(p) == comp['soc'] and p not in pkgs]
    return pkgs


def _leg(tables, package, sp, label):
    for c in tables.get('PackageContact', []):
        if c['package'] == package and ((sp and c.get('soc_pin') == sp['name']) or (not sp and c['label'] == label)):
            return c
    return None


def availability(pin, function, ctx, tables=None):
    """-> {board, pin, soc_pin, function, context, results: [{package, rungs, available, blocked_at, conditions}], differs}."""
    from board.custom import board_object as BO
    ctx = context_from(ctx)
    board = BO.board_name(ctx.get('board') or 'arduino-uno-r3')
    tables = tables if tables is not None else BO.seed_tables()
    comp, sp, bp, label = _resolve(pin, tables, board, ctx.get('chip', ''))
    function = function or 'GPIO'
    cache = {}
    results = []
    for package in _packages(comp, ctx, tables, board):
        rungs = _walk(tables, board, comp, sp, bp, label, function, package, ctx, cache)
        first = next((r for r in rungs if r['verdict'] == 'blocked'), None)
        conds = [r for r in rungs if r['verdict'] in ('conditional', 'undetermined')]
        results.append({'package': package, 'rungs': rungs, 'blocked_at': first['rung'] if first else 0,
                        'available': ('blocked at rung %d (%s): %s' % (first['rung'], first['name'], first['detail'])) if first else
                                     ('available with conditions (rungs %s)' % ', '.join(str(r['rung']) for r in conds)) if conds else 'available',
                        'conditions': [{'rung': r['rung'], 'verdict': r['verdict'], 'detail': r['detail']} for r in conds]})
    differs = len({r['blocked_at'] for r in results}) > 1
    return {'board': board, 'pin': pin, 'soc_pin': sp['name'] if sp else '', 'signal': '' if sp else '%s:%s' % (comp['soc'], label), 'function': function,
            'context': {k: v for k, v in ctx.items() if k not in ('participants', 'participants_json')}, 'results': results,
            'differs': differs, 'difference': ('the packages differ: ' + '; '.join('%s -> %s' % (r['package'], r['available'].split(':')[0]) for r in results)) if differs else ''}


def _walk(tables, board, comp, sp, bp, label, fn, package, ctx, cache):
    out = [_rung1(tables, comp, sp, label, fn)]
    leg = _leg(tables, package, sp, label)
    out.append(_rung2(tables, package, sp, label, leg))
    r3, consumers = _rung3_4(tables, board, comp, sp, bp, label, package, leg, ctx)
    out += [r3[0], r3[1]]
    e3 = [e for e in tables.get('HardwareEnclosure', []) if e.get('level') == 'E3' and e.get('board') == board]
    out.append(_r(5, 'undetermined', '%d E3 enclosure(s) on the board, their pin passes are not modelled' % len(e3)) if e3 else
               _r(5, 'ok', 'none attached (no E3 enclosure: shield stack, carrier, daughterboard is seeded for this board)'))
    out.append(_rung6(tables, bp, sp, fn))
    out.append(_rung7(tables, board, bp, label, ctx, cache))
    out.append(_rung8(tables, board, bp, sp, label, fn, ctx))
    out.append(_rung9(tables, board, bp, fn, ctx, cache))
    out.append(_r(10, 'not-yet', 'the selected CIsotope\'s requirements are read in fgm-4; nothing is claimed here'))
    return out


def _rung1(tables, comp, sp, label, fn):
    if sp is None:
        known = [c for c in tables.get('PackageContact', []) if c['label'] == label and c['package'] in {p['name'] for p in tables.get('PackageDefinition', []) if p['soc'] == comp['soc']}]
        ok = fn in (label, 'GPIO') and known and fn != 'GPIO'
        return _r(1, 'ok' if ok else 'blocked', ('%s is an analog-only input of %s (leg %d of %s); it has no digital pad, no GPIO' % (label, comp['soc'], known[0]['number'], known[0]['package'])) if ok
                  else '%s has no function %s on %s' % (label, fn, comp['soc']), known[0]['page_table'] if known else '')
    fns = ['GPIO'] + json.loads(sp.get('functions_json') or '[]')
    pf = next((f for f in tables.get('PinFunction', []) if f['soc_pin'] == sp['name'] and f['function'] == fn), None)
    if fn in fns:
        return _r(1, 'ok', '%s can be %s (%s)' % (sp['pin'], fn, ('PinFunction %s' % pf['name']) if pf else 'SocPin.functions_json'), sp.get('fact', ''))
    return _r(1, 'blocked', '%s has no function %s (it has %s)' % (sp['pin'], fn, '/'.join(fns)), sp.get('fact', ''))


def _rung2(tables, package, sp, label, leg):
    if leg is not None:
        return _r(2, 'ok', '%s leg %d of %s' % (leg['label'], leg['number'], package), leg['page_table'])
    nb = next((c for c in V.contacts(tables) if c['via'] == 'not-bonded' and c['enclosure'] and package in c['page_table'] + c['enclosure'] + c['notes']
               and (c['inner_ref'].endswith(':' + (sp['pin'] if sp else label)))), None)
    nb = nb or next((c for c in V.contacts(tables) if c['via'] == 'not-bonded' and c['inner_ref'].endswith(':' + (sp['name'].partition(':')[2] if sp else label))), None)
    return _r(2, 'blocked', 'not bonded on %s: %s' % (package, nb['notes'] if nb else 'no contact for it'), nb['page_table'] if nb else '')


def _rung3_4(tables, board, comp, sp, bp, label, package, leg, ctx):
    rows = V.board_rows(tables, board)
    modelled = comp['package']
    use = leg if package == modelled else _leg(tables, modelled, sp, label)   # a variant package: the board's parts and nets are the modelled package's
    e2 = [c for c in V.touching(rows, ['PackageContact:%s' % use['name']]) if c['level'] == 'E2'] if use else []
    headers, consumers = [], []
    for c in e2:
        k = V.outer_kind(c['outer_ref'], tables) if c['exposed'] or c['via'] == 'internal-only' else 'chip'
        if c['exposed'] and k == 'header':
            headers += V.header_pins(c['outer_ref'], tables)
            if c['via'] != 'direct':
                consumers.append(c)
        else:
            consumers.append(c)
    variant = package != modelled
    if leg is None:
        r3 = _r(3, 'blocked', 'no leg on %s, so no board route' % package) if not (bp and sp) else _r(3, 'blocked', 'no leg on %s' % package)
        if sp is None and variant:
            r3 = _r(3, 'blocked', 'no header on %s carries %s (the UNO\'s headers are wired to the 328P signals the design brings out); no board crossing is modelled for it' % (board, label))
    elif headers and not variant:
        r3 = _r(3, 'ok', 'reaches header pin(s) %s' % ', '.join(sorted(set(headers))), '; '.join(sorted({c['page_table'] for c in e2 if c['exposed']}))[:200])
    elif variant:
        hp = [cp['name'] for cp in tables.get('ConnectorPin', []) if bp and cp['board'] == board and cp.get('board_pin') == bp['canonical']]
        if hp:
            r3 = _r(3, 'conditional', 'the board\'s net %s reaches header pin(s) %s on the modelled package (%s); the %s variant\'s own routing is not modelled' % (bp['net'], ', '.join(hp), modelled, package))
        else:
            r3 = _r(3, 'blocked', 'no header on %s carries %s: the board design brings out no net for it (and no crossing is modelled for %s)' % (board, label, package))
    elif e2:
        why = '; '.join(sorted({c['consumed_by'] or V.short(c) for c in e2}))
        r3 = _r(3, 'blocked', 'internal: no header carries it — %s' % why, '; '.join(sorted({c['page_table'] for c in e2}))[:200])
    else:
        r3 = _r(3, 'undetermined', 'no board crossing is modelled for this leg')
    cons = [c for c in consumers if not (c['via'] == 'direct' and c['exposed'])]
    nets = [n for n in tables.get('BoardPinNet', []) if bp and n.get('board_pin') == bp['name'] and ctx.get('circuit') and n.get('circuit') == ctx['circuit']]
    if not cons and not nets:
        r4 = _r(4, 'ok', 'no onboard part shares this line' + (' (variant package: judged on the modelled package\'s board parts)' if variant else ''))
    else:
        bits = ['%s via %s%s: %s' % (c['inner_ref'].rpartition(':')[0].rpartition(':')[2] if False else c['label'], c['via'], (' %s %s' % (c['via_part'], c['via_value'])).rstrip(),
                                     c['consumed_by'] or 'a part on the line') for c in cons]
        bits += ['bench net %s on circuit %s (role %s)' % (n['circuit_net'], n['circuit'], n['role']) for n in nets]
        blocked = bool(cons) and not headers and any(c['via'] == 'internal-only' for c in cons)
        r4 = _r(4, 'blocked' if blocked else 'conditional' if cons else 'ok', '; '.join(bits), '; '.join(sorted({c['fact'] for c in cons if c['fact']})))
    return (r3, r4), cons


def _rung6(tables, bp, sp, fn):
    kind = TASK_KIND.get(fn, '')
    if bp is None or sp is None:
        return _r(6, 'undetermined', 'not on a board pin: no firmware task can be dropped on it, multiplexing is not asked')
    if not kind:
        return _r(6, 'undetermined', 'no firmware task kind names %s, and PinFunction.exclusive_group is not cited for it' % fn)
    from board.custom import target_compat as TC
    v, why = TC.compatible(kind, bp, sp)
    return _r(6, {'ok': 'ok', 'no': 'blocked'}.get(v, 'undetermined'), '%s (task kind %s)' % (why, kind), 'board.custom.target_compat.compatible')


def _etables(tables, cache):
    if 'et' not in cache:
        from board.custom import electrical_check as EC
        et = EC.tables_for(tables.get('_manager'))
        for k, v in tables.items():
            if v and k not in ('CircuitDefinition', 'CircuitNetDefinition', 'CircuitComponentDefinition', 'BoardPinNet') and k != '_manager':
                et[k] = v
        cache['et'] = et
    return cache['et']


def _rung7(tables, board, bp, label, ctx, cache):
    if not ctx.get('circuit'):
        return _r(7, 'unchecked', 'no circuit in the context: the electrical rules run on a circuit')
    from board.custom import electrical_check as EC
    key = ('ec', ctx['circuit'])
    if key not in cache:
        cache[key] = EC.check(ctx['circuit'], board, _etables(tables, cache), context={k: ctx[k] for k in ('transport', 'acknowledged', 'icsp') if k in ctx})
    canon = bp['canonical'] if bp else label
    mine = [f for f in cache[key] if re.search(r'(?<![A-Za-z0-9])%s(?![A-Za-z0-9])' % re.escape(canon), f['subject'] + ' ' + f['detail'])]
    bad = [f for f in mine if f['status'] == 'refuse']
    warn = [f for f in mine if f['status'] == 'warn']
    und = [f for f in mine if f['status'] == 'undetermined']
    pick = bad or warn or und
    if not mine:
        return _r(7, 'ok', 'no electrical finding of circuit %s names %s (%d findings checked)' % (ctx['circuit'], canon, len(cache[key])), 'board.custom.electrical_check.check')
    return _r(7, 'blocked' if bad else 'conditional' if warn else 'undetermined' if und else 'ok',
              '; '.join('%s [%s] %s' % (f['rule'], f['status'], f['detail']) for f in (pick or mine))[:400], '; '.join(sorted({f['cite'] for f in (pick or mine) if f.get('cite')}))[:200])


def _rung8(tables, board, bp, sp, label, fn, ctx):
    from board.custom import electrical_hw as HW
    names = {x['pin'] for x in tables.get('PinLifecycleConstraint', []) if x['board'] == board and sp and x.get('soc_pin') == sp['name']}
    names |= {bp['canonical']} if bp else set()
    names = names or {label}
    cl = [{'pin': n, 'mode': 'claim', 'function': (fn if ctx.get('purpose') else '')} for n in sorted(names)]
    lctx = {k: ctx[k] for k in ('transport', 'acknowledged', 'icsp', 'dtr') if k in ctx}
    lctx.update(ctx.get('conditions') or {})
    lctx['phases'] = [ctx.get('phase', 'runtime')]
    found = [f for f in HW.rule_lifecycle(HW._ensure(tables), {'claims': cl, 'context': lctx}) if f['status'] != 'ok' or f['subject'] != '(design)']
    bad = [f for f in found if f['status'] == 'refuse']
    cond = [f for f in bad if 'needs the design to acknowledge' in f['detail']]
    hard = [f for f in bad if f not in cond]
    warn = [f for f in found if f['status'] == 'warn']
    if hard:
        return _r(8, 'blocked', hard[0]['detail'], hard[0].get('cite', ''))
    if cond or warn:
        return _r(8, 'conditional', (cond or warn)[0]['detail'], (cond or warn)[0].get('cite', ''))
    return _r(8, 'ok', 'no lifecycle constraint holds for %s at %s%s' % (', '.join(sorted(names)), ctx.get('phase', 'runtime'),
                                                                        (' while ' + ', '.join('%s=%s' % kv for kv in sorted(lctx.items()) if kv[0] != 'phases')) if len(lctx) > 1 else ''), 'board.custom.electrical_hw.rule_lifecycle')


def _rung9(tables, board, bp, fn, ctx, cache):
    if not ctx.get('binding'):
        return _r(9, 'unchecked', 'no binding in the context: PinClaim / PeripheralClaim belong to a firmware solution\'s binding')
    from board.custom import electrical_check as EC
    _b, claims = EC._resolve(ctx['binding'], _etables(tables, cache))
    mine = [c for c in claims if bp and c.get('board_pin', '').rpartition(':')[2] == bp['canonical']]
    if not mine:
        return _r(9, 'ok', 'no PinClaim of binding %s sits on %s (PeripheralClaim rows are not read here)' % (ctx['binding'], bp['canonical'] if bp else '?'), 'cmod.custom.claims.pin_claims')
    other = [c for c in mine if (c.get('pin_function') or '') not in ('', fn)]
    return _r(9, 'blocked' if other else 'conditional', '; '.join('%s claims %s as %s (%s)' % (c.get('solution', ''), c.get('board_pin', ''), c.get('pin_function') or c.get('mode'), c.get('status', '')) for c in mine),
              'cmod.custom.claims.pin_claims')


def render(res):
    lines = ['%s %s %s — context %s' % (res['board'], res['pin'], res['function'], json.dumps(res['context'], sort_keys=True))]
    for r in res['results']:
        lines.append('  package %s: %s' % (r['package'], r['available']))
        for x in r['rungs']:
            lines.append('    %2d %-22s %-12s %s' % (x['rung'], x['name'], x['verdict'], x['detail'][:150]))
    if res['difference']:
        lines.append('  ' + res['difference'])
    return '\n'.join(lines)
