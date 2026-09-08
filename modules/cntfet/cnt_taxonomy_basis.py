"""
@module cntfet.cnt_taxonomy_basis

fp-3 (2026-08-27, FET_CELL_POWER_SILICON_PLAN §1 fp-3): the FET
TAXONOMY as rows — what a transistor is optimized FOR, what SHAPE
its gate takes, which device is its COMPLEMENT, and the three
operating REGIONS every FET page explains to the average person.

  FETOptimizationClass  switching-optimized (digital) vs
                        signal-optimized (analog): the figures of
                        merit each maximises/minimises, the region
                        each prefers, the score concept each maps to.
  fet-signal-quality    a SECOND score concept (cnt_scoring's
                        fet-switching-quality is the first) over a
                        SIGNAL FRAME at a declared analog bias:
                          gm/Id      ideal 1/(n φt) — the weak-inversion
                                     limit (≈ 38.7 /V at 300 K, n = 1)
                                     [EKV95] [SIL96]
                          gm/gds     intrinsic gain — higher better
                                     [RAZ01] [SAN06]
                          headroom   (Vds − Vdsat)/Vdd ≥ margin knob:
                                     the device must sit in saturation
                                     with room for signal swing
                          linearity  |d²Id/dVg²|/gm — lower better (0
                                     = a perfectly linear
                                     transconductor; 1/(n φt) = the
                                     exponential subthreshold law)
  FETShapeType          planar bulk / SOI / FinFET / GAA nanowire /
                        GAA nanosheet / CNT-GAA / TFET with the
                        electrostatic SCALE LENGTH formula as DATA
                        ([YAN92] [FTW98] [AP97] [TN09]) and n_ss /
                        DIBL priors (cited, marked prior).
  ComplementaryPair     n ↔ p with the LOGIC (why CMOS works) and the
                        CONDITIONS as data, evaluated with numbers by
                        `check_pair`; `complementary_of` resolves a
                        device's partner or names the affordance.
  regions_summary       Sub-threshold / Linear / Saturation with the
                        numeric boundaries Vt(Vds), Vt + Vov_min and
                        Vdsat (BdSat) per Vg — every number from
                        cnt_states (fi-0) / cnt_regimes (fv-1).

Everything downstream of `device_model → (id_fn, p)` is model-agnostic
(plan §0): a SiliconMOSFET row whose model yields the VS `p` gets the
same taxonomy report.

Honesty (stated everywhere it matters): the `cnt-aligned-s1-p` row's
polarity is a LABEL today — build_vs_params pins ptype 0, so the p
twin derives to the n numbers. `check_pair` applies the [VS1]
premise-ii mirror EXPLICITLY (solve n-system at (−Vg, −Vd), negate
Id) and says so in its payload; under that mirror the twin is exactly
symmetric, which is why the pair conditions pass by construction.

@consumers
  - cntfet.cnt_api (fp-6 integrator: /taxonomy, /signal-score,
    /complementary, /regions)
  - cntfet.cnt_device_viz_seed (curves 'signal-terms',
    'optimization-radar' via CURVE_BUILDERS)
  - polariServer (FETOptimizationClass / FETShapeType /
    ComplementaryPair registration + seeds; ScoreTerm/ScoreConcept
    seeds SEED_SIGNAL_SCORE_TERMS / SEED_SIGNAL_SCORE_CONCEPTS)
  - cntfet.taxonomy_selftest
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/cnt_taxonomy/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

import json
import math
from objectTreeDecorators import treeObject, treeObjectInit
from cntfet.custom.cnt_metrics import extract_metrics
from cntfet.cnt_regimes_basis import REGIME_KNOBS, regime_frame
from cntfet.cnt_scoring_seed import (
    CATEGORY as SWITCHING_CATEGORY, CONCEPT_NAME as SWITCHING_CONCEPT,
    FET_TERMS, SCORE_KNOBS, _term, fet_validity, score_device,
)
from cntfet.cnt_states_basis import (
    LN10, STATE_KNOBS, frame_at, model_vt, output_boundary,
    subthreshold_swing_v, transfer_boundaries,
)
from cntfet.custom.cnt_vs_model import vs_terminal_current

from cntfet.objects.cnt_taxonomy._shared import CURVE_BUILDERS, FIDELITY, PAIR_KNOBS, PAIR_LOGIC, PROVENANCE, SEED_CNT_TAXONOMY_GRAPHS, SEED_COMPLEMENTARY_PAIRS, SEED_FET_OPTIMIZATION_CLASSES, SEED_FET_SHAPE_TYPES, SEED_SIGNAL_SCORE_CONCEPTS, SEED_SIGNAL_SCORE_TERMS, SIGNAL_CATEGORY, SIGNAL_CONCEPT, SIGNAL_KNOBS, SIGNAL_TERMS, TAXONOMY_CITATIONS, _, _GM_ID_LIMIT_300, _PHIT_300, _SHAPE_ALIASES, _SI_PAIR_CONDITIONS, _build_radar, _build_signal, _device_graph, _opt, _pair_rows, _polarity_metrics, _rows_from_manager, _sdescribe, _shape_rows, _signal_term_rows, _signal_weights, _sterm, check_pair, classify_optimization, complementary_of, device_taxonomy_report, regions_summary, score_from_frame_registry, score_signal, score_signal_from_model, shape_of, signal_frame, signal_term_rows  # noqa: F401
from cntfet.objects.cnt_taxonomy.FETOptimizationClass import FETOptimizationClass  # noqa: F401
from cntfet.objects.cnt_taxonomy.FETShapeType import FETShapeType  # noqa: F401
from cntfet.objects.cnt_taxonomy.ComplementaryPair import ComplementaryPair  # noqa: F401
