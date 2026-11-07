# Topology (`topology`)

The Polari topology layer: which instances run which modules on which machines, their dependency edges, engine bindings and service connections. Describes itself at boot (tpl-0/1) and works with or without an isle; GET /api/topology/isle-needs says which features need one (tpl-4). AI-Notes/plans/TOPOLOGY_LAYERS_PLAN.md.

**Kind:** polari-app · **agent tier:** core · **requires:** nothing

## Objects

`EngineProviderBinding`, `EngineUsageWindow`, `EnginesAPI`, `InstanceDefinition`, `IntegrationPing`, `ModuleAssignment`, `ModuleDependencyEdge`, `MoveOperation`, `OrchestrationTarget`, `PolariNodeMachine`, `ServiceConnection`, `TopologyAPI`, `TopologyDefinition`, `TopologyObservation`, `TopologyTestRun`, `TopologyTestingAPI`

## Layout (the Standardized Polari App — see modules/README.md for what each entry means)

- **basis** — `topology_basis.py`
- **api** — `engines_api.py`, `topology_api.py`, `topology_testing_api.py`
- **seed** — `topology_seed.py`
- **selftests** — `selftest_engines.py`, `selftest_module_graph.py`, `selftest_move_operations.py`, `selftest_testing.py`, `selftest_topology.py`, `selftest_topology_self.py`
- **other** — `baseline_profile.py`, `device_resources.py`, `engine_metering.py`, `module_move_live.py`, `move_operations.py`, `object_ownership.py`, `placement_truth.py`, `provider_registry.py`, `test_isle_resource_reports.py`, `topology_analysis.py`, `topology_constants.py`, `topology_io.py`, … (7 more)

`polari-app.json` describes the package. Topology is a CORE package at the framework root (always loaded; `module_gating.CORE_PACKAGES`) and keeps its legacy layout: its classes live in `topology_basis.py` / `topology_modules.py` / `topology_state.py` rather than `objects/`, and its helpers carry no concept postfix rather than sitting in `custom/`. `pol modules conform topology` reports exactly that naming drift; moving the files is a separate change.

## Selftest

```
pol modules selftest topology        # in the running backend
PYTHONPATH=.:modules python3 -m topology.selftest_engines   # on the host, from polari-framework/
```

Conformance: `pol modules conform topology`

<!-- generated from polari-app.json by `pol modules manifests readme`; edit freely — the generator never overwrites a README without this marker -->
