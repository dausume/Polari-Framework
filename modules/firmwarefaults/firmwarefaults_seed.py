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
                                                 ScenarioRun, ScenarioTraceCycle, FAULT_KIND_CLASSES)
from firmwarefaults.custom.fault_rows import by_class
from firmwarefaults.custom.scenarios import SEED_SCENARIOS, SEED_STEPS, scenario_variants
from firmwarefaults.custom.taxonomy import SEED_PRIMITIVES, SEED_ASSUMPTIONS, SEED_TECHNIQUES

_MEASURED_TECHNIQUE = ('measured_cost_bytes', 'measured_cost_cycles', 'measured_latency_delta_cycles', 'measured_by_run')
_MEASURED_FAULT = ('rate', 'rate_source')


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
