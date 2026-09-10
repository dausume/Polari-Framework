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
    ('scoring', (
        ('scoring.scoring_basis', (
            'ContextualizedValue', 'ScoreContext', 'ScoreSubject',
            'ScoreTerm',
        )),
        ('scoring.score_concept_basis', (
            'ScoreConcept',
        )),
        ('scoring.score_group_basis', (
            'ScoreGroup',
        )),
        ('scoring.agreement_policy_basis', (
            'AgreementPolicy', 'SEED_AGREEMENT_POLICIES',
        )),
        ('scoring.scoring_seed', (
            'SEED_CONTEXTUALIZED_VALUES', 'SEED_SCORE_CONCEPTS',
            'SEED_SCORE_CONTEXTS', 'SEED_SCORE_GROUPS',
            'SEED_SCORE_SUBJECTS', 'SEED_SCORE_TERMS',
        )),
        ('scoring.assertions_basis', (
            'AssertionValidityVote', 'ScoreAssertion',
        )),
        ('scoring.contributors_basis', (
            'Contributor', 'SEED_CONTRIBUTORS',
        )),
        ('scoring.evidence_basis', (
            'EvidencePolicy', 'MediaEvidence', 'SEED_EVIDENCE_POLICIES',
        )),
        ('scoring.assertion_seed', (
            'SEED_MEDIA_EVIDENCE', 'SEED_POLICY_SUBJECTS',
            'SEED_SCORE_ASSERTIONS', 'SEED_VALIDITY_VOTES',
        )),
        ('scoring.policy_votes_basis', (
            'PolicyVote', 'SEED_COHORT_GROUPS', 'SEED_POLICY_VOTES',
            'SEED_POLITICIAN_SUBJECTS',
        )),
        ('scoring.worldview_elections_basis', (
            'SEED_ASSEMBLY_GROUPS', 'SEED_WORLDVIEW_BALLOTS',
            'SEED_WORLDVIEW_ELECTIONS', 'WorldviewBallot',
            'WorldviewElection',
        )),
        ('scoring.housing_affordability_seed', (
            'SEED_HOUSING_BALLOTS', 'SEED_HOUSING_CONTEXTUALIZED_VALUES',
            'SEED_HOUSING_CONTRIBUTORS', 'SEED_HOUSING_ELECTIONS',
            'SEED_HOUSING_SCORE_CONCEPTS', 'SEED_HOUSING_SCORE_GROUPS',
            'SEED_HOUSING_SCORE_TERMS',
        )),
        ('scoring.group_display_vote_basis', (
            'GroupDisplayBallot', 'GroupDisplayVote',
            'SEED_GROUP_DISPLAY_BALLOTS', 'SEED_GROUP_DISPLAY_VOTES',
            'SEED_GROUP_DISPLAYS',
        )),
        ('scoring.logic_fork_vote_basis', (
            'DecisionProcedureEdge', 'LogicForkBallot',
            'LogicForkCriterion', 'LogicForkVote',
            'SEED_DECISION_PROCEDURE_EDGES', 'SEED_LOGIC_FORK_BALLOTS',
            'SEED_LOGIC_FORK_CONTRIBUTORS', 'SEED_LOGIC_FORK_CRITERIA',
            'SEED_LOGIC_FORK_VOTES',
        )),
        ('scoring.system_choice_implications_basis', (
            'SEED_IMPLICATION_ASSERTIONS',
            'SEED_IMPLICATION_CONTEXTUALIZED_VALUES',
            'SEED_IMPLICATION_SCORE_TERMS', 'SEED_IMPLICATION_SUBJECTS',
            'SEED_IMPLICATION_VALIDITY_VOTES',
            'SEED_INTERPRETATION_BALLOTS', 'SEED_INTERPRETATION_ELECTIONS',
            'SEED_INTERPRETATION_SCORE_CONCEPTS',
            'SEED_INTERPRETATION_SCORE_GROUPS',
            'SEED_SYSTEM_CHOICES_IN_FORCE', 'SystemChoiceInForce',
        )),
        ('scoring.policy_drafts_basis', (
            'PolicyDraft',
        )),
        ('scoring.venue_patterns_basis', (
            'SEED_VENUE_PATTERNS', 'VenueActionRecord',
            'VenueMismatchPattern',
        )),
        ('scoring.data_gathering_basis', (
            'DataGatheringSolution', 'StepCredibilityAssertion',
        )),
        ('scoring.assertion_credibility_basis', (
            'AssertionCredibilityVote',
        )),
        ('scoring.policy_intent_basis', (
            'PolicyIntent',
        )),
        ('scoring.term_competition_basis', (
            'TermProposal', 'TermRelationAssertion', 'TermScopeVote',
        )),
        ('scoring.credibility_bases_basis', (
            'ClaimAttestation', 'CredibilityClaim',
            'QualificationRelevanceVote', 'StanceBasis',
        )),
        ('scoring.term_proofs_basis', (
            'DataManipulationPattern', 'ProofRebuttal', 'ProofVote',
            'SEED_MANIPULATION_PATTERNS', 'TermProof',
        )),
        ('scoring.legislation_basis', (
            'LegislationProvision', 'LegislationRecord',
            'LegislativeVoteEvent',
        )),
    )),
    ('dmvdata', (
        ('dmvdata.legis_sources_seed', (
            'SEED_LEGIS_DOMAINS', 'SEED_LEGIS_ENDPOINTS',
            'SEED_LEGIS_GOV_SOURCES',
        )),
    )),
    ('scoring', (
        ('scoring.court_case_basis', (
            'CourtCase',
        )),
        ('scoring.group_authority_basis', (
            'GroupAuthorityGrant', 'GroupInstanceBinding',
            'InstanceAuthorityGrant', 'TermAvailabilitySignal',
        )),
    )),
    ('zones', (
        ('zones.zone_basis', (
            'SEED_SITES', 'SEED_ZONE_POINTS', 'SEED_ZONES',
            'SiteDefinition', 'ZoneDefinition', 'ZoneEstimateRecord',
            'ZonePoint',
        )),
    )),
    ('hwdigital', (
        ('hwdigital.logic_basis', (
            'LogicBlockDesign', 'LogicBlockNode', 'SEED_LOGIC_DESIGNS',
            'SEED_LOGIC_NODES',
        )),
    )),
    ('electrodevice', (
        ('electrodevice.circuit_basis', (
            'CircuitComponentDefinition', 'CircuitDefinition',
            'CircuitNetDefinition', 'SEED_CIRCUIT_COMPONENTS',
            'SEED_CIRCUIT_NETS', 'SEED_CIRCUITS',
        )),
        ('electrodevice.breadboard_basis', (
            'BoardJumper', 'BreadboardDefinition', 'ComponentPlacement',
            'SEED_BREADBOARDS', 'SEED_JUMPERS', 'SEED_PLACEMENTS',
        )),
    )),
    ('scoring', (
        ('scoring.dmv_col_seed', (
            'SEED_DMV_GEO_CONTEXTS', 'SEED_DMV_SUBJECTS', 'SEED_DMV_TERMS',
            'SEED_DMV_TIMEFRAMES', 'SEED_ESCAPE_COST_CATEGORIES',
            'SEED_ESCAPE_COST_TERMS', 'SEED_PERSONA_CONTEXTS',
            'SEED_STATUTE_VALUES',
        )),
    )),
    ('dmvdata', (
        ('dmvdata.source_seed', (
            'SEED_API_DOMAINS', 'SEED_API_ENDPOINTS',
        )),
        ('dmvdata.gov_sources_basis', (
            'GovSource', 'SEED_GOV_SOURCES', 'SourceRetrieval',
        )),
        ('dmvdata.cross_validation_basis', (
            'RetrievalConfirmation', 'SEED_PROVIDER_CONCEPT',
            'SEED_PROVIDER_TERMS',
        )),
        ('dmvdata.legal_sources_basis', (
            'AcademicSource', 'CompanySource', 'IndividualSource',
            'JournalisticSource', 'NonProfitSource',
            'PoliticalGroupSource', 'SEED_COMPANY_SOURCES',
            'SEED_INDIVIDUAL_SOURCES', 'SEED_NONPROFIT_SOURCES',
            'SEED_POLITICAL_SOURCES',
        )),
    )),
    ('electrodevice', (
        ('electrodevice.level_bridge_basis', (
            'PinBindingDefinition', 'SEED_PIN_BINDINGS',
        )),
    )),
    ('scoring', (
        ('scoring.media_accuracy_basis', (
            'AccuracyPolicy', 'FactualClaim', 'SEED_ACCURACY_POLICIES',
            'SEED_FACTUAL_CLAIMS', 'SEED_MEDIA_OUTLETS',
        )),
        ('scoring.group_bias_basis', (
            'BiasPolicy', 'SEED_BIAS_POLICIES',
        )),
        ('scoring.survival_costs_basis', (
            'CostCategory', 'SEED_COST_CATEGORIES', 'SEED_COST_TERMS',
            'SEED_SURVIVAL_PROFILES', 'SurvivalCostProfile',
        )),
    )),
    ('aquaponics', (
        ('aquaponics.pot_basis', (
            'PotDefinition', 'PotHole',
        )),
        ('aquaponics.pot_seed', (
            'SEED_POTS', 'SEED_POT_HOLES',
        )),
    )),
    ('waxprint', (
        ('waxprint.waxprint_basis', (
            'DeviceMaterialDefinition', 'PrinterAssemblyDefinition',
            'WaxFeedstockDefinition', 'PrintConditionDefinition',
            'WaxReclaimBatch', 'MoldLifecycleRecord',
        )),
        ('waxprint.waxprint_seed', (
            'SEED_DEVICE_MATERIALS', 'SEED_FEEDSTOCKS', 'SEED_ASSEMBLIES',
            'SEED_CONDITIONS', 'SEED_WAXPRINT_MODULES',
        )),
        ('waxprint.sim_state_basis', (
            'WaxPrintSimState',
        )),
        ('waxprint', (
            'sim_seed',
        )),
        ('waxprint.sim_seed', (
            'SEED_WAXPRINT_STATE_ROWS', 'SEED_WAXPRINT_PAGE_DISPLAYS',
        )),
    )),
    ('pspp', (
        ('pspp.evidence_methods_basis', (
            'EvidenceMethod', 'SEED_EVIDENCE_METHODS',
        )),
        ('pspp.claims_basis', (
            'PropertyClaim', 'StructureClaim', 'ValidationClaim',
        )),
        ('pspp.digitized_datasets_basis', (
            'DigitizedDataset',
        )),
        ('pspp.datasets_seed', (
            'SEED_DIGITIZED_DATASETS',
        )),
        ('pspp.material_states_basis', (
            'MaterialState', 'ProcessingStage', 'SEED_PROCESSING_STAGES',
        )),
        ('pspp.pspp_page', (
            'SEED_PSPP_PAGE_DISPLAYS',
        )),
        ('pspp.material_structure_basis', (
            'ScaleStructureDefinition',
        )),
        ('pspp.reaction_windows_basis', (
            'ReactionWindow', 'SEED_REACTION_WINDOWS',
        )),
        ('pspp.threshold_windows_basis', (
            'ThresholdReactionWindow', 'SEED_THRESHOLD_WINDOWS',
        )),
        ('pspp.benchmark_cases_basis', (
            'BenchmarkCase', 'SEED_BENCHMARK_CASES',
        )),
        ('pspp.material_processes_basis', (
            'MaterialProcessDefinition', 'MaterialProcessExecution',
            'SEED_PROCESS_DEFINITIONS',
        )),
        ('pspp.cmc_library_seed', (
            'SEED_CMC_PROCESS_DEFINITIONS', 'SEED_CMC_PROCESSING_STAGES',
            'SEED_CMC_PROPERTY_MEANINGS',
        )),
        ('pspp.exposure_scenarios_basis', (
            'ExposureScenario', 'SEED_EXPOSURE_SCENARIOS',
        )),
        ('pspp.performance_scenarios_basis', (
            'MaterialPerformanceScenario',
        )),
        ('pspp.scale_transfers_basis', (
            'ScaleTransferDefinition', 'SEED_SCALE_TRANSFERS',
        )),
        ('pspp.reaction_network_basis', (
            'ChemicalSpecies', 'ReactionRule', 'SEED_CHEMICAL_SPECIES',
            'SEED_REACTION_RULES',
        )),
        ('pspp.custom.solgel_network', (
            'SOLGEL_CHEMICAL_SPECIES', 'SOLGEL_REACTION_RULES',
            'SOLGEL_THRESHOLD_WINDOWS',
        )),
        ('pspp.custom.solgel_process', (
            'SOLGEL_DIGITIZED_DATASETS', 'SOLGEL_PROCESSING_STAGES',
        )),
        ('pspp.solgel_sourcing_basis', (
            'PrecursorSource', 'SEED_PRECURSOR_SOURCES',
        )),
        ('pspp.sintering_seed', (
            'SEED_SINTERING_DATASETS',
        )),
        ('pspp.ceramics_samples_basis', (
            'CeramicSample', 'SEED_CERAMIC_SAMPLES',
            'SEED_CERAMICS_DATASETS',
        )),
        ('pspp.ceramics_ladder_basis', (
            'LadderRung', 'SEED_LADDER_RUNGS',
        )),
        ('pspp.research_tools_basis', (
            'ResearchTool', 'SEED_RESEARCH_TOOLS',
        )),
        ('pspp.characterization_seed', (
            'SEED_CHARACTERIZATION_DATASETS',
        )),
        ('pspp.custom.glass_refinement', (
            'GLASS_DIGITIZED_DATASETS', 'GLASS_THRESHOLD_WINDOWS',
        )),
    )),
    ('foodstate', (
        ('foodstate.food_contracts_basis', (
            'FoodDomainContract', 'SEED_FOOD_DOMAIN_CONTRACTS',
        )),
        ('foodstate.food_pspp_seed', (
            'SEED_FOOD_EVIDENCE_METHODS', 'SEED_FOOD_PROCESSES',
            'SEED_FOOD_STAGES',
        )),
        ('foodstate.food_materials_basis', (
            'FoodMaterial', 'build_food_material_seeds',
        )),
        ('foodstate.custom.food_composition', (
            'build_composition_claim_seeds', 'vendor_food_index',
        )),
        ('foodstate.food_ph_seed', (
            'SEED_FOOD_PH_CLAIMS',
        )),
        ('foodstate.food_acid_seed', (
            'SEED_FOOD_ACID_CLAIMS',
        )),
    )),
    ('aquaponics', (
        ('aquaponics.pot_materials_seed', (
            'SEED_POT_MATERIALS', 'SEED_POT_PROPERTY_MEANINGS',
            'SEED_POT_SCALE_DEFINITIONS',
        )),
        ('aquaponics.growth_media_basis', (
            'NutrientProfile', 'NutrientSpecies', 'SoilDefinition',
            'WaterDefinition',
        )),
        ('aquaponics.media_seed', (
            'SEED_NUTRIENT_PROFILES', 'SEED_NUTRIENT_SPECIES',
            'SEED_SOILS', 'SEED_WATERS',
        )),
        ('aquaponics.plant_basis', (
            'PlantDefinition', 'PlantPart',
        )),
        ('aquaponics.plant_seed', (
            'SEED_PLANTS', 'SEED_PLANT_PARTS',
        )),
        ('aquaponics.atmosphere_basis', (
            'AtmosphereDefinition',
        )),
        ('aquaponics.atmosphere_seed', (
            'SEED_ATMOSPHERES',
        )),
        ('aquaponics.pot_system_basis', (
            'PotSystemDefinition',
        )),
        ('aquaponics.pot_system_seed', (
            'SEED_AQP_CONTEXTUALIZED_VALUES', 'SEED_AQP_SCORE_CONCEPTS',
            'SEED_AQP_SCORE_SUBJECTS', 'SEED_AQP_SCORE_TERMS',
            'SEED_POT_SYSTEMS',
        )),
        ('aquaponics.vermicompost_basis', (
            'CompostBinDefinition', 'CompostLoopDefinition',
            'VermicompostProfile',
        )),
        ('aquaponics.vermicompost_seed', (
            'SEED_COMPOST_BINS', 'SEED_COMPOST_LOOPS',
            'SEED_ENRICH_CONTEXTUALIZED_VALUES',
            'SEED_ENRICH_SCORE_CONCEPTS', 'SEED_ENRICH_SCORE_SUBJECTS',
            'SEED_ENRICH_SCORE_TERMS', 'SEED_VERMICOMPOST_PROFILES',
        )),
        ('aquaponics.plant_growth_basis', (
            'PlantGrowthModel',
        )),
        ('aquaponics.plant_growth_seed', (
            'SEED_PLANT_GROWTH_MODELS',
        )),
    )),
    ('household', (
        ('household.household_basis', (
            'HOUSEHOLD_CLASSES', 'HOUSEHOLD_SEED_PAIRS',
        )),
    )),
    ('mealoptions', (
        ('mealoptions', (
            'MEALOPTIONS_CLASSES', 'MEALOPTIONS_SEED_PAIRS',
        )),
    )),
    ('nutrition', (
        ('nutrition.nutrient_basis', (
            'DietaryNutrient', 'NutrientReference',
        )),
        ('nutrition.nutrient_seed', (
            'SEED_DIETARY_NUTRIENTS', 'SEED_NUTRIENT_REFERENCES',
        )),
        ('nutrition.person_basis', (
            'PersonProfile',
        )),
        ('nutrition.household_basis', (
            'HouseholdProfile',
        )),
        ('nutrition.person_seed', (
            'SEED_HOUSEHOLDS', 'SEED_PERSONS',
        )),
        ('nutrition.food_basis', (
            'FoodItem', 'NutrientContent',
        )),
        ('nutrition.food_seed', (
            'SEED_FOOD_ITEMS', 'SEED_NUTRIENT_CONTENTS',
        )),
        ('nutrition.fdc_seed', (
            'SEED_FDC_FOOD_ITEMS', 'SEED_FDC_NUTRIENT_CONTENTS',
        )),
        ('nutrition.threshold_basis', (
            'EatingPatternDefinition', 'PersonThreshold',
            'SEED_EATING_PATTERNS',
        )),
        ('nutrition.tolerance_basis', (
            'ToleranceThreshold', 'SEED_TOLERANCE_THRESHOLDS',
        )),
        ('nutrition.meal_basis', (
            'MealPlanDefinition', 'MealEntry', 'SEED_MEAL_PLANS',
            'SEED_MEAL_ENTRIES',
        )),
        ('nutrition.activity_basis', (
            'ActivityDefinition', 'ActivityLog',
            'SEED_ACTIVITY_DEFINITIONS',
        )),
        ('nutrition.weight_basis', (
            'WeightObservation', 'SEED_WEIGHT_OBSERVATIONS',
        )),
        ('nutrition.fulfillment_basis', (
            'GardenPlanDefinition', 'SEED_GARDEN_PLANS',
        )),
        ('nutrition.workflow_basis', (
            'KitchenTool', 'MethodPreference', 'ToolAdvisorDismissal',
        )),
        ('nutrition.market_basis', (
            'SourceLocation', 'PriceObservation', 'UnitWeightPrior',
            'SEED_SOURCE_LOCATIONS', 'SEED_PRICE_OBSERVATIONS',
            'SEED_UNIT_WEIGHTS',
        )),
        ('nutrition.pantry_basis', (
            'PantryItem', 'SEED_PANTRY_ITEMS',
        )),
        ('nutrition.logistics_basis', (
            'LOGISTICS_CLASSES', 'LOGISTICS_SEED_PAIRS',
        )),
        ('nutrition.custom.logistics_analysis', (
            'MEAL_STEP_BUILDERS',
        )),
        ('nutrition.shoptrip_basis', (
            'SHOPTRIP_CLASSES', 'SHOPTRIP_SEED_PAIRS',
        )),
        ('nutrition.account_basis', (
            'UserAccountLink', 'SEED_USER_ACCOUNT_LINKS',
        )),
        ('nutrition.intake_basis', (
            'IntakeRecord', 'DailyIntakeMetric', 'PeriodIntakeMetric',
            'SEED_INTAKE_RECORDS',
        )),
        ('nutrition.exclusion_basis', (
            'FoodAllergenFlag', 'PersonExclusion',
            'SEED_FOOD_ALLERGEN_FLAGS', 'SEED_PERSON_EXCLUSIONS',
        )),
        ('nutrition.condition_basis', (
            'StatedCondition', 'ConditionSteering',
            'SEED_STATED_CONDITIONS', 'SEED_CONDITION_STEERINGS',
        )),
        ('nutrition.budget_basis', (
            'PlanBudget', 'SEED_PLAN_BUDGETS',
        )),
        ('nutrition.waste_basis', (
            'WasteRecord', 'SEED_WASTE_RECORDS',
        )),
        ('nutrition.rating_basis', (
            'MealRating', 'SEED_MEAL_RATINGS',
        )),
    )),
    ('plant_morphology', (
        ('plant_morphology.organ_basis', (
            'OrganModel', 'RootSystemModel',
        )),
        ('plant_morphology.morphology_seed', (
            'SEED_ORGAN_MODELS', 'SEED_ROOT_MODELS',
        )),
    )),
    ('aquaponics', (
        ('aquaponics.plant_growth_normalized_basis', (
            'PotPlanting',
        )),
        ('aquaponics.plant_growth_normalized_seed', (
            'SEED_POT_PLANTINGS',
        )),
        ('aquaponics.plant_stress_basis', (
            'StressResponseCurve',
        )),
        ('aquaponics.plant_stress_seed', (
            'SEED_STRESS_CURVES',
        )),
        ('aquaponics.light_basis', (
            'LightSourceDefinition', 'LightSpectrumDefinition',
        )),
        ('aquaponics.light_seed', (
            'SEED_LIGHT_SOURCES', 'SEED_LIGHT_SPECTRA',
        )),
        ('aquaponics.water_batch_basis', (
            'WaterBatchSchedule',
        )),
        ('aquaponics.water_batch_seed', (
            'SEED_WATER_BATCH_SCHEDULES',
        )),
    )),
    ('mathshapes', (
        ('mathshapes.shape_basis', (
            'MathShapeDefinition',
        )),
        ('mathshapes.shape_seed', (
            'SEED_MATH_SHAPES',
        )),
        ('mathshapes.tower_basis', (
            'AquaponicTowerDefinition',
        )),
        ('mathshapes.tower_seed', (
            'SEED_TOWERS',
        )),
        ('mathshapes.cad_basis', (
            'ImportedCadObject',
        )),
    )),
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
    ('microalgae', (
        ('microalgae.reactor_basis', (
            'AlgaeStrain', 'AlgaeReactorDefinition',
        )),
        ('microalgae.reactor_seed', (
            'SEED_ALGAE_REACTORS', 'SEED_ALGAE_STRAINS',
        )),
        ('microalgae.integrated_basis', (
            'IntegratedLoopDefinition',
        )),
        ('microalgae.integrated_seed', (
            'SEED_INTEGRATED_LOOPS',
        )),
    )),
    ('biomining', (
        ('biomining.biomining_basis', (
            'BioextractionAgent', 'BiomineralProduct',
            'BiomineSystemDefinition',
        )),
        ('biomining.biomining_seed', (
            'SEED_BIOEXTRACTION_AGENTS', 'SEED_BIOMINERAL_PRODUCTS',
            'SEED_BIOMINE_SYSTEMS',
        )),
        ('biomining.optical_seed', (
            'SEED_OPTICAL_AGENTS', 'SEED_OPTICAL_BIOMINE_SYSTEMS',
            'SEED_OPTICAL_PRODUCTS',
        )),
    )),
    ('biomining', (
        ('biomining.alloy_seed', (
            'SEED_ALLOY_AGENTS', 'SEED_ALLOY_BIOMINE_SYSTEMS',
            'SEED_ALLOY_PRODUCTS',
        )),
    )),
    ('video', (
        ('video.video_basis', (
            'VideoAsset',
        )),
    )),
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
    ('composition', (
        ('composition.archetype_basis', (
            'PartArchetypeDefinition',
        )),
        ('composition.component_basis', (
            'PartComponentDefinition',
        )),
        ('composition.design_matrix_basis', (
            'DesignMatrixDefinition',
        )),
        ('composition.failure_modes_basis', (
            'FailureModeDefinition',
        )),
        ('composition.functional_basis', (
            'ConstructionVariantDefinition', 'FunctionalPartDefinition',
        )),
        ('composition.interface_basis', (
            'InterfaceDefinition',
        )),
        ('composition.node_basis', (
            'CompositionNode',
        )),
        ('composition.routing_basis', (
            'RoutingDefinition', 'RoutingOperation',
        )),
    )),
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
            'BlockLayoutDefinition', 'BlockPlacement', 'BlockSizeVariant',
            'JointMortarAssignment', 'SEED_BLOCK_LAYOUTS',
            'SEED_BLOCK_PLACEMENTS', 'SEED_BLOCK_VARIANTS',
            'SEED_JOINT_MORTARS',
        )),
        ('magnetics.field_view_basis', (
            'FieldThresholdBand', 'FieldViewDefinition', 'FieldViewGroup',
            'SEED_FIELD_BANDS', 'SEED_FIELD_GROUPS', 'SEED_FIELD_VIEWS',
        )),
    )),
    ('motors', (
        ('motors.motor_basis', (
            'MotorDesignDefinition', 'MotorVerificationRun',
            'SEED_MOTOR_DESIGNS',
        )),
        ('motors.motor_shapes_seed', (
            'SEED_LAVET_PART_SHAPES', 'SEED_LAVET_SIM_SPACES',
            'SEED_LAVET_V2_PART_SHAPES', 'SEED_LAVET_V2_SIM_SPACES',
            'SEED_M1_PART_SHAPES', 'SEED_M1_SIM_SPACES',
            'SEED_M2_PART_SHAPES', 'SEED_M2_SIM_SPACES',
            'SEED_M3_PART_SHAPES', 'SEED_M3_SIM_SPACES',
            'SEED_MOTOR_MATERIALS_3D', 'SEED_MOTOR_PART_SHAPES',
            'SEED_MOTOR_SIM_SPACES',
        )),
        ('motors.motor_parts_basis', (
            'MotorPartDefinition', 'SEED_MOTOR_PARTS',
        )),
        ('motors.physics_equations_seed', (
            'SEED_EQUATION_ROWS',
        )),
        ('motors.motor_drive_basis', (
            'MotorControllerProfile', 'PhaseBindingDefinition',
            'SEED_CONTROLLER_PROFILES', 'SEED_PHASE_BINDINGS',
        )),
        ('motors.scale_goals_basis', (
            'ClockScaleDefinition', 'MotorGoalSpec',
        )),
        ('motors.clock_views_basis', (
            'ClockViewDefinition',
        )),
        ('motors.clock_scene_basis', (
            'ClockSceneLayerDefinition',
        )),
        ('motors.m1_positioning_basis', (
            'PrinterAxisRequirement',
        )),
        ('motors.m2_lift_basis', (
            'CrucibleHoistRequirement',
        )),
    )),
    ('meshassets', (
        ('meshassets.mesh_asset_basis', (
            'MeshAssetReference', 'MeshAssetSource', 'OrganMeshChoice',
        )),
        ('meshassets.mesh_asset_seed', (
            'SEED_MESH_ASSETS', 'SEED_MESH_SOURCES',
        )),
    )),
    ('gears', (
        ('gears.gear_basis', (
            'GearDefinition', 'GearMeshDefinition', 'GearTrainDefinition',
            'GearTypeDefinition', 'GearVerificationRun',
            'ShaftNodeDefinition',
        )),
        ('gears.gear_seed', (
            'SEED_GEAR_MESHES', 'SEED_GEAR_TRAINS', 'SEED_GEAR_TYPES',
            'SEED_GEARS', 'SEED_SHAFT_NODES',
        )),
    )),
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
        ('climate.co2_thresholds_seed', (
            'SEED_CO2_THRESHOLDS',
        )),
        ('climate.co2_indoor_seed', (
            'SEED_INDOOR_SPACES',
        )),
        ('climate.climate_history_seed', (
            'SEED_HUMAN_ERAS',
        )),
        ('climate.climate_series_seed', (
            'SEED_CLIMATE_SERIES',
        )),
        ('climate.sim_binding_basis', (
            'AtmosphereSeriesBinding', 'SEED_ATMOSPHERE_BINDINGS',
        )),
        ('climate.climate_compress_basis', (
            'SeriesCompressionRecord',
        )),
    )),
    ('odooconnect', (
        ('odooconnect.odoo_basis', (
            'OdooInstanceConfig',
        )),
        ('odooconnect.odoo_bindings_basis', (
            'OdooModelBinding', 'OdooSyncReceipt', 'SEED_ODOO_BINDINGS',
        )),
        ('odooconnect.odoo_scenarios_basis', (
            'BusinessScenarioDefinition', 'SEED_BUSINESS_SCENARIOS',
        )),
        ('odooconnect.odoo_seed', (
            'SEED_ODOO_INSTANCES',
        )),
    )),
    ('waxsupply', (
        ('waxsupply.wax_basis', (
            'WaxSourceDefinition',
        )),
        ('waxsupply.wax_seed', (
            'SEED_WAX_SOURCES',
        )),
    )),
    ('casting', (
        ('casting.casting_basis', (
            'CastingMaterialThermalProfile', 'MasterFeedstockDefinition',
            'MoldDefinition',
        )),
        ('casting.fill_sim_basis', (
            'MoldFillSimState',
        )),
        ('casting.interventions_basis', (
            'FillInterventionDefinition',
        )),
        ('casting.demold_basis', (
            'DemoldPlanDefinition',
        )),
        ('casting.coatings_basis', (
            'CastingRunRecord', 'MoldCoatingDefinition',
        )),
        ('casting.nesting_wizard_basis', (
            'NestingPlanDefinition',
        )),
        ('casting.sim_seed', (
            'SEED_CASTING_PAGE_DISPLAYS',
        )),
        ('casting.chain_basis', (
            'CastingStageDefinition', 'MoldNestingChain',
        )),
        ('casting.sprue_basis', (
            'SprueSetInstance', 'SprueStrategyDefinition',
        )),
        ('casting.casting_seed', (
            'SEED_CASTING_MODULES', 'seed_casting',
        )),
    )),
    ('supplychain', (
        ('supplychain.chain_basis', (
            'SupplyChainDefinition', 'SupplyFlow', 'SupplyNode',
        )),
        ('supplychain.chain_seed', (
            'SEED_SUPPLY_CHAINS', 'SEED_SUPPLY_FLOWS', 'SEED_SUPPLY_NODES',
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
    ('polariapps', (
        ('polariapps.apps_basis', (
            'AppDeploymentPlan', 'PolariAppDefinition',
        )),
        ('polariapps.apps_seed', (
            'SEED_POLARI_APPS',
        )),
        ('polariapps.apps_permissions_basis', (
            'AppPermissionProfile', 'SEED_PERMISSION_PROFILES',
        )),
    )),
    ('appstore', (
        ('appstore.appstore_basis', (
            'AppShellDefinition', 'ShellArtifact', 'ShellEnrollment',
            'ShellInstallation', 'AppEdgeBehavior',
        )),
        ('appstore.appstore_seed', (
            'SEED_APP_SHELLS', 'SEED_AI_TOOLS', 'SEED_EDGE_BEHAVIORS',
        )),
        ('appstore.appstore_page', (
            'SEED_APPSTORE_PAGE_DISPLAYS',
        )),
        ('appstore.appstore_ai_basis', (
            'AiToolDefinition',
        )),
        ('appstore.appstore_hosting_basis', (
            'RemoteHostingOption', 'SEED_REMOTE_HOSTING',
        )),
        ('appstore.appstore_forks_basis', (
            'ForkPin', 'SEED_FORK_PINS',
        )),
    )),
    ('islemesh', (
        ('islemesh.islemesh_basis', (
            'IsleApp', 'IsleAppService', 'IsleCatalogEntry', 'IsleDevice',
            'IsleEngine', 'IsleIngestReceipt', 'IsleProtocolPermit',
            'IsleUplink', 'MeshAppRealization',
        )),
        ('islemesh.islemesh_catalog', (
            'SEED_CATALOG',
        )),
        ('islemesh.islemesh_page', (
            'SEED_ISLEMESH_PAGE_DISPLAYS',
        )),
    )),
    ('techtree', (
        ('techtree.techtree_basis', (
            'TechDependencyEdge', 'TechNode', 'TechSegment',
            'TechSegmentAssignment', 'TechTreeDefinition',
        )),
        ('techtree.techtree_content_basis', (
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
    ('testing', (
        ('testing.capability_basis', (
            'CapabilityCheck', 'CheckRun',
        )),
        ('testing.testing_seed', (
            'SEED_CAPABILITY_CHECKS',
        )),
        ('testing.coverage_basis', (
            'StandardComputerBudget', 'AppHierarchyNode', 'ModuleCoverage',
            'AppBenchmark', 'TestCoveragePlan', 'SEED_STANDARD_COMPUTER_BUDGETS',
        )),
        ('testing.coverage_page', (
            'SEED_TESTING_COVERAGE_PAGE_DISPLAYS',
        )),
    )),
    ('grpcbridge', (
        ('grpcbridge.contract_basis', (
            'GrpcExposure', 'ProtoContractVersion',
        )),
        ('grpcbridge.java_bridge_basis', (
            'HardwareBridgeDefinition',
        )),
        ('grpcbridge.hwsim_basis', (
            'SimRigState', 'SEED_SIM_RIGS',
        )),
    )),
    ('hwfpga', (
        ('hwfpga.fpga_basis', (
            'FpgaRegisterState', 'RegisterDefinition',
            'RegisterMapDefinition', 'SEED_FPGA_STATES',
            'SEED_REGISTER_MAPS', 'SEED_REGISTERS',
        )),
        ('hwfpga.led_basis', (
            'LedMatrix4x4State', 'SEED_LED_MATRICES',
        )),
    )),
    ('electrodevice', (
        ('electrodevice.device_basis', (
            'CircuitRunResult', 'ElectronicDeviceDefinition',
            'SpiceModelCard', 'SEED_DEVICES',
        )),
        ('electrodevice.semiconductor_basis', (
            'SemiconductorProfile', 'SEED_SEMICONDUCTOR_PROFILES',
        )),
        ('electrodevice.device_validator_basis', (
            'DeviceValidationReport',
        )),
        ('electrodevice.photo_basis', (
            'PhotoAbsorberDefinition', 'SolarLayerDefinition',
            'SolarStackDefinition', 'SEED_PHOTO_ABSORBERS',
            'SEED_SOLAR_LAYERS', 'SEED_SOLAR_STACKS',
        )),
    )),
    ('cntfet', (
        ('cntfet.cnt_basis', (
            'AlignedCNTFETDevice', 'AlignedCNTFETGeometry',
            'CNTCalibrationAnchor', 'CNTContact', 'CNTFETParameterRow',
            'CNTFETSimResult', 'CNTMaterialState', 'CNTParasitics',
            'CNTTransportModel', 'GateStack', 'SEED_CNT_CONTACTS',
            'SEED_CNT_DEVICES', 'SEED_CNT_GEOMETRIES',
            'SEED_CNT_MATERIALS', 'SEED_CNT_PARASITICS',
            'SEED_CNT_TRANSPORT', 'SEED_GATE_STACKS',
        )),
        ('cntfet.cnt_calibration_seed', (
            'SEED_CALIBRATION_ANCHORS',
        )),
        ('cntfet.cnt_reference_papers_seed', (
            'SEED_REFERENCE_ANCHORS',
        )),
        ('cntfet.cnt_page', (
            'SEED_CNTFET_PAGE_DISPLAYS',
        )),
        ('cntfet.cnt_process_basis', (
            'CNTAlignmentProcess', 'CNTFETMonteCarloRun',
            'CNTPlacementProcess', 'CNTPurificationProcess',
            'ContactFormationProcess', 'GateStackProcess',
            'LithographyProcess', 'SEED_ALIGNMENT_PROCESSES',
            'SEED_CONTACT_PROCESSES', 'SEED_GATESTACK_PROCESSES',
            'SEED_LITHOGRAPHY_PROCESSES', 'SEED_PLACEMENT_PROCESSES',
            'SEED_PURIFICATION_PROCESSES',
        )),
        ('cntfet.cnt_characterization_basis', (
            'CellCharacterizationRun',
        )),
        ('cntfet.cnt_cell_library_basis', (
            'CNTCellDefinition', 'SEED_CNT_CELLS',
        )),
        ('cntfet.cnt_figures_seed', (
            'SEED_CNTFET_FIGURE_GRAPHS',
        )),
        ('cntfet.cnt_device_viz_seed', (
            'SEED_CNT_DEVICE_GRAPHS',
        )),
        ('cntfet.cnt_states_basis', (
            'FETOperatingState', 'SEED_FET_STATES',
        )),
        ('cntfet.cnt_scoring_seed', (
            'SEED_FET_SCORE_CONCEPTS', 'SEED_FET_SCORE_TERMS',
            'seed_subjects_and_values as _fet_score_subjects',
        )),
        ('cntfet.cnt_cell_scoring_seed', (
            'SEED_CELL_SCORE_CONCEPTS', 'SEED_CELL_SCORE_TERMS',
            'seed_cell_subjects as _cell_score_subjects',
        )),
        ('cntfet.custom.cnt_compare', (
            'score_pages as _cnt_score_pages',
        )),
        ('cntfet.cnt_cell_page', (
            'CellFETConfiguration', 'SEED_CELL_PAGES', 'seed_cell_configs',
        )),
        ('cntfet.cnt_block_page', (
            'BlockFETConfiguration', 'SEED_BLOCK_PAGES',
            'seed_block_configs',
        )),
    )),
    ('cntfet', (
        ('cntfet.cnt_regimes_basis', (
            'FETRegime', 'SEED_FET_REGIMES',
        )),
    )),
    ('cntfet', (
        ('cntfet.cnt_characteristics_basis', (
            'FETCharacteristic', 'SEED_FET_CHARACTERISTICS',
        )),
    )),
    ('cntfet', (
        ('cntfet.cnt_transport_basis', (
            'ScatteringMechanism', 'TransportRegime',
            'SEED_SCATTERING_MECHANISMS', 'SEED_TRANSPORT_REGIMES',
        )),
    )),
    ('cntfet', (
        ('cntfet.cnt_fields_basis', (
            'FETFieldBand', 'FETFieldSample', 'SEED_FET_FIELD_BANDS',
            'SEED_FET_FIELD_MATERIALS_3D',
        )),
    )),
    ('cntfet', (
        ('cntfet.cnt_scene_seed', (
            'SEED_CNT_DEVICE_SCENES', 'SEED_FET_FIELD_BINDINGS',
        )),
    )),
    ('cntfet', (
        ('cntfet.cnt_device_viz_seed', (
            'extra_graph_seeds as _cnt_fv_graphs',
            'SEED_CNT_DEVICE_GRAPHS',
        )),
    )),
    ('cntfet', (
        ('cntfet.cnt_taxonomy_basis', (
            'ComplementaryPair', 'FETOptimizationClass', 'FETShapeType',
            'SEED_COMPLEMENTARY_PAIRS', 'SEED_FET_OPTIMIZATION_CLASSES',
            'SEED_FET_SHAPE_TYPES', 'SEED_SIGNAL_SCORE_CONCEPTS',
            'SEED_SIGNAL_SCORE_TERMS',
        )),
    )),
    ('cntfet', (
        ('cntfet.cnt_power_basis', (
            'PowerBudget', 'SEED_POWER_BUDGETS', 'SEED_POWER_SCORE_TERMS',
        )),
    )),
    ('cntfet', (
        ('cntfet.cnt_targets_basis', (
            'DesignTarget', 'FETTargetMapping', 'SEED_DESIGN_TARGETS',
            'SEED_FET_TARGET_MAPPINGS', 'SEED_TARGET_POWER_BUDGETS',
        )),
    )),
    ('cntfet', (
        ('cntfet.cnt_ip_basis', (
            'SEED_TECHNOLOGY_IP', 'TechnologyIPRecord',
        )),
    )),
    ('cntfet', (
        ('cntfet.cnt_evidence_basis', (
            'EvidenceItem', 'SEED_EVIDENCE',
        )),
    )),
    ('cntfet', (
        ('cntfet.cnt_open_library_page', (
            'OpenCellLibrary', 'SEED_OPEN_LIBRARIES',
            'SEED_OPEN_LIBRARY_PAGES',
        )),
    )),
    ('cntfet', (
        ('cntfet.cnt_blocks_page', (
            'FunctionalBlock', 'SEED_FUNCTIONAL_BLOCKS',
            'SEED_BLOCK_PAGES',
        )),
    )),
    ('microchip', (
        ('microchip.chip_basis', (
            'DesignLevelDefinition', 'MicrochipDesignNode',
            'SEED_DESIGN_LEVELS', 'SEED_DESIGN_NODES',
        )),
        ('microchip.chip_page', (
            'SEED_MICROCHIP_PAGE_DISPLAYS',
        )),
        ('microchip.chip_families_basis', (
            'DeviceFamilyDefinition', 'SEED_DEVICE_FAMILIES',
        )),
    )),
    ('computerparts', (
        ('computerparts.parts_basis', (
            'ComputerBuildDefinition', 'ComputerPartDefinition',
        )),
        ('computerparts.parts_seed', (
            'SEED_COMPUTER_BUILDS', 'SEED_COMPUTER_PARTS',
        )),
    )),
    ('computers', (
        ('computers.computers_basis', (
            'ComputerAssemblyDefinition', 'ComputerPartClassDefinition',
            'ComputerProfileDefinition',
        )),
        ('computers.computers_page', (
            'SEED_COMPUTERS_PAGE_DISPLAYS',
        )),
        ('computers.computers_ports_basis', (
            'InterconnectDefinition',
        )),
    )),
    ('aquaponics', (
        ('aquaponics.aquaponics_page', (
            'SEED_AQUAPONICS_PAGE_DISPLAYS',
        )),
    )),
    ('mqttbridge', (
        ('mqttbridge.mqtt_basis', (
            'MqttBrokerDefinition', 'MqttMessageRecord',
            'MqttTopicBinding', 'SEED_MQTT_BINDINGS', 'SEED_MQTT_BROKERS',
        )),
    )),
    ('collab', (
        ('collab.collab_basis', (
            'CollaborationSession', 'MeetingRecord',
        )),
        ('collab.avatar_basis', (
            'AvatarDefinition', 'SEED_AVATARS',
        )),
    )),
    ('reticulum', (
        ('reticulum.reticulum_basis', (
            'ReticulumIdentity', 'ReticulumDestination',
            'ReticulumInterface', 'TransportBinding', 'LinkMeasurement',
            'AirtimeBudget', 'SEED_RNS_INTERFACES',
        )),
        ('reticulum.arch_basis', (
            'ArchipelagoNode', 'ArchipelagoTrust',
        )),
        ('reticulum.reticulum_page', (
            'SEED_RETICULUM_PAGE_DISPLAYS',
        )),
        ('reticulum.replication_basis', (
            'WatchedObject', 'ObjectStateVersion', 'StateConflict',
        )),
        ('reticulum.operator_basis', (
            'OperatorLicense', 'DeviceLink',
        )),
        ('reticulum.device_catalog_basis', (
            'DeviceModel', 'SEED_DEVICE_MODELS',
        )),
        ('reticulum.meshapp_basis', (
            'AppArchExposure', 'MeshAppRelay', 'MeshConsumer',
            'KitProfile', 'SEED_KIT_PROFILES',
        )),
        ('reticulum.datarule_basis', (
            'AppDataRule', 'QuarantinedSubmission',
        )),
        ('reticulum.discovery_basis', (
            'PeerSighting',
        )),
        ('reticulum.meshsim_basis', (
            'MeshSimScenario', 'MeshSimNode', 'MeshSimResult',
        )),
    )),
    ('vpn', (
        ('vpn', (
            'VPN_CLASSES', 'VPN_SEED_PAIRS', 'SEED_VPN_CATALOG',
            'SEED_VPN_PAGE_DISPLAYS', 'SEED_VPN_HARDWARE_APPS',
        )),
    )),
    ('hardwareapps', (
        ('hardwareapps.hardwareapps_basis', (
            'HardwareAppDefinition', 'HardwareAppState', 'HARDWAREAPPS_SEED_PAIRS',
        )),
        ('hardwareapps.hardwareapps_page', (
            'SEED_HARDWAREAPPS_PAGE_DISPLAYS',
        )),
    )),
    ('isle_relay', (
        ('isle_relay.isle_relay_basis', (
            'RelayNodeDefinition', 'RelayNodeState', 'ISLE_RELAY_SEED_PAIRS',
            'SEED_RELAY_HARDWARE_APPS', 'SEED_RELAY_CATALOG',
        )),
        ('isle_relay.isle_relay_page', (
            'SEED_ISLE_RELAY_PAGE_DISPLAYS',
        )),
    )),
    ('isle_guestnet', (
        ('isle_guestnet.isle_guestnet_basis', (
            'GuestNetworkDefinition', 'GuestNetworkExposure', 'GuestNetworkState', 'ISLE_GUESTNET_SEED_PAIRS',
            'SEED_GUESTNET_HARDWARE_APPS', 'SEED_GUESTNET_CATALOG',
        )),
        ('isle_guestnet.isle_guestnet_page', (
            'SEED_ISLE_GUESTNET_PAGE_DISPLAYS',
        )),
    )),
    ('hwmap', (
        ('hwmap.hwmap_basis', (
            'HardwareMapSnapshot', 'HardwarePort', 'HardwareSlot', 'PassthroughCandidate', 'HWMAP_SEED_PAIRS',
        )),
        ('hwmap.hwmap_page', (
            'SEED_HWMAP_PAGE_DISPLAYS',
        )),
    )),
    ('voron', (
        ('voron.voron_basis', (
            'PrinterDefinition', 'PrinterBoard', 'PrinterState', 'VORON_SEED_PAIRS',
            'SEED_VORON_HARDWARE_APPS', 'SEED_VORON_CATALOG',
        )),
        ('voron.voron_page', (
            'SEED_VORON_PAGE_DISPLAYS',
        )),
    )),
    ('suiteapps', (
        ('suiteapps.suiteapps_basis', (
            'SuiteAppDefinition', 'SuitePart', 'SuiteContract', 'SuitePlacement', 'SUITEAPPS_SEED_PAIRS', 'SEED_SUITE_CATALOG',
        )),
        ('suiteapps.suiteapps_page', (
            'SEED_SUITEAPPS_PAGE_DISPLAYS',
        )),
    )),
    ('printing_suite', (
        ('printing_suite.printing_suite_basis', (
            'MaterialLot', 'PrintProfile', 'SliceJob', 'GcodeArtifact', 'PrintJob', 'PrintOutcome',
            'ProductionRun', 'RunStepRecord', 'PRINTING_SUITE_SEED_PAIRS', 'SEED_PRINTING_SUITES', 'SEED_PRINTING_PARTS', 'SEED_PRINTING_CONTRACTS',
        )),
        ('printing_suite.printing_suite_page', (
            'SEED_PRINTING_SUITE_PAGE_DISPLAYS',
        )),
    )),
    ('kirimoto', (
        ('kirimoto.kirimoto_basis', (
            'SlicerInstance', 'SlicerProfile', 'KIRIMOTO_SEED_PAIRS', 'SEED_KIRIMOTO_CATALOG',
        )),
        ('kirimoto.kirimoto_page', (
            'SEED_KIRIMOTO_PAGE_DISPLAYS',
        )),
    )),
    ('terms', (
        ('terms.terms_basis', (
            'TermsDocument', 'TermsAcceptance', 'TERMS_CLASSES',
        )),
        ('terms.terms_seed', (
            'TERMS_SEED_PAIRS',
        )),
        ('terms.terms_page', (
            'SEED_TERMS_PAGE_DISPLAYS',
        )),
    )),
    ('printcam', (
        ('printcam.printcam_basis', (
            'CameraDefinition', 'TimelapseRecord', 'PRINTCAM_SEED_PAIRS', 'SEED_PRINTCAM_HARDWARE_APPS', 'SEED_PRINTCAM_CATALOG',
        )),
        ('printcam.printcam_page', (
            'SEED_PRINTCAM_PAGE_DISPLAYS',
        )),
    )),
)
