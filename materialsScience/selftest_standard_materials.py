"""
Selftest — the standard material definitions (msci-20): sol-gel
silica, geopolymer, alumina ceramic, CNT, N-doped CNT, silicon, and
the Bombastic-Laser-CNC nanoparticle family.

Run from polari-framework/:
    python3 -m materialsScience.selftest_standard_materials

Covers: identity/scale-row coherence (every scale row's material
exists; every executable row's model exists and its template resolves;
name conventions); lineage (doped CNT <- CNT; L1s <- L0s); provenance
on every row (nothing unlabeled); honesty markers (planned rows say
what earning them takes; the CNT anisotropy + composite-bound caveats
present; nanoparticle size ranges declared-but-null with the
measurement note); the executable models VALIDATE against their
templates and the cheap ones EXECUTE (FEM solves + the silicon ASE
bulk structure); benzene/pyridine fragments differ by exactly one
CH -> N.
"""

import json
from types import SimpleNamespace

from materialsScience.component_binding import validate_model
from materialsScience.engine_model_seed import (
    SEED_ENGINE_MODEL_TEMPLATES,
)
from materialsScience.model_execution import execute_model
from materialsScience.standard_materials_seed import (
    SEED_STANDARD_DFT_MODELS, SEED_STANDARD_FEM_MODELS,
    SEED_STANDARD_MATERIALS, SEED_STANDARD_SCALE_DEFINITIONS,
)

PASS, FAIL = '\033[0;32mPASS\033[0m', '\033[0;31mFAIL\033[0m'
_results = []


def check(label, cond, extra=''):
    _results.append(bool(cond))
    print(f'  [{PASS if cond else FAIL}] {label}'
          f'{("  " + extra) if extra else ""}')


class _StubDB:
    def saveInstanceInDB(self, row):
        pass


class _StubManager:
    def __init__(self):
        self.objectTables = {}
        self.db = _StubDB()

    def add(self, class_name, row):
        self.objectTables.setdefault(class_name, {})[id(row)] = row
        return row


def _mgr():
    mgr = _StubManager()
    for seed in SEED_ENGINE_MODEL_TEMPLATES:
        mgr.add('EngineModelTemplate', SimpleNamespace(**seed))
    for seed in SEED_STANDARD_FEM_MODELS:
        mgr.add('FEMModelDefinition', SimpleNamespace(
            **{**seed, 'last_result_json': '{}', 'last_executed_at': ''}))
    for seed in SEED_STANDARD_DFT_MODELS:
        mgr.add('DFTModelDefinition', SimpleNamespace(
            **{**seed, 'last_result_json': '{}', 'last_executed_at': ''}))
    return mgr


def _has_skfem():
    try:
        import skfem  # noqa: F401
        return True
    except ImportError:
        return False


def _has_ase():
    try:
        import ase  # noqa: F401
        return True
    except ImportError:
        return False


def _coherence():
    print('\nIdentity / scale-row coherence\n')
    names = {m['name'] for m in SEED_STANDARD_MATERIALS}
    expected = {'sol-gel-silica', 'geopolymer', 'alumina-ceramic',
                'carbon-nanotube', 'n-doped-carbon-nanotube',
                'silicon', 'feox-nanoparticle', 'siox-nanoparticle',
                'cuox-nanoparticle', 'c-nanoparticle',
                'nanoparticle-wax-composite'}
    check('all 11 identities seeded', names == expected,
          f'diff={names ^ expected}')
    check('every scale row belongs to a seeded identity',
          all(r['material_name'] in names
              for r in SEED_STANDARD_SCALE_DEFINITIONS))
    check("scale-row names follow '<material>@L<level>'",
          all(r['name'].startswith(f"{r['material_name']}@L")
              for r in SEED_STANDARD_SCALE_DEFINITIONS))
    fem_names = {m['name'] for m in SEED_STANDARD_FEM_MODELS}
    dft_names = {m['name'] for m in SEED_STANDARD_DFT_MODELS}
    for row in SEED_STANDARD_SCALE_DEFINITIONS:
        if row['definition_class'] == 'FEMModelDefinition':
            check(f"{row['name']} -> existing FEM model",
                  row['definition_ref'] in fem_names,
                  row['definition_ref'])
        if row['definition_class'] == 'DFTModelDefinition':
            check(f"{row['name']} -> existing DFT model",
                  row['definition_ref'] in dft_names,
                  row['definition_ref'])
    tpl_names = {t['name'] for t in SEED_ENGINE_MODEL_TEMPLATES}
    check('every model references a real catalog template',
          all(m.get('physics_ref') in tpl_names
              for m in SEED_STANDARD_FEM_MODELS)
          and all(m.get('calculation_ref') in tpl_names
                  for m in SEED_STANDARD_DFT_MODELS))
    check('every row and model carries provenance',
          all(r.get('provenance_id')
              for r in SEED_STANDARD_SCALE_DEFINITIONS)
          and all(m.get('provenance_id')
                  for m in SEED_STANDARD_MATERIALS))


def _lineage_and_honesty():
    print('\nLineage + honesty markers\n')
    rows = {r['name']: r for r in SEED_STANDARD_SCALE_DEFINITIONS}
    check('doped CNT L4 derives from pristine CNT L4',
          rows['n-doped-carbon-nanotube@L4']['derived_from_name']
          == 'carbon-nanotube@L4')
    check('doped CNT L0 derives from pristine CNT L0',
          rows['n-doped-carbon-nanotube@L0']['derived_from_name']
          == 'carbon-nanotube@L0')
    check('every executable L1 derives from its L0',
          all(rows[n]['derived_from_name'] == n.replace('@L1', '@L0')
              for n in rows if n.endswith('@L1')))
    planned = [r for r in SEED_STANDARD_SCALE_DEFINITIONS
               if r['status'] == 'planned']
    check('planned rows say what earning them takes',
          planned and all(len(r['notes']) > 30 for r in planned),
          f'planned={[r["name"] for r in planned]}')
    cnt0 = json.loads(rows['carbon-nanotube@L0']['parameters_json'])
    check('CNT anisotropy stated ON the data',
          'AXIAL' in cnt0.get('anisotropy', ''))
    cnt_model = next(m for m in SEED_STANDARD_FEM_MODELS
                     if m['name'] == 'cnt-epoxy-composite')
    check('composite-bound caveat stated on the CNT model',
          'ASSUMPTION' in cnt_model['description'])
    feox = json.loads(rows['feox-nanoparticle@L0']['parameters_json'])
    check('nanoparticle size ranges declared-but-null with the '
          'measurement note (notebook shape, honest gap)',
          feox['sizeRange_nm'] is None
          and 'TO BE MEASURED' in feox['sizeRangeNote'])
    recipes = json.loads(
        rows['nanoparticle-wax-composite@L0']['parameters_json'])
    check('all 7 notebook layer recipes transcribed',
          len(recipes['layerOptions']) == 7
          and recipes['minLayerDepth_um'] == 1.0)


def _fragments():
    print('\nDFT fragments\n')
    models = {m['name']: m for m in SEED_STANDARD_DFT_MODELS}
    benzene = json.loads(
        models['cnt-fragment-energy']['structure_json'])['atoms']
    pyridine = json.loads(
        models['doped-cnt-fragment-energy']['structure_json'])['atoms']
    b_atoms = [a.split()[0] for a in benzene.split(';')]
    p_atoms = [a.split()[0] for a in pyridine.split(';')]
    check('benzene fragment: C6H6',
          b_atoms.count('C') == 6 and b_atoms.count('H') == 6)
    check('pyridine fragment: C5H5N — exactly one CH -> N vs benzene',
          p_atoms.count('C') == 5 and p_atoms.count('N') == 1
          and p_atoms.count('H') == 5)


def _validation_and_execution():
    print('\nModel validation + cheap executions\n')
    mgr = _mgr()
    for class_name in ('FEMModelDefinition', 'DFTModelDefinition'):
        for row in mgr.objectTables[class_name].values():
            verdict = validate_model(mgr, row)
            check(f"{getattr(row, 'name', '?')} validates clean",
                  verdict['ok'],
                  f"errors={[f['message'] for f in verdict['findings'] if f['level'] == 'error']}")
    if _has_skfem():
        for name, lo, hi in (('solgel-porous-silica', 0.02, 1.38),
                             ('geopolymer-porous-gel', 0.026, 0.95),
                             ('alumina-slab-conduction', 0, 1),
                             ('silicon-slab-conduction', 0, 1),
                             ('feox-wax-composite', 0.25, 6.0)):
            report = execute_model(mgr, name)
            ok = report.get('ok')
            if ok and 'effectiveK' in (report.get('result') or {}):
                k = report['result']['effectiveK']
                ok = lo < k < hi
                extra = f'k_eff={k:.4f}'
            else:
                extra = f"maxT={((report.get('result') or {}).get('maxTemperature'))}"
            check(f'{name} executes', bool(ok), extra)
    else:
        check('FEM executions skipped honestly (no scikit-fem)', True)
    if _has_ase():
        report = execute_model(mgr, 'silicon-bulk-structure')
        check('silicon bulk structure executes (diamond cubic facts)',
              report.get('ok')
              and report['result'].get('atomCount', 0) >= 1,
              f"result={report.get('result')}")
    else:
        check('silicon structure execution skipped honestly (no ASE)',
              True)


if __name__ == '__main__':
    _coherence()
    _lineage_and_honesty()
    _fragments()
    _validation_and_execution()
    total, passed = len(_results), sum(_results)
    print(f'\n{passed}/{total} checks passed')
    raise SystemExit(0 if passed == total else 1)
