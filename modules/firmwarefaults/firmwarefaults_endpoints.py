"""
@module firmwarefaults.firmwarefaults_endpoints
construct_firmwarefaults_endpoints(polServer) — the endpoint constructor (manifest `endpoints`); admission calls it once.
"""
from firmwarefaults.firmwarefaults_api import FirmwareFaultsAPI


def construct_firmwarefaults_endpoints(polServer):
    return FirmwareFaultsAPI(polServer=polServer, manager=polServer.manager)
