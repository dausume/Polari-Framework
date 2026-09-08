"""
@module appstore.objects.appstore_forks.ForkPin

Row class ForkPin of the appstore module — one class per file (design §7), split
from appstore_forks_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class ForkPin(treeObject):
    """One pinned (or honestly not-pinned) upstream."""

    @treeObjectInit
    def __init__(
        self,
        # Unique key = repo name ('LocalAI').
        name: str = '',
        title: str = '',
        upstream_url: str = '',
        fork_url: str = '',
        # Code license (weights carry their own — check both).
        license: str = '',
        # FORK_ROLES entry.
        role: str = 'other',
        # FORK_STATUSES entry.
        status: str = 'forked',
        # Runs usefully on CPU (the 6338N-class question).
        cpu_ok: bool = False,
        # What it serves in polari terms.
        needed_for: str = '',
        # When the fork's existence was last VERIFIED on GitHub.
        verified_at: str = '',
        notes: str = '',
        published: bool = True,
        is_prior: bool = True,
        manager=None,
    ):
        self.name = name
        self.title = title
        self.upstream_url = upstream_url
        self.fork_url = fork_url
        self.license = license
        self.role = role
        self.status = status
        self.cpu_ok = cpu_ok
        self.needed_for = needed_for
        self.verified_at = verified_at
        self.notes = notes
        self.published = published
        self.is_prior = is_prior
