"""
@module reticulum.objects.replication.StateConflict

Row class StateConflict of the reticulum module — one class per file (design §7), split
from replication_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class StateConflict(treeObject):
    """A detected divergence, both sides carried. status 'proposed'
    means it went through the ai_actions seam and awaits a human."""

    @treeObjectInit
    def __init__(self, name='', watched_name='', held_parent_version=0,
                 child_version=0, arriving_version=0,
                 arriving_parent_version=0, both_sides_json='{}',
                 detected_at_ms=0, status='open', resolution='',
                 proposal_ref='', notes='', manager=None):
        self.name = name
        self.watched_name = watched_name
        self.held_parent_version = held_parent_version
        self.child_version = child_version
        self.arriving_version = arriving_version
        self.arriving_parent_version = arriving_parent_version
        self.both_sides_json = both_sides_json
        self.detected_at_ms = detected_at_ms
        self.status = status
        self.resolution = resolution
        # The ai_actions proposal this conflict became, when policy
        # is 'propose' — the record CITES the proposal, never IS one.
        self.proposal_ref = proposal_ref
        self.notes = notes
