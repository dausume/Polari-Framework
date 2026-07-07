"""
@module materialsScience.formulation_candidate_result

FormulationCandidateResult — one persisted candidate formulation from a
FormulationSearchRun: its components, predicted properties, score,
violations, thermal verdict, and the per-rung fidelity trail
(screened / FEM-verified / FEM-refused-with-reason / DFT-suggested).

Only the run's top-N candidates (+ every winner and every FEM-shortlist
member) persist — see FormulationSearchDefinition.results_keep_top_n.

`promoted_scale_def` links to the MaterialScaleDefinition L1 row created
when the user EXPLICITLY promotes this candidate (a button, never
automatic — [[knobs-and-suggestions]]); that promotion is the Track C
lineage step: composite winners become scale-definition rows.

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - materialsScience.formulation_search_runner (creates these,
    promotes them)
  - materialsScience.formulation_search_api (lists/promotes)
"""

from objectTreeDecorators import treeObject, treeObjectInit


class FormulationCandidateResult(treeObject):
    """One persisted candidate from a formulation-search run.
    Identified by `name` (`<run>-cand-<rank>`)."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        # The FormulationSearchRun this candidate belongs to.
        run_ref: str = '',
        # 1-based rank in the run's scoring order.
        rank: int = 0,
        # [{"name": "<additive>", "weightPercent": w}, ...]
        components_json: str = '[]',
        predicted_properties_json: str = '{}',
        score: float = 0.0,
        meets_targets: bool = False,
        violations_json: str = '[]',
        # Which target properties the effect data could NOT predict for
        # this candidate (honest display surface).
        unpredicted_json: str = '[]',
        thermal_verdict_json: str = '{}',
        # Per-rung fidelity trail:
        # {"screening": {"status": "scored"},
        #  "femVerify": {"status": "verified"|"refused"|"skipped", ...},
        #  "dftEvidence": {"status": "suggested"|"none", ...}}
        fidelity_json: str = '{}',
        is_winner: bool = False,
        # Set by the explicit promotion knob: the created
        # MaterialScaleDefinition L1 row's name.
        promoted_scale_def: str = '',
        manager=None,
    ):
        self.name = name
        self.run_ref = run_ref
        self.rank = rank
        self.components_json = components_json
        self.predicted_properties_json = predicted_properties_json
        self.score = score
        self.meets_targets = meets_targets
        self.violations_json = violations_json
        self.unpredicted_json = unpredicted_json
        self.thermal_verdict_json = thermal_verdict_json
        self.fidelity_json = fidelity_json
        self.is_winner = is_winner
        self.promoted_scale_def = promoted_scale_def
