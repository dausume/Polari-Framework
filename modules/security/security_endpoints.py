"""
@module security.security_endpoints

construct_security_endpoints(polServer) — the endpoint constructor (manifest `endpoints`); admission calls it once.
"""
from security.security_api import SecurityAPI


def construct_security_endpoints(polServer):
    return SecurityAPI(polServer=polServer, manager=polServer.manager)
