"""
@module cmod.custom.cmod_cli

`pol cmod` — C modularization (C_MODULARIZATION_PLAN.md, cmod-0):

    atoms <project>            parse the project NOW (pycparser, no engine) → one line per atom: kind, signature, ports, resources
    conform <project> [--no-measure]
                               parse + measure (avr-gcc / avr-nm / make through the board engines seam) → polari-firmware.json in
                               the project root; written only when something derived changed (a second conform: unchanged)
    show <atom> [--project P]  one atom from the committed manifest: ports, resources, ISR-safety, cost
    drift <project>            parse now vs the committed manifest (nothing measured, nothing written)
    registers [--refresh]      the register snapshot (avr-libc <avr/io.h> via avr-gcc -E -dM); --refresh re-derives it
    engines                    where avr-gcc / avr-nm / make would run

<project> = a template name (uno) or a directory holding *.c and a Makefile (a plain project).
"""
import json
import sys


def _atoms(project):
    from cmod.custom import analyse as AN
    p = AN.parse_project(project)
    print('%s (%s, %s) — %d atoms over %d configurations: %s' % (p['spec']['name'], p['spec']['kind'], p['spec']['root_rel'], len(p['atoms']),
                                                              len(p['configs']), ', '.join(c['name'] for c in p['configs'])))
    for k in sorted(p['atoms']):
        a = p['atoms'][k]
        ports = ', '.join('%s %s:%s' % (x['direction'], x['name'], x['polari_type'] or '-') for x in a['ports']) or '-'
        res = ', '.join('%s %s' % (r['kind'][:3], r['name']) for r in AN.resources(a, p['spec']['mcu'])) or '-'
        print('  %-30s %-8s %s\n      ports: %s\n      touches: %s\n      pure: %s   isr-safe: %s%s%s' % (
            k, 'isr' if a['isr'] else 'entry' if a['function'] == 'main' else 'function', AN.signature(a), ports, res, a['pure'],
            a['isr_safe'], (' — ' + a['isr_safe_why']) if a['isr_safe_why'] and a['isr_safe'] != 'isr' else '',
            '   [POLARI_NODE %s]' % a['annotation']['form'] if a.get('annotation') else ''))
    for prob in p['problems']:
        print('  preprocessor: %s' % prob)
    return 0


def _conform(project, measure):
    from cmod.custom import manifest as MF
    r = MF.conform(project, measure=measure)
    c = r['manifest']['counts']
    print('%s %s' % ('wrote' if r['written'] else 'unchanged', r['path']))
    print('  %d atoms (%d annotated, %d ISRs, %d pure, %d ports; %d not ISR-safe)' % (c['atoms'], c['annotated'], c['isr'], c['pure'], c['ports'],
                                                                                     c['not_isr_safe']))
    for k in ('added', 'removed', 'edited'):
        if r[k]:
            print('  %s: %s' % (k, ', '.join(r[k])))
    for cfg in r['manifest']['configurations']:
        mk = cfg.get('make_alone')
        if mk:
            print('  make alone: %-18s %s  .hex %s' % (cfg['name'], 'ok' if mk['ok'] else 'FAILED', mk['hex_sha256'][:16]))
    for p in r['problems']:
        print('  INVALID: %s' % p)
    return 0 if r['ok'] else 1


def _show(atom, project):
    from cmod.custom import projects as P
    m = json.load(open(P.manifest_path(P.resolve(project))))
    hits = [a for a in m['atoms'] if a['name'] == atom] or [a for a in m['atoms'] if a['function'] == atom or a['isr_vector'] == atom]
    if len(hits) != 1:
        print('%s: %s' % (atom, 'several atoms — %s' % ', '.join(a['name'] for a in hits) if hits else 'no such atom in %s' % project))
        return 2
    a = hits[0]
    c = a.get('cost') or {}
    print('%s:%s  (%s, %s:%d)\n  %s' % (m['project'], a['name'], a['kind'], a['module'], a['line'], a['signature']))
    if a.get('annotation'):
        print('  role: %s   [%s form]' % (a['annotation']['role'] or '-', a['annotation']['form']))
    print('  ports:')
    for x in a['ports'] or []:
        print('    %-6s %-8s %-24s %-12s %-6s %s  (%s)' % (x['direction'], x['name'], x['ctype'], x['polari_type'] or '-', x['unit'] or '-',
                                                       x['meaning'] or '', x['source']))
    if not a['ports']:
        print('    (none)')
    print('  resources:')
    for r in a['resources'] or []:
        print('    %-8s %-18s %-4s %-12s %s' % (r['kind'], r['name'], r['access'], r['peripheral'], r['detail']))
    if not a['resources']:
        print('    (none)')
    print('  calls: %s' % (', '.join(a['calls']) or '-'))
    print('  pure: %s%s' % (a['pure'], (' — ' + a['pure_why']) if a['pure_why'] else ''))
    print('  isr-safe: %s%s' % (a['isr_safe'], (' — ' + a['isr_safe_why']) if a['isr_safe_why'] else ''))
    print('  cost (%s): text %s B shipped, %s B as a node; stack %s B %s%s' % (
        c.get('measured_in', '-'), c.get('text_bytes'), c.get('text_bytes_noinline'), c.get('stack_bytes'), c.get('stack_kind', ''),
        ('\n    ' + c['why']) if c.get('why') else ''))
    print('  configurations: %s' % ', '.join(a['configs']))
    return 0


def main(argv):
    import argparse
    ap = argparse.ArgumentParser(prog='pol cmod')
    ap.add_argument('verb', choices=('atoms', 'conform', 'show', 'drift', 'registers', 'engines'))
    ap.add_argument('target', nargs='?', default='')
    ap.add_argument('--project', default='uno')
    ap.add_argument('--no-measure', action='store_true')
    ap.add_argument('--refresh', action='store_true')
    a = ap.parse_args(argv)
    from cmod.custom.annotation import AnnotationRefused
    from cmod.custom.atoms import CModRefused
    from cmod.custom.projects import ProjectRefused
    try:
        if a.verb == 'atoms':
            return _atoms(a.target or 'uno')
        if a.verb == 'conform':
            return _conform(a.target or 'uno', not a.no_measure)
        if a.verb == 'show':
            return _show(a.target, a.project)
        if a.verb == 'drift':
            from cmod.custom import manifest as MF
            r = MF.conform(a.target or 'uno', measure=False, write=False)
            print('%s: %s' % (a.target or 'uno', 'STALE — run pol cmod conform' if r['changed'] else 'the committed manifest matches the sources'))
            for k in ('added', 'removed', 'edited'):
                if r[k]:
                    print('  %s: %s' % (k, ', '.join(r[k])))
            return 1 if r['changed'] else 0
        if a.verb == 'registers':
            from cmod.custom import registers as R
            s = R.refresh() if a.refresh else R.load()
            print('%s: %d registers, %d vectors (avr-libc %s, -dM sha %s)%s' % (s.get('mcu', 'atmega328p'), len(s['registers']), len(s['vectors']),
                                                                              s.get('avr_libc'), (s.get('dm_sha256') or '')[:16],
                                                                              ' — refreshed' if a.refresh else ''))
            return 0
        from cmod.custom import cmod_engines
        for e, w in cmod_engines.placement().items():
            print('  %-8s %-13s %s  %s' % (e, w['how'], w.get('where', ''), w.get('why', '')))
        return 0
    except (AnnotationRefused, CModRefused, ProjectRefused) as e:
        print('refused: %s' % e)
        return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
