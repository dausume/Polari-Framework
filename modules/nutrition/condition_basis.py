"""
@cross-cutting
@module nutrition.condition_basis
@tags @xc:bindings

mpb-2 — stated-condition comfort steering as data (Dustin,
ratified 2026-09-01 verbatim: "we should not be doing diagnosis in
any way, what we can say is 'try to make meals that do not make
this condition worse'"):

  StatedCondition     one person's OWN declaration ("I have
                      reflux") — stated, never inferred, never
                      diagnosed here. The row exists so meals can
                      be steered AWAY from that condition's known
                      aggravators; nothing more.
  ConditionSteering   one condition → the EXISTING evidence rows
                      (nmp-2 tolerance substances) that count as
                      its aggravators, plus plain-language
                      guidance and the citation the mapping rests
                      on. Rows, not code — new conditions are new
                      rows.

THE POSTURE (rides every payload): steering only — "try to make
meals that do not make this condition worse". No diagnosis, no
treatment, no magnitude claims (fsp D6); a clinician's numbers
always win (PersonThreshold overrides carry them).

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - nutrition.custom.condition_analysis, mealplanning_api
@see AI-Notes/plans/MEAL_PLANNING_APP_PLAN.md §3b mpb-2
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/condition/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

from objectTreeDecorators import treeObject, treeObjectInit

from nutrition.objects.condition._shared import POSTURE, SEED_CONDITION_STEERINGS, SEED_STATED_CONDITIONS, _PROV, _steer  # noqa: F401
from nutrition.objects.condition.StatedCondition import StatedCondition  # noqa: F401
from nutrition.objects.condition.ConditionSteering import ConditionSteering  # noqa: F401
