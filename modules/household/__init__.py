"""
@module household

The HOUSEHOLD layer (HOUSEHOLD_APP_PLAN.md, hh-1): the people-side
objects and analyses the meal-logistics round (mlg-1..4) built and
that turned out to be household-generic — who is where and when
(PersonSchedule / SleepPreference), who does what share of which
work (HouseholdMember / WorkloadType / WorkDistributionPolicy /
WorkLedger), skills and safety bounding speed (SkillDefinition /
PersonSkill / MethodSkillRequirement / SafetyRule /
DurationObservation), dishes as the first non-cooking chore
(DishStrategy / HouseholdDishPolicy), and the allocation + fairness
readout over all of it.

hh-1 is a MOVE with names unchanged: live rows, TableDefinitions,
triggers and AnalysisDefinition callable refs converge through the
upsert path. `nutrition` requires this module and re-exports the
moved names from its old `logistics_*` homes, so every existing
importer keeps working. Chores / laundry / supplies arrive in hh-2+.
"""
