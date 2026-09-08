"""agro_forestry_selftest — the legacy example module on the standard
layout: imports, initialize(), the three row classes construct."""
import sys

passed = total = 0


def check(label, cond, extra=''):
    global passed, total
    total += 1
    passed += bool(cond)
    print('  [%s] %s %s' % ('\033[0;32mPASS\033[0m' if cond else '\033[0;31mFAIL\033[0m', label, extra if not cond else ''))


def main():
    import agro_forestry as af
    check('package imports + initialize()', callable(getattr(af, 'initialize', None)))
    from agro_forestry.plant_basis import Plant
    from agro_forestry.gardenBoundary_basis import GardenBoundary
    from agro_forestry.gardenBoundaryPost_basis import GardenBoundaryPost
    ok = True
    for cls in (Plant, GardenBoundary, GardenBoundaryPost):
        try:
            cls(name='selftest-' + cls.__name__)
        except Exception:  # noqa: BLE001
            ok = False
    check('the three row classes construct with defaults', ok)
    check('register + seed hooks are reachable from custom/', callable(getattr(af, 'register_agro_forestry_defaults', None)) and callable(getattr(af, 'seed_initial_data', None)))
    print('\n%d/%d checks passed' % (passed, total))
    return 0 if passed == total else 1


if __name__ == '__main__':
    sys.exit(main())
