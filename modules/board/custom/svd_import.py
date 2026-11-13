"""
@module board.custom.svd_import

hal-4 (econ, HAL_CATOM_CATALOGUE_PLAN.md §4): CMSIS-SVD -> the chip-description rows the generated HAL reads - the SAME shape
board.custom.registers_esp32c3 hand-writes (REGISTERS: register / block / offset / reset; FIELDS: bit_hi / bit_lo / width / reset_value
/ values ...), so a vendor SVD, a LiteX SoC's SVD export and our own RTL (SystemRDL -> PeakRDL -> SVD) all arrive one way.

The SVD gives STRUCTURE only. Its access word ('read-write', 'read-only', 'write-only' ...) is coarse - it cannot say write-1-to-clear
vs strobe vs FIFO - so it is kept as `svd_access` and every imported field starts with trm_access '' (= `missing` to the HAL's
choose(), which fails closed). A cited access overlay (board.custom.access_overlay) supplies the codes.

Handled (CMSIS-SVD 1.3): device defaults (size / access / resetValue / resetMask) inherited peripheral -> register -> field;
peripheral derivedFrom (registers copied, base and name its own); register / cluster dim arrays (%s and [%s], dimIndex lists and
ranges); nested clusters (offsets add); fields by bitOffset + bitWidth, lsb + msb, or bitRange "[msb:lsb]"; field-level
enumeratedValues -> values. Not handled, and refused in words rather than guessed: a register derivedFrom, alternateGroup
aliases (kept, flagged), dimArrayIndex enum names.
"""
import re
import xml.etree.ElementTree as ET


class SvdRefused(Exception):
    pass


def _int(text, default=None):
    if text is None:
        return default
    t = text.strip().lower().replace('_', '')
    if t.startswith('#'):
        raise SvdRefused('binary "#" literal %r (do-not-care bits) not supported' % text)
    return int(t, 0)


def _dim_indexes(el):
    dim = _int(el.findtext('dim'))
    if dim is None:
        return None
    idx = el.findtext('dimIndex')
    if idx is None:
        return [str(i) for i in range(dim)]
    idx = idx.strip()
    m = re.fullmatch(r'(\d+)-(\d+)', idx)
    out = [str(i) for i in range(int(m.group(1)), int(m.group(2)) + 1)] if m else [x.strip() for x in idx.split(',')]
    if len(out) != dim:
        raise SvdRefused('dimIndex %r names %d elements, dim says %d' % (idx, len(out), dim))
    return out


def _expand(el, name):
    """-> [(name, extra offset)] for one register / cluster element: one entry, or one per dim index"""
    idx = _dim_indexes(el)
    if idx is None:
        return [(name, 0)]
    inc = _int(el.findtext('dimIncrement'))
    if inc is None:
        raise SvdRefused('%s: dim without dimIncrement' % name)
    if '%s' not in name:
        raise SvdRefused('%s: dim without %%s in the name' % name)
    return [(name.replace('[%s]', i).replace('%s', i), k * inc) for k, i in enumerate(idx)]


def _bits(f, name):
    off, w = f.findtext('bitOffset'), f.findtext('bitWidth')
    if off is not None:
        return _int(off), _int(w, 1)
    lsb, msb = f.findtext('lsb'), f.findtext('msb')
    if lsb is not None:
        return _int(lsb), _int(msb) - _int(lsb) + 1
    br = f.findtext('bitRange')
    if br:
        m = re.fullmatch(r'\[(\d+):(\d+)\]', br.strip())
        if m:
            return int(m.group(2)), int(m.group(1)) - int(m.group(2)) + 1
    raise SvdRefused('field %s: no bitOffset/bitWidth, lsb/msb or bitRange' % name)


def _values(f):
    out = {}
    for ev in f.iter('enumeratedValue'):
        v, nm, desc = ev.findtext('value'), ev.findtext('name') or '', ' '.join((ev.findtext('description') or '').split())
        if v is None:
            continue
        out[str(_int(v))] = (nm + (': ' + desc if desc else '')).strip()
    return out


def load(path):
    """-> {'device', 'width', 'peripherals': {name: {'base', 'derived_from', 'registers': [...]}}, 'notes': [...]}"""
    root = ET.parse(path).getroot()
    dflt = {'size': _int(root.findtext('size'), 32), 'access': root.findtext('access') or 'read-write',
            'reset': _int(root.findtext('resetValue'), 0), 'mask': _int(root.findtext('resetMask'), 0xFFFFFFFF)}
    raw = {p.findtext('name'): p for p in root.iter('peripheral')}
    out, notes = {}, []
    for pname, p in raw.items():
        src = raw.get(p.get('derivedFrom')) if p.get('derivedFrom') else p
        if src is None:
            raise SvdRefused('peripheral %s derivedFrom unknown %s' % (pname, p.get('derivedFrom')))
        pd = dict(dflt, size=_int(src.findtext('size'), dflt['size']), access=src.findtext('access') or dflt['access'],
                  reset=_int(src.findtext('resetValue'), dflt['reset']))
        regs = []

        def walk(parent, base_off, prefix, inh):
            for el in parent:
                tag = el.tag
                if tag not in ('register', 'cluster'):
                    continue
                if el.get('derivedFrom'):
                    raise SvdRefused('%s.%s: a derivedFrom %s is not supported' % (pname, el.findtext('name'), tag))
                name, off = el.findtext('name'), _int(el.findtext('addressOffset'), 0)
                here = dict(inh, size=_int(el.findtext('size'), inh['size']), access=el.findtext('access') or inh['access'],
                            reset=_int(el.findtext('resetValue'), inh['reset']))
                for nm, extra in _expand(el, name):
                    if tag == 'cluster':
                        walk(el, base_off + off + extra, prefix + nm + '_', here)
                        continue
                    fields = []
                    for f in el.iter('field'):
                        fn = f.findtext('name')
                        lo, w = _bits(f, fn)
                        fields.append({'field': fn, 'bit_lo': lo, 'width': w, 'bit_hi': lo + w - 1,
                                       'svd_access': f.findtext('access') or here['access'],
                                       'reset_value': str((here['reset'] >> lo) & ((1 << w) - 1)),
                                       'description': ' '.join((f.findtext('description') or '').split()), 'values': _values(f)})
                    regs.append({'register': prefix + nm, 'offset': base_off + off + extra, 'size': here['size'], 'reset': here['reset'],
                                 'svd_access': here['access'], 'alternate': el.findtext('alternateRegister') or el.findtext('alternateGroup') or '',
                                 'description': ' '.join((el.findtext('description') or '').split()), 'fields': fields})
        walk(src.find('registers') if src.find('registers') is not None else [], 0, '', pd)
        out[pname] = {'base': _int(p.findtext('baseAddress')), 'derived_from': p.get('derivedFrom') or '', 'registers': regs}
        if any(r['alternate'] for r in regs):
            notes.append('%s: alternate registers kept and flagged (two names at one address)' % pname)
    return {'device': root.findtext('name'), 'width': _int(root.findtext('width'), 32), 'peripherals': out, 'notes': notes}


def rows(chip, peripheral, block=None, name_prefix=None):
    """the generator's row shape for one peripheral -> (REGISTERS, FIELDS). trm_access '' on every field: the SVD's access word is coarse
    (kept as svd_access); an access overlay supplies cited codes. Register names follow the TRM convention <PREFIX>_<SVD name>_REG."""
    p = chip['peripherals'][peripheral]
    block = block or peripheral
    pre = (name_prefix if name_prefix is not None else peripheral) + '_'
    R, F = [], []
    for r in p['registers']:
        rn = pre + r['register'] + '_REG'
        R.append({'register': rn, 'block': block, 'offset': r['offset'], 'reset': '0x%08X' % r['reset'], 'svd_access': r['svd_access'],
                  'title': r['description'], 'where': 'SVD %s.%s' % (peripheral, r['register']), 'undetermined': '', 'part': 'svd'})
        for f in r['fields']:
            F.append({'register': rn, 'field': f['field'], 'bit_hi': f['bit_hi'], 'bit_lo': f['bit_lo'], 'width': f['width'],
                      'reset_value': f['reset_value'], 'svd_access': f['svd_access'], 'trm_access': '', 'access': '',
                      'description': f['description'], 'values': f['values'] or {}, 'page_table': 'SVD %s.%s.%s' % (peripheral, r['register'], f['field']),
                      'affects_pin': '', 'affects_signal': '', 'notes': 'imported from the SVD: no cited access code yet (missing to choose())', 'part': 'svd'})
    return R, F


def address(chip, peripheral, offset):
    return chip['peripherals'][peripheral]['base'] + offset
