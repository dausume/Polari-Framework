"""
@module board.custom.chipdesc_provider

hal-4 (econ; plan §4d, pol's provider interface hal.custom.soc_rules.PROVIDERS / RULES): a HAL provider built from ANY chip description -
svd_import (+ access_overlay) rows, or rdl_import rows - so a new chip (our own RTL, a LiteX SoC, a vendor part) gets HAL units with zero
generator changes. The generator refuses an unknown soc; registering one is the only way in.

What is generated vs hand-written (the plan's line, kept):
  generated   the REGISTERS / FIELDS rows (structure + access words) from the chip description
  hand-written, cited, in `meta`
              the chip's identity and C facts (arch, reg_width, ctype, mask, field_forms, includes, prelude, guard ...): every one
              required explicitly, none copied from another chip; the PINS (pin -> register, field, bit - a pin is a design fact the
              register file does not carry); the ROLE rules (which register plays which HAL role, with the cite)
A pin's view: an operation on a pin acts on ONE bit, so a pin declared on bit k of a wider field (TOY OUT[7:0]) is presented to the
generator as a one-bit field OUT_k of the same register (affects_pin = the pin, the same access word, the reset bit k), cited as "bit k
of FIELD" - the same split board.custom.registers_esp32c3 records for GPIO_OUT's pads.
Vectors and pin functions: none unless meta gives them, said in words.
The chip's facts source (SR.doc, the header's "Facts from:" line and /api/hal/socs) is RULES[soc]['doc']: meta['doc'] if given, else
meta['source'] (the chip description the rows came from).
Second source (SR.PROVIDERS[soc]['crosscheck'], optional): meta['second_source'] = {'fields': rows, 'source': words} - the SAME chip read
through another description (its RDL beside its SVD). Each binding is checked against the second rows covering the same bits of the
same register: position and access word agree -> pass, either differs -> fail, said which; no covering row -> no-second-source.
With no second_source the chip has no crosscheck fn and gets no rows (never another chip's rule).
"""
from hal.custom import soc_rules as SR

REQUIRED_META = ('title', 'arch', 'reg_width', 'base', 'source', 'cite', 'c')
REQUIRED_C = ('ctype', 'mask', 'field_forms', 'includes', 'access_style')


class ChipdescRefused(Exception):
    pass


def provider_parts(soc, registers, fields, meta):
    """-> (RULES entry, PROVIDERS entry) for one chip description. Raises ChipdescRefused for a missing meta fact, a pin on an unknown
    register / field / bit, or a field with no access word (the generator must never see one silently)."""
    missing = [k for k in REQUIRED_META if k not in meta] + ['c.' + k for k in REQUIRED_C if k not in meta.get('c', {})]
    if missing:
        raise ChipdescRefused('%s: the chip description\'s meta lacks %s (each is a cited, hand-written fact - never copied from another chip)'
                              % (soc, ', '.join(missing)))
    regs = {r['register']: r for r in registers}
    rows = []
    for f in fields:
        word, why = SR.access_word(f)
        rows.append(dict(f, access=word, access_lossy=f.get('access', ''), access_why=why))
    by = {(f['register'], f['field']): f for f in rows}
    pin_bits = {}
    for pin, reg, field, bit in _pin_entries(meta):
        f = by.get((reg, field))
        if f is None:
            raise ChipdescRefused('%s: pin %s names %s.%s, which the chip description does not have' % (soc, pin, reg, field))
        if not 0 <= bit < f['width']:
            raise ChipdescRefused('%s: pin %s names bit %d of %s.%s, which is %d bits wide' % (soc, pin, bit, reg, field, f['width']))
        k = f['bit_lo'] + bit
        if pin_bits.setdefault(pin, k) != k:
            raise ChipdescRefused('%s: pin %s is bit %d of one register and bit %d of another (one pin, one bit position)' % (soc, pin, pin_bits[pin], k))
        rv = f['reset_value']
        rows.append(dict(f, field=pin_view_name(field, bit), bit_lo=k, bit_hi=k, width=1, affects_pin=pin,
                         reset_value=str((int(rv) >> bit) & 1) if str(rv).isdigit() else rv,
                         page_table='%s (bit %d of %s.%s, pin %s per the chip description\'s pin table)' % (f['page_table'], bit, reg, field, pin)))
    pins = {pin: {'port': '', 'bit': k, 'n': (meta.get('pin_numbers') or {}).get(pin, n)} for n, (pin, k) in enumerate(sorted(pin_bits.items()))}

    def register_facts(register):
        r = regs.get(register)
        if r is None:
            return None
        base = r.get('base', meta['base'])   # a register row may carry its own block's base (several blocks); else the chip's one base
        addr = base + r['offset']
        return {'address': '0x%08X' % addr, 'space': 'mem', 'io_addr': None, 'source': meta['source'],
                'cite': 'base 0x%08X (%s) + offset 0x%04X; %s' % (base, meta['cite'], r['offset'], r.get('where', ''))}

    ctype = meta['c']['ctype']
    rules = {'arch': meta['arch'], 'title': meta['title'], 'reg_width': meta['reg_width'], 'boards': tuple(meta.get('boards') or ()),
             'roles': dict(meta.get('roles') or {}), 'peripherals': dict(meta.get('peripherals') or {}), 'signal_vars': list(meta.get('signal_vars') or []),
             'facts': dict(meta.get('facts') or {}), 'setups': dict(meta.get('setups') or {}), 'c': dict(meta['c']),
             'doc': meta.get('doc') or meta['source']}
    prov = {'fields': lambda: rows, 'fields_source': 'board.custom.chipdesc_provider(%s): %s' % (soc, meta['source']),
            'register_facts': register_facts, 'pin_parts': lambda pin: pins.get(pin),
            'pin_functions': lambda pin: list((meta.get('pin_functions') or {}).get(pin, [])),
            'pin_source': ('the chip description\'s pin table (%s)' % meta['source'], meta.get('pins_cite', meta['cite'])),
            'pin_caveat': lambda pin: '',
            'vectors': lambda: dict(meta.get('vectors') or {}),
            'vectors_source': meta.get('vectors_source', 'none: the chip description names no interrupt vectors'),
            'c_register': lambda register, facts: '(*(volatile %s *)%su)' % (ctype, facts['address']),
            'datasheet_address': lambda register: ''}
    if meta.get('second_source'):
        prov['crosscheck'] = _crosscheck_fn(soc, meta['second_source'], meta['source'])
    return rules, prov


def _crosscheck_fn(soc, second, first_source):
    """-> crosscheck(unit, binding) comparing the binding's field against the second description's row over the same bits"""
    if not second.get('source') or second.get('fields') is None:
        raise ChipdescRefused('%s: second_source needs fields and a source (words naming the second description)' % soc)
    rows = [dict(f, access=SR.access_word(f)[0]) for f in second['fields']]

    def crosscheck(u, b):
        subject = '%s.%s position and access' % (b['register'], b['field'])
        first = 'bits %d-%d %s' % (b['bit_hi'], b['bit_lo'], b['access'])
        cover = [f for f in rows if f['register'] == b['register'] and f['bit_lo'] <= b['bit_lo'] and b['bit_hi'] <= f['bit_hi']]
        row = {'unit': u['key'], 'subject': subject, 'first': first, 'first_source': first_source, 'second_source': second['source']}
        if not cover:
            return dict(row, second='', result='no-second-source',
                        why='the second description has no field covering bits %d-%d of %s' % (b['bit_hi'], b['bit_lo'], b['register']))
        # the exact (bit_lo, bit_hi) row first, then the narrowest covering one (a wide register-level row never wins over the field)
        f = min(cover, key=lambda r: ((r['bit_lo'], r['bit_hi']) != (b['bit_lo'], b['bit_hi']), r['bit_hi'] - r['bit_lo']))
        diff = []
        if (f['bit_lo'], f['bit_hi']) != (b['bit_lo'], b['bit_hi']) and not (b['bit_lo'] == b['bit_hi'] and pin_view_name(f['field'], b['bit_lo'] - f['bit_lo']) == b['field']):
            diff.append('position: %s.%s is bits %d-%d there' % (f['register'], f['field'], f['bit_hi'], f['bit_lo']))
        if f['access'] != b['access']:
            diff.append('access: %s there, %s here' % (f['access'], b['access']))
        return dict(row, second='%s.%s bits %d-%d %s' % (f['register'], f['field'], f['bit_hi'], f['bit_lo'], f['access']),
                    result='fail' if diff else 'pass', why='; '.join(diff))
    return crosscheck


def pin_view_name(field, bit):
    """the one-bit pin view of bit k of FIELD is FIELD_k (the ONE place this naming lives; the crosscheck reads it back)"""
    return '%s_%d' % (field, bit)


def _pin_entries(meta):
    """meta['pins'][pin] is one (register, field, bit) or a list of them (a pin seen through several registers: the RP2350's GPIOn is bit
    n of GPIO_OUT, its SET / CLR aliases, GPIO_OE and GPIO_IN) -> [(pin, register, field, bit)]"""
    out = []
    for pin, spec in sorted((meta.get('pins') or {}).items()):
        for reg, field, bit in ([spec] if isinstance(spec, tuple) else list(spec)):
            out.append((pin, reg, field, bit))
    return out


def register(soc, registers, fields, meta):
    """install the provider (refused if the soc is already known: a chip is never silently replaced) -> the field rows it serves"""
    if soc in SR.PROVIDERS or soc in SR.RULES or soc in SR.DOCS or soc in SR.SOCS:
        raise ChipdescRefused('soc %r is already registered' % soc)
    rules, prov = provider_parts(soc, registers, fields, meta)
    SR.RULES[soc] = rules
    SR.PROVIDERS[soc] = prov
    SR.provider(soc)   # the generator's own acceptance (required C facts, reg_width)
    return prov['fields']()


def unregister(soc):
    """remove a chip-description provider (tests); the built-in chips cannot be removed this way"""
    if soc in SR.SOCS:
        raise ChipdescRefused('%s is a built-in provider' % soc)
    SR.RULES.pop(soc, None)
    SR.PROVIDERS.pop(soc, None)
