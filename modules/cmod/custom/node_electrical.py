"""
@module cmod.custom.node_electrical

bss-12 (AI-Notes/plans/BENCH_SOLUTION_SIM_PLAN.md; the user's go on the vital list, 2026-11-03): THE ELECTRICAL CHECK AT EVERY NODE. A node test proves
the structs; this proves the CIRCUIT the firmware left behind at that node does not hurt the chip. Nothing new is modelled: the circuit-states slice
(electrodevice cst-0/1: the bench circuit matched to the config by its pins, the catalogue of modes, one `.op` deck per state, the verdict against the
chip's cited limits - I_PIN 40 mA absolute / 20 mA recommended, VCC/GND 200 mA, DS40002061B) is run for the ONE state the node is in:

  circuit(variant)                     the config's circuit catalogue, its reachable states, the tables and the limits (cached per process; a refusal
                                       in words when no bench circuit names the config's pins)
  driver_pins(variant)                 {SoC pin: board pin} of the pins the circuit's firmware drives - node_run watches their port words at every node
  check(variant, levels, held, ...)    the node's circuit state from the driver pin's settled level (led-on / idle-led-off ...) and whether the button is
                                       held (a `held-` stimulus), its `.op` run and verdict -> {verdict, state, currents, findings, words}; the words
                                       start 'electrical circuit: <ok|warn|REFUSED|undetermined|unmeasured>' so the coverage reads them like any collateral

The deck is the worst-case bound (ideal pin sources, the pull-up at its stronger 20 kΩ end), said in the words. REFUSED makes the run `checks-failed`.
"""
from cmod.custom import config_rows as R  # noqa: F401 - the manager-less rows helpers; kept for the callers' symmetry

_CACHE = {}
SIGNAL = 'circuit'


def _tables():
    from board.custom import electrical_atmega328p as E
    from board.custom import electrical_check as EC
    t = EC.tables_for(None)
    t['ElectricalCharacteristic'] = E.characteristics()
    t['PinGroupBudget'] = E.budgets()
    return t


def _maps():
    """board pin (D6 / A0) <-> SoC pin (PD6 / PC0), from the UNO's own cited pinout (board.custom.board_uno)."""
    from board.custom.board_uno import A_PINS, D_PINS
    c2s = {c: s for c, (s, _n) in {**D_PINS, **A_PINS}.items()}
    return c2s, {s: c for c, s in c2s.items()}


def circuit(variant):
    if variant in _CACHE:
        return _CACHE[variant]
    try:
        from electrodevice.custom import cst_modes as M
        from electrodevice.custom import cst_verdict as V
        from electrodevice.custom.cst_sources import SourceRefused
        t = _tables()
        try:
            cat = M.catalogue(variant, t)
            out = {'cat': cat, 'states': M.states(variant, t, cat), 'tables': t, 'lim': V.limits(t)}
        except SourceRefused as e:
            out = {'refused': str(e)}
    except Exception as e:  # noqa: BLE001 - electrodevice absent, or a config the slice cannot read: said, never raised into a node run
        out = {'refused': 'the circuit-states slice could not read %s: %s' % (variant, e)}
    _CACHE[variant] = out
    return out


def driver_pins(variant):
    c = circuit(variant)
    if 'cat' not in c:
        return {}
    c2s, _s2c = _maps()
    return {c2s[p]: p for p, d in c['cat']['pins'].items() if 'driven-high' in d['can'] and p in c2s}


def check(variant, levels, held=False, lifecycle='running'):
    """levels: {SoC pin: 'high' | 'low'} settled at the node; held: the button closed for the whole window (a `held-` stimulus)."""
    c = circuit(variant)
    if 'cat' not in c:
        return {'verdict': 'unmeasured', 'state': '', 'currents': {}, 'findings': [], 'words': 'electrical %s: unmeasured - %s' % (SIGNAL, c['refused'])}
    from electrodevice.custom import cst_modes as M
    from electrodevice.custom import cst_netlist as N
    from electrodevice.custom import cst_verdict as V
    cat, c2s = c['cat'], _maps()[0]
    driver = cat['driver']['pin'] if cat['driver'] else ''
    soc = c2s.get(driver, '')
    if driver and soc not in levels:
        return {'verdict': 'unmeasured', 'state': '', 'currents': {}, 'findings': [],
                'words': 'electrical %s: unmeasured - the driver pin %s (%s) has no settled level at this node (no jumper read and no port word watched)' % (SIGNAL, driver, soc)}
    led_on = bool(driver) and levels.get(soc) == 'high'
    name = M._name(lifecycle, bool(held), led_on)
    state = next((s for s in c['states'] if s['name'] == name), None)
    if state is None:
        return {'verdict': 'unmeasured', 'state': name, 'currents': {}, 'findings': [],
                'words': 'electrical %s: unmeasured - the circuit %s has no state %s (its states: %s)' % (SIGNAL, cat['circuit'], name, ', '.join(s['name'] for s in c['states']))}
    run = N.run(state, cat, N.PULLUP_OHMS[0]) if lifecycle == 'running' else None
    j = V.judge(state, run, cat, c['lim'])
    verdict = {'refuse': 'REFUSED', 'ok': 'ok', 'warn': 'warn'}.get(j['verdict'], j['verdict'])
    cur = ', '.join('%s %.3f mA' % (k[2:-1], v) for k, v in sorted(j['currents'].items()) if k.startswith('i('))
    lim = c['lim']
    words = ('electrical %s: %s - circuit %s in state %s (%s); %s; %s; .op by ngspice batch, the pins as ideal sources and the pull-up at %d ohm (the worst-case bound, '
             'said); limits I_PIN %s mA recommended / %s mA absolute, VCC-GND %s mA (%s)'
             % (SIGNAL, verdict, cat['circuit'], name, state['words'][:120], j['words'][:300] or 'no finding', ('currents ' + cur) if cur else 'no currents (not simulated)',
                N.PULLUP_OHMS[0], lim.get('pin_recommended_ma'), lim.get('pin_abs_max_ma'), lim.get('supply_abs_max_ma'), (lim.get('cite') or {}).get('pin_abs_max', 'cited rows')))
    return {'verdict': verdict, 'state': name, 'currents': j['currents'], 'findings': j['findings'], 'words': words}
