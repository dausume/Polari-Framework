"""
@module security.objects.security.HardwareTrial

Row class HardwareTrial of the security module — one class per file.
"""
from objectTreeDecorators import treeObject, treeObjectInit


class HardwareTrial(treeObject):
    """One pkexec-traced first run of a hardware app (sec-i-5): what it touched (devices, caps, paths, groups) and the stanza it proposes; nothing is applied until an operator accepts. No trials exist yet — the class is the ledger's slot."""

    @treeObjectInit
    def __init__(self, name: str = '', app: str = '', started: str = '', ended: str = '', method: str = 'pkexec', observed_devices: str = '', observed_caps: str = '', observed_paths: str = '', observed_groups: str = '', proposed_stanza: str = '', accepted: bool = False, accepted_by: str = '', notes: str = ''):
        self.name = name
        self.app = app
        self.started = started
        self.ended = ended
        self.method = method
        self.observed_devices = observed_devices
        self.observed_caps = observed_caps
        self.observed_paths = observed_paths
        self.observed_groups = observed_groups
        self.proposed_stanza = proposed_stanza
        self.accepted = accepted
        self.accepted_by = accepted_by
        self.notes = notes
