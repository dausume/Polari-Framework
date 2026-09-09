# Printcam (`printcam`)

Print camera: a hardware-extension-app of the Voron guest — USB camera passthrough, ustreamer, Moonraker webcam + timelapse (D7, 2026-09-09).

**Kind:** hardware-extension-app · **agent tier:** hardware · **requires:** hardwareapps, voron, islemesh

## Objects

`CameraDefinition`, `PrintcamAPI`, `TimelapseRecord`

## Layout (the Standardized Polari App — see modules/README.md for what each entry means)

- **objects** — `objects/printcam/CameraDefinition.py`, `objects/printcam/TimelapseRecord.py`
- **basis** — `printcam_basis.py`
- **api** — `printcam_api.py`
- **page** — `printcam_page.py`
- **custom** — `custom/provision.py`
- **selftests** — `printcam_selftest.py`

`polari-app.json` is the manifest the core reads; `objects/` holds one class per file; `custom/` holds code that fits no concept file.

## Pages

- `printcam.printcam_page:SEED_PRINTCAM_PAGE_DISPLAYS`

## Selftest

```
pol modules selftest printcam        # in the running backend
PYTHONPATH=.:modules python3 -m printcam.printcam_selftest   # on the host, from polari-framework/
```

Conformance: `pol modules conform printcam`

<!-- generated from polari-app.json by `pol modules manifests readme`; edit freely — the generator never overwrites a README without this marker -->
