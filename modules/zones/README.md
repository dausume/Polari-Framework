# Zones (`zones`)

AR-captured 3D zones: planar/hull models, rooms vs selections, cube packing.

**Kind:** polari-app · **agent tier:** member · **requires:** scoring

## Objects

`SiteDefinition`, `ZoneDefinition`, `ZoneEstimateRecord`, `ZonePoint`, `ZonesAPI`

## Layout (the Standardized Polari App, postfix names)

- **basis** — `zone_basis.py`
- **api** — `zones_api.py`
- **custom** — `custom/zone_geometry.py`, `custom/zone_packing.py`, `custom/zone_sim_bridge.py`
- **selftests** — `zones_selftest.py`

`polari-app.json` is the manifest the core reads; `custom/` holds code that fits no concept file.

## Selftest

```
pol modules selftest zones        # in the running backend
PYTHONPATH=.:modules python3 -m zones.zones_selftest   # on the host, from polari-framework/
```

Conformance: `pol modules conform zones`
