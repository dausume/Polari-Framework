# Supplychain (`supplychain`)

Unifying bio supply-chain ledger — materials + food + carbon accounting.

**Kind:** polari-app · **agent tier:** member · **requires:** nothing

## Objects

`PriceCitation`, `ProductFormula`, `ProductInputRequirement`, `SourcePreferencePolicy`, `SourcingAPI`, `SupplyChainAPI`, `SupplyChainDefinition`, `SupplyFlow`, `SupplyNode`, `SupplySourceProfile`

## Layout (the Standardized Polari App, postfix names)

- **basis** — `chain_basis.py`, `sourcing_basis.py`
- **api** — `chain_api.py`, `sourcing_api.py`
- **seed** — `chain_seed.py`, `magnetic_sourcing_seed.py`, `sourcing_seed.py`
- **custom** — `custom/chain_analysis.py`, `custom/formula_analysis.py`, `custom/mold_analysis.py`, `custom/reclaim_analysis.py`, `custom/sourcing_analysis.py`
- **selftests** — `chain_selftest.py`, `formulas_selftest.py`, `magnetic_sourcing_selftest.py`, `molds_selftest.py`, `reclaim_selftest.py`, `sourcing_selftest.py`

`polari-app.json` is the manifest the core reads; `custom/` holds code that fits no concept file.

## Selftest

```
pol modules selftest supplychain        # in the running backend
PYTHONPATH=.:modules python3 -m supplychain.chain_selftest   # on the host, from polari-framework/
```

Conformance: `pol modules conform supplychain`

<!-- generated from polari-app.json by `pol modules manifests readme`; edit freely — the generator never overwrites a README without this marker -->
