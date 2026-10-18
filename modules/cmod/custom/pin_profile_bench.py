"""
@module cmod.custom.pin_profile_bench

pp-0 (MISSION_PROFILE_SOLVER_PLAN.md §2.2): what the BENCH CIRCUIT says about a board pin - read off rows that already exist, never typed
in: the `BoardPinNet` rows (which board pin sits on which circuit net, and whether it outputs onto it or only listens: SIGNAL direction,
D-pv-7) and the circuit's `CircuitComponentDefinition` / `CircuitNetDefinition` rows (LED1, R1, SW1 ...). From them each wired pin gets:
  role        "the LED" | "the button" | "the sense line"  (the part the pin serves, found by walking the net)
  load class  the ELECTRICAL load the pin sees ("an LED through a series resistor to ground", "a switch to ground")
  load        the parts walked, their ohms and the LED's forward-voltage basis (assumed is said, never promoted to a fact)
Live rows win when a manager has them; otherwise the seed rows (the pure path - the same pure/live duality as the rest of cmod).
"""
import inspect
import json


def _d(row):
    keys = [k for k in inspect.signature(type(row).__init__).parameters if k not in ('self', 'manager')]
    return {k: getattr(row, k, None) for k in keys}


def rows(manager, cls, seed):
    """[dict, ...] - the live rows of `cls` when the manager holds any, else the seed rows."""
    live = ((getattr(manager, 'objectTables', None) or {}).get(cls) or {}) if manager is not None else {}
    if live:
        return [r if isinstance(r, dict) else _d(r) for r in live.values()]
    return [dict(x) for x in seed]


def _json(text, default):
    try:
        return json.loads(text) if isinstance(text, str) and text else (text if text not in (None, '') else default)
    except ValueError:
        return default


def _seeds():
    from board.custom import board_pin_nets as BPN
    from electrodevice.objects.circuit import _shared as CS
    return BPN.SEED_BOARD_PIN_NETS, CS.SEED_CIRCUIT_COMPONENTS, CS.SEED_CIRCUIT_NETS


def _chain_to_led(net, comps, ground, used):
    """Walk from `net` through series resistors to an LED. -> {led, terminal (anode|cathode), series [resistor dicts]} | None.
    Convention (the circuit rows' own): an LED's pins_json is [anode net, cathode net]."""
    for c in comps:
        pins = _json(c.get('pins_json'), [])
        if net not in pins or c['name'] in used:
            continue
        if c['kind'] == 'led':
            return {'led': c, 'terminal': 'anode' if pins.index(net) == 0 else 'cathode', 'series': []}
        if c['kind'] == 'resistor':
            for other in (p for p in pins if p != net and p not in ground):
                hit = _chain_to_led(other, comps, ground, used | {c['name']})
                if hit:
                    hit['series'].append(c)
                    return hit
    return None


def bench(board, manager=None):
    """{board pin canonical: info} for every pin of `board` wired onto a bench circuit net.
    info = {pin, circuit, net, signal_role (output|input), role, load_class, load {...}, evidence [row refs], observes (the pin whose line it listens to)}."""
    seed_nets, seed_comps, seed_circ_nets = _seeds()
    pin_nets = [r for r in rows(manager, 'BoardPinNet', seed_nets) if r.get('board') == board and r.get('board_pin')]
    all_comps = rows(manager, 'CircuitComponentDefinition', seed_comps)
    net_rows = {r['name']: r for r in rows(manager, 'CircuitNetDefinition', seed_circ_nets)}
    out = {}
    for pn in pin_nets:
        pin = pn['board_pin'].rpartition(':')[2]
        nrow = net_rows.get(pn.get('circuit_net', ''))
        if nrow is None:
            continue
        net, circuit = nrow['net'], nrow['circuit_name']
        comps = [c for c in all_comps if c.get('circuit_name') == circuit]
        ground = {r['net'] for r in net_rows.values() if r.get('circuit_name') == circuit and r.get('is_ground')}
        sig = 'output' if pn.get('role') in ('output', 'driver') else pn.get('role', '')
        info = {'pin': pin, 'circuit': circuit, 'net': net, 'signal_role': sig, 'role': '', 'load_class': '', 'load': {},
                'evidence': ['BoardPinNet %s' % pn['name'], 'CircuitNetDefinition %s' % nrow['name']], 'observes': ''}
        on_net = [c for c in comps if net in _json(c.get('pins_json'), [])]
        switch = next((c for c in on_net if c['kind'] == 'switch'), None)
        if sig == 'output':
            hit = _chain_to_led(net, comps, ground, set())
            if hit:
                led, series = hit['led'], hit['series']
                lp = _json(led.get('params_json'), {})
                info.update(role='the LED', load_class='an LED through a series resistor to ground' if hit['terminal'] == 'anode'
                            else 'an LED through a series resistor, the pin on its cathode side',
                            load={'part': led['name'], 'terminal': hit['terminal'], 'series_parts': [s['name'] for s in series],
                                  'series_ohms': sum(float(_json(s.get('params_json'), {}).get('ohms', 0)) for s in series),
                                  'v_forward': lp.get('v_forward'), 'v_forward_basis': lp.get('v_forward_basis', 'undetermined')})
                info['evidence'] += ['CircuitComponentDefinition %s' % c['name'] for c in [led] + series]
        elif sig == 'input' and switch is not None:
            other = [p for p in _json(switch.get('pins_json'), []) if p != net]
            to_ground = bool(other) and other[0] in ground
            ext = [c['name'] for c in on_net if c['kind'] == 'resistor']
            info.update(role='the button', load_class='a switch to ground' if to_ground else 'a switch',
                        load={'part': switch['name'], 'to_ground': to_ground, 'external_pull_parts': ext})
            info['evidence'].append('CircuitComponentDefinition %s' % switch['name'])
        out[(pin)] = info
    for pin, info in out.items():          # an input listening to a net another pin outputs onto = the sense line
        if info['role'] or info['signal_role'] != 'input':
            continue
        drivers = [p for p, i in out.items() if i['net'] == info['net'] and i['circuit'] == info['circuit'] and i['signal_role'] == 'output']
        if drivers:
            info.update(role='the sense line', observes=drivers[0],
                        load_class='a listener on the line %s drives' % drivers[0],
                        load={'net': info['net'], 'driven_by': drivers[0]})
    return out
