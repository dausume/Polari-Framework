"""
@module reticulum.objects.discovery.PeerSighting

Row class PeerSighting of the reticulum module — one class per file (design §7), split
from discovery_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class PeerSighting(treeObject):
    """One peer as HEARD: evidence with timestamps, adjudicated by a
    named human into .arch, .mesh, or ignored. Row name = the
    destination hash (the stable thing a stranger shows us)."""

    @treeObjectInit
    def __init__(self, name='', identity_hash='', dest_hash='',
                 aspects='', heard_via='', first_heard_ms=0,
                 last_heard_ms=0, announce_count=0,
                 status='unadjudicated', adjudicated_by='',
                 adjudicated_at='', arch_node_name='', notes='',
                 manager=None):
        self.name = name
        self.identity_hash = identity_hash
        self.dest_hash = dest_hash
        self.aspects = aspects
        # comma-joined interface names — WHICH radios heard it.
        self.heard_via = heard_via
        self.first_heard_ms = first_heard_ms
        self.last_heard_ms = last_heard_ms
        self.announce_count = announce_count
        self.status = status
        self.adjudicated_by = adjudicated_by
        self.adjudicated_at = adjudicated_at
        # the ArchipelagoNode created on admission, when any.
        self.arch_node_name = arch_node_name
        self.notes = notes
