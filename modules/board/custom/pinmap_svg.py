"""
@module board.custom.pinmap_svg

demo1b (his 2026-10-04 verdict: "many rows of data with no demonstratables"): GENERATE an SVG pin map straight
from THE BOARD OBJECT's rows (board.custom.board_object.rows_for) — the four headers (Connector rows of
kind='header') as rectangles, every pin named from its ConnectorPin label (D0-D13, A0-A5, the power pins), the
underlying BoardPin's SoC pin + net on a second line, coloured by role (PWM, ADC, UART, I2C/SPI, power/ground,
plain GPIO), with a `<title>` carrying the C firmware symbol (when assigned) and the net. Pure and deterministic:
same rows -> same bytes (used both by GET /api/board/<board>/pinmap.svg and the `pol board assign` flip proof,
board_selftest.pinmap()) — change a BoardPin row (board_object.assign) and this text changes with it, same as
every other view brd-bo drives.

GENERIC across boards, not just the UNO: a board with Connector/ConnectorPin rows of kind='header' draws one
rectangle per header (the UNO's four); a board with none (e.g. esp32-c3 — ingested from Zephyr, whose dts "describes
no headers") falls back to ONE synthetic column listing every BoardPin row by its canonical name (`_layout`,
below) — so a board that is modelled AT ALL always draws its pins, never an empty legend-only box. `pins_by_role`
is the SAME per-pin role walk `render()` uses, reused by `GET /api/board/<board>/pin-roles`
(board.custom.pin_roles) so the drawing and that table never disagree on what role a pin has.
"""
from board.custom.pin_roles import ROLE_NAMES

#: colours only — the ROLE NAMES themselves (the vocabulary) live once in board.custom.pin_roles.ROLE_NAMES
ROLE_COLORS = {
    'pwm': '#e65100', 'adc': '#1565c0', 'uart': '#2e7d32', 'i2c': '#6a1b9a', 'spi': '#ad1457',
    'led': '#f9a825', 'power': '#c62828', 'ground': '#424242', 'button': '#00838f', 'gpio': '#78909c',
}
assert set(ROLE_COLORS) == set(ROLE_NAMES), 'pinmap_svg.ROLE_COLORS and pin_roles.ROLE_NAMES must name the same roles'
I2C_LABELS = {'SDA', 'SCL'}
SPI_LABELS = {'MOSI', 'MISO', 'SCK', 'COPI', 'CIPO'}
POWER_LABELS = {'+5V', '+3V3', 'VIN', 'IOREF', 'AREF', 'NC'}
GROUND_LABELS = {'GND'}
COL_W, ROW_H, PAD, HEADER_H, LEGEND_W = 170, 26, 16, 30, 150


def esc(s):
    return (str(s) if s is not None else '').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')


def role_of(label, board_pin):
    if label in I2C_LABELS:
        return 'i2c'
    if label in SPI_LABELS:
        return 'spi'
    if label in GROUND_LABELS:
        return 'ground'
    if label in POWER_LABELS:
        return 'power'
    if board_pin:
        return board_pin.get('function') or 'gpio'
    return 'gpio'


def _layout(r):
    """pins_by_canon, headers, by_conn — the one layout walk `render()` and `pins_by_role()` both use. Falls back to
    a synthetic single 'PINS' column (every BoardPin row, canonical order) when the board has no Connector/
    ConnectorPin rows of kind='header' (e.g. esp32-c3, ingested from a Zephyr dts that names none)."""
    pins_by_canon = {p['canonical']: p for p in r['pins']}
    headers = sorted([c for c in r['connectors'] if c.get('kind') == 'header'], key=lambda c: c['connector'])
    by_conn = {}
    for cp in r['connector_pins']:
        by_conn.setdefault(cp['connector'], []).append(cp)
    if not headers:
        headers = [{'connector': 'PINS', 'ref': r['board']}]
        by_conn['PINS'] = [{'connector': 'PINS', 'number': i, 'label': p['canonical'], 'board_pin': p['canonical'], 'net': p.get('net')}
                            for i, p in enumerate(r['pins'])]
    return pins_by_canon, headers, by_conn


def pins_by_role(r):
    """role -> sorted pin labels present on this board — the same role_of() walk render() colours by, reused by
    GET /api/board/<board>/pin-roles (board.custom.pin_roles.rows_for_roles) so the table and the drawing agree."""
    pins_by_canon, headers, by_conn = _layout(r)
    out = {}
    for c in headers:
        for cp in sorted(by_conn.get(c['connector'], []), key=lambda cp: cp['number']):
            bp = pins_by_canon.get(cp.get('board_pin') or '')
            role = role_of(cp['label'], bp)
            labels = out.setdefault(role, [])
            if cp['label'] not in labels:
                labels.append(cp['label'])
    return out


def render(r):
    """r = board.custom.board_object.rows_for(board)'s dict. -> the SVG document as text."""
    board = r['board']
    pins_by_canon, headers, by_conn = _layout(r)
    max_pins = max([len(by_conn.get(c['connector'], [])) for c in headers] or [1])
    width = PAD * 2 + len(headers) * (COL_W + PAD) + LEGEND_W
    height = PAD * 2 + HEADER_H + max_pins * ROW_H
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" height="%d" '
             'font-family="monospace" font-size="11">' % (width, height, width, height),
             '<title>%s pin map — generated from BoardPin/Connector rows (pol board assign changes it)</title>' % esc(board),
             '<rect x="0" y="0" width="%d" height="%d" fill="#ffffff"/>' % (width, height)]
    x = PAD
    for c in headers:
        pins = sorted(by_conn.get(c['connector'], []), key=lambda cp: cp['number'])
        box_h = HEADER_H + len(pins) * ROW_H
        parts.append('<g>')
        parts.append('<rect x="%d" y="%d" width="%d" height="%d" fill="none" stroke="#263238" stroke-width="1.5"/>'
                     % (x, PAD, COL_W, box_h))
        parts.append('<text x="%d" y="%d" font-weight="bold" text-anchor="middle">%s (%s)</text>'
                     % (x + COL_W // 2, PAD + 18, esc(c['connector']), esc(c.get('ref', ''))))
        y = PAD + HEADER_H
        for cp in pins:
            bp = pins_by_canon.get(cp.get('board_pin') or '')
            role = role_of(cp['label'], bp)
            color = ROLE_COLORS.get(role, ROLE_COLORS['gpio'])
            sym = (bp or {}).get('firmware_symbol') or ''
            net = cp.get('net') or (bp or {}).get('net') or ''
            soc_pin = (bp or {}).get('soc_pin') or ''
            title = ('%s: ' % sym if sym else '') + 'net=%s' % (net or '-')
            parts.append('<g>')
            parts.append('<title>%s</title>' % esc(title))
            parts.append('<rect x="%d" y="%d" width="%d" height="%d" fill="%s" fill-opacity="0.16" stroke="%s"/>'
                         % (x, y, COL_W, ROW_H, color, color))
            parts.append('<text x="%d" y="%d" font-weight="bold">%s</text>' % (x + 6, y + 11, esc(cp['label'])))
            parts.append('<text x="%d" y="%d" font-size="9" fill="#37474f">%s</text>'
                         % (x + 6, y + 22, esc('%s / %s' % (soc_pin or '-', net or '-'))))
            parts.append('</g>')
            y += ROW_H
        parts.append('</g>')
        x += COL_W + PAD
    ly = PAD
    parts.append('<g font-size="10">')
    for i, role in enumerate(sorted(ROLE_COLORS)):
        yy = ly + i * 15
        color = ROLE_COLORS[role]
        parts.append('<rect x="%d" y="%d" width="10" height="10" fill="%s" fill-opacity="0.4" stroke="%s"/>' % (x, yy, color, color))
        parts.append('<text x="%d" y="%d">%s</text>' % (x + 14, yy + 9, role))
    parts.append('</g>')
    parts.append('</svg>')
    return ''.join(parts)
