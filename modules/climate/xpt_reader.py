"""
@module climate.xpt_reader

THE SAS XPORT (.xpt) READ PATH — the format CDC publishes NHANES
lab data in (CO2_HEALTH_PLAN.md, xpt-1). Bicarbonate (LBXSC3SI in
BIOPRO_*.XPT) is the population biomarker the CO2/health study
stands on, and it arrives as a 1970s IBM-mainframe binary.

⚠ THE REASON THIS FILE VALIDATES BEFORE IT PARSES: wwwn.cdc.gov
answers retired NHANES paths with HTTP 200 and a 'Page Not Found'
HTML page (observed 2026-08-02: two different retired URLs, both
200, both a byte-identical 20905-byte webpage). A reader that
trusts its input therefore ingests a webpage as a lab result, and
`pandas.read_sas` raises a traceback from inside an API handler,
blaming the parser for a routing problem three layers up. So the
first 80 bytes are checked against XPORT_SIGNATURE and the refusal
QUOTES what actually arrived.

THE READER NEVER GUESSES WHAT A COLUMN MEANS. NHANES column names
are opaque ('LBXSC3SI', 'LBDSBUSI'); meaning and unit come from a
caller-supplied `column_map` built from the published codebook.
Columns with no entry are REPORTED as unmapped, never dropped —
an unmapped column is a gap in the codebook row, and silence about
it is how a unit error survives to a chart.

`make_min_xport` writes a minimal but genuinely valid XPORT v5
file in pure Python (IBM 360 hex floats included) so the selftest
round-trips without a network call or a checked-in binary blob.

@consumers climate.series_ingest, climate.co2_health,
climate.climate_api, tests.selftest_climate
"""

import io
import math
import struct

#: The first 41 bytes of every SAS XPORT v5 library. Anything that
#: does not start with this is not the format, whatever the HTTP
#: status said.
XPORT_SIGNATURE = b'HEADER RECORD*******LIBRARY HEADER RECORD'

#: How much of a rejected body to quote back. One 80-byte record —
#: enough to read '<!DOCTYPE html>' or a proxy error banner.
HEAD_QUOTE_BYTES = 80

#: How far in to look for an HTML tell. Some error pages open with
#: a comment or a BOM before the doctype.
HTML_PROBE_BYTES = 200

#: XPORT v5 fixed record size. Everything is 80-byte cards.
RECORD_SIZE = 80

#: Bytes per NAMESTR descriptor (the member header declares 140).
NAMESTR_SIZE = 140

_LIB_HEADER = (b'HEADER RECORD*******LIBRARY HEADER RECORD!!!!!!!'
               b'000000000000000000000000000000  ')
_MEMBER_HEADER = (b'HEADER RECORD*******MEMBER  HEADER RECORD!!!!!!!'
                  b'000000000000000001600000000140  ')
_DSCRPTR_HEADER = (b'HEADER RECORD*******DSCRPTR HEADER RECORD!!!!!!!'
                   b'000000000000000000000000000000  ')
_NAMESTR_PREFIX = (b'HEADER RECORD*******NAMESTR HEADER RECORD'
                   b'!!!!!!!')
_OBS_HEADER = (b'HEADER RECORD*******OBS     HEADER RECORD!!!!!!!'
               b'000000000000000000000000000000  ')

#: Fixed timestamp for generated fixtures. Deterministic on
#: purpose: a fixture whose sha256 changes every run cannot be
#: cited in a provenance row.
FIXTURE_DATETIME = '01JAN70:00:00:00'

_NAMESTR_FORMAT = '>hhhh8s40s8shhh2s8shhl52s'


def looks_like_xport(raw):
    """True iff `raw` opens with the XPORT library signature."""
    if not raw:
        return False
    return bytes(raw[:len(XPORT_SIGNATURE)]) == XPORT_SIGNATURE


def _head_quote(raw):
    """The opening bytes, made readable without pretending they
    decoded cleanly."""
    return bytes(raw[:HEAD_QUOTE_BYTES]).decode(
        'utf-8', errors='replace')


def _looks_like_html(raw):
    """Cheap tell for an error page served with a success code."""
    probe = bytes(raw[:HTML_PROBE_BYTES])
    if probe[:1] == b'<':
        return True
    return b'<!doctype' in probe.lower()


def _body_refusal(raw):
    """Name what arrived instead of an XPORT file, and what would
    retire the refusal."""
    n = len(raw)
    head = _head_quote(raw)
    if _looks_like_html(raw):
        return ('this is an HTML page, not a SAS XPORT file (the '
                'source served an error page with a success '
                'status); {n} bytes, first {h} decoded: {q!r}; '
                'retired by pointing the endpoint at a live .xpt '
                'path — check the NHANES cycle letter, retired '
                'paths still answer 200'.format(
                    n=n, h=HEAD_QUOTE_BYTES, q=head))
    return ('body does not start with the SAS XPORT signature '
            '{sig!r}; {n} bytes, first {h} decoded: {q!r}; '
            'retired by supplying the .xpt file itself (not a '
            'landing page, not a zip, not a gzip stream)'.format(
                sig=XPORT_SIGNATURE, n=n, h=HEAD_QUOTE_BYTES,
                q=head))


def read_xpt_bytes(raw, column_map=None, max_rows=0):
    """Parse XPORT bytes into a DataFrame, or refuse.

    `column_map` is {column: {'meaning': str, 'unit': str}} taken
    from the published codebook. Nothing here infers meaning.
    """
    if raw is None or len(raw) == 0:
        return {'ok': False, 'refusal': (
            'empty body (0 bytes); retired by a fetch that '
            'actually returned the file — an empty 200 is a '
            'proxy or a truncated download, not a data set')}
    if len(raw) < RECORD_SIZE:
        return {'ok': False, 'refusal': (
            'body is {n} bytes, shorter than one 80-byte XPORT '
            'record, so it cannot even carry a header; decoded: '
            '{q!r}; retired by fetching the whole file'.format(
                n=len(raw), q=_head_quote(raw)))}
    if not looks_like_xport(raw):
        return {'ok': False, 'refusal': _body_refusal(raw)}

    try:
        import pandas
    except ImportError as exc:
        return {'ok': False, 'refusal': (
            'pandas is not importable ({e}), and XPORT parsing '
            'needs pandas.read_sas; retired by installing '
            'pandas (it is listed in requirements.txt)'.format(
                e=exc))}

    try:
        frame = pandas.read_sas(io.BytesIO(bytes(raw)),
                                format='xport')
    except Exception as exc:
        return {'ok': False, 'refusal': (
            'pandas.read_sas rejected a body that DID carry the '
            'XPORT signature: {t}: {e}; retired by re-fetching '
            '(a truncated or partially-written .xpt reads as '
            'valid at byte 0)'.format(
                t=type(exc).__name__, e=exc))}

    columns = [str(c) for c in frame.columns]
    cmap = dict(column_map or {})
    mapped = {c: cmap[c] for c in columns if c in cmap}
    unmapped = [c for c in columns if c not in cmap]

    truncated = False
    if max_rows and max_rows > 0 and len(frame) > max_rows:
        frame = frame.head(max_rows)
        truncated = True

    result = {
        'ok': True,
        'rowCount': int(len(frame)),
        'columns': columns,
        'mappedColumns': mapped,
        'unmappedColumns': unmapped,
        'frame': frame,
    }
    if truncated:
        result['truncated'] = True
    return result


def read_xpt_fetch(fetch_result, column_map=None, max_rows=0):
    """Read the body a `fetch_endpoint` retrieval carries.

    An upstream refusal passes through VERBATIM. A surface that
    rewords the layer below it hides which layer actually failed.
    """
    if not isinstance(fetch_result, dict):
        return {'ok': False, 'refusal': (
            'expected the dict returned by '
            'polariApiProfiler.endpoint_fetch.fetch_endpoint, '
            'got {t}; retired by passing the retrieval '
            'unchanged'.format(t=type(fetch_result).__name__))}
    if not fetch_result.get('ok'):
        return {'ok': False,
                'refusal': fetch_result.get('refusal')}

    out = read_xpt_bytes(fetch_result.get('body'),
                         column_map=column_map,
                         max_rows=max_rows)
    out['sha256'] = fetch_result.get('sha256')
    out['urlRedacted'] = fetch_result.get('url_redacted')
    return out


def column_summary(frame, column, drop_sentinels=()):
    """Summary stats for one numeric column.

    `drop_sentinels` are treated as missing BEFORE anything is
    computed — some NHANES questionnaire files code refused /
    don't-know as 7777 / 9999, and averaging those in moves a
    mean by hundreds. Lab files usually carry none, so the
    default drops nothing and says so by doing nothing.
    """
    if frame is None:
        return {'ok': False, 'refusal': (
            'no frame given; retired by passing the "frame" from '
            'a successful read_xpt_bytes result')}
    try:
        available = [str(c) for c in frame.columns]
    except Exception as exc:
        return {'ok': False, 'refusal': (
            'object has no .columns ({t}: {e}); retired by '
            'passing a DataFrame'.format(
                t=type(exc).__name__, e=exc))}

    if column not in available:
        shown = available[:20]
        more = len(available) - len(shown)
        tail = ' (+{n} more)'.format(n=more) if more > 0 else ''
        return {'ok': False, 'refusal': (
            'column {c!r} is not in this file; available: '
            '{a}{tail}; retired by naming a column the codebook '
            'lists for THIS cycle — NHANES renames columns '
            'between cycles'.format(c=column, a=shown, tail=tail))}

    try:
        series = frame[column]
        if drop_sentinels:
            series = series.where(~series.isin(list(drop_sentinels)))
        series = series.astype('float64').dropna()
    except Exception as exc:
        return {'ok': False, 'refusal': (
            'column {c!r} is not numeric ({t}: {e}); retired by '
            'summarising a numeric lab column, or by decoding '
            'the character column first'.format(
                c=column, t=type(exc).__name__, e=exc))}

    n = int(len(series))
    if n == 0:
        dropped = list(drop_sentinels)
        return {'ok': False, 'refusal': (
            'column {c!r} has zero non-null values after '
            'dropping sentinels {d}; retired by a cycle whose '
            'participants were actually assayed for it, or by a '
            'shorter sentinel list if the values were real'
            .format(c=column, d=dropped))}

    def _r(value):
        return round(float(value), 6)

    return {
        'ok': True,
        'column': column,
        'n': n,
        'mean': _r(series.mean()),
        'std_dev': _r(series.std()),
        'median': _r(series.median()),
        'pct_5': _r(series.quantile(0.05)),
        'pct_95': _r(series.quantile(0.95)),
        'min': _r(series.min()),
        'max': _r(series.max()),
        'droppedSentinels': list(drop_sentinels),
    }


def _ieee_to_ibm(value):
    """One IEEE double -> 8 bytes of IBM 360 hex floating point.

    IBM floats are base-16: value = 0.f * 16**(E-64). frexp gives
    a base-2 exponent, so the mantissa is shifted until the
    exponent is a multiple of 4 and the remainder becomes the hex
    exponent.

    NOTE 0.0 is written as eight zero bytes — what SAS itself
    writes. pandas' vectorised decoder has no zero case and hands
    those back as ~5.4e-79 (2**-260), so a stored zero reads as
    5.4e-79, not 0.0. That is pandas' behaviour on EVERY real
    .xpt, not an artifact of this writer; do not "fix" it here.
    """
    v = float(value)
    if v == 0.0 or v != v:
        return b'\x00' * 8
    sign = 0x80 if v < 0 else 0x00
    m, e = math.frexp(abs(v))
    while e % 4:
        e += 1
        m /= 2.0
    exponent = e // 4 + 64
    mantissa = int(round(m * (1 << 56)))
    if mantissa >= (1 << 56):
        mantissa >>= 4
        exponent += 1
    if exponent < 0 or exponent > 127:
        return b'\x00' * 8
    return bytes([sign | exponent]) + mantissa.to_bytes(7, 'big')


def _pad80(raw):
    """Pad a byte block out to the next 80-byte card with spaces."""
    remainder = len(raw) % RECORD_SIZE
    if remainder == 0:
        return raw
    return raw + b' ' * (RECORD_SIZE - remainder)


def _fixed(text, width):
    """ASCII, space-padded, hard-truncated to `width`."""
    data = str(text).encode('ascii', errors='replace')
    return data[:width].ljust(width, b' ')


def _namestr(index, name):
    """One 140-byte NAMESTR for an 8-byte numeric variable."""
    block = struct.pack(
        _NAMESTR_FORMAT,
        1,                       # ntype: 1 = numeric
        0,                       # nhfun: no hash
        8,                       # nlng: 8-byte IBM double
        index + 1,               # nvar0: variable number
        _fixed(name, 8),         # nname
        b' ' * 40,               # nlabel
        b' ' * 8,                # nform
        0, 0, 0,                 # nfl, nfd, nfj
        b'  ',                   # nfill
        b' ' * 8,                # niform
        0, 0,                    # nifl, nifd
        index * 8,               # npos: byte offset in the record
        b' ' * 52,               # trailing pad
    )
    return block


def make_min_xport(columns, rows, dsname='POLARI'):
    """Build a minimal but VALID XPORT v5 file in pure Python.

    Exists so the selftest can round-trip the reader with no
    network call and no checked-in binary fixture — a fixture you
    cannot regenerate is a fixture nobody can audit.

    `columns` are variable names (<= 8 ASCII chars); `rows` are
    lists of floats, one list per observation. Returns bytes.

    This is a fixture builder, not a request surface: malformed
    fixture arguments raise ValueError, because a test that
    silently built the wrong file would prove nothing. Callers on
    a request path should use `build_min_xport`, which carries the
    ok/refusal contract.
    """
    names = [str(c) for c in (columns or [])]
    if not names:
        raise ValueError('make_min_xport needs at least 1 column')
    for name in names:
        if len(name) > 8:
            raise ValueError(
                'XPORT v5 variable names are <= 8 chars: '
                '{n!r}'.format(n=name))
    n_vars = len(names)

    stamp = FIXTURE_DATETIME.encode('ascii')
    out = bytearray()

    # --- library header -------------------------------------
    out += _LIB_HEADER
    out += (_fixed('SAS     SAS     SASLIB  9.1     bsd4.2  ', 40)
            + b' ' * 24 + stamp)
    out += (stamp + b' ' * 64)

    # --- member / descriptor headers -------------------------
    out += _MEMBER_HEADER
    out += _DSCRPTR_HEADER
    out += (_fixed('SAS', 8) + _fixed(dsname, 8)
            + _fixed('SASDATA', 8) + _fixed('9.1', 8)
            + _fixed('bsd4.2', 8) + b' ' * 24 + stamp)
    out += (stamp + b' ' * 16 + b' ' * 40 + _fixed('', 8))

    # --- NAMESTR block ---------------------------------------
    # pandas reads the variable count from bytes 54:58, so the
    # six zeros before it are not decoration.
    out += (_NAMESTR_PREFIX + b'000000'
            + ('%04d' % n_vars).encode('ascii')
            + b'0' * 20 + b'  ')
    namestrs = bytearray()
    for index, name in enumerate(names):
        block = _namestr(index, name)
        if len(block) != NAMESTR_SIZE:
            raise ValueError(
                'NAMESTR is {n} bytes, must be {m}'.format(
                    n=len(block), m=NAMESTR_SIZE))
        namestrs += block
    out += _pad80(bytes(namestrs))

    # --- observations ----------------------------------------
    out += _OBS_HEADER
    values = bytearray()
    for row_index, row in enumerate(rows or []):
        if len(row) != n_vars:
            raise ValueError(
                'row {i} has {n} values, expected {m}'.format(
                    i=row_index, n=len(row), m=n_vars))
        for value in row:
            values += _ieee_to_ibm(value)
    out += _pad80(bytes(values))

    if len(out) % RECORD_SIZE:
        raise ValueError(
            'built file is {n} bytes, not a multiple of '
            '{m}'.format(n=len(out), m=RECORD_SIZE))
    return bytes(out)


def build_min_xport(columns, rows, dsname='POLARI'):
    """`make_min_xport` with the ok/refusal contract, for any
    caller that is not a test."""
    try:
        raw = make_min_xport(columns, rows, dsname=dsname)
    except Exception as exc:
        return {'ok': False, 'refusal': (
            'could not build an XPORT fixture ({t}: {e}); '
            'retired by <= 8-char ASCII column names and rows '
            'that all have one float per column'.format(
                t=type(exc).__name__, e=exc))}
    return {'ok': True, 'bytes': raw, 'byteCount': len(raw),
            'columns': [str(c) for c in columns],
            'rowCount': len(rows or [])}
