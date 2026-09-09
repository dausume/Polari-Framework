# Composition (`composition`)

Part composition (PART_ARCHETYPES_PLAN.md): components/interfaces with DERIVED levels by separability, promotion as a recorded operation, EBOM/MBOM split, archetypes + design matrices, and the generic role engine (extracted from motors). Material/equation refs are DATA references, never imports.

**Kind:** polari-app · **agent tier:** member · **requires:** mathshapes, techtree

## Objects

`CompositionAPI`, `CompositionNode`, `ConstructionVariantDefinition`, `DesignMatrixDefinition`, `FailureModeDefinition`, `FunctionalPartDefinition`, `InterfaceDefinition`, `PartArchetypeDefinition`, `PartComponentDefinition`, `RoutingDefinition`, `RoutingOperation`

## Layout (the Standardized Polari App — see modules/README.md for what each entry means)

- **objects** — `objects/archetype/PartArchetypeDefinition.py`, `objects/archetype/_shared.py`, `objects/component/PartComponentDefinition.py`, `objects/design_matrix/DesignMatrixDefinition.py`, `objects/design_matrix/_shared.py`, `objects/failure_modes/FailureModeDefinition.py`, `objects/failure_modes/_shared.py`, `objects/functional/ConstructionVariantDefinition.py`, `objects/functional/FunctionalPartDefinition.py`, `objects/functional/_shared.py`, `objects/interface/InterfaceDefinition.py`, `objects/interface/_shared.py`, … (5 more)
- **basis** — `archetype_basis.py`, `component_basis.py`, `design_matrix_basis.py`, `failure_modes_basis.py`, `functional_basis.py`, `interface_basis.py`, `node_basis.py`, `routing_basis.py`
- **api** — `composition_api.py`
- **seed** — `composition_seed.py`
- **custom** — `custom/data_refs.py`, `custom/fill_models.py`, `custom/part_roles.py`, `custom/realization.py`, `custom/seed_upsert.py`
- **selftests** — `composition_selftest.py`

`polari-app.json` is the manifest the core reads; `objects/` holds one class per file; `custom/` holds code that fits no concept file.

## Selftest

```
pol modules selftest composition        # in the running backend
PYTHONPATH=.:modules python3 -m composition.composition_selftest   # on the host, from polari-framework/
```

Conformance: `pol modules conform composition`

<!-- generated from polari-app.json by `pol modules manifests readme`; edit freely — the generator never overwrites a README without this marker -->
