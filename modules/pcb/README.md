# PCB (`pcb`)

PCB from scratch — the pcb arc (`AI-Notes/plans/PCB_FROM_SCRATCH_PLAN.md`). **KiCad is the RELAY ENGINE**
(GPL-3.0, headless `kicad-cli`, a separate process — never linked): it checks (ERC, DRC) and exports (Gerbers,
drill, pos, BOM, netlist, SVG, STEP). Polari holds the design AS ROWS and writes `.kicad_sch`/`.kicad_pcb` itself
(D-pcb-1, his ruling: "write directly so we can track them through polari … while relaying them through kicad
engines"). **pcb-0** is the module itself: the rows, the `prf-pcb-engines` worker, `pol pcb ingest` over a real open
KiCad board, DKRed's fab rules cited, and the UNO shield's schematic SKELETON (no PCB yet — that is pcb-2).

**Kind:** polari-app · **agent tier:** member · **requires:** `board` (brd-bo's `BoardPin`/`BoardNet` rows feed the
UNO shield design; `pcb` reuses `board.BoardNet` rather than a second net class) · **engine:** `kicad-cli` (worker
image `prf-pcb-engines`)

## The ingested board (pcb-0's proof)

Plan §7 named Raspberry Pi's RP2040 Minimal design as the open board to ingest; its formal licence page returned
404 (only a forum staff statement backs it), so this slice ingests **KiCad's own `ecc83-pp` demo** instead — the
`kicad-demos` 9.0.2+dfsg-1 Debian package's `ecc83/` project (an ECC83/12AX7 valve push-pull preamp, all
through-hole), explicitly **GPL-2.0-or-later** per Debian's copyright file (compatible with this project's
GPL-3.0), fetched with the SAME pinned Debian packages the engine uses, small (15 footprints, 13 nets) and all-THT
like the UNO shield. Stored under `custom/upstream/kicad-demos-9.0.2/ecc83/` with `LICENSE.md` + `SOURCE.json`
(every file's sha256, the package's sha256, why this board was picked instead).

Real ingest through the worker (2026-10-03): **11 Part** rows (TMP-style groupings: 2× 1.5K, 1× 100K, 1× 47K
resistor, 2 capacitors, 4 connectors, 4 mounting holes as one group, 1 ECC83 valve), **8 Symbol**, **6 Footprint**,
**1 PcbBoard** (2 copper layers, 52.07 × 46.355 mm, 13 nets, 59 segments, 1 zone), **15 Placement**, **13 BoardNet**
+ **13 Route** rows. `sch erc` → **0 violations**; `pcb drc --schematic-parity` → 2 silkscreen-clipped warnings + 4
footprint/symbol mismatches (KiCad's own library footprints differ slightly from the demo's bundled ones — reported,
not hidden); the DKRed fab-rule check → **0 violations** (all extremes within DKRed's limits: narrowest track 0.8 mm
vs the 0.127 mm minimum, smallest hole 0.8 mm vs 0.2032 mm, board 2.05″×1.825″ vs the 0.5–10″ range). **34**
`FabricationExport` rows (Protel + `--no-protel-ext` Gerbers, Excellon drill + map, pos/BOM/netlist, 7 per-layer
SVGs, STEP, the KiCad job file) — the DKRed naming verdict is honest: some `yes` (silkscreen, paste), some `no`
(KiCad's own `.gm1`/`.pho` extensions DKRed's page does not list), some `discrepancy` (`.gtl`/`.gbl`/`.gbs`: on his
upload-form screenshot but not in the page text). **Byte-stable**: a second ingest with the same frozen clock
reproduces all 34 export shas exactly (checked, not asserted) and kicad-cli's own exported netlist agrees with the
board's own nets (13 = 13, `only_schematic`/`only_board` both empty).

## Rows

| class | what |
|---|---|
| `Part` | one BOM line: value, manufacturer/MPN where cited, package, mount, symbol/footprint, refs, provenance |
| `Symbol` / `Footprint` | a KiCad library reference (lib:name) + the library's version/sha256 + licence (official KiCad libraries: CC-BY-SA-4.0 with the design exception — our boards and Gerbers are free of the share-alike) |
| `LandPattern` | a footprint's dimensions — as drawn (pcb-0) or IPC-7351-derived and compared (pcb-3) |
| `Schematic` / `SchematicSheet` | one `.kicad_sch` by sha256, origin `rendered` (D-pcb-1) or `ingested`, its sheets |
| `PcbBoard` | the physical board: layers, stackup, outline, the board's own design rules, the fab rule set it targets |
| `Placement` | ref → x/y/rotation/side — INGESTED only (D-pcb-2: a person places and routes in KiCad) |
| `Route` | one net's copper SUMMARISED (segments, vias, length, widths) — never per-segment |
| `DrcResult` | one finding of ERC / DRC / schematic-parity / a DKRed fab-rule check; a clean run is ONE `severity=none` row |
| `FabricationExport` | one exported file: kind, layer, sha256, bytes, the fab's naming verdict, the artifact path/URL |
| `FabRuleSet` / `FabRule` | DKRed's constraints as cited rows (the only CODE-OWNED seed in this module) |

`board.BoardNet` (brd-bo's class) carries a PCB's nets — no second net model.

## Layout

- `objects/pcb/*` — one class per file · `pcb_basis.py` the index · `pcb_seed.py` the DKRed seed (everything else observed)
- `custom/sexpr.py` — brd-bo's s-expression reader/writer, extended with `find_all`/`check_kicad` for `.kicad_sch`/`.kicad_pcb`
- `custom/kicad_read.py` — a KiCad project → row dicts, NO engine (pure Python over the s-expressions)
- `custom/fab_rules.py` — DKRed's constraints (cited https://www.digikey.com/en/resources/dkred): the rule rows, a
  `.kicad_dru` generator, Polari's own row check (`check_board`), and export-naming verdicts (`naming`)
- `custom/pcb_engines.py` — the engines seam: `PCB_ENGINES_URL` → local `kicad-cli` → the local image
  `PCB_ENGINES_IMAGE` (`prf-pcb-engines:trixie`) → topology provider `pcb.engines` → refusal naming the knob; also
  fetches one official library entry (`library()`) for the schematic writer to embed
- `custom/ingest.py` — `pol pcb ingest`: rows (always) + every kicad-cli check/export through the ladder (a record +
  the exported files under `POLARI_PCB_HOME/<board>/`), DrcResult/FabricationExport rows FROM that record
- `custom/schematic_writer.py` — writes a `.kicad_sch` DIRECTLY from rows (D-pcb-1): power symbols + net labels at
  each wired pin, a PWR_FLAG per power net, unconnected pins left alone and reported — never hidden
- `custom/uno_shield.py` — the UNO shield's design from brd-bo's rows (headers = the UNO's Connector rows minus
  ICSP; TMP36/220 Ω/LED as kit parts)
- `pcb_api.py` (`/api/pcb` summary, `/api/pcb/engines`, `/api/pcb/ingest`, `/api/pcb/render/uno-shield`,
  `/api/pcb/artifacts/{board}/{path}`), `pcb_endpoints.py` (the manifest `endpoints` constructor), `pcb_page.py`
  (`/display/board-schematic`, `board-layout`, `board-bom`, `board-fab`, configured tables only)
- the worker image: `polari-rf-node/prf-pcb-engines/` (Debian trixie pinned by digest + `kicad` + `kicad-symbols` +
  `kicad-footprints`, **not** `kicad-packages3d`), `docker-compose.pcb-engines.yml` (if added), provider
  `pcb.engines` → `prf-pcb-engines` :9860

## CLI

```
pol pcb engines                               where kicad-cli WOULD run (the ladder; nothing run)
pol pcb ingest <path> [--board B]             a KiCad project dir → rows + ERC/DRC/exports through the ladder
pol pcb render-schematic uno-shield           the UNO shield skeleton (.kicad_sch) + sch erc through the ladder
(with a server: POST /api/pcb/ingest {path|files}, POST /api/pcb/render/uno-shield, GET /api/pcb, /api/pcb/engines,
 GET /api/pcb/artifacts/<board>/<path>)
```

## Selftest

```
pol modules selftest pcb
PYTHONPATH=.:modules python3 -m pcb.pcb_selftest        # on the host, from polari-framework/ — 35/35: classes, s-expr
                                                         # round trips on a real small .kicad_sch/.kicad_pcb (the stored
                                                         # ecc83-pp fixture), the 20 DKRed rules, export naming, the
                                                         # engine refusal (offline), the schematic writer on a fake library
cd /tmp/x && PCB_ENGINES_URL=http://<isle-core>:9860 PYTHONPATH=<fw>:<fw>/modules python3 <fw>/tests/pcb_probe.py
                                                         # 30/30: a REAL live boot (board + pcb together, brd-bo
                                                         # unchanged) + the real ingest/ERC/DRC/exports through the
                                                         # worker, byte-stability, the UNO shield's ERC — skips the
                                                         # worker-only checks honestly if PCB_ENGINES_URL is unset or
                                                         # unreachable
```

Conformance: `PYTHONPATH=.:modules python3 -m moduleService.manifests conform pcb`.

## Costs + licences

See `COST.md` for the measured numbers (image size, kicad-cli wall/CPU/RSS per verb, a whole-board ingest, the
byte-stability proof). Licences: KiCad GPL-3.0 (engine only, never linked); `kicad-symbols`/`kicad-footprints`
CC-BY-SA-4.0 with the design exception (our designs and Gerbers are free of the share-alike); the stored `ecc83-pp`
demo GPL-2.0-or-later (compatible); DKRed's constraints are cited, never copied as a table of someone else's IP.

## Owed (not pcb-0's scope)

A person placing/routing a board in KiCad and `pol pcb ingest`ing Placement/Route rows from it (pcb-2); the UNO
shield's own `.kicad_pcb` (pcb-2); SMD land-pattern derivation vs a KiCad footprint (pcb-3); Order/Quote rows and the
forge-published design repo (pcb-4); the iCE40 FPGA companion board (pcb-5); KiCad/FreeCAD as Polari-managed native
apps (pcb-na, §5b).
