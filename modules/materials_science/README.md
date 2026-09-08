# Materials Science (`materials_science`)

Legacy registry module (optional, toggleable).

**Kind:** library · **agent tier:** member · **requires:** nothing

## Objects

`Material`, `MaterialProperty`, `MaterialPurpose`, `MaterialRelatedDevice`, `MaterialResolution`

## Layout (the Standardized Polari App, postfix names)

- **basis** — `materialProperty_basis.py`, `materialPurpose_basis.py`, `materialRelatedDevice_basis.py`, `materialResolution_basis.py`, `material_basis.py`
- **seed** — `materials_science_data_seed.py`
- **custom** — `custom/registerMaterialsScienceModule.py`
- **initialData/** — module-initial-data/1 rows (non-regenerable data only)

`polari-app.json` is the manifest the core reads; `custom/` holds code that fits no concept file.

## Selftest

```
pol modules selftest materials_science        # in the running backend
PYTHONPATH=.:modules python3 -m materials_science.<none yet>   # on the host, from polari-framework/
```

Conformance: `pol modules conform materials_science`
