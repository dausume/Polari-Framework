"""
@module polariPeers.polari_module_dependency

PolariModuleDependency — one tracked dependency edge, persisted so the
dependency picture is an inspectable part of the object tree
([[object-coherence]]) rather than a transient scan result:

    kind='python'  <boundary/module>  ->  <pip package>
                   (resolved_version from importlib.metadata;
                    status installed|missing)
    kind='polari'  <boundary/module>  ->  <other boundary/module>
                   (status declared — the tracked seam between
                    coherent modules)

Rows are (re)populated idempotently-by-name by
moduleService.module_dependency_tracker.refresh_dependency_rows and
surfaced as trees/graphs by the dependency API.

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - moduleService.module_dependency_tracker
  - polariApiServer/module dependency endpoints + the module pages
"""

from objectTreeDecorators import treeObject, treeObjectInit


class PolariModuleDependency(treeObject):
    """One dependency edge (see module docstring). Identified by
    `name` = '<module>:<kind>:<dep>'."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        # The boundary/module the dependency belongs to.
        module_id: str = '',
        # 'python' (pip package) | 'polari' (boundary/module edge).
        kind: str = 'python',
        dep_name: str = '',
        # Optional constraint ('' = unpinned).
        version_spec: str = '',
        # importlib.metadata resolution ('' = missing / not python).
        resolved_version: str = '',
        # 'installed' | 'missing' | 'declared'
        status: str = 'declared',
        # Where the edge came from (import scan, manifest, manual).
        reason: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.module_id = module_id
        self.kind = kind
        self.dep_name = dep_name
        self.version_spec = version_spec
        self.resolved_version = resolved_version
        self.status = status
        self.reason = reason
        self.notes = notes
