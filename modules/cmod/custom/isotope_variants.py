"""
@module cmod.custom.isotope_variants

The isotope variant catalogue worked out (iso-0, MISSION_PROFILE_SOLVER_PLAN.md section 8): the declared rows (`isotope_variants_seeds`) joined to
what EXISTS - the atoms of the committed firmware manifests (their measured sizes), the builds those atoms are in, the KitPart rows (the bench),
the Purposes' proofs. Nothing derived is stored on a row. Pure Python, no engine; a manager is only needed to read live proofs (ScenarioRun).

status    declared -> template-exists -> compiles -> proven-on-twin -> proven-on-hardware, read off what exists:
          template-exists  every atom named in `implemented_by` is an atom of a committed manifest
          compiles         ... and the named configuration builds with make alone and every atom is in its measured shipped build
          proven-on-*      ... and a Purpose whose graph holds one of those atoms has a passing ScenarioRun (capabilities.derive_status);
                           with no live manager there is no run to read, so the status stops at `compiles` and says why
costs     measured (from the atoms' own measured sizes), estimated (stored, with basis) or undetermined - never a bare number
eligible  isotope_variants_eligibility.eligible(variant, ctx) -> ok | blocked (reason by name) | undetermined

    python3 -m cmod.custom.isotope_variants jobs [--json]
    python3 -m cmod.custom.isotope_variants variants <job> [--board B] [--tier T] [--json]
"""
import inspect
import json
import re

from cmod.custom import isotope_variants_seeds as S

PROOF_ORDER = ('declared', 'template-exists', 'compiles', 'proven-on-twin', 'proven-on-hardware')
COST_KEYS = ('pins', 'peripherals', 'parts', 'flash_bytes', 'ram_bytes', 'cpu_share', 'latency')
_CACHE = {}


def _j(s, default):
    try:
        v = json.loads(s) if isinstance(s, str) else s
        return default if v is None else v
    except Exception:  # noqa: BLE001
        return default


def row_dict(row, cls):
    """A row (or a seed dict) as a plain dict of its constructor fields."""
    if isinstance(row, dict):
        return {k: v for k, v in row.items() if k != '_converge'}
    keys = [k for k in inspect.signature(cls.__init__).parameters if k not in ('self', 'manager')]
    return {k: getattr(row, k, None) for k in keys}


def _live(manager, cls_name):
    return list(((getattr(manager, 'objectTables', None) or {}).get(cls_name, {}) or {}).values()) if manager is not None else []


def jobs(manager=None):
    from cmod.objects.cmod.AtomJob import AtomJob
    live = _live(manager, 'AtomJob')
    order = {j['name']: i for i, j in enumerate(S.JOB_SEEDS)}
    return sorted((row_dict(r, AtomJob) for r in live), key=lambda r: order.get(r['name'], 999)) if live else [dict(j) for j in S.JOB_SEEDS]


def variants(manager=None, job=None):
    from cmod.objects.cmod.IsotopeVariant import IsotopeVariant
    live = _live(manager, 'IsotopeVariant')
    rows = [row_dict(r, IsotopeVariant) for r in live] if live else [dict(v) for v in S.VARIANT_SEEDS]
    order = {v['name']: i for i, v in enumerate(S.VARIANT_SEEDS)}   # the plan's own order (section 8.3), not alphabetical
    return sorted((v for v in rows if job in (None, v['job'])), key=lambda v: order.get(v['name'], 999))


# ------------------------------------------------------------------ the atoms that exist (committed manifests: pure, no engine)
def atoms():
    """{'<project>:<atom>': (atom dict, manifest dict)} over every committed template project."""
    if 'atoms' not in _CACHE:
        from cmod.custom import code_interface as CI
        _CACHE['atoms'] = {'%s:%s' % (p, a['name']): (a, m) for p, m, a in CI._manifest_candidates()}
    return _CACHE['atoms']


def _bytes_of(detail):
    m = re.search(r'(\d+) B', detail or '')
    return int(m.group(1)) if m else None


def job_atoms(job):
    """The atoms of a job: the ones the seed lists, plus the atoms that declare the job's pin macro with uses() - DERIVED from the manifests - each
    checked to exist. -> {'atoms': [names], 'missing': [names], 'derived': [names found only by the macro]}"""
    listed = list(_j(job.get('atoms_json'), []))
    macro = job.get('uses_macro') or ''
    derived = []
    if macro:
        for name, (a, _m) in sorted(atoms().items()):
            if any(r.get('kind') == 'declared' and r.get('name') == macro for r in a.get('resources', [])) and name not in listed:
                derived.append(name)
    have = atoms()
    return {'atoms': [n for n in listed + derived if n in have], 'missing': [n for n in listed if n not in have], 'derived': derived}


# ------------------------------------------------------------------ the bench (KitPart rows)
def kit_rows():
    if 'kit' not in _CACHE:
        from board.custom import kit_parts as K
        _CACHE['kit'] = K.rows()
    return _CACHE['kit']


def part_on_bench(part, kit=None):
    """-> {on_bench: True|False|'undetermined', why, kit_part}. True when a KitPart row named by `kit_keys` exists (and, when a `spec` is asked
    for, the row's variants list holds it); False when no row names the class and no KitPart row's words mention it; 'undetermined' when a row
    mentions it but nothing settles it, or a spec cannot be read."""
    kit = kit if kit is not None else kit_rows()
    by = {r['name'].split(':', 1)[-1]: r for r in kit}
    spec = part.get('spec') or {}
    hits = [by[k] for k in part.get('kit_keys', []) if k in by]
    if hits:
        if not spec:
            return {'on_bench': True, 'why': 'in the kit: %s (quantity %s)' % (hits[0]['title'], hits[0]['kit_quantity']), 'kit_part': hits[0]['name']}
        for h in hits:
            vs = _j(h.get('variants_json'), [])
            if any(all(v.get(k) == val for k, val in spec.items()) for v in vs):
                return {'on_bench': True, 'why': 'in the kit: %s, the %s variant (quantity %s)' % (h['title'], ', '.join('%s=%s' % kv for kv in spec.items()), next(v.get('quantity') for v in vs if all(v.get(k) == val for k, val in spec.items()))), 'kit_part': h['name']}
        if any(_j(h.get('variants_json'), []) for h in hits):
            return {'on_bench': False, 'why': 'the kit has %s but no %s variant' % (hits[0]['title'], ', '.join('%s=%s' % kv for kv in spec.items())), 'kit_part': hits[0]['name']}
        return {'on_bench': 'undetermined', 'why': 'the kit has %s but its variants are not listed, so %s cannot be confirmed' % (hits[0]['title'], ', '.join('%s=%s' % kv for kv in spec.items())), 'kit_part': hits[0]['name']}
    terms = [t.lower() for t in part.get('terms', [])]
    text = lambda r: ' '.join(str(r.get(k, '')) for k in ('name', 'title', 'what_it_is', 'interface_kind', 'connects_to', 'driver_needed')).lower()   # noqa: E731
    mention = [r for r in kit if terms and any(t in text(r) for t in terms)]
    if mention:
        return {'on_bench': 'undetermined', 'why': 'KitPart %s mentions it but is not that part' % mention[0]['name'], 'kit_part': mention[0]['name']}
    return {'on_bench': False, 'why': 'not on the bench: none of the %d KitPart rows is a %s' % (len(kit), part['class']), 'kit_part': ''}


def parts_of(variant, kit=None):
    return [dict(p, **part_on_bench(p, kit)) for p in _j(variant.get('parts_json'), [])]


# ------------------------------------------------------------------ the implementation (what exists)
def _implementation(variant):
    """-> {atoms: [(name, atom, manifest)], missing, config, config_ok, shares_c_with, proof_purposes}; empty `atoms` = no implementation"""
    imp = _j(variant.get('implemented_by_json'), {})
    have = atoms()
    found = [(n, have[n][0], have[n][1]) for n in imp.get('atoms', []) if n in have]
    config = imp.get('config', '')
    config_ok = None
    if found and config:
        cfg = next((c for c in found[0][2].get('configurations', []) if c['name'] == config), None)
        config_ok = bool(cfg and (cfg.get('make_alone') or {}).get('ok'))
    return {'atoms': found, 'missing': [n for n in imp.get('atoms', []) if n not in have], 'config': config, 'config_ok': config_ok,
            'in_config': [n for n, a, _m in found if config and config in a.get('configs', [])],
            'shares_c_with': imp.get('shares_c_with', ''), 'shares_note': imp.get('shares_note', ''), 'proof_purposes': imp.get('proof_purposes', [])}


def _graph_atoms(graph):
    if 'graphs' not in _CACHE:
        from cmod.custom.rows import graph_rows
        g = {}
        for n in graph_rows()['CGraphNode']:
            if n.get('kind') == 'c-atom' and n.get('atom'):
                g.setdefault(n['graph'], set()).add(n['atom'])
        _CACHE['graphs'] = g
    return _CACHE['graphs'].get(graph, set())


def status(variant, manager=None):
    """-> {status, why, proof, proof_purposes_used}: DERIVED from the atoms, their builds and (with a manager) the Purposes' ScenarioRuns."""
    imp = _implementation(variant)
    if imp['missing']:
        return {'status': 'declared', 'why': 'implemented_by names atoms that no committed manifest holds: %s' % ', '.join(imp['missing']), 'proof': '', 'proof_purposes_used': []}
    if not imp['atoms']:
        why = 'no atom, template or build implements this route'
        if imp['shares_c_with']:
            why += ' (its C would be that of %s: %s)' % (imp['shares_c_with'], imp['shares_note'])
        return {'status': 'declared', 'why': why, 'proof': '', 'proof_purposes_used': []}
    st, why = 'template-exists', 'every named atom is in a committed manifest (%s)' % ', '.join(n for n, _a, _m in imp['atoms'])
    shipped = all(a.get('cost', {}).get('in_shipped_build') and a.get('cost', {}).get('text_bytes', 0) is not None for _n, a, _m in imp['atoms'])
    if imp['config_ok'] and shipped and len(imp['in_config']) == len(imp['atoms']):
        measured_in = sorted({a['cost'].get('measured_in', '') for _n, a, _m in imp['atoms']})
        st, why = 'compiles', 'all %d atoms are in the shipped build of %s, which builds with make alone; sizes measured in %s' % (len(imp['atoms']), imp['config'], ', '.join(measured_in))
    if st != 'compiles':
        return {'status': st, 'why': why, 'proof': '', 'proof_purposes_used': []}
    if manager is None:
        return {'status': st, 'why': why + '; no live instance to read ScenarioRuns from, so no proof is read', 'proof': '', 'proof_purposes_used': []}
    from cmod.custom import capabilities as CAP
    atom_names = {n for n, _a, _m in imp['atoms']}
    best, best_proof, used = st, '', []
    for pname in imp['proof_purposes']:
        cap = CAP.find(pname)
        if cap is None or not (atom_names & _graph_atoms(cap.get('graph', ''))):
            continue
        cstat, proof, _w, _k = CAP.derive_status(cap, manager=manager)
        if cstat in PROOF_ORDER and PROOF_ORDER.index(cstat) > PROOF_ORDER.index(best):
            best, best_proof, used = cstat, proof, [pname]
        elif cstat == best and best != st:
            used.append(pname)
    if best != st:
        return {'status': best, 'why': 'a Purpose whose graph holds this route\'s atoms passed: %s' % best_proof, 'proof': best_proof, 'proof_purposes_used': used}
    return {'status': st, 'why': why + '; no passing ScenarioRun yet for the Purposes that use these atoms', 'proof': '', 'proof_purposes_used': []}


# ------------------------------------------------------------------ the costs
def costs(variant):
    """The seven cost entries {kind: measured|estimated|undetermined, value, unit, basis}: the stored estimates, with the counts worked out from the
    declared lists and, where atoms exist, the MEASURED sizes (nm -S text, the stack frame from GCC's .su, the globals the atoms write)."""
    stored = _j(variant.get('cost_json'), {})
    prof, per, parts = _j(variant.get('profiles_json'), []), _j(variant.get('peripherals_json'), []), _j(variant.get('parts_json'), [])
    out = {k: dict(stored[k]) for k in COST_KEYS if k in stored}
    out['pins'] = {'kind': 'estimated', 'value': sum(int(p.get('count', 1)) for p in prof if not p.get('same_pin')), 'unit': 'pins',
                   'basis': 'counted from the route\'s declared pin profiles (%s; a profile marked same_pin is the same physical pin as the one before it); no pin assignment has been made' % ', '.join('%s x%s' % (p['kind'], p.get('count', 1)) for p in prof)}
    out['peripherals'] = {'kind': 'estimated', 'value': len(per), 'unit': 'blocks', 'basis': 'counted from the route\'s declared on-chip blocks (%s)' % ', '.join(p['kind'] for p in per)}
    out['parts'] = {'kind': 'estimated', 'value': len(parts), 'unit': 'part classes', 'basis': 'counted from the route\'s declared part classes; no circuit has been drawn for it'}
    imp = _implementation(variant)
    if imp['atoms'] and not imp['missing']:
        text = [(n, a['cost']) for n, a, _m in imp['atoms']]
        flash = sum((c['text_bytes'] if c.get('in_shipped_build') and c['text_bytes'] else c.get('text_bytes_noinline', 0)) for _n, c in text)
        builds = sorted({c.get('measured_in', '') for _n, c in text})
        out['flash_bytes'] = {'kind': 'measured', 'value': flash, 'unit': 'bytes',
                              'basis': 'nm -S text size of %s in the %s build (-Os), summed' % (', '.join('%s %d B' % (n.split(':', 1)[1], c['text_bytes']) for n, c in text), ', '.join(builds))}
        stack = max((c.get('stack_bytes', 0) or 0) for _n, c in text)
        out['stack_bytes'] = {'kind': 'measured', 'value': stack, 'unit': 'bytes', 'basis': 'the largest GCC .su stack frame among the atoms (%s build)' % ', '.join(builds)}
        glob = {}
        for _n, a, _m in imp['atoms']:
            for r in a.get('resources', []):
                if r.get('kind') == 'global' and 'w' in (r.get('access') or ''):
                    glob[r['name']] = _bytes_of(r.get('detail'))
        known = {k: v for k, v in glob.items() if v is not None}
        out['ram_bytes'] = {'kind': 'measured' if len(known) == len(glob) else 'undetermined', 'value': sum(known.values()), 'unit': 'bytes',
                            'basis': 'the declared size of each file-scope global the atoms write (%s), read by the parser; it equals the variable\'s size in .data/.bss (scalars, no padding) but is not an avr-size delta' % (', '.join('%s %s B' % kv for kv in sorted(glob.items())) or 'none written')}
        # the on-chip blocks are cross-checked against the registers the atoms touch (their Peripheral ids) - measured when they cover the declared kinds
        got = _peripheral_kinds([r.get('peripheral') for _n, a, _m in imp['atoms'] for r in a.get('resources', []) if r.get('peripheral')])
        want = {p['kind'] for p in per}
        if want and all(_covers(k, got) for k in want):
            out['peripherals'] = {'kind': 'measured', 'value': len(per), 'unit': 'blocks',
                                  'basis': 'the atoms\' parsed register touches cover every declared block (%s)' % ', '.join(sorted(got))}
    elif imp['shares_c_with']:
        pass   # the stored estimate already borrows the shared route's measured numbers (basis says so)
    return out


_PER_ID_KIND = {'EXINT': 'exint', 'PCINT': 'pcint', 'ADC': 'adc', 'AC': 'comparator', 'SPI': 'spi', 'TWI': 'twi', 'USART0': 'usart'}


def _peripheral_kinds(ids):
    out = set()
    for i in ids:
        if i.startswith('GPIO PORT'):
            out.add('gpio-port')
        elif i.startswith('TIMER'):
            out.add('timer-pwm')
        elif i in _PER_ID_KIND:
            out.add(_PER_ID_KIND[i])
    return out


def _covers(kind, got):
    return kind in got


# ------------------------------------------------------------------ one variant / one job, served
def pin_text(prof):
    return '; '.join('%s x%s (%s)' % (p['kind'], p.get('count', 1), p['role']) for p in prof)


def variant_dict(variant, ctx=None, manager=None, tier=None):
    """One variant with everything derived, plus flat plain-text columns for the tables. `ctx` = eligibility.context(board) or None."""
    from cmod.custom import isotope_variants_eligibility as E
    st = status(variant, manager)
    c = costs(variant)
    pr = parts_of(variant)
    d = dict(variant)
    for k in ('profiles_json', 'peripherals_json', 'parts_json', 'cost_json', 'implemented_by_json', 'citations_json'):
        d[k[:-5]] = _j(variant.get(k), {} if k in ('cost_json', 'implemented_by_json') else [])
        del d[k]
    imp = d['implemented_by']
    d.update({'status': st['status'], 'status_why': st['why'], 'proof': st['proof'], 'costs': c, 'parts': pr, 'implemented': bool(imp.get('atoms')),
              'implemented_atoms': ', '.join(imp.get('atoms', [])),
              'pins_text': pin_text(d['profiles']), 'peripherals_text': ', '.join(p['kind'] for p in d['peripherals']),
              'parts_text': '; '.join('%s (%s)' % (p['class'], {True: 'on the bench', False: 'NOT on the bench'}.get(p['on_bench'], 'bench status undetermined')) for p in pr),
              'parts_missing': ', '.join(p['class'] for p in pr if p['on_bench'] is False)})
    for k in COST_KEYS + ('stack_bytes',):
        if k in c:
            v = c[k]
            d['cost_' + k] = '%s (%s)' % ('undetermined' if v['value'] is None else ('%s %s' % (v['value'], v['unit'])).strip(), v['kind'])
    d.setdefault('cost_stack_bytes', 'undetermined (no build to measure)')
    if ctx is not None:
        e = E.eligible(variant, ctx, tier=tier)
        d['eligibility'] = e
        d['eligible'] = e['state']
        d['eligible_why'] = e['summary']
        d['board'] = ctx['board']
    return d


def job_dict(job, manager=None):
    ja = job_atoms(job)
    vs = variants(manager, job['name'])
    sts = [status(v, manager)['status'] for v in vs]
    return dict(job, purposes=', '.join(_j(job.get('purposes_json'), [])), atoms=', '.join(ja['atoms']), atoms_missing=', '.join(ja['missing']),
                atoms_derived=', '.join(ja['derived']), variant_count=len(vs), implemented_count=sum(1 for s in sts if s != 'declared'),
                routes=', '.join(v['route'] for v in vs), best_status=max(sts, key=PROOF_ORDER.index) if sts else 'declared')


# ------------------------------------------------------------------ the CLI (pol ... atom-jobs / atom-variants)
def _print_jobs(rows):
    for j in rows:
        print('%-18s %-16s %2d variants (%d implemented, best: %s)' % (j['name'], j['title'], j['variant_count'], j['implemented_count'], j['best_status']))
        print('    %s' % j['plain'])
        print('    atoms: %s' % (j['atoms'] or 'none'))
        if j['atoms_missing']:
            print('    MISSING atoms: %s' % j['atoms_missing'])


def _print_variants(job, rows, board):
    print('%s - %s' % (job['name'], job['plain']))
    for d in rows:
        flash = d.get('cost_flash_bytes', '?')
        print('  %-34s %-14s flash %-26s min tier %s' % (d['name'], d['status'], flash, d['minimum_level']))
        print('      pins: %s | blocks: %s' % (d['pins_text'], d['peripherals_text']))
        print('      parts: %s' % d['parts_text'])
        if board:
            print('      on %s: %s' % (board, d['eligible_why']))
        print('      status: %s' % d['status_why'])
        print('      when: %s' % d['wastefulness_note'])


def main(argv=None):
    import argparse
    import sys
    ap = argparse.ArgumentParser(prog='isotope_variants', description='The isotope variant catalogue: every way a C atom\'s job can be done.')
    sub = ap.add_subparsers(dest='cmd')
    sub.add_parser('jobs').add_argument('--json', action='store_true')
    v = sub.add_parser('variants')
    v.add_argument('job')
    v.add_argument('--board', default='')
    v.add_argument('--tier', default='')
    v.add_argument('--json', action='store_true')
    a = ap.parse_args(argv if argv is not None else sys.argv[1:])
    if a.cmd == 'jobs':
        rows = [job_dict(j) for j in jobs()]
        print(json.dumps({'ok': True, 'rows': rows}, indent=1) if a.json else '', end='')
        if not a.json:
            _print_jobs(rows)
        return 0
    if a.cmd == 'variants':
        job = next((j for j in jobs() if j['name'] == a.job), None)
        if job is None:
            print('[REFUSED] no job %r (python3 -m cmod.custom.isotope_variants jobs lists them: %s)' % (a.job, ', '.join(j['name'] for j in jobs())))
            return 3
        ctx = None
        if a.board:
            from cmod.custom import isotope_variants_eligibility as E
            ctx = E.context(a.board)
            if ctx is None:
                print('[REFUSED] no board %r with a SoC row (known: %s)' % (a.board, ', '.join(E.boards())))
                return 3
        rows = [variant_dict(x, ctx, tier=a.tier or None) for x in variants(None, a.job)]
        if a.json:
            print(json.dumps({'ok': True, 'job': a.job, 'board': a.board, 'rows': rows}, indent=1))
        else:
            _print_variants(job, rows, a.board)
        return 0
    ap.print_help()
    return 2


if __name__ == '__main__':
    import sys
    sys.exit(main())
