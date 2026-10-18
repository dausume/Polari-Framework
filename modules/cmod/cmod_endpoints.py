"""
@module cmod.cmod_endpoints
construct_cmod_endpoints(polServer) — the endpoint constructor (manifest `endpoints`); admission calls it once.
fs-0: the FirmwareSolution doors (cmod.cmod_firmware_api) are constructed beside the atoms/graphs API, same pattern
as board's installer/board_object APIs.
"""
from cmod.cmod_api import CModAPI
from cmod.cmod_firmware_api import FirmwareAPI
from cmod.cmod_capability_api import CapabilityAPI
from cmod.cmod_pin_profile_api import PinProfileAPI   # pp-0
from cmod.cmod_mission_api import MissionAPI
from cmod.cmod_isotope_api import IsotopeVariantAPI
from cmod.cmod_approach_profile_api import ApproachProfileAPI   # rt-0
from cmod.cmod_solve_api import SolveAPI   # sol-0
from cmod.cmod_colocation_api import ColocationAPI   # pp-1
from cmod.cmod_task_plan_api import TaskPlanAPI   # fgm-3
from cmod.cmod_template_api import TemplateAPI   # ed-0
from cmod.cmod_fsc_api import FscAPI   # fsc-2


def construct_cmod_endpoints(polServer):
    api = CModAPI(polServer=polServer, manager=polServer.manager)
    api.firmware = FirmwareAPI(polServer=polServer, manager=polServer.manager)
    api.capability = CapabilityAPI(polServer=polServer, manager=polServer.manager)
    api.pin_profiles = PinProfileAPI(polServer=polServer, manager=polServer.manager)   # pp-0
    api.mission = MissionAPI(polServer=polServer, manager=polServer.manager)   # mis-0
    api.atom_variants = IsotopeVariantAPI(polServer=polServer, manager=polServer.manager)   # iso-0
    api.approach_profile = ApproachProfileAPI(polServer=polServer, manager=polServer.manager)   # rt-0
    api.solve = SolveAPI(polServer=polServer, manager=polServer.manager)   # sol-0
    api.colocation = ColocationAPI(polServer=polServer, manager=polServer.manager)   # pp-1: /api/missions/{name}/colocation
    api.task_plan = TaskPlanAPI(polServer=polServer, manager=polServer.manager)   # fgm-3: /api/missions/{name}/task-plan, /api/task-plans/{plan}/also-runs-on
    api.templates = TemplateAPI(polServer=polServer, manager=polServer.manager)   # ed-0: /api/cmod/templates[/{tid:path}]
    api.fsc = FscAPI(polServer=polServer, manager=polServer.manager)   # fsc-2: /api/firmware-scores[/top|/breakdown|/values], /api/firmware-score-profiles
    return api
