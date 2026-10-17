"""
@module board.custom.exposure_names

hsp-0: the one place an EnclosureContact dict is made and named (so the E1, E2 and typed rows all carry the same fields and the same name rule).
Name = '<enclosure>:<inner>=<outer>' with each ref stripped of its class prefix; an empty outer (not-bonded / internal-only) is spelled by its via and part.
"""
import json

VIA = ('direct', 'series-resistor', 'buffer', 'capacitor', 'jumper', 'series-inductor', 'series-fuse', 'not-bonded', 'internal-only')
VERIFICATION = ('verified', 'partial', 'unverified', 'conflicted')


def ref_name(ref):
    """'PackageContact:atmega328p-28-spdip:12' -> 'atmega328p-28-spdip:12' (the class prefix is what the page links by, not part of the key)."""
    return ref.partition(':')[2] if ref else ''


def row(enclosure, level, inner, outer, via, *, via_part='', via_value='', exposed=False, consumed_by='', label='', verification='unverified',
        document='', datasheet='', page_table='', url='', fact='', undetermined='', notes=''):
    assert via in VIA and verification in VERIFICATION, (via, verification)
    tail = ref_name(outer) or '%s%s' % (via, ('-' + via_part.split()[0]) if via_part else '')
    return {'name': '%s:%s=%s' % (enclosure, ref_name(inner) or 'undetermined', tail), 'enclosure': enclosure, 'level': level, 'inner_ref': inner,
            'outer_ref': outer, 'via': via, 'via_part': via_part, 'via_value': via_value, 'exposed': bool(exposed), 'consumed_by': consumed_by, 'label': label,
            'verification': verification, 'document': document, 'datasheet': datasheet, 'page_table': page_table, 'url': url, 'fact': fact,
            'undetermined': undetermined, 'notes': notes}


def unique(rows):
    """Names are keys: a clash (two parallel branches of one pair) gets the via part appended — never silently dropped."""
    seen, out = {}, []
    for r in rows:
        n = r['name']
        if n in seen:
            r = dict(r, name='%s#%d' % (n, seen[n] + 1))
            seen[n] += 1
        else:
            seen[n] = 1
        out.append(r)
    return out


def dumps(x):
    return json.dumps(x)
