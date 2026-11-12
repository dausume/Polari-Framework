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

BOARDS = {'arduino-uno-r3': 'atmega328p'}
WANT = {'set': ('w1-set', 'rw'), 'clear': ('w1-clear', 'w1c', 'rw'), 'toggle': ('rw-toggle', 'rw'), 'read': ('r', 'rw', 'rw-toggle'),
        'lookup': ('rw', 'r', 'w1c', 'rw-toggle', 'w1-set', 'w1-clear')}


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
        b.update(status='undetermined', why='register %s has no address in %s' % (reg, 'the avr-libc snapshot' if soc == 'atmega328p' else 'REGISTERS'))
        tr.add('register', 'Where %s is' % reg, reg, 'lookup', b['why'], SR.fields_source(soc))
        return b
    b.update(address=facts['address'], space=facts['space'])
    tr.add('register', 'Where %s is' % reg, reg, 'lookup',
           'address %s, %s space%s' % (facts['address'], facts['space'], ' (I/O address 0x%02X)' % facts['io_addr'] if facts['io_addr'] is not None else ''),
           facts['source'], facts['cite'])
    width = field['bit_hi'] - field['bit_lo'] + 1
    mech, rule = MX.choose({'arch': SR.RULES[soc]['arch'], 'action': 'field' if value is not None else action, 'access': field['access'],
                            'width': width, 'space': facts['space'], 'io_addr': facts['io_addr']})
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
    tpl = m['templates']['field' if value is not None else action]
    fill = {'reg': creg, 'bit': field['bit_lo'], 'mask': SR.c_mask(soc, field['bit_lo'])}
    if value is not None:
        fill.update(SR.c_field(soc, field['bit_lo'], width, value))
    b['c_text'] = tpl.format(**fill)
    b['status'] = 'resolved'
    tr.add('c-statement', 'The C for %s.%s' % (reg, field['field']), 'template %r with reg=%s, bit=%d%s' % (
        tpl, creg, field['bit_lo'], ', value=%s' % value if value is not None else ''), 'fill the template', b['c_text'],
        'hal.custom.mechanisms (%s)' % mech, SR.RULES[soc]['c']['mask'].format(bit='n') + ' is this SoC\'s bit mask form')
    return b


def _isr_safe(b):
    return MX.by_name(b['mechanism'].split(' / ')[-1])['isr_safe']


def unit(soc, operation, pin, board=''):
    board_pin = pin if board else ''
    tr = _Trace('')
    out = {'unit': None, 'bindings': [], 'steps': tr.rows}
    op = OPS.by_name(operation)
    if soc not in SR.RULES:
        out['unit'] = {'key': key(soc, operation, pin), 'status': 'refused', 'why': 'unknown soc %r (known: %s)' % (soc, ', '.join(SR.SOCS))}
        return out
    pin_note = ('', '')
    if board:
        if BOARDS.get(board) != soc:
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
    pp = SR.pin_parts(soc, pin)
    src, cite = SR.pin_source(soc)
    if pp is None:
        tr.add('soc-pin', 'The chip pin', pin, 'lookup', '%s has no pin %r' % (soc, pin), src, cite)
        return stop('refused', '%s has no pin %r' % (soc, pin))
    tr.add('soc-pin', 'The chip pin', pin, 'lookup', (('port %s, bit %d' % (pp['port'], pp['bit'])) if pp['port'] else 'pad %d' % pp['n'])
           + ('; functions %s' % ', '.join(SR.pin_functions(soc, pin)) if SR.pin_functions(soc, pin) else '')
           + ('; caveat: %s' % SR.pin_caveat(soc, pin) if SR.pin_caveat(soc, pin) else ''), src, cite)
    rules = SR.RULES[soc]
    vars_ = {'port': pp['port'], 'n': pp['n']}
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
    for i, p in enumerate(parts, 1):
        role = rules['roles'].get(p['role'])
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
        if width > 1:
            vkey = p.get('value') or p['action']
            value = (role.get('values') or {}).get(vkey)
            if value is None:
                return stop('refused', 'a %d-bit field %s.%s needs a value for %r (role rule values)' % (width, f['register'], f['field'], vkey))
        b = _binding(soc, tr, uk, operation, pin, len(bindings) + 1, role.get('purpose') or op['intent'], f, p['action'], value=value)
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
    if symbols:
        text = '#define %s %s' % (name, symbols[0])
    elif op['returns'] != 'void':
        text = '#define %s() %s' % (name, stmts[0])
    else:
        text = '#define %s() do { %s } while (0)' % (name, ' '.join(stmts))
    if unsafe:
        u['c_text_init'] = '#define %s_INIT() do { %s } while (0)' % (name, ' '.join(plain))
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
    return sorted(pins, key=lambda p: (p[:2] if soc == 'atmega328p' else '', int(''.join(ch for ch in p if ch.isdigit()) or 0)))
