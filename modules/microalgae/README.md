# Microalgae (`microalgae`)

Photobioreactor decarbonization route.

**Kind:** polari-app · **agent tier:** member · **requires:** nothing

## Objects

`AlgaeReactorDefinition`, `AlgaeStrain`, `IntegratedLoopDefinition`, `MicroalgaeReactorAPI`

## Layout (the Standardized Polari App, postfix names)

- **basis** — `integrated_basis.py`, `reactor_basis.py`
- **api** — `reactor_api.py`
- **seed** — `integrated_seed.py`, `reactor_seed.py`
- **custom** — `custom/integrated_analysis.py`, `custom/reactor_analysis.py`
- **selftests** — `integrated_selftest.py`, `reactor_selftest.py`

`polari-app.json` is the manifest the core reads; `custom/` holds code that fits no concept file.

## Selftest

```
pol modules selftest microalgae        # in the running backend
PYTHONPATH=.:modules python3 -m microalgae.integrated_selftest   # on the host, from polari-framework/
```

Conformance: `pol modules conform microalgae`

<!-- generated from polari-app.json by `pol modules manifests readme`; edit freely — the generator never overwrites a README without this marker -->
