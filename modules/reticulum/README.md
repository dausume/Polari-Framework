# Reticulum (`reticulum`)

Reticulum mesh transport (ret-1, RETICULUM_TRANSPORT_PLAN): identities/destinations/interfaces/bindings as rows, per-PATH link measurements, ledgered airtime budgets, .arch archipelago with GRADED trust, parent+child state replication, operator-licence assertions + device links. RNS stack lives ONLY in the pol-reticulum sidecar, pinned rns==0.9.4+lxmf==0.6.3 (RETICULUM_LICENCE_GATE.md — pins are licence pins). THE LINE (ret-8): nothing arriving over Reticulum mutates Polari state. Third module born manifest-first on dyn-1.

**Kind:** hardware-extension-app · **agent tier:** hardware · **requires:** islemesh

## Objects

`AirtimeBudget`, `AppArchExposure`, `AppDataRule`, `ArchipelagoNode`, `ArchipelagoTrust`, `DeviceLink`, `DeviceModel`, `KitProfile`, `LinkMeasurement`, `MeshAppRelay`, `MeshConsumer`, `MeshSimNode`, `MeshSimResult`, `MeshSimScenario`, `ObjectStateVersion`, `OperatorLicense`, `PeerSighting`, `QuarantinedSubmission`, `ReticulumAPI`, `ReticulumDestination`, `ReticulumIdentity`, `ReticulumInterface`, `StateConflict`, `TransportBinding`, `WatchedObject`

## Layout (the Standardized Polari App — see modules/README.md for what each entry means)

- **objects** — `objects/arch/ArchipelagoNode.py`, `objects/arch/ArchipelagoTrust.py`, `objects/arch/_shared.py`, `objects/datarule/AppDataRule.py`, `objects/datarule/QuarantinedSubmission.py`, `objects/datarule/_shared.py`, `objects/device_catalog/DeviceModel.py`, `objects/device_catalog/_shared.py`, `objects/discovery/PeerSighting.py`, `objects/discovery/_shared.py`, `objects/meshapp/AppArchExposure.py`, `objects/meshapp/KitProfile.py`, … (21 more)
- **basis** — `arch_basis.py`, `datarule_basis.py`, `device_catalog_basis.py`, `discovery_basis.py`, `meshapp_basis.py`, `meshsim_basis.py`, `operator_basis.py`, `replication_basis.py`, `reticulum_basis.py`
- **api** — `reticulum_api.py`
- **remote** — `rns_remote.py`
- **custom** — `custom/arch_topology.py`, `custom/meshsim_placement.py`
- **selftests** — `reticulum_selftest.py`

`polari-app.json` is the manifest the core reads; `objects/` holds one class per file; `custom/` holds code that fits no concept file.

## Selftest

```
pol modules selftest reticulum        # in the running backend
PYTHONPATH=.:modules python3 -m reticulum.reticulum_selftest   # on the host, from polari-framework/
```

Conformance: `pol modules conform reticulum`

<!-- generated from polari-app.json by `pol modules manifests readme`; edit freely — the generator never overwrites a README without this marker -->
