"""
@cross-cutting
@module polariapps.apps_permissions_basis
@tags @xc:accessControl

sep-7 (separation plan decisions 10/11): per-app PERMISSION
PROFILES. ONE Polari login; access composes down the object-coherent
chain: KC group -> AppPermissionProfile -> app -> its modules ->
classes -> CRUDE verbs. Profiles are ROWS (reusable, auditable);
KC groups grant profiles; the union of a caller's profiles is what
they may touch.

Identity is evidence (the group-authority precedent, built ON not
around): every verdict carries WHERE the groups came from and WHICH
profile allowed, never a bare boolean. The `groups` JWT claim is
preferred (Keycloak group-membership mapper); realm/client ROLES
also grant, so existing realms work without new mappers — the
verdict names which source matched.

Enforcement itself lives in accessControl.app_permissions_gate
(core-resident, knob POLARI_APP_PERMISSIONS=off|advisory|enforce,
default off) — this module is the model + resolution only, so the
gate degrades honestly when polariapps is absent.

@consumers
  - accessControl.app_permissions_gate (CRUDE enforcement)
  - polariapps.apps_api (/api/apps/permissions/*)
  - polariapps.apps_selftest
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/apps_permissions/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

import json
from objectTreeDecorators import treeObject, treeObjectInit

from polariapps.objects.apps_permissions._shared import ADMIN_ROLES, CRUDE_VERBS, SEED_PERMISSION_PROFILES, _loads, caller_groups, classes_for_app, classes_for_module, permission_verdict, resolve_grants  # noqa: F401
from polariapps.objects.apps_permissions.AppPermissionProfile import AppPermissionProfile  # noqa: F401
