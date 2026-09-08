"""
@module reticulum.objects.arch.ArchipelagoTrust

Row class ArchipelagoTrust of the reticulum module — one class per file (design §7), split
from arch_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class ArchipelagoTrust(treeObject):
    """What a peer may ASK for — graded, never boolean. may_ask_json
    is the named-operations list a grade covers; the ai_actions level
    ceiling derives from the grade and never reaches irreversible."""

    @treeObjectInit
    def __init__(self, name='', grade='observe', may_ask_json='[]',
                 granted_by='', granted_at='', notes='', manager=None):
        self.name = name
        self.grade = grade
        # Named low-authority operations this trust covers, e.g.
        # ["telemetry-ingest", "gossip"]. An empty list with a high
        # grade grants NOTHING — the list is the grant.
        self.may_ask_json = may_ask_json
        self.granted_by = granted_by
        self.granted_at = granted_at
        self.notes = notes
