"""
@module reticulum.objects.datarule.QuarantinedSubmission

Row class QuarantinedSubmission of the reticulum module — one class per file (design §7), split
from datarule_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class QuarantinedSubmission(treeObject):
    """A caught submission — evidence, not garbage. payload_sample is
    BOUNDED (attackers don't get to fill our disk with their own
    ammunition); the hash identifies the full original."""

    @treeObjectInit
    def __init__(self, name='', rule_name='', app_name='',
                 consumer_identity='', reason='', evidence='',
                 payload_sha256='', payload_sample='',
                 payload_bytes=0, received_at_ms=0, notes='',
                 manager=None):
        self.name = name
        self.rule_name = rule_name
        self.app_name = app_name
        # the RNS identity hash — the census and the cadence both
        # read quarantine counts per identity.
        self.consumer_identity = consumer_identity
        self.reason = reason
        self.evidence = evidence
        self.payload_sha256 = payload_sha256
        self.payload_sample = payload_sample
        self.payload_bytes = payload_bytes
        self.received_at_ms = received_at_ms
        self.notes = notes
