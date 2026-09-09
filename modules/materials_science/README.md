# Materials Science (`materials_science`)

Legacy registry module (optional, toggleable).

**Kind:** library · **agent tier:** member · **requires:** nothing

## Objects

`AdditiveCompatibility`, `Compatibilizer`, `DataProvenance`, `DataSource`, `Formulation`, `FormulationComponent`, `FormulationIntent`, `Material`, `MaterialAdditive`, `MaterialProperty`, `MaterialPurpose`, `MaterialRelatedDevice`, `MaterialResolution`, `MaterialSourcing`, `PropertyEffect`, `PropertyTarget`, `PropertyValueSource`, `RawMaterial`, `ReferenceMaterial`, `TargetMaterialProfile`

## Layout (the Standardized Polari App — see modules/README.md for what each entry means)

- **objects** — `objects/material.py`, `objects/materialProperty.py`, `objects/materialPurpose.py`, `objects/materialRelatedDevice.py`, `objects/materialResolution.py`, `objects/dataProvenance/dataProvenance.py`, `objects/dataProvenance/dataSource.py`, `objects/devices/deviceCategory.py`, `objects/devices/cncLathes/cncLathe.py`, `objects/devices/cncMills/cncMill.py`, `objects/devices/cncMills/fiveAxisMill.py`, `objects/devices/cncMills/threeAxisMill.py`, … (104 more)
- **basis** — `materials_science_basis.py`
- **seed** — `materials_science_data_seed.py`
- **custom** — `custom/registerMaterialsScienceModule.py`
- **selftests** — `materials_science_selftest.py`
- **initialData/** — module-initial-data/1 rows (non-regenerable data only)

`polari-app.json` is the manifest the core reads; `objects/` holds one class per file; `custom/` holds code that fits no concept file.

## Selftest

```
pol modules selftest materials_science        # in the running backend
PYTHONPATH=.:modules python3 -m materials_science.materials_science_selftest   # on the host, from polari-framework/
```

Conformance: `pol modules conform materials_science`

<!-- generated from polari-app.json by `pol modules manifests readme`; edit freely — the generator never overwrites a README without this marker -->
