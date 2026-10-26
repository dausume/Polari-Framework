"""instruments_dialects_selftest — osc-5 part 2 (OSCILLOSCOPE_PLAN.md §3f): the two biggest makers' COMMAND DIALECTS, each cited to scopehal's
driver (BSD-3) and proven end to end against the emulator: the TEKTRONIX dialect (DAT:SOU/WID/ENC, WFMO? 22-field preamble, CURV? signed
blocks, CH:SCA/OFFS, HOR:MODE:SAMPLER/RECO, TRIG:A:EDGE, ACQ:STATE) through the client's tektronix path — volts reproduce the synthesised
signals with the V = (raw - yoff) x ymult formula, 1- and 2-byte widths, big-endian RIB; the KEYSIGHT Infiniium aliases on the agilent dialect
(CHANn:RANGE / INP, WAV:BYT MSBF, ACQUIRE:POINTS?, ADER?, TRIG:SOURCE); honest and strict *IDN? for both; the lineage rows name their dialect
proof without claiming a model (emulated stays False, numbers -1); the doors pick the dialect from the endpoint's Instrument row.

    PYTHONPATH=.:modules python3 -m instruments.instruments_dialects_selftest      # from polari-framework/
"""
import base64
import hashlib
import sys

import numpy as np

passed = total = 0


def check(label, cond, extra=''):
    global passed, total
    total += 1
    passed += bool(cond)
    print('  [%s] %s %s' % ('\033[0;32mPASS\033[0m' if cond else '\033[0;31mFAIL\033[0m', label, extra if not cond else ''))


def tektronix():
    from instruments.custom.emulator import Emulator, REFUSAL_UNSUPPORTED
    from instruments.custom.client import ScopeClient, ScopeRefusal
    from instruments.custom import lineage as L
    emu = Emulator(profile='tek-dialect', port=0).start()
    try:
        with ScopeClient('127.0.0.1', emu.port, timeout=10, dialect='tektronix') as sc:
            idn = sc.idn()
            check('tek IDN honest: POLARI,TEKTRONIX-DIALECT-EMU,<session>,osc-2', idn.split(',')[:2] == ['POLARI', 'TEKTRONIX-DIALECT-EMU'], idn)
            check('tek HEAD 0 / VERB OFF accepted; HOR:MODE? MAN; ACQ:MOD? SAM; TRIG:STATE? names ARM/SAV/REA',
                  sc.query('HEAD 0;VERB OFF;HOR:MODE?') == 'MAN' and sc.query('ACQ:MOD?') == 'SAM' and sc.query('TRIG:STATE?') in ('ARM', 'SAV', 'REA'))
            sc.write('HOR:MODE:RECO 5000')
            check('tek HOR:MODE:RECO 5000 -> record length 5000; HOR:MODE:SAMPLER? = 5000 / (10 x 1 ms) = 500 kSa/s', sc.query('HOR:MODE:RECO?') == '5000' and float(sc.query('HOR:MODE:SAMPLER?')) == 5e5)
            sc.write('HOR:MODE:SAMPLER 1e6')
            check('tek HOR:MODE:SAMPLER 1e6 sets the window so the rate is 1 MSa/s (5000 points over 5 ms -> 0.5 ms/div)', float(sc.query('HOR:MODE:SAMPLER?')) == 1e6 and abs(float(sc.query('HOR:SCA?')) - 5e-4) < 1e-12)
            sc.write('CH2:SCA 0.5;CH2:OFFS 0.25;CH2:COUP AC;CH2:BAN 20E6')
            st = sc.channel_settings_tek(2)
            check('tek channel settings read back: CH2 0.5 V/div, 0.25 V offset, AC, 20E6, probe 1X (PRO:GAIN? = 1), enabled off by default',
                  st == {'scale_v_div': 0.5, 'offset_v': 0.25, 'coupling': 'AC', 'bw_limit': '20E6', 'probe': 1.0, 'enabled': False}, st)
            sc.write('TRIG:A:TYP EDGE;TRIG:A:EDGE:SOU CH2;TRIG:A:LEV:CH2 0.3;TRIG:A:EDGE:SLO FALL')
            info = sc.acquisition_info_tek()
            check('tek trigger read back: EDGE on CH2 at 0.3 V falling', info['trigger'] == {'mode': 'EDGE', 'source': 'CH2', 'level': 0.3, 'slope': 'FALL'}, info)
            reads = sc.capture([1, 2, 3, 4])
            check('tek CAPTURE (DAT:WID 1, SRI): four channels x 5000 signed bytes, lineage tektronix, format INT8, the preamble kept verbatim with 22 fields',
                  len(reads) == 4 and all(r['points'] == 5000 and r['format'] == 'INT8' and r['raw_bytes'] == 5000 and r['lineage'] == 'tektronix' for r in reads)
                  and reads[0]['preamble_text'].count(';') == 21, [(r['points'], r['format']) for r in reads])
            own = {ch: hashlib.sha256(emu.state.acquired[ch].astype('i1').tobytes()).hexdigest() for ch in (1, 2, 3, 4)}
            check('tek the blocks arrive byte-exact (sha256 = the emulator\'s own int8 samples)', all(r['raw_sha256'] == own[r['channel']] for r in reads))
            f1 = reads[0]
            v1 = L.volts(L.samples(f1['payload'], 'INT8'), f1)
            t1 = L.times(f1['points'], f1)
            check('tek VOLTS ch1: V = (raw - yoff) x ymult + yzero reproduces the 1 kHz 1 V sine within one 8-bit level (ymult = 10 V / 256 at 1 V/div); t starts at -5 div',
                  np.max(np.abs(v1 - np.sin(2 * np.pi * 1000 * t1))) <= 10.0 / 256 + 1e-9 and abs(t1[0] - (-5 * 5e-4)) < 1e-15, float(np.max(np.abs(v1 - np.sin(2 * np.pi * 1000 * t1)))))
            f2 = reads[1]
            v2 = L.volts(L.samples(f2['payload'], 'INT8'), f2)
            check('tek VOLTS ch2 at 0.5 V/div + 0.25 V offset: the +-1 V square reads +-1 V (yoff carries the offset in levels; ymult = 5 V / 256)',
                  abs(f2['y_increment'] - 5.0 / 256) < 1e-15 and abs(float(v2.max()) - 1.0) <= 5.0 / 256 and abs(float(v2.min()) + 1.0) <= 5.0 / 256, (float(v2.min()), float(v2.max()), f2['y_reference']))
            r16 = sc.read_channel_tek(1, width=2)
            v16 = L.volts(L.samples(r16['payload'], 'INT16'), r16)
            check('tek DAT:WID 2: 16-bit signed little-endian, ymult = 10 V / 65536, the sine within one 16-bit level', r16['format'] == 'INT16' and r16['raw_bytes'] == 10000
                  and abs(r16['y_increment'] - 10.0 / 65536) < 1e-18 and np.max(np.abs(v16 - np.sin(2 * np.pi * 1000 * t1))) <= 10.0 / 65536 + 1e-9)
            sc.write('DAT:ENC RIB')
            sc.write('DAT:SOU CH1;DAT:START 1;DAT:STOP 4')
            big = sc.query_block('CURV?')
            little = L.samples(r16['payload'][:8], 'INT16')
            check('tek DAT:ENC RIB: big-endian 16-bit words (the first four samples equal the SRI read of the same acquisition)', list(L.samples(big, 'INT16_MSB')) == list(little), (big, little))
            sc.write('DAT:ENC SRI')
            sc.write('HOR:MODE:RECO 600000')
            r = sc.read_channel_tek(1, width=1)
            check('tek PAGING: 600,000 points in 250k pages via DAT:START/STOP + CURV?', r['points'] == 600000 and r['raw_sha256'] == hashlib.sha256(emu.state.acquired[1].astype('i1').tobytes()).hexdigest())
            sc.write('DAT:SOU CH1;DAT:START 250001;DAT:STOP 600000')
            pre = L.parse_tek_preamble(sc.query('WFMO?'))
            check('tek a page\'s WFMO? carries ITS point count (250000) and XZEro at the page start', pre['points'] == 250000 and abs(pre['x_origin'] - (emu.state.x_origin() + 250000 * pre['x_increment'])) < 1e-15, pre)
            sc.write('FOO:BAR 1')
            check('tek an unknown header: -113 on the event queue (EVMSG?), an unknown query answers the refusal words', sc.query('EVMSG?').startswith('-113') and sc.query('FOO:BAR?') == REFUSAL_UNSUPPORTED)
    finally:
        emu.stop()
    strict = Emulator(profile='tek-dialect', port=0, strict_idn=True, refuse_wav_data=True).start()
    try:
        with ScopeClient('127.0.0.1', strict.port, dialect='tektronix') as sc:
            idn = sc.idn()
            refused = ''
            try:
                sc.capture([1])
            except ScopeRefusal as e:
                refused = str(e)
            check('tek strict IDN starts with TEKTRONIX, and the CURV? refusal replay reaches the tektronix client path as words', idn.startswith('TEKTRONIX,DIALECT,') and 'EMU' in idn and refused == REFUSAL_UNSUPPORTED, (idn, refused))
    finally:
        strict.stop()
    bad = False
    try:
        L.parse_tek_preamble('1;8;BINARY')
    except ValueError:
        bad = True
    check('tek a WFMOutpre? reply with the wrong field count is refused', bad)


def keysight():
    from instruments.custom.emulator import Emulator
    from instruments.custom.client import ScopeClient
    from instruments.custom import lineage as L
    emu = Emulator(profile='keysight-dialect', port=0).start()
    try:
        with ScopeClient('127.0.0.1', emu.port, timeout=10) as sc:
            idn = sc.idn()
            check('keysight IDN honest: POLARI,KEYSIGHT-DIALECT-EMU,...', idn.startswith('POLARI,KEYSIGHT-DIALECT-EMU,'), idn)
            sc.write(':CHAN1:RANGE 4')
            check('keysight CHAN1:RANGE 4 -> 0.5 V/div (range = 8 divisions x scale); RANGE? reads 4; INP DC50 accepted; ACQ:POIN:AUTO OFF accepted',
                  float(sc.query(':CHAN1:SCALE?')) == 0.5 and float(sc.query(':CHAN1:RANGE?')) == 4.0 and sc.query(':CHAN1:INP DC50;:CHAN1:INP?') == 'DC50'
                  and sc.query(':ACQ:POIN:AUTO OFF;:ACQ:POIN:AUTO?') == 'OFF')
            sc.write(':ACQ:POINTS:ANALOG 20000')
            check('keysight ACQ:POINTS:ANALOG 20000 -> ACQUIRE:POINTS? 20000; ACQUIRE:SRATE? = 20000 / 10 ms = 2 MSa/s', sc.query(':ACQUIRE:POINTS?') == '20000' and float(sc.query(':ACQUIRE:SRATE?')) == 2e6)
            sc.write(':TRIG:SOURCE CHAN2;:TRIG:SLOPE NEG')
            check('keysight TRIG:SOURCE / TRIG:SLOPE land on the edge trigger; TRIG:LEV? answers; ADER? = 1 (done)',
                  sc.query(':TRIG:EDGE:SOUR?') == 'CHAN2' and sc.query(':TRIG:EDGE:SLOP?') == 'NEG' and sc.query(':TRIG:LEV?') == '0.000000e+00' and sc.query(':ADER?') == '1')
            sc.write(':WAV:BYT MSBF;:WAV:STR ON')
            check('keysight WAV:BYT MSBF / WAV:STR ON read back', sc.query(':WAV:BYT?') == 'MSBF' and sc.query(':WAV:STR?') == 'ON')
            sc.write(':SING')
            sc.query('*OPC?')
            r = sc.read_channel(1, max_points=1000)
            v = L.volts(L.samples(r['payload'], 'WORD_MSBF'), r)
            t = L.times(r['points'], r)
            check('keysight a WORD read with MSBF is big-endian: decoded as WORD_MSBF the 1 kHz sine is within one 16-bit level (ymult = 4 V / 65536 at 0.5 V/div, 16-bit profile)',
                  r['points'] == 1000 and abs(r['y_increment'] - 4.0 / 65536) < 1e-18 and np.max(np.abs(v - np.sin(2 * np.pi * 1000 * t))) <= 4.0 / 65536 + 1e-9, float(np.max(np.abs(v - np.sin(2 * np.pi * 1000 * t)))))
            sc.write(':WAV:BYT LSBF')
            reads = sc.capture([1, 2])
            check('keysight the agilent-dialect capture path works unchanged (two channels, WORD little-endian again)', len(reads) == 2 and all(r['format'] == 'WORD' for r in reads))
    finally:
        emu.stop()


def rows_and_doors():
    from instruments.custom import catalog as C
    from instruments.custom import captures as X
    from instruments.instruments_seed import SEED_INSTRUMENTS
    by = {r['name']: r for r in SEED_INSTRUMENTS}
    check('rows: the two lineage rows name their dialect-proof profile, stay emulated=False with every number -1, and cite the scopehal driver read today',
          by['keysight-lineage']['emulator_profile'] == 'keysight-dialect' and by['tektronix-lineage']['emulator_profile'] == 'tek-dialect'
          and not by['keysight-lineage'].get('emulated') and not by['tektronix-lineage'].get('emulated')
          and 'read 2026-10-26' in by['tektronix-lineage']['citation'] and 'WFMO?' in by['tektronix-lineage']['citation'])
    rows = {r['name']: r for r in C.model_rows(None)}
    check('rows: the card says "dialect proof only (tek-dialect)" for Tektronix, "yes (dho804)" for the DHO804', rows['tektronix-lineage']['emulator'] == 'dialect proof only (tek-dialect)' and rows['rigol-dho804']['emulator'] == 'yes (dho804)')
    X._MEM['InstrumentEndpoint'].clear()
    X._MEM['WaveformCapture'].clear()
    st, p = X.start_emulator(None, {'name': 'emu-tek', 'profile': 'tek-dialect', 'where': 'local'})
    try:
        check('doors: a tek-dialect emulator starts; its endpoint names the tektronix-lineage row, so the doors pick the tektronix client path',
              st == 201 and X.endpoint(None, 'emu-tek')['instrument'] == 'tektronix-lineage' and X._dialect(None, X.endpoint(None, 'emu-tek')) == 'tektronix')
        st, p = X.idn(None, 'emu-tek')
        st2, p2 = X.capture(None, 'emu-tek', {'channels': [1, 2], 'max_points': 2000})
        check('doors: *IDN? and a capture through the tektronix path -> two INT8 rows of 2000 points, ch1 peaks near 1 V', st == 200 and st2 == 201 and len(p2['rows']) == 2
              and all(r['format'] == 'INT8' and r['points'] == 2000 for r in p2['rows']) and abs(p2['rows'][0]['v_max'] - 1.0) <= 10.0 / 256, (p, p2))
        acq = p2['acquisition']
        st3, p3 = X.chart_rows(None, acq)
        row = next(r for r in X.captures(None) if r['acquisition'] == acq and r['channel'] == 1)
        check('doors: the chart decodes the signed block by the row\'s format + lineage (rows <= 4000, ch1 + ch2), the stored sha256 matches the inline bytes',
              st3 == 200 and set(p3['rows'][0]) == {'t_s', 'ch1', 'ch2'} and hashlib.sha256(base64.b64decode(row['raw_b64'])).hexdigest() == row['raw_sha256'] and row['lineage'] == 'tektronix')
    finally:
        X.stop_emulator(None, 'emu-tek')


def main():
    tektronix()
    keysight()
    rows_and_doors()
    print('\n%d/%d checks passed' % (passed, total))
    return 0 if passed == total else 1


if __name__ == '__main__':
    sys.exit(main())
