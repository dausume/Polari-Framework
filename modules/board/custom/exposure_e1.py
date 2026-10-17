"""
@module board.custom.exposure_e1

hsp-0 (L3): THE E1 EXPOSURE MAPS — one EnclosureContact per PackageContact (the chip's pin / supply -> the package leg), DERIVED from the
PackageContact + SocPin rows; and one `not-bonded` row for every pin the chip has that a package does NOT bring out (a label another package of the
same chip carries but this one lacks, or a SocPin with no contact on this package): the ATmega328P's ADC6 / ADC7 exist only in the 32-pin packages, so the
28-SPDIP gets two not-bonded rows. The DIE side is `undetermined` everywhere (no die-pad map is cited; stage S4, our own SoC).
"""
from board.custom.exposure_names import row, ref_name

INNER_SUPPLY = ('power', 'ground', 'analog-supply', 'analog-reference', 'usb-supply', 'usb-ground', 'regulator-output')
INNER_SIGNAL = ('analog-input', 'clock-input', 'usb-data')
DIE_UND = 'the die pad this leg is bonded from is not cited (no die-pad map: that arrives with our own SoC, stage S4)'


def inner_of(c, soc):
    if c['kind'] == 'io':
        return 'SocPin:%s' % c['soc_pin']
    if c['kind'] in INNER_SUPPLY:
        return 'Supply:%s:%s' % (soc, c['label'])
    if c['kind'] in INNER_SIGNAL:
        return 'SocSignal:%s:%s' % (soc, c['label'])
    return ''


def rows(tables, enclosures):
    """enclosures = the HardwareEnclosure dicts; one E1 enclosure per package."""
    by_pkg = {e['package']: e for e in enclosures if e['level'] == 'E1'}
    pkgs = {p['name']: p for p in tables.get('PackageDefinition', [])}
    contacts = tables.get('PackageContact', [])
    out = []
    for pname, enc in sorted(by_pkg.items(), key=lambda kv: kv[1]['name']):
        pd = pkgs[pname]
        mine = sorted([c for c in contacts if c['package'] == pname], key=lambda c: c['number'])
        cite = dict(document=pd['document'], datasheet=pd['datasheet'], url=pd['url'])
        for c in mine:
            pad = c['kind'] == 'thermal-pad'
            und = [] if not c['undetermined'] or c['kind'] == 'io' else [c['undetermined']]
            out.append(row(enc['name'], 'E1', inner_of(c, pd['soc']), 'PackageContact:%s' % c['name'], 'direct', exposed=True,
                           label='%s -> leg %d (%s)' % (c['label'], c['number'], pd['package_type']), verification='partial' if pad else 'verified',
                           page_table=c['page_table'], **cite, undetermined='; '.join([DIE_UND] + und), notes=c['notes']))
        other_labels = {(c['label'], c['kind']) for q in pkgs.values() if q['soc'] == pd['soc'] and q['name'] != pname
                        for c in contacts if c['package'] == q['name']}
        mine_labels = {c['label'] for c in mine}
        mine_socpins = {c['soc_pin'] for c in mine if c['soc_pin']}
        for lab, kind in sorted(other_labels):
            if lab in mine_labels:
                continue
            q = next(q for q in pkgs.values() if q['soc'] == pd['soc'] and q['name'] != pname
                     and any(c['package'] == q['name'] and c['label'] == lab for c in contacts))
            out.append(row(enc['name'], 'E1', 'SocSignal:%s:%s' % (pd['soc'], lab), '', 'not-bonded', exposed=False, label='%s: not brought out by the %s' % (lab, pd['package_type']),
                           verification='verified', page_table='%s; %s' % (q['page_table'], pd['page_table']), **cite,
                           undetermined=DIE_UND, notes='%s exists only in %s (%s %d-pin): the %d-pin %s has no leg for it' % (lab, q['name'], q['package_type'], q['pin_count'], pd['pin_count'], pd['package_type'])))
        for sp in tables.get('SocPin', []):
            if sp['soc'] == pd['soc'] and sp['name'] not in mine_socpins:
                out.append(row(enc['name'], 'E1', 'SocPin:%s' % sp['name'], '', 'not-bonded', exposed=False, label='%s: no leg on this package' % sp['pin'],
                               verification='verified', page_table=pd['page_table'], **cite, undetermined=DIE_UND, notes='the chip has this pin; %s has no contact for it' % pd['name']))
    return out


__all__ = ['rows', 'inner_of', 'ref_name']
