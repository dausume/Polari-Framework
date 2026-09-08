"""
@cross-cutting
@module nutrition.account_basis
@tags @xc:bindings

mpa-4 — Keycloak accounts ↔ meal-planning identities
(MEAL_PLANNING_APP_PLAN.md §0.2: "tie users and their information
to keycloak login accounts"):

  UserAccountLink   one explicit row linking a Keycloak subject to
                    a PersonProfile (and optionally a household).
                    The JWT middleware already puts {sub, username,
                    email} on request.context.user_info (/auth/me);
                    this row is what makes that identity MEAN a
                    person here. Explicit by design (A4): no silent
                    auto-provisioning — /api/mealplanning/me reports
                    an unlinked login honestly with the fix named.

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - nutrition.custom.tracking_analysis (resolve_me), mealplanning_api
@see AI-Notes/plans/MEAL_PLANNING_APP_PLAN.md §mpa-4
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/account/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

from objectTreeDecorators import treeObject, treeObjectInit

from nutrition.objects.account._shared import SEED_USER_ACCOUNT_LINKS, _PROV  # noqa: F401
from nutrition.objects.account.UserAccountLink import UserAccountLink  # noqa: F401
