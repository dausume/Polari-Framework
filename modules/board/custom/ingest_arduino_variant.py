"""
@module board.custom.ingest_arduino_variant

ARDUINO SAMD VARIANT -> ROWS (bob-5, 2026-10-30): read the pin table an Arduino SAMD core variant carries at the top of its `variant.cpp` (stored verbatim
under board/custom/upstream/) into one dict per row - never retyped. The table is the core's own documentation of `g_APinDescription[]`:

  | <Arduino pin number> | <board pin> | <PAnn / PBnn> | <label> | <functions, * = the default peripheral in use, + = an alternative the core uses>

A row with no Arduino pin number (5V0, RESET, GND on the legacy ICSP block) is kept with number None. Each row cites file:line.
"""
import hashlib
import re

ROW = re.compile(r'^\s*\*\s*\|(.*)$')
PORT = re.compile(r'^P[AB]\d{2}$')


def _functions(text):
    """'EIC/EXTINT[11] ADC/AIN[19] *SERCOM0/PAD[3]' -> (['EIC/EXTINT[11]', 'ADC/AIN[19]', 'SERCOM0/PAD[3]'], 'SERCOM0/PAD[3]')."""
    out, default = [], ''
    for tok in text.split():
        if '/' not in tok and '[' not in tok:
            continue
        clean = tok.lstrip('*+')
        if tok.startswith('*') and not default:
            default = clean
        if clean not in out:
            out.append(clean)
    return out, default


def parse(text, path='variant.cpp'):
    """-> [{'number': int | None, 'board_pin', 'port_pin', 'label', 'functions': [...], 'default', 'cite'}] in table order."""
    rows = []
    for ln, line in enumerate(text.splitlines(), 1):
        m = ROW.match(line)
        if not m:
            continue
        cells = [c.strip() for c in m.group(1).split('|')]
        if len(cells) < 4 or cells[0].startswith('Pin number'):
            continue
        num, board_pin, port, label = cells[0], cells[1], cells[2], cells[3]
        funcs, default = _functions(cells[4] if len(cells) > 4 else '')
        if not (port and PORT.match(port)) and not label:
            continue   # a section heading row (| | Digital Low | ...)
        rows.append({'number': int(num) if num.isdigit() else None, 'board_pin': board_pin, 'port_pin': port if PORT.match(port or '') else '',
                     'label': label, 'functions': funcs, 'default': default, 'cite': '%s:%d' % (path, ln)})
    return rows


def sha256(text):
    return hashlib.sha256(text.encode()).hexdigest()
