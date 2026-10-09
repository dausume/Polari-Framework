"""
@module uno_core_demo

ucd-2 (UNO_CORE_DEMO_PLAN.md §2/§3): the UNO core demo as a Polari Hardware App — a Hardware BRIDGE App
(D-ucd-2: `app.realization = bridge`), whose manifest NAMES the three composed parts his ask describes: a simple
firmware that keeps a date-time synced with the OS and lets one button simultaneously toggle an LED and have an
independent pin witness that switching, sent back through a configured bridge, through the kernel and a JavaFX app,
up into Polari (his words, UNO_CORE_DEMO_PLAN.md §0) — the Firmware Solution `uno-button-clock`, the Hardware
Bridge (`ButtonClockState`/`ButtonClockEvent` on the `button-clock` HardwareBridgeDefinition), and the Polari app
component (`button-clock-ledger` + `/display/uno-core-demo`) — composed as ONE Cross-Domain Solution
(`uno-button-clock`), so every state on that canvas opens the detailed no-code behind it and returns. This module
adds no compute of its own: it only NAMES the parts (`parts` in `polari-app.json`) and DERIVES their readiness
(`DemoReadiness`, `/display/uno-core-demo-readiness`, `GET /api/uno-core-demo/readiness`) — the composition's status
is the weakest of its six parts.
"""
from uno_core_demo.uno_core_demo_basis import *  # noqa: F401,F403
