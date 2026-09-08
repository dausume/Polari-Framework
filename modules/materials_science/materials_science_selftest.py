"""materials_science_selftest — the legacy dynamic module on the standard
layout (sap-2b): the package imports, exposes initialize(), every row
class is a treeObject that constructs with defaults, the consolidated
*_basis modules carry the classes the register expects."""
import sys

passed = total = 0


def check(label, cond, extra=''):
    global passed, total
    total += 1
    passed += bool(cond)
    print('  [%s] %s %s' % ('\033[0;32mPASS\033[0m' if cond else '\033[0;31mFAIL\033[0m', label, extra if not cond else ''))


def main():
    import materials_science as ms
    from objectTreeDecorators import treeObject
    check('package imports + initialize()', callable(getattr(ms, 'initialize', None)))
    from materials_science.objects import (dataProvenance, formulation, materialAdditives,
                                   materialSourcing, rawMaterials, referenceMaterials,
                                   targetProfiles, material)
    rows = []
    for mod in (dataProvenance, formulation, materialAdditives, materialSourcing,
                rawMaterials, referenceMaterials, targetProfiles, material):
        rows += [getattr(mod, n) for n in dir(mod) if isinstance(getattr(mod, n), type) and issubclass(getattr(mod, n), treeObject) and getattr(mod, n) is not treeObject]
    check('consolidated basis modules expose >= 15 row classes', len(rows) >= 15, str(len(rows)))
    bad = []
    for cls in rows:
        try:
            cls(name='selftest-' + cls.__name__)
        except Exception as e:  # noqa: BLE001
            bad.append('%s: %s' % (cls.__name__, str(e)[:60]))
    check('every row class constructs with defaults', not bad, '; '.join(bad)[:300])
    from materials_science.objects import properties, purposes, devices, resolutions
    check("taxonomies import from objects/", all(m is not None for m in (properties, purposes, devices, resolutions)))
    check("a taxonomy class resolves through objects/", hasattr(properties, "MeltingPoint") and hasattr(referenceMaterials, "ReferenceMaterial"))
    print('\n%d/%d checks passed' % (passed, total))
    return 0 if passed == total else 1


if __name__ == '__main__':
    sys.exit(main())
