"""
@module pcb.pcb_endpoints
construct_pcb_endpoints(polServer) — the endpoint constructor (manifest `endpoints`); admission calls it once.
"""
from pcb.pcb_api import PcbAPI
from pcb.pcb_sim_api import PcbSimAPI   # kxc-3: the deck from our rows + the run


def construct_pcb_endpoints(polServer):
    PcbSimAPI(polServer=polServer, manager=polServer.manager)
    return PcbAPI(polServer=polServer, manager=polServer.manager)
