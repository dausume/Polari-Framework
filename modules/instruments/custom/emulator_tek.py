"""
@module instruments.custom.emulator_tek

osc-5 part 2 (OSCILLOSCOPE_PLAN.md §3f): the TEKTRONIX command DIALECT of the emulator — the second of the two preamble lineages, so the client's
Tektronix path is proven before a Tektronix instrument is on the bench. Every command here is cited to the BSD-3 scopehal driver
`scopehal/TektronixOscilloscope.cpp` (read 2026-10-26, the MSO5/6 path); NO Tektronix document was read, so the `tek-dialect` profile's limits
are placeholders labelled as such in PROFILES (a dialect proof, not a model) and the Instrument row `tektronix-lineage` keeps every number -1.

  waveform    DAT:SOU CH<n> · DAT:WID 1|2 · DAT:ENC SRI|RIB (signed binary; SRI = little-endian) · DAT:START <n> · DAT:STOP <n> · WFMO? · CURV?
  preamble    WFMO? -> 22 ';'-separated fields in scopehal's order: byte_num;bit_num;encoding;bin_format;asc_format;byte_order;wfid;nr_pt;pt_fmt;
              pt_order;xunit;xincrement;xzero;pt_off;yunit;ymult;yoff;yzero;domain;wfmtype;centerfreq;span
              V = (raw - yoff) * ymult + yzero (scopehal passes gain = ymult, offset = -yoff; YZEro kept by us) ; t = (i - pt_off) * xincrement + xzero
  channels    CH<n>:SCA (V/div; scopehal: range = 10 x scale) · CH<n>:OFFS · CH<n>:COUP DC|AC · CH<n>:BAN FUL|<Hz> · CH<n>:PRO:GAIN? · DISP:WAVEV:CH<n>:STATE ON|OFF
  horizontal  HOR:MODE MAN · HOR:MODE:SAMPLER <sps> · HOR:MODE:RECO <points> · HOR:DEL:MOD ON · HOR:DELAY:TIME <s> · HOR:SCA
  trigger     TRIG:A:TYP EDGE · TRIG:A:EDGE:SOU CH<n> · TRIG:A:LEV:CH<n> <V> · TRIG:A:EDGE:SLO RIS|FALL|EIT · TRIG:STATE? (SAV|ARM|REA) · TRIG FORC
  acquisition ACQ:STATE ON|OFF|RUN|STOP|1|0 · ACQ:STOPA SEQ|RUNST · ACQ:MOD SAM · HEAD 0 · VERB OFF · *IDN? · *OPC?
Vertical convention (ours, stated): signed raw over 10 divisions, ymult = 10 x V/div / 2^(8 x DAT:WID), yoff = offset / ymult (levels), yzero = 0.
"""
import numpy as np

from instruments.custom import scpi
from instruments.custom import lineage as L

_SLOPES = {'RIS': 'RIS', 'RISE': 'RIS', 'FALL': 'FALL', 'EIT': 'EIT', 'EITHER': 'EIT', 'ANY': 'EIT'}


def _ch(arg):
    a = arg.upper().replace('CHANNEL', 'CH').replace('CHAN', 'CH')      # CH1 (Tektronix) - CHAN1 / CHANnel1 accepted too
    if a.startswith('CH') and a[2:].isdigit():
        return int(a[2:])
    return None


def tek_fields(state, channel):
    """The preamble parameters for one channel at the current settings (lineage tektronix, signed raw)."""
    c = state.channels[channel]
    wid = int(state.wav.get('width', 1))
    bits = 8 * wid
    ymult = state.p['divisions_v'] * c['scale'] / (1 << bits)
    return {'format': 'INT16' if wid == 2 else 'INT8', 'type': 'RAW', 'points': int(state.mdepth), 'count': 1,
            'x_increment': 1.0 / state.srate(), 'x_origin': state.x_origin(), 'x_reference': 0.0,
            'y_increment': ymult, 'y_origin': 0.0, 'y_reference': c['offset'] / ymult, 'lineage': 'tektronix', 'bits': bits}


def preamble_text(state, channel, points, x_origin):
    f = tek_fields(state, channel)
    c = state.channels[channel]
    wid = int(state.wav.get('width', 1))
    wfid = '"Ch%d, %s coupling, %gV/div, %gs/div, %d points, Sample mode"' % (channel, c['coupling'], c['scale'], state.tb_scale, points)
    return ';'.join([str(wid), str(8 * wid), 'BINARY', 'RI', 'RI', 'LSB', wfid, str(points), 'Y', 'LINEAR', '"s"', '%.12e' % f['x_increment'],
                     '%.12e' % x_origin, '0', '"V"', '%.12e' % f['y_increment'], '%.12e' % f['y_reference'], '%.12e' % f['y_origin'],
                     'TIME', 'ANALOG', '0.0E0', '0.0E0'])


def dispatch(emu, cmd):
    """One command unit in the Tektronix dialect -> reply text | bytes | None; raises emu's _Unsupported for an unknown header."""
    from instruments.custom.emulator import _Unsupported, REFUSAL_UNSUPPORTED
    s, parts, q, args = emu.state, cmd.parts, cmd.query, cmd.args
    M = scpi.matches
    head = parts[0].upper()
    if M(parts, ('*IDN',)) and q:
        return emu.idn()
    if M(parts, ('*OPC',)):
        return '1' if q else None
    if M(parts, ('*CLS',)):
        s.errors.clear()
        return None
    if M(parts, ('*RST',)):
        emu.reset()
        return None
    if head in ('HEAD', 'HEADER', 'VERB', 'VERBOSE'):
        return '0' if q else None
    if M(parts, ('ALLEV',)) and q or M(parts, ('EVMSG',)) and q:
        return s.errors.pop(0) if s.errors else '0,"No events"'
    # channels: CH<n>:SCA / OFFS / COUP / BAN / PRO:GAIN?
    if _ch(parts[0]) is not None and len(parts) >= 2:
        n = _ch(parts[0])
        if n not in s.channels:
            raise _Unsupported()
        c, sub = s.channels[n], parts[1]
        if scpi.long_or_short_match(sub, 'SCAle'):
            if q:
                return '%.6e' % c['scale']
            c['scale'] = min(max(float(args[0]), s.p['scale_min']), s.p['scale_max'])
            s.invalidate()
            return None
        if scpi.long_or_short_match(sub, 'OFFSet'):
            if q:
                return '%.6e' % c['offset']
            c['offset'] = float(args[0])
            s.invalidate()
            return None
        if scpi.long_or_short_match(sub, 'COUPling'):
            if q:
                return c['coupling']
            c['coupling'] = {'AC': 'AC', 'DC': 'DC'}[args[0].upper()]
            return None
        if scpi.long_or_short_match(sub, 'BANdwidth'):
            if q:
                return c['bwl']
            c['bwl'] = 'FUL' if args[0].upper().startswith('FUL') else args[0].upper()
            return None
        if scpi.long_or_short_match(sub, 'PRObe') and len(parts) == 3 and scpi.long_or_short_match(parts[2], 'GAIN') and q:
            return '%.6e' % (1.0 / c['probe'])
        raise _Unsupported()
    # DISP:WAVEV:CH<n>:STATE  (DISPlay:WAVEView1:CH<n>:STATE)
    if head in ('DISP', 'DISPLAY') and len(parts) == 4 and _ch(parts[2]) in s.channels and scpi.long_or_short_match(parts[3], 'STATE'):
        c = s.channels[_ch(parts[2])]
        if q:
            return '1' if c['display'] else '0'
        c['display'] = args[0].upper() in ('1', 'ON')
        s.invalidate()
        return None
    # horizontal
    if head in ('HOR', 'HORIZONTAL'):
        if len(parts) == 2 and scpi.long_or_short_match(parts[1], 'MODE'):
            return 'MAN' if q else None
        if len(parts) == 3 and scpi.long_or_short_match(parts[1], 'MODE') and scpi.long_or_short_match(parts[2], 'SAMPLERate'):
            if q:
                return '%.6e' % s.srate()
            wanted = float(args[0])
            s.tb_scale = min(max(s.mdepth / wanted / s.p['divisions_h'], s.p['tb_min']), s.p['tb_max'])   # the rate is set through the window (depth / rate)
            s.invalidate()
            return None
        if len(parts) == 3 and scpi.long_or_short_match(parts[1], 'MODE') and scpi.long_or_short_match(parts[2], 'RECOrdlength'):
            if q:
                return '%d' % int(s.mdepth)
            s.mdepth = int(min(int(float(args[0])), s.depth_cap()))
            s.wav['start'], s.wav['stop'] = 1, int(s.mdepth)
            s.invalidate()
            return None
        if len(parts) == 3 and scpi.long_or_short_match(parts[1], 'DELay') and scpi.long_or_short_match(parts[2], 'MODe'):
            return 'ON' if q else None
        if len(parts) == 3 and scpi.long_or_short_match(parts[1], 'DELay') and scpi.long_or_short_match(parts[2], 'TIMe'):
            if q:
                return '%.6e' % s.tb_offset
            s.tb_offset = float(args[0])
            s.invalidate()
            return None
        if len(parts) == 2 and scpi.long_or_short_match(parts[1], 'SCAle'):
            if q:
                return '%.6e' % s.tb_scale
            s.tb_scale = min(max(float(args[0]), s.p['tb_min']), s.p['tb_max'])
            s.invalidate()
            return None
        raise _Unsupported()
    # trigger
    if head in ('TRIG', 'TRIGGER'):
        if len(parts) == 1 and not q and args and args[0].upper().startswith('FORC'):
            s.acquire()
            s.run = 'SAV'
            return None
        if len(parts) == 2 and scpi.long_or_short_match(parts[1], 'STATE') and q:
            return {'RUN': 'ARM', 'STOP': 'SAV', 'SAV': 'SAV'}.get(s.run, 'REA')
        if len(parts) >= 3 and parts[1].upper() == 'A':
            if scpi.long_or_short_match(parts[2], 'TYPe'):
                if q:
                    return s.trigger['mode']
                s.trigger['mode'] = args[0].upper()
                return None
            if len(parts) == 4 and scpi.long_or_short_match(parts[2], 'EDGE') and scpi.long_or_short_match(parts[3], 'SOUrce'):
                if q:
                    return s.trigger['source']
                if _ch(args[0]) not in s.channels:
                    raise ValueError(args[0])
                s.trigger['source'] = 'CH%d' % _ch(args[0])
                return None
            if len(parts) == 4 and scpi.long_or_short_match(parts[2], 'EDGE') and scpi.long_or_short_match(parts[3], 'SLOpe'):
                if q:
                    return s.trigger['slope']
                s.trigger['slope'] = _SLOPES[args[0].upper()]
                return None
            if len(parts) == 4 and scpi.long_or_short_match(parts[2], 'LEVel') and _ch(parts[3]) in s.channels:
                if q:
                    return '%.6e' % s.trigger['level']
                s.trigger['level'] = float(args[0])
                return None
        raise _Unsupported()
    # acquisition
    if head in ('ACQ', 'ACQUIRE') and len(parts) == 2:
        sub = parts[1]
        if scpi.long_or_short_match(sub, 'STATE'):
            if q:
                return '1' if s.run == 'RUN' else '0'
            on = args[0].upper() in ('ON', 'RUN', '1')
            if on:
                s.acquire()
                s.run = 'SAV' if s.acq_stop_after == 'SEQ' else 'RUN'
            else:
                s.run = 'STOP'
            return None
        if scpi.long_or_short_match(sub, 'STOPAfter'):
            if q:
                return s.acq_stop_after
            s.acq_stop_after = 'SEQ' if args[0].upper().startswith('SEQ') else 'RUNST'
            return None
        if scpi.long_or_short_match(sub, 'MODe'):
            return 'SAM' if q else None
        raise _Unsupported()
    # waveform transfer
    if head in ('DAT', 'DATA') and len(parts) == 2:
        sub = parts[1]
        if scpi.long_or_short_match(sub, 'SOUrce'):
            if q:
                return s.wav['source']
            if _ch(args[0]) not in s.channels:
                raise ValueError(args[0])
            s.wav['source'] = 'CH%d' % _ch(args[0])
            return None
        if scpi.long_or_short_match(sub, 'WIDth'):
            if q:
                return '%d' % int(s.wav.get('width', 1))
            w = int(args[0])
            if w not in (1, 2):
                raise ValueError(args[0])
            s.wav['width'] = w
            s.invalidate()
            return None
        if scpi.long_or_short_match(sub, 'ENCdg'):
            if q:
                return s.wav.get('encoding', 'SRI')
            enc = args[0].upper()
            if enc not in ('SRI', 'RIB', 'SRIBINARY', 'RIBINARY'):
                raise ValueError(enc)      # signed binary only; ASCII and unsigned forms are not emulated
            s.wav['encoding'] = enc[:3]
            return None
        if scpi.long_or_short_match(sub, 'STARt'):
            if q:
                return '%d' % s.wav['start']
            s.wav['start'] = max(1, int(float(args[0])))      # scopehal sends 0; Tek numbers points from 1 - both name the first sample
            return None
        if scpi.long_or_short_match(sub, 'STOP'):
            if q:
                return '%d' % s.wav['stop']
            s.wav['stop'] = int(float(args[0]))
            return None
        raise _Unsupported()
    if head in ('WFMO', 'WFMOUTPRE', 'WFMOUTPRE?') and q:
        ch = _ch(s.wav['source'])
        if ch not in s.acquired:
            s.acquire()
        a, b = s.window()
        f = s.acq_fields.get(ch) or tek_fields(s, ch)
        return preamble_text(s, ch, b - a + 1, f['x_origin'] + (a - 1) * f['x_increment'])
    if head in ('CURV', 'CURVE') and q:
        if emu.refuse_wav_data:
            return REFUSAL_UNSUPPORTED
        ch = _ch(s.wav['source'])
        if ch not in s.acquired:
            s.acquire()
        if ch not in s.acquired:
            return REFUSAL_UNSUPPORTED
        a, b = s.window()
        raw = s.acquired[ch][a - 1:b]
        wid = int(s.wav.get('width', 1))
        big = s.wav.get('encoding', 'SRI') == 'RIB'
        payload = raw.astype(('>i2' if big else '<i2') if wid == 2 else 'i1').tobytes()
        return scpi.block_encode(payload) + b'\n'
    raise _Unsupported()


def acquire_raw(state, channel, volts):
    """Signed raw for the tek dialect (the emulator calls this from acquire())."""
    f = tek_fields(state, channel)
    lim = 1 << (f['bits'] - 1)
    return np.clip(L.to_raw(volts, f), -lim, lim - 1), f
