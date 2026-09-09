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
    from pspp.pspp_api import PsppAPI
    psppEndpoint = PsppAPI(polServer=polServer, manager=manager)


def construct_scoring_endpoints(polServer):
    manager = polServer.manager
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
    from waxprint.waxprint_api import WaxPrintAPI
    waxPrintEndpoint = WaxPrintAPI(polServer=polServer, manager=manager)
    # waxprint sim space (wp-5/wp-6): run one IC / a range + evaluate the
    # condition gates for a run.
    from waxprint.sim_api import WaxPrintSimAPI
    waxPrintSimEndpoint = WaxPrintSimAPI(polServer=polServer,
                                         manager=manager)


def construct_nutrition_endpoints(polServer):
    manager = polServer.manager
    from nutrition.nutrition_api import NutritionAPI
    nutritionEndpoint = NutritionAPI(
        polServer=polServer, manager=manager)
    # Nutrition: plant harvest -> meal-nutrient yield, closing the
    # self-watering-pot grow loop (nut-2).
    from nutrition.food_api import NutritionFoodAPI
    nutritionFoodEndpoint = NutritionFoodAPI(
        polServer=polServer, manager=manager)
    # mpa-5: the meal-planning app's derived-view surface
    # (me / dashboard / series / plan cost / pantry /
    # prices / acidity / the PSPP state chain).
    from nutrition.mealplanning_api import MealPlanningAPI
    mealPlanningEndpoint = MealPlanningAPI(
        polServer=polServer, manager=manager)
    # Night run 2026-09-03: the four view pages' own resources
    # (Today / Shopping trip / Cook now / Weekly review). Each
    # guards its routes; a missing one must not take the rest.
    for _mod, _cls in (('nutrition.today_api', 'TodayAPI'),
                       ('nutrition.shoptrip_api', 'ShoptripAPI'),
                       ('nutrition.cooknow_api', 'CookNowAPI'),
                       ('nutrition.weekreview_api', 'WeekReviewAPI')):
        try:
            _api_cls = getattr(__import__(_mod, fromlist=[_cls]), _cls)
            _api_cls(polServer=polServer, manager=manager)
        except Exception as _e:  # noqa: BLE001
            print(f'[MealplanPages] {_cls} not registered: {_e}',
                  flush=True)


def construct_plant_morphology_endpoints(polServer):
    manager = polServer.manager
    from plant_morphology.morphology_api import PlantMorphologyAPI
    plantMorphologyEndpoint = PlantMorphologyAPI(
        polServer=polServer, manager=manager)


def construct_mathshapes_endpoints(polServer):
    manager = polServer.manager
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
    from tanks.tank_api import TankSystemAPI
    tankSystemEndpoint = TankSystemAPI(
        polServer=polServer, manager=manager)


def construct_microalgae_endpoints(polServer):
    manager = polServer.manager
    from microalgae.reactor_api import MicroalgaeReactorAPI
    microalgaeReactorEndpoint = MicroalgaeReactorAPI(
        polServer=polServer, manager=manager)


def construct_biomining_endpoints(polServer):
    manager = polServer.manager
    from biomining.biomining_api import BiomineAPI
    biomineEndpoint = BiomineAPI(
        polServer=polServer, manager=manager)


def construct_video_endpoints(polServer):
    manager = polServer.manager
    from video.video_api import VideoAPI
    videoEndpoint = VideoAPI(
        polServer=polServer, manager=manager)


def construct_bizops_endpoints(polServer):
    manager = polServer.manager
    from bizops.bizops_api import BizOpsAPI
    bizOpsEndpoint = BizOpsAPI(
        polServer=polServer, manager=manager)


def construct_odooconnect_endpoints(polServer):
    manager = polServer.manager
    from odooconnect.odoo_api import OdooConnectAPI
    odooConnectEndpoint = OdooConnectAPI(
        polServer=polServer, manager=manager)


def construct_waxsupply_endpoints(polServer):
    manager = polServer.manager
    from waxsupply.wax_api import WaxSupplyAPI
    waxSupplyEndpoint = WaxSupplyAPI(
        polServer=polServer, manager=manager)


def construct_casting_endpoints(polServer):
    manager = polServer.manager
    from casting.casting_api import CastingAPI
    castingEndpoint = CastingAPI(
        polServer=polServer, manager=manager)


def construct_composition_endpoints(polServer):
    manager = polServer.manager
    from composition.composition_api import CompositionAPI
    compositionEndpoint = CompositionAPI(
        polServer=polServer, manager=manager)


def construct_magnetics_endpoints(polServer):
    manager = polServer.manager
    from magnetics.magnet_api import MagneticsAPI
    magneticsEndpoint = MagneticsAPI(
        polServer=polServer, manager=manager)


def construct_motors_endpoints(polServer):
    manager = polServer.manager
    from motors.motor_api import MotorsAPI
    motorsEndpoint = MotorsAPI(
        polServer=polServer, manager=manager)


def construct_climate_endpoints(polServer):
    manager = polServer.manager
    from climate.climate_api import ClimateAPI
    climateEndpoint = ClimateAPI(
        polServer=polServer, manager=manager)


def construct_meshassets_endpoints(polServer):
    manager = polServer.manager
    from meshassets.mesh_asset_api import MeshAssetsAPI
    meshAssetsEndpoint = MeshAssetsAPI(
        polServer=polServer, manager=manager)


def construct_gears_endpoints(polServer):
    manager = polServer.manager
    from gears.gear_api import GearsAPI
    gearsEndpoint = GearsAPI(
        polServer=polServer, manager=manager)


def construct_supplychain_endpoints(polServer):
    manager = polServer.manager
    from supplychain.chain_api import SupplyChainAPI
    supplyChainEndpoint = SupplyChainAPI(
        polServer=polServer, manager=manager)
    # Sourcing: cited prices + preference ladder (src-1).
    from supplychain.sourcing_api import SourcingAPI
    sourcingEndpoint = SourcingAPI(
        polServer=polServer, manager=manager)


def construct_testing_endpoints(polServer):
    manager = polServer.manager
    from testing.accountability_api import AccountabilityAPI
    accountabilityEndpoint = AccountabilityAPI(
        polServer=polServer, manager=manager)
    # acct-3: the twin rehearsal's out-of-process lease
    # handle (production keeps NO HTTP lease surface).
    # tcov-1: test coverage by app (hierarchy, budget, benchmarks, plan)
    from testing.coverage_api import CoverageAPI
    coverageEndpoint = CoverageAPI(polServer=polServer, manager=manager)
    from testing.twin_lease_api import TwinLeaseAPI
    twinLeaseEndpoint = TwinLeaseAPI(
        polServer=polServer, manager=manager)


def construct_polariapps_endpoints(polServer):
    manager = polServer.manager
    from polariapps.apps_api import AppsAPI
    appsEndpoint = AppsAPI(polServer=polServer, manager=manager)


def construct_appstore_endpoints(polServer):
    manager = polServer.manager
    from appstore.appstore_api import AppStoreAPI
    appStoreEndpoint = AppStoreAPI(
        polServer=polServer, manager=manager)
    # dl-1: the PUBLIC no-terminal downloads page (server-
    # rendered HTML + deb serving; POLARI_DOWNLOADS_DIR).
    from appstore.downloads_page import DownloadsPage
    downloadsEndpoint = DownloadsPage(
        polServer=polServer, manager=manager)
    # dl-4: /downloads/apps — registry modules as debs,
    # generated on request (POLARI_APP_DEBS_DIR + TTL).
    from appstore.app_debs_page import AppDebsPage
    appDebsEndpoint = AppDebsPage(
        polServer=polServer, manager=manager)
    # dl-5: /downloads/offline — staged chunk sets or the
    # honest not-built-yet page (POLARI_OFFLINE_DIR).
    from appstore.offline_page import OfflinePage
    offlineEndpoint = OfflinePage(
        polServer=polServer, manager=manager)
    # dl-6: /downloads/plan — the topology/bundle wizard
    # (speculates roles + per-device downloads; read-only).
    from appstore.planner_page import PlannerPage
    plannerEndpoint = PlannerPage(
        polServer=polServer, manager=manager)


def construct_computerparts_endpoints(polServer):
    manager = polServer.manager
    from computerparts.parts_api import ComputerPartsAPI
    computerPartsEndpoint = ComputerPartsAPI(
        polServer=polServer, manager=manager)


def construct_islemesh_endpoints(polServer):
    manager = polServer.manager
    from islemesh.islemesh_api import IsleMeshAPI
    isleMeshEndpoint = IsleMeshAPI(
        polServer=polServer, manager=manager)


def construct_techtree_endpoints(polServer):
    manager = polServer.manager
    from techtree.techtree_api import TechTreeAPI
    techTreeEndpoint = TechTreeAPI(
        polServer=polServer, manager=manager)


def construct_grpcbridge_endpoints(polServer):
    manager = polServer.manager
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
    from hwfpga.fpga_api import FpgaRegisterMapAPI
    fpgaRegisterMapEndpoint = FpgaRegisterMapAPI(
        polServer=polServer, manager=manager)


def construct_hwdigital_endpoints(polServer):
    manager = polServer.manager
    from hwdigital.logic_api import LogicDesignAPI
    logicDesignEndpoint = LogicDesignAPI(
        polServer=polServer, manager=manager)


def construct_electrodevice_endpoints(polServer):
    manager = polServer.manager
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


def construct_collab_endpoints(polServer):
    manager = polServer.manager
    # mtg-2: KC-verified token minting for LiveKit + capability/
    # join-info with the *_remote refusal ladder.
    from collab.collab_api import CollabAPI
    collabEndpoint = CollabAPI(polServer=polServer, manager=manager)


def construct_reticulum_endpoints(polServer):
    manager = polServer.manager
    # ret-1: capability (with the licence pins surfaced), .arch
    # reachability, and the ret-8 inbound→proposal seam.
    from reticulum.reticulum_api import ReticulumAPI
    reticulumEndpoint = ReticulumAPI(polServer=polServer,
                                     manager=manager)


def construct_cntfet_endpoints(polServer):
    manager = polServer.manager
    from cntfet.cnt_api import CNTFETAPI
    cntfetEndpoint = CNTFETAPI(
        polServer=polServer, manager=manager)


def construct_microchip_endpoints(polServer):
    manager = polServer.manager
    from microchip.chip_api import MicrochipAPI
    microchipEndpoint = MicrochipAPI(
        polServer=polServer, manager=manager)


def construct_foodstate_endpoints(polServer):
    manager = polServer.manager
    from foodstate.food_api import FoodStateAPI
    foodstateEndpoint = FoodStateAPI(
        polServer=polServer, manager=manager)


def construct_computers_endpoints(polServer):
    manager = polServer.manager
    from computers.computers_api import ComputersAPI
    computersEndpoint = ComputersAPI(
        polServer=polServer, manager=manager)


def construct_mqttbridge_endpoints(polServer):
    manager = polServer.manager
    from mqttbridge.mqtt_api import MqttBridgeAPI
    mqttBridgeEndpoint = MqttBridgeAPI(
        polServer=polServer, manager=manager)


def construct_vpn_endpoints(polServer):
    manager = polServer.manager
    # vpn requires islemesh (the acceptor family): the registry's
    # requires-closure carries islemesh into POLARI_MODULES and refuses
    # a drop while vpn is downloaded, so no second gate here.
    from vpn.vpn_api import VpnAPI
    vpnEndpoint = VpnAPI(polServer=polServer, manager=manager)


def construct_hardwareapps_endpoints(polServer):
    manager = polServer.manager
    from hardwareapps.hardwareapps_api import HardwareAppsAPI
    hardwareAppsEndpoint = HardwareAppsAPI(polServer=polServer, manager=manager)


def construct_isle_relay_endpoints(polServer):
    manager = polServer.manager
    from isle_relay.isle_relay_api import IsleRelayAPI
    isleRelayEndpoint = IsleRelayAPI(polServer=polServer, manager=manager)


def construct_isle_guestnet_endpoints(polServer):
    manager = polServer.manager
    from isle_guestnet.isle_guestnet_api import IsleGuestnetAPI
    isleGuestnetEndpoint = IsleGuestnetAPI(polServer=polServer, manager=manager)


def construct_hwmap_endpoints(polServer):
    manager = polServer.manager
    from hwmap.hwmap_api import HwmapAPI
    hwmapEndpoint = HwmapAPI(polServer=polServer, manager=manager)


def construct_voron_endpoints(polServer):
    manager = polServer.manager
    from voron.voron_api import VoronAPI
    voronEndpoint = VoronAPI(polServer=polServer, manager=manager)


def construct_suiteapps_endpoints(polServer):
    manager = polServer.manager
    from suiteapps.suiteapps_api import SuiteAppsAPI
    suiteAppsEndpoint = SuiteAppsAPI(polServer=polServer, manager=manager)


MODULE_ENDPOINT_CONSTRUCTORS = {
    'suiteapps': construct_suiteapps_endpoints,
    'hwmap': construct_hwmap_endpoints,
    'voron': construct_voron_endpoints,
    'hardwareapps': construct_hardwareapps_endpoints,
    'isle_relay': construct_isle_relay_endpoints,
    'isle_guestnet': construct_isle_guestnet_endpoints,
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
    'computerparts': construct_computerparts_endpoints,
    'islemesh': construct_islemesh_endpoints,
    'techtree': construct_techtree_endpoints,
    'grpcbridge': construct_grpcbridge_endpoints,
    'hwfpga': construct_hwfpga_endpoints,
    'hwdigital': construct_hwdigital_endpoints,
    'electrodevice': construct_electrodevice_endpoints,
    'collab': construct_collab_endpoints,
    'reticulum': construct_reticulum_endpoints,
    'cntfet': construct_cntfet_endpoints,
    'microchip': construct_microchip_endpoints,
    'foodstate': construct_foodstate_endpoints,
    'computers': construct_computers_endpoints,
    'mqttbridge': construct_mqttbridge_endpoints,
    'vpn': construct_vpn_endpoints,
}
