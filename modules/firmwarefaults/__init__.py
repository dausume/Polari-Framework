"""
@module firmwarefaults

FIRMWARE SCENARIO ANALYSIS (sc arc, AI-Notes/plans/FIRMWARE_SCENARIO_PLAN.md; D-sc-1 ruled 2026-10-02: its own module,
requiring board + grpcbridge + mathproofs): fault kinds as OBJECTS (one class per kind), the assumptions they break, the
techniques that restore them and what those cost, and SCENARIOS that force one interleaving on the UNO twin at an exact
PC — BEFORE (the fault at a named cycle) and AFTER (the technique holding), each run a witness or a counterexample
written as a mathproofs claim.
"""
