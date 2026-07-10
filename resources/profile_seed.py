"""
@cross-cutting
@module resources.profile_seed

Declared resource profiles for known subjects (res-2) — honest
starting points (fidelity='declared', provenance names the seed);
res-3 measurement overrides them. Numbers mirror observed reality
where we have it (image sizes are the real `docker image ls` sizes
2026-07-09) and stay conservative where we don't.

@consumers
  - polariServer seed_pairs (idempotent-by-name)
  - resources.selftest_profiles
"""

SEED_MODULE_RESOURCE_PROFILES = [
    {
        'name': 'prf-msci-engines-resource-profile',
        'subject_name': 'prf-msci-engines',
        'subject_kind': 'engine',
        'character': 'compute',
        'min_ram_mb': 900.0, 'min_disk_mb': 2500.0, 'min_threads': 1,
        'thread_ceiling': 8, 'cpu_benefit': 'sublinear',
        'ram_benefit': 'sublinear',
        'scales_note': 'FEM assembly + DFT (BLAS) scale with cores '
                       'sublinearly; RAM bounds mesh/basis size.',
        'image_mb': 2160.0,
        'fidelity': 'declared',
        'provenance_id': 'profile_seed',
        'notes': 'FEM/DFT worker (pyscf+sfepy+skfem). Benefits from '
                 'the biggest adequate node.',
    },
    {
        'name': 'prf-cad-engines-resource-profile',
        'subject_name': 'prf-cad-engines',
        'subject_kind': 'engine',
        'character': 'compute',
        'min_ram_mb': 300.0, 'min_disk_mb': 800.0, 'min_threads': 1,
        # The strictly single-threaded example: trimesh import/export
        # gains NOTHING from a big-compute node (res-4's small-node
        # placement rule exercises this).
        'thread_ceiling': 1, 'cpu_benefit': 'none',
        'ram_benefit': 'none',
        'scales_note': 'trimesh is single-threaded — placing this on '
                       'a big node wastes it.',
        'image_mb': 688.0,
        'fidelity': 'declared',
        'provenance_id': 'profile_seed',
        'notes': 'CAD import/export worker. Prefer the SMALLEST '
                 'adequate node.',
    },
    {
        'name': 'scoring-resource-profile',
        'subject_name': 'scoring',
        'subject_kind': 'module',
        'character': 'data',
        'min_ram_mb': 64.0, 'min_disk_mb': 200.0, 'min_threads': 1,
        'thread_ceiling': 1, 'cpu_benefit': 'none',
        'ram_benefit': 'none',
        'est_row_bytes': 0,  # boot fills from storage_predictor
        'growth_rate': 'high',
        'access_pattern': 'warm',
        'durability': 'durable',
        'concurrency': 'shared',
        'recommended_backend': 'mariadb',
        'fidelity': 'declared',
        'provenance_id': 'profile_seed',
        'notes': 'Assertions/evidence/votes/elections — mostly rows, '
                 'shared by prf + psc (scr-7 seam): the shared '
                 'durable concurrent store.',
    },
    {
        'name': 'topology-resource-profile',
        'subject_name': 'topology',
        'subject_kind': 'module',
        'character': 'data',
        'min_ram_mb': 32.0, 'min_disk_mb': 20.0, 'min_threads': 1,
        'thread_ceiling': 1, 'cpu_benefit': 'none',
        'ram_benefit': 'none',
        'est_row_bytes': 0,
        'growth_rate': 'low',
        'access_pattern': 'warm',
        'durability': 'durable',
        'concurrency': 'single',
        'recommended_backend': 'sqlite',
        'fidelity': 'declared',
        'provenance_id': 'profile_seed',
        'notes': 'Topology-as-data rows — small, single-writer, '
                 'durable: the SqliteAdapter path.',
    },
    {
        'name': 'simulations-resource-profile',
        'subject_name': 'simulations',
        'subject_kind': 'module',
        'character': 'balanced',
        'min_ram_mb': 256.0, 'min_disk_mb': 500.0, 'min_threads': 1,
        'thread_ceiling': 4, 'cpu_benefit': 'sublinear',
        'ram_benefit': 'linear',
        'scales_note': 'Step execution is per-run single-threaded '
                       'today (dask spreads RUNS, not steps); RAM '
                       'bounds retained step rows.',
        'growth_rate': 'high',
        'access_pattern': 'hot',
        'durability': 'ephemeral',
        'concurrency': 'single',
        'recommended_backend': 'redis',
        'fidelity': 'declared',
        'provenance_id': 'profile_seed',
        'notes': 'Sim engine + its step-row stream: compute AND '
                 'high-churn state (retention windows apply).',
    },
]
