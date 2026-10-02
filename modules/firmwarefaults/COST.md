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

# sc-1 (2026-10-02, `dev-sc-1`) — five single-board pairs, the space/safety rows, the statistics tier

Same host. Every number below is from a run on the simavr twin (`prf-board-engines:trixie`, harness `twin_forcing.c` +
`twin_scenario_io.c`); a re-run from the row + seed reproduces it (the S2 pair re-runs bit-identically: firmware + UART sha256).

## The harness and image delta

| what | after sc-0 | after sc-1 | how |
|---|---|---|---|
| harness C | 325 + 472 + 36 lines | 325 + **583** (twin_forcing.c) + **469 + 38** (twin_scenario_io.c/.h) + 36 | `wc -l` |
| image `prf-board-engines:trixie` | 534 787 909 B | **534 804 667 B (+17 KB)** — only the larger twin binary (no new package; `-lm`); `docker build --no-cache` 72.5 → **73.3 s** | `docker image inspect` |
| 10 s of firmware with the per-instruction step | 2.24 s (sc-0's flags) | **2.83 s** with sc-1's (+ the host/power-rail checks, the TX log); free-running unchanged 84–86 M cycles/s (1.91 s) | harness `exit` / `--bench` |
| one sc-1 forced run (0.5–2 s of firmware) | — | **0.10–0.45 s** inside the harness; ≈ 1.5–2 s end to end (docker start + the log decode) | run `wall_s` |
| one sc-1 pair end to end (gen + build both variants through the image, disassemble, static stack, two runs) | — | **≈ 10–20 s**, dominated by `docker run` per engine call | `pol faults run <s> --both` |
| statistics: one S4 run (500 commands + 128 B idle tail, 3.03 s of firmware) | — | **≈ 2 s** end to end; 20 seeds per (side, BER) 33–54 s; the whole 3-BER x 2-side batch **242 s** for 120 runs | ScenarioStatistic `wall_s` |
| statistics: one phase-sweep run (10 s of firmware, every tick logged) | — | **≈ 3 s** end to end (2.7 s in the harness); 60 seeds ≈ 3 min | same |

## The pairs (seed 0; AFTER − BEFORE is the technique's cost; plan §4 space/safety on every run)

| scenario | BEFORE (decisive line) | AFTER (decisive line) | technique cost |
|---|---|---|---|
| S2 `lost-ack-hang` | `uno-ack-wait`: ack #1 dropped on the host→board line at cycle 8 018 442; last telemetry 408.3 ms, the request at 503.2 ms, then **silent 1 591.7 ms** to the end (ack state 1 = waiting) → **refuted** | `uno-ack-wait-timeout`: the request **again at 553.2 ms (+50.0 ms)**, acked; worst telemetry gap 103.0 ms → **witnessed** | `timeout-fsm`: **+80 B flash, +4 B RAM, 28 cycles per `ack_step()` pass** (entry → return, `--fn-cycles START:ret`); stack 131 → 126 B |
| S3 `button-bounce-double-count` | `uno-button-count`: INT0 raised at cycles 8 000 001, 8 000 303 (the ring, 18.75 µs later) and 8 800 000 (a real press) → **g_presses = 3 for 2 presses** → refuted | `uno-button-debounce`: **2 for 2** (the ring ignored, the real press counted) → witnessed | `debounce-synchroniser`: **+130 B flash, +5 B RAM, INT0 ISR 27 → 114 cycles max (+87)**: the 32-bit `now - last` compare in the ISR; stack 116 → 124 B |
| S4 `uart-residual-frame-loss` | `uno-echo-uartstat` (the shipped resync parser): the false start + A + B (62 B from cycle 4 800 002) → **1 applied / 2 intact / 2 sent** → refuted | `uno-echo-keeptail` (`rx_parser keep-tail`): **2 / 2 / 2** → witnessed | `rescan-keep-tail`: **+76 B flash, +4 B RAM** (rx->tail, rx->used); not timed — polari_rx_feed is inlined into main |
| S5 `brownout-mid-eeprom-write` | `uno-eeprom-record`: old 0x11111111 preloaded, the command for 0x22222222, `avr_reset()` at the **3rd entry of eeprom_write_byte** (cycle 4 941 337) → boot reads **0x11112222** → refuted | `uno-eeprom-commit`: boot reads **0x11111111 (the old record)** → witnessed | `write-then-commit`: **+408 B flash, +2 B RAM**; EEPROM 4 → 12 B per record, 4 → 6 byte writes (≈ 3.4 ms each on silicon); stack 121 → 133 B |
| plan §4 `runaway-hang-watchdog` | `uno-sim-rig`: PC set to `_exit` (cli; rjmp .) at 500 ms → **no frame for 1 589.4 ms** (last 410.7 ms), 0 resets → refuted | `uno-sim-rig-wdt`: **one watchdog reset at 756.0 ms (cycle 12 095 934, MCUSR WDRF = 1)**, telemetry back at 766.9 ms (+266.9 ms after the hang) → witnessed | `watchdog`: **+300 B flash, 0 RAM**: `.init3` (MCUSR = 0; wdt_disable) 24 B + `wdt_enable`, and GCC laid `main` out 224 B larger with the kick at the loop top (0x93c → 0xa1c) — the WDT itself is small, the codegen shift is not; one `wdr` (1 cycle) per pass |

**EEPROM persistence across `avr_reset` (sc-0: assumed) — VERIFIED:** the S5 control run resets at cycle 6 400 000, after the 4 writes
completed; the record read at boot is **0x22222222** (`pol faults run brownout-mid-eeprom-write --control`). SRAM is re-initialised by the
C runtime after the reset (g_rec_writes reads 0).

**Not forcible on the UNO:** `priority-inversion-mutex` and `two-lock-deadlock` (no RTOS: no tasks, mutexes or preemption) — rows with the
recipe (`hold-lock-order`), refused with `not-yet-forcible: needs FreeRTOS (ESP32-C3 — his "STM32-C3" still to confirm) or Zephyr (SAMD21)`;
nothing is built.

## Statistics (ScenarioStatistic rows, Wilson 95 %, pooled over the seeds)

**S4 under `--uart-ber`** — 500 back-to-back 25-byte commands per run, 20 seeds per BER, the SAME seeds on both sides (paired: the line
destroys the same bytes), intact = an offline greedy scan of the bytes that reached the board (max payload 93, like the board):

| BER | BEFORE lost / 10 000 (per 1000) | BEFORE residual (the parser's own loss) | AFTER lost (per 1000) | AFTER residual |
|---|---|---|---|---|
| 1e-3 | 2 042 = **20.42 %** [19.64, 21.22] (204.2) | **23 = 0.230 %** [0.153, 0.345] — 1.1 % of the losses | 2 019 = 20.19 % [19.41, 20.99] (201.9) | **0** [0, 0.038 %] |
| 1e-4 | 250 = **2.50 %** [2.21, 2.82] (25.0) | **4 = 0.040 %** [0.016, 0.103] | 246 = 2.46 % [2.17, 2.78] (24.6) | **0** |
| 1e-5 | 23 = **0.23 %** [0.15, 0.34] (2.3) | 0 [0, 0.038 %] | 23 = 0.23 % (2.3) | **0** |

The line's own loss agrees with the bit model: 9 destructive bits per byte (8 data + the start bit; a flipped stop bit is a framing error with
the data intact) → 1 − (1 − p)^225 = 20.1 % / 2.22 % / 0.225 % for one 25-byte frame. FE0 counts and zero DOR0 / ring drops are on every run
(`HAL_UART_ERRCOUNT`); each stream ends with 128 idle zero bytes so no candidate is left waiting for a corrupted length at the end. Found on the
way: board's reference `StreamParser` (max payload 1024) undercounts at the end of a stream (it waits for a corrupted length's bytes) — it is
not an ideal reference, so `payloads.ideal_frames` is.

**Scenario 1's phase sweep** (`uno-sim-rig-torn`): see the rows `torn-millis-read@natural@ret-log` and `torn-millis-read@before@rx-noise=200`
— numbers in the next block.

| row | result |
|---|---|
| `torn-millis-read@natural@ret-log` (seed 0, no stimulus, 10 s, EVERY tick's return PC via `--ret-log 7`) | the 2nd lds of g_ms (`hal_millis+0x4`) takes **290 of 9 999 ticks = 2.90 %** [2.59, 3.25]; inside the carries' own residue classes (g_ms mod 100) **74 of 2 499 = 2.96 %**; the 39 carries land on 15 different PCs, none there — **P(0 of 39 \| 2.90 %) = 0.32** |
| `torn-millis-read@before@rx-noise=200` (60 seeds x 10 s, asynchronous 0x00 bytes at 200/s, exponential gaps from the seed) | **73 tears in 2 340 carries = 3.12 % per carry** [2.49, 3.90]; every tick 17 059 / 599 940 = 2.84 %; cross-check: 72 backwards frames + 1 torn FINAL frame (seed 22: the tear at the last carry, 9 983 ms → a frame of 10 239; the frame that would go backwards is due at 10.1 s, after the window) = 73 |

**Settled: sc-0's natural 0/39 was chance, not phase lock** — the exposure (2.90 %) lies inside the per-carry interval, the carries'
residue classes are exposed like any tick, and a 39-carry run sees no tear 32 % of the time. The measured per-carry probability
(3.12 % [2.49, 3.90]) is on the TornReadFault row. (An earlier 20-seed batch read 33/780 = 4.23 % [3.03, 5.88] — just above the
exposure; the 60-seed batch is the one recorded. Both numbers are kept here; the plan's ≈ 13 % counted three gaps.) Wall: the natural
run 2.7 s, the 60-seed sweep ≈ 3 min.

## Rows (sc-1)

25 classes (+ `ScenarioStatistic`); fields added: ScenarioRun `observable_value`, `reset_count`, `isr_cycles_max`, `isr_cycles_vector`;
Technique `measured_ram_bytes`, `measured_cost_what`. Seeded now: 17 fault rows (LivelockFault `runaway-hang` added), 6 primitives,
13 assumptions (`main-loop-returns`), 11 techniques (`rescan-keep-tail`), 9 scenarios, 14 steps, 11 scenario FirmwareVariants. Per sc-1 pair:
2 ScenarioRun + 2 MathClaim + 2 ProofRun rows (no trace window — the decision is the observable); a statistics batch: one ScenarioStatistic per
(side, parameter) + the fault row's measured rate.
