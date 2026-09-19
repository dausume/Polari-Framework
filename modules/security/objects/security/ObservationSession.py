"""
@module security.objects.security.ObservationSession

Row class ObservationSession of the security module — one class per file.
"""
from objectTreeDecorators import treeObject, treeObjectInit


class ObservationSession(treeObject):
    """A ROLE-PLAY window (his ask 2026-09-16): a person in dev mode declares "I am acting as <role>" (a Journalist,
    say); while the session is open everything they touch — backend acts, endpoints, frontend apps/pages/actions —
    is attributed to that role, so reviewing the role later shows all of it, and a permissions admin can concrete
    it into an enforced group.

    ct-7 (design §8): the session also states the TASK being performed — "publish an article", "reconcile last
    week's meals". A person's needs are the union of the tasks their roles perform, and a task's needs are the
    closure of the doors it walks through, so every act recorded while the session is open carries the task and
    `review(role)` reads as *tasks → doors → objects × verbs → closure* instead of a flat class list. The task is
    free text the role-player states; it may change mid-session through the same door, and `tasks_json` keeps the
    ones stated in order so a changed task never erases the one before it."""

    @treeObjectInit
    def __init__(self, name: str = '', role: str = '', actor: str = '', started_at: str = '', ended_at: str = '', active: bool = True,
                 note: str = '', acts: int = 0, usages: int = 0, task: str = '', tasks_json: str = '[]'):
        self.name = name            # role|started_at
        self.role = role            # the group being role-played ('journalist')
        self.actor = actor          # who is playing it
        self.started_at = started_at
        self.ended_at = ended_at
        self.active = active
        self.note = note
        self.acts = acts            # backend acts attributed while open
        self.usages = usages        # frontend usages attributed while open
        self.task = task            # ct-7: the task being performed RIGHT NOW ('' = none stated)
        self.tasks_json = tasks_json  # ct-7: [{task, at}] — every task stated in this session, in order
