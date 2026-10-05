# hwnocode — hardware as no-code (hn-0)

His ask (2026-10-03): *"incorporate the capability for hardware to be done as no-code … interwoven with the work we have done so
far … suggestions … whether a user should leverage straight C, FreeRTOS, or Zephyr."* Plan: `AI-Notes/plans/HARDWARE_NOCODE_PLAN.md`
(D-hn-1..6 ruled 2026-10-03). **ONE no-code model**: hardware adds node KINDS to the existing canvas, compiler seam, engine and
configured displays — not a second system.

**Kind:** polari-app · **requires:** board, cmod, grpcbridge · **engines:** none for placement / split / suggestion / the backend half;
`make` (build) and the simavr twin (the proof) through the board engines seam · **new image:** 0 MB.

## The model

| piece | what it is | stands on |
|---|---|---|
| `HardwareSolution` | one solution across board, bridge, backend, browser: `solution` (the canvas SolutionDefinition), `cgraph` (D-hn-1: the hardware SUBGRAPH stays cmod's rows), `board_definition` / `board_instance`, `interface` (the split point), `displays`, **`firmware_runtime`** (the person's knob) + derived placement / split / proof / costs | cmod `CGraph`, grpcbridge `HardwareInterfaceBinding`, `SolutionDefinition`, `DisplayDefinition` |
| `HardwareNodePlacement` | where ONE node runs and why (derived, never typed) | the placement rule |
| node kinds `HardwareSubgraph`, `HardwareInterface`, `CAtom` | the canvas kinds (D-hn-2); each declares a `statePalette` that GET /stateSpaceClasses returns, so the palette learns them as data | `polyTypedObject.getStateSpaceConfig` |
| `SimRigTempSample`, `SimRigTempDerived` | the split app's backend rows: a ring of samples (temp_c + moving average) and the derived state (average + `over_threshold`) | written by the engine's own nodes |
| `hn-split` | a `GraphCompilerDefinition` row: placement → board half through `cmod-glue` (unchanged output) + backend half as its own SolutionDefinition | `polariNoCode.graph_compilers` |

**The placement rule** (`custom/placement.py`, plan §2b): c-atom / glue kinds / a HardwareSubgraph → `board` (`twin` while no
BoardInstance is attached); the hw-interface → `bridge` (the generated Java bridge — the ONLY place board ⇄ backend may cross); engine
state classes → `backend`; displays → `browser`. A Python node on the device side — wired to a device node without crossing a
hw-interface, or a non-C kind inside the CGraph — is **refused, named**, with the way out ("move it across the hw-interface"); a
device→backend edge without a hw-interface is refused naming the edge.

**`firmware_runtime`** (`custom/knobs.py`): bare-c | freertos | esp-idf | zephyr. hn-0 renders **bare-c** only; `auto` is refused
(D-hn-3: suggest only), an RTOS on an S-class board is refused for the RAM, elsewhere as not-yet-a-graph-target (hn-5). The seed
never converges it (it stays the person's).

**The suggestion** (`custom/suggest.py`, plan §3): features from the rows (memory class, activities/scopes, blocking atoms read from
the POLARI_NODE role — the cmod `blocking` verdict is hn-1, radios, ISR-shared globals, the measured cost) → the ordered rule table
→ a suggestion with EVIDENCE rows. It never writes the knob.

## The split app `uno-temp-split` (variant h over the existing peripheral, variant b)

```
sim-rig           HardwareSubgraph → CGraph uno-sim-rig-graph (UNCHANGED)               twin   (C, 18 CGraph nodes below it)
uno-digital-twin  HardwareInterface → binding uno-temp-split/SimRigState/0              bridge (the split point: the twin's
                  (HARDWARE_MODE knob: the twin's pty, or the detected board's serial)          pty, or a detected board)
on-temp      BackendStateChange  SimRigState update                                     backend ┐ the backend half =
moving-avg   AnalysisCall  hwnocode-temp-derive (ring + moving average over `window`)   backend │ uno-temp-split.backend,
over?        ConditionalChain  temp_avg > threshold_c                                   backend │ run per frame by the
flag-on/off  VariableAssignment  over_threshold = true | false                          backend │ EventTrigger
commit       StateChangeCommit  SimRigTempDerived ← temp_avg, over_threshold, …         backend ┘ uno-temp-split-on-temp
/display/hardware-solutions  3 configured tables + a GraphDefinition chart (named-graph-panel)  browser
```
Knobs (window 5, threshold_c 25.0, keep 600) are on the trigger's `inputs_json`. The chart is a GraphDefinition row (x uptime_s,
y temp_c + temp_avg) fed by `GET /api/hwnocode/solutions/uno-temp-split/chart` — the graphs design's sanctioned path
(`sci-xy-chart` is the data-in component under bespoke pages, not a display component; no new component).

## CLI · API · page

```
pol hwnocode solutions | place <s> | render <s> [--work W] | build <s> [--work W] | suggest <s> | runtime <s> <value>
pol board twin uno up --work W --adc0-ramp 700,800,8000          # runs the build `pol hwnocode build` wrote
GET /api/hwnocode · /solutions · /solutions/{s} · /solutions/{s}/placement · /render · /suggest · /chart · /interface?binding=
/display/hardware-solutions
```

## hn-0 measured (2026-10-03, pol-core, prf-board-engines:trixie, no UNO attached — the real-UNO replay is his)

- **render**: the board half's files = cmod-1's committed record, file by file (files_sha256 `926ae056…`, graph `e5ea718e…`);
  **build** (make alone, 0.6–2.5 s, 27 MB RSS): `.hex 4188f6ae…` **byte-identical** to cmod-1 (.text 4302 / .data 8 / .bss 483;
  flash 4310 B, RAM 491 B).
- **twin proof** (`tests/hwnocode_probe.py`, 18/18): the server's own header for bridge uno-temp-split = the glue's
  `simrigstate_packets.h` (the pinned v2 ledger restored as v1 → v2, same tag order); the bridge decodes **9.94 frames/s**; the backend
  half **10.27 rows/s = 10.00 per firmware-second** (94/94 firings ok, lag 0 ms after a 4.6 s catch-up); the average follows the
  20→30 °C ramp (20.02 … 29.39 °C) and `over_threshold` is seen false AND true; the chart returns 258 rows of both series; a REST PUT
  `{led_on: true}` → Commands → firmware → `status=commanded` in **0.15 s**, PORTB5 high in simavr.
- **costs**: the engine per frame 7.8 ms (one core: 7.8 % at 10 Hz); a firing under load 55 ms mean (≈ 14 row saves per frame: the
  trigger + firing rows, the pushed row + its stability profile, xsim-2's queue entry ×3 / lease ×2 / lock rows ×2.8, the sample, the
  derived row); bridge RSS 92 MB; server peak 206 MB; mvn package 6 s.
- **the storage finding** (`--db disk`, 16/18): one sqlite commit is **10.8 ms on pol-core's disk vs 0.06 ms on tmpfs**; with ≈ 14
  synchronous commits per frame the backend half sustains **2.65 Hz** on disk — every frame is processed (9.6 per firmware-second) but
  the queue lags (48.9 s after 9 s) and, because the trigger runs in the gRPC push path, the row and the PUT echo lag with it (the
  command still reaches the firmware: PORTB5 high). The proof above runs the throwaway DB on tmpfs (`--db tmpfs`, the default when
  /dev/shm exists). Not fixed in hn-0 — the levers (a tied long-lived run per solution instead of one gated run per frame; object
  triggers off the push thread; batched firing rows for high-rate triggers) are core changes for a later slice.

## Selftest / probes

```
PYTHONPATH=.:modules python3 -m hwnocode.hwnocode_selftest          # 55/55: placement + refusals, the subgraph reference,
                                                                    # knob refusals, the suggestion on fixtures (rules 1/2/3), the
                                                                    # backend half in the REAL engine, palette, seeds/page/API, conform
cd /tmp/x && PYTHONPATH=<fw>:<fw>/modules python3 <fw>/tests/hwnocode_probe.py [--db tmpfs|disk] [--record] [--record-costs]
cd /tmp/y && PYTHONPATH=<fw>:<fw>/modules python3 <fw>/tests/hwnocode_liveboot_probe.py [--all-modules]
PYTHONPATH=.:modules python3 -m moduleService.manifests conform hwnocode
```
The split record (render + build + proof + costs, both DB modes) is `custom/splits/uno-temp-split.json`; the seed projects it into the
HardwareSolution row (nothing is rendered or built at boot).

Not in hn-0 (plan §7 rows hn-1..5 / owed): the RuntimeSuggestion + HardwareSuggestion ROWS and the cmod `blocking` verdict (hn-1); the
cmod edge kinds `field-cmd` / `deadband` (they change cmod's renderer — cmod stays unchanged here); `polari_propose_hardware_solution`
(MCP); the `register` overlay; the standalone variant (hn-2).
