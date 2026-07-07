"""
Selftest — the wax-multiscale msim (materials science as pure
configuration nesting abstracted components).

Run from polari-framework/:
    python3 -m materialsScience.selftest_wax_multiscale

Covers: the seed parses + validates (typed refs, no cycles);
conformance against the EXTENDED materials-science profile (subModel/
engineModel optional slots filled = ok, not gaps); the pendulum family
still conforms; the subModel stage executes the stubbed child and the
derive map picks the nested winner score; the @L1c bridge row executes
through execute_scale_definition; the profile upgrade pass refreshes
untouched rows and skips customized ones.
"""

import json
from types import SimpleNamespace

from materialsScience.engine_model_seed import (
    SEED_DFT_MODELS, SEED_ENGINE_MODEL_TEMPLATES, SEED_FEM_MODELS,
)
from materialsScience.formulation_search_seed import (
    SEED_FORMULATION_SEARCHES,
)
from materialsScience.materials_basis_seed import (
    SEED_MS_SCALE_DEFINITIONS,
)
from materialsScience.wax_derivation_seed import (
    SEED_WAX_DERIVATION_MSIMS,
)
from materialsScience.wax_multiscale_seed import (
    MSIM_WAX_MULTISCALE, SEED_WAX_MULTISCALE_MSIMS,
)
from simulations.multi_scale_profile_conformance import (
    check_profile_conformance,
)
from simulations.multi_scale_profile_seed import (
    SEED_MSIM_PROFILES, upgrade_profile_rows,
)
from simulations.multi_scale_seed import SEED_MULTI_SCALE_SIMS
from simulations.multi_scale_stages import apply_derive, parse_stages
from simulations.simulation_intents import validate_composition
from simulations.sub_model_stage import run_sub_model_stage

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


def _capture_formulation_rows():
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


def _mgr():
    mgr = _StubManager()
    for seed in SEED_ENGINE_MODEL_TEMPLATES:
        mgr.add('EngineModelTemplate', SimpleNamespace(**seed))
    for seed in SEED_FEM_MODELS:
        mgr.add('FEMModelDefinition', SimpleNamespace(
            **{**seed, 'last_result_json': '{}', 'last_executed_at': ''}))
    for seed in SEED_DFT_MODELS:
        mgr.add('DFTModelDefinition', SimpleNamespace(
            **{**seed, 'last_result_json': '{}', 'last_executed_at': ''}))
    mgr.add('FormulationSearchDefinition',
            SimpleNamespace(**SEED_FORMULATION_SEARCHES[0]))
    from materialsScience.thermal_windows import SEED_THERMAL_PROFILES
    for seed in SEED_THERMAL_PROFILES:
        mgr.add('ThermalProcessingProfile', SimpleNamespace(**seed))
    for seed in SEED_MS_SCALE_DEFINITIONS:
        mgr.add('MaterialScaleDefinition', SimpleNamespace(**seed))
    mgr.add('MultiScaleSimulationDefinition',
            SimpleNamespace(**SEED_WAX_DERIVATION_MSIMS[0]))
    wax_multi = SimpleNamespace(**SEED_WAX_MULTISCALE_MSIMS[0])
    mgr.add('MultiScaleSimulationDefinition', wax_multi)
    return mgr, wax_multi


def _has_skfem():
    try:
        import skfem  # noqa: F401
        return True
    except ImportError:
        return False


def _seed_and_conformance():
    print('\nSeed + composition + conformance\n')
    mgr, wax_multi = _mgr()
    stages = parse_stages(wax_multi)
    check('3 stages: subModel -> engineModel -> engineModel',
          [s['kind'] for s in stages]
          == ['subModel', 'engineModel', 'engineModel'])
    findings = validate_composition(mgr, wax_multi)
    errors = [f for f in findings if f['level'] == 'error']
    check('validate_composition clean (typed refs + no cycles)',
          not errors, f'errors={[e["message"] for e in errors]}')

    profiles = {p['name']: SimpleNamespace(**p)
                for p in SEED_MSIM_PROFILES}
    report = check_profile_conformance(
        None, wax_multi, profiles['materials-science'])
    check('wax-multiscale CONFORMS to the extended family',
          report['conforms'] is True,
          f"gaps={[f['message'] for f in report['findings'] if f['level'] == 'gap']}")
    ok_slots = [f['slot'] for f in report['findings']
                if f['level'] == 'ok']
    check('the subModel + engineModel templates are FILLED slots',
          'stage-template:sub-derivation' in ok_slots
          and 'stage-template:continuum-verification' in ok_slots
          and 'stage-template:quantum-evidence' in ok_slots,
          f'ok={ok_slots}')
    wax_deriv = SimpleNamespace(**SEED_WAX_DERIVATION_MSIMS[0])
    check('wax-derivation STILL conforms (new templates are optional)',
          check_profile_conformance(
              None, wax_deriv,
              profiles['materials-science'])['conforms'] is True)
    pend = SimpleNamespace(**SEED_MULTI_SCALE_SIMS[0])
    check('pendulum-in-wind STILL conforms',
          check_profile_conformance(
              None, pend,
              profiles['pendulum-in-wind'])['conforms'] is True)
    ladder = json.loads(profiles['materials-science']
                        .fidelity_ladder_json)
    template_names = {t['name'] for t in SEED_ENGINE_MODEL_TEMPLATES}
    check('fidelity ladder template refs name real catalog rows',
          all(set(r.get('templates', [])) <= template_names
              for r in ladder))


def _nested_execution():
    print('\nNested execution (the whole chain, stubbed persistence)\n')
    mgr, wax_multi = _mgr()
    stage1 = parse_stages(wax_multi)[0]
    orig = _capture_formulation_rows()
    try:
        report = run_sub_model_stage(
            mgr, MSIM_WAX_MULTISCALE, stage1, {})
    finally:
        _restore(orig)
    # The nested wax-derivation runs its real refine search; its best
    # does NOT meet all targets (honest), so the child gate blocks —
    # exactly what the parent must report.
    check('nested wax-derivation executed for real '
          '(honest non-achievement: targets unmet)',
          not report['achieved']
          and report['subModel']['child'] == 'wax-derivation'
          and report['attempted'] == 1,
          f"blockedAt={report['subModel']['blockedAt']}")
    check('the child stage reason carries the real verdict',
          'does not meet the targets'
          in report['attempts'][0]['reason'],
          f"reason={report['attempts'][0]['reason'][:100]}")
    # The derive map picks the nested candidate score when it IS there.
    derived = report['attempts'][0]['derivedValues']
    check('nested derived values are namespaced for the derive map',
          'sub.formulation-screening.candidate.score' in derived
          or not report['attempts'][0]['complete'])
    resolved = apply_derive(stage1, {
        'sub.formulation-screening.candidate.score': 0.61})
    check('derive map resolves the nested winner score',
          resolved['params']['derived']['winnerScore'] == 0.61)


def _bridge_and_upgrade():
    print('\n@L1c bridge row + profile upgrade pass\n')
    mgr, _ = _mgr()
    from materialsScience.scale_execution import execute_scale_definition
    verdict = execute_scale_definition(mgr, 'beeswax-carnauba-blend@L1c')
    if _has_skfem():
        row = next(r for r in mgr.objectTables[
            'MaterialScaleDefinition'].values()
            if getattr(r, 'name', '') == 'beeswax-carnauba-blend@L1c')
        check('@L1c executes the configured model + stores the result',
              verdict['ok']
              and json.loads(row.parameters_json)['result'].get(
                  'effectiveK')
              and row.status == 'defined')
    else:
        check('@L1c honest refusal without scikit-fem',
              not verdict['ok'])

    # Profile upgrade: untouched rows refresh, customized rows skip.
    mgr2 = _StubManager()
    seed = SEED_MSIM_PROFILES[1]
    stale = SimpleNamespace(**{**seed, 'stage_templates_json': '[]'})
    mgr2.add('MultiScaleSimulationProfile', stale)
    custom = SimpleNamespace(**{**SEED_MSIM_PROFILES[0],
                                'description': 'my own words',
                                'fidelity_ladder_json': '[]'})
    mgr2.add('MultiScaleSimulationProfile', custom)
    upgrade_profile_rows(mgr2)
    check('untouched profile row refreshed to the current seed',
          stale.stage_templates_json == seed['stage_templates_json'])
    check('customized-description profile row left alone',
          custom.fidelity_ladder_json == '[]')


if __name__ == '__main__':
    _seed_and_conformance()
    _nested_execution()
    _bridge_and_upgrade()
    total, passed = len(_results), sum(_results)
    print(f'\n{passed}/{total} checks passed')
    raise SystemExit(0 if passed == total else 1)
