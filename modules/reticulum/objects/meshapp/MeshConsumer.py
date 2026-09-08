"""
@module reticulum.objects.meshapp.MeshConsumer

Row class MeshConsumer of the reticulum module — one class per file (design §7), split
from meshapp_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class MeshConsumer(treeObject):
    """One mesh consumer. Its NAME is its Reticulum identity
    hash — the pseudonym IS the identity, and that is enough."""

    @treeObjectInit
    def __init__(self, name='', relay_name='', first_seen_ms=0,
                 last_seen_ms=0, last_return_interval_s=0.0,
                 returns_in_window=0, kc_subject='', kc_signed=False,
                 notes='', manager=None):
        self.name = name
        self.relay_name = relay_name
        self.first_seen_ms = first_seen_ms
        self.last_seen_ms = last_seen_ms
        # the feedback adaptive_cadence() aggregates.
        self.last_return_interval_s = last_return_interval_s
        self.returns_in_window = returns_in_window
        # '' unless the consumer OPTED IN under kc_link_mode
        # 'optional'; kc_signed says whether the linked identity is
        # signed or anonymous on the mesh-app's local Keycloak.
        self.kc_subject = kc_subject
        self.kc_signed = kc_signed
        self.notes = notes
