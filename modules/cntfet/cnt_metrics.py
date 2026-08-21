"""
@module cntfet.cnt_metrics

S2a: the device-metric family extracted from ANY engine's
Id(Vg, Vd) — the plan's round-2(d) rule: validation compares
Id-Vg/Id-Vd families, SS, Ion, Ioff, gm, DIBL, not one headline
on/off number. Engine-agnostic: callers pass a plain function
id_a(vg_v, vd_v) built from the VS path, the ToB path, or (later)
an F3 oracle, so every triangle edge is measured with the SAME
ruler.

Definitions (each recorded with the result so numbers are
comparable, never bare):
  SS      log-slope fit over the decade band [1e-3, 1e-6] x Ion
          at vd_lin (mV/dec)
  Vt(cc)  constant-current threshold at id_crit (bisection on the
          monotone Id-Vg)
  DIBL    (Vt(vd_lin) - Vt(vd_sat)) / (vd_sat - vd_lin)  [mV/V]
  Ion     Id(vdd, vdd);  Ioff = Id(0, vdd)
  gm_pk   max dId/dVg at vd = vdd (central difference on the grid)
  g_on    Id(vdd, vd_lin)/vd_lin  [S] — the [FC10] 0.7 G0
          comparison quantity (G0 = 4e^2/h, pinned from the
          paper's own RQ = 1/G0 = h/4e^2 statement)

@consumers
  - cntfet.cnt_triangle (F1-vs-F2 edges)
  - cntfet.cnt_calibration (anchor comparisons)
  - cntfet.selftest_cntfet
"""

import math

from cntfet.cnt_constants import H_JS, Q_C

#: G0 as [FC10] defines it: RQ = 1/G0 = h/4e^2 (~6.45 kOhm).
G0_FC10_S = 4.0 * Q_C * Q_C / H_JS

DEFAULT_SPEC = {
    'vdd_v': 0.6,
    'vd_lin_v': 0.05,
    'id_crit_a': 1e-9,   # per-tube constant-current Vt criterion
    'vg_max_v': 1.2,
}


def _vt_constant_current(id_fn, vd_v, spec):
    """Bisection for Vg where Id crosses id_crit (Id-Vg monotone
    increasing for the n-type device). None when the criterion is
    never reached in [0 - 0.5, vg_max] (honest, not extrapolated)."""
    lo, hi = -0.5, spec['vg_max_v']
    crit = spec['id_crit_a']
    if id_fn(lo, vd_v) >= crit or id_fn(hi, vd_v) < crit:
        return None
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        if id_fn(mid, vd_v) < crit:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def _subthreshold_slope(id_fn, vd_v, ion_a, spec):
    """Fit SS over the decade band [1e-6, 1e-3] x Ion: locate the
    band edges by bisection, slope = dVg/dlog10(Id)."""
    points = []
    for frac in (1e-6, 1e-3):
        target = frac * ion_a
        lo, hi = -0.5, spec['vg_max_v']
        if id_fn(lo, vd_v) >= target or id_fn(hi, vd_v) < target:
            return None
        for _ in range(80):
            mid = 0.5 * (lo + hi)
            if id_fn(mid, vd_v) < target:
                lo = mid
            else:
                hi = mid
        points.append((0.5 * (lo + hi), target))
    (vg1, i1), (vg2, i2) = points
    decades = math.log10(i2 / i1)
    if decades <= 0:
        return None
    return (vg2 - vg1) * 1000.0 / decades


def extract_metrics(id_fn, spec=None):
    """The metric family from one engine. Every metric that cannot
    be measured on this device comes back None with a reason in
    'refusals' — never a made-up number."""
    spec = {**DEFAULT_SPEC, **(spec or {})}
    refusals = {}
    vdd = spec['vdd_v']
    vd_lin = spec['vd_lin_v']
    ion = id_fn(vdd, vdd)
    ioff = id_fn(0.0, vdd)
    ss = _subthreshold_slope(id_fn, vd_lin, ion, spec)
    if ss is None:
        refusals['ss_mv_per_dec'] = ('decade band [1e-6,1e-3]xIon '
                                     'not reachable on the Vg '
                                     'window')
    vt_lin = _vt_constant_current(id_fn, vd_lin, spec)
    vt_sat = _vt_constant_current(id_fn, vdd, spec)
    dibl = None
    if vt_lin is None or vt_sat is None:
        refusals['dibl_mv_per_v'] = (f'constant-current Vt at '
                                     f"{spec['id_crit_a']} A not "
                                     'bracketed at both drain '
                                     'biases')
    else:
        dibl = (vt_lin - vt_sat) * 1000.0 / (vdd - vd_lin)
    gm_peak, gm_vg = 0.0, None
    step = 0.02
    vg = 0.0
    while vg <= spec['vg_max_v'] - step:
        gm = (id_fn(vg + step, vdd) - id_fn(vg - step, vdd)) \
            / (2.0 * step)
        if gm > gm_peak:
            gm_peak, gm_vg = gm, vg
        vg += step
    g_on = id_fn(vdd, vd_lin) / vd_lin
    return {
        'spec': spec,
        'ion_a': ion, 'ioff_a': ioff,
        'on_off_ratio': (ion / ioff) if ioff > 0 else None,
        'ss_mv_per_dec': ss,
        'vt_cc_lin_v': vt_lin, 'vt_cc_sat_v': vt_sat,
        'dibl_mv_per_v': dibl,
        'gm_peak_s': gm_peak, 'gm_peak_at_vg_v': gm_vg,
        'g_on_s': g_on,
        'g_on_over_g0': g_on / G0_FC10_S,
        'g0_convention': 'G0 = 4e^2/h ([FC10]: RQ = 1/G0 = '
                         'h/4e^2 ~ 6.5 kOhm)',
        'refusals': refusals,
    }
