# Microalgae (`microalgae`)

Photobioreactor decarbonization route.

**Kind:** polari-app · **agent tier:** member · **requires:** nothing

## Objects

`AlgaeReactorDefinition`, `AlgaeStrain`, `IntegratedLoopDefinition`, `MicroalgaeReactorAPI`

## Layout (the Standardized Polari App — see modules/README.md for what each entry means)

- **objects** — `objects/integrated/IntegratedLoopDefinition.py`, `objects/integrated/_shared.py`, `objects/reactor/AlgaeReactorDefinition.py`, `objects/reactor/AlgaeStrain.py`, `objects/reactor/_shared.py`
- **basis** — `integrated_basis.py`, `reactor_basis.py`
- **api** — `reactor_api.py`
- **seed** — `integrated_seed.py`, `reactor_seed.py`
- **custom** — `custom/integrated_analysis.py`, `custom/reactor_analysis.py`
- **selftests** — `integrated_selftest.py`, `reactor_selftest.py`

`polari-app.json` is the manifest the core reads; `objects/` holds one class per file; `custom/` holds code that fits no concept file.

## Selftest

```
pol modules selftest microalgae        # in the running backend
PYTHONPATH=.:modules python3 -m microalgae.integrated_selftest   # on the host, from polari-framework/
```

Conformance: `pol modules conform microalgae`

<!-- generated from polari-app.json by `pol modules manifests readme`; edit freely — the generator never overwrites a README without this marker -->
