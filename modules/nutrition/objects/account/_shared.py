"""@module nutrition.objects.account._shared — what the account row classes share (constants, seeds, helpers); split from account_basis.py (sap-2c)."""

_PROV = 'mpa-4 (MEAL_PLANNING_APP_PLAN.md)'
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
