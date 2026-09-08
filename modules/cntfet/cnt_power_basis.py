"""
@module cntfet.cnt_power_basis

fp-1 (FET_CELL_POWER_SILICON_PLAN §1, 2026-08-27): power
dissipation LIMITS for the FET and for the standard cells built
from it — static (leakage) and dynamic — as data with explicit
knobs, named gaps and budgets that say WHICH limit fails.

FET (from the same F1 model frame every fv/fi surface reads):
  P_static  = Vdd · Ioff             Ioff = Id(Vgs = 0, Vds = Vdd)
                                      (cnt_metrics definition)
  Ioff(Vt)  ∝ 10^(−Vt/SS)            → dlog10(Ioff)/dVt = −1/SS
  Ioff(T)   : SS = n_ss·φt·ln10, φt = kT/q → SS(T) = SS(300)·T/300
              (Vt and n_ss held; the prefactor's own T dependence
              is NOT modelled — stated approximation)
  E_switch  = C_gg · Vdd²            C_gg = Cinv·Lg (+ C_par row)
  P_dyn     = α · f · C_gg · Vdd²    [RAB03] textbook CMOS dynamic
                                      power; α = activity factor
  gate leakage / GIDL: NAMED GAPS at S1 — the VS model has no
  tunnelling term ([VS1] is thermionic + Rc); no number is
  invented for them (plan §2 decision 1).

Cell: leakage per INPUT STATE from the OFF network. The
transistor netlist of CELL_LIBRARY (flattened through `compose`)
is evaluated per input vector — an n device conducts when its
gate net is 1, a p device when it is 0; nets take the value of
any rail/input they reach through conducting devices. Every path
from a 1-valued net to a 0-valued net through k ≥ 1 OFF devices
(floating intermediates) leaks Ioff · stack_factor^(k−1): the
STACK EFFECT [NAR01] — series off devices raise the internal node,
reverse-bias the upper device's Vgs and drop its Vds, so each
extra series off device cuts the leakage by a factor the knob
holds (default 0.5, i.e. 2× per stacked device; the measured
range is 2–10× depending on DIBL and Vt). Drive xN = N parallel
devices per position → N× the per-position leakage. The path sum
is an UPPER bound when paths share a device (stated on the row).

Liberty: cnt_cell_library._liberty_library grew an optional
`leakage` entry per cell block ({when → W}) that emits
  leakage_power () { when : "!A"; value : <uW>; }
blocks + `cell_leakage_power : <mean uW>;` — OpenSTA-readable
grammar, backward compatible (blocks without it emit nothing).

Budgets: PowerBudget rows (scope fet | cell | block) with limits on
static W, dynamic W, W/cm² and K; `check_budget` names the limit
that fails and its margin — never a bare boolean.

Score terms: fet-static-power / cell-static-power /
cell-dynamic-energy in the cnt_scoring `_term` seed shape (lower is
better; min-max on log10 spans — the spans are the knobs); the
integrator adds them to FET_TERMS / CELL_TERMS and the frame keys
here (`power_frame`) are what they cite.

@consumers
  - cntfet.cnt_api (GET /api/cntfet/device/{name}/power,
    /cell-power — integrator wires)
  - cntfet.cnt_cell_library_basis (leakage blocks)
  - cntfet.cnt_device_viz_seed (CURVE_BUILDERS)
  - polariServer (PowerBudget / ScoreTerm / GraphDefinition seeds)
  - cntfet.power_selftest
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/cnt_power/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

import itertools
import json
import math
import re
from objectTreeDecorators import treeObject, treeObjectInit
from cntfet.custom.cnt_metrics import extract_metrics
from cntfet.cnt_states_basis import LN10, model_vt, subthreshold_swing_v

from cntfet.objects.cnt_power._shared import CATEGORY, CURVE_BUILDERS, EQUATIONS, FIDELITY, POWER_CITATIONS, POWER_KNOBS, POWER_TERMS, SEED_CNT_POWER_GRAPHS, SEED_POWER_BUDGETS, SEED_POWER_SCORE_TERMS, _LEAK_RE, _LIMITS, _budget_rows, _c_par_f, _conducts, _describe, _dynamic_from_library, _fet_ioffs, _get, _graph, _k, _log10, _off_paths, _refuse, _seed_terms, _term, _twin_ioffs, _when, budget_report, cell_leakage_state_rows, cell_leakage_states, cell_power, check_budget, evaluate_netlist, fet_power, flatten_devices, leakage_blocks_for, leakage_vs_vt_rows, library_power, parse_leakage, power_breakdown_rows, power_frame  # noqa: F401
from cntfet.objects.cnt_power.PowerBudget import PowerBudget  # noqa: F401
