"""
@module kirimoto

Kiri:Moto (Dustin 2026-09-08: "kiri:moto for slicing") — the browser-based
open-source slicer (grid.space, GridSpace/grid-apps) as an ISLE-APP: a
container behind the isle agent at kirimoto.isle, built from a PINNED
upstream commit (offline-installable, no runtime fetches), with slicer
profiles as rows and the SliceJob → GcodeArtifact contract of the
printing suite. Licence: verified in AI-Notes/evaluations/PRINTER_STACK_GATE.md
before the pin is filled; the catalog row refuses to install while the
pin is '<PIN ME>'.
"""
from kirimoto.kirimoto_basis import *  # noqa: F401,F403
