# Voron (`voron`)

Voron 3D printer as a hardware app: Klipper + Moonraker + Mainsail in a Debian KVM guest with the printer boards passed through (mode real) or Klipper's linux host MCU with no printer (mode sim — no motion physics).

**Kind:** hardware-app · **agent tier:** hardware · **requires:** hardwareapps, islemesh

## Objects

`PrinterBoard`, `PrinterDefinition`, `PrinterState`, `VoronAPI`

## Layout (the Standardized Polari App — see modules/README.md for what each entry means)

- **objects** — `objects/voron/PrinterBoard.py`, `objects/voron/PrinterDefinition.py`, `objects/voron/PrinterState.py`
- **basis** — `voron_basis.py`
- **api** — `voron_api.py`
- **page** — `voron_page.py`
- **custom** — `custom/board_pins.py`, `custom/printer_cfg.py`, `custom/provision.py`
- **selftests** — `voron_selftest.py`

`polari-app.json` is the manifest the core reads; `objects/` holds one class per file; `custom/` holds code that fits no concept file.

## Pages

- `voron.voron_page:SEED_VORON_PAGE_DISPLAYS`

## Selftest

```
pol modules selftest voron        # in the running backend
PYTHONPATH=.:modules python3 -m voron.voron_selftest   # on the host, from polari-framework/
```

Conformance: `pol modules conform voron`

<!-- generated from polari-app.json by `pol modules manifests readme`; edit freely — the generator never overwrites a README without this marker -->
