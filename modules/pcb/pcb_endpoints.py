"""
@module pcb.pcb_endpoints
construct_pcb_endpoints(polServer) — the endpoint constructor (manifest `endpoints`); admission calls it once.
"""
from pcb.pcb_api import PcbAPI
from pcb.pcb_sim_api import PcbSimAPI   # kxc-3: the deck from our rows + the run
from pcb.pcb_thermal_api import PcbThermalAPI   # bob-3g: powers a person gives, datasheet thermal models, the board over time
from pcb.pcb_temperature_api import PcbTemperatureAPI   # tmp-1 / tmp-2: the circuit at a temperature


def construct_pcb_endpoints(polServer):
    PcbSimAPI(polServer=polServer, manager=polServer.manager)
    PcbThermalAPI(polServer=polServer, manager=polServer.manager)
    PcbTemperatureAPI(polServer=polServer, manager=polServer.manager)
    return PcbAPI(polServer=polServer, manager=polServer.manager)
