# Board (`board`)

Program real boards over USB / USB-C from Polari — the brd arc (`AI-Notes/plans/BOARD_PROGRAMMING_PLAN.md`). brd-0 is
the object model, the register as rows, the two rules as selftests, detection, and the c_twin AVR mode. **brd-1** is the
UNO end to end in plain C — gen → build → flash (DRY-RUN; `--yes` with the board detected) → the simavr twin at a pty
→ the Java bridge — and the twin's measured cost (`COST.md`). No UNO was attached: everything up to the real flash is
proven on the twin; the real-hardware step is documented below and owed.

**Kind:** polari-app · **agent tier:** member · **requires:** hwmap (its scanner) · **engines:** avr-gcc, avrdude, simavr (worker image `prf-board-engines`)

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

Only `arduino-uno-r3` is `simulated` (`simavr:atmega328p`) — track all, simulate few (plan §8a). The `board-roads`
tech tree carries one concept node per device when techtree is loaded.

## Layout

- `objects/board/*` — one class per file · `board_basis.py` the index · `board_seed.py` the seed pairs
- `custom/register_import.py` — the register markdown → `custom/register_rows.json` (re-run after editing the register)
- `custom/register_map.py` — snapshot → rows; every judgement (which programmer, aliases, adapter VID:PIDs) is a table with its reason
- `custom/programmers.py`, `custom/uno_facts.py` — the programmer kinds; the UNO's cited facts (boards.txt pinned to a commit)
- `custom/board_engines.py` — the engines seam: `BOARD_ENGINES_URL` → local binary → topology provider `board.engines` → refusal; a flash is refused on a remote worker
- `custom/detect.py` — hwmap's scanner + a sysfs tty→usb link → BoardInstance / unadmitted; `custom/board_cli.py` — what the CLI prints offline
- `custom/firmware/uno/` — the plain-C template (main.c, Makefile, board_config.h defaults, README); `custom/contracts/SimRigState.v2.json` — the pinned contract for offline gen
- `custom/gen.py` · `custom/build.py` · `custom/flash.py` · `custom/twin.py` (+ `twin_pty.py`, the host pty pump) · `custom/sim_cost.py` — the brd-1 verbs; `custom/engine_run.py` runs an engine on the rung `board_engines` resolved (local binary / the image via `docker run` / the worker's `/run`); `custom/packet_ref.py` — an independent Python reference of the wire
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

**Contract order matters.** The wire carries fields in TAG order, and `contract_hash` hashes only field → type, so two
servers can share a hash yet order the fields differently (a fresh server's v1 is alphabetical: `led_on` first; the
staging ledger's v2 — the pinned snapshot — puts `name` first). Generate against the server the board will talk to.

## Selftest

```
pol modules selftest board
PYTHONPATH=.:modules python3 -m board.board_selftest        # on the host, from polari-framework/
PYTHONPATH=.:modules python3 tests/board_uno_twin_probe.py   # the REAL avr-gcc + simavr path (skips without the image)
cd /tmp/x && PYTHONPATH=<fw>:<fw>/modules python3 <fw>/tests/board_uno_bridge_probe.py   # + a throwaway server + the Java bridge
```

Conformance: `PYTHONPATH=.:modules python3 -m moduleService.manifests conform board` (write `requires.engines` by
hand — `generate` would drop it).
