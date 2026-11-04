"""
@module cmod.custom.run_diff

bss-14 (AI-Notes/plans/BENCH_SOLUTION_SIM_PLAN.md; the vital list's debug aid): WHAT CHANGED BETWEEN TWO RUNS OF A NODE - derived on read from the kept
assessment rows (StructNodeRun / RunEdge / RunSignal), never stored. The other run defaults to the PREVIOUS run of the same node, so after a rebuild the
question "what is different now?" is one door. Rows are small and in words: each names what it compares, the two values and the delta where one exists.

    diff(manager, run, other='')   -> {'run', 'other', 'rows': [{what, a, b, delta, changed}], 'changed': n, 'words'}
"""
from cmod.custom import config_rows as R


def _prev(manager, run):
    row = R.get(manager, 'StructNodeRun', run)
    if row is None:
        raise R.ConfigRefused('no run %r' % run, status=404)
    runs = sorted((r['name'] for r in R.rows(manager, 'StructNodeRun', node=row['node'])), key=lambda n: (len(n), n))
    i = runs.index(run)
    return runs[i - 1] if i > 0 else ''


def _row(what, a, b, delta=''):
    return {'what': what, 'a': '' if a is None else str(a), 'b': '' if b is None else str(b), 'delta': delta, 'changed': str(a) != str(b)}


def _kinds(words):
    """'pin-level PD6: ... ; net-current PD6: ... ; electrical circuit: ...' -> {'pin-level PD6': '...', ...}"""
    out = {}
    for part in (words or '').split(' ; '):
        if ': ' in part:
            k, v = part.split(': ', 1)
            out[k.strip()] = v.strip()
    return out


def diff(manager, run, other=''):
    a = R.get(manager, 'StructNodeRun', run)
    if a is None:
        raise R.ConfigRefused('no run %r' % run, status=404)
    other = other or _prev(manager, run)
    if not other:
        return {'ok': True, 'run': run, 'other': '', 'rows': [], 'changed': 0, 'words': '%s is the first run of %s: nothing to compare with' % (run, a['node'])}
    b = R.get(manager, 'StructNodeRun', other)
    if b is None:
        raise R.ConfigRefused('no run %r to compare with' % other, status=404)
    rows = []
    for k in ('outcome', 'path', 'hex_sha256', 'engine', 'profile', 'play_from', 'step_set_by'):
        rows.append(_row('run %s' % k, a.get(k), b.get(k), 'another build' if k == 'hex_sha256' and a.get(k) != b.get(k) else ''))
    da, db = float(a.get('duration_s') or -1), float(b.get('duration_s') or -1)
    rows.append(_row('run duration_s', '%.6f' % da, '%.6f' % db, ('%+.6f s' % (da - db)) if da >= 0 and db >= 0 else ''))
    ea = {e['order']: e for e in R.rows(manager, 'StructNodeRunEdge', run=run)}
    eb = {e['order']: e for e in R.rows(manager, 'StructNodeRunEdge', run=other)}
    for order in sorted(set(ea) | set(eb)):
        x, y = ea.get(order) or {}, eb.get(order) or {}
        label = 'edge %d %s' % (order, (x.get('edge') or y.get('edge') or '').split('->')[-1])
        rows.append(_row(label + ' outcome', x.get('outcome'), y.get('outcome')))
        mx, my = int(x.get('met_cycle', -1) or -1), int(y.get('met_cycle', -1) or -1)
        rows.append(_row(label + ' met_cycle', mx, my, ('%+d cycles' % (mx - my)) if mx >= 0 and my >= 0 else ''))
        ka, kb = _kinds(x.get('collaterals')), _kinds(y.get('collaterals'))
        for k in sorted(set(ka) | set(kb)):
            va, vb = ka.get(k, ''), kb.get(k, '')
            if va != vb:
                rows.append(_row(label + ' ' + k, va[:160], vb[:160], 'changed'))
        if (x.get('executions') or '') != (y.get('executions') or ''):
            rows.append(_row(label + ' executions', (x.get('executions') or '')[:160], (y.get('executions') or '')[:160], 'changed'))
    sa = {(s['kind'], s['signal']): s for s in R.rows(manager, 'StructNodeRunSignal', run=run)}
    sb = {(s['kind'], s['signal']): s for s in R.rows(manager, 'StructNodeRunSignal', run=other)}
    for key in sorted(set(sa) | set(sb)):
        x, y = sa.get(key) or {}, sb.get(key) or {}
        label = '%s %s' % key
        for k in ('first', 'last', 'changes'):
            rows.append(_row('%s %s' % (label, k), x.get(k), y.get(k)))
        cx, cy = int(x.get('first_change_cycle', -1) or -1), int(y.get('first_change_cycle', -1) or -1)
        rows.append(_row(label + ' first_change_cycle', cx, cy, ('%+d cycles' % (cx - cy)) if cx >= 0 and cy >= 0 else ''))
    changed = [r for r in rows if r['changed']]
    return {'ok': True, 'run': run, 'other': other, 'rows': rows, 'changed': len(changed),
            'words': '%s vs %s: %d of %d compared values differ%s' % (run, other, len(changed), len(rows), (' - ' + '; '.join(r['what'] for r in changed[:8])) if changed else '')}
