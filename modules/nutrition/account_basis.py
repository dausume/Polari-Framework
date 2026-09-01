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
  - nutrition.tracking_analysis (resolve_me), mealplanning_api
@see AI-Notes/plans/MEAL_PLANNING_APP_PLAN.md §mpa-4
"""

from objectTreeDecorators import treeObject, treeObjectInit

_PROV = 'mpa-4 (MEAL_PLANNING_APP_PLAN.md)'


class UserAccountLink(treeObject):
    """One Keycloak account → one PersonProfile."""

    @treeObjectInit
    def __init__(
        self,
        # unique key ('link-<username>').
        name: str = '',
        # Keycloak subject (the stable id — matching precedence:
        # sub, then username, then email).
        keycloak_sub: str = '',
        keycloak_username: str = '',
        keycloak_email: str = '',
        # the PersonProfile this login IS here.
        person_name: str = '',
        # optional HouseholdProfile for pantry/plan scoping.
        household_name: str = '',
        # ISO date the link was made.
        linked_date: str = '',
        is_prior: bool = False,
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.keycloak_sub = keycloak_sub
        self.keycloak_username = keycloak_username
        self.keycloak_email = keycloak_email
        self.person_name = person_name
        self.household_name = household_name
        self.linked_date = linked_date
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes


#: Demo link so the /me surface renders end-to-end before real
#: accounts are linked (demo-alex is the nut-3 seeded person).
SEED_USER_ACCOUNT_LINKS = [
    {'name': 'link-demo-alex', 'keycloak_sub': '',
     'keycloak_username': 'demo-alex',
     'keycloak_email': 'demo-alex@example.invalid',
     'person_name': 'demo-alex', 'household_name': 'demo-household',
     'linked_date': '2026-09-01', 'is_prior': True,
     'provenance_id': _PROV,
     'notes': 'demo row — link real accounts via CRUDE '
              '(UserAccountLink) or the profile page'},
]
