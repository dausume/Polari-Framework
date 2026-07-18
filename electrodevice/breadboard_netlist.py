"""
@module electrodevice.breadboard_netlist

ncg-5: the breadboard CONNECTIVITY COMPILER — placements + jumpers
in, a runnable netlist out, through the same seam as every other
compiler. Tie points map to per-board nets ('bb-demo-a' r5 left
strip -> net bb_demo_a_r5l); jumpers UNION nets across boards
(union-find, canonical smallest name); the 'gnd' rail is SPICE
ground everywhere. A populated board can also re-wrap as a .subckt
with named external pins (board-as-component): port mapping happens
at the PIN level through the same union-find the body uses — never
by rewriting rendered text.

Honesty: a tie point outside a board's rows (placements AND jumpers)
is a plain error naming the owning row; a jumper whose far end
touches a board NOT in the run set is a SUGGESTION on the result
(include the board or remove the jumper — the simulated wiring
otherwise silently diverges from the physical wiring); an unknown
analysis type is a plain error, mirroring circuit_netlist.
"""

import json

from electrodevice.circuit_netlist import (_device_card,
                                           _element_line, _PREFIX,
                                           run_netlist)

_RAILS = ('vplus', 'gnd')


def _rows(manager, class_name):
    table = (manager.objectTables or {}).get(class_name, {})
    return list(table.values()) if isinstance(table, dict) else list(table)


def tie_net(board, tie):
    """One tie point -> its net name. 'gnd' is global ground."""
    board_row = board if isinstance(board, str) else board.name
    ident = board_row.replace('-', '_')
    if tie == 'gnd':
        return '0'
    if tie == 'vplus':
        return f'{ident}_vplus'
    if (len(tie) >= 3 and tie[0] == 'r' and tie[-1] in 'LR'
            and tie[1:-1].isdigit()):
        return f'{ident}_r{int(tie[1:-1])}{tie[-1].lower()}'
    raise ValueError(
        f"tie point {tie!r} on board '{board_row}' is not "
        f"'r<N>L'/'r<N>R'/'vplus'/'gnd'")


def _validate_tie(board_row, tie, owner):
    """`owner` names the row at fault ("placement 'x'" /
    "jumper 'y'" / "external pin 'z'")."""
    if tie in _RAILS:
        return
    row_num = int(tie[1:-1]) if tie[1:-1].isdigit() else -1
    rows = int(getattr(board_row, 'rows', 30))
    if not 1 <= row_num <= rows:
        raise ValueError(
            f"{owner}: tie {tie!r} is outside "
            f"board '{board_row.name}' (rows 1..{rows})")


class _Unions:
    """Union-find over net names; canonical = smallest, so '0'
    (ground) always wins its group."""

    def __init__(self):
        self.parent = {}

    def find(self, net):
        self.parent.setdefault(net, net)
        while self.parent[net] != net:
            self.parent[net] = self.parent[self.parent[net]]
            net = self.parent[net]
        return net

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            keep, drop = sorted((ra, rb))
            self.parent[drop] = keep

    def resolve(self, net):
        return self.find(net)


def _board_map(manager, board_names):
    boards = {getattr(b, 'name', ''): b
              for b in _rows(manager, 'BreadboardDefinition')}
    missing = [n for n in board_names if n not in boards]
    if missing:
        raise ValueError(f'unknown breadboard(s): {missing} — known: '
                         f'{sorted(boards)}')
    return {n: boards[n] for n in board_names}


def _jumper_unions(manager, boards):
    """(unions, suggestions). Jumpers with BOTH ends in the run set
    union their nets (tie range validated, naming the jumper); a
    jumper whose far end is outside the run set becomes a suggestion
    — the physical wire exists, the simulation would silently omit
    it."""
    unions = _Unions()
    suggestions = []
    for jumper in _rows(manager, 'BoardJumper'):
        a = getattr(jumper, 'board_a', '')
        b = getattr(jumper, 'board_b', '')
        inside = [x for x in (a, b) if x in boards]
        if not inside:
            continue
        if len(inside) < 2:
            other = b if a in boards else a
            suggestions.append({
                'knob': 'BoardJumper',
                'action': f"jumper '{getattr(jumper, 'name', '')}' "
                          f"also touches board '{other}', which is "
                          f'not in this run — include that board or '
                          f'remove the jumper (the simulated wiring '
                          f'otherwise omits a physical wire)'})
            continue
        owner = f"jumper '{getattr(jumper, 'name', '')}'"
        _validate_tie(boards[a], jumper.tie_a, owner)
        _validate_tie(boards[b], jumper.tie_b, owner)
        unions.union(tie_net(boards[a], jumper.tie_a),
                     tie_net(boards[b], jumper.tie_b))
    return unions, suggestions


def _board_elements(manager, boards, unions, port_by_net=None):
    """THE one placement walk both renderers share -> (cards, lines,
    net_by_placement, needs_led_model). `port_by_net` maps a
    CANONICAL net name to a .subckt port name — applied at the pin
    list, before the element line is rendered, so element VALUES can
    never be corrupted by port naming."""
    port_by_net = port_by_net or {}
    cards, lines, needs_led_model = [], [], False
    net_by_placement = {}
    placements = sorted(
        (p for p in _rows(manager, 'ComponentPlacement')
         if getattr(p, 'board_name', '') in boards),
        key=lambda p: getattr(p, 'name', ''))
    if not placements:
        raise ValueError(f'no ComponentPlacement rows on boards '
                         f'{sorted(boards)}')
    for placement in placements:
        kind = getattr(placement, 'kind', '')
        if kind not in _PREFIX:
            kinds = ', '.join(sorted(_PREFIX))
            raise ValueError(
                f"placement '{placement.name}': unknown kind "
                f"'{kind}' (kinds: {kinds})")
        board_row = boards[placement.board_name]
        params = json.loads(getattr(placement, 'params_json', '{}')
                            or '{}')
        ties = json.loads(getattr(placement, 'tiepoints_json', '[]')
                          or '[]')
        pins = []
        for tie in ties:
            _validate_tie(board_row, tie,
                          f"placement '{placement.name}'")
            net = unions.resolve(tie_net(board_row, tie))
            pins.append(port_by_net.get(net, net))
        net_by_placement[placement.name] = pins
        sub = None
        if kind == 'device':
            card, sub = _device_card(manager, placement.device_name)
            if card not in cards:
                cards.append(card)
        if kind in ('diode', 'led') \
                and params.get('model', 'polari_led') == 'polari_led':
            needs_led_model = True
        lines.append(_element_line(placement, pins, params, sub))
    return cards, lines, net_by_placement, needs_led_model


def _control_block(analyses, probes, lines):
    """Mirror circuit_netlist exactly: op probes one print per line,
    tran gets ' uic' when any element carries an initial condition,
    anything else is a plain error — never silently dropped."""
    control = ['.control']
    uses_ic = any('ic=' in line for line in lines)
    for analysis in (analyses or [{'type': 'op'}]):
        if not isinstance(analysis, dict) or 'type' not in analysis:
            raise ValueError(
                f'analysis entries must be dicts with a "type" — '
                f'got {analysis!r}')
        if analysis['type'] == 'op':
            control.append('op')
            control += [f'print {p}' for p in (probes or [])]
        elif analysis['type'] == 'tran':
            if 'args' not in analysis:
                raise ValueError(
                    'tran analysis needs "args" (e.g. "0.1m 60m")')
            control.append(f"tran {analysis['args']}"
                           + (' uic' if uses_ic else ''))
            if analysis.get('meas'):
                control.append(f"meas {analysis['meas']}")
        else:
            raise ValueError(
                f"unknown analysis type '{analysis['type']}' "
                f'(op, tran)')
    control += ['quit', '.endc']
    return control


def render_breadboards(manager, board_names, analyses=None,
                       probes=None):
    """Placements on the named boards + every jumper inside the set
    -> {'netlist', 'netByPlacement', 'suggestions'}."""
    boards = _board_map(manager, board_names)
    unions, suggestions = _jumper_unions(manager, boards)
    cards, lines, net_by_placement, needs_led_model = (
        _board_elements(manager, boards, unions))
    from electrodevice.spice_run import LED_MODEL
    control = _control_block(analyses, probes, lines)
    netlist = '\n'.join(
        [f'* Generated by Polari electrodevice.breadboard_netlist '
         f'from boards {", ".join(sorted(boards))} — edit the '
         f'placement/jumper rows, not this file.']
        + cards + ([LED_MODEL] if needs_led_model else [])
        + lines + control + ['.end', ''])
    return {'netlist': netlist, 'netByPlacement': net_by_placement,
            'suggestions': suggestions}


def render_board_subckt(manager, board_name, external_pins):
    """Re-wrap ONE populated board as a .subckt — board-as-component
    (the circuit mirror of solution-as-state). external_pins: dict
    {port_name: tie_point} naming which ties become the ports.

    Ports map at the PIN level through the SAME union-find the body
    uses (a port tie jumped to another strip lands on the canonical
    net, never floats). Device subckt cards and the LED model are
    GLOBAL — they are emitted BEFORE the .subckt block; a composer
    embedding several boards should de-duplicate identical cards."""
    boards = _board_map(manager, [board_name])
    board_row = boards[board_name]
    unions, _ = _jumper_unions(manager, boards)
    port_by_net = {}
    for port, tie in external_pins.items():
        _validate_tie(board_row, tie, f"external pin '{port}'")
        net = unions.resolve(tie_net(board_row, tie))
        if net in port_by_net:
            raise ValueError(
                f"external pins '{port_by_net[net]}' and '{port}' "
                f'land on the same net {net!r} — one port per net')
        port_by_net[net] = port
    cards, lines, _, needs_led_model = _board_elements(
        manager, boards, unions, port_by_net=port_by_net)
    from electrodevice.spice_run import LED_MODEL
    sub_ident = board_name.replace('-', '_')
    ports = ' '.join(port_by_net.values())
    nl = '\n'
    preamble = ([f'* board {board_name} re-wrapped as a component '
                 f'(cards/models below are GLOBAL — de-duplicate '
                 f'when composing)']
                + cards
                + ([LED_MODEL] if needs_led_model else []))
    body = nl.join('    ' + line for line in lines)
    return (nl.join(preamble) + nl
            + f'.subckt {sub_ident} {ports}\n'
            + body + nl
            + f'.ends {sub_ident}\n')


def compile_breadboard(domain_rows):
    """Compiler-contract entry ('breadboard-netlist'):
    {'manager', 'board_names', 'analyses'?, 'probes'?} -> netlist
    artifact."""
    rendered = render_breadboards(
        domain_rows['manager'], domain_rows['board_names'],
        analyses=domain_rows.get('analyses'),
        probes=domain_rows.get('probes'))
    label = '+'.join(domain_rows['board_names'])
    return {'definition': None,
            'artifacts': [{'kind': 'spice-netlist',
                           'name': f'{label}.cir',
                           'text': rendered['netlist']}],
            'netByPlacement': rendered['netByPlacement'],
            'suggestions': rendered['suggestions']}


SEED_BREADBOARD_COMPILER = {
    'name': 'breadboard-netlist',
    'domain': 'circuit',
    'compiler_ref': 'electrodevice.breadboard_netlist'
                    ':compile_breadboard',
    'description': 'ComponentPlacement + BoardJumper rows -> a '
                   'runnable SPICE netlist; tie-point connectivity '
                   'IS the wiring, jumpers union nets across '
                   'boards, boards re-wrap as .subckt components.',
    'enabled': True,
}


def run_breadboards(manager, board_names, analyses=None,
                    probes=None):
    try:
        rendered = render_breadboards(manager, board_names,
                                      analyses=analyses,
                                      probes=probes)
    except ValueError as exc:
        return {'ok': False, 'error': str(exc)}
    except KeyError as exc:  # defense: a row shape we didn't foresee
        return {'ok': False,
                'error': f'circuit rows are missing required key '
                         f'{exc} — check the placement params_json'}
    result = run_netlist(rendered['netlist'],
                         label='-'.join(board_names))
    result.update({'boards': board_names,
                   'netlist': rendered['netlist'],
                   'netByPlacement': rendered['netByPlacement'],
                   'suggestions': rendered['suggestions']})
    return result
