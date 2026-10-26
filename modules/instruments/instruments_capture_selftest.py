"""instruments_capture_selftest — osc-1 / osc-2 / osc-3 (OSCILLOSCOPE_PLAN.md §3b-d): the IEEE 488.2 block codec round-trips byte-exact and
refuses malformed headers; SCPI units parse with long/short mnemonics; a DHO preamble line gives scopehal's volts/times; a Tektronix
WFMOutpre field set maps onto the same canonical record; 12-bit WORD at full scale spans ±4 divisions; the EMULATOR answers *IDN? honestly
(strict knob = the Rigol form with EMU markers), its sample rate / depth follow the channel count (1.25 G / 625 M / 312.5 M; 25 / 10 / 5 M),
the CLIENT captures four channels over a real loopback socket in 250,000-point pages with WORD data whose sha256 matches the emulator's own
samples and whose volts reproduce the synthesised signals; the refusal replay reaches the client as words; the doors (no manager, in-memory
store) start an emulator, add / refuse endpoints, ask *IDN?, capture, list, and answer chart rows (<= 4000, four series) and 404/409 honestly;
PyVISA-only transports refuse by name when the wheel is absent; the page's paths are routes and its chart is a named-graph-panel over the
seeded GraphDefinition.

    PYTHONPATH=.:modules python3 -m instruments.instruments_capture_selftest      # from polari-framework/
"""
import base64
import hashlib
import json
import re
import sys

import numpy as np

passed = total = 0


def check(label, cond, extra=''):
    global passed, total
    total += 1
    passed += bool(cond)
    print('  [%s] %s %s' % ('\033[0;32mPASS\033[0m' if cond else '\033[0;31mFAIL\033[0m', label, extra if not cond else ''))


def codec():
    from instruments.custom import scpi as S
    payload = bytes(range(256)) * 40
    enc = S.block_encode(payload)
    check('osc-1 BLOCK: encode = "#" + digit count + count + payload (10240 bytes -> #510240...)', enc.startswith(b'#510240') and len(enc) == 7 + 10240)
    dec, used = S.block_decode(enc + b'\nnext')
    check('osc-1 BLOCK: decode round-trips byte-exact and reports the bytes consumed (the newline is left to the caller)', dec == payload and used == len(enc))
    check('osc-1 BLOCK: an empty payload encodes as #10', S.block_encode(b'') == b'#10' and S.block_decode(b'#10\n') == (b'', 3))
    bad = []
    for data in (b'x10', b'#0', b'#2', b'#2ab', b'#3100ab'):
        try:
            S.block_decode(data)
            bad.append(data)
        except S.BlockError:
            pass
    check('osc-1 BLOCK: malformed headers (no #, #0, short digits, non-digits, truncated) raise BlockError', not bad, bad)
    cmds = S.parse_message(':WAV:SOUR CHAN2;:wav:form WORD;*IDN?;:CHANnel1:SCALe 0.5;WAV:DATA?')
    check('osc-1 SCPI: five units parsed; absolute vs relative; queries flagged; args split',
          [c.parts for c in cmds] == [('WAV', 'SOUR'), ('wav', 'form'), ('*IDN',), ('CHANnel1', 'SCALe'), ('WAV', 'DATA')]
          and [c.query for c in cmds] == [False, False, True, False, True] and cmds[0].args == ['CHAN2'] and cmds[3].args == ['0.5']
          and cmds[0].absolute and not cmds[4].absolute, cmds)
    check('osc-1 SCPI: short forms are the capitals (WAVeform -> WAV, SOURce -> SOUR, CHANnel1 -> CHAN1) and both forms match, any case',
          S.short_form('WAVeform') == 'WAV' and S.short_form('CHANnel1') == 'CHAN1' and S.matches(('wav', 'pre'), ('WAVeform', 'PREamble'))
          and S.matches(('WAVEFORM', 'PREAMBLE'), ('WAVeform', 'PREamble')) and not S.matches(('WAV', 'PREA'), ('WAVeform', 'PREamble')))
    check('osc-1 SCPI: *IDN? is four comma fields with commas inside a field replaced', S.idn('A,B', 'M', 'S', 'F') == 'A B,M,S,F')


def preambles():
    from instruments.custom import lineage as L
    text = '1,2,1000,1,8.000000e-10,-5.000000e-07,0,1.953125e-03,0,2048'
    f = L.parse_agilent_preamble(text)
    check('osc-1 AGILENT preamble: ten fields -> WORD / RAW / 1000 points / xinc 0.8 ns / xorigin -500 ns / yinc 1.953125 mV / yref 2048',
          f['format'] == 'WORD' and f['type'] == 'RAW' and f['points'] == 1000 and f['x_increment'] == 8e-10 and f['x_origin'] == -5e-7
          and f['y_increment'] == 1.953125e-3 and f['y_reference'] == 2048 and f['lineage'] == 'agilent', f)
    v = L.volts([2048, 4095, 0], f)
    check('osc-1 AGILENT formula: V = (raw - yorigin - yreference) * yincrement -> mid-scale 0 V, 4095 -> +3.998 V, 0 -> -4 V (±4 div at 1 V/div)',
          abs(v[0]) < 1e-12 and abs(v[1] - 2047 * 1.953125e-3) < 1e-9 and abs(v[2] + 4.0) < 1e-9, v)
    t = L.times(3, f)
    check('osc-1 AGILENT time: t = (i - xref) * xinc + xorigin', np.allclose(t, [-5e-7, -5e-7 + 8e-10, -5e-7 + 1.6e-9]))
    check('osc-1 AGILENT round trip: format_agilent_preamble(parse(x)) parses back to the same numbers',
          L.parse_agilent_preamble(L.format_agilent_preamble(f)) | {'preamble_text': ''} == f | {'preamble_text': ''})
    bad = False
    try:
        L.parse_agilent_preamble('1,2,3')
    except ValueError:
        bad = True
    check('osc-1 AGILENT: a preamble with the wrong field count is refused', bad)
    tek = L.from_tek_fields({'XINcr': 4e-9, 'XZEro': -1e-6, 'PT_Off': 0, 'YMUlt': 4e-3, 'YOFf': -1024, 'YZEro': 0.0, 'NR_Pt': 500, 'BYT_Nr': 2})
    check('osc-1 TEK adapter: WFMOutpre fields -> the canonical record (lineage tektronix, WORD, 500 points)',
          tek['lineage'] == 'tektronix' and tek['format'] == 'WORD' and tek['points'] == 500 and tek['x_increment'] == 4e-9 and tek['y_reference'] == -1024, tek)
    check('osc-1 TEK formula: V = (raw - YOFf) * YMUlt + YZEro; the inverse to_raw rounds back', abs(L.volts([0], tek)[0] - 1024 * 4e-3) < 1e-12
          and L.to_raw(L.volts([123], tek), tek)[0] == 123)
    raw = L.samples(b'\x00\x08\xff\x0f\x00\x00', 'WORD')
    check('osc-1 WORD samples are little-endian uint16 (0x0800 -> 2048, 0x0fff -> 4095)', list(raw) == [2048, 4095, 0])
    check('osc-1 BYTE samples are uint8', list(L.samples(b'\x00\x80\xff', 'BYTE')) == [0, 128, 255])


def emulator_and_client():
    from instruments.custom.emulator import Emulator, REFUSAL_UNSUPPORTED
    from instruments.custom.client import ScopeClient, ScopeRefusal
    from instruments.custom import lineage as L
    emu = Emulator(profile='dho804', port=0).start()
    try:
        with ScopeClient('127.0.0.1', emu.port, timeout=10) as sc:
            idn = sc.idn()
            check('osc-2 IDN honest by default: POLARI,DHO804-EMU,<session>,osc-2', idn.split(',')[:2] == ['POLARI', 'DHO804-EMU'] and idn.split(',')[2] == emu.state.session, idn)
            check('osc-2 SRATE / MDEPTH with one channel on: the channel-count maximum capped by depth / (10 div x s/div) -> 10000 / 10 ms = 1 MSa/s; depth 10000',
                  float(sc.query(':ACQ:SRAT?')) == 1e6 and sc.query(':ACQ:MDEP?') == '10000')
            sc.write(':TIM:SCAL 1e-6')
            check('osc-2 SRATE at 1 us/div with one channel: capped at 1.25 GSa/s (10000 / 10 us = 1 GSa/s < cap -> 1 GSa/s)', float(sc.query(':ACQ:SRAT?')) == 1e9)
            sc.write(':ACQ:MDEP 25M')
            check('osc-2 depth 25M with one channel on -> 25 Mpts and 1.25 GSa/s (both the single-channel maxima)',
                  sc.query(':ACQ:MDEP?') == '25000000' and float(sc.query(':ACQ:SRAT?')) == 1.25e9)
            for n in (2, 3, 4):
                sc.write(':CHAN%d:DISP ON' % n)
            sc.write(':ACQ:MDEP 25M')
            check('osc-2 four channels on: depth capped at 5 Mpts and the sample rate at 312.5 MSa/s (datasheet p.6/9)',
                  sc.query(':ACQ:MDEP?') == '5000000' and float(sc.query(':ACQ:SRAT?')) == 312.5e6)
            sc.write(':CHAN3:DISP OFF')
            sc.write(':CHAN4:DISP OFF')
            sc.write(':ACQ:MDEP 25M')
            check('osc-2 two channels on: 10 Mpts and 625 MSa/s', sc.query(':ACQ:MDEP?') == '10000000' and float(sc.query(':ACQ:SRAT?')) == 625e6)
            # a small, exact capture of all four channels
            for n in (3, 4):
                sc.write(':CHAN%d:DISP ON' % n)
            sc.write(':TIM:SCAL 1e-4')
            sc.write(':ACQ:MDEP 10000')
            sc.write(':CHAN2:SCAL 0.5')
            sc.write(':CHAN2:OFFS 0.25')
            s = sc.channel_settings(2)
            check('osc-3 channel settings read back (0.5 V/div, 0.25 V offset, DC, OFF, 1X, enabled)',
                  s == {'scale_v_div': 0.5, 'offset_v': 0.25, 'coupling': 'DC', 'bw_limit': 'OFF', 'probe': 1.0, 'enabled': True}, s)
            sc.write(':CHAN2:BWL 20M')
            check('osc-3 BWL 20M accepted; a wrong limit is an error on the queue (-224) and the query answers the refusal words',
                  sc.query(':CHAN2:BWL?') == '20M' and sc.query(':CHAN2:BWL 100M;:CHAN2:BWL?') == '20M' and sc.query(':SYST:ERR?').startswith('-224'))
            reads = sc.capture([1, 2, 3, 4])
            check('osc-3 CAPTURE: four channels, 10000 WORD points each, one acquisition (every channel the same shot: trigger info identical)',
                  len(reads) == 4 and all(r['points'] == 10000 and r['format'] == 'WORD' and r['raw_bytes'] == 20000 for r in reads)
                  and len({json.dumps(r['trigger']) for r in reads}) == 1 and reads[0]['sample_rate_sps'] == 1e7)
            own = {ch: hashlib.sha256(emu.state.acquired[ch].astype('<u2').tobytes()).hexdigest() for ch in (1, 2, 3, 4)}
            check('osc-3 CAPTURE: each channel\'s sha256 equals the sha256 of the emulator\'s own samples (the block arrived byte-exact)',
                  all(r['raw_sha256'] == own[r['channel']] for r in reads))
            f1 = reads[0]
            v1 = L.volts(L.samples(f1['payload'], 'WORD'), f1)
            t1 = L.times(f1['points'], f1)
            check('osc-3 VOLTS ch1: a 1 kHz 1 V sine reproduces within one level (yinc = 8 V / 4096) over the window starting at -5 div',
                  abs(t1[0] - (-5e-4)) < 1e-15 and np.max(np.abs(v1 - np.sin(2 * np.pi * 1000 * t1))) <= 8.0 / 4096 + 1e-9, float(np.max(np.abs(v1 - np.sin(2 * np.pi * 1000 * t1)))))
            f2 = reads[1]
            v2 = L.volts(L.samples(f2['payload'], 'WORD'), f2)
            check('osc-3 VOLTS ch2 at 0.5 V/div + 0.25 V offset: a ±1 V square reads ±1 V (the offset is undone by yorigin), yinc = 4 V / 4096',
                  abs(f2['y_increment'] - 4.0 / 4096) < 1e-15 and abs(float(v2.max()) - 1.0) <= 4.0 / 4096 and abs(float(v2.min()) + 1.0) <= 4.0 / 4096, (float(v2.min()), float(v2.max())))
            f4 = reads[3]
            v4 = L.volts(L.samples(f4['payload'], 'WORD'), f4)
            check('osc-3 VOLTS ch4: dc 0.5 V', abs(float(v4.mean()) - 0.5) <= 8.0 / 4096)
            # paging: 600k points in 250k pages
            sc.write(':ACQ:MDEP 600k')
            r = sc.read_channel(1)
            check('osc-3 PAGING: 600,000 points arrive as 250k + 250k + 100k pages, sha256 of the whole equals the emulator\'s',
                  r['points'] == 600000 and r['raw_sha256'] == hashlib.sha256(emu.state.acquired[1].astype('<u2').tobytes()).hexdigest())
            sc.write(':WAV:SOUR CHAN1')
            sc.write(':WAV:STAR 250001')
            sc.write(':WAV:STOP 600000')
            pre = L.parse_agilent_preamble(sc.query(':WAV:PRE?'))
            check('osc-3 PAGING: a page\'s preamble carries ITS point count (250000, the cap) and its own x_origin (the window start)',
                  pre['points'] == 250000 and abs(pre['x_origin'] - (f1['x_origin'] * 0 + emu.state.x_origin() + 250000 * pre['x_increment'])) < 1e-15, pre)
            # BYTE format keeps the top 8 bits
            sc.write(':ACQ:MDEP 1000')
            rb = sc.read_channel(4, fmt='BYTE')
            vb = L.volts(L.samples(rb['payload'], 'BYTE') << 4, rb)
            check('osc-3 BYTE format: 1000 one-byte samples; the top 8 of 12 bits (dc 0.5 V within 16 levels)', rb['points'] == 1000 and rb['raw_bytes'] == 1000 and abs(float(vb.mean()) - 0.5) <= 16 * 8.0 / 4096)
            # unknown header -> -113 on the queue; unknown query -> refusal words
            sc.write(':FOO:BAR 1')
            check('osc-2 ERRORS: an unknown header queues -113,"Undefined header"; an unknown query answers the refusal words; *CLS clears',
                  sc.query(':SYST:ERR?').startswith('-113') and sc.query(':FOO:BAR?') == REFUSAL_UNSUPPORTED and sc.query('*CLS;:SYST:ERR?') == '0,"No error"')
        with ScopeClient('127.0.0.1', emu.port) as sc2:
            check('osc-2 a second connection sees the same instrument (state is the scope\'s, not the socket\'s)', sc2.query(':ACQ:MDEP?') == '1000')
    finally:
        emu.stop()
    strict = Emulator(profile='dho804', port=0, strict_idn=True, refuse_wav_data=True).start()
    try:
        with ScopeClient('127.0.0.1', strict.port) as sc:
            idn = sc.idn()
            check('osc-2 strict IDN: RIGOL TECHNOLOGIES,DHO804,<serial with EMU>,EMU-osc-2 (a tool keyed on the maker connects; nothing claims a real unit)',
                  idn.startswith('RIGOL TECHNOLOGIES,DHO804,') and 'EMU' in idn.split(',')[2] and idn.endswith('EMU-osc-2'), idn)
            refused = ''
            try:
                sc.capture([1])
            except ScopeRefusal as e:
                refused = str(e)
            check('osc-2 REFUSAL replay: :WAV:DATA? answers "The instruction is not supported!" and the client raises ScopeRefusal with those words', refused == REFUSAL_UNSUPPORTED, refused)
    finally:
        strict.stop()


def doors():
    from instruments.custom import captures as X
    X._MEM['InstrumentEndpoint'].clear()
    X._MEM['WaveformCapture'].clear()
    st, p = X.start_emulator(None, {'profile': 'dho804', 'name': 'emu-test', 'sources': {'1': {'kind': 'sine', 'freq_hz': 2000, 'amp_v': 2.0}}})
    try:
        check('osc-3 DOOR emulators: 201 with the endpoint name, a loopback port and the session; the endpoint row is listed (status unchecked)',
              st == 201 and p['endpoint'] == 'emu-test' and p['port'] > 0 and X.endpoint(None, 'emu-test')['status'] == 'unchecked', p)
        check('osc-3 DOOR emulators: a duplicate name is 409; an unknown profile 400 naming the known ones; a bad source 400',
              X.start_emulator(None, {'name': 'emu-test'})[0] == 409 and X.start_emulator(None, {'profile': 'nope'})[0] == 400
              and X.start_emulator(None, {'name': 'emu-bad', 'sources': {'1': {'kind': 'sine', 'volts': 1}}})[0] == 400)
        st, p = X.idn(None, 'emu-test')
        check('osc-3 DOOR idn: 200, the words, the row now says answered with the IDN and a checked_at',
              st == 200 and p['idn'].startswith('POLARI,DHO804-EMU') and X.endpoint(None, 'emu-test')['status'] == 'answered' and X.endpoint(None, 'emu-test')['checked_at'])
        st, p = X.add_endpoint(None, {'name': 'lan-scope', 'instrument': 'rigol-dho804', 'address': '192.0.2.10'})
        check('osc-3 DOOR endpoints: a typed LAN address (TEST-NET here) is accepted at 201 with the default port 0 (= 5555 in the client) and status unchecked',
              st == 201 and X.endpoint(None, 'lan-scope')['port'] == 0 and X.endpoint(None, 'lan-scope')['status'] == 'unchecked')
        check('osc-3 DOOR endpoints refusals: no name 400, duplicate 409, unknown model 404 (known listed), lineage row 404, bad transport 400, no address 400',
              X.add_endpoint(None, {})[0] == 400 and X.add_endpoint(None, {'name': 'lan-scope', 'instrument': 'rigol-dho804', 'address': 'x'})[0] == 409
              and X.add_endpoint(None, {'name': 'e2', 'instrument': 'nope', 'address': 'x'})[0] == 404 and 'known' in X.add_endpoint(None, {'name': 'e2', 'instrument': 'nope', 'address': 'x'})[1]
              and X.add_endpoint(None, {'name': 'e2', 'instrument': 'keysight-lineage', 'address': 'x'})[0] == 404
              and X.add_endpoint(None, {'name': 'e2', 'instrument': 'rigol-dho804', 'address': 'x', 'transport': 'carrier-pigeon'})[0] == 400
              and X.add_endpoint(None, {'name': 'e2', 'instrument': 'rigol-dho804'})[0] == 400)
        st, p = X.idn(None, 'lan-scope')
        check('osc-3 DOOR idn on an unreachable address: 502 with the words, the row says unreachable (a 1 s connect timeout would be a knob; TEST-NET refuses fast or times out)',
              st == 502 and p['status'] == 'unreachable' and X.endpoint(None, 'lan-scope')['status'] == 'unreachable', p)
        st, p = X.add_endpoint(None, {'name': 'visa-scope', 'instrument': 'rigol-dho804', 'address': '192.0.2.11', 'transport': 'vxi-11'})
        st, p = X.idn(None, 'visa-scope')
        try:
            import pyvisa  # noqa: F401
            has = True
        except ImportError:
            has = False
        check('osc-3 DOOR idn over vxi-11 without the PyVISA wheel: refused BY NAME (never a silent fallback to the raw socket)',
              has or (st == 502 and p['status'] == 'refused' and 'PyVISA' in p['idn']), p)
        st, p = X.capture(None, 'emu-test', {'channels': [1, 2, 3, 4], 'max_points': 5000})
        acq = p.get('acquisition', '')
        check('osc-3 DOOR capture: 201, four summary rows of 5000 points, inline storage, source emulated with the source_ref naming the session + the signal',
              st == 201 and len(p['rows']) == 4 and all(r['points'] == 5000 and r['stored'] == 'inline' and r['source'] == 'emulated' for r in p['rows'])
              and 'sine 2000 Hz, 2 V amplitude' in p['rows'][0]['source_ref'] and p['rows'][0]['v_max'] > 1.9, p)
        check('osc-3 DOOR captures: the list has the four rows; the raw sha256 is kept; chart rows are <= 4000 with t_s + ch1..ch4 and a stride of 2',
              len(X.capture_rows(None)) == 4 and all(len(r['raw_sha256']) == 64 for r in X.capture_rows(None))
              and X.chart_rows(None, acq)[0] == 200 and X.chart_rows(None, acq)[1]['stride'] == 2 and len(X.chart_rows(None, acq)[1]['rows']) == 2500
              and set(X.chart_rows(None, acq)[1]['rows'][0]) == {'t_s', 'ch1', 'ch2', 'ch3', 'ch4'} and X.chart_rows(None, acq)[1]['channels'] == ['ch1', 'ch2', 'ch3', 'ch4'])
        check('osc-3 DOOR chart: an unknown acquisition is 404 naming the known ones', X.chart_rows(None, 'acq-nope')[0] == 404 and acq in X.chart_rows(None, 'acq-nope')[1]['known'])
        st, p = X.set_source(None, 'emu-test', {'channel': 3, 'source': {'kind': 'pulses', 'edges': [[0.0, 5.0], [0.0003, 0.0]], 'initial_v': 0.0}})
        st2, p2 = X.capture(None, 'emu-test', {'channels': [3], 'max_points': 10000})
        check('osc-3 DOOR source: a pulses source on ch3 (0 -> 5 V at t=0, back at 300 us) at the default 1 V/div CLIPS at +4 div = 3.998 V (the ±4 div dynamic range, '
              'datasheet p.7) and reads 0 V low (osc-4\'s device feed shape; a 5 V logic line wants 2 V/div)',
              st == 200 and st2 == 201 and abs(p2['rows'][0]['v_max'] - 4095 * 8.0 / 4096 + 2048 * 8.0 / 4096 - 0) < 1e-9 and abs(p2['rows'][0]['v_min']) <= 8.0 / 4096, (p, p2))
        row = next(r for r in X.captures(None) if r['acquisition'] == acq and r['channel'] == 1)
        check('osc-3 RECORD: the stored row holds the preamble text verbatim, the block inline (base64 of 10000 bytes), and the formula fields; sha256(raw) matches',
              row['preamble_text'].count(',') == 9 and len(base64.b64decode(row['raw_b64'])) == 10000
              and hashlib.sha256(base64.b64decode(row['raw_b64'])).hexdigest() == row['raw_sha256'] and row['y_reference'] == 2048.0)
        st, p = X.stop_emulator(None, 'emu-test')
        check('osc-3 DOOR stop: 200 and the row says stopped; a second stop is 404', st == 200 and X.endpoint(None, 'emu-test')['status'] == 'stopped' and X.stop_emulator(None, 'emu-test')[0] == 404)
    finally:
        for name in list(X._EMUS):
            X.stop_emulator(None, name)


def page():
    from instruments.instruments_page import SEED_INSTRUMENTS_PAGE_DISPLAYS as P, SEED_INSTRUMENTS_GRAPHS as G, GRAPH
    from instruments.instruments_seed import INSTRUMENTS_SEED_PAIRS
    d = json.loads(P[0]['definition'])
    keys = [t['key'] for t in d['tabs']]
    items = [it for t in d['tabs'] for r in t['rows'] for it in r['items']]
    kinds = [it.get('componentProps', {}).get('componentName') for it in items]
    check('osc-3 PAGE: /display/instruments has tabs models / endpoints / capture / chart; three door-forms; the chart is ONE named-graph-panel over the seeded GraphDefinition',
          keys == ['models', 'endpoints', 'capture', 'chart'] and kinds.count('door-form') == 3 and kinds.count('named-graph-panel') == 1
          and next(i for i in items if i['id'] == 'instrument-chart')['componentProps']['inputs']['graphName'] == GRAPH and G[0]['name'] == GRAPH
          and json.loads(G[0]['definition'])['graphConfig']['yDimensions'] == ['ch1', 'ch2', 'ch3', 'ch4'], kinds)
    check('osc-3 SEED: the GraphDefinition pair is seeded code-owned beside the Instrument rows', [p[0] for p in INSTRUMENTS_SEED_PAIRS] == ['Instrument', 'GraphDefinition'])
    paths = []

    def walk(node):
        if isinstance(node, dict):
            for k, v in node.items():
                if k in ('dataPath', 'data_path', 'path') and isinstance(v, str) and v.startswith('/api/'):
                    paths.append(v)
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)
    walk(d)
    api = open(__file__.replace('instruments_capture_selftest.py', 'instruments_api.py')).read()
    routes = re.findall(r"add\('([^']+)'", api)
    bad = [p for p in paths if not any(re.fullmatch(re.sub(r'\{[^}]+\}', '[^/]+', r), re.sub(r'\{scope:[^}]*\}', 'X', p.split('?')[0])) for r in routes)]
    check('osc-3 PATHS: every path the page uses (%d) is a route in instruments_api.py' % len(paths), paths and not bad, bad)
    check('osc-3 PAGE: no api-json-panel anywhere', 'api-json-panel' not in P[0]['definition'])


def device_feed():
    """osc-4: the uno-light stimulus's five presses on PD2 (157 ms apart, ~5 ms held) and its ADC0 750 mV become channels; the analog variant's
    triangle ramp; the twin's own pin events; the feed door's refusals."""
    from instruments.custom import captures as X
    from instruments.custom import device_feed as DF
    from instruments.custom import lineage as L
    from board.custom.cycle_stimuli import GAP, HOLD, START, CPS, N_PRESS
    st = DF.sources_from_stimulus('uno-light')
    pd2 = st['sources'].get('PD2')
    check('osc-4 STIMULUS uno-light: PD2 is a pulses line idling at 5 V with 10 edges (5 presses x press+release), the first at START/CPS = 0.1 s; ADC0 dc 0.75 V; the wire PD6:PD3 noted; 1.3 s window',
          pd2 and pd2['initial_v'] == 5.0 and len(pd2['edges']) == 2 * N_PRESS and pd2['edges'][0] == [START / CPS, 0.0] and pd2['edges'][1] == [(START + HOLD) / CPS, 5.0]
          and st['sources']['adc0'] == {'kind': 'dc', 'offset_v': 0.75} and st['wires'] == ['PD6:PD3'] and st['seconds'] == 1.3, st)
    ana = DF.sources_from_stimulus('uno-light-analog')
    check('osc-4 STIMULUS uno-light-analog: ADC0 is the twin\'s triangle 0.2..4.8 V over 1 s; no pin lines; 3.6 s window',
          ana['sources'] == {'adc0': {'kind': 'triangle', 'lo_v': 0.2, 'hi_v': 4.8, 'period_s': 1.0}} and ana['seconds'] == 3.6, ana)
    X._MEM['InstrumentEndpoint'].clear()
    X._MEM['WaveformCapture'].clear()
    st_, p = X.start_emulator(None, {'name': 'emu-feed'})
    try:
        st_, p = X.feed_device(None, 'emu-feed', {'stimulus': 'uno-light', 'channels': {'1': 'PD2', '2': 'adc0'}, 'depth': 100000})
        check('osc-4 FEED door: 200, the window is the stimulus\'s 1.3 s, ch1 <- PD2 and ch2 <- adc0 named, source_ref says the stimulus',
              st_ == 200 and p['seconds'] == 1.3 and p['channels']['1'].endswith('<- PD2') and p['channels']['2'].endswith('<- adc0') and p['source_ref'].startswith('stimulus uno-light'), p)
        st_, p = X.capture(None, 'emu-feed', {'channels': [1, 2]})
        check('osc-4 CAPTURE of the fed channels: 201, two rows, ch1 spans 0 V..5 V (2 V/div so nothing clips), ch2 reads 0.75 V, source_ref carries the stimulus',
              st_ == 201 and len(p['rows']) == 2 and abs(p['rows'][0]['v_max'] - 5.0) <= 16.0 / 4096 and abs(p['rows'][0]['v_min']) <= 16.0 / 4096
              and abs(p['rows'][1]['v_mean'] - 0.75) <= 16.0 / 4096 and 'from stimulus uno-light' in p['rows'][0]['source_ref'], p)
        row = next(r for r in X.captures(None) if r['channel'] == 1)
        f = {k: row[k] for k in ('x_increment', 'x_origin', 'x_reference', 'y_increment', 'y_origin', 'y_reference', 'lineage')}
        v = L.volts(L.samples(base64.b64decode(row['raw_b64']), 'WORD'), f)
        t = L.times(len(v), f)
        low = v < 2.5
        falls = np.flatnonzero(np.diff(low.astype(int)) == 1) + 1
        rises = np.flatnonzero(np.diff(low.astype(int)) == -1) + 1
        dt = float(row['x_increment'])
        check('osc-4 the five presses are five low pulses on ch1: falling edges at 0.1 s + k x 157 ms (within one sample), each held ~5 ms (80000 cycles), the window starts at t = 0',
              len(falls) == N_PRESS and len(rises) == N_PRESS and abs(t[0]) < dt and all(abs(t[fi] - (START + k * GAP) / CPS) <= dt for k, fi in enumerate(falls))
              and all(abs((t[ri] - t[fi]) - HOLD / CPS) <= 2 * dt for fi, ri in zip(falls, rises)), (len(falls), len(rises), [float(t[i]) for i in falls[:5]], dt))
        st_, p = X.feed_device(None, 'emu-feed', {'stimulus': 'uno-light-analog', 'channels': {'3': 'adc0'}})
        st_, p = X.capture(None, 'emu-feed', {'channels': [3]})
        from instruments.custom import sources as SRC
        want_mean = float(SRC.evaluate(ana['sources']['adc0'], np.arange(100000) * 3.6 / 100000).mean())    # 3.6 periods: the partial period lifts the mean above 2.5 V
        check('osc-4 the analog variant\'s triangle on ch3: min 0.2 V, max 4.8 V (within two levels at 2 V/div) and the mean of the function over the 3.6 s window (%.3f V, not 2.5: 3.6 periods)' % want_mean,
              st_ == 201 and abs(p['rows'][0]['v_min'] - 0.2) <= 32.0 / 4096 and abs(p['rows'][0]['v_max'] - 4.8) <= 32.0 / 4096 and abs(p['rows'][0]['v_mean'] - want_mean) < 0.01, p['rows'][0] if p.get('rows') else p)
        events = [{'t': 'pin', 'pin': 'PD6', 'level': 1, 'cycle': 1600000}, {'t': 'pin', 'pin': 'PD6', 'level': 0, 'cycle': 4800000},
                  {'t': 'status', 'cycle': 5000000}, {'t': 'pin', 'pin': 'PD6', 'level': 1, 'cycle': 8000000}]
        lines = DF.sources_from_events(events, CPS)
        check('osc-4 EVENTS: the twin\'s pin events become a pulses line (PD6: idle 0 V, high at 0.1 s, low at 0.3 s, high at 0.5 s; non-pin events ignored)',
              lines == {'PD6': {'kind': 'pulses', 'initial_v': 0.0, 'edges': [[0.1, 5.0], [0.3, 0.0], [0.5, 5.0]]}}, lines)
        st_, p = X.feed_device(None, 'emu-feed', {'events': events, 'cps': CPS, 'seconds': 0.6, 'channels': {'4': 'PD6'}})
        st2, p2 = X.capture(None, 'emu-feed', {'channels': [4]})
        check('osc-4 FEED from events: ch4 <- PD6 over 0.6 s; the capture is high 0.1-0.3 s and 0.5-0.6 s (mean 2.5 V)',
              st_ == 200 and st2 == 201 and abs(p2['rows'][0]['v_mean'] - 2.5) < 0.05 and abs(p2['rows'][0]['v_max'] - 5.0) <= 16.0 / 4096, (p, p2))
        check('osc-4 FEED refusals: no channels 400; an unknown line 404 naming the known; an unknown variant 404; neither stimulus nor events 400; a stopped emulator 404',
              X.feed_device(None, 'emu-feed', {'stimulus': 'uno-light'})[0] == 400
              and X.feed_device(None, 'emu-feed', {'stimulus': 'uno-light', 'channels': {'1': 'PB5'}})[0] == 404 and 'PD2' in X.feed_device(None, 'emu-feed', {'stimulus': 'uno-light', 'channels': {'1': 'PB5'}})[1]['known']
              and X.feed_device(None, 'emu-feed', {'stimulus': 'no-such-variant', 'channels': {'1': 'PD2'}})[0] == 404
              and X.feed_device(None, 'emu-feed', {'channels': {'1': 'PD2'}})[0] == 400 and X.feed_device(None, 'emu-none', {'channels': {'1': 'PD2'}})[0] == 404)
    finally:
        X.stop_emulator(None, 'emu-feed')


def main():
    codec()
    preambles()
    emulator_and_client()
    doors()
    device_feed()
    page()
    print('\n%d/%d checks passed' % (passed, total))
    return 0 if passed == total else 1


if __name__ == '__main__':
    sys.exit(main())
