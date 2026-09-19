"""
@module security.objects.security.OwnedClassPolicy

Row class OwnedClassPolicy of the security module — one class per file.
"""
from objectTreeDecorators import treeObject, treeObjectInit


class OwnedClassPolicy(treeObject):
    """OWNER-DEFINED PERMISSIONS, opted in PER CLASS (op-0; design OWNER_DEFINED_PERMISSIONS_DESIGN.md §2).

    Object-defined permissions (`AppPermissionProfile` × `crude_permission_gate`) stay the default for every
    class. A class carries no owner and no owner rules until an ENABLED row of this class names it — his ruling
    2026-09-18: *"something we typically want specifically enabled per object, not something we enable by
    default"*. Turning it on does three things: instances get an owner stamped at create, the CRUDE gate gains a
    second, instance-level check for that class, and (op-1) the owner may write per-instance grants.

    THE ORDER THE VERDICT FOLLOWS (design §3, implemented in security.custom.security_owned):
      1. the CLASS gate first, unchanged — owner-defined never widens what OTHERS may do beyond the class door;
      2. the OWNER FLOOR: the caller's `sub` == the instance's owner → `owner_verbs`, even where the class
         profile would not grant the verb to their group — the one place owner-defined ADDS — minus
         update/delete when `frozen_when` holds;
      3. OTHERS' CEILING: `others_verbs` only, reads PROJECTED to `others_fields`, the owner column dropped
         unless `owner_visible`;
      4. LISTS: own rows whole, others' rows projected, unreadable rows OMITTED — never a 403 for a whole list.

    THE PII BOUNDARY (his rule D18-1): the owner is the opaque Keycloak `sub` and nothing else — never a
    username, an e-mail or a display name.

    Lists are JSON-text columns (`*_json`), the module's existing convention (AppPermissionProfile.verbs_json).

    `owner_field` is op-0's one addition to the design's field list: the design assumes the owner column is
    literally named `owner`, but the first class to opt in (`UserAppPreference`, §57) already keys its person by
    a column called `sub`, and the per-class schema freeze says do not add a duplicate column to a live class.
    So the policy names the column instead; it defaults to `owner`, which is what a class designed for this arc
    (Ballot, op-3) will use.
    """

    #: the verbs an owner policy may ever speak about (the CRUDE vocabulary minus `create` — creation is the
    #: class door's business; an instance has no owner until it exists)
    OWNER_VERBS = ('read', 'update', 'delete', 'events')
    #: who may change `owner` — op-0 stores it and refuses nothing yet (transfer is op-2)
    TRANSFER_MODES = ('nobody', 'admin', 'owner')
    #: who an owner may grant to, when `owner_may_grant` (op-1)
    GRANTEE_KINDS = ('group', 'person')
    #: op-4: who wrote this row. `manifest` is re-derived from the module's `app.owned` stanza on every read;
    #: `admin` is a person's decision and is NEVER overwritten by a derivation (the `RoleAppBinding` discipline,
    #: §57). An empty value is an op-0 seeded row and is treated as re-derivable, because the seed IS the
    #: derivation's earlier spelling of the same policy.
    SOURCES = ('manifest', 'admin')

    @treeObjectInit
    def __init__(self, name: str = '', class_name: str = '', enabled: bool = False,
                 owner_verbs_json: str = '["read", "update", "delete"]',
                 others_verbs_json: str = '[]', others_fields_json: str = '[]',
                 owner_visible: bool = False, owner_may_grant: bool = False,
                 grantable_verbs_json: str = '[]', grantee_kinds_json: str = '[]',
                 frozen_when: str = '', transfer: str = 'nobody', anonymised: bool = False,
                 owner_field: str = 'owner', source: str = '', derived_from: str = '', notes: str = ''):
        self.name = name                              # the row id — the class name
        self.class_name = class_name                  # the opted-in class
        self.enabled = enabled                        # the opt-in itself; False = the class is object-defined only
        self.owner_verbs_json = owner_verbs_json      # what the owner has on their OWN instances
        self.others_verbs_json = others_verbs_json    # what a caller who passed the class door gets on others'
        self.others_fields_json = others_fields_json  # the fields a non-owner may see; everything else is dropped
        self.owner_visible = owner_visible            # may a non-owner see the owner column at all?
        self.owner_may_grant = owner_may_grant        # op-1: may the owner widen access per instance?
        self.grantable_verbs_json = grantable_verbs_json   # op-1: the bound on what a grant may carry
        self.grantee_kinds_json = grantee_kinds_json       # op-1: 'group' and/or 'person'
        self.frozen_when = frozen_when                # a condition after which the owner loses update/delete
        self.transfer = transfer                      # nobody | admin | owner
        self.anonymised = anonymised                  # op-2: owner_visible false + the side-channel suppressions
        self.owner_field = owner_field                # the column that holds the owner's `sub` (see the docstring)
        self.source = source                          # op-4: manifest | admin ('' = the op-0 seed, re-derivable)
        self.derived_from = derived_from              # op-4: the module whose `app.owned` stanza declared it
        self.notes = notes
