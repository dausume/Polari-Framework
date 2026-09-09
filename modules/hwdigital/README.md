# Hwdigital (`hwdigital`)

Logic diagrams as rows -> generated artifacts (iCE40 bitstreams).

**Kind:** polari-app · **agent tier:** member · **requires:** nothing

## Objects

`LogicBlockDesign`, `LogicBlockNode`, `LogicDesignAPI`

## Layout (the Standardized Polari App — see modules/README.md for what each entry means)

- **objects** — `objects/logic/LogicBlockDesign.py`, `objects/logic/LogicBlockNode.py`, `objects/logic/_shared.py`
- **basis** — `logic_basis.py`
- **api** — `logic_api.py`
- **seed** — `logic_compile_seed.py`
- **custom** — `custom/logic_sim.py`, `custom/logic_verilog.py`
- **selftests** — `logic_selftest.py`

`polari-app.json` is the manifest the core reads; `objects/` holds one class per file; `custom/` holds code that fits no concept file.

## Selftest

```
pol modules selftest hwdigital        # in the running backend
PYTHONPATH=.:modules python3 -m hwdigital.logic_selftest   # on the host, from polari-framework/
```

Conformance: `pol modules conform hwdigital`

<!-- generated from polari-app.json by `pol modules manifests readme`; edit freely — the generator never overwrites a README without this marker -->
