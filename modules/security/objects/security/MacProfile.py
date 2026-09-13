"""
@module security.objects.security.MacProfile

Row class MacProfile of the security module — one class per file.
"""
from objectTreeDecorators import treeObject, treeObjectInit


class MacProfile(treeObject):
    """One AppArmor / seccomp / sVirt profile as rendered for a scenario and as loaded on a machine: mode, loaded, denials in 24 h, and a stanza hash so a manifest change shows as 'profile stale'. Derived from os-security/out/<scenario>/manifest.json and the latest SecurityAuditRun."""

    @treeObjectInit
    def __init__(self, name: str = '', app: str = '', scenario: str = '', kind: str = 'apparmor', profile: str = '', mode: str = 'absent', loaded: bool = False, attach: str = '', denials_24h: int = 0, stanza_hash: str = '', artifact: str = '', state: str = 'rendered'):
        self.name = name
        self.app = app
        self.scenario = scenario
        self.kind = kind
        self.profile = profile
        self.mode = mode
        self.loaded = loaded
        self.attach = attach
        self.denials_24h = denials_24h
        self.stanza_hash = stanza_hash
        self.artifact = artifact
        self.state = state
