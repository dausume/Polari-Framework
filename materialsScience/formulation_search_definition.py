"""
@module materialsScience.formulation_search_definition

FormulationSearchDefinition — the OBJECT a wax-derivation search is
configured at ([[object-coherence]]: the capability was previously
API-only knobs on POST /api/msci/composites/search|refine; this row
makes the search itself a configurable member of the object tree, so a
derivation is something you can open, edit, run, and point a
multi-scale stage at).

One row = one named search: what to optimize toward (a legacy
TargetMaterialProfile id or inline targets), over which base material
and additive pool, under which sourcing policy and process gate, in
which mode ('grid' sweeps combinations, 'refine' batch-steps toward the
targets), and with which STAGED-FIDELITY ladder:

`fidelity_stages_json`:
    {"screening": {"engine": "rules-of-mixtures"},
     "verify":    {"engine": "fem.effective-conductivity",
                   "shortlistN": 5, "property": "thermalConductivity",
                   "matrixK": 0.25, "inclusionK": {"<additive>": k},
                   "refine": 5},
     "evidence":  {"engine": "dft.molecular-energy",
                   "onWinnersOnly": true, "autoRun": false}}
Screening always runs (it IS the search). The verify rung runs FEM
homogenization on the top shortlistN candidates — per-candidate honest
refusals when inputs are missing or the engine ladder is down, never
fabricated numbers. The evidence rung NEVER auto-runs (autoRun stays
false per [[knobs-and-suggestions]]): it emits suggestions naming the
winners' level-4 MaterialScaleDefinition rows that
POST /api/msci/scale-definitions/execute can mark as evidence.

`results_keep_top_n` — row-count realism: a grid sweep can evaluate
thousands of candidates; only the top N (plus every winner and every
FEM-shortlist member) persist as FormulationCandidateResult rows. The
full ranked list stays in the returned report; `evaluated` +
`sweep_capped` on the run keep the honest totals.

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - materialsScience.formulation_search_runner (execution)
  - materialsScience.formulation_search_api (HTTP)
  - materialsScience.formulation_search_seed ('wax-derivation-screening')
"""

from objectTreeDecorators import treeObject, treeObjectInit


class FormulationSearchDefinition(treeObject):
    """One configured formulation search (see module docstring).
    Identified by `name`."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        display_name: str = '',
        description: str = '',
        # WHAT to optimize toward: a legacy TargetMaterialProfile id
        # (resolved through the seeded JSON), OR inline PropertyTarget
        # dicts (targets_json non-empty overrides the profile id).
        target_profile_id: str = '',
        targets_json: str = '[]',
        # The base the additives modify. base_properties_json is
        # MANUALLY ENTERED data (echoed into every report's assumptions
        # — nothing is invented).
        base_material_name: str = '',
        base_properties_json: str = '{}',
        # Additive-name filter; empty = the full legacy pool.
        additive_pool_json: str = '[]',
        # 'fossil-free-local' (default; exclusions always named) or
        # 'any' (fossil reference benchmarks opt-in).
        sourcing_policy: str = 'fossil-free-local',
        # 'grid' = combination sweep (search_composites);
        # 'refine' = batch-incremental stepping (refine_formulation).
        mode: str = 'grid',
        # Mode knobs, passed through verbatim: maxAdditives,
        # loadingStep, perAdditiveCap, maxTotalLoad, stopPolicy,
        # continueAfterWinner, maxCandidates, maxBatches,
        # minLoadingStep, start_components.
        knobs_json: str = '{}',
        # Thermal process gate: '' | '3d-print' | 'cnc-machine'
        # (loads ThermalProcessingProfile rows, thermal_windows verdicts).
        process: str = '',
        thermal_knobs_json: str = '{}',
        # The staged-fidelity ladder (see module docstring).
        fidelity_stages_json: str = '{}',
        # Row-count realism knob (see module docstring).
        results_keep_top_n: int = 25,
        enabled: bool = True,
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.description = description
        self.target_profile_id = target_profile_id
        self.targets_json = targets_json
        self.base_material_name = base_material_name
        self.base_properties_json = base_properties_json
        self.additive_pool_json = additive_pool_json
        self.sourcing_policy = sourcing_policy
        self.mode = mode
        self.knobs_json = knobs_json
        self.process = process
        self.thermal_knobs_json = thermal_knobs_json
        self.fidelity_stages_json = fidelity_stages_json
        self.results_keep_top_n = results_keep_top_n
        self.enabled = enabled
