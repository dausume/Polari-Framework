"""
@module cmod

C MODULARIZATION (cmod arc, AI-Notes/plans/C_MODULARIZATION_PLAN.md; his ruling 2026-10-02: "modularization of C code into
polari is likely going to be a critical part of functionality"): a firmware project stays a NORMAL C project that builds
with make alone; Polari DERIVES its atoms — C functions with declared ports, the resources they touch, their measured
cost — by parsing (pycparser), into rows and the conformed manifest `polari-firmware.json`. No C<->Python transpiling.
cmod-0: the parser + the manifest over the UNO firmware; cmod-1: a no-code graph over atoms → generated plain-C glue.
"""
