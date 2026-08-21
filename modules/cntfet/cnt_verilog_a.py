'''
@module cntfet.cnt_verilog_a

S1d half 1: the clean-room Verilog-A twin of cnt_vs_model —
GENERATED text so the equation revision can never drift silently
from the Python reference (both carry EQUATION_REVISION; the
cnt_osdi regression proves numerical equivalence).

Construct gate (S0 OpenVAF verdict): single flat module, scalar
parameters, static contributions only — NO arrays, named events,
cross(), bit-shifts, analog filters (laplace_*/transition/absdelay),
genvar, or $table_model. construct_gate_check() lints the generated
source against that list so the gate is executable, not aspirational.

The exp-safe piecewise forms MIRROR the Python reference exactly
(same +/-40 cutovers) — that is what makes bit-close equivalence
achievable.

@consumers
  - cntfet.cnt_osdi (compile + regression)
  - cntfet.cnt_api ({action: verilog-a} download)
  - cntfet.selftest_cntfet (gate check)
'''

import re

from cntfet.cnt_constants import EQUATION_REVISION, MODEL_LABEL

_VA_TEMPLATE = r'''// cntfet_vs_s1.va — clean-room VS-CNFET-DERIVED compact model
// equation_revision: {revision}
// model_family: {family} | implementation: {implementation}
// numerically_equivalent_to_stanford: false
//
// CLEAN ROOM: equations reimplemented from the PUBLISHED papers
// only — Lee/Pop/Franklin/Haensch/Wong, IEEE TED 62(9):3061 (2015),
// DOI 10.1109/TED.2015.2457453 (read via arXiv:1503.04397) and the
// original VS formulation Khakifirooz et al., IEEE TED 56(8):1674
// (2009), DOI 10.1109/TED.2009.2024022. The Stanford VS-CNFET
// Verilog-A source (NEEDS Modified CMC License) was NEVER read.
// This model is NOT the Stanford VS-CNFET and must not be called
// that.
//
// Scope (S1): DC only, one tube, n-type; channel + Rc + SCE
// (profile VS_MINIMAL). No BTBT / S-D tunneling / parasitics —
// those are S2+ additive mechanisms, absent not approximated.
//
// License: GPL-3.0-or-later (polari project license).

`include "disciplines.vams"

// Exact SI-2019 constants, pinned to the SAME values the Python
// reference uses (constants.vams carries older CODATA values —
// that difference is visible at the D3 regression's tolerance in
// the subthreshold exponentials, proven live 2026-08-21).
`define KB_EXACT 1.380649e-23
`define Q_EXACT  1.602176634e-19

module cntfet_vs_s1(d, g, s);
    inout d, g, s;
    electrical d, g, s, di, si;

    // roles ride the generated parameter manifest, not the .va:
    parameter real lg_m  = 15e-9  from (0:inf);   // gate length [m]
    parameter real cinv  = 2.8e-10 from (0:inf);  // [F/m]
    parameter real vxo   = 3.8e5  from (0:inf);   // [m/s]
    parameter real mu    = 3.5e-3 from (0:inf);   // [m^2/Vs]
    parameter real vt0   = 0.3;                   // [V]
    parameter real dvt   = 0.0   from [0:inf);    // Vt roll-off [V]
    parameter real dibl  = 0.0   from [0:inf);    // [V/V]
    parameter real nss   = 1.0   from (0:inf);    // SS factor
    parameter real alpha = 3.5;
    parameter real beta  = 1.8   from (0:inf);
    parameter real rs    = 5500.0 from (0:inf);   // [ohm]
    parameter real rd    = 5500.0 from (0:inf);   // [ohm]
    parameter real tdev  = 300.0 from (0:inf);    // [K]
    // r2 polarity: 0 = n-type, 1 = p-type (mirrored equations,
    // [VS1] premise ii — symmetric bands). sgn folds the mirror
    // into the same expressions the Python reference mirrors.
    parameter real ptype = 0.0 from [0:1];

    real phit, vt, ff, qxo, vdsats, vdsat, xx, axx, fsat, idch;
    real ffarg, qarg, splus, sgn, ugsi, udsi;

    analog begin
        phit = `KB_EXACT * tdev / `Q_EXACT;
        if (ptype > 0.5)
            sgn = -1.0;
        else
            sgn = 1.0;
        ugsi = sgn * V(g, si);
        udsi = sgn * V(di, si);
        vt = vt0 - dvt - dibl * udsi;

        // logistic(-ffarg), exp-safe at +/-40 (mirrors Python)
        ffarg = (ugsi - (vt - alpha * phit / 2.0))
                / (alpha * phit);
        if (ffarg > 40.0)
            ff = 0.0;
        else if (ffarg < -40.0)
            ff = 1.0;
        else
            ff = 1.0 / (1.0 + exp(ffarg));

        // softplus(qarg), exp-safe at +/-40 (mirrors Python)
        qarg = (ugsi - (vt - alpha * phit * ff))
               / (nss * phit);
        if (qarg > 40.0)
            splus = qarg;
        else if (qarg < -40.0)
            splus = exp(qarg);
        else
            splus = ln(1.0 + exp(qarg));
        qxo = cinv * nss * phit * splus;

        vdsats = vxo * lg_m / mu;
        vdsat = vdsats * (1.0 - ff) + phit * ff;
        xx = udsi / vdsat;
        axx = abs(xx);
        fsat = xx / pow(1.0 + pow(axx, beta), 1.0 / beta);
        idch = qxo * vxo * fsat;

        I(di, si) <+ sgn * idch;
        // Rc first-class (D9): per-terminal series resistances as
        // their own branches — the SPICE solver owns the internal
        // nodes (the Python reference fixed-points the same system).
        I(d, di) <+ V(d, di) / rd;
        I(si, s) <+ V(si, s) / rs;
    end
endmodule
'''


def generate_va():
    """The .va source for the current equation revision."""
    return _VA_TEMPLATE.format(
        revision=EQUATION_REVISION,
        family=MODEL_LABEL['model_family'],
        implementation=MODEL_LABEL['implementation'])


# (pattern, why it is banned) — the S0 OpenVAF construct gate.
_BANNED = [
    (r'laplace_\w+', 'analog filter (laplace_*)'),
    (r'\btransition\s*\(', 'analog filter (transition)'),
    (r'\babsdelay\s*\(', 'analog filter (absdelay)'),
    (r'\bcross\s*\(', 'event cross()'),
    (r'@\s*\(\s*(?!initial_step|final_step)\w+',
     'named/monitored event'),
    (r'\bgenvar\b', 'genvar/generate'),
    (r'<<|>>', 'bit-shift operator'),
    (r'\$table_model', 'table model'),
    (r'^\s*(?:real|integer)\s+\w+\s*\[', 'module-internal array'),
]


def construct_gate_check(va_text):
    """Lint the source against the banned-construct list + the
    single-flat-module rule. Returns {'ok', 'violations'}."""
    violations = []
    for pattern, why in _BANNED:
        if re.search(pattern, va_text, flags=re.MULTILINE):
            violations.append(why)
    if len(re.findall(r'\bmodule\b', va_text)) != 1:
        violations.append('must be a single flat module')
    return {'ok': not violations, 'violations': violations}
