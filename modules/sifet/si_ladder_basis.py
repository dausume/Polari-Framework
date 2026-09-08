"""
@module sifet.si_ladder_basis

The OPEN-SILICON FET LADDER (Dustin 2026-08-30): which silicon
process nodes can we LEGITIMATELY reconstruct from public / openly
licensed material, and how well proven is each one?

Two INDEPENDENT axes on every rung — never collapsed:
  * `rights_class`        — what we may DO with it (licence / IP)
  * `fabrication_evidence` — how real the numbers are (measured die
                             ... hypothetical)
A node can be legally clean AND physically predictive (ASAP7) while an
older node has stronger real-silicon evidence (a measured 90 nm die).
`manufacturable` is a THIRD, evidence-only flag: True only when an
actually available open process exists (today: none — every rung says
so and why). An open predictive PDK never implies manufacturability.

Decision S1 = FreePDK45 (NC State, Apache-2.0): the best rung that is
BOTH rights-clean and calibrated against published silicon. Our own
VS-parameterised device (`si-nmos-freepdk45-class`, sifet.si_basis)
is CALIBRATED AGAINST the FreePDK45 documented numbers — we never
incorporate the FreePDK45 BSIM4 card itself; the anchors + the gap
report (`compare_to_anchors`) are the honesty surface.

Licence facts recorded here were fetched on LADDER_REVIEWED_AT (see
each row's source_url / `licence_verified`); PTM's terms could not be
fetched (ptm.asu.edu unreachable that day) → 'to-verify', never
assumed. GPLv3 direction: Apache-2.0 and BSD-3-Clause are ONE-WAY
compatible INTO a GPLv3 project (their material may be combined into
GPLv3 work; the combined work is GPLv3). NC / research-only terms are
a hard blocker per the suite licence gate.

@consumers
  - polariServer (SiliconProcessNode registration + seeds; the
    anchors into CNTCalibrationAnchor; SEED_LADDER_EVIDENCE into
    EvidenceItem; SEED_LADDER_IP into TechnologyIPRecord;
    SEED_SI_LADDER_GRAPHS into GraphDefinition) — to be wired
  - cntfet.cnt_api (GET /api/sifet/ladder → ladder_report) — to be wired
  - sifet.ladder_selftest
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/si_ladder/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

import json
import math
from objectTreeDecorators import treeObject, treeObjectInit
from cntfet.custom.cnt_metrics import extract_metrics
from sifet.custom.si_device import (
    derive_si_device, frame_aware_id_fn, get_row, metric_spec,
    params_from_rows, resolve_components,
)
from sifet.custom import si_model as sm

from sifet.objects.si_ladder._shared import CURVE_BUILDERS, DEVICE_ANCHOR_FLAVOUR, DEVICE_NODE, DOI_ASAP7, DOI_FREEPDK, DOI_PTM, EVIDENCE_REAL, FABRICATION_EVIDENCE, FABRICATION_MATURITY, FABRICATION_RANK, IOFF_TOL_DEC, ION_TOL, LADDER_REVIEWED_AT, LADDER_REVISION, MANUFACTURABLE_RULE, OPENNESS_CLASS, REUSED_EVIDENCE, RIGHTS_CLASS, RIGHTS_CLEAN, SEARCH_PROTOCOL, SEED_LADDER_EVIDENCE, SEED_LADDER_IP, SEED_SILICON_ANCHORS, SEED_SILICON_PROCESS_NODES, SEED_SI_LADDER_GRAPHS, URL_ASAP7, URL_ASAP7_LIC, URL_BSIM4, URL_BSIMCMG, URL_FREEPDK15, URL_FREEPDK45, URL_PTM, URL_PTM45_MIRROR, _EV_KINDS, _EV_PROVES, _FPDK45_COND, _FPDK45_REF, _FPDK45_SRC, _IP_REVIEWED_AT, _MAKE_RULE, _NO_OPEN_PROCESS, _PTM45_SRC, _anchor, _anchors, _ev, _ip, _knob_scan, _ladder_graph, _licence_clean, _metrics_with, _node, _nodes, _num, _reconstruction_status, _rows_of, _search, _verdict, _within, apply_anchor_knob, compare_to_anchors, ladder_ion_rows, ladder_report, per_um_metrics  # noqa: F401
from sifet.objects.si_ladder.SiliconProcessNode import SiliconProcessNode  # noqa: F401
