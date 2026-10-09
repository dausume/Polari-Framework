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
from board.custom.soc_atmega328p import SOC


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


#: a declared macro -> the board_config.h pin KNOB a variant may override away from the board's own default
#: (board.custom.board_object.SYMBOL_KNOBS, the pins' own firmware_symbol) — LED_PIN/PWM_PIN/ADC_CHANNEL only;
#: BUTTON_PIN/SENSE_PIN/L_LED_PIN never appear here (fixed, see _FIXED_DECLARED_CANONICALS below)
_VARIANT_PIN_KNOBS = {'LED_PIN': 'led_pin', 'PWM_PIN': 'pwm_pin', 'ADC_CHANNEL': 'adc_channel'}
#: a declared macro that is HARDWARE-FIXED (never a board_config.h knob a variant resolves) -> the one canonical pin
#: it always names (board.custom.variants.resolve refuses button_pin/sense_pin at any other value; L_LED_PIN is the
#: on-board L LED, button_clock.c's own comment: "not a configurable knob of this demo")
_FIXED_DECLARED_CANONICALS = {'BUTTON_PIN': 'D2', 'SENSE_PIN': 'D3', 'L_LED_PIN': 'D13'}


def _declared_canonicals(board, base_configuration):
    """{declared macro name: canonical pin} for ONE graph's base_configuration — ucd-0e2b: a variant may override
    led_pin/pwm_pin/adc_channel away from the board's own default pin for that symbol (uno-button-clock sets
    led_pin=6, not the board's own LED_PIN=D13), so matching a declared macro against the BOARD's static
    firmware_symbol alone (as `_match_pins` always did) binds the WRONG pin whenever a variant overrides it — fixed
    here by resolving the macro through THIS configuration's own knobs instead (`board.custom.variants.resolve`,
    the same resolution `pol board gen` itself applies), falling back to the board's own default when the variant
    does not override it (so uno-sim-rig's existing rows are unchanged). Fixed/hardware-pinned macros
    (`_FIXED_DECLARED_CANONICALS`) are added unconditionally — they carry no BoardPin.firmware_symbol at all."""
    out = dict(_FIXED_DECLARED_CANONICALS)
    try:
        from board.custom import board_object as BO
        from board.custom import variants as V
        base_pins, _src = BO.pin_knobs(board)
        v = V.find(base_configuration)
        r = V.resolve(v, base=base_pins)
    except Exception:
        return out
    for macro, knob in _VARIANT_PIN_KNOBS.items():
        if knob in r['knobs']:
            n = int(r['knobs'][knob])
            out[macro] = ('A%d' % n) if knob == 'adc_channel' else ('D%d' % n)
    return out


def _match_pins(pins, atom, fixed=None):
    declared, peripherals = _declared_names(atom), _peripherals(atom)
    fixed = fixed or {}
    by_canon = {p['canonical']: p for p in pins}
    named = {fixed[d] for d in declared if d in fixed}
    if named:
        return [by_canon[c] for c in sorted(named) if c in by_canon]
    out = []
    for p in pins:
        if p.get('firmware_symbol') and p['firmware_symbol'] in declared:
            out.append(p)
        elif p.get('peripheral') and p['peripheral'] in peripherals:
            out.append(p)
    return out


def _gpio_port_letter(peripheral_id):
    """'GPIO PORTB' -> 'B'; '' for anything else."""
    return peripheral_id[len('GPIO PORT'):] if peripheral_id.startswith('GPIO PORT') else ''


def _init_counterpart_match(node_instance, atom, by_instance, atoms, pins, fixed=None):
    """([BoardPin, ...], atom_kind) for an '*_init' node whose OWN registers touch only a GPIO port, with no
    declared pin macro (hal_led_init's `LED_DDR |= _BV(LED_BIT)` records only a DDRB register touch — the parser
    has no POLARI_NODE on it to name LED_PIN, so it cannot be matched by declared name or by peripheral the way
    pwm_init is matched to D6 via TIMER0). Many pins share one port, so the register touch alone never says WHICH
    one. Its own RUNTIME COUNTERPART — the same base instance name with '_init' stripped ('led_init' -> 'led') —
    already resolves to the exact declared-macro pin (LED_PIN -> D13, via `_match_pins`, never a new guess): when
    that pin's own GPIO port matches the one THIS atom's registers touch, the two tasks share one physical pin,
    the same Purpose (init + runtime, §5h B1's own wording) — never a new heuristic, only the counterpart's
    already-resolved pin and kind (ucd-0b2d). ([], 'undetermined') when there is no such counterpart or no shared
    port (never a guess otherwise)."""
    if not node_instance.endswith('_init') or _declared_names(atom):
        return [], 'undetermined'
    ports_touched = {_gpio_port_letter(p) for p in _peripherals(atom)} - {''}
    if not ports_touched:
        return [], 'undetermined'
    base = node_instance[:-len('_init')]
    counterpart = by_instance.get(base)
    if counterpart is None or counterpart.get('kind') != 'c-atom' or not counterpart.get('atom'):
        return [], 'undetermined'
    c_atom = atoms.get(counterpart['atom'].partition(':')[2])
    if c_atom is None:
        return [], 'undetermined'
    shared = [p for p in _match_pins(pins, c_atom, fixed=fixed) if (p.get('soc_pin') or '')[1:2] in ports_touched]
    if not shared:
        return [], 'undetermined'
    return shared, _atom_requirement_kind(c_atom)


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
_PERIPHERAL_KIND = {'ADC': 'analog-in', 'EXINT': 'interrupt-in', 'PCINT': 'interrupt-in'}
_TIMER_PERIPHERALS = ('TIMER0', 'TIMER1', 'TIMER2')


def _atom_requirement_kind(atom):
    """THE ATOM-LEVEL KIND (board.custom.target_compat.TASK_KINDS vocabulary, his ruling 2026-10-06), from one
    atom's own resources/ports alone — never looks at a board pin. A peripheral with one unambiguous direction
    (ADC, EXINT/PCINT) settles it outright; USART0 is settled by WHICH register the atom touches (UDR0 write =
    uart-tx, read = uart-rx) or, with no register touch at all (e.g. a ring-buffer consumer like hal_rx_pop), by the
    atom's own port shape (only 'out' ports = it reads a byte IN from the world = uart-rx; only 'in' ports = it
    writes a byte OUT = uart-tx); a bare TWI/SPI register touch does not say WHICH signal of the bus, so it is
    'undetermined' rather than guessed. A bare pin (a declared macro with no recognised peripheral, e.g. LED_PIN)
    falls back to the same port-shape rule: only 'in' ports (it is WRITTEN to) = digital-out; only 'out' ports (it
    is READ) = digital-in. 'undetermined' when none of this settles it (never guessed) — ucd-0b2a's `_kind_for_pin`
    then falls back to the BOUND PIN's own already-known signal, per TargetDefinition row."""
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
        # an OCR write ALONE is not PWM — e.g. hal_tick_init writes OCR2A to set Timer2's CTC compare value for a
        # 1 ms tick, driving no pin at all (ucd-0b2d: §5h, the HardwareBinding fix). Real PWM ALSO sets the output
        # pin's own DDR (hal_pwm_init: DDRD/DDRB beside TCCR0x/OCR0x) — require that GPIO-port co-touch too, never
        # guess pwm-out from the timer family alone.
        has_gpio_touch = any(res.get('kind') == 'register' and (res.get('peripheral') or '').startswith('GPIO PORT') for res in resources)
        if has_gpio_touch and any(res.get('kind') == 'register' and res['name'].startswith('OCR') and 'w' in (res.get('access') or '') for res in resources):
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
    declared = [res['name'] for res in resources if res.get('kind') == 'declared']
    if len(declared) > 1:
        # a SELECTABLE resource (uses() names more than one pin, e.g. spi_select(cs) choosing CS0_PIN/CS1_PIN) is
        # never guessed one direction at the atom level — _kind_for_pin decides each row from its own board pin
        return 'undetermined'
    # a bare pin (declared macro only, or a plain GPIO port register) — digital in/out from the port shape
    if has_in and not has_out:
        return 'digital-out'
    if has_out and not has_in:
        return 'digital-in'
    return 'undetermined'


#: a BoardPin's own `signal` (its already-known alternate function, authoritative — never a guess) -> requirement_kind,
#: for the rows the atom-level heuristic alone cannot settle (ucd-0b2a §5h B1 — the fallback cmod.custom.claims._kind_for
#: already used per solution; this is the SAME table, applied per TargetDefinition row so it is never recomputed downstream)
_SIGNAL_KIND = {'RXD': 'uart-rx', 'TXD': 'uart-tx', 'SDA': 'i2c-sda', 'SCL': 'i2c-scl', 'MOSI': 'spi-mosi', 'COPI': 'spi-mosi',
                'MISO': 'spi-miso', 'CIPO': 'spi-miso', 'SCK': 'spi-sck', 'SS': 'spi-ss'}
#: a BoardPin's own `function` -> requirement_kind, for the two kinds a bare function settles without a signal name
_FUNCTION_KIND = {'adc': 'analog-in', 'pwm': 'pwm-out'}
#: requirement_kind -> role (input | output | receive | transmit | clock | select | data | address | '') — every
#: TASK_KINDS entry maps to one; '' (not listed) covers 'undetermined' and any kind outside the vocabulary
_ROLE_BY_KIND = {'analog-in': 'input', 'pwm-out': 'output', 'uart-rx': 'receive', 'uart-tx': 'transmit',
                 'i2c-sda': 'data', 'i2c-scl': 'clock', 'spi-mosi': 'data', 'spi-miso': 'data', 'spi-sck': 'clock',
                 'spi-ss': 'select', 'digital-in': 'input', 'digital-out': 'output', 'interrupt-in': 'receive',
                 'timer': 'clock'}
#: a declared uses() name that is itself a whole PERIPHERAL id (board.custom.registers.PERIPHERAL_RULES /
#: soc_atmega328p.FUNCTION_PERIPHERAL's own vocabulary) rather than a board_config.h PIN macro (LED_PIN, PWM_PIN) —
#: hal_rx_pop's uses(USART0) names the peripheral its ring buffer is filled from, never a pin (ucd-0b2d)
_PERIPHERAL_IDS = frozenset({'USART0', 'TIMER0', 'TIMER1', 'TIMER2', 'ADC', 'SPI', 'TWI', 'EXINT', 'PCINT'})
#: requirement_kind -> the PeripheralSignal's own signal name, for a resource_kind='signal' row (the inverse of
#: `_SIGNAL_KIND` above, restricted to the kinds a signal-only atom (no register touch) can settle)
_KIND_TO_SIGNAL = {'uart-rx': 'RXD', 'uart-tx': 'TXD', 'i2c-sda': 'SDA', 'i2c-scl': 'SCL', 'spi-mosi': 'MOSI',
                    'spi-miso': 'MISO', 'spi-sck': 'SCK', 'spi-ss': 'SS'}
#: a SOLE register-touched peripheral family, with NO GPIO-port co-touch and no declared pin macro (hal_tick_init's
#: Timer2 CTC setup) -> the peripheral-level requirement_kind (board.custom.target_compat.TASK_KINDS, ucd-0b2d)
_SOLE_PERIPHERAL_KIND = {'TIMER0': 'timer', 'TIMER1': 'timer', 'TIMER2': 'timer', 'USART0': 'usart', 'ADC': 'adc',
                         'SPI': 'spi', 'TWI': 'twi', 'EXINT': 'exint', 'PCINT': 'pcint'}


def _sole_peripheral_kind(pid):
    if pid in _SOLE_PERIPHERAL_KIND:
        return _SOLE_PERIPHERAL_KIND[pid]
    return 'gpio-port' if pid.startswith('GPIO PORT') else 'undetermined'


def _kind_for_pin(pin, atom_kind):
    """The per-ROW requirement_kind: the atom-level kind wins when it settled one; otherwise the BOUND pin's own
    already-known signal/function (never a guess from a register name — the same posture as cmod.custom.claims.
    _kind_for's fallback, reused here so claims.py can read the row instead of recomputing it)."""
    if atom_kind != 'undetermined':
        return atom_kind
    pin = pin or {}
    sig = pin.get('signal') or ''
    if sig in _SIGNAL_KIND:
        return _SIGNAL_KIND[sig]
    fn = pin.get('function') or ''
    if fn in _FUNCTION_KIND:
        return _FUNCTION_KIND[fn]
    if fn == 'uart':   # the bare 'uart' function with a signal this table does not (yet) name
        return 'undetermined'
    return atom_kind


def _resource_fields(target_kind, requirement_kind):
    """(role, required, resource_kind) for one TargetDefinition row, from its `kind` (register | pin | peripheral |
    memory-field | bus | dynamic) and its just-derived `requirement_kind`. A memory-field row is not a hardware
    requirement at all (his rule, demo-4) — role/resource_kind stay '' and required is False; every other row's
    resource is inherently a PIN once its kind resolves (board.custom.target_compat: "the pins are the targets"),
    'undetermined' only while the kind itself is."""
    if target_kind == 'memory-field':
        return '', False, ''
    role = _ROLE_BY_KIND.get(requirement_kind, '')
    resource_kind = 'pin' if requirement_kind in _ROLE_BY_KIND else 'undetermined'
    return role, True, resource_kind


def requirement_kind(graph_name, task):
    """THE TASK TARGET KIND for existing callers (board.custom.target_compat.TASK_KINDS vocabulary) — ucd-0b2a:
    now READS the first of this task's own (per-row) `derive()` rows rather than recomputing; a task with several
    rows (a dispatcher, or one the atom alone cannot settle) may carry DIFFERENT kinds per row — this keeps
    returning one, for callers that only ever wanted one (`cmod.custom.firmware.valid_targets_for_task`,
    `check_drop`)."""
    rows = [r for r in derive(graph_name) if r['node'] == task]
    return rows[0]['requirement_kind'] if rows else 'undetermined'


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
    fixed = _declared_canonicals(g.get('board', ''), g.get('base_configuration', ''))
    by_instance = {n['instance']: n for n in nodes}
    out, seen = [], set()

    def add(node, port_name, kind, controls, lives_on, port=None, provenance='annotation', notes='', req_kind='undetermined',
            resource_kind=None, peripheral='', signal=''):
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
        role, required, inferred_resource_kind = _resource_fields(kind, req_kind)
        # ucd-0b2d: a row whose requirement is a whole PERIPHERAL or a SIGNAL through memory (never a pin —
        # hal_tick_init/hal_rx_pop) names its resource_kind explicitly; every other row keeps the pre-existing
        # pin-vocabulary inference (_resource_fields) unchanged.
        rk = resource_kind if resource_kind is not None else inferred_resource_kind
        out.append({'name': '%s:%s' % (graph_name, port_ref), 'graph': graph_name, 'node': node, 'port': port_name or '',
                    'port_ref': port_ref, 'kind': kind, 'controls': controls, 'lives_on': lives_on,
                    'board': g.get('board', '') if lives_on != 'unbound' else '', 'direction': direction, 'ctype': ctype,
                    'width_bytes': width, 'polari_type': polari_type, 'unit': unit, 'constraints': constraints,
                    'provenance': provenance, 'requirement_kind': req_kind if kind != 'memory-field' else '',
                    'role': role, 'required': required, 'resource_kind': rk, 'peripheral': peripheral,
                    'signal': signal, 'notes': notes})

    for n in nodes:
        if n.get('kind') != 'c-atom' or not n.get('atom'):
            continue
        bare = n['atom'].partition(':')[2]
        atom = atoms.get(bare)
        if atom is None:
            continue
        port = _representative_port(atom, n.get('bindings'))
        matched = _match_pins(pins, atom, fixed=fixed)
        if not atom.get('resources'):
            continue
        has_register_or_declared = any(r.get('kind') in ('register', 'declared') for r in atom['resources'])
        if not has_register_or_declared:
            continue
        kind = 'register' if _peripherals(atom) else ('pin' if _declared_names(atom) else 'dynamic')
        atom_kind = _atom_requirement_kind(atom)
        if matched:
            for pin in matched:
                add(n['instance'], port['name'] if port else '', kind, _node_controls(atom, pin, port),
                    '%s:%s' % (g.get('board', ''), pin['canonical']), port=port, provenance='annotation',
                    req_kind=_kind_for_pin(pin, atom_kind))
            continue
        # ucd-0b2d (§5h, the HardwareBinding fix): nothing matched a board pin — three distinct, never-guessed
        # shapes before falling back to the old plain 'unbound' row.
        # (1) an '*_init' task sharing its runtime counterpart's exact pin (hal_led_init -> led's own D13)
        counterpart_pins, counterpart_kind = _init_counterpart_match(n['instance'], atom, by_instance, atoms, pins, fixed=fixed)
        if counterpart_pins:
            for pin in counterpart_pins:
                add(n['instance'], port['name'] if port else '', kind, _node_controls(atom, pin, port),
                    '%s:%s' % (g.get('board', ''), pin['canonical']), port=port, provenance='annotation',
                    req_kind=_kind_for_pin(pin, counterpart_kind))
            continue
        declared = _declared_names(atom)
        periphs = _peripherals(atom)
        # (2) a declared uses() name that is itself a whole PERIPHERAL id (never a pin macro), no register touch
        # at all — the task reads/writes that peripheral's signal through memory only (hal_rx_pop's RX ring)
        if not periphs and len(declared) == 1 and declared[0] in _PERIPHERAL_IDS and atom_kind in _KIND_TO_SIGNAL:
            sig = '%s:%s:%s' % (SOC, declared[0], _KIND_TO_SIGNAL[atom_kind])
            add(n['instance'], port['name'] if port else '', kind, _node_controls(atom, None, port), 'unbound',
                port=port, provenance='annotation', req_kind=atom_kind, resource_kind='signal', signal=sig)
            continue
        # (3) EXACTLY ONE register-touched peripheral family, no GPIO-port co-touch, no declared pin macro — a
        # whole-PERIPHERAL requirement (hal_tick_init's Timer2 CTC setup: no OCR-to-a-pin, no pin declared)
        has_gpio_touch = any(p.startswith('GPIO PORT') for p in periphs)
        if len(periphs) == 1 and not has_gpio_touch and not declared:
            pid = next(iter(periphs))
            add(n['instance'], port['name'] if port else '', kind, _node_controls(atom, None, port), 'unbound',
                port=port, provenance='annotation', req_kind=_sole_peripheral_kind(pid), resource_kind='peripheral',
                peripheral='%s:%s' % (SOC, pid))
            continue
        add(n['instance'], port['name'] if port else '', kind, _node_controls(atom, None, port), 'unbound',
            port=port, provenance='annotation', req_kind=atom_kind)

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
