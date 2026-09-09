"""
@module printing_suite

The 3D printing PRODUCTION suite (sa-2, Dustin 2026-09-08): one suite app
that bundles everything needed for normal production printing — not the
research stack — as parts of every kind: the design step (mathshapes CAD
import → shapes), the material/mold step (materials_science, composition,
casting/waxprint molds), the slicer (Kiri:Moto, an isle container app),
the printer (voron: Klipper+Moonraker+Mainsail in a KVM guest), the
hardware map (which device can take the printer), and the measurement
step. The CONTRACTS are the rows the parts pass through Polari:
shape → mold → print profile → slice job → gcode artifact → print job →
print outcome (→ back into material/mold rows). This module seeds the
suite and OWNS the contract objects that no single part owned before.
"""
from printing_suite.printing_suite_basis import *  # noqa: F401,F403
