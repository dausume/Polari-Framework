"""
@module cmod.cmod_endpoints
construct_cmod_endpoints(polServer) — the endpoint constructor (manifest `endpoints`); admission calls it once.
fs-0: the FirmwareSolution doors (cmod.cmod_firmware_api) are constructed beside the atoms/graphs API, same pattern
as board's installer/board_object APIs.
"""
from cmod.cmod_api import CModAPI
from cmod.cmod_firmware_api import FirmwareAPI
from cmod.cmod_capability_api import CapabilityAPI


def construct_cmod_endpoints(polServer):
    api = CModAPI(polServer=polServer, manager=polServer.manager)
    api.firmware = FirmwareAPI(polServer=polServer, manager=polServer.manager)
    api.capability = CapabilityAPI(polServer=polServer, manager=polServer.manager)
    return api
