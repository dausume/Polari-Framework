"""
@module cntfet.cnt_states_basis

fi-0 (2026-08-26): FET operating STATES as data, and the
characteristic-equation criteria that QUALIFY a bias point for a
state — the foundation the intuition graphs (fi-1), the scoring
terms (fi-2) and the stochastic best/worst cases (fi-3) all cite.
Plan: AI-Notes/plans/FET_INTUITION_PLAN.md.

Every quantity a criterion compares is computed from the SAME VS
parameter set p the device's current comes from
(cnt_device_viz.device_model), so "why is this point in that
state" is answered with the model's own equations:

  Vt(Vds)   = vt0 - dVt - DIBL·Vds                    [VS1] eq.(8)
  φt        = kT/q;  n_ss the subthreshold ideality
  SS        = n_ss φt ln10           (60 mV/dec floor at n_ss = 1)
  Vov_min   = vov_decades · SS       (knob: decades of Id above the
                                     Vt crossing before "on")
  Ff        = 1/(1 + exp((Vgsi - (Vt - αφt/2))/(αφt)))  [VS1]
  Vdsat     = (v_xo Lg/μ)(1 - Ff) + φt Ff              [VS1]
  Fsat      = x/(1+|x|^β)^(1/β),  x = Vdsi/Vdsat

States (ordered along a rising-Vgs sweep):
  off            Vgs < Vt(Vds): Id is the subthreshold tail
                 Id ≈ Ioff·10^((Vgs-Vt)/SS) — SS rules everything
  transition-on  Vt ≤ Vgs < Vt + Vov_min: the barrier is collapsing
                 (Ff 1→0); Id climbs the last decades to "on"
  transition-off same band on a FALLING sweep (F1 is hysteresis-free
                 so the bounds are identical — stated, not hidden)
  on-linear      Vgs ≥ Vt + Vov_min and Vds < Vdsat: Fsat ≈ x, Id
                 ∝ Vds (the resistor-like leg of Id-Vd)
  on-saturation  Vgs ≥ Vt + Vov_min and Vds ≥ Vdsat: Fsat → 1,
                 Id = Qxo v_xo (velocity-saturated plateau)

Criteria are DATA (FETOperatingState.criteria_json): lists of
{lhs, op, rhs, why} over a named frame of numbers, evaluated by
`evaluate_criteria` — the same rows the page tables show, so the
"what qualifies" list is never a hidden branch in code. Knobs are
explicit (STATE_KNOBS) and every result carries them plus the F1
fidelity string.

@consumers
  - cntfet.cnt_api (GET /api/cntfet/device/{name}/states)
  - cntfet.cnt_device_viz_seed (state band / guide rows for fi-1 graphs)
  - cntfet.cntfet_selftest
  - polariServer (FETOperatingState registration + SEED_FET_STATES)
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/cnt_states/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

import json
import math
from objectTreeDecorators import treeObject, treeObjectInit
from cntfet.custom.cnt_vs_model import _logistic, vs_terminal_current

from cntfet.objects.cnt_states._shared import FIDELITY, LN10, OPS, SEED_FET_STATES, STATE_KNOBS, _c, _resolve, _state_defs, classify, device_states_report, evaluate_criteria, frame_at, model_vdsat, model_vt, output_boundary, state_at_bias, state_band_rows, subthreshold_swing_v, transfer_boundaries, transitions_on_sweep  # noqa: F401
from cntfet.objects.cnt_states.FETOperatingState import FETOperatingState  # noqa: F401
