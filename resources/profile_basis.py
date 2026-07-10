"""
@cross-cutting
@module resources.profile_basis
@tags @xc:bindings

Module/engine resource profiles (res-2): what a subject NEEDS (the
floor — min RAM/disk/threads), what it BENEFITS from (scalability —
a strictly single-threaded engine gains nothing from a big-compute
server), what it IS (compute / data / balanced), and — for data
subjects — which storage tier it belongs in (redis / sqlite /
mariadb, the InstanceDefinition.db_backend vocabulary).

Every number carries its label: fidelity='declared' (a knob or a
seed) until res-3 measurement flips it to 'measured' — labels travel
with numbers, honest absence otherwise.

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - resources.profile_analysis / resources.profile_api
  - resources.admission_advisor (res-4)
"""

from objectTreeDecorators import treeObject, treeObjectInit


class ModuleResourceProfile(treeObject):
    """The resource profile of one module or engine service."""

    @treeObjectInit
    def __init__(
        self,
        # '<subject>-resource-profile' (unique key).
        name: str = '',
        # The module name (FRAMEWORK_BOUNDARIES / ModuleAssignment
        # vocabulary) or the engine service kind (PROVIDER_PORTS).
        subject_name: str = '',
        # 'module' | 'engine'.
        subject_kind: str = 'module',
        # 'compute' | 'data' | 'balanced' — drives res-4 routing
        # (data -> storage tier, compute -> node placement).
        character: str = 'balanced',
        # --- FLOOR: the minimum that must be AVAILABLE to run ---
        min_ram_mb: float = 0.0,
        min_disk_mb: float = 0.0,
        # Dustin's "minimum threads that should be available".
        min_threads: int = 1,
        # --- SCALABILITY: what MORE resources actually buy ---
        # 1 = strictly single-threaded (gains nothing from cores).
        thread_ceiling: int = 1,
        # 'none' | 'sublinear' | 'linear'.
        cpu_benefit: str = 'none',
        ram_benefit: str = 'none',
        scales_note: str = '',
        # --- INSTALL footprint: what gets pulled down ---
        image_mb: float = 0.0,
        deps_mb: float = 0.0,
        # --- DATA profile (meaningful when character == 'data') ---
        est_row_bytes: int = 0,
        # 'low' | 'medium' | 'high' expected row growth.
        growth_rate: str = 'low',
        # 'hot' | 'warm' | 'cold'.
        access_pattern: str = 'warm',
        # 'ephemeral' | 'durable'.
        durability: str = 'durable',
        # 'single' | 'shared' — how many writers/instances touch it.
        concurrency: str = 'single',
        # DB_BACKENDS-adjacent tier: 'redis' | 'sqlite' | 'mariadb'.
        recommended_backend: str = '',
        # 'declared' (knob/seed) | 'measured' (res-3 evidence).
        fidelity: str = 'declared',
        # Where the numbers came from (seed name, /capability URL,
        # res-3 measurement context hash).
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.subject_name = subject_name
        self.subject_kind = subject_kind
        self.character = character
        self.min_ram_mb = min_ram_mb
        self.min_disk_mb = min_disk_mb
        self.min_threads = min_threads
        self.thread_ceiling = thread_ceiling
        self.cpu_benefit = cpu_benefit
        self.ram_benefit = ram_benefit
        self.scales_note = scales_note
        self.image_mb = image_mb
        self.deps_mb = deps_mb
        self.est_row_bytes = est_row_bytes
        self.growth_rate = growth_rate
        self.access_pattern = access_pattern
        self.durability = durability
        self.concurrency = concurrency
        self.recommended_backend = recommended_backend
        self.fidelity = fidelity
        self.provenance_id = provenance_id
        self.notes = notes
