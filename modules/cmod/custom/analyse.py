"""
@module cmod.custom.analyse

A PROJECT'S ATOMS across its configurations (C_MODULARIZATION_PLAN.md §2): parse every configuration (projects.render →
atoms.tu_facts), keep the functions defined in the project's own .c files as atoms (keyed `<module>.<function>`, an
ISR by its vector), UNION what each configuration says (conservative: an atom "may touch" what any configuration makes it
touch), attach the annotations, then the closure verdicts — pure, and ISR-safe against everything ISR context touches.
"""
import os
import tempfile

from cmod.custom import atoms as T
from cmod.custom import projects as P
from cmod.custom import registers as R
from cmod.custom.c_types import polari_type


def _key(module_file, name):
    return '%s.%s' % (os.path.splitext(module_file)[0], name)


def _merge(dst, f):
    for g, a in f['globals'].items():
        d = dst['globals'].setdefault(g, dict(a))
        for k in ('r', 'w', 'rmw', 'inside_atomic', 'outside_atomic'):
            d[k] = d.get(k) or a.get(k)
    for r, a in f['registers'].items():
        d = dst['registers'].setdefault(r, dict(a))
        d['r'], d['w'] = d['r'] or a['r'], d['w'] or a['w']
    for c in f['calls']:
        if c not in dst['calls']:
            dst['calls'].append(c)
    for p, u in f['pointers'].items():
        d = dst['pointers'].setdefault(p, {'r': False, 'w': False, 'passed': []})
        d['r'], d['w'] = d['r'] or u['r'], d['w'] or u['w']
        d['passed'] = sorted(set(d['passed']) | set(u['passed']))
    dst['atomic'] = dst['atomic'] or f['atomic']
    sig = (repr([(n, d['c']) for n, d in f['params']]), f['returns']['c'])
    if sig != dst['_sig']:
        dst['signature_varies'] = True


def parse_project(project, work=None):
    """→ {'spec', 'configs': [...], 'atoms': {key: facts}, 'library': {name: facts}, 'annotations': {key: ann}, 'problems'}."""
    spec = P.resolve(project)
    work = work or tempfile.mkdtemp(prefix='cmod-%s-' % spec['name'])
    atoms, library, configs, problems = {}, {}, [], []
    from cmod.custom import annotation as A
    for _mod, files, _role in spec['modules']:   # a malformed annotation is refused BEFORE anything is preprocessed
        for fn in files:
            if fn.endswith('.c') and os.path.isfile(os.path.join(spec['root'], fn)):
                A.find(open(os.path.join(spec['root'], fn)).read(), fn)
    for cfg in P.configurations(spec):
        r = P.render(spec, cfg, os.path.join(work, cfg['name']))
        cfg_rec = {'name': cfg['name'], 'kind': cfg['kind'], 'app': cfg.get('app', ''), 'flags': cfg.get('flags', []),
                   'sources': [r['map'][s] for s in r['sources']], 'generated': r['generated'], 'source_sha': r.get('source_sha', ''),
                   'dir': r['dir']}
        configs.append(cfg_rec)
        for src in r['sources']:
            facts, probs = T.tu_facts(os.path.join(r['dir'], src), r['include_dirs'], mcu=spec['mcu'])
            problems += ['%s/%s: %s' % (cfg['name'], src, p) for p in probs]
            for name, f in facts.items():
                if f['file'] == src:
                    mod = r['map'][src]
                    k = _key(mod, name)
                    if k not in atoms:
                        atoms[k] = dict(f, module=mod, name=name, configs=[], globals={}, registers={}, calls=[], pointers={}, atomic=False,
                                        _sig=(repr([(n, d['c']) for n, d in f['params']]), f['returns']['c']))
                    atoms[k]['configs'].append(cfg['name'])
                    _merge(atoms[k], f)
                else:
                    library.setdefault(name, f)
    anns = {}
    for mod, files, _role in spec['modules']:
        for fn in files:
            if fn.endswith('.c') and os.path.isfile(os.path.join(spec['root'], fn)):
                here = {a['name'] for a in atoms.values() if a['module'] == fn}
                for name, a in T.attach_annotations(os.path.join(spec['root'], fn), fn, here).items():
                    anns[_key(fn, name)] = a
    for k, a in atoms.items():
        a['annotation'] = anns.get(k)
        a['ports'] = T._ports(a, a['annotation'])
    missing = sorted(set(anns) - set(atoms))
    unparsed = [k for k in missing]
    _verdicts(atoms, library, spec['mcu'])
    return {'spec': spec, 'configs': configs, 'atoms': atoms, 'library': library, 'annotations': anns, 'problems': problems,
            'annotated_not_compiled': unparsed, 'work': work}


def _by_function(atoms, library):
    idx = {}
    for k, a in atoms.items():
        idx.setdefault(a['function'] if not a['isr'] else a['isr'], []).append(('atom', k, a))
    for n, f in library.items():
        idx.setdefault(n, []).append(('library', n, f))
    return idx


def _verdicts(atoms, library, mcu):
    idx = _by_function(atoms, library)
    every = list(atoms.values()) + list(library.values())
    # ---- pure: the greatest fixpoint (recursion stays pure if nothing else breaks it)
    for f in every:
        f['pure'], f['pure_why'] = True, ''
    changed = True
    while changed:
        changed = False
        for f in every:
            if not f['pure']:
                continue
            why = ''
            if f.get('isr'):
                why = 'is an ISR'
            elif f['globals']:
                why = 'touches %s' % ', '.join(sorted(f['globals']))
            elif f['registers']:
                why = 'touches register %s' % ', '.join(sorted(f['registers']))
            else:
                for c in f['calls']:
                    if T.lib_resource(c):
                        why = 'calls %s (%s)' % (c, T.lib_resource(c))
                    elif c in T.LIB_MEMORY:
                        continue
                    elif c not in idx:
                        why = 'calls %s (not defined in the project)' % c
                    elif not all(x[2]['pure'] for x in idx[c]):
                        why = 'calls %s (not pure)' % c
                    if why:
                        break
            if why:
                f['pure'], f['pure_why'], changed = False, why, True
    # ---- what ISR context touches (ISRs + everything they call, transitively)
    isr_g, seen, stack = {}, set(), [f for f in atoms.values() if f['isr']]
    while stack:
        f = stack.pop()
        fid = id(f)
        if fid in seen:
            continue
        seen.add(fid)
        for g, a in f['globals'].items():
            d = isr_g.setdefault(_gkey(f, g), {'r': False, 'w': False, 'by': set()})
            d['r'], d['w'] = d['r'] or a['r'], d['w'] or a['w']
            d['by'].add(f.get('isr') or f['function'])
        for c in f['calls']:
            stack += [x[2] for x in idx.get(c, [])]
    for f in every:
        for g, a in f['globals'].items():
            a['shared_with_isr'] = sorted(isr_g[_gkey(f, g)]['by']) if _gkey(f, g) in isr_g and not f.get('isr') else []
    # ---- ISR-safe: direct hazards, then through callees (fixpoint)
    for f in every:
        f['isr_safe'], f['isr_safe_why'] = ('isr', 'runs in interrupt context (interrupts are off inside it on the AVR)') if f.get('isr') else ('yes', '')
        if f.get('isr'):
            continue
        hazards = []
        for g, a in sorted(f['globals'].items()):
            k = _gkey(f, g)
            if k not in isr_g or not a['outside_atomic']:
                continue
            w = a['decl'].get('width', 0) if a['decl']['kind'] != 'array' else (a['decl'].get('target') or {}).get('width', 0)
            if w > 1:
                hazards.append('%s (%d B, %s by ISR %s) is accessed outside an atomic block — a tick between its byte loads tears it'
                               % (g, w, 'written' if isr_g[k]['w'] else 'read', ', '.join(sorted(isr_g[k]['by']))))
            elif a['rmw'] and isr_g[k]['w']:
                hazards.append('%s is modified read-modify-write outside an atomic block while ISR %s writes it (a lost update)'
                               % (g, ', '.join(sorted(isr_g[k]['by']))))
            if not a['decl'].get('volatile'):
                hazards.append('%s is shared with ISR %s but not volatile' % (g, ', '.join(sorted(isr_g[k]['by']))))
        if hazards:
            f['isr_safe'], f['isr_safe_why'] = 'no', '; '.join(hazards)
        elif any(c in ('sei', 'cli') for c in f['calls']) and any(_gkey(f, g) in isr_g for g in f['globals']):
            f['isr_safe'], f['isr_safe_why'] = 'undetermined', 'opens a manual cli()/sei() region around ISR-shared data (regions are not tracked)'
    changed = True
    while changed:
        changed = False
        for f in every:
            if f['isr_safe'] != 'yes':
                continue
            bad = [c for c in f['calls'] if any(x[2]['isr_safe'] in ('no', 'undetermined') for x in idx.get(c, []))]
            if bad:
                f['isr_safe'], f['isr_safe_why'], changed = 'no', 'calls %s (not ISR-safe)' % ', '.join(bad), True


def _gkey(f, g):
    decl = (f['globals'].get(g) or {}).get('decl') or {}
    return (decl.get('file', ''), g) if decl.get('static') else ('', g)


def resources(a, mcu='atmega328p'):
    """An atom's resources as flat records: register / global / isr / library / declared."""
    vec = R.load(mcu)['vectors']
    out = []
    if a.get('isr'):
        out.append({'kind': 'isr', 'name': a['isr'], 'access': 'is', 'peripheral': '', 'detail': 'vector %s' % vec.get(a['isr'], '?')})
    for name, u in sorted(a['registers'].items()):
        out.append({'kind': 'register', 'name': name, 'access': ('r' if u['r'] else '') + ('w' if u['w'] else ''), 'peripheral': R.peripheral(name),
                    'detail': ''})
    for name, u in sorted(a['globals'].items()):
        d = u['decl']
        w = d.get('width', 0) if d['kind'] != 'array' else (d.get('target') or {}).get('width', 0)
        det = '%s, %d B%s%s' % (d['c'], w, ' (element)' if d['kind'] == 'array' else '',
                                  ', shared with ISR %s' % ', '.join(u['shared_with_isr']) if u.get('shared_with_isr') else '')
        out.append({'kind': 'global', 'name': name, 'access': ('r' if u['r'] else '') + ('w' if u['w'] else ''), 'peripheral': '',
                    'detail': det + (', inside ATOMIC_BLOCK' if u['inside_atomic'] and not u['outside_atomic'] else '')})
    for c in a['calls']:
        if T.lib_resource(c):
            out.append({'kind': 'library', 'name': c, 'access': 'call', 'peripheral': T.lib_resource(c), 'detail': 'avr-libc'})
    for u in ((a.get('annotation') or {}).get('uses') or []):
        out.append({'kind': 'declared', 'name': u, 'access': '', 'peripheral': R.peripheral(u), 'detail': 'POLARI_NODE uses()'})
    return out


def signature(a):
    params = ', '.join('%s %s' % (d['c'], n) for n, d in a['params']) or 'void'
    if a.get('isr'):
        return 'ISR(%s)' % a['isr']
    return '%s %s(%s)' % (a['returns']['c'], a['function'], params)


def return_polari_type(a):
    return polari_type(a['returns'])
