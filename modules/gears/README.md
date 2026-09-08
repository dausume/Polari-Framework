# Gears (`gears`)

Gear trains as data (GEARS_PLAN.md): the gear-type taxonomy with ratio laws + literature efficiency bands + how each type would be MADE in our stack, and the abstract kinematic solve over a shaft-node/mesh-edge graph (speeds with direction, torque after the efficiency chain, power conservation, accumulated backlash). Motor splice = gr-5.

**Kind:** polari-app · **agent tier:** member · **requires:** mathshapes

## Objects

`GearDefinition`, `GearMeshDefinition`, `GearTrainDefinition`, `GearTypeDefinition`, `GearVerificationRun`, `GearsAPI`, `ShaftNodeDefinition`

## Layout (the Standardized Polari App, postfix names)

- **basis** — `gear_basis.py`
- **api** — `gear_api.py`
- **seed** — `gear_scene_seed.py`, `gear_seed.py`
- **custom** — `custom/gear_kinematics.py`, `custom/gear_motor.py`, `custom/planetary.py`
- **selftests** — `gears_selftest.py`

`polari-app.json` is the manifest the core reads; `custom/` holds code that fits no concept file.

## Selftest

```
pol modules selftest gears        # in the running backend
PYTHONPATH=.:modules python3 -m gears.gears_selftest   # on the host, from polari-framework/
```

Conformance: `pol modules conform gears`
