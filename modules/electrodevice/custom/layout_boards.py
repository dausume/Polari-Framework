"""
@module electrodevice.custom.layout_boards

c3g-5 (AI-Notes/plans/C3_SESSION_PLAN.md section 6): THE ONE TABLE OF LAYOUT FACTS PER BOARD, keyed by a config's `board_definition`. The layout engine names no board itself: the circuit rows, the
bench board the wires start from, the pin label, the supply label, the connectors, where a pin sits and the words for the board all come from a row here. A third board is a row (and its
twin facts in board.custom.twin_kinds), not code. The twin's own facts per chip (pad name, release, clock, ADC) live in twin_kinds; this table holds only what the picture and the steps need.

  arduino-uno-r3   circuit uno-button-clock, header board bench-uno-1, pins D<n>, supply +5V; connectors = board.custom.board_uno.CONNECTORS (five)
  esp32-c3         circuit c3-light, header board bench-c3-1, pins GPIO<n>, supply 3V3; connectors J1 and J3 = board.custom.board_c3.HEADERS (the ESP32-C3-DevKitM-1 user guide, cited there)

`board.*` is imported lazily, inside the functions, so electrodevice loads without the board module.
"""
from electrodevice.custom.layout_words import LayoutRefused

UNO, C3 = 'arduino-uno-r3', 'esp32-c3'
BOARDS = {
    # adc_max_mv: the top of the range the board's TWIN takes on an analog input (the UNO twin: 0..5000 mV); 0 = its twin has no analog input yet (the C3's pin model holds levels only)
    UNO: {'circuit': 'uno-button-clock', 'header_board': 'bench-uno-1', 'pin': 'D%d', 'supply': '+5V', 'said': 'the UNO', 'adc_max_mv': 5000},
    C3: {'circuit': 'c3-light', 'header_board': 'bench-c3-1', 'pin': 'GPIO%d', 'supply': '3V3', 'said': 'the ESP32-C3 dev kit', 'adc_max_mv': 0},
}


def of(board_definition):
    """The row of a board, or a LayoutRefused naming the boards a layout can be built for."""
    row = BOARDS.get(board_definition or UNO)
    if row is None:
        raise LayoutRefused("a layout cannot be built for the board %s yet: it can be built for %s" % (board_definition, ', '.join(sorted(BOARDS))))
    return dict(row, board=board_definition or UNO)


def default_knobs(board):
    """The knob defaults of the board's light config (board.custom.variants.DEFAULT_KNOBS; the C3's: variants_c3.LIGHT_KNOBS)."""
    of(board)
    if board == C3:
        from board.custom import variants_c3
        return dict(variants_c3.LIGHT_KNOBS)
    from board.custom import variants
    return dict(variants.DEFAULT_KNOBS)


def connectors(board):
    """-> [{name, ref, labels, order}] the board's header connectors in pin order (the C3's also carry `silk`, what is printed beside each pin)."""
    of(board)
    if board == C3:
        from board.custom import board_c3
        order = 'pin numbers as the "Header Block" tables of the %s list them (%s)' % (board_c3.UG_DOC, board_c3.UG_REV)
        return [{'name': n, 'ref': n, 'labels': [board_c3.header_gpio(s) or s for s in silk], 'silk': list(silk), 'order': order} for n, silk in board_c3.HEADERS.items()]
    from board.custom import board_uno
    return [{'name': n, 'ref': ref, 'labels': list(labels), 'order': order} for n, (ref, _k, _fp, labels, order) in board_uno.CONNECTORS.items()]


def power_labels(board):
    """The header labels that are not BoardPins: the UNO's = every connector label except NC; the C3's = the HEADERS labels with no GPIO (GND 3V3 5V RST)."""
    try:
        conns = connectors(board)
    except (LayoutRefused, ImportError):
        return frozenset()
    if board == C3:
        return frozenset(s for c in conns for l, s in zip(c['labels'], c['silk']) if l == s)
    return frozenset(l for c in conns for l in c['labels'] if l != 'NC')


def pin_where(board, label, board_pin_row):
    """'DIGITAL_L header, pin 7' (the UNO); 'J1 header, pin 9 (printed IO0)' (the C3). A power label sits where it first appears in the connectors; the BoardPin row says where a GPIO sits."""
    conns = connectors(board)
    if board_pin_row and board_pin_row.get('connector_pin'):
        c, _, n = board_pin_row['connector_pin'].partition(':')
        silk = next((x['silk'][int(n) - 1] for x in conns if x['name'] == c and 'silk' in x), '')
        return '%s header, pin %s%s' % (c, n, ' (printed %s)' % silk if silk and silk != label else '')
    for c in conns:
        if label in c['labels']:
            i = c['labels'].index(label)
            return '%s header, pin %d%s' % (c['name'], i + 1, ' (printed %s)' % c['silk'][i] if 'silk' in c and c['silk'][i] != label else '')
    return 'the %s header' % board


def twin_pin(board, label):
    """The twin's pad name of a header label: 'D6' -> 'PD6' (the UNO); a GPIO<n> BoardPin is its own pad on the C3; else ''."""
    if board == C3:
        from board.custom import board_object
        return label if label in {p['canonical'] for p in board_object.rows_for(C3)['pins']} else ''
    from board.custom import board_uno
    row = board_uno.D_PINS.get(label) or board_uno.A_PINS.get(label)
    return row[0] if row else ''


def adc_channel(board, label):
    """The ADC channel of an analog header label (A0 -> 0); the C3's twin has no analog input, so None."""
    if not BOARDS.get(board, BOARDS[UNO])['adc_max_mv']:
        return None
    from board.custom import board_uno
    row = board_uno.A_PINS.get(label)
    return row[1] if row else None


def notes(board, components):
    """The notes a board adds to a design. The UNO adds none. The C3: no board on the bench (the reference board, cited), and the LED current at the C3's 3.3 V."""
    if board != C3:
        return []
    from board.custom import board_c3
    out = ["No ESP32-C3 board is on the bench: this layout is the design drawn on the headers of the ESP32-C3-DevKitM-1, the reference board. Check a real board's header order before wiring one. Header source: %s, %s."
           % (board_c3.UG_DOC, board_c3.UG_REV)]
    led = next((c for c in components if c['kind'] == 'led' and c['params'].get('v_forward') is not None), None)
    res = next((c for c in components if c['kind'] == 'resistor' and c['params'].get('ohms')), None)
    if led and res:
        vdd, vf, ohms = board_c3.POWER['3V3'][2], float(led['params']['v_forward']), float(res['params']['ohms'])
        out.append("With the pad high at the board's %.1f V supply, the LED's current is at most (%.1f V - %.1f V) / %g ohm = about %.1f mA. The forward voltage is %s (%s), and the pad's drive limit is not cited here."
                   % (vdd, vdd, vf, ohms, (vdd - vf) / ohms * 1000, led['params'].get('v_forward_basis', 'not stated'), led['row']))
    return out
