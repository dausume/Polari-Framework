"""
@module cmod.custom.node_run

bss-2 (AI-Notes/plans/BENCH_SOLUTION_SIM_PLAN.md section 6b): ONE NODE TEST = ONE DETERMINISTIC TWIN RUN FROM RESET along one path. The Firmware
Solution's hex goes to polari-avr-twin (the engines seam); the path's trigger edges become `--pin-at` stimuli at cycles spaced by each node's guard; the
required struct fields are `--watch`ed by address (the struct instance's data symbol + the field offsets firmware_state derives); the twin's
`watch-change` events (D-bss-12) say the cycle each field changed, so "requirements met at cycle N" is exact. The target node's executions are observed
with one `--fn-cycles entry:ret` run each (the same deterministic history); a pin collateral is read from the `wire-edge` events when the pin is wired.
What is kept is the assessment (3c): StructNodeRun + one StructNodeRunEdge per edge + one StructNodeRunSignal per watched field / wired pin; the events
are the working buffer and are dropped.

    run(manager, bench_solution, node, path='')  -> the run view {run, edges, signals, working_events}
    runs(manager, node)                          -> the kept StructNodeRun rows of a node

A Polari command (bss-7a) is a `--inject` of a frame built from the to-node's exact requirements on the wire fields the command event names (bss-8: the
receiving atom's own presence tests). bss-8 adds the other stimuli: reset = `--reset-at cycle=N` (the twin keeps counting cycles across it; the watches see
the re-init); an analog level (an analog-threshold button, a sensor) = `--adc-at cycle=N,ch=C,mv=M` (new in the twin, prf-board-engines/twin_forcing.c) with
a press pulsed back to the release level after the hold; a period = no stimulus at all, the window is twice the period (the event's value, from the
telemetry_hz knob). A requirement may name an enum LABEL (`source = button`): it is translated to the wire value through the pinned contract's enum list.
"""
import datetime
import hashlib
import json
import os
import tempfile

from cmod.custom import bench_events as E
from cmod.custom import bench_topology as T
from cmod.custom import catom_config as CF
from cmod.custom import config_rows as R
from cmod.custom import isotope_step_rules as S

START_CYCLE = 1600000       # 100 ms in at 16 MHz: past the init at the top of main() (board.custom.light_twin.START_CYCLE)
TAIL_CYCLES = 1600000       # 100 ms after the last guard
DEFAULT_GUARD_S = 0.15      # KNOB: the guard's floor (the 150 ms gap light_twin uses between presses); a node whose executions carry no worst_s gets it too
GUARD_FACTOR = 2.0          # D-bss-2 (recommended): the guard is 2 x the slowest step rule's worst among the node's executions
MAX_WATCH = 8               # the twin's limit
PRESS_HOLD_CYCLES = 80000   # KNOB: a press is a 5 ms pulse (the line low, then back to rest) - light_twin.PRESS_HOLD_CYCLES; a line held low for ever
                            # is not a press (the UNO light toggled twice in the dry run of 2026-11-02 when it was)
_BUILDS = {}                # variant -> (hex, elf, sha, work): one build per process


def _clock(record):
    from board.custom import cycle_records as CR
    return float((CR.load(record) or {}).get('clock_hz') or 16000000)


def _build(variant):
    if variant in _BUILDS:
        return _BUILDS[variant]
    from board.custom import build as B
    from board.custom import gen
    work = tempfile.mkdtemp(prefix='node-run-')
    gen.gen('uno', None, work, variant=variant)
    row = B.build('uno', work)
    if row.get('state') != 'built':
        raise R.ConfigRefused('%s did not build: %s' % (variant, row.get('notes')), status=409)
    hexb = open(row['hex_path'], 'rb').read()
    elf = open(os.path.join(work, 'out', 'firmware.elf'), 'rb').read()
    _BUILDS[variant] = (hexb, elf, hashlib.sha256(hexb).hexdigest(), work)
    return _BUILDS[variant]


def _layout(config, struct, declared):
    """(instance name, {field: (offset, width)}) of the wire struct `struct` from the firmware state of `config`: the instance, the widths AND THE ORDER
    come from the generated packets header as firmware_state parsed it (the generator declares the members sorted by name: boot_session, led_on, name,
    seq, source, status, toggles - checked against lightstate_packets.h on 2026-11-02; the struct map's draft order is NOT the layout). avr-gcc aligns
    every type to 1, so offsets are cumulative (8 + 1 + 64 + 8 + 1 + 1 + 8 = 91, the firmware state's own size). `declared` (the map's fields) must all exist."""
    from board.custom import firmware_state as FS
    doc = FS.derive(config)
    objs = [o for o in FS.rows(doc, 'objects') if o.get('kind') == 'wire-struct' and str(o.get('c_type', '')).startswith(struct + ' ')]
    if not objs:
        raise R.ConfigRefused('no instance of %s in the firmware state of %s' % (struct, config), status=404)
    inst, obj = str(objs[0]['c_type']).split()[-1], objs[0]['name']
    off, layout = 0, {}
    for f in FS.rows(doc, 'fields'):
        if f.get('object') == obj:
            w = int(f.get('size_bytes') or 1)
            layout[f['field']] = (off, w)
            off += w
    missing = [f for f in declared if f not in layout]
    if missing:
        raise R.ConfigRefused('the struct map names %s.%s but the firmware state has no such field' % (struct, ', '.join(missing)), status=409)
    if int(objs[0].get('size_bytes') or off) != off:
        raise R.ConfigRefused('%s: the fields add up to %d bytes, the firmware state says %s' % (struct, off, objs[0].get('size_bytes')), status=409)
    return inst, layout


def _symbols(elf):
    from board.custom import cycle_measure as CM
    from firmwarefaults.custom import disasm
    return disasm.parse_nm(CM._fe('avr-nm', ['-n', 'firmware.elf'], elf)), CM.symbols(elf)


def _wire_spec(polari_class):
    from board.custom import gen
    from board.custom.compat import wire_spec
    fmap = gen.pinned_contract(polari_class)[0]['field_map']
    return wire_spec(None, polari_class, fmap)


def _coerce(ptype, value):
    if ptype == 'bool':
        return bool(int(float(value))) if str(value).strip() not in ('true', 'false', 'True', 'False') else str(value).strip().lower() == 'true'
    if ptype.startswith(('int', 'uint', 'sint')):
        return int(float(value))
    if ptype in ('float', 'double'):
        return float(value)
    return str(value)


def _enums(manager, object_map):
    """{field: the contract's enum spec} of the struct's enum fields, from the pinned contract (the wire byte: 0 = unknown, labels[i] = i + 1)."""
    som = R.get(manager, 'StructObjectMap', object_map) or {}
    try:
        return {f['name']: f['enum'] for f in _wire_spec(som.get('polari_class', ''))['fields'] if f.get('enum')}
    except Exception:  # noqa: BLE001 - no contract for the class: no labels
        return {}


def _labelled(manager, q):
    """bss-8: a requirement whose value is an enum LABEL ('button') judged by its WIRE byte (2: grpcbridge.custom.wire_contract.enum_to_wire, the same encoder the
    bridge uses); `label` keeps the person's word for the messages."""
    q = dict(q, label=str(q['value']))
    if q['kind'] not in ('exact', 'set') or _num(q['value']) is not None:
        return q
    spec = _enums(manager, q['object_map']).get(q['field'])
    if not spec:
        return q
    from grpcbridge.custom.wire_contract import enum_to_wire
    vals = []
    for word in str(q['value']).split(','):
        word = word.strip()
        vals.append(str(enum_to_wire(spec, word)) if word in spec.get('labels', []) else word)
    q['value'] = ','.join(vals)
    return q


def _command_frame(manager, ev, reqs, seq):
    """bss-7a: the frame a Polari command carries into the to-node: its EXACT requirements on the struct's wire fields, presence-masked to those fields.
    bss-8: only the fields the command event names (`value`: the receiving atom's presence tests) when it names any - the stamps (toggles, source) are the
    firmware's own, never carried."""
    from board.custom import packet_ref
    from grpcbridge.custom import wire_ref
    carry = [f.strip() for f in (ev.get('value') or '').split(',') if f.strip()]
    exact = [_labelled(manager, q) for q in reqs if q['kind'] == 'exact' and (not carry or q['field'] in carry)]
    if not exact:
        raise R.ConfigRefused('the command %r needs the to-node to require exact values on wire fields%s: that is what the frame carries'
                              % (ev['name'], ' (it carries %s)' % ', '.join(carry) if carry else ''), status=422)
    som = R.get(manager, 'StructObjectMap', exact[0]['object_map']) or {}
    spec = _wire_spec(som.get('polari_class', ''))
    types_ = {f['name']: f['ptype'] for f in spec['fields']}
    vals = {q['field']: _coerce(types_[q['field']], q['value']) for q in exact if q['field'] in types_}
    if not vals:
        raise R.ConfigRefused('none of the required fields (%s) is a wire field of %s' % (', '.join(q['field'] for q in exact), som.get('polari_class', '?')), status=422)
    payload = wire_ref.encode(spec, vals, present=list(vals))
    return packet_ref.frame(1, 0, seq, payload, version=spec['wire_version']), vals


def _stimulus(ev, cycle, reqs=(), manager=None, files=None):
    slug = ev['name'].split(':')[-1]
    if ev['kind'] == 'external-signal' and ev['source'] == 'polari':
        frame, vals = _command_frame(manager, ev, reqs, seq=1 + len(files or {}))
        name = 'cmd%d.bin' % cycle
        files[name] = frame
        return ['--inject', '%s@%d' % (name, cycle)]
    if ev['what'] == 'RESET':   # bss-8: the reset line pulled at the cycle; the twin keeps counting cycles across the reset
        return ['--reset-at', 'cycle=%d' % cycle]
    if ev['source'] == 'time':   # bss-8: a period elapses by itself; the edge's window (the guard) is where the change must land
        return []
    if ev['kind'] == 'actuation' and ev['what'].startswith('ADC') and _num(ev['value']) is not None:   # bss-8: an analog level stepped at the cycle
        ch, mv = int(ev['what'][3:]), int(float(ev['value']))
        out = ['--adc-at', 'cycle=%d,ch=%d,mv=%d' % (cycle, ch, mv)]
        if slug.startswith('press-'):   # a press is a pulse: the level back to the release event's rest after the hold
            rest = R.get(manager, 'HardwareEvent', ev['name'].replace(':press-', ':release-')) if manager is not None else None
            if rest and _num(rest.get('value')) is not None:
                out += ['--adc-at', 'cycle=%d,ch=%d,mv=%d' % (cycle + PRESS_HOLD_CYCLES, ch, int(float(rest['value'])))]
        return out
    if ev['kind'] == 'actuation' and ev['source'] == 'person' and ev['value'] in ('low', 'high'):
        level = 0 if ev['value'] == 'low' else 1
        out = ['--pin-at', 'cycle=%d,pin=%s,level=%d' % (cycle, ev['what'], level)]
        if slug.startswith('press-'):   # a press is a pulse: the line goes to its pressed level and back to rest after the hold
            out += ['--pin-at', 'cycle=%d,pin=%s,level=%d' % (cycle + PRESS_HOLD_CYCLES, ev['what'], 1 - level)]
        return out
    raise R.ConfigRefused('Hardware Event %r (%s from %s, %s = %r) cannot be applied to the twin: a pin level, an ADC level, a command, a reset and a period can'
                          % (ev['name'], ev['kind'], ev['source'], ev['what'], ev['value']), status=422)


def _guard_cycles(manager, node, hz):
    worst = [S.rule_for(manager, x['isotope'])['worst_s'] for x in R.rows(manager, 'StructNodeExecution', node=node) if x['isotope']]
    worst = [w for w in worst if w and w > 0]
    slowest = max(worst) if worst else -1.0
    return int(GUARD_FACTOR * max(slowest, DEFAULT_GUARD_S) * hz), slowest   # the floor keeps a fast interrupt node from collapsing the spacing


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _holds(q, value, changed):
    if q['kind'] == 'written':
        return changed
    v, want = _num(value), str(q['value'])
    if q['kind'] == 'exact':
        return (v is not None and _num(want) is not None and v == _num(want)) or str(value) == want
    if q['kind'] == 'range' and v is not None and '..' in want:
        lo, hi = (_num(x) for x in want.split('..', 1))
        return lo is not None and hi is not None and lo <= v <= hi
    if q['kind'] == 'set':
        return str(value) in [x.strip() for x in want.split(',')] or (v is not None and v in [_num(x) for x in want.split(',')])
    return False


class _Timeline:
    """One watched field: its changes [(cycle, from, to)] from the twin's watch-change events and its final value."""

    def __init__(self, changes, final):
        self.changes = sorted(changes)
        self.final = final if final is not None else (changes and changes[-1][2])
        self.first = self.changes[0][1] if self.changes else self.final

    def at(self, cycle):
        v = self.first
        for c, _f, t in self.changes:
            if c <= cycle:
                v = t
        return v

    def changed_in(self, lo, hi, upto=None):
        return any(lo <= c < hi and (upto is None or c <= upto) for c, _f, _t in self.changes)


def _judge(plan_edge, reqs, lines, hz):
    """-> (outcome, met_cycle, words) for one edge: the earliest cycle in its window at which every requirement of its to-node holds at once."""
    lo, hi = plan_edge['s'], plan_edge['end']
    if not reqs:
        return 'met', lo, 'no requirements on %s: met as soon as its edge starts' % plan_edge['edge']['to_node']
    cands = sorted({lo} | {c for q in reqs for c, _f, _t in lines[q['field']].changes if lo <= c < hi})
    for c in cands:
        if all(_holds(q, lines[q['field']].at(c), lines[q['field']].changed_in(lo, hi, upto=c)) for q in reqs):
            return 'met', c, 'met at cycle %d (%.3f ms after the stimulus)' % (c, (c - lo) * 1e3 / hz)
    bad = [q for q in reqs if lines[q['field']].changed_in(lo, hi) and not _holds(q, lines[q['field']].at(hi - 1), True)]
    if bad:
        return 'diverged', -1, '; '.join('%s became %s, required %s %s' % (q['field'], lines[q['field']].at(hi - 1), q['kind'], q.get('label', q['value'])) for q in bad)
    return 'not-reached', -1, '; '.join('%s stayed %s, required %s %s' % (q['field'], lines[q['field']].at(hi - 1), q['kind'], q.get('label', q['value'])) for q in reqs)


def _events(r):
    out = []
    for line in (r.get('stdout') or '').splitlines():
        if line.startswith('{"t":"'):
            try:
                out.append(json.loads(line))
            except ValueError:
                pass
    return out


_NOINLINE = {}


def _noinline(variant):
    """The -fno-inline build of the same sources (cyc-0's way): the shipped hex inlines the atoms, so they have no entry to count."""
    if variant not in _NOINLINE:
        from board.custom import cycle_measure as CM
        pair = CM.build_pair(variant, tempfile.mkdtemp(prefix='node-run-noinline-'))
        _NOINLINE[variant] = (pair['noinline']['hex'], CM.symbols(pair['noinline']['elf']))
    return _NOINLINE[variant]


def _executions(manager, node, variant, text_symbols, argv, hexb, lo, hi, files=None):
    from firmwarefaults.custom import harness
    words = []
    for x in sorted(R.rows(manager, 'StructNodeExecution', node=node), key=lambda x: x['order']):
        fn = x['atom'].split('.')[-1]
        syms, hx, where = text_symbols.get(fn) or [], hexb, 'the shipped hex'
        if not syms:
            hx, ts = _noinline(variant)
            syms, where = ts.get(fn) or [], 'the -fno-inline build (the shipped hex inlines it; cyc-0 measures atoms the same way)'
        if not syms:
            words.append('%s: no symbol in either build' % fn)
            continue
        r = harness.run_files(argv + ['--fn-cycles', '0x%X:ret' % syms[0][0]], hx, files or {}, timeout=300)
        fc = (r.get('final') or {}).get('fn_cycles') or {}
        n = int(fc.get('n') or 0)
        words.append('%s: %s (ran n=%d times over the WHOLE run, %s..%s cycles each, in %s; a per-edge count needs cycle-stamped calls: bss-3)'
                     % (fn, 'observed' if n else 'not observed', n, fc.get('min', '?'), fc.get('max', '?'), where))
    return ' ; '.join(words)


def _collaterals(manager, node, events, wired, lo, hi, met, hz, uart_len):
    words = []
    for c in R.rows(manager, 'StructNodeCollateral', node=node):
        if c['kind'] == 'pin-level':
            if c['signal'] not in wired:
                words.append('pin-level %s: unmeasured (no wire on %s in this config; the VCD pin trace is bss-3)' % (c['signal'], c['signal']))
                continue
            edges = [e for e in events if e.get('t') == 'wire-edge' and c['signal'] in (e.get('src'), e.get('dst')) and lo <= int(e.get('cycle', -1)) < hi]
            if not edges:
                words.append('pin-level %s: no change in the window%s' % (c['signal'], (' (bound %s: unmet)' % c['bound']) if c['bound'] else ''))
                continue
            last = edges[-1]
            level = 'high' if int(last.get('v', 0)) else 'low'
            verdict = '' if not c['bound'] else (' (bound %s: met)' % c['bound'] if c['bound'] == level else ' (bound %s: UNMET)' % c['bound'])
            words.append('pin-level %s: %s at cycle %d, %.3f ms after the stimulus%s' % (c['signal'], level, int(last['cycle']), (int(last['cycle']) - lo) * 1e3 / hz, verdict))
        elif c['kind'] == 'frame':
            words.append('frame %s: %d bytes on the UART over the run (per-frame cycles are bss-3)' % (c['signal'], uart_len))
        elif c['kind'] == 'timing':
            words.append('timing: %s' % ('%.3f ms' % ((met - lo) * 1e3 / hz) if met >= 0 else 'not reached'))
        else:
            words.append('%s %s: not measured by the twin (ngspice / Cauer come in bss-3)' % (c['kind'], c['signal']))
    return ' ; '.join(words)


def run(manager, bench_solution, node, path='', profile='', play_from=''):
    ctx = CF.context(manager, bench_solution)
    n = R.get(manager, 'StructNode', node)
    if n is None:
        raise R.ConfigRefused('no node %r' % node, status=404)
    stamp = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds')
    name = '%s#run%d' % (node, len(R.rows(manager, 'StructNodeRun', node=node)) + 1)
    blocked = T.blocks(manager, node)
    if blocked:
        row = R.upsert(manager, 'StructNodeRun', name, node=node, path=path, outcome='blocked', ran_at=stamp, words='; '.join(blocked), **T.step_of(manager, node))
        return {'ok': True, 'run': row, 'edges': [], 'signals': [], 'working_events': 0}
    ps = R.rows(manager, 'StructNodePath', node=node)
    p = next((x for x in ps if x['name'] == path), None) if path else next((x for x in ps if x['fastest']), None)
    if p is None:
        raise R.ConfigRefused('no path %r to %r' % (path or 'fastest', node), status=404)
    variant = E.variant_of(manager, ctx['firmware_solution'])
    hz = _clock(variant)
    edges = [R.get(manager, 'StructEdge', e) for e in p['edges'].split(',')]
    # the plan: a stimulus cycle per trigger edge, spaced by the to-node's guard
    plan, stimuli, cycle, last_s, files = [], [], START_CYCLE, 0, {}
    for e in edges:
        if e['kind'] in ('flash', 'init'):
            plan.append({'edge': e, 's': 0, 'guard_s': -1.0})
        elif e['kind'] == 'cascade':
            plan.append({'edge': e, 's': last_s, 'guard_s': -1.0})
        else:
            ev = R.get(manager, 'HardwareEvent', e['event'])
            if ev is None:
                raise R.ConfigRefused('edge %r names the Hardware Event %r, which no longer exists' % (e['name'], e['event']), status=404)
            stimuli += _stimulus(ev, cycle, R.rows(manager, 'StructNodeRequirement', node=e['to_node']), manager, files)
            g, worst = _guard_cycles(manager, e['to_node'], hz)
            if ev['source'] == 'time' and _num(ev['value']):   # bss-8: a period's window is at least GUARD_FACTOR periods
                g = max(g, int(GUARD_FACTOR * float(ev['value']) * hz))
            plan.append({'edge': e, 's': cycle, 'guard_s': g / hz, 'worst_s': worst})
            last_s, cycle = cycle, cycle + g
    end = cycle + TAIL_CYCLES
    for i, pe in enumerate(plan):
        nxt = next((x['s'] for x in plan[i + 1:] if x['s'] > pe['s']), end)
        pe['end'] = nxt if pe['s'] else (next((x['s'] for x in plan if x['s'] > 0), end))
    # the watches: every required field along the path (an enum label judged by its wire value, bss-8)
    reqs = {pe['edge']['to_node']: [_labelled(manager, q) for q in R.rows(manager, 'StructNodeRequirement', node=pe['edge']['to_node'])] for pe in plan}
    fields = []
    for qs in reqs.values():
        for q in qs:
            if (q['object_map'], q['field']) not in fields:
                fields.append((q['object_map'], q['field']))
    prof_pins = []
    if profile:   # bss-3: a named TestProfile adds fields to watch and pins to report (the derived default is the node's own requirements and collaterals)
        if R.get(manager, 'TestProfile', profile) is None:
            raise R.ConfigRefused('no TestProfile %r' % profile, status=404)
        for it in R.rows(manager, 'TestProfileItem', profile=profile):
            if it['kind'] == 'field' and (it['object_map'], it['signal']) not in fields:
                fields.append((it['object_map'], it['signal']))
            elif it['kind'] == 'pin':
                prof_pins.append(it['signal'])
    if len(fields) > MAX_WATCH:
        raise R.ConfigRefused('%d required fields along the path; the twin watches at most %d per run (split the path or the node)' % (len(fields), MAX_WATCH))
    hexb, elf, sha, _work = _build(variant)
    nm, text_symbols = _symbols(elf)
    watches = []
    for om, f in fields:
        som = R.get(manager, 'StructObjectMap', om) or {}
        struct = som.get('struct', '')
        declared = [x.get('field') for x in json.loads(som.get('fields_json') or '[]') if x.get('field')]
        inst, layout = _layout(ctx['firmware_solution'], struct, declared)
        if inst not in nm or f not in layout:
            raise R.ConfigRefused('cannot watch %s.%s: %s' % (struct, f, 'no data symbol %r in the ELF' % inst if inst not in nm else 'no such field in the firmware state'), status=404)
        off, w = layout[f]
        watches += ['--watch', '0x%X/%d=%s' % (nm[inst]['addr'] + off, min(w, 4), f)]
    rest = []
    try:
        from board.custom import light_button as LB
        wire = LB.wire_args(variant)
        rest = (LB.default_adc(variant) or '').split()   # bss-8: an analog-threshold button rests at the pull-up's level, else the twin's default
    except Exception:  # noqa: BLE001 - a config without the sense feature has no wire
        wire = []
    wired = {p for a in wire[1::2] for p in a.split(':')}
    unwired = [p for p in prof_pins if p not in wired]
    from firmwarefaults.custom import harness
    argv = ['--hex', 'firmware.hex', '--mcu', 'atmega328p', '--freq', '%d' % hz, '--free', '--seconds', '%g' % (end / hz), '--status-ms', '0', '--uart-out', 'uart.bin'] + rest + wire + watches + stimuli
    r = harness.run_files(argv, hexb, files, timeout=300)   # the command frames travel with the hex
    if not r.get('ok'):
        raise R.ConfigRefused('the twin run did not complete: %s' % ((r.get('stderr') or r.get('stdout') or '')[-300:]), status=409)
    events = _events(r)
    finals = {w.get('name'): w.get('final', w.get('value')) for w in ((r.get('final') or {}).get('watches') or []) if isinstance(w, dict)}   # [{name, addr, w, final}]
    lines = {f: _Timeline([(int(e['cycle']), e.get('from'), e.get('to')) for e in events if e.get('t') == 'watch-change' and e.get('name') == f], finals.get(f))
             for _om, f in fields}
    no_change_events = not any(e.get('t') == 'watch-change' for e in events)
    # judge edge by edge
    edge_rows, failed, met_target, replayed_done, failed_checks = [], False, -1, False, []
    for i, pe in enumerate(plan, 1):
        e = pe['edge']
        if failed:
            outcome, met, words = 'skipped', -1, 'an earlier edge failed'
        elif e['kind'] == 'flash':
            outcome, met, words = 'met', 0, 'the hex %s... is the twin\'s' % sha[:12]
        else:
            outcome, met, words = _judge(pe, reqs[e['to_node']], lines, hz)
        failed = failed or outcome in ('not-reached', 'diverged')
        exe = col = ''
        if play_from and not replayed_done:   # bss-3 play: everything up to the start node is replayed silently
            words = 'replayed silently: ' + words
            replayed_done = e['to_node'] == play_from
        if e['to_node'] == node and outcome == 'met':
            exe = _executions(manager, node, variant, text_symbols, argv, hexb, pe['s'], pe['end'], files)
            col = _collaterals(manager, node, events, wired, pe['s'], pe['end'], met, hz, len(r.get('uart') or b''))
            met_target = met
            failed_checks = _checks(manager, e['name'], lines, (met - pe['s']) / hz, pe['end'])
            if failed_checks:
                words += '; checks failed: ' + '; '.join(failed_checks)
        edge_rows.append(R.upsert(manager, 'StructNodeRunEdge', '%s:%d' % (name, i), run=name, edge=e['name'], order=i, outcome=outcome, stimulus_cycle=pe['s'], met_cycle=met,
                                  duration_s=((met - pe['s']) / hz) if met >= 0 else -1.0, executions=exe, collaterals=col, words=words))
    target = next(pe for pe in plan if pe['edge']['to_node'] == node)
    last = edge_rows[-1]
    outcome = last['outcome'] if last['outcome'] in ('met', 'not-reached', 'diverged') else next((x['outcome'] for x in edge_rows if x['outcome'] != 'met'), 'met')
    outcome = 'reached' if outcome == 'met' else outcome
    if outcome == 'reached' and failed_checks:
        outcome = 'checks-failed'
    worst = target.get('worst_s', -1.0)
    dur_by = ('the %s guard: %.3g ms worst among the node\'s executions (measured %.3f ms)' % ('execution', worst * 1e3, (met_target - target['s']) * 1e3 / hz)
              if met_target >= 0 and worst > 0 else ('measured on the twin: no execution rule carries a worst case' if met_target >= 0 else 'not reached'))
    words = last['words'] + ('; the twin printed no watch-change events: its image predates D-bss-12 (end state only)' if no_change_events else '')
    row = R.upsert(manager, 'StructNodeRun', name, node=node, path=p['name'], outcome=outcome, hex_sha256=sha, engine='twin', ran_at=stamp, words=words,
                   duration_s=((met_target - target['s']) / hz) if met_target >= 0 else -1.0, duration_set_by=dur_by, profile=profile, play_from=play_from,
                   **T.step_of(manager, node))
    from cmod.custom import confirmations as C
    if outcome == 'reached':   # bss-3: the twin's confirmation, for this path and this build (other builds' confirmations are voided, never deleted)
        C.confirm(manager, node, p['name'], 'twin', sha, run=name, words='run %s met the requirements with every check passing' % name)
    elif outcome == 'diverged':   # D-bss-10: the reached values are proposed as a node off the same parent, for a person to accept, loosen and name
        _propose(manager, bench_solution, node, target['edge'], lines, name)
    if unwired:
        words += '; profile pins not wired in this config: ' + ', '.join(unwired)
        row = R.upsert(manager, 'StructNodeRun', name, words=words)
    signals = []
    for _om, f in fields:
        tl = lines[f]
        signals.append(R.upsert(manager, 'StructNodeRunSignal', '%s:field:%s' % (name, f), run=name, kind='field', signal=f, first=str(tl.first), last=str(tl.final),
                                changes=len(tl.changes), first_change_cycle=tl.changes[0][0] if tl.changes else -1, last_change_cycle=tl.changes[-1][0] if tl.changes else -1))
    for pin in sorted(wired):
        ev = [e for e in events if e.get('t') == 'wire-edge' and pin in (e.get('src'), e.get('dst'))]
        if ev:
            signals.append(R.upsert(manager, 'StructNodeRunSignal', '%s:pin:%s' % (name, pin), run=name, kind='pin', signal=pin, first=str(1 - int(ev[0].get('v', 0))),
                                    last=str(ev[-1].get('v')), changes=len(ev), first_change_cycle=int(ev[0]['cycle']), last_change_cycle=int(ev[-1]['cycle'])))
    return {'ok': True, 'run': row, 'edges': edge_rows, 'signals': signals, 'working_events': len(events)}


def _checks(manager, edge, lines, duration_s, end_cycle):
    """The failed StructEdgeCheck rows of an edge, in words ([] = all passed)."""
    out = []
    for c in R.rows(manager, 'StructEdgeCheck', edge=edge):
        if c['kind'] == 'timing':
            if c['bound_s'] >= 0 and duration_s > c['bound_s']:
                out.append('reached in %.3f ms, bound %.3f ms' % (duration_s * 1e3, c['bound_s'] * 1e3))
        elif c['field'] in lines:
            v = _num(lines[c['field']].at(end_cycle - 1))
            if c['kind'] == 'field-tolerance':
                centre = _num(c['value'])
                if v is None or centre is None or abs(v - centre) > float(c['tolerance'] or 0):
                    out.append('%s ended %s, required %s +/- %g' % (c['field'], v, c['value'], c['tolerance']))
            elif c['kind'] == 'field-range' and '..' in str(c['value']):
                lo, hi = (_num(x) for x in str(c['value']).split('..', 1))
                if v is None or lo is None or hi is None or not lo <= v <= hi:
                    out.append('%s ended %s, required %s' % (c['field'], v, c['value']))
        else:
            out.append('%s: the field %s was not watched (add it to the node\'s requirements or a profile)' % (c['kind'], c['field']))
    return out


def _propose(manager, bs, node, edge, lines, run_name):
    """D-bss-10: a node with the REACHED values of the diverged node's required fields, off the same parent by the same edge kind and event; once per value set."""
    reqs = R.rows(manager, 'StructNodeRequirement', node=node)
    reached = {q['field']: str(lines[q['field']].final) for q in reqs if q['field'] in lines}
    for n in R.rows(manager, 'StructNode', bench_solution=bs, basis='proposed'):
        have = {q['field']: q['value'] for q in R.rows(manager, 'StructNodeRequirement', node=n['name'])}
        if have == reached:
            return n['name']
    slug = 'proposed-%d' % (len(R.rows(manager, 'StructNode', bench_solution=bs, basis='proposed')) + 1)
    pname = '%s:%s' % (bs, slug)
    R.upsert(manager, 'StructNode', pname, title='', bench_solution=bs, kind='state', basis='proposed', collaterals='none',
             notes='proposed from run %s: %s diverged here; accept, loosen and name it, or discard it' % (run_name, node))
    om = {q['field']: q['object_map'] for q in reqs}
    for f, v in reached.items():
        R.upsert(manager, 'StructNodeRequirement', '%s:%s' % (pname, f), node=pname, object_map=om.get(f, ''), field=f, kind='exact', value=v)
    R.upsert(manager, 'StructEdge', '%s->%s via %s' % (edge['from_node'], slug, edge['event'].split(':', 1)[-1]) if edge['kind'] == 'trigger' else '%s->%s' % (edge['from_node'], slug),
             title=edge['title'], bench_solution=bs, from_node=edge['from_node'], to_node=pname, kind=edge['kind'], event=edge['event'])
    T.all_paths(manager, bs)
    return pname


def runs(manager, node):
    return sorted(R.rows(manager, 'StructNodeRun', node=node), key=lambda r: r['name'])
