"""
@module electrodevice.custom.layout_edits

lay-1: A PERSON'S EDITS to a derived build, kept BESIDE the derived value. The derived layout (electrodevice.custom.layout_place) is recomputed every time and never overwritten; the edits
(`LayoutEdit` rows: config + board + subject + field) are applied on top, each part/wire that was changed carries `edit` = {derived: <the derived value>, who, note}, and the netlist gate
re-checks the edited layout, so a wrong edit is refused in words and a right one is accepted. Fields:
  holes   part:<ref>  the part's legs, in the order of its `legs` (a list of holes: r14e, rail:top:-:3)
          wire:<name> the wire's two ends [from, to] on the boards they are already on
  colour  wire:<name> a colour name (the effective colour; the scheme's colour stays as the derived one)
"""
import json
import re

from electrodevice.custom import board_family as BF
from electrodevice.custom import layout_colors as LCOL
from electrodevice.custom import layout_rows as LR
from electrodevice.custom.layout_words import LayoutRefused, hole_words

FIELDS = ('holes', 'colour')


def row_name(config, board, subject, field):
    return re.sub(r'[^A-Za-z0-9_.:@/-]+', '-', '%s@%s/%s/%s' % (config, board, subject, field))


def load(manager, config, board):
    out = []
    for r in LR.rows(manager, 'LayoutEdit'):
        if r.config == config and r.board == board:
            try:
                value = json.loads(r.value_json)
            except ValueError:
                value = None
            out.append({'name': r.name, 'subject': r.subject, 'field': r.field, 'value': value, 'who': r.who, 'note': r.note, 'created_at': r.created_at})
    return sorted(out, key=lambda e: (e['subject'], e['field']))


def _is_hole(tie):
    p = BF.parse_tie(tie)
    return p is not None and p[0] in ('hole', 'rail')


def check_edit(laid, subject, field, value):
    """Refuse (in words) an edit that cannot be applied to this layout; -> None when it can."""
    kind, _, name = subject.partition(':')
    if field not in FIELDS:
        raise LayoutRefused("an edit changes 'holes' or 'colour', not %r" % field)
    if kind == 'part':
        p = next((p for p in laid['placements'] if p['name'] == name), None)
        if p is None:
            raise LayoutRefused("no part %r in this layout (parts: %s)" % (name, ', '.join(x['name'] for x in laid['placements'])), status=404)
        if field != 'holes':
            raise LayoutRefused("a part has holes, not a colour: edit a wire's colour as wire:<name>")
        if not (isinstance(value, list) and len(value) == len(p['legs']) and all(isinstance(v, str) and _is_hole(v) for v in value)):
            raise LayoutRefused("%s has %d legs: give %d holes (like r14e), one per leg in this order: %s" % (name, len(p['legs']), len(p['legs']),
                                                                                                         ', '.join('%s %s' % (l['terminal'], l['name']) for l in p['legs'])))
    elif kind == 'wire':
        w = next((w for w in laid['wires'] if w['name'] == name), None)
        if w is None:
            raise LayoutRefused("no wire %r in this layout (wires: %s)" % (name, ', '.join(x['name'] for x in laid['wires'])), status=404)
        if field == 'colour':
            LCOL.check_colour(value)
        elif not (isinstance(value, list) and len(value) == 2 and all(isinstance(v, str) for v in value)):
            raise LayoutRefused("a wire has two ends: give [from, to] (a header pin or a hole each)")
    else:
        raise LayoutRefused("an edit's subject is part:<ref> or wire:<name>, not %r" % subject)


def apply(laid, edits):
    """Apply the edits on top of a DERIVED layout (a deep copy is changed; the derived one is untouched). -> (new layout, colour overrides {wire: colour}, [applied edit], [problem words])."""
    new = json.loads(json.dumps(laid))
    overrides, applied, problems = {}, [], []
    for e in edits:
        try:
            check_edit(new, e['subject'], e['field'], e['value'])
        except LayoutRefused as exc:
            problems.append('edit %s ignored: %s' % (e['name'], exc))
            continue
        kind, _, name = e['subject'].partition(':')
        if kind == 'wire' and e['field'] == 'colour':
            overrides[name] = e['value']
        elif kind == 'wire':
            w = next(w for w in new['wires'] if w['name'] == name)
            w['edit'] = {'derived': [w['from']['tie'], w['to']['tie']], 'who': e['who'], 'note': e['note']}
            w['from']['tie'], w['to']['tie'] = e['value']
        else:
            p = next(p for p in new['placements'] if p['name'] == name)
            derived = [l['hole'] for l in p['legs']]
            for leg, hole in zip(p['legs'], e['value']):
                parsed = BF.parse_tie(hole)
                leg['hole'] = hole
                if parsed[0] == 'hole':
                    leg['row'], leg['col'], leg['side'] = parsed[1], parsed[2], BF.side_of(parsed[2])
            first = {}
            for leg in p['legs']:
                first.setdefault(leg['terminal'], leg['hole'])
            p['ties'] = [first[t] for t in p['terminal_ids']]
            if p['internal']:
                p['internal'] = [[p['legs'][0]['hole'], p['legs'][1]['hole']], [p['legs'][2]['hole'], p['legs'][3]['hole']]]
            p['rows'] = sorted({l['row'] for l in p['legs'] if 'row' in l})
            p['edit'] = {'derived': derived, 'who': e['who'], 'note': e['note']}
        applied.append(e)
    return new, overrides, applied, problems


def occupancy(laid):
    """Findings for any hole used twice (a physical impossibility): -> [finding]."""
    seen, out = {}, []
    for p in laid['placements']:
        for l in p['legs']:
            seen.setdefault(l['hole'], []).append('%s (%s)' % (p['name'], l['name']))
    for w in laid['wires']:
        for end in ('from', 'to'):
            if w[end]['board'] == laid['board']:
                seen.setdefault(w[end]['tie'], []).append('wire %s' % w['name'])
    for hole, who in sorted(seen.items()):
        if len(who) > 1 and not hole.startswith('rail:'):
            out.append({'rule': 'hole-in-use', 'status': 'refuse', 'subject': hole, 'words': 'HOLE IN USE: %s is used by both %s' % (hole_words(hole), ' and '.join(who))})
    return out


def record(manager, config, board, laid, subject, field, value, who='', note='', clear=False):
    """Keep (or clear) one edit as a LayoutEdit row. Validates against the derived layout first. -> the row dict, or None when cleared."""
    from electrodevice.objects.layout.LayoutEdit import LayoutEdit
    name = row_name(config, board, subject, field)
    if clear:
        LR.remove(manager, 'LayoutEdit', name)
        return None
    check_edit(laid, subject, field, value)
    import datetime
    LR.upsert(manager, LayoutEdit, name, config=config, board=board, subject=subject, field=field, value_json=json.dumps(value), who=who, note=note,
              created_at=datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'))
    return {'name': name, 'config': config, 'board': board, 'subject': subject, 'field': field, 'value': value, 'who': who, 'note': note}
