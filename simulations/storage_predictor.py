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
from typing import Dict, Any, List


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


# Minimum number of samples PolyTyping needs before its measured
# average is considered statistically meaningful enough to replace the
# static fallback. Phase A+B+D use statics exclusively; once Phase C
# starts populating measurements, the predictor will switch on a
# per-field basis as soon as a field crosses this threshold.
MEASURED_SAMPLE_THRESHOLD = 10


def _per_field_size_estimate(
    manager,
    class_name: str,
    field_name: str,
) -> Dict[str, Any]:
    """Return the byte estimate for ONE field on a class, tagged with
    its source. Shape:

        {
          'bytes':     int,    # normal-case bytes (average / static)
          'minBytes':  int,    # best case — same as bytes when source='static'
          'maxBytes':  int,    # worst case — same as bytes when source='static'
          'source':    'static' | 'measured-insufficient' | 'measured',
          'sampleCount': int,  # 0 when no PolyTyping samples exist
        }

    The 'source' tagging is what lets the UI flag estimates that are
    based on conservative defaults vs. real measurements collected
    across prior runs (Phase C — not yet wired). Until Phase C lands,
    every field returns source='static' with min/max collapsed to the
    static value.
    """
    typing_obj = manager.objectTypingDict.get(class_name) if manager else None
    static_bytes = TYPE_BYTES['object']
    var_type = ''
    if typing_obj is not None:
        for var in (getattr(typing_obj, 'polyTypedVars', None) or []):
            if getattr(var, 'name', '') == field_name:
                var_type = (getattr(var, 'varType', None) or '').lower()
                static_bytes = TYPE_BYTES.get(var_type, TYPE_BYTES['object'])
                # Phase C will read measured stats off the polyTypedVariable
                # here — something like:
                #   stats = getattr(var, 'byteSampleStats', None)
                #   if stats and stats.count >= MEASURED_SAMPLE_THRESHOLD:
                #       return measured(stats)
                # For now everything's static.
                break
    return {
        'bytes':       static_bytes,
        'minBytes':    static_bytes,
        'maxBytes':    static_bytes,
        'source':      'static',
        'sampleCount': 0,
    }


def estimate_run_storage(
    manager,
    sim_def,
    run,
) -> Dict[str, Any]:
    """Top-level per-run storage estimator. Walks every participating
    class, applies the merged effective field policy, and returns a
    breakdown the UI can render.

    Return shape:
        {
          'totalSteps': int,
          'normalCaseBytes': int,
          'minBytes': int,           # best case
          'maxBytes': int,           # worst case
          'normalCaseHuman': str,    # '12.4 MB'
          'usesStaticEstimates': bool,
          'perClass': {
            '<cls>': {
              'rowOverheadBytes': int,
              'rowsPersisted': int,
              'normalCaseBytes': int,
              'minBytes': int,
              'maxBytes': int,
              'fields': {
                '<field>': {
                  'policy':       'core' | 'derivable' | 'skip',
                  'interval':     int,     # 0 = follow sim's recording_interval
                  'rowsPersisted': int,
                  'bytes':        int,     # per-row average for this field
                  'minBytes':     int,
                  'maxBytes':     int,
                  'source':       str,
                  'sampleCount':  int,
                }
              }
            }
          },
          'notes': [str, ...],
        }
    """
    # Late imports to avoid circular dependencies (the runner imports
    # the predictor for its public estimate; we import its helpers).
    from .simulation_runner import (
        _participating_classes,
        _effective_field_save_rules,
        _field_persists_at_step,
    )
    notes: List[str] = []
    participating = _participating_classes(sim_def)
    dt = float(getattr(sim_def, 'time_step_seconds', 0.01) or 0.01)
    if run is not None:
        run_dt = float(getattr(run, 'time_step_seconds', 0.0) or 0.0)
        if run_dt > 0:
            dt = run_dt
    duration = float(getattr(sim_def, 'duration_seconds', 0.0) or 0.0)
    if dt <= 0:
        dt = 0.01
        notes.append('time_step_seconds was 0; using 0.01s for the estimate.')
    total_steps = max(1, int(math.ceil(duration / dt))) if duration > 0 else 0
    default_interval = max(1, int(
        getattr(sim_def, 'recording_interval_steps', 1) or 1
    ))

    uses_static_anywhere = False
    per_class: Dict[str, Dict[str, Any]] = {}
    grand_normal = 0
    grand_min = 0
    grand_max = 0
    for cls_name in participating:
        rules = _effective_field_save_rules(manager, sim_def, run, cls_name)
        typing_obj = manager.objectTypingDict.get(cls_name) if manager else None
        poly_vars = getattr(typing_obj, 'polyTypedVars', None) or []
        all_fields = [getattr(v, 'name', '') for v in poly_vars if getattr(v, 'name', '')]
        cls_normal = 0
        cls_min = 0
        cls_max = 0
        fields_out: Dict[str, Dict[str, Any]] = {}
        cls_rows_persisted = 0  # max over fields — row overhead counts once per persisted row
        for fname in all_fields:
            rule = rules.get(fname, {'policy': 'core', 'interval': 0})
            policy = rule.get('policy', 'core')
            interval = int(rule.get('interval') or 0) or default_interval
            if total_steps == 0:
                rows_persisted = 0
            elif policy in ('skip', 'derivable'):
                rows_persisted = 0
            else:
                rows_persisted = max(1, int(math.ceil(total_steps / interval)))
            if rows_persisted > cls_rows_persisted:
                cls_rows_persisted = rows_persisted
            est = _per_field_size_estimate(manager, cls_name, fname)
            if est['source'] != 'measured':
                uses_static_anywhere = True
            field_normal = est['bytes'] * rows_persisted
            field_min = est['minBytes'] * rows_persisted
            field_max = est['maxBytes'] * rows_persisted
            cls_normal += field_normal
            cls_min += field_min
            cls_max += field_max
            fields_out[fname] = {
                'policy': policy,
                'interval': interval if interval != default_interval else 0,
                'rowsPersisted': rows_persisted,
                'bytes': est['bytes'],
                'minBytes': est['minBytes'],
                'maxBytes': est['maxBytes'],
                'source': est['source'],
                'sampleCount': est['sampleCount'],
            }
        overhead_total = ROW_OVERHEAD_BYTES * cls_rows_persisted
        cls_normal += overhead_total
        cls_min += overhead_total
        cls_max += overhead_total
        per_class[cls_name] = {
            'rowOverheadBytes': ROW_OVERHEAD_BYTES,
            'rowsPersisted': cls_rows_persisted,
            'normalCaseBytes': cls_normal,
            'minBytes': cls_min,
            'maxBytes': cls_max,
            'fields': fields_out,
        }
        grand_normal += cls_normal
        grand_min += cls_min
        grand_max += cls_max

    if uses_static_anywhere:
        notes.append(
            'Some field sizes are static defaults — no measured samples '
            'available yet. Numbers will tighten as more runs commit.'
        )

    return {
        'totalSteps': total_steps,
        'normalCaseBytes': grand_normal,
        'minBytes': grand_min,
        'maxBytes': grand_max,
        'normalCaseHuman': _human_bytes(grand_normal),
        'minCaseHuman': _human_bytes(grand_min),
        'maxCaseHuman': _human_bytes(grand_max),
        'usesStaticEstimates': uses_static_anywhere,
        'perClass': per_class,
        'notes': notes,
    }


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
