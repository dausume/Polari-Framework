"""
@cross-cutting
@module aquaponics.water_batch
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
reuses aquaponics.hydraulics.build_darcy_payload's own already-
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
    (that's aquaponics.hydraulics's job, already built; a future pass
    could feed a batch's elapsed-since-fill time into
    aquaponics.hydraulics.reservoir_model's own outflow math to get a
    real decaying water-level signal during the hold window — flagged
    as a natural, not-yet-wired extension, not silently claimed here).
  - Tower-level (multiple pots sharing ONE water source via gravity at
    a time) is explicitly NOT built this pass, per Dustin's own
    sequencing — but this resolver is deliberately schedule-name-
    agnostic (works for any named schedule, not hardcoded to one pot),
    so a future tower-level binding can reuse it directly rather than
    needing a second resolver.

@consumers
  - aquaponics.plant_growth_normalized.advance_growth (resolves the
    ACTIVE water source for a planting's per-tick stress/nutrient
    computation, when a PotSystemDefinition.water_batch_schedule_name
    is bound — overriding the system's static water_name)
  - aquaponics.water_batch_api (diagnostic reads)
@see /AQUAPONICS_POT_SHAPE_PLAN.md phase 10
"""

import json

from objectTreeDecorators import treeObject, treeObjectInit


def _rows(manager, class_name):
    table = (getattr(manager, 'objectTables', None) or {}).get(
        class_name, {})
    return list(table.values()) if isinstance(table, dict) \
        else list(table)


def _named(manager, class_name, name):
    for row in _rows(manager, class_name):
        if getattr(row, 'name', '') == name:
            return row
    return None


class WaterBatchSchedule(treeObject):
    """An ordered, optionally-repeating cycle of {waterName,
    holdHours, holdDays} batches. See module docstring for the full
    "go until full, then sit" design."""

    @treeObjectInit
    def __init__(
        self,
        # unique key ('basil-stress-cycle').
        name: str = '',
        display_name: str = '',
        description: str = '',
        # JSON list: [{"waterName": "...", "holdHours": 0.0,
        # "holdDays": 0.0}, ...] — ordered, at least one entry.
        batches_json: str = '[]',
        # Cycle back to batch 0 once the last batch's hold completes
        # (True), or hold indefinitely at the last batch (False).
        repeat: bool = True,
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.description = description
        self.batches_json = batches_json
        self.repeat = repeat
        self.provenance_id = provenance_id
        self.notes = notes


def _batch_duration_days(batch):
    return (float(batch.get('holdDays', 0.0) or 0.0)
           + float(batch.get('holdHours', 0.0) or 0.0) / 24.0)


def active_batch(manager, schedule_name, elapsed_days):
    """Which batch (and therefore which WaterDefinition) governs a pot
    at `elapsed_days` since the schedule started. Always returns a
    result dict (never raises) — a malformed/empty schedule is an
    honest refusal, never a silent default source."""
    schedule = _named(manager, 'WaterBatchSchedule', schedule_name)
    if schedule is None:
        return {'ok': False,
                'error': f"no WaterBatchSchedule named '{schedule_name}'"}
    try:
        batches = json.loads(schedule.batches_json or '[]')
    except Exception:
        batches = []
    if not batches:
        return {'ok': False,
                'error': f"WaterBatchSchedule '{schedule_name}' has no "
                         'batches',
                'suggestion': {
                    'knob': 'WaterBatchSchedule.batches_json',
                    'action': 'add at least one {waterName, holdHours/'
                              'holdDays} batch'}}
    total_cycle_days = sum(_batch_duration_days(b) for b in batches)
    if total_cycle_days <= 0:
        return {'ok': False,
                'error': f"WaterBatchSchedule '{schedule_name}' has "
                         'zero total duration (every batch has '
                         'holdHours=holdDays=0)'}

    t = float(elapsed_days)
    if bool(getattr(schedule, 'repeat', True)):
        t = t % total_cycle_days
    cursor = 0.0
    for i, batch in enumerate(batches):
        duration = _batch_duration_days(batch)
        is_last = (i == len(batches) - 1)
        if t < cursor + duration or is_last:
            return {
                'ok': True,
                'schedule': schedule_name,
                'waterName': batch.get('waterName', ''),
                'batchIndex': i,
                'batchCount': len(batches),
                'timeIntoBatchDays': round(max(0.0, t - cursor), 4),
                'batchDurationDays': round(duration, 4),
                'repeat': bool(getattr(schedule, 'repeat', True)),
                'note': ('cycled back to batch 0 after '
                        f'{total_cycle_days:.2f} days' if
                        getattr(schedule, 'repeat', True) else
                        'holding at the final batch indefinitely '
                        '(repeat=False)') if is_last and t >= cursor
                        + duration else '',
            }
        cursor += duration
    # Unreachable (the is_last branch above always matches), kept as
    # an honest fallback rather than relying on that invariant.
    return {'ok': False,
            'error': 'internal: no batch matched (should be '
                     'unreachable)'}
