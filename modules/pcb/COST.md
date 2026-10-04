# pcb — measured cost (the cost rule; PCB_FROM_SCRATCH_PLAN §6/§7 pcb-0)

Every number here was MEASURED on isle-core (the engine worker's own host) through `prf-pcb-engines:trixie`, called
from pol-core over `PCB_ENGINES_URL=http://192.168.0.24:9860` (no KiCad runs on pol-core, his rule). The worker's
`/run` reports `wall_s`, `cpu_s` and `peak_rss_mb` from `wait4()` on the kicad-cli process itself (`rusage`); the
client (`pcb.custom.pcb_engines`) adds `round_trip_s` (the HTTP call, including the ~0.1–0.2 s network/job-dir
overhead). Measured 2026-10-03 ingesting the real `ecc83-pp` board (GPL-2.0-or-later, 15 footprints, 13 nets,
2-layer, all-THT).

## The engine image `prf-pcb-engines:trixie`

| what | measured | how |
|---|---|---|
| image size | **1 231 504 880 B ≈ 1.23 GB** (base `debian:trixie-slim@sha256:a99cfc51…`) | `docker image inspect --format '{{.Size}}'` on isle-core |
| build time | **unknown** — not logged by the agent that built it; not rebuilt for this measurement (the running container was already up 2 h when this slice resumed) | — |
| container memory limit | 1024 MB (`docker run --memory 1024m`) | the run command |
| display | **none** — kicad-cli runs headless with no X and no Xvfb (verified: ERC, DRC, gerbers, drill, pos, svg, step all exit 0 with `DISPLAY` unset) | `/capability`'s `display` field |
| reproducible outputs | **yes**, via `libfaketime` — kicad-cli stamps the wall clock into every Gerber/drill/job/SVG/STEP/netlist and ignores `SOURCE_DATE_EPOCH`; the worker runs it under a frozen `FAKETIME` and the same job directory every time | `/run`'s `source_date` + a repeat ingest (below) |

## kicad-cli verbs on the real `ecc83-pp` board (one worker, one run at a time — `gunicorn -w 1`)

| verb | wall_s | cpu_s | peak RSS (MB) | round_trip_s |
|---|---|---|---|---|
| `sch erc --format json --severity-all` | 0.275 | 0.213 | 188.6 | 0.451 |
| `pcb drc --format json --severity-all --schematic-parity` | 0.754 | 0.462 | 235.7 | 0.899 |
| `pcb drc` + the DKRed `.kicad_dru` | 0.713 | 0.420 | 219.5 | 0.838 |
| `pcb export gerbers` (Protel names) | 0.446 | 0.400 | 220.0 | 0.632 |
| `pcb export gerbers --no-protel-ext` | 0.405 | 0.367 | 220.0 | 0.586 |
| `pcb export drill --generate-map` | 0.426 | 0.391 | 215.2 | 0.588 |
| `pcb export pos` | 0.365 | 0.316 | 109.2 | 0.536 |
| `pcb export svg --mode-multi` (7 layers) | 0.404 | 0.365 | 215.4 | 0.548 |
| `pcb export step --no-components` | 0.405 | 0.523 | 126.6 | 0.592 |
| `sch export bom` | 0.244 | 0.195 | 179.5 | 0.363 |
| `sch export netlist` | 0.214 | 0.164 | 179.8 | 0.355 |
| `sch export svg` | 0.224 | 0.179 | 179.4 | 0.580 |

**Whole-board ingest** (every check + every export above, in series, from `pol pcb ingest` through
`POST /api/pcb/ingest`): **7.86 s wall** end to end (rows parsed with no engine + 12 worker calls + writing the 34
exported files to the artifact dir). Peak RSS across the twelve calls: **235.7 MB** (the schematic-parity DRC).

**Byte-stability** (the reproducibility claim, proven not asserted): ingesting the same project twice with the same
`source_date` gives the **same sha256 for all 34 exported files** and the same `PcbBoard.sha256` — checked directly
(`diffs: []`), not merely argued.

## The UNO shield schematic skeleton (brd-bo's rows → `.kicad_sch` → worker ERC)

| what | measured |
|---|---|
| components | 7 (TMP36, 220 Ω, LED, 4 headers) |
| nets wired | 5 (+5V, GND, the TMP36 output, the LED net, PWM_LED) |
| connections made | 13 (every power/signal pin the shield actually uses) |
| unconnected header pins (by design — the shield passes them through) | 26, all listed by ERC, none hidden |
| `sch erc` on the worker | exit 0; 38 violations reported (4 `pin_not_connected` groups + `lib_symbol_issues` warnings for `power`/`Connector_Generic` not in this run's local library config) — reported honestly, not filtered |

## Whether a display was needed on the frontend

**No new component.** The four pages (`/display/board-schematic`, `board-layout`, `board-bom`, `board-fab`) are all
`class-rows-table` — the per-layer SVGs and the Gerber/drill/STEP files are links through
`GET /api/pcb/artifacts/{board}/{path}` on an `artifact_url` column (`column_formats=...:link`, the same pattern
`mathproofs` already uses for a URL column), not a new image viewer.
