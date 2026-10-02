# cmod — C modularization (cmod-0)

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

Not in cmod-0: graphs over atoms + generated glue (cmod-1), host execution via cffi (cmod-2), ports of pointer-to-byte
parameters stay `bytes` unless an annotation says more (it cannot yet set a Polari type).
