"""
@module tensormath.custom.torch_engine

PYTORCH AS THE THIRD ComputeImplementation (D5 — his word 2026-09-26; plan §F8 bridge, §G.5 owed). The SAME operator
(σ = C:ε, `stress-from-strain`) beside the numpy einsum and the FPGA MAC kernel: `torch.einsum` on the same operands with
the same contraction spec the numpy path derives, its result COMPARED to numpy (the reference; `error` = max relative
difference), its latency MEASURED where it runs. PyTorch is BSD-3 (GPLv3-compatible; polari-torch-tools/LICENSES.md).

The module never assumes a device (his rule 2026-09-24): torch resolves through the Polari engines ladder exactly as
computelod's EDA tools and mathproofs' lean —
  1. TORCH_ENGINES_URL set          → that worker, ALWAYS (unreachable = refusal; a declared worker never degrades)
  2. knob unset, `import torch` OK  → this process (a local execution: torch installed where the framework runs)
  3. nothing local                  → the topology's provider for `tensormath.engines` (`pol allocate tensormath.engines <inst>`)
  4. nothing                        → refusal naming both knobs
The worker is the submodule `polari-rf-node/polari-torch-tools` (python:3.12-slim + the pinned CPU wheel; :9820; /capability + /evaluate).
The framework image is Alpine/musl and has no torch wheel — like z3 — so on the node stack the worker IS the normal way.

Evidence: a benchmark through `POST /api/tensormath/benchmark {"implementation": "stress-from-strain/torch"}` sets the row's
latency/throughput/error MEASURED where it ran (local | remote), with torch's version, device and thread count, the element
count, the repeats and the median/min/max in `evidence_ref` — the reproduction record of that number. Determinism:
`torch.einsum` on CPU is deterministic for these shapes (no reduction-order nondeterminism at float64 on CPU) — stated,
and `torch.use_deterministic_algorithms(True)` is set on the worker and locally.
"""
import json
import os
import time
import urllib.error
import urllib.request

KNOB = 'TORCH_ENGINES_URL'
PROVIDER_MODULE = 'tensormath.engines'
REMOTE = 'remote'
_CAP_CACHE = {}
_CAP_TTL_S = 30.0


class TorchEngineError(RuntimeError):
    pass


def knob_url():
    return os.environ.get(KNOB, '').rstrip('/')


def _local_torch():
    try:
        import torch   # noqa: F401
        return torch
    except Exception:
        return None


def topology_url():
    try:
        from topology.provider_registry import resolve_provider
        resolved = resolve_provider(PROVIDER_MODULE)
        if resolved.get('ok'):
            return resolved['url'].rstrip('/')
    except Exception:
        pass
    return ''


def remote_capability(url, timeout=5):
    now = time.time()
    cached = _CAP_CACHE.get(url)
    if cached and now - cached[0] < _CAP_TTL_S:
        return cached[1]
    cap = None
    try:
        try:
            from polariApiServer import outbound
            with outbound.http_request('engine', 'torch', 'GET', '%s/capability' % url, means='probe', timeout=timeout, lib='urllib') as response:
                cap = json.load(response)
        except ImportError:
            with urllib.request.urlopen('%s/capability' % url, timeout=timeout) as response:
                cap = json.load(response)
    except Exception:
        cap = None
    _CAP_CACHE[url] = (now, cap)
    return cap


def _has(cap):
    return bool(cap and (cap.get('engines') or {}).get('torch', {}).get('available'))


def resolve():
    """{'how': 'remote'|'local'|'refused', 'where', 'why', 'version'}."""
    url = knob_url()
    if url:
        cap = remote_capability(url)
        if cap is None:
            return {'how': 'refused', 'where': url, 'why': '%s=%s is set but the worker is unreachable — refusing (a declared worker never silently falls back to local)' % (KNOB, url), 'version': ''}
        if not _has(cap):
            return {'how': 'refused', 'where': url, 'why': '%s=%s reached but that worker has no torch' % (KNOB, url), 'version': ''}
        return {'how': REMOTE, 'where': url, 'why': 'knob', 'version': str((cap.get('engines') or {}).get('torch', {}).get('version', ''))}
    t = _local_torch()
    if t is not None:
        return {'how': 'local', 'where': 'this process (import torch)', 'why': 'torch is installed where the framework runs', 'version': str(getattr(t, '__version__', ''))}
    url = topology_url()
    if url and _has(remote_capability(url)):
        return {'how': REMOTE, 'where': url, 'why': 'topology provider %s' % PROVIDER_MODULE, 'version': str((remote_capability(url).get('engines') or {}).get('torch', {}).get('version', ''))}
    return {'how': 'refused', 'where': '', 'why': 'no torch: not importable here (the framework image is Alpine — no torch wheel), no %s worker, no live %s provider — set %s or `pol allocate %s <instance>`' % (
        KNOB, PROVIDER_MODULE, KNOB, PROVIDER_MODULE), 'version': ''}


def placement():
    r = resolve()
    return {'engine': 'torch', 'knob': KNOB, 'knob_value': knob_url(), 'provider_module': PROVIDER_MODULE, 'resolution': r,
            'ladder': ['%s (always, or refusal)' % KNOB, 'import torch in this process', 'topology provider %s (live only)' % PROVIDER_MODULE, 'refusal'],
            'worker': 'polari-rf-node/polari-torch-tools (submodule; docker-compose.torch-engines.yml, :9820)', 'licence': 'PyTorch BSD-3-Clause (polari-torch-tools/LICENSES.md)'}


def _post(url, payload, timeout):
    data = json.dumps(payload).encode()
    req = urllib.request.Request('%s/evaluate' % url, data=data, headers={'Content-Type': 'application/json'}, method='POST')
    try:
        try:
            from polariApiServer import outbound
            with outbound.http_request('engine', 'torch', 'POST', req, timeout=timeout, lib='urllib') as response:
                return json.load(response)
        except ImportError:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                return json.load(response)
    except urllib.error.HTTPError as exc:
        try:
            return json.load(exc)
        except Exception:
            raise TorchEngineError('worker %s: HTTP %s' % (url, exc.code))
    except Exception as exc:
        raise TorchEngineError('worker %s unreachable: %s' % (url, exc))


def einsum_local(torch, spec, operands, dtype='float64'):
    """torch.einsum on CPU tensors built from nested lists; returns (values list, elapsed_s of the einsum alone, info)."""
    try:
        torch.use_deterministic_algorithms(True)
    except Exception:
        pass
    dt = getattr(torch, dtype)
    ts = [torch.tensor(a, dtype=dt) for a in operands]
    t0 = time.perf_counter()
    r = torch.einsum(spec, *ts)
    el = time.perf_counter() - t0
    return r.tolist(), el, {'device': str(r.device), 'threads': int(torch.get_num_threads()), 'version': str(torch.__version__), 'dtype': dtype}


def evaluate(manager, expression, reference=None):
    """The expression through torch wherever it resolves. `reference` = the numpy result (evaluate from tensor_ops) — computed
    here when not given; it supplies the contraction spec and is the value the torch result is compared to.
    Returns {values, dims, shape, einsum, elapsed_s, error_vs_numpy, how, where, torch}."""
    from tensormath.custom.tensor_ops import evaluate as np_evaluate, TensorOpsError, values as tensor_values, _find, _j
    ref = reference or np_evaluate(manager, expression)
    spec = ref.get('einsum') or ''
    if not spec:
        raise TorchEngineError('the expression has no einsum contraction (operation %r) — torch implements contract/outer; the rest stays numpy' % getattr(expression, 'operation', ''))
    ops = _j(getattr(expression, 'operands_json', '[]'), [])
    operands = []
    for o in ops:
        t = _find(manager, 'Tensor', str(o.get('tensor', '')))
        if t is None:
            raise TorchEngineError('operand tensor %r not found' % o.get('tensor'))
        operands.append(tensor_values(manager, t).tolist())
    r = resolve()
    if r['how'] == 'refused':
        raise TorchEngineError(r['why'])
    if r['how'] == REMOTE:
        rep = _post(r['where'], {'einsum': spec, 'operands': operands, 'dtype': 'float64'}, timeout=120)
        if not rep.get('ok'):
            raise TorchEngineError('worker refused: %s' % rep.get('error'))
        vals, el, info = rep['values'], float(rep.get('elapsed_s', 0.0)), rep.get('torch', {})
    else:
        vals, el, info = einsum_local(_local_torch(), spec, operands)
    import numpy as np
    a = np.asarray(vals, dtype=float); b = np.asarray(ref['values'], dtype=float)
    denom = float(np.max(np.abs(b))) or 1.0
    err = float(np.max(np.abs(a - b)) / denom) if a.shape == b.shape else float('inf')
    return {'values': vals, 'dims': ref.get('dims'), 'shape': list(a.shape), 'einsum': spec, 'elapsed_s': round(el, 6), 'error_vs_numpy': err,
            'how': r['how'], 'where': r['where'], 'torch': info}
