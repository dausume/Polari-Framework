"""
@cross-cutting
@module simulations.step_cost_tracker
@tags @xc:bindings

Step-cost instrumentation — measures what each live step actually costs
(wall-time + persisted bytes) into a StepCostProfile, with Dustin's
STAT-FREEZING rule so the measurement consolidates itself away:

  * wall-time: always-on cheap EMA (one clock read — never worth
    shedding) + observed max.
  * per-field size: len(json.dumps(value)) per persisted field — but a
    (Class.field) whose stats are FROZEN is skipped entirely; its stored
    mean/max are known constants from that point on. Freezing:
      - fixed-width numerics (int/float/bool): frozen after 3 samples
        of identical serialized width;
      - variable payloads (strings, JSON blobs): frozen at n >= 20 with
        coefficient of variation < 0.05;
      - high-variance payloads never freeze (adaptive grids keep being
        measured — correct).
  * config_hash pins stats to the LOCAL USAGE PATTERN (sim parameters,
    field-save policies, participating classes, the run's override
    shapes). On mismatch the profile resets and re-learns
    automatically; reset_profile() is the purposeful re-measure switch.

FAILURE-ISOLATED BY CONTRACT: track_step() swallows everything — an
observer must never kill the execution it observes (the stepping.py
lesson). Profile writes are throttled (every 10 steps + on freeze
transitions), through the standard saveInstanceInDB path.

@consumers
  - simulations.simulation_runner (one call after the atomic persist)
  - simulations.resource_monitor (reads profiles for projections)
@see /OVERLAP_MAP.md
"""

import hashlib
import json
import math
from typing import Any, Dict, Optional

# Freezing thresholds (see module docstring).
NUMERIC_FREEZE_SAMPLES = 3
TEXT_FREEZE_SAMPLES = 20
TEXT_FREEZE_CV = 0.05
# EMA smoothing for step seconds/bytes.
EMA_ALPHA = 0.1
# Persist the profile row at most every N measured steps.
PERSIST_EVERY_STEPS = 10

# Identity fields carry no useful size signal (constant-ish, tiny).
_SKIP_FIELDS = {'name', 'simulation_run_ref', 'step', 'time'}


def track_step(
    manager,
    run,
    sim_def,
    rows_by_class: Dict[str, Dict[str, Any]],
    step: int,
    elapsed_seconds: float,
) -> None:
    """Record one live step's measured cost. NEVER raises."""
    try:
        _track_step_inner(manager, run, sim_def, rows_by_class,
                          step, elapsed_seconds)
    except Exception as exc:  # observer never kills the observed
        try:
            print(f'[StepCost] tracking skipped ({type(exc).__name__}: {exc})',
                  flush=True)
        except Exception:
            pass


def reset_profile(manager, sim_ref: str) -> bool:
    """The purposeful re-measure switch: clear a sim's measured stats so
    everything is sampled fresh. Returns True when a profile existed."""
    profile = _find_profile(manager, sim_ref)
    if profile is None:
        return False
    profile.config_hash = ''
    profile.step_count = 0
    profile.avg_step_seconds = 0.0
    profile.max_step_seconds = 0.0
    profile.avg_step_bytes = 0.0
    profile.max_step_bytes = 0.0
    profile.field_stats_json = '{}'
    profile.updated_step = 0
    _persist(manager, profile)
    return True


def get_profile(manager, sim_ref: str):
    """The sim's StepCostProfile row, or None before any measurement."""
    return _find_profile(manager, sim_ref)


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------


def _track_step_inner(manager, run, sim_def, rows_by_class, step,
                      elapsed_seconds) -> None:
    if not rows_by_class or step <= 0:
        return  # step 0 is the IC write — unrepresentative of stepping cost
    sim_ref = getattr(sim_def, 'name', '')
    if not sim_ref:
        return

    profile = _find_profile(manager, sim_ref)
    cfg_hash = config_hash(sim_def, run)
    if profile is None:
        profile = _create_profile(manager, sim_ref, cfg_hash)
        if profile is None:
            return
    elif (getattr(profile, 'config_hash', '') or '') != cfg_hash:
        # The local usage pattern changed — stats no longer describe it.
        profile.config_hash = cfg_hash
        profile.step_count = 0
        profile.avg_step_seconds = 0.0
        profile.max_step_seconds = 0.0
        profile.avg_step_bytes = 0.0
        profile.max_step_bytes = 0.0
        profile.field_stats_json = '{}'

    stats: Dict[str, Dict[str, Any]] = _parse_stats(profile)
    froze_something = False
    step_bytes = 0.0

    for cls_name, fields in rows_by_class.items():
        for fname, value in (fields or {}).items():
            if fname in _SKIP_FIELDS:
                continue
            key = f'{cls_name}.{fname}'
            st = stats.get(key)
            if st and st.get('frozen'):
                # Known constant — no serialization, mean stands in.
                step_bytes += float(st.get('meanBytes', 0.0))
                continue
            size = _field_bytes(value)
            st = _update_field_stat(st, size, value)
            if st.pop('_justFroze', False):
                froze_something = True
            stats[key] = st
            step_bytes += size

    n = int(getattr(profile, 'step_count', 0) or 0)
    profile.step_count = n + 1
    profile.avg_step_seconds = _ema(
        float(getattr(profile, 'avg_step_seconds', 0.0) or 0.0),
        float(elapsed_seconds), n)
    profile.max_step_seconds = max(
        float(getattr(profile, 'max_step_seconds', 0.0) or 0.0),
        float(elapsed_seconds))
    profile.avg_step_bytes = _ema(
        float(getattr(profile, 'avg_step_bytes', 0.0) or 0.0),
        step_bytes, n)
    profile.max_step_bytes = max(
        float(getattr(profile, 'max_step_bytes', 0.0) or 0.0), step_bytes)
    profile.field_stats_json = json.dumps(stats)

    last_saved = int(getattr(profile, 'updated_step', 0) or 0)
    if froze_something or profile.step_count - last_saved >= PERSIST_EVERY_STEPS \
            or profile.step_count <= 1:
        profile.updated_step = profile.step_count
        _persist(manager, profile)


def _update_field_stat(st: Optional[Dict[str, Any]], size: int,
                       value: Any) -> Dict[str, Any]:
    """Welford-style running stats + the freeze decision. Returns the
    updated stat dict; sets '_justFroze' True on the frozen transition
    (caller pops it — transient, not persisted)."""
    if not st:
        st = {'n': 0, 'meanBytes': 0.0, 'maxBytes': 0, 'cv': 0.0,
              'frozen': False, '_m2': 0.0}
    n = int(st.get('n', 0)) + 1
    mean = float(st.get('meanBytes', 0.0))
    m2 = float(st.get('_m2', 0.0))
    delta = size - mean
    mean += delta / n
    m2 += delta * (size - mean)
    variance = (m2 / (n - 1)) if n > 1 else 0.0
    cv = (math.sqrt(variance) / mean) if mean > 0 else 0.0
    st.update({'n': n, 'meanBytes': round(mean, 2),
               'maxBytes': max(int(st.get('maxBytes', 0)), int(size)),
               'cv': round(cv, 6), '_m2': m2})

    numeric = isinstance(value, (int, float, bool))
    should_freeze = (
        (numeric and n >= NUMERIC_FREEZE_SAMPLES and cv < 1e-9)
        or (not numeric and n >= TEXT_FREEZE_SAMPLES and cv < TEXT_FREEZE_CV)
    )
    if should_freeze and not st.get('frozen'):
        st['frozen'] = True
        st['_justFroze'] = True
        st.pop('_m2', None)  # constants need no variance bookkeeping
    return st


def _field_bytes(value: Any) -> int:
    try:
        return len(json.dumps(value))
    except (TypeError, ValueError):
        try:
            return len(str(value))
        except Exception:
            return 0


def _ema(current: float, sample: float, prior_n: int) -> float:
    if prior_n <= 0:
        return float(sample)
    return current + EMA_ALPHA * (float(sample) - current)


def config_hash(sim_def, run) -> str:
    """Fingerprint of the LOCAL USAGE PATTERN the stats describe."""
    run_params = getattr(run, 'parameter_overrides_json', '') or '{}'
    parts = (
        getattr(sim_def, 'parameters_json', '') or '{}',
        getattr(sim_def, 'field_save_overrides_json', '') or '{}',
        getattr(sim_def, 'participating_sim_state_classes_json', '') or '[]',
        getattr(run, 'field_save_overrides_json', '') or '{}',
        # Shape (keys) of run param overrides, not values — a different
        # mass is the same usage pattern; a new overridden field is not.
        json.dumps(sorted(_keys_of(run_params))),
    )
    return hashlib.sha1('|'.join(parts).encode('utf-8')).hexdigest()[:16]


def _keys_of(raw_json: str):
    try:
        parsed = json.loads(raw_json)
        return list(parsed.keys()) if isinstance(parsed, dict) else []
    except (ValueError, TypeError):
        return []


def _parse_stats(profile) -> Dict[str, Dict[str, Any]]:
    try:
        parsed = json.loads(getattr(profile, 'field_stats_json', '') or '{}')
        return parsed if isinstance(parsed, dict) else {}
    except (ValueError, TypeError):
        return {}


def _find_profile(manager, sim_ref: str):
    table = manager.objectTables.get('StepCostProfile', {}) or {}
    for inst in table.values():
        if getattr(inst, 'simulation_ref', '') == sim_ref:
            return inst
    return None


def _create_profile(manager, sim_ref: str, cfg_hash: str):
    from simulations.step_cost_profile import StepCostProfile
    try:
        return StepCostProfile(
            name=f'{sim_ref}-cost-profile',
            simulation_ref=sim_ref,
            config_hash=cfg_hash,
            manager=manager,
        )
    except Exception:
        return None


def _persist(manager, profile) -> None:
    db = getattr(manager, 'db', None)
    if db is not None:
        try:
            db.saveInstanceInDB(profile)
        except Exception:
            pass
