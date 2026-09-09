# Electrodevice (`electrodevice`)

Material-derived electronic devices, SPICE cards, circuits/breadboards as rows.

**Kind:** polari-app · **agent tier:** member · **requires:** hwdigital

## Objects

`BoardJumper`, `BreadboardAPI`, `BreadboardDefinition`, `CircuitComponentDefinition`, `CircuitDefinition`, `CircuitNetDefinition`, `CircuitRowsAPI`, `CircuitRunResult`, `ComponentPlacement`, `DeviceValidationReport`, `ElectroDeviceAPI`, `ElectronicDeviceDefinition`, `PhotoAbsorberDefinition`, `PinBindingDefinition`, `SemiconductorProfile`, `SolarLayerDefinition`, `SolarStackDefinition`, `SpiceModelCard`

## Layout (the Standardized Polari App — see modules/README.md for what each entry means)

- **objects** — `objects/breadboard/BoardJumper.py`, `objects/breadboard/BreadboardDefinition.py`, `objects/breadboard/ComponentPlacement.py`, `objects/breadboard/_shared.py`, `objects/circuit/CircuitComponentDefinition.py`, `objects/circuit/CircuitDefinition.py`, `objects/circuit/CircuitNetDefinition.py`, `objects/circuit/_shared.py`, `objects/device/CircuitRunResult.py`, `objects/device/ElectronicDeviceDefinition.py`, `objects/device/SpiceModelCard.py`, `objects/device/_shared.py`, … (10 more)
- **basis** — `breadboard_basis.py`, `circuit_basis.py`, `device_basis.py`, `device_validator_basis.py`, `level_bridge_basis.py`, `photo_basis.py`, `semiconductor_basis.py`
- **api** — `circuit_api.py`, `device_api.py`
- **seed** — `breadboard_netlist_seed.py`, `circuit_netlist_seed.py`
- **custom** — `custom/device_derive.py`, `custom/photo_derive.py`, `custom/spice_run.py`, `custom/switching.py`
- **selftests** — `breadboard_selftest.py`, `circuit_rows_selftest.py`, `electrodevice_selftest.py`, `level_bridge_selftest.py`

`polari-app.json` is the manifest the core reads; `objects/` holds one class per file; `custom/` holds code that fits no concept file.

## Selftest

```
pol modules selftest electrodevice        # in the running backend
PYTHONPATH=.:modules python3 -m electrodevice.breadboard_selftest   # on the host, from polari-framework/
```

Conformance: `pol modules conform electrodevice`

<!-- generated from polari-app.json by `pol modules manifests readme`; edit freely — the generator never overwrites a README without this marker -->
