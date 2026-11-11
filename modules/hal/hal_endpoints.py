"""
@module hal.hal_endpoints

construct_hal_endpoints(polServer) — the endpoint constructor (manifest `endpoints`); admission calls it once.
"""
from hal.hal_api import HalAPI


def construct_hal_endpoints(polServer):
    return HalAPI(polServer=polServer, manager=polServer.manager)
