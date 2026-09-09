# Household (`household`)

Household layer: people's schedules and sleep, members and work shares, skills and safety, dish strategies, the allocation and fairness

**Kind:** library · **agent tier:** member · **requires:** nothing

## Objects

`DishStrategy`, `DurationObservation`, `HouseholdDishPolicy`, `HouseholdMember`, `MethodSkillRequirement`, `PersonSchedule`, `PersonSkill`, `SafetyRule`, `SkillDefinition`, `SleepPreference`, `WorkDistributionPolicy`, `WorkLedger`, `WorkloadType`

## Layout (the Standardized Polari App — see modules/README.md for what each entry means)

- **objects** — `objects/household/DishStrategy.py`, `objects/household/DurationObservation.py`, `objects/household/HouseholdDishPolicy.py`, `objects/household/HouseholdMember.py`, `objects/household/MethodSkillRequirement.py`, `objects/household/PersonSchedule.py`, `objects/household/PersonSkill.py`, `objects/household/SafetyRule.py`, `objects/household/SkillDefinition.py`, `objects/household/SleepPreference.py`, `objects/household/WorkDistributionPolicy.py`, `objects/household/WorkLedger.py`, … (2 more)
- **basis** — `household_basis.py`
- **custom** — `custom/household_analysis.py`
- **selftests** — `household_selftest.py`

`polari-app.json` is the manifest the core reads; `objects/` holds one class per file; `custom/` holds code that fits no concept file.

## Selftest

```
pol modules selftest household        # in the running backend
PYTHONPATH=.:modules python3 -m household.household_selftest   # on the host, from polari-framework/
```

Conformance: `pol modules conform household`

<!-- generated from polari-app.json by `pol modules manifests readme`; edit freely — the generator never overwrites a README without this marker -->
