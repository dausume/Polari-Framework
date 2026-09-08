"""
@module cntfet.cnt_cell_library_basis

S4d/S5b (Dustin 2026-08-25: "fully flesh out the cell stages and
their variants"): the cell library as DATA, not hardcoded
netlists. Each cell is a device-list row (function, inputs,
Liberty function, unateness, transistor topology) and each
VARIANT is a drive strength realized as N parallel devices per
position — so `cinv_x2` is generated, never hand-maintained.

Three capabilities ride the data:
  - subckt GENERATION per (cell, drive) — the S4c demonstrations
    and the characterization sweeps share one source of truth;
  - characterize_cells: the S5 own-loop executor generalized from
    INV to every combinational cell, per input-pin arc (the
    non-controlling tie is data), emitting ONE multi-cell NLDM
    Liberty;
  - the MANDATORY D11 SPICE-vs-STA composed-path cross-check: a
    two-stage INV chain timed by ngspice (transient truth) and by
    OpenSTA through the emitted Liberty — recorded side by side
    with a stated tolerance, refusing when `sta` is absent.

cell-2 (2026-08-26): AOI21/OAI21/MUX2 with PER-ARC ties and
Liberty `when` conditions, x4 drives, and energy-per-transition
tables (internal_power) integrated from the SAME transients.
Sequential characterization (DFF setup/hold/clk->Q) lives in
cnt_sequential (own-loop bisection; lctime = D14 ladder).

The ladder correspondence (cells -> the computers app's part
classes) is DESIGN, recorded in
AI-Notes/plans/CHIP_COMPUTE_DISTRIBUTION_PLAN.md — chip-4 stays
deferred code-wise (decision 4).

@consumers
  - cntfet.cnt_api ({action: cell-library | characterize-cells |
    d11-crosscheck})
  - cntfet.custom.cnt_cells (generated subckts for the battery)
  - cntfet.cntfet_selftest
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/cnt_cell_library/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

import json
import os
import re
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from objectTreeDecorators import treeObject, treeObjectInit
from cntfet.custom.cnt_cells import (
    PARASITIC_STANDIN_F, _cards, _pwl, _run_ngspice,
    _tau_estimate,
)
from cntfet.cnt_characterization_basis import _crossing, _sta_gate, \
    find_sta, run_sta
from cntfet.custom.cnt_derive import resolve_components
from cntfet.custom.cnt_osdi import compile_osdi, find_ngspice
from cntfet.custom.cnt_vs_model import build_vs_params, vs_terminal_current

from cntfet.objects.cnt_cell_library._shared import CELL_LIBRARY, COMBINATIONAL, DRIVES, MULTI_OUTPUT, SEED_CNT_CELLS, SEQUENTIAL_CELLS, TRISTATE, _device_params, _energy_summary, _liberty_library, _measure_arc_point, _monotone_report, _normalize_library, _null_row, _pair_params, _sample_before, _seed_cells, _seed_notes, _window_energy, arc_id, cell_arcs, characterize_cells, d11_crosscheck, fet_count, liberty_cell_name, library_report, library_subckts, subckt_name, subckt_text  # noqa: F401
from cntfet.objects.cnt_cell_library.CNTCellDefinition import CNTCellDefinition  # noqa: F401
