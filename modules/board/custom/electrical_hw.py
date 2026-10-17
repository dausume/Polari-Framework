"""
@module board.custom.electrical_hw

fgm-2 (FIRMWARE_GENERATION_MODULE_PLAN.md §7.7 slice 1'): the HARDWARE-TRUTH RULES (f)-(j) of board.custom.electrical_check, over the new rows
(`ElectricalCharacteristic` per pad class, `PinGroupBudget` per group, `PinLifecycleConstraint` per pin x phase) instead of one hand-typed per-pin number.
Same finding shape as the five Phase-1 rules: {rule, status, subject, detail, cite}; status ok | warn | refuse | undetermined (a number not cited is NEVER
guessed — `detail` names what is missing).

  (f) voh_under_load       a pin driving a load (an LED through a series resistor) keeps sourcing within the current the datasheet guarantees VOH at (Table 30-1
                           note 3: 20 mA at 5 V). An LED with NO series resistor is refused by name. The LED's forward voltage is a CITED number or the rule says
                           `undetermined` (the box prints none): only a Vf-free ceiling, I <= VCC / R, is used as evidence — never an assumed Vf.
  (g) power_budget         the sum of the source/sink currents per PinGroupBudget group stays within the RECOMMENDED limit; an absolute maximum is never the limit.
  (h) input_threshold      an input meets VIH/VIL against what drives it: an output on the same board (D6 -> D3: VOH min vs VIH min with the load, VOL max vs VIL max),
                           or the internal pull-up and a switch to GND.
  (i) abs_max_not_target   a design whose current exceeds the RECOMMENDED limit (or names abs-max as its basis) is refused: a rating that destroys the part is not a target.
  (j) lifecycle            a claim on a pin that a PinLifecycleConstraint reserves/prohibits/conditions (D0/D1 while the transport is USB-serial; SPI on D13 without
                           acknowledging the L LED buffer) is refused by name. A person's DerivedOverride downgrades a LIFECYCLE refusal to a warn (who/why shown);
                           NOTHING overrides an electrical refusal ((f)-(i) never read overrides).

A `design` is plain data: {board, vcc, context: {transport, acknowledged: [token], icsp?, dtr?, dwen?, phases?}, loads: [{pin, kind, led_variant?, series_ohms?,
v_forward?, current_ma?, direction?, limit_basis?}], links: [{output, input}], buttons: [{pin, pull, switch_ohms?}], claims: [{pin, mode, function?}]} — built from the
circuit rows by `design_from_circuit` or handed in directly (`check_design`).
"""
from board.custom import board_pin_nets as BPN   # D-pv-7: signal roles (output | input), is_output()
import json
import re

DEFAULT_VCC = 5.0
DEFAULT_TEMP = '85'
SOC = 'atmega328p'


# ---------------------------------------------------------------- rows, numbers
def _ensure(tables):
    t = dict(tables)
    need = [c for c in ('ElectricalCharacteristic', 'PinGroupBudget', 'PinLifecycleConstraint', 'SocPin', 'BoardPin') if not t.get(c)]
    if need:
        from board.custom import board_object as BO
        seed = BO.seed_tables()
        for c in need:
            t[c] = seed.get(c, [])
    if not t.get('KitPart'):
        from board.custom import kit_parts as KP
        t['KitPart'] = KP.rows()
    return t


def _num(text):
    try:
        return float(text)
    except (TypeError, ValueError):
        return None


def value_of(expr, vcc=DEFAULT_VCC):
    """A datasheet number as float: '4.2' | '0.3 VCC' | 'VCC + 0.5' | 'GND' (0) | '' / 'undetermined' -> None. 'VREF' -> None (not a number without the reference)."""
    e = (expr or '').strip()
    if not e:
        return None
    n = _num(e)
    if n is not None:
        return n
    if e == 'GND':
        return 0.0
    m = re.fullmatch(r'([0-9.]+)\s*VCC', e)
    if m:
        return float(m.group(1)) * vcc
    m = re.fullmatch(r'VCC\s*\+\s*([0-9.]+)', e)
    if m:
        return vcc + float(m.group(1))
    return None


def _cite(row):
    return '%s, %s' % (row.get('document', ''), row.get('page_table', '')) if row else ''


def characteristic(tables, pad_class, parameter, vcc=DEFAULT_VCC, temp=DEFAULT_TEMP, limit_class=None, slug=None):
    """The ONE row of a pad class for a parameter at this VCC (+ temperature for VOH/VOL); None when the table has none. `vcc=None` ignores the supply
    filter (a leakage current the datasheet states at ONE supply point, VCC = 5.5 V — its worst case, so it bounds every lower supply)."""
    best = None
    for r in tables.get('ElectricalCharacteristic', []):
        if r['pad_class'] != pad_class or r['parameter'] != parameter or r.get('undetermined'):
            continue
        if slug and not r['name'].endswith(':' + slug):
            continue
        if limit_class and r['limit_class'] != limit_class:
            continue
        if vcc is not None and r['vcc_min'] and not (r['vcc_min'] - 1e-9 <= vcc <= r['vcc_max'] + 1e-9):
            continue
        if r['temp_c'] and r['temp_c'] != temp:
            continue
        best = r
        break
    return best


def pad_class_of(tables, board_pin):
    """'atmega328p:io-standard' for a board pin canonical ('D6'); '' when it has no SoC pin."""
    bp = next((p for p in tables.get('BoardPin', []) if p['canonical'] == board_pin), None)
    if bp is None or not bp.get('soc_pin'):
        return '', None
    sp = next((s for s in tables.get('SocPin', []) if s['soc'] == SOC and s['pin'] == bp['soc_pin']), None)
    return (sp or {}).get('electrical_class', ''), sp


def _f(rule, status, subject, detail, cite=''):
    return {'rule': rule, 'status': status, 'subject': subject, 'detail': detail, 'cite': cite}


def _ma(x):
    return '%.1f mA' % x


def _recommended_ma(tables, pad, vcc):
    r = characteristic(tables, pad, 'I_PIN', vcc, limit_class='recommended')
    return (value_of(r['max_value']), r) if r else (None, None)


def _test_ma(tables, pad, vcc):
    r = characteristic(tables, pad, 'I_PIN', vcc, limit_class='guaranteed')
    return (value_of(r['max_value']), r) if r else (None, None)


def _abs_ma(tables, pad):
    r = characteristic(tables, pad, 'I_PIN', limit_class='abs-max')
    return (value_of(r['max_value']), r) if r else (None, None)


def load_current(load, vcc):
    """(ma | None, ceiling_ma | None, why). `ma` = the current when every number is cited (declared current_ma, or (VCC - Vf)/R with a CITED Vf); `ceiling_ma` = a
    Vf-free upper bound VCC/R when only the resistor is known. A resistor of 0 (no series resistor) -> (inf, inf)."""
    if load.get('current_ma') is not None:
        return float(load['current_ma']), float(load['current_ma']), 'declared by the design'
    if load.get('kind') != 'led':
        return None, None, 'no current declared and %r is not an LED branch' % load.get('kind')
    r = load.get('series_ohms')
    if r is None:
        return None, None, 'the series resistor is not known'
    if r == 0:
        return float('inf'), float('inf'), 'no series resistor'
    ceiling = vcc / r * 1000.0
    vf = load.get('v_forward')
    if vf is None:
        return None, ceiling, 'the %s LED forward voltage is not cited (the box and the kit book print none)' % (load.get('led_variant') or 'indicator')
    return (vcc - vf) / r * 1000.0, ceiling, 'I = (VCC - Vf) / R with the cited Vf'


# ---------------------------------------------------------------- (f) VOH under the load
def rule_voh_under_load(tables, design):
    vcc = design.get('vcc', DEFAULT_VCC)
    out = []
    for ld in design.get('loads', []):
        pin = ld['pin']
        pad, _sp = pad_class_of(tables, pin)
        voh = characteristic(tables, pad, 'VOH', vcc, slug='5v-20ma-85c') if pad else None
        test, test_row = _test_ma(tables, pad, vcc) if pad else (None, None)
        subj = '%s %s' % (pin, ld.get('kind', 'load'))
        if voh is None or test is None:
            out.append(_f('voh_under_load', 'undetermined', subj, 'no cited VOH / test current for pin %s (pad class %r)' % (pin, pad)))
            continue
        i, ceiling, why = load_current(ld, vcc)
        cite = '%s; %s' % (_cite(voh), _cite(test_row))
        if i == float('inf'):
            out.append(_f('voh_under_load', 'refuse', subj,
                          '%s has NO series resistor: its current is limited only by the pin, so it can exceed the %s the datasheet guarantees VOH at (min %s V at that current) '
                          'and head for the %s absolute maximum — add a series resistor' % (subj, _ma(test), voh['min_value'], _ma(_abs_ma(tables, pad)[0] or 0)), cite))
        elif i is None:
            out.append(_f('voh_under_load', 'undetermined', subj,
                          'cannot place the load current against the %s guaranteed-VOH current: %s. A Vf-free ceiling is I <= VCC / R = %s'
                          % (_ma(test), why, _ma(ceiling) if ceiling is not None else 'unknown'), cite))
        elif i <= test:
            out.append(_f('voh_under_load', 'ok', subj, 'load current %s <= %s: VOH stays >= %s V (guaranteed at %s, %s)' % (_ma(i), _ma(test), voh['min_value'], _ma(test), voh['condition']), cite))
        else:
            out.append(_f('voh_under_load', 'refuse', subj,
                          'load current %s EXCEEDS the %s at which the datasheet guarantees VOH >= %s V: "Pins are not ensured to source current greater than the listed test condition"'
                          % (_ma(i), _ma(test), voh['min_value']), cite))
    if not design.get('loads'):
        out.append(_f('voh_under_load', 'ok', '(design)', 'no output load declared: nothing sags the output high level'))
    return out


# ---------------------------------------------------------------- (i) abs-max is never a target
def rule_abs_max_not_target(tables, design):
    vcc = design.get('vcc', DEFAULT_VCC)
    out = []
    for ld in design.get('loads', []):
        pad, _sp = pad_class_of(tables, ld['pin'])
        rec, rec_row = _recommended_ma(tables, pad, vcc) if pad else (None, None)
        ab, ab_row = _abs_ma(tables, pad) if pad else (None, None)
        subj = '%s %s' % (ld['pin'], ld.get('kind', 'load'))
        if rec is None or ab is None:
            out.append(_f('abs_max_not_target', 'undetermined', subj, 'no cited recommended / absolute-maximum current for pin %s' % ld['pin']))
            continue
        cite = '%s; %s' % (_cite(rec_row), _cite(ab_row))
        i, ceiling, why = load_current(ld, vcc)
        if ld.get('limit_basis') == 'abs-max':
            out.append(_f('abs_max_not_target', 'refuse', subj, 'the design sizes %s against the ABSOLUTE MAXIMUM (%s): a stress rating that can destroy the part is never a design target; '
                          'the recommended limit is %s' % (subj, _ma(ab), _ma(rec)), cite))
        elif i is not None and i > rec:
            out.append(_f('abs_max_not_target', 'refuse', subj, 'design current %s exceeds the RECOMMENDED %s per pin%s: it relies on abs-max headroom (%s), which is not a design target'
                          % (_ma(i), _ma(rec), '' if i <= ab else ' and even the %s absolute maximum' % _ma(ab), _ma(ab)), cite))
        elif i is None:
            out.append(_f('abs_max_not_target', 'undetermined', subj, 'cannot compare to the recommended %s: %s (Vf-free ceiling %s)' % (_ma(rec), why, _ma(ceiling) if ceiling is not None else 'unknown'), cite))
        else:
            out.append(_f('abs_max_not_target', 'ok', subj, 'design current %s <= recommended %s; the %s absolute maximum is not relied on' % (_ma(i), _ma(rec), _ma(ab)), cite))
    return out


# ---------------------------------------------------------------- (g) group budgets
def rule_power_budget(tables, design):
    vcc = design.get('vcc', DEFAULT_VCC)
    out, used = [], False
    sums = {}
    for ld in design.get('loads', []):
        pad, sp = pad_class_of(tables, ld['pin'])
        if sp is None:
            continue
        i, ceiling, why = load_current(ld, vcc)
        bound = i if i is not None else ceiling
        direction = ld.get('direction', 'source')
        for b in tables.get('PinGroupBudget', []):
            if b['direction'] == direction and sp['name'] in json.loads(b['members_json']) and b['limit_class'] == 'recommended' and not b.get('undetermined'):
                s = sums.setdefault(b['name'], [b, 0.0, []])
                s[1] += bound if bound is not None else float('inf')
                s[2].append('%s %s' % (ld['pin'], ('%s (cited)' % _ma(i)) if i is not None else ('<= %s (Vf-free ceiling)' % _ma(ceiling)) if ceiling is not None else 'unknown'))
    for name, (b, total, parts) in sorted(sums.items()):
        used = True
        cite = _cite(b)
        if total <= b['limit_ma']:
            out.append(_f('power_budget', 'ok', b['title'], 'sum %s <= the recommended %s (%s)' % (_ma(total), _ma(b['limit_ma']), '; '.join(parts)), cite))
        else:
            out.append(_f('power_budget', 'refuse', b['title'], 'sum %s EXCEEDS the recommended %s (%s)' % ('unbounded' if total == float('inf') else _ma(total), _ma(b['limit_ma']), '; '.join(parts)), cite))
    sup = next((b for b in tables.get('PinGroupBudget', []) if b['direction'] == 'supply' and b.get('undetermined')), None)
    if sup:
        out.append(_f('power_budget', 'undetermined', sup['title'], sup['undetermined'], _cite(sup)))
    if not used and not sup:
        out.append(_f('power_budget', 'ok', '(design)', 'no pin shares a budget group with a declared load'))
    return out


# ---------------------------------------------------------------- (h) input thresholds
def rule_input_threshold(tables, design):
    vcc = design.get('vcc', DEFAULT_VCC)
    out = []
    loads = {ld['pin']: ld for ld in design.get('loads', [])}
    for lk in design.get('links', []):
        drv, inp = lk['output'], lk['input']
        dpad, _a = pad_class_of(tables, drv)
        ipad, _b = pad_class_of(tables, inp)
        voh, vol = characteristic(tables, dpad, 'VOH', vcc, slug='5v-20ma-85c'), characteristic(tables, dpad, 'VOL', vcc, slug='5v-20ma-85c')
        vih, vil = characteristic(tables, ipad, 'VIH', vcc), characteristic(tables, ipad, 'VIL', vcc)
        subj = '%s -> %s' % (drv, inp)
        if not all((voh, vol, vih, vil)):
            out.append(_f('input_threshold', 'undetermined', subj, 'a cited VOH/VOL/VIH/VIL is missing for pad classes %r / %r' % (dpad, ipad)))
            continue
        vih_min, vil_max = value_of(vih['min_value'], vcc), value_of(vil['max_value'], vcc)
        test, test_row = _test_ma(tables, dpad, vcc)
        cite = '; '.join(filter(None, (_cite(voh), _cite(vol), _cite(vih), _cite(vil))))
        ld = loads.get(drv)
        i, ceiling, why = load_current(ld, vcc) if ld else (0.0, 0.0, 'no load on the driving pin')
        voh_min = value_of(voh['min_value'], vcc)
        if i is not None and i <= test:
            out.append(_f('input_threshold', 'ok' if voh_min >= vih_min else 'refuse', subj + ' (high)',
                          'driven high with %s load: VOH min %.1f V (guaranteed to %s) %s the input VIH min %.1f V (%s)' % (_ma(i), voh_min, _ma(test), '>=' if voh_min >= vih_min else '<', vih_min, vih['formula'] or vih['min_value']), cite))
        elif i is None:
            out.append(_f('input_threshold', 'undetermined', subj + ' (high)', 'VOH is guaranteed only up to %s; whether the load stays within it is not known: %s (Vf-free ceiling %s). '
                          'IF it does, VOH min %.1f V >= VIH min %.1f V' % (_ma(test), why, _ma(ceiling) if ceiling is not None else 'unknown', voh_min, vih_min), cite))
        else:
            out.append(_f('input_threshold', 'refuse', subj + ' (high)', 'load current %s exceeds the %s VOH is guaranteed at: the input level is not assured' % (_ma(i), _ma(test)), cite))
        vol_max = value_of(vol['max_value'], vcc)
        out.append(_f('input_threshold', 'ok' if vol_max <= vil_max else 'refuse', subj + ' (low)',
                      'driven low: VOL max %.1f V (at the %s sink test condition; the LED branch sinks nothing when its pin is low) %s the input VIL max %.1f V (%s)'
                      % (vol_max, _ma(test), '<=' if vol_max <= vil_max else '>', vil_max, vil['formula'] or vil['max_value']), cite))
    for bt in design.get('buttons', []):
        pin = bt['pin']
        pad, _sp = pad_class_of(tables, pin)
        rpu, iih = characteristic(tables, pad, 'RPU', vcc), characteristic(tables, pad, 'IIH', None)
        vih, vil = characteristic(tables, pad, 'VIH', vcc), characteristic(tables, pad, 'VIL', vcc)
        subj = '%s button to GND' % pin
        if bt.get('pull') != 'up':
            out.append(_f('input_threshold', 'undetermined', subj, 'the pull on %s is not defined (see rule pull_defined): the open-switch level is not assured' % pin))
            continue
        if not all((rpu, iih, vih, vil)):
            out.append(_f('input_threshold', 'undetermined', subj, 'a cited RPU/IIH/VIH/VIL is missing for pad class %r' % pad))
            continue
        rmax, rmin = value_of(rpu['max_value']) * 1000.0, value_of(rpu['min_value']) * 1000.0
        leak = value_of(iih['max_value']) * 1e-6
        v_open = vcc - leak * rmax
        vih_min, vil_max = value_of(vih['min_value'], vcc), value_of(vil['max_value'], vcc)
        cite = '; '.join(filter(None, (_cite(rpu), _cite(iih), _cite(vih), _cite(vil))))
        out.append(_f('input_threshold', 'ok' if v_open >= vih_min else 'refuse', subj + ' (open)',
                      'internal pull-up (RPU %s-%s kohm) and at most %s uA leakage hold the pin at >= %.2f V, %s VIH min %.1f V' % (rpu['min_value'], rpu['max_value'], iih['max_value'], v_open, '>=' if v_open >= vih_min else '<', vih_min), cite))
        i_closed = vcc / rmin
        tol = vil_max / i_closed
        if bt.get('switch_ohms') is None:
            out.append(_f('input_threshold', 'undetermined', subj + ' (pressed)',
                          'pressed level = pull-up current %.2f mA x the switch\'s closed resistance; VIL max %.1f V allows up to %.1f kohm of contact resistance, but the kit pushbutton\'s closed resistance is not cited (box and book print none)'
                          % (i_closed * 1000, vil_max, tol / 1000.0), cite))
        else:
            v = i_closed * bt['switch_ohms']
            out.append(_f('input_threshold', 'ok' if v <= vil_max else 'refuse', subj + ' (pressed)', 'pressed level %.2f V %s VIL max %.1f V' % (v, '<=' if v <= vil_max else '>', vil_max), cite))
    if not design.get('links') and not design.get('buttons'):
        out.append(_f('input_threshold', 'ok', '(design)', 'no input is fed by an output or a switch in this design'))
    return out


# ---------------------------------------------------------------- (j) lifecycle
def _applies(row, context):
    cond = row.get('condition') or ''
    if not cond:
        return True
    k, _, v = cond.partition('=')
    have = context.get(k)
    if k == 'dtr':   # 'dtr=resets-mcu' holds for an interface whose dtr_resets_mcu is true — the design states it (context['dtr'])
        return have == v
    return have == v


def _native(claim, pin):
    """A claim that IS the reserved purpose (USART0 on D0/D1; SPI SCK on D13 is NOT native to the L LED: it still needs the acknowledgment)."""
    fn = (claim.get('function') or '').upper()
    return pin in ('D0', 'D1') and any(t in fn for t in ('USART', 'RXD', 'TXD', 'UART'))


def rule_lifecycle(tables, design, overrides=None):
    ctx = dict(design.get('context') or {})
    ctx.setdefault('transport', 'usb-serial')
    phases = set(ctx.get('phases') or ('init', 'runtime')) | ({'programming'} if ctx.get('icsp') == 'connected' else set())
    acks = set(ctx.get('acknowledged') or [])
    ovr = {o['target_name']: o for o in (overrides or []) if o.get('target_class') == 'PinLifecycleConstraint' and o.get('status', 'active') == 'active' and (o.get('why') or '').strip()}
    out, seen = [], 0
    for cl in design.get('claims', []):
        pin = (cl['pin'] or '').rpartition(':')[2]
        for row in tables.get('PinLifecycleConstraint', []):
            if row['pin'] != pin or row['phase'] not in phases or row['policy'] == 'free' or not _applies(row, ctx):
                continue
            seen += 1
            subj = '%s %s (%s)' % (pin, cl.get('mode') or 'claim', row['phase'])
            cite = _cite(row)
            if _native(cl, pin) and row['policy'] == 'reserved':
                out.append(_f('lifecycle', 'ok', subj, '%s is claimed by its own purpose (%s): %s' % (pin, cl.get('function'), row['reason']), cite))
                continue
            if row['policy'] == 'conditional' and row['acknowledgment'] in acks:
                out.append(_f('lifecycle', 'ok', subj, 'the design acknowledges %r: %s' % (row['acknowledgment'], row['reason']), cite))
                continue
            bad = {'prohibited': 'is PROHIBITED', 'reserved': 'is RESERVED', 'conditional': 'needs the design to acknowledge %r' % row['acknowledgment'], 'preserve': 'must be PRESERVED'}[row['policy']]
            detail = '%s %s%s at phase %s: %s' % (pin, bad, (' while %s' % row['condition']) if row['condition'] else '', row['phase'], row['reason'])
            o = ovr.get(row['name'])
            if o:
                out.append(_f('lifecycle', 'warn', subj, '%s — OVERRIDDEN by %s: %s (a lifecycle override; it never covers an electrical refusal)' % (detail, o.get('who') or 'a person', o['why']), cite))
            else:
                out.append(_f('lifecycle', 'refuse', subj, detail, cite))
    if not out:
        out.append(_f('lifecycle', 'ok', '(design)', 'no claim meets a lifecycle constraint (%d claim(s), phases %s)' % (len(design.get('claims', [])), '/'.join(sorted(phases)))))
    return out


# ---------------------------------------------------------------- the public doors
def check_design(board, design, tables=None, overrides=None):
    """[finding, ...] for rules (f)-(j) over a design dict (see the module doc). `overrides` = DerivedOverride-shaped dicts; only (j) reads them."""
    if tables is None:
        from board.custom import board_object as BO
        tables = BO.seed_tables()
    t = _ensure(tables)
    design = dict(design, board=board)
    return (rule_voh_under_load(t, design) + rule_power_budget(t, design) + rule_input_threshold(t, design)
            + rule_abs_max_not_target(t, design) + rule_lifecycle(t, design, overrides))


def design_from_circuit(nets, comps, pin_nets, claims, context, helpers):
    """Build a design from circuit rows. `helpers` = electrical_check's own (_pins, _params, _net_row_by_label, _pin_nets_on) — passed in, not re-imported (no cycle)."""
    _pins, _params, _net_row_by_label, _pin_nets_on = helpers
    d = {'context': dict(context or {}), 'loads': [], 'links': [], 'buttons': [], 'claims': [dict(c, pin=(c.get('board_pin') or c.get('pin') or '').rpartition(':')[2], function=c.get('pin_function', ''))
                                                                                          for c in (claims or [])]}
    for led in [c for c in comps if c.get('kind') == 'led']:
        pins = _pins(led)
        if len(pins) != 2:
            continue
        anode = pins[0]
        res = next((c for c in comps if c.get('kind') == 'resistor' and anode in _pins(c)), None)
        upstream = next((p for p in _pins(res) if p != anode), None) if res else anode
        row = _net_row_by_label(nets, upstream) if upstream else None
        drv = [p for p in (_pin_nets_on(pin_nets, row['name']) if row else []) if BPN.is_output(p.get('role'))]
        if drv:
            d['loads'].append({'pin': drv[0]['board_pin'].rpartition(':')[2], 'kind': 'led', 'led_variant': '', 'series_ohms': _params(res).get('ohms') if res else 0,
                               'v_forward': None})   # a CITED Vf only: the circuit row's v_forward is an ASSUMPTION its own description says so — never evidence here
    by_net = {}
    for p in pin_nets:
        by_net.setdefault(p['circuit_net'], []).append(p)
    for rows in by_net.values():
        outputs = [r for r in rows if BPN.is_output(r.get('role')) and r.get('board_pin')]
        inputs = [r for r in rows if r.get('role') == 'input' and r.get('board_pin')]
        for dr in outputs:
            for ip in inputs:
                d['links'].append({'output': dr['board_pin'].rpartition(':')[2], 'input': ip['board_pin'].rpartition(':')[2]})
    for p in pin_nets:
        if p.get('role') == 'input' and p.get('board_pin') and not any(BPN.is_output(r.get('role')) and r.get('circuit_net') == p['circuit_net'] for r in pin_nets):
            net = next((n for n in nets if n['name'] == p['circuit_net']), None)
            sw = next((c for c in comps if c.get('kind') == 'switch' and net and net['net'] in _pins(c)), None)
            if sw is None:
                continue
            canon = p['board_pin'].rpartition(':')[2]
            pull = next((c.get('pull') for c in (claims or []) if (c.get('board_pin') or '').endswith(':%s' % canon)), '') or ''
            d['buttons'].append({'pin': canon, 'pull': pull, 'switch_ohms': None})
    return d
