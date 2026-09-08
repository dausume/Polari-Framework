# Computerparts (`computerparts`)

Computer parts + builds as tracked data (ai-8): dated part prices, derived build cost, assembly-feasibility checks over declared specs; feeds the appstore buy-vs-rent advisory (row reads). Seeding imports composition.custom.seed_upsert (guarded) — prices converge on live rows.

**Kind:** polari-app · **agent tier:** member · **requires:** composition

## Objects

`ComputerBuildDefinition`, `ComputerPartDefinition`, `ComputerPartsAPI`

## Layout (the Standardized Polari App, postfix names)

- **basis** — `parts_basis.py`
- **api** — `parts_api.py`
- **seed** — `parts_seed.py`
- **custom** — `custom/parts_assembly.py`
- **selftests** — `computerparts_selftest.py`

`polari-app.json` is the manifest the core reads; `custom/` holds code that fits no concept file.

## Selftest

```
pol modules selftest computerparts        # in the running backend
PYTHONPATH=.:modules python3 -m computerparts.computerparts_selftest   # on the host, from polari-framework/
```

Conformance: `pol modules conform computerparts`
