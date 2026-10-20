"""
@module electrodevice.custom.layout_steps

lay-1: the BUILD STEPS — DERIVED from a layout, never typed. Step 0 unplugs the board; step 1 is the rails; then one step per part, in the order the placer put them (each with its orientation in
plain words); then one step per remaining wire with its EFFECTIVE colour; the last step is the final check list. Every part and every wire appears in exactly one step. Step k's DRAWING DATA is
steps 0..k: `draw` lists every part and wire placed up to and including step k, `adds` what step k itself puts in (the drawing highlights it and dims the rest).
A person's edits are already in the layout this reads (kept beside the derived value by electrodevice.custom.layout_edits); a changed hole or colour shows up in the text, with the derived value
named beside it.
"""
import hashlib
import json

from electrodevice.custom.layout_words import a_an, hole_words, join_words

DIGIT_COLOURS = ('black', 'brown', 'red', 'orange', 'yellow', 'green', 'blue', 'violet', 'grey', 'white')


def resistor_bands(ohms):
    """The first three colour bands of an ohm value (two digits and the multiplier): 220 -> red, red, brown. None for a value that does not fit two digits and a power of ten."""
    s = str(int(ohms))
    if len(s) < 2 or int(s) < 10:
        return None
    mult = len(s) - 2
    return [DIGIT_COLOURS[int(s[0])], DIGIT_COLOURS[int(s[1])], DIGIT_COLOURS[mult]] if mult < 10 and set(s[2:]) <= {'0'} else None


def _wire_text(w, pin_where, header_label):
    a, b = w['from'], w['to']
    start = ("the board's %s pin (%s)" % (a['tie'], pin_where(a['tie']))) if a['board'] == header_label else hole_words(a['tie'])
    end = ("the board's %s pin (%s)" % (b['tie'], pin_where(b['tie']))) if b['board'] == header_label else hole_words(b['tie'])
    colour = w['colour_effective']
    why = '' if not w['colour_override'] else " (your colour; the scheme would use %s)" % w['colour']
    return "Wire %s: %s to %s, with %s wire%s (net %s)." % (w['name'], start, end, a_an(colour), why, w['net'])


def _part_text(p, facts):
    legs, name = p['legs'], p['name']
    by_t = {}
    for l in legs:
        by_t.setdefault(l['name'], []).append(l)
    if p['straddles_trench']:
        rows = sorted({l['row'] for l in legs})
        return ("Press the pushbutton %s into the board so that it STRADDLES the centre trench: its legs go in row %d, holes %s and %s, and in row %d, holes %s and %s. "
                "Its legs are joined in pairs inside (two legs per side, KitPart arduino-starter-kit:pushbutton), and pressing it joins the left side to the right side. "
                "If the board reads the button as always pressed, turn the button a quarter turn."
                % (name, rows[0], legs[0]['col'], legs[2]['col'], rows[1], legs[1]['col'], legs[3]['col']))
    if p['kind'] == 'led':
        a, c = by_t['anode'][0], by_t['cathode'][0]
        return ("Put the LED %s in with its LONGER leg (the anode) in row %d, hole %s, and its SHORTER leg (the cathode, on the side of the flat edge of its rim) in row %d, hole %s. "
                "Current only flows from the longer leg to the shorter one." % (name, a['row'], a['col'], c['row'], c['col']))
    if p['kind'] == 'resistor':
        t1, t2 = by_t['1'][0], by_t['2'][0]
        bands = resistor_bands(p['params'].get('ohms')) if p['params'].get('ohms') else None
        return ("Put the %s ohm resistor %s%s in row %d, hole %s and row %d, hole %s (it has no polarity, either way round)."
                % (p['params'].get('ohms', '?'), name, ' (colour bands %s)' % ', '.join(bands) if bands else '', t1['row'], t1['col'], t2['row'], t2['col']))
    if p['kind'] in ('tmp36', 'transistor'):
        order = p['terminal_order']
        face = ("with the FLAT FACE toward you, left to right: %s" % ', '.join('%s in row %d' % (n, by_t[n][0]['row']) for n in order))
        return "Put %s %s in column %s, %s." % (p['kind'].upper() if p['kind'] == 'tmp36' else 'the transistor', name, legs[0]['col'], face)
    return "Put %s (%s) in %s." % (name, p['kind'], join_words('row %d hole %s' % (l['row'], l['col']) for l in legs))


def _final_checks(design, laid, steps_before):
    checks = ['Every one of the %d parts sits in the holes named above, with its legs straight and not touching a neighbour.' % len(laid['placements']),
              'Every one of the %d wires is pushed fully into both its holes.' % len(laid['wires'])]
    for p in laid['placements']:
        if p['kind'] == 'led':
            a = next(l for l in p['legs'] if l['name'] == 'anode')
            checks.append("The LED's longer leg is in row %d (the row joined to the resistor), its shorter leg in row %d." % (a['row'], next(l for l in p['legs'] if l['name'] == 'cathode')['row']))
    checks.append("Compare the board with the drawing, then plug the UNO in. Polari's netlist gate has already checked that this layout makes exactly the design's nets.")
    return checks


def build_steps(design, laid, board_label, pin_where, header_label):
    """-> [step]. A step: {index, kind, title, text, adds: {parts, wires}, draw: {parts, wires}, checks?}."""
    wires = [dict(w, _header=header_label) for w in laid['wires']]
    rail_wires = [w for w in wires if w['name'].endswith('-header')]
    other = [w for w in wires if w not in rail_wires]
    raw = [('unplug', 'Unplug the board', "Unplug the UNO from USB and from any other power, and take any old wires off %s. Nothing is wired while it has power." % board_label, [], [])]
    if rail_wires:
        raw.append(('rails', 'Wire the rails', ' '.join(_wire_text(w, pin_where, header_label) for w in rail_wires), [], [w['name'] for w in rail_wires]))
    for p in laid['placements']:
        note = (" (Your edit: the placer's holes were %s.)" % join_words(hole_words(h) for h in p['edit']['derived'])) if p.get('edit') else ''
        raw.append(('part', 'Place %s' % p['name'], _part_text(p, None) + note, [p['name']], []))
    for w in other:
        note = (" (Your edit: the placer's ends were %s and %s.)" % tuple(hole_words(h) for h in w['edit']['derived'])) if w.get('edit') else ''
        raw.append(('wire', 'Add wire %s' % w['name'], _wire_text(w, pin_where, header_label) + note, [], [w['name']]))
    raw.append(('check', 'Check the build', 'Final check.', [], []))
    steps, parts_so_far, wires_so_far = [], [], []
    for i, (kind, title, text, parts, wnames) in enumerate(raw):
        parts_so_far = parts_so_far + parts
        wires_so_far = wires_so_far + wnames
        step = {'index': i, 'kind': kind, 'title': title, 'text': text, 'adds': {'parts': parts, 'wires': wnames}, 'draw': {'parts': list(parts_so_far), 'wires': list(wires_so_far)}}
        if kind == 'check':
            step['checks'] = _final_checks(design, laid, steps)
            step['text'] = 'Final check: ' + ' '.join('(%d) %s' % (n + 1, c) for n, c in enumerate(step['checks']))
        steps.append(step)
    return steps


def steps_sha(steps):
    return hashlib.sha256(json.dumps(steps, sort_keys=True).encode()).hexdigest()


def walkthrough_lines(steps, limit=None):
    """The walkthrough as plain text lines, one per step: '<n>. <text>'."""
    lines = ['%d. %s' % (s['index'], s['text']) for s in steps]
    return lines[:limit] if limit else lines
