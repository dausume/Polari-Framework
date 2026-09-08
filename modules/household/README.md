# Household (`household`)

Household layer: people's schedules and sleep, members and work shares, skills and safety, dish strategies, the allocation and fairness

**Kind:** library · **agent tier:** member · **requires:** nothing

## Objects

`DishStrategy`, `DurationObservation`, `HouseholdDishPolicy`, `HouseholdMember`, `MethodSkillRequirement`, `PersonSchedule`, `PersonSkill`, `SafetyRule`, `SkillDefinition`, `SleepPreference`, `WorkDistributionPolicy`, `WorkLedger`, `WorkloadType`

## Layout (the Standardized Polari App, postfix names)

- **basis** — `household_basis.py`
- **custom** — `custom/household_analysis.py`
- **selftests** — `household_selftest.py`

`polari-app.json` is the manifest the core reads; `custom/` holds code that fits no concept file.

## Selftest

```
pol modules selftest household        # in the running backend
PYTHONPATH=.:modules python3 -m household.household_selftest   # on the host, from polari-framework/
```

Conformance: `pol modules conform household`
