"""
@module board.custom.part_fixes

drv-2 / drv-3 (AI-Notes/plans/DRIVERS_AND_ESD_PLAN.md): WHAT FIXES A DRIVE FINDING, AND WHOLE-PART BUDGETS - each catalogue part judged against every
cited number (`fits`), and each part's total_ma against what its pins carry (re-exported by board.custom.part_boards).

  suggestions(nets, manager)   for each over-voltage / under-voltage / drive-shortfall finding, the catalogue parts that fix it, with why
  budgets(nets, manager)       one row per part with a whole-part budget; over when its pins carry more
"""
UNKNOWN = -1.0


def _n(r, k):
    v = r.get(k)
    return float(v) if v is not None else UNKNOWN


def _fixes(finding, members, cat):
    """Catalogue parts whose cited contract fixes one finding, each with the evidence in words; `fits` says whether every cited number agrees."""
    from board.custom.part_boards import REGULATORS, contract_words   # part_boards re-exports this module: import it late
    out = []
    kind = finding['kind']
    if kind == 'drive-shortfall' and finding.get('from_supply'):
        need, volts = finding['need_ma'], finding.get('source_volts', UNKNOWN)
        for r in cat:
            if r['kind'] not in REGULATORS or _n(r, 'out_source_ma') < need:
                continue
            same = volts < 0 or abs(_n(r, 'out_volts') - volts) < 0.05 * max(volts, 1e-9)
            out.append({'part': r['name'], 'kind': r['kind'],
                        'why': 'a %s giving %g V at up to %g mA (need %g mA) from a %g .. %g V input%s%s'
                               % (r['kind'], _n(r, 'out_volts'), _n(r, 'out_source_ma'), need, _n(r, 'supply_min_v'), _n(r, 'supply_max_v'),
                                  '' if same else ' - NOT the net\'s %g V' % volts, ('; needs %s' % r['needs']) if r.get('needs') else ''),
                        'fits': same and not r.get('needs', '').startswith('its inductor'), 'source': r['document'] or r['origin']})
    elif kind == 'drive-shortfall':
        need, level = finding['need_ma'], finding.get('source_volts', UNKNOWN)
        for r in cat:
            sink, src = _n(r, 'out_sink_ma'), _n(r, 'out_source_ma')
            if r['kind'] in ('load',) + REGULATORS or max(sink, src) < need:
                continue
            ok_level = level < 0 or 0 <= _n(r, 'on_volts') <= level
            out.append({'part': r['name'], 'kind': r['kind'], 'why': ('its outputs %s up to %g mA (need %g mA); its input turns on from %s and draws %s - %s'
                                                                       % ('sink' if sink >= src else 'source', max(sink, src), need,
                                                                          ('%g V' % _n(r, 'on_volts')) if _n(r, 'on_volts') >= 0 else 'an uncited level',
                                                                          ('%g mA' % _n(r, 'draw_ma')) if _n(r, 'draw_ma') >= 0 else 'an uncited current',
                                                                          'the driving pin\'s %g V reaches it' % level if ok_level and level >= 0 else
                                                                          'check the driving level' if ok_level else
                                                                          'NOT reached by the driving pin\'s %g V' % level)),
                        'fits': ok_level, 'source': r['document'] or r['origin']})
    elif kind == 'under-voltage':
        driven = finding.get('driven_volts', UNKNOWN)
        for r in cat:
            if r['kind'] not in ('level-shifter', 'buffer'):
                continue
            on, high = _n(r, 'on_volts'), _n(r, 'out_volts')
            fits = on >= 0 and driven >= 0 and on <= driven and high >= finding.get('on_volts', 0)
            out.append({'part': r['name'], 'kind': r['kind'], 'why': ('its input turns on from %s (the net reaches %s) and its output drives high to %s (%s needed) '
                                                                       '- %s' % (('%g V' % on) if on >= 0 else 'an uncited level',
                                                                                 ('%g V' % driven) if driven >= 0 else 'an unknown level',
                                                                                 ('%g V' % high) if high >= 0 else 'an uncited level',
                                                                                 '%g V' % finding.get('on_volts', 0), contract_words(r))),
                        'fits': fits, 'source': r['document'] or r['origin']})
    elif kind == 'over-voltage':
        net_v, pin_v = finding.get('net_volts', UNKNOWN), finding.get('pin_volts', UNKNOWN)
        for r in cat:
            if r['kind'] not in ('level-shifter', 'buffer'):
                continue
            takes, high = _n(r, 'in_max_v'), _n(r, 'out_volts')
            fits = takes >= net_v >= 0 and 0 <= high <= pin_v and _n(r, 'out_max_v') <= max(pin_v, 0) + 0.5
            out.append({'part': r['name'], 'kind': r['kind'], 'why': ('its inputs take up to %s (the net carries %s); its output drives high to %s (the pin takes '
                                                                       '%s)%s' % (('%g V' % takes) if takes >= 0 else 'an uncited level', '%g V' % net_v,
                                                                                  ('%g V' % high) if high >= 0 else 'an uncited level', '%g V' % pin_v,
                                                                                  '' if fits else ' - it does NOT bring the level down to the pin\'s')),
                        'fits': fits, 'source': r['document'] or r['origin']})
    if kind in ('over-voltage', 'under-voltage') and not any(x['fits'] for x in out):
        out.append({'part': '', 'kind': 'level-shifter', 'why': 'no catalogue part fits this level change yet - define one (POST /api/board/parts) from '
                                                                'its datasheet', 'fits': False, 'source': ''})
    return out


def budgets(nets, manager=None):
    """drv-3: each part on the bench against its whole-part budget (total_ma, e.g. the ULN2003A's 2.5 A total emitter current): the sum, over the nets
    its outputs / regulated pins are on, of what the OTHER footholds draw. One row per part with a budget; a finding when the sum is above it."""
    from board.custom.part_boards import part
    sums = {}
    for n in nets:
        for m in n['members']:
            if m.get('definition_kind') != 'part' or m['direction'] not in ('out', 'supply') or (m['direction'] == 'supply' and m['rail_volts'] <= 0):
                continue
            draw = sum(x['draw_ma'] for x in n['members'] if x['board'] != m['board'] and x.get('draw_ma', -1.0) > 0)
            sums.setdefault((m['board'], m['definition']), []).append((m['foothold'], n['net'], draw))
    rows = []
    for (board, name), feet in sorted(sums.items()):
        r = part(name, manager) or {}
        total = _n(r, 'total_ma')
        if total < 0:
            continue
        need = sum(d for _, _, d in feet)
        rows.append({'board': board, 'part': name, 'need_ma': need, 'total_ma': total, 'over': need > total,
                     'words': '%s (%s): its pins carry %g mA in all (%s) against its %g mA total (%s)'
                              % (board, name, need, ', '.join('pin %s %g mA' % (f, d) for f, _, d in feet if d > 0) or 'nothing drawn', total,
                                 r.get('document') or r.get('origin', ''))})
    return rows


def suggestions(nets, manager=None):
    from board.custom.part_boards import catalogue
    cat = catalogue(manager)
    rows = []
    for n in nets:
        for f in n['findings']:
            if f['kind'] not in ('drive-shortfall', 'over-voltage', 'under-voltage'):
                continue
            for s in _fixes(f, n['members'], cat) or [{'part': '', 'kind': '', 'why': 'no catalogue part fixes this yet', 'fits': False, 'source': ''}]:
                rows.append(dict(s, net=n['net'], finding=f['kind'], problem=f['words']))
    for b in budgets(nets, manager):
        if b['over']:
            rows.append({'part': '', 'kind': '', 'why': 'split the load across a second %s, or use a part with a larger total' % b['part'], 'fits': False,
                         'source': '', 'net': '(the whole part)', 'finding': 'group-budget', 'problem': b['words']})
    return rows
