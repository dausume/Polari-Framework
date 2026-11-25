"""
@module hwnocode.custom.schematic_rules

cb-3 (AI-Notes/plans/COMPONENT_BINDING_PLAN.md §5): THE CONDITIONING RULES of one derived schematic component, and the board's own
electrical findings (board.custom.electrical_check (a)-(e), electrical_hw (f)-(j)) sorted onto the component they are about.

Four conditioning rules, each per component, each deciding placed | not-needed | needed in words from the rows in hand:
  pull    a switch on an input pin needs a pull (an open contact leaves the pin floating): placed when the circuit carries a resistor to a
          rail or the firmware's PinClaim sets the chip's own pull; cross-read with electrical rule (e) pull_defined
  series  an LED needs a current-limiting resistor between the pin and the LED: placed when one is on the way (rule (a) led_current
          gives the numbers); an input on a switch carries no load
  guard   a diode against current flowing back into a pin is needed only when something other than this board's own pins can drive the
          component's nets (another board, a supply): not-needed when only this board and ground reach them (one board, one logic
          level: rule (d) level_compatible)
  filter  an input from a mechanical contact bounces: not-needed when the firmware debounces it (the FirmwareVariant's own
          debounce_ms knob), else a filter capacitor at the pin is needed (its value undetermined until the switch's bounce is cited);
          an input driven by this board's own output on one wire has no contact to bounce
Nothing here guesses a number: a part the rule wants but cannot size is `needed` with the value undetermined, and the component is
blocked until a person or a later rule decides it. What a rule does not model (long wires, outside noise, ESD) is said in its words.

  conditioning(component, ports, parts, port_meta, tables_view, knobs, variant)  -> [check, ...]
  electrical(component, ports, parts, findings)                                  -> [check, ...] (the findings about this component)
  verdict(checks)                                                                -> (solve_state, words)
"""
from board.custom import board_pin_nets as BPN

RULE_ORDER = ('pull', 'series', 'guard', 'filter')
BLOCKING = ('needed', 'refuse')


def _check(component, rule, status, subject, detail, part='', cite=''):
    return {'component': component['name'], 'rule': rule, 'status': status, 'subject': subject, 'detail': detail, 'part': part, 'cite': cite}


def _signal(ports):
    return [p for p in ports if p.get('kind') == 'signal']


def _parts(parts, role, port=None):
    return [p for p in parts if p.get('role') == role and (port is None or p.get('port') == port)]


def _rule_pull(c, ports, parts, meta, knobs):
    out = []
    if c['core_part'] != 'pushbutton':
        return [_check(c, 'pull', 'not-needed', c['title'], 'an %s is driven by its pin; nothing on its line is left floating' % c['core_part'])]
    for p in _signal(ports):
        if meta.get(p['name'], {}).get('role') != 'input':
            continue
        have = _parts(parts, 'pull', p['port'])
        if have:
            out.append(_check(c, 'pull', 'placed', p['port'], '%s: %s' % (have[0]['ref'], have[0]['rule']), part=have[0]['name']))
        else:
            out.append(_check(c, 'pull', 'needed', p['port'],
                              'the switch leaves %s floating while it is open: define a pull - the chip\'s own pull-up (a PinClaim pull \'up\' in '
                              'the firmware) or a resistor from the pin to the rail (its value undetermined: no rule sizes it yet)' % p['port']))
    return out


def _rule_series(c, ports, parts, meta, knobs):
    if c['core_part'] != 'led':
        return [_check(c, 'series', 'not-needed', c['title'], 'the pin is an input: the switch only pulls it to ground through the pull, '
                                                             'so there is no load current to limit')]
    have = _parts(parts, 'series')
    outs = [p['port'] for p in _signal(ports) if meta.get(p['name'], {}).get('role') == 'output']
    if have:
        r = have[0]
        return [_check(c, 'series', 'placed', ', '.join(outs) or c['title'], '%s %s between %s and the LED (%s)' % (
            r['ref'], r['value'] or '(value not on the circuit)', ', '.join(outs) or 'the pin', r['rule']), part=r['name'])]
    return [_check(c, 'series', 'needed', ', '.join(outs) or c['title'],
                   'an LED straight on a pin draws whatever the pin can give: a series resistor is needed between the pin and the LED '
                   '(its value undetermined until the LED\'s forward voltage and current are cited)')]


def _rule_guard(c, ports, parts, meta, view):
    board = c['board']
    nets = sorted({meta[p['name']]['net'] for p in ports if p['name'] in meta and p.get('kind') == 'signal'})
    others = []
    for net in nets:
        for pn in view['pin_nets_by_label'].get(net, ()):
            if pn.get('board') and pn.get('board') != board:
                others.append('%s (another board)' % pn['name'])
            elif pn.get('role') in ('power', 'supply'):
                others.append('%s (a supply)' % pn['name'])
    pins = ', '.join(p['port'] for p in _signal(ports))
    have = _parts(parts, 'guard')
    if others:
        if have:
            return [_check(c, 'guard', 'placed', pins, '%s guards %s against %s' % (have[0]['ref'], pins, ', '.join(others)), part=have[0]['name'])]
        return [_check(c, 'guard', 'needed', pins, 'something other than this board drives %s: %s - a guard diode is needed so current cannot '
                                                   'flow back into the pin (its part undetermined: no rule picks one yet)' % (', '.join(nets), ', '.join(others)))]
    return [_check(c, 'guard', 'not-needed', pins or c['title'],
                   'only this board\'s own pins and ground reach %s (net %s): no other supply or board can push current back into a pin - '
                   'one board, one logic level (electrical rule level_compatible). Not modelled: ESD on a hand-touched part, which the '
                   'board\'s ESD protection rows cover separately' % (pins or 'its lines', ', '.join(nets) or '-'))]


def _rule_filter(c, ports, parts, meta, view, knobs, variant):
    out = []
    for p in _signal(ports):
        m = meta.get(p['name'], {})
        if m.get('role') != 'input':
            continue
        have = _parts(parts, 'filter', p['port'])
        if have:
            out.append(_check(c, 'filter', 'placed', p['port'], '%s: %s' % (have[0]['ref'], have[0]['rule']), part=have[0]['name']))
            continue
        drivers = [pn for pn in view['pin_nets_by_label'].get(m.get('net'), ()) if BPN.is_output(pn.get('role')) and pn.get('board') == c['board']]
        if c['core_part'] != 'pushbutton' and drivers:
            out.append(_check(c, 'filter', 'not-needed', p['port'], '%s reads the line this board\'s own %s drives on one wire: no contact to bounce. '
                                                                    'Not modelled: noise picked up on a long wire' % (p['port'], drivers[0]['board_pin'].rpartition(':')[2])))
            continue
        ms = knobs.get('debounce_ms')
        if c['core_part'] == 'pushbutton' and isinstance(ms, (int, float)) and ms > 0:
            out.append(_check(c, 'filter', 'not-needed', p['port'], 'the contact bounce on %s is filtered in the firmware: debounce_ms %s (FirmwareVariant '
                                                                    '%s knobs) - no filter capacitor is needed at the pin. Not modelled: noise picked '
                                                                    'up on a long wire' % (p['port'], ms, variant), cite='FirmwareVariant %s knobs_json' % variant))
            continue
        out.append(_check(c, 'filter', 'needed', p['port'], 'nothing filters the input on %s: a filter capacitor at the pin or a firmware debounce is needed '
                                                            '(the capacitor\'s value undetermined: the switch\'s bounce time is not cited)' % p['port']))
    if not out:
        out.append(_check(c, 'filter', 'not-needed', c['title'], 'no input pin: nothing comes in to smooth'))
    return out


def conditioning(component, ports, parts, port_meta, view, knobs, variant):
    out = []
    out += _rule_pull(component, ports, parts, port_meta, knobs)
    out += _rule_series(component, ports, parts, port_meta, knobs)
    out += _rule_guard(component, ports, parts, port_meta, view)
    out += _rule_filter(component, ports, parts, port_meta, view, knobs, variant)
    return out


def tokens(component, ports, parts, port_meta):
    """The words a finding's subject may use for this component: its pins (D2, arduino-uno-r3:D2), nets and circuit parts."""
    t = set()
    for p in ports:
        m = port_meta.get(p['name'], {})
        if p.get('kind') == 'signal':
            t |= {p['pin'], m.get('board_pin', '')}
            t.add(m.get('net', ''))
    for p in parts:
        n = (p.get('notes') or '')
        if n.startswith('CircuitComponentDefinition:'):
            t.add(n.split(':', 1)[1])
    return {x for x in t if x}


def _subject_words(subject):
    import re
    return set(re.split(r'[\s,()>]+|->', subject or '')) - {''}


def electrical(component, ports, parts, port_meta, findings):
    mine = tokens(component, ports, parts, port_meta)
    out = []
    for f in findings:
        if _subject_words(f.get('subject')) & mine:
            out.append(_check(component, f['rule'], f['status'], f.get('subject', ''), f.get('detail', ''), cite=f.get('cite', '')))
    return out


def claimed(findings, checks):
    """The findings no component took: they are about the whole solution."""
    taken = {(c['rule'], c['subject']) for c in checks}
    return [f for f in findings if (f['rule'], f.get('subject', '')) not in taken]


def verdict(checks):
    """(solve_state, words) of one component from its checks."""
    blocking = [c for c in checks if c['status'] in BLOCKING]
    open_numbers = [c for c in checks if c['status'] == 'undetermined']
    cond = [c for c in checks if c['rule'] in RULE_ORDER]
    said = ', '.join('%s %s' % (c['rule'], c['status']) for c in cond)
    tail = ('; %d number%s not cited (named in its checks)' % (len(open_numbers), '' if len(open_numbers) == 1 else 's')) if open_numbers else ''
    if blocking:
        return 'blocked', 'blocked - %s%s' % ('; '.join('%s %s on %s' % (c['rule'], c['status'], c['subject']) for c in blocking), tail)
    return 'solved', 'solved - %s%s' % (said, tail)
