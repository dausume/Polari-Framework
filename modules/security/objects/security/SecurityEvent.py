"""
@module security.objects.security.SecurityEvent

Row class SecurityEvent of the security module — one class per file.
"""
from objectTreeDecorators import treeObject, treeObjectInit


class SecurityEvent(treeObject):
    """A security decision that was OBSERVED rather than enforced (ISLE_HARDENING_PLAN §17): in dev posture every
    control still evaluates and each would-have-been-denial lands here — who, what, which control would have denied,
    why, how many times. Counted by the notice bar ("N actions ran that production would deny") and the audit."""

    @treeObjectInit
    def __init__(self, name: str = '', control: str = '', action: str = '', target: str = '', actor: str = '', app: str = '',
                 outcome: str = 'observed', would_deny: bool = True, reason: str = '', posture: str = 'dev', count: int = 0,
                 first_seen: str = '', last_seen: str = '', source: str = ''):
        self.name = name
        self.control = control          # authz | peer-admission | certificate | trust-channel | content | browser | tier | posture
        self.action = action            # e.g. "update Person", "join-request from child-x", "https to core.example"
        self.target = target
        self.actor = actor
        self.app = app
        self.outcome = outcome          # observed (ran, would deny) | denied (production refused) | allowed (dev-admitted peer etc.)
        self.would_deny = would_deny
        self.reason = reason
        self.posture = posture
        self.count = count
        self.first_seen = first_seen
        self.last_seen = last_seen
        self.source = source            # the code path that decided (crude gate, agreements api, join flow, ...)
