"""
@module cicd.cicd_endpoints

construct_cicd_endpoints(polServer) — the endpoint constructor (manifest `endpoints`); admission calls it once.
"""
from cicd.cicd_api import CicdAPI


def construct_cicd_endpoints(polServer):
    return CicdAPI(polServer=polServer, manager=polServer.manager)
