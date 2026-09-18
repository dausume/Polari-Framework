"""
@cross-cutting
@module polariapps.apps_roles_basis
@tags @xc:bindings

ROLES -> APPS (his ask 2026-09-18): *"We want to be able to have a primary role and additional roles. We will
want to be able to tie Apps to roles so that the user can see and navigate to the apps they need more easily.
And then the user should be able to refine that further and add apps they want to use or remove ones they do
not care about."*

Two rows, layered, and the layering is the whole design:

  RoleAppBinding     institutional — role (a Keycloak GROUP name) -> ordered app names. Derived from what the
                     modules themselves declare (a manifest's `app.roles`, personas as the older fallback),
                     or set by an administrator, or accepted from a role-play review.
  UserAppPreference  personal — one person's primary role plus the apps they added or hid. Keyed by the
                     Keycloak `sub` ALONE (his rule D18-1).

WHY THESE LIVE IN polariapps AND NOT security: these rows are about APPS. polariapps already owns
`PolariAppDefinition`, the persona index, `/api/apps/nav` and `AppPermissionProfile`; a binding is navigation,
not enforcement, and hiding an app grants and revokes nothing (the gate stays
`accessControl.app_permissions_gate`). The security module owns roles as a SECURITY concept — prototypes,
claims, observations — and this module reads its review only as a SUGGESTION, through a guarded import, so
polariapps keeps working on an instance that carries no security module at all.

The logic is in `polariapps.custom.apps_roles`; this file is the sap-2c index that re-exports the rows.

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - polariapps.apps_api (/api/apps/roles, /api/apps/mine)
  - polariapps.custom.apps_roles · polariapps.apps_selftest
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/apps_roles/;
# this file re-exports them (imports keep working) and holds what they share.

from polariapps.objects.apps_roles._shared import BINDING_SOURCES, DERIVATIONS, VIA  # noqa: F401
from polariapps.objects.apps_roles.RoleAppBinding import RoleAppBinding  # noqa: F401
from polariapps.objects.apps_roles.UserAppPreference import UserAppPreference  # noqa: F401
