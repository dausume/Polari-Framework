"""
@module firmwarefaults.firmwarefaults_seed

THE TAXONOMY AND THE SCENARIOS AS ROWS (FIRMWARE_SCENARIO_PLAN.md §1, §3): one row per fault kind (16, in their kind
classes), the UNO's concurrency primitives (+ the RTOS ones the faults name), the assumptions the UNO firmware makes, the
techniques with their costs, scenario 1 (torn-millis-read) + 1b (rx-ring-over-256) with their steps, and the two
scenario FirmwareVariants (board's class: uno-sim-rig-torn, uno-sim-rig-ring512). Seeds are code-owned (re-seed → the
rows follow), EXCEPT what a run measures: a technique's measured_* cost and a fault's rate / rate_source stay as the
instance has them. ScenarioRun / ScenarioTraceCycle rows are observed, never seeded.
"""
from firmwarefaults.firmwarefaults_basis import (FirmwareFault, ConcurrencyPrimitive, Assumption, Technique, Scenario, ScenarioStep,
                                                 ScenarioRun, ScenarioTraceCycle, ScenarioStatistic, FAULT_KIND_CLASSES,
                                                 ScenarioCampaign, FaultLikelihood, FormalCheck, StaticCheck, StaticFinding)
from firmwarefaults.custom.campaign import seed_rows as campaign_rows
from firmwarefaults.custom.formal import seed_rows as formal_rows
from firmwarefaults.custom.formal_mthread import seed_rows as mthread_rows
from firmwarefaults.custom.fault_rows import by_class
from firmwarefaults.custom.scenarios import SEED_SCENARIOS, SEED_STEPS, scenario_variants
from firmwarefaults.custom.taxonomy import SEED_PRIMITIVES, SEED_ASSUMPTIONS, SEED_TECHNIQUES

_MEASURED_TECHNIQUE = ('measured_cost_bytes', 'measured_cost_cycles', 'measured_latency_delta_cycles', 'measured_by_run', 'measured_ram_bytes',
                       'measured_cost_what')
_MEASURED_FAULT = ('rate', 'rate_source')
#: sc-2 / sc-2b: what a campaign / a formal check RUN writes stays as the instance has it (the definition converges)
_MEASURED_CAMPAIGN = ('status', 'results_json', 'likelihood_summary', 'ttff_summary', 'statistics_json', 'runs', 'wall_s', 'harness_digest',
                      'repro_json', 'ran_at', 'seeds', 'rates_json')
_MEASURED_FORMAL = ('build_name', 'engine_version', 'engine_where', 'outcome', 'claim_status', 'verdict_raw', 'outcome_words', 'properties_json',
                    'failed_property', 'counterexample_json', 'trace_sha256', 'trace_steps', 'source_sha256', 'harness_sha256', 'wall_s', 'cpu_s',
                    'peak_rss_mb', 'claim', 'repro_json', 'ran_at')


def _owned(rows, keep=()):
    """Code-owned fields converge on re-seed; `keep` stays as the instance has it (what a run measured)."""
    return [dict(r, _converge=[k for k in r if k != 'name' and k not in keep]) for r in rows]


SEED_FAULT_ROWS_BY_CLASS = by_class()
SEED_SCENARIO_VARIANTS = scenario_variants()

FIRMWAREFAULTS_SEED_PAIRS = [
    ('ConcurrencyPrimitive', ConcurrencyPrimitive, _owned(SEED_PRIMITIVES)),
    ('Assumption', Assumption, _owned(SEED_ASSUMPTIONS)),
    ('Technique', Technique, _owned(SEED_TECHNIQUES, keep=_MEASURED_TECHNIQUE)),
    ('FirmwareFault', FirmwareFault, []),   # the base: every seeded fault lives in its kind class
] + [(c.__name__, c, _owned(SEED_FAULT_ROWS_BY_CLASS.get(c.__name__, []), keep=_MEASURED_FAULT)) for c in FAULT_KIND_CLASSES] + [
    ('Scenario', Scenario, _owned(SEED_SCENARIOS)),
    ('ScenarioStep', ScenarioStep, _owned(SEED_STEPS)),
    ('ScenarioRun', ScenarioRun, []),
    ('ScenarioTraceCycle', ScenarioTraceCycle, []),
    ('ScenarioStatistic', ScenarioStatistic, []),
    ('ScenarioCampaign', ScenarioCampaign, _owned(campaign_rows(), keep=_MEASURED_CAMPAIGN)),
    ('FaultLikelihood', FaultLikelihood, []),
    ('FormalCheck', FormalCheck, _owned(formal_rows() + mthread_rows(), keep=_MEASURED_FORMAL)),
    ('StaticCheck', StaticCheck, []),
    ('StaticFinding', StaticFinding, []),
]

def _module_on():
    """The class gate keys off each row's CLASS, and FirmwareVariant is board's — so an instance that runs board WITHOUT this
    module would still get the two scenario variants. Seed them only where firmwarefaults itself is enabled."""
    try:
        from polariApiServer.module_gating import module_enabled
        return module_enabled('firmwarefaults')
    except Exception:  # pragma: no cover — no gating module (a bare selftest): seed
        return True


try:   # the two scenario variants are board's FirmwareVariant rows — seeded only with board present (required) and this module on
    from board.board_basis import FirmwareVariant
    if _module_on():
        FIRMWAREFAULTS_SEED_PAIRS.append(('FirmwareVariant', FirmwareVariant, _owned(SEED_SCENARIO_VARIANTS)))
except Exception:  # pragma: no cover
    pass
