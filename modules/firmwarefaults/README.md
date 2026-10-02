# Firmware Faults (`firmwarefaults`) — sc-0

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
(drop-nth-frame, flip-bit-at-cycle, uart-ber, hold-lock-order, clock-skew) are listed with the reason; a scenario using one is
refused, never half-run.

**Claims:** each run writes a mathproofs `MathClaim` (kind `safe-under-scenario`, checker `sim`) per (scenario, build) and a
`ProofRun`; failed → refuted, passed → witnessed, inapplicable → inapplicable, undetermined → undetermined. A refuted claim is never
flipped back by a later witness on the same build.

```
pol faults list                                   # scenarios, step kinds, recorded runs
pol faults run torn-millis-read --both            # the BEFORE/AFTER pair + costs (local; --api URL runs it on a server)
pol faults run torn-millis-read --natural         # 10 s, no forcing: the measured rate onto the fault row
pol faults show <run>                             # the cycles around the fault + the claim
GET /api/firmwarefaults[/faults|/techniques|/scenarios|/runs|/runs/{run}|/engines] · POST /api/firmwarefaults/run
/display/firmware-faults                          # configured tables only
```

Selftest: `PYTHONPATH=.:modules python3 -m firmwarefaults.firmwarefaults_selftest` · the real pair + a live boot:
`tests/firmwarefaults_probe.py` (skips honestly without the engines) · cost: `COST.md`.
