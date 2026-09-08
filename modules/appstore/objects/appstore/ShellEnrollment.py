"""
@module appstore.objects.appstore.ShellEnrollment

Row class ShellEnrollment of the appstore module — one class per file (design §7), split
from appstore_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class ShellEnrollment(treeObject):
    """One-time enrollment token, HASHED at rest.

    The wire token is '<name>.<secret>'; only sha256(secret) is
    stored. The plaintext exists exactly once — in the mint
    response — and redemption is single-use (status flips to
    'redeemed' BEFORE the response is written)."""

    @treeObjectInit
    def __init__(
        self,
        # Public token id ('enr-<12 hex>') — safe to log.
        name: str = '',
        # sha256 hexdigest of the secret half. NEVER the secret.
        token_hash: str = '',
        shell_name: str = '',
        # InstanceDefinition.name this enrollment binds to.
        instance_name: str = '',
        # Minter identity (Keycloak sub + preferred_username) — the
        # username becomes the shell's oidc login_hint.
        user_sub: str = '',
        username: str = '',
        created_at: str = '',
        # ISO-8601 UTC; TTL clamped to [60, 86400] s, default 900.
        expires_at: str = '',
        # ENROLLMENT_STATUSES entry.
        status: str = 'active',
        redeemed_at: str = '',
        redeemed_by_platform: str = '',
        # Client-supplied deviceLabel — audit trail only, no trust.
        redeemed_evidence: str = '',
        is_prior: bool = True,
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.token_hash = token_hash
        self.shell_name = shell_name
        self.instance_name = instance_name
        self.user_sub = user_sub
        self.username = username
        self.created_at = created_at
        self.expires_at = expires_at
        self.status = status
        self.redeemed_at = redeemed_at
        self.redeemed_by_platform = redeemed_by_platform
        self.redeemed_evidence = redeemed_evidence
        self.is_prior = is_prior
        self.notes = notes
