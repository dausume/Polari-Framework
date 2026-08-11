"""
@module polariApiServer.module_endpoints

dyn-1 (DYNAMIC_MODULES_PLAN): per-module custom-API endpoint
construction, extracted verbatim from polariServer.__init__'s
``if _feature_available(...)`` blocks so ONE code path serves
boot and live admission (dyn-2). Each constructor takes the
polariServer instance; constructing a resource registers its
routes (falcon add_route happens in each API's __init__).
Bodies import inside the function on purpose — a constructor
only runs when its module's code is present + enabled.
"""


def construct_pspp_endpoints(polServer):
    manager = polServer.manager
    # PSPP: dataset curves + reaction network + composition
    # grading + cure progress (pspp-V — every chart generated
    # from rows so a book figure proofs against live data).
    from pspp.pspp_api import PsppAPI
    psppEndpoint = PsppAPI(polServer=polServer, manager=manager)


def construct_scoring_endpoints(polServer):
    manager = polServer.manager
    # Context-based scoring: concept list + the scoring pipeline
    # (normalize -> context-match -> weight -> levelize) (scr-1).
    # mp-3: every feature-module endpoint below is gated on the
    # module's code being downloaded + enabled — an absent module
    # registers no routes (the /modules surface says why).
    from scoring.scoring_api import ScoringAPI
    scoringEndpoint = ScoringAPI(polServer=polServer, manager=manager)
    from scoring.authority_api import AuthorityAPI
    authorityEndpoint = AuthorityAPI(polServer=polServer,
                                     manager=manager)
    from scoring.epistemics_api import EpistemicsAPI
    epistemicsEndpoint = EpistemicsAPI(polServer=polServer,
                                       manager=manager)


def construct_zones_endpoints(polServer):
    manager = polServer.manager
    from zones.zones_api import ZonesAPI
    zonesEndpoint = ZonesAPI(polServer=polServer, manager=manager)


def construct_aquaponics_endpoints(polServer):
    manager = polServer.manager
    # Aquaponics: self-watering pot geometry validation + hole
    # generation (aqp-1).
    from aquaponics.pot_api import AquaponicsPotAPI
    aquaponicsPotEndpoint = AquaponicsPotAPI(
        polServer=polServer, manager=manager)
    # Aquaponics: soil / water / nutrient-profile analysis (aqp-2).
    from aquaponics.media_api import AquaponicsMediaAPI
    aquaponicsMediaEndpoint = AquaponicsMediaAPI(
        polServer=polServer, manager=manager)
    # Aquaponics: per-part plant capture + budget (aqp-4).
    from aquaponics.plant_api import AquaponicsPlantAPI
    aquaponicsPlantEndpoint = AquaponicsPlantAPI(
        polServer=polServer, manager=manager)
    # Aquaponics: atmospheric conditions + gas exchange (aqp-5).
    from aquaponics.atmosphere_api import AquaponicsAtmosphereAPI
    aquaponicsAtmosphereEndpoint = AquaponicsAtmosphereAPI(
        polServer=polServer, manager=manager)
    # Aquaponics: bound pot systems — survival + impact (aqp-6).
    from aquaponics.pot_system_api import AquaponicsSystemAPI
    aquaponicsSystemEndpoint = AquaponicsSystemAPI(
        polServer=polServer, manager=manager)
    # Aquaponics: Darcy pot hydraulics — drains-by-gravity +
    # head field, fidelity ladder fem->reservoir (aqp-3).
    from aquaponics.hydraulics_api import AquaponicsHydraulicsAPI
    aquaponicsHydraulicsEndpoint = AquaponicsHydraulicsAPI(
        polServer=polServer, manager=manager)
    # Aquaponics: worm-compost enrichment loop — release /
    # simulate / compare-modes / enriched-water (aqp-7).
    from aquaponics.vermicompost_api import AquaponicsCompostAPI
    aquaponicsCompostEndpoint = AquaponicsCompostAPI(
        polServer=polServer, manager=manager)
    # Aquaponics: SIMPLIFIED/AGGREGATE growth model (was aqp-8;
    # renamed + rebuilt 2026-07-15 to pull its constants + curve
    # from the real detailed model, plant_growth_normalized).
    from aquaponics.plant_growth_simplified_api import (
        AquaponicsPlantGrowthSimplifiedAPI,
    )
    aquaponicsPlantGrowthSimplifiedEndpoint = (
        AquaponicsPlantGrowthSimplifiedAPI(
            polServer=polServer, manager=manager))
    # Plant-growth-sim phase 1: free-soil/constrained-limits +
    # per-part PotPlanting state + animation-bones skeleton
    # (2026-07-15).
    from aquaponics.plant_growth_normalized_api import (
        AquaponicsPlantGrowthNormalizedAPI,
    )
    aquaponicsPlantGrowthNormalizedEndpoint = (
        AquaponicsPlantGrowthNormalizedAPI(
            polServer=polServer, manager=manager))
    # Plant-growth-sim phase 8: direct-light field diagnostics.
    from aquaponics.light_field_api import AquaponicsLightFieldAPI
    aquaponicsLightFieldEndpoint = AquaponicsLightFieldAPI(
        polServer=polServer, manager=manager)
    # Plant-growth-sim phase 10: water batching + nutrient uptake.
    from aquaponics.water_batch_api import AquaponicsWaterBatchAPI
    aquaponicsWaterBatchEndpoint = AquaponicsWaterBatchAPI(
        polServer=polServer, manager=manager)
    # Plant-growth-sim phase 11: decomposed water-level trajectory.
    from aquaponics.water_level_api import AquaponicsWaterLevelAPI
    aquaponicsWaterLevelEndpoint = AquaponicsWaterLevelAPI(
        polServer=polServer, manager=manager)


def construct_waxprint_endpoints(polServer):
    manager = polServer.manager
    # waxprint (wp-1): pellet-fed auger-screw wax printer — list rows +
    # run the two-zone melt with the wax thermal-safety gate.
    from waxprint.waxprint_api import WaxPrintAPI
    waxPrintEndpoint = WaxPrintAPI(polServer=polServer, manager=manager)
    # waxprint sim space (wp-5/wp-6): run one IC / a range + evaluate the
    # condition gates for a run.
    from waxprint.sim_api import WaxPrintSimAPI
    waxPrintSimEndpoint = WaxPrintSimAPI(polServer=polServer,
                                         manager=manager)


def construct_nutrition_endpoints(polServer):
    manager = polServer.manager
    # Nutrition: dietary-nutrient vocab + person BMR/needs +
    # household demand aggregation (nut-1/3/4).
    from nutrition.nutrition_api import NutritionAPI
    nutritionEndpoint = NutritionAPI(
        polServer=polServer, manager=manager)
    # Nutrition: plant harvest -> meal-nutrient yield, closing the
    # self-watering-pot grow loop (nut-2).
    from nutrition.food_api import NutritionFoodAPI
    nutritionFoodEndpoint = NutritionFoodAPI(
        polServer=polServer, manager=manager)


def construct_plant_morphology_endpoints(polServer):
    manager = polServer.manager
    # Plant morphology: 3D organ/root stand-ins + confinement /
    # dwarfing assessment (morph-1).
    from plant_morphology.morphology_api import PlantMorphologyAPI
    plantMorphologyEndpoint = PlantMorphologyAPI(
        polServer=polServer, manager=manager)


def construct_mathshapes_endpoints(polServer):
    manager = polServer.manager
    # Math-defined shapes: quadric/primitive/CSG geometry (shape-1)
    # + parametric modification (shape-2, POST /modify).
    from mathshapes.shape_api import MathShapesAPI
    mathShapesEndpoint = MathShapesAPI(
        polServer=polServer, manager=manager)
    # Aquaponic towers: stacked math-defined pots (shape-2) +
    # growth forecast (shape-4).
    from mathshapes.tower_api import AquaponicTowerAPI
    aquaponicTowerEndpoint = AquaponicTowerAPI(
        polServer=polServer, manager=manager)
    # CAD import/export via cad-engines worker + MinIO (shape-3).
    from mathshapes.cad_api import CadImportAPI
    cadImportEndpoint = CadImportAPI(
        polServer=polServer, manager=manager)


def construct_tanks_endpoints(polServer):
    manager = polServer.manager
    # Tanks: freshwater + saltwater ecosystem nutrient balance +
    # harvest yield (the alternate nutrient source, tank-1).
    from tanks.tank_api import TankSystemAPI
    tankSystemEndpoint = TankSystemAPI(
        polServer=polServer, manager=manager)


def construct_microalgae_endpoints(polServer):
    manager = polServer.manager
    # Microalgae reactors: sustainability (no-collapse) + CO2
    # decarbonization coupled to a parent system (algae-1).
    from microalgae.reactor_api import MicroalgaeReactorAPI
    microalgaeReactorEndpoint = MicroalgaeReactorAPI(
        polServer=polServer, manager=manager)


def construct_biomining_endpoints(polServer):
    manager = polServer.manager
    # Biomining: element extraction + refinement + nutrient recovery
    # specialized aquaponic variants (biomine-1).
    from biomining.biomining_api import BiomineAPI
    biomineEndpoint = BiomineAPI(
        polServer=polServer, manager=manager)


def construct_video_endpoints(polServer):
    manager = polServer.manager
    # Self-hosted video: presigned upload/stream URLs + ffmpeg
    # conversion trigger (video-1).
    from video.video_api import VideoAPI
    videoEndpoint = VideoAPI(
        polServer=polServer, manager=manager)


def construct_bizops_endpoints(polServer):
    manager = polServer.manager
    # Business flows + economy track + order planner (biz-1).
    from bizops.bizops_api import BizOpsAPI
    bizOpsEndpoint = BizOpsAPI(
        polServer=polServer, manager=manager)


def construct_odooconnect_endpoints(polServer):
    manager = polServer.manager
    # Odoo ERP connector status/catalog (od-3).
    from odooconnect.odoo_api import OdooConnectAPI
    odooConnectEndpoint = OdooConnectAPI(
        polServer=polServer, manager=manager)


def construct_waxsupply_endpoints(polServer):
    manager = polServer.manager
    # Wax sources for molds/masks (wax-1).
    from waxsupply.wax_api import WaxSupplyAPI
    waxSupplyEndpoint = WaxSupplyAPI(
        polServer=polServer, manager=manager)


def construct_casting_endpoints(polServer):
    manager = polServer.manager
    # The nesting wizard: part × material → the full derived
    # mold-nesting process, every step viewable (nest-1).
    from casting.casting_api import CastingAPI
    castingEndpoint = CastingAPI(
        polServer=polServer, manager=manager)


def construct_composition_endpoints(polServer):
    manager = polServer.manager
    # Part composition (arch-7): derived levels, variant
    # reports, routings, audited promotions, archetypes.
    from composition.composition_api import CompositionAPI
    compositionEndpoint = CompositionAPI(
        polServer=polServer, manager=manager)


def construct_magnetics_endpoints(polServer):
    manager = polServer.manager
    # Magnetic materials Section A: catalog gates, role
    # search, powder designer (mag-2/2r/2t).
    from magnetics.magnet_api import MagneticsAPI
    magneticsEndpoint = MagneticsAPI(
        polServer=polServer, manager=manager)


def construct_motors_endpoints(polServer):
    manager = polServer.manager
    # Motors Section C: ladder designs, clock control case,
    # torque curves, parity (mag-5).
    from motors.motor_api import MotorsAPI
    motorsEndpoint = MotorsAPI(
        polServer=polServer, manager=manager)


def construct_climate_endpoints(polServer):
    manager = polServer.manager
    # co2-A: Climate Change & Atmosphere — series, spans,
    # trends, thresholds, the coupled crossing table and
    # the citation/export surfaces.
    from climate.climate_api import ClimateAPI
    climateEndpoint = ClimateAPI(
        polServer=polServer, manager=manager)


def construct_meshassets_endpoints(polServer):
    manager = polServer.manager
    # mesh-1: the licence-gated catalog + organ fit.
    from meshassets.mesh_asset_api import MeshAssetsAPI
    meshAssetsEndpoint = MeshAssetsAPI(
        polServer=polServer, manager=manager)


def construct_gears_endpoints(polServer):
    manager = polServer.manager
    # Gear trains: taxonomy + the abstract kinematic solve
    # (gr-1); the motor splice lands at gr-5.
    from gears.gear_api import GearsAPI
    gearsEndpoint = GearsAPI(
        polServer=polServer, manager=manager)


def construct_supplychain_endpoints(polServer):
    manager = polServer.manager
    # The unifying bio supply-chain ledger — materials + food +
    # carbon accounting (chain-1).
    from supplychain.chain_api import SupplyChainAPI
    supplyChainEndpoint = SupplyChainAPI(
        polServer=polServer, manager=manager)
    # Sourcing: cited prices + preference ladder (src-1).
    from supplychain.sourcing_api import SourcingAPI
    sourcingEndpoint = SourcingAPI(
        polServer=polServer, manager=manager)


def construct_testing_endpoints(polServer):
    manager = polServer.manager
    # acct-0: the accountability matrix. Endpoint construction is
    # NOT auto-gated (only defClassList is), so guard explicitly —
    # a normal build must register no /api/accountability route.
    # mp-3: the gate also requires the testing code to be present.
    from testing.accountability_api import AccountabilityAPI
    accountabilityEndpoint = AccountabilityAPI(
        polServer=polServer, manager=manager)
    # acct-3: the twin rehearsal's out-of-process lease
    # handle (production keeps NO HTTP lease surface).
    from testing.twin_lease_api import TwinLeaseAPI
    twinLeaseEndpoint = TwinLeaseAPI(
        polServer=polServer, manager=manager)


def construct_polariapps_endpoints(polServer):
    manager = polServer.manager
    # Polari-Apps (tt-12): use-case module configurations —
    # plan/export/apply (rows only; deploys stay pol commands).
    from polariapps.apps_api import AppsAPI
    appsEndpoint = AppsAPI(polServer=polServer, manager=manager)


def construct_appstore_endpoints(polServer):
    manager = polServer.manager
    # App Store (appstore-1): installable shells over the
    # polariapps content layer — catalog/identity/enroll/
    # redeem/download. Endpoint construction is NOT
    # auto-gated (only defClassList is), hence the guard.
    from appstore.appstore_api import AppStoreAPI
    appStoreEndpoint = AppStoreAPI(
        polServer=polServer, manager=manager)


def construct_islemesh_endpoints(polServer):
    manager = polServer.manager
    # islemesh (mac-1): ingest + read surface for isle-mesh
    # data (registry/fragments/device facts; mock flagged).
    from islemesh.islemesh_api import IsleMeshAPI
    isleMeshEndpoint = IsleMeshAPI(
        polServer=polServer, manager=manager)


def construct_techtree_endpoints(polServer):
    manager = polServer.manager
    # Tech tree (tt-3): trees/nodes/segments + derived completion
    # rollup — the topology expansion toward the OSEB.
    from techtree.techtree_api import TechTreeAPI
    techTreeEndpoint = TechTreeAPI(
        polServer=polServer, manager=manager)


def construct_grpcbridge_endpoints(polServer):
    manager = polServer.manager
    # gRPC contracts (grpc-1): exposure catalogue + the
    # enable/disable/regenerate knob + .proto download. Contracts
    # generate ONLY from stabilized schemas.
    from grpcbridge.contract_api import GrpcContractsAPI
    grpcContractsEndpoint = GrpcContractsAPI(
        polServer=polServer, manager=manager)
    # Polari Hardware Bridge (grpc-j1): bridge-definition rows +
    # generate/download of the buildable Java app (tar.gz).
    from grpcbridge.java_bridge_api import HardwareBridgeAPI
    hardwareBridgeEndpoint = HardwareBridgeAPI(
        polServer=polServer, manager=manager)


def construct_hwfpga_endpoints(polServer):
    manager = polServer.manager
    # FPGA register maps (hwsim-3): catalogue + generated
    # Verilog/C/testbench artifacts, all FROM the knob rows.
    from hwfpga.fpga_api import FpgaRegisterMapAPI
    fpgaRegisterMapEndpoint = FpgaRegisterMapAPI(
        polServer=polServer, manager=manager)


def construct_hwdigital_endpoints(polServer):
    manager = polServer.manager
    # ncg-7 (Dustin: split across small devices): endpoint
    # construction is NOT auto-gated (only defClassList is), so
    # the ncg level surfaces guard explicitly — a node assigned
    # only 'scoring' must carry no /api/hw or circuit routes,
    # and vice versa, exactly like the testing surface.
    # mp-3: the gate also requires the module code to be present.
    # ncg-3: logic diagrams as rows — catalogue, generated
    # artifacts (through the compiler seam), evaluate.
    from hwdigital.logic_api import LogicDesignAPI
    logicDesignEndpoint = LogicDesignAPI(
        polServer=polServer, manager=manager)


def construct_electrodevice_endpoints(polServer):
    manager = polServer.manager
    # ncg-4: circuits as rows — catalogue, netlist, run.
    from electrodevice.circuit_api import (BreadboardAPI,
                                           CircuitRowsAPI)
    circuitRowsEndpoint = CircuitRowsAPI(
        polServer=polServer, manager=manager)
    # ncg-5: jumpered breadboards, run as one netlist.
    breadboardEndpoint = BreadboardAPI(
        polServer=polServer, manager=manager)
    # Material-derived electronic devices (derive from msci sims,
    # SPICE cards, ngspice circuit tests).
    from electrodevice.device_api import ElectroDeviceAPI
    electroDeviceEndpoint = ElectroDeviceAPI(
        polServer=polServer, manager=manager)


# Ordered as the original __init__ constructed them.
MODULE_ENDPOINT_CONSTRUCTORS = {
    'pspp': construct_pspp_endpoints,
    'scoring': construct_scoring_endpoints,
    'zones': construct_zones_endpoints,
    'aquaponics': construct_aquaponics_endpoints,
    'waxprint': construct_waxprint_endpoints,
    'nutrition': construct_nutrition_endpoints,
    'plant_morphology': construct_plant_morphology_endpoints,
    'mathshapes': construct_mathshapes_endpoints,
    'tanks': construct_tanks_endpoints,
    'microalgae': construct_microalgae_endpoints,
    'biomining': construct_biomining_endpoints,
    'video': construct_video_endpoints,
    'bizops': construct_bizops_endpoints,
    'odooconnect': construct_odooconnect_endpoints,
    'waxsupply': construct_waxsupply_endpoints,
    'casting': construct_casting_endpoints,
    'composition': construct_composition_endpoints,
    'magnetics': construct_magnetics_endpoints,
    'motors': construct_motors_endpoints,
    'climate': construct_climate_endpoints,
    'meshassets': construct_meshassets_endpoints,
    'gears': construct_gears_endpoints,
    'supplychain': construct_supplychain_endpoints,
    'testing': construct_testing_endpoints,
    'polariapps': construct_polariapps_endpoints,
    'appstore': construct_appstore_endpoints,
    'islemesh': construct_islemesh_endpoints,
    'techtree': construct_techtree_endpoints,
    'grpcbridge': construct_grpcbridge_endpoints,
    'hwfpga': construct_hwfpga_endpoints,
    'hwdigital': construct_hwdigital_endpoints,
    'electrodevice': construct_electrodevice_endpoints,
}
