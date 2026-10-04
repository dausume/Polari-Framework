"""
@module cmod.cmod_endpoints
construct_cmod_endpoints(polServer) — the endpoint constructor (manifest `endpoints`); admission calls it once.
"""
from cmod.cmod_api import CModAPI


def construct_cmod_endpoints(polServer):
    return CModAPI(polServer=polServer, manager=polServer.manager)
