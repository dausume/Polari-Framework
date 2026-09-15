"""
@module iso.iso_endpoints

construct_iso_endpoints(polServer) — the endpoint constructor (manifest `endpoints`); admission calls it once.
"""
from iso.iso_api import IsoAPI


def construct_iso_endpoints(polServer):
    return IsoAPI(polServer=polServer, manager=polServer.manager)
