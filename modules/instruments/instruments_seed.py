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
        'note': 'the first model of the osc arc (his pick: 4 channels for 4-channel debugging)' if name == 'rigol-dho804' else ''}


SEED_INSTRUMENTS = [
    _dho('rigol-dho804', 'DHO804', 4, False, 70, 5, price=454.0, price_basis='Jameco listing USD 454 / TestEquity USD 459, seen 2026-10-26', emulated=True),
    _dho('rigol-dho802', 'DHO802', 2, True, 70, 5),
    _dho('rigol-dho812', 'DHO812', 2, True, 100, 3.5),
    _dho('rigol-dho814', 'DHO814', 4, False, 100, 3.5),
    # the two biggest makers by revenue as commonly reported — LINEAGE rows only until one of their models has its datasheet read
    {'name': 'keysight-lineage', 'vendor': 'Keysight', 'model': '(lineage)', 'kind': 'vendor-lineage', 'family': 'InfiniiVision / Infiniium',
     'lineage': 'agilent', 'idn_format': 'KEYSIGHT TECHNOLOGIES,<model>,<serial>,<firmware> (unverified: no Keysight document read)',
     'transports_json': json.dumps([{'name': 'scpi-raw', 'port': -1, 'basis': 'unverified'}, {'name': 'vxi-11', 'port': -1, 'basis': 'unverified'},
                                    {'name': 'hislip', 'port': -1, 'basis': 'unverified'}]),
     'citation': 'the :WAVeform:PREamble? ten-field lineage Rigol adopted (scopehal AgilentOscilloscope + RigolOscilloscope drivers, BSD-3); '
                 'model facts owed: read an InfiniiVision programmer\'s guide + datasheet before any number is written',
     'note': 'second vendor profile for the emulator (D-osc-5 recommended order)'},
    {'name': 'tektronix-lineage', 'vendor': 'Tektronix', 'model': '(lineage)', 'kind': 'vendor-lineage', 'family': 'TBS / MSO',
     'lineage': 'tektronix', 'idn_format': 'TEKTRONIX,<model>,<serial>,<firmware> (unverified: no Tektronix document read)',
     'transports_json': json.dumps([{'name': 'scpi-raw', 'port': -1, 'basis': 'unverified'}, {'name': 'vxi-11', 'port': -1, 'basis': 'unverified'}]),
     'citation': 'WFMOutpre? / CURVe? lineage (scopehal TektronixOscilloscope driver, BSD-3); model facts owed: read a Tektronix programmer '
                 'manual + datasheet before any number is written',
     'note': 'third vendor profile for the emulator; its preamble is the second adapter (osc-1)'},
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
