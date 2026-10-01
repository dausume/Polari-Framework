# Board (`board`)

Program real boards over USB / USB-C from Polari — the brd arc (`AI-Notes/plans/BOARD_PROGRAMMING_PLAN.md`). brd-0 is
the object model, the register as rows, the two rules as selftests, detection, and the c_twin AVR mode.

**Kind:** polari-app · **agent tier:** member · **requires:** hwmap (its scanner) · **engines:** avr-gcc, avrdude, simavr

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
| `DatasheetFact` | a cited number (document, revision, line/page, URL) | 19, the UNO only |
| `BoardInstance` | a board or adapter seen plugged in | observed (`detect`) |
| `FirmwareBuild` | one build, sizes measured | from brd-1 |
| `BoardSimCost` | a twin's measured cost (the yardstick before another twin) | from brd-3 |

Only `arduino-uno-r3` is `simulated` (`simavr:atmega328p`) — track all, simulate few (plan §8a). The `board-roads`
tech tree carries one concept node per device when techtree is loaded.

## Layout

- `objects/board/*` — one class per file · `board_basis.py` the index · `board_seed.py` the seed pairs
- `custom/register_import.py` — the register markdown → `custom/register_rows.json` (re-run after editing the register)
- `custom/register_map.py` — snapshot → rows; every judgement (which programmer, aliases, adapter VID:PIDs) is a table with its reason
- `custom/programmers.py`, `custom/uno_facts.py` — the programmer kinds; the UNO's cited facts (boards.txt pinned to a commit)
- `custom/board_engines.py` — the engines seam: `BOARD_ENGINES_URL` → local binary → topology provider `board.engines` → refusal; a flash is refused on a remote worker
- `custom/detect.py` — hwmap's scanner + a sysfs tty→usb link → BoardInstance / unadmitted; `custom/board_cli.py` — what the CLI prints offline
- `board_api.py` (`/api/board`, `/api/board/detect` GET preview · POST upsert, `/roads`, `/facts`, `/engines`), `board_page.py` (`/display/boards`, configured tables only)

## CLI

```
pol board detect [--push] [--api URL]   # scan THIS host; --push upserts BoardInstance rows
pol board list | roads | facts <board> | engines
```

## Selftest

```
pol modules selftest board
PYTHONPATH=.:modules python3 -m board.board_selftest        # on the host, from polari-framework/
```

Conformance: `PYTHONPATH=.:modules python3 -m moduleService.manifests conform board` (write `requires.engines` by
hand — `generate` would drop it).
