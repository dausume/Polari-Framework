"""
@module polariApiServer.feature_imports

dyn-1 (DYNAMIC_MODULES_PLAN): the guarded feature-import blocks
of polariServer.py as DATA. One entry per original block, in the
original order (a module may have several entries — they merge
at un-stub time). This table is CORE-RESIDENT on purpose: it
describes what to stub when a module's code is ABSENT, so it
cannot live in the module's own directory.

Consumed by moduleService.module_loading.import_feature_blocks
(boot) and unstub_feature_module (live admission, dyn-2/4).
The drift guard (moduleService.selftest_lazy_imports) pins this
file's invariants; extend entries here, never re-inline imports
in polariServer.py.
"""

FEATURE_IMPORT_BLOCKS = (
    # Context-based scoring: the Political Scorecard's term/context/weight
    # system generalized over arbitrary Polari data (scr-1).
    ('scoring', (
        ('scoring.scoring_basis', (
            'ContextualizedValue', 'ScoreContext', 'ScoreSubject',
            'ScoreTerm',
        )),
        ('scoring.score_concept', ('ScoreConcept',)),
        ('scoring.score_group', ('ScoreGroup',)),
        ('scoring.agreement_policy', (
            'AgreementPolicy', 'SEED_AGREEMENT_POLICIES',
        )),
        ('scoring.scoring_seed', (
            'SEED_CONTEXTUALIZED_VALUES', 'SEED_SCORE_CONCEPTS',
            'SEED_SCORE_CONTEXTS', 'SEED_SCORE_GROUPS',
            'SEED_SCORE_SUBJECTS', 'SEED_SCORE_TERMS',
        )),
        # scr-5: assertions bind policy text to concepts; evidence carries
        # graded proof; contributors make individuals/orgs/lobbies trackable
        # (or pseudonymous) accountable identities.
        ('scoring.assertions', ('AssertionValidityVote', 'ScoreAssertion')),
        ('scoring.contributors', ('Contributor', 'SEED_CONTRIBUTORS')),
        ('scoring.evidence', (
            'EvidencePolicy', 'MediaEvidence', 'SEED_EVIDENCE_POLICIES',
        )),
        ('scoring.assertion_seed', (
            'SEED_MEDIA_EVIDENCE', 'SEED_POLICY_SUBJECTS',
            'SEED_SCORE_ASSERTIONS', 'SEED_VALIDITY_VOTES',
        )),
        # scr-6: politician voting records → vote-weighted politician scores.
        ('scoring.policy_votes', (
            'PolicyVote', 'SEED_COHORT_GROUPS', 'SEED_POLICY_VOTES',
            'SEED_POLITICIAN_SUBJECTS',
        )),
        # scr-8: worldview elections → vote-derived group member weights.
        ('scoring.worldview_elections', (
            'SEED_ASSEMBLY_GROUPS', 'SEED_WORLDVIEW_BALLOTS',
            'SEED_WORLDVIEW_ELECTIONS', 'WorldviewBallot',
            'WorldviewElection',
        )),
        # Democratic Scorecard revamp Phase 2: Housing Affordability, the first
        # real (non-demo) Context Tree — mechanism B applied to real content.
        ('scoring.housing_affordability_seed', (
            'SEED_HOUSING_BALLOTS', 'SEED_HOUSING_CONTEXTUALIZED_VALUES',
            'SEED_HOUSING_CONTRIBUTORS', 'SEED_HOUSING_ELECTIONS',
            'SEED_HOUSING_SCORE_CONCEPTS', 'SEED_HOUSING_SCORE_GROUPS',
            'SEED_HOUSING_SCORE_TERMS',
        )),
        # Democratic Scorecard revamp Phase 4: mechanism A (Group Display
        # votes) — vote on which Display best EXPLAINS a score, distinct from
        # mechanism B's vote on term-WEIGHTING worldviews.
        ('scoring.group_display_vote', (
            'GroupDisplayBallot', 'GroupDisplayVote',
            'SEED_GROUP_DISPLAY_BALLOTS', 'SEED_GROUP_DISPLAY_VOTES',
            'SEED_GROUP_DISPLAYS',
        )),
        # Democratic Scorecard revamp mechanism C: logic-fork criterion votes
        # — vote on which alternate criterion a SPECIFIC decision point/fork
        # inside a decision procedure should use, distinct from mechanism A
        # (whole Displays) and mechanism B (whole worldview concepts).
        ('scoring.logic_fork_vote', (
            'DecisionProcedureEdge', 'LogicForkBallot',
            'LogicForkCriterion', 'LogicForkVote',
            'SEED_DECISION_PROCEDURE_EDGES', 'SEED_LOGIC_FORK_BALLOTS',
            'SEED_LOGIC_FORK_CONTRIBUTORS', 'SEED_LOGIC_FORK_CRITERIA',
            'SEED_LOGIC_FORK_VOTES',
        )),
        # System-choice implications: which criterion is actually deployed
        # where over time (SystemChoiceInForce), and evidence-weighted claims
        # that a system choice affects a real-world score (reuses
        # ScoreAssertion unchanged).
        ('scoring.system_choice_implications', (
            'SEED_IMPLICATION_ASSERTIONS',
            'SEED_IMPLICATION_CONTEXTUALIZED_VALUES',
            'SEED_IMPLICATION_SCORE_TERMS', 'SEED_IMPLICATION_SUBJECTS',
            'SEED_IMPLICATION_VALIDITY_VOTES',
            'SEED_INTERPRETATION_BALLOTS',
            'SEED_INTERPRETATION_ELECTIONS',
            'SEED_INTERPRETATION_SCORE_CONCEPTS',
            'SEED_INTERPRETATION_SCORE_GROUPS',
            'SEED_SYSTEM_CHOICES_IN_FORCE', 'SystemChoiceInForce',
        )),
        # Policy drafts scoreable through their lifecycle; venue-mismatch
        # pattern analysis (findings adjudicated by scr-6 validity votes).
        ('scoring.policy_drafts', ('PolicyDraft',)),
        ('scoring.venue_patterns', (
            'SEED_VENUE_PATTERNS', 'VenueActionRecord',
            'VenueMismatchPattern',
        )),
        # Org-defined data-gathering procedures on the graph seam + the
        # step-credibility assertions comparing equivalent terms' methods.
        ('scoring.data_gathering', (
            'DataGatheringSolution', 'StepCredibilityAssertion',
        )),
        # Assertion credibility voting (group + individual units) and
        # drafter-set PolicyIntent (opt-in personal participation).
        ('scoring.assertion_credibility', ('AssertionCredibilityVote',)),
        ('scoring.policy_intent', ('PolicyIntent',)),
        # Term Competition (the PSC termcompetition draft, built): cited
        # composite proposals, relation assertions, scope votes, elections.
        ('scoring.term_competition', (
            'TermProposal', 'TermRelationAssertion', 'TermScopeVote',
        )),
        # Credibility bases: professional/impact/methodological/locality
        # standing per context, attestations, relevance voting, prioritized
        # (never-excluding) stance readings.
        ('scoring.credibility_bases', (
            'ClaimAttestation', 'CredibilityClaim',
            'QualificationRelevanceVote', 'StanceBasis',
        )),
        # Democratic term proofs: rebuttable re-runnable demonstrations,
        # validity + comprehension votes, the manipulation-pattern catalog.
        # (SEED_TERM_PROOFS held back — its demo terms await a demo-content
        # pass; the pattern catalog seeds now.)
        ('scoring.term_proofs', (
            'DataManipulationPattern', 'ProofRebuttal', 'ProofVote',
            'SEED_MANIPULATION_PATTERNS', 'TermProof',
        )),
        # Legislation tracking: who drafted what, who voted, provision-level
        # contributor attribution; official legislative API registrations.
        ('scoring.legislation', (
            'LegislationProvision', 'LegislationRecord',
            'LegislativeVoteEvent',
        )),
    )),
    ('dmvdata', (
        ('dmvdata.legis_sources', (
            'SEED_LEGIS_DOMAINS', 'SEED_LEGIS_ENDPOINTS',
            'SEED_LEGIS_GOV_SOURCES',
        )),
    )),
    # ncg-2: court cases advanced fork-by-fork through compiled no-code
    # graphs (the judicial client of the graph-compiler seam).
    ('scoring', (
        ('scoring.court_case', ('CourtCase',)),
        # Group/instance authority: users hold primary/shared authority over
        # groups + instances; bindings make an instance THE authoritative
        # source for a group (both-sides definition with the PSC); signals
        # are admitted only through the three-check authority verdict.
        ('scoring.group_authority', (
            'GroupAuthorityGrant', 'GroupInstanceBinding',
            'InstanceAuthorityGrant', 'TermAvailabilitySignal',
        )),
    )),
    # AR zone capture (arz-1): 3+ placed points become a volume (prism)
    # or a shape in the air (hull); sites aggregate zones house-wide.
    ('zones', (
        ('zones.zone_basis', (
            'SEED_SITES', 'SEED_ZONE_POINTS', 'SEED_ZONES',
            'SiteDefinition', 'ZoneDefinition', 'ZoneEstimateRecord',
            'ZonePoint',
        )),
    )),
    # ncg-3: digital-logic diagrams as rows -> generated Verilog/bench,
    # iCE40 synthesis target (the hwdigital client of the same seam).
    ('hwdigital', (
        ('hwdigital.logic_basis', (
            'LogicBlockDesign', 'LogicBlockNode', 'SEED_LOGIC_DESIGNS',
            'SEED_LOGIC_NODES',
        )),
    )),
    # ncg-4: circuits as rows -> generated SPICE netlists (the circuit
    # client of the same seam).
    ('electrodevice', (
        ('electrodevice.circuit_basis', (
            'CircuitComponentDefinition', 'CircuitDefinition',
            'CircuitNetDefinition', 'SEED_CIRCUIT_COMPONENTS',
            'SEED_CIRCUIT_NETS', 'SEED_CIRCUITS',
        )),
        # ncg-5: breadboards — placements wired by tie point, jumpers
        # joining boards, boards re-wrappable as components.
        ('electrodevice.breadboard_basis', (
            'BoardJumper', 'BreadboardDefinition', 'ComponentPlacement',
            'SEED_BREADBOARDS', 'SEED_JUMPERS', 'SEED_PLACEMENTS',
        )),
    )),
    # col-1 (DMV cost of living): persona/geography vocabulary, the
    # obscure-factor terms, escape-cost walkthrough categories, and the
    # law-as-data statute values (DMV_COST_OF_LIVING_DATA_PLAN.md).
    ('scoring', (
        ('scoring.dmv_col_seed', (
            'SEED_DMV_GEO_CONTEXTS', 'SEED_DMV_SUBJECTS',
            'SEED_DMV_TERMS', 'SEED_DMV_TIMEFRAMES',
            'SEED_ESCAPE_COST_CATEGORIES', 'SEED_ESCAPE_COST_TERMS',
            'SEED_PERSONA_CONTEXTS', 'SEED_STATUTE_VALUES',
        )),
    )),
    # col-2: the official-source registrations the API profiler ingests
    # from (auth via env knobs only — repos are public).
    ('dmvdata', (
        ('dmvdata.source_seed', ('SEED_API_DOMAINS', 'SEED_API_ENDPOINTS')),
        # GovSource registry: acronym glossary + key requirements +
        # duplication-origin records (retrievals are runtime data, no seeds).
        ('dmvdata.gov_sources', (
            'GovSource', 'SEED_GOV_SOURCES', 'SourceRetrieval',
        )),
        # Cross-validation: independent re-pull confirmations + provider-
        # group reliability terms/concept (weights mechanism-B votable).
        ('dmvdata.cross_validation', (
            'RetrievalConfirmation', 'SEED_PROVIDER_CONCEPT',
            'SEED_PROVIDER_TERMS',
        )),
        # Varying legal source types — nonprofit/company/political-group/
        # individual siblings of GovSource, one cross-type machinery.
        ('dmvdata.legal_sources', (
            'AcademicSource', 'CompanySource', 'IndividualSource',
            'JournalisticSource', 'NonProfitSource',
            'PoliticalGroupSource', 'SEED_COMPANY_SOURCES',
            'SEED_INDIVIDUAL_SOURCES', 'SEED_NONPROFIT_SOURCES',
            'SEED_POLITICAL_SOURCES',
        )),
    )),
    # ncg-6: design-output -> circuit-source bindings, and authorable
    # no-code test cases/packs (the acct-6 seed).
    ('electrodevice', (
        ('electrodevice.level_bridge', (
            'PinBindingDefinition', 'SEED_PIN_BINDINGS',
        )),
    )),
    # scr-15: media outlets held accountable for accuracy to the data.
    ('scoring', (
        ('scoring.media_accuracy', (
            'AccuracyPolicy', 'FactualClaim', 'SEED_ACCURACY_POLICIES',
            'SEED_FACTUAL_CLAIMS', 'SEED_MEDIA_OUTLETS',
        )),
        # scr-16: per-group bias reads (bands are editable rows).
        ('scoring.group_bias', ('BiasPolicy', 'SEED_BIAS_POLICIES')),
        # scr-12a: survival-cost walkthrough (categories ARE the wizard).
        ('scoring.survival_costs', (
            'CostCategory', 'SEED_COST_CATEGORIES', 'SEED_COST_TERMS',
            'SEED_SURVIVAL_PROFILES', 'SurvivalCostProfile',
        )),
    )),
    # Aquaponics module (aqp-1): self-watering pot geometry as first-class
    # objects + waterproof pot materials (ceramic/geopolymer).
    ('aquaponics', (
        ('aquaponics.pot_basis', ('PotDefinition', 'PotHole')),
        ('aquaponics.pot_seed', ('SEED_POTS', 'SEED_POT_HOLES')),
    )),
    # waxprint module (wp-1): pellet-fed auger-screw wax 3D-printer sim —
    # printer assembly + wax feedstock + print condition + device materials,
    # with the two-zone (auger + hotend) melt and wax thermal-safety gate.
    ('waxprint', (
        ('waxprint.waxprint_basis', (
            'DeviceMaterialDefinition', 'PrinterAssemblyDefinition',
            'WaxFeedstockDefinition', 'PrintConditionDefinition',
            'WaxReclaimBatch', 'MoldLifecycleRecord',
        )),
        ('waxprint.waxprint_seed', (
            'SEED_DEVICE_MATERIALS', 'SEED_FEEDSTOCKS',
            'SEED_ASSEMBLIES', 'SEED_CONDITIONS',
            'SEED_WAXPRINT_MODULES',
        )),
        # waxprint sim space (wp-5/wp-6): a registered, 3D-viewable multiscale sim
        # (WaxPrintSimState rows over build height) + condition-evaluation gates.
        # Importing sim_seed appends the scene/bindings/equations/sim-def/runs/msim/
        # ic-picker to the shared framework seed lists (trigger-on-import pattern).
        ('waxprint.sim_state', ('WaxPrintSimState',)),
        ('waxprint', ('sim_seed',)),
        ('waxprint.sim_seed', (
            'SEED_WAXPRINT_STATE_ROWS', 'SEED_WAXPRINT_PAGE_DISPLAYS',
        )),
    )),
    # pspp module (pspp-1): PSPP evidence + claims + digitized-dataset
    # foundation — the one EvidenceMethod vocabulary, claims-not-values
    # rows, and book figures/tables as data read by one generic engine.
    ('pspp', (
        ('pspp.evidence_methods', (
            'EvidenceMethod', 'SEED_EVIDENCE_METHODS',
        )),
        ('pspp.claims', (
            'PropertyClaim', 'StructureClaim', 'ValidationClaim',
        )),
        ('pspp.digitized_datasets', ('DigitizedDataset',)),
        ('pspp.datasets_seed', ('SEED_DIGITIZED_DATASETS',)),
        # pspp-2: the MaterialState DAG + processing-stage vocabulary.
        # MaterialState rows are EARNED (canonical states stay implicit
        # until written — pspp.state_resolution), so only stages seed.
        ('pspp.material_states', (
            'MaterialState', 'ProcessingStage', 'SEED_PROCESSING_STAGES',
        )),
        # pspp-3: structure rows (earned, never seeded) + reaction
        # windows (Ch.8 ranges arrive as cited rows — none hardcoded).
        ('pspp.pages_seed', ('SEED_PSPP_PAGE_DISPLAYS',)),
        ('pspp.material_structure', ('ScaleStructureDefinition',)),
        ('pspp.reaction_windows', (
            'ReactionWindow', 'SEED_REACTION_WINDOWS',
        )),
        # pspp-8: threshold-shaped (banded/asymmetric) windows — p.193
        # graded bands + condition gates the stepping engine enforces.
        ('pspp.threshold_windows', (
            'ThresholdReactionWindow', 'SEED_THRESHOLD_WINDOWS',
        )),
        # pspp-V3: the Ch.8 patent/lab examples as benchmark rows the
        # measured-vs-predicted overlay runs against.
        ('pspp.benchmark_cases', ('BenchmarkCase', 'SEED_BENCHMARK_CASES')),
        # pspp-4: processes as first-class transformations + the reaction
        # network as data (generic reactive-material engine).
        ('pspp.material_processes', (
            'MaterialProcessDefinition', 'MaterialProcessExecution',
            'SEED_PROCESS_DEFINITIONS',
        )),
        ('pspp.cmc_library_seed', (
            'SEED_CMC_PROCESS_DEFINITIONS', 'SEED_CMC_PROCESSING_STAGES',
            'SEED_CMC_PROPERTY_MEANINGS',
        )),
        ('pspp.exposure_scenarios', (
            'ExposureScenario', 'SEED_EXPOSURE_SCENARIOS',
        )),
        ('pspp.performance_scenarios', ('MaterialPerformanceScenario',)),
        ('pspp.scale_transfers', (
            'ScaleTransferDefinition', 'SEED_SCALE_TRANSFERS',
        )),
        ('pspp.reaction_network', (
            'ChemicalSpecies', 'ReactionRule', 'SEED_CHEMICAL_SPECIES',
            'SEED_REACTION_RULES',
        )),
        # mtt-2 sg: the sol-gel LIBRARY — the third swap-the-library
        # proof; rows concatenate into the pspp seeds below.
        ('pspp.solgel_network', (
            'SOLGEL_CHEMICAL_SPECIES', 'SOLGEL_REACTION_RULES',
            'SOLGEL_THRESHOLD_WINDOWS',
        )),
        ('pspp.solgel_process', (
            'SOLGEL_DIGITIZED_DATASETS', 'SOLGEL_PROCESSING_STAGES',
        )),
        # mtt-2 sg-community: precursor sourcing / common-material routes.
        ('pspp.solgel_sourcing', (
            'PrecursorSource', 'SEED_PRECURSOR_SOURCES',
        )),
        # mtt-2 Part B: the ceramic sintering engine's master-curve
        # calibration data (provisional until digitized).
        ('pspp.sintering_seed', ('SEED_SINTERING_DATASETS',)),
        # mtt-2 ceramics: usable samples (local + olivine tracks) + the
        # furnace escalation ladder + the olivine-carbonation dataset.
        ('pspp.ceramics_samples', (
            'CeramicSample', 'SEED_CERAMIC_SAMPLES',
            'SEED_CERAMICS_DATASETS',
        )),
        ('pspp.ceramics_ladder', ('LadderRung', 'SEED_LADDER_RUNGS')),
        # mtt-2 research tools: buildable open-source instruments (the
        # measurement half — FTIR, red-cabbage pH, Brix, spectrometer...).
        ('pspp.research_tools', ('ResearchTool', 'SEED_RESEARCH_TOOLS')),
        # mtt-2 characterization: the FTIR band-calibration data gap.
        ('pspp.characterization', ('SEED_CHARACTERIZATION_DATASETS',)),
        # mtt-2 glass core: viscosity reference points + refinement
        # windows + the devit/viscous-master-curve data asks.
        ('pspp.glass_refinement', (
            'GLASS_DIGITIZED_DATASETS', 'GLASS_THRESHOLD_WINDOWS',
        )),
    )),
    ('aquaponics', (
        ('aquaponics.pot_materials_seed', (
            'SEED_POT_MATERIALS', 'SEED_POT_PROPERTY_MEANINGS',
            'SEED_POT_SCALE_DEFINITIONS',
        )),
        # aqp-2: multiscale soil + water + nutrient profiles.
        ('aquaponics.growth_media', (
            'NutrientProfile', 'NutrientSpecies', 'SoilDefinition',
            'WaterDefinition',
        )),
        ('aquaponics.media_seed', (
            'SEED_NUTRIENT_PROFILES', 'SEED_NUTRIENT_SPECIES',
            'SEED_SOILS', 'SEED_WATERS',
        )),
        # aqp-4: per-part plant profiles (permanent structure + carbon/nutrient
        # capture + CO2/O2 flux).
        ('aquaponics.plant_basis', ('PlantDefinition', 'PlantPart')),
        ('aquaponics.plant_seed', ('SEED_PLANTS', 'SEED_PLANT_PARTS')),
        # aqp-5: full atmospheric conditions + plant<->air gas exchange.
        ('aquaponics.atmosphere_basis', ('AtmosphereDefinition',)),
        ('aquaponics.atmosphere_seed', ('SEED_ATMOSPHERES',)),
        # aqp-6: bound pot systems + environmental-impact/survival synthesis +
        # the scoring bridge (systems ranked through the context-scoring engine).
        ('aquaponics.pot_system', ('PotSystemDefinition',)),
        ('aquaponics.pot_system_seed', (
            'SEED_AQP_CONTEXTUALIZED_VALUES', 'SEED_AQP_SCORE_CONCEPTS',
            'SEED_AQP_SCORE_SUBJECTS', 'SEED_AQP_SCORE_TERMS',
            'SEED_POT_SYSTEMS',
        )),
        # Aquaponics worm-compost enrichment loop (aqp-7).
        ('aquaponics.vermicompost', (
            'CompostBinDefinition', 'CompostLoopDefinition',
            'VermicompostProfile',
        )),
        ('aquaponics.vermicompost_seed', (
            'SEED_COMPOST_BINS', 'SEED_COMPOST_LOOPS',
            'SEED_ENRICH_CONTEXTUALIZED_VALUES',
            'SEED_ENRICH_SCORE_CONCEPTS', 'SEED_ENRICH_SCORE_SUBJECTS',
            'SEED_ENRICH_SCORE_TERMS', 'SEED_VERMICOMPOST_PROFILES',
        )),
        # Aquaponics per-part plant growth / growth-failure (aqp-8).
        ('aquaponics.plant_growth_basis', ('PlantGrowthModel',)),
        ('aquaponics.plant_growth_seed', ('SEED_PLANT_GROWTH_MODELS',)),
    )),
    # Nutrition: dietary-nutrient vocab + person + household profiling
    # (nut-1/3/4).
    ('nutrition', (
        ('nutrition.nutrient_basis', (
            'DietaryNutrient', 'NutrientReference',
        )),
        ('nutrition.nutrient_seed', (
            'SEED_DIETARY_NUTRIENTS', 'SEED_NUTRIENT_REFERENCES',
        )),
        ('nutrition.person_basis', ('PersonProfile',)),
        ('nutrition.household_basis', ('HouseholdProfile',)),
        ('nutrition.person_seed', ('SEED_HOUSEHOLDS', 'SEED_PERSONS')),
        # Nutrition: plant harvest -> meal-nutrient yield (nut-2).
        ('nutrition.food_basis', ('FoodItem', 'NutrientContent')),
        ('nutrition.food_seed', (
            'SEED_FOOD_ITEMS', 'SEED_NUTRIENT_CONTENTS',
        )),
    )),
    # Plant morphology: 3D organ + root stand-in models + confinement
    # (morph-1).
    ('plant_morphology', (
        ('plant_morphology.organ_basis', ('OrganModel', 'RootSystemModel')),
        ('plant_morphology.morphology_seed', (
            'SEED_ORGAN_MODELS', 'SEED_ROOT_MODELS',
        )),
    )),
    # Plant-growth-sim phase 1: per-part normalized-growth instance state
    # (2026-07-15 — the missing "this specific plant, in this pot, this
    # far along" object; see aquaponics/plant_growth_normalized.py).
    ('aquaponics', (
        ('aquaponics.plant_growth_normalized', ('PotPlanting',)),
        ('aquaponics.plant_growth_normalized_seed', ('SEED_POT_PLANTINGS',)),
        # Plant-growth-sim phase 7: stress-type-differentiated response curves
        # (2026-07-15 — see aquaponics/plant_stress.py).
        ('aquaponics.plant_stress', ('StressResponseCurve',)),
        ('aquaponics.plant_stress_seed', ('SEED_STRESS_CURVES',)),
        # Plant-growth-sim phase 8: direct-light field simulation (2026-07-15
        # — see aquaponics/light_field.py).
        ('aquaponics.light_basis', (
            'LightSourceDefinition', 'LightSpectrumDefinition',
        )),
        ('aquaponics.light_seed', (
            'SEED_LIGHT_SOURCES', 'SEED_LIGHT_SPECTRA',
        )),
        # Plant-growth-sim phase 10: water batching + real nutrient uptake
        # (2026-07-15 — see aquaponics/water_batch.py, nutrient_uptake.py).
        ('aquaponics.water_batch', ('WaterBatchSchedule',)),
        ('aquaponics.water_batch_seed', ('SEED_WATER_BATCH_SCHEDULES',)),
    )),
    # Math-defined shapes: quadric/primitive/CSG geometry core (shape-1).
    ('mathshapes', (
        ('mathshapes.shape_basis', ('MathShapeDefinition',)),
        ('mathshapes.shape_seed', ('SEED_MATH_SHAPES',)),
        # Aquaponic tower: vertical stack of math-defined pots (shape-2).
        ('mathshapes.tower_basis', ('AquaponicTowerDefinition',)),
        ('mathshapes.tower_seed', ('SEED_TOWERS',)),
        # CAD import/export via cad-engines worker + MinIO (shape-3).
        ('mathshapes.cad_basis', ('ImportedCadObject',)),
    )),
    # Tanks: freshwater + saltwater ecosystem simulation — alternate
    # nutrient source (tank-1).
    ('tanks', (
        ('tanks.tank_basis', (
            'AquacultureSpecies', 'TankDefinition',
            'TankSubstrateDefinition', 'TankSystemDefinition',
        )),
        ('tanks.tank_seed', (
            'SEED_AQUACULTURE_SPECIES', 'SEED_TANK_SUBSTRATES',
            'SEED_TANK_SYSTEMS', 'SEED_TANKS',
        )),
    )),
    # Microalgae photobioreactors — the decarbonization route, coupled
    # sustainably to aquaponics / tanks / hydroponics (algae-1).
    ('microalgae', (
        ('microalgae.reactor_basis', (
            'AlgaeStrain', 'AlgaeReactorDefinition',
        )),
        ('microalgae.reactor_seed', (
            'SEED_ALGAE_REACTORS', 'SEED_ALGAE_STRAINS',
        )),
        # Integrated excess-source + reactor loops (algae-2).
        ('microalgae.integrated_basis', ('IntegratedLoopDefinition',)),
        ('microalgae.integrated_seed', ('SEED_INTEGRATED_LOOPS',)),
    )),
    # Biomining / bioextraction specialized aquaponic variants (biomine-1).
    ('biomining', (
        ('biomining.biomining_basis', (
            'BioextractionAgent', 'BiomineralProduct',
            'BiomineSystemDefinition',
        )),
        ('biomining.biomining_seed', (
            'SEED_BIOEXTRACTION_AGENTS', 'SEED_BIOMINERAL_PRODUCTS',
            'SEED_BIOMINE_SYSTEMS',
        )),
        # Fully-bio optical-dielectric biomining variants (dielectric-optics-1).
        ('biomining.optical_seed', (
            'SEED_OPTICAL_AGENTS', 'SEED_OPTICAL_BIOMINE_SYSTEMS',
            'SEED_OPTICAL_PRODUCTS',
        )),
    )),
    # Bio ferrous alloys: Ni phytomining + galvanized bio-steel (bio-alloys-1).
    ('biomining', (
        ('biomining.alloy_seed', (
            'SEED_ALLOY_AGENTS', 'SEED_ALLOY_BIOMINE_SYSTEMS',
            'SEED_ALLOY_PRODUCTS',
        )),
    )),
    # Self-hosted video (video-1): WebM/MP4 + optional adaptive HLS.
    ('video', (
        ('video.video_basis', ('VideoAsset',)),
    )),
    # Business ops — setup/upgrade flows, economy track, order planner
    # (biz-1).
    ('bizops', (
        ('bizops.bizops_basis', (
            'BusinessStageDefinition', 'BusinessUpgradeStep',
            'BusinessProfile', 'LocalEconomyMilestone',
            'ProcessWorkflowDefinition', 'ProductOrder',
            'MarketSessionRecord', 'ProductionRunRecord',
            'PartnershipAgreement', 'BusinessRiskNote',
            'ComplianceRequirement', 'ComplianceRecord',
            'QualityCheckDefinition', 'QualityCheckRecord',
        )),
        ('bizops.bizops_seed', (
            'SEED_BUSINESS_STAGES', 'SEED_BUSINESS_UPGRADES',
            'SEED_BUSINESS_PROFILES', 'SEED_ECONOMY_MILESTONES',
            'SEED_PROCESS_WORKFLOWS', 'SEED_RISK_NOTES',
            'SEED_PARTNERSHIPS', 'SEED_COMPLIANCE_REQUIREMENTS',
            'SEED_QUALITY_CHECKS',
        )),
    )),
    # Part composition (arch-2..5): components/interfaces with derived
    # levels, EBOM/MBOM split, routings + promotion, archetypes +
    # design matrices. Seeds are NOT listed in the legacy insert-only
    # pass — composition seeds itself through its arch-1 upsert path
    # (see the seed_composition call in _seedSimSpace3D).
    ('composition', (
        ('composition.archetype_basis', ('PartArchetypeDefinition',)),
        ('composition.component_basis', ('PartComponentDefinition',)),
        ('composition.design_matrix', ('DesignMatrixDefinition',)),
        ('composition.failure_modes', ('FailureModeDefinition',)),
        ('composition.functional_basis', (
            'ConstructionVariantDefinition', 'FunctionalPartDefinition',
        )),
        ('composition.interface_basis', ('InterfaceDefinition',)),
        ('composition.node_basis', ('CompositionNode',)),
        ('composition.routing_basis', (
            'RoutingDefinition', 'RoutingOperation',
        )),
    )),
    # Magnetic materials Section A — option catalog + role taxonomy +
    # powder designer (mag-2/2r/2t).
    ('magnetics', (
        ('magnetics.magnet_basis', (
            'MagneticMaterialOption', 'MagneticPowderDefinition',
            'MaterialUseRole',
        )),
        ('magnetics.magnet_seed', (
            'SEED_MAGNETIC_POWDERS', 'SEED_MATERIAL_OPTIONS',
            'SEED_USE_ROLES',
        )),
        ('magnetics.magnet_circuit_basis', (
            'FluxNodeDefinition', 'MagneticCircuitDefinition',
            'MagneticElementDefinition', 'SEED_FLUX_NODES',
            'SEED_MAGNETIC_CIRCUITS', 'SEED_MAGNETIC_ELEMENTS',
        )),
        ('magnetics.magnet_block_basis', (
            'BlockLayoutDefinition', 'BlockPlacement',
            'BlockSizeVariant', 'JointMortarAssignment',
            'SEED_BLOCK_LAYOUTS', 'SEED_BLOCK_PLACEMENTS',
            'SEED_BLOCK_VARIANTS', 'SEED_JOINT_MORTARS',
        )),
        ('magnetics.field_view_basis', (
            'FieldThresholdBand', 'FieldViewDefinition',
            'FieldViewGroup', 'SEED_FIELD_BANDS', 'SEED_FIELD_GROUPS',
            'SEED_FIELD_VIEWS',
        )),
    )),
    # Electric motors Section C — the M0..M3 ladder of buildable
    # samples (mag-5).
    ('motors', (
        ('motors.motor_basis', (
            'MotorDesignDefinition', 'MotorVerificationRun',
            'SEED_MOTOR_DESIGNS',
        )),
        ('motors.motor_shapes', (
            'SEED_LAVET_PART_SHAPES', 'SEED_LAVET_SIM_SPACES',
            'SEED_LAVET_V2_PART_SHAPES', 'SEED_LAVET_V2_SIM_SPACES',
            'SEED_M1_PART_SHAPES', 'SEED_M1_SIM_SPACES',
            'SEED_M2_PART_SHAPES', 'SEED_M2_SIM_SPACES',
            'SEED_M3_PART_SHAPES', 'SEED_M3_SIM_SPACES',
            'SEED_MOTOR_MATERIALS_3D', 'SEED_MOTOR_PART_SHAPES',
            'SEED_MOTOR_SIM_SPACES',
        )),
        ('motors.motor_parts', ('MotorPartDefinition', 'SEED_MOTOR_PARTS')),
        ('motors.physics_equations', ('SEED_EQUATION_ROWS',)),
        ('motors.motor_drive', (
            'MotorControllerProfile', 'PhaseBindingDefinition',
            'SEED_CONTROLLER_PROFILES', 'SEED_PHASE_BINDINGS',
        )),
        ('motors.scale_goals', ('ClockScaleDefinition', 'MotorGoalSpec')),
        ('motors.clock_views', ('ClockViewDefinition',)),
        ('motors.clock_scene', ('ClockSceneLayerDefinition',)),
        ('motors.m1_positioning', ('PrinterAxisRequirement',)),
        ('motors.m2_lift', ('CrucibleHoistRequirement',)),
    )),
    # mesh-1: license-GATED external mesh catalog + the fit engine
    # (borrowed meshes measured against our vector organ definitions).
    ('meshassets', (
        ('meshassets.mesh_asset_basis', (
            'MeshAssetReference', 'MeshAssetSource', 'OrganMeshChoice',
        )),
        ('meshassets.mesh_asset_seed', (
            'SEED_MESH_ASSETS', 'SEED_MESH_SOURCES',
        )),
    )),
    # Gear trains (gr-1) — the mechanical twin of the reluctance
    # network: shaft nodes as graph nodes, meshes as edges.
    ('gears', (
        ('gears.gear_basis', (
            'GearDefinition', 'GearMeshDefinition',
            'GearTrainDefinition', 'GearTypeDefinition',
            'GearVerificationRun', 'ShaftNodeDefinition',
        )),
        ('gears.gear_seed', (
            'SEED_GEAR_MESHES', 'SEED_GEAR_TRAINS', 'SEED_GEAR_TYPES',
            'SEED_GEARS', 'SEED_SHAFT_NODES',
        )),
    )),
    # Climate Change & Atmosphere (co2-A) — measured series and the
    # spans that cover them, health thresholds WITH their evidence
    # grade, room archetypes, and stored crossing projections.
    ('climate', (
        ('climate.climate_basis', (
            'AtmosphericObservation', 'AtmosphericSeriesDefinition',
            'AmbientSettingProfile', 'AtmosphericTrendFit',
            'BiomarkerCycleObservation', 'CO2HealthThreshold',
            'CarbonSinkSeries', 'ExposureProjection',
            'HealthSymptomDefinition', 'HumanEraDefinition',
            'IndoorSpaceProfile', 'ObservedLevelReference',
            'SymptomOnsetClaim', 'PopulationBiomarkerSeries',
            'SourceCoverageSpan',
        )),
        ('climate.co2_thresholds', ('SEED_CO2_THRESHOLDS',)),
        ('climate.co2_indoor', ('SEED_INDOOR_SPACES',)),
        ('climate.climate_history', ('SEED_HUMAN_ERAS',)),
        ('climate.climate_series', ('SEED_CLIMATE_SERIES',)),
        ('climate.sim_binding', (
            'AtmosphereSeriesBinding', 'SEED_ATMOSPHERE_BINDINGS',
        )),
        ('climate.climate_compress', ('SeriesCompressionRecord',)),
    )),
    # Odoo ERP connector — instance configs + sim/ops write guards (od-3).
    ('odooconnect', (
        ('odooconnect.odoo_basis', ('OdooInstanceConfig',)),
        ('odooconnect.odoo_bindings', (
            'OdooModelBinding', 'OdooSyncReceipt', 'SEED_ODOO_BINDINGS',
        )),
        ('odooconnect.odoo_scenarios', (
            'BusinessScenarioDefinition', 'SEED_BUSINESS_SCENARIOS',
        )),
        ('odooconnect.odoo_seed', ('SEED_ODOO_INSTANCES',)),
    )),
    # Bio wax sources (wax-1) + the unifying supply-chain ledger (chain-1).
    ('waxsupply', (
        ('waxsupply.wax_basis', ('WaxSourceDefinition',)),
        ('waxsupply.wax_seed', ('SEED_WAX_SOURCES',)),
    )),
    # Casting molds (cast-1): the inversion primitive — molds DERIVED as
    # negatives of math-defined parts (WAX_MOLD_NESTING_PLAN).
    ('casting', (
        ('casting.casting_basis', (
            'CastingMaterialThermalProfile', 'MasterFeedstockDefinition',
            'MoldDefinition',
        )),
        ('casting.fill_sim', ('MoldFillSimState',)),
        ('casting.interventions', ('FillInterventionDefinition',)),
        ('casting.demold', ('DemoldPlanDefinition',)),
        ('casting.coatings', ('CastingRunRecord', 'MoldCoatingDefinition')),
        ('casting.nesting_wizard', ('NestingPlanDefinition',)),
        # trigger-on-import: registers the mold-fill scene/binding/sim
        # into the shared seed lists (the waxprint sim_seed pattern).
        ('casting.sim_seed', ('SEED_CASTING_PAGE_DISPLAYS',)),
        ('casting.chain_basis', (
            'CastingStageDefinition', 'MoldNestingChain',
        )),
        ('casting.sprue_basis', (
            'SprueSetInstance', 'SprueStrategyDefinition',
        )),
        ('casting.casting_seed', ('SEED_CASTING_MODULES', 'seed_casting')),
    )),
    ('supplychain', (
        ('supplychain.chain_basis', (
            'SupplyChainDefinition', 'SupplyFlow', 'SupplyNode',
        )),
        ('supplychain.chain_seed', (
            'SEED_SUPPLY_CHAINS', 'SEED_SUPPLY_FLOWS',
            'SEED_SUPPLY_NODES',
        )),
        ('supplychain.sourcing_basis', (
            'PriceCitation', 'ProductFormula', 'ProductInputRequirement',
            'SourcePreferencePolicy', 'SupplySourceProfile',
        )),
        ('supplychain.sourcing_seed', (
            'SEED_PRICE_CITATIONS', 'SEED_PRODUCT_FORMULAS',
            'SEED_PRODUCT_REQUIREMENTS', 'SEED_SOURCE_POLICIES',
            'SEED_SUPPLY_SOURCES',
        )),
    )),
    # tt-12: Polari-Apps — module configurations per use-case; plans are
    # exportable JSON packages the pol CLI deploys (rows only).
    ('polariapps', (
        ('polariapps.apps_basis', (
            'AppDeploymentPlan', 'PolariAppDefinition',
        )),
        ('polariapps.apps_seed', ('SEED_POLARI_APPS',)),
        # sep-7: per-app permission profiles (KC groups grant them).
        ('polariapps.apps_permissions', (
            'AppPermissionProfile', 'SEED_PERMISSION_PROFILES',
        )),
    )),
    # appstore-1: the Polari App Store — downloadable native shells over
    # the polariapps content layer (one-time enrollment tokens hashed at
    # rest, overlaid Gradle source archives, prebuilt binaries in MinIO).
    ('appstore', (
        ('appstore.appstore_basis', (
            'AppEdgeBehavior', 'AppShellDefinition', 'ShellArtifact',
            'ShellEnrollment', 'ShellInstallation',
        )),
        # ai-0: AI tools as first-class store citizens.
        ('appstore.appstore_ai', ('AiToolDefinition',)),
        # ai-7: remote-hosting suggestions with DATED prices.
        ('appstore.appstore_hosting', ('RemoteHostingOption',
                                       'SEED_REMOTE_HOSTING')),
        # ai-9: the fork-pin ledger (self-host software half).
        ('appstore.appstore_forks', ('ForkPin',
                                     'SEED_FORK_PINS')),
        ('appstore.appstore_seed', ('SEED_AI_TOOLS',
                                    'SEED_APP_SHELLS',
                                    'SEED_EDGE_BEHAVIORS')),
        ('appstore.appstore_page', ('SEED_APPSTORE_PAGE_DISPLAYS',)),
    )),
    # ai-8: computer parts + builds as tracked data — dated prices,
    # derived build cost, assembly-feasibility checks over declared
    # specs. The appstore's buy-vs-rent advisory reads these ROWS.
    ('computerparts', (
        ('computerparts.parts_basis', (
            'ComputerBuildDefinition', 'ComputerPartDefinition',
        )),
        ('computerparts.parts_seed', (
            'SEED_COMPUTER_BUILDS', 'SEED_COMPUTER_PARTS',
        )),
    )),
    # islemesh (mac-1): the polari-side acceptor for isle-mesh data —
    # devices/uplinks/apps/permits rows are isle's ACCEPTED copy (isle
    # stays authoritative over networking); mock ingests carry a flag
    # real data never does, surfaced as the summary banner.
    ('islemesh', (
        ('islemesh.islemesh_basis', (
            'IsleApp', 'IsleAppService', 'IsleCatalogEntry',
            'IsleDevice', 'IsleEngine', 'IsleIngestReceipt',
            'IsleProtocolPermit', 'IsleUplink', 'MeshAppRealization',
        )),
        ('islemesh.islemesh_catalog', ('SEED_CATALOG',)),
        ('islemesh.islemesh_page', ('SEED_ISLEMESH_PAGE_DISPLAYS',)),
    )),
    # Tech tree (tt-3): technologies with theory/real/business/politics
    # segments; completion always DERIVED (techtree_analysis), edges
    # derived from depends_on_json with tt-1 transient designation.
    ('techtree', (
        ('techtree.techtree_basis', (
            'TechDependencyEdge', 'TechNode', 'TechSegment',
            'TechSegmentAssignment', 'TechTreeDefinition',
        )),
        ('techtree.techtree_content', (
            'BusinessModelDefinition', 'BusinessOutcome',
            'PolicyDefinition', 'RealArtifact',
        )),
        ('techtree.techtree_seed', (
            'SEED_BUSINESS_MODELS', 'SEED_OSEB_POLARI_MODULES',
            'SEED_POLICY_DEFINITIONS', 'SEED_REAL_ARTIFACTS',
            'SEED_TECH_NODES', 'SEED_TECH_SEGMENT_ASSIGNMENTS',
            'SEED_TECH_TREE_DEFINITIONS',
        )),
    )),
    # Testing accountability spine (acct-0): checks as tree objects.
    # TEST-BUILD ONLY — `testing` is an OPT_IN package (module_gating),
    # so these classes register/seed only under POLARI_TEST_BUILD or an
    # explicit POLARI_MODULES entry; import alone registers nothing.
    ('testing', (
        ('testing.capability_basis', ('CapabilityCheck', 'CheckRun')),
        ('testing.testing_seed', ('SEED_CAPABILITY_CHECKS',)),
    )),
    # gRPC contracts (grpc-1): per-class exposure KNOB + append-only
    # contract versions, generated from stabilization snapshots only.
    ('grpcbridge', (
        ('grpcbridge.contract_basis', (
            'GrpcExposure', 'ProtoContractVersion',
        )),
        # Polari Hardware Bridge (grpc-j1): generatable Java bridge apps —
        # simulation-first, per-bridge knob rows.
        ('grpcbridge.java_bridge_basis', ('HardwareBridgeDefinition',)),
        # hwsim-1: hardware rig digital twins (Renode firmware streams here).
        ('grpcbridge.hwsim_basis', ('SimRigState', 'SEED_SIM_RIGS')),
    )),
    # hwsim-3: FPGA register maps as DATA (every register = a knob row;
    # Verilog/C/testbench artifacts generate FROM the rows).
    ('hwfpga', (
        ('hwfpga.fpga_basis', (
            'FpgaRegisterState', 'RegisterDefinition',
            'RegisterMapDefinition', 'SEED_FPGA_STATES',
            'SEED_REGISTER_MAPS', 'SEED_REGISTERS',
        )),
        # The 4x4 LED demo grid (driver knob: fpga | mcu profiles).
        ('hwfpga.led_basis', ('LedMatrix4x4State', 'SEED_LED_MATRICES')),
    )),
    # Material-derived electronic devices (materials -> SPICE ladder).
    ('electrodevice', (
        ('electrodevice.device_basis', (
            'CircuitRunResult', 'ElectronicDeviceDefinition',
            'SpiceModelCard', 'SEED_DEVICES',
        )),
        ('electrodevice.semiconductor', (
            'SemiconductorProfile', 'SEED_SEMICONDUCTOR_PROFILES',
        )),
        ('electrodevice.device_validator', ('DeviceValidationReport',)),
        ('electrodevice.photo_basis', (
            'PhotoAbsorberDefinition', 'SolarLayerDefinition',
            'SolarStackDefinition', 'SEED_PHOTO_ABSORBERS',
            'SEED_SOLAR_LAYERS', 'SEED_SOLAR_STACKS',
        )),
    )),
    # The aquaponics-pot-shape phase 2 pot-geometry-editor DisplayDefinition page.
    ('aquaponics', (
        ('aquaponics.aquaponics_pages_seed', (
            'SEED_AQUAPONICS_PAGE_DISPLAYS',
        )),
    )),
    # Collaboration sessions (mtg-2): the session row + the durable
    # meeting record. Tokens/capability live in collab_api; nothing
    # arriving over LiveKit mutates Polari state. The second module
    # born manifest-first on the dyn-1 machinery.
    ('collab', (
        ('collab.collab_basis', (
            'CollaborationSession', 'MeetingRecord',
        )),
        # mtg-5: avatars as rows (licence + rig carried on the row;
        # geometry referenced, never inlined).
        ('collab.avatar_basis', (
            'AvatarDefinition', 'SEED_AVATARS',
        )),
    )),
    # Reticulum mesh transport (ret-1): rows are facts ABOUT the mesh;
    # the RNS stack itself lives ONLY in the pol-reticulum sidecar
    # (licence boundary — RETICULUM_LICENCE_GATE.md). Nothing arriving
    # over Reticulum mutates Polari state (ret-8, the LiveKit §2 rule
    # inherited verbatim). Third module born manifest-first on dyn-1.
    ('reticulum', (
        ('reticulum.reticulum_basis', (
            'ReticulumIdentity', 'ReticulumDestination',
            'ReticulumInterface', 'TransportBinding',
            'LinkMeasurement', 'AirtimeBudget',
            'SEED_RNS_INTERFACES',
        )),
        # `.arch` — the archipelago: named nodes, GRADED trust,
        # measured reachability (§5c).
        ('reticulum.arch_basis', (
            'ArchipelagoNode', 'ArchipelagoTrust',
        )),
        # parent+child state replication; keyframes mandatory (§5f).
        ('reticulum.replication_basis', (
            'WatchedObject', 'ObjectStateVersion', 'StateConflict',
        )),
        # operator assertions + attached devices (§5g/§5i).
        ('reticulum.operator_basis', (
            'OperatorLicense', 'DeviceLink',
        )),
        # the device CATALOG: what a KIND of device is — vendor/OEM
        # lineage, openness, interop limits, restrictions, setup
        # steps — each fact with evidence (Dustin 2026-08-13).
        ('reticulum.device_catalog_basis', (
            'DeviceModel', 'SEED_DEVICE_MODELS',
        )),
        # the app access LADDER: isle → arch → open-sea; lighthouses
        # + pseudonymous consumers (ret-1c, DECIDED row 20).
        ('reticulum.meshapp_basis', (
            'AppArchExposure', 'MeshAppRelay', 'MeshConsumer',
            'KitProfile', 'SEED_KIT_PROFILES',
        )),
        # per-app data rules: submission caps, strict typing,
        # ballot-box dedupe; caught garbage is QUARANTINED evidence.
        ('reticulum.datarule_basis', (
            'AppDataRule', 'QuarantinedSubmission',
        )),
        # peer discovery: heard broadcasts adjudicated into .arch
        # (ours) or .mesh (the wider mesh) by a named human (ret-1d).
        ('reticulum.discovery_basis', (
            'PeerSighting',
        )),
        # mesh planning simulator (ret-1e, §5p): flat-terrain math
        # with a LOUD disclaimer; elevation deliberately deferred.
        ('reticulum.meshsim_basis', (
            'MeshSimScenario', 'MeshSimNode', 'MeshSimResult',
        )),
    )),
)
