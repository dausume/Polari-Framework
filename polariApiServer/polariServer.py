#    Copyright (C) 2020  Dustin Etts
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.

#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.

#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <https://www.gnu.org/licenses/>.
from polariNetworking.defineLocalSys import *
from objectTreeDecorators import *
from polariApiServer.dataStreams import *
from polariFiles.dataChannels import *
from polariFiles.managedFiles import *
from polariApiServer.polariCRUDE import polariCRUDE
from polariApiServer.polariAPI import polariAPI
from polariApiServer.managerObjectAPI import managerObjectAPI
from polariApiServer.polyTypedObjectAPI import polyTypedObjectAPI
from polariApiServer.classInstanceCountsAPI import classInstanceCountsAPI
from polariApiServer.apiDiscoveryAPI import APIDiscoveryAPI
from polariApiServer.createClassAPI import createClassAPI
from polariApiServer.stateSpaceAPI import StateSpaceClassesAPI, StateSpaceConfigAPI, StateDefinitionAPI
from polariApiServer.apiConfigAPI import ApiConfigAPI
from polariApiServer.modulesAPI import ModulesAPI
from polariApiServer.displayDefinition import DisplayDefinition
from polariApiServer.tableDefinition import TableDefinition
from polariApiServer.graphDefinition import GraphDefinition
from polariApiServer.geoJsonDefinition import GeoJsonDefinition
from polariApiServer.dataSetDefinition import DataSetDefinition
from polariApiServer.fieldProfileDefinition import FieldProfileDefinition
from polariApiServer.filterChainDefinition import FilterChainDefinition
from polariApiServer.equationDefinition import EquationDefinition
from polariApiServer.tileSourceDefinition import TileSourceDefinition
from polariApiServer.geocoderDefinition import GeocoderDefinition
from polariApiServer.solutionDefinition import SolutionDefinition
from polariApiServer.solutionVersion import SolutionVersion
from polariApiServer.solutionTestCase import SolutionTestCase
from polariApiServer.executionStepAssertion import ExecutionStepAssertion
from polariApiServer.solutionProcessLink import SolutionProcessLink
from polariApiServer.mapPointDefinition import MapPointDefinition
from polariApiServer.mapLineSegmentDefinition import MapLineSegmentDefinition
from polariApiServer.mapPolygonDefinition import MapPolygonDefinition
from polariApiServer.solutionSeedData import SEED_SOLUTIONS
from polariApiServer.equationSeedData import SEED_EQUATIONS
from polariApiServer.solutionCodeGeneratorAPI import SolutionCodeGeneratorAPI
from polariApiServer.solutionExecutionAPI import SolutionExecutionAPI
from polariApiServer.equationExecutionAPI import EquationExecutionAPI
from matrices.matrix_api import MatrixAPI
from matrices.matrix_definition import MatrixDefinition
from matrices.matrix_equation_api import MatrixEquationAPI
from matrices.matrix_equation_definition import MatrixEquationDefinition
from matrices.seed_data import SEED_MATRICES, SEED_MATRIX_EQUATIONS
from polariApiServer.solutionVersionAPI import SolutionVersionAPI
from polariApiServer.updateClassConfigAPI import UpdateClassConfigAPI
from polariApiServer.systemInfoAPI import systemInfoAPI
from polariApiServer.aiChatAPI import aiChatAPI
from polariApiServer.providersAPI import providersAPI
from polariApiServer.aiActionsAPI import aiActionsAPI
from polariApiServer.apiFormatConfig import ApiFormatConfig
from polariApiServer.configuredFormattedAPIs import FlatJsonAPI, D3ColumnAPI, GeoJsonAPI
from polariApiServer.tileGeneratorAPI import TileGeneratorAPI
from polariApiServer.objectStorageAPI import ObjectStorageAPI
from polariApiServer.wsStatusAPI import WsStatusAPI
from polariApiServer.authMeAPI import AuthMeAPI, AuthJwksHealthAPI
from polariApiServer.roleAPI import RoleAPI
from accessControl.role import Role
# SimSpace abstraction — shared base + 2D-specific Definition classes.
# 3D classes land in Phase 2 and will be imported here as well.
from simSpace.sim_space_definition import SimSpaceDefinition
from simSpace.sim_space_binding_definition import SimSpaceBindingDefinition
from simSpace.sim_space_api import SimSpaceAPI
from simSpace2D.shape_2d_definition import Shape2DDefinition
from simSpace2D.style_2d_definition import Style2DDefinition
from simSpace2D.seed_data import SEED_SHAPES_2D, SEED_STYLES_2D, SEED_SIM_SPACES_2D
# 3D Definition classes (Phase 2 — three.js renderer skeleton).
from simSpace3D.mesh_3d_definition import Mesh3DDefinition
from simSpace3D.material_3d_definition import Material3DDefinition
from simSpace3D.texture_3d_definition import Texture3DDefinition
from simSpace3D.material_phase_appearance import MaterialPhaseAppearance
from simSpace3D.seed_data import (
    SEED_MESHES_3D, SEED_MATERIALS_3D, SEED_SIM_SPACES_3D,
    SEED_TEXTURES_3D, SEED_MATERIAL_PHASE_APPEARANCES,
)
# Materials Science: chemical elements + the periodic-table selection
# space (importing the seed module extends the shared 3D lists).
from materialsScience.chemical_element_definition import ChemicalElementDefinition
from materialsScience.periodic_table_seed import (
    SEED_CHEMICAL_ELEMENTS, SEED_PERIODIC_DISPLAYS,
)
# Materials basis: one identity per material + explicit per-scale
# definitions (bridges the legacy module's three unlinked roots).
from materialsScience.materials_basis import (
    MaterialsScienceMaterial, MaterialScaleDefinition,
)
from materialsScience.materials_basis_seed import (
    SEED_MS_MATERIALS, SEED_MS_SCALE_DEFINITIONS,
)
# Thermal processing windows (no-volatiles rule from Dustin's notes).
from materialsScience.thermal_windows import (
    ThermalProcessingProfile, SEED_THERMAL_PROFILES,
)
# Property meanings: what each material property IS + how it moves per
# scenario, as editable rows the detail view reads (msci-28).
from materialsScience.property_meanings import (
    MaterialPropertyMeaning, SEED_PROPERTY_MEANINGS,
)
# mp-3 (MODULE_PROJECTS_PLAN): feature modules may be ABSENT from a
# checkout (pol modules get/drop). Every feature-module import below
# sits in a guarded block: present code imports exactly as before;
# absent code stubs its symbols (SEED_* -> [], classes -> None) and
# records itself in MISSING_FEATURE_MODULES so surfaces stay honest.
# A downloaded module that fails to import still raises — lazy
# loading never swallows broken code.
from moduleService.module_loading import (
    feature_available as _feature_available,
    feature_import_error as _feature_import_error,
    stub_feature_symbols as _stub_feature_symbols,
    boot_report as _module_loading_boot_report,
)


def _stub_missing_feature(module_name, exc, globalns, symbols):
    _feature_import_error(module_name, exc)  # re-raises when downloaded
    _stub_feature_symbols(globalns, module_name, symbols)


# Context-based scoring: the Political Scorecard's term/context/weight
# system generalized over arbitrary Polari data (scr-1).
try:
    from scoring.scoring_basis import (
        ContextualizedValue, ScoreContext, ScoreSubject, ScoreTerm,
    )
    from scoring.score_concept import ScoreConcept
    from scoring.score_group import ScoreGroup
    from scoring.agreement_policy import (
        AgreementPolicy, SEED_AGREEMENT_POLICIES,
    )
    from scoring.scoring_seed import (
        SEED_CONTEXTUALIZED_VALUES, SEED_SCORE_CONCEPTS,
        SEED_SCORE_CONTEXTS, SEED_SCORE_GROUPS, SEED_SCORE_SUBJECTS,
        SEED_SCORE_TERMS,
    )
    # scr-5: assertions bind policy text to concepts; evidence carries
    # graded proof; contributors make individuals/orgs/lobbies trackable
    # (or pseudonymous) accountable identities.
    from scoring.assertions import AssertionValidityVote, ScoreAssertion
    from scoring.contributors import Contributor, SEED_CONTRIBUTORS
    from scoring.evidence import (
        EvidencePolicy, MediaEvidence, SEED_EVIDENCE_POLICIES,
    )
    from scoring.assertion_seed import (
        SEED_MEDIA_EVIDENCE, SEED_POLICY_SUBJECTS, SEED_SCORE_ASSERTIONS,
        SEED_VALIDITY_VOTES,
    )
    # scr-6: politician voting records → vote-weighted politician scores.
    from scoring.policy_votes import (
        PolicyVote, SEED_COHORT_GROUPS, SEED_POLICY_VOTES,
        SEED_POLITICIAN_SUBJECTS,
    )
    # scr-8: worldview elections → vote-derived group member weights.
    from scoring.worldview_elections import (
        SEED_ASSEMBLY_GROUPS, SEED_WORLDVIEW_BALLOTS,
        SEED_WORLDVIEW_ELECTIONS, WorldviewBallot, WorldviewElection,
    )
    # Democratic Scorecard revamp Phase 2: Housing Affordability, the first
    # real (non-demo) Context Tree — mechanism B applied to real content.
    from scoring.housing_affordability_seed import (
        SEED_HOUSING_BALLOTS, SEED_HOUSING_CONTEXTUALIZED_VALUES,
        SEED_HOUSING_CONTRIBUTORS, SEED_HOUSING_ELECTIONS,
        SEED_HOUSING_SCORE_CONCEPTS, SEED_HOUSING_SCORE_GROUPS,
        SEED_HOUSING_SCORE_TERMS,
    )
    # Democratic Scorecard revamp Phase 4: mechanism A (Group Display
    # votes) — vote on which Display best EXPLAINS a score, distinct from
    # mechanism B's vote on term-WEIGHTING worldviews.
    from scoring.group_display_vote import (
        GroupDisplayBallot, GroupDisplayVote, SEED_GROUP_DISPLAY_BALLOTS,
        SEED_GROUP_DISPLAY_VOTES, SEED_GROUP_DISPLAYS,
    )
    # Democratic Scorecard revamp mechanism C: logic-fork criterion votes
    # — vote on which alternate criterion a SPECIFIC decision point/fork
    # inside a decision procedure should use, distinct from mechanism A
    # (whole Displays) and mechanism B (whole worldview concepts).
    from scoring.logic_fork_vote import (
        DecisionProcedureEdge, LogicForkBallot, LogicForkCriterion,
        LogicForkVote, SEED_DECISION_PROCEDURE_EDGES,
        SEED_LOGIC_FORK_BALLOTS, SEED_LOGIC_FORK_CONTRIBUTORS,
        SEED_LOGIC_FORK_CRITERIA, SEED_LOGIC_FORK_VOTES,
    )
    # System-choice implications: which criterion is actually deployed
    # where over time (SystemChoiceInForce), and evidence-weighted claims
    # that a system choice affects a real-world score (reuses
    # ScoreAssertion unchanged).
    from scoring.system_choice_implications import (
        SEED_IMPLICATION_ASSERTIONS, SEED_IMPLICATION_CONTEXTUALIZED_VALUES,
        SEED_IMPLICATION_SCORE_TERMS, SEED_IMPLICATION_SUBJECTS,
        SEED_IMPLICATION_VALIDITY_VOTES, SEED_INTERPRETATION_BALLOTS,
        SEED_INTERPRETATION_ELECTIONS, SEED_INTERPRETATION_SCORE_CONCEPTS,
        SEED_INTERPRETATION_SCORE_GROUPS, SEED_SYSTEM_CHOICES_IN_FORCE,
        SystemChoiceInForce,
    )
    # Policy drafts scoreable through their lifecycle; venue-mismatch
    # pattern analysis (findings adjudicated by scr-6 validity votes).
    from scoring.policy_drafts import PolicyDraft
    from scoring.venue_patterns import (SEED_VENUE_PATTERNS,
                                        VenueActionRecord,
                                        VenueMismatchPattern)
    # Org-defined data-gathering procedures on the graph seam + the
    # step-credibility assertions comparing equivalent terms' methods.
    from scoring.data_gathering import (DataGatheringSolution,
                                        StepCredibilityAssertion)
    # Assertion credibility voting (group + individual units) and
    # drafter-set PolicyIntent (opt-in personal participation).
    from scoring.assertion_credibility import AssertionCredibilityVote
    from scoring.policy_intent import PolicyIntent
    # Term Competition (the PSC termcompetition draft, built): cited
    # composite proposals, relation assertions, scope votes, elections.
    from scoring.term_competition import (TermProposal,
                                          TermRelationAssertion,
                                          TermScopeVote)
    # Credibility bases: professional/impact/methodological/locality
    # standing per context, attestations, relevance voting, prioritized
    # (never-excluding) stance readings.
    from scoring.credibility_bases import (ClaimAttestation,
                                           CredibilityClaim,
                                           QualificationRelevanceVote,
                                           StanceBasis)
    # Democratic term proofs: rebuttable re-runnable demonstrations,
    # validity + comprehension votes, the manipulation-pattern catalog.
    # (SEED_TERM_PROOFS held back — its demo terms await a demo-content
    # pass; the pattern catalog seeds now.)
    from scoring.term_proofs import (DataManipulationPattern,
                                     ProofRebuttal, ProofVote,
                                     SEED_MANIPULATION_PATTERNS,
                                     TermProof)
    # Legislation tracking: who drafted what, who voted, provision-level
    # contributor attribution; official legislative API registrations.
    from scoring.legislation import (LegislationProvision,
                                     LegislationRecord,
                                     LegislativeVoteEvent)
except ImportError as _exc:
    _stub_missing_feature('scoring', _exc, globals(), (
        'ContextualizedValue', 'ScoreContext', 'ScoreSubject', 'ScoreTerm',
        'ScoreConcept', 'ScoreGroup', 'AgreementPolicy', 'SEED_AGREEMENT_POLICIES',
        'SEED_CONTEXTUALIZED_VALUES', 'SEED_SCORE_CONCEPTS', 'SEED_SCORE_CONTEXTS', 'SEED_SCORE_GROUPS',
        'SEED_SCORE_SUBJECTS', 'SEED_SCORE_TERMS', 'AssertionValidityVote', 'ScoreAssertion',
        'Contributor', 'SEED_CONTRIBUTORS', 'EvidencePolicy', 'MediaEvidence',
        'SEED_EVIDENCE_POLICIES', 'SEED_MEDIA_EVIDENCE', 'SEED_POLICY_SUBJECTS', 'SEED_SCORE_ASSERTIONS',
        'SEED_VALIDITY_VOTES', 'PolicyVote', 'SEED_COHORT_GROUPS', 'SEED_POLICY_VOTES',
        'SEED_POLITICIAN_SUBJECTS', 'SEED_ASSEMBLY_GROUPS', 'SEED_WORLDVIEW_BALLOTS', 'SEED_WORLDVIEW_ELECTIONS',
        'WorldviewBallot', 'WorldviewElection', 'SEED_HOUSING_BALLOTS', 'SEED_HOUSING_CONTEXTUALIZED_VALUES',
        'SEED_HOUSING_CONTRIBUTORS', 'SEED_HOUSING_ELECTIONS', 'SEED_HOUSING_SCORE_CONCEPTS', 'SEED_HOUSING_SCORE_GROUPS',
        'SEED_HOUSING_SCORE_TERMS', 'GroupDisplayBallot', 'GroupDisplayVote', 'SEED_GROUP_DISPLAY_BALLOTS',
        'SEED_GROUP_DISPLAY_VOTES', 'SEED_GROUP_DISPLAYS', 'DecisionProcedureEdge', 'LogicForkBallot',
        'LogicForkCriterion', 'LogicForkVote', 'SEED_DECISION_PROCEDURE_EDGES', 'SEED_LOGIC_FORK_BALLOTS',
        'SEED_LOGIC_FORK_CONTRIBUTORS', 'SEED_LOGIC_FORK_CRITERIA', 'SEED_LOGIC_FORK_VOTES', 'SEED_IMPLICATION_ASSERTIONS',
        'SEED_IMPLICATION_CONTEXTUALIZED_VALUES', 'SEED_IMPLICATION_SCORE_TERMS', 'SEED_IMPLICATION_SUBJECTS', 'SEED_IMPLICATION_VALIDITY_VOTES',
        'SEED_INTERPRETATION_BALLOTS', 'SEED_INTERPRETATION_ELECTIONS', 'SEED_INTERPRETATION_SCORE_CONCEPTS', 'SEED_INTERPRETATION_SCORE_GROUPS',
        'SEED_SYSTEM_CHOICES_IN_FORCE', 'SystemChoiceInForce', 'PolicyDraft', 'SEED_VENUE_PATTERNS',
        'VenueActionRecord', 'VenueMismatchPattern', 'DataGatheringSolution', 'StepCredibilityAssertion',
        'AssertionCredibilityVote', 'PolicyIntent', 'TermProposal', 'TermRelationAssertion',
        'TermScopeVote', 'ClaimAttestation', 'CredibilityClaim', 'QualificationRelevanceVote',
        'StanceBasis', 'DataManipulationPattern', 'ProofRebuttal', 'ProofVote',
        'SEED_MANIPULATION_PATTERNS', 'TermProof', 'LegislationProvision', 'LegislationRecord',
        'LegislativeVoteEvent',
    ))
try:
    from dmvdata.legis_sources import (SEED_LEGIS_DOMAINS,
                                       SEED_LEGIS_ENDPOINTS,
                                       SEED_LEGIS_GOV_SOURCES)
except ImportError as _exc:
    _stub_missing_feature('dmvdata', _exc, globals(), (
        'SEED_LEGIS_DOMAINS', 'SEED_LEGIS_ENDPOINTS', 'SEED_LEGIS_GOV_SOURCES',
    ))
# ncg-2: court cases advanced fork-by-fork through compiled no-code
# graphs (the judicial client of the graph-compiler seam).
try:
    from scoring.court_case import CourtCase
    # Group/instance authority: users hold primary/shared authority over
    # groups + instances; bindings make an instance THE authoritative
    # source for a group (both-sides definition with the PSC); signals
    # are admitted only through the three-check authority verdict.
    from scoring.group_authority import (GroupAuthorityGrant,
                                         GroupInstanceBinding,
                                         InstanceAuthorityGrant,
                                         TermAvailabilitySignal)
except ImportError as _exc:
    _stub_missing_feature('scoring', _exc, globals(), (
        'CourtCase', 'GroupAuthorityGrant', 'GroupInstanceBinding', 'InstanceAuthorityGrant',
        'TermAvailabilitySignal',
    ))
# AR zone capture (arz-1): 3+ placed points become a volume (prism)
# or a shape in the air (hull); sites aggregate zones house-wide.
try:
    from zones.zone_basis import (SEED_SITES, SEED_ZONE_POINTS,
                                  SEED_ZONES, SiteDefinition,
                                  ZoneDefinition, ZoneEstimateRecord,
                                  ZonePoint)
except ImportError as _exc:
    _stub_missing_feature('zones', _exc, globals(), (
        'SEED_SITES', 'SEED_ZONE_POINTS', 'SEED_ZONES', 'SiteDefinition',
        'ZoneDefinition', 'ZoneEstimateRecord', 'ZonePoint',
    ))
from polariNoCode.graph_compilers import (GraphCompilerDefinition,
                                          SEED_GRAPH_COMPILERS)
# ncg-3: digital-logic diagrams as rows -> generated Verilog/bench,
# iCE40 synthesis target (the hwdigital client of the same seam).
try:
    from hwdigital.logic_basis import (LogicBlockDesign, LogicBlockNode,
                                       SEED_LOGIC_DESIGNS,
                                       SEED_LOGIC_NODES)
except ImportError as _exc:
    _stub_missing_feature('hwdigital', _exc, globals(), (
        'LogicBlockDesign', 'LogicBlockNode', 'SEED_LOGIC_DESIGNS', 'SEED_LOGIC_NODES',
    ))
# ncg-4: circuits as rows -> generated SPICE netlists (the circuit
# client of the same seam).
try:
    from electrodevice.circuit_basis import (
        CircuitComponentDefinition, CircuitDefinition,
        CircuitNetDefinition, SEED_CIRCUIT_COMPONENTS,
        SEED_CIRCUIT_NETS, SEED_CIRCUITS)
    # ncg-5: breadboards — placements wired by tie point, jumpers
    # joining boards, boards re-wrappable as components.
    from electrodevice.breadboard_basis import (
        BoardJumper, BreadboardDefinition, ComponentPlacement,
        SEED_BREADBOARDS, SEED_JUMPERS, SEED_PLACEMENTS)
except ImportError as _exc:
    _stub_missing_feature('electrodevice', _exc, globals(), (
        'CircuitComponentDefinition', 'CircuitDefinition', 'CircuitNetDefinition', 'SEED_CIRCUIT_COMPONENTS',
        'SEED_CIRCUIT_NETS', 'SEED_CIRCUITS', 'BoardJumper', 'BreadboardDefinition',
        'ComponentPlacement', 'SEED_BREADBOARDS', 'SEED_JUMPERS', 'SEED_PLACEMENTS',
    ))
# col-1 (DMV cost of living): persona/geography vocabulary, the
# obscure-factor terms, escape-cost walkthrough categories, and the
# law-as-data statute values (DMV_COST_OF_LIVING_DATA_PLAN.md).
try:
    from scoring.dmv_col_seed import (
        SEED_DMV_GEO_CONTEXTS, SEED_DMV_SUBJECTS, SEED_DMV_TERMS,
        SEED_DMV_TIMEFRAMES, SEED_ESCAPE_COST_CATEGORIES,
        SEED_ESCAPE_COST_TERMS, SEED_PERSONA_CONTEXTS,
        SEED_STATUTE_VALUES)
except ImportError as _exc:
    _stub_missing_feature('scoring', _exc, globals(), (
        'SEED_DMV_GEO_CONTEXTS', 'SEED_DMV_SUBJECTS', 'SEED_DMV_TERMS', 'SEED_DMV_TIMEFRAMES',
        'SEED_ESCAPE_COST_CATEGORIES', 'SEED_ESCAPE_COST_TERMS', 'SEED_PERSONA_CONTEXTS', 'SEED_STATUTE_VALUES',
    ))
# col-2: the official-source registrations the API profiler ingests
# from (auth via env knobs only — repos are public).
try:
    from dmvdata.source_seed import (SEED_API_DOMAINS,
                                     SEED_API_ENDPOINTS)
    # GovSource registry: acronym glossary + key requirements +
    # duplication-origin records (retrievals are runtime data, no seeds).
    from dmvdata.gov_sources import (GovSource, SEED_GOV_SOURCES,
                                     SourceRetrieval)
    # Cross-validation: independent re-pull confirmations + provider-
    # group reliability terms/concept (weights mechanism-B votable).
    from dmvdata.cross_validation import (RetrievalConfirmation,
                                          SEED_PROVIDER_CONCEPT,
                                          SEED_PROVIDER_TERMS)
    # Varying legal source types — nonprofit/company/political-group/
    # individual siblings of GovSource, one cross-type machinery.
    from dmvdata.legal_sources import (
        CompanySource, IndividualSource, NonProfitSource,
        PoliticalGroupSource, SEED_COMPANY_SOURCES,
        SEED_INDIVIDUAL_SOURCES, SEED_NONPROFIT_SOURCES,
        SEED_POLITICAL_SOURCES)
except ImportError as _exc:
    _stub_missing_feature('dmvdata', _exc, globals(), (
        'SEED_API_DOMAINS', 'SEED_API_ENDPOINTS', 'GovSource', 'SEED_GOV_SOURCES',
        'SourceRetrieval', 'RetrievalConfirmation', 'SEED_PROVIDER_CONCEPT', 'SEED_PROVIDER_TERMS',
        'CompanySource', 'IndividualSource', 'NonProfitSource', 'PoliticalGroupSource',
        'SEED_COMPANY_SOURCES', 'SEED_INDIVIDUAL_SOURCES', 'SEED_NONPROFIT_SOURCES', 'SEED_POLITICAL_SOURCES',
    ))
# ncg-6: design-output -> circuit-source bindings, and authorable
# no-code test cases/packs (the acct-6 seed).
try:
    from electrodevice.level_bridge import (PinBindingDefinition,
                                            SEED_PIN_BINDINGS)
except ImportError as _exc:
    _stub_missing_feature('electrodevice', _exc, globals(), (
        'PinBindingDefinition', 'SEED_PIN_BINDINGS',
    ))
from polariNoCode.nocode_tests import (NoCodeTestCase,
                                       NoCodeTestPack,
                                       SEED_TEST_CASES,
                                       SEED_TEST_PACKS)
# scr-15: media outlets held accountable for accuracy to the data.
try:
    from scoring.media_accuracy import (
        AccuracyPolicy, FactualClaim, SEED_ACCURACY_POLICIES,
        SEED_FACTUAL_CLAIMS, SEED_MEDIA_OUTLETS,
    )
    # scr-16: per-group bias reads (bands are editable rows).
    from scoring.group_bias import BiasPolicy, SEED_BIAS_POLICIES
    # scr-12a: survival-cost walkthrough (categories ARE the wizard).
    from scoring.survival_costs import (
        CostCategory, SEED_COST_CATEGORIES, SEED_COST_TERMS,
        SEED_SURVIVAL_PROFILES, SurvivalCostProfile,
    )
except ImportError as _exc:
    _stub_missing_feature('scoring', _exc, globals(), (
        'AccuracyPolicy', 'FactualClaim', 'SEED_ACCURACY_POLICIES', 'SEED_FACTUAL_CLAIMS',
        'SEED_MEDIA_OUTLETS', 'BiasPolicy', 'SEED_BIAS_POLICIES', 'CostCategory',
        'SEED_COST_CATEGORIES', 'SEED_COST_TERMS', 'SEED_SURVIVAL_PROFILES', 'SurvivalCostProfile',
    ))
# Aquaponics module (aqp-1): self-watering pot geometry as first-class
# objects + waterproof pot materials (ceramic/geopolymer).
try:
    from aquaponics.pot_basis import PotDefinition, PotHole
    from aquaponics.pot_seed import SEED_POTS, SEED_POT_HOLES
except ImportError as _exc:
    _stub_missing_feature('aquaponics', _exc, globals(), (
        'PotDefinition', 'PotHole', 'SEED_POTS', 'SEED_POT_HOLES',
    ))
# waxprint module (wp-1): pellet-fed auger-screw wax 3D-printer sim —
# printer assembly + wax feedstock + print condition + device materials,
# with the two-zone (auger + hotend) melt and wax thermal-safety gate.
try:
    from waxprint.waxprint_basis import (
        DeviceMaterialDefinition, PrinterAssemblyDefinition,
        WaxFeedstockDefinition, PrintConditionDefinition,
        WaxReclaimBatch, MoldLifecycleRecord,
    )
    from waxprint.waxprint_seed import (
        SEED_DEVICE_MATERIALS, SEED_FEEDSTOCKS, SEED_ASSEMBLIES, SEED_CONDITIONS,
        SEED_WAXPRINT_MODULES,
    )
    # waxprint sim space (wp-5/wp-6): a registered, 3D-viewable multiscale sim
    # (WaxPrintSimState rows over build height) + condition-evaluation gates.
    # Importing sim_seed appends the scene/bindings/equations/sim-def/runs/msim/
    # ic-picker to the shared framework seed lists (trigger-on-import pattern).
    from waxprint.sim_state import WaxPrintSimState
    from waxprint import sim_seed  # noqa: F401 (import triggers the seed appends)
    from waxprint.sim_seed import (
        SEED_WAXPRINT_STATE_ROWS, SEED_WAXPRINT_PAGE_DISPLAYS,
    )
except ImportError as _exc:
    _stub_missing_feature('waxprint', _exc, globals(), (
        'DeviceMaterialDefinition', 'PrinterAssemblyDefinition', 'WaxFeedstockDefinition', 'PrintConditionDefinition', 'WaxReclaimBatch', 'MoldLifecycleRecord',
        'SEED_DEVICE_MATERIALS', 'SEED_FEEDSTOCKS', 'SEED_ASSEMBLIES', 'SEED_CONDITIONS',
        'SEED_WAXPRINT_MODULES', 'WaxPrintSimState', 'sim_seed', 'SEED_WAXPRINT_STATE_ROWS',
        'SEED_WAXPRINT_PAGE_DISPLAYS',
    ))
# pspp module (pspp-1): PSPP evidence + claims + digitized-dataset
# foundation — the one EvidenceMethod vocabulary, claims-not-values
# rows, and book figures/tables as data read by one generic engine.
try:
    from pspp.evidence_methods import EvidenceMethod, SEED_EVIDENCE_METHODS
    from pspp.claims import PropertyClaim, StructureClaim, ValidationClaim
    from pspp.digitized_datasets import DigitizedDataset
    from pspp.datasets_seed import SEED_DIGITIZED_DATASETS
    # pspp-2: the MaterialState DAG + processing-stage vocabulary.
    # MaterialState rows are EARNED (canonical states stay implicit
    # until written — pspp.state_resolution), so only stages seed.
    from pspp.material_states import (
        MaterialState, ProcessingStage, SEED_PROCESSING_STAGES,
    )
    # pspp-3: structure rows (earned, never seeded) + reaction
    # windows (Ch.8 ranges arrive as cited rows — none hardcoded).
    from pspp.pages_seed import SEED_PSPP_PAGE_DISPLAYS
    from pspp.material_structure import ScaleStructureDefinition
    from pspp.reaction_windows import ReactionWindow, SEED_REACTION_WINDOWS
    # pspp-8: threshold-shaped (banded/asymmetric) windows — p.193
    # graded bands + condition gates the stepping engine enforces.
    from pspp.threshold_windows import (
        ThresholdReactionWindow, SEED_THRESHOLD_WINDOWS,
    )
    # pspp-V3: the Ch.8 patent/lab examples as benchmark rows the
    # measured-vs-predicted overlay runs against.
    from pspp.benchmark_cases import (
        BenchmarkCase, SEED_BENCHMARK_CASES,
    )
    # pspp-4: processes as first-class transformations + the reaction
    # network as data (generic reactive-material engine).
    from pspp.material_processes import (
        MaterialProcessDefinition, MaterialProcessExecution,
        SEED_PROCESS_DEFINITIONS,
    )
    from pspp.cmc_library_seed import (
        SEED_CMC_PROCESS_DEFINITIONS, SEED_CMC_PROCESSING_STAGES,
        SEED_CMC_PROPERTY_MEANINGS,
    )
    from pspp.exposure_scenarios import (
        ExposureScenario, SEED_EXPOSURE_SCENARIOS,
    )
    from pspp.performance_scenarios import MaterialPerformanceScenario
    from pspp.scale_transfers import (
        ScaleTransferDefinition, SEED_SCALE_TRANSFERS,
    )
    from pspp.reaction_network import (
        ChemicalSpecies, ReactionRule, SEED_CHEMICAL_SPECIES,
        SEED_REACTION_RULES,
    )
    # mtt-2 sg: the sol-gel LIBRARY — the third swap-the-library
    # proof; rows concatenate into the pspp seeds below.
    from pspp.solgel_network import (
        SOLGEL_CHEMICAL_SPECIES, SOLGEL_REACTION_RULES,
        SOLGEL_THRESHOLD_WINDOWS,
    )
    from pspp.solgel_process import (
        SOLGEL_DIGITIZED_DATASETS, SOLGEL_PROCESSING_STAGES,
    )
    # mtt-2 sg-community: precursor sourcing / common-material routes.
    from pspp.solgel_sourcing import (
        PrecursorSource, SEED_PRECURSOR_SOURCES,
    )
    # mtt-2 Part B: the ceramic sintering engine's master-curve
    # calibration data (provisional until digitized).
    from pspp.sintering_seed import SEED_SINTERING_DATASETS
    # mtt-2 ceramics: usable samples (local + olivine tracks) + the
    # furnace escalation ladder + the olivine-carbonation dataset.
    from pspp.ceramics_samples import (
        CeramicSample, SEED_CERAMIC_SAMPLES, SEED_CERAMICS_DATASETS,
    )
    from pspp.ceramics_ladder import LadderRung, SEED_LADDER_RUNGS
    # mtt-2 research tools: buildable open-source instruments (the
    # measurement half — FTIR, red-cabbage pH, Brix, spectrometer...).
    from pspp.research_tools import ResearchTool, SEED_RESEARCH_TOOLS
    # mtt-2 characterization: the FTIR band-calibration data gap.
    from pspp.characterization import SEED_CHARACTERIZATION_DATASETS
    # mtt-2 glass core: viscosity reference points + refinement
    # windows + the devit/viscous-master-curve data asks.
    from pspp.glass_refinement import (
        GLASS_DIGITIZED_DATASETS, GLASS_THRESHOLD_WINDOWS,
    )
except ImportError as _exc:
    _stub_missing_feature('pspp', _exc, globals(), (
        'EvidenceMethod', 'SEED_EVIDENCE_METHODS', 'PropertyClaim',
        'StructureClaim', 'ValidationClaim', 'DigitizedDataset',
        'SEED_DIGITIZED_DATASETS', 'MaterialState', 'ProcessingStage',
        'SEED_PROCESSING_STAGES', 'ScaleStructureDefinition',
        'ReactionWindow', 'SEED_REACTION_WINDOWS',
        'ThresholdReactionWindow', 'SEED_THRESHOLD_WINDOWS',
        'BenchmarkCase', 'SEED_BENCHMARK_CASES',
        'SEED_PSPP_PAGE_DISPLAYS', 'MaterialProcessDefinition', 'MaterialProcessExecution',
        'SEED_PROCESS_DEFINITIONS', 'ChemicalSpecies', 'ReactionRule',
        'SEED_CHEMICAL_SPECIES', 'SEED_REACTION_RULES',
        'ScaleTransferDefinition', 'SEED_SCALE_TRANSFERS',
        'ExposureScenario', 'SEED_EXPOSURE_SCENARIOS',
        'SEED_CMC_PROCESS_DEFINITIONS', 'SEED_CMC_PROCESSING_STAGES',
        'SEED_CMC_PROPERTY_MEANINGS',
        'MaterialPerformanceScenario',
        'SOLGEL_CHEMICAL_SPECIES', 'SOLGEL_REACTION_RULES',
        'SOLGEL_THRESHOLD_WINDOWS', 'SOLGEL_DIGITIZED_DATASETS',
        'SOLGEL_PROCESSING_STAGES',
        'PrecursorSource', 'SEED_PRECURSOR_SOURCES',
        'SEED_SINTERING_DATASETS',
        'CeramicSample', 'SEED_CERAMIC_SAMPLES', 'SEED_CERAMICS_DATASETS',
        'LadderRung', 'SEED_LADDER_RUNGS',
        'ResearchTool', 'SEED_RESEARCH_TOOLS',
        'SEED_CHARACTERIZATION_DATASETS',
        'GLASS_DIGITIZED_DATASETS', 'GLASS_THRESHOLD_WINDOWS',
    ))
try:
    from aquaponics.pot_materials_seed import (
        SEED_POT_MATERIALS, SEED_POT_PROPERTY_MEANINGS,
        SEED_POT_SCALE_DEFINITIONS,
    )
    # aqp-2: multiscale soil + water + nutrient profiles.
    from aquaponics.growth_media import (
        NutrientProfile, NutrientSpecies, SoilDefinition, WaterDefinition,
    )
    from aquaponics.media_seed import (
        SEED_NUTRIENT_PROFILES, SEED_NUTRIENT_SPECIES, SEED_SOILS,
        SEED_WATERS,
    )
    # aqp-4: per-part plant profiles (permanent structure + carbon/nutrient
    # capture + CO2/O2 flux).
    from aquaponics.plant_basis import PlantDefinition, PlantPart
    from aquaponics.plant_seed import SEED_PLANTS, SEED_PLANT_PARTS
    # aqp-5: full atmospheric conditions + plant<->air gas exchange.
    from aquaponics.atmosphere_basis import AtmosphereDefinition
    from aquaponics.atmosphere_seed import SEED_ATMOSPHERES
    # aqp-6: bound pot systems + environmental-impact/survival synthesis +
    # the scoring bridge (systems ranked through the context-scoring engine).
    from aquaponics.pot_system import PotSystemDefinition
    from aquaponics.pot_system_seed import (
        SEED_AQP_CONTEXTUALIZED_VALUES, SEED_AQP_SCORE_CONCEPTS,
        SEED_AQP_SCORE_SUBJECTS, SEED_AQP_SCORE_TERMS, SEED_POT_SYSTEMS,
    )
    # Aquaponics worm-compost enrichment loop (aqp-7).
    from aquaponics.vermicompost import (
        CompostBinDefinition, CompostLoopDefinition, VermicompostProfile,
    )
    from aquaponics.vermicompost_seed import (
        SEED_COMPOST_BINS, SEED_COMPOST_LOOPS, SEED_ENRICH_CONTEXTUALIZED_VALUES,
        SEED_ENRICH_SCORE_CONCEPTS, SEED_ENRICH_SCORE_SUBJECTS,
        SEED_ENRICH_SCORE_TERMS, SEED_VERMICOMPOST_PROFILES,
    )
    # Aquaponics per-part plant growth / growth-failure (aqp-8).
    from aquaponics.plant_growth_basis import PlantGrowthModel
    from aquaponics.plant_growth_seed import SEED_PLANT_GROWTH_MODELS
except ImportError as _exc:
    _stub_missing_feature('aquaponics', _exc, globals(), (
        'SEED_POT_MATERIALS', 'SEED_POT_PROPERTY_MEANINGS', 'SEED_POT_SCALE_DEFINITIONS', 'NutrientProfile',
        'NutrientSpecies', 'SoilDefinition', 'WaterDefinition', 'SEED_NUTRIENT_PROFILES',
        'SEED_NUTRIENT_SPECIES', 'SEED_SOILS', 'SEED_WATERS', 'PlantDefinition',
        'PlantPart', 'SEED_PLANTS', 'SEED_PLANT_PARTS', 'AtmosphereDefinition',
        'SEED_ATMOSPHERES', 'PotSystemDefinition', 'SEED_AQP_CONTEXTUALIZED_VALUES', 'SEED_AQP_SCORE_CONCEPTS',
        'SEED_AQP_SCORE_SUBJECTS', 'SEED_AQP_SCORE_TERMS', 'SEED_POT_SYSTEMS', 'CompostBinDefinition',
        'CompostLoopDefinition', 'VermicompostProfile', 'SEED_COMPOST_BINS', 'SEED_COMPOST_LOOPS',
        'SEED_ENRICH_CONTEXTUALIZED_VALUES', 'SEED_ENRICH_SCORE_CONCEPTS', 'SEED_ENRICH_SCORE_SUBJECTS', 'SEED_ENRICH_SCORE_TERMS',
        'SEED_VERMICOMPOST_PROFILES', 'PlantGrowthModel', 'SEED_PLANT_GROWTH_MODELS',
    ))
# Nutrition: dietary-nutrient vocab + person + household profiling
# (nut-1/3/4).
try:
    from nutrition.nutrient_basis import DietaryNutrient, NutrientReference
    from nutrition.nutrient_seed import (
        SEED_DIETARY_NUTRIENTS, SEED_NUTRIENT_REFERENCES,
    )
    from nutrition.person_basis import PersonProfile
    from nutrition.household_basis import HouseholdProfile
    from nutrition.person_seed import SEED_HOUSEHOLDS, SEED_PERSONS
    # Nutrition: plant harvest -> meal-nutrient yield (nut-2).
    from nutrition.food_basis import FoodItem, NutrientContent
    from nutrition.food_seed import SEED_FOOD_ITEMS, SEED_NUTRIENT_CONTENTS
except ImportError as _exc:
    _stub_missing_feature('nutrition', _exc, globals(), (
        'DietaryNutrient', 'NutrientReference', 'SEED_DIETARY_NUTRIENTS', 'SEED_NUTRIENT_REFERENCES',
        'PersonProfile', 'HouseholdProfile', 'SEED_HOUSEHOLDS', 'SEED_PERSONS',
        'FoodItem', 'NutrientContent', 'SEED_FOOD_ITEMS', 'SEED_NUTRIENT_CONTENTS',
    ))
# Plant morphology: 3D organ + root stand-in models + confinement
# (morph-1).
try:
    from plant_morphology.organ_basis import OrganModel, RootSystemModel
    from plant_morphology.morphology_seed import (
        SEED_ORGAN_MODELS, SEED_ROOT_MODELS,
    )
except ImportError as _exc:
    _stub_missing_feature('plant_morphology', _exc, globals(), (
        'OrganModel', 'RootSystemModel', 'SEED_ORGAN_MODELS', 'SEED_ROOT_MODELS',
    ))
# Plant-growth-sim phase 1: per-part normalized-growth instance state
# (2026-07-15 — the missing "this specific plant, in this pot, this
# far along" object; see aquaponics/plant_growth_normalized.py).
try:
    from aquaponics.plant_growth_normalized import PotPlanting
    from aquaponics.plant_growth_normalized_seed import SEED_POT_PLANTINGS
    # Plant-growth-sim phase 7: stress-type-differentiated response curves
    # (2026-07-15 — see aquaponics/plant_stress.py).
    from aquaponics.plant_stress import StressResponseCurve
    from aquaponics.plant_stress_seed import SEED_STRESS_CURVES
    # Plant-growth-sim phase 8: direct-light field simulation (2026-07-15
    # — see aquaponics/light_field.py).
    from aquaponics.light_basis import LightSourceDefinition, LightSpectrumDefinition
    from aquaponics.light_seed import SEED_LIGHT_SOURCES, SEED_LIGHT_SPECTRA
    # Plant-growth-sim phase 10: water batching + real nutrient uptake
    # (2026-07-15 — see aquaponics/water_batch.py, nutrient_uptake.py).
    from aquaponics.water_batch import WaterBatchSchedule
    from aquaponics.water_batch_seed import SEED_WATER_BATCH_SCHEDULES
except ImportError as _exc:
    _stub_missing_feature('aquaponics', _exc, globals(), (
        'PotPlanting', 'SEED_POT_PLANTINGS', 'StressResponseCurve', 'SEED_STRESS_CURVES',
        'LightSourceDefinition', 'LightSpectrumDefinition', 'SEED_LIGHT_SOURCES', 'SEED_LIGHT_SPECTRA',
        'WaterBatchSchedule', 'SEED_WATER_BATCH_SCHEDULES',
    ))
# Math-defined shapes: quadric/primitive/CSG geometry core (shape-1).
try:
    from mathshapes.shape_basis import MathShapeDefinition
    from mathshapes.shape_seed import SEED_MATH_SHAPES
    # Aquaponic tower: vertical stack of math-defined pots (shape-2).
    from mathshapes.tower_basis import AquaponicTowerDefinition
    from mathshapes.tower_seed import SEED_TOWERS
    # CAD import/export via cad-engines worker + MinIO (shape-3).
    from mathshapes.cad_basis import ImportedCadObject
except ImportError as _exc:
    _stub_missing_feature('mathshapes', _exc, globals(), (
        'MathShapeDefinition', 'SEED_MATH_SHAPES', 'AquaponicTowerDefinition', 'SEED_TOWERS',
        'ImportedCadObject',
    ))
from polariRefs.write_journal import WriteJournalEntry
from simulationLocks.lease import LeaseBreakEvent, MutationLease
from simulationLocks.object_locks import LockBreakEvent, ObjectLockEntry
from simulationLocks.sim_queue import SimulationQueueEntry
# Tanks: freshwater + saltwater ecosystem simulation — alternate
# nutrient source (tank-1).
try:
    from tanks.tank_basis import (
        AquacultureSpecies, TankDefinition, TankSubstrateDefinition,
        TankSystemDefinition,
    )
    from tanks.tank_seed import (
        SEED_AQUACULTURE_SPECIES, SEED_TANK_SUBSTRATES, SEED_TANK_SYSTEMS,
        SEED_TANKS,
    )
except ImportError as _exc:
    _stub_missing_feature('tanks', _exc, globals(), (
        'AquacultureSpecies', 'TankDefinition', 'TankSubstrateDefinition', 'TankSystemDefinition',
        'SEED_AQUACULTURE_SPECIES', 'SEED_TANK_SUBSTRATES', 'SEED_TANK_SYSTEMS', 'SEED_TANKS',
    ))
# Microalgae photobioreactors — the decarbonization route, coupled
# sustainably to aquaponics / tanks / hydroponics (algae-1).
try:
    from microalgae.reactor_basis import AlgaeStrain, AlgaeReactorDefinition
    from microalgae.reactor_seed import (
        SEED_ALGAE_REACTORS, SEED_ALGAE_STRAINS,
    )
    # Integrated excess-source + reactor loops (algae-2).
    from microalgae.integrated_basis import IntegratedLoopDefinition
    from microalgae.integrated_seed import SEED_INTEGRATED_LOOPS
except ImportError as _exc:
    _stub_missing_feature('microalgae', _exc, globals(), (
        'AlgaeStrain', 'AlgaeReactorDefinition', 'SEED_ALGAE_REACTORS', 'SEED_ALGAE_STRAINS',
        'IntegratedLoopDefinition', 'SEED_INTEGRATED_LOOPS',
    ))
# Biomining / bioextraction specialized aquaponic variants (biomine-1).
try:
    from biomining.biomining_basis import (
        BioextractionAgent, BiomineralProduct, BiomineSystemDefinition,
    )
    from biomining.biomining_seed import (
        SEED_BIOEXTRACTION_AGENTS, SEED_BIOMINERAL_PRODUCTS,
        SEED_BIOMINE_SYSTEMS,
    )
    # Fully-bio optical-dielectric biomining variants (dielectric-optics-1).
    from biomining.optical_seed import (
        SEED_OPTICAL_AGENTS, SEED_OPTICAL_BIOMINE_SYSTEMS,
        SEED_OPTICAL_PRODUCTS,
    )
except ImportError as _exc:
    _stub_missing_feature('biomining', _exc, globals(), (
        'BioextractionAgent', 'BiomineralProduct', 'BiomineSystemDefinition', 'SEED_BIOEXTRACTION_AGENTS',
        'SEED_BIOMINERAL_PRODUCTS', 'SEED_BIOMINE_SYSTEMS', 'SEED_OPTICAL_AGENTS', 'SEED_OPTICAL_BIOMINE_SYSTEMS',
        'SEED_OPTICAL_PRODUCTS',
    ))
from materialsScience.dielectric_optics_seed import (
    SEED_DIELECTRIC_MATERIALS, SEED_DIELECTRIC_PROPERTY_MEANINGS,
)
# Bio ferrous alloys: Ni phytomining + galvanized bio-steel (bio-alloys-1).
try:
    from biomining.alloy_seed import (
        SEED_ALLOY_AGENTS, SEED_ALLOY_BIOMINE_SYSTEMS, SEED_ALLOY_PRODUCTS,
    )
except ImportError as _exc:
    _stub_missing_feature('biomining', _exc, globals(), (
        'SEED_ALLOY_AGENTS', 'SEED_ALLOY_BIOMINE_SYSTEMS', 'SEED_ALLOY_PRODUCTS',
    ))
from materialsScience.bio_alloys_seed import (
    SEED_BIO_ALLOY_MATERIALS, SEED_BIO_ALLOY_PROPERTY_MEANINGS,
)
# Self-hosted video (video-1): WebM/MP4 + optional adaptive HLS.
try:
    from video.video_basis import VideoAsset
except ImportError as _exc:
    _stub_missing_feature('video', _exc, globals(), ('VideoAsset',))
# Business ops — setup/upgrade flows, economy track, order planner
# (biz-1).
try:
    from bizops.bizops_basis import (
        BusinessStageDefinition, BusinessUpgradeStep,
        BusinessProfile, LocalEconomyMilestone,
        ProcessWorkflowDefinition, ProductOrder,
        MarketSessionRecord, ProductionRunRecord,
        PartnershipAgreement, BusinessRiskNote,
        ComplianceRequirement, ComplianceRecord,
        QualityCheckDefinition, QualityCheckRecord,
    )
    from bizops.bizops_seed import (
        SEED_BUSINESS_STAGES, SEED_BUSINESS_UPGRADES,
        SEED_BUSINESS_PROFILES, SEED_ECONOMY_MILESTONES,
        SEED_PROCESS_WORKFLOWS, SEED_RISK_NOTES,
        SEED_PARTNERSHIPS, SEED_COMPLIANCE_REQUIREMENTS,
        SEED_QUALITY_CHECKS,
    )
except ImportError as _exc:
    _stub_missing_feature('bizops', _exc, globals(), (
        'BusinessStageDefinition', 'BusinessUpgradeStep',
        'BusinessProfile', 'LocalEconomyMilestone',
        'ProcessWorkflowDefinition', 'ProductOrder',
        'MarketSessionRecord', 'ProductionRunRecord',
        'PartnershipAgreement', 'BusinessRiskNote',
        'ComplianceRequirement', 'ComplianceRecord',
        'QualityCheckDefinition', 'QualityCheckRecord',
        'SEED_BUSINESS_STAGES', 'SEED_BUSINESS_UPGRADES',
        'SEED_BUSINESS_PROFILES', 'SEED_ECONOMY_MILESTONES',
        'SEED_PROCESS_WORKFLOWS', 'SEED_RISK_NOTES',
        'SEED_PARTNERSHIPS', 'SEED_COMPLIANCE_REQUIREMENTS',
        'SEED_QUALITY_CHECKS',
    ))
# Part composition (arch-2..5): components/interfaces with derived
# levels, EBOM/MBOM split, routings + promotion, archetypes +
# design matrices. Seeds are NOT listed in the legacy insert-only
# pass — composition seeds itself through its arch-1 upsert path
# (see the seed_composition call in _seedSimSpace3D).
try:
    from composition.archetype_basis import PartArchetypeDefinition
    from composition.component_basis import PartComponentDefinition
    from composition.design_matrix import DesignMatrixDefinition
    from composition.failure_modes import FailureModeDefinition
    from composition.functional_basis import (
        ConstructionVariantDefinition, FunctionalPartDefinition,
    )
    from composition.interface_basis import InterfaceDefinition
    from composition.node_basis import CompositionNode
    from composition.routing_basis import (
        RoutingDefinition, RoutingOperation,
    )
except ImportError as _exc:
    _stub_missing_feature('composition', _exc, globals(), (
        'PartArchetypeDefinition', 'PartComponentDefinition',
        'DesignMatrixDefinition', 'FailureModeDefinition',
        'ConstructionVariantDefinition', 'FunctionalPartDefinition',
        'InterfaceDefinition', 'CompositionNode',
        'RoutingDefinition', 'RoutingOperation',
    ))
# Magnetic materials Section A — option catalog + role taxonomy +
# powder designer (mag-2/2r/2t).
try:
    from magnetics.magnet_basis import (
        MagneticMaterialOption, MagneticPowderDefinition,
        MaterialUseRole,
    )
    from magnetics.magnet_seed import (
        SEED_MAGNETIC_POWDERS, SEED_MATERIAL_OPTIONS, SEED_USE_ROLES,
    )
    from magnetics.magnet_circuit_basis import (
        FluxNodeDefinition, MagneticCircuitDefinition,
        MagneticElementDefinition, SEED_FLUX_NODES,
        SEED_MAGNETIC_CIRCUITS, SEED_MAGNETIC_ELEMENTS,
    )
    from magnetics.magnet_block_basis import (
        BlockLayoutDefinition, BlockPlacement, BlockSizeVariant,
        JointMortarAssignment, SEED_BLOCK_LAYOUTS,
        SEED_BLOCK_PLACEMENTS, SEED_BLOCK_VARIANTS,
        SEED_JOINT_MORTARS,
    )
    from magnetics.field_view_basis import (
        FieldThresholdBand, FieldViewDefinition, FieldViewGroup,
        SEED_FIELD_BANDS, SEED_FIELD_GROUPS, SEED_FIELD_VIEWS,
    )
except ImportError as _exc:
    _stub_missing_feature('magnetics', _exc, globals(), (
        'MagneticMaterialOption', 'MagneticPowderDefinition',
        'MaterialUseRole', 'SEED_MAGNETIC_POWDERS',
        'SEED_MATERIAL_OPTIONS', 'SEED_USE_ROLES',
        'FluxNodeDefinition', 'MagneticCircuitDefinition',
        'MagneticElementDefinition', 'SEED_FLUX_NODES',
        'SEED_MAGNETIC_CIRCUITS', 'SEED_MAGNETIC_ELEMENTS',
        'BlockLayoutDefinition', 'BlockPlacement',
        'BlockSizeVariant', 'JointMortarAssignment',
        'SEED_BLOCK_LAYOUTS', 'SEED_BLOCK_PLACEMENTS',
        'SEED_BLOCK_VARIANTS', 'SEED_JOINT_MORTARS',
        'FieldThresholdBand', 'FieldViewDefinition',
        'FieldViewGroup', 'SEED_FIELD_BANDS', 'SEED_FIELD_GROUPS',
        'SEED_FIELD_VIEWS',
    ))
# Electric motors Section C — the M0..M3 ladder of buildable
# samples (mag-5).
try:
    from motors.motor_basis import (
        MotorDesignDefinition, MotorVerificationRun,
        SEED_MOTOR_DESIGNS,
    )
    from motors.motor_shapes import (
        SEED_LAVET_PART_SHAPES, SEED_LAVET_SIM_SPACES,
        SEED_LAVET_V2_PART_SHAPES, SEED_LAVET_V2_SIM_SPACES,
        SEED_M1_PART_SHAPES, SEED_M1_SIM_SPACES,
        SEED_M3_PART_SHAPES, SEED_M3_SIM_SPACES,
        SEED_MOTOR_MATERIALS_3D, SEED_MOTOR_PART_SHAPES,
        SEED_MOTOR_SIM_SPACES,
    )
    from motors.motor_parts import (
        MotorPartDefinition, SEED_MOTOR_PARTS,
    )
    from motors.physics_equations import SEED_EQUATION_ROWS
    from motors.motor_drive import (
        MotorControllerProfile, PhaseBindingDefinition,
        SEED_CONTROLLER_PROFILES, SEED_PHASE_BINDINGS,
    )
    from motors.scale_goals import (
        ClockScaleDefinition, MotorGoalSpec,
    )
    from motors.clock_views import ClockViewDefinition
    from motors.clock_scene import ClockSceneLayerDefinition
except ImportError as _exc:
    # The stub tuple must list EVERY name the try block imports —
    # stub_feature_symbols already maps SEED_* to [] and everything
    # else to None, so the three SEED_MOTOR_* names belong here
    # rather than in hand-written `= []` lines after the block
    # (which is what the lazy-import selftest was flagging).
    _stub_missing_feature('motors', _exc, globals(), (
        'MotorDesignDefinition', 'MotorVerificationRun',
        'SEED_MOTOR_DESIGNS', 'MotorControllerProfile',
        'PhaseBindingDefinition', 'SEED_CONTROLLER_PROFILES',
        'SEED_PHASE_BINDINGS', 'SEED_MOTOR_MATERIALS_3D',
        'SEED_MOTOR_PART_SHAPES', 'SEED_MOTOR_SIM_SPACES',
        'SEED_LAVET_PART_SHAPES', 'SEED_LAVET_SIM_SPACES',
        'SEED_LAVET_V2_PART_SHAPES', 'SEED_LAVET_V2_SIM_SPACES',
        'SEED_M1_PART_SHAPES', 'SEED_M1_SIM_SPACES',
        'SEED_M3_PART_SHAPES', 'SEED_M3_SIM_SPACES',
        'MotorPartDefinition', 'SEED_MOTOR_PARTS',
        'SEED_EQUATION_ROWS',
        'ClockScaleDefinition', 'MotorGoalSpec',
        'ClockViewDefinition', 'ClockSceneLayerDefinition',
    ))
# mesh-1: license-GATED external mesh catalog + the fit engine
# (borrowed meshes measured against our vector organ definitions).
try:
    from meshassets.mesh_asset_basis import (
        MeshAssetReference, MeshAssetSource, OrganMeshChoice,
    )
    from meshassets.mesh_asset_seed import (
        SEED_MESH_ASSETS, SEED_MESH_SOURCES,
    )
except ImportError as _exc:
    _stub_missing_feature('meshassets', _exc, globals(), (
        'MeshAssetSource', 'MeshAssetReference', 'OrganMeshChoice',
        'SEED_MESH_SOURCES', 'SEED_MESH_ASSETS',
    ))
# Gear trains (gr-1) — the mechanical twin of the reluctance
# network: shaft nodes as graph nodes, meshes as edges.
try:
    from gears.gear_basis import (
        GearDefinition, GearMeshDefinition, GearTrainDefinition,
        GearTypeDefinition, GearVerificationRun,
        ShaftNodeDefinition,
    )
    from gears.gear_seed import (
        SEED_GEAR_MESHES, SEED_GEAR_TRAINS, SEED_GEAR_TYPES,
        SEED_GEARS, SEED_SHAFT_NODES,
    )
except ImportError as _exc:
    _stub_missing_feature('gears', _exc, globals(), (
        'GearTypeDefinition', 'GearDefinition',
        'GearMeshDefinition', 'ShaftNodeDefinition',
        'GearTrainDefinition', 'GearVerificationRun',
        'SEED_GEAR_TYPES', 'SEED_GEARS', 'SEED_GEAR_MESHES',
        'SEED_SHAFT_NODES', 'SEED_GEAR_TRAINS',
    ))
# Odoo ERP connector — instance configs + sim/ops write guards (od-3).
try:
    from odooconnect.odoo_basis import OdooInstanceConfig
    from odooconnect.odoo_bindings import (
        OdooModelBinding, OdooSyncReceipt, SEED_ODOO_BINDINGS,
    )
    from odooconnect.odoo_scenarios import (
        BusinessScenarioDefinition, SEED_BUSINESS_SCENARIOS,
    )
    from odooconnect.odoo_seed import SEED_ODOO_INSTANCES
except ImportError as _exc:
    _stub_missing_feature('odooconnect', _exc, globals(), (
        'OdooInstanceConfig', 'OdooModelBinding', 'OdooSyncReceipt',
        'BusinessScenarioDefinition', 'SEED_ODOO_INSTANCES',
        'SEED_ODOO_BINDINGS', 'SEED_BUSINESS_SCENARIOS',
    ))
# Bio wax sources (wax-1) + the unifying supply-chain ledger (chain-1).
try:
    from waxsupply.wax_basis import WaxSourceDefinition
    from waxsupply.wax_seed import SEED_WAX_SOURCES
except ImportError as _exc:
    _stub_missing_feature('waxsupply', _exc, globals(), (
        'WaxSourceDefinition', 'SEED_WAX_SOURCES',
    ))
try:
    from supplychain.chain_basis import (
        SupplyChainDefinition, SupplyFlow, SupplyNode,
    )
    from supplychain.chain_seed import (
        SEED_SUPPLY_CHAINS, SEED_SUPPLY_FLOWS, SEED_SUPPLY_NODES,
    )
    from supplychain.sourcing_basis import (
        PriceCitation, ProductFormula, ProductInputRequirement,
        SourcePreferencePolicy, SupplySourceProfile,
    )
    from supplychain.sourcing_seed import (
        SEED_PRICE_CITATIONS, SEED_PRODUCT_FORMULAS,
        SEED_PRODUCT_REQUIREMENTS, SEED_SOURCE_POLICIES,
        SEED_SUPPLY_SOURCES,
    )
except ImportError as _exc:
    _stub_missing_feature('supplychain', _exc, globals(), (
        'SupplyChainDefinition', 'SupplyFlow', 'SupplyNode', 'SEED_SUPPLY_CHAINS',
        'SEED_SUPPLY_FLOWS', 'SEED_SUPPLY_NODES',
        'SupplySourceProfile', 'PriceCitation',
        'SourcePreferencePolicy', 'ProductInputRequirement',
        'ProductFormula', 'SEED_SUPPLY_SOURCES',
        'SEED_PRICE_CITATIONS', 'SEED_SOURCE_POLICIES',
        'SEED_PRODUCT_REQUIREMENTS', 'SEED_PRODUCT_FORMULAS',
    ))
# Topology orchestration (top-1): the swarm/compose topology as
# object-tree data — machines, instances, module assignments +
# dependency edges, typed connections, desired vs observed state.
from topology.topology_basis import (
    InstanceDefinition, OrchestrationTarget, PolariNodeMachine,
)
from topology.topology_modules import (
    ModuleAssignment, ModuleDependencyEdge,
)
from topology.topology_links import ServiceConnection
from topology.topology_state import (
    TopologyDefinition, TopologyObservation,
)
# tt-11: testing over the topology — suite runs + integration pings
# as observed-state rows (never seeded).
from topology.topology_testing import IntegrationPing, TopologyTestRun
from topology.move_operations import MoveOperation
# tt-12: Polari-Apps — module configurations per use-case; plans are
# exportable JSON packages the pol CLI deploys (rows only).
try:
    from polariapps.apps_basis import (
        AppDeploymentPlan, PolariAppDefinition,
    )
    from polariapps.apps_seed import SEED_POLARI_APPS
except ImportError as _exc:
    _stub_missing_feature('polariapps', _exc, globals(), (
        'AppDeploymentPlan', 'PolariAppDefinition', 'SEED_POLARI_APPS',
    ))
from topology.topology_seed import (
    SEED_INSTANCE_DEFINITIONS, SEED_MODULE_ASSIGNMENTS,
    SEED_MODULE_DEPENDENCY_EDGES, SEED_NODE_MACHINES,
    SEED_ORCHESTRATION_TARGETS, SEED_SERVICE_CONNECTIONS,
    SEED_TOPOLOGY_DEFINITIONS,
)
# Tech tree (tt-3): technologies with theory/real/business/politics
# segments; completion always DERIVED (techtree_analysis), edges
# derived from depends_on_json with tt-1 transient designation.
try:
    from techtree.techtree_basis import (
        TechDependencyEdge, TechNode, TechSegment, TechSegmentAssignment,
        TechTreeDefinition,
    )
    from techtree.techtree_content import (
        BusinessModelDefinition, BusinessOutcome, PolicyDefinition,
        RealArtifact,
    )
    from techtree.techtree_seed import (
        SEED_BUSINESS_MODELS, SEED_OSEB_POLARI_MODULES,
        SEED_POLICY_DEFINITIONS, SEED_REAL_ARTIFACTS, SEED_TECH_NODES,
        SEED_TECH_SEGMENT_ASSIGNMENTS, SEED_TECH_TREE_DEFINITIONS,
    )
except ImportError as _exc:
    _stub_missing_feature('techtree', _exc, globals(), (
        'TechDependencyEdge', 'TechNode', 'TechSegment', 'TechSegmentAssignment',
        'TechTreeDefinition', 'BusinessModelDefinition', 'BusinessOutcome', 'PolicyDefinition',
        'RealArtifact', 'SEED_BUSINESS_MODELS', 'SEED_OSEB_POLARI_MODULES', 'SEED_POLICY_DEFINITIONS',
        'SEED_REAL_ARTIFACTS', 'SEED_TECH_NODES', 'SEED_TECH_SEGMENT_ASSIGNMENTS', 'SEED_TECH_TREE_DEFINITIONS',
    ))
# Resource profiles (res-2): each module/engine's floor, scalability,
# character, and storage-tier recommendation — the admission basis.
from resources.profile_basis import ModuleResourceProfile
from xr.xr_settings import (
    XrGlobalSettings, XrTypeDefault, XrInterfaceVariant,
    SEED_XR_GLOBAL_SETTINGS, SEED_XR_TYPE_DEFAULTS,
)
from resources.profile_seed import SEED_MODULE_RESOURCE_PROFILES
# Schema stabilization: per-class trust state + captured OOPS events
# (stat-freezing for object schemas; typing work exits the tree).
from polariDataTyping.schema_stability_basis import (
    SchemaDeviationEvent, SchemaStabilityProfile,
)
# Testing accountability spine (acct-0): checks as tree objects.
# TEST-BUILD ONLY — `testing` is an OPT_IN package (module_gating),
# so these classes register/seed only under POLARI_TEST_BUILD or an
# explicit POLARI_MODULES entry; import alone registers nothing.
try:
    from testing.capability_basis import CapabilityCheck, CheckRun
    from testing.testing_seed import SEED_CAPABILITY_CHECKS
except ImportError as _exc:
    _stub_missing_feature('testing', _exc, globals(), (
        'CapabilityCheck', 'CheckRun', 'SEED_CAPABILITY_CHECKS',
    ))
# gRPC contracts (grpc-1): per-class exposure KNOB + append-only
# contract versions, generated from stabilization snapshots only.
try:
    from grpcbridge.contract_basis import (
        GrpcExposure, ProtoContractVersion,
    )
    # Polari Hardware Bridge (grpc-j1): generatable Java bridge apps —
    # simulation-first, per-bridge knob rows.
    from grpcbridge.java_bridge_basis import HardwareBridgeDefinition
    # hwsim-1: hardware rig digital twins (Renode firmware streams here).
    from grpcbridge.hwsim_basis import SimRigState, SEED_SIM_RIGS
except ImportError as _exc:
    _stub_missing_feature('grpcbridge', _exc, globals(), (
        'GrpcExposure', 'ProtoContractVersion', 'HardwareBridgeDefinition', 'SimRigState',
        'SEED_SIM_RIGS',
    ))
# msci-26: L3 MD + L2 mesoscale model definitions + seeds.
from materialsScience.md_model_definition import MDModelDefinition
from materialsScience.meso_model_definition import MesoModelDefinition
from materialsScience.l2_l3_models_seed import (
    SEED_MD_MODELS, SEED_MESO_MODELS, SEED_L2_L3_SCALE_ROWS,
    SEED_DERIVED_VFC_MODELS,
)
# hwsim-3: FPGA register maps as DATA (every register = a knob row;
# Verilog/C/testbench artifacts generate FROM the rows).
try:
    from hwfpga.fpga_basis import (
        FpgaRegisterState, RegisterDefinition, RegisterMapDefinition,
        SEED_FPGA_STATES, SEED_REGISTER_MAPS, SEED_REGISTERS,
    )
    # The 4x4 LED demo grid (driver knob: fpga | mcu profiles).
    from hwfpga.led_basis import LedMatrix4x4State, SEED_LED_MATRICES
except ImportError as _exc:
    _stub_missing_feature('hwfpga', _exc, globals(), (
        'FpgaRegisterState', 'RegisterDefinition', 'RegisterMapDefinition', 'SEED_FPGA_STATES',
        'SEED_REGISTER_MAPS', 'SEED_REGISTERS', 'LedMatrix4x4State', 'SEED_LED_MATRICES',
    ))
# Material-derived electronic devices (materials -> SPICE ladder).
try:
    from electrodevice.device_basis import (
        CircuitRunResult, ElectronicDeviceDefinition, SpiceModelCard,
        SEED_DEVICES,
    )
    from electrodevice.semiconductor import (
        SemiconductorProfile, SEED_SEMICONDUCTOR_PROFILES,
    )
    from electrodevice.device_validator import DeviceValidationReport
    from electrodevice.photo_basis import (
        PhotoAbsorberDefinition, SolarLayerDefinition,
        SolarStackDefinition, SEED_PHOTO_ABSORBERS, SEED_SOLAR_LAYERS,
        SEED_SOLAR_STACKS,
    )
except ImportError as _exc:
    _stub_missing_feature('electrodevice', _exc, globals(), (
        'CircuitRunResult', 'ElectronicDeviceDefinition', 'SpiceModelCard', 'SEED_DEVICES',
        'SemiconductorProfile', 'SEED_SEMICONDUCTOR_PROFILES', 'DeviceValidationReport', 'PhotoAbsorberDefinition',
        'SolarLayerDefinition', 'SolarStackDefinition', 'SEED_PHOTO_ABSORBERS', 'SEED_SOLAR_LAYERS',
        'SEED_SOLAR_STACKS',
    ))
# Formulation searches as OBJECTS (object-coherence: the wax derivation
# is configurable/runnable at these rows, not just API knobs).
from materialsScience.formulation_search_definition import (
    FormulationSearchDefinition,
)
from materialsScience.formulation_search_run import FormulationSearchRun
from materialsScience.formulation_candidate_result import (
    FormulationCandidateResult,
)
from materialsScience.formulation_search_seed import (
    SEED_FORMULATION_SEARCHES,
)
# The wax derivation as a multi-scale simulation (formulationSearch
# stage over the seeded search definition).
from materialsScience.wax_derivation_seed import (
    SEED_WAX_DERIVATION_MSIMS,
)
# The recursive composition: wax-multiscale nests wax-derivation as a
# sub-model + the two configured FEM/DFT model definitions (msci-19).
from materialsScience.wax_multiscale_seed import (
    SEED_WAX_MULTISCALE_MSIMS,
)
# The materials-basis + formulation-search DisplayDefinition pages.
from materialsScience.msci_pages_seed import SEED_MSCI_PAGE_DISPLAYS
# The aquaponics-pot-shape phase 2 pot-geometry-editor DisplayDefinition page.
try:
    from aquaponics.aquaponics_pages_seed import SEED_AQUAPONICS_PAGE_DISPLAYS
except ImportError as _exc:
    _stub_missing_feature('aquaponics', _exc, globals(), (
        'SEED_AQUAPONICS_PAGE_DISPLAYS',
    ))
# No-code pages for the modules that had APIs but no UI (nutrition,
# vermicompost, tanks, biomining, microalgae, wax, supply chain,
# morphology, authority) — pure class-rows-table/api-json-panel data.
from polariApiServer.module_pages_seed import SEED_MODULE_PAGE_DISPLAYS
# The engine-model layer: the FEM/DFT catalog + the specialized
# domain-shaped model definitions (msci-15).
from materialsScience.engine_model_template import EngineModelTemplate
from materialsScience.fem_model_definition import FEMModelDefinition
from materialsScience.dft_model_definition import DFTModelDefinition
from materialsScience.engine_model_seed import (
    SEED_DFT_MODELS, SEED_ENGINE_MODEL_TEMPLATES, SEED_FEM_MODELS,
)
# Standard material families (sol-gel / geopolymer / alumina / CNT /
# N-doped CNT) as coherent identities + piecemeal scale rows, with
# executable levels backed by configured FEM/DFT models (msci-20).
from materialsScience.standard_materials_seed import (
    SEED_STANDARD_DFT_MODELS, SEED_STANDARD_FEM_MODELS,
    SEED_STANDARD_MATERIALS, SEED_STANDARD_SCALE_DEFINITIONS,
)
# Solid-state physics (ssp-1): crystal lattices as first-class rows —
# the structural representation the L3/L4 rungs share.
from materialsScience.crystal_structure_definition import (
    CrystalStructureDefinition,
)
from materialsScience.crystal_structures_seed import (
    SEED_CRYSTAL_STRUCTURES,
)
# ssp-2: importing crystal_scene_seed appends the lattice 3D scenes +
# element materials to the shared simSpace3D seed lists
# (trigger-on-import, the waxprint sim_seed idiom).
from materialsScience import crystal_scene_seed  # noqa: F401
from materialsScience.crystal_scene_seed import (
    SEED_SSP_PAGE_DISPLAYS,
)
# Simulations module — composed *SimState classes + variable metadata
# + config tie-in + storage predictor.
from simulations.sim_variable import SimVariable
from simulations.sim_space_evaluation_equation import SimSpaceEvaluationEquation
from simulations.simulation_execution_solution import SimulationExecutionSolution
from simulations.pendulum_bob_sim_state import PendulumBobSimState
from simulations.pendulum_string_sim_state import PendulumStringSimState
from simulations.newtonian_pendulum_bob_sim_state import NewtonianPendulumBobSimState
from simulations.newtonian_pendulum_viz_states import (
    NewtonianPendulumRodSimState,
)
from simulations.simulation_definition import SimulationDefinition
from simulations.simulation_run import SimulationRun
from simulations.simulation_api import SimulationAPI
from simulations.seed_data import (
    SEED_PENDULUM_BOB_ROWS,
    SEED_PENDULUM_STRING_ROWS,
    SEED_SIM_VARIABLES,
    SEED_PENDULUM_EQUATIONS,
    SEED_PENDULUM_EVALUATION_EQUATIONS,
    SEED_PENDULUM_STEP_SOLUTIONS,
    SEED_PENDULUM_STEP_SOLUTION_DEFS,
    SEED_PENDULUM_STEP_EQUATIONS,
    SEED_PENDULUM_STEP_TEST_CASES,
    SEED_SIMULATION_DEFINITIONS,
    SEED_SIMULATION_RUNS,
    SEED_PENDULUM_SIMSPACES,
    SEED_PENDULUM_BINDINGS,
)
# Importing newtonian_pendulum_seed registers the Newtonian sim into the
# SEED_PENDULUM_* lists above (it extends them in place) and provides the
# step-0 IC row seeds. Keep this AFTER the seed_data import.
from simulations.newtonian_pendulum_seed import (
    SEED_NEWTON_BOB_ROWS,
    SEED_NEWTON_ROD_ROWS,
)
# Wind-field space + its coupling into the Newtonian pendulum (the first
# multi-scale composition). Extends the SEED_PENDULUM_* lists AND the
# matrices SEED_MATRIX_EQUATIONS in place — keep AFTER newtonian_pendulum_seed
# (it mutates the newtonian scene's bound classes).
from simulations.wind_field_grid_sim_state import WindFieldGridState
from simulations.simulation_coupling_definition import SimulationCouplingDefinition
from simulations.wind_field_seed import (
    SEED_WIND_GRID_ROWS,
    SEED_NEWTON_WIND_BOB_ROWS,
    SEED_NEWTON_WIND_ROD_ROWS,
    SEED_SIMULATION_COUPLINGS,
)
# Material condensation space (Milestone B) — the first-principles stage:
# search T/P until the substance condenses into a solid ball; the gate
# derives the ball's properties into the pendulum's initial conditions.
from simulations.material_condensation_state import MaterialCondensationState
from simulations.material_space_seed import SEED_MATERIAL_ROWS
# Multi-Scale Simulation Page objects: the tying definition (spaces +
# couplings + stages + panels) and configured IC interfaces. Keep AFTER
# the wind seed (the demo references the wind coupling by name).
from simulations.multi_scale_simulation_definition import MultiScaleSimulationDefinition
from simulations.initial_condition_interface_definition import (
    InitialConditionInterfaceDefinition,
)
from simulations.multi_scale_seed import (
    SEED_MULTI_SCALE_SIMS,
    SEED_IC_INTERFACES,
    SEED_MSIM_GRAPHS,
)
# Multi-scale FAMILIES: the profile object naming what a class of msims
# has in common (scale levels, stage shapes, fidelity ladder, panel
# roster) + conformance checking. Declarative naming, never codegen.
from simulations.multi_scale_simulation_profile import (
    MultiScaleSimulationProfile,
)
from simulations.multi_scale_profile_seed import SEED_MSIM_PROFILES
# Resource-aware simulation: measured per-step cost profiles (created
# lazily by the runner's step-cost tracker — no seed rows).
from simulations.step_cost_profile import StepCostProfile
# Peer + module handshake (twin-Polari / node integration).
from polariPeers.peer_node import PeerNode
from polariPeers.polari_module import PolariModule
from moduleService.module_boot_records import ModuleBootRecord
from polariPeers.module_source_config import (
    ModuleSourceConfig, SEED_MODULE_SOURCE_CONFIGS,
)
# Dependency edges (python libs + polari boundaries) as persisted,
# inspectable rows (msci-21).
from polariPeers.polari_module_dependency import PolariModuleDependency
from polariPeers.peers_api import PeersAPI
# Mesh convergence Phase 1: bilateral admission agreements.
from polariPeers.peer_agreement import PeerAgreement
from polariPeers.agreements_api import AgreementsAPI
from polariApiProfiler.apiProfilerAPI import (
    APIProfilerQueryAPI,
    APIProfilerMatchAPI,
    APIProfilerBuildAPI,
    APIProfilerCreateClassAPI,
    APIProfilerTemplatesAPI,
    APIProfilerDetectTypesAPI,
    APIDomainAPI,
    APIEndpointAPI,
    APIEndpointFetchAPI
)
from polariApiProfiler.apiProfile import APIProfile
from polariApiProfiler.apiDomain import APIDomain
from polariApiProfiler.apiEndpoint import APIEndpoint
from accessControl.polariPermissionSet import polariPermissionSet
from accessControl.polariUserGroup import UserGroup
from accessControl.polariUser import User
from accessControl.auth_middleware import AuthContextMiddleware
from wsgiref import simple_server
import falcon
import secrets
import subprocess

# Dynamic module discovery
from moduleService.moduleDiscovery import discover_available_modules, apply_metadata_type_overrides

# Import configuration loader for CORS origins
try:
    from config_loader import config
    CORS_ORIGINS = config.get('api.cors_origins', ['*'])
    # If it's a string (from env var), split it
    if isinstance(CORS_ORIGINS, str):
        CORS_ORIGINS = [o.strip() for o in CORS_ORIGINS.split(',')]
except ImportError:
    # Fallback if config_loader not available
    CORS_ORIGINS = ['*']

# mp-3: one honest boot line per feature module whose code is absent.
for _line in _module_loading_boot_report():
    print(_line, flush=True)


class CORSExtraHeadersMiddleware:
    """Adds CORS headers that Falcon 4.x built-in CORSMiddleware doesn't cover.
    Falcon's CORSMiddleware handles Allow-Origin, Allow-Credentials, and OPTIONS preflight.
    This adds Allow-Headers and Max-Age which are needed for preflight responses.
    Note: In staging/prod, nginx also sets these headers. Duplicates are tolerated."""
    def process_response(self, req, resp, resource, req_succeeded):
        resp.set_header('Access-Control-Allow-Headers',
                        'Content-Type, Authorization, Accept, Origin, X-Requested-With')
        resp.set_header('Access-Control-Max-Age', '86400')

class apiError(Exception):
    @staticmethod
    async def handle(ex, req, resp, params):
        # TODO: Log the error, clean up, etc. before raising
        raise falcon.HTTPInternalServerError()

#Creates a server which either generates an api-endpoint for each object defined in the manager as well as for each dataChannel, or maps them to an endpoint on another server
#which handles that responsibility instead.  The Server can indicate certain polyTypedObjects & dataChannels as 
class polariServer(treeObject):
    @treeObjectInit
    def __init__(self, name="NEW_SERVER", displayName="NEW_POLARI_SERVER", hostSystem=None, serverChannel=None, serverDataStream=None):
        self.name = name
        #Creates a random salt for hashing passwords for validating users.
        #THE VALUES IN THIS DICT SHOULD NOT BE CHANGED OR ALL PASSWORDS WILL BE RESET.
        #Contains a set of salts that define password hashes for given time periods
        #or just a * for all time periods.
        self.serverPasswordSaltDict = {"*":secrets.token_urlsafe(16)}
        #Temporary Users and Registered Users should be at least equal so that all Users can
        #login simultaneously if needed, so long as no unaccounted for or malicious people or bots
        #are attempting to occupy space as temporary Users.
        #Analysis of the server overall should be made to determine what these limits
        #should be set as.
        self.temporaryUsersLimit = 10
        self.registeredUsersLimit = 10
        self.displayName = displayName
        #Password requirements
        self.passwordRequirements = {"min-length":8, "max-length":24, "min-special-chars":1, "min-nums":2}
        self.publicFrontendKey = None
        self.privateFrontendKey = None
        # Configure CORS: Falcon 4.x built-in handles Origin, Credentials, and OPTIONS preflight.
        # CORSExtraHeadersMiddleware adds Allow-Headers and Max-Age.
        # In staging/prod, nginx also handles CORS (including OPTIONS interception).
        allow_origins = '*' if '*' in CORS_ORIGINS else CORS_ORIGINS
        allow_creds = '*' if '*' in CORS_ORIGINS else allow_origins
        # mlb-1: the boot registry exists on EVERY boot (monolithic
        # boots mark themselves all-online, so the middleware is a
        # no-op there); the loading middleware turns not-yet-admitted
        # modules' requests into honest 503s instead of empty data.
        from polariApiServer.lazy_boot import (
            HealthEndpoint, ModuleBootRegistry, ModuleLoadingMiddleware,
            ModulesStatusEndpoint,
        )
        # gm-2: the quiesce seam every stateful move calls first.
        from polariApiServer.quiesce import (
            QuiesceEndpoint, QuiesceMiddleware, QuiesceState,
        )
        self.bootRegistry = ModuleBootRegistry()
        self.quiesceState = QuiesceState()
        self.falconServer = falcon.App(
            middleware=[
                falcon.CORSMiddleware(allow_origins=allow_origins, allow_credentials=allow_creds),
                CORSExtraHeadersMiddleware(),
                # Populates req.context.user_info / req.context.roles from
                # the incoming Bearer token. Lenient in Phase 1 — never
                # rejects, just plumbs identity for downstream gating.
                AuthContextMiddleware(),
                ModuleLoadingMiddleware(self),
                QuiesceMiddleware(self.quiesceState),
            ]
        )
        # /api/health (net-new, mlb-1): 200 at core-data-ready;
        # /api/modules/status (mlb-3): the bring-up summary doc;
        # /api/quiesce* (gm-2): the stateful-move write gate.
        HealthEndpoint(self)
        ModulesStatusEndpoint(self)
        QuiesceEndpoint(self, self.quiesceState)
        self.active = False
        # STOMP WebSocket server reference (set after startup in initLocalhostPolariServer)
        # Declared here during @treeObjectInit so it's a known variable on the tree.
        # The actual StompWebSocketServer instance is assigned post-init via
        # object.__setattr__ since it contains non-serializable asyncio internals.
        # Note: stompServer is stored as a module-level singleton in
        # stompWebSocketServer.py (not on this instance) to avoid tree
        # serialization issues — use get_stomp_server() to access it.
        #Defines endpoints or mapping to remote endpoints which allow for CRUD access to all objects of the server's manager as well as it's subordinate manager objects.
        managerIdTuple = self.manager.getInstanceIdentifiers(self.manager)
        self.objectEndpoints = {}
        #Defines endpoints or mapping to remote endpoints which allow for CRUD access through dataChannel specifications on a server's manager as well as it's subordinate manager objects.
        self.dataChannelEndpoints = {}
        #A variable used for testing purposes, determines how long the server should be active.
        self.timeActiveInMinutes = 5
        #Records the last time the server on the nodeJS side
        self.lastCycleTime = time.localtime()
        #Sets up the primary data channel which is used as a file relay for information between the back-end and the server
        #if(serverChannel == None):
            #print('Setting manager for dataChannel to ', self.manager)
        #    self.serverChannel = dataChannel(name=name + '_serverChannel', manager=(self.manager))
        #else:
        #    self.serverChannel = serverChannel
        #print('ServerChannel: ', self.serverChannel)
        typing = self.manager.getObjectTyping(self.__class__)
        #print('Typing Dict for polServer: ')
        #Get the typing for the manager object which houses this server.
        managerType = type(self.manager).__name__
        #SECURE: Does not grant any visibility by default.
        self.secureManagerObjects = []
        #PROTECTED: Grants only read by default.
        self.protectedManagerObjects = [managerType]
        self.tempUsersList = []
        self.tempUsersDict = {}
        self.usersList = [User(username="topadmin", password="topadmin", manager=self.manager)]
        self.usersDict = {self.usersList[0].username:self.usersList[0]}
        self.userGroupsList = [UserGroup(name="adminGroup", assignedUsers=[self.usersList[0]], manager=self.manager)]
        self.userGroupsDict = {self.userGroupsList[0].name:self.userGroupsList[0]}
        #PUBLIC: Anyone with access to read all and create by default.
        #anything which someone has created will be granted modify access by default.
        #Secondary permissions grant update based on creators or other criteria.
        self.managersOnServer = [self.manager]
        self.publicManagersList = []
        self.apiRestrictedObjects = ["isoSys"]
        self.secureTreeObjects = []
        self.protectedTreeObjects = ["polyTypedObject", "polyTypedVar", "polariServer", "managedDatabase"]
        self.publicTreeObjectsList = []
        #Creates an endpoint for the given manager object for the specific channel object Ex:
        #  https://someURL.com/manager-managerObjectType-(id0:val0, id1:val1, id2:val2, ...)/channel/channelName
        self.uriList = []
        objList = [self, self.manager]
        serverTouchPointAPI = polariAPI(apiName='', polServer=self, minAccessDict={'R':{"polariAPI":"*","polariCRUDE":"*", "polariServer":"*", "polyTypedObject":"*", "polyTypedVariable":"*"}}, minPermissionsDict={'R':{"polariAPI":"*","polariCRUD":"*", "polariServer":"*"}}, manager=self.manager)
        #Create User API - Creates an API for the user to temporarily register with until they either login or create their own actual registration.
        tempRegisterAPI = polariAPI(apiName='tempRegister', polServer=self, minAccessDict={'E':{"polariServer":"*"}}, minPermissionsDict={'E':{"polariServer":"tempRegister"}}, manager=self.manager)
        #Update temp registration to actual registration
        registerAPI = polariAPI(apiName='register', polServer=self, minAccessDict={'E':{"polariServer":"*"}}, minPermissionsDict={'E':{"polariServer":"register"}}, manager=self.manager)
        #Change over to the official registration, transfer over all instances owned by the current temporary registration
        #to the official one.  Then delete the temporary registration.
        loginAPI = polariAPI(apiName='login', polServer=self, minAccessDict={'E':{"polariServer":"*"}}, minPermissionsDict={'E':{"polariServer":"login"}}, manager=self.manager)

        # Create custom endpoint for managerObject
        managerObjectEndpoint = managerObjectAPI(polServer=self, manager=self.manager)

        # Create custom endpoint for polyTypedObject
        polyTypedObjectEndpoint = polyTypedObjectAPI(polServer=self, manager=self.manager)

        # Create custom endpoint for class instance counts (used/unused classes)
        classInstanceCountsEndpoint = classInstanceCountsAPI(polServer=self, manager=self.manager)

        # Create API discovery endpoint (lists all available endpoints)
        apiDiscoveryEndpoint = APIDiscoveryAPI(polServer=self, manager=self.manager)

        # Create custom endpoint for dynamic class creation. Also held on
        # `self` so the seed loader can call `_createDynamicClass()` directly
        # to register seeded solution boundClasses (see `_seedBoundClasses`).
        # The local binding stays so `customAPIsList` below still resolves.
        createClassEndpoint = createClassAPI(polServer=self, manager=self.manager)
        self.createClassEndpoint = createClassEndpoint

        # Create state-space API endpoints for no-code system
        stateSpaceClassesEndpoint = StateSpaceClassesAPI(polServer=self, manager=self.manager)
        stateSpaceConfigEndpoint = StateSpaceConfigAPI(polServer=self, manager=self.manager)
        stateDefinitionEndpoint = StateDefinitionAPI(polServer=self, manager=self.manager)

        # Create API Profiler endpoints
        apiProfilerQueryEndpoint = APIProfilerQueryAPI(polServer=self, manager=self.manager)
        apiProfilerMatchEndpoint = APIProfilerMatchAPI(polServer=self, manager=self.manager)
        apiProfilerBuildEndpoint = APIProfilerBuildAPI(polServer=self, manager=self.manager)
        apiProfilerCreateClassEndpoint = APIProfilerCreateClassAPI(polServer=self, manager=self.manager)
        apiProfilerTemplatesEndpoint = APIProfilerTemplatesAPI(polServer=self, manager=self.manager)
        apiProfilerDetectTypesEndpoint = APIProfilerDetectTypesAPI(polServer=self, manager=self.manager)

        # Create API Domain and Endpoint management endpoints
        apiDomainEndpoint = APIDomainAPI(polServer=self, manager=self.manager)
        apiEndpointEndpoint = APIEndpointAPI(polServer=self, manager=self.manager)
        apiEndpointFetchEndpoint = APIEndpointFetchAPI(polServer=self, manager=self.manager)

        # Create API Configuration endpoint for viewing/managing CRUDE permissions
        apiConfigEndpoint = ApiConfigAPI(polServer=self, manager=self.manager)

        # Create Module Management endpoint for enabling/disabling modules
        modulesEndpoint = ModulesAPI(polServer=self, manager=self.manager)

        # Create System Info endpoint for diagnostics and resource profiling
        systemInfoEndpoint = systemInfoAPI(polServer=self, manager=self.manager)

        # Create in-app AI assistant endpoint (Phase 4 — text/voice/XR panel backend)
        aiChatEndpoint = aiChatAPI(polServer=self, manager=self.manager)

        # Create reasoning-provider management endpoint (select/auth/validate)
        providersEndpoint = providersAPI(polServer=self, manager=self.manager)

        # Create in-app AI action loop endpoint (gated propose->confirm->execute)
        aiActionsEndpoint = aiActionsAPI(polServer=self, manager=self.manager)

        # Create endpoint for updating class configuration flags
        updateClassConfigEndpoint = UpdateClassConfigAPI(polServer=self, manager=self.manager)

        # Create Tile Generator endpoint for .mbtiles generation
        tileGeneratorEndpoint = TileGeneratorAPI(polServer=self, manager=self.manager)

        # Create Object Storage endpoint for MinIO connection management
        objectStorageEndpoint = ObjectStorageAPI(polServer=self, manager=self.manager)

        # Create Solution Code Generator endpoint for backend code generation
        solutionCodeGenEndpoint = SolutionCodeGeneratorAPI(polServer=self, manager=self.manager)

        # Create Solution Execution endpoint for running no-code solutions
        solutionExecEndpoint = SolutionExecutionAPI(polServer=self, manager=self.manager)

        # Create Equation Execution endpoint for testing / running calculus equations
        equationExecEndpoint = EquationExecutionAPI(polServer=self, manager=self.manager)

        # Matrix endpoint — evaluate / validate a MatrixDefinition (numeric
        # resolution, equation-typed elements, matrix-of-matrices composition).
        matrixEndpoint = MatrixAPI(polServer=self, manager=self.manager)

        # Matrix Equation endpoint — evaluate / validate a
        # MatrixEquationDefinition (operations over matrices / equations).
        matrixEquationEndpoint = MatrixEquationAPI(polServer=self, manager=self.manager)

        # Create Solution Version endpoint for atomic version snapshots
        solutionVersionEndpoint = SolutionVersionAPI(polServer=self, manager=self.manager)

        # Create WebSocket Status endpoint for STOMP server inspection
        wsStatusEndpoint = WsStatusAPI(polServer=self, manager=self.manager)

        # Phase-1 auth plumbing: introspection endpoints powering the
        # Permissions → Auth Diagnostics page. AuthMe returns identity
        # from the request's Bearer token; AuthJwksHealth reports whether
        # the backend itself can reach + parse Keycloak's JWKS, so the
        # UI can tell "JWKS unreachable" apart from "token rejected".
        authMeEndpoint = AuthMeAPI(polServer=self, manager=self.manager)
        authJwksHealthEndpoint = AuthJwksHealthAPI(polServer=self, manager=self.manager)

        # Phase-2 permissions: Role tree-object (synced from Keycloak,
        # role-indexed grants) + per-user effective-permissions endpoint.
        # The transient user matrix is keyed by `sub` (KC UUID) — no
        # user PII is ever persisted by the framework.
        roleEndpoint = RoleAPI(polServer=self, manager=self.manager)

        # SimSpace snapshot dispatcher — single URL that compiles either a
        # 2D or 3D scene based on the definition's dimensionality flag.
        simSpaceEndpoint = SimSpaceAPI(polServer=self, manager=self.manager)

        # Simulation endpoints — storage prediction + run introspection.
        # Runtime engine (the part that actually iterates a step function)
        # lands in the next phase alongside simulation-kind no-code.
        simulationEndpoint = SimulationAPI(polServer=self, manager=self.manager)

        # Peer + module handshake — twin-Polari instances register with a
        # shared token, probe each other's simulations and modules.
        peersEndpoint = PeersAPI(polServer=self, manager=self.manager)

        # Materials basis: engine capability + scale-definition execution
        # + scale-presence gates (FEM/DFT via local libs or msci-engines).
        from materialsScience.scale_execution_api import ScaleExecutionAPI
        msciEndpoint = ScaleExecutionAPI(polServer=self, manager=self.manager)

        # Scale-presence accountability: the materials x levels matrix
        # + per-level defined/partial/missing pages (msci-24).
        from materialsScience.scale_presence_api import ScalePresenceAPI
        presenceEndpoint = ScalePresenceAPI(
            polServer=self, manager=self.manager)

        # Per-material detail: properties + meanings + scenario context
        # + per-level rows behind the material detail view (msci-28).
        from materialsScience.material_detail_api import MaterialDetailAPI
        materialDetailEndpoint = MaterialDetailAPI(
            polServer=self, manager=self.manager)

        # ssp-1: crystal-structure list/detail (facts + atoms + bonds).
        from materialsScience.crystal_structure_api import (
            CrystalStructureAPI,
        )
        crystalStructureEndpoint = CrystalStructureAPI(
            polServer=self, manager=self.manager)

        # PSPP: dataset curves + reaction network + composition
        # grading + cure progress (pspp-V — every chart generated
        # from rows so a book figure proofs against live data).
        if _feature_available('pspp'):
            from pspp.pspp_api import PsppAPI
            psppEndpoint = PsppAPI(polServer=self, manager=self.manager)

        # Context-based scoring: concept list + the scoring pipeline
        # (normalize -> context-match -> weight -> levelize) (scr-1).
        # mp-3: every feature-module endpoint below is gated on the
        # module's code being downloaded + enabled — an absent module
        # registers no routes (the /modules surface says why).
        if _feature_available('scoring'):
            from scoring.scoring_api import ScoringAPI
            scoringEndpoint = ScoringAPI(polServer=self, manager=self.manager)
            from scoring.authority_api import AuthorityAPI
            authorityEndpoint = AuthorityAPI(polServer=self,
                                             manager=self.manager)
            from scoring.epistemics_api import EpistemicsAPI
            epistemicsEndpoint = EpistemicsAPI(polServer=self,
                                               manager=self.manager)
        if _feature_available('zones'):
            from zones.zones_api import ZonesAPI
            zonesEndpoint = ZonesAPI(polServer=self, manager=self.manager)

        if _feature_available('aquaponics'):
            # Aquaponics: self-watering pot geometry validation + hole
            # generation (aqp-1).
            from aquaponics.pot_api import AquaponicsPotAPI
            aquaponicsPotEndpoint = AquaponicsPotAPI(
                polServer=self, manager=self.manager)
            # Aquaponics: soil / water / nutrient-profile analysis (aqp-2).
            from aquaponics.media_api import AquaponicsMediaAPI
            aquaponicsMediaEndpoint = AquaponicsMediaAPI(
                polServer=self, manager=self.manager)
            # Aquaponics: per-part plant capture + budget (aqp-4).
            from aquaponics.plant_api import AquaponicsPlantAPI
            aquaponicsPlantEndpoint = AquaponicsPlantAPI(
                polServer=self, manager=self.manager)
            # Aquaponics: atmospheric conditions + gas exchange (aqp-5).
            from aquaponics.atmosphere_api import AquaponicsAtmosphereAPI
            aquaponicsAtmosphereEndpoint = AquaponicsAtmosphereAPI(
                polServer=self, manager=self.manager)
            # Aquaponics: bound pot systems — survival + impact (aqp-6).
            from aquaponics.pot_system_api import AquaponicsSystemAPI
            aquaponicsSystemEndpoint = AquaponicsSystemAPI(
                polServer=self, manager=self.manager)
            # Aquaponics: Darcy pot hydraulics — drains-by-gravity +
            # head field, fidelity ladder fem->reservoir (aqp-3).
            from aquaponics.hydraulics_api import AquaponicsHydraulicsAPI
            aquaponicsHydraulicsEndpoint = AquaponicsHydraulicsAPI(
                polServer=self, manager=self.manager)
        if _feature_available('waxprint'):
            # waxprint (wp-1): pellet-fed auger-screw wax printer — list rows +
            # run the two-zone melt with the wax thermal-safety gate.
            from waxprint.waxprint_api import WaxPrintAPI
            waxPrintEndpoint = WaxPrintAPI(polServer=self, manager=self.manager)
            # waxprint sim space (wp-5/wp-6): run one IC / a range + evaluate the
            # condition gates for a run.
            from waxprint.sim_api import WaxPrintSimAPI
            waxPrintSimEndpoint = WaxPrintSimAPI(polServer=self,
                                                 manager=self.manager)
        if _feature_available('aquaponics'):
            # Aquaponics: worm-compost enrichment loop — release /
            # simulate / compare-modes / enriched-water (aqp-7).
            from aquaponics.vermicompost_api import AquaponicsCompostAPI
            aquaponicsCompostEndpoint = AquaponicsCompostAPI(
                polServer=self, manager=self.manager)
            # Aquaponics: SIMPLIFIED/AGGREGATE growth model (was aqp-8;
            # renamed + rebuilt 2026-07-15 to pull its constants + curve
            # from the real detailed model, plant_growth_normalized).
            from aquaponics.plant_growth_simplified_api import (
                AquaponicsPlantGrowthSimplifiedAPI,
            )
            aquaponicsPlantGrowthSimplifiedEndpoint = (
                AquaponicsPlantGrowthSimplifiedAPI(
                    polServer=self, manager=self.manager))
        if _feature_available('nutrition'):
            # Nutrition: dietary-nutrient vocab + person BMR/needs +
            # household demand aggregation (nut-1/3/4).
            from nutrition.nutrition_api import NutritionAPI
            nutritionEndpoint = NutritionAPI(
                polServer=self, manager=self.manager)
            # Nutrition: plant harvest -> meal-nutrient yield, closing the
            # self-watering-pot grow loop (nut-2).
            from nutrition.food_api import NutritionFoodAPI
            nutritionFoodEndpoint = NutritionFoodAPI(
                polServer=self, manager=self.manager)
        if _feature_available('plant_morphology'):
            # Plant morphology: 3D organ/root stand-ins + confinement /
            # dwarfing assessment (morph-1).
            from plant_morphology.morphology_api import PlantMorphologyAPI
            plantMorphologyEndpoint = PlantMorphologyAPI(
                polServer=self, manager=self.manager)
        if _feature_available('aquaponics'):
            # Plant-growth-sim phase 1: free-soil/constrained-limits +
            # per-part PotPlanting state + animation-bones skeleton
            # (2026-07-15).
            from aquaponics.plant_growth_normalized_api import (
                AquaponicsPlantGrowthNormalizedAPI,
            )
            aquaponicsPlantGrowthNormalizedEndpoint = (
                AquaponicsPlantGrowthNormalizedAPI(
                    polServer=self, manager=self.manager))
            # Plant-growth-sim phase 8: direct-light field diagnostics.
            from aquaponics.light_field_api import AquaponicsLightFieldAPI
            aquaponicsLightFieldEndpoint = AquaponicsLightFieldAPI(
                polServer=self, manager=self.manager)
            # Plant-growth-sim phase 10: water batching + nutrient uptake.
            from aquaponics.water_batch_api import AquaponicsWaterBatchAPI
            aquaponicsWaterBatchEndpoint = AquaponicsWaterBatchAPI(
                polServer=self, manager=self.manager)
            # Plant-growth-sim phase 11: decomposed water-level trajectory.
            from aquaponics.water_level_api import AquaponicsWaterLevelAPI
            aquaponicsWaterLevelEndpoint = AquaponicsWaterLevelAPI(
                polServer=self, manager=self.manager)
        if _feature_available('mathshapes'):
            # Math-defined shapes: quadric/primitive/CSG geometry (shape-1)
            # + parametric modification (shape-2, POST /modify).
            from mathshapes.shape_api import MathShapesAPI
            mathShapesEndpoint = MathShapesAPI(
                polServer=self, manager=self.manager)
            # Aquaponic towers: stacked math-defined pots (shape-2) +
            # growth forecast (shape-4).
            from mathshapes.tower_api import AquaponicTowerAPI
            aquaponicTowerEndpoint = AquaponicTowerAPI(
                polServer=self, manager=self.manager)
            # CAD import/export via cad-engines worker + MinIO (shape-3).
            from mathshapes.cad_api import CadImportAPI
            cadImportEndpoint = CadImportAPI(
                polServer=self, manager=self.manager)
        # xsim-2: single-writer lease + object locks + simulation queue.
        from simulationLocks.locks_api import SimulationLocksAPI
        simulationLocksEndpoint = SimulationLocksAPI(
            polServer=self, manager=self.manager)
        # xsim-3: the reference ladder's resolve endpoint (read-only).
        from polariRefs.refs_api import PolariRefsAPI
        polariRefsEndpoint = PolariRefsAPI(
            polServer=self, manager=self.manager)
        if _feature_available('tanks'):
            # Tanks: freshwater + saltwater ecosystem nutrient balance +
            # harvest yield (the alternate nutrient source, tank-1).
            from tanks.tank_api import TankSystemAPI
            tankSystemEndpoint = TankSystemAPI(
                polServer=self, manager=self.manager)
        if _feature_available('microalgae'):
            # Microalgae reactors: sustainability (no-collapse) + CO2
            # decarbonization coupled to a parent system (algae-1).
            from microalgae.reactor_api import MicroalgaeReactorAPI
            microalgaeReactorEndpoint = MicroalgaeReactorAPI(
                polServer=self, manager=self.manager)
        if _feature_available('biomining'):
            # Biomining: element extraction + refinement + nutrient recovery
            # specialized aquaponic variants (biomine-1).
            from biomining.biomining_api import BiomineAPI
            biomineEndpoint = BiomineAPI(
                polServer=self, manager=self.manager)
        if _feature_available('video'):
            # Self-hosted video: presigned upload/stream URLs + ffmpeg
            # conversion trigger (video-1).
            from video.video_api import VideoAPI
            videoEndpoint = VideoAPI(
                polServer=self, manager=self.manager)
        if _feature_available('bizops'):
            # Business flows + economy track + order planner (biz-1).
            from bizops.bizops_api import BizOpsAPI
            bizOpsEndpoint = BizOpsAPI(
                polServer=self, manager=self.manager)
        if _feature_available('odooconnect'):
            # Odoo ERP connector status/catalog (od-3).
            from odooconnect.odoo_api import OdooConnectAPI
            odooConnectEndpoint = OdooConnectAPI(
                polServer=self, manager=self.manager)
        if _feature_available('waxsupply'):
            # Wax sources for molds/masks (wax-1).
            from waxsupply.wax_api import WaxSupplyAPI
            waxSupplyEndpoint = WaxSupplyAPI(
                polServer=self, manager=self.manager)
        if _feature_available('composition'):
            # Part composition (arch-7): derived levels, variant
            # reports, routings, audited promotions, archetypes.
            from composition.composition_api import CompositionAPI
            compositionEndpoint = CompositionAPI(
                polServer=self, manager=self.manager)
        if _feature_available('magnetics'):
            # Magnetic materials Section A: catalog gates, role
            # search, powder designer (mag-2/2r/2t).
            from magnetics.magnet_api import MagneticsAPI
            magneticsEndpoint = MagneticsAPI(
                polServer=self, manager=self.manager)
        if _feature_available('motors'):
            # Motors Section C: ladder designs, clock control case,
            # torque curves, parity (mag-5).
            from motors.motor_api import MotorsAPI
            motorsEndpoint = MotorsAPI(
                polServer=self, manager=self.manager)
        if _feature_available('meshassets'):
            # mesh-1: the licence-gated catalog + organ fit.
            from meshassets.mesh_asset_api import MeshAssetsAPI
            meshAssetsEndpoint = MeshAssetsAPI(
                polServer=self, manager=self.manager)
        if _feature_available('gears'):
            # Gear trains: taxonomy + the abstract kinematic solve
            # (gr-1); the motor splice lands at gr-5.
            from gears.gear_api import GearsAPI
            gearsEndpoint = GearsAPI(
                polServer=self, manager=self.manager)
        if _feature_available('supplychain'):
            # The unifying bio supply-chain ledger — materials + food +
            # carbon accounting (chain-1).
            from supplychain.chain_api import SupplyChainAPI
            supplyChainEndpoint = SupplyChainAPI(
                polServer=self, manager=self.manager)
            # Sourcing: cited prices + preference ladder (src-1).
            from supplychain.sourcing_api import SourcingAPI
            sourcingEndpoint = SourcingAPI(
                polServer=self, manager=self.manager)
        # acct-0: the accountability matrix. Endpoint construction is
        # NOT auto-gated (only defClassList is), so guard explicitly —
        # a normal build must register no /api/accountability route.
        # mp-3: the gate also requires the testing code to be present.
        if _feature_available('testing'):
            from testing.accountability_api import AccountabilityAPI
            accountabilityEndpoint = AccountabilityAPI(
                polServer=self, manager=self.manager)
            # acct-3: the twin rehearsal's out-of-process lease
            # handle (production keeps NO HTTP lease surface).
            from testing.twin_lease_api import TwinLeaseAPI
            twinLeaseEndpoint = TwinLeaseAPI(
                polServer=self, manager=self.manager)

        # Topology orchestration: graph/validate/assign/drift/observe
        # + portable package export/import (top-1).
        from topology.topology_api import TopologyAPI
        topologyEndpoint = TopologyAPI(
            polServer=self, manager=self.manager)
        # Testing over topology (tt-11): run module selftests +
        # foundational integration pings; the topology graph is the
        # progress visualization (red/green modules + hosts, edges
        # annotated with protocol + security).
        from topology.topology_testing_api import TopologyTestingAPI
        topologyTestingEndpoint = TopologyTestingAPI(
            polServer=self, manager=self.manager)
        if _feature_available('polariapps'):
            # Polari-Apps (tt-12): use-case module configurations —
            # plan/export/apply (rows only; deploys stay pol commands).
            from polariapps.apps_api import AppsAPI
            appsEndpoint = AppsAPI(polServer=self, manager=self.manager)
        if _feature_available('techtree'):
            # Tech tree (tt-3): trees/nodes/segments + derived completion
            # rollup — the topology expansion toward the OSEB.
            from techtree.techtree_api import TechTreeAPI
            techTreeEndpoint = TechTreeAPI(
                polServer=self, manager=self.manager)
        # Provider routing (top-7): module delegation resolves its
        # provider from the topology rows when no explicit URL knob
        # is set (see materialsScience.engines.remote's ladder).
        from topology.provider_registry import set_manager
        set_manager(self.manager)
        # Node resource inventory (res-1): every PolariNodeMachine
        # carries observed cores/RAM/disk — isoSys bridged into the
        # topology; remote nodes pull (system_info_url knob) or push.
        from resources.node_resources_api import NodeResourcesAPI
        nodeResourcesEndpoint = NodeResourcesAPI(
            polServer=self, manager=self.manager)
        # Module/engine resource profiles (res-2): floor + scalability
        # + character + storage tier; declared now, measured in res-3.
        from resources.profile_api import ResourceProfilesAPI
        resourceProfilesEndpoint = ResourceProfilesAPI(
            polServer=self, manager=self.manager)
        # XR cascade resolution (xr-1): read-only resolve surface —
        # mode/framing + provenance for one space (writes go through
        # the generated CRUDE endpoints on the settings rows).
        from xr.xr_api import XrAPI
        xrEndpoint = XrAPI(polServer=self, manager=self.manager)
        # Admission advisor (res-4): route-to-storage / fits-as-is /
        # fits-with-reallocation / would-break — verdicts as
        # suggestions, never auto-applied.
        from resources.admission_api import AdmissionAPI
        admissionEndpoint = AdmissionAPI(
            polServer=self, manager=self.manager)
        # Schema stabilization: learning state per class + the
        # captured type-mismatch (OOPS) events + manual knobs.
        from polariDataTyping.schema_stability_api import (
            SchemaStabilityAPI,
        )
        schemaStabilityEndpoint = SchemaStabilityAPI(
            polServer=self, manager=self.manager)
        if _feature_available('grpcbridge'):
            # gRPC contracts (grpc-1): exposure catalogue + the
            # enable/disable/regenerate knob + .proto download. Contracts
            # generate ONLY from stabilized schemas.
            from grpcbridge.contract_api import GrpcContractsAPI
            grpcContractsEndpoint = GrpcContractsAPI(
                polServer=self, manager=self.manager)
            # Polari Hardware Bridge (grpc-j1): bridge-definition rows +
            # generate/download of the buildable Java app (tar.gz).
            from grpcbridge.java_bridge_api import HardwareBridgeAPI
            hardwareBridgeEndpoint = HardwareBridgeAPI(
                polServer=self, manager=self.manager)
        if _feature_available('hwfpga'):
            # FPGA register maps (hwsim-3): catalogue + generated
            # Verilog/C/testbench artifacts, all FROM the knob rows.
            from hwfpga.fpga_api import FpgaRegisterMapAPI
            fpgaRegisterMapEndpoint = FpgaRegisterMapAPI(
                polServer=self, manager=self.manager)
        # ncg-7 (Dustin: split across small devices): endpoint
        # construction is NOT auto-gated (only defClassList is), so
        # the ncg level surfaces guard explicitly — a node assigned
        # only 'scoring' must carry no /api/hw or circuit routes,
        # and vice versa, exactly like the testing surface.
        # mp-3: the gate also requires the module code to be present.
        if _feature_available('hwdigital'):
            # ncg-3: logic diagrams as rows — catalogue, generated
            # artifacts (through the compiler seam), evaluate.
            from hwdigital.logic_api import LogicDesignAPI
            logicDesignEndpoint = LogicDesignAPI(
                polServer=self, manager=self.manager)
        if _feature_available('electrodevice'):
            # ncg-4: circuits as rows — catalogue, netlist, run.
            from electrodevice.circuit_api import (BreadboardAPI,
                                                   CircuitRowsAPI)
            circuitRowsEndpoint = CircuitRowsAPI(
                polServer=self, manager=self.manager)
            # ncg-5: jumpered breadboards, run as one netlist.
            breadboardEndpoint = BreadboardAPI(
                polServer=self, manager=self.manager)
            # Material-derived electronic devices (derive from msci sims,
            # SPICE cards, ngspice circuit tests).
            from electrodevice.device_api import ElectroDeviceAPI
            electroDeviceEndpoint = ElectroDeviceAPI(
                polServer=self, manager=self.manager)

        # Multi-scale family conformance (profile_ref → slot-by-slot
        # findings + suggestions; separate module keeps SimulationAPI
        # at size).
        from simulations.profile_api import ProfileAPI
        profileEndpoint = ProfileAPI(polServer=self, manager=self.manager)

        # Formulation searches as objects: run / list runs / promote
        # winners (Track C lineage). Separate module keeps
        # ScaleExecutionAPI at size.
        from materialsScience.formulation_search_api import (
            FormulationSearchAPI,
        )
        formulationEndpoint = FormulationSearchAPI(
            polServer=self, manager=self.manager)

        # Engine-model layer: the FEM/DFT catalog + model definition
        # validate/execute endpoints (msci-15).
        from materialsScience.engine_model_api import EngineModelAPI
        engineModelEndpoint = EngineModelAPI(
            polServer=self, manager=self.manager)

        # Modules as projects: configured module code folders, fetched
        # by explicit selection (or per-row auto_fetch knob at boot).
        from polariPeers.module_projects_api import ModuleProjectsAPI
        moduleProjectsEndpoint = ModuleProjectsAPI(
            polServer=self, manager=self.manager)

        # Boundary + dependency tracking: the coherent-module map,
        # python requires-trees, persisted dependency rows, and the
        # union-resolve install knob (msci-21).
        from polariPeers.module_dependency_api import ModuleDependencyAPI
        moduleDependencyEndpoint = ModuleDependencyAPI(
            polServer=self, manager=self.manager)

        # Admission agreements — join-request → pending PeerAgreement →
        # explicit approve/deny → per-child scoped revocable token
        # (mesh convergence ruling; replaces the shared token).
        agreementsEndpoint = AgreementsAPI(polServer=self, manager=self.manager)

        # Register APIProfile, APIDomain, APIEndpoint, and ApiFormatConfig types
        self.manager.getObjectTyping(classObj=APIProfile)
        self.manager.getObjectTyping(classObj=APIDomain)
        self.manager.getObjectTyping(classObj=APIEndpoint)
        self.manager.getObjectTyping(classObj=ApiFormatConfig)
        # Register Definition classes and configure them for CRUDE access.
        # By default polyTypedObject sets excludeFromCRUDE=True; override for
        # these data-container classes so the frontend knows CRUDE is available.
        # Also pre-populate polyTypedVars from the class signature since there
        # are no instances at startup for runAnalysis() to inspect.
        self.defClassList = [DisplayDefinition, TableDefinition, GraphDefinition, GeoJsonDefinition, DataSetDefinition, FieldProfileDefinition, FilterChainDefinition, EquationDefinition, MatrixDefinition, MatrixEquationDefinition, TileSourceDefinition, GeocoderDefinition, SolutionDefinition, SolutionVersion, SolutionTestCase, ExecutionStepAssertion, SolutionProcessLink, MapPointDefinition, MapLineSegmentDefinition, MapPolygonDefinition, Role, SimSpaceDefinition, SimSpaceBindingDefinition, Shape2DDefinition, Style2DDefinition, Mesh3DDefinition, Material3DDefinition, Texture3DDefinition, MaterialPhaseAppearance, ChemicalElementDefinition, MaterialsScienceMaterial, MaterialScaleDefinition, CrystalStructureDefinition, ThermalProcessingProfile, EvidenceMethod, PropertyClaim, StructureClaim, ValidationClaim, DigitizedDataset, MaterialState, ProcessingStage, ScaleStructureDefinition, ReactionWindow, MaterialProcessDefinition, MaterialProcessExecution, ChemicalSpecies, ReactionRule, ScaleTransferDefinition, ExposureScenario, MaterialPerformanceScenario,
            # Simulations
            SimulationDefinition, SimulationRun, SimVariable,
            SimSpaceEvaluationEquation,
            SimulationExecutionSolution, SimulationCouplingDefinition,
            MultiScaleSimulationDefinition, MultiScaleSimulationProfile,
            InitialConditionInterfaceDefinition,
            StepCostProfile,
            # Node integration (twin-Polari): peers + module registry +
            # admission agreements (mesh convergence Phase 1).
            FormulationSearchDefinition, FormulationSearchRun,
            FormulationCandidateResult,
            EngineModelTemplate, FEMModelDefinition, DFTModelDefinition,
            MaterialPropertyMeaning,
            ScoreTerm, ScoreContext, ScoreSubject, ContextualizedValue,
            ScoreConcept, ScoreGroup, AgreementPolicy,
            ScoreAssertion, AssertionValidityVote, MediaEvidence,
            EvidencePolicy, Contributor, PolicyVote,
            WorldviewElection, WorldviewBallot,
            GroupDisplayVote, GroupDisplayBallot,
            LogicForkCriterion, LogicForkVote, LogicForkBallot,
            DecisionProcedureEdge, SystemChoiceInForce,
            CourtCase, GraphCompilerDefinition,
            GroupAuthorityGrant, InstanceAuthorityGrant,
            GroupInstanceBinding, TermAvailabilitySignal,
            SiteDefinition, ZoneDefinition, ZonePoint,
            ZoneEstimateRecord,
            LogicBlockDesign, LogicBlockNode,
            CircuitDefinition, CircuitNetDefinition,
            CircuitComponentDefinition,
            BreadboardDefinition, ComponentPlacement, BoardJumper,
            PinBindingDefinition, NoCodeTestCase, NoCodeTestPack,
            GovSource, SourceRetrieval, RetrievalConfirmation,
            NonProfitSource, CompanySource, PoliticalGroupSource,
            IndividualSource,
            PolicyDraft, VenueActionRecord, VenueMismatchPattern,
            LegislationRecord, LegislationProvision,
            LegislativeVoteEvent,
            DataGatheringSolution, StepCredibilityAssertion,
            AssertionCredibilityVote, PolicyIntent,
            TermProposal, TermRelationAssertion, TermScopeVote,
            TermProof, ProofRebuttal, DataManipulationPattern,
            ProofVote,
            CredibilityClaim, ClaimAttestation, StanceBasis,
            QualificationRelevanceVote,
            FactualClaim, AccuracyPolicy, BiasPolicy,
            CostCategory, SurvivalCostProfile,
            PotDefinition, PotHole,
            DeviceMaterialDefinition, PrinterAssemblyDefinition,
            WaxFeedstockDefinition, PrintConditionDefinition,
            # wp-r: geopolymer-wax-mold-reuse-cycles tracking.
            WaxReclaimBatch,
            # mold-1: mold strategies + crush-recycle lifecycle.
            MoldLifecycleRecord,
            WaxPrintSimState,
            NutrientSpecies, NutrientProfile, SoilDefinition,
            WaterDefinition, PlantDefinition, PlantPart,
            AtmosphereDefinition, PotSystemDefinition,
            # Plant-growth-sim phase 8: direct-light field simulation.
            LightSpectrumDefinition, LightSourceDefinition,
            # Plant-growth-sim phase 10: water batching schedules.
            WaterBatchSchedule,
            CompostBinDefinition, VermicompostProfile,
            CompostLoopDefinition, PlantGrowthModel,
            # Nutrition (nut-1/3/4 + nut-2 foods).
            DietaryNutrient, NutrientReference, PersonProfile,
            HouseholdProfile, FoodItem, NutrientContent,
            # Plant morphology 3D stand-ins (morph-1).
            OrganModel, RootSystemModel,
            # Plant-growth-sim phase 1: normalized-growth instance state.
            PotPlanting,
            # Plant-growth-sim phase 7: stress-type response curves.
            StressResponseCurve,
            # Math-defined shapes: quadric/primitive/CSG (shape-1).
            MathShapeDefinition,
            # Aquaponic tower: stacked math-defined pots (shape-2).
            AquaponicTowerDefinition,
            # CAD imports via cad-engines worker + MinIO (shape-3).
            ImportedCadObject,
            # Tanks: freshwater + saltwater ecosystem (tank-1/2).
            TankDefinition, AquacultureSpecies, TankSystemDefinition,
            TankSubstrateDefinition,
            # Microalgae reactors + integrated loops (algae-1/2).
            AlgaeStrain, AlgaeReactorDefinition, IntegratedLoopDefinition,
            # Biomining / bioextraction variants (biomine-1).
            BioextractionAgent, BiomineralProduct,
            BiomineSystemDefinition,
            # Self-hosted video: WebM/MP4 + optional adaptive HLS (video-1).
            VideoAsset,
            # Wax sources (wax-1) + supply-chain ledger (chain-1)
            # + sourcing profiles/citations/preference ladder (src-1).
            WaxSourceDefinition, SupplyNode, SupplyFlow,
            SupplyChainDefinition, SupplySourceProfile,
            PriceCitation, SourcePreferencePolicy,
            ProductInputRequirement, ProductFormula,
            # Odoo ERP connector (od-3/od-4/od-5).
            OdooInstanceConfig, OdooModelBinding, OdooSyncReceipt,
            BusinessScenarioDefinition,
            # Business ops (biz-1).
            BusinessStageDefinition, BusinessUpgradeStep,
            BusinessProfile, LocalEconomyMilestone,
            ProcessWorkflowDefinition, ProductOrder,
            MarketSessionRecord, ProductionRunRecord,
            PartnershipAgreement, BusinessRiskNote,
            ComplianceRequirement, ComplianceRecord,
            QualityCheckDefinition, QualityCheckRecord,
            # Part composition (arch-2..5).
            PartComponentDefinition, CompositionNode,
            InterfaceDefinition, FailureModeDefinition,
            FunctionalPartDefinition, ConstructionVariantDefinition,
            RoutingDefinition, RoutingOperation,
            PartArchetypeDefinition, DesignMatrixDefinition,
            # Magnetic materials Section A (mag-2/2r/2t) + circuits
            # (mag-3).
            MaterialUseRole, MagneticMaterialOption,
            MagneticPowderDefinition, MagneticCircuitDefinition,
            MagneticElementDefinition, FluxNodeDefinition,
            # Slot-matrix assembly (mag-4) + field views (mag-fv).
            BlockSizeVariant, BlockLayoutDefinition,
            BlockPlacement, JointMortarAssignment,
            FieldViewDefinition, FieldThresholdBand, FieldViewGroup,
            # Motors Section C (mag-5/6).
            MotorDesignDefinition, MotorVerificationRun,
            MotorControllerProfile, PhaseBindingDefinition,
            # mag-11: the per-piece bill (part -> material -> job).
            MotorPartDefinition,
            # goal-1: the size ladder + goal specs.
            ClockScaleDefinition, MotorGoalSpec,
            # view-1: discipline views as rows.
            ClockViewDefinition,
            # viz-1: 3D visualization layers as rows.
            ClockSceneLayerDefinition,
            # mesh-1: licence findings, the assets under them, and
            # the human's accepted picks.
            MeshAssetSource, MeshAssetReference, OrganMeshChoice,
            # Gear trains (gr-1): types before bodies, bodies before
            # the meshes that reference them.
            GearTypeDefinition, ShaftNodeDefinition,
            GearTrainDefinition, GearDefinition,
            GearMeshDefinition, GearVerificationRun,
            # Topology orchestration (top-1).
            PolariNodeMachine, OrchestrationTarget,
            InstanceDefinition, ModuleAssignment,
            ModuleDependencyEdge, ServiceConnection,
            # gm-2-lite: graceful moves as observable data.
            MoveOperation,
            TopologyDefinition, TopologyObservation,
            # Testing over topology (tt-11): observed runs/pings.
            TopologyTestRun, IntegrationPing,
            # Polari-Apps (tt-12): app configs + plan receipts.
            PolariAppDefinition, AppDeploymentPlan,
            # Tech tree (tt-3) + segment content (tt-6).
            TechTreeDefinition, TechNode, TechSegment,
            TechSegmentAssignment, TechDependencyEdge,
            RealArtifact, BusinessModelDefinition, BusinessOutcome,
            PolicyDefinition,
            # Resource profiles (res-2).
            ModuleResourceProfile,
            # XR settings cascade + interface variants (xr-1).
            XrGlobalSettings, XrTypeDefault, XrInterfaceVariant,
            # Schema stabilization (freeze/oops/adapt).
            SchemaStabilityProfile, SchemaDeviationEvent,
            # gRPC exposure knob + contract history (grpc-1).
            GrpcExposure, ProtoContractVersion,
            # Polari Hardware Bridge definitions (grpc-j1).
            HardwareBridgeDefinition,
            # Hardware rig digital twins (hwsim-1).
            SimRigState,
            # L3 MD + L2 mesoscale model definitions (msci-26).
            MDModelDefinition, MesoModelDefinition,
            # FPGA register maps as data + FPGA twin (hwsim-3).
            RegisterMapDefinition, RegisterDefinition,
            FpgaRegisterState, LedMatrix4x4State,
            # Material-derived devices + SPICE cards + circuit runs.
            ElectronicDeviceDefinition, SpiceModelCard,
            CircuitRunResult, SemiconductorProfile,
            DeviceValidationReport, PhotoAbsorberDefinition,
            SolarStackDefinition, SolarLayerDefinition,
            PeerNode, PolariModule, PeerAgreement, ModuleSourceConfig,
            PolariModuleDependency,
            # mlb-2: per-boot module timing history (durable — later
            # boots derive expected-online ETAs from these rows).
            ModuleBootRecord,
            PendulumBobSimState, PendulumStringSimState,
            NewtonianPendulumBobSimState, NewtonianPendulumRodSimState,
            WindFieldGridState, MaterialCondensationState,
            # xsim-2 single-writer machinery: lease + object locks +
            # queue (persisted rows — the queue survives restart).
            MutationLease, LeaseBreakEvent, ObjectLockEntry,
            LockBreakEvent, SimulationQueueEntry,
            # xsim-4: the remote-write audit ledger.
            WriteJournalEntry,
            # acct-0 accountability spine (TEST BUILDS ONLY — the
            # module gate below drops these on normal builds).
            CapabilityCheck, CheckRun]
        # modsplit-1: each instance registers ONLY its assigned
        # modules' classes (POLARI_MODULES env; unset = all). Seeds,
        # CRUDE endpoints, and boot restore all key off the typing
        # this filter controls — one honest gate point.
        from polariApiServer.module_gating import class_enabled, gate_summary
        # mp-3: absent feature modules stubbed their classes to None
        # in the guarded import blocks — drop those before gating.
        _absent = len([c for c in self.defClassList if c is None])
        if _absent:
            print(f'[DefInit] mp-3: {_absent} definition classes belong '
                  f'to modules that are not downloaded — skipped '
                  f'(pol modules registry shows what is missing)',
                  flush=True)
            self.defClassList = [c for c in self.defClassList
                                 if c is not None]
        _gate = gate_summary(self.defClassList)
        if _gate['dropped']:
            print(f"[DefInit] Module gating (POLARI_MODULES="
                  f"{_gate['modulesKnob']}): dropped "
                  f"{sum(_gate['dropped'].values())} classes from "
                  f"{sorted(_gate['dropped'])}", flush=True)
        self.defClassList = [c for c in self.defClassList
                             if class_enabled(c)]
        # mlb-1: the middleware resolves each CRUDE route's owning
        # module through this map.
        self.bootRegistry.register_classes(self.defClassList)
        print(f'[DefInit] Registering {len(self.defClassList)} definition classes', flush=True)
        for defClass in self.defClassList:
            className = defClass.__name__
            defTyping = self.manager.getObjectTyping(classObj=defClass)
            if defTyping is not None:
                defTyping.excludeFromCRUDE = False
                defTyping.isDefinitionClass = True
                created = defTyping.initializeVarsFromSignature()
                print(f'[DefInit] {className}: polyTypedVarsDict keys={list(defTyping.polyTypedVarsDict.keys())}, identifiers={defTyping.identifiers}, created={created}', flush=True)
            else:
                print(f'[DefInit] {className}: getObjectTyping returned None!', flush=True)
        # NOTE: DB table creation and instance restoration happen later via
        # ensureDefinitionTables(), called from managerObject.__init__ AFTER
        # jumpstartDatabase() completes (self.manager.db is still None here).

        # NOTE: _autoRegisterMbtilesSources() is called from the manager's
        # __init__ after jumpstartObjectStore() completes, since object storage
        # is not yet connected at this point in polariServer.__init__.

        self.customAPIsList = [serverTouchPointAPI, tempRegisterAPI, managerObjectEndpoint, polyTypedObjectEndpoint, classInstanceCountsEndpoint, createClassEndpoint, stateSpaceClassesEndpoint, stateSpaceConfigEndpoint, stateDefinitionEndpoint, apiProfilerQueryEndpoint, apiProfilerMatchEndpoint, apiProfilerBuildEndpoint, apiProfilerCreateClassEndpoint, apiProfilerTemplatesEndpoint, apiProfilerDetectTypesEndpoint, apiDomainEndpoint, apiEndpointEndpoint, apiEndpointFetchEndpoint, apiConfigEndpoint, systemInfoEndpoint, updateClassConfigEndpoint, tileGeneratorEndpoint, objectStorageEndpoint, solutionCodeGenEndpoint, solutionExecEndpoint, solutionVersionEndpoint, wsStatusEndpoint]

        # Populate uriList with custom API endpoints for overlap tracking
        for api in self.customAPIsList:
            apiName = getattr(api, 'apiName', '')
            if apiName and apiName not in self.uriList:
                self.uriList.append(apiName)

        self.crudeObjectsList = [polariCRUDE(apiObject="polariCRUDE", polServer=self, manager=self.manager)]
        objNamesList = list(self.manager.objectTypingDict)
        if(not "polariAPI" in objNamesList):
            objNamesList.append("polariAPI")
        if(not "polariCRUDE" in objNamesList):
            objNamesList.append("polariCRUDE")

        # Filter out core system objects that shouldn't have CRUDE endpoints
        # Note: polyTypedObject needs BOTH CRUDE (for frontend services) AND custom API (for typing-info page)
        excludedFromCRUDE = ["managerObject"]
        objNamesList = [obj for obj in objNamesList if obj not in excludedFromCRUDE]

        print("="*70)
        print("CRUDE ENDPOINTS BEING CREATED:")
        print(objNamesList)
        print("="*70)
        for objType in objNamesList:
            typingObj = self.manager.objectTypingDict[objType]
            typingObj.runAnalysis()
            newCRUDE = polariCRUDE(apiObject=objType, polServer=self, manager=self.manager)
            self.crudeObjectsList.append(newCRUDE)
            if newCRUDE.apiName not in self.uriList:
                self.uriList.append(newCRUDE.apiName)
            # Set the polariTree endpoint on the ApiFormatConfig if it exists
            if hasattr(typingObj, 'apiFormatConfig') and typingObj.apiFormatConfig is not None:
                typingObj.apiFormatConfig.polariTreeEndpoint = newCRUDE.apiName
            print(f"✓ Created CRUDE endpoint: {newCRUDE.apiName} for {objType}")
        
        
        #mainChannelURI = self.baseURIprefix + 'channel/' + self.serverChannel.name + '/' + self.baseURIpostfix
        #print('Template URI: ', templateURI)
        #self.crudObjectsList.append(polariCRUD(self.serverChannel, manager=self.manager))
        #self.apiServer.add_route(uri_template = mainChannelURI, resource= self.crudObjectsList[0] )
        #The systems that maintain a secure local connection to this system/server and are used
        #for data processing by it, but do not have their own servers.
        self.siblingSystems = []
        #Other servers which maintain a connection with the internet, which this server may
        #maintain APIs to for exclusive access to that server.
        self.siblingServers = []
        #A certificate file which is used to establish and confirm https connections to this server EX: './server.pem'
        self.certFile = None
        #A list of applications (Angular by default) which are being used to establish and serve the frontend of the application.
        self.apps = []
        #A list of data streams / pipelines where the server is constantly sending data to endpoints according to the object's specified conditions.
        self.streams = []
        #
        self.groups = []
        #
        self.serverInstance = None

        # Dynamic module initialization: discover and load all enabled modules
        self._module_classes = {}  # {module_id: [class_names]}
        # Backwards compat alias for materials_science specifically
        self._materials_science_classes = []
        # mlb-1: lazy boots defer dynamic modules to the admission
        # worker (Phase C) — construction stays fast.
        from polariApiServer.lazy_boot import lazy_boot_enabled
        if not lazy_boot_enabled():
            self.initializeDynamicModules()

    def initializeDynamicModules(self):
        """Discover + initialize the dynamic (modules/-registry)
        modules. Runs during construction on monolithic boots; the
        admission worker calls it post-listen on lazy boots."""
        try:
            from config_loader import config as mod_config
        except ImportError:
            mod_config = None

        # Load persisted module state (survives restarts via data volume)
        from moduleService.moduleState import get_module_enabled

        discovered = discover_available_modules()
        for module_id, module_info in discovered.items():
            if not module_info['available']:
                print(f"[ModuleLoad] {module_id}: not available (import failed), skipping")
                continue

            # Priority: persisted state file > env vars/config.yaml
            # get_module_enabled returns None if no persisted state exists,
            # in which case we fall back to the config system
            persisted = get_module_enabled(module_id)
            if persisted is not None:
                enabled = persisted
                print(f"[ModuleLoad] {module_id}: enabled={enabled} (from persisted state)")
            else:
                enabled = False
                if mod_config:
                    enabled = mod_config.get(f'modules.{module_id}.enabled', False)
                    if isinstance(enabled, str):
                        enabled = enabled.lower() in ('true', '1', 'yes')

            if not enabled:
                print(f"[ModuleLoad] {module_id}: disabled")
                continue

            try:
                import importlib
                mod = importlib.import_module(module_info['package_name'])
                include_seed = True
                if mod_config:
                    include_seed = mod_config.get(f'modules.{module_id}.include_seed_data', True)

                print(f"[ModuleLoad] {module_id}: initializing ({module_info['package_name']})")
                result = mod.initialize(manager=self.manager, include_seed_data=include_seed)

                class_names = list(result['registered_classes'].keys())
                self._module_classes[module_id] = class_names

                # Ensure moduleBinding is set on all classes (even pre-existing ones)
                for cn in class_names:
                    typing = self.manager.objectTypingDict.get(cn)
                    if typing:
                        typing.moduleBinding = module_id

                # Apply semantic type overrides from metadata (safety net)
                apply_metadata_type_overrides(module_info['dir_path'], self.manager)

                # Backwards compat for materials_science
                if module_id == 'materials_science':
                    self._materials_science_classes = class_names

                crude_ok = 0
                crude_fail = 0
                for class_name in result['registered_classes']:
                    try:
                        self.registerCRUDEforObjectType(class_name)
                        crude_ok += 1
                    except Exception as ce:
                        crude_fail += 1
                        print(f"[ModuleLoad] {module_id}: CRUDE failed for {class_name}: {ce}")

                seed_count = sum(len(v) for v in result['seed_data'].values())
                print(f"[ModuleLoad] {module_id}: {len(class_names)} classes, {crude_ok} CRUDE, {seed_count} seed records")
            except Exception as e:
                print(f"[ModuleLoad] {module_id}: ERROR: {e}")
                import traceback
                traceback.print_exc()

    #Creates a new sink which operates stictly over a secure local network (Wifi Router)
    def makeNewLocalSink(self, localNetworkedSystemIP, remotePort, managerAPI):
        #Set up a new sink instance in order to proxy things to another service
        sink = SinkAdapter()
        sinkURL = '/' + localNetworkedSystemIP + '/' + remotePort + '/' + managerAPI
        app.add_sink(sink, sinkURL.encode('unicode_escape'))

    def makeNewErrorType(self):
        # If a responder ever raises an instance of StorageError, pass control to
        # the given handler.
        app.add_error_handler(apiError, apiError.handle)

    def startLocalServerRun(self):
        self.serverInstance = simple_server.make_server('127.0.0.1', 8000, self.apiServer)
        self.serverInstance.serve_forever()

    def makeDefaultUserGroups(self):
        #Make AdminGroup access group - users with admin privilages.
        self.groups.append(UserGroup(groupname="AdminGroup", manager=self.manager))
        #Make SecureLocalSystems access group - for connected systems on a secure network.
        self.groups.append(UserGroup(groupname="SecureLocalSystems", manager=self.manager))
        #Make RemoteConnectedSystems access group - for connected systems which communicate over the internet.
        self.groups.append(UserGroup(groupname="RemoteConnectedSystems", manager=self.manager))
        #Make AuthenticatedUsers access group - for users that have logged in and been authenticated.
        self.groups.append(UserGroup(groupname="AuthenticatedUsers", manager=self.manager))
        #Make AnonymousTrackedUsers access group - for users who have yet to log in or are browsing anonymously.
        self.groups.append(UserGroup(groupname="AnonymousTrackedUsers", manager=self.manager))
        #Make PotentialSecurityThreat access group - for anonymous users who have triggered multiple security flags and may be trying to infiltrate the system.
        #(this can be used to prevent many attempts from singular IPs at accessing the Node)
        self.groups.append(UserGroup(groupname="PotentialSecurityThreat", manager=self.manager))
        return

    #This can be run to quickly produce permission sets which allow access to everything
    #SHOULD ONLY EVER BE RUN WHILE TESTING ON LOCALHOST.
    def makeDefaultLocalTestPermissionSets(self):
        noPermissionSetObjects = []
        for someTyping in self.manager.objectTyping:
            if(someTyping.permissionSets == []):
                noPermissionSetObjects.append(someTyping)
        for someTyping in noPermissionSetObjects:
            someTyping.permissionSets.append(
                polariPermissionSet(manager=self.manager, environment="localhost", setName="localHostTestPS_"+someTyping.className, apiObject=someTyping.className, forAllAnonymousUsers=True, assignedUserGroups=["AdminGroup"],
                functionsAll=True,createAll=True, readAll=True, updateAll=True, delete=True)
            )

    def setupExistingObjectAPIs(self):
        #Get all polytyped objects in the given manager objects
        #first get all of the Polari-Defined manager and tree objects
        #these will have certain restrictions placed on them that are necessary
        #in order to keep the entire system cohesive and not failing horribly.
        otherNonAPIenabledObjects = []
        treeObjectsList = []
        managersList = []
        accountedTypes = self.securityManagerObjects + self.protectedManagerObjects + self.publicManagersListmanagersList + self.securityTreeObjects + self.protectedTreeObjects + self.publicTreeObjectsList + self.apiRestrictedObjects
        #Get all objects that do not already have an indicated default typing.
        for someTyping in self.manager.polyTypedObjects:
            if(someTyping.isTreeObject == None or someTyping.isManagerObject):
                otherNonAPIenabledObjects.append(someTyping.className)
            elif(someTyping.isTreeObject and not someTyping.className in accountedTypes):
                treeObjectsList.append(someTyping.className)
            elif(someTyping.isManagerObject and not someTyping.className in accountedTypes):
                managersList.append(someTyping.className)
        for treeObjName in treeObjectsList:
            for someTyping in self.manager.polyTypedObjects:
                if(someTyping.className == treeObjName):
                    newPermissionSet = self.newDefaultPermissionSet(apiObject=treeObjName, isSecure=True)
                    newOwnerPermissionSet = self.newDefaultPermissionSet(apiObject=treeObjName, isOwnerPerms=True)
                    someTyping.permissionSets.append(newPermissionSet)
                    someTyping.permissionSets.append(newOwnerPermissionSet)
                    break

    def newDefaultPermissionSet(self, apiObject, isBasePS=False, isOwnerPerms=False, isSecure=False, isProtected=False, isPublic=False):
        if(isSecure):
            return polariPermissionSet(apiObject=apiObject, isGeneralized=isBasePS,
    functionsAll=False, functionsSpecific=[], createAll=False, createSpecific=[],
    readAll=False, readSpecific=[], updateAll=False, updateSpecific=[], delete=False,
    filter = [])
        elif(isProtected):
            return polariPermissionSet(apiObject=apiObject, isGeneralized=isBasePS,
    functionsAll=False, functionsSpecific=[], createAll=False, createSpecific=[],
    readAll=True, readSpecific=[], updateAll=False, updateSpecific=[], delete=False,
    filter = [])
        elif(isPublic):
            return polariPermissionSet(apiObject=apiObject, isGeneralized=isBasePS,
    functionsAll=False, functionsSpecific=[], createAll=True, createSpecific=[],
    readAll=True, readSpecific=[], updateAll=True, updateSpecific=[], delete=False,
    filter = [])
        elif(isOwnerPerms):
            return polariPermissionSet(apiObject=apiObject, isGeneralized=isBasePS,
    functionsAll=False, functionsSpecific=[], createAll=False, createSpecific=[],
    readAll=True, readSpecific=[], updateAll=True, updateSpecific=[], delete=True,
    filter = [apiObject + ' WHERE owner=var(someUser)'], userCriteriaSharingFilter=[])

    def setCertForSSL(self, path, filename):
        if(self.manager != None):
            fileObj = self.manager.makeFile(Path=path, name=filename)

    def polariServerLoop(self):
        self.lastCycleTime = time.localtime()
        #First checks the Main Channel to see if there are any requests there.
        #Note: if the mainChannel is not there, this should not be running.
        now = self.lastCycleTime
        #(Event Loop for the application)
        print('Starting loop at: ' + str(self.lastCycleTime[3]) + ':' + str(self.lastCycleTime[4]))
        while( (now[4] - self.lastCycleTime[4]) < self.timeout):
            now = time.localtime()

    def setMainServerChannel(self):
        self.mainServerChannel

    def setupNodeServer(self):
        #Sets up the corresponding javaScript file which defines the server for node.js
        if(sourceFileJS == None and os.path.exists(os.getcwd() + '/managedServer.js')):
            self.sourceFileJS = fileObject(name='managedServer', Path=os.getcwd(), extension='js', manager=self.manager)
        else:
            self.sourceFileJS = sourceFileJS

    def setSourceFile(self, sourceFileJS=None):
        if(sourceFileJS == None):
            sourceFileJS = managedFile()
        else:
            sourceFileJS = sourceFileJS

    def startNodeServer(self):
        #Creates a subprocess for launching the server and navigates directly to the
        #file holding the source code for the Node Express server.
        bytePath = bytes(string, self.sourceFileJS.Path)
        byteName = bytes(string, self.sourceFileJS.name)
        serverProcess = subprocess.Popen(args = b'cd ' + bytePath + b' \n',
                            stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)
        #Launches a process with the base code for a Node Express Server.
        serverProcess.stdin.write(b'node ' + byteName + b'.js \n')
        serverProcess.stdin.flush()
        print(serverProcess.stdout.readline())
        #Input data to define the startup of the server and information about the basis of the server
        serverProcess.stdin.write(b'\n')
        serverProcess.stdin.flush()
        print(serverProcess.stdout.readline())
        #Recieve confirmation that the bootup process of the server is completed, start a test information
        #exchange using the server dataChannel.
        serverProcess.stdin.close()
        serverProcess.terminate()
        serverProcess.wait(timeout=0.2)
        output = subprocess.check_output()

    def tempRegister(self):
        #First, check if the maximum allowed amount of tempUsers has been reached.
        #If limit has been reached, return an error saying limit was reached.
        if(len(self.tempUsersList) > self.temporaryUsersLimit):
            raise PermissionError("Maximum amount of temporarry users reached for this server.")
        else:
            #Else, create the new temporary user and return it's info to the frontend. 
            newTempUser = User(unregistered=True)
            self.tempUsersList.append(newTempUser)
            self.tempUsersDict[newTempUser.id] = newTempUser
            return newTempUser

    def register(self, tempUserId, newUsername, newPassword):
        cur_user = self.tempUsersDict[tempUserId]
        usernames = list(self.usersDict.keys())
        if(newUsername in usernames):
            raise ValueError("Username already has associated user.")
        

    def login(self, tempUserId, username, password):
        getTempUser = ""
        transferTempUserData = ""

    def changePassword(self, newPassword):
        if(len(newPassword) < self.passwordRequirements["min-length"]):
            raise ValueError("Must have over ", self.passwordRequirements["min-length"], " characters in password.")
        if(len(newPassword) < self.passwordRequirements["max-length"]):
            raise ValueError("Must have under ", self.passwordRequirements["max-length"], " characters in password.")
        specialCharCount = 0
        numCharCount = 0
        for someChar in newPassword:
            if(not someChar.isalnum()):
                specialCharCount += 1
            if(someChar.isnumeric()):
                numCharCount += 1
        if(specialCharCount < self.passwordRequirements["min-special-chars"]):
            raise ValueError("Must have over ", self.passwordRequirements["min-special-chars"], " special characters in password.")
        if(numCharCount < self.passwordRequirements["min-nums"]):
            raise ValueError("Must have over ", self.passwordRequirements["min-nums"], " numbers in password.")

    def ensureDefinitionTables(self, only_classes=None):
        """Create DB tables for Definition classes and restore saved instances.

        Called from managerObject.__init__ AFTER jumpstartDatabase() completes,
        because self.manager.db is None when polariServer.__init__ runs.
        This method:
        1. Creates missing tables for each Definition class
        2. Migrates old tables that lack an 'id' column
        3. Restores previously-saved Definition instances from the DB

        only_classes (mlb-1): restrict the pass to these class names —
        the admission worker calls this once for the core set and then
        once per module. None = everything (monolithic boot).
        """
        db = self.manager.db
        if db is None:
            print('[DefInit] ensureDefinitionTables: no database, skipping', flush=True)
            return
        scoped = ([c for c in self.defClassList
                   if c.__name__ in only_classes]
                  if only_classes is not None else self.defClassList)

        def in_scope(class_name):
            return only_classes is None or class_name in only_classes

        print(f'[DefInit] ensureDefinitionTables: db.tables={db.tables}', flush=True)
        for defClass in scoped:
            className = defClass.__name__
            defTyping = self.manager.objectTypingDict.get(className)
            if defTyping is None:
                print(f'[DefInit] {className}: not in objectTypingDict, skipping', flush=True)
                continue
            if className not in db.tables:
                if defTyping.polyTypedVarsDict:
                    print(f'[DefInit] {className}: creating DB table', flush=True)
                    try:
                        defTyping.makeTypedTableFromAnalysis()
                    except Exception as e:
                        print(f'[DefInit] DB table creation failed for {className}: {e}', flush=True)
                        import traceback
                        traceback.print_exc()
                else:
                    print(f'[DefInit] {className}: no polyTypedVarsDict, cannot create table', flush=True)
            else:
                # Table exists — verify it has an 'id' column
                self._migrateDefinitionTable(className)
                # ...and ALTER-in any columns the class gained since this
                # volume was created (fields added to a persisted class
                # used to be silently dropped by saveInstanceInDB).
                # makeTypedTableFromAnalysis is idempotent: CREATE TABLE
                # IF NOT EXISTS + managedDB._syncTableColumns.
                if defTyping.polyTypedVarsDict:
                    try:
                        defTyping.makeTypedTableFromAnalysis()
                    except Exception as e:
                        print(f'[DefInit] column sync failed for '
                              f'{className}: {e}', flush=True)
        print(f'[DefInit] DB tables after ensureDefinitionTables: {db.tables}', flush=True)
        # Now restore any saved Definition instances
        self._restoreDefinitionInstances(scoped)
        # Register each seeded solution's `boundClass` as a real Polari class
        # so it appears in the Class Manager / Class Selector and can be
        # referenced by Equation bindings. Must run before
        # `_seedSolutionDefinitions` so the class exists when the solution
        # row is created.
        # (Each seed method runs only when its primary class is in
        # scope — the mlb-1 per-module pass skips foreign seeds.)
        if in_scope('SolutionDefinition'):
            self._seedBoundClasses()
            # Seed SolutionDefinition with sample data if the table is empty
            self._seedSolutionDefinitions()
        # Seed EquationDefinition with smoke-test equations if missing
        if in_scope('EquationDefinition'):
            self._seedEquationDefinitions()
        # Seed MatrixDefinition with concept-test + element-kind demos
        if in_scope('MatrixDefinition'):
            self._seedMatrixDefinitions()
        # Seed MatrixEquationDefinition with one example per math kind
        if in_scope('MatrixEquationDefinition'):
            self._seedMatrixEquations()
        # Seed SimSpace2D stock library + a demo space
        if in_scope('Shape2DDefinition'):
            self._seedSimSpace2D()
        # Seed SimSpace3D stock library + a demo space (Phase 2) —
        # ALSO carries the per-module definition seed pairs, which
        # filter to the scope.
        self._seedSimSpace3D(only_classes=only_classes)
        # Seed simulations module — Pendulum2D demo + its SimSpace + binding
        if in_scope('SimulationDefinition'):
            self._seedSimulations()
        # Modules-as-projects boot hook: materialize ONLY rows whose
        # auto_fetch knob is on; everything else surfaces as suggestions.
        # (Monolithic pass only — the admission worker runs it once at
        # the very end of the lazy boot.)
        if only_classes is None:
            try:
                from polariPeers.module_fetcher import auto_fetch_configured
                for result in auto_fetch_configured(self.manager):
                    print(f'[ModuleProjects] auto-fetch: {result}', flush=True)
            except Exception as e:
                print(f'[ModuleProjects] auto-fetch skipped: {e}', flush=True)

    def _migrateDefinitionTable(self, className):
        """Check if a Definition table has an 'id' column and recreate it if not.

        Older versions created tables without an 'id' PRIMARY KEY because
        initializeVarsFromSignature() skipped the 'id' parameter. This
        method detects the old schema and recreates the table with the
        correct structure so instances can be properly persisted.
        """
        db = self.manager.db
        if db is None:
            return
        try:
            conn = db.adapter.connect()
            columns = db.adapter.tableColumns(conn, className)
            conn.close()
            if 'id' not in columns:
                print(f'[polariServer] Migrating {className} table: adding "id" column (recreating table)', flush=True)
                # Drop the old table (it has no usable data without IDs) —
                # dropTable also removes it from db.tables so
                # makeTypedTableFromAnalysis can recreate it.
                db.dropTable(className)
                typingObj = self.manager.objectTypingDict.get(className)
                if typingObj:
                    typingObj.makeTypedTableFromAnalysis()
        except Exception as e:
            print(f'[polariServer] Migration check failed for {className}: {e}', flush=True)

    def _restoreDefinitionInstances(self, defClassList):
        """Restore Definition instances (Table/Graph/Display/GeoJson) from DB.

        These classes are registered in objectTypingDict after
        jumpstartDatabase() → restoreFromDatabase() has already run,
        so their table rows were skipped during the main restore pass.
        This method performs a targeted restore for those classes only.
        """
        db = self.manager.db
        if db is None:
            print('[DefRestore] No database, skipping restore', flush=True)
            return
        import json as jsonLib
        for defClass in defClassList:
            className = defClass.__name__
            if className not in db.tables:
                print(f'[DefRestore] {className}: not in db.tables, skipping', flush=True)
                continue
            # Skip if instances already exist (e.g. from another restore path)
            existing = self.manager.objectTables.get(className, {})
            if existing:
                print(f'[DefRestore] {className}: {len(existing)} instances already in objectTables, skipping', flush=True)
                continue
            try:
                columnNames, dataTuples = db.getAllInTable(className)
            except Exception as e:
                print(f'[DefRestore] {className}: Error reading table: {e}', flush=True)
                continue
            print(f'[DefRestore] {className}: columns={columnNames}, rows={len(dataTuples)}', flush=True)
            if not dataTuples:
                print(f'[DefRestore] {className}: no rows in DB', flush=True)
                continue
            restoredCount = 0
            for row in dataTuples:
                # Build kwargs from DB columns matching constructor params
                initKwargs = {'manager': self.manager}
                for i, colName in enumerate(columnNames):
                    if colName == '_branch_path':
                        continue
                    if row[i] is not None:
                        initKwargs[colName] = row[i]
                print(f'[DefRestore] {className}: restoring with kwargs keys={list(initKwargs.keys())}', flush=True)
                try:
                    instance = defClass(**initKwargs)
                    restoredCount += 1
                    print(f'[DefRestore] {className}: restored instance id={getattr(instance, "id", "?")}', flush=True)
                except Exception as e:
                    print(f'[DefRestore] {className}: Error restoring instance: {e}', flush=True)
                    import traceback
                    traceback.print_exc()
            if restoredCount > 0:
                print(f'[DefRestore] Restored {restoredCount} {className} instances from DB', flush=True)

    def _seedBoundClasses(self):
        """Register every seeded solution's `boundClass` as a real Polari class.

        Without this, classes like `AdditionTester` / `CalculusTester` that are
        only declared inside a seed solution's JSON never get a polyTyping
        entry, never appear in the Class Manager, and can't be referenced by
        Equation bindings (`from_object` / `from_dataset` need the class to
        exist in `manager.objectTypingDict` to be selectable).

        Idempotent: classes already registered (whether by a previous boot or
        a manual `/createClass` POST) are left alone.

        The seed `boundClass` shape uses frontend keys (`name`, `displayName`,
        `type`); we translate them into the `varName` / `varDisplayName` /
        `varType` shape `_createDynamicClass` expects. Method declarations on
        the boundClass are metadata only and intentionally not registered as
        real Python methods (the no-code editor uses them as labels).
        """
        if not getattr(self, 'createClassEndpoint', None):
            print('[SeedBoundClasses] createClassEndpoint not initialised; skipping', flush=True)
            return

        registered_in_this_pass = set()

        for seedData in SEED_SOLUTIONS:
            try:
                definition_str = seedData.get('definition') or ''
                if not definition_str:
                    continue
                definition = json.loads(definition_str) if isinstance(definition_str, str) else definition_str
            except Exception as e:
                print(f"[SeedBoundClasses] Could not parse definition for {seedData.get('name')}: {e}", flush=True)
                continue

            boundClass = definition.get('boundClass') or {}
            className = boundClass.get('className', '').strip()
            if not className:
                continue

            # Skip if this class is already registered (previous boot, manual
            # /createClass call, or earlier in this same pass).
            if className in self.manager.objectTypingDict or className in registered_in_this_pass:
                continue

            displayName = boundClass.get('displayName') or className
            seed_fields = boundClass.get('fields') or []

            # Translate frontend field shape → _createDynamicClass variable shape.
            variables = []
            for f in seed_fields:
                fName = f.get('name') or ''
                if not fName:
                    continue
                variables.append({
                    'varName': fName,
                    'varDisplayName': f.get('displayName') or fName,
                    'varType': f.get('type') or 'str',
                    'isIdentifier': bool(f.get('isIdentifier', False)),
                    'isUnique': bool(f.get('isUnique', False)),
                    # `refClass` carries through for reference / referenceList types.
                    'refClass': f.get('refClass'),
                })

            try:
                self.createClassEndpoint._createDynamicClass(
                    className=className,
                    displayName=displayName,
                    variables=variables,
                    registerCRUDE=True,
                    isStateSpaceObject=True,
                    stateSpaceDisplayFields=[v['varName'] for v in variables],
                    stateSpaceFieldsPerRow=2,
                )
                registered_in_this_pass.add(className)
                print(f'[SeedBoundClasses] Registered: {className} ({len(variables)} fields)', flush=True)
            except Exception as e:
                print(f'[SeedBoundClasses] Failed to register {className}: {e}', flush=True)
                import traceback
                traceback.print_exc()

    def _seedSolutionDefinitions(self):
        """Seed SolutionDefinition with sample solutions if the table is empty.

        This runs once on first startup so the no-code editor has sample data
        to display without requiring the frontend to push mock data.
        """
        typingObj = self.manager.objectTypingDict.get('SolutionDefinition')
        if typingObj is None:
            print('[SeedSolutions] SolutionDefinition not in objectTypingDict, skipping', flush=True)
            return
        existing = self.manager.objectTables.get('SolutionDefinition', {})
        existingDict = existing if isinstance(existing, dict) else {}

        # Build a set of existing solution names for reconciliation
        existingNames = set()
        for objId, obj in existingDict.items():
            name = getattr(obj, 'name', None)
            if name:
                existingNames.add(name)

        seedNames = {s['name'] for s in SEED_SOLUTIONS}

        # Ensure every seed solution exists (create missing ones)
        for seedData in SEED_SOLUTIONS:
            if seedData['name'] in existingNames:
                print(f'[SeedSolutions] Already exists: {seedData["name"]}', flush=True)
                continue
            try:
                instance = SolutionDefinition(
                    name=seedData['name'],
                    function_name=seedData['function_name'],
                    target_runtime=seedData['target_runtime'],
                    definition=seedData['definition'],
                    manager=self.manager
                )
                print(f'[SeedSolutions] Created: {seedData["name"]} (id={getattr(instance, "id", "?")})', flush=True)
            except Exception as e:
                print(f'[SeedSolutions] Failed to create {seedData["name"]}: {e}', flush=True)
                import traceback
                traceback.print_exc()

    def _seedEquationDefinitions(self):
        """Seed EquationDefinition with smoke-test equations if missing.

        Same pattern as _seedSolutionDefinitions: each seed creates a real
        EquationDefinition row that the frontend Equations page can list and
        run. Existing rows with matching names are left alone.
        """
        typingObj = self.manager.objectTypingDict.get('EquationDefinition')
        if typingObj is None:
            print('[SeedEquations] EquationDefinition not in objectTypingDict, skipping', flush=True)
            return

        existing = self.manager.objectTables.get('EquationDefinition', {})
        existingDict = existing if isinstance(existing, dict) else {}
        existingNames = {getattr(obj, 'name', None) for obj in existingDict.values()}

        for seedData in SEED_EQUATIONS:
            if seedData['name'] in existingNames:
                print(f'[SeedEquations] Already exists: {seedData["name"]}', flush=True)
                continue
            try:
                instance = EquationDefinition(
                    name=seedData['name'],
                    description=seedData.get('description', ''),
                    source_class=seedData.get('source_class', ''),
                    definition=seedData['definition'],
                    manager=self.manager,
                )
                print(f'[SeedEquations] Created: {seedData["name"]} (id={getattr(instance, "id", "?")})', flush=True)
            except Exception as e:
                print(f'[SeedEquations] Failed to create {seedData["name"]}: {e}', flush=True)
                import traceback
                traceback.print_exc()

    def _seedMatrixDefinitions(self):
        """Seed MatrixDefinition with concept-test + element-kind demos.

        Same idempotent-by-name pattern as _seedEquationDefinitions. Covers
        numeric literals, matrix-of-matrices composition, equation-typed
        elements, elementwise equations, and a matrix_op expression.
        """
        typingObj = self.manager.objectTypingDict.get('MatrixDefinition')
        if typingObj is None:
            print('[SeedMatrices] MatrixDefinition not in objectTypingDict, skipping', flush=True)
            return

        existing = self.manager.objectTables.get('MatrixDefinition', {})
        existingDict = existing if isinstance(existing, dict) else {}
        existingNames = {getattr(obj, 'name', None) for obj in existingDict.values()}

        for seedData in SEED_MATRICES:
            if seedData['name'] in existingNames:
                print(f'[SeedMatrices] Already exists: {seedData["name"]}', flush=True)
                continue
            try:
                MatrixDefinition(
                    name=seedData['name'],
                    description=seedData.get('description', ''),
                    shape_json=seedData['shape_json'],
                    element_type=seedData['element_type'],
                    element_matrix_ref=seedData.get('element_matrix_ref', ''),
                    values_json=seedData['values_json'],
                    computation_json=seedData['computation_json'],
                    is_template=seedData.get('is_template', False),
                    tags=seedData.get('tags', ''),
                    manager=self.manager,
                )
                print(f'[SeedMatrices] Created: {seedData["name"]}', flush=True)
            except Exception as e:
                print(f'[SeedMatrices] Failed to create {seedData["name"]}: {e}', flush=True)
                import traceback
                traceback.print_exc()

    def _seedMatrixEquations(self):
        """Seed MatrixEquationDefinition with one example per matrix-math kind.

        Idempotent by name. Operands reference the seeded MatrixDefinitions
        (and one references another matrix equation, exercising composition).
        """
        typingObj = self.manager.objectTypingDict.get('MatrixEquationDefinition')
        if typingObj is None:
            print('[SeedMatrixEqs] MatrixEquationDefinition not in objectTypingDict, skipping', flush=True)
            return

        existing = self.manager.objectTables.get('MatrixEquationDefinition', {})
        existingDict = existing if isinstance(existing, dict) else {}
        existingNames = {getattr(obj, 'name', None) for obj in existingDict.values()}

        for seedData in SEED_MATRIX_EQUATIONS:
            if seedData['name'] in existingNames:
                print(f'[SeedMatrixEqs] Already exists: {seedData["name"]}', flush=True)
                continue
            try:
                MatrixEquationDefinition(
                    name=seedData['name'],
                    description=seedData.get('description', ''),
                    latex=seedData.get('latex', ''),
                    operation_json=seedData['operation_json'],
                    operands_json=seedData['operands_json'],
                    tags=seedData.get('tags', ''),
                    manager=self.manager,
                )
                print(f'[SeedMatrixEqs] Created: {seedData["name"]}', flush=True)
            except Exception as e:
                print(f'[SeedMatrixEqs] Failed to create {seedData["name"]}: {e}', flush=True)
                import traceback
                traceback.print_exc()

    def _seedSimSpace2D(self):
        """Seed the SimSpace 2D library (shapes + styles) and a demo space.

        Same idempotent-by-name pattern as _seedEquationDefinitions. Each
        of the three seed lists (shapes, styles, sim-spaces) is checked
        independently so partial-success scenarios are tolerated.
        """
        seed_pairs = [
            ('Shape2DDefinition', Shape2DDefinition, SEED_SHAPES_2D),
            ('Style2DDefinition', Style2DDefinition, SEED_STYLES_2D),
            ('SimSpaceDefinition', SimSpaceDefinition, SEED_SIM_SPACES_2D),
        ]
        for class_name, cls, seed_list in seed_pairs:
            typingObj = self.manager.objectTypingDict.get(class_name)
            if typingObj is None:
                print(f'[SeedSimSpace2D] {class_name} not in objectTypingDict, skipping', flush=True)
                continue
            existing = self.manager.objectTables.get(class_name, {}) or {}
            existing_by_name = {getattr(o, 'name', None): o for o in existing.values()}
            for seed in seed_list:
                if seed.get('name') in existing_by_name:
                    # Migrate legacy 24x24 styles to the new 40x40 default.
                    # Safe heuristic: only resize when the row matches the
                    # *exact* prior defaults (untouched by admins).
                    if class_name == 'Style2DDefinition':
                        row = existing_by_name[seed['name']]
                        if (getattr(row, 'width', None) == 24.0
                                and getattr(row, 'height', None) == 24.0):
                            row.width = seed.get('width', 40.0)
                            row.height = seed.get('height', 40.0)
                            try:
                                self.manager.db.saveInstanceInDB(row)
                                print(f'[SeedSimSpace2D] Resized legacy style "{seed["name"]}" to {row.width}×{row.height}', flush=True)
                            except Exception:
                                pass
                    print(f'[SeedSimSpace2D] {class_name} "{seed["name"]}" exists; skipping', flush=True)
                    continue
                try:
                    cls(**seed, manager=self.manager)
                    print(f'[SeedSimSpace2D] Created {class_name} "{seed["name"]}"', flush=True)
                except Exception as e:
                    print(f'[SeedSimSpace2D] Failed to create {class_name} "{seed.get("name")}": {e}', flush=True)
                    import traceback
                    traceback.print_exc()

    def _seedSimSpace3D(self, only_classes=None):
        """Seed SimSpace 3D library (meshes + materials) + a demo 3D space.
        Same idempotent-by-name pattern as _seedSimSpace2D, plus a small
        upgrade pass that refreshes legacy demo-3d definitions to the
        expanded showcase layout (safe: only updates when the row exactly
        matches the prior seed signature).

        only_classes (mlb-1): the per-module admission pass filters the
        seed pairs to that module's class names; the boot-side hooks at
        the tail run only for the class scope that owns them."""
        seed_pairs = [
            ('Mesh3DDefinition', Mesh3DDefinition, SEED_MESHES_3D),
            # Textures BEFORE materials — materials reference them.
            ('Texture3DDefinition', Texture3DDefinition, SEED_TEXTURES_3D),
            ('Material3DDefinition', Material3DDefinition,
             SEED_MATERIALS_3D + SEED_MOTOR_MATERIALS_3D),
            ('MaterialPhaseAppearance', MaterialPhaseAppearance,
             SEED_MATERIAL_PHASE_APPEARANCES),
            ('SimSpaceDefinition', SimSpaceDefinition,
             SEED_SIM_SPACES_3D + SEED_MOTOR_SIM_SPACES
             + SEED_LAVET_SIM_SPACES
             + SEED_LAVET_V2_SIM_SPACES
             + SEED_M1_SIM_SPACES + SEED_M3_SIM_SPACES),
            # Materials Science: the periodic table as objects + its
            # selection-space demo page.
            ('ChemicalElementDefinition', ChemicalElementDefinition,
             SEED_CHEMICAL_ELEMENTS),
            ('DisplayDefinition', DisplayDefinition,
             SEED_PERIODIC_DISPLAYS + SEED_MSCI_PAGE_DISPLAYS
             + SEED_AQUAPONICS_PAGE_DISPLAYS + SEED_MODULE_PAGE_DISPLAYS
             + SEED_GROUP_DISPLAYS + SEED_WAXPRINT_PAGE_DISPLAYS
             + (SEED_PSPP_PAGE_DISPLAYS or [])
             + SEED_SSP_PAGE_DISPLAYS),
            # Materials basis — identities before their scale rows.
            ('MaterialsScienceMaterial', MaterialsScienceMaterial,
             SEED_MS_MATERIALS + SEED_STANDARD_MATERIALS
             + SEED_POT_MATERIALS + SEED_DIELECTRIC_MATERIALS
             + SEED_BIO_ALLOY_MATERIALS),
            ('MaterialScaleDefinition', MaterialScaleDefinition,
             SEED_MS_SCALE_DEFINITIONS
             + SEED_STANDARD_SCALE_DEFINITIONS
             + SEED_POT_SCALE_DEFINITIONS
             + SEED_L2_L3_SCALE_ROWS),
            # ssp-1: canonical crystal lattices with literature
            # provenance — the L3/L4 structural representation.
            ('CrystalStructureDefinition', CrystalStructureDefinition,
             SEED_CRYSTAL_STRUCTURES),
            # Modules-as-projects: the in-tree module, config-tracked.
            ('ModuleSourceConfig', ModuleSourceConfig,
             SEED_MODULE_SOURCE_CONFIGS),
            # hwsim-1: the Renode rig twin exists from boot so its
            # schema can stabilize before the first telemetry frame.
            ('SimRigState', SimRigState, SEED_SIM_RIGS),
            # hwsim-3: the Hardware Runtime register map — maps
            # before their registers (registers name their map).
            ('RegisterMapDefinition', RegisterMapDefinition,
             SEED_REGISTER_MAPS),
            ('RegisterDefinition', RegisterDefinition,
             SEED_REGISTERS),
            ('FpgaRegisterState', FpgaRegisterState,
             SEED_FPGA_STATES),
            ('LedMatrix4x4State', LedMatrix4x4State,
             SEED_LED_MATRICES),
            ('ElectronicDeviceDefinition', ElectronicDeviceDefinition,
             SEED_DEVICES),
            ('SemiconductorProfile', SemiconductorProfile,
             SEED_SEMICONDUCTOR_PROFILES),
            ('PhotoAbsorberDefinition', PhotoAbsorberDefinition,
             SEED_PHOTO_ABSORBERS),
            ('SolarStackDefinition', SolarStackDefinition,
             SEED_SOLAR_STACKS),
            ('SolarLayerDefinition', SolarLayerDefinition,
             SEED_SOLAR_LAYERS),
            # Thermal windows from the Base Wax Properties notes.
            ('ThermalProcessingProfile', ThermalProcessingProfile,
             SEED_THERMAL_PROFILES),
            # Property meanings the material detail view explains with.
            ('MaterialPropertyMeaning', MaterialPropertyMeaning,
             SEED_PROPERTY_MEANINGS + SEED_POT_PROPERTY_MEANINGS
             + SEED_DIELECTRIC_PROPERTY_MEANINGS
             + SEED_BIO_ALLOY_PROPERTY_MEANINGS
             + (SEED_CMC_PROPERTY_MEANINGS or [])),
            # pspp (pspp-1): evidence vocabulary + book datasets —
            # claims have no seeds (they are earned, never seeded).
            ('EvidenceMethod', EvidenceMethod, SEED_EVIDENCE_METHODS),
            ('DigitizedDataset', DigitizedDataset,
             SEED_DIGITIZED_DATASETS
             + (SOLGEL_DIGITIZED_DATASETS or [])
             + (SEED_SINTERING_DATASETS or [])
             + (SEED_CERAMICS_DATASETS or [])
             + (SEED_CHARACTERIZATION_DATASETS or [])
             + (GLASS_DIGITIZED_DATASETS or [])),
            # pspp-2: stage vocabulary rows; MaterialState never seeds.
            ('ProcessingStage', ProcessingStage,
             SEED_PROCESSING_STAGES
             + (SEED_CMC_PROCESSING_STAGES or [])
             + (SOLGEL_PROCESSING_STAGES or [])),
            # pspp-4: process vocabulary, patent windows, and the
            # reaction-network library (species before the rules that
            # trade in them). Executions/states are earned, not seeded.
            ('MaterialProcessDefinition', MaterialProcessDefinition,
             SEED_PROCESS_DEFINITIONS
             + (SEED_CMC_PROCESS_DEFINITIONS or [])),
            ('ReactionWindow', ReactionWindow, SEED_REACTION_WINDOWS),
            ('ThresholdReactionWindow', ThresholdReactionWindow,
             SEED_THRESHOLD_WINDOWS
             + (SOLGEL_THRESHOLD_WINDOWS or [])
             + (GLASS_THRESHOLD_WINDOWS or [])),
            ('BenchmarkCase', BenchmarkCase, SEED_BENCHMARK_CASES),
            ('ChemicalSpecies', ChemicalSpecies,
             SEED_CHEMICAL_SPECIES
             + (SOLGEL_CHEMICAL_SPECIES or [])),
            ('ReactionRule', ReactionRule,
             SEED_REACTION_RULES
             + (SOLGEL_REACTION_RULES or [])),
            # mtt-2 sg-community: precursor sourcing / common-material
            # accessibility for the sol-gel routes.
            ('PrecursorSource', PrecursorSource,
             SEED_PRECURSOR_SOURCES or []),
            # mtt-2 ceramics: usable samples + the furnace escalation
            # ladder (the thermal strain of material refinement).
            ('CeramicSample', CeramicSample,
             SEED_CERAMIC_SAMPLES or []),
            ('LadderRung', LadderRung, SEED_LADDER_RUNGS or []),
            # mtt-2 research tools (the measurement half).
            ('ResearchTool', ResearchTool, SEED_RESEARCH_TOOLS or []),
            ('ScaleTransferDefinition', ScaleTransferDefinition,
             SEED_SCALE_TRANSFERS),
            ('ExposureScenario', ExposureScenario,
             SEED_EXPOSURE_SCENARIOS),
            # Context-based scoring: terms/contexts/subjects before the
            # values and concepts that reference them.
            ('ScoreTerm', ScoreTerm,
             SEED_SCORE_TERMS + SEED_COST_TERMS
             + SEED_AQP_SCORE_TERMS + SEED_ENRICH_SCORE_TERMS
             + SEED_HOUSING_SCORE_TERMS + SEED_IMPLICATION_SCORE_TERMS
             + SEED_DMV_TERMS + SEED_ESCAPE_COST_TERMS
             + SEED_PROVIDER_TERMS),
            ('ScoreContext', ScoreContext,
             SEED_SCORE_CONTEXTS + SEED_DMV_GEO_CONTEXTS
             + SEED_DMV_TIMEFRAMES + SEED_PERSONA_CONTEXTS),
            ('ScoreSubject', ScoreSubject,
             SEED_SCORE_SUBJECTS + SEED_POLICY_SUBJECTS
             + SEED_POLITICIAN_SUBJECTS + SEED_MEDIA_OUTLETS
             + SEED_AQP_SCORE_SUBJECTS + SEED_ENRICH_SCORE_SUBJECTS
             + SEED_IMPLICATION_SUBJECTS + SEED_DMV_SUBJECTS),
            ('ContextualizedValue', ContextualizedValue,
             SEED_CONTEXTUALIZED_VALUES
             + SEED_AQP_CONTEXTUALIZED_VALUES
             + SEED_ENRICH_CONTEXTUALIZED_VALUES
             + SEED_HOUSING_CONTEXTUALIZED_VALUES
             + SEED_IMPLICATION_CONTEXTUALIZED_VALUES
             + SEED_STATUTE_VALUES),
            ('ScoreConcept', ScoreConcept,
             SEED_SCORE_CONCEPTS + SEED_AQP_SCORE_CONCEPTS
             + SEED_ENRICH_SCORE_CONCEPTS
             + SEED_HOUSING_SCORE_CONCEPTS
             + SEED_INTERPRETATION_SCORE_CONCEPTS
             + SEED_PROVIDER_CONCEPT),
            # Groups + the editable agreement-classification bands
            # (concepts first — groups reference member concepts).
            ('ScoreGroup', ScoreGroup,
             SEED_SCORE_GROUPS + SEED_COHORT_GROUPS
             + SEED_ASSEMBLY_GROUPS + SEED_HOUSING_SCORE_GROUPS
             + SEED_INTERPRETATION_SCORE_GROUPS),
            ('AgreementPolicy', AgreementPolicy,
             SEED_AGREEMENT_POLICIES),
            # scr-5: contributors before the evidence/assertions that
            # cite them; evidence before assertions.
            ('Contributor', Contributor,
             SEED_CONTRIBUTORS + SEED_HOUSING_CONTRIBUTORS
             + SEED_LOGIC_FORK_CONTRIBUTORS),
            ('EvidencePolicy', EvidencePolicy,
             SEED_EVIDENCE_POLICIES),
            ('MediaEvidence', MediaEvidence, SEED_MEDIA_EVIDENCE),
            ('ScoreAssertion', ScoreAssertion,
             SEED_SCORE_ASSERTIONS + SEED_IMPLICATION_ASSERTIONS),
            ('AssertionValidityVote', AssertionValidityVote,
             SEED_VALIDITY_VOTES + SEED_IMPLICATION_VALIDITY_VOTES),
            # scr-6: votes after the politician/policy subjects they
            # reference.
            ('PolicyVote', PolicyVote, SEED_POLICY_VOTES),
            # scr-8: elections after the groups/worldviews they run
            # over; ballots after their election.
            ('WorldviewElection', WorldviewElection,
             SEED_WORLDVIEW_ELECTIONS + SEED_HOUSING_ELECTIONS
             + SEED_INTERPRETATION_ELECTIONS),
            ('WorldviewBallot', WorldviewBallot,
             SEED_WORLDVIEW_BALLOTS + SEED_HOUSING_BALLOTS
             + SEED_INTERPRETATION_BALLOTS),
            # Phase 4 mechanism A: votes after their group + candidate
            # Displays (both seeded above); ballots after their vote.
            ('GroupDisplayVote', GroupDisplayVote,
             SEED_GROUP_DISPLAY_VOTES),
            ('GroupDisplayBallot', GroupDisplayBallot,
             SEED_GROUP_DISPLAY_BALLOTS),
            # Mechanism C: logic-fork criteria before the votes that
            # reference them as candidates; ballots after their vote.
            ('LogicForkCriterion', LogicForkCriterion,
             SEED_LOGIC_FORK_CRITERIA),
            ('LogicForkVote', LogicForkVote, SEED_LOGIC_FORK_VOTES),
            ('LogicForkBallot', LogicForkBallot,
             SEED_LOGIC_FORK_BALLOTS),
            ('DecisionProcedureEdge', DecisionProcedureEdge,
             SEED_DECISION_PROCEDURE_EDGES),
            # System-choice implications: which criterion is actually
            # deployed where (references LogicForkCriterion by name,
            # resolved live, no ordering dependency).
            ('SystemChoiceInForce', SystemChoiceInForce,
             SEED_SYSTEM_CHOICES_IN_FORCE),
            # ncg-2: the compiler registry rows, then cases (cases
            # are runtime data — no seeds, the table registers).
            ('GraphCompilerDefinition', GraphCompilerDefinition,
             SEED_GRAPH_COMPILERS),
            ('CourtCase', CourtCase, []),
            # Group/instance authority rows are runtime data (grants
            # and bindings are explicit acts, never seeded) — the
            # tables just register.
            ('GroupAuthorityGrant', GroupAuthorityGrant, []),
            ('InstanceAuthorityGrant', InstanceAuthorityGrant, []),
            ('GroupInstanceBinding', GroupInstanceBinding, []),
            ('TermAvailabilitySignal', TermAvailabilitySignal, []),
            # AR zones: sites before zones before points (rows
            # reference upward by name); estimates are runtime data.
            ('SiteDefinition', SiteDefinition, SEED_SITES),
            ('ZoneDefinition', ZoneDefinition, SEED_ZONES),
            ('ZonePoint', ZonePoint, SEED_ZONE_POINTS),
            ('ZoneEstimateRecord', ZoneEstimateRecord, []),
            # ncg-3: designs before their nodes (nodes reference the
            # design by name).
            ('LogicBlockDesign', LogicBlockDesign,
             SEED_LOGIC_DESIGNS),
            ('LogicBlockNode', LogicBlockNode, SEED_LOGIC_NODES),
            # ncg-4: circuits before nets before components (both
            # reference the circuit by name).
            ('CircuitDefinition', CircuitDefinition, SEED_CIRCUITS),
            ('CircuitNetDefinition', CircuitNetDefinition,
             SEED_CIRCUIT_NETS),
            ('CircuitComponentDefinition',
             CircuitComponentDefinition, SEED_CIRCUIT_COMPONENTS),
            # ncg-5: boards before placements/jumpers (both
            # reference boards by name).
            ('BreadboardDefinition', BreadboardDefinition,
             SEED_BREADBOARDS),
            ('ComponentPlacement', ComponentPlacement,
             SEED_PLACEMENTS),
            ('BoardJumper', BoardJumper, SEED_JUMPERS),
            # ncg-6: bindings after the designs/placements they
            # reference; packs before their cases.
            ('PinBindingDefinition', PinBindingDefinition,
             SEED_PIN_BINDINGS),
            ('NoCodeTestPack', NoCodeTestPack, SEED_TEST_PACKS),
            ('NoCodeTestCase', NoCodeTestCase, SEED_TEST_CASES),
            # col-2: source domains before the endpoints that
            # reference them by domainName.
            ('APIDomain', APIDomain,
             SEED_API_DOMAINS + SEED_LEGIS_DOMAINS),
            ('APIEndpoint', APIEndpoint,
             SEED_API_ENDPOINTS + SEED_LEGIS_ENDPOINTS),
            ('GovSource', GovSource,
             SEED_GOV_SOURCES + SEED_LEGIS_GOV_SOURCES),
            ('SourceRetrieval', SourceRetrieval, []),
            ('RetrievalConfirmation', RetrievalConfirmation, []),
            ('NonProfitSource', NonProfitSource,
             SEED_NONPROFIT_SOURCES),
            ('CompanySource', CompanySource, SEED_COMPANY_SOURCES),
            ('PoliticalGroupSource', PoliticalGroupSource,
             SEED_POLITICAL_SOURCES),
            ('IndividualSource', IndividualSource,
             SEED_INDIVIDUAL_SOURCES),
            # Drafts + venue records are runtime data; the pattern
            # catalog seeds Dustin's two sequences (votable rows).
            ('PolicyDraft', PolicyDraft, []),
            ('VenueMismatchPattern', VenueMismatchPattern,
             SEED_VENUE_PATTERNS),
            ('VenueActionRecord', VenueActionRecord, []),
            # Legislation rows are runtime data (API pulls or the
            # manual-entry acts).
            ('LegislationRecord', LegislationRecord, []),
            ('LegislationProvision', LegislationProvision, []),
            ('LegislativeVoteEvent', LegislativeVoteEvent, []),
            ('DataGatheringSolution', DataGatheringSolution, []),
            ('StepCredibilityAssertion', StepCredibilityAssertion,
             []),
            ('AssertionCredibilityVote', AssertionCredibilityVote,
             []),
            ('PolicyIntent', PolicyIntent, []),
            ('TermProposal', TermProposal, []),
            ('TermRelationAssertion', TermRelationAssertion, []),
            ('TermScopeVote', TermScopeVote, []),
            ('DataManipulationPattern', DataManipulationPattern,
             SEED_MANIPULATION_PATTERNS),
            ('TermProof', TermProof, []),
            ('ProofRebuttal', ProofRebuttal, []),
            ('ProofVote', ProofVote, []),
            ('CredibilityClaim', CredibilityClaim, []),
            ('ClaimAttestation', ClaimAttestation, []),
            ('StanceBasis', StanceBasis, []),
            ('QualificationRelevanceVote',
             QualificationRelevanceVote, []),
            # scr-15: claims after the outlets/terms they reference.
            ('AccuracyPolicy', AccuracyPolicy,
             SEED_ACCURACY_POLICIES),
            ('FactualClaim', FactualClaim, SEED_FACTUAL_CLAIMS),
            # scr-16: bias bands as editable rows.
            ('BiasPolicy', BiasPolicy, SEED_BIAS_POLICIES),
            # scr-12a: the walkthrough vocabulary + demo households.
            ('CostCategory', CostCategory,
             SEED_COST_CATEGORIES + SEED_ESCAPE_COST_CATEGORIES),
            ('SurvivalCostProfile', SurvivalCostProfile,
             SEED_SURVIVAL_PROFILES),
            # waxprint (wp-1): device materials + wax feedstocks BEFORE the
            # assemblies (which ref materials) and conditions.
            ('DeviceMaterialDefinition', DeviceMaterialDefinition,
             SEED_DEVICE_MATERIALS),
            ('WaxFeedstockDefinition', WaxFeedstockDefinition,
             SEED_FEEDSTOCKS),
            ('PrinterAssemblyDefinition', PrinterAssemblyDefinition,
             SEED_ASSEMBLIES),
            ('PrintConditionDefinition', PrintConditionDefinition,
             SEED_CONDITIONS),
            # waxprint sim space (wp-5): pre-computed baseline run states
            # (the two seeded runs render in the wax-print-wall scene).
            ('WaxPrintSimState', WaxPrintSimState, SEED_WAXPRINT_STATE_ROWS),
            # waxprint (wp-8): first-class Polari Module identity row.
            ('PolariModule', PolariModule,
             SEED_WAXPRINT_MODULES + SEED_OSEB_POLARI_MODULES),
            # Tech tree (tt-5): the OSEB baseline tree — definition
            # before nodes, nodes before assignments. Edges are
            # NEVER seeded: TechDependencyEdge rows derive from
            # depends_on_json (sync on read/write), like drift.
            ('TechTreeDefinition', TechTreeDefinition,
             SEED_TECH_TREE_DEFINITIONS),
            ('TechNode', TechNode, SEED_TECH_NODES),
            ('TechSegmentAssignment', TechSegmentAssignment,
             SEED_TECH_SEGMENT_ASSIGNMENTS),
            # tt-6 worked examples (honest state: unproven printer,
            # unevidenced business model + policy — their gaps name
            # exactly what makes them real).
            ('RealArtifact', RealArtifact, SEED_REAL_ARTIFACTS),
            ('BusinessModelDefinition', BusinessModelDefinition,
             SEED_BUSINESS_MODELS),
            ('PolicyDefinition', PolicyDefinition,
             SEED_POLICY_DEFINITIONS),
            # Polari-Apps (tt-12): the three worked use-cases.
            # AppDeploymentPlan rows are receipts — never seeded.
            ('PolariAppDefinition', PolariAppDefinition,
             SEED_POLARI_APPS),
            # aqp-1: self-watering pots + their side holes (pots
            # before holes — holes reference their pot).
            ('PotDefinition', PotDefinition, SEED_POTS),
            ('PotHole', PotHole, SEED_POT_HOLES),
            # aqp-2: species vocab before profiles; soils/waters
            # reference profiles.
            ('NutrientSpecies', NutrientSpecies,
             SEED_NUTRIENT_SPECIES),
            ('NutrientProfile', NutrientProfile,
             SEED_NUTRIENT_PROFILES),
            ('SoilDefinition', SoilDefinition, SEED_SOILS),
            ('WaterDefinition', WaterDefinition, SEED_WATERS),
            # aqp-4: plants before their parts (parts reference plant).
            ('PlantDefinition', PlantDefinition, SEED_PLANTS),
            ('PlantPart', PlantPart, SEED_PLANT_PARTS),
            # aqp-5: atmospheric environments.
            ('AtmosphereDefinition', AtmosphereDefinition,
             SEED_ATMOSPHERES),
            # Plant-growth-sim phase 8: light spectra/sources (before
            # PotSystemDefinition, which references a source by name).
            ('LightSpectrumDefinition', LightSpectrumDefinition,
             SEED_LIGHT_SPECTRA),
            ('LightSourceDefinition', LightSourceDefinition,
             SEED_LIGHT_SOURCES),
            # Plant-growth-sim phase 10: water batch schedules (before
            # PotSystemDefinition, which references one by name).
            ('WaterBatchSchedule', WaterBatchSchedule,
             SEED_WATER_BATCH_SCHEDULES),
            # aqp-6: bound pot systems (the scoring rows above bind to
            # these via objectRef into impact_result_json).
            ('PotSystemDefinition', PotSystemDefinition,
             SEED_POT_SYSTEMS),
            # aqp-7: worm-compost — profiles + bins before the loops
            # (loops reference the bin + pot system).
            ('VermicompostProfile', VermicompostProfile,
             SEED_VERMICOMPOST_PROFILES),
            ('CompostBinDefinition', CompostBinDefinition,
             SEED_COMPOST_BINS),
            ('CompostLoopDefinition', CompostLoopDefinition,
             SEED_COMPOST_LOOPS),
            # aqp-8: per-part growth models (reference PlantPart rows
            # seeded above).
            ('PlantGrowthModel', PlantGrowthModel,
             SEED_PLANT_GROWTH_MODELS),
            # nut-1/3/4: nutrient vocab before references; persons
            # before the household that lists them.
            ('DietaryNutrient', DietaryNutrient,
             SEED_DIETARY_NUTRIENTS),
            ('NutrientReference', NutrientReference,
             SEED_NUTRIENT_REFERENCES),
            ('PersonProfile', PersonProfile, SEED_PERSONS),
            ('HouseholdProfile', HouseholdProfile, SEED_HOUSEHOLDS),
            # nut-2: foods before their per-nutrient contents.
            ('FoodItem', FoodItem, SEED_FOOD_ITEMS),
            ('NutrientContent', NutrientContent,
             SEED_NUTRIENT_CONTENTS),
            # morph-1: 3D organ + root stand-in models.
            ('OrganModel', OrganModel, SEED_ORGAN_MODELS),
            ('RootSystemModel', RootSystemModel, SEED_ROOT_MODELS),
            # Plant-growth-sim phase 1: real plantings (after
            # PotDefinition + PlantDefinition, which they reference).
            ('PotPlanting', PotPlanting, SEED_POT_PLANTINGS),
            # Plant-growth-sim phase 7: stress-type response curves.
            ('StressResponseCurve', StressResponseCurve,
             SEED_STRESS_CURVES),
            # shape-1: math-defined shapes (quadric/primitive/CSG).
            ('MathShapeDefinition', MathShapeDefinition,
             SEED_MATH_SHAPES + SEED_MOTOR_PART_SHAPES
             + SEED_LAVET_PART_SHAPES
             + SEED_LAVET_V2_PART_SHAPES
             + SEED_M1_PART_SHAPES + SEED_M3_PART_SHAPES),
            # shape-2: aquaponic towers (reference math-defined pots).
            ('AquaponicTowerDefinition', AquaponicTowerDefinition,
             SEED_TOWERS),
            # tank-1/2: species + substrates before tanks (tanks
            # reference a substrate); tanks before the systems.
            ('AquacultureSpecies', AquacultureSpecies,
             SEED_AQUACULTURE_SPECIES),
            ('TankSubstrateDefinition', TankSubstrateDefinition,
             SEED_TANK_SUBSTRATES),
            ('TankDefinition', TankDefinition, SEED_TANKS),
            ('TankSystemDefinition', TankSystemDefinition,
             SEED_TANK_SYSTEMS),
            # algae-1: strains before the reactors that use them.
            ('AlgaeStrain', AlgaeStrain, SEED_ALGAE_STRAINS),
            ('AlgaeReactorDefinition', AlgaeReactorDefinition,
             SEED_ALGAE_REACTORS),
            # algae-2: integrated loops (after tanks + reactors exist).
            ('IntegratedLoopDefinition', IntegratedLoopDefinition,
             SEED_INTEGRATED_LOOPS),
            # biomine-1 (+ optical-dielectric): agents + products before
            # the systems that use them.
            ('BioextractionAgent', BioextractionAgent,
             SEED_BIOEXTRACTION_AGENTS + SEED_OPTICAL_AGENTS
             + SEED_ALLOY_AGENTS),
            ('BiomineralProduct', BiomineralProduct,
             SEED_BIOMINERAL_PRODUCTS + SEED_OPTICAL_PRODUCTS
             + SEED_ALLOY_PRODUCTS),
            ('BiomineSystemDefinition', BiomineSystemDefinition,
             SEED_BIOMINE_SYSTEMS + SEED_OPTICAL_BIOMINE_SYSTEMS
             + SEED_ALLOY_BIOMINE_SYSTEMS),
            # video-1: no baseline seed data — assets are user-uploaded.
            ('VideoAsset', VideoAsset, []),
            # wax-1: bio wax sources for molds / electronic masks.
            ('WaxSourceDefinition', WaxSourceDefinition,
             SEED_WAX_SOURCES),
            # Odoo endpoints — sim free, ops guarded (od-3);
            # instances before the bindings that name them (od-4).
            ('OdooInstanceConfig', OdooInstanceConfig,
             SEED_ODOO_INSTANCES),
            ('OdooModelBinding', OdooModelBinding,
             SEED_ODOO_BINDINGS),
            ('BusinessScenarioDefinition', BusinessScenarioDefinition,
             SEED_BUSINESS_SCENARIOS),
            # biz-1: stages before profiles that name them.
            ('BusinessStageDefinition', BusinessStageDefinition,
             SEED_BUSINESS_STAGES),
            ('BusinessUpgradeStep', BusinessUpgradeStep,
             SEED_BUSINESS_UPGRADES),
            ('BusinessProfile', BusinessProfile,
             SEED_BUSINESS_PROFILES),
            ('LocalEconomyMilestone', LocalEconomyMilestone,
             SEED_ECONOMY_MILESTONES),
            ('ProcessWorkflowDefinition', ProcessWorkflowDefinition,
             SEED_PROCESS_WORKFLOWS),
            ('BusinessRiskNote', BusinessRiskNote,
             SEED_RISK_NOTES),
            ('PartnershipAgreement', PartnershipAgreement,
             SEED_PARTNERSHIPS),
            ('ComplianceRequirement', ComplianceRequirement,
             SEED_COMPLIANCE_REQUIREMENTS),
            ('QualityCheckDefinition', QualityCheckDefinition,
             SEED_QUALITY_CHECKS),
            # mag-2r/2/2t: roles before the options whose viability
            # derives against them; powders before options that
            # reference them by powder_ref.
            ('MaterialUseRole', MaterialUseRole, SEED_USE_ROLES),
            ('MagneticPowderDefinition', MagneticPowderDefinition,
             SEED_MAGNETIC_POWDERS),
            ('MagneticMaterialOption', MagneticMaterialOption,
             SEED_MATERIAL_OPTIONS),
            # mag-3: circuits before nodes/elements that name them.
            ('MagneticCircuitDefinition', MagneticCircuitDefinition,
             SEED_MAGNETIC_CIRCUITS),
            ('FluxNodeDefinition', FluxNodeDefinition,
             SEED_FLUX_NODES),
            ('MagneticElementDefinition', MagneticElementDefinition,
             SEED_MAGNETIC_ELEMENTS),
            # mag-4: variants before placements; layouts before
            # placements/joints that name them.
            ('BlockSizeVariant', BlockSizeVariant,
             SEED_BLOCK_VARIANTS),
            ('BlockLayoutDefinition', BlockLayoutDefinition,
             SEED_BLOCK_LAYOUTS),
            ('BlockPlacement', BlockPlacement,
             SEED_BLOCK_PLACEMENTS),
            ('JointMortarAssignment', JointMortarAssignment,
             SEED_JOINT_MORTARS),
            # mag-fv: views before bands/groups that name them.
            ('FieldViewDefinition', FieldViewDefinition,
             SEED_FIELD_VIEWS),
            ('FieldThresholdBand', FieldThresholdBand,
             SEED_FIELD_BANDS),
            ('FieldViewGroup', FieldViewGroup, SEED_FIELD_GROUPS),
            # mag-5: the ladder designs; verification runs NEVER
            # seeded (observed state).
            ('MotorDesignDefinition', MotorDesignDefinition,
             SEED_MOTOR_DESIGNS),
            ('MotorVerificationRun', MotorVerificationRun, []),
            # mag-6: drive profiles + phase bindings.
            ('MotorControllerProfile', MotorControllerProfile,
             SEED_CONTROLLER_PROFILES),
            ('PhaseBindingDefinition', PhaseBindingDefinition,
             SEED_PHASE_BINDINGS),
            # mag-11: parts AFTER designs (they reference them).
            ('MotorPartDefinition', MotorPartDefinition,
             SEED_MOTOR_PARTS),
            # mesh-1: sources carry the licence finding, so they
            # seed BEFORE the assets that cite them. Picks
            # (OrganMeshChoice) are never seeded — choosing an
            # approximation is a human act.
            ('MeshAssetSource', MeshAssetSource, SEED_MESH_SOURCES),
            ('MeshAssetReference', MeshAssetReference,
             SEED_MESH_ASSETS),
            ('OrganMeshChoice', OrganMeshChoice, []),
            # gr-1: the type taxonomy first (bodies reference it),
            # then shafts, trains, bodies, meshes. Verification runs
            # NEVER seeded (observed state, the motors rule).
            ('GearTypeDefinition', GearTypeDefinition,
             SEED_GEAR_TYPES),
            ('ShaftNodeDefinition', ShaftNodeDefinition,
             SEED_SHAFT_NODES),
            ('GearTrainDefinition', GearTrainDefinition,
             SEED_GEAR_TRAINS),
            ('GearDefinition', GearDefinition, SEED_GEARS),
            ('GearMeshDefinition', GearMeshDefinition,
             SEED_GEAR_MESHES),
            ('GearVerificationRun', GearVerificationRun, []),
            # chain-1: nodes + flows before the chain that binds them.
            ('SupplyNode', SupplyNode, SEED_SUPPLY_NODES),
            ('SupplyFlow', SupplyFlow, SEED_SUPPLY_FLOWS),
            ('SupplyChainDefinition', SupplyChainDefinition,
             SEED_SUPPLY_CHAINS),
            # Sourcing (src-1): sources before citations that name
            # them; the ladder is independent.
            ('SupplySourceProfile', SupplySourceProfile,
             SEED_SUPPLY_SOURCES),
            ('PriceCitation', PriceCitation,
             SEED_PRICE_CITATIONS),
            ('SourcePreferencePolicy', SourcePreferencePolicy,
             SEED_SOURCE_POLICIES),
            # Formula layer (src-2): requirements before formulas.
            ('ProductInputRequirement', ProductInputRequirement,
             SEED_PRODUCT_REQUIREMENTS),
            ('ProductFormula', ProductFormula,
             SEED_PRODUCT_FORMULAS),
            # The MVW wax derivation as a configurable search object.
            ('FormulationSearchDefinition', FormulationSearchDefinition,
             SEED_FORMULATION_SEARCHES),
            # Engine-model layer: the catalog before the models that
            # reference it.
            ('EngineModelTemplate', EngineModelTemplate,
             SEED_ENGINE_MODEL_TEMPLATES),
            ('FEMModelDefinition', FEMModelDefinition,
             SEED_FEM_MODELS + SEED_STANDARD_FEM_MODELS
             + SEED_DERIVED_VFC_MODELS),
            # msci-26: MD + meso models BEFORE the scale rows that
            # reference them.
            ('MDModelDefinition', MDModelDefinition, SEED_MD_MODELS),
            ('MesoModelDefinition', MesoModelDefinition,
             SEED_MESO_MODELS),
            ('DFTModelDefinition', DFTModelDefinition,
             SEED_DFT_MODELS + SEED_STANDARD_DFT_MODELS),
            # Topology orchestration (top-1): machines + targets
            # before the definition; the definition before the
            # instances; instances before assignments/edges/
            # connections that reference them. Observations are
            # NEVER seeded — observed state is reported.
            ('PolariNodeMachine', PolariNodeMachine,
             SEED_NODE_MACHINES),
            ('OrchestrationTarget', OrchestrationTarget,
             SEED_ORCHESTRATION_TARGETS),
            ('TopologyDefinition', TopologyDefinition,
             SEED_TOPOLOGY_DEFINITIONS),
            ('InstanceDefinition', InstanceDefinition,
             SEED_INSTANCE_DEFINITIONS),
            ('ModuleAssignment', ModuleAssignment,
             SEED_MODULE_ASSIGNMENTS),
            ('ModuleDependencyEdge', ModuleDependencyEdge,
             SEED_MODULE_DEPENDENCY_EDGES),
            ('ServiceConnection', ServiceConnection,
             SEED_SERVICE_CONNECTIONS),
            # Resource profiles (res-2): declared floors/scalability
            # for known subjects; res-3 measurement overrides.
            ('ModuleResourceProfile', ModuleResourceProfile,
             SEED_MODULE_RESOURCE_PROFILES),
            # XR cascade (xr-1): the global singleton + category type
            # defaults (Q9 seeds — suggestions made durable, editable).
            ('XrGlobalSettings', XrGlobalSettings,
             SEED_XR_GLOBAL_SETTINGS),
            ('XrTypeDefault', XrTypeDefault, SEED_XR_TYPE_DEFAULTS),
            # acct-0: every discovered test surface as a never-run
            # CapabilityCheck row (skipped on normal builds — the
            # class is absent from objectTypingDict). CheckRun rows
            # are never seeded: runs are observed state.
            ('CapabilityCheck', CapabilityCheck,
             SEED_CAPABILITY_CHECKS),
        ]
        # Old demo-3d description (used as the "untouched" signature). If
        # the existing demo-3d row still has this verbatim, we treat it
        # as un-customized and overwrite to the new showcase layout.
        LEGACY_DEMO_3D_DESCRIPTION = (
            'Demo SimSpace3D — five primitives arranged in a row. '
            'Proves the 3D renderer wires up behind the same '
            'SimSpaceRenderer interface as 2D.'
        )
        if only_classes is not None:
            seed_pairs = [(n, c, s) for n, c, s in seed_pairs
                          if n in only_classes]
        for class_name, cls, seed_list in seed_pairs:
            typingObj = self.manager.objectTypingDict.get(class_name)
            if typingObj is None:
                print(f'[SeedSimSpace3D] {class_name} not in objectTypingDict, skipping', flush=True)
                continue
            existing = self.manager.objectTables.get(class_name, {}) or {}
            existing_by_name = {getattr(o, 'name', None): o for o in existing.values()}
            for seed in seed_list:
                name = seed.get('name')
                if name in existing_by_name:
                    row = existing_by_name[name]
                    # Demo-3d upgrade — only when the row is still the
                    # legacy showcase (admin hasn't touched description).
                    if (class_name == 'SimSpaceDefinition'
                            and name == 'demo-3d'
                            and getattr(row, 'description', '') == LEGACY_DEMO_3D_DESCRIPTION):
                        for key in (
                            'description', 'viewport_json', 'bound_classes_json', 'definition',
                        ):
                            if key in seed:
                                setattr(row, key, seed[key])
                        try:
                            self.manager.db.saveInstanceInDB(row)
                            print(f'[SeedSimSpace3D] Upgraded legacy demo-3d to showcase layout', flush=True)
                        except Exception:
                            pass
                    print(f'[SeedSimSpace3D] {class_name} "{name}" exists; skipping create', flush=True)
                    continue
                try:
                    cls(**seed, manager=self.manager)
                    print(f'[SeedSimSpace3D] Created {class_name} "{name}"', flush=True)
                except Exception as e:
                    print(f'[SeedSimSpace3D] Failed to create {class_name} "{name}": {e}', flush=True)
                    import traceback
                    traceback.print_exc()
        # arch-1: composition seeds go through the UPSERT path —
        # changed seed fields REACH live prior rows instead of
        # requiring hand CRUDE PUTs (the ten-strikes gotcha, ended
        # for these tables). Runs in composition's admission pass.
        if _feature_available('composition') and (
                only_classes is None
                or 'CompositionNode' in only_classes):
            try:
                from composition.composition_seed import (
                    seed_composition,
                )
                reports = seed_composition(self.manager)
                changed = [
                    (r['class'], len(r.get('inserted', [])),
                     len(r.get('updated', [])))
                    for r in reports
                    if r.get('inserted') or r.get('updated')]
                if changed:
                    print(f'[CompositionSeed] converged: {changed}',
                          flush=True)
            except Exception as e:
                print(f'[CompositionSeed] failed: {e}', flush=True)
        # goal-1: scale/goal seeds, same upsert path, motors-gated.
        if _feature_available('motors') and (
                only_classes is None
                or 'ClockScaleDefinition' in only_classes):
            try:
                from motors.clock_assembly import (
                    seed_clock_assembly,
                )
                from motors.clock_scene import seed_clock_scene
                from motors.clock_views import seed_clock_views
                from motors.motor_shapes import seed_v2_shapes
                from motors.scale_goals import seed_scale_goals
                for r in (seed_scale_goals(self.manager)
                          + seed_clock_views(self.manager)
                          + seed_clock_scene(self.manager)
                          + seed_v2_shapes(self.manager)
                          + seed_clock_assembly(self.manager)):
                    if r.get('inserted') or r.get('updated'):
                        print(f'[ScaleGoalsSeed] {r["class"]}: '
                              f'+{len(r.get("inserted", []))} '
                              f'~{len(r.get("updated", []))}',
                              flush=True)
            except Exception as e:
                print(f'[ScaleGoalsSeed] failed: {e}', flush=True)
        # gr-4: the gear-train scene rows (gear shapes + the
        # isolated SimSpace) — upsert path, gears-gated, in gears'
        # own admission pass.
        if (_feature_available('gears')
                and _feature_available('mathshapes') and (
                only_classes is None
                or 'GearDefinition' in only_classes)):
            try:
                from gears.gear_scene import seed_gear_scene
                for r in seed_gear_scene(self.manager):
                    if r.get('inserted') or r.get('updated'):
                        print(f'[GearSceneSeed] {r["class"]}: '
                              f'+{len(r.get("inserted", []))} '
                              f'~{len(r.get("updated", []))}',
                              flush=True)
            except Exception as e:
                print(f'[GearSceneSeed] failed: {e}', flush=True)
        # nav-1: polariapps rows ride the SAME upsert path — the three
        # live use-case rows predate nav_json/personas_json/discipline
        # and the legacy insert-only pass would never deliver the new
        # fields (the ten-strikes gotcha). The legacy entry stays as
        # the no-composition fallback; this pass converges live rows.
        if (_feature_available('composition')
                and _feature_available('polariapps') and (
                only_classes is None
                or 'PolariAppDefinition' in only_classes)):
            try:
                # NOTE: PolariAppDefinition / SEED_POLARI_APPS are the
                # MODULE-LEVEL imports — re-importing them here would
                # make the names function-local and break the legacy
                # seed list above (UnboundLocalError at boot).
                from composition.seed_upsert import upsert_seed_pairs
                for r in upsert_seed_pairs(
                        self.manager,
                        [('PolariAppDefinition', PolariAppDefinition,
                          SEED_POLARI_APPS)], tag='AppsNavSeed'):
                    if r.get('inserted') or r.get('updated'):
                        print(f'[AppsNavSeed] {r["class"]}: '
                              f'+{len(r.get("inserted", []))} '
                              f'~{len(r.get("updated", []))}',
                              flush=True)
            except Exception as e:
                print(f'[AppsNavSeed] failed: {e}', flush=True)
        # tt-8: the single 'oseb' tree became three DOMAIN trees —
        # retire its persisted rows (idempotent no-op once gone) and
        # remap stale PolariModule.tech_node_ref hints.
        # mp-3: skipped when techtree is not downloaded/enabled.
        # mlb-1: runs in techtree's own admission pass (or monolithic).
        if _feature_available('techtree') and (
                only_classes is None or 'TechNode' in only_classes):
            try:
                from techtree.techtree_seed import (
                    backfill_cross_refs, retire_legacy_trees,
                )
                retired = retire_legacy_trees(self.manager)
                if retired:
                    print(f'[TechTree] retired legacy tree rows: '
                          f'{retired}', flush=True)
                filled = backfill_cross_refs(self.manager)
                if filled.get('filled'):
                    print(f'[TechTree] cross-ref backfill: {filled}',
                          flush=True)
            except Exception as e:
                print(f'[TechTree] legacy retirement/backfill failed: '
                      f'{e}', flush=True)
        # res-1: observe THIS device onto its PolariNodeMachine row
        # (ssh_alias=='' convention) so the topology is resource-aware
        # from boot — fills the historical `mem_gb: 0.0` gap.
        # mlb-1: topology is core, so this runs in the core pass.
        if only_classes is not None \
                and 'PolariNodeMachine' not in only_classes:
            return
        try:
            from resources.node_resources import (
                fetch_remote_specs, refresh_local_machine,
            )
            report = refresh_local_machine(self.manager)
            print(f'[NodeResources] local self-observation: {report}',
                  flush=True)
            # Remote nodes with a system_info_url knob are observed at
            # boot too (an observation, not a configuration change) —
            # staging is stateless, so the inventory re-fills itself.
            for row in list((self.manager.objectTables.get(
                    'PolariNodeMachine') or {}).values()):
                if getattr(row, 'system_info_url', ''):
                    remote = fetch_remote_specs(
                        self.manager, getattr(row, 'name', ''))
                    print(f'[NodeResources] remote observation '
                          f'{getattr(row, "name", "")}: '
                          f'ok={remote.get("ok")} '
                          f'{remote.get("error", "")}', flush=True)
        except Exception as e:
            print(f'[NodeResources] boot observation failed: {e}',
                  flush=True)
        # res-2: fill est_row_bytes on seeded data profiles from the
        # storage predictor (declared seeds carry 0 = not yet derived).
        try:
            from resources.profile_analysis import (
                classify_module, estimate_module_row_bytes,
            )
            for row in list((self.manager.objectTables.get(
                    'ModuleResourceProfile') or {}).values()):
                if (getattr(row, 'subject_kind', '') == 'module'
                        and getattr(row, 'character', '') == 'data'
                        and not getattr(row, 'est_row_bytes', 0)):
                    verdict = classify_module(
                        self.manager, getattr(row, 'subject_name', ''))
                    est, est_class = estimate_module_row_bytes(
                        self.manager, verdict['dataClasses'])
                    if est:
                        row.est_row_bytes = est
                        row.provenance_id = (
                            f'{getattr(row, "provenance_id", "")}; '
                            f'est_row_bytes from {est_class}')
                        try:
                            self.manager.db.saveInstanceInDB(row)
                        except Exception:
                            pass
                        print(f'[ResourceProfiles] {row.subject_name}: '
                              f'est_row_bytes={est} ({est_class})',
                              flush=True)
        except Exception as e:
            print(f'[ResourceProfiles] est_row_bytes fill failed: {e}',
                  flush=True)

    def _seedSimulations(self):
        """Seed the simulations module — pendulum-2d demo end-to-end.

        Idempotent-by-name. Order matters: SimulationDefinition →
        SimulationRun → *SimState rows → SimVariable metadata → SimSpace
        + bindings. The two *SimState row streams are keyed by `name`
        (composite "<run>-<role>-<step>") so standard name-keyed
        idempotency works for everything; no special path needed.
        """
        seed_pairs = [
            ('SimulationDefinition', SimulationDefinition, SEED_SIMULATION_DEFINITIONS),
            ('SimulationRun', SimulationRun, SEED_SIMULATION_RUNS),
            ('PendulumBobSimState', PendulumBobSimState, SEED_PENDULUM_BOB_ROWS),
            ('PendulumStringSimState', PendulumStringSimState, SEED_PENDULUM_STRING_ROWS),
            # Newtonian pendulum — seed only the step-0 IC rows; steps 1+ are
            # produced live by the runner via the no-code vector solutions.
            # The *_WIND_* rows are the coupled (wind-forced) run's step-0 ICs.
            ('NewtonianPendulumBobSimState', NewtonianPendulumBobSimState,
             SEED_NEWTON_BOB_ROWS + SEED_NEWTON_WIND_BOB_ROWS),
            ('NewtonianPendulumRodSimState', NewtonianPendulumRodSimState,
             SEED_NEWTON_ROD_ROWS + SEED_NEWTON_WIND_ROD_ROWS),
            # Wind-field space: step-0 grid row + the cross-simulation
            # coupling that feeds the pendulum's wind Partial.
            ('WindFieldGridState', WindFieldGridState, SEED_WIND_GRID_ROWS),
            # Material condensation space: step-0 baseline row (the search's
            # attempt runs write their own step-0 rows at run time).
            ('MaterialCondensationState', MaterialCondensationState,
             SEED_MATERIAL_ROWS),
            ('SimulationCouplingDefinition', SimulationCouplingDefinition,
             SEED_SIMULATION_COUPLINGS),
            # Multi-scale FAMILIES first (msims reference them by
            # profile_ref), then the "Pendulum in Wind" demo + the
            # bob-material IC interface.
            ('MultiScaleSimulationProfile', MultiScaleSimulationProfile,
             SEED_MSIM_PROFILES),
            ('MultiScaleSimulationDefinition', MultiScaleSimulationDefinition,
             SEED_MULTI_SCALE_SIMS + SEED_WAX_DERIVATION_MSIMS
             + SEED_WAX_MULTISCALE_MSIMS),
            ('InitialConditionInterfaceDefinition', InitialConditionInterfaceDefinition,
             SEED_IC_INTERFACES),
            # Demo graphs-over-time for the multi-scale page's graph panels.
            ('GraphDefinition', GraphDefinition, SEED_MSIM_GRAPHS),
            ('SimVariable', SimVariable, SEED_SIM_VARIABLES),
            # Equations: the live-readout set (KE/PE/E_total) PLUS the
            # per-step math each CalculusOperation references. Must seed
            # before the SolutionDefinitions that point at them by name.
            ('EquationDefinition', EquationDefinition,
             SEED_PENDULUM_EQUATIONS + SEED_PENDULUM_STEP_EQUATIONS
             # mag-20: the motor/gear physics held as CONFIGURATION
             # rather than Python — inspectable and editable without
             # a deploy.
             + SEED_EQUATION_ROWS),
            ('SimSpaceDefinition', SimSpaceDefinition, SEED_PENDULUM_SIMSPACES),
            ('SimSpaceBindingDefinition', SimSpaceBindingDefinition, SEED_PENDULUM_BINDINGS),
            ('SimSpaceEvaluationEquation', SimSpaceEvaluationEquation, SEED_PENDULUM_EVALUATION_EQUATIONS),
            # Step solutions: the no-code graphs go in SolutionDefinition
            # (where the editor sees them), then thin metadata wrappers
            # in SimulationExecutionSolution tag each one with its
            # simulation role. Order matters: SimulationExecutionSolution
            # rows reference the SolutionDefinitions by name.
            ('SolutionDefinition', SolutionDefinition, SEED_PENDULUM_STEP_SOLUTION_DEFS),
            ('SimulationExecutionSolution', SimulationExecutionSolution, SEED_PENDULUM_STEP_SOLUTIONS),
            # Manual-Process test cases for the step solutions — let the
            # user verify each step solution's math via the existing
            # /executeSolutionStepped endpoint without standing up a
            # full simulation run.
            ('SolutionTestCase', SolutionTestCase, SEED_PENDULUM_STEP_TEST_CASES),
        ]
        for class_name, cls, seed_list in seed_pairs:
            typingObj = self.manager.objectTypingDict.get(class_name)
            if typingObj is None:
                print(f'[SeedSimulations] {class_name} not in objectTypingDict, skipping', flush=True)
                continue
            existing = self.manager.objectTables.get(class_name, {}) or {}
            existing_names = {getattr(o, 'name', None) for o in existing.values()}
            created = 0
            for seed in seed_list:
                if seed.get('name') in existing_names:
                    continue
                try:
                    cls(**seed, manager=self.manager)
                    created += 1
                except Exception as e:
                    print(f'[SeedSimulations] {class_name} "{seed.get("name")}" failed: {e}', flush=True)
                    import traceback
                    traceback.print_exc()
            if created:
                print(f'[SeedSimulations] Created {created} {class_name} row(s)', flush=True)

        # Config-knob upgrade passes: refresh untouched msim rows'
        # panels (shape-signature guarded) and untouched profile rows'
        # blobs (description-match guarded) from the current seeds.
        try:
            from simulations.multi_scale_seed import upgrade_msim_rows
            upgrade_msim_rows(self.manager)
        except Exception as e:
            print(f'[SeedSimulations] msim upgrade pass failed: {e}', flush=True)
        try:
            from simulations.multi_scale_profile_seed import (
                upgrade_profile_rows,
            )
            upgrade_profile_rows(self.manager)
        except Exception as e:
            print(f'[SeedSimulations] profile upgrade pass failed: {e}',
                  flush=True)
        try:
            from materialsScience.standard_materials_seed import (
                upgrade_material_category_rows,
            )
            upgrade_material_category_rows(self.manager)
        except Exception as e:
            print(f'[SeedSimulations] material category pass failed: '
                  f'{e}', flush=True)

    def _autoRegisterMbtilesSources(self):
        """Scan MinIO buckets for .mbtiles files and create or update
        TileSourceDefinition instances so tile-serving works correctly.

        This ensures that previously generated tile sources survive server
        restarts and that old-format definitions get migrated to the new
        tileserver-based format with proper bucket/objectName fields.
        """
        store = getattr(self.manager, 'objectStore', None)
        if store is None or not store.connected:
            print('[polariServer] Auto-register: objectStore not connected, skipping', flush=True)
            return

        import json as jsonLib

        # Build lookup of existing TileSourceDefinition instances by name
        existing_by_name = {}
        ts_table = self.manager.objectTables.get('TileSourceDefinition', {})
        if isinstance(ts_table, dict):
            for defId, inst in ts_table.items():
                existing_by_name[getattr(inst, 'name', '')] = (defId, inst)
        elif isinstance(ts_table, list):
            for inst in ts_table:
                existing_by_name[getattr(inst, 'name', '')] = (getattr(inst, 'polariId', ''), inst)

        print(f'[polariServer] Auto-register: found {len(existing_by_name)} existing TileSourceDefinition(s): {list(existing_by_name.keys())}', flush=True)

        registered = 0
        updated = 0
        try:
            buckets = store.list_buckets()
            print(f'[polariServer] Auto-register: MinIO buckets: {buckets}', flush=True)
        except Exception as e:
            print(f'[polariServer] Auto-register: failed to list buckets: {e}', flush=True)
            return

        for bucket in buckets:
            try:
                objects = store.list_objects(bucket)
            except Exception:
                continue
            for obj in objects:
                obj_name = obj.get('name', '')
                if not obj_name.endswith('.mbtiles'):
                    continue
                # Derive a readable name from the filename (strip extension)
                source_name = obj_name.rsplit('.', 1)[0]

                # Build the correct definition JSON
                new_definition = jsonLib.dumps({
                    'type': 'vector',
                    'url': f'/tiles/{source_name}/{{z}}/{{x}}/{{y}}.pbf',
                    'bucket': bucket,
                    'objectName': obj_name,
                    'attribution': 'Generated by Polari Tile Generator',
                    'tileFormat': 'vector',
                    'sourceLayer': 'default',
                    'defaultCenter': None,
                    'defaultZoom': None
                })

                if source_name in existing_by_name:
                    # Check if the existing definition needs updating
                    defId, inst = existing_by_name[source_name]
                    old_def_str = getattr(inst, 'definition', '{}')
                    old_type = getattr(inst, 'type', '')
                    try:
                        old_def = jsonLib.loads(old_def_str) if isinstance(old_def_str, str) else old_def_str
                    except (jsonLib.JSONDecodeError, ValueError):
                        old_def = {}

                    needs_update = (
                        old_type != 'tileserver' or
                        'bucket' not in old_def or
                        'objectName' not in old_def or
                        old_def.get('type') != 'vector'
                    )
                    print(f'[polariServer] Auto-register: "{source_name}" exists (type={old_type}), needs_update={needs_update}', flush=True)
                    if needs_update:
                        print(f'[polariServer] Auto-register: updating "{source_name}" old_def={old_def_str}', flush=True)
                        inst.type = 'tileserver'
                        inst.definition = new_definition
                        if self.manager.db is not None:
                            try:
                                self.manager.db.saveInstanceInDB(inst)
                            except Exception as db_err:
                                print(f'[polariServer] Auto-register: DB update failed for {source_name}: {db_err}', flush=True)
                        updated += 1
                    continue

                # Create new TileSourceDefinition
                try:
                    instance = TileSourceDefinition(
                        name=source_name, type='tileserver',
                        definition=new_definition, manager=self.manager
                    )
                    # Persist to DB if available
                    if self.manager.db is not None:
                        try:
                            self.manager.db.saveInstanceInDB(instance)
                        except Exception as db_err:
                            print(f'[polariServer] Auto-register: DB save failed for {source_name}: {db_err}', flush=True)
                    existing_by_name[source_name] = (getattr(instance, 'polariId', ''), instance)
                    registered += 1
                    print(f'[polariServer] Auto-register: created new "{source_name}" in bucket "{bucket}"', flush=True)
                except Exception as e:
                    print(f'[polariServer] Auto-register: failed to create TileSourceDefinition for {source_name}: {e}', flush=True)

        print(f'[polariServer] Auto-register complete: {registered} new, {updated} updated', flush=True)

    def registerCRUDEforObjectType(self, objType, overrideExclusion=False):
        """
        Dynamically register a CRUDE endpoint for an object type.
        This is useful when object types are registered after server initialization.

        Args:
            objType: The class name (string) of the object type to register
            overrideExclusion: polyTypedObject defaults excludeFromCRUDE=True,
                so a typing created via manager.getObjectTyping() gets
                silently skipped here even though the caller explicitly
                asked for an endpoint (the bug behind the long-standing
                dynamic-registration test failures). Pass True to treat
                THIS call as the deliberate opt-in: the flag is flipped
                to False and registration proceeds. Default False keeps
                the knob authoritative for automated callers.

        Returns:
            The polariCRUDE instance that was created, or None if excludeFromCRUDE is True
        """
        if objType not in self.manager.objectTypingDict:
            raise ValueError(f"Object type '{objType}' not found in manager.objectTypingDict. Register the object type first using manager.getObjectTyping().")

        # Get typing object to check configuration flags
        typingObj = self.manager.objectTypingDict[objType]

        # Check if this object type should be excluded from CRUDE API
        # Core framework objects may set this to True to prevent runtime issues
        if hasattr(typingObj, 'excludeFromCRUDE') and typingObj.excludeFromCRUDE:
            if not overrideExclusion:
                print(f"Object type '{objType}' has excludeFromCRUDE=True, skipping CRUDE endpoint registration")
                return None
            print(f"Object type '{objType}': overriding excludeFromCRUDE for explicit registration")
            typingObj.excludeFromCRUDE = False

        # Check if CRUDE endpoint already exists for this type
        for crude in self.crudeObjectsList:
            if crude.apiObject == objType:
                print(f"CRUDE endpoint for '{objType}' already exists at {crude.apiName}")
                return crude

        # Run analysis on the typing object
        typingObj.runAnalysis()

        # Create new CRUDE endpoint
        newCRUDE = polariCRUDE(apiObject=objType, polServer=self, manager=self.manager)
        self.crudeObjectsList.append(newCRUDE)

        print(f"Registered CRUDE endpoint for '{objType}' at {newCRUDE.apiName}")
        return newCRUDE

