"""
@cross-cutting
@module resources.custom.profile_measure
@tags @xc:bindings

Empirical measurement (res-3) — the honest high-fidelity path,
mirroring simulations/StepCostProfile: measured values override
declared ones, every number keeps its label, and what was NOT
measured keeps its declared value with the absence named.

Three measurable dimensions:
  RAM      — a worker's own resident/peak RSS, self-reported in its
             /system-info `process` block (measured ON the device it
             actually runs on, over the swarm).
  DATA     — observed rows in the live object tree × the
             storage_predictor per-row estimate (labeled
             estimate×count, not raw disk bytes).
  THREADS  — a benchmark run at N=1,2,4,… threads → speedup curve →
             the empirical thread_ceiling + cpu_benefit. A strictly
             single-threaded workload shows a flat curve and the
             ceiling honestly stays 1. The default in-backend
             benchmark is pure-Python (GIL-bound) — its flat result
             IS the truth for python-thread module code; engines
             measure on their own device or keep declared, labeled.

@consumers
  - resources.profile_api (POST /api/resources/measure)
  - resources.measure_selftest
@see /OVERLAP_MAP.md
"""

import json
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from resources.custom.profile_analysis import find_profile

#: Thread counts probed for the speedup curve (capped at the host).
_THREAD_STEPS = (1, 2, 4, 8)
#: Marginal speedup below this over a doubling = the curve plateaued.
_PLATEAU_GAIN = 1.25
#: speedup(max) thresholds for the benefit verdict.
_LINEAR_FRACTION = 0.70
_FLAT_THRESHOLD = 1.3


def _now():
    return datetime.now(timezone.utc).isoformat()


def default_benchmark(threads, work_items=64, inner=20000):
    """A GIL-bound representative workload: seconds to finish
    `work_items` chunks of pure-python math on `threads` threads."""
    def chunk(_):
        acc = 0.0
        for i in range(inner):
            acc += (i % 7) * 1.000001
        return acc
    start = time.perf_counter()
    with ThreadPoolExecutor(max_workers=threads) as pool:
        list(pool.map(chunk, range(work_items)))
    return time.perf_counter() - start


def derive_speedup_curve(bench=default_benchmark, max_threads=8,
                         steps=_THREAD_STEPS):
    """Run `bench(n)` at increasing n → the empirical scalability.

    Returns {'speedup': {n: x}, 'threadCeiling', 'cpuBenefit'}.
    thread_ceiling = the last probed n that still bought a
    meaningful (> _PLATEAU_GAIN per doubling) improvement; a flat
    curve keeps it at 1 with cpu_benefit='none'.
    """
    ns = [n for n in steps if n <= max(1, int(max_threads))]
    if 1 not in ns:
        ns.insert(0, 1)
    times = {}
    for n in ns:
        try:
            times[n] = float(bench(n))
        except Exception as e:
            return {'ok': False,
                    'error': f'benchmark failed at {n} threads: {e}'}
    base = times[1] or 1e-9
    speedup = {n: round(base / (t or 1e-9), 3)
               for n, t in times.items()}
    ceiling = 1
    for prev, n in zip(ns, ns[1:]):
        if speedup[n] / max(speedup[prev], 1e-9) >= _PLATEAU_GAIN:
            ceiling = n
        else:
            break
    top = speedup[ns[-1]]
    if ceiling == 1 or top < _FLAT_THRESHOLD:
        ceiling, benefit = 1, 'none'
    elif top >= _LINEAR_FRACTION * ns[-1]:
        benefit = 'linear'
    else:
        benefit = 'sublinear'
    return {'ok': True, 'speedup': speedup, 'threadCeiling': ceiling,
            'cpuBenefit': benefit}


def observed_data_footprint(manager, module_name, root=None):
    """Live rows of the module's data classes × the predictor's
    per-row bytes — an OBSERVED volume (labeled estimate×count)."""
    from resources.custom.profile_analysis import scan_module_source
    try:
        from simulations.storage_predictor import estimate_row_bytes
    except Exception:
        return {'ok': False, 'error': 'storage_predictor unavailable'}
    src = scan_module_source(module_name, root=root)
    tables = getattr(manager, 'objectTables', None) or {}
    per_class, total = [], 0
    for cls in src['dataClasses']:
        rows = len(tables.get(cls) or {})
        est = estimate_row_bytes(manager, cls)
        per_class.append({'class': cls, 'rows': rows,
                          'estRowBytes': est, 'bytes': rows * est})
        total += rows * est
    return {'ok': True, 'module': module_name,
            'observedBytes': total, 'observedMb': round(
                total / (1024.0 * 1024.0), 3),
            'perClass': per_class,
            'label': 'estimate-x-count (predictor bytes x live rows)'}


def _fetch_process_block(url, fetch=None):
    """A worker's self-reported resident/peak RSS from /system-info."""
    from resources.custom.node_resources import _default_fetch
    fetch = fetch or _default_fetch
    if not url.rstrip('/').endswith('/system-info'):
        url = url.rstrip('/') + '/system-info'
    doc = fetch(url)
    if isinstance(doc, list) and doc:
        doc = doc[0]
    if isinstance(doc, dict):
        doc = doc.get('system-info', doc)
    if not isinstance(doc, dict):
        return None
    return doc.get('process') or None


def measure_subject(manager, subject_name, url='', fetch=None,
                    bench=None, max_threads=8, root=None):
    """Measure what CAN be measured for a subject and write it onto
    its ModuleResourceProfile (fidelity='measured'); everything
    unmeasured keeps its declared value, named in `unmeasured`.

    Engine subjects (a URL or PROVIDER_PORTS entry): RAM from the
    worker's own /system-info process block. Module subjects:
    observed data footprint + (optional) a thread benchmark run
    IN this backend.
    """
    profile = find_profile(manager, subject_name)
    if profile is None:
        return {'ok': False,
                'error': f'no ModuleResourceProfile for '
                         f'"{subject_name}" — declare one first '
                         f'(GET /api/modules/{subject_name}/'
                         'resource-profile)'}
    measured, unmeasured = {}, []

    kind = getattr(profile, 'subject_kind', 'module')
    if kind == 'engine':
        if not url:
            import os
            try:
                from topology.provider_registry import PROVIDER_PORTS
            except Exception:
                PROVIDER_PORTS = {}
            port = PROVIDER_PORTS.get(subject_name)
            host = os.environ.get('LOCAL_IP', '')
            if port and host:
                url = f'http://{host}:{port}'
        if url:
            try:
                process = _fetch_process_block(url, fetch=fetch)
            except Exception as e:
                process = None
                unmeasured.append(f'ram (worker unreachable: {e})')
            if process and process.get('residentMb'):
                measured['min_ram_mb'] = float(process['residentMb'])
                measured['_peak_ram_mb'] = float(
                    process.get('peakMb', process['residentMb']))
        else:
            unmeasured.append('ram (no URL — PROVIDER_PORTS/LOCAL_IP '
                              'unset and none passed)')
        unmeasured.append('threads (engine benchmark endpoint not '
                          'built — declared scalability kept)')
        unmeasured.append('image (docker not reachable in-backend — '
                          'declared image_mb kept)')
    else:
        data = observed_data_footprint(manager, subject_name,
                                       root=root)
        if data.get('ok'):
            measured['min_disk_mb'] = max(
                float(getattr(profile, 'min_disk_mb', 0) or 0),
                data['observedMb'])
            measured['_observed_data'] = data
        if bench is not None or getattr(
                profile, 'character', '') != 'data':
            curve = derive_speedup_curve(
                bench or default_benchmark, max_threads=max_threads)
            if curve.get('ok'):
                measured['thread_ceiling'] = curve['threadCeiling']
                measured['cpu_benefit'] = curve['cpuBenefit']
                measured['_speedup'] = curve['speedup']
            else:
                unmeasured.append(f'threads ({curve.get("error")})')
        else:
            unmeasured.append('threads (data module — no benchmark '
                              'run)')
        unmeasured.append('ram (module shares the backend process — '
                          'per-module RSS not attributable)')

    if not any(k for k in measured if not k.startswith('_')):
        return {'ok': False, 'subject': subject_name,
                'error': 'nothing measurable — declared profile kept',
                'unmeasured': unmeasured}

    for key, value in measured.items():
        if not key.startswith('_'):
            setattr(profile, key, value)
    stamp = _now()
    profile.fidelity = 'measured'
    profile.provenance_id = (
        f'measured@{stamp}'
        + (f' via {url}' if url else ' in-backend'))
    detail = {k.lstrip('_'): v for k, v in measured.items()
              if k.startswith('_')}
    if unmeasured:
        detail['unmeasuredKept'] = unmeasured
    profile.scales_note = (
        (getattr(profile, 'scales_note', '') or '')
        + f' | res-3 {stamp}: ' + json.dumps(detail))[:2000]
    try:
        manager.db.saveInstanceInDB(profile)
    except Exception:
        pass
    return {'ok': True, 'subject': subject_name,
            'measured': {k: v for k, v in measured.items()
                         if not k.startswith('_')},
            'detail': detail, 'unmeasured': unmeasured,
            'fidelity': 'measured'}
