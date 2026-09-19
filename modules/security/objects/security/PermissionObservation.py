"""
@module security.objects.security.PermissionObservation

Row class PermissionObservation of the security module — one class per file.
"""
from objectTreeDecorators import treeObject, treeObjectInit


class PermissionObservation(treeObject):
    """DEV MODE ONLY (his ask 2026-09-15): who did what — the caller's groups/roles, the permission profiles that
    applied, the verb and the class — counted. The primary route to WORK OUT app-level permission profiles: the
    observations are derived into proposed AppPermissionProfile rows (a suggestion with its evidence, never
    auto-applied)."""

    @treeObjectInit
    def __init__(self, name: str = '', actor: str = '', groups: str = '', profiles: str = '', verb: str = '', class_name: str = '',
                 app: str = '', verdict: str = '', count: int = 0, first_seen: str = '', last_seen: str = '', posture: str = 'dev',
                 tasks_json: str = '{}'):
        self.name = name                # groups|class|verb (one row per role-set × act)
        self.actor = actor              # the last caller (username / sub) — the ROLES are what profiles are derived from
        self.groups = groups            # the caller's KC groups + realm/client roles, comma-joined, sorted
        self.profiles = profiles        # the AppPermissionProfile rows that granted (comma-joined); '' = none matched
        self.verb = verb                # read | create | update | delete | events
        self.class_name = class_name
        self.app = app                  # the app the class belongs to, when known
        self.verdict = verdict          # granted-by-profile | admin | would-deny | unauthenticated | ungated (gate off, no model)
        self.count = count
        self.first_seen = first_seen
        self.last_seen = last_seen
        self.posture = posture
        # ct-7 (design §8): {task: count} — how many of this act's occurrences happened while a role-play session
        # stated that task. The row's NAME stays `groups|class|verb`, so adding tasks never multiplies the
        # ledger; an act performed under two tasks is ONE row that says so, and `review` groups by the key.
        self.tasks_json = tasks_json
