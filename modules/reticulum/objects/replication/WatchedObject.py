"""
@module reticulum.objects.replication.WatchedObject

Row class WatchedObject of the reticulum module — one class per file (design §7), split
from replication_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class WatchedObject(treeObject):
    """WHICH objects are replicated, and under what policy. Everything
    here is a knob with a conservative default; nothing silently picks
    for you."""

    @treeObjectInit
    def __init__(self, name='', class_name='', object_name='',
                 query_json='', direction='publish',
                 publication_class='local-only',
                 bearer_policy_json='{}', cadence_seconds=300,
                 keyframe_every_n=10, conflict_policy='propose',
                 enabled=False, notes='', manager=None):
        self.name = name
        # By class, by name, or by query — the three selection shapes.
        self.class_name = class_name
        self.object_name = object_name
        self.query_json = query_json
        self.direction = direction
        self.publication_class = publication_class
        self.bearer_policy_json = bearer_policy_json
        self.cadence_seconds = cadence_seconds
        self.keyframe_every_n = keyframe_every_n
        self.conflict_policy = conflict_policy
        self.enabled = enabled
        self.notes = notes
