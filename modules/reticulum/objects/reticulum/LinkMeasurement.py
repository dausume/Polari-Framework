"""
@module reticulum.objects.reticulum.LinkMeasurement

Row class LinkMeasurement of the reticulum module — one class per file (design §7), split
from reticulum_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class LinkMeasurement(treeObject):
    """Measured facts PER PATH (destination + bearer path), §5e — a
    fast local interface says nothing about a peer three hops away
    whose last hop is LoRa. Turns §2's placeholders into facts; the
    fidelity field says HOW the number was obtained (a VM number must
    never decide an encoding/FEC choice, §5h)."""

    @treeObjectInit
    def __init__(self, name='', destination_name='',
                 bearer_path_json='[]', hop_count=0,
                 worst_hop_bearer='', throughput_bps=0, rtt_ms=0,
                 loss_rate=0.0, airtime_ms_consumed=0,
                 measured_at_ms=0, fidelity='declared', notes='',
                 manager=None):
        self.name = name
        self.destination_name = destination_name
        # Ordered bearer list for the path, worst hop named beside it.
        self.bearer_path_json = bearer_path_json
        self.hop_count = hop_count
        self.worst_hop_bearer = worst_hop_bearer
        self.throughput_bps = throughput_bps
        self.rtt_ms = rtt_ms
        self.loss_rate = loss_rate
        self.airtime_ms_consumed = airtime_ms_consumed
        self.measured_at_ms = measured_at_ms
        self.fidelity = fidelity
        self.notes = notes
