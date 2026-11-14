"""
@module board.custom.sim_layout

pt-1a (AI-Notes/plans/PIN_TWIN_PLAN.md §2a, "the interface between the layers"): one SimulatedChip's rows -> ONE DEVICE LAYOUT (JSON), the
document the generic `polari-block` QEMU device loads at start (`-device polari-block,layout=FILE`). A new chip, or a changed register, is a new
layout, never a QEMU rebuild.

What it reads, and never re-types:
  * layer 1, the chip: the seeded Register / RegisterField rows (address, reset, bits, the access word, acts_on), selected BY ADDRESS inside each
    overlay span, so any source of those rows (a manual's hand rows, an SVD, our own SystemRDL) gives a layout;
  * layer 2, the behaviour: the BlockBehaviour row's roles, each resolved through hal.custom.soc_rules RULES[soc]['roles'] (the binding the
    firmware generator reads) to a cited RegisterField per pin;
  * layer 3, the binding: the SimOverlay rows (span, mode, device, params).

Refusals are words, never a half-written layout (LayoutRefused): a role the behaviour needs that the chip's rules lack (or mark `missing`), a role
whose register or field is not a row inside the device's spans, a w1-set / w1-clear field with no acts_on, an access word the device does not
interpret, a reset that is neither hex nor composable from its fields, a register the fields contradict.

Passthrough needs no device code: an overlay maps ONLY the registers it models (as contiguous runs), at a higher priority than the vendor model,
so every other offset of the span - the C3's GPIO_STRAP - falls through to the vendor model unchanged. The layout lists both.

  layout(chip_name, registers=None, fields=None, rules=None) -> dict (with 'sha256' of the canonical text)
  text(layout) -> the canonical JSON text (sorted keys, no whitespace variance): same rows -> same sha
"""
import hashlib
import json
import re

from board.custom import sim_bindings as SB

SCHEMA = 'polari-block-layout/1'
#: the access words the polari-block device interprets (HAL plan §4d's vocabulary, board.custom.register_access); fifo is the UART's, not a pin word
DEVICE_WORDS = ('rw', 'r', 'w1-set', 'w1-clear', 'w-strobe', 'r-w1c', 'rw-sc', 'w1c', 'w0c')
ALIASES = ('w1-set', 'w1-clear')


class LayoutRefused(Exception):
    pass


def _int(s):
    s = str(s).strip()
    return int(s, 16) if s.lower().startswith('0x') else int(s) if re.fullmatch(r'\d+', s) else None


def _seed_rows():
    from board import board_seed as S
    return S.SEED_BOARD_OBJECT['Register'], S.SEED_BOARD_OBJECT['RegisterField']


def _rules(soc):
    from hal.custom import soc_rules as SR
    return SR.RULES.get(soc, {}).get('roles', {})


def _register(reg, fields):
    out = []
    for f in sorted(fields, key=lambda f: f['bit_lo']):
        if f['access'] not in DEVICE_WORDS:
            raise LayoutRefused('%s: access word %r is not one the polari-block device interprets (%s)' % (f['name'], f['access'], ', '.join(DEVICE_WORDS)))
        if f['access'] in ALIASES and not f.get('acts_on'):
            raise LayoutRefused('%s is %s but its row names no acts_on register: the device would not know what it sets / clears' % (f['name'], f['access']))
        r = _int(f['reset_value'])
        if r is None:
            raise LayoutRefused('%s: reset %r is not a number' % (f['name'], f['reset_value']))
        out.append({'name': f['field'], 'lo': f['bit_lo'], 'width': f['width'], 'access': f['access'], 'reset': r,
                    'acts_on': f.get('acts_on', '').split(':', 1)[-1], 'pin': f.get('affects_pin', '').split(':', 1)[-1]})
    composed = sum(f['reset'] << f['lo'] for f in out)
    mask = sum(((1 << f['width']) - 1) << f['lo'] for f in out)
    printed = _int(reg['reset_value'].split()[0]) if reg['reset_value'].strip() else None
    if printed is None:
        reset, how = composed, 'composed from its fields (the register\'s printed reset is words: %s)' % reg['reset_value'][:80]
    else:
        if printed & mask != composed:
            raise LayoutRefused('%s: printed reset 0x%X disagrees with its fields\' resets (0x%X on mask 0x%X)' % (reg['name'], printed, composed, mask))
        reset, how = printed, 'printed'
    return {'name': reg['register'], 'addr': _int(reg['addr']), 'reset': reset, 'reset_from': how, 'fields': out}


def _runs(offsets, size):
    """sorted 4-byte register offsets -> mapped runs [[off, len]] and the passthrough complement inside [0, size)"""
    runs = []
    for o in offsets:
        if runs and runs[-1][0] + runs[-1][1] == o:
            runs[-1][1] += 4
        else:
            runs.append([o, 4])
    gaps, at = [], 0
    for o, n in runs:
        if o > at:
            gaps.append([at, o - at])
        at = o + n
    if at < size:
        gaps.append([at, size - at])
    return runs, gaps


def _resolve(role, binding, pins, by_name, soc):
    if binding is None:
        raise LayoutRefused('role %r: not in hal soc_rules RULES[%r][\'roles\'] (add it there, so the firmware generator gains it too)' % (role, soc))
    if binding.get('missing'):
        raise LayoutRefused('role %r on %s is marked missing in the HAL rules: %s' % (role, soc, binding['missing']))
    per_pin = []
    for n in range(pins):
        for tmpl in binding['registers']:
            name = tmpl.replace('{n}', str(n))
            reg = by_name.get(name)
            if reg is None:
                raise LayoutRefused('role %r, pin %d: register %s is not a row inside this device\'s spans' % (role, n, name))
            if binding.get('field'):
                fld = next((f for f in reg['fields'] if f['name'] == binding['field']), None)
            else:
                fld = next((f for f in reg['fields'] if f['pin'] == 'GPIO%d' % n), None)
            if fld is None:
                raise LayoutRefused('role %r, pin %d: %s has no field %s' % (role, n, name, binding.get('field') or ('for GPIO%d' % n)))
            per_pin.append({'pin': n, 'register': name, 'field': fld['name']})
    return {'values': binding.get('values', {}), 'cite': binding.get('cite', ''), 'per_pin': per_pin}


def layout(chip_name, registers=None, fields=None, rules=None):
    chip = SB.chip(chip_name)
    if chip is None:
        raise LayoutRefused('no SimulatedChip row %r' % chip_name)
    soc = chip['soc']
    if registers is None or fields is None:
        registers, fields = _seed_rows()
    rules = _rules(soc) if rules is None else rules
    fields_of = {}
    for f in fields:
        if f.get('soc') == soc:
            fields_of.setdefault(f['register'], []).append(f)
    regs = [r for r in registers if r.get('soc') == soc and _int(r.get('addr', '')) is not None]

    devices, vendor = {}, []
    for ov in sorted(SB.overlays(chip_name), key=lambda o: _int(o['base'])):
        base, size = _int(ov['base']), _int(ov['size'])
        if ov['mode'] == 'vendor':
            vendor.append({'name': ov['name'], 'peripheral': ov['peripheral'], 'base': base, 'size': size, 'why': ov['why']})
            continue
        params = json.loads(ov['params_json'] or '{}')
        keep = set(params.get('leave_to_vendor', []))
        inside = sorted((r for r in regs if base <= _int(r['addr']) < base + size and r['register'] not in keep), key=lambda r: _int(r['addr']))
        if not inside:
            raise LayoutRefused('%s: no Register rows inside 0x%X + 0x%X' % (ov['name'], base, size))
        modelled = [_register(r, fields_of.get(r['name'], [])) for r in inside]
        runs, gaps = _runs([m['addr'] - base for m in modelled], size)
        dev = devices.setdefault(ov['device'], {'name': ov['device'], 'behaviour': ov['behaviour'], 'mode': ov['mode'], 'params': {}, 'spans': []})
        if dev['behaviour'] != ov['behaviour']:
            raise LayoutRefused('device %r mixes behaviours %s and %s' % (ov['device'], dev['behaviour'], ov['behaviour']))
        dev['params'].update({k: v for k, v in params.items() if k != 'leave_to_vendor'})
        dev['spans'].append({'name': ov['name'], 'peripheral': ov['peripheral'], 'base': base, 'size': size, 'map': runs, 'passthrough': gaps,
                             'left_to_vendor': sorted(keep), 'registers': modelled, 'why': ov['why']})

    for dev in devices.values():
        beh = SB.behaviour(dev['behaviour'])
        if beh is None:
            raise LayoutRefused('device %r: no BlockBehaviour row %r' % (dev['name'], dev['behaviour']))
        need = json.loads(beh['roles_json'])
        by_name = {r['name']: r for s in dev['spans'] for r in s['registers']}
        for s in dev['spans']:   # every acts_on target is modelled by the same device
            for r in s['registers']:
                for f in r['fields']:
                    if f['acts_on'] and f['acts_on'] not in by_name:
                        raise LayoutRefused('%s.%s acts on %s, which this device does not model' % (r['name'], f['name'], f['acts_on']))
        pins = int(dev['params'].get('pins', 0))
        dev['roles'] = {role: _resolve(role, rules.get(role), pins, by_name, soc) for role in need['modelled']}
        dev['values'] = {}
        for role in need['values']:
            b = rules.get(role)
            if b is None or b.get('missing') or not b.get('values'):
                raise LayoutRefused('value role %r on %s: %s' % (role, soc, (b or {}).get('missing') or 'not in hal soc_rules RULES with its value'))
            dev['values'][role] = {'values': b['values'], 'cite': b.get('cite', '')}

    out = {'schema': SCHEMA, 'chip': {k: chip[k] for k in ('name', 'soc', 'simulator', 'machine')},
           'devices': [devices[k] for k in sorted(devices)], 'vendor': vendor}
    out['sha256'] = hashlib.sha256(text(out).encode()).hexdigest()
    return out


def text(lay):
    """canonical: sorted keys, compact separators, without the sha line itself"""
    return json.dumps({k: v for k, v in lay.items() if k != 'sha256'}, sort_keys=True, separators=(',', ':'), ensure_ascii=True)
