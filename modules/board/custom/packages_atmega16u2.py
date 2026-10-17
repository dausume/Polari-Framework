"""
@module board.custom.packages_atmega16u2

hsp-0 (L5): THE ATmega16U2's QFN32 PACKAGE as rows — what the UNO R3's U2 is (the schematic's "ATMEGA16U2-MU(R)": "-MU" = package 32M1-A, 32-pad
5 x 5 x 1 mm QFN at 0.50 mm pitch, doc7799 Ordering Information p.295; uno_evidence fact 'schematic.usb_bridge_part'). READ 2026-10-17 from the
RENDERED Figure 1-1 "Pinout" (QFN32 drawing), p.2 of the cached doc7799 (sha256 = uno_evidence.U2_SHA):

  1 XTAL1 · 2 (PC0) XTAL2 · 3 GND · 4 VCC · 5 (PCINT11/AIN2) PC2 · 6 (OC.0B/INT0) PD0 · 7 (AIN0/INT1) PD1 · 8 (RXD1/AIN1/INT2) PD2 ·
  9 (TXD1/INT3) PD3 · 10 (INT5/AIN3) PD4 · 11 (XCK/AIN4/PCINT12) PD5 · 12 (RTS/AIN5/INT6) PD6 · 13 (CTS/HWB/AIN6/T0/INT7) PD7 · 14 (SS/PCINT0) PB0 ·
  15 (SCLK/PCINT1) PB1 · 16 (PDI/MOSI/PCINT2) PB2 · 17 PB3 (PDO/MISO/PCINT3) · 18 PB4 (T1/PCINT4) · 19 PB5 (PCINT5) · 20 PB6 (PCINT6) ·
  21 PB7 (PCINT7/OC.0A/OC.1C) · 22 PC7 (INT4/ICP1/CLKO) · 23 PC6 (OC.1A/PCINT8) · 24 Reset (PC1/dW) · 25 PC5 (PCINT9/OC.1B) · 26 PC4 (PCINT10) ·
  27 UCAP · 28 UGND · 29 D+ · 30 D- · 31 UVCC · 32 AVCC
and the figure's own note: "The large center pad underneath the QFN package should be soldered to ground on the board to ensure good mechanical
stability." — the centre pad is modelled as contact 33 (the UNO schematic itself numbers it "33 PAD"). Whether the datasheet ties the pad to the die's
ground electrically is NOT stated (undetermined). Pin descriptions (§2.2, p.4-5) say what each supply/USB leg is. The kind of every contact
comes from those descriptions; the SocPin of an I/O leg is soc_atmega16u2's row.
"""
import json

from board.custom import uno_evidence as EV
from board.custom import soc_atmega16u2 as S

QFN = 'atmega16u2-32-qfn'
DS = 'atmega16u2-doc7799'
FIG = 'Figure 1-1 Pinout (QFN32), p.2'
DESC = '§2.2 Pin Descriptions, p.4-5'

#: leg number -> label, in the figure's numbering
_LEGS = ['XTAL1', 'PC0', 'GND', 'VCC', 'PC2', 'PD0', 'PD1', 'PD2', 'PD3', 'PD4', 'PD5', 'PD6', 'PD7', 'PB0', 'PB1', 'PB2', 'PB3', 'PB4', 'PB5',
         'PB6', 'PB7', 'PC7', 'PC6', 'PC1', 'PC5', 'PC4', 'UCAP', 'UGND', 'D+', 'D-', 'UVCC', 'AVCC']
_KIND = {'XTAL1': 'clock-input', 'GND': 'ground', 'VCC': 'power', 'UCAP': 'regulator-output', 'UGND': 'usb-ground', 'D+': 'usb-data', 'D-': 'usb-data',
         'UVCC': 'usb-supply', 'AVCC': 'analog-supply'}
_WORDS = {'XTAL1': 'input to the inverting oscillator amplifier / the internal clock circuit (§2.2.13)', 'GND': 'ground (§2.2.2)',
          'VCC': 'digital supply (§2.2.1)', 'AVCC': 'supply for the analog features (analog comparator, PLL); to be connected to VCC through a low-pass filter (§2.2.3)',
          'D-': 'USB full-speed negative data, upstream port (§2.2.7)', 'D+': 'USB full-speed positive data, upstream port (§2.2.8)', 'UGND': 'USB ground (§2.2.9)',
          'UVCC': 'USB pads internal regulator input supply (§2.2.10)',
          'UCAP': 'USB pads internal regulator output; to be connected to an external 1 uF capacitor (§2.2.11)'}
_FIGLABELS = {  # the figure's own labels per leg, in its order (verbatim, "OC.0B" printed with the dot as the figure has it)
    'XTAL1': ['XTAL1'], 'PC0': ['PC0', 'XTAL2'], 'PC2': ['PCINT11', 'AIN2', 'PC2'], 'PD0': ['OC.0B', 'INT0', 'PD0'], 'PD1': ['AIN0', 'INT1', 'PD1'],
    'PD2': ['RXD1', 'AIN1', 'INT2', 'PD2'], 'PD3': ['TXD1', 'INT3', 'PD3'], 'PD4': ['INT5', 'AIN3', 'PD4'], 'PD5': ['XCK', 'AIN4', 'PCINT12', 'PD5'],
    'PD6': ['RTS', 'AIN5', 'INT6', 'PD6'], 'PD7': ['CTS', 'HWB', 'AIN6', 'T0', 'INT7', 'PD7'], 'PB0': ['SS', 'PCINT0', 'PB0'], 'PB1': ['SCLK', 'PCINT1', 'PB1'],
    'PB2': ['PDI', 'MOSI', 'PCINT2', 'PB2'], 'PB3': ['PB3', 'PDO', 'MISO', 'PCINT3'], 'PB4': ['PB4', 'T1', 'PCINT4'], 'PB5': ['PB5', 'PCINT5'], 'PB6': ['PB6', 'PCINT6'],
    'PB7': ['PB7', 'PCINT7', 'OC.0A', 'OC.1C'], 'PC7': ['PC7', 'INT4', 'ICP1', 'CLKO'], 'PC6': ['PC6', 'OC.1A', 'PCINT8'], 'PC1': ['Reset', 'PC1', 'dW'],
    'PC5': ['PC5', 'PCINT9', 'OC.1B'], 'PC4': ['PC4', 'PCINT10']}


def contacts():
    out = []
    for n, lab in enumerate(_LEGS, 1):
        io = lab in S.PINS
        out.append({'name': '%s:%d' % (QFN, n), 'package': QFN, 'number': n, 'label': lab, 'kind': 'io' if io else _KIND[lab],
                    'soc_pin': '%s:%s' % (S.SOC, lab) if io else '', 'functions_json': json.dumps(_FIGLABELS.get(lab, [lab])), 'electrical_class': '',
                    'page_table': '%s%s' % (FIG, '' if io else '; ' + DESC),
                    'undetermined': 'no ElectricalCharacteristic rows for the 16U2 are read (pad numbers not cited)' if io else '',
                    'notes': _WORDS.get(lab, '')})
    out.append({'name': '%s:33' % QFN, 'package': QFN, 'number': 33, 'label': 'PAD', 'kind': 'thermal-pad', 'soc_pin': '', 'functions_json': json.dumps(['PAD']),
                'electrical_class': '', 'page_table': '%s, note under the figure' % FIG,
                'undetermined': 'the datasheet says the centre pad "should be soldered to ground on the board" (mechanical stability); that it is electrically the die ground is not stated',
                'notes': 'not a numbered leg: the UNO schematic draws it as pin "33 PAD"'})
    return out


def package_definition(c_rows=None):
    c_rows = c_rows if c_rows is not None else contacts()
    return {'name': QFN, 'soc': S.SOC, 'title': 'ATmega16U2 32-pad QFN (32M1-A) — U2 on the UNO R3', 'package_type': 'QFN', 'pin_count': 32, 'code': '32M1-A',
            'footprint': '', 'adc_channels': 0, 'document': EV.U2_DOC, 'datasheet': DS, 'page_table': FIG + '; Ordering Information p.295 (ATmega16U2-MU = 32M1-A, 32-pad 5 x 5 x 1 mm QFN, 0.50 mm pitch)',
            'url': EV.U2_URL, 'contacts_refs_json': json.dumps(['PackageContact:%s' % c['name'] for c in c_rows]),
            'used_by_json': json.dumps([{'board': EV.BOARD, 'component': 'U2', 'how': 'ATMEGA16U2-MU(R) on the UNO R3 schematic (sheet 1, "U3" there): the "-MU" ordering code'}]),
            'undetermined': 'the KiCad footprint is not in the cited sources (the datasheet\'s drawing is §31.1 p.297, its numbers were not read); the 16U2 has no ADC (adc_channels 0 = none stated, not measured)',
            'notes': 'the 32-lead TQFP (32A) the same chip is also sold in (Figure 1-1 draws it beside the QFN) is NOT modelled: no board here carries it'}


def link_soc_pins(soc_pin_rows, c_rows):
    """Fill each atmega16u2 SocPin's package-contact refs IN PLACE (derived, never typed twice)."""
    by_pin = {}
    for c in c_rows:
        if c['soc_pin']:
            by_pin.setdefault(c['soc_pin'], []).append('PackageContact:%s' % c['name'])
    for sp in soc_pin_rows:
        if sp.get('soc') == S.SOC:
            sp['package_contacts_refs_json'] = json.dumps(sorted(by_pin.get(sp['name'], [])))
    return soc_pin_rows
