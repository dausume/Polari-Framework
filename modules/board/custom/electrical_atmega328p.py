"""
@module board.custom.electrical_atmega328p

fgm-2 (FIRMWARE_GENERATION_MODULE_PLAN.md §7.7 slice 1', REVIEW_R2 Part 4's "minimum electrical data set"): THE ATmega328P's
ELECTRICAL NUMBERS as rows — `ElectricalCharacteristic` per PAD CLASS x condition (never per pin) and `PinGroupBudget` per GROUP
of pins. READ 2026-10-15 from the datasheet the repo already cites (DS40002061B, file sha256 b9b9d83c…9320e re-fetched and
matched; page numbers are the document's own = the PDF page index, as soc_atmega328p.py already cites them):

  p.308  §29.1 Absolute Maximum Ratings (TA -40..85 C): DC current per I/O pin 40.0 mA; VCC and GND pins 200.0 mA; voltage on any
         pin except RESET -0.5 V .. VCC+0.5 V; on RESET -0.5 V .. 13.0 V; maximum operating voltage 6.0 V
  p.322  §30.1 (the same ratings, TA -40..105 C) and Table 30-1 "Common DC characteristics" — VIL/VIH (by VCC range, by pin kind),
         VOL (IOL = 20 mA at 5 V: 0.9 V max at TA=85 C, 1.0 V at 105 C; IOL = 10 mA at 3 V: 0.6 / 0.7 V)
  p.323  Table 30-1 continued: VOH (IOH = -20 mA at 5 V: 4.2 V min at 85 C, 4.1 V at 105 C; IOH = -10 mA at 3 V: 2.3 / 2.1 V), IIL/IIH
         1 uA max, RRST 30..60 kOhm, RPU 20..50 kOhm; notes 1-4 (the "max/min" meaning, and the group sums below)
  p.319  Table 29-15 ADC characteristics (VIN GND..VREF, RAIN 100 MOhm typ, AVCC VCC +/- 0.3 V)
THE FINDING THAT SHAPES THE ROWS: §29 (the 85 C chapter) carries no common DC table of its own in DS40002061B — the pad numbers live in
Table 30-1 (TA = -40..105 C) with separate TA=85 C / 105 C columns for VOL/VOH. The UNO's own thermal limit is 85 C (the board's product
datasheet A000066, §2.1), so the 85 C rows are the ones a UNO design reads; the 105 C rows are modelled too. Nothing here is typed from
memory: a number the document does not give (a RECOMMENDED continuous per-pin current, a recommended VCC/GND total) is a row naming
what is missing.

PER-PIN CURRENT, three rows (REVIEW_R2: "recommended 20 mA, abs-max 40 mA — abs-max NOT a design target"): 40 mA abs-max (p.308/322, verified);
20 mA at 5 V as the datasheet's GUARANTEED test condition (Table 30-1 note 3/4, p.323, verified); and 20 mA as RECOMMENDED — the Arduino
pinout's own "MAXIMUM current per I/O pin is 20 mA" (board_uno fact pinout.max_current_io) agreeing with the test condition: `partial`,
because no sentence of the chip datasheet calls 20 mA "recommended".
"""
import json

from board.custom.uno_facts import M328_DOC, M328_URL
from board.custom import board_uno as U

SOC = 'atmega328p'
DS = 'atmega328p-ds40002061b'
P_ABS = '§29.1 Absolute Maximum Ratings, p.308 (same ratings §30.1, p.322)'
P_T301 = 'Table 30-1 Common DC characteristics, p.322'
P_T301B = 'Table 30-1 Common DC characteristics (continued), p.323'

#: pad class -> (plain words, [SocPin names it applies to as their default], citation)
PAD_CLASSES = {
    'io-standard': 'a standard I/O pad: every PB, PC (except RESET) and PD pin used as digital I/O — one driver class, symmetrical drive (DS p.84, p.13 port descriptions)',
    'reset': 'the RESET pad (PC6): its own input thresholds; as an I/O pin (RSTDISBL fuse programmed) the "RESET pin as I/O" thresholds apply',
    'xtal1': 'the XTAL1 oscillator input (PB6 when it is the clock input)',
    'adc-only': 'the analog-only inputs ADC6 / ADC7 that exist only in the 32-pin packages (no digital pad, no pull-up)',
}


def cls(name):
    return '%s:%s' % (SOC, name)


def _row(pad, param, cond_slug, condition, *, vcc=(0.0, 0.0), temp='', formula='', lo='', typ='', hi='', unit='', limit='guaranteed',
         verification='verified', page=P_T301, doc=M328_DOC, ds=DS, url=M328_URL, undetermined='', notes=''):
    return {'name': '%s:%s:%s:%s' % (SOC, pad, param, cond_slug), 'soc': SOC, 'pad_class': cls(pad), 'parameter': param, 'condition': condition,
            'vcc_min': vcc[0], 'vcc_max': vcc[1], 'temp_c': temp, 'formula': formula, 'min_value': lo, 'typ_value': typ, 'max_value': hi,
            'unit': unit, 'limit_class': limit, 'verification': verification, 'document': doc, 'datasheet': ds, 'page_table': page, 'url': url,
            'undetermined': undetermined, 'notes': notes}


def characteristics():
    io, rs, xt, ad = 'io-standard', 'reset', 'xtal1', 'adc-only'
    note1 = 'Table 30-1 note 1: "Max" means the highest value where the pin is ensured to be read as low'
    note2 = 'Table 30-1 note 2: "Min." means the lowest value where the pin is ensured to be read as high'
    rows = [
        # ---- input thresholds (standard I/O)
        _row(io, 'VIL', '1v8-2v4', 'VCC = 1.8 V - 2.4 V', vcc=(1.8, 2.4), formula='0.2 VCC', lo='-0.5', hi='0.2 VCC', unit='V', notes=note1),
        _row(io, 'VIL', '2v4-5v5', 'VCC = 2.4 V - 5.5 V', vcc=(2.4, 5.5), formula='0.3 VCC', lo='-0.5', hi='0.3 VCC', unit='V', notes=note1 + '; 1.5 V at VCC = 5 V'),
        _row(io, 'VIH', '1v8-2v4', 'VCC = 1.8 V - 2.4 V', vcc=(1.8, 2.4), formula='0.7 VCC', lo='0.7 VCC', hi='VCC + 0.5', unit='V', notes=note2),
        _row(io, 'VIH', '2v4-5v5', 'VCC = 2.4 V - 5.5 V', vcc=(2.4, 5.5), formula='0.6 VCC', lo='0.6 VCC', hi='VCC + 0.5', unit='V', notes=note2 + '; 3.0 V at VCC = 5 V'),
        # ---- output levels (standard I/O) — the 85 C rows are the UNO's (board thermal limit 85 C); 105 C modelled too
        _row(io, 'VOL', '5v-20ma-85c', 'IOL = 20 mA, VCC = 5 V, TA = 85 C', vcc=(5.0, 5.0), temp='85', hi='0.9', unit='V', page=P_T301,
             notes='Table 30-1 note 4: the pin can sink more under steady state, but the group sums (PinGroupBudget) apply and VOL may exceed the spec above the test current'),
        _row(io, 'VOL', '5v-20ma-105c', 'IOL = 20 mA, VCC = 5 V, TA = 105 C', vcc=(5.0, 5.0), temp='105', hi='1.0', unit='V', page=P_T301),
        _row(io, 'VOL', '3v-10ma-85c', 'IOL = 10 mA, VCC = 3 V, TA = 85 C', vcc=(3.0, 3.0), temp='85', hi='0.6', unit='V', page=P_T301),
        _row(io, 'VOL', '3v-10ma-105c', 'IOL = 10 mA, VCC = 3 V, TA = 105 C', vcc=(3.0, 3.0), temp='105', hi='0.7', unit='V', page=P_T301),
        _row(io, 'VOH', '5v-20ma-85c', 'IOH = -20 mA, VCC = 5 V, TA = 85 C', vcc=(5.0, 5.0), temp='85', lo='4.2', unit='V', page=P_T301B,
             notes='Table 30-1 note 3: "Pins are not ensured to source current greater than the listed test condition"; the VOH guarantee holds only up to 20 mA'),
        _row(io, 'VOH', '5v-20ma-105c', 'IOH = -20 mA, VCC = 5 V, TA = 105 C', vcc=(5.0, 5.0), temp='105', lo='4.1', unit='V', page=P_T301B),
        _row(io, 'VOH', '3v-10ma-85c', 'IOH = -10 mA, VCC = 3 V, TA = 85 C', vcc=(3.0, 3.0), temp='85', lo='2.3', unit='V', page=P_T301B),
        _row(io, 'VOH', '3v-10ma-105c', 'IOH = -10 mA, VCC = 3 V, TA = 105 C', vcc=(3.0, 3.0), temp='105', lo='2.1', unit='V', page=P_T301B),
        # ---- leakage and pull-up
        _row(io, 'IIL', '5v5-low', 'VCC = 5.5 V, pin low (absolute value)', vcc=(5.5, 5.5), hi='1', unit='uA', page=P_T301B),
        _row(io, 'IIH', '5v5-high', 'VCC = 5.5 V, pin high (absolute value)', vcc=(5.5, 5.5), hi='1', unit='uA', page=P_T301B),
        _row(io, 'RPU', 'internal', 'I/O pin pull-up resistor (enabled by PORTxn with DDxn = 0 and MCUCR.PUD = 0)', vcc=(1.8, 5.5), lo='20', hi='50', unit='kohm', page=P_T301B,
             notes='the pull-up resistance is supply-voltage invariant (DS p.84); no typical value is stated'),
        # ---- per-pin current: abs-max / guaranteed test condition / recommended
        _row(io, 'I_PIN', 'abs-max', 'DC current per I/O pin (absolute maximum)', hi='40.0', unit='mA', limit='abs-max', page=P_ABS,
             notes='ABSOLUTE MAXIMUM — a stress rating: never a design target (the datasheet\'s own *NOTICE)'),
        _row(io, 'I_PIN', 'test-5v', 'the output test current of VOH/VOL at VCC = 5 V', vcc=(5.0, 5.0), hi='20', unit='mA', page=P_T301B,
             notes='Table 30-1 note 3/4: "each I/O port can source more than the test conditions (20 mA at VCC = 5 V, 10 mA at VCC = 3 V) under steady state, the following [group sums] must be observed"'),
        _row(io, 'I_PIN', 'test-3v', 'the output test current of VOH/VOL at VCC = 3 V', vcc=(3.0, 3.0), hi='10', unit='mA', page=P_T301B),
        _row(io, 'I_PIN', 'recommended', 'per-pin current a design may rely on (UNO R3)', vcc=(5.0, 5.0), hi='20', unit='mA', limit='recommended', verification='partial',
             doc=U.DOC, ds='arduino-uno-r3-pinout', page='p.1 legend: "MAXIMUM current per I/O pin is 20mA" (board fact arduino-uno-r3:pinout.max_current_io); equals the chip\'s guaranteed test current, Table 30-1 note 3, p.323',
             url=U.URL, notes='partial: no sentence of DS40002061B calls 20 mA "recommended"; the figure is the board vendor\'s own stated maximum and the datasheet\'s guaranteed test condition'),
        # ---- pin voltage
        _row(io, 'V_PIN', 'abs-max', 'voltage on any pin except RESET with respect to ground (absolute maximum)', lo='-0.5', hi='VCC + 0.5', unit='V', limit='abs-max', page=P_ABS),
        # ---- RESET pad
        _row(rs, 'VIL', 'reset', 'RESET pin, VCC = 1.8 V - 5.5 V (VIL2)', vcc=(1.8, 5.5), formula='0.1 VCC', lo='-0.5', hi='0.1 VCC', unit='V', page=P_T301, notes=note1),
        _row(rs, 'VIH', 'reset', 'RESET pin, VCC = 1.8 V - 5.5 V (VIH2)', vcc=(1.8, 5.5), formula='0.9 VCC', lo='0.9 VCC', hi='VCC + 0.5', unit='V', page=P_T301, notes=note2),
        _row(rs, 'VIL', 'reset-as-io-2v4-5v5', 'RESET pin as I/O, VCC = 2.4 V - 5.5 V (VIL3)', vcc=(2.4, 5.5), formula='0.3 VCC', lo='-0.5', hi='0.3 VCC', unit='V', page=P_T301),
        _row(rs, 'VIH', 'reset-as-io-2v4-5v5', 'RESET pin as I/O, VCC = 2.4 V - 5.5 V (VIH3)', vcc=(2.4, 5.5), formula='0.6 VCC', lo='0.6 VCC', hi='VCC + 0.5', unit='V', page=P_T301),
        _row(rs, 'RPU', 'reset', 'reset pull-up resistor (RRST)', vcc=(1.8, 5.5), lo='30', hi='60', unit='kohm', page=P_T301B),
        _row(rs, 'V_PIN', 'abs-max', 'voltage on RESET with respect to ground (absolute maximum)', lo='-0.5', hi='13.0', unit='V', limit='abs-max', page=P_ABS),
        # ---- XTAL1
        _row(xt, 'VIL', 'xtal1', 'XTAL1 pin, VCC = 1.8 V - 5.5 V (VIL1)', vcc=(1.8, 5.5), formula='0.1 VCC', lo='-0.5', hi='0.1 VCC', unit='V', page=P_T301),
        _row(xt, 'VIH', 'xtal1-2v4-5v5', 'XTAL1 pin, VCC = 2.4 V - 5.5 V (VIH1)', vcc=(2.4, 5.5), formula='0.7 VCC', lo='0.7 VCC', hi='VCC + 0.5', unit='V', page=P_T301),
        # ---- analog-only inputs (ADC6/ADC7, TQFP/VQFN only)
        _row(ad, 'V_IN', 'adc', 'ADC input voltage, single-ended', vcc=(1.8, 5.5), lo='GND', hi='VREF', unit='V', page='Table 29-15 ADC Characteristics, p.319'),
        _row(ad, 'R_AIN', 'adc', 'analog input resistance', vcc=(1.8, 5.5), typ='100', unit='Mohm', limit='typical', page='Table 29-15 ADC Characteristics, p.319',
             notes='typical value only; no min/max stated'),
        _row(ad, 'V_PIN', 'abs-max', 'voltage on any pin except RESET with respect to ground (absolute maximum)', lo='-0.5', hi='VCC + 0.5', unit='V', limit='abs-max', page=P_ABS),
    ]
    # the numbers the sources do NOT give — named, never guessed
    rows.append(_row(io, 'I_PIN', 'continuous-recommended-chip', 'a recommended CONTINUOUS per-pin current stated by the chip datasheet', verification='unverified', limit='recommended',
                     page='(not stated in DS40002061B)', undetermined='DS40002061B states test currents (20 mA at 5 V) and the 40 mA absolute maximum but no "recommended continuous" per-pin current; '
                     'the 20 mA recommended row above rests on the board vendor figure'))
    rows.append(_row(ad, 'IIL', 'adc-leakage', 'input leakage of the ADC6/ADC7 analog-only pads', verification='unverified', page='(not stated for the analog-only pads)',
                     undetermined='Table 30-1 gives I/O pin leakage only; the datasheet states RAIN (100 Mohm typ) for the analog inputs but no leakage current for ADC6/ADC7'))
    return rows


# ---------------------------------------------------------------- group budgets (Table 30-1 notes 3 and 4, p.323; §29.1 p.308)
_PC = ['PC%d' % i for i in range(6)]
_PD04 = ['PD%d' % i for i in range(5)]
_PD57 = ['PD%d' % i for i in (5, 6, 7)]
_PB05 = ['PB%d' % i for i in range(6)]
_XT = ['PB6', 'PB7']


def _pb(name, title, direction, members, limit, *, limit_class='recommended', verification='verified', page=P_T301B, package_only=(), cond='', undetermined='', notes=''):
    return {'name': '%s:%s' % (SOC, name), 'soc': SOC, 'title': title, 'direction': direction,
            'members_json': json.dumps(['%s:%s' % (SOC, m) if m[0] == 'P' else m for m in members]),
            'package_only_json': json.dumps(list(package_only)), 'limit_ma': limit, 'limit_class': limit_class, 'verification': verification,
            'condition': cond, 'document': M328_DOC, 'datasheet': DS, 'page_table': page, 'url': M328_URL, 'undetermined': undetermined, 'notes': notes}


def budgets():
    steady = 'steady-state (non-transient) sum; Table 30-1 note %s: "should not exceed"'
    return [
        _pb('ioh-pc-pd-reset', 'Sourcing group 1: PC0-PC5, PD0-PD4, RESET (plus ADC7 in the 32-pin packages)', 'source', _PC + _PD04 + ['PC6'], 150,
            package_only=['ADC7'], cond=steady % '3, item 1', notes='the note names "ports C0 - C5, D0 - D4, ADC7, RESET"; RESET is PC6 (SocPin atmega328p:PC6)'),
        _pb('ioh-pb-pd-xtal', 'Sourcing group 2: PB0-PB5, PD5-PD7, XTAL1, XTAL2 (plus ADC6 in the 32-pin packages)', 'source', _PB05 + _PD57 + _XT, 150,
            package_only=['ADC6'], cond=steady % '3, item 2', notes='the note names "ports B0 - B5, D5 - D7, ADC6, XTAL1, XTAL2"; XTAL1/XTAL2 are PB6/PB7'),
        _pb('iol-pc-adc', 'Sinking group 1: PC0-PC5 (plus ADC6 and ADC7 in the 32-pin packages)', 'sink', _PC, 100,
            package_only=['ADC6', 'ADC7'], cond=steady % '4, item 1', notes='the note names "ports C0 - C5, ADC7, ADC6"'),
        _pb('iol-pb-pd-xtal', 'Sinking group 2: PB0-PB5, PD5-PD7, XTAL1, XTAL2', 'sink', _PB05 + _PD57 + _XT, 100, cond=steady % '4, item 2'),
        _pb('iol-pd-reset', 'Sinking group 3: PD0-PD4, RESET', 'sink', _PD04 + ['PC6'], 100, cond=steady % '4, item 3'),
        _pb('vcc-gnd-abs-max', 'Total through the VCC and GND pins — ABSOLUTE MAXIMUM', 'supply', ['VCC', 'GND'], 200.0, limit_class='abs-max', page=P_ABS,
            notes='ABSOLUTE MAXIMUM — never a design target (§29.1 p.308, same §30.1 p.322)'),
        _pb('vcc-gnd-recommended', 'Total through the VCC and GND pins — recommended', 'supply', ['VCC', 'GND'], 0.0, verification='unverified', page='(not stated in DS40002061B)',
            undetermined='the datasheet states only the 200 mA absolute maximum for the VCC and GND pins; the group sums above bound the pin currents (2 x 150 mA sourcing, 3 x 100 mA sinking) '
                         'but no recommended supply-pin total is given — and the chip\'s own supply current (Table 29-8, p.312) is a separate number'),
    ]
