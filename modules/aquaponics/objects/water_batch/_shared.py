"""@module aquaponics.objects.water_batch._shared — what the water_batch row classes share (constants, seeds, helpers); split from water_batch_basis.py (sap-2c)."""
import json

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
