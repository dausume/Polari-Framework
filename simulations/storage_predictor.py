"""
@cross-cutting
@module simulations.storage_predictor
@tags @xc:bindings

Pure-function storage predictor. Given a target class + a recording
schedule, estimates how many rows will be persisted and how many bytes
they'll consume — used by the UI to warn before kicking off a long
simulation.

Estimation philosophy: bounded-but-defensive. We over-estimate per-field
bytes (especially for strings) so the user isn't surprised by larger
real footprints. Add a small DB row overhead (PK, indexes, row metadata)
that's consistent with MariaDB defaults.

No Polari-specific framework dependencies beyond the manager's
objectTypingDict — keeps this function trivially testable.

@consumers
  - simulations.simulation_api (REST endpoint)
  - (future) frontend predictor UI before "Run Simulation"
@see /OVERLAP_MAP.md
"""

import math
from typing import Dict, Any


# Field-type → estimated bytes. Conservative — covers DB column width
# plus serialization overhead. Strings are the wildcard; we use a
# generous default (handles most labels + UUIDs).
TYPE_BYTES: Dict[str, int] = {
    'int': 8,
    'float': 8,
    'number': 8,
    'numeric': 8,
    'bool': 1,
    'boolean': 1,
    'str': 64,     # generous default for labels, ids, names
    'string': 64,
    'text': 256,   # multi-line / longer text
    'date': 16,
    'datetime': 24,
    'time': 16,
    'list': 256,   # JSON-serialized; rough heuristic
    'dict': 256,
    'object': 256,
    'reference': 64,
    'referenceList': 256,
}

# Per-row overhead: id PK, _branch_path, framework metadata. Empirically
# ~50–80 bytes on MariaDB row headers + a small index entry.
ROW_OVERHEAD_BYTES = 80

# Minimum number of rows we always persist regardless of recording_interval:
#   1. first step (t=0 initial conditions)
#   2. current step (most recent recorded by interval)
#   3. step-being-computed (live tip, the running edge)
#   4. last step (final state when run completes)
# These can coincide (e.g. small max_steps), so the predictor enforces a
# floor of MIN_RECORDED_ROWS even when the interval would emit fewer.
MIN_RECORDED_ROWS = 4


def estimate_row_bytes(manager, class_name: str) -> int:
    """Walk the class's polyTyped variable list and sum estimated bytes.
    Returns 0 if the class isn't registered (caller decides whether to
    treat as an error)."""
    typing_obj = manager.objectTypingDict.get(class_name) if manager else None
    if typing_obj is None:
        return 0
    total = ROW_OVERHEAD_BYTES
    poly_vars = getattr(typing_obj, 'polyTypedVars', None) or []
    for var in poly_vars:
        # `polyTypedVar` has a `varType` attribute (string). Tolerant
        # fallback to 'object' if the type is unrecognised.
        var_type = (getattr(var, 'varType', None) or '').lower()
        total += TYPE_BYTES.get(var_type, TYPE_BYTES['object'])
    return total


def predict_storage(
    manager,
    class_name: str,
    duration_seconds: float,
    time_step_seconds: float,
    recording_interval_steps: int,
) -> Dict[str, Any]:
    """Return a dict with the storage prediction:

    {
      "className": str,
      "rowBytes": int,
      "totalSteps": int,         # how many steps the engine will compute
      "recordedRows": int,       # how many will be persisted
      "totalBytes": int,
      "totalHuman": str,         # e.g. "12.4 KB" or "3.2 MB"
      "notes": [str, ...],       # warnings / context for the UI
    }
    """
    notes = []
    row_bytes = estimate_row_bytes(manager, class_name)
    if row_bytes == 0:
        notes.append(f'Class "{class_name}" not registered — row size unknown.')

    if time_step_seconds <= 0:
        notes.append('time_step_seconds must be > 0; treating as 0.01s.')
        time_step_seconds = 0.01

    total_steps = max(1, int(math.ceil(duration_seconds / time_step_seconds)))

    if recording_interval_steps < 1:
        notes.append('recording_interval_steps < 1 — clamping to 1 (record every step).')
        recording_interval_steps = 1

    # Recorded rows by interval, plus the minimum guaranteed set
    # (first/current/live/last). Math.ceil because the final partial
    # interval still gets recorded as the "last" row.
    by_interval = int(math.ceil(total_steps / recording_interval_steps)) + 1
    recorded_rows = max(MIN_RECORDED_ROWS, by_interval)

    if recorded_rows >= total_steps:
        notes.append(
            f'Interval {recording_interval_steps} would record ≥ all computed steps '
            f'({total_steps}); every computed step will be persisted.'
        )
        recorded_rows = total_steps

    total_bytes = row_bytes * recorded_rows
    return {
        'className': class_name,
        'rowBytes': row_bytes,
        'totalSteps': total_steps,
        'recordedRows': recorded_rows,
        'totalBytes': total_bytes,
        'totalHuman': _human_bytes(total_bytes),
        'notes': notes,
    }


def _human_bytes(n: int) -> str:
    """Compact human-readable byte count. 1024-based."""
    if n < 1024:
        return f'{n} B'
    units = ['KB', 'MB', 'GB', 'TB']
    size = float(n)
    unit = 'B'
    for u in units:
        size /= 1024.0
        unit = u
        if size < 1024:
            break
    # 1 decimal place; trim trailing .0 for clean look.
    formatted = f'{size:.1f}'
    if formatted.endswith('.0'):
        formatted = formatted[:-2]
    return f'{formatted} {unit}'
