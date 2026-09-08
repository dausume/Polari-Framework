"""
@module reticulum.objects.reticulum.TransportBinding

Row class TransportBinding of the reticulum module — one class per file (design §7), split
from reticulum_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class TransportBinding(treeObject):
    """'This app endpoint reaches that destination' + the admission
    policy — what makes ret-3's detection DATA rather than code."""

    @treeObjectInit
    def __init__(self, name='', app_name='', app_protocol='',
                 endpoint='', destination_name='', encoding='grpc',
                 max_message_bytes=4096, max_rate_per_min=60,
                 priority=5, fec_mode='auto', snapshot_mode='auto',
                 direction='both', enabled=False, notes='',
                 manager=None):
        self.name = name
        # WHICH app is asking (ret-1b: bindings are an app's asks —
        # the arch view groups demand by this).
        self.app_name = app_name
        # e.g. 'grpc-unary', 'http-get', 'json-message' — the named
        # handful; truly arbitrary IP is a promise the physics cannot
        # keep (plan §6, assumed as written).
        self.app_protocol = app_protocol
        self.endpoint = endpoint
        self.destination_name = destination_name
        self.encoding = encoding
        self.max_message_bytes = max_message_bytes
        self.max_rate_per_min = max_rate_per_min
        self.priority = priority
        self.fec_mode = fec_mode
        self.snapshot_mode = snapshot_mode
        self.direction = direction
        self.enabled = enabled
        self.notes = notes
