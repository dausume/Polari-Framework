"""
@module instruments.instruments_endpoints

construct_instruments_endpoints(polServer) — the endpoint constructor (manifest `endpoints`); admission calls it once.
"""
from instruments.instruments_api import InstrumentsAPI


def construct_instruments_endpoints(polServer):
    return InstrumentsAPI(polServer=polServer, manager=polServer.manager)
