"""
@module electrodevice.custom.layout_gate

lay-1: THE NETLIST GATE. A layout is accepted only when the nets it COMPILES to (electrodevice.custom.layout_compile, through electrodevice.breadboard_netlist_seed) EQUAL the nets of the
design (the circuit rows + the BoardPin refs: layout_sources.design_of). Equal means the same partition of terminals: every design net is exactly one group in the layout, no more, no less.
Otherwise the layout is REFUSED, naming each mismatching net and what is wrong with it; the electrical rules (electrodevice.custom.layout_rules) run on the same groups and their findings are
part of the verdict. The verdict is words first (`words`), data second.
"""
from electrodevice.custom import layout_compile as LC
from electrodevice.custom import layout_rules as RU
from electrodevice.custom.layout_rules import terminal_words
from electrodevice.custom.layout_words import join_words


def _design_net_of(design):
    return {t: n for n, ts in design['nets'].items() for t in ts}


def compare(design, groups):
    """-> [mismatch {net, design, layout, words}] for every design net the layout does not reproduce exactly, plus one for each terminal the layout adds that the design does not know."""
    net_of = _design_net_of(design)
    out = []
    in_layout = {t for g in groups for t in g}
    for net, terms in sorted(design['nets'].items()):
        want = set(terms)
        have = [set(g) for g in groups if set(g) & want]
        missing = sorted(t for t in want if t not in in_layout)
        if len(have) == 1 and have[0] == want:
            continue
        parts = []
        if len(have) > 1:
            parts.append('the design joins %s, but in the layout %s are not connected to each other' % (join_words([terminal_words(t) for t in sorted(want)]),
                                                                                                      ' and '.join('{%s}' % ', '.join(terminal_words(t) for t in sorted(h & want)) for h in have)))
        for h in have:
            extra = sorted(h - want)
            if extra:
                parts.append('%s share%s it in the layout but belong%s to %s' % (join_words([terminal_words(t) for t in extra]), 's' if len(extra) == 1 else '', 's' if len(extra) == 1 else '',
                                                                                  join_words(sorted({'net ' + net_of.get(t, '(no design net)') for t in extra}))))
        if missing:
            parts.append('%s %s not placed in the layout' % (join_words([terminal_words(t) for t in missing]), 'is' if len(missing) == 1 else 'are'))
        out.append({'net': net, 'design': sorted(want), 'layout': [sorted(h) for h in have], 'words': 'net %s is wrong: %s' % (net, '; '.join(parts))})
    return out


def gate(manager, design, laid, board, header_board):
    """-> the verdict {ok, equal, words, mismatches, findings, design_nets, layout_groups, nets_compared}."""
    comp = LC.compile_nets(manager, design, laid, board, header_board)
    mism = compare(design, comp['groups'])
    findings = RU.check(design, comp['groups'])
    refused = [f for f in findings if f['status'] == 'refuse']
    ok = not mism and not refused
    if ok:
        words = "OK: the layout's %d nets equal the design's %d nets (circuit %s + the BoardPin refs of config %s), and the electrical rules hold" % (len(design['nets']), len(design['nets']), design['circuit'], design['config'])
    else:
        bits = [f['words'] for f in refused] + [m['words'] for m in mism]
        words = 'REFUSED: ' + ' | '.join(bits)
    return {'ok': ok, 'equal': not mism, 'words': words, 'mismatches': mism, 'findings': findings, 'design_nets': design['nets'], 'layout_groups': comp['groups'],
            'nets_compared': len(design['nets']), 'suggestions': comp['suggestions']}
