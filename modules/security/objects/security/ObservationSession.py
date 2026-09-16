"""
@module security.objects.security.ObservationSession

Row class ObservationSession of the security module — one class per file.
"""
from objectTreeDecorators import treeObject, treeObjectInit


class ObservationSession(treeObject):
    """A ROLE-PLAY window (his ask 2026-09-16): a person in dev mode declares "I am acting as <role>" (a Journalist,
    say); while the session is open everything they touch — backend acts, endpoints, frontend apps/pages/actions —
    is attributed to that role, so reviewing the role later shows all of it, and a permissions admin can concrete
    it into an enforced group."""

    @treeObjectInit
    def __init__(self, name: str = '', role: str = '', actor: str = '', started_at: str = '', ended_at: str = '', active: bool = True,
                 note: str = '', acts: int = 0, usages: int = 0):
        self.name = name            # role|started_at
        self.role = role            # the group being role-played ('journalist')
        self.actor = actor          # who is playing it
        self.started_at = started_at
        self.ended_at = ended_at
        self.active = active
        self.note = note
        self.acts = acts            # backend acts attributed while open
        self.usages = usages        # frontend usages attributed while open
