# Uno Core Demo (`uno_core_demo`)

The UNO core demo (ucd arc): "a simple proof based on the arduino uno, that can show thoroughly that everything makes sense and works and talks to one another" — a bare-bones firmware that keeps a date-time synced with the OS while one button simultaneously turns an LED on and off and an independent pin detects that switching, maintaining a struct on the microcontroller which gets sent back through a configured bridge through the kernel and the JavaFX app and up into Polari (his words, UNO_CORE_DEMO_PLAN.md §0). This module composes the demo's three parts by manifest — a Firmware Solution, a Hardware Bridge, and a Polari app component — as one Cross-Domain Solution, and derives each part's readiness (never a hand-set claim).

**Kind:** hardware-app · **agent tier:** member · **requires:** board, cmod, electrodevice, grpcbridge, hwnocode

## Objects

`DemoReadiness`, `UnoCoreDemoAPI`

## Layout (the Standardized Polari App — see modules/README.md for what each entry means)

- **objects** — `objects/uno_core_demo/DemoReadiness.py`
- **basis** — `uno_core_demo_basis.py`
- **api** — `uno_core_demo_api.py`
- **page** — `uno_core_demo_page.py`
- **custom** — `custom/readiness.py`
- **selftests** — `uno_core_demo_selftest.py`

`polari-app.json` is the manifest the core reads; `objects/` holds one class per file; `custom/` holds code that fits no concept file.

## Pages

- `uno_core_demo.uno_core_demo_page:SEED_UNO_CORE_DEMO_PAGE_DISPLAYS`

## Selftest

```
pol modules selftest uno_core_demo        # in the running backend
PYTHONPATH=.:modules python3 -m uno_core_demo.uno_core_demo_selftest   # on the host, from polari-framework/
```

Conformance: `pol modules conform uno_core_demo`

<!-- generated from polari-app.json by `pol modules manifests readme`; edit freely — the generator never overwrites a README without this marker -->
