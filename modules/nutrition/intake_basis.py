"""
@cross-cutting
@module nutrition.intake_basis
@tags @xc:bindings

mpa-4 — what was actually EATEN, over time:

  IntakeRecord   one eaten meal: person × date × slot × template ×
                 variation × scale. A plan is an intention; this is
                 the fact — the tracking series (nutrition, meal
                 acidity, GL over time) roll up from THESE rows.
                 `source` keeps the honesty: 'planned-confirmed'
                 (ate as planned — the A6 default gesture) vs
                 'logged' (entered directly) vs 'estimated'.

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - nutrition.custom.tracking_analysis, mealplanning_api
@see AI-Notes/plans/MEAL_PLANNING_APP_PLAN.md §mpa-4
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/intake/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

from objectTreeDecorators import treeObject, treeObjectInit

from nutrition.objects.intake._shared import INTAKE_SOURCES, SEED_INTAKE_RECORDS, _PROV, _ir  # noqa: F401
from nutrition.objects.intake.IntakeRecord import IntakeRecord  # noqa: F401
from nutrition.objects.intake.DailyIntakeMetric import DailyIntakeMetric  # noqa: F401
from nutrition.objects.intake.PeriodIntakeMetric import PeriodIntakeMetric  # noqa: F401
