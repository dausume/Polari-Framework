"""
@module security.objects.security.SshCapability

Row class SshCapability — one device's ssh surface as a security vector: who can get in, how, and from where.
"""
from objectTreeDecorators import treeObject, treeObjectInit


class SshCapability(treeObject):
    """Per device (his ask 2026-09-13): whether sshd listens and on which addresses, whether passwords or
    keyboard-interactive logins are accepted (the guessable vector) or keys only, whether root may log in,
    how many authorized keys of which types exist and for which users (never the key material), which
    private keys and outbound relationships the device holds (it can reach whom), fail2ban / rate limiting,
    failed logins in 24 h, and the verdict. Derived from the audit's `ssh` ring and the posted inventory;
    shown on the isle topology (his ask: "the ssh accounted for on the isle topology")."""

    @treeObjectInit
    def __init__(self, name: str = '', device: str = '', role: str = '', listens: bool = False, listen_addresses: str = '',
                 password_auth: str = 'unknown', pubkey_auth: str = 'unknown', permit_root: str = 'unknown', kbd_interactive: str = 'unknown',
                 authorized_keys: int = 0, key_types: str = '', key_users: str = '', weak_keys: int = 0, private_keys: str = '',
                 reaches: str = '', brute_force_guard: str = 'none', failed_logins_24h: int = 0, ufw: str = '', verdict: str = 'unknown',
                 vector: str = '', observed_at: str = ''):
        self.name = name
        self.device = device
        self.role = role
        self.listens = listens
        self.listen_addresses = listen_addresses
        self.password_auth = password_auth
        self.pubkey_auth = pubkey_auth
        self.permit_root = permit_root
        self.kbd_interactive = kbd_interactive
        self.authorized_keys = authorized_keys
        self.key_types = key_types
        self.key_users = key_users
        self.weak_keys = weak_keys
        self.private_keys = private_keys
        self.reaches = reaches
        self.brute_force_guard = brute_force_guard
        self.failed_logins_24h = failed_logins_24h
        self.ufw = ufw
        self.verdict = verdict
        self.vector = vector
        self.observed_at = observed_at
