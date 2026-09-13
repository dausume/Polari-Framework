"""
@module security.objects.security.TrustChannel

Row class TrustChannel of the security module — one class per file.
"""
from objectTreeDecorators import treeObject, treeObjectInit


class TrustChannel(treeObject):
    """One channel the system knows (from → to): transport, authentication, key kind (asymmetric for users, symmetric between servers), key source, verified. Derived from the proxy templates (user→app), the Keycloak realm (clients), ServiceConnection rows and the isle protocol matrix. A symmetric key on a user channel is a finding."""

    @treeObjectInit
    def __init__(self, name: str = '', from_kind: str = '', to_kind: str = '', from_app: str = '', to_app: str = '', direction: str = 'to', transport: str = 'plain', auth: str = 'none', key_kind: str = 'asymmetric', key_source: str = '', scenario: str = 'any', verified: bool = False, finding: str = '', evidence: str = ''):
        self.name = name
        self.from_kind = from_kind
        self.to_kind = to_kind
        self.from_app = from_app
        self.to_app = to_app
        self.direction = direction
        self.transport = transport
        self.auth = auth
        self.key_kind = key_kind
        self.key_source = key_source
        self.scenario = scenario
        self.verified = verified
        self.finding = finding
        self.evidence = evidence
