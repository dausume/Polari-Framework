"""
@module moduleService.module_boot_records

mlb-2 (MODULE_LAZY_BOOT_PLAN): module boot TIMING as durable data.

Every lazy boot writes one ModuleBootRecord per admitted module:
when its dependencies were all online (deps_ready_at), when IT came
online, and the duration between — Dustin's ask: "based on prior
knowledge/tracking (if it exists for the module) track how long it
takes to come online after its dependencies are loaded." The history
persists like everything else (CRUDE-visible rows), so later boots
derive an expected duration (median of prior runs on this instance)
and the status API / frontend can show an honest ETA. No history ->
no ETA, never a guess.

Also THE single source of module dependency edges for admission
ordering: modules/polari-modules.json `requires` is authoritative;
module_loading.FEATURE_REQUIRES must be a subset (the drift selftest
pins it).

@consumers
  - polariApiServer.lazy_boot (admission ordering + record writes)
  - polariApiServer.polariServer (defClassList registration)
  - moduleService.selftest_module_boot_records
"""

import json
import os

from objectTreeDecorators import treeObject, treeObjectInit

BOOT_STATUSES = ('online', 'failed')


class ModuleBootRecord(treeObject):
    """One module's timing for one boot of one instance."""

    @treeObjectInit
    def __init__(
        self,
        # '<module>@<instance>@<boot_id>'.
        name: str = '',
        module_name: str = '',
        instance_name: str = '',
        # One id per boot of the process (epoch-seconds string) — all
        # records of a boot share it.
        boot_id: str = '',
        # Epoch seconds. deps_ready_at = the moment the LAST
        # dependency (or the core, if none) came online; the tracked
        # duration starts there, not at process start.
        boot_started_at: float = 0.0,
        deps_ready_at: float = 0.0,
        online_at: float = 0.0,
        duration_after_deps_s: float = 0.0,
        status: str = 'online',
        error: str = '',
        # Rows seeded/restored while admitting this module — context
        # for why a duration is what it is.
        seeded_rows: int = 0,
        # Was this a lazy (two-phase) boot? Monolithic boots don't
        # write records (there is no per-module timing to measure).
        lazy_boot: bool = True,
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.module_name = module_name
        self.instance_name = instance_name
        self.boot_id = boot_id
        self.boot_started_at = boot_started_at
        self.deps_ready_at = deps_ready_at
        self.online_at = online_at
        self.duration_after_deps_s = duration_after_deps_s
        self.status = status
        self.error = error
        self.seeded_rows = seeded_rows
        self.lazy_boot = lazy_boot
        self.notes = notes


def _framework_root():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_module_requires(root=None):
    """THE dependency-edge source for admission ordering:
    modules/polari-modules.json `requires` (authoritative), unioned
    with module_loading.FEATURE_REQUIRES (which the drift selftest
    pins as a subset). Returns {module: set(requires)}."""
    from moduleService.module_loading import FEATURE_REQUIRES
    edges = {m: set(reqs) for m, reqs in FEATURE_REQUIRES.items()}
    path = os.path.join(root or _framework_root(), 'modules',
                        'polari-modules.json')
    try:
        register = json.load(open(path))
    except Exception:
        register = {}
    for name, entry in (register.get('modules') or {}).items():
        reqs = (entry or {}).get('requires') or []
        if name and reqs:
            edges.setdefault(name, set()).update(reqs)
    return edges


def requires_drift(root=None):
    """Edges in FEATURE_REQUIRES that the json register does NOT
    carry — should be empty (json is authoritative; the frozenset is
    the boot-safe mirror). The selftest pins this."""
    from moduleService.module_loading import FEATURE_REQUIRES
    path = os.path.join(root or _framework_root(), 'modules',
                        'polari-modules.json')
    try:
        register = json.load(open(path))
    except Exception:
        return {'error': 'polari-modules.json unreadable'}
    json_edges = {}
    for name, entry in (register.get('modules') or {}).items():
        json_edges[name] = set((entry or {}).get('requires') or [])
    missing = {}
    for mod, reqs in FEATURE_REQUIRES.items():
        gap = set(reqs) - json_edges.get(mod, set())
        if gap:
            missing[mod] = sorted(gap)
    return missing


def dependency_order(modules, requires=None):
    """Deterministic topological order over `modules` (alphabetical
    among ready nodes). Dependencies OUTSIDE `modules` are treated as
    already satisfied (core, or gated off on this instance — gating
    is per-instance; ordering only sequences what THIS boot admits).
    A cycle refuses loudly with the cycle members."""
    requires = requires if requires is not None \
        else load_module_requires()
    pending = sorted(set(modules))
    inside = set(pending)
    done = set()
    order = []
    while pending:
        ready = [m for m in pending
                 if not (set(requires.get(m, ())) & inside - done)]
        if not ready:
            return {'ok': False,
                    'refusal': 'dependency cycle among modules: '
                               + ', '.join(sorted(pending)),
                    'suggestion': 'fix requires in '
                                  'polari-modules.json'}
        nxt = ready[0]
        pending.remove(nxt)
        done.add(nxt)
        order.append(nxt)
    return {'ok': True, 'order': order}


def expected_duration_s(records, module_name, instance_name=None):
    """Median duration-after-deps from prior ONLINE records for this
    module (this instance's records preferred; any instance as the
    fallback). None when no history exists — the honest 'no ETA'."""
    def _get(r, key, default=None):
        return (r.get(key, default) if isinstance(r, dict)
                else getattr(r, key, default))
    mine = [r for r in records
            if _get(r, 'module_name') == module_name
            and _get(r, 'status') == 'online'
            and (_get(r, 'duration_after_deps_s') or 0) > 0]
    if instance_name:
        scoped = [r for r in mine
                  if _get(r, 'instance_name') == instance_name]
        mine = scoped or mine
    if not mine:
        return None
    values = sorted(float(_get(r, 'duration_after_deps_s'))
                    for r in mine)
    mid = len(values) // 2
    if len(values) % 2:
        return values[mid]
    return (values[mid - 1] + values[mid]) / 2.0
