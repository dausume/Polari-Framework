# Voron (`voron`)

The Voron 3D printer as a **hardware app**: Klipper + Moonraker + Mainsail running in a Debian KVM guest on the isle, with the printer's control boards passed through over USB/CAN — or, with no printer at all, Klipper's Linux-process host MCU so the whole software stack runs anyway.

**Kind:** hardware-app · **agent tier:** hardware · **requires:** hardwareapps, islemesh

## What it is

- `PrinterDefinition` — one Voron 2.4 / Trident / 0 (or an equivalent CoreXY): model, bed envelope, toolhead/extruder/probe, motion limits, **mode**.
- `PrinterBoard` — one MCU of that printer: the main board (`btt-octopus-1.1`, usb), a toolhead board (`btt-ebb36`/`ebb42`, canbus) or the `linux-host` pseudo-board. Named by `serial_by_id` / `canbus_uuid` — **empty until measured** (`pol hwmap scan` on the device; `canbus_query.py` in the guest).
- `PrinterState` — the twin (Klipper state, Moonraker, MCUs, temps, job) as Moonraker reports it.
- The guest is a `HardwareAppDefinition` row (`SEED_VORON_HARDWARE_APPS`, name `voron-printer`, Debian, 2 GiB / 2 vCPU, `provisioner: voron.custom.provision:render_provision`) and a store row (`SEED_VORON_CATALOG`, kind `hardware-app`, plan = `isle vm define/start`).

## sim vs real

| | `sim` (the seed) | `real` |
|---|---|---|
| boards used | only the `linux-host` board, as Klipper's primary `[mcu]` (`serial: /tmp/klipper_host_mcu`) | every board except `linux-host`: usb → `serial: <serial_by_id>`, canbus → `canbus_uuid:` |
| printer.cfg | `kinematics: none`, no steppers/heaters/probe, `[virtual_sdcard]` `[display_status]` `[pause_resume]` + the macros | the Voron reference mapping (BTT Octopus 1.1 main, EBB36/42 toolhead — **MUST be checked**), `[quad_gantry_level]` (2.4) / `[z_tilt]` (Trident), `[bed_mesh]`, `[safe_z_home]` |
| provisioner | builds Klipper's MCU with the Linux-process target (`.config` + `make olddefconfig` + `make`, binary → `/usr/local/bin/klipper_mcu`, `klipper-mcu.service`) | skips that build; the boards are passed through by hardwareapps (`passthrough_json`) |
| what runs | Klipper, Moonraker, Mainsail, the macros, G-code streaming — **no motion physics, nothing moves or heats** | the printer |

Named refusals instead of guesses: real mode with an unmeasured usb board, a canbus board without `canbus_uuid`, no `main` board, an unmapped board model, an unknown model, a bed dimension ≤ 0, a multi-Z model with `probe: none`, a non-Debian guest.

## The pins to fill (before any release)

`custom/provision.py` holds the upstreams at `'<PIN ME>'` — the provisioner **refuses to render** until they are commits/tags (all GPL-3.0, compatible with the project's GPLv3):

- `KLIPPER['commit']` — https://github.com/Klipper3d/klipper
- `MOONRAKER['commit']` — https://github.com/Arksine/moonraker
- `MAINSAIL['release']` — https://github.com/mainsail-crew/mainsail/releases/download/**vX.Y.Z**/mainsail.zip

`allow_unpinned: True` in the render input (`?allow_unpinned=1` on `/api/voron/render/<printer>`) renders a development script that says so in its header and clones the default-branch HEAD. The guest image (`debian-12-genericcloud-amd64.qcow2`) is pinned by RAW sha at deploy time in the guest row's `image_sha256_raw` (empty = the domain render refuses).

Offline installs: the script prefers `$VORON_STAGE/{klipper,moonraker,mainsail.zip}` (default `/var/lib/polari/voron-stage`) and Moonraker's `[update_manager]` is absent on purpose.

## Layout (the Standardized Polari App, postfix names)

- **objects/voron/** — `PrinterDefinition.py`, `PrinterBoard.py`, `PrinterState.py`
- **basis** — `voron_basis.py` (index + `SEED_PRINTERS`, `SEED_PRINTER_BOARDS`, `SEED_VORON_HARDWARE_APPS`, `SEED_VORON_CATALOG`, `VORON_SEED_PAIRS`, `VORON_CLASSES`)
- **api** — `voron_api.py` (`/api/voron/summary`, `/api/voron/render/{printer}`)
- **page** — `voron_page.py` (`/display/voron`)
- **custom/** — `printer_cfg.py` (printer.cfg), `provision.py` (the guest provisioner + macros), `board_pins.py` (the reference pin maps)
- **selftests** — `voron_selftest.py`

## Selftest

```
pol modules selftest voron        # in the running backend
PYTHONPATH=.:modules python3 -m voron.voron_selftest   # on the host, from polari-framework/
```

Conformance: `pol modules conform voron`
