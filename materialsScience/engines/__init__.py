"""
materialsScience.engines — per-scale computation engines behind the
materials basis.

Level 1 (continuum): fem_engine (scikit-fem — pure-Python OO FEM).
Level 4 (quantum):   dft_engine (ASE calculator layer over Quantum
                     ESPRESSO, per Dustin's research notes).

Every engine exposes capability() — an honest report of what is
importable/runnable here — and refuses missing capabilities with a
suggestion pointing at the knob, never a silent fallback.
"""
