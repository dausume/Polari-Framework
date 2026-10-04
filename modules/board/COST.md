# board — measured cost (the cost rule; plan §8a)

Every number here was MEASURED on pol-core (Intel Core i5-4590 @ 3.30 GHz, 4 cpus, 16 GB, kernel 6.8) on
2026-10-01. The rows that carry them: `ModuleResourceProfile prf-board-engines-resource-profile`
(`resources/profile_seed.py`), the worker's `/capability` `resources` block (`polari-rf-node/prf-board-engines/cost.json`),
the `BoardSimCost` row `arduino-uno-r3:simavr:atmega328p` (from `custom/sim_cost_uno.json`, re-measured by
`pol board cost uno --write`), and each `FirmwareBuild.repro_json.cost`.

## The engine image `prf-board-engines:trixie`

| what | measured | how |
|---|---|---|
| image size | **534.7 MB** (base `debian:trixie-slim@sha256:a99cfc51…` 78.8 MB) | `docker image inspect` |
| build time | **46 s** (`docker build --no-cache`, base already local, apt downloads included) | `/usr/bin/time` |
| one UNO compile (avr-gcc, `-Os`) | **0.11 CPU-s, 30.5 MB peak RSS, 0.11 s wall** (3 runs: 0.116 / 0.106 / 0.105 CPU-s) | worker `/run` rusage(RUSAGE_CHILDREN) |
| objcopy + size | 0.002 CPU-s each | same |
| worker process (gunicorn, idle) | 29.5 MB resident | `/system-info` process block |
| compose `mem_limit` | 512 MB (8x headroom over the compile) | — |

Reproducibility: the same project built through the local image and through the remote worker gave the SAME .hex
(sha256 `5e56f8c9…72be`) every time — avr-gcc is deterministic on identical inputs, flags and versions.

## The firmware (avr-size -A, avr-gcc 14.2.0, default knobs)

| section | bytes | budget (cited) |
|---|---|---|
| `.text` | 4416 | |
| `.data` | 26 | |
| `.bss` | 737 | |
| **flash** = .text + .data | **4442** | 32256 (boards.txt `upload.maximum_size`, line 89) — 13.8 % |
| **static RAM** = .data + .bss | **763** | 2048 (`upload.maximum_data_size`, line 90) — 37.3 %; the stack is not counted |

The plan's estimate was 3–5 KB flash and ~0.6 KB RAM: flash is inside it, RAM is 0.16 KB over (the 173-B RX frame of
the header's parser + a 173-B TX frame + a 157-B payload buffer + the 149-B state + the 64-B ring).

## The twin — one simulated UNO (§8a's yardstick)

| what | measured | how |
|---|---|---|
| simulated speed | **78.6 M cycles/s = 4.9x real time** for a 16 MHz ATmega328P (free-running the SAME .hex, 160 M cycles) | `polari-avr-twin --bench 160000000` |
| twin process | **11.2 MB peak RSS**, one core (paced to real time it needs ≈ 1/4.9 ≈ 20 % of it — derived from the bench, not metered) | getrusage in the harness |
| simavr core state | **52 112 B** = avr_t 16 016 + data space 2 304 (regs + I/O + SRAM) + flash 32 768 + EEPROM 1 024; **mutable per cycle 19 344 B** (flash is read-only) | `polari-avr-twin --state-size`; the peripheral structs live in simavr's mcu_t beside avr_t and are bounded by the RSS |
| rows per simulated board | **33**: BoardDefinition 1, Road 1, TechNode 1, DatasheetFact 24, ProgrammerKind 1 (seeded) + BoardInstance 1, FirmwareBuild 1 per build, SimRigState 1, BoardSimCost 1, HardwareBridgeDefinition 1 (run time) | `board.custom.sim_cost.object_cost()` — derived from the seeds, not typed |
| rows per CLASS spoken (shared by every board on it) | 3: SchemaStabilityProfile, GrpcExposure, ProtoContractVersion | same |
| seeded rows' size | 16 065 B as JSON | same |
| wire | 10 frames/s × 55–60 B ≈ 0.6 KB/s up per board | the twin probe |

**Feasibility reading.** A UNO twin is cheap: ~11 MB and (derived) a fifth of one core in real time, so a cheap SBC runs several;
the image (535 MB) is the only real cost and is needed once per device that compiles or simulates. The 24 cited facts
dominate the row count — facts grow with what a firmware uses, not with the twin. The next twin is admitted against
this row.

## brd-wire — the wire v2 firmwares and the mapping (2026-10-02, same host)

Firmware sizes (avr-size -A, avr-gcc 14.2.0 `-Os`, live v1 field order as a fresh server makes it — `tests/board_installer_probe.py`):

| variant | brd-fi (wire v1) flash / static RAM | brd-wire (wire v2) flash / static RAM |
|---|---|---|
| uno-sim-rig | 4532 / 763 B | **4338 / 491 B** |
| uno-blink-only | 1514 / 501 B | **1014 / 302 B** |
| uno-adc-sweep | 1394 / 528 B | **1270 / 329 B** |
| uno-echo | 3152 / 763 B | **3022 / 495 B** |
| uno-pair (n=2, 1-bit index), per instance | — | **4372 / 493 B** |
| the same for n=3 (2-bit index) | — | 4378 / 4378 / 4380 B, 493 B (`tests/board_pair_probe.py`) |

RAM falls ~35–40 %: the status enum is 1 byte (was a 64-byte string buffer, ×3: state, scratch, the RX bound), and the
RX/TX bounds shrink with it. The presence/index code costs flash only where it is used.

Frame sizes (12-byte header + CRC included; `grpcbridge.custom.wire_ref`): SimRigState v1 **54 B** (status `ok`) – 61 B
(`commanded`) → v2 with every field **52 B** → the pair without `name` (the binding is the identity) **43 B**; blink v1
56 → v2 **38 B** (temp_c / pwm_duty absent). At n=20 (an index byte) 44 B, n=257 (u16) 45 B. At 10 Hz a pair is 0.86 KB/s
up for both boards.

Rows per bound board: +1 `HardwareInterfaceBinding` (+1 `WireContract` per class per bridge, +1 `EnumMapping` per mapped
field, shared). Twins: n twins = n × ~11 MB (three ran side by side in the n=3 probe).

Re-measured after his ruling "if it is index 0 and only one instance, the struct in the firmware is not needed" (the
single-instance header/board_config carry NO index symbol at all; `tests/board_installer_probe.py`, 2026-10-02): uno-sim-rig
**4338 / 491**, uno-blink-only **1014 / 302**, uno-adc-sweep **1270 / 329**, uno-echo **3022 / 495**, uno-pair **4372 / 493** B —
byte-for-byte the same sizes: with one instance the index was already 0 bits on the wire and avr-gcc `-Os` had folded the
constant index away, so the elision removes symbols from the interface, not bytes from the image.


## sc-3 — the ESP32-C3 (2026-10-02, pol-core, `dev-sc-3`)

| what | measured | how |
|---|---|---|
| engine image `prf-esp-engines:noble` | **1 813 008 516 B** (ubuntu:24.04 digest-pinned + ESP-IDF v5.5.5 431 MB + tools 862 MB + python env 92 MB) — `espressif/idf:v5.5.5` would be 5 116 MB compressed (every target) | `docker image inspect`; Docker Hub API |
| one from-scratch `idf.py build` | **57 s wall, 178 CPU-s, 193 MB peak RSS** (c3-prio-inversion 56.9 / 57.1 s; c3-sim-rig 56.6 s) | wait4 inside `polari-idf-build` |
| `idf.py size --format json2` / `merge_bin` | 0.95 s / 0.09 s | same |
| reproducibility | the SAME merged-image sha256 across forced rebuilds and across the image and worker (ESP_ENGINES_URL) rungs (`3902c420…` for c3-two-lock) | `CONFIG_APP_REPRODUCIBLE_BUILD=y` |
| the twin (`BoardSimCost esp32-c3:qemu:esp32c3`) | **0.533 virtual s per wall s** at `-icount 3` (sleep=off; boot + window, the whole QEMU process; 3 runs 0.533 / 0.534 / 0.533) = **66.6 M virtual instructions/s**; **43.3 MB peak RSS**; 9 rows per simulated C3 (4 seeded — BoardDefinition, Road, TechNode, ProgrammerKind; no DatasheetFact rows yet — + 5 at run time) vs the UNO's 33 (24 of them cited facts) | `pol board cost c3 --write` |
| the twin in serve mode (`-icount shift=auto,sleep=on`) | settles at 0.7–1.1 virtual/wall after ≈ 35 virtual s in the first ≈ 2 wall s; 10.8 telemetry frames/s for a 10 Hz firmware | `tests/board_c3_twin_probe.py` |

Firmware sizes (`idf.py size`, `-Os`):

| variant | app.bin | flash code | flash data | IRAM .text | DRAM .data / .bss | DRAM used / total |
|---|---|---|---|---|---|---|
| c3-sim-rig | 156 768 B | 77 564 | 28 556 | 45 328 | 5 180 / 37 288 | 87 796 / 321 296 B |
| c3-prio-inversion | 159 248 B | 79 474 | 28 972 | 45 452 | 5 188 / 37 816 | 88 456 / 321 296 B |

The technique pairs' deltas are in `modules/firmwarefaults/COST.md` (sc-3).

## brd-bo — THE BOARD OBJECT (measured 2026-10-03, pol-core i5-4590; builds on isle-core's workers)

| what | measured | how |
|---|---|---|
| rows | 2 SoCs, 45 SoC pins, 32 board pins (UNO 20, C3 12), 39 nets, 5 connectors / 38 connector pins, 2 BoardHardware, 8 runtime profiles, +95 DatasheetFacts (119 total) | the seed |
| seed build | 45 ms (incl. the Zephyr ingest: 4 files parsed, 11 stored at 156 KB) | `board_object.seed_tables()` wall, one process |
| render / ingest | UNO kicad 20.9 / 2.6 ms (7 585 B), bare-c 8.0 / 1.0 ms; C3 kicad 4.8 / 1.1 ms, zephyr 1.5 / 1.9 ms (2 051 B), esp-idf 0.5 / 1.1 ms | perf_counter, one run; peak RSS of the whole process 17.4 MB |
| UNO builds (16 variants + 1 refused + the flip) | ~4 s total on `BOARD_ENGINES_URL=http://<isle-core>:9830` (isle-core) | tests/board_object_probe.py |
| C3 build (c3-sim-rig) | 33.4 s wall, 148.8 CPU-s, 193.5 MB peak RSS on `ESP_ENGINES_URL=http://<isle-core>:9850` (isle-core) | the worker's /run rusage (build step) |
| pol-core during the probe | `free -m` used 7 778 → 7 842 MB (no local engine, no twin) | the probe prints it |
