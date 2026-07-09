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
# Context-based scoring: the Political Scorecard's term/context/weight
# system generalized over arbitrary Polari data (scr-1).
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
# scr-15: media outlets held accountable for accuracy to the data.
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
# Aquaponics module (aqp-1): self-watering pot geometry as first-class
# objects + waterproof pot materials (ceramic/geopolymer).
from aquaponics.pot_basis import PotDefinition, PotHole
from aquaponics.pot_seed import SEED_POTS, SEED_POT_HOLES
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
from topology.topology_seed import (
    SEED_INSTANCE_DEFINITIONS, SEED_MODULE_ASSIGNMENTS,
    SEED_MODULE_DEPENDENCY_EDGES, SEED_NODE_MACHINES,
    SEED_ORCHESTRATION_TARGETS, SEED_SERVICE_CONNECTIONS,
    SEED_TOPOLOGY_DEFINITIONS,
)
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
        self.falconServer = falcon.App(
            middleware=[
                falcon.CORSMiddleware(allow_origins=allow_origins, allow_credentials=allow_creds),
                CORSExtraHeadersMiddleware(),
                # Populates req.context.user_info / req.context.roles from
                # the incoming Bearer token. Lenient in Phase 1 — never
                # rejects, just plumbs identity for downstream gating.
                AuthContextMiddleware()
            ]
        )
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

        # Context-based scoring: concept list + the scoring pipeline
        # (normalize -> context-match -> weight -> levelize) (scr-1).
        from scoring.scoring_api import ScoringAPI
        scoringEndpoint = ScoringAPI(polServer=self, manager=self.manager)

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

        # Topology orchestration: graph/validate/assign/drift/observe
        # + portable package export/import (top-1).
        from topology.topology_api import TopologyAPI
        topologyEndpoint = TopologyAPI(
            polServer=self, manager=self.manager)
        # Provider routing (top-7): module delegation resolves its
        # provider from the topology rows when no explicit URL knob
        # is set (see materialsScience.engines.remote's ladder).
        from topology.provider_registry import set_manager
        set_manager(self.manager)

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
        self.defClassList = [DisplayDefinition, TableDefinition, GraphDefinition, GeoJsonDefinition, DataSetDefinition, FieldProfileDefinition, FilterChainDefinition, EquationDefinition, MatrixDefinition, MatrixEquationDefinition, TileSourceDefinition, GeocoderDefinition, SolutionDefinition, SolutionVersion, SolutionTestCase, ExecutionStepAssertion, SolutionProcessLink, MapPointDefinition, MapLineSegmentDefinition, MapPolygonDefinition, Role, SimSpaceDefinition, SimSpaceBindingDefinition, Shape2DDefinition, Style2DDefinition, Mesh3DDefinition, Material3DDefinition, Texture3DDefinition, MaterialPhaseAppearance, ChemicalElementDefinition, MaterialsScienceMaterial, MaterialScaleDefinition, ThermalProcessingProfile,
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
            FactualClaim, AccuracyPolicy, BiasPolicy,
            CostCategory, SurvivalCostProfile,
            PotDefinition, PotHole,
            NutrientSpecies, NutrientProfile, SoilDefinition,
            WaterDefinition, PlantDefinition, PlantPart,
            AtmosphereDefinition, PotSystemDefinition,
            # Topology orchestration (top-1).
            PolariNodeMachine, OrchestrationTarget,
            InstanceDefinition, ModuleAssignment,
            ModuleDependencyEdge, ServiceConnection,
            TopologyDefinition, TopologyObservation,
            PeerNode, PolariModule, PeerAgreement, ModuleSourceConfig,
            PolariModuleDependency,
            PendulumBobSimState, PendulumStringSimState,
            NewtonianPendulumBobSimState, NewtonianPendulumRodSimState,
            WindFieldGridState, MaterialCondensationState]
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

    def ensureDefinitionTables(self):
        """Create DB tables for Definition classes and restore saved instances.

        Called from managerObject.__init__ AFTER jumpstartDatabase() completes,
        because self.manager.db is None when polariServer.__init__ runs.
        This method:
        1. Creates missing tables for each Definition class
        2. Migrates old tables that lack an 'id' column
        3. Restores previously-saved Definition instances from the DB
        """
        db = self.manager.db
        if db is None:
            print('[DefInit] ensureDefinitionTables: no database, skipping', flush=True)
            return
        print(f'[DefInit] ensureDefinitionTables: db.tables={db.tables}', flush=True)
        for defClass in self.defClassList:
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
        self._restoreDefinitionInstances(self.defClassList)
        # Register each seeded solution's `boundClass` as a real Polari class
        # so it appears in the Class Manager / Class Selector and can be
        # referenced by Equation bindings. Must run before
        # `_seedSolutionDefinitions` so the class exists when the solution
        # row is created.
        self._seedBoundClasses()
        # Seed SolutionDefinition with sample data if the table is empty
        self._seedSolutionDefinitions()
        # Seed EquationDefinition with smoke-test equations if missing
        self._seedEquationDefinitions()
        # Seed MatrixDefinition with concept-test + element-kind demos
        self._seedMatrixDefinitions()
        # Seed MatrixEquationDefinition with one example per math kind
        self._seedMatrixEquations()
        # Seed SimSpace2D stock library + a demo space
        self._seedSimSpace2D()
        # Seed SimSpace3D stock library + a demo space (Phase 2)
        self._seedSimSpace3D()
        # Seed simulations module — Pendulum2D demo + its SimSpace + binding
        self._seedSimulations()
        # Modules-as-projects boot hook: materialize ONLY rows whose
        # auto_fetch knob is on; everything else surfaces as suggestions.
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

    def _seedSimSpace3D(self):
        """Seed SimSpace 3D library (meshes + materials) + a demo 3D space.
        Same idempotent-by-name pattern as _seedSimSpace2D, plus a small
        upgrade pass that refreshes legacy demo-3d definitions to the
        expanded showcase layout (safe: only updates when the row exactly
        matches the prior seed signature)."""
        seed_pairs = [
            ('Mesh3DDefinition', Mesh3DDefinition, SEED_MESHES_3D),
            # Textures BEFORE materials — materials reference them.
            ('Texture3DDefinition', Texture3DDefinition, SEED_TEXTURES_3D),
            ('Material3DDefinition', Material3DDefinition, SEED_MATERIALS_3D),
            ('MaterialPhaseAppearance', MaterialPhaseAppearance,
             SEED_MATERIAL_PHASE_APPEARANCES),
            ('SimSpaceDefinition', SimSpaceDefinition, SEED_SIM_SPACES_3D),
            # Materials Science: the periodic table as objects + its
            # selection-space demo page.
            ('ChemicalElementDefinition', ChemicalElementDefinition,
             SEED_CHEMICAL_ELEMENTS),
            ('DisplayDefinition', DisplayDefinition,
             SEED_PERIODIC_DISPLAYS + SEED_MSCI_PAGE_DISPLAYS),
            # Materials basis — identities before their scale rows.
            ('MaterialsScienceMaterial', MaterialsScienceMaterial,
             SEED_MS_MATERIALS + SEED_STANDARD_MATERIALS
             + SEED_POT_MATERIALS),
            ('MaterialScaleDefinition', MaterialScaleDefinition,
             SEED_MS_SCALE_DEFINITIONS
             + SEED_STANDARD_SCALE_DEFINITIONS
             + SEED_POT_SCALE_DEFINITIONS),
            # Modules-as-projects: the in-tree module, config-tracked.
            ('ModuleSourceConfig', ModuleSourceConfig,
             SEED_MODULE_SOURCE_CONFIGS),
            # Thermal windows from the Base Wax Properties notes.
            ('ThermalProcessingProfile', ThermalProcessingProfile,
             SEED_THERMAL_PROFILES),
            # Property meanings the material detail view explains with.
            ('MaterialPropertyMeaning', MaterialPropertyMeaning,
             SEED_PROPERTY_MEANINGS + SEED_POT_PROPERTY_MEANINGS),
            # Context-based scoring: terms/contexts/subjects before the
            # values and concepts that reference them.
            ('ScoreTerm', ScoreTerm,
             SEED_SCORE_TERMS + SEED_COST_TERMS
             + SEED_AQP_SCORE_TERMS),
            ('ScoreContext', ScoreContext, SEED_SCORE_CONTEXTS),
            ('ScoreSubject', ScoreSubject,
             SEED_SCORE_SUBJECTS + SEED_POLICY_SUBJECTS
             + SEED_POLITICIAN_SUBJECTS + SEED_MEDIA_OUTLETS
             + SEED_AQP_SCORE_SUBJECTS),
            ('ContextualizedValue', ContextualizedValue,
             SEED_CONTEXTUALIZED_VALUES
             + SEED_AQP_CONTEXTUALIZED_VALUES),
            ('ScoreConcept', ScoreConcept,
             SEED_SCORE_CONCEPTS + SEED_AQP_SCORE_CONCEPTS),
            # Groups + the editable agreement-classification bands
            # (concepts first — groups reference member concepts).
            ('ScoreGroup', ScoreGroup,
             SEED_SCORE_GROUPS + SEED_COHORT_GROUPS
             + SEED_ASSEMBLY_GROUPS),
            ('AgreementPolicy', AgreementPolicy,
             SEED_AGREEMENT_POLICIES),
            # scr-5: contributors before the evidence/assertions that
            # cite them; evidence before assertions.
            ('Contributor', Contributor, SEED_CONTRIBUTORS),
            ('EvidencePolicy', EvidencePolicy,
             SEED_EVIDENCE_POLICIES),
            ('MediaEvidence', MediaEvidence, SEED_MEDIA_EVIDENCE),
            ('ScoreAssertion', ScoreAssertion,
             SEED_SCORE_ASSERTIONS),
            ('AssertionValidityVote', AssertionValidityVote,
             SEED_VALIDITY_VOTES),
            # scr-6: votes after the politician/policy subjects they
            # reference.
            ('PolicyVote', PolicyVote, SEED_POLICY_VOTES),
            # scr-8: elections after the groups/worldviews they run
            # over; ballots after their election.
            ('WorldviewElection', WorldviewElection,
             SEED_WORLDVIEW_ELECTIONS),
            ('WorldviewBallot', WorldviewBallot,
             SEED_WORLDVIEW_BALLOTS),
            # scr-15: claims after the outlets/terms they reference.
            ('AccuracyPolicy', AccuracyPolicy,
             SEED_ACCURACY_POLICIES),
            ('FactualClaim', FactualClaim, SEED_FACTUAL_CLAIMS),
            # scr-16: bias bands as editable rows.
            ('BiasPolicy', BiasPolicy, SEED_BIAS_POLICIES),
            # scr-12a: the walkthrough vocabulary + demo households.
            ('CostCategory', CostCategory, SEED_COST_CATEGORIES),
            ('SurvivalCostProfile', SurvivalCostProfile,
             SEED_SURVIVAL_PROFILES),
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
            # aqp-6: bound pot systems (the scoring rows above bind to
            # these via objectRef into impact_result_json).
            ('PotSystemDefinition', PotSystemDefinition,
             SEED_POT_SYSTEMS),
            # The MVW wax derivation as a configurable search object.
            ('FormulationSearchDefinition', FormulationSearchDefinition,
             SEED_FORMULATION_SEARCHES),
            # Engine-model layer: the catalog before the models that
            # reference it.
            ('EngineModelTemplate', EngineModelTemplate,
             SEED_ENGINE_MODEL_TEMPLATES),
            ('FEMModelDefinition', FEMModelDefinition,
             SEED_FEM_MODELS + SEED_STANDARD_FEM_MODELS),
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
        ]
        # Old demo-3d description (used as the "untouched" signature). If
        # the existing demo-3d row still has this verbatim, we treat it
        # as un-customized and overwrite to the new showcase layout.
        LEGACY_DEMO_3D_DESCRIPTION = (
            'Demo SimSpace3D — five primitives arranged in a row. '
            'Proves the 3D renderer wires up behind the same '
            'SimSpaceRenderer interface as 2D.'
        )
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
             SEED_PENDULUM_EQUATIONS + SEED_PENDULUM_STEP_EQUATIONS),
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

    def registerCRUDEforObjectType(self, objType):
        """
        Dynamically register a CRUDE endpoint for an object type.
        This is useful when object types are registered after server initialization.

        Args:
            objType: The class name (string) of the object type to register

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
            print(f"Object type '{objType}' has excludeFromCRUDE=True, skipping CRUDE endpoint registration")
            return None

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

