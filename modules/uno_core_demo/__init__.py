"""
@module uno_core_demo

The light test as a Polari Hardware App (ucd-2, re-pointed at the light test by ucd-light): the simplest proof that data and
signals travel in both directions between a Polari screen and a board. A Hardware BRIDGE App (D-ucd-2: `app.realization =
bridge`) whose manifest NAMES the parts the test is made of — the Firmware Solution `uno-light`, the Hardware Bridge
(`LightState` on the `uno-light` HardwareBridgeDefinition), the Cross-Domain Solution `uno-light` that ties them together and
the two Purposes `light-from-polari` / `light-from-button`. This module adds no compute of its own: it only NAMES the parts
(`parts` in `polari-app.json`) and DERIVES their readiness (`DemoReadiness`, `/display/uno-core-demo-readiness`,
`GET /api/uno-core-demo/readiness`) — the composition's status is the weakest of its parts. The light itself is on
`/display/uno-core-demo`.
"""
from uno_core_demo.uno_core_demo_basis import *  # noqa: F401,F403
