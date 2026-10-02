# Firmware Faults (`firmwarefaults`) — sc-0 + sc-1 + sc-2 / sc-2b / sc-2c

Force a concurrency or physics bug ON PURPOSE on a firmware twin, see the cycle where it goes wrong, then see the technique
that makes it safe and what that technique costs. Plan: `AI-Notes/plans/FIRMWARE_SCENARIO_PLAN.md` (D-sc-1 ruled 2026-10-02:
its own module). **Requires** `board` (variants, builds, the twin), `grpcbridge` (the wire + the reference parser), `mathproofs`
(claims). Engines resolve through the **board engines seam** (`BOARD_ENGINES_URL` → local binary → `prf-board-engines:trixie` →
topology provider `board.engines` → refusal): `polari-avr-twin` with the scenario flags, `avr-gcc` (builds, `-fstack-usage`),
`avr-objdump`/`avr-nm`, `polari-vcd-window` (pyvcd).

**Rows** (one class per file): `FirmwareFault` + 16 KIND classes by family — `objects/concurrency/` (TornRead, DoubleGive,
LostWakeup, PriorityInversion, Deadlock, Livelock, Starvation), `objects/physical/` (UartBitError, DoubleEdge, MetastableInput,
BrownoutMidWrite, BitFlip, ClockSkew), `objects/space_safety/` (StackOverflow, BufferOverrun, MissedDeadline); `ConcurrencyPrimitive`,
`Assumption`, `Technique` (seeded cost + MEASURED cost), `Scenario`, `ScenarioStep`, `ScenarioRun`, `ScenarioTraceCycle` (the cycles
around the fault, so the page shows them in a configured table). Seeds: one row per kind (a rate is cited, measured, an estimate,
or `unverified`), the UNO's primitives, 12 assumptions, 10 techniques, scenario 1 + 1b and their steps, and two scenario
FirmwareVariants (`uno-sim-rig-torn` = `HAL_MILLIS_ATOMIC=0`; `uno-sim-rig-ring512` = `RX_RING=512`, refused by hal.c's
`_Static_assert`).

**Scenario 1 (`torn-millis-read`)** — the ring buffer cannot tear (uint8_t indices, one `lds` each); the 4-byte tick read can.
The runner builds BEFORE (`uno-sim-rig-torn`) and AFTER (`uno-sim-rig`), finds the 2nd `lds` of `g_ms` in each build's own
disassembly, forces TIMER2_COMPA (vector 7) there when `g_ms & 0xFF == 0xFF`, decodes the UART frames with board's reference parser
and reads the VCD window with pyvcd. BEFORE: `hal_millis` returns 511, uptime_ms goes 200 → 511 → 400 with every CRC fine → claim
**refuted** (counterexample cycle + PC). AFTER: the IRQ stays pending through `cli` and lands after `out SREG` → monotone → claim
**witnessed** (one interleaving, never a proof). The pair measures the technique: **+6 B flash, +3 cycles per call, +14 cycles worst
ISR latency**. **1b** (`rx-ring-over-256`) is a refused build → **inapplicable**. Step kinds the harness cannot force yet
are listed with the reason (since sc-1 only flip-bit-at-cycle, hold-lock-order and clock-skew); a scenario using one is refused, never
half-run.

**sc-1 — five single-board scenarios, each a BEFORE/AFTER pair of FirmwareVariants that differ in exactly the technique**
(C only, RULE 2; every knob default-off, so `uno-sim-rig` stays byte-identical, sha256 `4188f6ae…`):

| scenario | BEFORE → AFTER | forcing (twin flags) | decided by | technique |
|---|---|---|---|---|
| `lost-ack-hang` (S2) | `uno-ack-wait` → `uno-ack-wait-timeout` (app `scenario_rig`, `SC_ACK_WAIT` / `SC_ACK_TIMEOUT_MS`) | a scripted host answers each request (`--respond`), the 1st ack dropped (`--drop-frame rx:1`) | telemetry gap > 250 ms (hang) vs a retry + no gap | `timeout-fsm` |
| `button-bounce-double-count` (S3) | `uno-button-count` → `uno-button-debounce` (`HAL_INT0`, `HAL_INT0_DEBOUNCE_MS 20`) | INT0 raised at 500 ms, +300 cycles (the ring), +50 ms (a real press) | `g_presses` 3 vs 2 for 2 presses | `debounce-synchroniser` |
| `uart-residual-frame-loss` (S4) | `uno-echo-uartstat` → `uno-echo-keeptail` (`HAL_UART_ERRCOUNT`; header knob `rx_parser keep-tail`) | the documented residual: a false start reaching 10 B into frame B, then A, B (`--inject`) | commands applied vs an ideal offline parse of the delivered bytes | `rescan-keep-tail` |
| `brownout-mid-eeprom-write` (S5) | `uno-eeprom-record` → `uno-eeprom-commit` (`SC_EEPROM_RECORD 1/2`) | old record preloaded (`--eeprom-set`), a command writes the new one, `--reset-at` the 3rd `eeprom_write_byte` (simavr has NO brown-out model: a reset approximates the droop) | the record read at boot: a mix vs the old value | `write-then-commit` |
| `runaway-hang-watchdog` (§4) | `uno-sim-rig` → `uno-sim-rig-wdt` (`HAL_WDT 1`, WDTO_250MS, `.init3` clears MCUSR + the WDT) | `--jump-at` `_exit` (cli; rjmp .) at 500 ms | no frame after the hang vs a WDRF reset + frames again | `watchdog` |
| `priority-inversion-mutex`, `two-lock-deadlock` (S6/S7) | — | **not-yet-forcible**: no RTOS on the UNO; the recipe is written (`hold-lock-order`) for sc-3 (FreeRTOS on the ESP32-C3 — his "STM32-C3" unconfirmed — or Zephyr on the SAMD21) | refused with that reason, nothing built | `priority-inheritance`, `lock-ordering` |

Every sc-1 run records plan §4 space/safety too: stack high-water (SP watch + paint + static), worst ISR latency, each ISR's length,
sizes, resets (simavr's reset hook). `--control` on S5 resets AFTER the write completed: the new record is read at boot — **EEPROM
persists across `avr_reset` on the twin** (sc-0 had it as assumed). **Statistics** (`pol faults stats`, ScenarioStatistic rows, Wilson
95 %): S4 under `--uart-ber` (500 commands x 20 seeds per BER, paired BEFORE/AFTER, the residual counted apart from the line's own loss)
and scenario 1's phase sweep (every tick's return PC logged with `--ret-log`, then asynchronous RX traffic x seeds → torn reads per
carry, onto the TornReadFault row). Numbers: `COST.md`.

**Claims:** each run writes a mathproofs `MathClaim` (kind `safe-under-scenario`, checker `sim`) per (scenario, build) and a
`ProofRun`; failed → refuted, passed → witnessed, inapplicable → inapplicable, undetermined → undetermined. A refuted claim is never
flipped back by a later witness on the same build.

```
pol faults list                                   # scenarios (runnable or why not), step kinds, recorded runs
pol faults run torn-millis-read --both            # the BEFORE/AFTER pair + costs (local; --api URL runs it on a server)
pol faults run torn-millis-read --natural         # 10 s, no forcing: the measured rate onto the fault row
pol faults run lost-ack-hang --both               # any sc-1 scenario the same way
pol faults run brownout-mid-eeprom-write --control   # the EEPROM persistence check
pol faults stats uart-residual-frame-loss --seeds 20 # | torn-millis-read — the statistics tier
pol faults show <run>                             # the cycles around the fault + the claim
GET /api/firmwarefaults[/faults|/techniques|/scenarios|/runs|/runs/{run}|/engines|/statistics]
POST /api/firmwarefaults/run · POST /api/firmwarefaults/stats
/display/firmware-faults                          # configured tables only (sc-1 adds the statistics table)
```

**sc-2 — the STATISTICS tier as campaigns** (`custom/campaign.py`, `custom/campaign_runs.py`; rows `ScenarioCampaign`, `FaultLikelihood`,
plus sc-1's `ScenarioStatistic`): a campaign = scenario × fault kind × the fault's RATE as the stimulus × seeds × window. Each (side, rate,
seed) is one harness run (the SAME seeds on both sides); per rate: the likelihood WITHOUT the technique and the technique's RESIDUAL WITH
it (Wilson 95 %), the time to the first fault where a run can see it (censored seeds counted apart). Seeded: `torn-read-phase` (scenario 1,
async RX 200/s, 60 seeds — per byte-0 carry), `uart-ber` (scenario 4, BER 1e-3/1e-4/1e-5 — the parser's residual per command),
`bounce-window` (scenario 3, the bounce edge uniform in (0, W] for W = 0.02…40 ms — per press), `ack-drop-probability` (scenario 2, each
ack lost with p = 0.5/0.2/0.1 — per request; the AFTER give-up apart). A campaign writes the likelihood table (one FaultLikelihood row per
(fault, stimulus value)), the fault row's rate_source, and the claims' `statistics` evidence tier (the STATUS stays witnessed / refuted;
the likelihood + interval go into `MathClaim.measure_json`). Harness (sc-2): `--align-at-pc` (scenario 1 with NO extra tick — the next
genuine raise is swallowed; scenario `torn-millis-read-aligned`), `--flip-bit 0xADDR:BIT@CYCLE`, `--drop-frame tx:N[,type=0xTT]` (scenario
`lost-request-hang`) and `rx:p=P`, up to 64 `--irq-at`.

**sc-2b — the FORMAL tier, narrow, and the static rules** (`custom/formal.py`, `custom/static_rules.py`, `custom/formal_engines.py`; rows
`FormalCheck`, `StaticCheck`, `StaticFinding`): CBMC 6.6.0 and cppcheck 2.17.1 run in their OWN worker image `prf-formal-engines:trixie`
(CBMC is BSD-4-clause style — GPL-incompatible to link, so it is only ever a separate process), resolved by the ladder `FORMAL_ENGINES_URL`
→ local binary → the local image → topology `firmwarefaults.formal` → refusal naming the knob. A FormalCheck compiles the variant's OWN
generated hal.c (unedited) against `custom/cbmc_model/stubs/` with a harness that makes the interrupt CBMC nondeterminism
(`--nondet-volatile-model g_ms:…` = the AVR's four one-byte loads with a tick possible between any two while SREG.I is set, and `--isr`
between statements): `hal-millis-not-torn@uno-sim-rig` → **decided (bounded, k=2)**, never proved; `@uno-sim-rig-torn` → **refuted** with the
C trace (sha kept); `rx-ring-index-bound@uno-sim-rig` → decided (bounded, k=4 steps from any valid state); `@uno-sim-rig-ring512` →
**inapplicable** (hal.c's static guard refuses the source). Limits on every row: CBMC has no AVR arch — `--16` (int 16 bits as avr-gcc,
little-endian), 32-bit pointers, the byte-wise read is our model of the core (cross-checked by the twin). Each check adds the `formal`
evidence tier to the scenario's claim (mathproofs checker `cbmc`). cppcheck: built-ins (warning, style, portability, performance, avr8) +
the threadsafety addon on all 16 UNO variants — MISRA is NOT run (its rule texts are not free); findings are rows, never a build failure.

**sc-2c — Frama-C/Mthread joins the formal engines** (`custom/formal_mthread.py`, `custom/mthread_model/`; D-sc-6 ruled 2026-10-02):
Frama-C 33.0's Mthread plugin (LGPL-2.1, opam-built into the SAME `prf-formal-engines` image: +185 MB) answers, UNBOUNDED, whether every
access the ISR and the main loop share holds the interrupt lock or is safe without it. The bridge (`mthread_model/polari_mthread.h`, its
assumptions A1–A6 quoted on every row): the variant's own hal.c preprocessed with `-DPOLARI_MTHREAD` against `mthread_model/stubs/`
(cli/sei/ATOMIC_BLOCK → acquire/release of ONE global interrupt lock) over the CBMC stubs; the ISR = a `Frama_C_thread_create`d thread
holding the lock for its body; the main loop = `<main>`. `classify` turns Mthread's report into PROTECTED / BYTE-ATOMIC (one byte, one
writer) / RACE: `hal-millis-race@uno-sim-rig` → **decided (unbounded)**; `@uno-sim-rig-torn` → **refuted** (`read by <main> at
hal.c:134, unprotected` vs the tick's write at hal.c:110); `rx-ring-race@uno-sim-rig` → **decided (unbounded)**; the negative control
`rx-ring-race@uno-sim-rig+broken-flush` → refuted (speaks to no claim); `@uno-sim-rig-ring512` → inapplicable. The claim gains the
Mthread evidence beside CBMC's bounded one (checker `frama-c-mthread`). Never `proved`.

```
pol faults formal run mthread                     # the five Mthread checks (| cbmc | all | one by name)
pol faults campaign run uart-ber [--seeds 20]     # | torn-read-phase | bounce-window | ack-drop-probability
pol faults campaign show bounce-window
pol faults formal run all                         # | hal-millis-not-torn@uno-sim-rig-torn …
pol faults static run all                         # | <variant>
GET /api/firmwarefaults/campaigns|likelihoods|formal|static · POST /api/firmwarefaults/campaign|formal|static
```

Pipeline (sc-4): `tests/scenarios_stage.py --out results.json [--seeds N]` runs every runnable pair in-process and writes the summary
polari-jenkins/scenarios.sh expects (advisory: a red pair is recorded, never a failure).

Selftest: `PYTHONPATH=.:modules python3 -m firmwarefaults.firmwarefaults_selftest` · the real pair + a live boot:
`tests/firmwarefaults_probe.py` (skips honestly without the engines) · cost: `COST.md`.
