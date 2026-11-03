"""
@module cmod.custom.bench_events

bss-1 (AI-Notes/plans/BENCH_SOLUTION_SIM_PLAN.md sections 2 and 4): THE HARDWARE EVENTS A BENCH SOLUTION OFFERS, and what each is predicted to change,
both derived from the firmware's own claims (the CatomAssertion rows of its variant) and its HAL values (CatomVariable):

  variant_of(manager, firmware_solution)      the assertion variant of a Firmware Solution (its graph's measured variant, else its own name)
  offered(manager, bench_solution)            -> HardwareEvent rows: press / release per edge-asserted pin (person), a command per bridge received from (polari),
                                                 a period per 'per period' send (time), reset (person, always), a level per adc.in variable (environment);
                                                 derived rows are rewritten, a person's rows (origin 'person') kept
  predicted(manager, bench_solution, event)   -> the chain the assertions predict: [{stage, atom, kind, fields, pins, bridge, assertion}] in order
                                                 (hardware-event-result -> cascade -> bridge); [] when nothing is asserted (the rule, section 4)

bss-8: the assertions of a variant without its own rows come re-pinned from uno-light's (catom_assertions.for_variant), so every light build offers its
events: an analog-threshold button offers press / release as ADC LEVELS (what 'ADC0', value in mV: the switch to ground / the pull-up's rest level); a
command event's `value` names the fields the receiving atom's presence tests take (derived from the atom's own body: LIGHTSTATE_F_LED_ON -> led_on), so
the frame a command edge injects carries only those; a period event's `value` is the period in seconds from the variant's telemetry_hz knob.
"""
import os
import re

from cmod.custom import catom_config as CF
from cmod.custom import config_rows as R

EDGE_EVENTS = ('edge-fall', 'edge-rise')
ADC_PRESSED_MV = 0   # the switch pulls the ADC pin to ground (board.custom.variants: 'pushbutton from A0 to GND')
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))   # polari-framework/


def variant_of(manager, firmware_solution):
    fs = R.get(manager, 'FirmwareSolution', firmware_solution) if getattr(manager, 'objectTables', None) is not None else None
    graph = (fs or {}).get('graph', '')
    try:
        from board.custom.cycle_records import GRAPH_VARIANT
    except ImportError:
        GRAPH_VARIANT = {}
    return GRAPH_VARIANT.get(graph) or firmware_solution


def _assertions(manager, variant):
    rows = R.rows(manager, 'CatomAssertion', variant=variant) if getattr(manager, 'objectTables', None) is not None else []
    if not rows:
        from cmod.custom import catom_assertions as CA
        rows = CA.for_variant(variant)
    return rows


def command_fields(atom, basis):
    """bss-8: the struct fields a receiving atom TAKES from a command frame - the presence bits its own body tests (`m & LIGHTSTATE_F_LED_ON` -> led_on),
    read from the source file the assertion's basis names. [] when the source or the function is not found (said by the caller: the frame then carries
    every exact wire-field requirement, as bss-7a did)."""
    path = basis.split(' (')[0].strip()
    full = os.path.join(_ROOT, path)
    fn = atom.split('.')[-1]
    try:
        src = open(full, encoding='utf-8').read()
    except OSError:
        return []
    m = re.search(r'\n[^\n]*\b%s\s*\([^)]*\)\s*\n\{(.*?)\n\}' % re.escape(fn), src, re.S)
    if not m:
        return []
    found, out = re.findall(r'\b[A-Z][A-Z0-9]*_F_([A-Z0-9_]+)\b', m.group(1)), []
    for f in found:
        f = f.lower()
        if f != 'all' and f not in out:
            out.append(f)
    return out


def _knobs(variant):
    try:
        from board.custom import variants as V
        return V.resolve(V.find(variant))['knobs']
    except Exception:  # noqa: BLE001 - board absent or an unknown variant: no knobs
        return {}


def _adc_levels(variant):
    try:
        from board.custom import light_button as LB
        return ADC_PRESSED_MV, LB.ADC_RELEASED_MV
    except Exception:  # noqa: BLE001
        return ADC_PRESSED_MV, 4800


def _variables(manager, variant):
    return R.rows(manager, 'CatomVariable', variant=variant) if getattr(manager, 'objectTables', None) is not None else []


def _line_name(pin, variables):
    for v in variables:
        if pin and pin in (v.get('board_value', ''), v.get('bench_value', '')):
            return '%s (%s)' % (pin, v['variable'])
    return pin


def _derived(bs, assertions, variables, variant=''):
    ev = []
    seen = set()
    knobs = _knobs(variant)
    takes = [a for a in assertions if a['kind'] == 'changes-field' and a.get('event') == 'uart-rx']   # the atom that applies a command frame
    for a in assertions:
        if a['kind'] == 'changes-field' and a.get('event') in EDGE_EVENTS and a.get('pins'):
            pin = a['pins'].split(',')[0].strip()
            if pin in seen:
                continue
            seen.add(pin)
            line = _line_name(pin, variables)
            ev.append(dict(name='%s:press-%s' % (bs, pin), title='press %s' % line, kind='actuation', source='person', what=pin, value='low' if a['event'] == 'edge-fall' else 'high',
                           origin=a['name'], notes='the asserted %s on %s' % (a['event'], pin)))
            ev.append(dict(name='%s:release-%s' % (bs, pin), title='release %s' % line, kind='actuation', source='person', what=pin, value='high' if a['event'] == 'edge-fall' else 'low',
                           origin=a['name'], notes='the line back to rest; the firmware asserts nothing on it'))
        elif a['kind'] == 'changes-field' and a.get('event') == 'level' and a.get('pins', '').startswith('ADC'):   # bss-8: an analog-threshold button
            pin = a['pins'].split(',')[0].strip()
            if pin in seen:
                continue
            seen.add(pin)
            pressed, released = _adc_levels(variant)
            ev.append(dict(name='%s:press-%s' % (bs, pin), title='press the button on %s (the level falls)' % pin, kind='actuation', source='person', what=pin, value=str(pressed),
                           origin=a['name'], notes='the asserted level on %s: the switch pulls the pin to %d mV (below the press threshold)' % (pin, pressed)))
            ev.append(dict(name='%s:release-%s' % (bs, pin), title='release the button on %s (the level rises)' % pin, kind='actuation', source='person', what=pin, value=str(released),
                           origin=a['name'], notes='the pin back at the pull-up\'s %d mV; the firmware asserts nothing on it' % released))
        elif a['kind'] == 'receives-from-bridge' and a.get('bridge'):
            fields = []
            for t in takes:
                fields += [f for f in command_fields(t['atom'], t.get('basis', '')) if f not in fields]
            ev.append(dict(name='%s:command-%s' % (bs, a['bridge']), title='a command arrives on %s' % a['bridge'], kind='external-signal', source='polari',
                           what='a command frame on %s' % a['bridge'], value=','.join(fields), origin=a['name'],
                           notes=('the frame carries %s (the presence bits %s tests, read from its body); the values are the to-node\'s exact requirements'
                                  % (', '.join(fields), ', '.join(t['atom'] for t in takes))) if fields else 'the frame kind and its fields are the node\'s requirements'))
        elif a['kind'] == 'sends-to-bridge' and 'period' in a.get('notes', ''):
            hz = float(knobs.get('telemetry_hz') or 0)
            ev.append(dict(name='%s:period-%s' % (bs, a['atom'].split('.')[-1]), title='the %s period elapses' % a['atom'].split('.')[-1], kind='actuation', source='time',
                           what=a['atom'], value=('%g' % (1.0 / hz)) if hz > 0 else '', origin=a['name'],
                           notes=a['notes'] + ('; the period is %g s from the knob telemetry_hz = %g' % (1.0 / hz, hz) if hz > 0 else '; the period is not known here (no telemetry_hz knob)')))
    ev.append(dict(name='%s:reset' % bs, title='reset', kind='actuation', source='person', what='RESET', value='low', origin='the board (every board has a reset)',
                   notes='back through init: the boot node'))
    for v in variables:
        if v.get('role') == 'adc.in':
            ev.append(dict(name='%s:level-%s' % (bs, v['variable']), title='the level at %s changes' % v['variable'], kind='actuation', source='environment', what=v['variable'],
                           value='', origin=v['name'], notes='a sample value is required on the node (StructFieldSamples)'))
    return ev


def offered(manager, bench_solution):
    ctx = CF.context(manager, bench_solution)
    variant = variant_of(manager, ctx['firmware_solution'])
    assertions, variables = _assertions(manager, variant), _variables(manager, variant)
    derived = _derived(bench_solution, assertions, variables, variant)
    keep = {e['name'] for e in derived}
    for old in R.rows(manager, 'HardwareEvent', bench_solution=bench_solution):
        if old['origin'] != 'person' and old['name'] not in keep:
            R.drop(manager, 'HardwareEvent', name=old['name'])
    out = [R.upsert(manager, 'HardwareEvent', e['name'], bench_solution=bench_solution, **{k: x for k, x in e.items() if k != 'name'}) for e in derived]
    out += [e for e in R.rows(manager, 'HardwareEvent', bench_solution=bench_solution) if e['origin'] == 'person']
    return sorted(out, key=lambda e: e['name'])


def _step(stage, a):
    return {'stage': stage, 'atom': a['atom'], 'kind': a['kind'], 'fields': a.get('fields', ''), 'pins': a.get('pins', ''), 'bridge': a.get('bridge', ''), 'assertion': a['name']}


def predicted(manager, bench_solution, event):
    ctx = CF.context(manager, bench_solution)
    ev = R.get(manager, 'HardwareEvent', event)
    if ev is None:
        raise R.ConfigRefused('no Hardware Event %r' % event, status=404)
    A = _assertions(manager, variant_of(manager, ctx['firmware_solution']))
    chain, changed = [], set()
    if ev['what'] == 'RESET':
        first = [a for a in A if a['kind'] == 'changes-field' and a.get('lane') == 'init']
    elif ev['source'] == 'polari':
        first = [a for a in A if a['kind'] == 'receives-from-bridge' and a.get('bridge') and a['bridge'] in ev['what']]
        chain += [_step('hardware-event-result', a) for a in first]
        first = [a for a in A if a['kind'] == 'changes-field' and a.get('event') == 'uart-rx']
        chain += [_step('cascade', a) for a in first]
    elif ev['source'] == 'time':
        first = [a for a in A if a['atom'] == ev['what'] and a['kind'] == 'changes-field']
    elif ev['what'].startswith('ADC'):   # bss-8: an analog level: a press matches the asserted level, a release asserts nothing
        slug = ev['name'].split(':')[-1]
        first = [a for a in A if a['kind'] == 'changes-field' and ev['what'] in a.get('pins', '').split(',') and a.get('event') == 'level' and slug.startswith('press-')]
    else:
        edge = {'low': 'edge-fall', 'high': 'edge-rise'}.get(ev.get('value', ''))   # a press matches the asserted fall, a release only an asserted rise
        first = [a for a in A if a['kind'] == 'changes-field' and ev['what'] and ev['what'] in a.get('pins', '').split(',') and (edge is None or a.get('event') == edge)]
    if ev['source'] not in ('polari',):
        chain += [_step('hardware-event-result', a) for a in first]
    for a in first:
        changed |= {f.strip() for f in a.get('fields', '').split(',') if f.strip()}
    used = {s['assertion'] for s in chain}
    for a in A:   # the cascades: code that reads a changed field (drives a pin), then the report upward
        if a['name'] in used or a['kind'] != 'reads-field':
            continue
        if changed & {f.strip() for f in a.get('fields', '').split(',')}:
            chain.append(_step('cascade', a))
            used.add(a['name'])
    if changed:
        for a in A:
            if a['name'] not in used and a['kind'] == 'changes-field' and a.get('event') == 'poll':
                chain.append(_step('cascade', a))
                used.add(a['name'])
        for a in A:
            if a['name'] not in used and a['kind'] == 'sends-to-bridge':
                chain.append(_step('bridge', a))
                used.add(a['name'])
    return chain
