"""
@module hal.custom.generate

THE HAL GENERATOR, with its trace (hal-0/hal-1, HAL_CATOM_CATALOGUE_PLAN.md §4a). One call = one HalCodeUnit: a generalized
HalOperation on one pin of one SoC, resolved through the per-SoC rules to register bindings, written in C by the access
mechanism each binding's own facts select. EVERY step is recorded (HalGenerationStep: inputs, rule, output, the module the
data came from and the datasheet place behind it) so a page can show exactly how the code was made (the user, 2026-11-11).

  unit(soc, operation, pin, board='')  -> {unit, bindings[], steps[]}     pure, deterministic, reads only board's tables
  key(soc, operation, pin)             -> 'soc:operation:pin' (the unit's identity on pages and links)
  parse_key(key)                       -> (soc, operation, pin)
  default_pins(soc)                    -> every pin the cited tables reach

An operation is an ordered list of PARTS ({role, action[, value]}); each part is found on the chip through its role rule:
  match pin     the field on the role's registers whose affects_pin is the pin (PORTB5 for PB5; PCMSK2.PCINT20 for PD4)
  match signal  the field whose affects_signal is one of the pin's alternate functions matching the rule (EIMSK.INT0 for PD2)
  match name    the field named by the rule, filled from variables earlier parts yielded (PCICR.PCIE{bank} -> PCIE2)
A part's `yields` (a regex over the register or signal found) sets those variables. action lookup = find, yield, write nothing;
action symbol = a name, not a register (an interrupt vector: PCINT2_vect).

Steps, in order (a unit that stops early says at which step and why):
  operation, board-pin (when a board pin was given), soc-pin, setup (+ field/register/mechanism/c-statement per setup binding),
  then per part: role, field, register, mechanism, c-statement (or vector), then guard, context, macro.
"""
import hashlib
import json
import re

from hal.custom import mechanisms as MX
from hal.custom import operations as OPS
from hal.custom import soc_rules as SR

def _boards():
    """board -> soc, from each chip's RULES 'boards' (data), never a hard-coded map."""
    return {b: soc for soc in SR.PROVIDERS for b in (SR.RULES.get(soc, {}).get('boards') or ())}
WANT = {'set': ('w1-set', 'rw', 'rw-sc'), 'clear': ('w1-clear', 'w1c', 'r-w1c', 'w0c', 'rw', 'rw-sc', 'w'), 'toggle': ('rw-toggle', 'rw'),
        'read': ('r', 'rw', 'rw-toggle', 'rw-sc', 'r-w1c', 'w1c', 'w0c'),
        'lookup': ('rw', 'r', 'w1c', 'r-w1c', 'rw-toggle', 'w1-set', 'w1-clear', 'rw-sc', 'w', 'w-strobe'),
        # hal-3b value actions (the access words of the access table, plan §4d)
        'write': ('rw', 'w', 'rw-sc', 'fifo'), 'read_value': ('r', 'rw', 'rw-sc', 'r-w1c', 'fifo'), 'strobe': ('w-strobe',)}


def key(soc, operation, pin):
    return '%s:%s:%s' % (soc, operation, pin)


def parse_key(k):
    parts = (k or '').split(':')
    return tuple(parts) if len(parts) == 3 and all(parts) else None


def _board_pin(board, pin):
    """-> (soc pin, source, cite) or (None, why, '')."""
    if board == 'arduino-uno-r3':
        from board.custom import board_uno as BU
        hit = BU.D_PINS.get(pin) or BU.A_PINS.get(pin)
        if not hit:
            return None, '%s has no board pin %r (D0-D13, A0-A5)' % (board, pin), ''
        return hit[0], 'board.custom.board_uno.D_PINS / A_PINS', '%s (%s), p.1' % (BU.DOC, BU.REV.split(' —')[0])
    return None, 'no board map for %r yet (the HAL knows arduino-uno-r3; other boards take SoC pin names)' % board, ''


class _Trace:
    def __init__(self, unit_key):
        self.unit, self.rows = unit_key, []

    def add(self, step, title, inputs, rule, output, source='', cite=''):
        self.rows.append({'unit': self.unit, 'index': len(self.rows) + 1, 'step': step, 'title': title, 'inputs': inputs,
                          'rule': rule, 'output': output, 'source': source, 'cite': cite})


def _fill(text, vars_):
    try:
        return text.format(**vars_)
    except KeyError as e:
        raise LookupError('the rule needs {%s}, which no earlier part yielded' % e.args[0])


def _find_field(soc, rule, pin, action, vars_):
    """-> (field, candidates, why). Matches by pin / signal / name (module docstring), then ranks by the action's access preference."""
    names = [_fill(r, vars_) for r in rule['registers']]
    match = rule.get('match', 'pin')
    on = [f for f in SR.fields(soc) if f['register'] in names]
    if match == 'pin':
        cands = [f for f in on if f.get('affects_pin') == pin and (not rule.get('field') or f['field'] == _fill(rule['field'], vars_))]
    elif match == 'signal':
        sig = re.compile(rule['signal_re'])
        mine = [fn for fn in SR.pin_functions(soc, pin) if sig.match(fn)]
        cands = [f for f in on if f.get('affects_signal') in mine]
    else:
        cands = [f for f in on if f['field'] == _fill(rule['field'], vars_)]
    want = WANT[action]
    ranked = sorted([f for f in cands if f['access'] in want], key=lambda f: (want.index(f['access']), names.index(f['register'])))
    if not ranked:
        return None, cands, ('no field on %s reaches %s by %s with an access that can %s it (candidates: %s)'
                             % ('/'.join(names), pin, match, action, ', '.join('%s.%s %s' % (f['register'], f['field'], f['access']) for f in cands) or 'none'))
    pick = ranked[0]
    return pick, cands, '%s.%s (access %s), matched by %s; preferred order for %s: %s' % (
        pick['register'], pick['field'], pick['access'], match, action, ' > '.join(want))


def _yield(rule, field, vars_):
    """Variables a part yields for later parts (rule['yields'] = {var: (regex, 'register'|'signal')})."""
    got = {}
    for var, (rx, what) in (rule.get('yields') or {}).items():
        m = re.match(rx, field['register'] if what == 'register' else (field.get('affects_signal') or ''))
        if m:
            got[var] = m.group(1)
    vars_.update(got)
    return got


def _binding(soc, tr, unit_key, op_name, pin, part, purpose, field, action, value=None):
    """register / mechanism / c-statement for one binding -> the binding dict (status resolved | refused | undetermined)."""
    reg = field['register']
    facts = SR.register_facts(soc, reg)
    b = {'unit': unit_key, 'soc': soc, 'operation': op_name, 'pin': pin, 'part': part, 'purpose': purpose, 'register': reg,
         'field': field['field'], 'bit_lo': field['bit_lo'], 'bit_hi': field['bit_hi'], 'access': field['access'],
         'value': '' if value is None else str(value), 'cite': field.get('page_table', ''), 'address': '', 'space': '',
         'mechanism': '', 'c_text': '', 'status': '', 'why': ''}
    if facts is None:
        b.update(status='undetermined', why='register %s has no address in the chip\'s register facts (%s)' % (reg, SR.fields_source(soc)))
        tr.add('register', 'Where %s is' % reg, reg, 'lookup', b['why'], SR.fields_source(soc))
        return b
    b.update(address=facts['address'], space=facts['space'])
    tr.add('register', 'Where %s is' % reg, reg, 'lookup',
           'address %s, %s space%s' % (facts['address'], facts['space'], ' (I/O address 0x%02X)' % facts['io_addr'] if facts['io_addr'] is not None else ''),
           facts['source'], facts['cite'])
    width = field['bit_hi'] - field['bit_lo'] + 1
    valued = action in ('write', 'read_value')   # hal-3b: a value goes in / comes out (vs a named field constant)
    mech, rule = MX.choose({'action': action if valued else ('field' if value is not None else action),
                            'access': field['access'], 'width': width, 'space': facts['space'], 'io_addr': facts['io_addr'],
                            'reg_width': SR.RULES[soc]['reg_width'], 'lo': field['bit_lo'],
                            'bit_instr_window': SR.RULES[soc]['c'].get('bit_instr_window'), 'clear_by_store': bool(field.get('clear_by_store'))})
    inputs = 'action %s, access %s, width %d, space %s%s' % ('field=%s' % value if value is not None else action, field['access'], width,
                                                           facts['space'], ', I/O 0x%02X' % facts['io_addr'] if facts['io_addr'] is not None else '')
    if mech is None:
        b.update(status='refused', why=rule)
        tr.add('mechanism', 'How %s.%s is written' % (reg, field['field']), inputs, 'hal.custom.mechanisms.choose', 'refused: ' + rule,
               'hal.custom.mechanisms')
        return b
    m = MX.by_name(mech)
    b['mechanism'] = mech
    tr.add('mechanism', 'How %s.%s is written' % (reg, field['field']), inputs, rule, '%s — %s' % (mech, m['title']), 'hal.custom.mechanisms', m['cite'])
    creg = SR.c_register(soc, reg, facts)
    tpl = m['templates'][action if valued else ('field' if value is not None else action)]
    fill = {'reg': creg, 'bit': field['bit_lo'], 'mask': SR.c_mask(soc, field['bit_lo'])}
    if valued:
        fill.update({'value': value, 'lo': field['bit_lo'], 'ctype': SR.RULES[soc]['c']['ctype'],   # required (SR.provider refuses a chip without it)
                     'fmask': SR.c_field(soc, field['bit_lo'], width, 0)['fmask']})
    elif value is not None:
        fill.update(SR.c_field(soc, field['bit_lo'], width, value))
    if mech == 'w0c-flag':   # 1 in the OTHER w0c flags (writing 1 has no effect on them), 0 in the one cleared and in reserved bits
        fill['others'] = SR.RULES[soc]['c']['field_forms']['fmask'].format(m=_access_mask(soc, reg, ('w0c',), field['field']))
    b['c_text'] = tpl.format(**fill)
    keep0 = _w1c_siblings(soc, reg, field) if mech in RMW_MECHANISMS else 0
    if keep0:
        # hal-3b step 1: a read-modify-write writes back what it read; a write-1-to-clear flag that happened to be set (ADCSRA.ADIF,
        # UCSR0A.TXC0, WDTCSR.WDIF) would be CLEARED by that write-back. Those bits are written as 0 instead ("writing zero has no effect").
        km = SR.RULES[soc]['c']['field_forms']['fmask'].format(m=keep0)
        b['c_text'] = _keep_w1c(b['c_text'], creg, km)
        tr.add('w1c-keep', 'Write-1-to-clear flags in %s' % reg, ', '.join('%s.%s' % (reg, f['field']) for f in SR.fields(soc)
               if f['register'] == reg and f['access'] in ('w1c', 'r-w1c') and f['field'] != field['field']),
               'a read-modify-write must write 0 to them (a 1 written back would clear a pending flag)', b['c_text'],
               'hal.custom.generate (_keep_w1c)', 'the w1c access of each field: %s' % SR.fields_source(soc))
    b['status'] = 'resolved'
    tr.add('c-statement', 'The C for %s.%s' % (reg, field['field']), 'template %r with reg=%s, bit=%d%s' % (
        tpl, creg, field['bit_lo'], ', value=%s' % value if value is not None else ''), 'fill the template', b['c_text'],
        'hal.custom.mechanisms (%s)' % mech, SR.RULES[soc]['c']['mask'].format(bit='n') + ' is this SoC\'s bit mask form')
    return b


RMW_MECHANISMS = ('avr-io-byte-rmw', 'mem-rmw', 'rmw-field', 'field-write', 'strobe')


def _access_mask(soc, reg, accesses, but=None):
    """the mask of the register's cited fields with one of these access words, except the field named `but`"""
    m = 0
    for f in SR.fields(soc):
        if f['register'] == reg and f['access'] in accesses and f['field'] != but:
            m |= ((1 << (f['bit_hi'] - f['bit_lo'] + 1)) - 1) << f['bit_lo']
    return m


def _w1c_siblings(soc, reg, field):
    """the mask of the OTHER write-1-to-clear fields in the register (0 if none)"""
    m = 0
    for f in SR.fields(soc):
        if f['register'] == reg and f['access'] in ('w1c', 'r-w1c') and f['field'] != field['field']:
            m |= ((1 << (f['bit_hi'] - f['bit_lo'] + 1)) - 1) << f['bit_lo']
    return m


def _keep_w1c(c, creg, km):
    """rewrite a read-modify-write statement so the register's value READ is masked with ~km before it is written back:
    every read of `creg` on the right-hand side becomes (creg & ~km). Covers the |= / &= / ^= and the `reg = (reg & ...)` forms."""
    ce = re.escape(creg)
    m = re.match(r'^\s*%s\s*([|&^])=\s*(.*);\s*$' % ce, c)
    if m:   # REG op= X  ->  REG = (REG & ~km) op X   (for &=, the cleared bits join km: REG &= ~(X | km) reads the same)
        op, rhs = m.group(1), m.group(2)
        return '%s = (%s & ~%s) %s %s;' % (creg, creg, km, op, rhs)
    lhs, eq, rhs = c.partition('=')
    return lhs + eq + re.sub(r'(?<![\w.])%s(?![\w])' % ce, '(%s & ~%s)' % (creg, km), rhs, count=1)


def _part_value(soc, role, p, vars_, args, tr, i, functions, field=None):
    """hal-3b: the C expression a part writes -> (expression, words). Forms (plan §4b):
      '{arg}' / an expression over args      the op's own arguments
      role value_expr                         over args + named cited facts ({f_cpu} ...), composite or not
      '@derive:divider:{arg}'                 the field's CITED value table mapped division factor -> code, as a C conditional
                                              (constant-folded when the argument is a constant; an unlisted factor gives 0xFF,
                                              which a static check in the role layer refuses)
      '@derive:mode:<name>'                   the WGM-style mode whose cited description carries the rule's `modes` words
      '@derive:signal_index:<re>'             the number in the target's signal matching <re> (ADC3 -> 3)
    """
    v = p.get('value')
    facts = SR.chip_facts(soc)
    env = dict(vars_, **{a: '(%s)' % a for a in args}, **facts)
    if role.get('value_expr') and (v is None or v == 'value_expr'):
        try:
            expr = role['value_expr'].format(**env)
        except KeyError as e:
            raise LookupError('value_expr needs {%s}' % e.args[0])
        if role.get('range_bits'):
            # hal-3b step 1: a computed register value that does not fit its field (a baud rate too slow for UBRR's 12 bits, a tick too slow
            # for an 8-bit top) is a COMPILE error, never a silent truncation - the same bit-field guard as the divider (constants only)
            top = (1 << int(role['range_bits'])) - 1
            expr = '(0u * sizeof(struct { int hal_value_out_of_range : ((%s) <= %dUL) ? 1 : -1; }) + (%s))' % (expr, top, expr)
        tr.add('value', 'Part %d: the value' % i, role['value_expr'], 'role value_expr over args + cited chip facts%s' % (
            '; checked at compile time to fit %d bits' % role['range_bits'] if role.get('range_bits') else ''), expr, 'hal.custom.soc_rules',
            '; '.join('%s = %s' % kv for kv in sorted(facts.items())))
        return expr, 'value_expr %s' % role['value_expr']
    if isinstance(v, str) and v.startswith('@derive:'):
        kind, _, rest = v[len('@derive:'):].partition(':')
        f = field or _first_field(soc, role, vars_)
        if f is None:
            raise LookupError('no cited field to derive %s from' % kind)
        table = f.get('values') or {}
        if kind == 'divider':
            pairs = []
            for code, words in sorted(table.items()):
                m = re.search(r'/\s*(\d+)\b|division factor (\d+)', words)
                n = int(m.group(1) or m.group(2)) if m else (1 if 'No prescaling' in words else None)
                if n is not None and 'External' not in words and int(code, 2) and all(n != q for q, _ in pairs):
                    pairs.append((n, int(code, 2)))
            arg = rest.format(**env)
            ok = ' || '.join('(%s) == %du' % (arg, n) for n, _ in pairs)
            # an unlisted factor is a COMPILE error ("negative width in bit-field 'hal_unlisted_prescaler'"), and so is a NON-constant
            # argument ("width not an integer constant"): a bit-field width must be an integer constant expression (econ's review, 2026-11-13;
            # a char array would have been a silent VLA at run time)
            expr = '(0u * sizeof(struct { int hal_unlisted_prescaler : (%s) ? 1 : -1; }) + (%s0u))' % (ok, ''.join('(%s) == %du ? %du : ' % (arg, n, c) for n, c in pairs))
            tr.add('value', 'Part %d: the code for a division factor' % i, '%s.%s values' % (f['register'], f['field']),
                   'derive divider: each cited value whose words name a division factor', ', '.join('/%d -> %d' % pc for pc in pairs),
                   SR.fields_source(soc), f.get('page_table', ''))
            return expr, 'the cited %s.%s divider table (the argument must be a constant; an unlisted factor does not compile)' % (f['register'], f['field'])
        if kind == 'mode':
            alts = (role.get('modes') or {}).get(rest)
            if not alts:
                raise LookupError('no `modes` words for %r in the role rule' % rest)
            hits = set()
            for code, words in table.items():
                for m in re.finditer(r'mode (\d+) ([^;]*)', words):   # a low-bits key names one mode per high-bits value
                    if any(all(w in m.group(2) for w in ws) for ws in alts):
                        hits.add(int(m.group(1)))
            if len(hits) != 1:
                raise LookupError('mode %r matches %s cited modes of %s.%s (need exactly one)' % (rest, sorted(hits) or 'no', f['register'], f['field']))
            mode = hits.pop()
            tr.add('value', 'Part %d: the mode' % i, '%s.%s mode table' % (f['register'], f['field']), 'derive mode: the one cited mode whose '
                   'description carries %s' % ' | '.join(' + '.join(ws) for ws in alts), 'mode %d' % mode, SR.fields_source(soc), f.get('page_table', ''))
            return '%du' % mode, 'mode %d (%s)' % (mode, rest)
        if kind == 'signal_index':
            sig = next((fn for fn in functions if re.match(rest, fn)), None)
            if sig is None:
                raise LookupError('the target has no signal matching %s (its signals: %s)' % (rest, ', '.join(functions) or 'none'))
            n = int(re.search(r'(\d+)$', sig).group(1))
            tr.add('value', 'Part %d: the signal index' % i, sig, 'derive signal_index', str(n), 'hal.custom.soc_rules')
            return '%du' % n, '%s -> %d' % (sig, n)
        raise LookupError('unknown derive kind %r' % kind)
    if isinstance(v, str) and '{' in v:
        try:
            expr = v.format(**env)
        except KeyError as e:
            raise LookupError('the value needs {%s}, which is no argument or fact' % e.args[0])
        return expr, 'the op argument(s) %s' % ', '.join(args)
    if v is not None and v in (role.get('values') or {}):
        return '%du' % role['values'][v], 'value %s' % v
    raise LookupError('no value for this part (the op gives %r)' % (v,))


def _first_field(soc, role, vars_):
    if role.get('fields'):
        cf = role['fields'][0]
        reg = _fill(cf['register'], vars_)
        names = [_fill(x, vars_) for x in (cf['field'] if isinstance(cf['field'], list) else [cf['field']])]
        return next((x for x in SR.fields(soc) if x['register'] == reg and x['field'] in names), None)
    names = [_fill(r, vars_) for r in role.get('registers') or []]
    fname = _fill(role['field'], vars_) if role.get('field') else None
    return next((x for x in SR.fields(soc) if x['register'] in names and (fname is None or x['field'] == fname)), None)


def _wide_binding(soc, tr, unit_key, op_name, pin, part, purpose, field, wide, action, value):
    """hal-3b: a value wider than the chip's registers through its wide-access symbol (avr-libc OCR1A / ADC: avr-gcc orders the byte
    accesses the datasheet requires - the high byte through TEMP first on a write, the low byte first on a read)."""
    facts = SR.register_facts(soc, wide)
    if 'wide_ctype' not in SR.RULES[soc]['c']:
        return {'unit': unit_key, 'soc': soc, 'operation': op_name, 'pin': pin, 'part': part, 'purpose': purpose, 'register': wide, 'field': field['field'],
                'bit_lo': field['bit_lo'], 'bit_hi': field['bit_hi'], 'access': field['access'], 'value': '', 'cite': '', 'address': '', 'space': '',
                'mechanism': '', 'c_text': '', 'status': 'refused', 'why': 'the role names a wide symbol but the chip rules give no wide_ctype (never a default)'}
    mech = 'wide-write' if action == 'write' else 'wide-read'
    m = MX.by_name(mech)
    c = m['templates'][action].format(wide=SR.c_register(soc, wide, facts), value=value, ctype=SR.RULES[soc]['c']['wide_ctype'])
    tr.add('mechanism', 'How %s is reached' % wide, 'a value wider than the %d-bit registers' % SR.RULES[soc]['reg_width'], 'the role\'s wide symbol',
           '%s — %s' % (mech, m['title']), 'hal.custom.mechanisms', m['cite'])
    tr.add('c-statement', 'The C for %s' % wide, m['templates'][action], 'fill the template', c, 'hal.custom.mechanisms (%s)' % mech)
    return {'unit': unit_key, 'soc': soc, 'operation': op_name, 'pin': pin, 'part': part, 'purpose': purpose, 'register': wide,
            'field': field['field'], 'bit_lo': field['bit_lo'], 'bit_hi': field['bit_hi'], 'access': field['access'],
            'value': '' if value is None else str(value), 'cite': field.get('page_table', ''), 'address': facts['address'], 'space': facts['space'],
            'mechanism': mech, 'c_text': c, 'status': 'resolved', 'why': ''}


def _blank(unit_key, soc, op_name, pin, part, purpose):
    return {'unit': unit_key, 'soc': soc, 'operation': op_name, 'pin': pin, 'part': part, 'purpose': purpose, 'register': '', 'field': '',
            'bit_lo': 0, 'bit_hi': 0, 'access': '', 'value': '', 'cite': '', 'address': '', 'space': '', 'mechanism': '', 'c_text': '', 'status': '', 'why': ''}


def _call_binding(soc, tr, unit_key, op_name, pin, part, role, i, args, op):
    """hal-3b step 1: a part that is a cited LIBRARY call (avr-libc wdt_enable: the WDT's timed sequence). Refused unless the chip rules
    DECLARE the library (name, version, licence) and the role says why the call is interrupt-safe. A ranged argument is checked at compile
    time with the bit-field guard - which also means a NON-constant argument does not compile (refused, never clamped at run time)."""
    cl = role['call']
    b = _blank(unit_key, soc, op_name, pin, part, role.get('purpose') or op['intent'])
    b['cite'] = role.get('cite', '')
    libs = SR.RULES[soc].get('libraries') or {}
    lib = libs.get(cl.get('library'))
    if lib is None:
        b.update(status='refused', why='%s declares no library %r (declared: %s): a call needs a provider-declared library; a chip without one '
                 'uses register rows (keyed-write)' % (soc, cl.get('library'), ', '.join(sorted(libs)) or 'none'))
        tr.add('call', 'Part %d: the library call' % i, cl.get('function', ''), 'the chip rules must declare the library', 'refused: ' + b['why'],
               'hal.custom.soc_rules RULES[%s].libraries' % soc)
        return b
    if not cl.get('isr_safe_basis'):
        b.update(status='refused', why='the call role gives no isr_safe_basis (why an interrupt cannot split the sequence): never assumed')
        return b
    env = {a: '(%s)' % a for a in args}
    argv = []
    for a_text in cl.get('args') or []:
        try:
            expr = a_text.format(**env)
        except KeyError as e:
            b.update(status='refused', why='the call argument needs {%s}, which is no argument of the operation' % e.args[0])
            return b
        name = a_text.strip('{}')
        rng = (cl.get('arg_range') or {}).get(name)
        if rng:
            expr = '(0u * sizeof(struct { int hal_arg_out_of_range : ((unsigned)(%s) <= %du) ? 1 : -1; }) + (%s))' % (expr, rng[1], expr)
        argv.append(expr)
    m = MX.by_name('library-call')
    b.update(mechanism='library-call', c_text=m['templates']['call'].format(function=cl['function'], args=', '.join(argv)), status='resolved',
             value=', '.join(argv))
    tr.add('call', 'Part %d: the library call' % i, '%s from %s (%s)' % (cl['function'], cl['include'], cl['library']),
           'a sequence plain writes cannot express: %s' % cl.get('why', ''), b['c_text'],
           'hal.custom.soc_rules RULES[%s].libraries[%s] = %s' % (soc, cl['library'], lib.get('version', '')),
           '%s; interrupt-safe: %s%s' % (role.get('cite', ''), cl['isr_safe_basis'],
                                          '; %s must be a constant in %d..%d (else a compile error, never a run-time clamp)' % (
                                              ', '.join(cl['arg_range']), *next(iter(cl['arg_range'].values()))) if cl.get('arg_range') else ''))
    return b


def _clear_all_binding(soc, tr, unit_key, op_name, pin, part, role, i, vars_, op):
    """every flag of one register cleared by ONE store (MCUSR = 0): only when EVERY cited field of the register has the role's access word
    (w0c: writing 0 clears, the reserved bits are written 0) - checked against the field rows, never assumed."""
    ca = role['clear_all']
    reg = _fill(ca['register'], vars_)
    b = _blank(unit_key, soc, op_name, pin, part, role.get('purpose') or op['intent'])
    b.update(register=reg, cite=role.get('cite', ''))
    flds = [f for f in SR.fields(soc) if f['register'] == reg]
    facts = SR.register_facts(soc, reg)
    bad = [f['field'] for f in flds if f['access'] != ca['access']]
    if ca['access'] != 'w0c' or not flds or bad or facts is None:
        b.update(status='refused', why='clear_all of %s needs every cited field w0c (fields: %s; not w0c: %s)' % (
            reg, ', '.join(f['field'] for f in flds) or 'none', ', '.join(bad) or 'none'))
        return b
    m = MX.by_name('w0c-flag')
    c = m['templates']['clear'].format(reg=SR.c_register(soc, reg, facts), others=SR.RULES[soc]['c']['field_forms']['fmask'].format(m=0))
    b.update(field=', '.join(f['field'] for f in flds), bit_lo=min(f['bit_lo'] for f in flds), bit_hi=max(f['bit_hi'] for f in flds),
             access='w0c', value='0', address=facts['address'], space=facts['space'], mechanism='w0c-flag', c_text=c, status='resolved')
    tr.add('field', 'Part %d: every flag of %s' % (i, reg), ', '.join('%s %s' % (f['field'], f['access']) for f in flds),
           'clear_all: every cited field must be w0c', 'all w0c: one store of 0 clears them all, no read', SR.fields_source(soc), role.get('cite', ''))
    tr.add('c-statement', 'The C for %s' % reg, m['templates']['clear'], 'fill the template', c, 'hal.custom.mechanisms (w0c-flag)', m['cite'])
    return b


def _isr_safe(b):
    return MX.by_name(b['mechanism'].split(' / ')[-1])['isr_safe']


def unit(soc, operation, pin, board=''):
    board_pin = pin if board else ''
    tr = _Trace('')
    out = {'unit': None, 'bindings': [], 'steps': tr.rows}
    op = OPS.by_name(operation)
    try:
        SR.provider(soc)
    except SR.SocUnknown as e:
        out['unit'] = {'key': key(soc, operation, pin), 'status': 'refused', 'why': str(e).strip('"')}
        return out
    pin_note = ('', '')
    if board:
        if _boards().get(board) != soc:
            out['unit'] = {'key': key(soc, operation, pin), 'status': 'refused', 'why': 'board %r is not on soc %r' % (board, soc)}
            return out
        soc_pin, src, cite = _board_pin(board, pin)
        if soc_pin is None:
            out['unit'] = {'key': key(soc, operation, pin), 'status': 'refused', 'why': src}
            return out
        pin, pin_note = soc_pin, (src, cite)
    uk = key(soc, operation, pin)
    tr.unit = uk
    u = {'key': uk, 'soc': soc, 'operation': operation, 'pin': pin, 'board_pin': board_pin, 'macro': '', 'c_text': '', 'c_text_init': '',
         'includes': '', 'guarded': False, 'status': '', 'why': '', 'steps_sha256': '', 'code_sha256': ''}
    out['unit'] = u

    def stop(status, why):
        u.update(status=status, why=why)
        return out
    if op is None:
        tr.add('operation', 'The operation', operation, 'lookup', 'unknown operation %r' % operation, 'hal.custom.operations')
        return stop('refused', 'unknown operation %r' % operation)
    parts = OPS.parts(op)
    tr.add('operation', 'The operation', operation, 'lookup',
           '%s%s — %s' % ('; '.join('%s %s%s' % (p['role'], p['action'], '=' + p['value'] if p.get('value') else '') for p in parts),
                          '; setup %s' % op['setup'] if op.get('setup') else '', op['intent']),
           'hal.custom.operations (HalOperation %s)' % operation, op['basis'])
    if board:
        tr.add('board-pin', 'Board pin to chip pin', '%s %s' % (board, board_pin), 'lookup', '%s -> %s' % (board_pin, pin), pin_note[0], pin_note[1])
    rules = SR.RULES[soc]
    if op.get('target') == 'peripheral':
        # hal-3b: a peripheral INSTANCE (USART0, TIMER2, ADC): its variables and signals come from the chip's peripherals table
        per = (rules.get('peripherals') or {}).get(pin)
        if per is None:
            tr.add('peripheral', 'The peripheral', pin, 'lookup', '%s has no peripheral %r (known: %s)' % (
                soc, pin, ', '.join(sorted(rules.get('peripherals') or {})) or 'none'), 'hal.custom.soc_rules peripherals')
            return stop('refused', '%s has no peripheral %r' % (soc, pin))
        tr.add('peripheral', 'The peripheral', pin, 'lookup', 'variables %s; signals %s' % (
            ', '.join('%s=%s' % kv for kv in sorted(per['vars'].items())) or 'none', ', '.join(per.get('signals') or []) or 'none'),
            'hal.custom.soc_rules RULES[%s].peripherals' % soc, per.get('cite', ''))
        if op['family'] not in (per.get('families') or ()):
            tr.add('peripheral', 'The peripheral', pin, 'family', '%s serves %s, not %s' % (pin, ', '.join(per.get('families') or ()) or 'nothing', op['family']),
                   'hal.custom.soc_rules RULES[%s].peripherals' % soc, per.get('cite', ''))
            return stop('refused', '%s is not a %s peripheral (it serves %s)' % (pin, op['family'], ', '.join(per.get('families') or ()) or 'no family'))
        vars_ = dict(per['vars'])
        functions = list(per.get('signals') or [])
    else:
        pp = SR.pin_parts(soc, pin)
        src, cite = SR.pin_source(soc)
        if pp is None:
            tr.add('soc-pin', 'The chip pin', pin, 'lookup', '%s has no pin %r' % (soc, pin), src, cite)
            return stop('refused', '%s has no pin %r' % (soc, pin))
        tr.add('soc-pin', 'The chip pin', pin, 'lookup', (('port %s, bit %d' % (pp['port'], pp['bit'])) if pp['port'] else 'pad %d' % pp['n'])
               + ('; functions %s' % ', '.join(SR.pin_functions(soc, pin)) if SR.pin_functions(soc, pin) else '')
               + ('; caveat: %s' % SR.pin_caveat(soc, pin) if SR.pin_caveat(soc, pin) else ''), src, cite)
        vars_ = {'port': pp['port'], 'n': pp['n']}
        functions = SR.pin_functions(soc, pin)
        # hal-3b: variables named by the pin's own alternate functions (OC0A -> t=0, ch=A), from the chip's signal_vars rules
        for rx, names in rules.get('signal_vars') or []:
            for fn in functions:
                m = re.match(rx, fn)
                if m:
                    got = {k: m.group(g) for k, g in names.items()}
                    vars_.update(got)
                    tr.add('signal-vars', 'What the pin\'s %s function names' % fn, fn, 'hal.custom.soc_rules signal_vars %s' % rx,
                           ', '.join('%s = %s' % kv for kv in sorted(got.items())), 'hal.custom.soc_rules', SR.pin_source(soc)[1])
    bindings = out['bindings']
    # setup
    setup = rules['setups'].get(op.get('setup', ''), []) if op.get('setup') else []
    tr.add('setup', 'Setup before the operation', op.get('setup') or '(none)', 'hal.custom.soc_rules RULES[%s].setups' % soc,
           ('%d binding(s) first, via the signal routing matrix: %s' % (len(setup), '; '.join('%s.%s = %s' % (_fill(s['register'], vars_), s['field'], s['value']) for s in setup)))
           if setup else 'none: on this chip the operation needs no routing first', 'hal.custom.soc_rules', '; '.join(s['cite'] for s in setup))
    for s in setup:
        reg = _fill(s['register'], vars_)
        f = next((x for x in SR.fields(soc) if x['register'] == reg and x['field'] == s['field']), None)
        if f is None:
            tr.add('field', 'Setup field', '%s.%s' % (reg, s['field']), 'lookup', 'not in the cited table', SR.fields_source(soc))
            return stop('undetermined', 'setup field %s.%s is not in the cited table' % (reg, s['field']))
        tr.add('field', 'Setup field %d: %s.%s' % (len(bindings) + 1, reg, s['field']), s['purpose'], 'named by the setup rule',
               'bits %d-%d, access %s' % (f['bit_hi'], f['bit_lo'], f['access']), SR.fields_source(soc), f.get('page_table', ''))
        b = _binding(soc, tr, uk, operation, pin, len(bindings) + 1, s['purpose'], f, 'set', value=s['value'])
        b['mechanism'] = b['mechanism'] and 'signal-routing-matrix / ' + b['mechanism']
        bindings.append(b)
    # parts
    symbols = []
    reads = []
    extra_includes = []
    args = [x['name'] for x in op.get('args') or []]
    for i, p in enumerate(parts, 1):
        role = rules['roles'].get(p['role'])
        if role and role.get('by_action') and p['action'] in role['by_action']:   # hal-3b: per-action registers (C3 W1TS/W1TC/IN, LiteX rxtx)
            role = dict({k: v for k, v in role.items() if k != 'by_action'}, **role['by_action'][p['action']])
        if role and role.get('inherent'):   # hal-3b: fixed by silicon - nothing to write, and the trace says why
            tr.add('role', 'Part %d: role %s' % (i, p['role']), soc, 'hal.custom.soc_rules', 'inherent: ' + role['inherent']['words'],
                   'hal.custom.soc_rules', role['inherent'].get('cite', ''))
            continue
        if role and role.get('call') and p['action'] == 'call':   # hal-3b step 1: a cited library function (econ's review folded in)
            b = _call_binding(soc, tr, uk, operation, pin, len(bindings) + 1, role, i, args, op)
            bindings.append(b)
            if b['status'] != 'resolved':
                return stop(b['status'], 'part %d (%s): %s' % (i, p['role'], b['why']))
            extra_includes.append(role['call']['include'])
            continue
        if role and role.get('clear_all') and p['action'] == 'clear':   # every flag of a register at once (MCUSR = 0)
            b = _clear_all_binding(soc, tr, uk, operation, pin, len(bindings) + 1, role, i, vars_, op)
            bindings.append(b)
            if b['status'] != 'resolved':
                return stop(b['status'], 'part %d (%s): %s' % (i, p['role'], b['why']))
            continue
        if role and role.get('fields') and p['action'] in ('write', 'set'):   # hal-3b: one logical value over several fields
            try:
                value_c, vwhy = _part_value(soc, role, p, vars_, args, tr, i, functions)
            except LookupError as e:
                return stop('refused', 'part %d (%s): %s' % (i, p['role'], e))
            for j, cf in enumerate(role['fields'], 1):
                try:
                    reg = _fill(cf['register'], vars_)
                    names = [_fill(x, vars_) for x in (cf['field'] if isinstance(cf['field'], list) else [cf['field']])]
                except LookupError as e:
                    return stop('refused', 'part %d (%s): %s' % (i, p['role'], e))
                f = next((x for x in SR.fields(soc) if x['register'] == reg and x['field'] in names), None)
                if f is None:
                    return stop('undetermined', 'composite part %d.%d: no cited field %s on %s' % (i, j, '/'.join(names), reg))
                width = f['bit_hi'] - f['bit_lo'] + 1
                lit = re.fullmatch(r'\(?(\d+)u\)?', value_c)
                piece = ((int(lit.group(1)) >> cf['lo']) & ((1 << width) - 1)) if lit else '((%s) >> %d) & 0x%Xu' % (value_c, cf['lo'], (1 << width) - 1)
                tr.add('field', 'Part %d.%d: composite slice %s.%s' % (i, j, reg, f['field']), 'logical bits %d..%d of %s' % (
                    cf['lo'] + width - 1, cf['lo'], vwhy), 'hal.custom.soc_rules fields (composite)', 'bits %d-%d, access %s' % (
                    f['bit_hi'], f['bit_lo'], f['access']), SR.fields_source(soc), f.get('page_table', ''))
                b = _binding(soc, tr, uk, operation, pin, len(bindings) + 1, role.get('purpose') or op['intent'], f,
                             'set' if isinstance(piece, int) else 'write', value=piece)   # a folded constant is a plain field write
                bindings.append(b)
                if b['status'] != 'resolved':
                    return stop(b['status'], 'binding %d: %s' % (b['part'], b['why']))
            continue
        if not role or role.get('missing') or not (role.get('registers') or role.get('vector')):
            why = (role or {}).get('missing') or 'no rule for role %r on %s' % (p['role'], soc)
            tr.add('role', 'Part %d: role %s' % (i, p['role']), soc, 'hal.custom.soc_rules', 'unsupported: ' + why, 'hal.custom.soc_rules', (role or {}).get('cite', ''))
            return stop('unsupported', why)
        if p['action'] == 'symbol':
            try:
                name = _fill(role['vector'], vars_)
            except LookupError as e:
                return stop('refused', str(e))
            known = SR.vectors(soc)
            ok = name in known
            tr.add('vector', 'Part %d: the interrupt vector' % i, role['vector'] + ' with ' + ', '.join('%s=%s' % kv for kv in sorted(vars_.items())),
                   'fill the vector name, then look it up in the chip\'s vector table', ('%s (vector %d)' % (name, known[name])) if ok else '%s is not a vector of %s' % (name, soc),
                   SR.vectors_source(soc), role['cite'])
            if not ok:
                return stop('undetermined', '%s is not in the vector table' % name)
            symbols.append(name)
            continue
        try:
            names = ', '.join(_fill(r, vars_) for r in role['registers'])
        except LookupError as e:
            return stop('refused', str(e))
        tr.add('role', 'Part %d: role %s' % (i, p['role']), '%s, pin %s' % (soc, pin), 'hal.custom.soc_rules RULES[%s].roles[%s]' % (soc, p['role']),
               names + (' (field %s)' % role['field'] if role.get('field') else '') + ('; condition: ' + role['condition'] if role.get('condition') else ''),
               'hal.custom.soc_rules', role['cite'])
        f, cands, why = _find_field(soc, role, pin, p['action'], vars_)
        tr.add('field', 'Part %d: the field' % i, '%d candidate(s): %s' % (len(cands), ', '.join('%s.%s %s' % (c['register'], c['field'], c['access']) for c in cands)),
               'match by %s; prefer the access that does the action in one write' % role.get('match', 'pin'),
               why if f else 'none: ' + why, SR.fields_source(soc), f.get('page_table', '') if f else '')
        if f is None:
            if role.get('match') == 'signal' and not [fn for fn in SR.pin_functions(soc, pin) if re.match(role['signal_re'], fn)]:
                return stop('unsupported', '%s has no %s alternate function (its functions: %s)' % (
                    pin, role['signal_re'].strip('^$').replace('\\d', 'n'), ', '.join(SR.pin_functions(soc, pin)) or 'none'))
            if not cands:   # nothing cited for this pin yet: a gap in the table, not a fact about the chip
                return stop('undetermined', 'the cited field table has no %s field for %s yet (%s)' % (names, pin, SR.fields_source(soc)))
            return stop('unsupported', why)
        got = _yield(role, f, vars_)
        if got:
            tr.add('yield', 'Part %d: what it tells later parts' % i, '%s.%s' % (f['register'], f['field']), 'hal.custom.soc_rules yields',
                   ', '.join('%s = %s' % kv for kv in sorted(got.items())), 'hal.custom.soc_rules', role['cite'])
        if p['action'] == 'lookup':
            continue
        width = f['bit_hi'] - f['bit_lo'] + 1
        value = None
        action = p['action']
        if action in ('write', 'read_value'):
            if action == 'write':
                try:
                    value, _vwhy = _part_value(soc, role, p, vars_, args, tr, i, functions)
                except LookupError as e:
                    return stop('refused', 'part %d (%s): %s' % (i, p['role'], e))
            wide = _fill(role['wide'], vars_) if role.get('wide') else ''
            if wide and wide != f['register'] and SR.register_facts(soc, wide):   # the chip's wide-access symbol (avr-libc OCR1A / ADC)
                b = _wide_binding(soc, tr, uk, operation, pin, len(bindings) + 1, role.get('purpose') or op['intent'], f, wide, action, value)
            else:
                b = _binding(soc, tr, uk, operation, pin, len(bindings) + 1, role.get('purpose') or op['intent'], f, action, value=value)
            bindings.append(b)
            if b['status'] != 'resolved':
                return stop(b['status'], 'binding %d: %s' % (b['part'], b['why']))
            if action == 'read_value':
                reads.append(b)
            continue
        if width > 1:
            vkey = p.get('value') or p['action']
            if isinstance(vkey, str) and vkey.startswith('@derive:'):
                try:
                    value, _vwhy = _part_value(soc, role, p, vars_, args, tr, i, functions, field=f)
                except LookupError as e:
                    return stop('refused', 'part %d (%s): %s' % (i, p['role'], e))
            else:
                value = (role.get('values') or {}).get(vkey)
            if value is None and vkey in (role.get('lacks') or {}):   # hal-iso: a setting the chip does not have, cited
                tr.add('value', 'Part %d: the setting %s' % (i, vkey), '%s.%s' % (f['register'], f['field']), 'hal.custom.soc_rules lacks',
                       'unsupported: ' + role['lacks'][vkey], 'hal.custom.soc_rules', role.get('cite', ''))
                return stop('unsupported', 'the chip has no %s setting: %s' % (vkey, role['lacks'][vkey]))
            if value is None:
                return stop('refused', 'a %d-bit field %s.%s needs a value for %r (role rule values)' % (width, f['register'], f['field'], vkey))
        lit = re.fullmatch(r'\(?(\d+)u\)?', value) if isinstance(value, str) else None
        if lit:
            value = int(lit.group(1))   # a derived constant (a mode number) folds to the plain field write
        act = 'write' if isinstance(value, str) else p['action']   # a derived C expression is written as a value
        b = _binding(soc, tr, uk, operation, pin, len(bindings) + 1, role.get('purpose') or op['intent'], f, act, value=value)
        bindings.append(b)
        if b['status'] != 'resolved':
            return stop(b['status'], 'binding %d: %s' % (b['part'], b['why']))
    # guard + context
    c = rules['c']
    name = '%s_%s' % (op['c_name'], pin.upper())
    unsafe = [b for b in bindings if not _isr_safe(b)]
    stmts = [(c['guard'] % b['c_text']) if not _isr_safe(b) else b['c_text'] for b in bindings]
    plain = [b['c_text'] for b in bindings]
    if bindings:
        tr.add('guard', 'Interrupt safety', ', '.join(b['mechanism'] for b in bindings),
               'a binding whose mechanism is not isr_safe is wrapped in the SoC guard',
               ('guarded: %s' % ', '.join('%s.%s' % (b['register'], b['field']) for b in unsafe)) if unsafe else 'none needed: every write is one indivisible write',
               'hal.custom.mechanisms (isr_safe) + hal.custom.soc_rules (guard)', c['guard_why'] if unsafe else '')
    includes = list(c['includes']) + ([c['guard_include']] if unsafe and c['guard_include'] else [])
    includes += [x for x in extra_includes if x not in includes]
    params = '(%s)' % ', '.join(args)
    if symbols:
        text = '#define %s %s' % (name, symbols[0])
    elif op['returns'] != 'void':
        text = '#define %s%s %s' % (name, params, (reads[-1] if reads else bindings[-1])['c_text'] if bindings else '0')
    elif not bindings:   # every part inherent on this chip: the macro is the empty statement, and the trace said why
        text = '#define %s%s do { } while (0)' % (name, params)
    else:
        text = '#define %s%s do { %s } while (0)' % (name, params, ' '.join(stmts))
    if unsafe and op['returns'] == 'void':
        u['c_text_init'] = '#define %s_INIT%s do { %s } while (0)' % (name, params, ' '.join(plain))
        tr.add('context', 'The init-context form', name + '_INIT', c['init_rule'], u['c_text_init'], 'hal.custom.soc_rules (init_rule)', c['init_cite'])
    u.update(macro=name, c_text=text, includes=' '.join(includes), status='resolved', guarded=bool(unsafe))
    if SR.pin_caveat(soc, pin):
        u['why'] = SR.pin_caveat(soc, pin)
    u['steps_sha256'] = hashlib.sha256(json.dumps([{k: r[k] for k in ('step', 'inputs', 'rule', 'output', 'source', 'cite')} for r in tr.rows],
                                                  sort_keys=True).encode()).hexdigest()
    u['code_sha256'] = hashlib.sha256((text + '\n' + u['c_text_init']).encode()).hexdigest()
    tr.add('macro', 'The finished macro', name, 'one macro per operation and pin; a read is an expression, a vector a name, a write a statement',
           text, 'hal.custom.generate', 'includes: %s' % ' '.join(includes))
    return out


def default_pins(soc):
    """Every pin the cited field tables reach, in chip order (PB0..PB7, PC0.., PD0..PD7; GPIO0..GPIO21)."""
    pins = {f.get('affects_pin') for f in SR.fields(soc) if f.get('affects_pin') and SR.pin_parts(soc, f['affects_pin'])}
    return sorted(pins, key=lambda p: ((SR.pin_parts(soc, p) or {}).get('port', ''), int(''.join(ch for ch in p if ch.isdigit()) or 0)))
