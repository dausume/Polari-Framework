# Microchip (`microchip`)

Microchip design-level ladder (device -> cell -> block -> core -> chip) + traversal interface. Separable from the device modules: reads cntfet/electrodevice rows softly, imports no device code; absent modules degrade honestly.

**Kind:** polari-app · **agent tier:** member · **requires:** nothing

## Objects

`DesignLevelDefinition`, `DeviceFamilyDefinition`, `MicrochipAPI`, `MicrochipDesignNode`

## Layout (the Standardized Polari App — see modules/README.md for what each entry means)

- **objects** — `objects/chip/DesignLevelDefinition.py`, `objects/chip/MicrochipDesignNode.py`, `objects/chip/_shared.py`, `objects/chip_families/DeviceFamilyDefinition.py`, `objects/chip_families/_shared.py`
- **basis** — `chip_basis.py`, `chip_families_basis.py`
- **api** — `chip_api.py`
- **page** — `chip_page.py`
- **custom** — `custom/chip_traverse.py`
- **selftests** — `families_selftest.py`, `microchip_selftest.py`

`polari-app.json` is the manifest the core reads; `objects/` holds one class per file; `custom/` holds code that fits no concept file.

## Pages

- `microchip.chip_page:SEED_MICROCHIP_PAGE_DISPLAYS`

## Selftest

```
pol modules selftest microchip        # in the running backend
PYTHONPATH=.:modules python3 -m microchip.families_selftest   # on the host, from polari-framework/
```

Conformance: `pol modules conform microchip`

<!-- generated from polari-app.json by `pol modules manifests readme`; edit freely — the generator never overwrites a README without this marker -->
