# Computers (`computers`)

Computer assembly + use-case profiles as their own app (cmp-c): component taxonomy rows (declared specs + honest gaps), DFA-style assembly gates over the computerparts catalog, profiles as data with ai-6-shaped evidence-bearing fits (db-binding declare-only v1). Separable from the microchip ladder (chip-4 seam deferred).

**Kind:** polari-app · **agent tier:** member · **requires:** composition, computerparts

## Objects

`ComputerAssemblyDefinition`, `ComputerPartClassDefinition`, `ComputerProfileDefinition`, `ComputersAPI`, `InterconnectDefinition`

## Layout (the Standardized Polari App, postfix names)

- **basis** — `computers_basis.py`, `computers_ports_basis.py`
- **api** — `computers_api.py`
- **seed** — `computers_app_seed.py`, `computers_seed.py`
- **page** — `computers_page.py`
- **custom** — `custom/computers_fit.py`, `custom/computers_gates.py`
- **selftests** — `computers_selftest.py`

`polari-app.json` is the manifest the core reads; `custom/` holds code that fits no concept file.

## Pages

- `computers.computers_page:SEED_COMPUTERS_PAGE_DISPLAYS`

## Selftest

```
pol modules selftest computers        # in the running backend
PYTHONPATH=.:modules python3 -m computers.computers_selftest   # on the host, from polari-framework/
```

Conformance: `pol modules conform computers`
