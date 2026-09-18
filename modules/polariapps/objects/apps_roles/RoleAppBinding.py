"""
@module polariapps.objects.apps_roles.RoleAppBinding

Row class RoleAppBinding of the polariapps module — one class per file.
"""
from objectTreeDecorators import treeObject, treeObjectInit


class RoleAppBinding(treeObject):
    """ROLE -> APPS (his ask 2026-09-18): the apps a role needs, so somebody holding that role can see and
    navigate to them without hunting through the whole catalogue.

    The role name IS the Keycloak group name — the same key the permission model already grants by
    (`polariapps.objects.apps_permissions._shared.caller_groups`), so a binding never invents an identity
    concept. `apps_json` is an ORDERED list of `PolariAppDefinition` names; order is what the person sees.

    This row is INSTITUTIONAL: it says what the role needs, not what one person wants. A person's own
    additions and removals live in `UserAppPreference`, which is layered on top of this and never edits it.

    `source` (see _shared.BINDING_SOURCES) records who decided: a module manifest declared it, an
    administrator set it, or a role-play review was accepted into it. `derived_from` is the evidence for a
    manifest-sourced row ('app.roles' or 'personas'). An `admin` row is never overwritten by the manifest
    derivation.
    """

    @treeObjectInit
    def __init__(self, name: str = '', role: str = '', apps_json: str = '[]', source: str = 'manifest',
                 derived_from: str = '', updated_at: str = '', updated_by: str = '', notes: str = '',
                 is_prior: bool = False):
        self.name = name                  # the row id — the role name, so there is exactly one binding per role
        self.role = role                  # the Keycloak group name ('journalist')
        self.apps_json = apps_json        # ORDERED JSON list of PolariAppDefinition names
        self.source = source              # manifest | admin | prototype-review
        self.derived_from = derived_from  # 'app.roles' | 'personas' | '' (evidence for a manifest row)
        self.updated_at = updated_at
        #: D18-1: a Keycloak `sub`, never a username or e-mail. '' for a derived row (nobody acted).
        self.updated_by = updated_by
        self.notes = notes
        self.is_prior = is_prior
