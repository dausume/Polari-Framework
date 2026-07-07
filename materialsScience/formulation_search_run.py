"""
@module materialsScience.formulation_search_run

FormulationSearchRun — one execution of a FormulationSearchDefinition,
persisted as an object-tree row so derivation runs are inspectable
(and comparable) after the fact instead of vanishing with the HTTP
response ([[object-coherence]]).

The heavyweight per-candidate results live in their own
FormulationCandidateResult rows (run_ref points back here); this row
carries the run-level story: outcome, honest totals
(evaluated/sweep_capped — the ranked list is trimmed to top-N rows,
the totals are not), the refine trajectory (small: ≤ maxBatches
entries), gap analysis, sourcing exclusions, assumptions, and the
per-rung fidelity summary including honest refusals.

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - materialsScience.formulation_search_runner (creates these)
  - materialsScience.formulation_search_api (lists these)
"""

from objectTreeDecorators import treeObject, treeObjectInit


class FormulationSearchRun(treeObject):
    """One persisted formulation-search execution. Identified by `name`
    (`<search>-run-<k>`, attempt tag included when supplied)."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        # The FormulationSearchDefinition this run executed.
        search_ref: str = '',
        # 'grid' | 'refine' (copied from the definition at run time so
        # the row stays meaningful if the definition is later edited).
        mode: str = '',
        # 'complete' | 'failed' | 'refused'
        status: str = '',
        # grid: 'met' | 'first-winner' | 'exhausted'
        # refine: 'met' | 'converged' | 'batch-limit'
        outcome: str = '',
        # Honest totals (independent of the top-N row trim).
        evaluated: int = 0,
        sweep_capped: bool = False,
        winners_count: int = 0,
        # Echoed manual-entry + prior assumptions (nothing invented).
        assumptions_json: str = '[]',
        # refine mode: per unmet target, delta + which additives move it.
        gap_analysis_json: str = '[]',
        # refine mode: the full named-move batch trajectory (≤ maxBatches).
        trajectory_json: str = '[]',
        # Sourcing policy actually applied + the exclusions it named.
        sourcing_policy: str = '',
        excluded_by_sourcing_json: str = '[]',
        # Which target properties the effect data could predict at all.
        predictable_properties_json: str = '[]',
        # Per-rung fidelity summary incl. honest refusals:
        # {"screening": {...}, "verify": {...}, "evidence": {...}}
        fidelity_summary_json: str = '{}',
        started_at: str = '',
        finished_at: str = '',
        error: str = '',
        manager=None,
    ):
        self.name = name
        self.search_ref = search_ref
        self.mode = mode
        self.status = status
        self.outcome = outcome
        self.evaluated = evaluated
        self.sweep_capped = sweep_capped
        self.winners_count = winners_count
        self.assumptions_json = assumptions_json
        self.gap_analysis_json = gap_analysis_json
        self.trajectory_json = trajectory_json
        self.sourcing_policy = sourcing_policy
        self.excluded_by_sourcing_json = excluded_by_sourcing_json
        self.predictable_properties_json = predictable_properties_json
        self.fidelity_summary_json = fidelity_summary_json
        self.started_at = started_at
        self.finished_at = finished_at
        self.error = error
