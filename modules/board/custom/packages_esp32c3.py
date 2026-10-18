"""
@module board.custom.packages_esp32c3

c3pf: THE ESP32-C3's QFN32 PACKAGE as rows (the chip on the DevKitM-1's ESP32-C3-MINI-1 module) - what the availability ladder's rung 2 ("package exposure")
reads, and what the E1 exposure map derives from. READ from the datasheet v2.4 (the file board_c3 already cites; sha256 in esp32c3_evidence): Figure 2-1 "Pin Layout
(Top View) for ESP32-C3, ESP32-C3FH4, ESP32-C3FN4 and ESP32-C3FH8X", p.14 (the leg numbers; "33 GND" is the centre pad) and Table 2-1 "Pin Overview", pp.16-17 (the
pin type of each leg: IO / Analog / Power). Leg 18, VDD_SPI, is a power pin that is also GPIO11 (Table 2-1 note 8, p.17) - modelled as the GPIO11 leg with that said.

NOT modelled (named, not guessed): the ESP32-C3FH4X / FH4AZ variant (Figure 2-2, p.15) whose legs 19-24 are "not bonded"/NC and which has 16 GPIOs - which chip sits
under his module is undetermined (MINI-1 datasheet Table 1-1, p.3, lists N4 = chip revision v0.4 and N4X = v1.1 side by side); the ESP32-C3-MINI-1 module's own 53
pads are not rows (only which chip pins it brings out, in the lifecycle and BoardPin notes).
"""
import json

from board.custom import esp32c3_evidence as EV
from board.custom import esp32c3_tables as T

SOC = EV.SOC
QFN = 'esp32c3-32-qfn'
DS = 'espressif-esp32-c3-datasheet'
FIG = 'Figure 2-1 Pin Layout (Top View), p.14; Table 2-1 Pin Overview, pp.16-17'
#: leg -> (label, kind). I/O legs take the GPIO label (the SocPin); their datasheet pin NAME is in `notes`.
_NAME = {1: 'LNA_IN', 2: 'VDD3P3', 3: 'VDD3P3', 7: 'CHIP_EN', 11: 'VDD3P3_RTC', 17: 'VDD3P3_CPU', 29: 'XTAL_N', 30: 'XTAL_P', 31: 'VDDA', 32: 'VDDA', 33: 'GND'}
_KIND = {1: 'analog-input', 2: 'power', 3: 'power', 7: 'analog-input', 11: 'power', 17: 'power', 29: 'clock-input', 30: 'clock-input', 31: 'analog-supply', 32: 'analog-supply', 33: 'ground'}
_WORDS = {1: 'RF low-noise-amplifier input (type Analog)', 2: 'analog power supply (Table 2-1: Power)', 3: 'analog power supply (Table 2-1: Power)', 7: 'chip enable (type Analog)',
          11: 'RTC-domain I/O supply', 17: 'CPU-domain I/O supply', 29: '40 MHz crystal pad (type Analog)', 30: '40 MHz crystal pad (type Analog)', 31: 'analog supply', 32: 'analog supply',
          33: 'the centre pad, drawn as "33 GND" in Figure 2-1'}


def _label_of(pin_rows):
    return {int(r['package_pin']): r['pin'] for r in pin_rows}


def contacts(soc_pin_rows):
    by_leg = _label_of([r for r in soc_pin_rows if r['soc'] == SOC])
    out = []
    for n in range(1, 34):
        io = n in by_leg
        label = by_leg[n] if io else _NAME[n]
        pin_name = T.PRIORITY[int(label[4:])][1] if io else ''
        out.append({'name': '%s:%d' % (QFN, n), 'package': QFN, 'number': n, 'label': label, 'kind': 'io' if io else _KIND[n],
                    'soc_pin': '%s:%s' % (SOC, label) if io else '', 'functions_json': json.dumps([pin_name] if io else [label]), 'electrical_class': '',
                    'page_table': FIG,
                    'undetermined': 'no ElectricalCharacteristic rows for the ESP32-C3 pads are read (Table 5-4 DC characteristics not read)' if io else '',
                    'notes': ('datasheet pin name %s%s' % (pin_name, '; a power pin by default that is also GPIO11 (Table 2-1 note 8, p.17)' if n == 18 else '')
                              + ('; the in-package flash pad (Table 2-12 p.29); legs 19-24 are NC on the ESP32-C3FH4X / FH4AZ (p.17 note 9)' if 19 <= n <= 24 else '')) if io else _WORDS[n]})
    return out


def package_definition(c_rows):
    return {'name': QFN, 'soc': SOC, 'title': 'ESP32-C3 QFN32 (5x5 mm) - the chip inside the ESP32-C3-MINI-1 module of the DevKitM-1', 'package_type': 'QFN', 'pin_count': 32, 'code': 'QFN32 (5*5)',
            'footprint': '', 'adc_channels': 6, 'document': EV.DS_DOC, 'datasheet': DS, 'page_table': FIG + '; Table 1-1 ESP32-C3 Series Comparison p.12 (QFN32 (5*5))', 'url': EV.DS_URL,
            'contacts_refs_json': json.dumps(['PackageContact:%s' % c['name'] for c in c_rows]),
            'used_by_json': json.dumps([{'board': EV.BOARD, 'component': 'U1', 'how': 'the chip of the ESP32-C3-MINI-1 module on the DevKitM-1 (Zephyr esp32c3_devkitm includes esp32c3_mini_n4.dtsi)'}]),
            'undetermined': 'the KiCad footprint is not in the cited sources; the ESP32-C3FH4X / FH4AZ variant (16 GPIOs, legs 19-24 not bonded; Figure 2-2 p.15) is not modelled - which chip is under his module is undetermined',
            'notes': 'ADC channels: ADC1 5 + ADC2 1 (datasheet §4.2.2.1 p.49; Table 2-6 p.21)'}


def component():
    """U1, the MCU of the reference board (BoardComponent row)."""
    return {'name': '%s:U1' % EV.BOARD, 'board': EV.BOARD, 'ref': 'U1', 'value': 'ESP32-C3 in ESP32-C3-MINI-1 (N4)', 'role': 'mcu', 'soc': SOC, 'package': QFN,
            'package_options_json': json.dumps([QFN]), 'programmable': True, 'targeted_by_firmware': True, 'usb_interface': '', 'fact': '%s:pin.GPIO0' % SOC,
            'origin': 'derived:board_c3.soc_definition().package (Zephyr SOC_ESP32C3_MINI_N4) + the DevKitM-1 user guide ("with the ESP32-C3-MINI-1 module")',
            'undetermined': 'which MINI-1 variant (N4 = chip rev v0.4, N4X = v1.1) and so which chip is on his board is not known; the module\'s internal wiring is the vendor\'s',
            'notes': 'the module is one part (U1) here; its own designators are not modelled'}


def link_soc_pins(soc_pin_rows, c_rows):
    by_pin = {}
    for c in c_rows:
        if c['soc_pin']:
            by_pin.setdefault(c['soc_pin'], []).append('PackageContact:%s' % c['name'])
    for sp in soc_pin_rows:
        if sp.get('soc') == SOC:
            sp['package_contacts_refs_json'] = json.dumps(sorted(by_pin.get(sp['name'], [])))
    return soc_pin_rows
