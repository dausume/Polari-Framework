"""
@module cmod.custom.targets

TARGET + CAPABILITY DEFINITIONS (demo-4, AI-Notes/plans/DEMONSTRABLES_PLAN.md §3 demo-4; his ruling: "in the no-code we
may say 'assign to 1 specific register this part of a struct, which we will use to track temperature from a sensor'.
Then we generalize that along with its code as 'temperature sensor solution' ... and be able to define multiple
temperature sensors"). Everything here is DERIVED from rows already produced elsewhere — the atoms' committed manifest
(cmod-0's parse: registers / peripherals / declared pin macros), the graph's own nodes/edges (cmod-1, custom/graph_seed.py)
and the graph's board's `BoardPin` rows (board/custom/board_object.py, brd-bo) — never typed in. Pure functions over
plain dicts (the same style as custom/rows.py), so they run at SEED time with no manager and no engine.

Matching a c-atom node's resource touch to a board pin:
  - a 'declared' resource (a board_config.h macro the atom's C body uses directly — LED_PIN, PWM_PIN) matches a BoardPin
    whose `firmware_symbol` equals that macro's name — the same knob `board.custom.gen.board_pins()` resolves from.
  - a 'register' resource's `peripheral` (ADC, TIMER0, USART0, …) matches a BoardPin whose own `peripheral` field
    (derived from its `signal` through `soc_atmega328p.FUNCTION_PERIPHERAL`) equals it.
A node with no matching pin still gets a target (`lives_on='unbound'`) — a register/struct-field target exists before
it is ever tied to a specific board (his rule: "unbound targets are allowed and visibly marked").
A `CGraphEdge` of kind 'field' (a port written into the class instance's field) is a memory-field target: it has no
board pin at all (a struct field lives in the generated glue's memory layout, not a fixed SoC register), so it is
always `provenance='derived'`, `lives_on='unbound'`.
"""
import json
import os

from cmod.custom import projects as P


def _csv_set(s):
    return {x.strip() for x in (s or '').split(',') if x.strip()}


def _manifest_atoms(project):
    spec = P.resolve(project)
    path = P.manifest_path(spec)
    if not os.path.isfile(path):
        return {}
    return {a['name']: a for a in json.load(open(path))['atoms']}


def _board_pins(board):
    """Static BoardPin-shaped dicts for `board` — no manager needed (brd-bo's own seed fallback)."""
    try:
        from board.custom import board_object as BO
        return BO.rows_for(board)['pins']
    except Exception:
        return []


def _declared_names(atom):
    """The board_config.h macros this atom's C body touches directly ('declared' resources — LED_PIN, PWM_PIN)."""
    return [r['name'] for r in (atom.get('resources') or []) if r.get('kind') == 'declared']


def _peripherals(atom):
    return sorted({r['peripheral'] for r in (atom.get('resources') or []) if r.get('kind') == 'register' and r.get('peripheral')})


def _match_pins(pins, atom):
    declared, peripherals = _declared_names(atom), _peripherals(atom)
    out = []
    for p in pins:
        if p.get('firmware_symbol') and p['firmware_symbol'] in declared:
            out.append(p)
        elif p.get('peripheral') and p['peripheral'] in peripherals:
            out.append(p)
    return out


def _bindings_dict(bindings):
    out = {}
    for part in (bindings or '').split(';'):
        part = part.strip()
        if '=' in part:
            k, v = part.split('=', 1)
            out[k.strip()] = v.strip()
    return out


def _representative_port(atom, bindings):
    """Which of the atom's ports this node's board touch is best named by: a bound in-port first, else the first
    in-port, else '' (a whole-node target — not every touch is one port's business, e.g. init atoms)."""
    ports = atom.get('ports') or []
    bound = _bindings_dict(bindings)
    for p in ports:
        if p['name'] in bound:
            return p
    for p in ports:
        if p['direction'] == 'in':
            return p
    return None


def _node_controls(atom, pin, port):
    role = (atom.get('annotation') or {}).get('role', '') or atom.get('function', '')
    meaning = (port or {}).get('meaning', '')
    base = '%s (%s)' % (meaning, role) if meaning and role else (meaning or role or atom.get('function', ''))
    return '%s — touches %s' % (base, pin['canonical']) if pin else base


# ------------------------------------------------------------------ fs-2a: THE TASK'S REQUIREMENT KIND
#: peripheral -> target kind, for the peripherals whose direction is NOT ambiguous (board.custom.target_compat's
#: vocabulary) — USART0 is handled separately (its UDR0 register's access settles rx/tx; TWI/SPI are handled
#: separately too (a bare register touch does not by itself say WHICH signal of the bus, so they stay undetermined)
_PERIPHERAL_KIND = {'ADC': 'analog-in', 'EXTINT': 'interrupt-in', 'PCINT': 'interrupt-in'}
_TIMER_PERIPHERALS = ('TIMER0', 'TIMER1', 'TIMER2')


def requirement_kind(graph_name, task):
    """THE TASK TARGET KIND (board.custom.target_compat.TASK_KINDS vocabulary, his ruling 2026-10-06), derived from
    one graph node's atom resources — never typed in. A peripheral with one unambiguous direction (ADC, EXTINT/
    PCINT) settles it outright; USART0 is settled by WHICH register the atom touches (UDR0 write = uart-tx, read =
    uart-rx) or, with no register touch at all (e.g. a ring-buffer consumer like hal_rx_pop), by the atom's own
    port shape (only 'out' ports = it reads a byte IN from the world = uart-rx; only 'in' ports = it writes a byte
    OUT = uart-tx); a bare TWI/SPI register touch does not say WHICH signal of the bus, so it is 'undetermined'
    rather than guessed. A bare pin (a declared macro with no recognised peripheral, e.g. LED_PIN) falls back to the
    same port-shape rule: only 'in' ports (it is WRITTEN to) = digital-out; only 'out' ports (it is READ) =
    digital-in. 'undetermined' when none of this settles it (never guessed)."""
    from cmod.custom.graph_seed import seed_graph
    rows = seed_graph(graph_name)
    if rows is None:
        return 'undetermined'
    g, nodes = rows['graph'], rows['nodes']
    node = next((n for n in nodes if n['instance'] == task), None)
    if node is None or node.get('kind') != 'c-atom' or not node.get('atom'):
        return 'undetermined'
    atoms = _manifest_atoms(g['project'])
    atom = atoms.get(node['atom'].partition(':')[2])
    if atom is None or not atom.get('resources'):
        return 'undetermined'
    resources = atom['resources']
    peripherals = {res['peripheral'] for res in resources if res.get('kind') in ('register', 'declared') and res.get('peripheral')}
    ports = atom.get('ports') or []
    has_in = any(p['direction'] == 'in' for p in ports)
    has_out = any(p['direction'] in ('out', 'inout') for p in ports)
    for peripheral, kind in _PERIPHERAL_KIND.items():
        if peripheral in peripherals:
            return kind
    if peripherals & set(_TIMER_PERIPHERALS):
        if any(res.get('kind') == 'register' and res['name'].startswith('OCR') and 'w' in (res.get('access') or '') for res in resources):
            return 'pwm-out'
    if 'USART0' in peripherals:
        udr = next((res for res in resources if res.get('kind') == 'register' and res['name'].startswith('UDR')), None)
        if udr is not None:
            return 'uart-tx' if 'w' in (udr.get('access') or '') else 'uart-rx'
        if has_out and not has_in:
            return 'uart-rx'
        if has_in and not has_out:
            return 'uart-tx'
        return 'undetermined'
    if 'TWI' in peripherals or 'SPI' in peripherals:
        return 'undetermined'
    # a bare pin (declared macro only, or a plain GPIO port register) — digital in/out from the port shape
    if has_in and not has_out:
        return 'digital-out'
    if has_out and not has_in:
        return 'digital-in'
    return 'undetermined'


def derive(graph_name, manager=None):
    """-> [TargetDefinition dict, ...] for one graph: one row per (c-atom node, matched-or-unbound board touch), plus
    one row per 'field' CGraphEdge (a memory-field target). `manager` is accepted and ignored — kept for callers that
    pass it uniformly (the API, selftest); this deriver is pure over seeded/committed data, same as custom/rows.py."""
    from cmod.custom.graph_seed import seed_graph
    rows = seed_graph(graph_name)
    if rows is None:
        return []
    g, nodes, edges = rows['graph'], rows['nodes'], rows['edges']
    atoms = _manifest_atoms(g['project'])
    pins = _board_pins(g.get('board', ''))
    by_instance = {n['instance']: n for n in nodes}
    out, seen = [], set()

    def add(node, port_name, kind, controls, lives_on, port=None, provenance='annotation', notes=''):
        port_ref = '%s.%s' % (node, port_name) if port_name else node
        key = (port_ref, kind, lives_on)
        if key in seen:
            return
        seen.add(key)
        direction = (port or {}).get('direction', '')
        ctype = (port or {}).get('ctype', '')
        width = int((port or {}).get('width_bytes') or 0)
        polari_type = (port or {}).get('polari_type', '')
        unit = (port or {}).get('unit', '')
        constraints = ('%s, width %d B' % (direction, width)) if direction else ('width %d B' % width if width else '')
        out.append({'name': '%s:%s' % (graph_name, port_ref), 'graph': graph_name, 'node': node, 'port': port_name or '',
                    'port_ref': port_ref, 'kind': kind, 'controls': controls, 'lives_on': lives_on,
                    'board': g.get('board', '') if lives_on != 'unbound' else '', 'direction': direction, 'ctype': ctype,
                    'width_bytes': width, 'polari_type': polari_type, 'unit': unit, 'constraints': constraints,
                    'provenance': provenance, 'notes': notes})

    for n in nodes:
        if n.get('kind') != 'c-atom' or not n.get('atom'):
            continue
        bare = n['atom'].partition(':')[2]
        atom = atoms.get(bare)
        if atom is None:
            continue
        port = _representative_port(atom, n.get('bindings'))
        matched = _match_pins(pins, atom)
        if not atom.get('resources'):
            continue
        has_register_or_declared = any(r.get('kind') in ('register', 'declared') for r in atom['resources'])
        if not has_register_or_declared:
            continue
        kind = 'register' if _peripherals(atom) else ('pin' if _declared_names(atom) else 'dynamic')
        if matched:
            for pin in matched:
                add(n['instance'], port['name'] if port else '', kind, _node_controls(atom, pin, port),
                    '%s:%s' % (g.get('board', ''), pin['canonical']), port=port, provenance='annotation')
        else:
            add(n['instance'], port['name'] if port else '', kind, _node_controls(atom, None, port), 'unbound',
                port=port, provenance='annotation')

    for e in edges:
        if e.get('kind') != 'field':
            continue
        src = by_instance.get(e['from_node']) or {}
        src_atom = atoms.get((src.get('atom') or '').partition(':')[2]) if src.get('atom') else None
        src_port = None
        if src_atom:
            src_port = next((p for p in (src_atom.get('ports') or []) if p['name'] == e.get('from_port')), None)
        meaning = (src_port or {}).get('meaning', '')
        controls = '%s.%s <- %s' % (g.get('class_name', ''), e.get('to_port', ''), meaning or e.get('from_port', ''))
        add(e['from_node'], e.get('from_port', ''), 'memory-field', controls, 'unbound', port=src_port, provenance='derived',
            notes='written into %s.%s by the generated glue (a struct field — no fixed register)' % (g.get('class_name', ''), e.get('to_port', '')))

    return out


# ------------------------------------------------------------------ capabilities (demo-4: "temperature sensor solution")
TEMP_SENSOR_CAPABILITY = 'uno-sim-rig-graph:temperature-sensor-solution'


def temperature_sensor_capability(graph_name='uno-sim-rig-graph'):
    """The seeded capability: the sensor_value/moving-average path of the graph — required targets {ADC channel pin,
    temp_c memory field}, exposing `temp_c`. One row; its two uses are `temperature_sensor_instances()` below."""
    targets = derive(graph_name)
    by_ref = {t['port_ref']: t for t in targets}
    required = [r for r in ('adc.channel', 'temp.return') if r in by_ref]
    adc = by_ref.get('adc.channel') or {}
    pin = adc.get('lives_on', 'unbound')
    where = (' on %s' % pin.split(':')[-1]) if pin and pin != 'unbound' else ' (not yet tied to a board pin)'
    return {'name': TEMP_SENSOR_CAPABILITY, 'graph': graph_name, 'title': 'Temperature sensor solution',
            'purpose': "TMP36 temperature%s, read through the ADC channel target and written into the rig's temp_c "
                       "memory-field target — generalized into one droppable capability (his worked example: "
                       "\"assign to 1 specific register this part of a struct ... generalize that ... as 'temperature "
                       "sensor solution'\")." % where,
            'required_targets': ', '.join(required), 'exposes_fields': 'temp_c',
            'instance_count': 2, 'notes': ''}


def temperature_sensor_instances(graph_name='uno-sim-rig-graph'):
    """TWO instances of the capability — proving "multiple temperature sensors" are rows, not just a template.
    Binding either to a real board pin (a second ADC channel) is demo-5, not this slice — both start unbound."""
    cap = TEMP_SENSOR_CAPABILITY
    return [{'name': '%s#%d' % (cap, i), 'capability': cap, 'graph': graph_name, 'index': i,
            'bindings': 'adc.channel=unbound, temp.return=unbound', 'status': 'unbound',
            'notes': 'instance %d of 2 (his worked example: "be able to define multiple temperature sensors")' % i}
            for i in (1, 2)]
