"""
@module cmod.custom.firmware_cli

`pol firmware` — fs-0 (DEMONSTRABLES_PLAN.md §9): FirmwareSolutions (a CGraph + a board in, a firmware build out).
ucd-0b2b (§5h, his ruling 2026-10-08): every verb that took `<solution>` also accepts `<solution>@<board>` (a
specific HardwareBinding — the default binding when omitted, unchanged).

    list                          every FirmwareSolution row
    show <solution>[@<board>]      its DERIVED schedule (lane/order/trigger) + register map (bound/unbound/conflict)
    validate <solution>[@<board>]  re-run validate() now: board exists + usable, targets named, no pin conflicts
    build <solution>                cmod-glue render+build (reused) — refuses if validate() fails first
    run <solution> --mode digital-twin|hardware
                                   validate -> build's twin proof, or the detected board's flash route
    assign <solution>[@<board>] --task T --port P --pin <BoardPin>
                                   the door the pin-map drag (fs-1) will call
    bindings [<solution>]          every HardwareBinding (or just one solution's) with status/why
    bind <solution> --board <board>
                                   a NEW HardwareBinding over `solution` (a dry-run preview — PURE, no manager; a
                                   running server's POST /api/firmware/solutions/{name}/bindings persists it)
"""
import json
import sys


def _solution(name):
    from cmod.cmod_seed import CMOD_SEED_PAIRS
    sol_name = (name or '').partition('@')[0]
    for n, _cls, rs in CMOD_SEED_PAIRS:
        if n == 'FirmwareSolution':
            for r in rs:
                if r['name'] == sol_name:
                    return r
    return None


def _target(name):
    """(solution_name, binding_dict_or_None) — binding is None for a bare solution name (every verb's pre-0b2b
    behavior, unchanged: claims.py's thin wrapper resolves the default binding itself); set to the resolved
    HardwareBinding dict when `name` carries '@board' (ucd-0b2b). PURE (manager=None) — this CLI never touches a
    running server's own rows."""
    from cmod.custom import binding as BND
    sol_name, rest = BND.parse_target(name)
    if not rest:
        return sol_name, None
    return sol_name, BND.resolve(name, manager=None)


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
    """fs-2a (his ruling: "pol firmware assign prints the refusal"): a DRY-RUN check against the pure, seed-time
    rows (board.custom.target_compat + cmod.custom.firmware.check_drop) — no manager, no write; against a RUNNING
    server, POST /api/firmware/solutions/{name}/assign is still the door that actually moves the row."""
    from cmod.custom import firmware as FW
    fs = _solution(name)
    if fs is None:
        print('no FirmwareSolution %r (pol firmware list)' % name)
        return 2
    if not task or not pin:
        print('usage: pol firmware assign <solution> --task <task> [--port <port>] --pin <BoardPin|unbound>')
        return 2
    sol_name, b = _target(name)
    ok, status, why = FW.check_drop(fs['graph'], sol_name, task, pin, manager=None, binding_name=(b['name'] if b else None))
    if not ok:
        print('refused: %s' % why)
    elif status == 'undetermined':
        print('ok (undetermined — warning): %s' % why)
    else:
        print('ok: %s' % why)
    print('(this is a dry run against the seed-time rows; against a RUNNING server, use '
          'POST /api/firmware/solutions/%s/assign {"task": %r, "port": %r, "lives_on": %r})' % (name, task, port, pin))
    return 0 if ok else 1


def _claims(name, as_json):
    """ucd-0b: pin claims + peripheral claims + register settings (+ their field lines) — the PURE, seed-time
    derivation (no manager, no persisted canvas overrides); a running server's GET /api/firmware/solutions/<name>
    carries the live, materialized rows instead. ucd-0b2b: `name` may be '<solution>@<board>'."""
    from cmod.custom import claims as C
    fs = _solution(name)
    if fs is None:
        print('no FirmwareSolution %r (pol firmware list)' % name)
        return 2
    sol_name, b = _target(name)
    target = b if b is not None else sol_name
    pins = C.pin_claims(target, fs['graph'])
    periph = C.peripheral_claims(target, fs['graph'])
    gen = C.register_settings(target, fs['graph'])
    if as_json:
        print(json.dumps({'claims': pins, 'peripheral_claims': periph, 'register_settings': gen['RegisterSetting'],
                          'field_settings': gen['RegisterFieldSetting'], 'routes': gen['SignalRoute']}, indent=1))
        return 0
    print('%s — pin claims:' % name)
    for c in pins:
        canonical = c['name'].split(':', 1)[1]
        print('  %-5s %-13s mode=%-4s pin_function=%-22s pull=%-11s edge=%-11s initial=%-5s [%s] %s'
              % (canonical, c['requirement_kind'], c['mode'], c['pin_function'] or '-', c['pull'], c['edge'], c['initial'], c['status'], c['why']))
    print('peripheral claims:')
    for p in periph:
        tasks = ', '.join(json.loads(p['tasks_json']))
        print('  %-20s %-14s [%s] tasks=%s' % (p['name'].split(':', 1)[1], p['usage'], p['status'], tasks))
    print('register settings (init):')
    for r in gen['RegisterSetting']:
        print('  %-10s = %s (mask %s) [%s]' % (r['register'].split(':', 1)[1], r['value'], r['write_mask'], r['status']))
        for f in gen['RegisterFieldSetting']:
            if f['register_setting'] == r['name']:
                print('      %-10s = %-4s %-10s (%s)' % (f['register_field'].split('.', 1)[1], f['value'], f['rule'], f['meaning'][:60]))
    return 0


def _server_statuses():
    """{Purpose name: derived status} from the server POLARI_API names (its ScenarioRuns live there); None when unset or
    unreachable (then the seed's own status is used and the export says so)."""
    import os, ssl, urllib.request
    api = os.environ.get('POLARI_API', '').rstrip('/')
    if not api:
        return None
    try:
        ctx = ssl._create_unverified_context()
        with urllib.request.urlopen(urllib.request.Request(api + '/api/capabilities'), timeout=15, context=ctx) as r:
            d = json.load(r)
        rows = d if isinstance(d, list) else (d.get('rows') or d.get('capabilities') or [])
        return {x.get('name'): x.get('status', 'planned') for x in rows if x.get('name')}
    except Exception as e:  # noqa: BLE001 — said, not raised
        print('  (Purpose statuses not read from %s: %s — the seed\'s own statuses are used)' % (api, e))
        return None


def _export(name, target, out, verify, as_json, form='source-dir'):
    from cmod.custom import export_cmake as EX
    fs = _solution(name)
    try:
        statuses = _server_statuses()
        row = EX.export(fs, target=target, out_root=out, verify_build=verify, statuses=statuses, form=form)
    except EX.ExportRefused as e:
        print('refused: %s' % e)
        return 2
    if as_json:
        print(json.dumps(row, indent=1))
        return 0
    print('exported %s -> %s' % (name, row['path']))
    print('  tar      %s  sha256 %s' % (row['tar_path'], row['tar_sha256'][:16]))
    print('  files    %s' % ', '.join(f['file'] for f in json.loads(row['files_json'])))
    print('  build    cmake -S . -B build && cmake --build build   |   cmake -P polari-build.cmake')
    print('  parity   %s (makefile hex %s, cmake hex %s)' % (row['parity'], row['makefile_sha256'][:16] or '—', row['cmake_sha256'][:16] or '—'))
    print('  proof    %s' % row['notes'])
    if row['verify_log']:
        print('  verify   ' + row['verify_log'].strip().splitlines()[0][:140])
    return 0 if row['status'] != 'refused' else 1


def _bindings(name):
    """ucd-0b2b: `pol firmware bindings [<solution>]` — every HardwareBinding (just one solution's default, pure/
    seed-time path) with status/why. PURE: a running server may carry MORE bindings (a canvas-added one); this CLI
    only ever sees the one converged default, named so."""
    from cmod.custom import binding as BND
    from cmod.cmod_seed import CMOD_SEED_PAIRS
    if name:
        sols = [name]
    else:
        sols = [r['name'] for r in next((rs for n, _c, rs in CMOD_SEED_PAIRS if n == 'FirmwareSolution'), [])]
    for sol_name in sols:
        b = BND.derive(sol_name, manager=None)
        if b is None:
            print('no FirmwareSolution %r (pol firmware list)' % sol_name)
            continue
        print('%-28s board=%-16s default=%-5s [%s] %d/%d met' % (b['name'], b['board'], b['is_default'], b['status'],
                                                                   b['requirements_met'], b['requirements_total']))
        if b['why']:
            print('  why: %s' % b['why'])
    print('(PURE/seed-time: a running server may carry more bindings — GET /api/firmware/bindings lists them all)')
    return 0


def _bind(name, board):
    """ucd-0b2b: `pol firmware bind <solution> --board <board>` — a dry-run PREVIEW of a new HardwareBinding (never
    persisted; a running server's POST /api/firmware/solutions/{name}/bindings does the real create)."""
    from cmod.custom import binding as BND
    if _solution(name) is None:
        print('no FirmwareSolution %r (pol firmware list)' % name)
        return 2
    if not board:
        print('usage: pol firmware bind <solution> --board <board>')
        return 2
    b = BND.create(name, board, manager=None)
    print('%s [%s] %d/%d requirement(s) met' % (b['name'], b['status'], b['requirements_met'], b['requirements_total']))
    if b['why']:
        print('  why: %s' % b['why'])
    print('(dry run — PURE preview, not persisted; against a RUNNING server use '
          'POST /api/firmware/solutions/%s/bindings {"board": %r})' % (name, board))
    return 0


def main(argv):
    import argparse
    ap = argparse.ArgumentParser(prog='pol firmware')
    ap.add_argument('verb', choices=('list', 'show', 'validate', 'build', 'run', 'assign', 'export', 'claims', 'bindings', 'bind'))
    ap.add_argument('--target', dest='target_kind', default='both', choices=('both', 'board', 'twin'))   # export
    ap.add_argument('--form', default='source-dir', choices=('source-dir', 'install-bundle', 'solution'))   # export
    ap.add_argument('--out', default=None)        # export: the directory to write under (default module_home('exp'))
    ap.add_argument('--verify', action='store_true')   # export: run the exported CMake build on the engines rung + compare shas
    ap.add_argument('--json', action='store_true')
    ap.add_argument('target', nargs='?', default='')
    ap.add_argument('--mode', default='digital-twin')
    ap.add_argument('--task', default='')
    ap.add_argument('--port', default='')
    ap.add_argument('--pin', default='')
    ap.add_argument('--board', default='')   # bind: the board a new HardwareBinding lays the solution over
    a = ap.parse_args(argv)
    if a.verb == 'list':
        return _list()
    if a.verb == 'bindings':
        return _bindings(a.target)
    if not a.target:
        print('usage: pol firmware %s <solution>   (pol firmware list)' % a.verb)
        return 2
    return {'export': lambda: _export(a.target, a.target_kind, a.out, a.verify, a.json, a.form), 'show': lambda: _show(a.target), 'validate': lambda: _validate(a.target), 'build': lambda: _build(a.target),
            'run': lambda: _run(a.target, a.mode), 'assign': lambda: _assign(a.target, a.task, a.port, a.pin),
            'claims': lambda: _claims(a.target, a.json), 'bind': lambda: _bind(a.target, a.board)}[a.verb]()


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
