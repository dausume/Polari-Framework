"""
@module board.custom.packages_atmega328p

fgm-2 (his ruling 2026-10-15, FIRMWARE_GENERATION_MODULE_PLAN.md §7.8.1): THE ATmega328P's PACKAGES as rows — the 28-pin SPDIP the UNO R3
model uses and the 32-pin TQFP (the only one of the two that exposes ADC6 and ADC7). READ 2026-10-15 from DS40002061B Figure 1-1
"Pinout ATmega48A/PA/88A/PA/168A/PA/328/P", p.12 (32 TQFP top view and 28 SPDIP, the same file soc_atmega328p.py cites; sha256 b9b9d83c…9320e
matched; the figure was RENDERED and read, the TQFP numbers are not inferred):
  28-SPDIP   1 PC6 · 2 PD0 · 3 PD1 · 4 PD2 · 5 PD3 · 6 PD4 · 7 VCC · 8 GND · 9 PB6 · 10 PB7 · 11 PD5 · 12 PD6 · 13 PD7 · 14 PB0 · 15 PB1 · 16 PB2 ·
             17 PB3 · 18 PB4 · 19 PB5 · 20 AVCC · 21 AREF · 22 GND · 23 PC0 · … · 28 PC5   (every I/O number is soc_atmega328p.PINS, unchanged)
  32-TQFP    1 PD3 · 2 PD4 · 3 GND · 4 VCC · 5 GND · 6 VCC · 7 PB6 · 8 PB7 · 9 PD5 · 10 PD6 · 11 PD7 · 12 PB0 · 13 PB1 · 14 PB2 · 15 PB3 · 16 PB4 ·
             17 PB5 · 18 AVCC · 19 ADC6 · 20 AREF · 21 GND · 22 ADC7 · 23 PC0 · 24 PC1 · 25 PC2 · 26 PC3 · 27 PC4 · 28 PC5 · 29 PC6 · 30 PD0 · 31 PD1 · 32 PD2
Features list p.2: "8-channel 10-bit ADC in TQFP and VQFN package / 6-channel 10-bit ADC in SPDIP Package". The package CODE '28P3' and the
KiCad footprint come from what the repo already states (soc_atmega328p.soc_definition, board_uno.hardware); the TQFP's vendor code and footprint are
not in the cited sources (undetermined). `SocPin.package_pin` stays the SPDIP number — the model the UNO R3 uses.
"""
import json

from board.custom.uno_facts import M328_DOC, M328_URL
from board.custom import soc_atmega328p as A
from board.custom import electrical_atmega328p as E

SPDIP = 'atmega328p-28-spdip'
TQFP = 'atmega328p-32-tqfp'
DS = 'atmega328p-ds40002061b'
FIG = 'Figure 1-1 Pinout (%s), p.12'

#: TQFP-32 numbers, read from the rendered Figure 1-1 (label per number, 1..32)
_TQFP = ['PD3', 'PD4', 'GND', 'VCC', 'GND', 'VCC', 'PB6', 'PB7', 'PD5', 'PD6', 'PD7', 'PB0', 'PB1', 'PB2', 'PB3', 'PB4',
         'PB5', 'AVCC', 'ADC6', 'AREF', 'GND', 'ADC7', 'PC0', 'PC1', 'PC2', 'PC3', 'PC4', 'PC5', 'PC6', 'PD0', 'PD1', 'PD2']
#: the SPDIP's non-I/O legs (soc_atmega328p.POWER_PINS)
_KIND = {'VCC': 'power', 'GND': 'ground', 'AVCC': 'analog-supply', 'AREF': 'analog-reference', 'ADC6': 'analog-input', 'ADC7': 'analog-input'}


def _class_of(label):
    if label in ('ADC6', 'ADC7'):
        return E.cls('adc-only')
    if label in A.PINS:
        return E.cls('reset' if label == 'PC6' else 'io-standard')
    return ''


def _contacts(package, labels, fig):
    out = []
    for n, lab in labels:
        io = lab in A.PINS
        fns = list(A.PINS[lab][1]) if io else []
        out.append({'name': '%s:%d' % (package, n), 'package': package, 'number': n, 'label': lab, 'kind': 'io' if io else _KIND[lab],
                    'soc_pin': '%s:%s' % (A.SOC, lab) if io else '', 'functions_json': json.dumps((['GPIO'] + fns) if io else [lab]),
                    'electrical_class': _class_of(lab), 'page_table': fig,
                    'undetermined': '' if io or lab in _KIND else 'unknown leg',
                    'notes': ('exists ONLY in the 32-pin packages (TQFP/VQFN): analog-only, no digital pad, no pull-up' if lab in ('ADC6', 'ADC7') else
                              'PC6 is RESET unless the RSTDISBL fuse is programmed (Table 14-6, p.94-95)' if lab == 'PC6' else '')})
    return out


def contacts():
    spdip = [(int(n), lab) for n, lab in ((p[0], s) for s, p in A.PINS.items())] + [(int(n), v) for n, v in A.POWER_PINS.items()]
    spdip.sort()
    return _contacts(SPDIP, spdip, FIG % '28 SPDIP') + _contacts(TQFP, list(enumerate(_TQFP, 1)), FIG % '32 TQFP')


def package_definitions(c_rows=None):
    c_rows = c_rows if c_rows is not None else contacts()
    refs = lambda pkg: json.dumps(['PackageContact:%s' % c['name'] for c in c_rows if c['package'] == pkg])   # noqa: E731
    return [
        {'name': SPDIP, 'soc': A.SOC, 'title': 'ATmega328P 28-pin SPDIP (28P3) — what the UNO R3 model carries', 'package_type': 'SPDIP', 'pin_count': 28, 'code': '28P3',
         'footprint': 'Package_DIP:DIP-28_W7.62mm', 'adc_channels': 6, 'document': M328_DOC, 'datasheet': DS, 'page_table': FIG % '28 SPDIP' + '; features list p.2 (6-channel ADC in SPDIP)',
         'url': M328_URL, 'contacts_refs_json': refs(SPDIP),
         'used_by_json': json.dumps([{'board': 'arduino-uno-r3', 'component': 'U1', 'how': 'ATmega328P-PU in DIP-28 (board_uno.hardware); the physical bench board\'s package stays PENDING'}]),
         'undetermined': '', 'notes': 'code 28P3 and the footprint are the repo\'s existing statements (soc_atmega328p.soc_definition.package, board_uno.hardware U1)'},
        {'name': TQFP, 'soc': A.SOC, 'title': 'ATmega328P 32-pin TQFP — adds the analog-only inputs ADC6 and ADC7', 'package_type': 'TQFP', 'pin_count': 32, 'code': '',
         'footprint': '', 'adc_channels': 8, 'document': M328_DOC, 'datasheet': DS, 'page_table': FIG % '32 TQFP' + '; features list p.2 (8-channel ADC in TQFP and VQFN)',
         'url': M328_URL, 'contacts_refs_json': refs(TQFP), 'used_by_json': '[]',
         'undetermined': 'the vendor package code and the KiCad footprint are not in the cited sources; no UNO design in this repo carries this package (it is the SMD-UNO variant, modelled so ADC6/ADC7 are not omitted)',
         'notes': 'the 32-pin VQFN (DS Figure 1-1 also draws 28/32 VQFN) is NOT modelled: add a PackageDefinition + contacts from the same figure when a board needs it'},
    ]


def link_soc_pins(soc_pin_rows, c_rows):
    """Fill each SocPin's `electrical_class` / alternate classes / package-contact refs IN PLACE (derived, never typed twice)."""
    by_pin = {}
    for c in c_rows:
        if c['soc_pin']:
            by_pin.setdefault(c['soc_pin'], []).append('PackageContact:%s' % c['name'])
    for sp in soc_pin_rows:
        if sp.get('soc') != A.SOC:
            continue
        sp['electrical_class'] = E.cls('reset' if sp['pin'] == 'PC6' else 'io-standard')
        sp['electrical_alt_classes_json'] = json.dumps({'XTAL1': E.cls('xtal1')} if sp['pin'] == 'PB6' else {'RESET': E.cls('reset')} if sp['pin'] == 'PC6' else {})
        sp['package_contacts_refs_json'] = json.dumps(sorted(by_pin.get(sp['name'], [])))
    return soc_pin_rows
