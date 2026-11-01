"""
@module pcb.custom.esd_cdm

esd-7 (AI-Notes/plans/DRIVERS_AND_ESD_PLAN.md): THE CHARGED-DEVICE MODEL (CDM) as the series LCR loop the ESD Industry Council reduces a CDM tester to, its
values cited or derived, and checked against JS-002's own verification numbers (pcb.custom.esd_events re-exports these).

JS-002 itself is sold, not public; every number here is from the PUBLIC Industry Council on ESD Target Levels White Paper 2, "A Case for Lowering
Component Level CDM ESD Specifications and Requirements", revision 3.0 (May 2021):
  Table C-II   JS-002-2018 verification modules 6.8 pF (small) and 55 pF (large), +-5 %; calibration levels 125 / 250 / 500 / 750 / 1000 V
  Table C-III  JS-002 at 500 V, 6+ GHz scope: small 7.2 A +-15 %, rise < 250 ps, FWHM 250 - 600 ps; large 12.1 A +-15 %, rise < 350 ps, FWHM 450 - 900 ps
               (1 GHz scope: small 5.1 A, < 350 ps, 325 - 725 ps; large 10.7 A, < 450 ps, 500 - 1000 ps)
  Annex D      the outer loop "reducible to the well-known series LRC" (Eq. 3); I_peak (Eq. 9); R = 25 Ohm "commonly found for equivalent spark
               resistance"; Figure D2: Rp = 1 Ohm, the test head's current detector
The loop: C = the module, R = 25 + 1 Ohm, L DERIVED - solved so Eq. 9 gives Table C-III's 7.2 A on the small module at 500 V (15.9 nH). The large module
is then a CHECK, not a fit: Eq. 9 gives 12.8 A against 12.1 A +-15 %. WP2 calls the peak "the most critical CDM waveform parameter that leads to IC
device failures"; the loop's SHAPE is slower than JS-002's (cdm_check, said on the page): small 278 ps rise / 696 ps FWHM against < 250 ps / 250 - 600 ps,
large 596 ps / 2.1 ns against < 350 ps / 450 - 900 ps - one loop holds the charge longer than the tester's (WP2 Annex D: the real tester adds inner loops
and transmission lines), so it delivers MORE charge than JS-002: on the safe side for a clamp's voltage. No single R, L meets all six numbers (searched
2026-10-31: the large module's FWHM is always above 1.8 ns); a narrower fit (R up to 50 Ohm for the small module's FWHM) loses the large module's peak.

  cdm_peak(level_v, c_f)        Eq. 9 for the loop
  cdm_current(t, level_v, c_f)  the loop's current t seconds after the spark (perfect closure - the spark's own 50 - 200 ps rise is not added)
  cdm_check()                   rows: each module at 500 V against Table C-III's 6+ GHz numbers
"""
import math

WP2 = ('Industry Council on ESD Target Levels, White Paper 2: A Case for Lowering Component Level CDM ESD Specifications and Requirements, rev. 3.0 '
       '(May 2021) - Tables C-II, C-III; Annex D (Eq. 3, Eq. 9, Figure D2)')
R_SPARK = 25.0          # WP2 Annex D: "a value of R, 25 Ohm, that is commonly found for equivalent spark resistance"
R_DETECT = 1.0          # WP2 Figure D2: "Rp = 1 Ohm is the test head current detector"
R_LOOP = R_SPARK + R_DETECT
MODULES = {'small': 6.8e-12, 'large': 55e-12}             # WP2 Table C-II (JS-002-2018)
LEVELS = [125.0, 250.0, 500.0, 750.0, 1000.0]              # WP2 Table C-II calibration levels
TABLE = {'small': {'ip_a': 7.2, 'tol': 0.15, 'rise_max_s': 250e-12, 'fwhm_s': (250e-12, 600e-12)},   # WP2 Table C-III, JS-002 (6+ GHz), 500 V
         'large': {'ip_a': 12.1, 'tol': 0.15, 'rise_max_s': 350e-12, 'fwhm_s': (450e-12, 900e-12)}}


def cdm_peak_rlc(v0, r, l_h, c_f):
    """WP2 Eq. 9: the first peak of a series LCR discharging C from v0 (perfect closure)."""
    d = r / 2.0 * math.sqrt(c_f / l_h)
    if abs(d - 1.0) < 1e-9:
        return 2.0 * v0 / r * math.exp(-1.0)
    if d < 1:
        s = math.sqrt(1 - d * d)
        return 2.0 * v0 / r * d * math.exp(-d / s * math.atan(s / d))
    s = math.sqrt(d * d - 1)
    return 2.0 * v0 / r * d * math.exp(-d / s * math.atanh(s / d))


def _solve_l():
    """L such that Eq. 9 gives Table C-III's small-module peak at 500 V (bisection on log L; the peak falls as L grows)."""
    lo, hi = math.log(1e-11), math.log(1e-6)
    for _ in range(200):
        mid = (lo + hi) / 2.0
        if cdm_peak_rlc(500.0, R_LOOP, math.exp(mid), MODULES['small']) > TABLE['small']['ip_a']:
            lo = mid
        else:
            hi = mid
    return math.exp((lo + hi) / 2.0)


L_LOOP = _solve_l()


def cdm_peak(level_v, c_f):
    return cdm_peak_rlc(level_v, R_LOOP, L_LOOP, c_f)


def cdm_current(t, level_v, c_f):
    """The loop's current t s after closure: V/(w L) e^(-a t) sin(w t) underdamped (a = R / 2L, w^2 = 1/LC - a^2), its sinh / t forms otherwise."""
    if t <= 0:
        return 0.0
    a, w0sq = R_LOOP / (2.0 * L_LOOP), 1.0 / (L_LOOP * c_f)
    if w0sq > a * a:
        w = math.sqrt(w0sq - a * a)
        return level_v / (w * L_LOOP) * math.exp(-a * t) * math.sin(w * t)
    if w0sq < a * a:
        g = math.sqrt(a * a - w0sq)
        return level_v / (g * L_LOOP) * math.exp(-a * t) * math.sinh(g * t)
    return level_v / L_LOOP * t * math.exp(-a * t)


def _shape(c_f, level_v=500.0):
    ts = [k * 0.5e-12 for k in range(1, 8001)]
    v = [cdm_current(t, level_v, c_f) for t in ts]
    k = max(range(len(v)), key=lambda i: v[i])
    ip = v[k]
    t10 = next(t for t, x in zip(ts, v) if x >= 0.1 * ip)
    t90 = next(t for t, x in zip(ts, v) if x >= 0.9 * ip)
    up = next(t for t, x in zip(ts, v) if x >= 0.5 * ip)
    down = next(t for t, x in zip(ts[k:], v[k:]) if x < 0.5 * ip)
    return ip, t90 - t10, down - up


def cdm_check():
    """Each JS-002 verification module at 500 V through the loop, against WP2 Table C-III (JS-002, 6+ GHz scope)."""
    rows = []
    for mod, c_f in MODULES.items():
        ip, rise, fwhm = _shape(c_f)
        t = TABLE[mod]
        lo, hi = t['ip_a'] * (1 - t['tol']), t['ip_a'] * (1 + t['tol'])
        rows.append({'module': mod, 'c_pf': c_f * 1e12, 'peak_a': ip, 'eq9_peak_a': cdm_peak(500.0, c_f), 'table_peak_a': t['ip_a'], 'peak_ok': lo <= ip <= hi,
                     'rise_s': rise, 'rise_max_s': t['rise_max_s'], 'rise_ok': rise < t['rise_max_s'], 'fwhm_s': fwhm, 'fwhm_range_s': t['fwhm_s'],
                     'fwhm_ok': t['fwhm_s'][0] <= fwhm <= t['fwhm_s'][1], 'role': 'fitted (L solved from it)' if mod == 'small' else 'a check'})
    return rows
