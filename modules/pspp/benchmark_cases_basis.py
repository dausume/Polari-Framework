"""
@module pspp.benchmark_cases_basis

pspp-V3: the Ch.8 patent/lab examples as BENCHMARK ROWS + the
measured-vs-predicted OVERLAY — the book's near-complete experiments
laid beside what Polari's engines predict from the same inputs.

Honesty contract per overlay section:
- 'match'/'mismatch' only where an engine genuinely predicts
  (window grading, framework reachability).
- 'refusal' where the engine correctly declines (no strength law —
  I5; off-table MRs) — a refusal beside measured data IS the point:
  it shows exactly which dataset/calibration would turn that section
  into a prediction.
- 'recorded' for as-printed observations no engine consumes yet.

Framework prediction uses a QUALITATIVE inventory (species present,
amounts None): benchmarks state what was mixed, not solution Q
percentages, and presence-only closure needs no invented amounts.

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - pspp.pspp_api (GET /api/pspp/benchmarks[/{name}/overlay])
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/benchmark_cases/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

import json
from objectTreeDecorators import treeObject, treeObjectInit
from pspp.custom.network_stepping import reachable_frameworks
from pspp.custom.progress_engine import cure_progress
from pspp.threshold_windows_basis import grade_composition_merged

from pspp.objects.benchmark_cases._shared import SEED_BENCHMARK_CASES, _BM_PROVENANCE, _get, _loads, _normalized_ratios, _row, benchmark_catalog, benchmark_overlay, benchmark_overlay_by_name, qualitative_inventory  # noqa: F401
from pspp.objects.benchmark_cases.BenchmarkCase import BenchmarkCase  # noqa: F401
