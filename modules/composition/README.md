# Composition (`composition`)

Part composition (PART_ARCHETYPES_PLAN.md): components/interfaces with DERIVED levels by separability, promotion as a recorded operation, EBOM/MBOM split, archetypes + design matrices, and the generic role engine (extracted from motors). Material/equation refs are DATA references, never imports.

**Kind:** polari-app · **agent tier:** member · **requires:** mathshapes, techtree

## Objects

`CompositionAPI`, `CompositionNode`, `ConstructionVariantDefinition`, `DesignMatrixDefinition`, `FailureModeDefinition`, `FunctionalPartDefinition`, `InterfaceDefinition`, `PartArchetypeDefinition`, `PartComponentDefinition`, `RoutingDefinition`, `RoutingOperation`

## Layout (the Standardized Polari App, postfix names)

- **basis** — `archetype_basis.py`, `component_basis.py`, `design_matrix_basis.py`, `failure_modes_basis.py`, `functional_basis.py`, `interface_basis.py`, `node_basis.py`, `routing_basis.py`
- **api** — `composition_api.py`
- **seed** — `composition_seed.py`
- **custom** — `custom/data_refs.py`, `custom/fill_models.py`, `custom/part_roles.py`, `custom/realization.py`, `custom/seed_upsert.py`
- **selftests** — `composition_selftest.py`

`polari-app.json` is the manifest the core reads; `custom/` holds code that fits no concept file.

## Selftest

```
pol modules selftest composition        # in the running backend
PYTHONPATH=.:modules python3 -m composition.composition_selftest   # on the host, from polari-framework/
```

Conformance: `pol modules conform composition`
