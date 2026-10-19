"""
@module electrodevice.custom.layout_rules

lay-1: the ELECTRICAL RULES a layout is checked against, read off the layout's own compiled groups (electrodevice.custom.layout_compile): which terminals share a net as built.
  shorted        two supplies/outputs joined, or a two-lead part with both leads on one net (the part does nothing)
  series-resistor an LED whose anode sits on the same net as a header output pin or the supply, with nothing in between (the kit book: an LED needs a series resistor to limit current)
  led-polarity   an LED whose anode is on the ground side or whose cathode is on the output/supply side (current flows anode -> cathode only)
A finding is {rule, status, subject, words}. status is `refuse` (the layout must not be built as it is) or `ok` (the rule was checked and holds). Nothing is guessed: a rule that cannot be read
off the layout (no LED in the design) is simply not listed.
"""
from electrodevice.custom.layout_words import join_words


def terminal_words(tid):
    """'LED1.anode' -> "LED1's anode"; 'R1.2' -> 'R1 lead 2'; 'SW1.1' -> 'SW1 contact 1'; 'hdr:D6' -> 'pin D6'."""
    if tid.startswith('hdr:'):
        return 'pin %s' % tid[4:]
    ref, _, name = tid.partition('.')
    if name in ('1', '2'):
        return '%s %s %s' % (ref, 'contact' if ref.startswith('SW') else 'lead', name)
    return "%s's %s" % (ref, name)


def _group_of(groups, tid):
    return next((g for g in groups if tid in g), [tid])


def _roles(design):
    """header terminal id -> role (output | input | ground | supply)."""
    out = {}
    for atts in design['attach'].values():
        for a in atts:
            out['hdr:%s' % a['pin']] = a['role']
    for s in design.get('supply_nets') or []:
        out['hdr:+5V'] = 'supply'
    return out


def check(design, groups):
    """-> [finding]. `groups` is the layout's partition (layout_compile.compile_nets()['groups'])."""
    findings, roles = [], _roles(design)
    drivers = lambda g: [t for t in g if roles.get(t) in ('output', 'supply')]   # noqa: E731
    grounds = lambda g: [t for t in g if roles.get(t) == 'ground']   # noqa: E731
    for g in groups:
        pw = [t for t in g if roles.get(t) in ('output', 'supply', 'ground')]
        bad = [t for t in pw if roles[t] != 'input']
        kinds = {roles[t] for t in bad}
        if len(bad) > 1 and (len(kinds) > 1 or kinds == {'output'}):
            findings.append({'rule': 'shorted', 'status': 'refuse', 'subject': join_words(sorted(terminal_words(t) for t in bad)),
                             'words': 'SHORT: %s are joined on one net in the layout (%s); a wire or a part lead is bridging them' % (join_words(sorted(terminal_words(t) for t in bad)),
                                                                                                                                     join_words(sorted(roles[t] for t in bad)))})
    for c in design['components']:
        t = [x['id'] for x in c['terminals']]
        if c['kind'] != 'switch' and len(t) == 2 and _group_of(groups, t[0]) == _group_of(groups, t[1]) and t[0] in {x for g in groups for x in g}:
            findings.append({'rule': 'shorted', 'status': 'refuse', 'subject': c['ref'], 'words': 'SHORT: both leads of %s are on the same net, so it is shorted out and does nothing' % c['ref']})
    for c in design['components']:
        if c['kind'] != 'led':
            continue
        anode, cathode = '%s.anode' % c['ref'], '%s.cathode' % c['ref']
        ga, gc = _group_of(groups, anode), _group_of(groups, cathode)
        problems = []
        if grounds(ga) and not drivers(ga):
            problems.append("%s is IN BACKWARDS: its anode (the longer leg) is on the ground side (%s) - current can only flow from the anode to the cathode, so it will stay dark"
                            % (c['ref'], join_words(sorted(terminal_words(t) for t in grounds(ga)))))
        if drivers(gc) and not grounds(gc):
            problems.append("%s is IN BACKWARDS: its cathode (the shorter leg) is on the driven side (%s) - current can only flow from the anode to the cathode" % (c['ref'], join_words(sorted(terminal_words(t) for t in drivers(gc)))))
        if problems:
            findings.append({'rule': 'led-polarity', 'status': 'refuse', 'subject': c['ref'], 'words': '; '.join(problems)})
        else:
            findings.append({'rule': 'led-polarity', 'status': 'ok', 'subject': c['ref'], 'words': '%s: anode toward the driven side, cathode toward ground' % c['ref']})
        if drivers(ga):
            findings.append({'rule': 'series-resistor', 'status': 'refuse', 'subject': c['ref'],
                             'words': "NO SERIES RESISTOR: %s's anode is on the same net as %s with nothing between them. An LED needs a series resistor to limit its current "
                                      "(KitPart arduino-starter-kit:led, driver_needed); put the resistor between the pin and the anode" % (c['ref'], join_words(sorted(terminal_words(t) for t in drivers(ga))))})
        else:
            findings.append({'rule': 'series-resistor', 'status': 'ok', 'subject': c['ref'], 'words': '%s has a part between the driven pin and its anode' % c['ref']})
    return findings
