"""
@module cmod.custom.approach_profile_input

rt-0: the Mission read into the SHAPE the approach profiler works on (also the shape a test hands in directly). Everything here is DERIVED from rows
that already exist - the Mission's Purposes (their trigger and criteria), each Purpose's c-device tasks, the graphs' nodes / edges / schedule lanes
(`cmod.custom.firmware.schedule_for`), the atoms' measured sizes and source (`approach_profile_atoms`), the board's bare-c RuntimeProfile row (clock,
baud, tick) and the recorded build (`cmod/custom/glue_builds/<graph>.json`).

spec = {mission, board_ref, source, purposes: [Purpose], processors: [Processor], notes: []}
  Purpose    {purpose, importance, title, trigger {kind, what}, deadline_ms (q|None), deadline_key, debounce_ms (q|None), period_ms (q|None),
              tasks [instance names], graph}
  Processor  {name (the graph), board, clock_hz, baud, frame_bytes, tasks [Task], isrs [Isr], build {...}|None, builds_note}
  Task       {name, lane (init|loop|called|thread), period_ms (q|None), wcet_us (q), known_us (float, the bounded part), unbounded [reasons],
              blocking [{atom, kind, what, worst_us (q)}], text_bytes, stack_bytes, peripherals [ids], serves [purposes], atom}
  Isr        {name, vector, cycles_ub, per_event_us (q), rate_hz (q), text_bytes, stack_bytes}
`q` = {kind: measured|estimated|cited|criterion|undetermined, value, unit, basis}.
"""
import json
import os
import re

from cmod.custom import approach_profile_atoms as A
from cmod.custom.approach_profile_atoms import q, undetermined

MODULES = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
IMPORTANCE = ('safety', 'required', 'important', 'desired')
# peripheral ids that every firmware uses (no driver of their own): they do not count toward the "many drivers" test
BASIC = re.compile(r'^(GPIO PORT.*|TIMER\d*|EXINT|PCINT|SREG.*|.*_PIN|AC)$')


def _j(s, default):
    try:
        v = json.loads(s) if isinstance(s, str) and s else s
        return default if v in (None, '') else v
    except ValueError:
        return default


def find_mission(mission, manager=None):
    """-> dict of the HardwareMission (a live row, else the seed), or None. A dict handed in is used as given (a synthetic Mission)."""
    from cmod.custom import mission_derived as MD
    from cmod.custom import mission_seeds as MS
    if isinstance(mission, dict):
        return dict(mission)
    rows = ((getattr(manager, 'objectTables', None) or {}).get('HardwareMission') or {}).values() if manager is not None else []
    hit = next((r for r in rows if getattr(r, 'name', '') == mission), None)
    if hit is not None:
        return MD.mission_dict(hit)
    seed = next((m for m in MS.MISSION_SEEDS if m['name'] == mission), None)
    return dict(seed) if seed else None


def _board_runtime(board):
    from board.custom import board_object as BO
    return next((r for r in BO.seed_tables()['RuntimeProfile'] if r['board'] == board and r['runtime'] == 'bare-c'), None)


def _graph_dir(graph):
    return os.path.join(MODULES, 'cmod', 'custom', 'graphs', graph)


def _read(path):
    try:
        return open(path, encoding='utf-8').read()
    except OSError:
        return ''


def _define(text, name):
    m = re.search(r'#define\s+%s\s+\(?\s*(\d+)\s*[uU]?\b' % re.escape(name), text)
    return int(m.group(1)) if m else None


def frame_bytes(graph):
    """(bytes, basis) - the largest frame the graph's generated packets header allows: header + class payload maximum + CRC, or (None, why)."""
    d = _graph_dir(graph)
    if not os.path.isdir(d):
        return None, 'no generated project for %s' % graph
    for f in sorted(os.listdir(d)):
        if f.endswith('_packets.h'):
            t = _read(os.path.join(d, f))
            hdr = _define(t, 'POLARI_HEADER_LEN')
            pm = re.search(r'#define\s+\w+_PAYLOAD_MAX\s+(\d+)', t)
            if hdr and pm:
                return hdr + int(pm.group(1)) + 4, '%s: POLARI_HEADER_LEN %d + payload maximum %s + 4 (CRC)' % (f, hdr, pm.group(1))
    return None, 'no *_packets.h with a header length and a payload maximum in %s' % graph


def period_of(params, graph):
    """period_ms=<macro> from a tick node -> q (macro resolved from the graph's board_config.h: <STEM>_MS from <STEM>_HZ, or the macro itself)."""
    m = re.search(r'period_ms=([A-Za-z_0-9]+)', params or '')
    if not m:
        return undetermined('the tick node names no period')
    macro = m.group(1)
    if macro.isdigit():
        return q('criterion', int(macro), 'ms', 'the tick node\'s own period_ms')
    cfg = _read(os.path.join(_graph_dir(graph), 'board_config.h'))
    hz = _define(cfg, re.sub(r'_MS$', '_HZ', macro)) if macro.endswith('_MS') else None
    if hz:
        return q('estimated', 1000.0 / hz, 'ms', '%s = 1000 / %s_HZ (%d Hz) read from %s/board_config.h; the schedule fires on the 1 ms tick, so this is the intended period, not a measured one' % (
            macro, re.sub(r'_MS$', '', macro), hz, graph))
    direct = _define(cfg, macro)
    if direct:
        return q('estimated', direct, 'ms', '%s read from %s/board_config.h' % (macro, graph))
    return undetermined('the period macro %s is not defined in %s/board_config.h' % (macro, graph))


def purposes_of(mission_row, manager=None):
    """[Purpose dict] for every Purpose a Mission names (importance from the Mission, trigger and criteria from the Purpose)."""
    from cmod.custom import mission_derived as MD
    out = []
    for p in _j(mission_row.get('purposes_json'), []):
        name = str(p.get('purpose', ''))
        cap = MD.capability(name, manager)
        imp = str(p.get('importance') or 'required')
        if cap is None:
            out.append({'purpose': name, 'importance': imp, 'title': name, 'trigger': {'kind': '', 'what': ''}, 'deadline_ms': None, 'deadline_key': '',
                        'debounce_ms': None, 'period_ms': None, 'tasks': [], 'graph': '', 'missing': True})
            continue
        spec = _j(cap.get('criteria_json'), {})
        crit = {c['key']: c for c in spec.get('criteria', []) if isinstance(c, dict) and 'key' in c}
        dl = [(c['value'], k) for k, c in crit.items() if k in ('max_latency_ms', 'freshness_ms', 'deadline_ms') and isinstance(c.get('value'), (int, float))]
        dv = min(dl) if dl else None
        tasks = [t.partition(':') for t in _j(cap.get('tasks_by_runtime_json'), {}).get('c-device', [])]
        out.append({'purpose': name, 'importance': imp, 'title': cap.get('title') or name, 'trigger': spec.get('trigger') or {'kind': '', 'what': ''},
                    'deadline_ms': q('criterion', dv[0], 'ms', 'Purpose %s criterion %s' % (name, dv[1])) if dv else None, 'deadline_key': dv[1] if dv else '',
                    'debounce_ms': q('criterion', crit['debounce_ms']['value'], 'ms', 'Purpose %s criterion debounce_ms' % name) if 'debounce_ms' in crit else None,
                    'period_ms': None, 'tasks': [t[2] for t in tasks], 'graph': tasks[0][0] if tasks else ''})
    return out


def processor(graph, purposes, manager=None):
    """One Processor (a graph = the firmware of one chip) with its tasks and ISRs analysed."""
    from cmod.custom import firmware as FW
    from cmod.custom import code_interface as CI
    from cmod.custom.graph_seed import seed_graph
    g = seed_graph(graph)
    nodes = {n['instance']: n for n in g['nodes']}
    slots = {s['task']: s for s in FW.schedule_for(graph)}
    from cmod.custom.rows import graph_rows
    graph_row = next((r for r in graph_rows()['CGraph'] if r['name'] == graph), {})
    board = graph_row.get('board') or ''
    rt = _board_runtime(board) or {}
    per = _j(rt.get('peripherals_json'), [])
    usart = next((p for p in per if p.get('name') == 'USART0'), {})
    mb = re.search(r'(\d{4,7}) Bd', usart.get('use', ''))
    baud = int(mb.group(1)) if mb else None
    fb, fbasis = frame_bytes(graph)
    ctx = {'baud': baud, 'frame_bytes': fb}
    clock = int(rt.get('clock_hz') or 0) or None
    periods = {}
    for e in g['edges']:
        if e['kind'] == 'tick' and nodes.get(e['from_node'], {}).get('kind') == 'tick':
            periods[e['to_node']] = period_of(nodes[e['from_node']].get('params', ''), graph)
    serves = {}
    for p in purposes:
        for t in p['tasks']:
            serves.setdefault(t, []).append(p['purpose'])
    tasks = []
    for inst, n in sorted(nodes.items(), key=lambda kv: kv[1].get('order', 0)):
        if n.get('kind') != 'c-atom' or not n.get('atom'):
            continue
        slot = slots.get(inst, {})
        lane = slot.get('lane') or n.get('stage') or 'loop'
        project, _m, atom = CI.find_atom(n['atom'])
        an = A.analyse(project, atom, ctx)
        known = A.cycles_to_us(an['cycles_ub'], clock) if clock else None
        if not an['bounded'] or known is None:
            wcet = undetermined('; '.join(an['unbounded']) or 'no CPU clock for the board')
        else:
            wcet = q('estimated', round(known, 2), 'us', 'upper bound: %d B / 2 B per instruction x 4 cycles = %d cycles at %d Hz (no loop, no call outside the atoms); not a measured cycle count' % (
                an['text_bytes'], an['cycles_ub'], clock))
        tasks.append({'name': inst, 'lane': lane, 'period_ms': periods.get(inst), 'wcet_us': wcet, 'known_us': known or 0.0, 'unbounded': an['unbounded'],
                      'blocking': an['blocking'], 'text_bytes': an['text_bytes'], 'stack_bytes': an['stack_bytes'], 'peripherals': an['peripherals'],
                      'serves': serves.get(inst, []), 'atom': n['atom']})
    isrs = []
    for s in sorted((s for s in slots.values() if s['lane'] == 'isr'), key=lambda s: s['order']):
        project, _m, atom = CI.find_atom('%s:%s' % (graph_row.get('project', 'uno'), s['task']))
        an = A.analyse(project, atom, ctx)
        us = A.cycles_to_us(an['cycles_ub'], clock) if clock else None
        isrs.append({'name': s['task'], 'vector': s['isr_vector'], 'cycles_ub': an['cycles_ub'], 'text_bytes': an['text_bytes'], 'stack_bytes': an['stack_bytes'],
                     'per_event_us': q('estimated', round(us, 2), 'us', 'upper bound: %d B / 2 x 4 cycles at %d Hz' % (an['text_bytes'], clock)) if us is not None else undetermined('no clock'),
                     'rate_hz': _isr_rate(s['isr_vector'], per, baud)})
    build = _build(graph)
    return {'name': graph, 'board': board, 'clock_hz': clock, 'baud': baud, 'frame_bytes': fb, 'frame_basis': fbasis, 'tasks': tasks, 'isrs': isrs, 'build': build,
            'runtime_row': rt.get('name', '')}


def _isr_rate(vector, per, baud):
    if vector.startswith('TIMER') and vector.endswith('COMPA_vect'):
        tick = next((p for p in per if 'ms tick' in p.get('use', '')), None)
        m = re.search(r'the (\d+) ms tick', (tick or {}).get('use', ''))
        if m:
            return q('cited', 1000.0 / int(m.group(1)), 'Hz', 'the board\'s bare-c RuntimeProfile row: %s = %s' % (tick['name'], tick['use']))
    if vector.startswith('USART') and vector.endswith('RX_vect') and baud:
        return q('estimated', baud / 10.0, 'Hz', 'at most one byte per 10 bit times at %d Bd (a full-rate receive; the real rate is the commands sent, far lower)' % baud)
    return undetermined('%s fires when the outside world does; its rate is not a property of the board (it is left out of the CPU share, said)' % vector)


def _build(graph):
    from cmod.custom import glue
    path = os.path.join(glue.RECORDS, graph + '.json')
    try:
        rec = json.load(open(path))
    except (OSError, ValueError):
        return None
    b = rec.get('build') or {}
    if not b.get('ok'):
        return None
    return {'size_text': b.get('size_text'), 'size_data': b.get('size_data'), 'size_bss': b.get('size_bss'), 'flash_bytes': b.get('flash_bytes'),
            'built_by': b.get('built_by', ''), 'hex_sha256': b.get('hex_sha256', ''), 'built_at': b.get('built_at', ''),
            'basis': 'cmod/custom/glue_builds/%s.json build (%s, hex %s, %s)' % (graph, b.get('built_by', ''), (b.get('hex_sha256') or '')[:12], b.get('built_at', ''))}


def from_mission(mission, manager=None):
    """The spec of a real Mission (a name, or a dict shaped like a HardwareMission row). Raises ValueError for an unknown Mission."""
    row = find_mission(mission, manager)
    if row is None:
        raise ValueError('no HardwareMission %r (GET /api/missions lists them)' % mission)
    purposes = purposes_of(row, manager)
    parts = _j(row.get('participants_json'), [])
    board = next((p.get('ref') for p in parts if p.get('role') == 'board'), '')
    graphs = []
    for p in purposes:
        if p['graph'] and p['graph'] not in graphs:
            graphs.append(p['graph'])
    procs = [processor(g, [p for p in purposes if p['graph'] == g], manager) for g in graphs]
    for p in purposes:      # a periodic Purpose's period = the period of the tick-fed task it names
        if str((p['trigger'] or {}).get('kind')) == 'period':
            pr = next((t['period_ms'] for pc in procs for t in pc['tasks'] if t['name'] in p['tasks'] and t.get('period_ms') and t['period_ms'].get('value')), None)
            p['period_ms'] = pr or undetermined('the Purpose is periodic but none of its tasks is fed by a tick node')
    return {'mission': row.get('name', ''), 'board_ref': board, 'source': 'HardwareMission %s and its Purposes' % row.get('name', ''), 'purposes': purposes,
            'processors': procs, 'notes': []}
