"""board_pin_view_modes_selftest — pv-2 (PIN_VIEW_PLAN.md section 7): the DRIVE and SIGNAL modes of the pin payload, the multi-protocol / activated-only filters, the drive row filters, the pv-0 follow-up (an unclaimed
line names no protocol signal) and the label layout (no two part labels overlap). Run by board_selftest.run(). Every verdict asserted here is compared with the output of the code that OWNS it (the electrical
rules' findings via pin_view_state._canon_verdict, the PinGroupBudget / PinLifecycleConstraint rows, the PinFunction directions), never with a copy.
"""
import contextlib
import io
import json

BOARD = 'arduino-uno-r3'
SYSTEM = 'uno-light-system'
BINDING = 'uno-light@arduino-uno-r3'


def _by_canon(res, canon, level):
    return next(p for p in res['pins'] if p['canonical'] == canon and p['level'] == level)


def _fields(p, names):
    """All the text of the named fields of one pin (strings, lists and dicts flattened)."""
    return json.dumps([p[n] for n in names], default=str)


def _overlap(a, b, eps=1e-9):
    return a['x0'] < b['x1'] - eps and b['x0'] < a['x1'] - eps and a['y0'] < b['y1'] - eps and b['y0'] < a['y1'] - eps


def _abs(box, ox, oy):
    return {'x0': box['x0'] + ox, 'x1': box['x1'] + ox, 'y0': box['y0'] + oy, 'y1': box['y1'] + oy}


def run_pin_view_modes(check):
    from board.custom import hardware_system as HS
    from board.custom import hwsys_system as SYS
    from board.custom import pin_view as PV
    from board.custom import pin_view_modes as MD
    from board.custom import pin_view_state as ST
    from board.custom import pv_shapes as S
    from board.custom.hwsys_context import Ctx
    with contextlib.redirect_stdout(io.StringIO()):
        t = HS.default_tables()
    base = PV.build(BOARD, {'system': SYSTEM})
    fc = PV.build(BOARD, {'system': SYSTEM, 'binding': BINDING, 'stage': 'firmware-committed'})
    DRIVE_F = ('drive_status', 'drive_why', 'rail', 'pull', 'limit_class', 'limit_basis', 'group_budget')
    SIGNAL_F = ('activated', 'capable', 'lifecycle')
    kinds = lambda res, level, ks: [p for p in res['pins'] if p['level'] == level and p['kind'] in ks]   # noqa: E731

    # ---- DRIVE at base
    io_pads = [p for p in base['pins'] if p['level'] == 'die' and p['kind'] == 'io']
    check('DRIVE base: the supply pads are `supplied`, the ground pads `returns`, the I/O pads (%d) are drive-relevant and ALL `not-driven` with no pull (the blank chip), the 5V header pin `supplies` on the 5V rail, GND `returns`'
          % len(io_pads),
          io_pads and all(p['drive_relevant'] and p['drive_status'] == 'not-driven' and p['pull'] == 'none' and p['rail'] == 'logic-io' for p in io_pads)
          and all(p['drive_status'] == 'supplied' and p['drive_relevant'] for p in kinds(base, 'die', ('power', 'analog-supply', 'usb-supply')))
          and all(p['drive_status'] == 'returns' and p['rail'] == 'GND' for p in kinds(base, 'die', ('ground', 'usb-ground')))
          and next(p for p in base['pins'] if p['id'] == 'ConnectorPin:%s:POWER:5' % BOARD)['drive_status'] == 'supplies'
          and next(p for p in base['pins'] if p['id'] == 'ConnectorPin:%s:POWER:5' % BOARD)['rail'] == '5V'
          and next(p for p in base['pins'] if p['id'] == 'ConnectorPin:%s:POWER:6' % BOARD)['drive_status'] == 'returns', str(len(io_pads)))
    check('DRIVE vocabulary: every pin carries one of the nine statuses, a rail from {5V, 3V3, VBUS, GND, logic-io, undetermined} (from the BoardNet class / volts and the contact kind: VCC / AVCC on the +5V net are 5V, the USB supply is VBUS, '
          'the regulator output is undetermined), a pull from {none, internal-up, internal-down, external} and a limit class; the USB data pair is NOT drive-relevant',
          all(p['drive_status'] in MD.DRIVE_STATUSES and p['rail'] in MD.RAILS and p['pull'] in MD.PULLS and p['limit_class'] in ('within-recommended', 'undetermined', 'over', 'unchecked') for p in fc['pins'])
          and {p['rail'] for p in fc['pins'] if p['level'] == 'die' and p['kind'] in ('power', 'analog-supply') and p['soc'] == 'atmega328p'} == {'5V'}
          and {p['rail'] for p in kinds(fc, 'die', ('usb-supply',))} == {'VBUS'} and {p['rail'] for p in kinds(fc, 'die', ('regulator-output',))} == {'undetermined'}
          and not any(p['drive_relevant'] for p in kinds(fc, 'die', ('usb-data',))), '')

    # ---- DRIVE at firmware-committed
    d6, d2, d0, d1 = (_by_canon(fc, c, 'die') for c in ('D6', 'D2', 'D0', 'D1'))
    ctx = Ctx(t, None, SYS.rows(t)[0])
    ref_cls, ref_basis = ST._canon_verdict(ctx, 'D6')
    claim2 = next(c for c in d2['consumers'] if c['kind'] == 'task')
    dirs = {s['function']: s['direction'] for s in d0['signals'] + d1['signals']}
    check('DRIVE firmware-committed (%s): D6 = sources-or-sinks with limit_class `%s` and the rule id led_current in its basis (the rules\' own verdict, compared with the owner); D2 = pulled-up because the claim says pull=%s (pull internal-up); '
          'D0 (RXD, %s) = high-impedance, D1 (TXD, %s) = sources-or-sinks' % (BINDING, ref_cls, claim2['pull'], dirs['RXD'], dirs['TXD']),
          d6['drive_status'] == 'sources-or-sinks' and d6['limit_class'] == ref_cls == 'undetermined' and 'led_current' in d6['limit_basis'] and 'led_current' in ref_basis
          and d2['drive_status'] == 'pulled-up' and claim2['pull'] == 'up' and d2['pull'] == 'internal-up'
          and dirs['RXD'] == 'in' and d0['drive_status'] == 'high-impedance' and dirs['TXD'] == 'out' and d1['drive_status'] == 'sources-or-sinks'
          and all(p['drive_status'] == 'not-driven' for p in fc['pins'] if p['level'] == 'die' and p['kind'] == 'io' and p['stage'] not in ('proposed', 'committed')), str((d6['drive_status'], d2['drive_status'], d0['drive_status'])))
    gnd = kinds(fc, 'package', ('ground', 'usb-ground', 'thermal-pad'))
    vcc = [p for p in fc['pins'] if p['id'] == 'PackageContact:atmega328p-28-spdip:7']
    hdr5 = next(p for p in fc['pins'] if p['id'] == 'ConnectorPin:%s:POWER:5' % BOARD)
    check('DRIVE firmware-committed: every GND / USB ground / thermal-pad leg `returns` (%d), VCC `supplied` on 5V, the 5V header pin `supplies` on 5V, and the lines the claims leave alone stay `not-driven`; the header pin of D6 reads what its leg reads'
          % len(gnd), gnd and all(p['drive_status'] == 'returns' and p['rail'] == 'GND' for p in gnd) and vcc and vcc[0]['drive_status'] == 'supplied' and vcc[0]['rail'] == '5V'
          and hdr5['drive_status'] == 'supplies' and hdr5['rail'] == '5V' and _by_canon(fc, 'D6', 'board')['drive_status'] == 'sources-or-sinks' and _by_canon(fc, 'D2', 'board')['drive_status'] == 'pulled-up', '')
    budgets = {b['name']: json.loads(b['members_json']) for b in t['PinGroupBudget']}
    want = sorted(n for n, m in budgets.items() if 'atmega328p:PD6' in m)
    check('DRIVE group budget: D6 counts toward exactly the PinGroupBudget rows that list PD6 (%s) - names only; the VCC leg counts toward the VCC / GND total' % ', '.join(want),
          sorted(d6['group_budget']) == want and len(want) == 2 and 'atmega328p:vcc-gnd-abs-max' in vcc[0]['group_budget'] and all(isinstance(n, str) for p in fc['pins'] for n in p['group_budget']), str(d6['group_budget']))
    modes = PV.build(BOARD, {'system': SYSTEM, 'binding': BINDING, 'stage': 'firmware-committed', 'phase': 'bootloader'})
    boot = [r for r in t['PinLifecycleConstraint'] if r['pin'] == 'D0' and r['phase'] == 'bootloader']
    lc0 = _by_canon(modes, 'D0', 'die')['lifecycle']
    check('SIGNAL lifecycle: the pin carries the PinLifecycleConstraint rows of the REQUEST\'S phase (names only: policy + condition + a lock flag) - D0 at runtime is reserved (transport=usb-serial), at bootloader reserved, D2 has none; RESET is prohibited at runtime',
          [x['policy'] for x in d0['lifecycle']] == ['reserved'] and d0['lifecycle'][0]['condition'] == 'transport=usb-serial' and d0['lifecycle'][0]['locks'] and [x['name'] for x in lc0] == [r['name'] for r in boot] and not d2['lifecycle']
          and any(x['policy'] == 'prohibited' and x['locks'] for p in fc['pins'] if p['soc_pin'] == 'atmega328p:PC6' for x in p['lifecycle']), '')

    # ---- SIGNAL
    supply_kinds = ('power', 'analog-supply', 'usb-supply', 'ground', 'usb-ground', 'thermal-pad', 'regulator-output')
    check('SIGNAL relevance: no supply, ground or regulator pad / leg is signal-relevant, every I/O pad is, the supply header pins (5V, 3V3, VIN, GND, IOREF, NC) are not; at stage base NOTHING is activated (every pin shows capabilities only)',
          not any(p['signal_relevant'] for p in fc['pins'] if p['level'] in ('die', 'package') and p['kind'] in supply_kinds) and all(p['signal_relevant'] for p in fc['pins'] if p['level'] in ('die', 'package') and p['kind'] == 'io')
          and not any(p['signal_relevant'] for p in fc['pins'] if p['level'] == 'board' and p['label'] in ('+5V', '+3V3', 'VIN', 'GND', 'IOREF', 'NC'))
          and not any(p['activated'] for p in base['pins']) and any(p['capable'] for p in base['pins']), '')
    cap0 = {(c['function'], c['family']) for c in d0['capable']}
    check('SIGNAL activated: D0 = RXD (uart, inputs) at firmware-committed - the claim\'s function, compared with the claim - and its capable list names every function of the pad with its family ({GPIO gpio, RXD uart, PCINT16 interrupt}); D2 = INT0 (interrupt), D6 = GPIO-out (gpio, outputs); '
          'the header pin and the leg of D0 carry the same activation',
          d0['activated']['function'] == 'RXD' == next(c for c in d0['consumers'] if c['kind'] == 'task')['function'] and d0['activated']['family'] == 'uart' and d0['activated']['direction'] == 'inputs'
          and cap0 == {('GPIO', 'gpio'), ('RXD', 'uart'), ('PCINT16', 'interrupt')} and d2['activated']['function'] == 'INT0' and d6['activated']['function'] == 'GPIO-out' and d6['activated']['direction'] == 'outputs'
          and _by_canon(fc, 'D0', 'board')['activated'] == d0['activated'] == _by_canon(fc, 'D0', 'package')['activated'] and _by_canon(base, 'D0', 'die')['activated'] is None, str(d0['activated']))
    mix_bad = [p['id'] for p in fc['pins'] if MD.SIGNAL_WORDS.search(_fields(p, DRIVE_F)) or MD.DRIVE_WORDS.search(_fields(p, SIGNAL_F))]
    check('NO MIXING: across all %d pins of the committed view not one DRIVE field (status, why, rail, pull, limit class and basis, group budget) holds a signal word (outputs / inputs / RXD / protocol ...) and not one SIGNAL field '
          '(activated, capable, lifecycle) holds a drive word (sources / sinks / supplied / pulled / rail ...)' % len(fc['pins']), not mix_bad, str(mix_bad[:3]))
    cons = [c for c in fc['connections'] if 'drive_relevant' in c and 'signal_relevant' in c]
    check('CONNECTIONS per mode: every connection says whether it is drive-relevant and signal-relevant (both ends are); a supply rail connection is drive- but never signal-relevant, the D0 line to U2 is both',
          len(cons) == len(fc['connections']) and all(c['drive_relevant'] and not c['signal_relevant'] for c in fc['connections'] if c['kind'] == 'on-board' and c['signal']['family'] in ('power', 'ground'))
          and any(c['kind'] == 'chip-to-chip' and c['drive_relevant'] and c['signal_relevant'] for c in fc['connections']), '')

    # ---- the filters
    def lit_set(res):
        return {p['canonical'] or p['label'] for p in res['pins'] if p['lit']}
    i2c = PV.build(BOARD, {'system': SYSTEM, 'protocol': 'i2c'})
    spi = PV.build(BOARD, {'system': SYSTEM, 'protocol': 'spi'})
    both = PV.build(BOARD, {'system': SYSTEM, 'protocol': 'i2c,spi'})
    i2c_board = {p['label'] for p in i2c['pins'] if p['lit'] and p['level'] == 'board'}
    check('PROTOCOL i2c: only the SDA / SCL related pins are lit - on the board A4, A5 and the SDA / SCL header pins (%s) - nothing of D0-D13 / A0-A3' % ', '.join(sorted(i2c_board)),
          i2c_board == {'A4', 'A5', 'SDA', 'SCL'} and not ({'D%d' % n for n in range(14)} | {'A0', 'A1', 'A2', 'A3'}) & {p['label'] for p in i2c['pins'] if p['lit']}
          and {p['soc_pin'] for p in i2c['pins'] if p['lit'] and p['level'] == 'die'} == {'atmega328p:PC4', 'atmega328p:PC5'}, str(sorted(i2c_board)))
    check('PROTOCOL i2c,spi: SEVERAL protocols at once light BOTH sets - the union of the i2c and spi sets (%d + %d pins, the two are disjoint on the 328P), the answer echoes protocols [i2c, spi] and every lit child names the protocol it answers'
          % (len(lit_set(i2c)), len(lit_set(spi))),
          {p['id'] for p in both['pins'] if p['lit']} == {p['id'] for p in i2c['pins'] if p['lit']} | {p['id'] for p in spi['pins'] if p['lit']} and both['protocol']['protocols'] == ['i2c', 'spi']
          and both['protocol']['protocol'] == 'i2c,spi' and {'A4', 'D13'} <= lit_set(both)
          and all(ch.get('protocol') in ('i2c', 'spi') for p in both['pins'] if p['lit'] for ch in p['lit']['children']) and both['protocol']['children'] == ['SDA', 'SCL', 'SCK', 'MOSI', 'MISO', 'SS'], '')
    ao_base = PV.build(BOARD, {'system': SYSTEM, 'protocol': 'uart', 'activated_only': '1'})
    ao_fc = PV.build(BOARD, {'system': SYSTEM, 'binding': BINDING, 'stage': 'firmware-committed', 'protocol': 'uart,i2c', 'activated_only': '1'})
    cap = PV.build(BOARD, {'system': SYSTEM, 'binding': BINDING, 'stage': 'firmware-committed', 'protocol': 'uart,i2c'})
    check('ACTIVATED ONLY: at stage base nothing is activated, so nothing is lit (the note says so); at firmware-committed uart,i2c with activated_only lights only D0 / D1 (the claimed USART0 pair) - A4 / A5 are capable of i2c but no claim activates them; '
          'without activated_only they are lit',
          ao_base['protocol']['activated_only'] and not any(p['lit'] for p in ao_base['pins']) and lit_set(ao_fc) == {'D0', 'D1'} and {'A4', 'A5'} <= lit_set(cap)
          and all(p['soc_pin'] in ('atmega328p:PD0', 'atmega328p:PD1') for p in ao_fc['pins'] if p['lit'] and p['level'] == 'die'), str(sorted(lit_set(ao_fc))))
    unknown = False
    try:
        PV.build(BOARD, {'protocol': 'i2c,nope'})
    except ValueError:
        unknown = True
    rail5 = PV.door(None, BOARD, {'system': SYSTEM, 'binding': BINDING, 'stage': 'firmware-committed', 'rail': '5V'}, 'pins')[1]
    two = PV.door(None, BOARD, {'system': SYSTEM, 'binding': BINDING, 'stage': 'firmware-committed', 'drive_status': 'pulled-up,high-impedance'}, 'pins')[1]
    lim = PV.door(None, BOARD, {'system': SYSTEM, 'binding': BINDING, 'stage': 'firmware-committed', 'limit_class': 'undetermined', 'level': 'board'}, 'pins')[1]
    conn5 = PV.door(None, BOARD, {'system': SYSTEM, 'rail': 'GND'}, 'connections')[1]
    surf = PV.door(None, BOARD, {'rail': 'GND'}, 'surfaces')[1]
    check('DRIVE FILTERS on the row views: rail=5V, drive_status=pulled-up,high-impedance (a comma list) and limit_class=undetermined narrow the pin rows to exactly the pins whose payload field matches (%d / %d / %d rows); the connection rows filter by rail too; '
          'a column the view lacks (surfaces) is skipped, not emptied; an unknown protocol in a list is refused'
          % (rail5['count'], two['count'], lim['count']),
          rail5['count'] == sum(1 for p in fc['pins'] if p['rail'] == '5V') and all(r['rail'] == '5V' for r in rail5['rows'])
          and two['count'] == sum(1 for p in fc['pins'] if p['drive_status'] in ('pulled-up', 'high-impedance')) and {r['drive_status'] for r in two['rows']} == {'pulled-up', 'high-impedance'}
          and lim['count'] == sum(1 for p in fc['pins'] if p['level'] == 'board' and p['limit_class'] == 'undetermined') and lim['count'] > 0
          and conn5['count'] > 0 and all(r['rail'] == 'GND' for r in conn5['rows']) and surf['count'] == len(base['surfaces']) and unknown, str((rail5['count'], two['count'], lim['count'])))
    prow = next(r for r in PV.rows_payload(fc, 'pins')['rows'] if r['id'] == d6['id'])
    check('ROWS: a pin row also carries drive status, rail, pull, limit class, group budget, activated function, capable functions and lifecycle as columns (D6: %s / %s / %s)' % (prow['drive_status'], prow['limit_class'], prow['activated']),
          prow['drive_status'] == 'sources-or-sinks' and prow['activated'] == 'GPIO-out' and 'PWM' not in prow['capable'] and 'OC0A' in prow['capable'] and prow['group_budget'].count('atmega328p:') == 2, '')

    # ---- pv-0 follow-up 1: an unclaimed line names no protocol signal
    sc = {c['id']: c for c in base['connections']}
    d6l = [c for c in base['connections'] if (c['a'] in {p['id'] for p in base['pins'] if p['canonical'] == 'D6'} or c['b'] in {p['id'] for p in base['pins'] if p['canonical'] == 'D6'}) and c['kind'] in ('pad-to-leg', 'to-header')]
    d6c = [c for c in fc['connections'] if (c['a'] in {p['id'] for p in fc['pins'] if p['canonical'] == 'D6'}) and c['kind'] == 'pad-to-leg']
    uart = next(c for c in base['connections'] if c['kind'] == 'chip-to-chip' and c['via_part'] == 'RN4B')
    check('BASE honesty (pv-0 follow-up 1): at stage base the unclaimed D6 line (pad-to-leg, leg-to-header) names NO family and NO protocol signal - it lists what it CAN carry (gpio, pwm-timer, analog, interrupt); once a claim configures it the family is the claim\'s (gpio); '
          'the chip-to-chip UART pair keeps its one shared family',
          d6l and all(c['signal']['family'] == '' and c['signal']['protocol_signal'] == '' and c['signal']['function_a'] == '' and {'gpio', 'pwm-timer'} <= set(c['signal']['capable']) for c in d6l)
          and d6c and all(c['signal']['family'] == 'gpio' for c in d6c) and uart['signal']['family'] == 'uart' and uart['signal']['function_a'] == 'RXD' and sc, str([c['signal']['family'] for c in d6l]))

    # ---- layout: no two part labels overlap
    parts = [s for s in base['surfaces'] if s['kind'] in ('board-part', 'bench-part')]
    bw, bh = S.BOARD_BBOX
    boxes = []   # (owner, kind, absolute rect)
    for s in parts:
        p = base['shapes'][s['shape']]['parameters']
        geo = S.part_geometry(p)
        for b in geo['boxes']:
            boxes.append((s['id'], b['kind'], b['text'], _abs(b, s['x'], s['y'])))
        hw, hh = float(p['box'][0]) / 2, float(p['box'][1]) / 2
        boxes.append((s['id'], 'body', '', {'x0': s['x'] - hw, 'x1': s['x'] + hw, 'y0': s['y'] - hh, 'y1': s['y'] + hh}))
    clash = [(a[0], a[2] or a[1], b[0], b[2] or b[1]) for i, a in enumerate(boxes) for b in boxes[i + 1:] if _overlap(a[3], b[3]) and not (a[0] == b[0] and 'body' in (a[1], b[1]))]
    check('LAYOUT labels: every part title and pin label is a box estimated from len(text) x font (%.1f mm) x char width (%.2f em); across all %d parts (%d label and body boxes) NO two boxes overlap - not CSTCE16M0V53-R0 and ICSP1, not the PB6 / PB7 lines, not Y1 and its neighbours'
          % (S.LABEL['font'], S.LABEL['char_w'], len(parts), len(boxes)), not clash and len(parts) == 17, str(clash[:3]))
    sample = [b for b in boxes if b[0].endswith(':Y1')]
    inside = all(b[3]['x0'] >= 0 and b[3]['y0'] >= 0 and b[3]['x1'] <= bw and b[3]['y1'] <= bh for s in parts if s['kind'] == 'board-part' for b in boxes if b[0] == s['id'])
    chips = [s for s in base['surfaces'] if s['kind'] == 'enclosure']
    m = S.CHIP_LABEL_MARGIN
    rects = []
    for s in chips:
        w, h = (s['h'], s['w']) if s.get('rot') in (90, 270) else (s['w'], s['h'])
        rects.append({'x0': s['x'] - w / 2 - m, 'x1': s['x'] + w / 2 + m, 'y0': s['y'] - h / 2 - m, 'y1': s['y'] + h / 2 + m})
    pins_hdr = [p for p in base['pins'] if p['level'] == 'board']
    hdr_pts = [{'x0': p['x'] - 1.2, 'x1': p['x'] + 1.2, 'y0': p['y'] - 1.2, 'y1': p['y'] + 1.2} for p in pins_hdr]
    hits = [(b[0], b[2] or b[1]) for b in boxes for r in rects + hdr_pts if b[0].startswith('part:') and _overlap(b[3], r)]
    check('LAYOUT keep-out: every board-part label lies INSIDE the board outline (Y1 no longer spills off the left edge: %d boxes checked), clear of the chip packages (body + %.1f mm leg-label margin) and of every header pin; bench parts sit entirely right of the board'
          % (len(sample), m), inside and not hits and all(b[3]['x0'] > bw for b in boxes if b[0].startswith('bench:')), str(hits[:3]))
    sh = {s['id']: s for s in parts}
    check('LAYOUT payload: every part surface carries its abbreviated title (<= %d characters; the full name stays the title), the title position and the extent the component fits; every part pin carries a short label (<= %d characters)'
          % (S.LABEL['max_title'], S.LABEL['max_pin']),
          all(s['short_title'] and len(s['short_title']) <= S.LABEL['max_title'] and s['title_pos'] and s['extent'] for s in parts) and sh['part:%s:RESET button TS42031-160R-TR-7260' % BOARD]['short_title'].endswith('…')
          and all(p['short_label'] and len(p['short_label']) <= S.LABEL['max_pin'] for p in base['pins'] if p['level'] in ('part', 'bench')) and base['layout']['font'] == S.LABEL['font'], '')
    # ---- layout: a package title never lies over another chip's leg labels (the U2 title ran into U1's top-left leg label)
    import math
    K = S.PKG_TITLE
    mm = lambda px: px / K['fit_px_per_mm']   # noqa: E731
    pkgs = [s for s in base['surfaces'] if s['kind'] == 'enclosure']
    byid = {s['id']: s for s in base['surfaces']}

    def rot(s, x, y):
        a = math.radians(s.get('rot') or 0)
        return s['x'] + math.cos(a) * x - math.sin(a) * y, s['y'] + math.sin(a) * x + math.cos(a) * y

    leg_boxes = []   # (chip, label, rect): the leg labels of every package, outward of the leg, estimated at the fit zoom
    for s in pkgs:
        for p in base['pins']:
            if p['surface'] != s['id']:
                continue
            x, y = rot(s, p['x'], p['y'])
            ox, oy = x - s['x'], y - s['y']
            w, hh = mm(len(p['label']) * K['label_px'] * K['char_em']), mm(K['label_px'])
            if abs(ox) >= abs(oy):
                r = {'x0': x, 'x1': x + w, 'y0': y - hh / 2, 'y1': y + hh / 2} if ox >= 0 else {'x0': x - w, 'x1': x, 'y0': y - hh / 2, 'y1': y + hh / 2}
            else:
                r = {'x0': x - w / 2, 'x1': x + w / 2, 'y0': y, 'y1': y + hh} if oy >= 0 else {'x0': x - w / 2, 'x1': x + w / 2, 'y0': y - hh, 'y1': y}
            leg_boxes.append((s['id'], p['label'], r))
    title_boxes = []
    for s in pkgs:
        w, h = (s['h'], s['w']) if s.get('rot') in (90, 270) else (s['w'], s['h'])
        text = s['short_title'] or s['title']
        tw = mm(len(text) * K['title_px'] * K['char_em'])
        top = s['y'] - h / 2 - mm(K['lift_px'])
        title_boxes.append((s['id'], text, {'x0': s['x'] - w / 2, 'x1': s['x'] - w / 2 + tw, 'y0': top - mm(K['title_px']), 'y1': top}))
    tclash = [(t[1], l[0], l[1]) for t in title_boxes for l in leg_boxes if t[0] != l[0] and _overlap(t[2], l[2])]
    tt = [(a[1], b[1]) for i, a in enumerate(title_boxes) for b in title_boxes[i + 1:] if _overlap(a[2], b[2])]
    u2 = next(b for b in title_boxes if b[0].endswith(':U2'))
    check('LAYOUT package titles: each package carries a short drawn title (the full name stays the hover text); across %d packages (%d leg-label boxes at the %g px/mm fit zoom) no package title overlaps another chip\'s leg labels or another title - '
          'U2\'s title is "%s", not the 27-character name that ran into U1\'s top-left leg label' % (len(pkgs), len(leg_boxes), K['fit_px_per_mm'], u2[1]),
          len(pkgs) == 2 and all(s['short_title'] and len(s['short_title']) < len(s['title']) for s in pkgs) and not tclash and not tt, str((tclash[:3], tt)))
    ghost = [(title_boxes[0][1], 'U2 atmega16u2 package (QFN)')]
    long_t = {'x0': u2[2]['x0'], 'x1': u2[2]['x0'] + mm(len('U2 atmega16u2 package (QFN)') * K['title_px'] * K['char_em']), 'y0': u2[2]['y0'], 'y1': u2[2]['y1']}
    check('LAYOUT package titles detector: the OLD full-length U2 title DOES overlap a U1 leg label under the same test (the check can fail)', any(_overlap(long_t, l[2]) for l in leg_boxes if l[0].endswith(':U1')) and ghost, '')
    # ---- page titles and table -> view links (sf)
    import json as _json
    from board.pin_view_page import PIN_VIEW_PAGES
    from board.register_profile_page import REGISTER_PROFILE_PAGES
    from polariApiServer.module_pages_seed import _page as _seed_page
    titles = {pg['name']: _json.loads(pg['definition']).get('title') for pg in PIN_VIEW_PAGES + REGISTER_PROFILE_PAGES}
    plain = _seed_page('x-y', 'x-y', 'd', 'C', [])
    tables = [it for pg in PIN_VIEW_PAGES if pg['name'] != 'pin-view' for r in _json.loads(pg['definition'])['rows'] for it in r['items']]
    links = {it['componentProps']['inputs']['columnFormats'] for it in tables}
    check('PAGE titles: the pin view, its three table pages, the register profile and the memory map carry a readable title in their definition (a page without one has none: the header humanizes its name); every table on the three '
          'table pages has a `view` link column ({id} into /display/pin-view?pin= | connection= | surface=)',
          titles == {'pin-view': 'Pin view', 'pin-view-pins': 'Pins', 'pin-view-connections': 'Connections', 'pin-view-surfaces': 'Surfaces', 'register-profile': 'Register profile', 'memory-map': 'Memory map'}
          and 'title' not in _json.loads(plain['definition'])
          and links == {'view:view:/display/pin-view?pin={id}', 'view:view:/display/pin-view?connection={id}', 'view:view:/display/pin-view?surface={id}'}
          and all(it['componentProps']['inputs']['columns'].endswith(',view') for it in tables), str(titles))
    forced = _overlap({'x0': 0, 'x1': 2, 'y0': 0, 'y1': 1}, {'x0': 1.5, 'x1': 3, 'y0': 0.5, 'y1': 2}) and not _overlap({'x0': 0, 'x1': 2, 'y0': 0, 'y1': 1}, {'x0': 2, 'x1': 3, 'y0': 0, 'y1': 1})
    items = [('a', {'x0': -2.0, 'y0': -1.0, 'x1': 2.0, 'y1': 1.0}), ('b', {'x0': -2.0, 'y0': -1.0, 'x1': 2.0, 'y1': 1.0})]
    packed = S.pack_parts(items, [{'x0': 0.0, 'y0': 0.0, 'x1': 10.0, 'y1': 10.0}])
    ra, rb = [_abs(e, *packed[k]) for k, e in items]
    check('LAYOUT detector: the overlap test itself is sound (touching edges do not overlap, crossing boxes do) and the packer separates two identical extents (it never stacks them)', forced and not _overlap(ra, rb), str(packed))
