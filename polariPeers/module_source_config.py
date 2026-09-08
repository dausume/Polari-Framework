"""
@cross-cutting
@module polariPeers.module_source_config
@tags @xc:bindings

MODULES AS PROJECTS — the configuration row (Track 2 of the materials
science plan): which module code folders this workspace WANTS, where
they come from, and whether they are materialized right now. Modules
not configured (or not fetched) are simply absent — boot tolerates
that (moduleService discovery scans whatever folders exist).

Fetching is explicit ('by selecting to download them' — Dustin's
directive): auto_fetch is a per-row knob defaulting OFF, and nothing
fetches without either that knob or a direct POST
/api/module-projects/fetch.
"""

from objectTreeDecorators import treeObject, treeObjectInit


class ModuleSourceConfig(treeObject):
    """One module project this workspace is configured to know about."""

    @treeObjectInit
    def __init__(
        self,
        # The module folder name (modules/<name>) — polari*Module
        # convention makes discovery pick it up once fetched.
        name: str = '',
        # 'git' | 'github' | 'file' | 'peer'  (same vocabulary as
        # PolariModule.source_kind).
        source_kind: str = 'git',
        # Kind-specific: git URL, owner/repo shorthand, local path, or
        # peer module name.
        locator: str = '',
        # Branch / tag / commit for git kinds ('' = default branch).
        ref: str = '',
        # Fetch at boot when true — default OFF (explicit selection is
        # the norm; the knob is per-module).
        auto_fetch: bool = False,
        # 'absent' | 'fetched' | 'error' — reflects the FOLDER, updated
        # by the fetcher.
        status: str = 'absent',
        # Commit SHA / source fingerprint of the materialized copy.
        fetched_version: str = '',
        last_error: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.source_kind = source_kind
        self.locator = locator
        self.ref = ref
        self.auto_fetch = auto_fetch
        self.status = status
        self.fetched_version = fetched_version
        self.last_error = last_error
        self.notes = notes


#: Seed: the one module project that already lives in-tree, so the
#: config surface starts honest instead of empty.
SEED_MODULE_SOURCE_CONFIGS = [{
    'name': 'materials_science',
    'source_kind': 'file',
    'locator': 'modules/materials_science',
    'status': 'fetched',
    'notes': 'ships in-tree today; listed so the modules-as-projects '
             'surface reflects reality. Its extraction into its own '
             'repo is the workstream goal.',
}]
