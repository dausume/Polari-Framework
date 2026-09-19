"""
@module security.objects.security.OwnerGrant

Row class OwnerGrant of the security module — one class per file.
"""
from objectTreeDecorators import treeObject, treeObjectInit


class OwnerGrant(treeObject):
    """ONE INSTANCE, SHARED BY ITS OWNER, inside the bounds the class set (op-1; design
    OWNER_DEFINED_PERMISSIONS_DESIGN.md §2 and §3 step 3).

    `OwnedClassPolicy` says what a class allows; this row says what ONE owner did with one of their own
    instances. A household member sharing one meal plan with one other person is this row; a ballot never has
    one, because its policy sets `owner_may_grant` false and the grant door refuses before a row is written.

    THE BOUNDS, all checked by `security.custom.security_owner_grants.grant()` and none of them by this class:
      * only when the policy's `owner_may_grant`;
      * only by the instance's OWNER (an administrator may act too — they are outside the owner rules anyway);
      * `verbs` ⊆ the policy's `grantable_verbs`; `grantee_kind` ∈ the policy's `grantee_kinds`;
      * `fields` ⊆ the class's own fields — a grant may only widen the projection, never invent a column;
      * never to yourself: a grant to the owner is the owner floor said twice, and is refused.

    A GRANT NEVER WIDENS THE CLASS DOOR. `crude_permission_gate` (class × verb for the caller's groups) has
    already decided before any of this runs, so a grant can only narrow-then-restore inside what the grantee's
    groups could already do to the class. Owner-defined permissions narrow; they never widen (design §3, as
    built).

    THE GRANTEE, and why it is TWO columns rather than the design's one:
      the design names one `grantee` field holding *a group name, or a `sub` — never a name*. A single column
      would mean a Keycloak subject id and a Keycloak group name share one place, and the screens cannot then
      say which they are looking at: the `person` column format (§54) shortens a cell to 8 characters and
      resolves it live through `POST /api/security/people`, which would mangle `household-members` into
      `househol` the moment a group grant appeared. So the row keeps `grantee_group` and `grantee_sub`, exactly
      one of which is ever set, and the DOOR keeps the design's shape (`{grantee_kind, grantee}`) by routing
      the value to the right column. The dict answers carry `grantee` as the design spells it.

    EXPIRY is honest, not lazy: `valid_until` (an ISO-8601 UTC instant, '' = no expiry) is checked by the
    verdict on every read — an expired grant decides nothing the second it expires — and the row is PRUNED on
    the next read of the instance's grants, so the table does not grow a tail of dead permissions.
    """

    #: a grant names a group or a person, and the policy's `grantee_kinds` says which of the two it may name
    GRANTEE_KINDS = ('group', 'person')

    @treeObjectInit
    def __init__(self, name: str = '', class_name: str = '', object_id: str = '',
                 grantee_kind: str = 'person', grantee_group: str = '', grantee_sub: str = '',
                 verbs_json: str = '[]', fields_json: str = '[]',
                 valid_until: str = '', granted_by: str = '', granted_at: str = '', notes: str = ''):
        self.name = name                    # class|id|kind|grantee — the dedup key (one row per grantee per instance)
        self.class_name = class_name        # the owned class; its policy sets every bound this row lives inside
        self.object_id = object_id          # the ONE instance shared — a grant is never class-wide
        self.grantee_kind = grantee_kind    # group | person
        self.grantee_group = grantee_group  # the Keycloak GROUP name, when grantee_kind is group; '' otherwise
        self.grantee_sub = grantee_sub      # the Keycloak `sub` alone (D18-1), when grantee_kind is person; '' otherwise
        self.verbs_json = verbs_json        # ⊆ the policy's grantable_verbs
        self.fields_json = fields_json      # ⊆ the class's fields; unioned with others_fields when a read is projected
        self.valid_until = valid_until      # ISO-8601 UTC; '' = no expiry. An expired grant decides nothing and is pruned
        self.granted_by = granted_by        # the OWNER's Keycloak sub (D18-1) — who shared it, on the record
        self.granted_at = granted_at
        self.notes = notes
