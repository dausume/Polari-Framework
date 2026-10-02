# Hwmap (`hwmap`)

Hardware map: an on-device scanner (usb, pci + IOMMU groups, serial by-id, nics, kvm/libvirt facts) pushes a snapshot; Polari keeps ports and slots as rows and answers what can be mapped to a potential KVM (usb hostdev, pci vfio, nic macvtap) with reasons, and which hardware apps each port satisfies (hwm-1, 2026-09-08).

**Kind:** polari-app · **agent tier:** member · **requires:** hardwareapps, islemesh

## Objects

`HardwareMapSnapshot`, `HardwarePort`, `HardwareSlot`, `HwmapAPI`, `PassthroughCandidate`

## Layout (the Standardized Polari App — see modules/README.md for what each entry means)

- **objects** — `objects/hwmap/HardwareMapSnapshot.py`, `objects/hwmap/HardwarePort.py`, `objects/hwmap/HardwareSlot.py`, `objects/hwmap/PassthroughCandidate.py`
- **basis** — `hwmap_basis.py`
- **api** — `hwmap_api.py`
- **page** — `hwmap_page.py`
- **custom** — `custom/mapping.py`, `custom/scanner.py`
- **selftests** — `hwmap_selftest.py`

`polari-app.json` is the manifest the core reads; `objects/` holds one class per file; `custom/` holds code that fits no concept file.

## Pages

- `hwmap.hwmap_page:SEED_HWMAP_PAGE_DISPLAYS`

## Selftest

```
pol modules selftest hwmap        # in the running backend
PYTHONPATH=.:modules python3 -m hwmap.hwmap_selftest   # on the host, from polari-framework/
```

`custom/fixture_pol_core.json` is a captured snapshot (`python3 -m hwmap.custom.scanner`)
run through the mapping rules as the "real box" half of the selftest; it is tracked
(exempted from the blanket `*.json` .gitignore rule) and MUST be sanitised before
committing — hostname → a placeholder, MACs → locally-administered fakes, LAN IPs →
TEST-NET-1 (`192.0.2.0/24`), any by-id serial strings → deterministic fakes of the
same shape. Vendor:product ids, bus topology, IOMMU groups and driver names are not
personal and stay real — the mapping rules need them. If the fixture is absent (a
narrower checkout, or before a first capture), the real-snapshot checks SKIP with a
named reason instead of crashing; the synthetic-snapshot checks still run.

Conformance: `pol modules conform hwmap`

<!-- generated from polari-app.json by `pol modules manifests readme`; edit freely — the generator never overwrites a README without this marker -->
