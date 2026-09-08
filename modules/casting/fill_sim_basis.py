"""
@cross-cutting
@module casting.fill_sim_basis
@tags @xc:bindings

cast-5 core: SIMULATE THE FILL — does the poured material reach
everywhere, and where does air get trapped? Quasi-static gravity
model on the cast-2 OccupancyGrid, with the cast-4 channels as the
plumbing:

  DOMAIN     the `--master-sprued` shape (cavity + channels as ONE
             solid) voxelized on the STOCK lattice — channel exits
             land exactly on the grid boundary, so "outside" is
             well-defined.
  FEED       fluid enters at the SPRUE mouths (boundary cells inside
             the sprue shapes — vents are air exits, not feeds) and
             fills level-by-level from the bottom; channels are
             always traversable (fluid falls through them).
  UNFED      cavity regions with NO path from the gate at all — the
             gate feeds the wrong chamber (a real two-chamber
             failure this sim catches).
  AIR        at every level, air must escape to a boundary through
             air cells OR through channels (counterflow up a filled
             gate is allowed WITH a finding — bubble defects); an
             air region that loses every escape path is TRAPPED at
             that level and never fills.
  FREEZE     fill time (cavity volume ÷ pour rate, Torricelli rate
             from the gate neck by default — claim named) against
             the material's pot life; ratio > 1 blocks.

Verdicts are knobs-and-suggestions: a trapped pocket names its top
cell — exactly where cast-4 would put the next vent — and never
auto-applies anything.

MoldFillSimState rows (one per domain cell per recorded level, the
WaxPrintSimState idiom) make runs 3D-viewable; the SimSpace scene
binding lands with the cast-9 page pass (named).

Named unmodelled v1: turbulence, surface tension/menisci, viscosity-
limited channel flow, gas back-pressure magnitude, thermal front
during fill (metals refuse — their freeze window is not seeded).

@see /WAX_MOLD_NESTING_PLAN.md (PHASE cast-5)
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/fill_sim/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

import json
import math
from casting.custom.mold_geometry import _mold_named, _rows
from casting.custom.voxel_grid import OccupancyGrid
from casting.custom.wax_feasibility import _row_named
from mathshapes.custom.shape_analysis import _named, evaluate_point
from objectTreeDecorators import treeObject, treeObjectInit

from casting.objects.fill_sim._shared import FILL_MATERIAL_PRIORS, _G, _boundary_cells, _cells_in_shapes, _sprue_instance_for, compute_fill_rows, simulate_fill  # noqa: F401
from casting.objects.fill_sim.MoldFillSimState import MoldFillSimState  # noqa: F401


def persist_fill_rows(manager, rows):
    """Insert-or-overwrite MoldFillSimState rows (derived — always
    converge, the cast-1 rule). Real treeObjects when the manager
    hosts them; attribute bundles for duck managers."""
    table = manager.objectTables.setdefault('MoldFillSimState', {})
    by_name = {getattr(r, 'name', None): r for r in table.values()}
    inserted = updated = 0
    for rd in rows:
        row = by_name.get(rd['name'])
        if row is not None:
            for k, v in rd.items():
                setattr(row, k, v)
            updated += 1
            continue
        made = None
        try:
            made = MoldFillSimState(**rd, manager=manager)
        except Exception:
            made = None
        if made is None or rd['name'] not in {
                getattr(r, 'name', None) for r in table.values()}:
            class _Row:
                pass
            r = _Row()
            for k, v in rd.items():
                setattr(r, k, v)
            table[rd['name']] = r
        inserted += 1
    return {'inserted': inserted, 'updated': updated}
