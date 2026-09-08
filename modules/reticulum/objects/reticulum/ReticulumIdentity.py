"""
@module reticulum.objects.reticulum.ReticulumIdentity

Row class ReticulumIdentity of the reticulum module — one class per file (design §7), split
from reticulum_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class ReticulumIdentity(treeObject):
    """An RNS identity we hold or trust. Binds an INSTANCE (default,
    §6 assumption) or a KC subject to an identity hash. Private keys
    never land in a row — key_location is a label naming where the
    sidecar keeps it, not material."""

    @treeObjectInit
    def __init__(self, name='', kind='instance', instance_name='',
                 kc_subject='', identity_hash='', key_location='',
                 held=False, source='', notes='', manager=None):
        self.name = name
        self.kind = kind
        self.instance_name = instance_name
        # NULLABLE by design: instance-level is the default binding;
        # a per-user (operator) identity fills this in.
        self.kc_subject = kc_subject
        self.identity_hash = identity_hash
        self.key_location = key_location
        # Whether WE hold the private key (vs. a trusted remote peer).
        self.held = held
        # How this identity entered the rows — evidence, never bare.
        self.source = source
        self.notes = notes
