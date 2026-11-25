"""
@module hwnocode.custom.schematic_derive

cb-1 (AI-Notes/plans/COMPONENT_BINDING_PLAN.md §3), DERIVED: the schematic components of a REAL circuit - the electrodevice
`CircuitDefinition` rows (its nets and parts) and the board's `BoardPinNet` rows (which board pin sits on which net, output or input) -
cut into the blocks a person names: one component per core part (a switch is a button, an LED a light), its ports where its lines meet
the board's pins, and its parts: the core part, the resistors on the way to a pin (series), a resistor to a rail on its pin's net (pull)
and a firmware pull the pin claims declare (an internal pull-up is a part of the schematic even though it sits inside the chip).

Nothing is typed here: the parts, values, pins and pulls come from the rows. A part kind not in CORE_KINDS is never a component of its
own; it joins the component whose line it sits on.

  components(circuit, board, soc, tables, claims, prefix)  -> {'SchematicComponent': [...], 'SchematicComponentPort': [...],
                                                             'SchematicComponentPart': [...], '_port_meta': {port: {net, role,
                                                             board_pin, pin_net}}}  (solve_state left 'unsolved': the
                                                             solver, hwnocode.custom.schematic_solve, decides it)
"""
from board.custom import board_pin_nets as BPN
from board.custom import electrical_check as EC

#: a circuit part kind -> (the component's intent, the core part's kind on the drawing)
CORE_KINDS = {'switch': ('button', 'pushbutton'), 'led': ('light', 'led')}
#: circuit part kinds drawn under another name
PART_KIND = {'switch': 'pushbutton', 'led': 'led', 'resistor': 'resistor', 'capacitor': 'capacitor', 'diode': 'diode'}
SIGNAL_ROLES = ('output', 'driver', 'input')
POWER_ROLES = ('power', 'supply')


def ref_of(part_name):
    """'ubc-sw1' -> 'SW1' (the reference on the drawing is the part's own name after its circuit prefix)."""
    return part_name.rsplit('-', 1)[-1].upper()


def canonical(board_pin):
    """'arduino-uno-r3:D2' -> 'D2'."""
    return (board_pin or '').rpartition(':')[2]


def _value(part):
    p = EC._params(part)
    if part.get('kind') == 'resistor' and p.get('ohms') is not None:
        return '%s ohm' % p['ohms']
    if part.get('kind') == 'capacitor' and p.get('farads') is not None:
        return '%s F' % p['farads']
    return ''


def _graph(nets, comps, pin_nets):
    """label -> {'row': net row, 'pins': [BoardPinNet], 'parts': [part]}."""
    by_label = {n['net']: {'row': n, 'pins': [], 'parts': []} for n in nets}
    for pn in pin_nets:
        row = next((n for n in nets if n['name'] == pn.get('circuit_net')), None)
        if row is not None:
            by_label[row['net']]['pins'].append(pn)
    for c in comps:
        for label in EC._pins(c):
            if label in by_label:
                by_label[label]['parts'].append(c)
    return by_label


def _is_ground(node):
    return any(p.get('role') == 'ground' for p in node['pins']) or node['row']['net'].upper() in ('GND', '0')


def _is_power(node):
    return any(p.get('role') in POWER_ROLES for p in node['pins'])


def _signal_pins(node):
    return [p for p in node['pins'] if p.get('role') in SIGNAL_ROLES and p.get('board_pin')]


def _walk(label, graph, core, depth=3):
    """From one of the core part's lines to the net that meets a board pin: [(net label, [resistors crossed])]. A two-pin resistor on
    the way is crossed (it is the component's own series part); a ground or power net ends the walk."""
    path, seen, here = [], {core['name']}, label
    for _ in range(depth + 1):
        node = graph.get(here)
        if node is None or _is_ground(node) or _is_power(node):
            return here, path
        if _signal_pins(node):
            return here, path
        nxt = [c for c in node['parts'] if c['name'] not in seen and c.get('kind') == 'resistor' and len(EC._pins(c)) == 2]
        if len(nxt) != 1:
            return here, path
        r = nxt[0]
        seen.add(r['name'])
        path.append(r)
        here = next(l for l in EC._pins(r) if l != here)
    return here, path


def _pull_resistors(node, graph, taken):
    """Resistors from this signal net to a power net: external pulls."""
    out = []
    for c in node['parts']:
        if c.get('kind') != 'resistor' or c['name'] in taken:
            continue
        others = [graph.get(l) for l in EC._pins(c) if l != node['row']['net']]
        if any(o is not None and _is_power(o) for o in others):
            out.append(c)
    return out


def components(circuit, board, soc, tables, claims=(), prefix=''):
    circ, nets, comps, pin_nets = EC.circuit_rows(tables, circuit)
    out = {'SchematicComponent': [], 'SchematicComponentPort': [], 'SchematicComponentPart': [], '_port_meta': {}}
    if circ is None:
        return out
    pin_nets = [p for p in pin_nets if p.get('board') == board or not p.get('board')]
    graph = _graph(nets, comps, pin_nets)
    claims_by_pin = {c.get('board_pin'): c for c in claims or ()}
    prefix = prefix or circuit
    for core in comps:
        if core.get('kind') not in CORE_KINDS:
            continue
        intent, core_kind = CORE_KINDS[core['kind']]
        name = '%s:%s' % (prefix, core['name'])
        ports, parts, taken = [], [], {core['name']}
        parts.append(_part(name, core, 'core', '', 0, 'circuit', 'the circuit\'s own %s (%s)' % (core['kind'], core['name'])))
        for label in EC._pins(core):
            end, crossed = _walk(label, graph, core)
            node = graph.get(end)
            if node is None:
                continue
            if _is_ground(node):
                if not any(p['kind'] == 'ground' for p in ports):
                    ports.append({'port': 'gnd', 'kind': 'ground', 'chip': '', 'pin': '', 'net': end, 'role': 'ground'})
                continue
            if _is_power(node):
                ports.append({'port': end.lower(), 'kind': 'supply', 'chip': '', 'pin': '', 'net': end, 'role': 'power'})
                continue
            signals = sorted(_signal_pins(node), key=lambda p: (0 if BPN.is_output(p.get('role')) else 1, p['board_pin']))
            for p in signals:
                ports.append({'port': canonical(p['board_pin']), 'kind': 'signal', 'chip': soc, 'pin': canonical(p['board_pin']),
                              'net': end, 'role': 'output' if BPN.is_output(p.get('role')) else 'input', 'board_pin': p['board_pin'],
                              'pin_net': p['name']})
            first = signals[0] if signals else None
            for r in crossed:
                taken.add(r['name'])
                parts.append(_part(name, r, 'series', canonical(first['board_pin']) if first else '', len(parts), 'circuit',
                                   'on the circuit: %s between the %s and %s' % (r['name'], core['kind'], end)))
            for r in _pull_resistors(node, graph, taken):
                taken.add(r['name'])
                parts.append(_part(name, r, 'pull', canonical(first['board_pin']) if first else '', len(parts), 'circuit',
                                   'on the circuit: %s from %s to a supply rail' % (r['name'], end)))
            for p in signals:
                claim = claims_by_pin.get(p['board_pin'])
                if claim and claim.get('pull') in ('up', 'down'):
                    pin = canonical(p['board_pin'])
                    parts.append({'name': '%s/RP%s' % (name, pin), 'component': name, 'ref': 'RP%s' % pin, 'role': 'pull',
                                  'part_kind': 'internal-pull-%s' % claim['pull'], 'value': '', 'port': pin, 'placed_by': 'firmware',
                                  'rule': "the firmware's PinClaim %s: pull '%s' (the chip's own pull resistor, inside the pin)" % (claim['name'], claim['pull']),
                                  'order': len(parts)})
        signal_ports = [p for p in ports if p['kind'] == 'signal']
        title = '%s %s' % (intent.capitalize(), ref_of(core['name']))
        out['SchematicComponent'].append({
            'name': name, 'title': title, 'intent': intent, 'core_part': core_kind, 'protocol': '', 'solve_state': 'unsolved',
            'solved_by': '', 'circuit': circuit, 'board': board,
            'description': '%s on %s, derived from the circuit %s: %s' % (title, ', '.join(p['pin'] for p in signal_ports) or 'no pin',
                                                                     circuit, (core.get('description') or '')[:160])})
        for i, p in enumerate(ports):
            pname = '%s/%s' % (name, p['port'])
            out['_port_meta'][pname] = {k: p[k] for k in ('net', 'role', 'board_pin', 'pin_net') if p.get(k)}
            out['SchematicComponentPort'].append({'name': pname, 'component': name, 'port': p['port'], 'kind': p['kind'],
                                                  'chip': p['chip'], 'pin': p['pin'], 'pin_source': 'chosen' if p['pin'] else '', 'order': i, 'net': p['net'],
                                                  'notes': ('%s on net %s (BoardPinNet %s)' % (p['role'], p['net'], p['pin_net'])) if p.get('pin_net')
                                                  else '%s net %s' % (p['role'], p['net'])})
        out['SchematicComponentPart'] += parts
    return out


def _part(component, part, role, port, order, placed_by, rule):
    return {'name': '%s/%s' % (component, ref_of(part['name'])), 'component': component, 'ref': ref_of(part['name']), 'role': role,
            'part_kind': PART_KIND.get(part.get('kind'), part.get('kind', '')), 'value': _value(part), 'port': port, 'placed_by': placed_by,
            'rule': rule, 'order': order, 'notes': 'CircuitComponentDefinition:%s' % part['name']}
