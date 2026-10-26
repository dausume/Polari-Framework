"""
@module instruments.custom.lineage

osc-1 (OSCILLOSCOPE_PLAN.md §0, D-osc-3): the two vendor PREAMBLE conventions mapped onto ONE canonical capture (the WaveformCapture fields)
and the two formulas that turn raw samples back into volts and times. Pure functions; numpy only for the sample arrays.

  AGILENT lineage (Keysight; Rigol adopted it — cited to scopehal RigolOscilloscope.cpp, the DHO branch):
      :WAVeform:PREamble?  ->  format,type,points,count,xincrement,xorigin,xreference,yincrement,yorigin,yreference
      V = (raw - yorigin - yreference) * yincrement          t = (i - xreference) * xincrement + xorigin
      format 0 = BYTE, 1 = WORD, 2 = ASCii ; type 0 = NORMal, 1 = MAXimum, 2 = RAW   (the Rigol DS/DHO guides' encoding; unverified for the DHO
      guide itself, which was not read — the emulator uses it and the client does not depend on it: it carries `format` as the word it set)
  TEKTRONIX lineage (cited to the field names of WFMOutpre? as every Tek programmer manual lists them; no Tek document read for this slice,
  so the adapter is driven by NAMED fields a later slice fills from a real `WFMOutpre?` reply):
      YOFf -> y_reference, YMUlt -> y_increment, YZEro -> y_origin, PT_Off -> x_reference, XINcr -> x_increment, XZEro -> x_origin, NR_Pt -> points
      V = (raw - YOFf) * YMUlt + YZEro                        t = (i - PT_Off) * XINcr + XZEro

  parse_agilent_preamble(text) -> dict(points, format, type, count, x_increment, x_origin, x_reference, y_increment, y_origin, y_reference, lineage)
  format_agilent_preamble(fields) -> the ten-field text (the emulator's reply)
  from_tek_fields({'XINcr':.., 'XZEro':.., 'PT_Off':.., 'YMUlt':.., 'YOFf':.., 'YZEro':.., 'NR_Pt':..}) -> the same canonical dict (lineage tektronix)
  samples(payload, fmt) -> int array (BYTE: uint8; WORD: little-endian uint16 — scopehal reinterprets the DHO buffer as native LE with no swap)
  volts(raw, fields) / times(n, fields) -> float arrays by the lineage's formula
"""
import numpy as np

FORMAT_CODES = {0: 'BYTE', 1: 'WORD', 2: 'ASCII'}
TYPE_CODES = {0: 'NORMAL', 1: 'MAXIMUM', 2: 'RAW'}
_AGILENT_ORDER = ('format', 'type', 'points', 'count', 'x_increment', 'x_origin', 'x_reference', 'y_increment', 'y_origin', 'y_reference')


def parse_agilent_preamble(text):
    parts = [p.strip() for p in str(text).strip().split(',')]
    if len(parts) != 10:
        raise ValueError('an Agilent-lineage preamble has 10 fields, got %d: %r' % (len(parts), text))
    fmt, typ, points, count = int(float(parts[0])), int(float(parts[1])), int(float(parts[2])), int(float(parts[3]))
    xi, xo, xr, yi, yo, yr = (float(p) for p in parts[4:])
    return {'format': FORMAT_CODES.get(fmt, 'unverified'), 'type': TYPE_CODES.get(typ, 'unverified'), 'points': points, 'count': count,
            'x_increment': xi, 'x_origin': xo, 'x_reference': xr, 'y_increment': yi, 'y_origin': yo, 'y_reference': yr,
            'lineage': 'agilent', 'preamble_text': str(text).strip()}


def format_agilent_preamble(f):
    fmt = {v: k for k, v in FORMAT_CODES.items()}[f.get('format', 'WORD')]
    typ = {v: k for k, v in TYPE_CODES.items()}[f.get('type', 'RAW')]
    return '%d,%d,%d,%d,%.12e,%.12e,%.12e,%.12e,%.12e,%.12e' % (fmt, typ, int(f['points']), int(f.get('count', 1)), f['x_increment'], f['x_origin'],
                                                              f['x_reference'], f['y_increment'], f['y_origin'], f['y_reference'])


def from_tek_fields(t):
    need = ('XINcr', 'XZEro', 'PT_Off', 'YMUlt', 'YOFf', 'YZEro', 'NR_Pt')
    missing = [k for k in need if k not in t]
    if missing:
        raise ValueError('Tektronix WFMOutpre fields missing: %s' % ', '.join(missing))
    byt = int(t.get('BYT_Nr', 1))
    return {'format': 'WORD' if byt == 2 else 'BYTE', 'type': 'RAW', 'points': int(t['NR_Pt']), 'count': 1,
            'x_increment': float(t['XINcr']), 'x_origin': float(t['XZEro']), 'x_reference': float(t['PT_Off']),
            'y_increment': float(t['YMUlt']), 'y_origin': float(t['YZEro']), 'y_reference': float(t['YOFf']),
            'lineage': 'tektronix', 'preamble_text': ';'.join('%s %s' % (k, t[k]) for k in need + (('BYT_Nr',) if 'BYT_Nr' in t else ()))}


def samples(payload, fmt='WORD'):
    if fmt == 'WORD':
        if len(payload) % 2:
            raise ValueError('a WORD payload has an even byte count, got %d' % len(payload))
        return np.frombuffer(payload, dtype='<u2').astype(np.int64)
    if fmt == 'BYTE':
        return np.frombuffer(payload, dtype=np.uint8).astype(np.int64)
    raise ValueError('samples() reads BYTE or WORD payloads, not %r' % fmt)


def volts(raw, f):
    raw = np.asarray(raw, dtype=np.float64)
    if f.get('lineage') == 'tektronix':
        return (raw - f['y_reference']) * f['y_increment'] + f['y_origin']
    return (raw - f['y_origin'] - f['y_reference']) * f['y_increment']


def times(n, f):
    i = np.arange(int(n), dtype=np.float64)
    return (i - f['x_reference']) * f['x_increment'] + f['x_origin']


def to_raw(v, f):
    """The inverse of volts() — what the emulator writes for a wanted voltage (rounded to the nearest level)."""
    v = np.asarray(v, dtype=np.float64)
    if f.get('lineage') == 'tektronix':
        return np.rint((v - f['y_origin']) / f['y_increment'] + f['y_reference']).astype(np.int64)
    return np.rint(v / f['y_increment'] + f['y_origin'] + f['y_reference']).astype(np.int64)
