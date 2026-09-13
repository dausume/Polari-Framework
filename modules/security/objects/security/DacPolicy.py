"""
@module security.objects.security.DacPolicy

Row class DacPolicy of the security module — one class per file.
"""
from objectTreeDecorators import treeObject, treeObjectInit


class DacPolicy(treeObject):
    """One app's DAC as declared by its stanza for a scenario (uid, read-only root, capabilities added back, writable paths, pid limit, tmpfs) beside what the container actually runs with when an audit run reports it. Never hand-typed."""

    @treeObjectInit
    def __init__(self, name: str = '', app: str = '', scenario: str = '', kind: str = '', read_only: bool = True, caps_add: str = '', writable: str = '', pids_limit: int = 512, tmpfs: str = '/tmp,/run', no_new_privileges: bool = True, userns: str = '', live_read_only: str = '', live_caps: str = '', live_user: str = '', drift: str = ''):
        self.name = name
        self.app = app
        self.scenario = scenario
        self.kind = kind
        self.read_only = read_only
        self.caps_add = caps_add
        self.writable = writable
        self.pids_limit = pids_limit
        self.tmpfs = tmpfs
        self.no_new_privileges = no_new_privileges
        self.userns = userns
        self.live_read_only = live_read_only
        self.live_caps = live_caps
        self.live_user = live_user
        self.drift = drift
