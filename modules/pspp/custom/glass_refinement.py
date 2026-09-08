"""
@module pspp.custom.glass_refinement

mtt-2 glass core (MATERIALS_TECH_TREE_PLAN: "glass refinement
windows"): the REFINEMENT half of silicate glass as DATA + one exact
fit. No new classes — DigitizedDataset + ThresholdReactionWindow rows
carry everything (the CMC/sol-gel swap-the-library precedent).

The honest split, mirroring the sintering engine:
- The VISCOSITY FIXED POINTS (working / Littleton softening /
  annealing / strain / practical melting) are DEFINITIONS — their
  log10 viscosities are exact by convention. The TEMPERATURES at
  which one glass hits them are per-composition DATA
  (soda-lime float values seeded, literature-approximate, cited).
- The VFT curve log10 η = A + B/(T − T0) is fitted EXACTLY through 3
  cited fixed points (closed-form solve, zero free parameters) and
  self-checks against the remaining points as reported residuals.
  Reads outside the fitted temperature span REFUSE (UNSUPPORTED
  extrapolation — below strain the fit is unreliable, above practical
  melting it is unmeasured).
- Process windows (fining / forming / annealing gates + the
  devitrification-risk zone) are ThresholdReactionWindow rows on
  log10ViscosityPaS (temperature for devit) — data, not code.
- Devitrification KINETICS refuse: the TTT/growth-rate curve is a
  points-empty provisional dataset whose refusal names the ask.

@consumers
  - polariServer.defClassList seeding (GLASS_DIGITIZED_DATASETS +
    GLASS_THRESHOLD_WINDOWS concatenate into the pspp seeds)
  - pspp.custom.viscous_sintering (η(T) for the viscous work integral)
  - pspp.pspp_api (GET /api/pspp/glass/refinement)
  - pspp.glass_refinement_selftest
"""

import json
import math

C_TO_K = 273.15

_GLASS_PROVENANCE = ('mtt-2 glass refinement seed 2026-07-27 — fixed-'
                     'point log-viscosities are definitions; soda-lime '
                     'temperatures literature-approximate (Shelby 2005)')

_SHELBY = ('Shelby, Introduction to Glass Science and Technology, '
           '2nd ed. (RSC 2005) — viscosity reference points; soda-lime '
           'float temperatures approximate')

#: The standard viscosity reference points. log10 η (Pa·s) values are
#: DEFINITIONS (10^3 Pa·s working, 10^6.6 Littleton softening, 10^12
#: annealing, 10^13.5 strain; practical melting/fining ~10^1). The
#: temperatures are soda-lime float glass, literature-approximate.
REFERENCE_POINTS = [
    {'name': 'practical-melting', 'log10ViscosityPaS': 1.0,
     'temperatureC': 1450.0,
     'what': 'fluid enough to melt batch + let fining bubbles rise'},
    {'name': 'working-point', 'log10ViscosityPaS': 3.0,
     'temperatureC': 1025.0,
     'what': 'delivered to forming — gobs/gathers hold shape while '
             'still flowing'},
    {'name': 'littleton-softening', 'log10ViscosityPaS': 6.6,
     'temperatureC': 725.0,
     'what': 'deforms under its own weight (Littleton fiber test) — '
             'the bottom of the forming range'},
    {'name': 'annealing-point', 'log10ViscosityPaS': 12.0,
     'temperatureC': 548.0,
     'what': 'internal stress relaxes in ~minutes — hold here to '
             'anneal'},
    {'name': 'strain-point', 'log10ViscosityPaS': 13.5,
     'temperatureC': 508.0,
     'what': 'stress relaxes only over hours — below this the glass '
             'is effectively rigid'},
]

#: Soda-lime devitrification landmarks (temperature window bounds) —
#: literature-approximate; the KINETICS inside the window refuse.
GLASS_TRANSITION_C = 560.0
LIQUIDUS_C = 1040.0

GLASS_DIGITIZED_DATASETS = [
    {
        'name': 'soda-lime-viscosity-reference-points',
        'source_reference': _SHELBY,
        'status': 'ready',
        'independent_variables_json': '["temperatureC"]',
        'dependent_variables_json': '["log10ViscosityPaS"]',
        'units_json': json.dumps({
            'temperatureC': 'C',
            'log10ViscosityPaS': 'log10(Pa*s)'}),
        'source_conditions_json': json.dumps({
            'system': 'soda-lime float glass (~74 SiO2 / 13 Na2O / '
                      '10 CaO wt%, nominal)',
            'note': 'log-viscosity values of the fixed points are '
                    'DEFINITIONS; the temperatures are the '
                    'approximate composition-specific data'}),
        'interpolation_policy': 'linear',
        'extrapolation_policy': 'UNSUPPORTED',
        'validity_domain_json': json.dumps(
            {'temperatureC': [508.0, 1450.0]}),
        'digitization_method': 'textbook fixed-point table transcribed '
                               '(approximate, no figure read needed)',
        'points_json': json.dumps([
            {'temperatureC': p['temperatureC'],
             'log10ViscosityPaS': p['log10ViscosityPaS']}
            for p in REFERENCE_POINTS]),
        'qualitative_shape':
            'Viscosity falls ~12.5 decades from the strain point to '
            'practical melting, strongly curved in 1/T — VFT, not '
            'Arrhenius. Between fixed points read via the exact VFT '
            'fit, not linear interpolation.',
        'notes': 'The VFT fit (glass_refinement.fit_vft) passes '
                 'EXACTLY through strain/softening/melting and '
                 'self-checks against working + annealing as reported '
                 'residuals. DATA ASK (upgrade, not unlock): replace '
                 'approximate temperatures with a measured viscosity '
                 'curve for an actual local glass batch.',
    },
    {
        'name': 'soda-lime-devitrification-ttt',
        'source_reference': 'devitrite/wollastonite growth-rate or '
                            'TTT curve for soda-lime — specific '
                            'figure PENDING digitization',
        'status': 'provisional-low-confidence',
        'independent_variables_json': '["temperatureC"]',
        'dependent_variables_json': '["crystalGrowthRateUmPerMin"]',
        'units_json': json.dumps({
            'temperatureC': 'C',
            'crystalGrowthRateUmPerMin': 'um/min'}),
        'source_conditions_json': json.dumps({
            'system': 'soda-lime glass held between glass transition '
                      'and liquidus',
            'note': 'growth rate peaks somewhere inside the window; '
                    'asserting where needs the curve'}),
        'interpolation_policy': 'linear',
        'extrapolation_policy': 'UNSUPPORTED',
        'validity_domain_json': '{}',
        'digitization_method': 'NOT digitized — awaiting a straight-on '
                               'figure read',
        'points_json': '[]',
        'qualitative_shape':
            'Zero at the glass transition (too stiff to rearrange), '
            'zero at the liquidus (crystals melt), a growth-rate '
            'maximum between — the classic nose. Time spent near the '
            'nose is what devitrifies ware.',
        'notes': 'DATA ASK: digitize a soda-lime crystal-growth-rate '
                 'vs temperature (or TTT) curve — it turns the '
                 'devitrification-risk window from a qualitative zone '
                 'into hold-time budgets. Until then devit kinetics '
                 'refuse.',
    },
    {
        'name': 'glass-frit-viscous-sintering-master-curve',
        'source_reference': 'glass-frit densification vs reduced '
                            'viscous work — specific run PENDING '
                            'digitization',
        'status': 'provisional-low-confidence',
        'independent_variables_json': '["log10Lambda"]',
        'dependent_variables_json': '["relativeDensity"]',
        'units_json': json.dumps({
            'log10Lambda': 'log10(dimensionless)',
            'relativeDensity': 'fraction of theoretical'}),
        'source_conditions_json': json.dumps({
            'system': 'glass frit / powder compact, viscous-flow '
                      'sintering',
            'note': 'Λ = ∫ γ/(η(T)·r) dt collapses runs the way Θ '
                    'does for solid-state sintering; the ρ(Λ) curve '
                    'is the calibration'}),
        'interpolation_policy': 'linear',
        'extrapolation_policy': 'UNSUPPORTED',
        'validity_domain_json': '{}',
        'digitization_method': 'NOT digitized — awaiting a straight-on '
                               'figure read',
        'points_json': '[]',
        'qualitative_shape':
            'Sigmoidal: green density through the Frenkel neck-growth '
            'stage, steep viscous densification, saturation near full '
            'density as pores close. One curve per frit family when '
            'plotted against log Λ.',
        'notes': 'DATA ASK: digitize a glass-frit relative-density vs '
                 'log Λ run (dilatometry of a frit compact through a '
                 'known schedule + the same glass\'s viscosity curve). '
                 'Until then the viscous engine computes Λ and the '
                 'Frenkel early stage, and refuses mid/final-stage ρ.',
    },
]

for _row in GLASS_DIGITIZED_DATASETS:
    _row.setdefault('provenance_id', _GLASS_PROVENANCE)


GLASS_THRESHOLD_WINDOWS = [
    {
        'name': 'silicate-glass:fining-gate',
        'material_family': 'silicate-glass',
        'descriptor': 'log10ViscosityPaS',
        'window_role': 'condition-gate',
        'bands_json': json.dumps([
            {'lo': None, 'hi': 2.0, 'grade': 'ideal',
             'note': 'Fluid enough that seed/bubble rise and batch '
                     'homogenization proceed — fining is OPEN.'},
            {'lo': 2.0, 'hi': None, 'grade': 'failure',
             'note': 'Too stiff for bubbles to escape in practical '
                     'time — fining is CLOSED; expect seeds in the '
                     'ware.'},
        ]),
        'behavior_note': 'Melting/fining wants ~10 Pa·s or less.',
        'source_reference': _SHELBY,
    },
    {
        'name': 'silicate-glass:forming-gate',
        'material_family': 'silicate-glass',
        'descriptor': 'log10ViscosityPaS',
        'window_role': 'condition-gate',
        'bands_json': json.dumps([
            {'lo': None, 'hi': 3.0, 'grade': 'failure',
             'note': 'Runnier than the working point — the gob flows '
                     'off the tool before it can be shaped.'},
            {'lo': 3.0, 'hi': 6.6, 'grade': 'ideal',
             'note': 'The working RANGE (working point down to '
                     'Littleton softening) — blowing, pressing, '
                     'drawing all live here.'},
            {'lo': 6.6, 'hi': None, 'grade': 'failure',
             'note': 'Below softening the glass no longer flows '
                     'under forming forces — forming is CLOSED '
                     '(reheat to continue).'},
        ]),
        'behavior_note': 'Forming lives between 10^3 and 10^6.6 Pa·s '
                         '— the "long" vs "short" character of a '
                         'glass is how fast it crosses this band.',
        'source_reference': _SHELBY,
    },
    {
        'name': 'silicate-glass:annealing-gate',
        'material_family': 'silicate-glass',
        'descriptor': 'log10ViscosityPaS',
        'window_role': 'condition-gate',
        'bands_json': json.dumps([
            {'lo': None, 'hi': 12.0, 'grade': 'failure',
             'note': 'Above the annealing point the ware still '
                     'deforms — it slumps while you try to anneal.'},
            {'lo': 12.0, 'hi': 13.5, 'grade': 'ideal',
             'note': 'The annealing window (annealing point down to '
                     'strain point): stress relaxes in minutes-to-'
                     'hours with no shape change.'},
            {'lo': 13.5, 'hi': None, 'grade': 'marginal',
             'note': 'Below the strain point relaxation takes hours+ '
                     '— residual stress is effectively frozen in; '
                     'cooling rate through here sets the permanent '
                     'stress.'},
        ]),
        'behavior_note': 'Anneal between the annealing and strain '
                         'points; the schedule through this band '
                         'decides residual stress.',
        'source_reference': _SHELBY,
    },
    {
        'name': 'soda-lime-glass:devitrification-risk',
        'material_family': 'silicate-glass',
        'descriptor': 'temperatureC',
        'window_role': 'condition-gate',
        'bands_json': json.dumps([
            {'lo': None, 'hi': GLASS_TRANSITION_C, 'grade': 'ideal',
             'note': 'Below the glass transition the network is '
                     'frozen — no crystallization on any practical '
                     'timescale.'},
            {'lo': GLASS_TRANSITION_C, 'hi': LIQUIDUS_C,
             'grade': 'marginal',
             'note': 'Between glass transition and liquidus crystals '
                     'CAN nucleate and grow (devitrite etc.) — time '
                     'here is devitrification risk. HOW MUCH time is '
                     'safe needs the TTT dataset (refuses until '
                     'digitized).'},
            {'lo': LIQUIDUS_C, 'hi': None, 'grade': 'ideal',
             'note': 'Above the liquidus crystals redissolve — hold '
                     'here to erase devit before forming.'},
        ]),
        'behavior_note': 'The devit-risk zone is the price of the '
                         'forming range sitting inside it — schedules '
                         'minimize time between softening and '
                         'liquidus. Kinetics = the TTT data ask.',
        'source_reference': 'window bounds literature-approximate '
                            '(soda-lime Tg ~560C, liquidus ~1040C); '
                            + _SHELBY,
        'notes': 'Bounds are soda-lime; the window does not transfer '
                 'to other glass families (I5).',
    },
]

for _row in GLASS_THRESHOLD_WINDOWS:
    _row.setdefault('provenance_id', _GLASS_PROVENANCE)
    _row.setdefault('notes', '')


def _points_list(points):
    out = []
    for p in points or []:
        try:
            out.append((float(p['temperatureC']),
                        float(p['log10ViscosityPaS'])))
        except (KeyError, TypeError, ValueError):
            return None
    return out


def fit_vft(points=None):
    """Exact VFT fit log10 η = A + B/(T_K − T0_K) through 3 anchor
    points (coldest, median, hottest), residual-checked against every
    other point. ZERO free parameters — the closed-form solve either
    passes through the cited points or refuses. points:
    [{'temperatureC', 'log10ViscosityPaS'}, ...] (>=3); defaults to
    the seeded soda-lime reference points."""
    pts = _points_list(points if points is not None
                       else REFERENCE_POINTS)
    if pts is None:
        return {'ok': False,
                'refusal': 'malformed viscosity points',
                'suggestion': 'each point needs numeric temperatureC '
                              '+ log10ViscosityPaS'}
    pts = sorted(set(pts))
    if len(pts) < 3:
        return {'ok': False,
                'refusal': f'{len(pts)} distinct viscosity points — '
                           'the VFT solve needs 3',
                'suggestion': 'supply at least 3 cited (T, log10 η) '
                              'fixed points'}
    anchors = [pts[0], pts[len(pts) // 2], pts[-1]]
    (t1, l1), (t2, l2), (t3, l3) = [
        (t + C_TO_K, l) for t, l in anchors]
    if l1 == l3 or l1 == l2:
        return {'ok': False,
                'refusal': 'degenerate anchor points (equal '
                           'viscosities)',
                'suggestion': 'points must span distinct viscosities'}
    r = (l1 - l2) / (l1 - l3)
    denom = r * (t3 - t1) - (t2 - t1)
    if abs(denom) < 1e-12:
        return {'ok': False,
                'refusal': 'VFT solve is singular for these points',
                'suggestion': 'check the point spread'}
    t0 = (r * (t3 - t1) * t2 - (t2 - t1) * t3) / denom
    if t0 >= t1:
        return {'ok': False,
                'refusal': f'solved T0 ({t0 - C_TO_K:.0f}C) is not '
                           'below the coldest point — not a physical '
                           'VFT branch',
                'suggestion': 'check the cited points'}
    b = (l1 - l2) / (1.0 / (t1 - t0) - 1.0 / (t2 - t0))
    a = l1 - b / (t1 - t0)
    if b <= 0:
        return {'ok': False,
                'refusal': f'solved B ({b:.0f} K) is not positive — '
                           'viscosity would rise with temperature',
                'suggestion': 'check the cited points'}
    residuals = []
    for t_c, l in pts:
        pred = a + b / (t_c + C_TO_K - t0)
        residuals.append({'temperatureC': t_c, 'cited': l,
                          'predicted': round(pred, 3),
                          'residual': round(pred - l, 3)})
    return {
        'ok': True,
        'A': a, 'B_K': b, 'T0_C': t0 - C_TO_K,
        'anchorsC': [t for t, _ in anchors],
        'validTempRangeC': [pts[0][0], pts[-1][0]],
        'residuals': residuals,
        'assumptions': [
            'VFT solved EXACTLY through the 3 anchor points — no '
            'fitted/invented parameters; other points are honesty '
            'residuals',
            'valid only inside the span of the cited points — reads '
            'outside refuse',
        ],
    }


def viscosity_at(temp_c, vft=None, points=None):
    """log10 η (Pa·s) at temp_c through the VFT fit. REFUSES outside
    the fitted temperature span (UNSUPPORTED extrapolation). vft: a
    fit_vft result to reuse; else fitted from points/seeds here."""
    fit = vft if vft is not None else fit_vft(points)
    if not fit.get('ok'):
        return fit
    try:
        t = float(temp_c)
    except (TypeError, ValueError):
        return {'ok': False,
                'refusal': f'temperature {temp_c!r} is not a number',
                'suggestion': 'Celsius'}
    lo, hi = fit['validTempRangeC']
    if not lo <= t <= hi:
        return {'ok': False,
                'refusal': f'{t}C is outside the fitted span '
                           f'[{lo}, {hi}]C — UNSUPPORTED '
                           'extrapolation',
                'suggestion': 'below the strain point the fit is '
                              'unreliable (glass is rigid); above '
                              'practical melting it is unmeasured — '
                              'cite points that cover your range'}
    log_eta = fit['A'] + fit['B_K'] / (t - fit['T0_C'])
    return {'ok': True,
            'temperatureC': t,
            'log10ViscosityPaS': log_eta,
            'viscosityPaS': 10.0 ** log_eta,
            'fit': {'A': fit['A'], 'B_K': fit['B_K'],
                    'T0_C': fit['T0_C']}}


def process_map(temp_c, vft=None, windows=None):
    """What glasswork is admissible at temp_c: viscosity through the
    VFT fit + every refinement gate graded at that viscosity + the
    devitrification-risk read. windows: banded rows/dicts (defaults to
    the seeds)."""
    from pspp.threshold_windows_basis import (
        banded_window_dict, grade_value_banded,
    )
    visc = viscosity_at(temp_c, vft=vft)
    rows = [banded_window_dict(w)
            for w in (windows if windows is not None
                      else GLASS_THRESHOLD_WINDOWS)]
    gates = []
    for w in rows:
        if w['descriptor'] == 'log10ViscosityPaS':
            if not visc.get('ok'):
                gates.append({'window': w['name'], 'ok': False,
                              'refusal': visc['refusal']})
                continue
            verdict = grade_value_banded(
                w, visc['log10ViscosityPaS'])
        elif w['descriptor'] == 'temperatureC':
            verdict = grade_value_banded(w, float(temp_c))
        else:
            continue
        verdict['window'] = w['name']
        verdict['open'] = (verdict.get('grade')
                           not in ('failure', None))
        gates.append(verdict)
    return {
        'ok': True,
        'temperatureC': float(temp_c),
        'viscosity': visc,
        'gates': gates,
        'note': 'gates grade the seeded refinement windows at this '
                'temperature — devit TIME budgets stay refused until '
                'the TTT dataset is digitized',
    }


def refinement_report(points=None, windows=None):
    """The whole glass-refinement surface in one payload: reference
    points, the exact VFT fit + residuals, the process windows, and
    the devit data ask."""
    from pspp.threshold_windows_basis import banded_window_dict
    fit = fit_vft(points)
    return {
        'ok': True,
        'referencePoints': list(points if points is not None
                                else REFERENCE_POINTS),
        'vftFit': fit,
        'windows': [banded_window_dict(w)
                    for w in (windows if windows is not None
                              else GLASS_THRESHOLD_WINDOWS)],
        'devitrification': {
            'zoneC': [GLASS_TRANSITION_C, LIQUIDUS_C],
            'kinetics': 'REFUSED — soda-lime-devitrification-ttt is '
                        'provisional; digitize it to turn the risk '
                        'zone into hold-time budgets',
        },
        'note': 'fixed-point log-viscosities are definitions; '
                'temperatures are literature-approximate soda-lime '
                'data — swap the points row to model another glass',
    }
