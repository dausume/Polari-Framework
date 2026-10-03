# Board (`board`)

Program real boards over USB / USB-C from Polari — the brd arc (`AI-Notes/plans/BOARD_PROGRAMMING_PLAN.md`). brd-0 is
the object model, the register as rows, the two rules as selftests, detection, and the c_twin AVR mode. **brd-1** is the
UNO end to end in plain C — gen → build → flash (DRY-RUN; `--yes` with the board detected) → the simavr twin at a pty
→ the Java bridge — and the twin's measured cost (`COST.md`). No UNO was attached: everything up to the real flash is
proven on the twin; the real-hardware step is documented below and owed. **brd-fi** is the Firmware Installer App: firmware
VARIANTS as rows (different things to test on the one UNO), compatibility judged on the header itself, and
detect → builds that fit → DRY-RUN → confirm → install → the rows arriving, on `/display/firmware-installer` and
`pol board install` — proven on the twin (below). **brd-wire** (grpc-j4, his ruling 2026-10-02) is the computer↔firmware
MAPPING: every row that IS a piece of hardware has a `HardwareInterfaceBinding` (grpcbridge) naming its board instance,
interface and port; the wire carries fields only + a prelude (the instance index — its width a function of how many are
bound — and one presence bit per field); the gRPC message carries the identity; `GET /api/board/instances/<id>/interface`
walks a row to its datasheet (below). **sc-3** (D-sc-4 RULED 2026-10-02: the RTOS board is the ESP32-C3) brings the **ESP32-C3**:
an ESP-IDF C template (FreeRTOS tasks; the SAME SimRigState frames on UART0; FreeRTOS trace hooks on UART1), gen → build through
the `prf-esp-engines` worker → flash (the exact esptool argv, DRY-RUN) → the twin in Espressif's QEMU fork (`qemu:esp32c3`) at a
pty → the SAME generated Java bridge. No C3 is on hand: everything is proven on the twin (below).

**Kind:** polari-app · **agent tier:** member · **requires:** hwmap (its scanner), grpcbridge (contracts, the mapping rows) · **engines:** avr-gcc, avrdude, simavr (worker image `prf-board-engines`); sc-3: esp-idf, qemu-esp32c3 (worker image `prf-esp-engines`)

## The two rules (his, 2026-10-01)

1. **USB from the host** — a device is admitted if the Polari host reaches it over USB, directly or through a known
   USB adapter (`AdapterDefinition`). `BoardDefinition.usb_rule` is `ok | undetermined | not-a-target`, never guessed.
2. **C, Verilog or SystemVerilog only** on the device side — every engine has a kind (`c-compiler`, `hdl-toolchain`,
   `flasher`, `simulator`); an Arduino core, MicroPython or VHDL flow has none and fails.

## Rows

| class | what | seeded |
|---|---|---|
| `BoardDefinition` | one device model, register §1 cells verbatim (`?` → empty + a note) | 33 (every register device) |
| `Road` | the device's steps (facts → definition → twin → template → flashed → measured), todo/in-progress/done | 33 (all todo but the UNO's first step) |
| `AdapterDefinition` | USB-UART / probe / ISP / mass-storage bridge, register §1a | 13 |
| `ProgrammerKind` | programmer → engine → adapter kind → DRY-RUN argv | 9 |
| `DatasheetFact` | a cited number (document, revision, line/page, URL) | 24, the UNO only (brd-1 added the USART baud table, the ADC formula, the TMP36's two numbers) |
| `BoardInstance` | a board or adapter seen plugged in | observed (`detect`) |
| `FirmwareBuild` | one build: state generated → built \| refused → flashed, sizes measured, .hex sha256, engines, repro block | built (`pol board build`, `POST /api/board/builds`) |
| `BoardSimCost` | a twin's measured cost (the yardstick before another twin) | 1 — the UNO twin, measured (`custom/sim_cost_uno.json`) |
| `FirmwareVariant` | a named recipe over the template: app, classes, features, knobs, build defines, what to watch (brd-fi) | 4 (the UNO's) |
| `InstallPlan` | the DRY-RUN of one install: exact argv, engine, adapter, compat, what will be stamped | made by the installer |
| `InstallRecord` | what a confirmed install did: verdict, read-back, firmware sha, elapsed, log tail, bridge, first frames | made by the installer |
| `UnoAnalogState` | the UNO's SECOND class (uno-adc-sweep): raw a0/a1/a2, uptime, status | pushed by the board |

Only `arduino-uno-r3` is `simulated` (`simavr:atmega328p`) — track all, simulate few (plan §8a). The `board-roads`
tech tree carries one concept node per device when techtree is loaded.

## Layout

- `objects/board/*` — one class per file · `board_basis.py` the index · `board_seed.py` the seed pairs
- `custom/register_import.py` — the register markdown → `custom/register_rows.json` (re-run after editing the register)
- `custom/register_map.py` — snapshot → rows; every judgement (which programmer, aliases, adapter VID:PIDs) is a table with its reason
- `custom/programmers.py`, `custom/uno_facts.py` — the programmer kinds; the UNO's cited facts (boards.txt pinned to a commit)
- `custom/board_engines.py` — the engines seam: `BOARD_ENGINES_URL` → local binary → topology provider `board.engines` → refusal; a flash is refused on a remote worker
- `custom/detect.py` — hwmap's scanner + a sysfs tty→usb link → BoardInstance / unadmitted; `custom/board_cli.py` — what the CLI prints offline
- `custom/firmware/uno/` — the plain-C template (hal.c/hal.h, `apps/<app>.c` → main.c per variant, Makefile, board_config.h defaults, README); `custom/contracts/SimRigState.v2.json` — the pinned contract for offline gen
- `custom/gen.py` · `custom/build.py` · `custom/flash.py` · `custom/twin.py` (+ `twin_pty.py`, the host pty pump) · `custom/sim_cost.py` — the brd-1 verbs; `custom/engine_run.py` runs an engine on the rung `board_engines` resolved (local binary / the image via `docker run` / the worker's `/run`); `custom/packet_ref.py` — an independent Python reference of the wire
- brd-fi: `custom/variants.py` (the variant rows + knob validation), `custom/compat.py`, `custom/installer.py`, `custom/attach.py`,
  `custom/install_cli.py`; `installer_api.py` (the installer doors); `board_page.py` also seeds `/display/firmware-installer`
  (six configured tables + the ONE new component `firmware-installer-panel`, polari-platform-angular)
- `board_api.py` (`/api/board`, `/api/board/detect` GET preview · POST upsert, `/roads`, `/facts`, `/engines`, `/builds` GET · POST upsert + flash stamp, `/sim-costs`), `board_page.py` (`/display/boards`, configured tables only)
- the worker image: `polari-rf-node/prf-board-engines/` (gcc-avr, avr-libc, avrdude, simavr + `polari-avr-twin`), `docker-compose.board-engines.yml`, provider `board.engines` → `prf-board-engines` :9830

## CLI

```
pol board detect [--push] [--api URL]   # scan THIS host; --push upserts BoardInstance rows
pol board list | roads | facts <board> | engines
pol board gen uno [--class SimRigState] [--api URL]     # the project around the AVR header → FirmwareBuild 'generated'
pol board build uno                                     # avr-gcc via the ladder; sizes; refused past 32256 / 2048 B
pol board flash uno [--port P]                          # DRY-RUN: the exact avrdude argv
pol board flash uno --yes                               # real: needs the UNO detected on THIS host; read-back verify
pol board twin uno up|status|down [--adc0-mv 750]       # the SAME .hex in simavr; UART at /tmp/polari-uno-twin-uart
pol board cost uno [--write]                            # re-measure the twin's object cost
pol board interface twin:arduino-uno-r3#1               # brd-wire: the binding chain of a board instance
pol board gen c3 [--variant c3-sim-rig] [--api URL]     # sc-3: the ESP-IDF project around the target=host header
pol board build c3 [--force]                            # ESP-IDF v5.5.5 via the esp engines; idf.py size; the build cache
pol board flash c3 [--port P]                           # DRY-RUN: the exact esptool write_flash argv (idf.py's flash_args)
pol board twin c3 up|status|down                        # the SAME merged image in the QEMU fork; UART0 at /tmp/polari-c3-twin-uart
pol board cost c3 [--write]                             # re-measure the C3 twin's cost (QEMU RSS, wall-time ratio)
```

## Testing different things on the UNO (brd-fi)

His intent: *"that way we can test different kinds of things on the arduino uno to see if it works."* Each variant is one
such thing; install one, watch for its effect, try the next — on `/display/firmware-installer` or `pol board install`.

| variant | app (`firmware/uno/apps/`) | speaks | compiled in | what to watch | measured flash / RAM (avr-gcc 14.2.0, -Os) |
|---|---|---|---|---|---|
| `uno-sim-rig` | `sim_rig.c` (brd-1's firmware) | SimRigState | LED D13, PWM D6, ADC A0 (TMP36), commands | temp_c follows a finger; a PUT lights D13 / dims D6; status `commanded` | 4338 / 491 B |
| `uno-blink-only` | `blink.c` | SimRigState | LED only (toggles every 500 ms); transmit only | D13 blinks; led_on flips in the frames AND the row | 1014 / **302** B |
| `uno-adc-sweep` | `analog.c` | **UnoAnalogState** | ADC A0..A2 raw; transmit only | a0/a1/a2 follow a pot / photoresistor | **1270** / 329 B |
| `uno-echo` | `echo.c` | SimRigState | nothing but the command path | a PUT comes back WHOLE (even temp_c), status `echoed` | 3022 / 495 B |
| `uno-pair` (brd-wire) | `sim_rig.c` | SimRigState | as uno-sim-rig, built per `instance_index` for bridge `uno-pair`, `SEND_NAME 0` | each row follows ITS board; a PUT reaches only the board it names | 4372 / 493 B |

(Sizes from the live-contract builds in `tests/board_installer_probe.py`, wire v2 — brd-fi's v1 builds were 4532/763,
1514/501, 1394/528, 3152/763: the status enum is 1 byte instead of a 64-byte buffer, an absent field costs nothing. blink-only
is the smallest in RAM; the adc sweep the smallest in flash — SimRigState's one `double` costs the software
binary32→binary64 encoder, ~120 B, which the all-integer UnoAnalogState does not need.)

**Adding a variant:** add a `FirmwareVariant` row (on the page's Variants table, or a dict in `custom/variants.py` for a
seeded one): pick an `app`, list the class it speaks, set `features_json` / `knobs_json` (telemetry_hz 1..50, led_pin
D2..D13, pwm_pin 5/6/9/10, adc_channel 0..5, temp_formula tmp36|raw, blink_ms, rig_name, device_id) and optional
`build_flags_json` (`NAME=integer` defines, never compiler arguments). `pol board gen uno --variant <name>` validates it and
refuses with the reason (PWM on Timer2, LED on D0/D1, a feature the app has no code for, …). A NEW class needs a new app
`.c` (a generated header alone is not firmware) plus its pinned contract in `custom/contracts/`.

**Compatibility** (`custom/compat.py`, `GET /api/board/builds/<b>/compat`): the build's `header_sha256` and wire (tag) order,
captured at gen, against the header THIS server generates now from its live gRPC exposure (the pinned snapshot only when
no exposure exists) → `compatible | stale-header | unknown-class`. Never contract_hash alone (brd-1's finding: a fresh
server's v1 and the ledger's v2 share hash 2bcc9d1a2774ef33 yet differ in order). Install refuses anything but
`compatible` (exit 3, plain words naming both orders).

**The flow** (`custom/installer.py`, `custom/attach.py`, doors in `installer_api.py`): `GET /api/board/installer` (one document
for the page) → `POST …/build {variant}` (gen against this server's contracts + build) → `POST …/plan {instance, build}` (the
InstallPlan row: the argv, fixed here) → `POST …/run {plan, confirm: true}` (this server's own host only; re-checks
compat; the twin: simavr loads the .hex and its loaded byte count is the read-back; a board: avrdude's read-back verify)
→ `POST …/attach {record}` (the generated Java bridge at the port / the twin's pty; needs the class's gRPC exposure
enabled — never flipped by the installer) → `GET …/result/<record>` (first frames, frames per device-second, the row).
The page sends NAMES only; no request field reaches a command line.

```
pol board variants
pol board gen uno --variant uno-adc-sweep [--api URL]
pol board install uno --variant uno-echo --twin            # DRY-RUN: the argv
pol board install uno --variant uno-echo --twin --yes      # install into the twin, attach, first frames
pol board install uno --variant uno-sim-rig --yes          # the detected UNO (needs it on the server's host)
pol board result [install-…]
```

## The real-hardware step (owed — no UNO attached on 2026-10-01)

1. Plug the UNO in; `pol board detect --push` → a `BoardInstance` `board present` with its `/dev/serial/by-id/…` path.
2. `pol board gen uno --api <the server>` (the LIVE header — a fresh server's contract can order fields differently
   from the pinned v2 snapshot; see below) → `pol board build uno` → `pol board flash uno` (read the argv) →
   `pol board flash uno --yes`.
3. Point a bridge at the board: `POST /api/grpc/bridges {bridgeName, classes: [SimRigState], source: serial,
   serialDevice: <by-id>, grpcEnabled: true}`, exposure `enable` + `set-transport both`, download, `mvn package`,
   `java -jar`. Expect the first ~1–2 s after the port opens to belong to Optiboot (the DTR reset; unverified length).
4. Proof: the TMP36 on A0 (kit project 03 wiring) — `temp_c` in the row tracks a finger; a PUT of `led_on` lights
   D13, a PUT of `pwm_duty` dims an LED on D6 (220 Ω), and the next frame says `status=commanded`.

**Contract order matters.** The wire carries fields in TAG order. `contract_hash` (v1) hashes only field → type, so two
servers can share it yet order the fields differently (a fresh server's v1 is alphabetical; the staging ledger's v2 —
the pinned snapshot — puts `name` first). brd-wire's **contract hash v2** sees the order (+ enum tables + the index
representation); every build records it and the installer compares it first. Generate against the server the board
will talk to.

## The computer↔firmware mapping (brd-wire / grpc-j4)

His ruling (2026-10-02): *"define a mapping from the computer side to the firmware side … identifiers tying it to the
hardware interface it belongs to … converted to not having that when being sent over as a struct … enum mappings …
indexes … in the shortest format we possibly can."* Design: `AI-Notes/plans/GRPC_BRIDGE_PLAN.md` §grpc-j4.

- **The binding is the identity.** `HardwareInterfaceBinding` (row class + name ↔ board instance ↔ interface + port, on a
  bridge, with a dense `instance_index`). Frames up are matched to the row by binding, never by the name the struct
  carries; a frame whose index belongs to another port is refused and counted.
- **The index is a function of the bound count** n: none for 1, ceil(log2 n) bits packed beside the presence bits up to
  `packed_max_bits` (default 4 → 16 instances; a knob on the `WireContract` row), then an explicit index byte (≤ 256), then a
  16-bit index — the version byte (2/3/4) says which.
- **Presence**: one bit per field; absent fields are not sent; a present false/0 IS applied to the row.
- **Several twins**: `pol board twin uno up --work W --tcp T --link L --tag K` (one per binding port);
  `pol board gen uno --variant uno-pair --instance-index K`.
- **Analysis**: `pol board interface twin:arduino-uno-r3#1` / `GET /api/board/instances/<id>/interface` — the row, its
  contract (hash v1), the wire contract (hash v2, index representation), the binding, the instance, the port/adapter,
  the board definition and its cited facts (the interface's own first); the bindings table on `/display/boards`.

## The ESP32-C3 (sc-3)

**The twin decision, with its evidence** (FIRMWARE_SCENARIO_PLAN.md §9 sc-3):
- Espressif's QEMU fork (`github.com/espressif/qemu`, GPL-2.0) has a `-machine esp32c3`. ESP-IDF v5.5.5's own tools.json pins
  release `esp_develop_9.2.2_20260417` by sha256.
- Its UART0/1 are real character devices, and the timers, SYSTIMER, interrupt matrix and SPI flash are emulated. The USB
  Serial/JTAG controller is only a register stub, so the twin speaks on UART0.
- It runs a FreeRTOS app headlessly: UART0 goes to a TCP port that the pty pump turns into a link.
- It is picked over Renode, which was not needed, and over a host FreeRTOS POSIX port, which would not be the C3.

The template `custom/firmware/esp32c3/` is an ESP-IDF C project. CMake is used only because ESP-IDF requires it; RULE 2 is
about the language, and gen's RULE 2 check admits only `.c`/`.h` plus CMakeLists.txt, sdkconfig.defaults and partitions.csv.
- `main/polari_c3.c|h` is the common layer:
  - UART0 carries SimRigState frames through the header c_twin renders with **target=host** (riscv32's double is 8 bytes), on
    the same wire v2 as the UNO's.
  - UART1 carries the trace lines.
  - A 4 KB `polari` params partition steers the SAME binary per seed.
  - The telemetry and rx tasks live here.
- `main/polari_trace.c|h` holds the FreeRTOS hook macros, force-included into every C file of the build (the kernel too) by the
  top CMakeLists.txt. They cover switch-in, block, take (`traceQUEUE_SEMAPHORE_RECEIVE` — ESP-IDF's queue.c reports a
  semaphore take there, not in `traceQUEUE_RECEIVE`), give, inherit, disinherit and timeout. They feed an 8-byte-per-event ring
  that is dumped after the window.
- `apps/`:
  - `sim_rig.c` (c3-sim-rig): telemetry and commands.
  - `prio_inversion.c` (c3-prio-inversion / -mutex: `SC_PI_MUTEX`).
  - `two_lock.c` (c3-two-lock / -ordered / -backoff: `SC_LOCK_ORDER`, `SC_LOCK_TIMEOUT_MS`).

`sdkconfig.defaults` sets:
- a 1 kHz tick;
- no console and no logs on UART0;
- the task watchdog off (the app's own monitor detects a deadlock and says so);
- `CONFIG_APP_REPRODUCIBLE_BUILD=y`.

| file | role |
|---|---|
| `custom/variants_c3.py` | the six C3 FirmwareVariant rows (seeded by board; the scenario ones marked SCENARIO ONLY), validated per app |
| `custom/gen_c3.py` | `pol board gen c3`: the project + the target=host header (live `--api`, in-process, or the pinned contract) |
| `custom/build_c3.py` | `pol board build c3`: a deterministic project tar → engine `idf-build`; idf.py size json2 → the size columns; refused past the 1 MB app partition / DRAM total; the build cache (source sha + image id) |
| `custom/flash_c3.py` | `pol board flash c3`: the esptool ProgrammerKind template + idf.py's flash_args → the exact argv; a real flash needs a detected C3 + `--yes`, verified by esptool's hash check |
| `custom/twin_c3.py` | `pol board twin c3 up|down|status`: `polari-c3-run --serve` (local binary or the image as `prf-board-twin-c3`), UART0 → TCP → `twin_pty` |
| `custom/sim_cost_c3.py` + `sim_cost_c3.json` | the BoardSimCost row `esp32-c3:qemu:esp32c3` (objects, QEMU peak RSS, virtual instructions/s, the wall-time ratio) |
| `custom/board_engines.py` | engines in FAMILIES: `avr` (BOARD_ENGINES_URL …) and `esp` (ESP_ENGINES_URL → local → `prf-esp-engines:noble` → provider `board.esp-engines` → refusal) |

**Proven on the twin (2026-10-02):**
- `tests/board_c3_twin_probe.py` 13/13, run as a throwaway server with the live v1 contract:
  - the live target=host header;
  - the build in 59 s;
  - the esptool DRY-RUN;
  - QEMU up, with 10.8 frames/s on the pty after the shift=auto warm-up and 0 bad CRC;
  - **the SAME generated Java bridge** (mvn package, `source=serial` at the C3 twin's link): the `c3-twin` row follows the
    firmware, and a REST PUT `{led_on: true, pwm_duty: 42}` comes back `status=commanded` in 0.10 s.
- The UNO's finding held here too: a fresh server's v1 tag order differs from the pinned v2 snapshot under the same contract
  hash, so decode with the server's own field map.

## Selftest

```
pol modules selftest board
PYTHONPATH=.:modules python3 -m board.board_selftest        # on the host, from polari-framework/
PYTHONPATH=.:modules python3 tests/board_uno_twin_probe.py   # the REAL avr-gcc + simavr path (skips without the image)
cd /tmp/y && PYTHONPATH=<fw>:<fw>/modules python3 <fw>/tests/board_installer_probe.py   # brd-fi: five variants, compat, installs into the twin + the bridge
cd /tmp/x && PYTHONPATH=<fw>:<fw>/modules python3 <fw>/tests/board_uno_bridge_probe.py   # + a throwaway server + the Java bridge
cd /tmp/p && PYTHONPATH=<fw>:<fw>/modules python3 <fw>/tests/board_pair_probe.py        # brd-wire: n=2 and n=3 twins on one bridge
cd /tmp/c && PYTHONPATH=<fw>:<fw>/modules python3 <fw>/tests/board_c3_twin_probe.py      # sc-3: the C3 twin + the Java bridge (skips without prf-esp-engines)
PYTHONPATH=.:modules python3 -m board.board_c3_selftest       # sc-3 alone (also run by board_selftest): variants, gen, flash argv, a FAKE twin, a REAL build
# the in-process servers boot through tests/board_probe_boot.py: the framework as cwd for the boot, the DB in ./data here
```

Conformance: `PYTHONPATH=.:modules python3 -m moduleService.manifests conform board` (write `requires.engines` by
hand — `generate` would drop it).
