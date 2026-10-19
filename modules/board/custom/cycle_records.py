"""
@module board.custom.cycle_records

cyc-0: the COMMITTED cycle records (`cycle_records/<variant>.json`, written by board.custom.cycle_measure) and the lookups the cost basis uses. A record is
the CycleMeasurement of one variant: per-atom cycles per call (the -fno-inline build), per-interrupt cycles, the main-loop gaps, and the inputs by sha256
(shipped / -fno-inline hex, sources, stimulus, tool versions) - see cycle_measure's docstring. The repo ignores *.json, so these are `git add -f`.

    cycles_of(atom_name, variant=None) -> {variant, n, min, max, ref} | None     atom_name is the manifest's own name ('apps/light.apply_command')
    isr_of(isr_name, variant)          -> {n, min, max, mean, ref} | None         isr_name 'hal.INT0_vect' (its vector name 'INT0_vect' is looked up)
    ref(rec)                           -> 'cycle record uno-light 3f2a... (hex 7c1d...)' - the run reference carried by a cost field
GRAPH_VARIANT maps a graph project (the generated glue firmware) to the variant whose atoms it calls: the graph is the SAME atoms, so the variant's
measured numbers are the graph's.
"""
import json
import os

DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cycle_records')
GRAPH_VARIANT = {'uno-light-graph': 'uno-light-unsensed',     # smp-1: the graph is the light app WITHOUT the sense line = the variant uno-light-unsensed (uno-light itself now carries the sense line)
                  'uno-button-clock-graph': 'uno-button-clock'}
_CACHE = {}


def path(variant):
    return os.path.join(DIR, variant + '.json')


def load(variant):
    if variant in _CACHE:
        return _CACHE[variant]
    try:
        rec = json.load(open(path(variant)))
    except (OSError, ValueError):
        rec = None
    _CACHE[variant] = rec
    return rec


def save(rec):
    os.makedirs(DIR, exist_ok=True)
    p = path(rec['variant'])
    with open(p, 'w') as f:
        json.dump(rec, f, indent=1, sort_keys=True)
        f.write('\n')
    _CACHE.pop(rec['variant'], None)
    return p


def variants():
    try:
        return sorted(f[:-5] for f in os.listdir(DIR) if f.endswith('.json'))
    except OSError:
        return []


def ref(rec):
    return 'cycle record %s %s (shipped hex %s, stimulus %s)' % (rec['variant'], rec['record_sha256'][:12], rec['inputs']['shipped_hex_sha256'][:12], rec['stimulus']['name'])


def cycles_of(atom_name, variant=None):
    """The measured cycles of one atom in `variant` (None = the variant that measured it with the largest max). n == 0 means 'measured, never reached' -> None."""
    best = None
    for v in ([variant] if variant else variants()):
        rec = load(v)
        f = ((rec or {}).get('functions') or {}).get(atom_name)
        if f and f.get('n'):
            if best is None or f['max'] > best['max']:
                best = {'variant': v, 'n': f['n'], 'min': f['min'], 'max': f['max'], 'ref': ref(rec), 'frame_bytes_max': rec['stimulus'].get('frame_bytes_max'),
                        'cpu_max': f.get('cpu_cycles_max'), 'cpu_basis': f.get('cpu_basis', ''), 'blocks_on_uart': bool(f.get('blocks_on_uart')),
                        'caveat': f.get('twin_caveat', ''), 'stimulus': rec['stimulus']['describe'], 'hex_sha256': rec['inputs']['noinline_hex_sha256']}
    return best


def isr_of(isr_name, variant=None):
    vec = isr_name.split('.', 1)[-1]
    best = None
    for v in ([variant] if variant else variants()):
        rec = load(v)
        f = ((rec or {}).get('isrs') or {}).get(vec)
        if f and f.get('n'):
            if best is None or f['max'] > best['max']:
                best = dict(f, variant=v, ref=ref(rec), stimulus=rec['stimulus']['describe'], hex_sha256=rec['inputs']['shipped_hex_sha256'])
    return best


def loop_of(variant):
    rec = load(variant)
    lp = (rec or {}).get('loop') or {}
    if not rec or not lp.get('worst_gap_cycles'):
        return None
    return dict(lp, variant=variant, ref=ref(rec), frame_bytes_max=rec['stimulus'].get('frame_bytes_max'))


def annotate(project, atom):
    """Give a manifest atom's cost a `cycles` entry (kind measured, with the run reference) when a record measured it - read-only, nothing stored in the
    manifest. {'kind', 'value' (the worst max over the variants), 'unit', 'basis', 'ref', 'by_variant': {variant: {n, min, max, cpu_max}}}."""
    if project != 'uno' or not isinstance(atom.get('cost'), dict):
        return atom
    by = {}
    isr = atom.get('kind') == 'isr'
    for v in variants():
        rec = load(v)
        f = ((rec or {}).get('isrs') or {}).get(atom.get('isr_vector')) if isr else ((rec or {}).get('functions') or {}).get(atom['name'])
        if f and f.get('n') and v in atom.get('configs', ()):
            by[v] = {'n': f['n'], 'min': f['min'], 'max': f['max'], 'cpu_max': f.get('cpu_cycles_max'), 'ref': ref(rec)}
    if by:
        worst = max(by.values(), key=lambda d: d['max'])
        wv = next(v for v, d in by.items() if d is worst)
        atom['cost']['cycles'] = {'kind': 'measured', 'value': worst['max'], 'unit': 'cycles', 'by_variant': by,
                                  'basis': ('worst max cycles per %s on the simavr twin (%s in %s); %s' % ('event' if isr else 'call (as a node, -fno-inline)', 'n=%d' % worst['n'], wv, worst['ref'])),
                                  'ref': worst['ref']}
    return atom
