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
    for pin, (reg, field, bit) in sorted((meta.get('pins') or {}).items()):
        f = by.get((reg, field))
        if f is None:
            raise ChipdescRefused('%s: pin %s names %s.%s, which the chip description does not have' % (soc, pin, reg, field))
        if not 0 <= bit < f['width']:
            raise ChipdescRefused('%s: pin %s names bit %d of %s.%s, which is %d bits wide' % (soc, pin, bit, reg, field, f['width']))
        k = f['bit_lo'] + bit
        rv = f['reset_value']
        rows.append(dict(f, field='%s_%d' % (field, bit), bit_lo=k, bit_hi=k, width=1, affects_pin=pin,
                         reset_value=str((int(rv) >> bit) & 1) if str(rv).isdigit() else rv,
                         page_table='%s (bit %d of %s.%s, pin %s per the chip description\'s pin table)' % (f['page_table'], bit, reg, field, pin)))
    pins = {pin: {'port': '', 'bit': f_bit_lo(by, reg, field) + bit, 'n': n}
            for n, (pin, (reg, field, bit)) in enumerate(sorted((meta.get('pins') or {}).items()))}

    def register_facts(register):
        r = regs.get(register)
        if r is None:
            return None
        addr = meta['base'] + r['offset']
        return {'address': '0x%08X' % addr, 'space': 'mem', 'io_addr': None, 'source': meta['source'],
                'cite': 'base 0x%08X (%s) + offset 0x%04X; %s' % (meta['base'], meta['cite'], r['offset'], r.get('where', ''))}

    ctype = meta['c']['ctype']
    rules = {'arch': meta['arch'], 'title': meta['title'], 'reg_width': meta['reg_width'], 'boards': tuple(meta.get('boards') or ()),
             'roles': dict(meta.get('roles') or {}), 'peripherals': dict(meta.get('peripherals') or {}), 'signal_vars': list(meta.get('signal_vars') or []),
             'facts': dict(meta.get('facts') or {}), 'setups': dict(meta.get('setups') or {}), 'c': dict(meta['c'])}
    prov = {'fields': lambda: rows, 'fields_source': 'board.custom.chipdesc_provider(%s): %s' % (soc, meta['source']),
            'register_facts': register_facts, 'pin_parts': lambda pin: pins.get(pin),
            'pin_functions': lambda pin: list((meta.get('pin_functions') or {}).get(pin, [])),
            'pin_source': ('the chip description\'s pin table (%s)' % meta['source'], meta.get('pins_cite', meta['cite'])),
            'pin_caveat': lambda pin: '',
            'vectors': lambda: dict(meta.get('vectors') or {}),
            'vectors_source': meta.get('vectors_source', 'none: the chip description names no interrupt vectors'),
            'c_register': lambda register, facts: '(*(volatile %s *)%su)' % (ctype, facts['address']),
            'datasheet_address': lambda register: ''}
    return rules, prov


def f_bit_lo(by, reg, field):
    return by[(reg, field)]['bit_lo']


def register(soc, registers, fields, meta):
    """install the provider (refused if the soc is already known: a chip is never silently replaced) -> the field rows it serves"""
    if soc in SR.PROVIDERS or soc in SR.RULES or soc in SR.DOCS:
        raise ChipdescRefused('soc %r is already registered' % soc)
    rules, prov = provider_parts(soc, registers, fields, meta)
    SR.RULES[soc] = rules
    SR.PROVIDERS[soc] = prov
    # STOPGAP (reported to pol 2026-11-13): render.header and hal_api still read the module-level SR.DOCS[soc], outside the provider
    # interface - without this a registered chip crashes there (KeyError) instead of rendering. Remove once DOCS moves into RULES / PROVIDERS.
    SR.DOCS[soc] = meta['cite']
    SR.provider(soc)   # the generator's own acceptance (required C facts, reg_width)
    return prov['fields']()


def unregister(soc):
    """remove a chip-description provider (tests); the built-in chips cannot be removed this way"""
    if soc in ('atmega328p', 'esp32c3'):
        raise ChipdescRefused('%s is a built-in provider' % soc)
    SR.RULES.pop(soc, None)
    SR.PROVIDERS.pop(soc, None)
    SR.DOCS.pop(soc, None)
