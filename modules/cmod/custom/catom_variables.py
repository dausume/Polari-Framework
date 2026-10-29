"""
@module cmod.custom.catom_variables

hsp-3d (HARDWARE_SYSTEM_PINS_PLAN.md §7, his words 2026-10-28: "Catom Variables are how we make a generalized HAL ... We need the variables and assertions to be
a way that enforces the logic to the visualization and rules"): the role vocabulary, the CHECK every value passes before it counts, and what the variables
make - the `defines-role` Catom assertions, the pin -> role rows the views draw, the no-code slots, and the HAL header lines the firmware carries.

  check(var, value, others)   -> {verdict accepted|warning|refused, why[], pin, function}   - the ONE enforcement path (the views and the doors read it)
  variables(variant, rows)    -> the rows with value + scope + status recomputed
  slots(var, others)          -> the pins a role slot may offer, accepted first, then warnings (refusals left out, counted)
  role_assertions(variant)    -> CatomAssertion-shaped dicts, kind defines-role (role x pin), derived
  render_header(variant)      -> '#define UART0_TX_PIN PD1 ...' lines (the value the firmware is generated with)
  propose(variant, edits)     -> hsp-3c: the ONE write path (a slot choice): checked against the proposed set + the variant's own rules -> writes[]
  apply_writes(writes, ...)   -> the rows touched; a knob-backed variable (KNOB_OF) lives in its FirmwareVariant knob, the rest in bench_value

The rules, in order (a refusal stops nothing - every reason is reported):
  1. the value is a pin of the SoC (UNO names D6 / A0 / 6 resolve to the SoC pin through board_uno.D_PINS / A_PINS; the C3's GPIO<n> / <n>)
  2. the role is a function the pin OFFERS: the ATmega328P's port tables (soc_atmega328p.PINS, Table 14-3/6/9) - refused naming the pins that do; the C3's IO MUX
     (esp32c3_tables.PRIORITY, Table 2-7 p.24) or its GPIO matrix (accepted, said: the matrix routes the signal; the IO MUX pin is named)
  3. the pin's lifecycle rows (lifecycle_uno / lifecycle_c3, cited): prohibited = refused; reserved BY THE ROLE'S OWN PERIPHERAL (the reason names the role's
     function or ROLE_KEYWORDS: USART0 / the serial transport on D0/D1) = a warning naming it (Optiboot); reserved by anything else = refused (a GPIO claim on
     D1 fights the 16U2); conditional / preserve = a warning
     - a row with a condition is judged in the board's context (pin_stages.DEFAULT_CONTEXT): one that does not hold is listed as not applied
  4. no other variable of the variant claims the pin for a different role
A number role (clock.hz) needs a positive number. The electrical check needs a bench net and is not run here (said on every row).
"""
import fnmatch
import re

ROLES = ('uart.tx', 'uart.rx', 'gpio.out', 'gpio.in', 'int.ext', 'adc.in', 'pwm.out', 'clock.hz')
NUMBER_ROLES = ('clock.hz',)
VERDICTS = ('accepted', 'warning', 'refused')
#: role -> the ATmega328P function names (soc_atmega328p.PINS) that serve it; GPIO = every port pin (§14.2)
AVR_ROLE_FUNCTIONS = {'uart.tx': ('TXD',), 'uart.rx': ('RXD',), 'int.ext': ('INT0', 'INT1'), 'gpio.out': ('GPIO',), 'gpio.in': ('GPIO',),
                      'adc.in': ('ADC?',), 'pwm.out': ('OC0A', 'OC0B', 'OC1A', 'OC1B', 'OC2A', 'OC2B')}
#: role -> (the C3 IO MUX function, whether the GPIO matrix may route it to any GPIO)
C3_ROLE_FUNCTIONS = {'uart.tx': ('U0TXD', True), 'uart.rx': ('U0RXD', True), 'int.ext': ('GPIO', True), 'gpio.out': ('GPIO', True), 'gpio.in': ('GPIO', True),
                     'adc.in': ('ADC1_CH?', False), 'pwm.out': ('GPIO', True)}
#: words by which a lifecycle reason names the role's OWN peripheral (then a reservation is that peripheral's, and the role is its rightful user: a warning)
ROLE_KEYWORDS = {'uart.tx': ('TXD', 'USART0', 'UART0', 'serial'), 'uart.rx': ('RXD', 'USART0', 'UART0', 'serial'), 'int.ext': ('INT0', 'INT1', 'interrupt'),
                 'adc.in': ('ADC',), 'pwm.out': ('PWM', 'OC0', 'OC1', 'OC2')}
_ELECTRICAL = 'electrical check: not run for a role assignment (it needs the bench net the pin drives)'

_TX = 'ATmega328P DS40002061B Table 14-9 Port D Pins Alternate Functions p.97 (soc_atmega328p.PINS)'
_C3_UART = 'ESP32-C3 datasheet §4.2.1.1 UART Controller p.46: IO MUX pins GPIO20 (U0RXD) / GPIO21 (U0TXD); Table 2-7 p.24 (esp32c3_tables.PRIORITY)'
_UNO_LIGHT = 'variant uno-light knobs (board.custom.variants: led_pin 6, button_pin 2, sense_pin 3) - the bench wiring'
_C3_LIGHT = 'variant esp32c3-light knobs (board.custom.variants_c3.LIGHT_KNOBS: led_pin 0, button_pin 3, sense_pin 1) - the bench wiring'


def _v(variant, var, role, soc, board, c_form, chip='', chip_basis='', board_value='', board_basis='', bench='', bench_basis='', used_by='', type_='pin', notes=''):
    return {'name': '%s:%s' % (variant, var), 'variant': variant, 'variable': var, 'role': role, 'type': type_, 'soc': soc, 'board': board, 'c_form': c_form,
            'chip_default': chip, 'chip_basis': chip_basis, 'board_value': board_value, 'board_basis': board_basis, 'bench_value': bench, 'bench_basis': bench_basis,
            'used_by': used_by, 'status': '', 'status_why': '', 'notes': notes}


_U, _UB, _C, _CB = 'atmega328p', 'arduino-uno-r3', 'esp32c3', 'esp32-c3'
SEED_VARIABLES = [
    _v('uno-light', 'UART0_TX_PIN', 'uart.tx', _U, _UB, 'port-bit', 'PD1', _TX, used_by='apps/light.telemetry_send,hal.hal_usart_send'),
    _v('uno-light', 'UART0_RX_PIN', 'uart.rx', _U, _UB, 'port-bit', 'PD0', _TX, used_by='hal.USART_RX_vect'),
    _v('uno-light', 'LED_PIN', 'gpio.out', _U, _UB, 'arduino-number', board_value='D13', board_basis='board_config.h LED_PIN 13 (the on-board L LED; board_uno.ROLES D13 firmware_symbol LED_PIN)',
       bench='D6', bench_basis=_UNO_LIGHT, used_by='apps/light.led_follow_state'),
    _v('uno-light', 'BUTTON_PIN', 'int.ext', _U, _UB, 'arduino-number', bench='D2', bench_basis=_UNO_LIGHT, used_by='hal.hal_button_init,hal.hal_presses'),
    _v('uno-light', 'SENSE_PIN', 'gpio.in', _U, _UB, 'arduino-number', bench='D3', bench_basis=_UNO_LIGHT + ' (sense_route poll)', used_by='apps/light.sense_poll'),
    _v('uno-light', 'F_CPU', 'clock.hz', _U, _UB, 'number', board_value='16000000', board_basis='the build\'s -DF_CPU=16000000UL (cycle record uno-light inputs.cflags; boards.txt build.f_cpu)',
       type_='number'),
    _v('esp32c3-light', 'UART0_TX_PIN', 'uart.tx', _C, _CB, 'gpio-number', 'GPIO21', _C3_UART, used_by='light.telemetry'),
    _v('esp32c3-light', 'UART0_RX_PIN', 'uart.rx', _C, _CB, 'gpio-number', 'GPIO20', _C3_UART, used_by='light.uart_rx'),
    _v('esp32c3-light', 'LED_PIN', 'gpio.out', _C, _CB, 'gpio-number', bench='GPIO0', bench_basis=_C3_LIGHT),
    _v('esp32c3-light', 'BUTTON_PIN', 'int.ext', _C, _CB, 'gpio-number', bench='GPIO3', bench_basis=_C3_LIGHT),
    _v('esp32c3-light', 'SENSE_PIN', 'gpio.in', _C, _CB, 'gpio-number', bench='GPIO1', bench_basis=_C3_LIGHT),
]


# ------------------------------------------------------------------------------------------------ the chips' facts, read from board
def _avr_pins():
    from board.custom.soc_atmega328p import PINS
    return {p: ['GPIO'] + list(fns) for p, (_n, fns) in PINS.items()}


def _c3_pins():
    from board.custom.esp32c3_tables import PRIORITY
    out = {}
    for n, (_pkg, _name, fixed, ifaces) in PRIORITY.items():
        out['GPIO%d' % n] = ['GPIO'] + [f for f, _p in fixed] + sorted({sig for sig, _p in ifaces.values() if not sig.startswith('GPIO')})
    return out


def pins_of(soc):
    return _avr_pins() if soc == 'atmega328p' else _c3_pins() if soc == 'esp32c3' else {}


def resolve_pin(soc, value):
    """The SoC pin a value names, or '' - D6 / A0 / 6 on the UNO, GPIO21 / 21 / IO21 on the C3."""
    v = str(value).strip().upper()
    if soc == 'atmega328p':
        from board.custom.board_uno import D_PINS, A_PINS
        if v.isdigit():
            v = 'D' + v
        hit = D_PINS.get(v) or A_PINS.get(v)
        v = hit[0] if hit else v
    elif soc == 'esp32c3':
        m = re.match(r'^(?:GPIO|IO)?(\d+)$', v)
        v = 'GPIO%d' % int(m.group(1)) if m else v
    return v if v in pins_of(soc) else ''


def _lifecycle(soc):
    if soc == 'atmega328p':
        from board.custom.lifecycle_uno import constraints
    elif soc == 'esp32c3':
        from board.custom.lifecycle_c3 import constraints
    else:
        return []
    return constraints()


def _offers(soc, pin, role):
    """(function serving the role on this pin | '', note) - '' = the pin cannot do it."""
    fns = pins_of(soc).get(pin, [])
    if soc == 'atmega328p':
        hit = next((f for f in fns for p in AVR_ROLE_FUNCTIONS.get(role, ()) if fnmatch.fnmatchcase(f, p)), '')
        return hit, ''
    fn, matrix = C3_ROLE_FUNCTIONS.get(role, ('', False))
    hit = next((f for f in fns if fnmatch.fnmatchcase(f, fn)), '')
    if hit:
        return hit, 'IO MUX function %s' % hit if hit != 'GPIO' else ''
    if matrix:
        home = [p for p, fs in pins_of(soc).items() if fn in fs]
        return 'matrix:%s' % fn, 'routed through the GPIO matrix (TRM signal %s_out/_in)%s' % (fn, '; its IO MUX pin is %s' % ', '.join(home) if home else '')
    return '', ''


def offering_pins(soc, role):
    return [p for p in pins_of(soc) if _offers(soc, p, role)[0]]


def _get(o, k, d=''):
    return o.get(k, d) if isinstance(o, dict) else getattr(o, k, d)


def effective(var):
    """(value, scope, basis) - the narrowest scope set: bench -> board -> chip."""
    for scope in ('bench', 'board', 'chip'):
        key = 'chip_default' if scope == 'chip' else '%s_value' % scope
        if str(_get(var, key) or '').strip():
            return str(_get(var, key)).strip(), scope, _get(var, '%s_basis' % scope)
    return '', 'none', 'no value at any scope'


def check(var, value, others=(), context=None):
    """THE enforcement path. -> {verdict, why[], pin, function, refusals[]}. `others` = the variant's other variables (for the one-pin-one-role rule);
    `context` = the conditions a lifecycle row is judged in (hsp-3c: the board's bench path, board.custom.pin_stages.DEFAULT_CONTEXT, plus any given) -
    a row whose condition does not hold (D13 ICSP SCK when icsp=connected, with no programmer on the header) is listed as not applied."""
    from board.custom.pin_stages import DEFAULT_CONTEXT, _cond_holds
    ctx = dict(DEFAULT_CONTEXT.get(_get(var, 'board'), {}), **(context or {}))
    role, soc, name = _get(var, 'role'), _get(var, 'soc'), _get(var, 'variable')
    why, warned = [], False
    refusals = []
    if role not in ROLES:
        return {'verdict': 'refused', 'why': ['role %r is not a HAL role (%s)' % (role, ', '.join(ROLES))], 'pin': '', 'function': ''}
    if role in NUMBER_ROLES:
        try:
            ok = float(str(value).rstrip('UL')) > 0
        except ValueError:
            ok = False
        return ({'verdict': 'accepted', 'why': ['%s = %s (a positive number)' % (name, value)], 'pin': '', 'function': ''} if ok else
                {'verdict': 'refused', 'why': ['%s is a %s: a positive number (got %r)' % (name, role, value)], 'pin': '', 'function': ''})
    pin = resolve_pin(soc, value)
    if not pin:
        return {'verdict': 'refused', 'why': ['%r is not a pin of the %s' % (value, soc)], 'pin': '', 'function': ''}
    fn, note = _offers(soc, pin, role)
    if not fn:
        fns = [f for f in pins_of(soc)[pin] if f != 'GPIO']
        refusals.append(len(why))
        why.append('%s = %s refused: %s offers %s, not %s; %s is offered by %s' % (
            name, pin, pin, ', '.join(fns) or 'GPIO only', role, role, ', '.join('%s (%s)' % (p, _offers(soc, p, role)[0]) for p in offering_pins(soc, role)) or 'no pin'))
    else:
        why.append('%s offers %s as %s%s' % (pin, role, fn, (' - ' + note) if note else ''))
    words = ROLE_KEYWORDS.get(role, ())
    for c in _lifecycle(soc):
        if c['soc_pin'].split(':', 1)[-1] != pin or c['policy'] == 'free':
            continue
        same = bool(fn) and fn != 'GPIO' and (fn.split(':')[-1] in c['reason'] or any(w in c['reason'] for w in words))
        cond = (' (when %s)' % c['condition']) if c['condition'] else ''
        if not _cond_holds(c['condition'], ctx):
            why.append('not applied (condition %s does not hold here): %s %s in %s' % (c['condition'], c['pin'], c['policy'], c['phase'].upper()))
            continue
        if c['policy'] == 'prohibited' or (c['policy'] == 'reserved' and not same):
            refusals.append(len(why))
            why.append('%s is %s in %s%s: %s [%s]' % (c['pin'], c['policy'], c['phase'].upper(), cond, c['reason'], c['page_table']))
        else:
            warned = True
            why.append('warning: %s is %s in %s%s - %s [%s]' % (c['pin'], c['policy'], c['phase'].upper(), cond, c['reason'], c['page_table']))
    for o in others:
        if _get(o, 'variable') == name or _get(o, 'role') in NUMBER_ROLES:
            continue
        ov, _s, _b = effective(o)
        if ov and resolve_pin(soc, ov) == pin and _get(o, 'role') != role:
            refusals.append(len(why))
            why.append('%s already claims %s as %s: one pin, one role' % (_get(o, 'variable'), pin, _get(o, 'role')))
    why.append(_ELECTRICAL)
    return {'verdict': 'refused' if refusals else 'warning' if warned else 'accepted', 'why': why, 'pin': pin, 'function': fn,
            'refusals': [why[i] for i in refusals]}


def _rows(variant, rows):
    src = SEED_VARIABLES if rows is None else rows
    return [{k: _get(r, k) for k in SEED_VARIABLES[0]} for r in src if _get(r, 'variant') == variant]


# ------------------------------------------------------------------------------------------------ hsp-3c: the bench scope IS the variant knob
#: a HAL variable whose bench value the firmware build reads from a FirmwareVariant knob: the knob is the ONE place it lives (the variable reads it,
#: a slot choice writes it, `pol board gen` renders it into board_config.h) - never a second copy that could drift
KNOB_OF = {'LED_PIN': 'led_pin', 'BUTTON_PIN': 'button_pin', 'SENSE_PIN': 'sense_pin'}


def _variants_mod(soc):
    if soc == 'atmega328p':
        from board.custom import variants as V
    elif soc == 'esp32c3':
        from board.custom import variants_c3 as V
    else:
        return None
    return V


def variant_knobs(variant, soc, variant_rows=None):
    """{knob: value} the variant itself sets (knobs_json; the C3 light app's LIGHT_KNOBS under them); {} when there is no such variant."""
    V = _variants_mod(soc)
    if V is None:
        return {}
    try:
        d = V.find(variant, variant_rows)
    except V.VariantRefused:
        return {}
    k = dict(V._j(d.get('knobs_json'), {}))
    if soc == 'esp32c3' and d.get('app') == 'light':
        k = dict(V.LIGHT_KNOBS, **k)
    return k


def board_form(soc, pin, c_form=''):
    """The value as the variable is written: the UNO's arduino-number variables keep D<n> / A<n>; every other form the SoC pin."""
    if soc == 'atmega328p' and c_form == 'arduino-number':
        from board.custom.board_uno import D_PINS, A_PINS
        return next((c for c, (s, _n) in list(D_PINS.items()) + list(A_PINS.items()) if s == pin), pin)
    return pin


def knob_number(soc, pin):
    """The integer the variant knob holds for a pin: the Arduino number on the UNO (A0 = 14), the GPIO number on the C3."""
    if soc == 'atmega328p':
        name = board_form(soc, pin, 'arduino-number')
        return int(name[1:]) + (14 if name.startswith('A') else 0)
    return int(pin.replace('GPIO', ''))


def _knob_value(soc, n):
    if soc == 'atmega328p':
        n = int(n)
        return 'D%d' % n if n < 14 else 'A%d' % (n - 14)
    return 'GPIO%d' % int(n)


def _overlay(vs, variant, variant_rows):
    """Lay the variant's own knobs over the bench scope of the knob-backed variables."""
    soc = vs[0]['soc'] if vs else ''
    k = variant_knobs(variant, soc, variant_rows)
    for v in vs:
        knob = KNOB_OF.get(v['variable'])
        if knob and knob in k:
            v['bench_value'] = _knob_value(soc, k[knob])
            v['bench_basis'] = 'FirmwareVariant %s knobs %s %s (the bench wiring; a slot choice writes it there)' % (variant, knob, k[knob])
    return vs


def _judge(vs):
    for v in vs:
        v['value'], v['scope'], v['value_basis'] = effective(v)
        r = check(v, v['value'], vs)
        v['status'], v['status_why'], v['pin'], v['function'] = r['verdict'], '; '.join(r['why']), r['pin'], r['function']
        v['refusals'] = r.get('refusals') or ([r['why'][0]] if r['verdict'] == 'refused' else [])
    return vs


def variables(variant, rows=None, variant_rows=None):
    return _judge(_overlay(_rows(variant, rows), variant, variant_rows))


def build_check(variant, knobs, rows=None):
    """hsp-3c, what `pol board gen` asks: the variant's HAL with the knobs the build ACTUALLY uses (`knobs` = the ones the variant or the command set,
    resolved) laid over the bench scope. -> None when the variant has no catom variables, else {refused: ['VAR = value: reason'], values: {VAR: value},
    verdicts: {VAR: verdict}} - a refused one stops the build."""
    vs = _rows(variant, rows)
    if not vs:
        return None
    soc = vs[0]['soc']
    for v in vs:
        knob = KNOB_OF.get(v['variable'])
        if knob and knob in knobs:
            v['bench_value'], v['bench_basis'] = _knob_value(soc, knobs[knob]), 'the build\'s knob %s = %s' % (knob, knobs[knob])
    vs = _judge(vs)
    return {'refused': ['%s = %s: %s' % (v['variable'], v['value'], ' | '.join(v['refusals'])) for v in vs if v['status'] == 'refused'],
            'values': {v['variable']: v['value'] for v in vs}, 'verdicts': {v['variable']: v['status'] for v in vs}}


def slots(var, others=(), soc_pins=None):
    """The pins a role slot offers on this chip: accepted first, then warnings; refusals left out and counted."""
    if _get(var, 'role') in NUMBER_ROLES:
        return {'variable': _get(var, 'variable'), 'role': _get(var, 'role'), 'options': [], 'refused': 0, 'note': 'a number, not a pin'}
    opts, refused = [], 0
    for p in soc_pins or pins_of(_get(var, 'soc')):
        r = check(var, p, others)
        if r['verdict'] == 'refused':
            refused += 1
            continue
        opts.append({'pin': p, 'verdict': r['verdict'], 'function': r['function'], 'why': r['why'][0]})
    opts.sort(key=lambda o: (VERDICTS.index(o['verdict']), o['pin']))
    return {'variable': _get(var, 'variable'), 'role': _get(var, 'role'), 'options': opts, 'refused': refused}


def propose(variant, edits, rows=None, variant_rows=None):
    """hsp-3c, THE write path (the no-code slot choice, PUT the drawing, POST /set): `edits` = {variable: value}. Every edit is checked against the
    PROPOSED set (so two pins can swap in one write), then the variant's own rules (variants.resolve with the knobs overridden) - both must pass.
    -> {ok, results[{variable, value, pin, verdict, why}], variant_rule, writes[]}; nothing is written here - the door applies `writes`:
       {target: FirmwareVariant, name, knob, value} for a knob-backed variable, {target: CatomVariable, name, field: bench_value, value, basis} otherwise.
    An unchanged value is skipped (said); one refusal refuses the whole write."""
    vs = variables(variant, rows, variant_rows)
    by = {v['variable']: v for v in vs}
    unknown = [n for n in edits if n not in by]
    if unknown:
        return {'ok': False, 'results': [], 'variant_rule': '', 'writes': [],
                'error': 'no catom variable %s on %s (it has %s)' % (', '.join(unknown), variant, ', '.join(by))}
    proposed, changed, results = [dict(v) for v in vs], {}, []
    pby = {v['variable']: v for v in proposed}
    for n, raw in edits.items():
        v = pby[n]
        if v['role'] in NUMBER_ROLES:
            val = str(raw).strip()
        else:
            pin = resolve_pin(v['soc'], raw)
            val = board_form(v['soc'], pin, v['c_form']) if pin else str(raw).strip()
        if val == v['value']:
            results.append({'variable': n, 'value': val, 'pin': v['pin'], 'verdict': 'unchanged', 'why': ['%s is already %s (%s scope)' % (n, val, v['scope'])]})
            continue
        v['bench_value'], v['value'], v['scope'] = val, val, 'bench'
        changed[n] = val
    for n, val in changed.items():
        r = check(pby[n], val, proposed)
        results.append({'variable': n, 'value': val, 'pin': r['pin'], 'verdict': r['verdict'], 'why': r['why'], 'refusals': r.get('refusals') or r['why'][:1]})
    ok = all(r['verdict'] != 'refused' for r in results)
    soc = vs[0]['soc'] if vs else ''
    overrides = {KNOB_OF[n]: knob_number(soc, resolve_pin(soc, val)) for n, val in changed.items() if n in KNOB_OF and resolve_pin(soc, val)}
    rule = 'no knob-backed variable changed: the variant rules were not asked'
    V = _variants_mod(soc)
    if overrides and V is not None:
        try:
            V.resolve(V.find(variant, variant_rows), overrides)
            rule = 'ok: variant %s accepts %s' % (variant, ', '.join('%s=%s' % kv for kv in sorted(overrides.items())))
        except V.VariantRefused as e:
            ok, rule = False, 'refused by the variant\'s own rule: %s' % e
    writes = []
    if ok:
        for n, val in changed.items():
            if KNOB_OF.get(n) in overrides:
                writes.append({'target': 'FirmwareVariant', 'name': variant, 'knob': KNOB_OF[n], 'value': overrides[KNOB_OF[n]], 'variable': n})
            else:
                verdict = next(r['verdict'] for r in results if r['variable'] == n)
                writes.append({'target': 'CatomVariable', 'name': by[n]['name'], 'field': 'bench_value', 'value': val, 'variable': n,
                               'basis': 'no-code slot choice (%s); checked by catom_variables.check' % verdict})
    return {'ok': ok, 'results': results, 'variant_rule': rule, 'writes': writes}


def apply_writes(writes, cv_rows, variant_rows):
    """Apply propose()'s writes to row objects or dicts in place -> (rows touched (the door saves them), written[], not_written[]). A row missing
    from the given rows (a seed with no stored row) is reported, never invented."""
    import json
    touched, written, missing = [], [], []
    for w in writes:
        if w['target'] == 'FirmwareVariant':
            row = next((r for r in variant_rows or [] if _get(r, 'name') == w['name']), None)
            if row is None:
                missing.append('FirmwareVariant %s (no stored row: knob %s not written)' % (w['name'], w['knob']))
                continue
            k = dict(json.loads(_get(row, 'knobs_json') or '{}'), **{w['knob']: w['value']})
            _set(row, 'knobs_json', json.dumps(k, sort_keys=True))
            written.append('FirmwareVariant %s knob %s = %s' % (w['name'], w['knob'], w['value']))
        else:
            row = next((r for r in cv_rows or [] if _get(r, 'name') == w['name']), None)
            if row is None:
                missing.append('CatomVariable %s (no stored row)' % w['name'])
                continue
            _set(row, 'bench_value', w['value'])
            _set(row, 'bench_basis', w['basis'])
            written.append('CatomVariable %s bench_value = %s' % (w['name'], w['value']))
        if not any(row is t for t in touched):
            touched.append(row)
    return touched, written, missing


def _set(o, k, v):
    if isinstance(o, dict):
        o[k] = v
    else:
        setattr(o, k, v)


def role_assertions(variant, rows=None, variant_rows=None):
    """Each pin variable's value, as the Catom assertion it makes: kind defines-role, the role x the pin, by the catoms that read it."""
    out = []
    for v in variables(variant, rows, variant_rows):
        if v['type'] != 'pin' or not v['pin']:
            continue
        for atom in [a for a in (v['used_by'] or '').split(',') if a] or ['(no catom named)']:
            out.append({'name': '%s:%s:defines-role:%s' % (variant, atom, v['variable']), 'variant': variant, 'atom': atom, 'kind': 'defines-role',
                        'role': v['role'], 'pins': v['pin'], 'variable': v['variable'], 'status': v['status'], 'basis': 'derived from the catom variable %s = %s (%s)' % (
                            v['variable'], v['value'], v['scope'])})
    return out


def pin_roles(variant, rows=None, variant_rows=None):
    """What the pin view draws at each pin: role, variable, verdict - from the same rows the rules read."""
    return [{'pin': v['pin'], 'role': v['role'], 'variable': v['variable'], 'value': v['value'], 'scope': v['scope'], 'verdict': v['status']}
            for v in variables(variant, rows, variant_rows) if v['type'] == 'pin' and v['pin']]


def _c_value(v):
    form, val = v['c_form'], v['value']
    if form == 'arduino-number':
        m = re.match(r'^[DA](\d+)$', val.upper())
        return (m.group(1) if val.upper().startswith('D') else str(14 + int(m.group(1)))) if m else val
    if form == 'gpio-number':
        return v['pin'].replace('GPIO', '') if v['pin'] else val
    if form == 'number':
        return val + ('UL' if val.isdigit() else '')
    return v['pin'] or val


def render_header(variant, rows=None, variant_rows=None):
    """The HAL lines the firmware is generated with: one #define per variable that is not refused (a refused one is a comment saying why)."""
    lines = ['/* GENERATED from the catom variables of %s (cmod.custom.catom_variables, hsp-3d) - each value checked against the pin functions + lifecycle */' % variant]
    for v in variables(variant, rows, variant_rows):
        if v['status'] == 'refused':
            lines.append('/* %s REFUSED: %s */' % (v['variable'], v['status_why'].split('; ')[0]))
            continue
        lines.append('#define %-14s %-10s /* %s, %s scope%s */' % (v['variable'], _c_value(v), v['role'], v['scope'], ', WARNING' if v['status'] == 'warning' else ''))
    return '\n'.join(lines) + '\n'
