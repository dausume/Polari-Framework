"""
@cross-cutting
@module polariPeers.polari_module
@tags @xc:bindings

PolariModule — the registry row for a loadable capability module: a JSON
bundle of configuration objects (class definitions in /createClass form,
sim/solution/equation/scene/composition definitions, seed rows) that a
Polari instance can install, serve to peers, and unload.

This class is the Track-3 SKELETON: the registry + the modules API exist
from the twin handshake onward (peers can probe what a node has or is
installing); the exporter/loader that fills it arrive with Track 3.

Source kinds: 'github' | 'git' | 'file' | 'peer' — GitHub is A
distribution channel, not THE one; any Polari serves its own modules.

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - polariPeers.peers_api (GET /api/modules[/name])
@see /OVERLAP_MAP.md
"""

from objectTreeDecorators import treeObject, treeObjectInit


class PolariModule(treeObject):
    """One module known to this instance. Identified by `name`."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        # Module version — by convention the source commit SHA (or a tag).
        version: str = '',
        # Where it came from: 'github' | 'git' | 'file' | 'peer'.
        source_kind: str = '',
        # Kind-specific ref: repo/path, git URL, file path, or the peer
        # name + module name.
        source_ref: str = '',
        # 'installed' | 'installing' | 'available' — peers probing this
        # node see in-progress installs too.
        status: str = 'available',
        # The module manifest (name, version, dependencies, contents
        # summary). The full bundle is served by GET /api/modules/{name}
        # once the Track-3 loader stores it.
        manifest_json: str = '{}',
        # Local cache of the full bundle JSON ('' until Track 3 stores it).
        bundle_json: str = '',
        # tt-1 self-declarations (TECH_TREE_TOPOLOGY_PLAN A2/B):
        # data_only marks a module that is just stored class/data
        # information — no logic dependencies; the module graph
        # classifies it 'data-only' regardless of degree.
        data_only: bool = False,
        # Which tech-tree node this module's theory work belongs to
        # ('' = unplaced). A hint the tt-5 seeding reads; the durable
        # mapping is the TechSegmentAssignment row.
        tech_node_ref: str = '',
        # mlb-2 lifecycle (written by the lazy-boot admission worker;
        # '' / 0 on instances that never lazy-booted):
        # pending|loading|online|failed|blocked|disabled.
        boot_status: str = '',
        boot_started_at: float = 0.0,
        boot_finished_at: float = 0.0,
        seeded_rows: int = 0,
        boot_error: str = '',
        # Expected seconds-to-online after deps, from ModuleBootRecord
        # history (0.0 = no history yet — no ETA is shown, not a guess).
        expected_online_s: float = 0.0,
        manager=None,
    ):
        self.name = name
        self.version = version
        self.source_kind = source_kind
        self.source_ref = source_ref
        self.status = status
        self.manifest_json = manifest_json
        self.bundle_json = bundle_json
        self.data_only = data_only
        self.tech_node_ref = tech_node_ref
        self.boot_status = boot_status
        self.boot_started_at = boot_started_at
        self.boot_finished_at = boot_finished_at
        self.seeded_rows = seeded_rows
        self.boot_error = boot_error
        self.expected_online_s = expected_online_s
