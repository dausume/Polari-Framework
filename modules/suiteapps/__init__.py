"""
@module suiteapps

Suite apps (sa-1, Dustin 2026-09-08): "bundle everything needed … in one
larger app that incorporates all of those smaller apps that are a mix of
hardware kvm apps and container apps … overarching purpose oriented apps
… an amalgam of apps and foundationally too big for one computer."

A suite app is a PURPOSE (production 3D printing) composed of PARTS —
apps of any kind (polari-app modules, isle-app containers, hardware-app
KVM guests, extension apps) — each with a placement need (any device /
the core / a hardware-tier device / a named node), plus the CONTRACTS:
the object classes its parts pass to one another through Polari (rows,
never files handed around). Placement is computed against the same
StandardComputerBudget + nodes the test-coverage planner uses: a suite
that does not fit one device is spread, and the plan says where each
part runs and what it still lacks. This library holds the rows and the
placement logic; each suite (printing_suite, …) seeds its own.
"""
from suiteapps.suiteapps_basis import *  # noqa: F401,F403
