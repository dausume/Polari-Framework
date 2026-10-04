"""
@module hwnocode.custom.hwnocode_cli

`pol hwnocode` — hardware as no-code (HARDWARE_NOCODE_PLAN.md, hn-0):

    solutions                       the HardwareSolutions: subgraph, interface, runtime knob, status
    place <solution>                the placement report: every node → board | twin | bridge | backend | browser, and why
                                    (a Python node on the device side is REFUSED, naming it)
    render <solution> [--work W]    hn-split: the board half through cmod-glue into W/project (its files_sha256 must EQUAL cmod-1's
                                    record), the backend half as <solution>.backend; the record custom/splits/<solution>.json
    build <solution> [--work W]     make ALONE in W/project (board engines) → W/out/firmware.hex + W/firmware_build.json, so
                                    `pol board twin uno up --work W` runs that build
    suggest <solution>              the runtime suggestion with its evidence rows — SUGGEST ONLY (D-hn-3): nothing is changed
    runtime <solution> <value>      would the knob accept this value? (bare-c | freertos | esp-idf | zephyr; auto refused)
W defaults to $POLARI_HWNOCODE_HOME/<solution> (module_home.module_home('hwnocode')/<solution>: /app/data/hwnocode/<solution>
inside a backend container, ~/.cache/polari-hwnocode/<solution> on a bare host).
"""
import sys


def _place(name):
    from hwnocode.custom import placement as PL
    from hwnocode.custom import split as SP
    r = SP.place_solution(name)
    print('%s — placement (derived, never typed in; plan §2b): %s' % (name, PL.summary(r)))
    for layer in ('solution', 'subgraph', 'display'):
        rows = [n for n in r['nodes'] if n['layer'] == layer]
        if rows:
            print('  [%s]' % layer)
        for n in rows:
            print('    %-12s %-19s %-8s %-24s %s' % (n['node'], n['kind'], n['placement'], n['language'], n['why']))
    print('  firmware_runtime: %s — %s' % (r['runtime']['value'], r['runtime']['why']))
    for x in r['refusals']:
        print('  REFUSED: %s' % x)
    return 2 if r['refusals'] else 0


def _render(name, work):
    from hwnocode.custom import split as SP
    r = SP.render(name, work=work)
    pv = r['provenance']
    print('%s rendered by hn-split into %s' % (name, r['project']))
    print('  split sha256 %s   placement: %s' % (pv['split_sha256'][:16], pv['placement_summary']))
    print('  board half   cmod-glue of %s: graph %s, files %s' % (pv['glue']['graph'], pv['glue']['graph_sha256'][:16], pv['glue_files_sha256'][:16]))
    for f in sorted(pv['glue_files']):
        print('    %-24s %s  %s' % (f, pv['glue_files'][f][:16], 'equal to cmod-1' if r['same']['files'][f] else 'DIFFERS from cmod-1'))
    print('  cmod-1 record files_sha256 %s → %s' % (r['cmod_record']['files_sha256'][:16],
                                                  'UNCHANGED OUTPUT (equal)' if r['unchanged_output'] else 'DIFFERENT'))
    print('  backend half %s: %s' % (r['backend_definition']['solutionName'],
                                    ', '.join(s['stateName'] for s in r['backend_definition']['stateInstances'])))
    print('  next: pol hwnocode build %s%s' % (name, (' --work %s' % work) if work else ''))
    return 0 if r['unchanged_output'] else 1


def _build(name, work):
    from hwnocode.custom import split as SP
    b = SP.build(name, work=work)
    print('%s built by %s in %.1f s' % (name, b['built_by'], b['wall_s']))
    print('  .hex %s  .text %d  .data %d  .bss %d  (flash %d B, RAM %d B)' % (b['hex_sha256'][:16], b['size_text'], b['size_data'], b['size_bss'],
                                                                         b['flash_bytes'], b['ram_bytes']))
    print('  cmod-1 .hex %s → %s' % (b['ref_hex_sha256'][:16], 'BYTE-IDENTICAL' if b['byte_identical_to_cmod1'] else 'DIFFERENT'))
    print('  next: pol board twin uno up --work %s --adc0-ramp 700,800,8000' % b['work'])
    return 0 if b['byte_identical_to_cmod1'] else 1


def _suggest(name):
    from hwnocode.custom import suggest as SG
    r = SG.suggest(name)
    print('%s — runtime SUGGESTION: %s (rule %d decides; plan §3)' % (name, r['suggested'], r['decisive_rule']))
    for x in r['reasons']:
        print('  - %s' % x)
    print('  rule table (ordered; the first that holds decides):')
    for ru in r['rules']:
        print('    %s %d. %-78s → %s' % ('*' if ru['rule'] == r['decisive_rule'] else ' ', ru['rule'], ru['condition'], ru['suggests']
                                       if ru['holds'] else 'does not hold'))
    print('  evidence (rule %d):' % r['decisive_rule'])
    for ru in r['rules']:
        if ru['rule'] == r['decisive_rule'] or (ru['holds'] and ru['rule'] == 4):
            for e in ru['evidence']:
                print('    - %s' % e)
    print('  knob: firmware_runtime = %s (%s)' % (r['knob']['firmware_runtime'], 'accepted' if r['knob']['ok'] else 'refused: ' + r['knob']['why']))
    print('  %s' % r['policy'])
    return 0


def _solutions():
    from hwnocode.custom import seed_rows as SR
    sols, places = SR.solution_rows()
    for s in sols:
        print('%-16s variant %s · subgraph %s · interface %s · runtime %s · %s\n    placement %s\n    status %s%s' % (
            s['name'], s['variant_kind'], s['cgraph'], s['interface'], s['firmware_runtime'], s['runtime_status'][:60], s['placement_summary'],
            s['status'], ('  · split %s' % s['split_sha256'][:16]) if s['split_sha256'] else ''))
    return 0


def main(argv):
    import argparse
    ap = argparse.ArgumentParser(prog='pol hwnocode')
    ap.add_argument('verb', choices=('solutions', 'place', 'render', 'build', 'suggest', 'runtime'))
    ap.add_argument('target', nargs='?', default='uno-temp-split')
    ap.add_argument('value', nargs='?', default='')
    ap.add_argument('--work', default=None)
    a = ap.parse_args(argv)
    from hwnocode.custom.split import SplitRefused
    from cmod.custom.glue import GlueRefused
    from cmod.custom.graph import GraphRefused
    try:
        if a.verb == 'solutions':
            return _solutions()
        if a.verb == 'place':
            return _place(a.target)
        if a.verb == 'render':
            return _render(a.target, a.work)
        if a.verb == 'build':
            return _build(a.target, a.work)
        if a.verb == 'suggest':
            return _suggest(a.target)
        from hwnocode.custom import knobs as K
        from hwnocode.custom import split as SP
        p = SP.solution_rows(a.target)
        ok, why = K.check_runtime(a.value, p['board'])
        print('%s: firmware_runtime=%s %s — %s' % (a.target, a.value or 'bare-c', 'ACCEPTED' if ok else 'REFUSED', why))
        return 0 if ok else 2
    except (SplitRefused, GlueRefused, GraphRefused) as e:
        print('refused: %s' % e)
        return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
