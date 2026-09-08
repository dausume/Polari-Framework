"""
@module reticulum.objects.meshapp.MeshAppRelay

Row class MeshAppRelay of the reticulum module — one class per file (design §7), split
from meshapp_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class MeshAppRelay(treeObject):
    """The lighthouse: broadcasts one app's state to the open sea.
    Reuses the §5f machinery wholesale — watched_name points at the
    WatchedObject whose parent/child versions and keyframes carry
    the actual state."""

    @treeObjectInit
    def __init__(self, name='', app_name='', exposure_name='',
                 watched_name='', cadence_seconds=60,
                 min_cadence_seconds=10, max_cadence_seconds=600,
                 prior_states_kept=1, expected_users=0,
                 kc_link_mode='disabled', enabled=False, notes='',
                 manager=None):
        self.name = name
        self.app_name = app_name
        self.exposure_name = exposure_name
        self.watched_name = watched_name
        # current cadence — adaptive_cadence() moves it between the
        # bounds; the floor answers to the airtime budget (row 19).
        self.cadence_seconds = cadence_seconds
        self.min_cadence_seconds = min_cadence_seconds
        self.max_cadence_seconds = max_cadence_seconds
        # current + N prior states ride each keyframe window.
        self.prior_states_kept = prior_states_kept
        self.expected_users = expected_users
        self.kc_link_mode = kc_link_mode
        self.enabled = enabled
        self.notes = notes
