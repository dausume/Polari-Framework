"""
@module cmod.custom.test_procedures

msv-0b (AI-Notes/plans/MEASURED_VS_SIMULATED_PLAN.md section 5b): THE STEP-BY-STEP MANUAL TEST of a Bench Solution's built units, GENERATED from what
is already there, never written by hand. The sources are:
- the topology (each node's fastest path from the root, and its edges' Hardware Events)
- the bench circuit rows (the nets, their board pins and the parts)
- each node's measurement points (msv-0)
- the circuit state its latest reached run left (what a person can see: the LED lit or dark).

  generate(manager, bs, hex_sha256='')   -> {steps, owed, hex_sha256, layout} - derived on read, nothing stored
  freeze(manager, bs, body)              -> the TestProcedure + its TestProcedureStep rows (an unchanged regeneration returns the frozen one)
  procedures(manager, bs) / steps(manager, proc)

The order:
  1. Power off. Continuity checks between the circuit's board pins, and between each of them and its header neighbours: a solder bridge beeps
     before power is ever applied. The 5 V header pin to GND is checked, and so is each switch (open, then held).
  2. Power on, flash, boot (the root chain's edges).
  3. Every state node, grouped so a node whose fastest path extends the one just walked continues from it. Otherwise RESET first (back to boot),
     then that path's stimuli. Each node ends with its measurements (its points) and what to look at (its circuit state's LED).
A node with no reached run has no points and no known circuit state yet. That is said in `owed`, and its stimuli are still listed.
"""
import datetime
import json

from cmod.custom import config_rows as R

#: the UNO R3's header order (the board's silkscreen, left to right with the USB on the left): neighbours = one apart within one header
HEADERS = (('D0', 'D1', 'D2', 'D3', 'D4', 'D5', 'D6', 'D7'), ('D8', 'D9', 'D10', 'D11', 'D12', 'D13', 'GND', 'AREF'),
           ('IOREF', 'RESET', '3V3', '5V', 'GND', 'GND', 'VIN'), ('A0', 'A1', 'A2', 'A3', 'A4', 'A5'))


def _now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds')


def board_label(soc_pin):
    """PD2 -> D2, ADC0 -> A0 (board_uno's D_PINS / A_PINS); a label already on the board stays."""
    from board.custom.board_uno import A_PINS, D_PINS
    v = str(soc_pin or '')
    if v.startswith('ADC') and v[3:].isdigit():
        return 'A' + v[3:]
    return next((c for c, (s, _n) in list(D_PINS.items()) + list(A_PINS.items()) if s == v), v)


def _neighbours(pin):
    out = []
    for h in HEADERS:
        for i, p in enumerate(h):
            if p == pin:
                out += [h[j] for j in (i - 1, i + 1) if 0 <= j < len(h) and h[j] not in ('GND',)]
    return out


def _context(manager, bs):
    from cmod.custom import bench_events as E
    from cmod.custom import catom_config as CF
    from cmod.custom import node_electrical as NE
    if R.get(manager, 'BenchSolution', bs) is None:
        raise R.ConfigRefused('no Bench Solution %r' % bs, status=404)
    variant = E.variant_of(manager, CF.context(manager, bs)['firmware_solution'])
    c = NE.circuit(variant)
    return variant, (c if 'cat' in c else None)


def _pins(net_row):
    try:
        return [r.split(':')[-1] for r in json.loads(net_row.get('board_pins_refs_json') or '[]')]
    except ValueError:
        return []


_FIELDS = ('node', 'edge', 'event', 'point', 'mode', 'plus_at', 'minus_at', 'part', 'basis')


def _step(kind, words, expect='', **kw):
    return dict({f: '' for f in _FIELDS}, kind=kind, words=words, expect=expect, **kw)


def _continuity(cat):
    """Power-off checks from the circuit rows: pins sharing a net beep; each pin against its header neighbours (another net) does not; 5V-GND does
    not; a switch beeps only while held."""
    nets = {n['net']: _pins(n) for n in cat['nets'].values()}
    pin_net = {p: net for net, ps in nets.items() for p in ps}
    out, seen = [], set()
    basis = 'the bench circuit rows (%s): %s' % (cat['circuit'], '; '.join('%s on %s' % (net, '/'.join(ps)) for net, ps in nets.items() if ps))

    def pair(a, b, beep, why):
        key = tuple(sorted((a, b)))
        if key in seen:
            return
        seen.add(key)
        out.append(_step('continuity', 'continuity mode: red probe on %s, black on %s' % (a, b), 'BEEP (%s)' % why if beep else 'NO beep (%s)' % why,
                         mode='continuity', plus_at=a, minus_at=b, basis=basis))

    out.append(_step('continuity', 'continuity mode: red probe on the 5V header pin, black on a GND header pin',
                     'NO steady beep (a steady beep is a short across the supply; a brief chirp while the board\'s capacitors charge is normal)',
                     mode='continuity', plus_at='5V', minus_at='GND', basis='the UNO\'s 5V and GND header pins are never joined on a good build'))
    for net, ps in nets.items():
        for i, a in enumerate(ps):
            for b in ps[i + 1:]:
                pair(a, b, True, '%s and %s are both on the net %s' % (a, b, net))
    for net, ps in nets.items():
        for a in ps:
            for b in _neighbours(a):
                if pin_net.get(b) != net:
                    pair(a, b, False, '%s is on %s, its header neighbour %s is %s: a beep is a solder bridge' % (a, net, b, 'on ' + pin_net[b] if b in pin_net else 'not used'))
    for name, comp in cat['components'].items():
        if comp.get('kind') != 'switch' or len(comp['nets']) < 2:
            continue
        a, b = (nets.get(n) or [n if n != 'GND' else 'GND'] for n in comp['nets'][:2])
        a, b = a[0], b[0]
        out.append(_step('continuity', 'continuity mode: red probe on %s, black on %s, the button %s NOT pressed' % (a, b, name), 'NO beep (the switch is open)',
                         mode='continuity', plus_at=a, minus_at=b, part=name, basis='%s joins %s and %s only while held' % (name, comp['nets'][0], comp['nets'][1])))
        out.append(_step('continuity', 'continuity mode: red probe on %s, black on %s, and press and HOLD the button %s' % (a, b, name), 'BEEP while held (the switch closes)',
                         mode='continuity', plus_at=a, minus_at=b, part=name, basis='%s joins %s and %s only while held' % (name, comp['nets'][0], comp['nets'][1])))
    return out


def _switch_on(cat, label):
    if cat is None:
        return ''
    for net in cat['nets'].values():
        if label in _pins(net):
            return next((n for n, c in cat['components'].items() if c.get('kind') == 'switch' and net['net'] in c['nets']), '')
    return ''


def stimulus_words(manager, ev, cat=None):
    """-> (words, part) for one Hardware Event, in a person's words."""
    from cmod.custom import node_run as NR
    slug = ev['name'].split(':')[-1]
    kind = NR._press_kind(slug) or ('release' if slug.startswith('release-') else '')
    label = board_label(ev['what'])
    part = _switch_on(cat, label)
    btn = 'the button on %s' % label + (' (%s)' % part if part else '')
    if ev['what'] == 'RESET':
        return 'press and release the RESET button on the board', ''
    if ev['source'] == 'time':
        return 'wait%s - nothing to touch (%s)' % (' %s s' % ev['value'] if ev.get('value') else '', ev.get('title') or slug), ''
    if ev['kind'] == 'external-signal' and ev['source'] == 'polari':
        return 'send the command %r from Polari through the bridge (%s)' % (ev.get('value') or '', ev.get('title') or slug), ''
    words = {'press': 'press and release %s' % btn,
             'bounce': 'tap %s quickly, a short jabbing press, so the contact bounces' % btn,
             'long-press': 'press %s, hold it for %g s, then release' % (btn, NR.LONG_PRESS_S),
             'held': 'press and HOLD %s - keep holding until this node\'s checks are done' % btn,
             'release': 'release %s' % btn}.get(kind)
    return (words or '%s (%s %s)' % (ev.get('title') or slug, ev['what'], ev.get('value') or '')), part


def _edge_steps(manager, e, node, cat, hex_sha256):
    if e['kind'] == 'flash':
        return [_step('setup', 'flash %s onto the board through the bridge (the flash tool verifies it)' % ('build %s..' % hex_sha256[:12] if hex_sha256 else 'the Firmware Solution\'s build'),
                      'the flash tool reports the verify complete', node=e['to_node'], edge=e['name'], basis='the root chain: %s' % e['name'])]
    if e['kind'] == 'init':
        return [_step('setup', 'wait for the reset after the flash: the firmware starts (the boot node)', 'the board resets once and the firmware runs',
                      node=e['to_node'], edge=e['name'], basis='the root chain: %s' % e['name'])]
    to = R.get(manager, 'StructNode', e['to_node']) or {}
    if e['kind'] == 'cascade':
        return [_step('stimulus', 'nothing to do - it follows by itself from the previous state', 'the board reaches "%s"' % (to.get('title') or e['to_node']),
                      node=e['to_node'], edge=e['name'], basis='a cascade edge (no outside trigger)')]
    ev = R.get(manager, 'HardwareEvent', e['event']) or {'name': e['event'], 'what': '', 'source': '', 'kind': '', 'value': '', 'title': e.get('title', '')}
    words, part = stimulus_words(manager, ev, cat)
    return [_step('stimulus', words, 'the board reaches "%s"' % (to.get('title') or e['to_node']), node=e['to_node'], edge=e['name'], event=ev['name'], part=part,
                  basis='the edge %s (Hardware Event %s)' % (e['name'], ev['name']))]


def _node_state(manager, node, pts):
    from cmod.custom import measure_points as MP
    st = next((p['state'] for p in pts if p.get('state')), '')
    if st:
        return st
    run = MP._latest_reached(manager, node)
    got = MP._state_of(manager, run) if run else None
    return got[2] if got else ''


def _node_checks(manager, n, cat):
    from cmod.custom import measure_points as MP
    pts = [p for p in MP.points(manager, n['name']) if p['origin'] != 'stale']
    out = []
    for p in pts:
        from cmod.custom.measure_readings import fmt
        out.append(_step('measure', '%s mode: %s' % (p['quantity'], p['where']), '%s (the simulation; %s)' % (fmt(float(p['nominal']), p['si_unit']), p['source']),
                         node=n['name'], point=p['name'], mode=p['quantity'], plus_at=p['plus_at'], minus_at=p['minus_at'],
                         part=p['plus_at'] if p['quantity'] == 'I dc' else '', basis=p['basis']))
    state_name = _node_state(manager, n['name'], pts)
    st = next((s for s in ((cat or {}).get('_states') or []) if s['name'] == state_name), None)
    if st is not None:
        for comp, mode in sorted(st['modes'].items()):
            c = cat['components'].get(comp) or {}
            if c.get('kind') == 'led':
                lit = mode == 'forward'
                out.append(_step('observe', 'look at the LED %s' % comp, 'it is %s' % ('LIT' if lit else 'DARK'), node=n['name'], part=comp,
                                 basis='circuit %s in state %s: %s' % (cat['circuit'], state_name, st.get('words', ''))))
    owed = '' if (pts or st) else ('%s: no reached run - its measurements and what to look at come once it is run (the Nodes tab)' % n['name'])
    return out, owed


def generate(manager, bs, hex_sha256=''):
    from cmod.custom import node_electrical as NE
    variant, c = _context(manager, bs)
    nodes = {n['name']: n for n in R.rows(manager, 'StructNode', bench_solution=bs)}
    states = [n for n in nodes.values() if n['kind'] == 'state']
    if not states:
        raise R.ConfigRefused('Bench Solution %s has no state nodes: define its topology first (the light spec, or the canvas)' % bs, status=409)
    edges = {e['name']: e for e in R.rows(manager, 'StructEdge', bench_solution=bs)}
    if not hex_sha256:
        hexes = [r.get('hex_sha256') for n in states for r in R.rows(manager, 'StructNodeRun', node=n['name']) if r.get('hex_sha256')]
        hex_sha256 = max(set(hexes), key=hexes.count) if hexes else ''
    cat = None
    owed = []
    if c is not None:
        cat = dict(c['cat'], _states=c['states'])
    else:
        owed.append('no bench circuit rows for %s: the power-off continuity checks, the measurements and the look-checks are owed' % variant)
    steps = [_step('setup', 'power OFF: unplug the USB cable from the board', 'the board\'s ON LED is dark', basis='the continuity checks need the board unpowered')]
    steps += _continuity(cat) if cat else []
    steps.append(_step('setup', 'plug the USB cable into the bridge host: the board powers up', 'the board\'s ON LED is lit and the bridge sees its serial device',
                       basis='the root node: plugged in'))

    def fastest(n):
        p = next((x for x in R.rows(manager, 'StructNodePath', node=n['name']) if x['fastest']), None)
        return [edges[x] for x in (p['edges'].split(',') if p and p['edges'] else []) if x in edges]

    walked = []
    root_done = False
    for n in sorted(states, key=lambda n: ([e['name'] for e in fastest(n)], n['name'])):
        path = fastest(n)
        if not path:
            owed.append('%s: no path from the root' % n['name'])
            continue
        root_part = [e for e in path if e['kind'] in ('flash', 'init')]
        trig = [e for e in path if e['kind'] not in ('flash', 'init')]
        if not root_done:
            for e in root_part:
                steps += _edge_steps(manager, e, n['name'], cat, hex_sha256)
            root_done = True
        if walked == trig[:len(walked)] and walked:
            todo = trig[len(walked):]
        else:
            if walked:
                steps.append(_step('stimulus', 'press and release the RESET button on the board: back to the start (boot)', 'the firmware starts again',
                                   node=n['name'], basis='%s is not reached from the state just tested: its path starts again from boot' % n['name']))
            todo = trig
        for e in todo:
            steps += _edge_steps(manager, e, n['name'], cat, hex_sha256)
        walked = trig
        checks, why = _node_checks(manager, n, cat)
        steps += checks
        if why:
            owed.append(why)
    for i, s in enumerate(steps, 1):
        s['order'] = i
    return {'bench_solution': bs, 'variant': variant, 'hex_sha256': hex_sha256, 'layout': variant, 'steps': steps, 'owed': owed,
            'circuit': cat['circuit'] if cat else ''}


_SIG = ('kind', 'words', 'expect', 'node', 'point', 'edge')


def freeze(manager, bs, body=None):
    body = body or {}
    g = generate(manager, bs, str(body.get('hex_sha256') or ''))
    sig = [tuple(s.get(k, '') for k in _SIG) for s in g['steps']]
    for p in procedures(manager, bs):
        if p['hex_sha256'] == g['hex_sha256'] and p['layout'] == g['layout'] and [tuple(s.get(k, '') for k in _SIG) for s in steps(manager, p['name'])] == sig:
            return dict(p, rows=steps(manager, p['name']), unchanged=True)
    name = '%s-proc-%d' % (bs, len(procedures(manager, bs)) + 1)
    for s in g['steps']:
        R.upsert(manager, 'TestProcedureStep', '%s-s%d' % (name, s['order']), procedure=name, **s)
    p = R.upsert(manager, 'TestProcedure', name, bench_solution=bs, hex_sha256=g['hex_sha256'], layout=g['layout'], steps=len(g['steps']),
                 owed='; '.join(g['owed']), at=_now(), notes=str(body.get('notes') or ''))
    return dict(p, rows=steps(manager, name), unchanged=False)


def procedures(manager, bs):
    return sorted(R.rows(manager, 'TestProcedure', bench_solution=bs), key=lambda p: (len(p['name']), p['name']))


def steps(manager, proc):
    return sorted(R.rows(manager, 'TestProcedureStep', procedure=proc), key=lambda s: int(s['order']))
