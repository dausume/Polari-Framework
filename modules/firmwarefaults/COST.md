# firmwarefaults — measured cost (the cost rule; FIRMWARE_SCENARIO_PLAN.md §8)

Measured on pol-core (Intel Core i5-4590 @ 3.30 GHz, 4 cpus, 16 GB) on 2026-10-02.

## The harness and image delta (prf-board-engines)

| what | before sc-0 | after sc-0 | how |
|---|---|---|---|
| image `prf-board-engines:trixie` | 534.7 MB (534 669 380 B) | **534.8 MB (534 787 909 B), +0.12 MB** (pyvcd 0.5.0 wheel + `polari-vcd-window` + the larger twin binary) | `docker image inspect` |
| `docker build --no-cache` (base local) | 46.1 s | **72.5 s** (python3-pip in the BUILD stage only — the final image does not carry pip) | `time docker compose … build --no-cache` |
| harness C | 311 lines | 325 + **twin_forcing.c 472 / .h 36** (the plan estimated 250–400 added) | `wc -l` |
| free-running speed (no scenario flags) | 78.6 M cycles/s (2026-10-01) | **86.5 M cycles/s** (`--bench 160000000`, 2 runs; same code path — host load differs) | harness |
| 10 s of firmware, no flags | — | **1.79 s wall** | harness `exit` line |
| 10 s with the per-instruction step (`--sp-watch --isr-latency --stack-fill --fn-cycles --watch --uart-out`) | — | **2.24 s wall (+25 %)**; the plan guessed 2–5x | same |
| one forced scenario-1 run (0.6 s of firmware, VCD window 48:160) | — | **0.16–0.17 s** inside the harness; ≈ 1 s per run end to end (docker start + avr-objdump/avr-nm + pyvcd) | runner `wall_s` |
| twin peak RSS | 11.2–11.5 MB | **11.9 MB** with the step + trace ring | harness `peak_rss_kb` |
| one VCD window (104–208 samples) | — | **≈ 4.7 KB** | file size |
| one pair end to end (gen + build both variants through the image, disassemble, static stack, two runs, pyvcd) | — | **≈ 10 s wall**, dominated by `docker run` per engine call | `pol faults run torn-millis-read --both` |

## What the pair measured (scenario 1, seed 0)

| | BEFORE `uno-sim-rig-torn` | AFTER `uno-sim-rig` | delta (the technique `atomic-block`) |
|---|---|---|---|
| flash (.text + .data) | 4304 B | 4310 B | **+6 B** (plan: +6 B) |
| static RAM | 491 B | 491 B | 0 |
| `hal_millis` entry → `ret`, uninterrupted | 8 cycles | 11 cycles | **+3 cycles** (plan: +3) |
| worst natural ISR latency (vector 7, 599 ticks) | 0 cycles | 14 cycles | **+14 cycles** (plan estimate ≈ 9: it left out the `ret` and the one instruction simavr runs after `out SREG` re-enables I) |
| stack high-water (SP watch = 0xA5 paint) | 119 B | 119 B | 0; static peak 131 B (`-fstack-usage` + call graph: main 119 B + the largest ISR 12 B; libgcc float/division routines and strcpy/memmove not counted, listed) |

Latency is measured from the vector's flag raised (`AVR_INT_IRQ_PENDING`) to the vector taken (`AVR_INT_IRQ_RUNNING`) in simavr
cycles; simavr adds the vectoring cycles after that point, so the absolute number is a lower bound and the DELTA is the reading.

## The natural rate (no forcing, 10 s, BEFORE)

**0 torn reads in 39 byte-0 carries.** The twin is deterministic and the tick shares the CPU clock, so every run from reset repeats
these same 39 carries at the same phases. Exposure if the phase were uniform (asynchronous RX traffic): **2.83 % per carry** =
2 cycles of load 1 × 2 264 582 `hal_millis` calls / 160 001 572 cycles → 1.1 tears expected in 39 carries (P(0) = 0.33), so 0/39
alone cannot separate a locked phase from luck — the seed phase sweep is sc-2. The plan's ≈ 13 % counted three gaps; at a byte-0
carry only the load-1 → load-2 gap tears.

## Rows

24 classes; seeded: 16 fault rows + 6 primitives + 12 assumptions + 10 techniques + 2 scenarios + 2 steps + 2 FirmwareVariants
(50 rows). Per pair: 2 ScenarioRun + ≈ 2 × 53 ScenarioTraceCycle + 2 MathClaim + 2 ProofRun rows; a natural run adds 1 run,
1 claim, 1 proof run and updates the fault row.
