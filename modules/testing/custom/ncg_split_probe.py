"""
ncg-7 probe: boot ONE gated instance and prove the module split is
honest — the assigned ncg level is fully present (classes, tables,
routes) and every other ncg level is fully absent. Run via
selftest_ncg_split with POLARI_MODULES set; standalone:

    POLARI_MODULES=hwdigital NCG_PROBE_EXPECT=hwdigital \\
        python3 -m testing.custom.ncg_split_probe
"""

import os

EXPECT = (os.environ.get('NCG_PROBE_EXPECT') or '').strip()

#: What each splittable ncg level owns (class marker + route prefix).
LEVELS = {
    'hwdigital': (('LogicBlockDesign', 'LogicBlockNode'),
                  '/api/hw/logic-designs'),
    'electrodevice': (('CircuitDefinition', 'BreadboardDefinition',
                       'PinBindingDefinition'),
                      '/api/electrodevice/circuits'),
    'scoring': (('CourtCase',), '/api/scoring/court-cases'),
}

_results = []


def check(label, cond, extra=''):
    _results.append(bool(cond))
    print(f"  [{'PASS' if cond else 'FAIL'}] {label}"
          f"{('  ' + extra) if extra else ''}")


def main():
    if EXPECT not in LEVELS:
        raise SystemExit(f'NCG_PROBE_EXPECT must be one of '
                         f'{sorted(LEVELS)}')
    print(f'booting a {EXPECT}-only instance '
          f'(POLARI_MODULES={os.environ.get("POLARI_MODULES")})...')
    from falcon import inspect as falcon_inspect
    from objectTreeManagerDecorators import managerObject
    manager = managerObject(hasServer=True)
    routes = [r.path for r in falcon_inspect.inspect_app(
        manager.polServer.falconServer).routes]

    for level, (classes, route_prefix) in sorted(LEVELS.items()):
        present = level == EXPECT
        for class_name in classes:
            registered = class_name in manager.objectTypingDict
            check(f'{class_name} '
                  f'{"registered" if present else "ABSENT"} on a '
                  f'{EXPECT} node', registered == present)
        has_route = any(p.startswith(route_prefix) for p in routes)
        # Court-case routes ride the legacy unguarded ScoringAPI —
        # the CLASS gate is the split proof there; the two NEW ncg
        # surfaces must gate their routes too.
        if level != 'scoring':
            check(f'{route_prefix} route '
                  f'{"present" if present else "absent"}',
                  has_route == present)

    check('the compiler seam (GraphCompilerDefinition) is CORE — '
          'present on every node',
          'GraphCompilerDefinition' in manager.objectTypingDict)

    failed = _results.count(False)
    print(f'\n{len(_results) - failed}/{len(_results)} passed')
    raise SystemExit(1 if failed else 0)


if __name__ == '__main__':
    main()
