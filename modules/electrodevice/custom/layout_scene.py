"""
@module electrodevice.custom.layout_scene

lay-2: THE SCENE the N-board renderer (`hardware-layout-view`) draws, derived from the layout and sent beside it (key `scene` of GET /api/layout/<config>), so the browser
holds no part knowledge of its own:

  boards   every board of the picture, in drawing order (the development board first, then the bench board): kind, geometry numbers (rows, holes per side, rail holes, pitch)
           and, for a development board, its header connectors (labels in pin order, from board.custom.board_uno.CONNECTORS - nothing is stored here);
  parts    per placed part: the sprite kind, the INTERACTION it offers and the OUTPUT it shows, both DERIVED from the KitPart row (D-hbc-3: no per-part UI code);
  pins     the board's header label -> the twin's port pin name (D6 -> PD6) and the ADC channel of an analog pin (A0 -> 0);
  watch    every twin pin the layout drives an output on (the LED's pin), which the sim bench asks the session to watch.

Interaction kinds (the browser draws exactly these, whatever the part):
  press    a momentary switch (KitPart interface digital-in, the pushbutton): holding it drives `pin` to `pressed_level` (the level the switch's other side sits at), releasing it to the opposite
  toggle   a latching switch (digital-in, the tilt sensor): on = `pressed_level`
  slider   an analog source (analog-in): the value `x` in `unit` between min and max becomes `mv = offset_mv + per_unit_mv * x` on ADC channel `adc`
             potentiometer   x in % of the turn, 0-100, 0 mV at 0 % and 5000 mV at 100 % (the book: "0-5V at the wiper when the ends are at 5V/GND"; the twin accepts 0..5000 mV)
             TMP36           x in degrees C, -40..125, mv = 500 + 10 * x (the Analog Devices TMP35/36/37 datasheet's output scale: 10 mV/degC, 500 mV at 0 degC, 750 mV at 25 degC; the same two
                             numbers as board.custom.uno_facts tmp36.scale / tmp36.offset - that datasheet was NOT re-fetched on this machine, uno_facts.TMP36_REV says so)
A part whose KitPart has no interaction kind gets none and draws as a plain sprite. Photoresistor (analog-in) has no interaction here: its voltage depends on the divider it is wired in, which
this layer does not know (said, not guessed).
Output kinds: led (lit by the level of the pin that drives it through any series resistor), tone (a piezo on a digital-out pin).
"""
#: (KitPart interface_kind, kit key) -> the interaction. The ONE table; adding a part kind is a row here, never browser code.
INTERACTIONS = {
    ('digital-in', 'pushbutton'): {'control': 'press', 'label': 'Press and hold'},
    ('digital-in', 'tilt-sensor'): {'control': 'toggle', 'label': 'Tilt'},
    ('analog-in', 'potentiometer'): {'control': 'slider', 'label': 'Turn the knob', 'unit': '%', 'min': 0, 'max': 100, 'step': 1, 'initial': 50, 'offset_mv': 0, 'per_unit_mv': 50,
                                     'basis': '0-5 V at the wiper with the ends on 5 V and GND (Arduino Starter Kit book); 0 % = 0 mV, 100 % = 5000 mV'},
    ('analog-in', 'tmp36'): {'control': 'slider', 'label': 'Temperature', 'unit': '°C', 'min': -40, 'max': 125, 'step': 1, 'initial': 25, 'offset_mv': 500, 'per_unit_mv': 10,
                             'basis': 'TMP36: 10 mV per °C with 500 mV at 0 °C (Analog Devices TMP35/36/37 datasheet: 750 mV at 25 °C); datasheet not re-fetched here'},
}
#: (KitPart interface_kind, kit key) -> the output a part shows
OUTPUTS = {('digital-out', 'led'): 'led', ('digital-out', 'piezo'): 'tone'}
ADC_MAX_MV = 5000


def twin_pin(label):
    """'D6' -> 'PD6', 'A0' -> 'PC0', anything that is not a port pin of the UNO -> ''."""
    try:
        from board.custom import board_uno
    except Exception:   # noqa: BLE001 - the board module is optional here
        return ''
    row = board_uno.D_PINS.get(label) or board_uno.A_PINS.get(label)
    return row[0] if row else ''


def adc_channel(label):
    try:
        from board.custom import board_uno
    except Exception:   # noqa: BLE001
        return None
    row = board_uno.A_PINS.get(label)
    return row[1] if row else None


def _hdr(design, net):
    return [m[4:] for m in design['nets'].get(net, []) if m.startswith('hdr:')]


def _signal_pins(design, net):
    return [p for p in _hdr(design, net) if twin_pin(p)]


def _level_of(design, net):
    """The level a net sits at when nothing drives it: 0 for a net joined to GND, 1 for one joined to the supply, None otherwise."""
    pins = _hdr(design, net)
    if 'GND' in pins:
        return 0
    if any(p in ('+5V', '5V', '+3V3', 'VIN') for p in pins):
        return 1
    return None


def _kit_key(comp):
    return comp.get('kit_key') or ''


def _interface(comp):
    return (comp.get('kit_part') or {}).get('interface_kind', '') if isinstance(comp.get('kit_part'), dict) else ''


def _pick(design, pins):
    """Several header pins on one net (a stand-in sense jumper puts D3 beside D6): prefer the config's own led pin, then any that is not the sense pin."""
    a = design.get('assignment') or {}
    for want in (a.get('led'), a.get('button')):
        if want in pins:
            return want
    rest = [p for p in pins if p != a.get('sense')]
    return (rest or pins or [''])[0]


def _drive_pin(design, comps, comp, term_names):
    """The header pin that drives a part through any series resistor: from the named terminal's net, follow resistors to a net that has a signal pin."""
    by_ref = {c['ref']: c for c in comps}
    seen = set()
    todo = [t['net'] for t in comp['terminals'] if t['name'] in term_names]
    while todo:
        net = todo.pop(0)
        if net in seen:
            continue
        seen.add(net)
        pins = _signal_pins(design, net)
        if pins:
            return _pick(design, pins)
        for m in design['nets'].get(net, []):
            ref = m.split('.')[0]
            other = by_ref.get(ref)
            if other is not None and other['kind'] == 'resistor':
                todo += [t['net'] for t in other['terminals'] if t['net'] != net]
    return ''


def _interaction(design, comps, comp):
    spec = INTERACTIONS.get((_interface(comp), _kit_key(comp)))
    if spec is None:
        return None
    out = dict(spec)
    if spec['control'] in ('press', 'toggle'):
        sig = next((t for t in comp['terminals'] if _signal_pins(design, t['net'])), None)
        if sig is None:
            return dict(out, pin='', twin_pin='', note='no signal pin is wired to this part, so there is nothing to drive')
        pin = _pick(design, _signal_pins(design, sig['net']))
        other = next((t for t in comp['terminals'] if t is not sig), None)
        lvl = _level_of(design, other['net']) if other else None
        out.update(pin=pin, twin_pin=twin_pin(pin), pressed_level=0 if lvl is None else lvl,
                   note='' if lvl is not None else 'the other side is not joined to GND or the supply; assumed GND (pressed = 0)')
    else:
        sig = next((t for t in comp['terminals'] if any(adc_channel(p) is not None for p in _hdr(design, t['net']))), None)
        if sig is None:
            return dict(out, pin='', adc=None, note='no analog pin is wired to this part, so there is nothing to drive')
        pin = next(p for p in _hdr(design, sig['net']) if adc_channel(p) is not None)
        out.update(pin=pin, adc=adc_channel(pin), twin_pin=twin_pin(pin), note='')
    return out


def _output(design, comps, comp):
    kind = OUTPUTS.get((_interface(comp), _kit_key(comp)))
    if kind is None:
        return None
    names = ('anode',) if kind == 'led' else tuple(t['name'] for t in comp['terminals'])
    pin = _drive_pin(design, comps, comp, names)
    return {'kind': kind, 'pin': pin, 'twin_pin': twin_pin(pin), 'note': '' if pin else 'no header pin drives this part'}


def _board_row(geo, label, role):
    row = {'name': geo.name, 'role': role, 'model': geo.model, 'kind': geo.kind, 'size': geo.size, 'label': label, 'rows': geo.rows, 'holes_per_side': geo.holes_per_side,
           'rail_holes': geo.rail_holes, 'pitch_mm': 2.54, 'reserved': bool(geo.reserved)}
    if geo.kind == 'devboard':
        try:
            from board.custom import board_uno
            row['connectors'] = [{'name': n, 'ref': ref, 'labels': list(labels), 'order': order} for n, (ref, _k, _fp, labels, order) in board_uno.CONNECTORS.items()]
        except Exception:   # noqa: BLE001 - without the board module the header is drawn as a labelled strip from the wires' own pins
            row['connectors'] = []
    return row


def scene(geo, header_geo, design, placements, label='', header_label=''):
    """The scene dict (module words). `design` is layout_sources.design_of(...), `placements` the laid placements."""
    comps = design['components']
    by_ref = {c['ref']: c for c in comps}
    parts, watch = {}, []
    for p in placements:
        comp = by_ref.get(p['name'])
        if comp is None:
            parts[p['name']] = {'interaction': None, 'output': None, 'kit_key': ''}
            continue
        out = _output(design, comps, comp)
        if out and out['twin_pin'] and out['twin_pin'] not in watch:
            watch.append(out['twin_pin'])
        parts[p['name']] = {'kit_key': _kit_key(comp), 'interface': _interface(comp), 'interaction': _interaction(design, comps, comp), 'output': out}
    pins = {}
    for labels in (m[4:] for nets in design['nets'].values() for m in nets if m.startswith('hdr:')):
        if twin_pin(labels):
            pins[labels] = {'twin_pin': twin_pin(labels), 'adc': adc_channel(labels)}
    boards = [_board_row(header_geo, header_label, 'header'), _board_row(geo, label, 'bench')]
    return {'boards': boards, 'parts': parts, 'pins': pins, 'watch': sorted(watch), 'adc_max_mv': ADC_MAX_MV}
