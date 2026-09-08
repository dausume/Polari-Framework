"""
@module cntfet.cnt_regimes_basis

fv-1 (2026-08-27, FET_VIEWS_PLAN §fv-1): the MOSFET-style IV
REGIMES as data — the sub-regimes of "on" the fi-0 states do not
resolve (linear/triode, square-law, velocity-saturated, the
exponent crossover, DIBL-tilted saturation) — plus the 2-D regime
MAP on the (Vd, Vg) plane, the Id–Vg EXPONENT curve and the
regime-coloured output family.

The discriminating number is the LOCAL EXPONENT of the drive law,

  m = d ln Id / d ln Vov,   Vov = Vgsi - Vt(Vds)      (fixed Vd)

evaluated by a central difference on the SAME VS model the device's
curves come from (cnt_device_viz.device_model → p). Textbook laws:

  long-channel square law   Id = (μ Cinv/2Lg)(Vgs - Vt)²  → m ≈ 2
                            (Vds ≥ Vdsat = Vgs - Vt)       [SZE-type]
  velocity-saturated        Id = Qxo·v_xo,  Qxo ∝ Vov      → m ≈ 1
                            (Fsat → 1, the VS/ballistic limit)
                            [VS1] eq.(9)-(10), [KHA09], [RAH03]
  triode                    Id ≈ Qxo·v_xo·Vds/Vdsat ∝ Vds  (Vds < Vdsat)
  subthreshold              Id ∝ exp(Vgs/(n_ss φt))          (Vgs < Vt)
  DIBL-tilted saturation    Vt = vt0 - dVt - DIBL·Vds ⇒ dId/dVds =
                            gm·DIBL ≠ 0 in saturation      [VS1] eq.(8)

HONESTY: the VS compact model saturates by VELOCITY, not by
pinch-off — Vdsat = (v_xo Lg/μ)(1-Ff) + φt Ff does not grow with
Vov, so Id ∝ Qxo ∝ Vov in strong inversion and m → 1 (below 1 when
the series Rc eats Vov). A synthetic long-channel parameter set
moves m UP toward 1 (Rc-free) but the model CANNOT reach m ≈ 2:
the square-law band is a reference band the reader compares
against, and a device that lands in it would be doing so through
the softplus/Ff corner, not the textbook pinch-off law. This is
stated on the row and in the verdict, not hidden.

Regimes are DATA (FETRegime.criteria_json: [{lhs, op, rhs, why}]
over the extended frame of `regime_frame`), evaluated by
cnt_states.evaluate_criteria; first row (by order) whose criteria
ALL pass wins; manager rows win over seeds. Bands and thresholds
are explicit knobs (REGIME_KNOBS), echoed on every payload.

@consumers
  - cntfet.cnt_api (GET /api/cntfet/device/{name}/regimes?vg=&vd=)
  - cntfet.cnt_device_viz_seed (CURVE_BUILDERS → device_curve_points)
  - cntfet.regimes_selftest
  - polariServer (FETRegime registration + SEED_FET_REGIMES;
    SEED_CNT_REGIME_GRAPHS concat onto the GraphDefinition pass)
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/cnt_regimes/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

import json
import math
from objectTreeDecorators import treeObject, treeObjectInit
from cntfet.cnt_states_basis import (
    STATE_KNOBS, evaluate_criteria, frame_at,
)

from cntfet.objects.cnt_regimes._shared import CURVE_BUILDERS, FIDELITY, OUTPUT_VG, REGIME_KNOBS, SEED_CNT_REGIME_GRAPHS, SEED_FET_REGIMES, _M_OK, _ON, _SAT, _build_exponent, _build_map, _build_output, _c, _device_graph, _grid, _id, _regime_defs, _verdict, classify_regime, device_regimes_report, exponent_rows, map_summary, output_regime_rows, regime_at_bias, regime_frame, regime_map, vov_exponent  # noqa: F401
from cntfet.objects.cnt_regimes.FETRegime import FETRegime  # noqa: F401
