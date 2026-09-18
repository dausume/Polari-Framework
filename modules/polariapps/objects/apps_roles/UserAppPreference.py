"""
@module polariapps.objects.apps_roles.UserAppPreference

Row class UserAppPreference of the polariapps module — one class per file.
"""
from objectTreeDecorators import treeObject, treeObjectInit


class UserAppPreference(treeObject):
    """ONE PERSON'S REFINEMENT of what their roles gave them (his ask 2026-09-18: *"the user should be able to
    refine that further and add apps they want to use or remove ones they do not care about"*).

    `primary_role` is which of the roles they HOLD leads — its apps come first. Everything else they hold is an
    additional role. The role list itself is never stored here: roles live in Keycloak and arrive in the
    token's `groups` claim, so this row can never drift out of agreement with what the person actually holds.

    `added_apps_json` are apps they asked for that no role of theirs binds; `removed_apps_json` are apps a role
    of theirs binds that they do not care about. Removal HIDES, it never revokes — permission is the
    `AppPermissionProfile` gate's business, and this row has no say in it.

    PII BOUNDARY (his rule D18-1, 2026-09-18): the person is identified by the opaque Keycloak `sub` and by
    nothing else. There is deliberately no username, e-mail or display-name column; a name is resolved live
    through the one gated door `GET /api/security/people/{sub}` and never cached into the tree. The row id
    (`name`) is the sub as well, so there is exactly one row per person.
    """

    @treeObjectInit
    def __init__(self, name: str = '', sub: str = '', primary_role: str = '', added_apps_json: str = '[]',
                 removed_apps_json: str = '[]', updated_at: str = ''):
        self.name = name                            # the row id — the Keycloak sub
        self.sub = sub                              # the Keycloak subject id; the ONLY identifier here
        self.primary_role = primary_role            # must be a role the person HOLDS, or '' (first bound one wins)
        self.added_apps_json = added_apps_json      # JSON list of app names they asked for
        self.removed_apps_json = removed_apps_json  # JSON list of app names they hid
        self.updated_at = updated_at
