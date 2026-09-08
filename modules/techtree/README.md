# Techtree (`techtree`)

Tech trees with theory/real/business/politics segments; OSEB baseline rollup.

**Kind:** polari-app · **agent tier:** member · **requires:** nothing

## Objects

`BusinessModelDefinition`, `BusinessOutcome`, `PolicyDefinition`, `RealArtifact`, `TechDependencyEdge`, `TechNode`, `TechSegment`, `TechSegmentAssignment`, `TechTreeAPI`, `TechTreeDefinition`

## Layout (the Standardized Polari App, postfix names)

- **basis** — `techtree_basis.py`, `techtree_content_basis.py`
- **api** — `techtree_api.py`
- **seed** — `techtree_seed.py`
- **custom** — `custom/techtree_analysis.py`, `custom/wire_ladder.py`
- **selftests** — `techtree_selftest.py`

`polari-app.json` is the manifest the core reads; `custom/` holds code that fits no concept file.

## Selftest

```
pol modules selftest techtree        # in the running backend
PYTHONPATH=.:modules python3 -m techtree.techtree_selftest   # on the host, from polari-framework/
```

Conformance: `pol modules conform techtree`
