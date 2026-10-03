# cmod — C modularization (cmod-0 + cmod-1)

His ruling (2026-10-02): people write hardware C **normally**, and Polari embeds it into no-code like custom Python —
"modularization of C code into polari is likely going to be a critical part of functionality". Plan:
`AI-Notes/plans/C_MODULARIZATION_PLAN.md`. **No C↔Python transpiling.**

A firmware project stays a NORMAL C project (`*.c`, `*.h`, a Makefile) that builds with `make` and the toolchain with
Polari absent. Polari DERIVES its **atoms** — C functions with ports, the resources they touch and their cost — by parsing,
never by hand:

| what | how |
|---|---|
| parser | pycparser 2.21 (BSD-3) in the framework process — already in the image for cffi; its bundled PLY preprocessor (`custom/preprocess.py`, two fixes: `!=` in `#if`, `#line` per file) + fake avr-libc headers (`ISR(v)` → `__polari_isr_v`, `ATOMIC_BLOCK` → a marked `if`) |
| atom | a function defined in one of the project's `.c` files; an ISR by its vector; `main` = kind `entry`; header functions (the generated `<class>_packets.h`) are library |
| ports | by value = in; const pointer = in; pointer only written through = out; read+written or handed on = inout; non-void return = out(return). C type → AVR width → Polari type (int64 / double / bool / string / bytes / ref:<Type>) |
| resources | registers by avr-libc's own names (`custom/registers_atmega328p.json`, derived from `<avr/io.h>` with `avr-gcc -E -dM`) → peripheral; file-scope globals (r/w, volatile, width, shared with an ISR); EEPROM / WDT / SREG.I library calls; `uses()` from the annotation |
| verdicts | pure (no global/register/resource, pure callees); ISR-safe (a >1-byte ISR-shared global outside an ATOMIC_BLOCK = the torn read; a 1-byte RMW while an ISR writes = a lost update; propagates to callers) |
| cost | the project's own Makefile flags + `-fstack-usage`: shipped (text in the firmware; 0 when inlined or gc'd) and `-fno-inline` (text as a node); `nm -S --size-sort`; the `.su` frame |
| manifest | `polari-firmware.json` beside the Makefile — conformed, never hand-maintained (hand-set: title / description / notes, per atom title / notes); written only when something derived changed |

The annotation is optional and changes no byte (hal.h: `#define POLARI_NODE(...)`):

```c
POLARI_NODE(hal_adc_read, in(channel, "", "A0..A5 (0..5)"), out(return, "count", "10-bit ADC = Vin*1024/Vref, 0..1023"),
            role("one blocking ADC conversion, AVcc reference"))
uint16_t hal_adc_read(uint8_t channel)
```
or, in a file that must not depend on our header, `/* @polari-node(name, in(…), out(…)) */`. A malformed one is refused.

```
pol cmod atoms uno | <dir>         parse now (no engine)
pol cmod conform uno | <dir>       parse + measure → polari-firmware.json (a second run: unchanged)
pol cmod show hal_millis           one atom: ports, resources, ISR-safety, cost
pol cmod drift uno                 the committed manifest vs the sources
pol cmod registers [--refresh]     the register snapshot
GET /api/cmod · /projects · /atoms[?project=&kind=] · /atoms/{atom} · /ports[?atom=] · /engines · /projects/{p}/drift
/display/c-atoms                   5 configured tables (projects, atoms, ports, costs, modules)
```

**cmod-0 measured (2026-10-02, avr-gcc 14.2.0, prf-board-engines:trixie):** the UNO template = 34 atoms over 6
configurations (uno-sim-rig, uno-blink-only, uno-adc-sweep, uno-echo + two coverage configurations turning every sc-1 knob
on), 32 ports, 3 ISRs, 2 pure, 12 annotated, 0 not ISR-safe; the torn build (HAL_MILLIS_ATOMIC=0) → hal_millis and main
not ISR-safe. The 12 annotations leave every .hex byte-identical (17/17 builds: the 5 seeded variants, uno-pair ×2 and the
11 scenario variants incl. the one refused build). `make` alone builds all 6 configurations; uno-sim-rig's .hex = board's
own (4188f6ae…). A conform: ~16 s (12 compiles + 12 nm + 6 make, all on the local image); a parse alone: ~0.9 s.

Selftest `pol modules selftest cmod` (fixtures, refusals, idempotence, the UNO, seeds/page/API, manifests conform);
probe `tests/cmod_liveboot_probe.py` (live boot + the byte-identical proof through the engines).

## cmod-1 — a no-code graph over atoms → generated plain-C glue (always a real C project)

A `CGraph` (rows: `CGraphNode`, `CGraphEdge`) wires atoms; `custom/glue.py` renders it into a project COMMITTED in the repo
(D-cmod-4) that `make` alone builds — no Python at run time, no interpreter, no table walked at run time:

| node kind | what the glue does with it |
|---|---|
| `c-atom` (stage init / loop / called) | calls the atom BY NAME; in ports from data edges or bindings (`channel=ADC_CHANNEL`: a literal or a header macro, never free C); `called` = the caller atom calls it itself (a `calls` edge, checked against the derived calls) |
| `class` | the class instance (`static SimRigState_t state;`), zeroed, identity + initial status set before `sei()` |
| `parser` | the generated header's receiver; an `on-rx` edge drains a byte source into it, `on-command` runs atoms on a complete frame of the class's msg_type |
| `tick` | `if ((int32_t)(now - next) >= 0) { next += period; … }` on a uint32_t ms clock |
| `rule` | `after-ms`: a field from → to once the clock passes N ms (the sim rig's boot → ok) |
| `frame` | `<Class>_encode` with the listed fields + `<Class>_frame` + a sequence counter into static buffers |

Edges: `data` (out → in, Polari types must agree), `field` (out → class field, optional scale/offset), `tick`, `on-rx`,
`on-command`, `calls`. REFUSED (`custom/graph.py`, with the reason): a data cycle, an unbound or doubly-bound in port, a type
mismatch, free C in a binding, an unknown atom, an ISR or main as a node, an atom not compiled in the base configuration, a
`calls` edge the C does not have, a field written after the frame that sends it, a node fed from two ticks.

The rendered project: `polari_graph.c` (GENERATED glue + the app atoms copied VERBATIM with their POLARI_NODE line and
enclosing `#if` — an app file holds a main(), so it is never compiled whole), `polari_graph.h` (graph name + sha, frame masks,
every file's provenance sha), `Makefile` (the template's flags; SRCS listed), `hal.c`/`hal.h` verbatim, `board_config.h` and
`<class>_packets.h` rendered by board's own gen. Each generated file names the graph, its sha and `pol cmod render <graph>`;
a hand edit shows in `pol cmod diff` and is never overwritten without `--force`. The record (files + shas, the cost estimate,
make alone, the twin proof) is `custom/glue_builds/<graph>.json` → the `CGlueBuild` row.

```
pol cmod graphs                 the graphs and their state
pol cmod cost   <graph>         the cost BEFORE building: atoms as nodes + the ISRs they share globals with + the replaced main
pol cmod render <graph> [--force]   rows → the committed project (only what changed)
pol cmod diff   <graph>         the graph changed / hand edits / stale files (unified diffs)
pol cmod build  <graph>         make ALONE through the board engines → .hex, avr-size, the measured cost; conform reads it back
pol cmod prove  <graph>         hand-written app vs rendered glue on the simavr twin, same stimulus → frames field by field
GET /api/cmod/graphs · /graphs/{g} · /graphs/{g}/render (in memory) · /graphs/{g}/diff
```
The generator is also the `cmod-glue` GraphCompilerDefinition (polariNoCode.graph_compilers): artifacts only — a C graph never
runs in the engine (RULE 2).

**cmod-1 measured (2026-10-02, prf-board-engines:trixie, avr-gcc 14.2.0, libsimavr 1.6):** `uno-sim-rig-graph` (18 nodes, 15
edges, 13 atoms) renders the sim-rig app; `make` alone builds it — and its .hex is **byte-identical** to the hand-written
uno-sim-rig (4188f6ae…, .text 4302 / .data 8 / .bss 483 for both). On the twin (4 s, seed 1, ADC0 700→800 mV triangle,
three commands at 1.5 / 2.25 / 3.0 s) both emit **40 frames identical on seq, device_id, msg_type, uptime_ms, temp_c, led_on,
pwm_duty, status, name**; the raw UART streams are identical and every frame leaves the UART on the same cycle (Δ 0). A
negative control (the status rule at 500 ms) is caught: 5 status differences. Cost before building 3144 B (atoms as nodes
644 + ISRs 136 + the replaced main 2364) vs 2874 B attributable after (the 270 B gap = exactly apply_command 192 +
sensor_value 48 inlined and hal_millis 30 B smaller shipped) + 1428 B C runtime. Conform reads the rendered project back
as a plain project: 16 atoms incl. the glue's own `polari_graph.main`.

Not in cmod-1: a presence-gated command FIELD → atom port edge (the hwsim-nocode FieldRegisterBinding without an apply atom —
the sim rig keeps apply_command, which does it in C), `deadband` on field edges, graphs over a plain (non-template) project,
host execution via cffi (cmod-2), the canvas overlay for a `c-atom` node (cmod-3). Ports of pointer-to-byte parameters stay
`bytes` unless an annotation says more (it cannot yet set a Polari type).
