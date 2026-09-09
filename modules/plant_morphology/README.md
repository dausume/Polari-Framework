# Plant Morphology (`plant_morphology`)

3D organ + root stand-in models, confinement/dwarfing assessment.

**Kind:** polari-app · **agent tier:** member · **requires:** nothing

## Objects

`OrganModel`, `PlantMorphologyAPI`, `RootSystemModel`

## Layout (the Standardized Polari App — see modules/README.md for what each entry means)

- **objects** — `objects/organ/OrganModel.py`, `objects/organ/RootSystemModel.py`, `objects/organ/_shared.py`
- **basis** — `organ_basis.py`
- **api** — `morphology_api.py`
- **seed** — `morphology_seed.py`
- **custom** — `custom/morphology_analysis.py`
- **selftests** — `morphology_selftest.py`

`polari-app.json` is the manifest the core reads; `objects/` holds one class per file; `custom/` holds code that fits no concept file.

## Selftest

```
pol modules selftest plant_morphology        # in the running backend
PYTHONPATH=.:modules python3 -m plant_morphology.morphology_selftest   # on the host, from polari-framework/
```

Conformance: `pol modules conform plant_morphology`

<!-- generated from polari-app.json by `pol modules manifests readme`; edit freely — the generator never overwrites a README without this marker -->
