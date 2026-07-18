"""
The pinned NORMAL-BUILD ABSENCE assert (acct-0 acceptance, Dustin
non-negotiable #1): a normal build — no POLARI_TEST_BUILD, testing
absent from POLARI_MODULES — carries ZERO test machinery. No
CapabilityCheck/CheckRun classes registered, no tables, no CRUDE
surface, no /api/accountability route.

Run from polari-framework/ (the matrix runs it with a scrubbed env;
running it by hand in a test-build shell would honestly FAIL):
    python3 -m testing.absence_probe
"""

import os

# Scrub BEFORE any framework import — gating reads env at boot.
os.environ.pop('POLARI_TEST_BUILD', None)
os.environ.pop('POLARI_MODULES', None)

_results = []


def check(label, cond, extra=''):
    _results.append(bool(cond))
    print(f"  [{'PASS' if cond else 'FAIL'}] {label}"
          f"{('  ' + extra) if extra else ''}")


def main():
    from polariApiServer.module_gating import module_enabled
    check('gating: testing module disabled in a normal build',
          not module_enabled('testing'))

    print('booting a NORMAL in-process server (no test knobs)...')
    from falcon import inspect as falcon_inspect

    from objectTreeManagerDecorators import managerObject
    manager = managerObject(hasServer=True)

    for class_name in ('CapabilityCheck', 'CheckRun'):
        check(f'{class_name} not in objectTypingDict',
              class_name not in manager.objectTypingDict)
        check(f'{class_name} has no object table rows',
              not (manager.objectTables.get(class_name) or {}))

    routes = [r.path for r in falcon_inspect.inspect_app(
        manager.polServer.falconServer).routes]
    check('no /api/accountability route',
          not any(p.startswith('/api/accountability')
                  for p in routes))
    check('no /api/testing route (lease handle is test-build-only)',
          not any(p.startswith('/api/testing') for p in routes))
    check('no CapabilityCheck CRUDE route',
          not any('CapabilityCheck' in p for p in routes))
    check('testing classes absent from defClassList',
          not any(c.__name__ in ('CapabilityCheck', 'CheckRun')
                  for c in manager.polServer.defClassList))

    failed = _results.count(False)
    print(f'\n{len(_results) - failed}/{len(_results)} passed')
    raise SystemExit(1 if failed else 0)


if __name__ == '__main__':
    main()
