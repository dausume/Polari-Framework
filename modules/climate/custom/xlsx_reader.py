"""
@module climate.custom.xlsx_reader

A MINIMAL, DEPENDENCY-FREE XLSX READER.

The Global Carbon Budget is published as one .xlsx and nothing
else — no CSV, no JSON API. `pandas.read_excel` needs `openpyxl`,
which is NOT installed in this image, and adding it would mean a
new pin and an image rebuild to read one file a year.

An .xlsx is a ZIP of XML, so stdlib `zipfile` + `ElementTree` is
enough. This reader does the small, well-specified part of the
format that a data table needs:

- `xl/workbook.xml` + its rels map sheet NAME -> sheet part
- `xl/sharedStrings.xml` holds every string once, by index
- a cell is `<c r="B12" t="s"><v>41</v></c>`, where t="s" means
  the value is an INDEX into the shared strings, t="inlineStr"
  means the text is inline, and no `t` means a number

It deliberately does NOT do: formulas (it reads the CACHED value,
which is what the publisher last computed — stated here because a
cached value can in principle be stale), styles, dates as dates
(a date arrives as its serial number), or merged-cell expansion.

Anything it cannot do it REFUSES by name rather than guessing.

@consumers climate.carbon_sinks_seed, climate.climate_selftest
"""

import re
import xml.etree.ElementTree as ET
import zipfile
from io import BytesIO

#: xlsx files are ZIPs; every one starts with the ZIP local file
#: header. This is the content signature an APIEndpoint row should
#: carry for an xlsx source.
XLSX_SIGNATURE = b'PK\x03\x04'

_NS = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
_REL_NS = ('{http://schemas.openxmlformats.org/officeDocument/'
           '2006/relationships}')


def looks_like_xlsx(raw):
    return bool(raw) and raw[:4] == XLSX_SIGNATURE


def _refuse(reason, saw=b''):
    head = saw[:80].decode('utf-8', errors='replace') if saw else ''
    return {'ok': False, 'refusal': reason, 'saw': head}


def _col_index(ref):
    """'BC12' -> 54 (0-based column). Cells can be sparse, so the
    column must come from the reference, never from position."""
    letters = re.match(r'([A-Z]+)', ref or '')
    if not letters:
        return None
    idx = 0
    for ch in letters.group(1):
        idx = idx * 26 + (ord(ch) - ord('A') + 1)
    return idx - 1


def _shared_strings(zf):
    try:
        raw = zf.read('xl/sharedStrings.xml')
    except KeyError:
        return []
    out = []
    for si in ET.fromstring(raw).iter(_NS + 'si'):
        # A string may be split across several <t> runs by
        # formatting; joining them is the difference between
        # 'Global Carbon Budget' and 'Global'.
        out.append(''.join(t.text or '' for t in si.iter(_NS + 't')))
    return out


def sheet_names(raw):
    """-> {'ok', 'sheets': [names], 'parts': {name: zip path}}"""
    if not looks_like_xlsx(raw):
        return _refuse(
            'not an xlsx: the payload does not start with the ZIP '
            'signature PK\\x03\\x04 (an HTML error page served with '
            'a success status looks exactly like this)', raw)
    try:
        zf = zipfile.ZipFile(BytesIO(raw))
    except Exception as exc:
        return _refuse(f'payload is not a readable ZIP: {exc}', raw)
    try:
        book = ET.fromstring(zf.read('xl/workbook.xml'))
        rels = zf.read('xl/_rels/workbook.xml.rels').decode('utf-8')
    except (KeyError, ET.ParseError) as exc:
        return _refuse(f'not a workbook (missing or bad '
                       f'xl/workbook.xml): {exc}')
    targets = dict(re.findall(
        r'Id="([^"]+)"[^>]*Target="([^"]+)"', rels))
    parts, names = {}, []
    for sheet in book.iter(_NS + 'sheet'):
        name = sheet.get('name') or ''
        target = targets.get(sheet.get(_REL_NS + 'id') or '')
        if not target:
            continue
        target = target.lstrip('/')
        if not target.startswith('xl/'):
            target = 'xl/' + target
        names.append(name)
        parts[name] = target
    if not names:
        return _refuse('workbook declares no sheets')
    return {'ok': True, 'sheets': names, 'parts': parts}


def read_sheet(raw, sheet_name, max_rows=0):
    """One sheet -> a dense list of rows of cell values.

    Values are floats where the cell is numeric and strings
    otherwise; an empty cell is None. Rows are padded to the
    widest row so callers can index by column safely.
    """
    meta = sheet_names(raw)
    if not meta.get('ok'):
        return meta
    if sheet_name not in meta['parts']:
        return {'ok': False,
                'refusal': (f'no sheet named {sheet_name!r}; the '
                            f'workbook has: '
                            f'{", ".join(meta["sheets"])}')}
    zf = zipfile.ZipFile(BytesIO(raw))
    strings = _shared_strings(zf)
    try:
        sheet = ET.fromstring(zf.read(meta['parts'][sheet_name]))
    except (KeyError, ET.ParseError) as exc:
        return {'ok': False,
                'refusal': (f'sheet {sheet_name!r} will not parse: '
                            f'{exc}')}

    rows, width = [], 0
    for row_el in sheet.iter(_NS + 'row'):
        cells = {}
        for cell in row_el.iter(_NS + 'c'):
            idx = _col_index(cell.get('r') or '')
            if idx is None:
                continue
            kind = cell.get('t')
            if kind == 'inlineStr':
                text = ''.join(
                    t.text or ''
                    for t in cell.iter(_NS + 't'))
                cells[idx] = text
                continue
            value_el = cell.find(_NS + 'v')
            if value_el is None or value_el.text is None:
                continue
            text = value_el.text
            if kind == 's':
                try:
                    cells[idx] = strings[int(text)]
                except (ValueError, IndexError):
                    cells[idx] = ''
            elif kind in ('str', 'e'):
                cells[idx] = text
            else:
                try:
                    cells[idx] = float(text)
                except ValueError:
                    cells[idx] = text
            width = max(width, idx + 1)
        rows.append(cells)
        if max_rows and len(rows) >= max_rows:
            break

    dense = [[r.get(i) for i in range(width)] for r in rows]
    return {'ok': True, 'sheet': sheet_name, 'rows': dense,
            'rowCount': len(dense), 'width': width,
            'note': ('formula cells report the publisher\'s CACHED '
                     'value; this reader does not evaluate '
                     'formulas')}


def find_header_row(rows, required, max_scan=40):
    """Locate the header row by the labels it must contain.

    Published workbooks carry a licence/citation preamble of
    varying length above the table, so the header must be found by
    CONTENT. Counting preamble lines is how a reader breaks
    silently the year the publisher adds a sentence.
    """
    want = [r.lower() for r in required]
    for i, row in enumerate(rows[:max_scan]):
        text = [str(c).strip().lower() if c is not None else ''
                for c in row]
        if all(any(w in cell for cell in text) for w in want):
            return {'ok': True, 'index': i, 'header': row}
    return {'ok': False,
            'refusal': (f'no header row containing all of '
                        f'{required} in the first {max_scan} rows '
                        f'- the publisher changed the layout, so '
                        f'the column mapping must be re-checked '
                        f'against the file before any ingest')}
