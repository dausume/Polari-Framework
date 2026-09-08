"""
@module reticulum.objects.replication.ObjectStateVersion

Row class ObjectStateVersion of the reticulum module — one class per file (design §7), split
from replication_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class ObjectStateVersion(treeObject):
    """One side of the two-state model. parent rows are stored
    VERBATIM as received (evidence of what the other side believes)
    and never edited locally; child rows are ours."""

    @treeObjectInit
    def __init__(self, name='', watched_name='', role='child',
                 version=0, content_hash='', payload_json='',
                 received_at_ms=0, source_arch_name='', notes='',
                 manager=None):
        self.name = name
        self.watched_name = watched_name
        self.role = role
        # Monotonic per (watched, role).
        self.version = version
        self.content_hash = content_hash
        self.payload_json = payload_json
        self.received_at_ms = received_at_ms
        # Which .arch node this parent state arrived from.
        self.source_arch_name = source_arch_name
        self.notes = notes
