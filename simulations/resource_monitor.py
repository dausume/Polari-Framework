"""
@cross-cutting
@module simulations.resource_monitor
@tags @xc:bindings

Resource awareness — what memory/disk is actually available, and the
CRITICAL pre-run projection Dustin asked for: "this amount of steps you
are entering, if each step costs the average it usually does, will be
close to draining your memory completely" — detected and said in plain
language BEFORE the run, not discovered as a frozen machine after.

Projection sources, in preference order:
  1. the sim's StepCostProfile (MEASURED average bytes/seconds per step,
     with frozen constants standing in for stabilized fields),
  2. Dustin's static storage_predictor estimate (no measurements yet) —
     the response says which source it used.

@consumers
  - simulations.simulation_api (/resources, /project, batch-run guard)
@see /OVERLAP_MAP.md
"""

import shutil
from typing import Any, Dict, Optional

from simulations.storage_predictor import estimate_run_storage, _human_bytes
from simulations.step_cost_tracker import get_profile, _parse_stats

# Projection severity thresholds against min(available memory, free disk).
WARNING_FRACTION = 0.50
CRITICAL_FRACTION = 0.85

# cgroup v2 / v1 / proc sources, in probe order.
_CGROUP_V2_MAX = '/sys/fs/cgroup/memory.max'
_CGROUP_V2_CUR = '/sys/fs/cgroup/memory.current'
_CGROUP_V1_MAX = '/sys/fs/cgroup/memory/memory.limit_in_bytes'
_CGROUP_V1_CUR = '/sys/fs/cgroup/memory/memory.usage_in_bytes'
_PROC_MEMINFO = '/proc/meminfo'
# Sentinel for "no cgroup limit" (v1 reports a huge number, v2 'max').
_NO_LIMIT_FLOOR = 1 << 60


def system_resources(db_dir: str = '/app/data',
                     paths: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """Current memory + disk budget. `paths` lets tests inject fake
    cgroup/proc file locations."""
    p = paths or {}
    v2_max = p.get('v2_max', _CGROUP_V2_MAX)
    v2_cur = p.get('v2_cur', _CGROUP_V2_CUR)
    v1_max = p.get('v1_max', _CGROUP_V1_MAX)
    v1_cur = p.get('v1_cur', _CGROUP_V1_CUR)
    meminfo = p.get('meminfo', _PROC_MEMINFO)

    limit = _read_int(v2_max)
    used = _read_int(v2_cur)
    source = 'cgroup-v2'
    if limit is None or used is None:
        limit = _read_int(v1_max)
        used = _read_int(v1_cur)
        source = 'cgroup-v1'
    if limit is not None and limit >= _NO_LIMIT_FLOOR:
        limit = None  # unlimited container — fall through to host view
    if limit is None or used is None:
        available = _meminfo_available(meminfo)
        limit, used = None, None
        source = 'proc-meminfo'
    else:
        available = max(0, limit - used)

    try:
        disk_free = shutil.disk_usage(db_dir).free
    except OSError:
        disk_free = None

    return {
        'memory': {
            'limitBytes': limit,
            'usedBytes': used,
            'availableBytes': available,
        },
        'disk': {'freeBytes': disk_free},
        'source': source,
    }


def project_run(manager, run, sim_def, steps: int,
                resources: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Project `steps` more steps of this run against the budget.

    Returns {steps, source, avgStepBytes, projectedBytes,
    projectedSeconds, availableMemoryBytes, diskFreeBytes, level,
    message, topConsumers} — `level` ∈ ok|warning|critical, `message`
    written for a non-specialist.
    """
    steps = max(0, int(steps or 0))
    res = resources or system_resources()
    mem_avail = (res.get('memory') or {}).get('availableBytes')
    disk_free = (res.get('disk') or {}).get('freeBytes')

    profile = get_profile(manager, getattr(sim_def, 'name', ''))
    top_consumers = []
    if profile is not None and int(getattr(profile, 'step_count', 0) or 0) > 0:
        source = 'measured'
        avg_bytes = float(getattr(profile, 'avg_step_bytes', 0.0) or 0.0)
        avg_seconds = float(getattr(profile, 'avg_step_seconds', 0.0) or 0.0)
        stats = _parse_stats(profile)
        ranked = sorted(stats.items(),
                        key=lambda kv: float(kv[1].get('meanBytes', 0.0)),
                        reverse=True)
        top_consumers = [
            {'field': k, 'meanBytes': v.get('meanBytes', 0.0),
             'frozen': bool(v.get('frozen'))}
            for k, v in ranked[:5]
        ]
    else:
        # No measurements yet — Dustin's static predictor stands in.
        source = 'static-estimate'
        est = estimate_run_storage(manager, sim_def, run)
        total_steps = max(1, int(est.get('totalSteps') or 1))
        avg_bytes = float(est.get('normalCaseBytes') or 0) / total_steps
        avg_seconds = 0.0

    projected_bytes = avg_bytes * steps
    projected_seconds = avg_seconds * steps

    budgets = [b for b in (mem_avail, disk_free) if isinstance(b, (int, float))]
    budget = min(budgets) if budgets else None
    if budget and budget > 0 and projected_bytes > 0:
        fraction = projected_bytes / budget
        if fraction >= CRITICAL_FRACTION:
            level = 'critical'
        elif fraction >= WARNING_FRACTION:
            level = 'warning'
        else:
            level = 'ok'
    else:
        level = 'ok'

    message = _plain_message(steps, avg_bytes, projected_bytes,
                             mem_avail, disk_free, level, source)
    return {
        'steps': steps,
        'source': source,
        'avgStepBytes': round(avg_bytes, 2),
        'projectedBytes': int(projected_bytes),
        'projectedHuman': _human_bytes(int(projected_bytes)),
        'projectedSeconds': round(projected_seconds, 3),
        'availableMemoryBytes': mem_avail,
        'diskFreeBytes': disk_free,
        'level': level,
        'message': message,
        'topConsumers': top_consumers,
    }


def _plain_message(steps, avg_bytes, projected_bytes, mem_avail,
                   disk_free, level, source) -> str:
    per_step = _human_bytes(int(avg_bytes)) if avg_bytes else 'a negligible amount'
    total = _human_bytes(int(projected_bytes))
    verb = ('usually costs' if source == 'measured'
            else 'is estimated to cost')
    base = (f'Running {steps:,} steps at the ~{per_step}/step this '
            f'simulation {verb} needs ~{total}')
    budget_bits = []
    if isinstance(mem_avail, (int, float)):
        budget_bits.append(f'{_human_bytes(int(mem_avail))} memory available')
    if isinstance(disk_free, (int, float)):
        budget_bits.append(f'{_human_bytes(int(disk_free))} disk free')
    budget = ' and '.join(budget_bits) if budget_bits else 'an unknown budget'
    if level == 'critical':
        return (f'{base} — that would nearly drain what this machine has '
                f'left ({budget}). Reduce the steps or apply a data-saving '
                f'suggestion before running.')
    if level == 'warning':
        return (f'{base} — a large share of what this machine has left '
                f'({budget}). Consider the data-saving suggestions.')
    return f'{base} ({budget}).'


def _read_int(path: str) -> Optional[int]:
    try:
        with open(path) as f:
            raw = f.read().strip()
        if raw == 'max':
            return _NO_LIMIT_FLOOR
        return int(raw)
    except (OSError, ValueError):
        return None


def _meminfo_available(path: str) -> Optional[int]:
    try:
        with open(path) as f:
            for line in f:
                if line.startswith('MemAvailable:'):
                    return int(line.split()[1]) * 1024
    except (OSError, ValueError, IndexError):
        pass
    return None
