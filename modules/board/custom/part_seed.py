"""
@module board.custom.part_seed

drv-0 / drv-2 (AI-Notes/plans/DRIVERS_AND_ESD_PLAN.md): THE CITED PART CATALOGUE - the PartBoard seed rows, every number from its datasheet (board.custom.part_boards
reads it).

SEED - ULN2003A in PDIP-16, every number from TI SLRS027T (ULN200x / ULQ200x, December 1976 - revised March 2025):
  pins (Table 4-1): 1B..7B = 1..7 channel inputs, E = 8 common emitter ("typically tied to ground"), COM = 9 common cathode of the clamp diodes,
  7C..1C = 10..16 open-collector outputs; positions from the N (R-PDIP-T16) mechanical drawing 4040049/E: pin pitch 0.100 in (2.54 mm), rows
  0.300 in (7.62 mm) apart (the drawing's 0.300 (7,62) minimum lead spread, the JEDEC MS-001 300-mil row)
  §5.1 absolute maximum: collector-emitter 50 V; input 30 V; peak collector current 500 mA; total emitter-terminal current -2.5 A; operating
  free-air -40 .. 70 C (ULN200xA); §5.6 at 25 C: V_I(on) 2.4 V max at I_C 200 mA (V_CE 2 V); input current 1.35 mA max at V_I 3.85 V;
  §5.2 ESD: HBM +-2000 V (ANSI/ESDA/JEDEC JS-001), CDM +-500 V (JESD22-C101)
SN74AHCT125 (TI SCLS264R), TLC5916 (TI SLVS695D), LM1117-3.3 (TI SNOS412Q), LM2596-5.0 (TI SNVS124G): each row's contract_basis names its sections.
"""
import json

UNKNOWN = -1.0


ULN_DOC = 'TI SLRS027T, ULN200x / ULQ200x High-Voltage, High-Current Darlington Transistor Arrays (rev. March 2025)'


def _uln_pins():
    pins = [{'number': k, 'name': '%dB' % k, 'role': 'in', 'channel': k, 'x_mm': round((k - 1) * 2.54, 3), 'y_mm': 7.62} for k in range(1, 8)]
    pins.append({'number': 8, 'name': 'E', 'role': 'ground', 'channel': 0, 'x_mm': round(7 * 2.54, 3), 'y_mm': 7.62})
    pins.append({'number': 9, 'name': 'COM', 'role': 'common', 'channel': 0, 'x_mm': round(7 * 2.54, 3), 'y_mm': 0.0})
    pins += [{'number': k, 'name': '%dC' % (17 - k), 'role': 'out', 'channel': 17 - k, 'x_mm': round((16 - k) * 2.54, 3), 'y_mm': 0.0} for k in range(10, 17)]
    return pins


def _dip(names_roles, extra=None):
    """A DIP's pins in the ULN2003A's frame (top view): pins 1 .. n/2 along y 7.62 from x 0, then back along y 0 - pin n opposite pin 1. pitch 2.54,
    rows 7.62 apart (TI drawing 4040049/E: pitch 0.100 in basic; rows 0.300 in - JEDEC MS-001)."""
    n, half, out = len(names_roles), len(names_roles) // 2, []
    for k, (name, role, ch) in enumerate(names_roles, 1):
        x = (k - 1) * 2.54 if k <= half else (n - k) * 2.54
        pin = {'number': k, 'name': name, 'role': role, 'channel': ch, 'x_mm': round(x, 3), 'y_mm': 7.62 if k <= half else 0.0}
        pin.update((extra or {}).get(k, {}))
        out.append(pin)
    return out


AHCT_DOC = 'TI SCLS264R, SNx4AHCT125 Quadruple Bus Buffer Gates With 3-State Outputs (rev. February 2024)'
TLC_DOC = 'TI SLVS695D, TLC591x 8-Channel Constant-Current LED Sink Drivers (rev. January 2015)'
LM1117_DOC = 'TI SNOS412Q, LM1117 800-mA, Low-Dropout Linear Regulator (rev. January 2023)'
LM2596_DOC = 'TI SNVS124G, LM2596 SIMPLE SWITCHER Power Converter 150-kHz 3-A Step-Down Voltage Regulator (rev. March 2023)'
DIP_BASIS = ('N (R-PDIP-T**) drawing 4040049/E: pitch 0.100 in (2.54 mm) basic, rows 0.300 in (7.62 mm) apart (JEDEC MS-001); top view, pin 1 bottom '
             'left, the last pin opposite it')

SEED = [{
    'name': 'uln2003a-n', 'kind': 'darlington-array', 'part_number': 'ULN2003AN', 'package': 'PDIP-16 (TI N, R-PDIP-T16)', 'channels': 7,
    'pins_json': json.dumps(_uln_pins()), 'on_volts': 2.4, 'draw_ma': 1.35, 'in_max_v': 30.0, 'out_sink_ma': 500.0, 'out_source_ma': 0.0,
    'out_max_v': 50.0, 'supply_min_v': UNKNOWN, 'supply_max_v': UNKNOWN, 'total_ma': 2500.0, 't_min_c': -40.0, 't_max_c': 70.0, 'esd_hbm_v': 2000.0,
    'esd_cdm_v': 500.0,
    'position_basis': 'N (R-PDIP-T16) drawing 4040049/E: pitch 0.100 in (2.54 mm), rows 0.300 in (7.62 mm) apart (JEDEC MS-001); top view, pin 1 '
                      'bottom left, pin 16 opposite it',
    'contract_basis': ('on_volts = V_I(on) max at I_C 200 mA, V_CE 2 V (§5.6; 2.7 V at 250 mA, 3 V at 300 mA); draw_ma = I_I max at V_I 3.85 V (§5.6); '
                       'in_max_v = V_I (§5.1); out_sink_ma = peak collector current (§5.1, an absolute maximum - the continuous figure falls with duty '
                       'cycle and channels on, Figures 5-4 / 5-5); out_source_ma 0 = an open collector sources nothing (Table 4-1); out_max_v = V_CC '
                       'collector-emitter (§5.1); total_ma = total emitter-terminal current (§5.1)'),
    'document': ULN_DOC, 'page_table': '§3, Table 4-1, §5.1, §5.2, §5.6; N package drawing', 'url': 'https://www.ti.com/lit/ds/symlink/uln2003a.pdf',
    'origin': 'cited', 'notes': 'COM goes to the load supply for inductive loads (the clamp diodes); E to ground'},
    {'name': 'sn74ahct125-n', 'kind': 'buffer', 'part_number': 'SN74AHCT125N', 'package': 'PDIP-14 (TI N)', 'channels': 4,
     'pins_json': json.dumps(_dip([('1OE', 'in', 1), ('1A', 'in', 1), ('1Y', 'out', 1), ('2OE', 'in', 2), ('2A', 'in', 2), ('2Y', 'out', 2),
                                   ('GND', 'ground', 0), ('3Y', 'out', 3), ('3A', 'in', 3), ('3OE', 'in', 3), ('4Y', 'out', 4), ('4A', 'in', 4),
                                   ('4OE', 'in', 4), ('VCC', 'supply', 0)], {14: {'on_volts': 4.5, 'max_volts': 7.0}})),
     'on_volts': 2.0, 'draw_ma': 0.001, 'in_max_v': 7.0, 'out_sink_ma': 8.0, 'out_source_ma': 8.0, 'out_max_v': 5.5, 'out_volts': 3.8,
     'supply_min_v': 4.5, 'supply_max_v': 5.5, 'total_ma': 50.0, 't_min_c': -40.0, 't_max_c': 85.0, 'esd_hbm_v': UNKNOWN, 'esd_cdm_v': UNKNOWN,
     'needs': '', 'position_basis': DIP_BASIS,
     'contract_basis': ('on_volts = V_IH min 2 V (§5.2, VCC 4.5 - 5.5 V: TTL levels, so a 3.3 V output drives it); draw_ma = I_I max +-1 uA over '
                        'temperature (§5.4); in_max_v = V_I absolute maximum 7 V (§5.1); out_sink_ma / out_source_ma = I_OL / I_OH 8 mA (§5.2); out_volts = '
                        'V_OH min 3.8 V at I_OH -8 mA, VCC 4.5 V (§5.4); out_max_v = V_O absolute maximum VCC + 0.5 V at VCC 5 V (§5.1); supply 4.5 - 5.5 V '
                        '(§5.2); total_ma = current through VCC or GND +-50 mA (§5.1); VCC pin: on from its 4.5 V minimum, absolute maximum 7 V (§5.1)'),
     'document': AHCT_DOC, 'page_table': 'Table 4-1, §5.1, §5.2, §5.4; N package drawing', 'url': 'https://www.ti.com/lit/ds/symlink/sn74ahct125.pdf',
     'origin': 'cited', 'notes': ('a 3.3 V -> 5 V up-shifter: TTL inputs on a 5 V supply. OE is active low (output off while OE is high, §3). Each input held '
                                  'at 3.4 V adds up to 1.5 mA supply current (delta I_CC, §5.4). No ESD rating table (§9.4 caution only). TA -40 .. 85 C '
                                  '(§5.2; the package addendum says -40 .. 125 C)')},
    {'name': 'tlc5916-n', 'kind': 'led-driver', 'part_number': 'TLC5916IN', 'package': 'PDIP-16 (TI N)', 'channels': 8,
     'pins_json': json.dumps(_dip([('GND', 'ground', 0), ('SDI', 'in', 0), ('CLK', 'in', 0), ('LE(ED1)', 'in', 0)]
                                  + [('OUT%d' % k, 'out', k + 1) for k in range(8)]
                                  + [('OE(ED2)', 'in', 0), ('SDO', 'out', 0), ('R-EXT', 'common', 0), ('VDD', 'supply', 0)],
                                  {14: {'source_ma': 1.0, 'sink_ma': 1.0, 'max_volts': 5.4}, 16: {'on_volts': 3.0, 'max_volts': 7.0}})),
     'on_volts': 3.5, 'draw_ma': UNKNOWN, 'in_max_v': 5.4, 'out_sink_ma': 120.0, 'out_source_ma': 0.0, 'out_max_v': 20.0, 'out_volts': UNKNOWN,
     'supply_min_v': 3.0, 'supply_max_v': 5.5, 'total_ma': 960.0, 't_min_c': -40.0, 't_max_c': 125.0, 'esd_hbm_v': 1500.0, 'esd_cdm_v': 500.0,
     'needs': 'R-EXT, a resistor to ground that sets the output current (§7.5: 720 Ohm about 26 mA, 360 Ohm about 52 mA)', 'position_basis': DIP_BASIS,
     'contract_basis': ('at VDD 5 V: on_volts = V_IH min 0.7 VDD = 3.5 V (§7.3 - a 3.3 V output does NOT reach it); draw_ma not given (only the 500 kOhm '
                        'typical pull-up on OE, pull-down on LE, §7.5); in_max_v = V_I absolute maximum VDD + 0.4 V (§7.1); out_sink_ma = I_O max 120 mA '
                        'at V_O >= 1 V (§7.3, set by R-EXT; 3 mA minimum); out_source_ma 0 = constant-current sinks; out_max_v = V_O absolute maximum 20 V '
                        '(§7.1); supply 3 - 5.5 V (§7.3); total_ma = I_GND 960 mA (§7.1); SDO: I_OH -1 mA / I_OL 1 mA (§7.3); VDD absolute maximum 7 V'),
     'document': TLC_DOC, 'page_table': '§6 Pin Functions, §7.1, §7.2, §7.3, §7.5; N package drawing', 'url': 'https://www.ti.com/lit/ds/symlink/tlc5916.pdf',
     'origin': 'cited', 'notes': 'eight constant-current sinks loaded serially (SDI / CLK / LE); OE active low; TA -40 .. 125 C (§7.1)'},
    {'name': 'lm1117t-3.3', 'kind': 'ldo', 'part_number': 'LM1117T-3.3/NOPB', 'package': 'TO-220 (TI NDE)', 'channels': 1,
     'pins_json': json.dumps([{'number': 1, 'name': 'GND', 'role': 'ground', 'channel': 0, 'x_mm': 0.0, 'y_mm': 0.0},
                              {'number': 2, 'name': 'VOUT', 'role': 'regulated', 'channel': 1, 'x_mm': 2.54, 'y_mm': 0.0},
                              {'number': 3, 'name': 'VIN', 'role': 'supply', 'channel': 0, 'x_mm': 5.08, 'y_mm': 0.0, 'on_volts': 4.6, 'max_volts': 20.0}]),
     'on_volts': UNKNOWN, 'draw_ma': UNKNOWN, 'in_max_v': UNKNOWN, 'out_sink_ma': UNKNOWN, 'out_source_ma': 800.0, 'out_max_v': UNKNOWN, 'out_volts': 3.3,
     'supply_min_v': 4.6, 'supply_max_v': 15.0, 'total_ma': 800.0, 't_min_c': 0.0, 't_max_c': 125.0, 'esd_hbm_v': 2000.0, 'esd_cdm_v': UNKNOWN,
     'needs': 'input and output capacitors (the datasheet\'s application section)',
     'position_basis': ('NDE0003B (TO-220) drawing: adjacent leads 0.090 - 0.110 in apart, pin 1 to pin 3 0.190 - 0.210 in - the midpoints, 2.54 mm and '
                        '5.08 mm, in one row (derived); the tab is VOUT'),
     'contract_basis': ('out_volts = V_OUT 3.3 V (3.235 - 3.365 V over 0 - 800 mA, 4.75 - 10 V in, TJ 0 - 125 C, §7.5); out_source_ma = 800 mA (§3; '
                        'I_LIMIT 800 min at 25 C, §7.5); supply_min_v = 3.3 V + the 1.3 V maximum dropout at 800 mA (§7.5) = 4.6 V (derived); '
                        'supply_max_v = V_IN 15 V (§7.3); VIN absolute maximum 20 V (§7.1)'),
     'document': LM1117_DOC, 'page_table': 'Table 6-1, §7.1, §7.2, §7.3, §7.5; NDE0003B drawing', 'url': 'https://www.ti.com/lit/ds/symlink/lm1117.pdf',
     'origin': 'cited', 'notes': 'minimum load 5 mA typ / 10 mA max (§7.5); TJ 0 .. 125 C (§7.3; the -40 C LM1117I is not offered in TO-220)'},
    {'name': 'lm2596t-5.0', 'kind': 'buck', 'part_number': 'LM2596T-5.0/NOPB', 'package': 'TO-220-5 (TI NDH)', 'channels': 1,
     'pins_json': json.dumps([{'number': 1, 'name': 'VIN', 'role': 'supply', 'channel': 0, 'x_mm': 0.0, 'y_mm': 0.0, 'on_volts': 7.0, 'max_volts': 45.0},
                              {'number': 2, 'name': 'Output', 'role': 'common', 'channel': 1, 'x_mm': 1.7, 'y_mm': 4.0},
                              {'number': 3, 'name': 'Ground', 'role': 'ground', 'channel': 0, 'x_mm': 3.4, 'y_mm': 0.0},
                              {'number': 4, 'name': 'Feedback', 'role': 'in', 'channel': 1, 'x_mm': 5.1, 'y_mm': 4.0, 'max_volts': 25.0},
                              {'number': 5, 'name': 'ON/OFF', 'role': 'in', 'channel': 0, 'x_mm': 6.8, 'y_mm': 0.0, 'max_volts': 25.0, 'draw_ma': 0.015}]),
     'on_volts': UNKNOWN, 'draw_ma': UNKNOWN, 'in_max_v': 25.0, 'out_sink_ma': UNKNOWN, 'out_source_ma': 3000.0, 'out_max_v': UNKNOWN, 'out_volts': 5.0,
     'supply_min_v': 7.0, 'supply_max_v': 40.0, 'total_ma': 3000.0, 't_min_c': -40.0, 't_max_c': 125.0, 'esd_hbm_v': 2000.0, 'esd_cdm_v': UNKNOWN,
     'needs': ('its inductor, catch diode and input / output capacitors (the typical application): the bare chip has NO regulated pin - Output is the '
               'switch node; the 5 V appears after the inductor, where Feedback senses it. On a bench, a buck module built round it is the Board (define '
               'it as a custom part)'),
     'position_basis': ('NDH0005D (TO-220-5) drawing: leads 0.067 in (1.70 mm) apart; pins 1, 3, 5 bent to one row and 2, 4 to the other (Figure 6-1); '
                        'the rows about 4.0 mm apart, from the lead-tip heights 0.324 - 0.343 in and 0.176 in (derived, not dimensioned directly) - '
                        'not a 2.54 mm breadboard fit'),
     'contract_basis': ('out_volts = V_OUT 5 V (4.75 - 5.25 V over TJ -40 - 125 C, 7 V <= V_IN <= 40 V, 0.2 - 3 A, §7.6); out_source_ma = the 3 A load (§1, '
                        '§7.6); supply_min_v 7 V = the input the 5 V output is specified from (§7.6), supply_max_v 40 V (§7.3); VIN absolute maximum 45 V '
                        '(§7.1); Feedback -0.3 - 25 V (§7.1); ON/OFF up to 25 V (Table 6-1), I_IH 15 uA max at 2.5 V (§7.9); dropout not given as a number '
                        '(Figure 7-6 only)'),
     'document': LM2596_DOC, 'page_table': 'Table 6-1, Figure 6-1, §7.1, §7.2, §7.3, §7.6, §7.9; NDH0005D drawing',
     'url': 'https://www.ti.com/lit/ds/symlink/lm2596.pdf', 'origin': 'cited',
     'notes': ('ON/OFF is active low: on below 0.6 V, off above 2 V (over temperature, §7.9), may be left open (on); the document\'s own tables call the '
               'packages NDZ / KTW where Figure 6-1 says NDH / KTT')}]
