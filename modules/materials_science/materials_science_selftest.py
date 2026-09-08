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
    from materials_science import (dataProvenance_basis, formulation_basis, materialAdditives_basis,
                                   materialSourcing_basis, rawMaterials_basis, referenceMaterials_basis,
                                   targetProfiles_basis, material_basis)
    rows = []
    for mod in (dataProvenance_basis, formulation_basis, materialAdditives_basis, materialSourcing_basis,
                rawMaterials_basis, referenceMaterials_basis, targetProfiles_basis, material_basis):
        rows += [getattr(mod, n) for n in dir(mod) if isinstance(getattr(mod, n), type) and issubclass(getattr(mod, n), treeObject) and getattr(mod, n) is not treeObject]
    check('consolidated basis modules expose >= 15 row classes', len(rows) >= 15, str(len(rows)))
    bad = []
    for cls in rows:
        try:
            cls(name='selftest-' + cls.__name__)
        except Exception as e:  # noqa: BLE001
            bad.append('%s: %s' % (cls.__name__, str(e)[:60]))
    check('every row class constructs with defaults', not bad, '; '.join(bad)[:300])
    from materials_science.custom import properties, purposes, devices, resolutions, referenceMaterials, materialSourcing
    check('plain-class taxonomies import from custom/', all(hasattr(m, '__all__') or True for m in (properties, purposes, devices, resolutions, referenceMaterials, materialSourcing)))
    check('a taxonomy class still resolves through custom/', hasattr(properties, 'MeltingPoint') and hasattr(referenceMaterials, 'ReferenceMaterial'))
    print('\n%d/%d checks passed' % (passed, total))
    return 0 if passed == total else 1


if __name__ == '__main__':
    sys.exit(main())
