"""
@module cmod.custom.firmware_cli

`pol firmware` — fs-0 (DEMONSTRABLES_PLAN.md §9): FirmwareSolutions (a CGraph + a board in, a firmware build out).

    list                          every FirmwareSolution row
    show <solution>                its DERIVED schedule (lane/order/trigger) + register map (bound/unbound/conflict)
    validate <solution>            re-run validate() now: board exists + usable, targets named, no pin conflicts
    build <solution>                cmod-glue render+build (reused) — refuses if validate() fails first
    run <solution> --mode digital-twin|hardware
                                   validate -> build's twin proof, or the detected board's flash route
    assign <solution> --task T --port P --pin <BoardPin>
                                   the door the pin-map drag (fs-1) will call
"""
import sys


def _solution(name):
    from cmod.cmod_seed import CMOD_SEED_PAIRS
    for n, _cls, rs in CMOD_SEED_PAIRS:
        if n == 'FirmwareSolution':
            for r in rs:
                if r['name'] == name:
                    return r
    return None


def _list():
    from cmod.cmod_seed import CMOD_SEED_PAIRS
    rows = next(rs for n, _c, rs in CMOD_SEED_PAIRS if n == 'FirmwareSolution')
    for r in rows:
        print('%-16s graph=%-20s board=%-16s runtime=%-14s %s (%s)'
              % (r['name'], r['graph'], r['board_definition'] or r['board_variable'], r['runtime'], r['status'], r['validation']))
    return 0


def _show(name):
    from cmod.custom import firmware as FW
    fs = _solution(name)
    if fs is None:
        print('no FirmwareSolution %r (pol firmware list)' % name)
        return 2
    print('%s — %s' % (fs['name'], fs['purpose']))
    print('schedule (DERIVED, D-fs-1):')
    for s in sorted(FW.schedule_for(fs['graph'], name), key=lambda r: (r['lane'], r['order'])):
        print('  %-6s %3d  %-14s %s' % (s['lane'], s['order'], s['task'], s['trigger']))
    print('register map (DERIVED, D-fs-2):')
    for a in sorted(FW.assignments_for(fs['graph'], name), key=lambda r: (r['target_kind'], r['task'])):
        port = ('.' + a['port']) if a['port'] else ''
        print('  %-8s %-16s %-10s -> %-20s [%s]' % (a['target_kind'], a['task'] + port, a['status'], a['lives_on'], a['controls'][:50]))
    return 0


def _validate(name):
    from cmod.custom import firmware as FW
    fs = _solution(name)
    if fs is None:
        print('no FirmwareSolution %r (pol firmware list)' % name)
        return 2
    ok, why, _ = FW.validate(fs, manager=None)
    print(('ok: ' if ok else 'refused: ') + why)
    return 0 if ok else 1


def _build(name):
    from cmod.custom import firmware as FW
    from cmod.custom.glue import GlueRefused
    fs = _solution(name)
    if fs is None:
        print('no FirmwareSolution %r (pol firmware list)' % name)
        return 2
    try:
        rec = FW.build(fs, manager=None)
    except GlueRefused as e:
        print('refused: %s' % e)
        return 2
    b = rec['build']
    print('%s built by %s\n  .hex %s  .text %d .data %d .bss %d' % (name, b['built_by'], b['hex_sha256'][:16], b['size_text'], b['size_data'], b['size_bss']))
    return 0


def _run(name, mode):
    from cmod.custom import firmware as FW
    fs = _solution(name)
    if fs is None:
        print('no FirmwareSolution %r (pol firmware list)' % name)
        return 2
    r = FW.run(fs, mode, manager=None)
    print('%s route=%s ok=%s why=%s' % (name, r.get('route'), r.get('ok'), r.get('why')))
    return 0 if r.get('ok') else 1


def _assign(name, task, port, pin):
    print('pol firmware assign is the door /api/firmware/solutions/%s/assign calls from a live server (needs a manager); '
          'this CLI path is for the pin-map drag (fs-1) against a RUNNING instance — use the API directly until then: '
          'POST /api/firmware/solutions/%s/assign {"task": %r, "port": %r, "lives_on": %r}' % (name, name, task, port, pin))
    return 0


def main(argv):
    import argparse
    ap = argparse.ArgumentParser(prog='pol firmware')
    ap.add_argument('verb', choices=('list', 'show', 'validate', 'build', 'run', 'assign'))
    ap.add_argument('target', nargs='?', default='')
    ap.add_argument('--mode', default='digital-twin')
    ap.add_argument('--task', default='')
    ap.add_argument('--port', default='')
    ap.add_argument('--pin', default='')
    a = ap.parse_args(argv)
    if a.verb == 'list':
        return _list()
    if not a.target:
        print('usage: pol firmware %s <solution>   (pol firmware list)' % a.verb)
        return 2
    return {'show': lambda: _show(a.target), 'validate': lambda: _validate(a.target), 'build': lambda: _build(a.target),
            'run': lambda: _run(a.target, a.mode), 'assign': lambda: _assign(a.target, a.task, a.port, a.pin)}[a.verb]()


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
