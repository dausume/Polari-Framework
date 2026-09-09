# Meshassets (`meshassets`)

License-GATED external mesh catalog: verified open-source 3D assets as pointers (never vendored bytes), graded by what the licence actually permits (simulate vs redistribute), plus the fit engine that scales a borrowed mesh onto our vector organ definitions and MEASURES the compromise (shape fidelity). Gears are flagged approximation-invalid: an approximate gear does not mesh.

**Kind:** polari-app · **agent tier:** member · **requires:** plant_morphology

## Objects

`MeshAssetReference`, `MeshAssetSource`, `MeshAssetsAPI`, `OrganMeshChoice`

## Layout (the Standardized Polari App, postfix names)

- **basis** — `mesh_asset_basis.py`
- **api** — `mesh_asset_api.py`
- **seed** — `mesh_asset_seed.py`
- **custom** — `custom/mesh_fit.py`
- **selftests** — `meshassets_selftest.py`

`polari-app.json` is the manifest the core reads; `custom/` holds code that fits no concept file.

## Selftest

```
pol modules selftest meshassets        # in the running backend
PYTHONPATH=.:modules python3 -m meshassets.meshassets_selftest   # on the host, from polari-framework/
```

Conformance: `pol modules conform meshassets`

<!-- generated from polari-app.json by `pol modules manifests readme`; edit freely — the generator never overwrites a README without this marker -->
