"""
Cross-module seed smoke test.

Auto-discovers every `*_seed.py` in the framework, imports it, and
validates each module-level SEED_* list: importable, non-empty, and —
when the rows carry a 'name' — names are unique and non-blank. This is a
cheap regression net over ALL data modules (aquaponics, nutrition,
materialsScience, tanks, microalgae, biomining, waxsupply, supplychain,
plant_morphology, mathshapes, scoring, …) that catches a malformed or
duplicate seed the moment it lands.

Run (in the backend container):
    python3 -m unittest tests.test_modules_smoke -v
"""

import importlib
import os
import sys
import unittest

_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_TESTS_DIR)          # framework root (…/polari-framework)
sys.path.insert(0, _ROOT)

_SKIP_DIRS = {'.git', '.claude', '__pycache__', 'node_modules', 'tests',
              '.pytest_cache'}

# mp-4: modules/ is a second IMPORT ROOT — its packages import under
# their PLAIN names ('waxprint', never 'modules.waxprint'). Importing
# through the 'modules.' prefix creates a SECOND module object whose
# in-place seed appends run twice (duplicate names). Strip the prefix
# so every module imports exactly once, under its real name.
_MODULES_ROOT = os.path.join(_ROOT, 'modules')
sys.path.insert(0, _MODULES_ROOT)


def _discover_seed_modules():
    """Return dotted module names for every *_seed.py under the root."""
    found = []
    for dirpath, dirnames, filenames in os.walk(_ROOT):
        dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS]
        for fn in filenames:
            if fn.endswith('_seed.py') and fn != '__init__.py':
                base = (_MODULES_ROOT
                        if dirpath.startswith(_MODULES_ROOT) else _ROOT)
                rel = os.path.relpath(os.path.join(dirpath, fn), base)
                dotted = rel[:-3].replace(os.sep, '.')
                found.append(dotted)
    return sorted(set(found))


def _seed_lists(module):
    """Module-level SEED_* attributes that are non-empty lists of dicts."""
    out = {}
    for attr in dir(module):
        if not attr.startswith('SEED_'):
            continue
        value = getattr(module, attr)
        if isinstance(value, list) and value and all(
                isinstance(r, dict) for r in value):
            out[attr] = value
    return out


class SeedModulesSmokeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.modules = _discover_seed_modules()

    def test_discovered_several_seed_modules(self):
        # Sanity: the discovery itself works and finds the data layer.
        self.assertGreaterEqual(len(self.modules), 10,
                                msg=f'only found {self.modules}')

    def test_all_seed_modules_import(self):
        failures = []
        for name in self.modules:
            with self.subTest(module=name):
                try:
                    importlib.import_module(name)
                except Exception as exc:                # noqa: BLE001
                    failures.append(f'{name}: {exc}')
                    self.fail(f'import failed: {exc}')
        self.assertEqual(failures, [])

    def test_seed_lists_well_formed(self):
        checked = 0
        for name in self.modules:
            try:
                module = importlib.import_module(name)
            except Exception:
                continue                                 # covered above
            for attr, rows in _seed_lists(module).items():
                with self.subTest(module=name, seed=attr):
                    checked += 1
                    # if every row is name-keyed, names must be unique + set
                    if all('name' in r for r in rows):
                        names = [r['name'] for r in rows]
                        self.assertTrue(all(names),
                                        f'{name}.{attr} has a blank name')
                        self.assertEqual(
                            len(names), len(set(names)),
                            f'{name}.{attr} has duplicate names')
        self.assertGreater(checked, 0, 'no SEED_* lists validated')


if __name__ == '__main__':
    unittest.main(verbosity=2)
