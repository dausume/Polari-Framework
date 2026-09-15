"""
@module iso.objects.iso.IsoBuild

IsoBuild — one requested installer image: the choices, the state, the file.
"""
from objectTreeDecorators import treeObject, treeObjectInit


class IsoBuild(treeObject):
    """IsoBuild

    What it is: one unattended Ubuntu + Polari installer image as someone asked for it (ISO plan D1–D15): the base,
    the role (core / member / hardware / access / server), the shape (desktop / headless / detect), the options with
    their warnings (encryption off by default and refused on headless; Secure Boot on by default), the posture
    (production / dev), the look preset, the isle join info (or "become the core"), the target device (a probe's
    hash, so one stick can carry several plans), the state of the build with its steps, and the resulting file with
    its sha256 and bytes — held in the ISO pool under the same lifecycle as the app debs.
    Related concepts: IsoBase, DeviceProbe, the platform debs it carries, the app stick it is copied to.
    How it is measured or derived: everything is the person's choices or measured build output; nothing typed.
    """

    @treeObjectInit
    def __init__(self, name: str = '', base: str = '', role: str = 'member', shape: str = 'detect', encryption: bool = False, secure_boot: str = 'on',
                 posture: str = 'production', look: str = 'plasma-default', hostname: str = '', username: str = 'polari', ssh_keys: str = '',
                 join_core: str = '', join_fingerprint: str = '', join_tier: str = '', target_hash: str = '', apps: str = '', offline: bool = True,
                 state: str = 'requested', step: str = '', refusal: str = '', warnings: str = '', file: str = '', sha256: str = '', bytes: int = 0,
                 seconds: float = 0.0, requested_at: str = '', built_at: str = '', requested_by: str = ''):
        self.name = name
        self.base = base
        self.role = role
        self.shape = shape
        self.encryption = encryption
        self.secure_boot = secure_boot
        self.posture = posture
        self.look = look
        self.hostname = hostname
        self.username = username
        self.ssh_keys = ssh_keys
        self.join_core = join_core
        self.join_fingerprint = join_fingerprint
        self.join_tier = join_tier
        self.target_hash = target_hash
        self.apps = apps
        self.offline = offline
        self.state = state
        self.step = step
        self.refusal = refusal
        self.warnings = warnings
        self.file = file
        self.sha256 = sha256
        self.bytes = bytes
        self.seconds = seconds
        self.requested_at = requested_at
        self.built_at = built_at
        self.requested_by = requested_by
