"""
@module pcb.custom.fab_rules

THE FAB'S CONSTRAINTS AS ROWS (plan §2 FabProfile/FabRule; pcb-0): DKRed — DigiKey's PCB fab service — cited from its page
(https://www.digikey.com/en/resources/dkred, read 2026-10-03, the values as plan §2 records them; the page was not re-read on
pcb-0's day: `retrieved` says so). Three uses, all from the SAME rows:

  1. rule_set_rows() / rule_rows()   the FabRuleSet + one FabRule per constraint (seeded, code-owned)
  2. dru(rules)                      a `.kicad_dru` written FROM the length rules — KiCad's own DRC then checks clearance (5 mil
                                     spacing: a geometry check Polari does not reimplement), track width, hole sizes, via size
  3. check_board(rows, rules)        Polari's row checks over an ingested board: copper layers, outline size, the narrowest
                                     track, the smallest / largest hole, via hole + pad, the smallest pad — each a DrcResult row
                                     (kind fab-rule), violations named, a passing rule recorded as severity none
  4. naming(filename)                the fab's verdict on an export's extension (accepted | no | discrepancy) + the name it lists

Plan §2's two discrepancies are kept as data, never settled here: the page text lists neither copper .gtl/.gbl nor mask .gbs
(it shows ".bgs", likely a typo) while his screenshot of the upload form shows .gtl/.gbl/.gbs — those get `discrepancy`; the
upload form's verdict at pcb-2 becomes a DatasheetFact.
"""
import json

FAB = 'dkred'
URL = 'https://www.digikey.com/en/resources/dkred'
RETRIEVED = '2026-10-03 (plan §2, verified that day by the plan\'s author; not re-read at pcb-0)'
MIL = 0.0254
INCH = 25.4

#: (key, op, value as stated, unit, mm or 0, source text, kicad .kicad_dru constraint or '', polari row check or '')
RULES = [
    ('layers', 'in', '2,4', 'layers', 0.0, '2 or 4 layers', '', 'copper layer count'),
    ('board_min', 'min', '0.5', 'in', 0.5 * INCH, '0.5" x 0.5" to 10" x 10"', '', 'outline width and height (Edge.Cuts bbox)'),
    ('board_max', 'max', '10', 'in', 10 * INCH, '0.5" x 0.5" to 10" x 10"', '', 'outline width and height (Edge.Cuts bbox)'),
    ('thickness', 'eq', '62', 'mil', 62 * MIL, '62 mil (1.6 mm)', '', 'board thickness (general.thickness)'),
    ('min_trace', 'min', '5', 'mil', 5 * MIL, 'minimum trace 5 mil (0.13 mm)', 'track_width', 'narrowest track segment'),
    ('min_space', 'min', '5', 'mil', 5 * MIL, 'minimum space 5 mil (0.13 mm)', 'clearance', '— (KiCad DRC with the .kicad_dru)'),
    ('min_drill', 'min', '8', 'mil', 8 * MIL, 'minimum drill 8 mil (0.20 mm)', 'hole_size', 'smallest pad / via hole'),
    ('max_drill', 'max', '245', 'mil', 245 * MIL, 'maximum drill 245 mil (6.22 mm)', 'hole_size', 'largest pad / via hole'),
    ('min_via_hole', 'min', '8', 'mil', 8 * MIL, 'minimum via hole 8 mil', 'hole_size (vias)', 'smallest via hole'),
    ('min_via_pad', 'min', '16', 'mil', 16 * MIL, 'minimum via pad 16 mil (0.41 mm)', 'via_diameter', 'smallest via diameter'),
    ('min_pad', 'min', '10', 'mil', 10 * MIL, 'minimum pad 10 mil (0.25 mm)', '', 'smallest pad dimension'),
    ('min_copies', 'min', '4', 'boards', 0.0, 'minimum 4 copies', '', '— (an order quantity, pcb-4)'),
    ('copper_weight', 'eq', '1', 'oz', 0.0, '1 oz copper', '', '— (stackup intent, pcb-2)'),
    ('finish', 'eq', 'ENIG', '', 0.0, 'ENIG finish', '', '—'),
    ('material', 'eq', 'FR4 TG 170-180', '', 0.0, 'FR4 TG 170–180', '', '—'),
    ('plating', 'eq', '1', 'mil', 1 * MIL, 'plating 1 mil', '', '—'),
    ('tolerance', 'eq', '5', 'mil', 5 * MIL, 'tolerance 5 mil', '', '—'),
    ('colours', 'eq', 'red mask, white silk', '', 0.0, 'red mask, white silk', '', '—'),
    ('lead_time', 'info', '5-10', 'business days', 0.0, '5–10 business days', '', '—'),
    ('price', 'info', '1.50', 'USD per square inch', 0.0, '"starting at $1.50 per square inch" (a quote row is the price, never this)', '', '—'),
]

#: the accepted extensions per layer kind, AS LISTED on the page (plan §2), + what his upload-form screenshot adds
ACCEPTED = {
    'silkscreen': ['.gbo', '.gto', '.sst', '.ssb', '.legend', '.silk'],
    'paste': ['.gtp', '.gbp', '.gpt', '.gpb', '.paste'],
    'soldermask': ['.gts', '.bgs', '.smt', '.sm_', '.smb', '.mask', '.solder'],
    'drill': ['.drl', '.drd', '.xln', '.drill'],
    'drill-drawing': ['.gd', '.dd'],
    'mechanical': ['.gm'],
    'outline': ['.gko', '.outline', '.profile'],
    'copper': ['.pho', '.copper', '.physical_layer', '.layer'],
}
SCREENSHOT_ONLY = {'.gtl': 'copper', '.gbl': 'copper', '.gbs': 'soldermask'}
#: the layer → the kind DKRed groups it under (KiCad layer names)
LAYER_KIND = {'F.Cu': 'copper', 'B.Cu': 'copper', 'F.Mask': 'soldermask', 'B.Mask': 'soldermask', 'F.Paste': 'paste', 'B.Paste': 'paste',
              'F.Silkscreen': 'silkscreen', 'B.Silkscreen': 'silkscreen', 'Edge.Cuts': 'outline', 'drill': 'drill', 'drill-map': 'drill-drawing'}


def rule_set_rows():
    return [{'name': FAB, 'fab': 'DKRed (DigiKey)', 'title': 'DKRed — DigiKey\'s PCB fabrication service (2- and 4-layer, red mask)', 'url': URL,
             'retrieved': RETRIEVED, 'accepted_extensions_json': json.dumps(ACCEPTED, sort_keys=True),
             'discrepancies': 'copper .gtl/.gbl and mask .gbs: on his upload-form screenshot, NOT in the page text (which lists ".bgs" — likely a '
                              'typo for .gbs); KiCad\'s Protel names are .gtl/.gbl/.gts/.gbs, so those are exported and marked `discrepancy` until the '
                              'upload form\'s verdict (pcb-2) is recorded as a DatasheetFact. A DigiKey forum thread (2025) reports 0.20 mm holes finished '
                              'at 0.25 mm within the stated plated tolerance (knob drill_margin_mil at pcb-2).',
             'notes': 'the rules are FabRule rows (rule_set = dkred); prices are quote rows (pcb-4), never these'}]


def rule_rows():
    return [{'name': '%s:%s' % (FAB, k), 'rule_set': FAB, 'key': k, 'op': op, 'value': v, 'unit': u, 'value_mm': round(mm, 4), 'source_text': src,
             'url': URL, 'retrieved': RETRIEVED, 'kicad_rule': dru_c or '—', 'polari_check': chk or '—', 'notes': ''}
            for k, op, v, u, mm, src, dru_c, chk in RULES]


def _rules(rules=None):
    return {r['key']: r for r in (rules or rule_rows())}


def dru(rules=None):
    """A `.kicad_dru` (KiCad custom rules, version 1) written FROM the FabRule rows — KiCad's DRC checks them."""
    R = _rules(rules)
    mm = lambda k: '%.4fmm' % R[k]['value_mm']  # noqa: E731
    lines = ['(version 1)',
             '# written by pcb.custom.fab_rules from the FabRule rows of %s (%s) — generated, edit the rows' % (FAB, URL),
             '(rule "%s_min_space" (constraint clearance (min %s)))' % (FAB, mm('min_space')),
             '(rule "%s_min_trace" (constraint track_width (min %s)))' % (FAB, mm('min_trace')),
             '(rule "%s_drill" (constraint hole_size (min %s) (max %s)))' % (FAB, mm('min_drill'), mm('max_drill')),
             '(rule "%s_via_hole" (condition "A.Type == \'Via\'") (constraint hole_size (min %s)))' % (FAB, mm('min_via_hole')),
             '(rule "%s_via_pad" (condition "A.Type == \'Via\'") (constraint via_diameter (min %s)))' % (FAB, mm('min_via_pad'))]
    return '\n'.join(lines) + '\n'


def board_facts(pcb_text):
    """What the row checks read from a `.kicad_pcb`: holes (pads + vias), via pads, pad sizes, track widths."""
    from pcb.custom import sexpr as S
    t = S.parse(pcb_text)
    holes, via_holes, via_pads, pads, widths = [], [], [], [], []
    for fp in S.find(t, 'footprint'):
        ref = S.prop(fp, 'Reference')
        for p in S.find(fp, 'pad'):
            size = S.find(p, 'size')
            if size:
                pads.append((min(S.num(size[0][1]), S.num(size[0][2] if len(size[0]) > 2 else size[0][1])), '%s pad %s' % (ref, p[1])))
            d = S.find(p, 'drill')
            if d:
                nums = [x for x in d[0][1:] if not isinstance(x, list) and x != 'oval']
                if nums and S.num(nums[0]) > 0:
                    holes.append((S.num(nums[0]), '%s pad %s' % (ref, p[1])))
    for v in S.find(t, 'via'):
        x, y, _ = S.xy(v)
        via_holes.append((S.num(S.value(v, 'drill')), 'via at %.2f,%.2f' % (x, y)))
        via_pads.append((S.num(S.value(v, 'size')), 'via at %.2f,%.2f' % (x, y)))
    for s in S.find(t, 'segment') + S.find(t, 'arc'):
        x, y, _ = S.xy(s, 'start')
        widths.append((S.num(S.value(s, 'width')), 'track at %.2f,%.2f (%s)' % (x, y, S.value(s, 'layer'))))
    return {'holes': holes + via_holes, 'via_holes': via_holes, 'via_pads': via_pads, 'pads': pads, 'widths': widths}


def check_board(board_row, pcb_text, rules=None, checker='polari fab rules (pcb.custom.fab_rules)'):
    """DrcResult rows (kind fab-rule): each checkable rule → a violation row per offending item, or ONE severity-none row saying
    what was checked and the extreme found. Rules with no row check are listed once as not checked here (never silently)."""
    R = _rules(rules)
    f = board_facts(pcb_text)
    b = board_row['name']
    out = []

    def row(key, severity, desc, items=(), x=0.0, y=0.0):
        out.append({'name': '%s:fab:%s:%d' % (b, key, len(out)), 'board': b, 'kind': 'fab-rule', 'checker': checker, 'severity': severity,
                    'rule': '%s:%s' % (FAB, key), 'description': desc, 'items_json': json.dumps(list(items)), 'x_mm': x, 'y_mm': y,
                    'report_sha256': '', 'engine_version': '', 'argv': '', 'source_date': '', 'at': ''})

    n = int(board_row.get('copper_layers') or 0)
    ok_layers = [int(v) for v in R['layers']['value'].split(',')]
    row('layers', 'none' if n in ok_layers else 'error', '%d copper layers — %s accepts %s' % (n, FAB, R['layers']['value']))
    w, h = float(board_row.get('width_mm') or 0), float(board_row.get('height_mm') or 0)
    lo, hi = R['board_min']['value_mm'], R['board_max']['value_mm']
    if not w or not h:
        row('board_min', 'error', 'no Edge.Cuts outline — the size cannot be checked')
    else:
        bad = [d for d in (w, h) if d < lo or d > hi]
        row('board_min' if any(d < lo for d in bad) else 'board_max', 'error' if bad else 'none',
            'outline %.3f x %.3f mm (%.3f x %.3f in) — %s accepts %.1f–%.1f in per side' % (w, h, w / INCH, h / INCH, FAB, lo / INCH, hi / INCH))
    t = float(board_row.get('thickness_mm') or 0)
    tol = R['tolerance']['value_mm']
    row('thickness', 'none' if abs(t - R['thickness']['value_mm']) <= tol else 'warning',
        'board thickness %.3f mm — %s builds %.3f mm (62 mil), tolerance %.3f mm' % (t, FAB, R['thickness']['value_mm'], tol))

    def extreme(key, items, mode, what):
        lim = R[key]['value_mm']
        if not items:
            row(key, 'none', 'no %s on the board — nothing to check' % what)
            return
        bad = [(v, it) for v, it in items if (v < lim - 1e-9 if mode == 'min' else v > lim + 1e-9)]
        for v, it in bad:
            row(key, 'error', '%s %.4f mm %s the %s %s %.4f mm (%s %s)' % (it, v, '<' if mode == 'min' else '>', FAB, mode, lim, R[key]['value'], R[key]['unit']),
                [{'description': it}])
        if not bad:
            v, it = (min if mode == 'min' else max)(items)
            row(key, 'none', '%s %s: %.4f mm (%s) — within the %s %s %.4f mm' % (mode == 'min' and 'smallest' or 'largest', what, v, it, FAB, mode, lim))

    extreme('min_trace', f['widths'], 'min', 'track width')
    extreme('min_drill', f['holes'], 'min', 'hole')
    extreme('max_drill', f['holes'], 'max', 'hole')
    extreme('min_via_hole', f['via_holes'], 'min', 'via hole')
    extreme('min_via_pad', f['via_pads'], 'min', 'via pad')
    extreme('min_pad', f['pads'], 'min', 'pad dimension')
    row('min_space', 'info', 'clearance (5 mil) is a geometry check: KiCad\'s DRC runs it with the .kicad_dru written from these rows (kind drc, '
                             'checker kicad-cli + dkred rules) — not reimplemented here')
    return out


def naming(filename, layer):
    """(accepted, fab_name, note) for one exported file name against the page's list (+ the screenshot's)."""
    ext = '.' + filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    kind = LAYER_KIND.get(layer)
    if kind is None:
        return 'n/a', '', 'not a fabrication layer DKRed lists (%s)' % (layer or ext)
    listed = ACCEPTED.get(kind, [])
    if ext in listed:
        return 'yes', ext, '%s is listed for %s on the DKRed page' % (ext, kind)
    if SCREENSHOT_ONLY.get(ext) == kind:
        return 'discrepancy', ext, ('%s is on his upload-form screenshot for %s but NOT in the page text (%s) — settled at the first upload (pcb-2)'
                                    % (ext, kind, ', '.join(listed)))
    return 'no', listed[0] if listed else '', '%s is not listed for %s (the page lists %s) — rename to %s for the upload' % (ext, kind, ', '.join(listed),
                                                                                                                          listed[0] if listed else '?')
