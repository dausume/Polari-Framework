"""
@module cmod.custom.claims

PIN CLAIMS + PERIPHERAL CLAIMS + GENERATED REGISTER CONFIG (ucd-0b, UNO_CORE_DEMO_PLAN.md §5f/§5g): the firmware-side
half of his two explanation chains —

    Firmware Task -> PinClaim -> SignalRoute -> PinFunction -> PeripheralSignal -> Peripheral -> RegisterField
    -> RegisterFieldSetting -> RegisterSetting -> the generated C line

Everything here is DERIVED from rows already produced elsewhere (a solution's `RegisterAssignment` rows, the board's
own BoardPin/SocPin/PinFunction/RegisterField chain built in ucd-0a) — the atom scan never recorded the VALUES a
task writes (register names + r/w access only, §5f point 1), so `PinClaim.mode/pull/edge/initial` default from the
TASK KIND (`cmod.custom.targets.requirement_kind`) and the board pin's OWN already-known alternate function (never
guessed from a register name); a person overrides them on the pin page, persisted on the originating
`RegisterAssignment.config_json` (never lost on a re-derive).

`register_settings()` generates GPIO + external-interrupt/pin-change config ONLY (DDRx/PORTx, EICRA/EIFR/EIMSK for a
pin with an INTn alternate function, PCMSKk/PCICR for any other GPIO pin) — timer and USART configuration stay in
the HAND-WRITTEN HAL for this slice (hal_pwm_init/hal_usart_init/hal_adc_init), named here so the gap is never
silent; a later slice may move them into the same generator. Every bit position/value/meaning is read off the
RegisterField rows ucd-0a cited — never a hard-coded bit number.
"""
import json

from board.custom.soc_atmega328p import SOC

#: requirement_kind (board.custom.target_compat.TASK_KINDS vocabulary) -> PinClaim.mode, for the kinds a bare pin
#: BoardPin + atom scan settle outright; 'undetermined' falls back to the board pin's own known alternate function
#: (set(), never guessed from a register name — see _kind_for)
_MODE_BY_KIND = {
    'digital-out': 'out', 'digital-in': 'in', 'interrupt-in': 'alt', 'pwm-out': 'alt',
    'analog-in': 'alt', 'uart-rx': 'alt', 'uart-tx': 'alt',
}
#: an 'alt' mode kind that STILL has a definite plain-GPIO direction underneath (PWM must be driven out; an
#: interrupt-sensed pin is still a plain input) — analog-in/uart-rx/uart-tx/i2c/spi are NOT here: this slice never
#: writes their DDR, matching the real hal_adc_init/hal_usart_init, which never touch it either
_ALT_DIRECTION_BY_KIND = {'pwm-out': 1, 'interrupt-in': 0}


def _ddr_direction(claim):
    """1 (out) | 0 (in) | None (no DDR write this slice generates) — from the claim's EFFECTIVE `mode` (so an
    override that flips mode also flips the direction this generates, never the static kind alone)."""
    if claim['mode'] == 'out':
        return 1
    if claim['mode'] == 'in':
        return 0
    if claim['mode'] == 'alt':
        return _ALT_DIRECTION_BY_KIND.get(claim['requirement_kind'])
    return None
_ISC_VALUE = {'any': 0b01, 'falling': 0b10, 'rising': 0b11, 'low': 0b00}
#: peripheral id -> usage (board.custom.hardware_chain's peripheral vocabulary; TIMERn handled separately, channel by channel)
_USAGE_BY_PERIPHERAL = {'USART0': 'exclusive', 'ADC': 'shared-read', 'GPIO PORTB': 'shared-config',
                        'GPIO PORTC': 'shared-config', 'GPIO PORTD': 'shared-config', 'EXINT': 'exclusive',
                        'PCINT': 'exclusive', 'SPI': 'exclusive', 'TWI': 'exclusive'}


# ---------------------------------------------------------------- shared plumbing (board chain tables, live or pure)

def _chain_tables(manager=None):
    from board.custom import board_object as BO
    if manager is not None:
        t = BO.tables_from_manager(manager)
        if t.get('BoardPin'):
            return t
    return BO.seed_tables()


def _index(tables, cls):
    return {r['name']: r for r in tables.get(cls, [])}


def _live_assignments(solution_name, graph, manager=None):
    """[RegisterAssignment dict, …] — the LIVE rows (carrying a canvas-authored `config_json`) when a manager has
    them, else the pure re-derivation (`cmod.custom.firmware.assignments_for`), same duality as
    `cmod.custom.firmware._occupants`."""
    if manager is not None:
        rows = [{'name': getattr(r, 'name', ''), 'task': getattr(r, 'task', ''), 'port': getattr(r, 'port', ''),
                 'target_kind': getattr(r, 'target_kind', ''), 'lives_on': getattr(r, 'lives_on', 'unbound'),
                 'status': getattr(r, 'status', 'unbound'), 'provenance': getattr(r, 'provenance', 'derived'),
                 'config_json': getattr(r, 'config_json', '{}') or '{}', 'notes': getattr(r, 'notes', '')}
                for r in (manager.objectTables or {}).get('RegisterAssignment', {}).values()
                if getattr(r, 'solution', '') == solution_name]
        if rows:
            return rows
    from cmod.custom import firmware as FW
    rows = FW.assignments_for(graph, solution_name)
    for r in rows:
        r.setdefault('config_json', '{}')
    return rows


def _dispatchers(graph):
    from cmod.custom import targets as T
    per_node_pins = {}
    for t in T.derive(graph):
        if t['lives_on'] != 'unbound':
            per_node_pins.setdefault(t['node'], set()).add(t['lives_on'])
    return {n for n, pins in per_node_pins.items() if len(pins) > 1}


def _groups(rows):
    g = {}
    for r in rows:
        if r.get('lives_on') and r['lives_on'] != 'unbound':
            g.setdefault(r['lives_on'], []).append(r)
    return g


def _representative(rows_at_pin, dispatchers):
    """The ONE assignment row that CONFIGURES this pin: an '_init' task first (it is the one that calls DDR/PORT/
    peripheral setup), else the sole non-dispatcher task, else (every candidate is a dispatcher, e.g. USART0's own
    init touching both D0 and D1) the lexically first. Never ambiguous — deterministic, never guessed."""
    inits = [r for r in rows_at_pin if r['task'].endswith('_init')]
    pool = inits if inits else rows_at_pin
    non_disp = [r for r in pool if r['task'] not in dispatchers]
    pool = non_disp if non_disp else pool
    return sorted(pool, key=lambda r: (r['task'], r.get('port', '')))[0]


def _int_capable(soc_pin_row):
    """('EXINT', 'INT1') | ('PCINT', 'PCINT19') | (None, None) — whether this SoC pin carries an external-interrupt
    or pin-change function, from its OWN `functions_json` (never guessed; every GPIO pin has a PCINT, only PD2/PD3
    also have an INTn)."""
    fns = json.loads(soc_pin_row.get('functions_json') or '[]')
    intn = next((x for x in fns if x.startswith('INT') and x[3:].isdigit()), None)
    if intn:
        return 'EXINT', intn
    pcint = next((x for x in fns if x.startswith('PCINT')), None)
    if pcint:
        return 'PCINT', pcint
    return None, None


# ---------------------------------------------------------------- PinClaim

def _kind_for(graph, rep_task, board_pin):
    """requirement_kind, falling back to the BOARD PIN's own already-known alternate function (its `function`/
    `signal`, assigned when the board was defined — authoritative, not a guess) when the atom-scan heuristic cannot
    settle it (e.g. a USART init atom that only touches UBRR/UCSR, never UDR0, so the port-shape rule alone cannot
    tell RX from TX)."""
    from cmod.custom import targets as T
    kind = T.requirement_kind(graph, rep_task)
    if kind != 'undetermined':
        return kind
    fn = board_pin.get('function') or ''
    sig = board_pin.get('signal') or ''
    if fn == 'adc':
        return 'analog-in'
    if fn == 'pwm':
        return 'pwm-out'
    if fn == 'uart':
        return 'uart-rx' if sig == 'RXD' else ('uart-tx' if sig == 'TXD' else 'undetermined')
    return 'undetermined'   # spi/i2c: a bare register touch does not say which signal of the bus (targets.py's own posture)


def _defaults(kind):
    if kind == 'digital-out':
        return {'pull': 'none', 'edge': 'none', 'initial': 'low'}
    if kind == 'digital-in':
        return {'pull': 'undetermined', 'edge': 'none', 'initial': 'none'}
    if kind == 'interrupt-in':
        return {'pull': 'undetermined', 'edge': 'undetermined', 'initial': 'none'}
    return {'pull': 'none', 'edge': 'none', 'initial': 'none'}   # alt (pwm/adc/uart) or undetermined


def _effective(canonical, defaults, mode, rep, overrides):
    """Merge: derived defaults <- persisted RegisterAssignment.config_json <- an explicit `overrides[canonical]`
    (the caller's own, e.g. a dry-run preview or a selftest — the assign door is what PERSISTS one)."""
    try:
        persisted = json.loads(rep.get('config_json') or '{}')
    except (TypeError, ValueError):
        persisted = {}
    explicit = (overrides or {}).get(canonical) or {}
    merged = dict(persisted)
    merged.update(explicit)
    eff_mode = merged.get('mode', mode)
    eff_pull = merged.get('pull', defaults['pull'])
    eff_edge = merged.get('edge', defaults['edge'])
    eff_initial = merged.get('initial', defaults['initial'])
    return eff_mode, eff_pull, eff_edge, eff_initial, bool(merged)


def pin_claims(solution_name, graph, manager=None, overrides=None):
    """[PinClaim dict, …] — one per physical pin this solution's RegisterAssignment rows bind. `overrides` =
    {canonical: {mode?, pull?, edge?, initial?}}, layered over whatever is already persisted on the representative
    assignment's `config_json`."""
    tables = _chain_tables(manager)
    board_pins = _index(tables, 'BoardPin')
    soc_pins = _index(tables, 'SocPin')
    rows = _live_assignments(solution_name, graph, manager)
    dispatchers = _dispatchers(graph)
    out = []
    for lives_on, group in _groups(rows).items():
        bp = board_pins.get(lives_on)
        if bp is None:
            continue
        rep = _representative(group, dispatchers)
        soc_pin_name = '%s:%s' % (SOC, bp['soc_pin']) if bp.get('soc_pin') else ''
        sp = soc_pins.get(soc_pin_name)
        kind = _kind_for(graph, rep['task'], bp)
        mode = _MODE_BY_KIND.get(kind) or ('alt' if bp.get('function') not in ('', 'gpio', 'led') else 'undetermined')
        defaults = _defaults(kind)
        eff_mode, pull, edge, initial, overridden = _effective(bp['canonical'], defaults, mode, rep, overrides)
        pin_function = ''
        if eff_mode == 'alt':
            if bp.get('signal'):
                pin_function = '%s:%s:%s' % (SOC, bp['soc_pin'], bp['signal'])
            elif sp is not None:
                fam, fn = _int_capable(sp)
                if fn:
                    pin_function = '%s:%s:%s' % (SOC, sp['pin'], fn)
        status, why = 'ok', ''
        if rep.get('status') == 'conflict':
            status, why = 'conflict', rep.get('notes') or 'the underlying register assignment conflicts'
        elif kind == 'interrupt-in' and edge == 'undetermined':
            status, why = 'incomplete', 'edge not yet chosen for this interrupt-in claim — author it on the pin page (any/rising/falling/low)'
        others = sorted({r['task'] for r in group} - {rep['task']})
        out.append({'name': '%s:%s' % (solution_name, bp['canonical']), 'solution': solution_name, 'board': bp.get('board', ''),
                    'board_pin': bp['name'], 'soc_pin': soc_pin_name, 'task': rep['task'], 'port': rep.get('port', ''),
                    'assignment': rep['name'], 'requirement_kind': kind, 'mode': eff_mode, 'pin_function': pin_function,
                    'pull': pull, 'edge': edge, 'initial': initial, 'rule': 'kind-%s' % kind,
                    'provenance': 'canvas' if overridden else 'derived', 'status': status, 'why': why,
                    'notes': ('also used by: %s' % ', '.join(others)) if others else ''})
    return sorted(out, key=lambda r: r['name'])


# ---------------------------------------------------------------- PeripheralClaim

def _atom_resources(graph):
    """[(task, [resource dict, …]), …] — every c-atom node's own resources, from the committed manifest (same
    source `cmod.custom.targets` reads; no manager needed, pure)."""
    import os
    from cmod.custom import projects as P
    from cmod.custom.graph_seed import seed_graph
    rows = seed_graph(graph)
    if rows is None:
        return []
    g, nodes = rows['graph'], rows['nodes']
    spec = P.resolve(g['project'])
    path = P.manifest_path(spec)
    atoms = {a['name']: a for a in json.load(open(path))['atoms']} if os.path.isfile(path) else {}
    out = []
    for n in nodes:
        if n.get('kind') != 'c-atom' or not n.get('atom'):
            continue
        a = atoms.get(n['atom'].partition(':')[2])
        if a is not None:
            out.append((n['instance'], a.get('resources') or []))
    return out


#: TIMER0/TIMER1 register -> (channel, usage): OCRnX/TCCRnA carry the channel's own compare/mode bits (exclusive to
#: whichever task drives that channel); TCCRnB ALSO carries the shared clock-select prescaler, tracked here at
#: register granularity as its own shared-config claim (a named simplification — this slice does not split TCCRnB
#: bit by bit). An explicit table (never string-sliced) so TCCRnB is never mistaken for a channel-B register.
_TIMER01_REG_CHANNEL = {'OCR0A': ('A', 'exclusive'), 'TCCR0A': ('A', 'exclusive'), 'OCR0B': ('B', 'exclusive'), 'TCCR0B': ('', 'shared-config'),
                        'OCR1AH': ('A', 'exclusive'), 'OCR1AL': ('A', 'exclusive'), 'OCR1BH': ('B', 'exclusive'), 'OCR1BL': ('B', 'exclusive'),
                        'TCCR1A': ('', 'exclusive'), 'TCCR1B': ('', 'shared-config'), 'TCCR1C': ('', 'shared-config')}


def _timer_channel(pid, reg):
    """(channel, usage) for one TIMER register. TIMER0/TIMER1 split by channel (`_TIMER01_REG_CHANNEL`); every other
    timer (TIMER2 in this demo — the 1 ms tick, his `hal_millis`) is one exclusive, whole-peripheral claim, never
    split into channels (its two Output Compare channels are not independently used here)."""
    if pid in ('TIMER0', 'TIMER1'):
        return _TIMER01_REG_CHANNEL.get(reg, ('', 'exclusive'))
    return '', 'exclusive'


def peripheral_claims(solution_name, graph, manager=None):
    """[PeripheralClaim dict, …] — every peripheral (or channel of it) this solution's atoms touch, grouped from
    their own register resources (never re-typed)."""
    atoms = _atom_resources(graph)
    groups = {}
    for task, resources in atoms:
        for r in resources:
            if r.get('kind') != 'register' or not r.get('peripheral'):
                continue
            pid, reg = r['peripheral'], r['name']
            channel, usage = _timer_channel(pid, reg) if pid.startswith('TIMER') else ('', _USAGE_BY_PERIPHERAL.get(pid, 'exclusive'))
            slot = groups.setdefault((pid, channel), {'tasks': set(), 'registers': set(), 'usage': usage})
            slot['tasks'].add(task)
            slot['registers'].add(reg)
    if ('ADC', '') in groups:
        pins = pin_claims(solution_name, graph, manager=manager)
        chans = sorted({p['pin_function'].rsplit(':', 1)[-1][3:] for p in pins
                        if p['requirement_kind'] == 'analog-in' and p['pin_function']})
        groups[('ADC', chans[0] if len(chans) == 1 else ('undetermined' if not chans else '+'.join(chans)))] = groups.pop(('ADC', ''))
    out = []
    for (pid, channel), slot in sorted(groups.items()):
        tasks = sorted(slot['tasks'])
        non_init = [t for t in tasks if not t.endswith('_init')]
        status, why = 'ok', ''
        if slot['usage'] == 'exclusive' and len(non_init) > 1:
            status = 'conflict'
            why = 'two non-cooperating tasks hold %s%s exclusively: %s' % (pid, (':' + channel if channel else ''), ', '.join(non_init))
        out.append({'name': '%s:%s%s' % (solution_name, pid, (':' + channel if channel else '')), 'solution': solution_name,
                    'peripheral': '%s:%s' % (SOC, pid), 'channel': channel, 'tasks_json': json.dumps(tasks),
                    'usage': slot['usage'], 'registers_json': json.dumps(sorted(slot['registers'])),
                    'rule': 'timer-channel-split' if pid.startswith('TIMER') else 'peripheral-wide',
                    'status': status, 'why': why, 'provenance': 'derived', 'notes': ''})
    return out


# ---------------------------------------------------------------- RegisterSetting / RegisterFieldSetting / SignalRoute

def _combine(solution_name, register_name, phase, specs, tables, source_file='pin_config.c'):
    """One RegisterSetting + its RegisterFieldSetting rows for one (solution, register, phase), from `specs` =
    [(RegisterField dict, bit_value:int, pin_claim_name, peripheral_claim_name, task, rule), …]. Two specs whose bit
    ranges overlap -> both (and the RegisterSetting) go to status='conflict', NAMED — never last-write-wins. Bit
    positions/values/meanings come from the RegisterField rows themselves (never a hard-coded bit number)."""
    reg = _index(tables, 'Register').get('%s:%s' % (SOC, register_name))
    rs_name = '%s:%s:%s' % (solution_name, register_name, phase)
    value = mask = 0
    claimed_bits = {}
    conflict, conflict_why = False, ''
    fs_rows = []
    for field_row, bit_value, pin_claim, peripheral_claim, task, rule in specs:
        hi, lo, width = field_row['bit_hi'], field_row['bit_lo'], field_row['width']
        bits = set(range(lo, hi + 1))
        overlap = bits & set(claimed_bits)
        fs_name = '%s:%s.%s:%s' % (solution_name, register_name, field_row['field'], phase)
        if overlap:
            conflict = True
            conflict_why = 'bits %s of %s overlap between %s and %s' % (sorted(overlap), register_name, fs_name, claimed_bits[next(iter(overlap))])
        for b in bits:
            claimed_bits[b] = fs_name
        value |= (bit_value << lo)
        mask |= (((1 << width) - 1) << lo)
        vals = json.loads(field_row['values_json'])
        bitstr = format(bit_value, '0%db' % width)
        fs_rows.append({'name': fs_name, 'solution': solution_name, 'register_setting': rs_name,
                        'register_field': field_row['name'], 'value': bitstr, 'meaning': vals.get(bitstr, ''),
                        'pin_claim': pin_claim, 'peripheral_claim': peripheral_claim, 'task': task, 'rule': rule,
                        'status': 'planned', 'provenance': 'derived', 'notes': ''})
    if conflict:
        for fs in fs_rows:
            fs['status'] = 'conflict'
            fs['notes'] = conflict_why
    width_bits = int((reg or {}).get('width_bytes') or 1) * 8
    rs = {'name': rs_name, 'solution': solution_name, 'register': '%s:%s' % (SOC, register_name), 'phase': phase,
         'value': '0x%02X' % value, 'value_bits': format(value, '0%db' % width_bits), 'write_mask': '0x%02X' % mask,
         'field_settings_refs_json': json.dumps(['RegisterFieldSetting:%s' % fs['name'] for fs in fs_rows]),
         'source_file': source_file, 'source_line': 0, 'status': 'conflict' if conflict else 'planned',
         'provenance': 'derived', 'notes': conflict_why}
    return rs, fs_rows


def _route_for(solution_name, claim, pf_name, pf_row):
    canonical = claim['name'].split(':', 1)[1]
    return {'name': '%s:%s:%s' % (solution_name, canonical, pf_row['function']), 'solution': solution_name,
           'pin_claim': claim['name'], 'board_pin': claim['board_pin'], 'soc_pin': claim['soc_pin'],
           'pin_function': pf_name, 'signal': pf_row.get('signal', ''), 'peripheral': pf_row.get('peripheral', ''),
           'routing': pf_row.get('routing', 'fixed'), 'configuration_refs_json': '[]', 'status': 'planned',
           'provenance': 'derived', 'notes': ''}


def register_settings(solution_name, graph, manager=None, overrides=None):
    """{'RegisterSetting': […], 'RegisterFieldSetting': […], 'SignalRoute': […]} — GPIO direction/level + external-
    interrupt/pin-change enable for this solution's PinClaims ONLY; timer and USART configuration stay in the HAL
    for now (hal_pwm_init/hal_tick_init/hal_usart_init/hal_adc_init), named here so the gap is never silent.
    `overrides` is the same {canonical: {...}} `pin_claims` takes — with a live manager an override is normally
    already persisted on the RegisterAssignment (the assign door's job); this lets a pure/no-manager caller (a dry
    run, a selftest) see the effect without a server."""
    tables = _chain_tables(manager)
    soc_pins = _index(tables, 'SocPin')
    pin_functions = _index(tables, 'PinFunction')

    def field(reg, name):
        return _index(tables, 'RegisterField').get('%s:%s.%s' % (SOC, reg, name))

    by_register = {}
    routes = []
    routed_functions = set()

    def add_route(pf_name, claim):
        if pf_name and pf_name in pin_functions and pf_name not in routed_functions:
            routed_functions.add(pf_name)
            routes.append(_route_for(solution_name, claim, pf_name, pin_functions[pf_name]))

    for c in pin_claims(solution_name, graph, manager=manager, overrides=overrides):
        sp = soc_pins.get(c['soc_pin'])
        if sp is None:
            continue
        port, bit = sp['port'], sp['bit']
        direction = _ddr_direction(c)
        if direction is not None:
            f = field('DDR%s' % port, 'DD%s%d' % (port, bit))
            if f is not None:
                by_register.setdefault('DDR%s' % port, []).append((f, direction, c['name'], '', c['task'], 'ddr-from-%s' % c['requirement_kind']))
        port_value = None
        if direction == 1 and c['initial'] == 'high':
            port_value = 1
        elif direction == 0 and c['pull'] == 'up':
            port_value = 1
        if port_value is not None:
            f = field('PORT%s' % port, 'PORT%s%d' % (port, bit))
            if f is not None:
                rule = 'port-initial-high' if direction == 1 else 'port-pull-up'
                by_register.setdefault('PORT%s' % port, []).append((f, port_value, c['name'], '', c['task'], rule))
        if c['edge'] not in ('none', 'undetermined'):
            fam, fn = _int_capable(sp)
            pf_name = ''
            if fam == 'EXINT':
                n = fn[3:]
                f = field('EICRA', 'ISC%s' % n)
                if f is not None:
                    by_register.setdefault('EICRA', []).append((f, _ISC_VALUE[c['edge']], c['name'], '', c['task'], 'edge-%s-to-ISC%s' % (c['edge'], n)))
                f = field('EIFR', 'INTF%s' % n)
                if f is not None:
                    by_register.setdefault('EIFR', []).append((f, 1, c['name'], '', c['task'], 'clear-pending-before-enable'))
                f = field('EIMSK', 'INT%s' % n)
                if f is not None:
                    by_register.setdefault('EIMSK', []).append((f, 1, c['name'], '', c['task'], 'enable-external-interrupt'))
                pf_name = '%s:%s:%s' % (SOC, sp['pin'], fn)
            elif fam == 'PCINT':
                k = int(fn[5:]) // 8
                f = field('PCMSK%d' % k, fn)
                if f is not None:
                    by_register.setdefault('PCMSK%d' % k, []).append((f, 1, c['name'], '', c['task'], 'pcint-enable-mask'))
                f = field('PCICR', 'PCIE%d' % k)
                if f is not None:
                    by_register.setdefault('PCICR', []).append((f, 1, c['name'], '', c['task'], 'pcint-bank-enable'))
                pf_name = '%s:%s:%s' % (SOC, sp['pin'], fn)
            add_route(pf_name, c)
        if c['mode'] == 'alt' and c['pin_function']:
            add_route(c['pin_function'], c)

    settings, field_settings = [], []
    for reg_name, specs in sorted(by_register.items()):
        rs, fss = _combine(solution_name, reg_name, 'init', specs, tables)
        settings.append(rs)
        field_settings.extend(fss)
    # a route is 'active' only once a setting that actually ENABLES that alternate function exists — a DDRx/PORTx
    # direction/level setting is not that (D6's DDRD bit is plain GPIO direction, not what turns OC0A on; TCCR0A's
    # COM0A bits would be, but those stay in the HAL this slice — so a PWM/ADC/UART route stays 'planned' here,
    # named, not silently marked active)
    _ACTIVATES = ('edge-', 'enable-external-interrupt', 'pcint-')
    by_claim = {}
    for fs in field_settings:
        if fs.get('pin_claim') and fs['rule'].startswith(_ACTIVATES):
            by_claim.setdefault(fs['pin_claim'], []).append('RegisterFieldSetting:%s' % fs['name'])
    for r in routes:
        refs = by_claim.get(r['pin_claim'], [])
        r['configuration_refs_json'] = json.dumps(refs)
        r['status'] = 'active' if refs else 'planned'
    return {'RegisterSetting': settings, 'RegisterFieldSetting': field_settings, 'SignalRoute': routes}
