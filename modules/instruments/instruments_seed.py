"""
@module instruments.instruments_seed

Seed rows (upserted by name — never insert-by-name). INSTRUMENTS_SEED_PAIRS is what admission applies (manifest `seedPairs`).

osc-0 (OSCILLOSCOPE_PLAN.md §1): the RIGOL DHO800 family from ONE table — the DHO800 Series Data Sheet DSA36106-1110 (Oct. 2024)
pp. 6-9, read 2026-10-26 — plus the two vendor-lineage rows (Keysight, Tektronix) whose datasheets have NOT been read: their
numbers are -1 and their strings 'unverified' until a model's document is. Nothing below is typed from memory: every value
names its page, every forum-sourced fact says so (derive-or-cite). No endpoint, channel or capture is ever seeded.
"""
import json

from instruments.instruments_basis import Instrument

_DS = 'RIGOL DHO800 Series Data Sheet DSA36106-1110, Oct. 2024'
_CMD = ('command set + preamble formula: scopehal RigolOscilloscope.cpp (ngscopeclient, BSD-3), DHO branch, read 2026-10-26; '
        'LAN ports: forum-compiled DHO800/900 port list (eevblog "Hacking the Rigol DHO800/900"), NOT the programming guide '
        '(PGA39106-1110, 2025-05-09, listed on rigol.com, no direct URL found)')
_TRIGGERS = ('Edge, Pulse, Slope, Video, Pattern, Duration, Timeout, Runt, Window, Delay, Setup/Hold, Nth Edge, RS232/UART, I2C, SPI, CAN '
             '(datasheet p.10-11)')
_DHO_TRANSPORTS = json.dumps([
    {'name': 'scpi-raw', 'port': 5555, 'basis': 'forum-reported (eevblog DHO800/900 port list); unverified against the programming guide'},
    {'name': 'vxi-11', 'port': 111, 'basis': 'forum-reported portmapper on 111; unverified against the programming guide'},
    {'name': 'usbtmc', 'port': 0, 'basis': 'USB Device interface, datasheet p.1 (TMC class unverified)'},
    {'name': 'hislip', 'port': -1, 'basis': 'unverified'}])
_RIGOL_IDN = 'RIGOL TECHNOLOGIES,<model>,<serial>,<firmware> (four IEEE 488.2 comma fields; serial prefix unverified)'


def _dho(name, model, channels, ext, bw_mhz, rise_ns, price=-1.0, price_basis='', emulated=False):
    """One DHO800 row. Sample rate and depth per enabled-channel count are the datasheet's p.6/p.9 tables; the two-channel models
    quote 'full-channel' at 625 MSa/s / 10 Mpts, the four-channel models 312.5 MSa/s / 5 Mpts with all four on."""
    four = channels == 4
    srate = {'1': 1.25e9, '2': 625e6} | ({'4': 312.5e6} if four else {})
    depth = {'1': 25e6, '2': 10e6} | ({'4': 5e6} if four else {})
    return {
        'name': name, 'vendor': 'RIGOL', 'model': model, 'kind': 'oscilloscope', 'family': 'DHO800',
        'channels': channels, 'ext_trigger': ext, 'bandwidth_hz': bw_mhz * 1e6, 'rise_time_ns': rise_ns,
        'sample_rate_sps': 1.25e9, 'sample_rate_by_channels_json': json.dumps(srate),
        'memory_depth_pts': 25e6, 'memory_depth_by_channels_json': json.dumps(depth),
        'resolution_bits': 12, 'capture_rate_wfms': 1000000, 'capture_rate_basis': 'UltraAcquire mode (30,000 wfms/s in Vector mode), datasheet p.6',
        'input_impedance_ohm': 1e6, 'input_capacitance_pf': 15, 'max_input_v_rms': 300,
        'sensitivity_min_v_div': 500e-6, 'sensitivity_max_v_div': 10.0, 'timebase_min_s_div': 5e-9, 'timebase_max_s_div': 500.0,
        'bw_limits': '20 MHz, FULL (per channel, datasheet p.7)', 'trigger_types': _TRIGGERS,
        'transports_json': _DHO_TRANSPORTS, 'lineage': 'agilent', 'idn_format': _RIGOL_IDN, 'lxi': 'unverified',
        'display': '7 in 1024x600 capacitive multi-touch (p.6-7)', 'size_mm': '265.35 x 161.75 x 77.38 (W x H x D, p.2)',
        'price_usd': price, 'price_basis': price_basis,
        'citation': '%s pp.6-9 (bandwidth, channels, rise time, sample rate and depth per channel count, capture rate, 12 bits, input, '
                    'sensitivity, timebase, triggers); %s' % (_DS, _CMD),
        'emulated': emulated, 'emulator_profile': 'dho804' if emulated else '',
        'digital_channels': 0, 'differential_inputs': 0, 'openness': 'hardware closed / firmware closed / software closed (a commercial instrument; the command set is cited to scopehal)',
        'data_access': 'SCPI over LAN (raw socket 5555 / VXI-11) or USBTMC: the 488.2 block + preamble (osc-1..3)',
        'note': 'the first model of the osc arc (his pick: 4 channels for 4-channel debugging)' if name == 'rigol-dho804' else ''}


# osc-6 (his ask 2026-10-27): two OPEN SOURCE oscilloscopes, "because open source options should be our priority, we want people to be able to test
# without expensive options if possible". Every number names its page; the licence is stated only where a licence file / page was READ.
_SF_SITE = 'scopefun.com home page (read 2026-10-27)'
_SF_CS = 'Crowd Supply campaign page "ScopeFun: Open Source Instrumentation" (read 2026-10-27; funded 2019-08-09)'
_SF_GL = 'gitlab.com/scopefun/scopefun-software project page (read 2026-10-27: licence "GNU GPLv3", COPYING.TXT)'
SCOPEFUN = {
    'name': 'scopefun', 'vendor': 'ScopeFun', 'model': 'ScopeFun', 'kind': 'oscilloscope', 'family': 'open source instrumentation platform',
    'channels': 2, 'ext_trigger': False, 'bandwidth_hz': 100e6, 'rise_time_ns': -1.0,
    'sample_rate_sps': 500e6, 'sample_rate_by_channels_json': json.dumps({'1': 500e6, '2': 250e6}),
    'memory_depth_pts': 128e6, 'memory_depth_by_channels_json': json.dumps({'1': 128e6, '2': 128e6}),
    'resolution_bits': 10, 'capture_rate_wfms': -1.0, 'capture_rate_basis': '',
    'input_impedance_ohm': -1.0, 'input_capacitance_pf': -1.0, 'max_input_v_rms': -1.0,
    'sensitivity_min_v_div': 10e-3, 'sensitivity_max_v_div': 2.0, 'timebase_min_s_div': -1.0, 'timebase_max_s_div': -1.0,
    'bw_limits': 'unverified', 'trigger_types': 'unverified (the campaign page lists none by name)',
    'transports_json': json.dumps([{'name': 'usb3', 'port': 0, 'basis': 'USB 3.0 through a Cypress FX3 (%s); the host protocol is the GPLv3 software\'s own, not SCPI' % _SF_CS}]),
    'lineage': 'none', 'idn_format': 'none (no SCPI; the software identifies the board over USB - unverified)', 'lxi': 'none (USB only)',
    'display': 'none: the host software draws (PC)', 'size_mm': 'unverified',
    'price_usd': 899.0, 'price_basis': 'Crowd Supply campaign price USD 899 (2019); SparkFun lists it "retired" and Crowd Supply\'s enclosure "no longer available" (2026-10-27) - current availability unverified',
    'citation': '%s: "2 analog oscilloscope channels (10-bit)", "500 Msps Real-Time Sampling rate (single channel) / 250 Msps (dual channel)", "2.0 GSps Equivalent-Time Sampling rate (ETS)", '
                '"128 Mega samples memory buffer (per channel)", "12 digital channels (logic analyzer / digital pattern generator)", "2 analog generators (200 Msps, 12-bit)", "USB 3.0 interface"; '
                '%s: 100 MHz analog bandwidth (-3 dB), 10 mV to 2 V per division (1x probe), inputs "protected against over-voltages up to +/- 50 V", logic analyzer 12 channels at 250 MSPS '
                '(125 MHz max toggle), interface voltage 1.25-3.3 V, inputs accept up to 5 V, Xilinx Artix-7 XC7A35T, 512 MB DDR3, Cypress FX3; %s' % (_SF_SITE, _SF_CS, _SF_GL),
    'emulated': False, 'emulator_profile': '',
    'digital_channels': 12, 'digital_max_rate_sps': 250e6, 'differential_inputs': 0, 'ets_sample_rate_sps': 2.0e9,
    'openness': 'OPEN - ADMITTED (his ruling 2026-10-27: "GPLv3 is sufficient, the hardware is under the CERN OHL"): software GPLv3 (COPYING.TXT read); hardware CERN OHL by his statement '
                '(the variant S / W / P and the hardware repository\'s licence file not read: to_read)',
    'data_access': 'its own USB 3.0 protocol through the GPLv3 host software (no SCPI): Polari would read its saved captures or wrap the software - a later adapter (osc-7); not built',
    'note': 'OPEN SOURCE pick 1 (his ask): 2 analog + 12 digital channels on an Artix-7, PC-hosted. Price is the 2019 campaign\'s; availability today unverified.'}

_DSO_MAN = 'JYE Tech DSO138 Users Manual (13803K/04K), the Specifications table and the schematic page (PDF read 2026-10-27: the MCU symbol reads STM32F103Cx)'
_DSO_PAGE = 'jyetech.com DSO138 product page (read 2026-10-27)'
_DSO_TOM = 'tomeko.net/projects/dso138 (a third-party page, read 2026-10-27)'
DSO138 = {
    'name': 'jyetech-dso138', 'vendor': 'JYE Tech', 'model': 'DSO138', 'kind': 'oscilloscope', 'family': 'DSO138 (DIY kit)',
    'channels': 1, 'ext_trigger': False, 'bandwidth_hz': 200e3, 'rise_time_ns': -1.0,
    'sample_rate_sps': 1e6, 'sample_rate_by_channels_json': json.dumps({'1': 1e6}),
    'memory_depth_pts': 1024, 'memory_depth_by_channels_json': json.dumps({'1': 1024}),
    'resolution_bits': 12, 'capture_rate_wfms': -1.0, 'capture_rate_basis': '',
    'input_impedance_ohm': 1e6, 'input_capacitance_pf': 20, 'max_input_v_rms': -1.0,
    'sensitivity_min_v_div': 10e-3, 'sensitivity_max_v_div': 5.0, 'timebase_min_s_div': 10e-6, 'timebase_max_s_div': 500.0,
    'bw_limits': 'none stated', 'trigger_types': 'Auto, Normal, Single (edge; trigger position fixed at 50 %) - the manual\'s table',
    'transports_json': json.dumps([{'name': 'serial-text', 'port': 0, 'basis': 'UART TX at 115200 8N1: on HOLD the firmware sends the record as text (%s - third-party, '
                                                                                'not in the manual read; the exact format unverified)' % _DSO_TOM}]),
    'lineage': 'none', 'idn_format': 'none (no SCPI)', 'lxi': 'none', 'display': '2.4 in colour TFT 320 x 240 (product page)', 'size_mm': '117 x 76 x 15 (manual\'s table)',
    'price_usd': -1.0, 'price_basis': 'reported as a USD 23 kit by cnx-software (2015-04-06); the current price is unverified (the product page says the model is old and points to the DSO138mini)',
    'citation': '%s: "Max realtime sample rate 1MSa/s", "Analog bandwidth 0 -- 200KHz", "Sensitivity range 10mV/div - 5V/div", "Max input voltage 50Vpk (1X probe)", '
                '"Input impedance 1M ohm/20pF", "Resolution 12 bits", "Record length 1024 points", "Timebase range 500s/Div -- 10us/Div", "Trigger modes Auto, Normal, and Single", '
                '"Trigger position range 50%%", "Power supply 9V DC (8 - 12V)", "Current consumption ~120mA", "Dimension 117 x 76 x 15mm", "Weight 70 gram"; %s; %s: the anti-aliasing '
                'filter differs between the JYE board (C8 120 pF: -3 dB at 11 MHz) and a clone (100 nF: 13.3 kHz) - so the EFFECTIVE bandwidth depends on the board' % (_DSO_MAN, _DSO_PAGE, _DSO_TOM),
    'emulated': False, 'emulator_profile': '',
    'digital_channels': 0, 'digital_max_rate_sps': -1.0, 'differential_inputs': 0, 'ets_sample_rate_sps': -1.0,
    'openness': 'OPEN - ADMITTED (his ruling 2026-10-27: "gives sufficient permissions to be both open source and allows resale"): the JYE Tech source readme (seen through the gitee '
                'mirror HEYAHONG/DSO138, 2026-10-27) says "free software ... NO WARRANTY ... use, modify, and redistribute it for personal, non-profit, or commercial product UNDER YOUR '
                'OWN RESPONSIBILITY ... Redistributions of source codes must retain the above copyright notice" - no SPDX licence name; the product page offers "Source Code: Basic '
                'version" + the LCD-board schematic (the main schematic is in the manual); a third-party page says most functionality sits in a precompiled library (libdso138.a). '
                'The alternative firmware DLO-138 (github ardyesp/DLO-138, Arduino build, 2 analog + 2 digital channels, serial output) shows NO licence file (read 2026-10-27)',
    'data_access': 'serial text dump of the 1024-point record on HOLD (115200 8N1, one-way; third-party description) - a serial adapter into the canonical capture is osc-7; not built',
    'note': 'OPEN SOURCE pick 2 (his ask): the cheapest real instrument that could stand on the bench; 1 channel, 200 kHz, 1 MSa/s, 12 bits. Admitted by his ruling; the readme\'s own words are the terms.'}


SEED_INSTRUMENTS = [
    SCOPEFUN,
    DSO138,
    _dho('rigol-dho804', 'DHO804', 4, False, 70, 5, price=454.0, price_basis='Jameco listing USD 454 / TestEquity USD 459, seen 2026-10-26', emulated=True),
    _dho('rigol-dho802', 'DHO802', 2, True, 70, 5),
    _dho('rigol-dho812', 'DHO812', 2, True, 100, 3.5),
    _dho('rigol-dho814', 'DHO814', 4, False, 100, 3.5),
    # the two biggest makers by revenue as commonly reported — LINEAGE rows only until one of their models has its datasheet read
    {'name': 'keysight-lineage', 'vendor': 'Keysight', 'model': '(lineage)', 'kind': 'vendor-lineage', 'family': 'InfiniiVision / Infiniium',
     'lineage': 'agilent', 'idn_format': 'KEYSIGHT TECHNOLOGIES,<model>,<serial>,<firmware> (unverified: no Keysight document read)',
     'transports_json': json.dumps([{'name': 'scpi-raw', 'port': -1, 'basis': 'unverified'}, {'name': 'vxi-11', 'port': -1, 'basis': 'unverified'},
                                    {'name': 'hislip', 'port': -1, 'basis': 'unverified'}]),
     'citation': 'the :WAVeform:PREamble? ten-field lineage Rigol adopted (scopehal AgilentOscilloscope.cpp, BSD-3, read 2026-10-26: WAV:SOUR / WAV:FORM WORD / '
                 'WAV:BYT LSBF / WAV:STR ON / WAV:PRE? / WAV:DATA?; CHANn:DISP / RANGE / OFFS / INP / BWL / PROB; ACQUIRE:SRATE? / POINTS?; SING; ADER?; TRIG:EDGE:SOUR?, '
                 'TRIG:LEV? CHANn); model facts owed: read an InfiniiVision programmer\'s guide + datasheet before any number is written',
     'emulator_profile': 'keysight-dialect',
     'note': 'second vendor profile for the emulator (D-osc-5 recommended order): a DIALECT PROOF profile exists (emulated stays False: no model is claimed)'},
    {'name': 'tektronix-lineage', 'vendor': 'Tektronix', 'model': '(lineage)', 'kind': 'vendor-lineage', 'family': 'TBS / MSO',
     'lineage': 'tektronix', 'idn_format': 'TEKTRONIX,<model>,<serial>,<firmware> (unverified: no Tektronix document read)',
     'transports_json': json.dumps([{'name': 'scpi-raw', 'port': -1, 'basis': 'unverified'}, {'name': 'vxi-11', 'port': -1, 'basis': 'unverified'}]),
     'citation': 'WFMOutpre? / CURVe? lineage (scopehal TektronixOscilloscope.cpp, BSD-3, read 2026-10-26, the MSO5/6 path: DAT:SOU / DAT:WID 1 / DAT:ENC SRI / '
                 'DAT:START / DAT:STOP / WFMO? (22 fields: byte_num;bit_num;encoding;bin_format;asc_format;byte_order;wfid;nr_pt;pt_fmt;pt_order;xunit;xincrement;xzero;'
                 'pt_off;yunit;ymult;yoff;yzero;domain;wfmtype;centerfreq;span) / CURV?; CHn:SCA / OFFS / COUP / BAN / PRO:GAIN?; DISP:WAVEV:CHn:STATE; HOR:MODE:SAMPLER / '
                 'RECO; TRIG:A:TYP / EDGE:SOU / LEV:CHn / EDGE:SLO; ACQ:STATE / STOPA; V = (raw - yoff) x ymult (scopehal: gain = ymult, offset = -yoff)); model facts owed: '
                 'read a Tektronix programmer manual + datasheet before any number is written',
     'emulator_profile': 'tek-dialect',
     'note': 'third vendor profile for the emulator; its preamble is the second adapter (osc-1); a DIALECT PROOF profile exists (emulated stays False: no model is claimed)'},
]

def _pairs():
    pairs = [('Instrument', Instrument, SEED_INSTRUMENTS)]
    try:
        from polariApiServer.graphDefinition import GraphDefinition
        from instruments.instruments_page import SEED_INSTRUMENTS_GRAPHS
        pairs.append(('GraphDefinition', GraphDefinition,
                      [dict(r, _converge=[k for k in r if k not in ('name', 'description')]) for r in SEED_INSTRUMENTS_GRAPHS]))   # code-owned, as hwnocode's graphs
    except ImportError:
        pass
    return pairs


INSTRUMENTS_SEED_PAIRS = _pairs()
