"""
@module security.objects.security.SshPermissionLevel

Row class SshPermissionLevel — one principal (a person or a group) on one device and what it may do over ssh.
"""
from objectTreeDecorators import treeObject, treeObjectInit


class SshPermissionLevel(treeObject):
    """His ask 2026-09-14: Polari tracks ssh AND the permission levels behind it, so a device can be assured
    secure or declared dev. One row per principal per device: whether it may log in over ssh at all
    (AllowGroups / an authorized key), and its level once in — root, blanket sudo (ALL), scoped sudo (a named
    command list), a plain shell, or none. `via` says where the level comes from; `expires` is set when the
    level exists only under a dev posture. Derived from the posted inventory (sshd -T, /etc/group, sudoers
    lines — never key material)."""

    @treeObjectInit
    def __init__(self, name: str = '', device: str = '', principal: str = '', kind: str = 'user', allowed_over_ssh: bool = False,
                 level: str = 'none', via: str = '', commands: str = '', members: str = '', posture: str = 'secure', expires: str = '',
                 observed_at: str = ''):
        self.name = name
        self.device = device
        self.principal = principal
        self.kind = kind
        self.allowed_over_ssh = allowed_over_ssh
        self.level = level
        self.via = via
        self.commands = commands
        self.members = members
        self.posture = posture
        self.expires = expires
        self.observed_at = observed_at
