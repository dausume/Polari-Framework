"""
Selftest — the wax-derivation msim + the formulationSearch stage kind.

Run from polari-framework/:
    python3 -m materialsScience.selftest_wax_derivation

Covers:
  - the wax-derivation msim seed parses via parse_stages and passes
    validate_composition (the formulationSearchRef candidate-space rule);
  - run_formulation_stage returns the EXACT run_stage_search report
    contract with flat human-readable candidates;
  - evaluate_formulation_gate: honest default without a solutionRef
    (outcome check, reason says so), correct flattened context;
  - profile conformance: wax-derivation × materials-science conforms
    (evidence-attachment optional slot = note, not gap) AND
    pendulum-in-wind still conforms — the generalization proof.
"""

import json
from types import SimpleNamespace

from materialsScience.formulation_stage import (
    evaluate_formulation_gate, run_formulation_stage,
)
from materialsScience.formulation_search_seed import (
    SEED_FORMULATION_SEARCHES,
)
from materialsScience.wax_derivation_seed import (
    MSIM_WAX_DERIVATION, SEED_WAX_DERIVATION_MSIMS,
)
from simulations.multi_scale_profile_conformance import (
    check_profile_conformance,
)
from simulations.multi_scale_profile_seed import SEED_MSIM_PROFILES
from simulations.multi_scale_seed import SEED_MULTI_SCALE_SIMS
from simulations.multi_scale_stages import parse_stages
from simulations.simulation_intents import validate_composition

PASS, FAIL = '\033[0;32mPASS\033[0m', '\033[0;31mFAIL\033[0m'
_results = []

# The run_stage_search report contract keys the frontend consumes.
CONTRACT_KEYS = {'achieved', 'winner', 'winners', 'searchComplete',
                 'exhausted', 'totalCandidates', 'attempted',
                 'advancedThisCall', 'attempts', 'backend', 'warnings',
                 'error'}


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


def _capture_rows():
    import materialsScience.formulation_search_run as run_mod
    import materialsScience.formulation_candidate_result as cand_mod
    orig = (run_mod.FormulationSearchRun,
            cand_mod.FormulationCandidateResult)

    def _factory(class_name):
        def make(manager=None, **fields):
            row = SimpleNamespace(**fields)
            if manager is not None:
                manager.add(class_name, row)
            return row
        return make

    run_mod.FormulationSearchRun = _factory('FormulationSearchRun')
    cand_mod.FormulationCandidateResult = _factory(
        'FormulationCandidateResult')
    return orig


def _restore(orig):
    import materialsScience.formulation_search_run as run_mod
    import materialsScience.formulation_candidate_result as cand_mod
    run_mod.FormulationSearchRun = orig[0]
    cand_mod.FormulationCandidateResult = orig[1]


def _seed_msim():
    print('\nSeed + composition coherence\n')
    msim = SimpleNamespace(**SEED_WAX_DERIVATION_MSIMS[0])
    stages = parse_stages(msim)
    check('seed parses via parse_stages (1 formulationSearch stage)',
          len(stages) == 1 and stages[0]['kind'] == 'formulationSearch'
          and stages[0]['intent'] == 'search')
    check('stage references the seeded search definition',
          stages[0]['formulationSearchRef']
          == SEED_FORMULATION_SEARCHES[0]['name'])
    mgr = _StubManager()   # no SimulationDefinitions needed — no members
    findings = validate_composition(mgr, msim)
    errors = [f for f in findings if f['level'] == 'error']
    check('validate_composition has NO errors '
          '(formulationSearchRef counts as the candidate space)',
          not errors, f'errors={[e["message"] for e in errors]}')
    check('panels: explainer + formulationSearch',
          [p['kind'] for p in json.loads(msim.panels_json)]
          == ['explainer', 'formulationSearch'])
    return msim


def _stage_execution():
    print('\nformulationSearch stage execution (real seeds, stub manager)\n')
    mgr = _StubManager()
    from materialsScience.thermal_windows import SEED_THERMAL_PROFILES
    for seed in SEED_THERMAL_PROFILES:
        mgr.add('ThermalProcessingProfile', SimpleNamespace(**seed))
    mgr.add('FormulationSearchDefinition',
            SimpleNamespace(**SEED_FORMULATION_SEARCHES[0]))
    msim = SimpleNamespace(**SEED_WAX_DERIVATION_MSIMS[0])
    stage = parse_stages(msim)[0]
    orig = _capture_rows()
    try:
        report = run_formulation_stage(
            mgr, MSIM_WAX_DERIVATION, stage, {})
    finally:
        _restore(orig)
    check('report carries the full stage-search contract',
          CONTRACT_KEYS <= set(report), f'missing='
          f'{sorted(CONTRACT_KEYS - set(report))}')
    check('search reports complete + honest achievement',
          report['searchComplete'] is True
          and report['achieved'] == bool(report['winners']))
    attempts = report['attempts']
    check('attempts carry flat human-readable candidates',
          attempts and all(
              isinstance(v, (int, float, str, type(None)))
              for a in attempts for v in a['candidate'].values()),
          f"candidate={attempts[0]['candidate'] if attempts else None}")
    check('candidate keys are named loadings + score',
          attempts and 'score' in attempts[0]['candidate']
          and any(k.endswith('wt%') for k in attempts[0]['candidate']),
          f"keys={sorted(attempts[0]['candidate']) if attempts else []}")
    check('derivedValues flatten candidate.<prop> / thermal.<key> / run.<k>',
          attempts and any(k.startswith('candidate.')
                           for k in attempts[0]['derivedValues'])
          and any(k.startswith('run.')
                  for k in attempts[0]['derivedValues']))
    check('formulation extras ride without breaking the contract',
          set(report.get('formulation', {}))
          >= {'run', 'outcome', 'gapAnalysis', 'trajectory', 'fidelity'})
    check('missing searchRef refuses honestly',
          'formulationSearchRef' in (run_formulation_stage(
              mgr, MSIM_WAX_DERIVATION,
              {'key': 'x', 'kind': 'formulationSearch'}, {})['error']))
    return mgr


def _gate(_unused):
    print('\nFormulation gate (honest default, flattened context)\n')
    mgr = _StubManager()   # fresh — isolation from the execution test
    run_row = SimpleNamespace(name='wax-derivation-screening-run-1',
                              outcome='converged', evaluated=15)
    mgr.add('FormulationSearchRun', run_row)
    mgr.add('FormulationCandidateResult', SimpleNamespace(
        name='wax-derivation-screening-run-1-cand-1',
        run_ref='wax-derivation-screening-run-1', rank=1,
        predicted_properties_json='{"ShoreHardness": 28.75}',
        score=0.61, meets_targets=False,
        components_json='[{"materialId": "additive-rosin", '
                        '"weightPercent": 17.5}]',
        thermal_verdict_json='{"ok": true, "windowC": [150.0, 180.0]}'))
    stage = {'key': 'formulation-screening', 'kind': 'formulationSearch',
             'gate': {'failReason': 'targets unmet'}}
    verdict = evaluate_formulation_gate(mgr, stage, run_row)
    check('no solutionRef → honest outcome-check default',
          verdict['complete'] is False and verdict['hasGate'] is False
          and 'no gate solution configured' in verdict['reason'])
    flat = verdict['derivedValues']
    check('gate context flattens candidate + thermal + run facts',
          flat.get('candidate.ShoreHardness') == 28.75
          and flat.get('thermal.ok') is True
          and flat.get('run.outcome') == 'converged',
          f'keys={sorted(flat)}')
    met_row = SimpleNamespace(name='r2', outcome='met', evaluated=3)
    verdict2 = evaluate_formulation_gate(mgr, stage, met_row)
    check("outcome 'met' completes the default gate",
          verdict2['complete'] is True)


def _conformance():
    print('\nProfile conformance — BOTH families (generalization proof)\n')
    profiles = {p['name']: SimpleNamespace(**p) for p in SEED_MSIM_PROFILES}
    wax = SimpleNamespace(**SEED_WAX_DERIVATION_MSIMS[0])
    report = check_profile_conformance(
        None, wax, profiles['materials-science'])
    check('wax-derivation CONFORMS to materials-science',
          report['conforms'] is True,
          f"gaps={[f['message'] for f in report['findings'] if f['level'] == 'gap']}")
    notes = [f for f in report['findings'] if f['level'] == 'note']
    check('unfilled OPTIONAL slots are notes (evidence stage, graph, '
          'display panels)',
          any('evidence-attachment' in f['slot'] for f in notes),
          f'notes={[f["slot"] for f in notes]}')
    pend = SimpleNamespace(**SEED_MULTI_SCALE_SIMS[0])
    report2 = check_profile_conformance(
        None, pend, profiles['pendulum-in-wind'])
    check('pendulum-in-wind STILL conforms to its family',
          report2['conforms'] is True)


if __name__ == '__main__':
    _seed_msim()
    mgr = _stage_execution()
    _gate(mgr)
    _conformance()
    total, passed = len(_results), sum(_results)
    print(f'\n{passed}/{total} checks passed')
    raise SystemExit(0 if passed == total else 1)
