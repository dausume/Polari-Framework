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
  - resources.profiles_selftest
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
        'name': 'pol-livekit-resource-profile',
        'subject_name': 'pol-livekit',
        'subject_kind': 'engine',
        'character': 'compute',
        'min_ram_mb': 256.0, 'min_disk_mb': 100.0, 'min_threads': 1,
        'thread_ceiling': 4, 'cpu_benefit': 'linear',
        'ram_benefit': 'sublinear',
        'scales_note': 'SFU forwarding scales with participants x '
                       'tracks; the REAL constraint is BANDWIDTH, '
                       'which this ledger does not measure yet (named '
                       'follow-up, mtg-1) — treat CPU numbers as the '
                       'proxy and the host pin as the decision.',
        'image_mb': 45.0,
        'fidelity': 'declared',
        'provenance_id': 'profile_seed',
        'notes': 'LiveKit media server (mtg-1). Host: NAMED for v1 '
                 '(Dustin default 2026-08-12), sized family 4-8 '
                 'participants, LAN-only.',
    },
    {
        'name': 'pol-reticulum-resource-profile',
        'subject_name': 'pol-reticulum',
        'subject_kind': 'engine',
        'character': 'compute',
        'min_ram_mb': 128.0, 'min_disk_mb': 50.0, 'min_threads': 1,
        'thread_ceiling': 2, 'cpu_benefit': 'none',
        'ram_benefit': 'none',
        'scales_note': 'the mesh bearer is the constraint, not the '
                       'host: LoRa is kilobits and duty-cycled, so a '
                       'bigger node buys NOTHING — airtime is the '
                       'ledgered resource (AirtimeBudget rows), not '
                       'CPU. Any host that runs Python is adequate.',
        'image_mb': 180.0,
        'fidelity': 'declared',
        'provenance_id': 'profile_seed',
        'notes': 'Reticulum mesh sidecar (ret-2). rns==0.9.4 + '
                 'lxmf==0.6.3 — LICENCE pins '
                 '(RETICULUM_LICENCE_GATE.md), never bumped without '
                 're-running the gate.',
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
    # ---- rc-1 (2026-09-26, his rule: adhere to topology's tracking) — the compute arc's workers and modules, DECLARED here;
    # image sizes read from pol-core's docker on 2026-09-26; RAM floors from the flows' cgroup meters where measured (the
    # reproduction blocks) — profile_measure flips them to 'measured' from those reports; the boot itself: 371 MB peak, 18 modules.
    {
        'name': 'prf-eda-engines-resource-profile', 'subject_name': 'prf-eda-engines', 'subject_kind': 'engine', 'character': 'compute',
        'min_ram_mb': 600.0, 'min_disk_mb': 1000.0, 'min_threads': 1, 'thread_ceiling': 2, 'cpu_benefit': 'sublinear', 'ram_benefit': 'none',
        'scales_note': 'gcc / yosys / iverilog / magic / netgen / OpenSTA one process at a time; yosys and magic are single-threaded, PDK reads are I/O',
        'image_mb': 2560.0, 'deps_mb': 930.0, 'fidelity': 'declared', 'provenance_id': 'profile_seed (rc-1)',
        'notes': 'polari-eda-tools:noble (2.56 GB) + the ciel-built sky130A PDK on the host (0.93 GB, never in the image). Worker :9800. Serves computelod.engines (lod-1…lod-3c, tt-3).',
    },
    {
        'name': 'prf-orfs-engines-resource-profile', 'subject_name': 'prf-orfs-engines', 'subject_kind': 'engine', 'character': 'compute',
        'min_ram_mb': 1500.0, 'min_disk_mb': 200.0, 'min_threads': 1, 'thread_ceiling': 4, 'cpu_benefit': 'sublinear', 'ram_benefit': 'sublinear',
        'scales_note': 'the place-and-route flow (OpenROAD): global placement and routing use threads; RAM grows with the design — the 96-cell adder is tiny',
        'image_mb': 4690.0, 'deps_mb': 0.0, 'fidelity': 'declared', 'provenance_id': 'profile_seed (rc-1, eng-1)',
        'notes': 'prf-orfs-engines:staging = openroad/orfs:26Q3-651-gbc334a4aa (4.64 GB, used as published, pinned by digest) + the eda-engines service (~50 MB). Worker :9801 (eng-1). Serves computelod.pnr (lod-3e / lod-3f); the adder flow measured 527 MB peak / 68 CPU-s.',
    },
    {
        'name': 'prf-proof-engines-resource-profile', 'subject_name': 'prf-proof-engines', 'subject_kind': 'engine', 'character': 'compute',
        'min_ram_mb': 2000.0, 'min_disk_mb': 500.0, 'min_threads': 1, 'thread_ceiling': 4, 'cpu_benefit': 'sublinear', 'ram_benefit': 'linear',
        'scales_note': 'Lean 4 + Mathlib: each theorem check loads oleans (RAM-bound); never at boot — a person or the pipeline asks',
        'image_mb': 11000.0, 'deps_mb': 0.0, 'fidelity': 'declared', 'provenance_id': 'profile_seed (rc-1)',
        'notes': 'polari-proof-tools:noble (11 GB — the largest image; Mathlib\'s compiled oleans). Worker :9810 (mem_limit 4000m in its compose). Serves mathproofs.engines (the lean tier only).',
    },
    {
        'name': 'prf-torch-engines-resource-profile', 'subject_name': 'prf-torch-engines', 'subject_kind': 'engine', 'character': 'compute',
        'min_ram_mb': 400.0, 'min_disk_mb': 50.0, 'min_threads': 1, 'thread_ceiling': 4, 'cpu_benefit': 'sublinear', 'ram_benefit': 'none',
        'scales_note': 'torch.einsum on CPU uses the wheel\'s thread pool; the operands here are small (64 elements)',
        'image_mb': 1010.0, 'deps_mb': 0.0, 'fidelity': 'declared', 'provenance_id': 'profile_seed (rc-1)',
        'notes': 'polari-torch-tools:bookworm (1.01 GB, torch 2.14.0+cpu). Worker :9820 (mem_limit 2000m). Serves tensormath.engines (the third ComputeImplementation, D5).',
    },
    {   # brd-1 (2026-10-01): MEASURED on pol-core — modules/board/COST.md
        'name': 'prf-board-engines-resource-profile', 'subject_name': 'prf-board-engines', 'subject_kind': 'engine', 'character': 'compute',
        'min_ram_mb': 64.0, 'min_disk_mb': 535.0, 'min_threads': 1, 'thread_ceiling': 1, 'cpu_benefit': 'none', 'ram_benefit': 'none',
        'scales_note': 'one avr-gcc compile of the UNO firmware: 0.11 CPU-s, 30.5 MB peak RSS (worker rusage); the simavr twin: one core, 11.4 MB peak RSS, 78.8 M cycles/s = 4.9x real time for a 16 MHz ATmega328P',
        'image_mb': 534.7, 'deps_mb': 0.0, 'fidelity': 'declared', 'provenance_id': 'profile_seed (brd-1, measured 2026-10-01)',
        'notes': 'prf-board-engines:trixie (534.7 MB; debian:trixie-slim@sha256:a99cfc51… 78.8 MB + gcc-avr 14.2.0, avr-libc 2.2.1, avrdude 7.1, simavr 1.6, polari-avr-twin). Worker :9830, twin TCP :9831. Serves board.engines; a flash never runs on it.',
    },
    {
        'name': 'prf-cnt-engines-resource-profile', 'subject_name': 'prf-cnt-engines', 'subject_kind': 'engine', 'character': 'compute',
        'min_ram_mb': 500.0, 'min_disk_mb': 200.0, 'min_threads': 1, 'thread_ceiling': 6, 'cpu_benefit': 'sublinear', 'ram_benefit': 'sublinear',
        'scales_note': 'ngspice transients are single-threaded per deck; kwant (quantum transport) uses cores; a 400k-point 0.6 V deck was killed by oomd beside other jobs on a 16 GB host — run long decks alone',
        'image_mb': 0.0, 'deps_mb': 0.0, 'fidelity': 'declared', 'provenance_id': 'profile_seed (rc-1)',
        'notes': 'the cntfet engines worker (:9700; ngspice + OpenVAF/OSDI + kwant) — image size read where it is built (isle-core), not here. Serves cntfet.engines; the lod flows reach ngspice through it or ~/tools.',
    },
    {
        'name': 'tensormath-resource-profile', 'subject_name': 'tensormath', 'subject_kind': 'module', 'character': 'compute',
        'min_ram_mb': 64.0, 'min_disk_mb': 5.0, 'min_threads': 1, 'thread_ceiling': 1, 'cpu_benefit': 'none', 'ram_benefit': 'none',
        'scales_note': 'in the backend process: einsum over small tensors, one FEM solve at seed time; the whole backend boot with the arc (18 modules) peaked at 371 MB, 95 CPU-s, 116 s on pol-core (2026-09-26)',
        'image_mb': 0.0, 'deps_mb': 0.0, 'fidelity': 'declared', 'provenance_id': 'profile_seed (rc-1)',
        'notes': 'engines by the ladder: yosys/nextpnr/iverilog (tt-3, the FPGA kernel flow — a separate command), torch (D5, a worker). Declared share of the boot; the boot is the measured unit.',
    },
    {
        'name': 'tensortree-resource-profile', 'subject_name': 'tensortree', 'subject_kind': 'module', 'character': 'data',
        'min_ram_mb': 32.0, 'min_disk_mb': 5.0, 'min_threads': 1, 'thread_ceiling': 1, 'cpu_benefit': 'none', 'ram_benefit': 'none',
        'scales_note': 'rows and a validator; discovery is a few hundred rows at most', 'est_row_bytes': 600, 'growth_rate': 'low', 'access_pattern': 'warm', 'durability': 'durable', 'concurrency': 'shared',
        'recommended_backend': 'sqlite', 'image_mb': 0.0, 'deps_mb': 0.0, 'fidelity': 'declared', 'provenance_id': 'profile_seed (rc-1)',
        'notes': 'trees, nodes, mappings, selections (a click = a row), policies; no engine.',
    },
    {
        'name': 'computelod-resource-profile', 'subject_name': 'computelod', 'subject_kind': 'module', 'character': 'balanced',
        'min_ram_mb': 64.0, 'min_disk_mb': 20.0, 'min_threads': 1, 'thread_ceiling': 1, 'cpu_benefit': 'none', 'ram_benefit': 'none',
        'scales_note': 'the ladder rows are light; the lod FLOWS are separate commands whose costs are in their reports\' reproduction.cost (host 27–44 MB; the engines\' peaks in their containers)',
        'image_mb': 0.0, 'deps_mb': 20.0, 'fidelity': 'declared', 'provenance_id': 'profile_seed (rc-1)',
        'notes': 'initialData ~1 MB of committed reports/decks/DEF/SPEF; the PDK cache (~1.9 GB: Liberty, cells, models, the ciel PDK) lives on the host, never in git — deps_mb counts only the committed data.',
    },
    {
        'name': 'mathproofs-resource-profile', 'subject_name': 'mathproofs', 'subject_kind': 'module', 'character': 'compute',
        'min_ram_mb': 96.0, 'min_disk_mb': 5.0, 'min_threads': 1, 'thread_ceiling': 1, 'cpu_benefit': 'none', 'ram_benefit': 'none',
        'scales_note': 'numeric/interval/sympy tiers in-process (milliseconds); z3 in-process within a 25 s budget per claim (the bit-blasted MAC encoding needs ~19 s); lean only through the proof worker',
        'image_mb': 0.0, 'deps_mb': 0.0, 'fidelity': 'declared', 'provenance_id': 'profile_seed (rc-1)',
        'notes': 'the boot pass checks every never-run claim once (2.7 s live); worst case is the sum of budgets (aggregate endpoint).',
    },
]
