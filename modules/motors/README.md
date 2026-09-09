# Motors (`motors`)

Electric motors Section C: the M0-M3 ladder of buildable samples (Lavet clock stepper -> reluctance -> ferrite-PM -> dual-stator axial flux), clock control-case sim, torque curves, torque_parity (MAGNETIC_MATERIALS_PLAN.md).

**Kind:** polari-app · **agent tier:** member · **requires:** composition, magnetics

## Objects

`ClockScaleDefinition`, `ClockSceneLayerDefinition`, `ClockViewDefinition`, `CrucibleHoistRequirement`, `MotorControllerProfile`, `MotorDesignDefinition`, `MotorGoalSpec`, `MotorPartDefinition`, `MotorVerificationRun`, `MotorsAPI`, `PhaseBindingDefinition`, `PrinterAxisRequirement`

## Layout (the Standardized Polari App — see modules/README.md for what each entry means)

- **objects** — `objects/clock_scene/ClockSceneLayerDefinition.py`, `objects/clock_scene/_shared.py`, `objects/clock_views/ClockViewDefinition.py`, `objects/clock_views/_shared.py`, `objects/m1_positioning/PrinterAxisRequirement.py`, `objects/m1_positioning/_shared.py`, `objects/m2_lift/CrucibleHoistRequirement.py`, `objects/m2_lift/_shared.py`, `objects/motor/MotorDesignDefinition.py`, `objects/motor/MotorVerificationRun.py`, `objects/motor/_shared.py`, `objects/motor_drive/MotorControllerProfile.py`, … (7 more)
- **basis** — `clock_scene_basis.py`, `clock_views_basis.py`, `m1_positioning_basis.py`, `m2_lift_basis.py`, `motor_basis.py`, `motor_drive_basis.py`, `motor_parts_basis.py`, `scale_goals_basis.py`
- **api** — `motor_api.py`
- **seed** — `clock_assembly_seed.py`, `m1_composition_seed.py`, `m1_product_seed.py`, `m1_relations_seed.py`, `m1_scene_seed.py`, `m1_views_seed.py`, `m2_composition_seed.py`, `m2_product_seed.py`, `m2_scene_seed.py`, `m2_views_seed.py`, `motor_shapes_seed.py`, `physics_equations_seed.py`, … (1 more)
- **page** — `motors_page.py`
- **custom** — `custom/bench_campaign.py`, `custom/clock_product.py`, `custom/composition_splice.py`, `custom/contact_wear.py`, `custom/distributed_traction.py`, `custom/inductance.py`, `custom/lifecycle_cost.py`, `custom/local_route.py`, `custom/m1_sequencing.py`, `custom/m2_rotation.py`, `custom/materials_audit.py`, `custom/motor_designer.py`, … (9 more)
- **selftests** — `m1_selftest.py`, `m2_selftest.py`, `motors_selftest.py`

`polari-app.json` is the manifest the core reads; `objects/` holds one class per file; `custom/` holds code that fits no concept file.

## Pages

- `motors.motors_page:SEED_MOTOR_PAGE_DISPLAYS`

## Selftest

```
pol modules selftest motors        # in the running backend
PYTHONPATH=.:modules python3 -m motors.m1_selftest   # on the host, from polari-framework/
```

Conformance: `pol modules conform motors`

<!-- generated from polari-app.json by `pol modules manifests readme`; edit freely — the generator never overwrites a README without this marker -->
