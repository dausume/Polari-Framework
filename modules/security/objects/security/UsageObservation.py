"""
@module security.objects.security.UsageObservation

Row class UsageObservation of the security module — one class per file.
"""
from objectTreeDecorators import treeObject, treeObjectInit


class UsageObservation(treeObject):
    """DEV MODE, recording on: what a role USES beyond CRUDE acts — the frontend's apps, pages, components and
    actions (posted by the frontend while role-playing) and the API endpoints it hits (seen by the backend) — one
    row per role × kind × name, counted. With PermissionObservation (objects × verbs) this is the whole picture of a
    role's job, the material a permissions admin concretes into an enforced group."""

    @treeObjectInit
    def __init__(self, name: str = '', role: str = '', kind: str = '', item: str = '', app: str = '', page: str = '', detail: str = '',
                 actor: str = '', count: int = 0, first_seen: str = '', last_seen: str = '', tasks_json: str = '{}'):
        self.name = name        # role|kind|item
        self.role = role        # the role-played group ('journalist'); '' = the caller's real groups only
        self.kind = kind        # app | page | component | action | endpoint
        self.item = item        # the app id, the route, the component name, the action, or "GET /api/x/{id}"
        self.app = app
        self.page = page
        self.detail = detail
        self.actor = actor
        self.count = count
        self.first_seen = first_seen
        self.last_seen = last_seen
        # ct-7 (design §8): {task: count} — which stated task walked through this door, and how often. Same rule
        # as PermissionObservation: the row's name is still `role|kind|item`, so a door used by three tasks is
        # one counted row that names all three rather than three rows.
        self.tasks_json = tasks_json
