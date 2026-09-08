"""
@cross-cutting
@module aquaponics.water_batch_basis
@tags @xc:bindings

Plant-growth-sim phase 10 (2026-07-15) — water BATCHING/scheduling.
Dustin, correcting the first design pass: "water batching should be
'go until full' then leave to sit for N hours and/or N days." Also:
"we simulate this at the per pot level to prepare for the tower level
where one type of water goes through the whole system via gravity at
a time and we batch different water sources to optimize growth or
purposefully stress plants in particular ways without killing them."

A `WaterBatchSchedule` is an ORDERED CYCLE of batches, each naming a
real `WaterDefinition` source. "Full" is NOT a new field here — it
reuses aquaponics.custom.hydraulics.build_darcy_payload's own already-
established convention (default water level = the pot's own input-
hole height, the pot's real "maintained level"), so a batch's fill
target is whatever the pot's OWN geometry already defines as full, not
a second, potentially-inconsistent number. Each batch then HOLDS (no
new source added — this schedule never claims fill itself takes real
time; that's a stated v1 simplification, see below) for
holdHours+holdDays before the next batch's fill begins. `repeat=True`
cycles back to batch 0 once the last batch's hold completes — real
stress-testing protocols often want a repeating pattern (e.g. "3 days
rich, 1 day deliberately Fe-deficient, repeat"), not a one-shot
sequence.

Real, stated v1 simplifications:
  - Fill is treated as near-instantaneous for the purpose of "which
    water source governs uptake right now" — no dilution/mixing
    between a batch's incoming water and whatever was left from the
    PREVIOUS batch is modeled; each batch's water is treated as
    instantaneously fully replacing the prior one. A real transient
    mixing model is future work, not built here.
  - This module resolves WHICH source governs a pot at a given elapsed
    time — it does not itself run a water-LEVEL fill/drain simulation
    (that's aquaponics.custom.hydraulics's job, already built; a future pass
    could feed a batch's elapsed-since-fill time into
    aquaponics.custom.hydraulics.reservoir_model's own outflow math to get a
    real decaying water-level signal during the hold window — flagged
    as a natural, not-yet-wired extension, not silently claimed here).
  - Tower-level (multiple pots sharing ONE water source via gravity at
    a time) is explicitly NOT built this pass, per Dustin's own
    sequencing — but this resolver is deliberately schedule-name-
    agnostic (works for any named schedule, not hardcoded to one pot),
    so a future tower-level binding can reuse it directly rather than
    needing a second resolver.

@consumers
  - aquaponics.plant_growth_normalized_basis.advance_growth (resolves the
    ACTIVE water source for a planting's per-tick stress/nutrient
    computation, when a PotSystemDefinition.water_batch_schedule_name
    is bound — overriding the system's static water_name)
  - aquaponics.water_batch_api (diagnostic reads)
@see /AQUAPONICS_POT_SHAPE_PLAN.md phase 10
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/water_batch/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

import json
from objectTreeDecorators import treeObject, treeObjectInit

from aquaponics.objects.water_batch._shared import _batch_duration_days, _named, _rows, active_batch  # noqa: F401
from aquaponics.objects.water_batch.WaterBatchSchedule import WaterBatchSchedule  # noqa: F401
