"""@module nutrition.objects.budget._shared — what the budget row classes share (constants, seeds, helpers); split from budget_basis.py (sap-2c)."""

_PROV = 'mpb-3 (MEAL_PLANNING_APP_PLAN §3b)'
SEED_PLAN_BUDGETS = [
    {'name': 'demo-alex-week-budget', 'plan_name': 'demo-alex-week',
     'household_name': '', 'weekly_amount': 60.0,
     'currency': 'USD', 'scope_note': 'demo cap — set your own',
     'is_prior': True, 'provenance_id': _PROV,
     'notes': 'demo row'},
]
