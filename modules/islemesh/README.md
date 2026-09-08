# Islemesh (`islemesh`)

isle-mesh convergence (mac-1): the polari-side acceptor for isle-mesh data — devices/uplinks/mesh-apps/protocol-permits ingested from the isle agent's registry.json + nginx fragments (isle stays authoritative over networking); mock ingests carry mock_network=true, surfaced as a banner. Feeds /display/isle-mesh and the mac-10 console.

**Kind:** polari-app · **agent tier:** member · **requires:** nothing

**Catalog kinds this module adds:** ai-tool, mesh-app, polari-app, polari-app-option, polari-instance

## Objects

`IsleApp`, `IsleAppService`, `IsleCatalogEntry`, `IsleDevice`, `IsleEngine`, `IsleIngestReceipt`, `IsleMeshAPI`, `IsleProtocolPermit`, `IsleUplink`, `MeshAppRealization`

## Layout (the Standardized Polari App, postfix names)

- **basis** — `islemesh_basis.py`
- **api** — `islemesh_api.py`
- **page** — `islemesh_page.py`
- **catalog** — `islemesh_catalog.py`
- **custom** — `custom/islemesh_coherence.py`, `custom/islemesh_constants.py`, `custom/islemesh_engines.py`, `custom/islemesh_mock.py`, `custom/islemesh_netledger.py`, `custom/islemesh_parse.py`
- **selftests** — `islemesh_selftest.py`

`polari-app.json` is the manifest the core reads; `custom/` holds code that fits no concept file.

## Pages

- `islemesh.islemesh_page:SEED_ISLEMESH_PAGE_DISPLAYS`

## Selftest

```
pol modules selftest islemesh        # in the running backend
PYTHONPATH=.:modules python3 -m islemesh.islemesh_selftest   # on the host, from polari-framework/
```

Conformance: `pol modules conform islemesh`
