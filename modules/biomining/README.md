# Biomining (`biomining`)

Bacteria/algae extraction -> product variants.

**Kind:** polari-app · **agent tier:** member · **requires:** nothing

## Objects

`BioextractionAgent`, `BiomineAPI`, `BiomineSystemDefinition`, `BiomineralProduct`

## Layout (the Standardized Polari App — see modules/README.md for what each entry means)

- **objects** — `objects/biomining/BioextractionAgent.py`, `objects/biomining/BiomineSystemDefinition.py`, `objects/biomining/BiomineralProduct.py`, `objects/biomining/_shared.py`
- **basis** — `biomining_basis.py`
- **api** — `biomining_api.py`
- **seed** — `alloy_seed.py`, `biomining_seed.py`, `optical_seed.py`
- **custom** — `custom/biomining_analysis.py`
- **selftests** — `biomining_selftest.py`

`polari-app.json` is the manifest the core reads; `objects/` holds one class per file; `custom/` holds code that fits no concept file.

## Selftest

```
pol modules selftest biomining        # in the running backend
PYTHONPATH=.:modules python3 -m biomining.biomining_selftest   # on the host, from polari-framework/
```

Conformance: `pol modules conform biomining`

<!-- generated from polari-app.json by `pol modules manifests readme`; edit freely — the generator never overwrites a README without this marker -->
