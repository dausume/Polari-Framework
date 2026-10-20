"""
@module electrodevice.custom.cst_modes

cst-0 (PROTOTYPING_VIEWS_PLAN.md §2, §8): THE CIRCUIT STATES OF ONE CONFIG, enumerated without exploding. His words: "a list of different electronic
circuit state changes and what events in the firmware they are tied to".

  catalogue(config, tables)   per component / board pin: the modes it can take and where that was read (a switch: open | closed, external; the LED:
                              follows its driver net; a driver pin: the levels its writer atom drives; an input pin: input-pullup | input-hiz from the HAL
                              init; every pin: high-z at reset)
  states(config, tables)      the REACHABLE states = switches × the driver pin's levels × lifecycle (running | reset) — each named from its modes
                              (idle-led-off, button-held-led-off, led-on, led-on-button-held, reset-high-z, reset-button-held for S1) with `reachable_by`
  transitions(config, tables) every move between two states: external (press / release), firmware (the writer atom -> the pin reader, timed by the press
                              record when it has the step), lifecycle (power/reset -> high-z; init -> the HAL's modes)

Two states differ exactly when the SPICE netlist differs (D-ptv-2): a purely logical firmware state (toggles, source) is NOT a circuit state.
"""
import itertools
import json

from electrodevice.custom import cst_sources as SRC

PIN_MODES = ('driven-low', 'driven-high', 'input-pullup', 'input-hiz', 'high-z')
SWITCH_MODES = ('open', 'closed')


def _canon(board_pin):
    return (board_pin or '').split(':')[-1]


def catalogue(config, tables, manager=None):
    """-> {'circuit', 'why', 'components': {name: {...}}, 'pins': {canon: {...}}, 'driver': {...}|None, 'sources': [...]}"""
    circuit, why = SRC.circuit_for(config, tables, manager)
    comps = [c for c in (tables.get('CircuitComponentDefinition') or []) if c.get('circuit_name') == circuit]
    nets = [n for n in (tables.get('CircuitNetDefinition') or []) if n.get('circuit_name') == circuit]
    pin_nets = [p for p in (tables.get('BoardPinNet') or []) if p.get('circuit') == circuit]
    net_label = {n['name']: n['net'] for n in nets}
    init = SRC.hal_init_modes(config)
    writer = SRC.pin_writer(config, manager)
    pins = {}
    for pn in pin_nets:
        canon = _canon(pn.get('board_pin'))
        if not canon:
            continue
        hi = init.get(canon, {})
        role = pn.get('role', '')
        if writer and writer['pin'] == canon:
            can = ['driven-low', 'driven-high']
            at_init = 'driven-low' if hi.get('initial', 'low') == 'low' else 'driven-high'
            src = (hi.get('source') or 'no HAL init writes this pin') + ' | ' + writer['source']
        elif hi.get('mode') == 'input' and hi.get('pull') == 'up':
            can, at_init, src = ['input-pullup'], 'input-pullup', hi['source']
        elif hi.get('mode') == 'input':
            can, at_init, src = ['input-hiz'], 'input-hiz', hi['source']
        elif hi.get('mode') == 'output':
            can, at_init, src = ['driven-low' if hi.get('initial') != 'high' else 'driven-high'], 'driven-low' if hi.get('initial') != 'high' else 'driven-high', hi['source']
        else:
            can, at_init, src = ['high-z'], 'high-z', 'no HAL init of %s writes %s: it stays as reset left it (high-Z input, no pull)' % (config, canon)
        pins[canon] = {'net': net_label.get(pn.get('circuit_net'), pn.get('circuit_net')), 'role': role, 'can': can + (['high-z'] if 'high-z' not in can else []), 'at_init': at_init,
                       'at_reset': 'high-z', 'source': src, 'init': hi.get('init', '')}
    components = {}
    for c in comps:
        params = json.loads(c.get('params_json') or '{}')
        pins_on = json.loads(c.get('pins_json') or '[]')
        kind = c.get('kind')
        if kind == 'switch':
            components[c['name']] = {'kind': kind, 'modes': list(SWITCH_MODES), 'at_init': params.get('state', 'open'), 'who': 'external (a finger)', 'nets': pins_on,
                                     'source': 'CircuitComponentDefinition %s: a momentary pushbutton, open unless held' % c['name']}
        elif kind in ('led', 'diode'):
            # the driver may sit one passive part away (D6 -> R1 -> the LED's anode net)
            reach = set(pins_on)
            for c2 in comps:
                if c2.get('kind') in ('resistor',) and set(json.loads(c2.get('pins_json') or '[]')) & reach:
                    reach |= set(json.loads(c2.get('pins_json') or '[]'))
            drv = next((p for p, d in pins.items() if d['net'] in reach and 'driven-high' in d['can']), '')
            components[c['name']] = {'kind': kind, 'modes': ['off', 'forward'], 'at_init': 'off', 'who': 'follows %s' % (drv or 'its net'), 'nets': pins_on,
                                     'source': 'CircuitComponentDefinition %s: forward-biased when %s drives its line high through the series resistor' % (c['name'], drv or '?')}
        else:
            components[c['name']] = {'kind': kind, 'modes': ['passive'], 'at_init': 'passive', 'who': 'passive', 'nets': pins_on,
                                     'source': 'CircuitComponentDefinition %s (%s): no mode of its own' % (c['name'], kind)}
    return {'config': config, 'circuit': circuit, 'why': why, 'components': components, 'pins': pins, 'driver': writer, 'init': init,
            'nets': {n['name']: n for n in nets}, 'pin_nets': pin_nets, 'press': SRC.press_record(config)}


def _name(lifecycle, held, led_on):
    if lifecycle == 'reset':
        return 'reset-button-held' if held else 'reset-high-z'
    if led_on:
        return 'led-on-button-held' if held else 'led-on'
    return 'button-held-led-off' if held else 'idle-led-off'


def states(config, tables, cat=None, manager=None):
    """The reachable states, each {name, lifecycle, modes, led, words, reachable_by, evidence}."""
    cat = cat or catalogue(config, tables, manager)
    switches = [n for n, c in cat['components'].items() if c['kind'] == 'switch']
    leds = [n for n, c in cat['components'].items() if c['kind'] in ('led', 'diode')]
    driver = cat['driver']['pin'] if cat['driver'] else None
    out = []
    sw_space = list(itertools.product(SWITCH_MODES, repeat=len(switches))) or [()]
    for lifecycle in ('running', 'reset'):
        levels = (['driven-low', 'driven-high'] if driver and lifecycle == 'running' else ['high-z'])
        for sw in sw_space:
            for lvl in levels:
                held = 'closed' in sw
                led_on = lvl == 'driven-high'
                modes = {}
                for n, s in zip(switches, sw):
                    modes[n] = s
                for n in leds:
                    modes[n] = 'forward' if led_on else 'off'
                for p, d in cat['pins'].items():
                    modes[p] = 'high-z' if lifecycle == 'reset' else (lvl if p == driver else d['at_init'])
                name = _name(lifecycle, held, led_on)
                words = ('every pin high-Z after power-on / reset (before init runs)' if lifecycle == 'reset' else
                         '%s %s; %s' % (driver or 'the driver', 'high — the LED lit' if led_on else 'low — the LED dark',
                                        ', '.join('%s %s' % (p, d['at_init']) for p, d in cat['pins'].items() if p != driver))) + \
                    ('; %s held (closed to GND)' % ', '.join(switches) if held else '; %s released' % ', '.join(switches) if switches else '')
                out.append({'name': name, 'config': config, 'circuit': cat['circuit'], 'lifecycle': lifecycle, 'modes': modes, 'led': 'forward' if led_on else 'off',
                            'words': words, 'reachable_by': '', 'evidence': '; '.join(sorted({d['source'] for d in cat['pins'].values()} | {c['source'] for c in cat['components'].values()}))[:600]})
    return out


def transitions(config, tables, cat=None, sts=None, manager=None):
    cat = cat or catalogue(config, tables, manager)
    sts = sts or states(config, tables, cat, manager)
    names = {s['name'] for s in sts}
    switches = [n for n, c in cat['components'].items() if c['kind'] == 'switch']
    sw = switches[0] if switches else ''
    sw_pin = next((p for p, d in cat['pins'].items() if d['net'] in (cat['components'].get(sw) or {}).get('nets', [])), '')
    drv = cat['driver']
    press = cat['press']
    out = []

    def add(frm, to, kind, trigger, atoms='', timing='', timing_ms=-1.0, evidence='', words='', via=''):
        if frm in names and to in names:
            out.append({'name': '%s:%s->%s#%s%s' % (config, frm, to, kind, (':' + via) if via else ''), 'config': config, 'circuit': cat['circuit'], 'from_state': frm, 'to_state': to, 'kind': kind,
                        'trigger': trigger, 'atoms': atoms, 'timing': timing, 'timing_ms': timing_ms, 'evidence': evidence, 'words': words or '%s -> %s: %s' % (frm, to, trigger)})
    src_words = 'read from the source: no twin record of this step'
    if sw:
        press_t, rel_t = 'press on %s (%s to GND)' % (sw, sw_pin), 'release of %s' % sw
        ext_ev = 'external: a finger; the switch row %s' % sw
        add('idle-led-off', 'button-held-led-off', 'external', press_t, evidence=ext_ev, timing='instant (the contact closes; the firmware has not acted yet)')
        add('button-held-led-off', 'idle-led-off', 'external', rel_t, evidence=ext_ev, timing='instant')
        add('led-on', 'led-on-button-held', 'external', press_t, evidence=ext_ev, timing='instant (the contact closes; the firmware has not acted yet)')
        add('led-on-button-held', 'led-on', 'external', rel_t, evidence=ext_ev, timing='instant')
        add('reset-high-z', 'reset-button-held', 'external', press_t, evidence=ext_ev, timing='instant')
        add('reset-button-held', 'reset-high-z', 'external', rel_t, evidence=ext_ev, timing='instant')
    if drv:
        chain_press = [w for w in drv['writers'] if 'toggle' in w] or drv['writers'][:1]
        chain_cmd = [w for w in drv['writers'] if 'command' in w or 'apply' in w] or drv['writers'][-1:]
        pt = ('measured on the twin: %s..%s ms from the press to %s\'s first rise (%s, %d presses)' % (press['best_ms'], press['worst_ms'], drv['pin'], press['file'], press['runs'])) if press else src_words
        pms = float(press['worst_ms']) if press else -1.0
        pev = ('%s sha256 %s' % (press['file'], press['sha256'][:16])) if press else drv['source']
        # the press-driven flip: the contact has just closed (button-held) -> the writer flips the field -> the reader drives the pin
        add('button-held-led-off', 'led-on-button-held', 'firmware', 'the press, acted on: %s flips %s.%s, %s drives %s high' % (' -> '.join(chain_press), drv['object'].split(':')[-1], drv['field'], drv['reader'], drv['pin']),
            atoms=', '.join(chain_press + [drv['reader']]), timing=pt, timing_ms=pms, evidence=pev, via='press')
        add('led-on-button-held', 'button-held-led-off', 'firmware', 'the press, acted on: %s flips %s.%s, %s drives %s low' % (' -> '.join(chain_press), drv['object'].split(':')[-1], drv['field'], drv['reader'], drv['pin']),
            atoms=', '.join(chain_press + [drv['reader']]), timing=pt, timing_ms=pms, evidence=pev, via='press')
        for frm, to, lvl in (('idle-led-off', 'led-on', 'high'), ('led-on', 'idle-led-off', 'low'), ('button-held-led-off', 'led-on-button-held', 'high'), ('led-on-button-held', 'button-held-led-off', 'low')):
            add(frm, to, 'firmware', 'SET_LED %s=%d from Polari: %s sets %s.%s, %s drives %s %s' % (drv['field'], 1 if lvl == 'high' else 0, ' -> '.join(chain_cmd), drv['object'].split(':')[-1], drv['field'], drv['reader'], drv['pin'], lvl),
                atoms=', '.join(chain_cmd + [drv['reader']]), timing=src_words, evidence=drv['source'], via='set-led')
    inits = sorted({d['init'] for d in cat['pins'].values() if d.get('init')})
    init_words = 'init: %s set the pin modes (%s)' % (', '.join(inits), '; '.join('%s %s' % (p, d['at_init']) for p, d in cat['pins'].items()))
    init_ev = '; '.join(sorted({d['source'].split(' | ')[0] for d in cat['pins'].values()}))[:400]
    add('reset-high-z', 'idle-led-off', 'lifecycle', init_words, atoms=', '.join(inits), timing='the first microseconds of main() (read from the source)', evidence=init_ev)
    add('reset-button-held', 'button-held-led-off', 'lifecycle', init_words + ' while the button is held', atoms=', '.join(inits), timing='the first microseconds of main() (read from the source)', evidence=init_ev)
    for s in sts:
        if s['lifecycle'] == 'running':
            held = any(v == 'closed' for v in s['modes'].values())
            add(s['name'], 'reset-button-held' if held else 'reset-high-z', 'lifecycle', 'power on / reset: every pin returns to high-Z, the pull-ups off',
                timing='at once (the reset line)', evidence='ATmega328P DS40002061B §14.2.1: after reset every port pin is tri-stated (DDxn = 0, PORTxn = 0)')
    # reachable_by on the states
    by_to = {}
    for t in out:
        by_to.setdefault(t['to_state'], []).append('%s (%s)' % (t['trigger'].split(':')[0], t['kind']))
    for s in sts:
        s['reachable_by'] = '; '.join(by_to.get(s['name'], [])) or 'the start (power on)'
    return out
