# Islemesh (`islemesh`)

isle-mesh convergence (mac-1): the polari-side acceptor for isle-mesh data — devices/uplinks/mesh-apps/protocol-permits ingested from the isle agent's registry.json + nginx fragments (isle stays authoritative over networking); mock ingests carry mock_network=true, surfaced as a banner. Feeds /display/isle-mesh and the mac-10 console.

**Kind:** polari-app · **agent tier:** member · **requires:** nothing

**Catalog kinds this module adds:** ai-tool, mesh-app, polari-app, polari-app-option, polari-instance

## Objects

`IsleApp`, `IsleAppService`, `IsleCatalogEntry`, `IsleDevice`, `IsleEngine`, `IsleIngestReceipt`, `IsleMeshAPI`, `IsleProtocolPermit`, `IsleUplink`, `MeshAppRealization`

## Layout (the Standardized Polari App — see modules/README.md for what each entry means)

- **objects** — `objects/islemesh/IsleApp.py`, `objects/islemesh/IsleAppService.py`, `objects/islemesh/IsleCatalogEntry.py`, `objects/islemesh/IsleDevice.py`, `objects/islemesh/IsleEngine.py`, `objects/islemesh/IsleIngestReceipt.py`, `objects/islemesh/IsleProtocolPermit.py`, `objects/islemesh/IsleUplink.py`, `objects/islemesh/MeshAppRealization.py`
- **basis** — `islemesh_basis.py`
- **api** — `islemesh_api.py`
- **page** — `islemesh_page.py`
- **catalog** — `islemesh_catalog.py`
- **custom** — `custom/islemesh_coherence.py`, `custom/islemesh_constants.py`, `custom/islemesh_engines.py`, `custom/islemesh_mock.py`, `custom/islemesh_netledger.py`, `custom/islemesh_parse.py`
- **selftests** — `islemesh_selftest.py`

`polari-app.json` is the manifest the core reads; `objects/` holds one class per file; `custom/` holds code that fits no concept file.

## Pages

- `islemesh.islemesh_page:SEED_ISLEMESH_PAGE_DISPLAYS`

## Selftest

```
pol modules selftest islemesh        # in the running backend
PYTHONPATH=.:modules python3 -m islemesh.islemesh_selftest   # on the host, from polari-framework/
```

Conformance: `pol modules conform islemesh`

<!-- generated from polari-app.json by `pol modules manifests readme`; edit freely — the generator never overwrites a README without this marker -->

## Concurrency and persistence truth (handoff 2026-11-09, item B)

All islemesh writers serialize on `islemesh.custom.islemesh_engines.MUTATION_LOCK`: the ingest doors
(registry / fragments / device / engine) and the mock seeder hold it for their whole
replace+insert+dedup+receipt sequence; `sync_from_registry` holds it for its apply phase only (the
registry fetch runs outside it, so a slow core never stalls ingests). Readers do not take it. Pops
tolerate a key that vanished between snapshot and pop. The registry / fragments / device doors (and
retire) answer `500 ok:false persisted:false` with words and counts when a save was refused or raised
or a delete could not be performed, so the sender retries instead of trusting a receipt for rows that
vanish or return on restart. `ingest/engine` reports persistence through its own `_TrackedSave`
(`persisted:false` + 500) as before; the mock seeder is development seeding and is not tracked. A
healthy database (every Isle* table present, `saveInstanceInDB` True) answers exactly as before; a
missing table makes `saveInstanceInDB` return False and IS reported as not persisted, by design.
Not covered here: the admission worker's table restore runs on its own thread in the manager; the
tolerant pops keep an overlap from crashing, true serialization of restore against ingest is a
manager follow-up. Regression controls: `islemesh_ingest_concurrency_selftest`.
