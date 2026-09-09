# Scoring (`scoring`)

Context-based scoring engine + epistemics stack (terms, proofs, credibility, authority).

**Kind:** polari-app · **agent tier:** member · **requires:** nothing

## Objects

`AccuracyPolicy`, `AgreementPolicy`, `AssertionCredibilityVote`, `AssertionValidityVote`, `AuthorityAPI`, `BiasPolicy`, `ClaimAttestation`, `ContextualizedValue`, `Contributor`, `CostCategory`, `CourtCase`, `CredibilityClaim`, `DataGatheringSolution`, `DataManipulationPattern`, `DecisionProcedureEdge`, `EpistemicsAPI`, `EvidencePolicy`, `FactualClaim`, `GroupAuthorityGrant`, `GroupDisplayBallot`, `GroupDisplayVote`, `GroupInstanceBinding`, `InstanceAuthorityGrant`, `LegislationProvision`, `LegislationRecord`, `LegislativeVoteEvent`, `LogicForkBallot`, `LogicForkCriterion`, `LogicForkVote`, `MediaEvidence`, `PolicyDraft`, `PolicyIntent`, `PolicyVote`, `ProofRebuttal`, `ProofVote`, `QualificationRelevanceVote`, `ScoreAssertion`, `ScoreConcept`, `ScoreContext`, `ScoreGroup`, `ScoreSubject`, `ScoreTerm`, `ScoringAPI`, `StanceBasis`, `StepCredibilityAssertion`, `SurvivalCostProfile`, `SystemChoiceInForce`, `TermAvailabilitySignal`, `TermProof`, `TermProposal`, `TermRelationAssertion`, `TermScopeVote`, `VenueActionRecord`, `VenueMismatchPattern`, `WorldviewBallot`, `WorldviewElection`

## Layout (the Standardized Polari App — see modules/README.md for what each entry means)

- **objects** — `objects/agreement_policy/AgreementPolicy.py`, `objects/agreement_policy/_shared.py`, `objects/assertion_credibility/AssertionCredibilityVote.py`, `objects/assertion_credibility/_shared.py`, `objects/assertions/AssertionValidityVote.py`, `objects/assertions/ScoreAssertion.py`, `objects/assertions/_shared.py`, `objects/contributors/Contributor.py`, `objects/contributors/_shared.py`, `objects/court_case/CourtCase.py`, `objects/court_case/_shared.py`, `objects/credibility_bases/ClaimAttestation.py`, … (67 more)
- **basis** — `agreement_policy_basis.py`, `assertion_credibility_basis.py`, `assertions_basis.py`, `contributors_basis.py`, `court_case_basis.py`, `credibility_bases_basis.py`, `data_gathering_basis.py`, `evidence_basis.py`, `group_authority_basis.py`, `group_bias_basis.py`, `group_display_vote_basis.py`, `legislation_basis.py`, … (14 more)
- **api** — `authority_api.py`, `epistemics_api.py`, `scoring_api.py`
- **seed** — `assertion_seed.py`, `dmv_col_seed.py`, `housing_affordability_seed.py`, `scoring_seed.py`
- **custom** — `custom/abstraction.py`, `custom/data_ingestion.py`, `custom/group_aggregation.py`, `custom/policy_scoring.py`, `custom/politician_scoring.py`, `custom/scoring_engine.py`, `custom/specificity.py`, `custom/timeframes.py`
- **selftests** — `assertion_credibility_selftest.py`, `assertions_selftest.py`, `bias_selftest.py`, `court_case_selftest.py`, `credibility_bases_selftest.py`, `data_gathering_selftest.py`, `dmv_col_selftest.py`, `elections_selftest.py`, `group_authority_selftest.py`, `group_display_vote_selftest.py`, `housing_context_tree_selftest.py`, `legislation_selftest.py`, … (11 more)

`polari-app.json` is the manifest the core reads; `objects/` holds one class per file; `custom/` holds code that fits no concept file.

## Selftest

```
pol modules selftest scoring        # in the running backend
PYTHONPATH=.:modules python3 -m scoring.assertion_credibility_selftest   # on the host, from polari-framework/
```

Conformance: `pol modules conform scoring`

<!-- generated from polari-app.json by `pol modules manifests readme`; edit freely — the generator never overwrites a README without this marker -->
