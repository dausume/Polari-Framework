"""
@module pcb.pcb_endpoints
construct_pcb_endpoints(polServer) — the endpoint constructor (manifest `endpoints`); admission calls it once.
"""
from pcb.pcb_api import PcbAPI


def construct_pcb_endpoints(polServer):
    return PcbAPI(polServer=polServer, manager=polServer.manager)
