"""
@module security.objects.security.ContentPolicyViolation

Row class ContentPolicyViolation of the security module — one class per file.
"""
from objectTreeDecorators import treeObject, treeObjectInit


class ContentPolicyViolation(treeObject):
    """Evidence rows in observe mode: app, target, field, reason, count, first/last seen, hashed client. Empty until the observe hook exists."""

    @treeObjectInit
    def __init__(self, name: str = '', app: str = '', target: str = '', field: str = '', reason: str = '', count: int = 0, first_seen: str = '', last_seen: str = '', client_hash: str = ''):
        self.name = name
        self.app = app
        self.target = target
        self.field = field
        self.reason = reason
        self.count = count
        self.first_seen = first_seen
        self.last_seen = last_seen
        self.client_hash = client_hash
