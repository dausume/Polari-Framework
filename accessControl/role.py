"""
Role — Polari-side reflection of a Keycloak realm role.

Storage of choice for permission grants:
    grants_by_class_json : JSON blob mapping {className: [ops...]} where
                           ops are CRUDE letters (C/R/U/D/E).

Why JSON-in-a-column and not a separate join table:
    - matches how every other definition-class stores its variable shape
      in this codebase (EquationDefinition.definition, etc.)
    - permissions are read all at once whenever they're read at all
    - admin writes go through dedicated endpoints; no DB-level joins needed

PII posture:
    This class never stores user data. It stores roles + grants only.
    User-side data (sub, username, email, roles) is read from each
    request's JWT and never persisted by the framework.
"""

from objectTreeDecorators import treeObject, treeObjectInit


class Role(treeObject):
    """A reflection of a Keycloak role plus its per-class CRUDE grants.

    Identity: `name` — must match the Keycloak realm-role name.
    Synced lazily by RoleAPI when `/api/roles` is read.
    """

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        description: str = '',
        # 'keycloak-realm' is the only source for now. `polari-local` is
        # reserved for a future Phase where we may add roles that exist
        # only inside Polari (not synced from KC).
        source: str = 'keycloak-realm',
        synced_at: str = '',
        # JSON-encoded dict: {className: [op_letter, ...]}.
        # Kept as a string for DB-table compatibility; RoleAPI handles
        # parsing/serialization on read/write so callers see a real dict.
        grants_by_class_json: str = '{}',
        manager=None,
    ):
        self.name = name
        self.description = description
        self.source = source
        self.synced_at = synced_at
        self.grants_by_class_json = grants_by_class_json
