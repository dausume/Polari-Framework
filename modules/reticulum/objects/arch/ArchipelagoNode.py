"""
@module reticulum.objects.arch.ArchipelagoNode

Row class ArchipelagoNode of the reticulum module — one class per file (design §7), split
from arch_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class ArchipelagoNode(treeObject):
    """A named node in `.arch`: the human/app surface of §3's mapping.
    Measured reachability lives here; declared trust lives on the
    ArchipelagoTrust row it names — the split is the point."""

    @treeObjectInit
    def __init__(self, name='', arch_name='', destination_name='',
                 node_kind='peer-isle', vouched_by='', trust_name='',
                 last_heard_ms=0, hop_count=0, link_quality='',
                 fidelity='declared', notes='', manager=None):
        self.name = name
        # The '<x>.arch' name; kept beside row name so a row rename
        # never silently changes what resolvers hand out.
        self.arch_name = arch_name
        self.destination_name = destination_name
        self.node_kind = node_kind
        # WHO vouches for this node (an identity name) — provenance,
        # not authority.
        self.vouched_by = vouched_by
        self.trust_name = trust_name
        # Measured reachability — timestamps, not hopes.
        self.last_heard_ms = last_heard_ms
        self.hop_count = hop_count
        self.link_quality = link_quality
        self.fidelity = fidelity
        self.notes = notes
