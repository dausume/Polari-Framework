# Reticulum (`reticulum`)

Reticulum mesh transport (ret-1, RETICULUM_TRANSPORT_PLAN): identities/destinations/interfaces/bindings as rows, per-PATH link measurements, ledgered airtime budgets, .arch archipelago with GRADED trust, parent+child state replication, operator-licence assertions + device links. RNS stack lives ONLY in the pol-reticulum sidecar, pinned rns==0.9.4+lxmf==0.6.3 (RETICULUM_LICENCE_GATE.md — pins are licence pins). THE LINE (ret-8): nothing arriving over Reticulum mutates Polari state. Third module born manifest-first on dyn-1.

**Kind:** polari-app · **agent tier:** member · **requires:** nothing

## Objects

`AirtimeBudget`, `AppArchExposure`, `AppDataRule`, `ArchipelagoNode`, `ArchipelagoTrust`, `DeviceLink`, `DeviceModel`, `KitProfile`, `LinkMeasurement`, `MeshAppRelay`, `MeshConsumer`, `MeshSimNode`, `MeshSimResult`, `MeshSimScenario`, `ObjectStateVersion`, `OperatorLicense`, `PeerSighting`, `QuarantinedSubmission`, `ReticulumAPI`, `ReticulumDestination`, `ReticulumIdentity`, `ReticulumInterface`, `StateConflict`, `TransportBinding`, `WatchedObject`

## Layout (the Standardized Polari App, postfix names)

- **basis** — `arch_basis.py`, `datarule_basis.py`, `device_catalog_basis.py`, `discovery_basis.py`, `meshapp_basis.py`, `meshsim_basis.py`, `operator_basis.py`, `replication_basis.py`, `reticulum_basis.py`
- **api** — `reticulum_api.py`
- **remote** — `rns_remote.py`
- **custom** — `custom/arch_topology.py`, `custom/meshsim_placement.py`
- **selftests** — `reticulum_selftest.py`

`polari-app.json` is the manifest the core reads; `custom/` holds code that fits no concept file.

## Selftest

```
pol modules selftest reticulum        # in the running backend
PYTHONPATH=.:modules python3 -m reticulum.reticulum_selftest   # on the host, from polari-framework/
```

Conformance: `pol modules conform reticulum`
