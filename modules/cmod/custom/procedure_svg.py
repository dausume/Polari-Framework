"""
@module cmod.custom.procedure_svg

msv-0b (AI-Notes/plans/MEASURED_VS_SIMULATED_PLAN.md section 5b, the guided sheet's LEFT PANE): WHERE TO TEST, drawn for one TestProcedureStep.

The drawing has two parts:
- The UNO R3's headers in their board order (test_procedures.HEADERS). The red probe's pins are ringed red and the black probe's black.
- The bench circuit's parts beside them, each joined to its nets. The probed net, the part to press or look at, and the part the meter goes in
  series with are lit.

A net with no board pin on it (the R1 / LED junction) is lit among the parts, so the picture still shows where the probe goes. Drawn from the
circuit rows and the step - nothing positioned by hand except the header order. Served raw: the generic api-svg-panel inlines it.
"""
from html import escape

from cmod.custom import config_rows as R
from cmod.custom import test_procedures as TP

RED, BLACK, LIT, DIM, INK = '#d62828', '#111111', '#f4a261', '#d9d9d9', '#333333'
_PITCH, _PIN = 34, 22


def _pins_of(cat, at):
    """The header pins a probe target means: a pin label, '5V' / 'GND', or a net (its board pins; GND's header pins)."""
    if not at:
        return []
    if any(at in h for h in TP.HEADERS):
        return [at]
    for n in (cat or {}).get('nets', {}).values():
        if n['net'] == at:
            return TP._pins(n) or (['GND'] if at == 'GND' else [])
    return []


def draw(manager, step):
    st = R.get(manager, 'TestProcedureStep', step)
    if st is None:
        raise R.ConfigRefused('no procedure step %r' % step, status=404)
    proc = R.get(manager, 'TestProcedure', st['procedure']) or {}
    _v, c = TP._context(manager, proc.get('bench_solution', ''))
    cat = c['cat'] if c else None
    red, black = _pins_of(cat, st['plus_at']), _pins_of(cat, st['minus_at'])
    lit_nets = {st['plus_at'], st['minus_at']} - {''}
    red_net = st['plus_at']
    if st['mode'] == 'I dc':   # in series at a part's leg: no header pin is probed - the part and the net at that leg are lit
        comp = ((cat or {}).get('components') or {}).get(st['plus_at']) or {}
        red, black = [], []
        red_net = (comp.get('nets') or [''])[0]
        lit_nets = {red_net} - {''}
    ringed = set()
    out = []
    w = 40 + _PITCH * 16 + 320
    h = 380
    out.append('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" font-family="sans-serif" font-size="11">' % (w, h))
    out.append('<rect x="0" y="0" width="%d" height="%d" fill="#ffffff"/>' % (w, h))
    out.append('<text x="12" y="20" font-size="14" fill="%s">step %s - %s</text>' % (INK, escape(str(st['order'])), escape(st['kind'])))
    out.append('<text x="12" y="38" fill="%s">%s</text>' % (INK, escape(st['words'][:150])))
    out.append('<text x="12" y="54" fill="%s">expect: %s</text>' % (INK, escape(st['expect'][:150])))
    # the board and its headers
    bx, by, bw, bh = 20, 96, _PITCH * 16 + 20, 240
    out.append('<rect x="%d" y="%d" width="%d" height="%d" rx="10" fill="#1f6f8b" fill-opacity="0.12" stroke="#1f6f8b"/>' % (bx, by, bw, bh))
    out.append('<text x="%d" y="%d" fill="#1f6f8b">Arduino UNO R3 (USB on the left)</text>' % (bx + 12, by + bh / 2))
    rows = [(TP.HEADERS[0][::-1], by + 14, bx + 20 + _PITCH * 8), (TP.HEADERS[1][::-1], by + 14, bx + 20),
            (TP.HEADERS[2], by + bh - 34 - _PIN, bx + 20), (TP.HEADERS[3], by + bh - 34 - _PIN, bx + 20 + _PITCH * 8)]
    used = {p for n in (cat or {}).get('nets', {}).values() for p in TP._pins(n)}
    for pins, y, x0 in rows:
        for i, p in enumerate(pins):
            x = x0 + i * _PITCH
            fill = LIT if p in used else '#ffffff'
            out.append('<rect x="%d" y="%d" width="%d" height="%d" fill="%s" stroke="%s"/>' % (x, y, _PIN, _PIN, fill, INK))
            top = y < by + 40
            out.append('<text x="%d" y="%d" text-anchor="middle" font-size="9" fill="%s">%s</text>' % (x + _PIN / 2, y - 14 if top else y + _PIN + 16, INK, escape(p)))
            for probe, col in ((red, RED), (black, BLACK)):
                if p in probe and not (p == 'GND' and ('GND', col) in ringed):   # one GND pin is enough to show
                    ringed.add((p, col))
                    out.append('<circle cx="%d" cy="%d" r="%d" fill="none" stroke="%s" stroke-width="4"/>' % (x + _PIN / 2, y + _PIN / 2, _PIN / 2 + 3, col))
    # the circuit's parts beside the board
    px = bx + bw + 30
    out.append('<text x="%d" y="%d" fill="%s">the bench circuit%s</text>' % (px, by - 6, INK, ' %s' % escape(cat['circuit']) if cat else ': no circuit rows'))
    for i, (name, comp) in enumerate(sorted((cat or {}).get('components', {}).items())):
        y = by + 10 + i * 70
        hot = name == st['part'] or name == st['plus_at']
        out.append('<rect x="%d" y="%d" width="120" height="40" rx="6" fill="%s" stroke="%s" stroke-width="%d"/>' % (px, y, LIT if hot else '#ffffff', RED if hot else INK, 3 if hot else 1))
        out.append('<text x="%d" y="%d" fill="%s">%s (%s)</text>' % (px + 6, y + 16, INK, escape(name), escape(comp.get('kind', ''))))
        nets = comp.get('nets', [])
        out.append('<text x="%d" y="%d" font-size="9" fill="%s">%s</text>' % (px + 6, y + 32, INK, escape(' - '.join(nets))))
        for k, net in enumerate(nets[:2]):
            ny = y + 10 + k * 20
            on = net in lit_nets
            col = (RED if net == red_net else BLACK) if on else DIM
            out.append('<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="%s" stroke-width="%d"/>' % (px + 120, ny, px + 170, ny, col, 3 if on else 1))
            out.append('<text x="%d" y="%d" font-size="9" fill="%s">%s</text>' % (px + 174, ny + 3, col if on else INK, escape(net)))
    if st['mode']:
        out.append('<text x="%d" y="%d" font-size="13" fill="%s">meter: %s%s</text>' % (bx, h - 14, INK, escape(st['mode']),
                   ' - in SERIES, the circuit broken at the part' if st['mode'] == 'I dc' else ''))
    out.append('<text x="%d" y="%d" fill="%s">red = the red probe, black = the black probe, orange = used / the part</text>' % (w - 380, h - 14, INK))
    out.append('</svg>')
    return '\n'.join(out)


def print_view(manager, session):
    """The sheet for paper (D-msv-8: an HTML print view): one block per step - its picture, what to do, what to expect, a box to write in."""
    from cmod.custom import test_sessions as TS
    v = TS.sheet(manager, session)
    parts = ['<!doctype html><html><head><meta charset="utf-8"><title>Test sheet %s</title>' % escape(session),
             '<style>body{font-family:sans-serif;margin:16px}section{page-break-inside:avoid;border-top:1px solid #999;padding:8px 0}'
             '.box{display:inline-block;min-width:160px;border-bottom:1px solid #000;height:18px}svg{max-width:100%;height:auto}</style></head><body>',
             '<h1>Test sheet</h1><p>session %s - unit %s - procedure %s</p>' % (escape(session), escape(v['unit']), escape(v['procedure']))]
    for r in v['rows']:
        parts.append('<section><h3>%d. %s</h3><p>%s</p><p>expect: %s</p><p>result: <span class="box">%s</span> verdict: %s</p>%s</section>' % (
            r['order'], escape(r['kind']), escape(r['words']), escape(r['expect']), escape(str(r['answer'])), escape(r['verdict']),
            draw(manager, r['step']) if r['kind'] in ('continuity', 'measure', 'observe') or 'button' in r['words'] else ''))
    parts.append('</body></html>')
    return ''.join(parts)

