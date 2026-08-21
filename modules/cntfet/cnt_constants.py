"""
@module cntfet.cnt_constants

Every literature number the S1 aligned-CNT FET model uses, as a
CITED, ROLE-TAGGED record (plan D8: physical | derived |
compact-model | calibration | output roles; never flat constants).
The clean-room rule (plan D3 + S0 gate): equations and values come
from the PAPERS ONLY — the Stanford VS-CNFET source is never read.

Primary sources (cite-values-only bucket, none CC):
  [VS1]  Lee, Pop, Franklin, Haensch, Wong, "A Compact
         Virtual-Source Model for CNFETs in the Sub-10-nm Regime —
         Part I: Intrinsic Elements", IEEE TED 62(9):3061-3069
         (2015), DOI 10.1109/TED.2015.2457453 (read via the legally
         free arXiv:1503.04397 author copy).
  [VS2]  ibid. Part II: Extrinsic Elements, DOI
         10.1109/TED.2015.2457424 (arXiv:1503.04398). S1 uses only
         its existence for scoping — extrinsic tunneling/BTBT are
         S2+.
  [FC10] Franklin & Chen, "Length scaling of carbon nanotube
         transistors", Nat. Nanotech. 5:858-862 (2010), DOI
         10.1038/nnano.2010.220 (author PDF) — the v_xo calibration
         device set (Lg 15 nm / 300 nm / 3 um on the same tube).
  [RAH03] Rahman, Guo, Datta, Lundstrom, "Theory of Ballistic
         Nanotransistors", IEEE TED 50(9):1853-1864 (2003), DOI
         10.1109/TED.2003.815366 (free PDF nanohub.org/resources/122)
         — the F2 top-of-the-barrier reference set.
  [LUN97] Lundstrom, "Elementary Scattering Theory of the Si
         MOSFET", IEEE EDL 18(7):361-363 (1997), DOI
         10.1109/55.596937 — T = lambda/(lambda+L).
  [GUO04] Guo et al., multiscale CNFET modeling, arXiv
         cond-mat/0312551 — hyperbolic E(k), m* = Eg/(2 vF^2).
  [JAV04] Javey et al., PRL 92:106804 (2004), arXiv
         cond-mat/0309242 — mfp anchors lambda_AP ~300 nm,
         lambda_OP ~15 nm.
  [PARK04] Park et al., Nano Lett. 4:517 (2004), arXiv
         cond-mat/0309641 — lambda_ac ~300 nm low bias,
         lambda_op ~10-15 nm high bias.
  [WIL98] Wildoer et al., Nature 391:59 (1998), DOI 10.1038/34139 —
         STS bandgap: gamma0 = 2.7 +/- 0.1 eV, Eg ~ 0.77 eV nm / d.
  [KHA09] Khakifirooz, Nayfeh, Antoniadis, IEEE TED 56(8):1674-1680
         (2009), DOI 10.1109/TED.2009.2024022 — the original
         virtual-source (VS) MOSFET formulation [VS1 ref 24];
         alpha/beta smoothing values quoted via [VS1].

@consumers
  - cntfet.cnt_bandstructure / cnt_tob / cnt_vs_model (equations)
  - cntfet.cnt_calibration (anchor rows)
  - cntfet.selftest_cntfet (value pins)
"""

import math

# ---- exact/CODATA physical constants (role: physical) -------------
Q_C = 1.602176634e-19          # elementary charge [C] (exact, SI)
H_JS = 6.62607015e-34          # Planck [J s] (exact, SI)
HBAR_JS = H_JS / (2.0 * math.pi)
KB_J_PER_K = 1.380649e-23      # Boltzmann [J/K] (exact, SI)
EPS0_F_PER_M = 8.8541878128e-12


def _rec(value, unit, role, source, confidence, notes=''):
    """One structured, cited number (the hwsim structured-property
    shape + the D8 role axis)."""
    return {'value': value, 'unit': unit, 'role': role,
            'source': source, 'confidence': confidence,
            'notes': notes}


# ---- literature numbers (every one cited + role-tagged) -----------
LIT = {
    # Graphene/CNT lattice.
    'a_cc_nm': _rec(0.142, 'nm', 'physical',
                    '[VS1] Sec.II (a_cc, C-C distance)', 'high'),
    'Ep_eV': _rec(3.0, 'eV', 'compact-model',
                  '[VS1] Sec.II: Eg = 2 Ep a_cc / d with Ep = 3 eV '
                  '(Hueckel tight-binding)', 'high',
                  'Model-family value. The STS experiment [WIL98] '
                  'gives gamma0 = 2.7 +/- 0.1 eV (Eg ~ 0.77/d); the '
                  'VS-CNFET family uses Ep = 3 eV (Eg ~ 0.85/d). '
                  'Both recorded; the model uses Ep, the residual '
                  'is calibration-visible.'),
    'gamma0_exp_eV': _rec(2.7, 'eV', 'calibration',
                          '[WIL98] STS: gamma0 = 2.7 +/- 0.1 eV',
                          'high', 'uncertainty +/- 0.1 eV'),
    # Effective quantum capacitance [VS1 Sec.II.A].
    'cqe_coeff': _rec(0.64, 'fF/(um sqrt(eV))', 'compact-model',
                      '[VS1] Sec.II.A: Cqe = 0.64 sqrt(Eg) + 0.1 '
                      '(fF/um, Eg in eV)', 'medium',
                      'empirical fit to numerical simulation'),
    'cqe_offset': _rec(0.1, 'fF/um', 'compact-model',
                       '[VS1] Sec.II.A (same fit)', 'medium'),
    # Apparent-mobility model [VS1 eq.(4)].
    'mu0_cm2_per_vs': _rec(1350.0, 'cm^2/(V s)', 'compact-model',
                           '[VS1] eq.(4): mu = mu0 Lg/(lambda_mu + '
                           'Lg) d^c_mu', 'medium',
                           'empirical fit; d in nm'),
    'lambda_mu_nm': _rec(66.2, 'nm', 'compact-model',
                         '[VS1] eq.(4)', 'medium'),
    'c_mu': _rec(1.5, '1', 'compact-model', '[VS1] eq.(4)', 'medium'),
    # VS injection-velocity model [VS1 eq.(9)].
    'lambda_v_nm': _rec(440.0, 'nm', 'compact-model',
                        '[VS1] Sec.II.D: v_xo = lambda_v/'
                        '(lambda_v + 2 l) vB, l ~= Lg; lambda_v = '
                        '440 nm fitted to [FC10]', 'medium'),
    'vB0_m_per_s': _rec(4.1e5, 'm/s', 'compact-model',
                        '[VS1] Sec.II.D: vB = vB0 sqrt(d/d0), '
                        'vB0 = 4.1e7 cm/s', 'medium'),
    'd0_nm': _rec(1.2, 'nm', 'compact-model',
                  '[VS1] Sec.II.D reference diameter (the [FC10] '
                  'tube)', 'high'),
    # VS smoothing parameters (via [VS1] Sec.II.D <- [KHA09]).
    'alpha_vs': _rec(3.5, '1', 'compact-model',
                     '[VS1] Sec.II.D extraction step (d): alpha = '
                     '3.5 as suggested in [KHA09]', 'medium'),
    'beta_vs': _rec(1.8, '1', 'compact-model',
                    '[VS1] Sec.II.D extraction step (d): beta = 1.8',
                    'medium'),
    # Scale-length model [VS1 eq.(7)].
    'z0_bessel': _rec(2.405, '1', 'physical',
                      '[VS1] eq.(7): z0, first zero of J0 (2.40483)',
                      'high'),
    'k_cnt': _rec(1.0, '1', 'compact-model',
                  '[VS1] Sec.II.C: k_cnt = 1 used (air inside the '
                  'tube); 5-20 reported elsewhere, eq.(7) holds '
                  'across the range', 'medium'),
    'lof_over_tox': _rec(1.0 / 3.0, '1', 'compact-model',
                         '[VS1] Sec.II.C: Lof ~= tox/3 empirical '
                         'best fit', 'medium'),
    # Phonon energies / mean free paths (F2 + mobility physics).
    'hw_op_eV': _rec(0.18, 'eV', 'physical',
                     '[VS1] eq.(3) context: hbar w_OP ~ 0.18 eV '
                     '(0.16-0.2 eV in [JAV04])', 'medium'),
    'lambda_ap_nm': _rec(300.0, 'nm', 'physical',
                         '[JAV04]/[PARK04]: acoustic-phonon mfp '
                         '~300 nm (low bias)', 'medium',
                         'd,T scaling exists (Perebeinos '
                         'cond-mat/0411021) — S1 holds d,T fixed'),
    'lambda_op_nm': _rec(12.5, 'nm', 'physical',
                         '[JAV04]/[PARK04]: optical-phonon mfp '
                         '10-15 nm at high bias (midpoint)', 'low',
                         'S1 F2 uses the acoustic mfp only; OP '
                         'scattering is a named gap'),
    # Contact quantum floor [VS1 Sec.IV].
    'rq_half_ohm': _rec(H_JS / (4.0 * Q_C * Q_C) / 2.0, 'ohm',
                        'physical',
                        '[VS1] Sec.IV: Rs = RQ/2 = h/(2(2q^2)) ~ '
                        '3.3 kOhm per terminal (lowest band, '
                        '2 spins x 2 valleys)', 'high'),
}

# Equation revision shared by the Python reference and the
# Verilog-A twin (plan D3: both implement the SAME revision and are
# regression-compared).
EQUATION_REVISION = 'cntfet-vs-s1-r1'

MODEL_LABEL = {
    'model_family': 'VS-CNFET-derived',
    'implementation': 'independent',
    'numerically_equivalent_to_stanford': False,
    'equation_revision': EQUATION_REVISION,
    'clean_room': 'equations from [VS1]/[RAH03] papers only; '
                  'Stanford VS-CNFET source never read (NEEDS '
                  'Modified CMC License, GPL-incompatible)',
}


def lit_value(key):
    return LIT[key]['value']


def thermal_voltage_v(temperature_k):
    """kT/q [V] — role: derived."""
    return KB_J_PER_K * temperature_k / Q_C
