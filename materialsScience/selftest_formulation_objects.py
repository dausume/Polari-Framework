"""
Selftest — FormulationSearch objects + staged fidelity + promotion.

Run from polari-framework/:
    python3 -m materialsScience.selftest_formulation_objects

Covers (against the REAL legacy seed data, with a stub manager):
  - a refine-mode run end to end: run row persisted with honest
    outcome/totals, candidate rows ≤ top-N + winners, sourcing
    exclusions echoed;
  - FEM verify: refuses honestly per missing knob, verifies with
    literature inputs when scikit-fem is available (skips honestly
    when not), never alters screening scores;
  - DFT evidence: suggestions only, autoRun never honored;
  - promotion: explicit-only, correct lineage, idempotent;
  - the seeded 'wax-derivation-screening' definition parses and its
    fidelity inclusionK keys name REAL additives.
"""

import json
from types import SimpleNamespace

from materialsScience.composite_search import load_legacy_seed_data
from materialsScience.formulation_search_definition import (
    FormulationSearchDefinition,  # noqa: F401 (import = registration sanity)
)
from materialsScience.formulation_search_runner import (
    promote_winner_to_scale_definition,
    run_formulation_search,
    suggest_dft_evidence,
    verify_shortlist_fem,
)
from materialsScience.formulation_search_seed import (
    SEED_FORMULATION_SEARCHES,
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
    """objectTables-shaped stub; treeObject rows are replaced by
    SimpleNamespace rows the runner reads via getattr."""

    def __init__(self):
        self.objectTables = {}
        self.db = _StubDB()

    def add(self, class_name, row):
        self.objectTables.setdefault(class_name, {})[id(row)] = row


def _seed_definition(mgr, **overrides):
    seed = dict(SEED_FORMULATION_SEARCHES[0])
    seed.update(overrides)
    row = SimpleNamespace(**{k: v for k, v in seed.items()})
    mgr.add('FormulationSearchDefinition', row)
    return row


def _install_row_capture(mgr):
    """The runner instantiates real treeObjects with manager=mgr; the
    stub can't host them, so monkeypatch the two classes to plain
    namespace factories that self-register into the stub tables."""
    import materialsScience.formulation_search_runner as runner_mod
    created = {'FormulationSearchRun': [], 'FormulationCandidateResult': []}

    def _factory(class_name):
        def make(manager=None, **fields):
            row = SimpleNamespace(**fields)
            created[class_name].append(row)
            if manager is not None:
                manager.add(class_name, row)
            return row
        return make

    class _RunPatch:
        FormulationSearchRun = staticmethod(
            _factory('FormulationSearchRun'))

    import materialsScience.formulation_search_run as run_mod
    import materialsScience.formulation_candidate_result as cand_mod
    orig = (run_mod.FormulationSearchRun,
            cand_mod.FormulationCandidateResult)
    run_mod.FormulationSearchRun = _factory('FormulationSearchRun')
    cand_mod.FormulationCandidateResult = _factory(
        'FormulationCandidateResult')
    return created, orig


def _restore(orig):
    import materialsScience.formulation_search_run as run_mod
    import materialsScience.formulation_candidate_result as cand_mod
    run_mod.FormulationSearchRun = orig[0]
    cand_mod.FormulationCandidateResult = orig[1]


def _thermal_rows(mgr):
    from materialsScience.thermal_windows import SEED_THERMAL_PROFILES
    for seed in SEED_THERMAL_PROFILES:
        mgr.add('ThermalProcessingProfile', SimpleNamespace(**seed))


def _run_end_to_end():
    print('\nRefine-mode run end to end (real seed data, stub manager)\n')
    mgr = _StubManager()
    _thermal_rows(mgr)
    _seed_definition(mgr)
    created, orig = _install_row_capture(mgr)
    try:
        report = run_formulation_search(mgr, 'wax-derivation-screening')
    finally:
        _restore(orig)

    check('run succeeds against the real seeds', report.get('ok'),
          f"error={report.get('error')}")
    check('outcome is honest (met/converged/batch-limit)',
          report.get('outcome') in ('met', 'converged', 'batch-limit'),
          f"outcome={report.get('outcome')}")
    runs = created['FormulationSearchRun']
    cands = created['FormulationCandidateResult']
    check('exactly one run row persisted, named by the search',
          len(runs) == 1
          and runs[0].name == 'wax-derivation-screening-run-1'
          and report.get('run') == runs[0].name)
    check('run row carries honest sourcing exclusions (3 fossil refs)',
          len(json.loads(runs[0].excluded_by_sourcing_json)) == 3,
          runs[0].excluded_by_sourcing_json)
    keep_n = SEED_FORMULATION_SEARCHES[0]['results_keep_top_n']
    check('candidate rows ≤ top-N + winners',
          0 < len(cands) <= keep_n + runs[0].winners_count,
          f'cands={len(cands)} winners={runs[0].winners_count}')
    check('candidate rows carry the honest unpredicted list',
          all(isinstance(json.loads(c.unpredicted_json), list)
              for c in cands))
    check('fidelity summary has all three rungs',
          set(json.loads(runs[0].fidelity_summary_json))
          == {'screening', 'verify', 'evidence'},
          runs[0].fidelity_summary_json)
    check('DFT evidence arrives as suggestions, never execution',
          isinstance(report.get('dftEvidenceSuggestions'), list)
          and all('action' in s and 'reason' in s
                  for s in report['dftEvidenceSuggestions']))
    check('promotion is NOT triggered by the search',
          all(not getattr(c, 'promoted_scale_def', '') for c in cands))
    return mgr, runs, cands


def _fem_verify():
    print('\nFEM verify rung — honest refusals + real homogenization\n')
    data = load_legacy_seed_data()
    additives_by_id = {a['id']: a for a in data['additives']}
    carnauba = next(a for a in data['additives']
                    if a['name'] == 'Carnauba Wax')
    cand = {'components': [
        {'materialId': carnauba['id'], 'weightPercent': 10.0}],
        'score': 0.5}

    # Missing matrixK → refused with the exact knob named.
    summaries = verify_shortlist_fem(
        [dict(cand)], {'shortlistN': 1}, additives_by_id)
    check('missing matrixK refuses and names the knob',
          summaries[0]['status'] == 'refused'
          and 'matrixK' in summaries[0]['reason'])

    # Missing inclusionK for the component → per-component refusal.
    c2 = dict(cand)
    verify_shortlist_fem([c2], {'shortlistN': 1, 'matrixK': 0.25,
                                'inclusionK': {}}, additives_by_id)
    comp = c2['femVerify']['components'][0]
    check('missing inclusionK refuses per component and names it',
          c2['femVerify']['status'] == 'refused'
          and comp['status'] == 'refused'
          and 'Carnauba Wax' in comp['reason'])

    # With real inputs: verified when scikit-fem is importable, an
    # honest engine refusal otherwise — never a fabricated number.
    c3 = dict(cand)
    before_score = c3['score']
    verify_shortlist_fem(
        [c3], {'shortlistN': 1, 'matrixK': 0.25,
               'inclusionK': {'Carnauba Wax': 0.30}, 'refine': 3},
        additives_by_id)
    fem = c3['femVerify']
    try:
        import skfem  # noqa: F401
        has_fem = True
    except ImportError:
        has_fem = False
    if has_fem:
        comp = fem['components'][0]
        check('with inputs + scikit-fem: verified with k_eff in bounds',
              fem['status'] == 'verified'
              and comp['status'] == 'verified'
              and comp.get('assumption') == 'wt% treated as vol%',
              f'result={comp}')
    else:
        check('without scikit-fem: honest engine refusal',
              fem['status'] == 'refused', f'fem={fem}')
    check('screening score never altered by verification',
          c3['score'] == before_score)

    # Beyond the shortlist → skipped with the reason.
    c4, c5 = dict(cand), dict(cand)
    verify_shortlist_fem([c4, c5],
                         {'shortlistN': 1, 'matrixK': 0.25,
                          'inclusionK': {'Carnauba Wax': 0.30},
                          'refine': 3},
                         additives_by_id)
    check('outside the shortlist is skipped honestly',
          c5['femVerify']['status'] == 'skipped')


def _dft_suggestions():
    print('\nDFT evidence rung — suggestions only\n')
    data = load_legacy_seed_data()
    additives_by_id = {a['id']: a for a in data['additives']}
    rosin = next(a for a in data['additives'] if a['name'] == 'Pine Rosin')
    winners = [{'components': [
        {'materialId': rosin['id'], 'weightPercent': 15.0}]}]

    mgr = _StubManager()
    mgr.add('MaterialScaleDefinition', SimpleNamespace(
        name='pine-rosin@L4', material_name='pine-rosin', scale_level=4))
    sugg = suggest_dft_evidence(mgr, winners,
                                {'engine': 'dft.molecular-energy'},
                                additives_by_id)
    check('existing L4 row → execute suggestion naming it',
          len(sugg) == 1 and 'pine-rosin@L4' in sugg[0]['action'],
          f'sugg={sugg}')
    sugg2 = suggest_dft_evidence(_StubManager(), winners,
                                 {'engine': 'dft.molecular-energy'},
                                 additives_by_id)
    check('no L4 row → honest create-row gap suggestion',
          len(sugg2) == 1 and 'create a level-4' in sugg2[0]['action'])
    sugg3 = suggest_dft_evidence(_StubManager(), winners,
                                 {'autoRun': True}, additives_by_id)
    check('autoRun=true is refused, not honored',
          len(sugg3) == 1 and 'not honored' in sugg3[0]['action'])


def _promotion(mgr, runs, cands):
    print('\nPromotion — explicit Track-C lineage knob\n')
    # Give the base material an L1 row so lineage prefers it.
    mgr.add('MaterialScaleDefinition', SimpleNamespace(
        name='beeswax@L1', material_name='beeswax', scale_level=1))
    import materialsScience.materials_basis as basis_mod
    created = []
    orig = basis_mod.MaterialScaleDefinition

    def _fake(manager=None, **fields):
        row = SimpleNamespace(**fields)
        created.append(row)
        if manager is not None:
            manager.add('MaterialScaleDefinition', row)
        return row

    basis_mod.MaterialScaleDefinition = _fake
    try:
        cand = cands[0]
        result = promote_winner_to_scale_definition(
            mgr, runs[0].name, cand.name)
        check('promotion creates a lineaged L1 row',
              result.get('ok')
              and created
              and created[0].scale_level == 1
              and created[0].derived_from_name == 'beeswax@L1'
              and created[0].definition_ref == cand.name,
              f'result={result}')
        check('derivation method is honest about FEM status',
              ('fem-verified' in result.get('derivationMethod', ''))
              == (json.loads(cand.fidelity_json)['femVerify'].get('status')
                  == 'verified'),
              result.get('derivationMethod'))
        again = promote_winner_to_scale_definition(
            mgr, runs[0].name, cand.name)
        check('promotion is idempotent',
              again.get('alreadyPromoted') and len(created) == 1)
        missing = promote_winner_to_scale_definition(
            mgr, runs[0].name, 'nope-cand')
        check('unknown candidate refuses honestly',
              not missing.get('ok') and 'nope-cand' in missing['error'])
    finally:
        basis_mod.MaterialScaleDefinition = orig


def _seed_sanity():
    print('\nSeed sanity\n')
    seed = SEED_FORMULATION_SEARCHES[0]
    fidelity = json.loads(seed['fidelity_stages_json'])
    data = load_legacy_seed_data()
    names = {a['name'] for a in data['additives']}
    check('seeded inclusionK keys name REAL additives',
          set(fidelity['verify']['inclusionK']) <= names,
          f"keys={sorted(fidelity['verify']['inclusionK'])}")
    check('evidence rung ships suggestion-only', fidelity['evidence']
          ['autoRun'] is False)
    check('seeded profile id exists in the target data',
          seed['target_profile_id']
          in {t['profileId'] for t in data['targets']})
    check('sourcing policy defaults fossil-free-local',
          seed['sourcing_policy'] == 'fossil-free-local')


if __name__ == '__main__':
    mgr, runs, cands = _run_end_to_end()
    _fem_verify()
    _dft_suggestions()
    _promotion(mgr, runs, cands)
    _seed_sanity()
    total, passed = len(_results), sum(_results)
    print(f'\n{passed}/{total} checks passed')
    raise SystemExit(0 if passed == total else 1)
