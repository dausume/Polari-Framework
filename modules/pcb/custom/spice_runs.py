"""
@module pcb.custom.spice_runs

kxc-3b (KICAD_INTERCHANGE_PLAN.md): SIMULATION RUNS KEPT AND CHARTED. A run of an ingested schematic's deck (pcb_sim_api's /simulate on a host with
libngspice, a worker's result posted back, or a recorded reference) becomes one SpiceRun row + one SpiceVector row per result vector - the values
exactly as the solver returned them. The chart reads them back in long form (x, y, series) for the named graph `pcb-spice-run`, thinned to at most
`max_rows` points per series (the stride is said).

  store(manager, board, deck, result, source, host, ran_at=None) -> run name (or None + why when the result is not a finished run)
  runs(manager, board)        one row per run, newest first
  vectors(manager, run)       one row per vector, without its values
  chart(manager, run, max_rows=2000) -> (status, {ok, rows: [{x, y, series}], x_vector, x_unit, stride, points})
  projection(manager, board, run=None, nets=None) -> (rows, why)   kxc-3c: a run's results on the board's nets (and the footholds on them)
With no manager (selftests) the rows live in this process only.
"""
import datetime
import hashlib
import json

SCALES = {'time': 's', 'frequency': 'Hz'}
_MEM = {'SpiceRun': {}, 'SpiceVector': {}}


def unit_of(name):
    n = name.lower()
    return SCALES.get(n) or ('A' if n.endswith('#branch') else 'V')


def _table(manager, cls):
    if manager is None:
        return list(_MEM[cls].values())
    t = (getattr(manager, 'objectTables', None) or {}).get(cls) or {}
    return [{k: v for k, v in vars(o).items() if not k.startswith('_')} if not isinstance(o, dict) else o for o in t.values()]


def _save(manager, cls, row):
    if manager is None:
        _MEM[cls][row['name']] = dict(row)
        return
    if cls == 'SpiceRun':
        from pcb.objects.pcb.SpiceRun import SpiceRun as C
    else:
        from pcb.objects.pcb.SpiceVector import SpiceVector as C
    obj = C(manager=manager, **row)
    try:
        manager.db.saveInstanceInDB(obj)
    except Exception:  # noqa: BLE001 - an in-memory manager has no db
        pass


def store(manager, board, deck, result, source='local', host='', ran_at=None):
    """Keep one run. A refusal is kept too (ok False, the reason in words, no vectors) so a person sees the attempt."""
    ran_at = ran_at or datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()
    sha = hashlib.sha256((deck or '').encode()).hexdigest()
    vecs = result.get('vectors') or {}
    ok = bool(result.get('ok')) and bool(vecs)
    name = '%s:%s:%s' % (board, sha[:12], ran_at)
    points = max((len(v.get('real') or v.get('mag') or []) for v in vecs.values()), default=0)
    _save(manager, 'SpiceRun', {'name': name, 'board': board, 'ran_at': ran_at, 'deck_sha256': sha, 'plot': result.get('plot', ''), 'points': points,
                                'engine': result.get('library', '') or result.get('engine', ''), 'source': source, 'host': host, 'ok': ok,
                                'refused': '' if ok else (result.get('refused') or '; '.join(result.get('errors') or []) or 'no vectors returned'),
                                'notes': result.get('note', '')})
    for vn, v in (vecs.items() if ok else []):
        vals = v.get('real') if 'real' in v else v.get('mag', [])
        _save(manager, 'SpiceVector', {'name': '%s:%s' % (name, vn), 'run': name, 'vector': vn, 'role': 'scale' if vn.lower() in SCALES else 'value',
                                       'unit': unit_of(vn), 'complex_values': 'mag' in v, 'points': len(vals), 'values_json': json.dumps(vals),
                                       'phase_json': json.dumps(v.get('phase_deg', [])), 'min_value': min(vals) if vals else 0.0,
                                       'max_value': max(vals) if vals else 0.0})
    return name


def runs(manager, board):
    rows = [r for r in _table(manager, 'SpiceRun') if r['board'] == board]
    n = {}
    for v in _table(manager, 'SpiceVector'):
        n[v['run']] = n.get(v['run'], 0) + 1
    return [dict(r, vectors=n.get(r['name'], 0), status='ran' if r['ok'] else 'REFUSED - %s' % r['refused'],
                 analysis={'tran': 'transient', 'ac': 'AC sweep', 'op': 'operating point', 'dc': 'DC sweep'}.get(r['plot'].rstrip('0123456789'), r['plot']))
            for r in sorted(rows, key=lambda r: r['ran_at'], reverse=True)]


def vectors(manager, run):
    return [{k: v for k, v in r.items() if k not in ('values_json', 'phase_json')} for r in _table(manager, 'SpiceVector') if r['run'] == run]


def chart(manager, run, max_rows=2000):
    vs = [r for r in _table(manager, 'SpiceVector') if r['run'] == run]
    if not vs:
        known = sorted(r['name'] for r in _table(manager, 'SpiceRun'))
        return 404, {'ok': False, 'error': 'no vectors for run %r (a refused run keeps none)' % run, 'known': known[-20:]}
    scale = next((r for r in vs if r['role'] == 'scale'), None)
    if scale is None:
        return 409, {'ok': False, 'error': 'run %r has no scale vector (time / frequency) to chart against' % run}
    xs = json.loads(scale['values_json'])
    stride = max(1, -(-len(xs) // int(max_rows)))
    rows = []
    for r in sorted((v for v in vs if v['role'] == 'value'), key=lambda v: v['vector']):
        ys = json.loads(r['values_json'])
        label = '%s (%s%s)' % (r['vector'], '|' if r['complex_values'] else '', r['unit'] + ('|' if r['complex_values'] else ''))
        rows += [{'x': xs[i], 'y': ys[i], 'series': label} for i in range(0, min(len(xs), len(ys)), stride)]
    return 200, {'ok': True, 'run': run, 'rows': rows, 'x_vector': scale['vector'], 'x_unit': scale['unit'], 'stride': stride, 'points': len(xs)}


def _latest_ok(manager, board):
    return next((r for r in runs(manager, board) if r['ok']), None)


def projection(manager, board, run=None, nets=None):
    """kxc-3c: one run's results PROJECTED onto the board's nets - each net's node vector (the deck's node name, pcb.custom.kicad_spice.node_name, as
    ngspice names it: lower case), summarised. Transient: min / max / final volts. AC: the largest |V| and the frequency it occurs at, and |V| at the
    lowest frequency. GND is SPICE node 0: 0 V by definition. A net with no vector says why. `run` = a run name, else the newest finished run of the
    board; `nets` = the net names (else the board's SchematicNet rows). -> (rows, why)"""
    from pcb.custom import kicad_spice as P
    if run and not board:
        board = next((x['board'] for x in _table(manager, 'SpiceRun') if x['name'] == run), '')
    r = next((x for x in runs(manager, board) if x['name'] == run), None) if run else _latest_ok(manager, board)
    if r is None:
        return [], ('no run %r for %s' % (run, board)) if run else 'no finished run kept for %s - simulate it first' % board
    vs = {v['vector'].lower(): v for v in _table(manager, 'SpiceVector') if v['run'] == r['name']}
    scale = next((v for v in vs.values() if v['role'] == 'scale'), None)
    xs = json.loads(scale['values_json']) if scale else []
    if nets is None:
        nets = sorted({getattr(n, 'net', '') if not isinstance(n, dict) else n.get('net', '') for n in
                       ((getattr(manager, 'objectTables', None) or {}).get('SchematicNet') or {}).values()
                       if (getattr(n, 'board', '') if not isinstance(n, dict) else n.get('board')) == board} - {''})
        if not nets:   # no schematic nets stored for this board: the run's own nodes, by their vector names
            nets = sorted(v['vector'] for v in vs.values() if v['role'] == 'value' and not v['vector'].endswith('#branch'))
    out = []
    for net in nets:
        node = P.node_name(net)
        base = {'net': net, 'node': node, 'run': r['name'], 'analysis': r['analysis'], 'unit': 'V', 'min': -1.0, 'max': -1.0, 'final': -1.0,
                'at': '', 'basis': ''}
        if node == 'GND':
            out.append(dict(base, min=0.0, max=0.0, final=0.0, basis='SPICE ground (node 0): 0 V by definition'))
            continue
        v = vs.get(node.lower())
        if v is None:
            out.append(dict(base, basis='no vector %r in run %s (the deck did not save this node)' % (node.lower(), r['name'])))
            continue
        ys = json.loads(v['values_json'])
        if v['complex_values']:
            i = max(range(len(ys)), key=lambda k: ys[k]) if ys else 0
            out.append(dict(base, unit='|V|', min=min(ys), max=ys[i] if ys else -1.0, final=ys[0] if ys else -1.0,
                            at='%g Hz' % xs[i] if i < len(xs) else '', basis='AC magnitude of vector %s: max at %s; final = |V| at the lowest frequency'
                            % (v['vector'], '%g Hz' % xs[i] if i < len(xs) else '?')))
        else:
            out.append(dict(base, min=min(ys), max=max(ys), final=ys[-1], at='%s %s' % (xs[-1], scale['unit']) if xs and scale else '',
                            basis='transient vector %s over %d points (%s): min / max / the last point' % (v['vector'], len(ys), r['plot'])))
    feet = {}
    for f in ((getattr(manager, 'objectTables', None) or {}).get('BoardFoothold') or {}).values():
        if getattr(f, 'definition_kind', '') == 'layers' and getattr(f, 'definition', '') == board and getattr(f, 'net', ''):
            feet.setdefault(f.net, []).append(f.foothold)
    for row in out:
        row['footholds'] = ', '.join(sorted(feet.get(row['net'], [])))
    return out, ''
