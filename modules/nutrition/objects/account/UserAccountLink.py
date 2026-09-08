"""
@module nutrition.objects.account.UserAccountLink

Row class UserAccountLink of the nutrition module — one class per file (design §7), split
from account_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

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
