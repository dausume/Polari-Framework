"""
@module cntfet.cnt_transport_basis

fv-2 (2026-08-27): the TRANSPORT regime of a FET — is carrier
velocity Ballistic / Quasi-Ballistic / Semi-Scattered / Scattered —
and, when scattered, WHICH mechanisms contribute and what they
enforce on the device over time. Plan: AI-Notes/plans/FET_VIEWS_PLAN.md
§1 fv-2. Sibling of cnt_states (states as data with criteria_json).

Physics (every equation cited, every number a LIT record or a knob):

  Matthiessen   1/λ_eff = Σ_i 1/λ_i(bias, T, t)          [LUN97]
  transmission  T = λ_eff/(λ_eff + Lg)                   [LUN97]
  ballistic eff B = T/(2 − T)   (Ion = Ion_ballistic·B,
                v_inj = v_T·B)                           [LUN97]/[RAH03]
  VS ballisticity  v_xo/vB = λ_v/(λ_v + 2 Lg), λ_v = 440 nm — the
                compact model's OWN fitted definition, reported
                BESIDE ours (two definitions, both stated)   [VS1] §II.D
  apparent mobility  μ_app = v_T λ_eff/(2 kT/q) (1-D non-degenerate
                thermal velocity v_T = sqrt(2kT/(π m*)))     [LUN97]

Mechanisms (ScatteringMechanism rows, seeded — see the seeds for
the citations and the PRIOR labels):
  acoustic-phonon        λ_ac = 300 nm · (d/d0) · (T0/T)   [JAV04]/[PARK04]
  optical-phonon         λ_op = 12.5 nm, ACTIVE only when the
                         carrier can gain ħω_op: q·Vds ≥ 0.18 eV
                                                       [JAV04]/[PARK04]/[VS1]
  defect-impurity        λ_def ∝ 1/(1 − purity) — PRIOR from the
                         purification row; ages: λ/(1 + t/τ) PRIOR
  contact-interface      NOT a mfp: T_c = (RQ/2)/Rc clipped ≤ 1,
                         multiplicative on T                 [VS1] §IV
  alignment-misorientation  NOT a mfp: the path lengthens,
                         Lg_eff = Lg/cos(σ_θ) (the S3 sampler's rule)

Regimes (TransportRegime rows, criteria_json over the transport
frame; thresholds are TRANSPORT_KNOBS and are echoed):
  ballistic T ≥ 0.9 · quasi-ballistic 0.6 ≤ T < 0.9 ·
  semi-scattered 0.3 ≤ T < 0.6 · scattered T < 0.3

Honesty: the regime is classified on the CHANNEL transmission by
default (knob `regime_on`: 'channel' | 'total'); the contact factor
is reported separately because the VS current already carries Rc
as series resistance — folding T_c into Ion would double count.
Time profiles are PRIORS (low confidence) until a measured aging
series exists; priorFlagged lists every prior that touched a number.

@consumers
  - cntfet.cnt_api (GET /api/cntfet/device/{name}/transport — wired
    by the integrator)
  - cntfet.cnt_device_viz_seed (CURVE_BUILDERS for the transport graphs)
  - cntfet.transport_selftest
  - polariServer (ScatteringMechanism / TransportRegime registration
    + SEED_* passes, SEED_CNT_TRANSPORT_GRAPHS concat)
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/cnt_transport/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

import json
import math
from objectTreeDecorators import treeObject, treeObjectInit
from cntfet.custom.cnt_bandstructure import M0_KG, m_eff_over_m0
from cntfet.custom.cnt_constants import KB_J_PER_K, Q_C, lit_value
from cntfet.custom.cnt_derive import get_row, resolve_components
from cntfet.cnt_device_viz_seed import _device_graph
from cntfet.cnt_states_basis import OPS, evaluate_criteria

from cntfet.objects.cnt_transport._shared import CURVE_BUILDERS, FIDELITY, LG_GRID_NM, REF_D_NM, SEED_CNT_TRANSPORT_GRAPHS, SEED_SCATTERING_MECHANISMS, SEED_TRANSPORT_REGIMES, TRANSPORT_KNOBS, _MECH_FIELDS, _NO_AGING, _aged, _c, _log_times, _regime, _regime_bands, _table_rows, apparent_mobility_cm2_per_vs, ballistic_efficiency, classify_regime, contact_transmission, effective_length_nm, mechanism_defs, mechanism_lambdas, regime_defs, scattering_contribution_rows, thermal_velocity_m_per_s, transmission, transport_context, transport_frame, transport_over_time_rows, transport_report, transport_vs_lg_rows, vs_model_ballisticity  # noqa: F401
from cntfet.objects.cnt_transport.ScatteringMechanism import ScatteringMechanism  # noqa: F401
from cntfet.objects.cnt_transport.TransportRegime import TransportRegime  # noqa: F401
