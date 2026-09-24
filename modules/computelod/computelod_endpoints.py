"""
@module computelod.computelod_endpoints
construct_computelod_endpoints(polServer) — the endpoint constructor (manifest `endpoints`); admission calls it once.
"""
from computelod.computelod_api import ComputeLodAPI


def construct_computelod_endpoints(polServer):
    return ComputeLodAPI(polServer=polServer, manager=polServer.manager)
