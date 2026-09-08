"""@module cntfet.objects.cnt_regimes._shared — what the cnt_regimes row classes share (constants, seeds, helpers); split from cnt_regimes_basis.py (sap-2c)."""
from cntfet.cnt_states_basis import (
    STATE_KNOBS, evaluate_criteria, frame_at,
)
import json
import math

FIDELITY = ('F1 (VS_MINIMAL compact model): regimes are the local '
            'exponent m = dlnId/dlnVov and the Fsat/Vdsat/DIBL '
            'quantities of the model\'s own equations at the '
            'device\'s derived parameters; the model saturates by '
            'velocity, so the square-law band (m ≈ 2) is a '
            'reference it cannot reach — stated, not hidden; '
            'F3/NEGF re-grading is row-backed work')
REGIME_KNOBS = {
    **STATE_KNOBS,
    # the long-channel square-law exponent band (Id ∝ Vov^m)
    'm_sq_lo': 1.7,
    'm_sq_hi': 2.3,
    # the velocity-saturated / ballistic band (Id ∝ Vov)
    'm_vs_lo': 0.8,
    'm_vs_hi': 1.2,
    # Fsat above which the knee is over, so residual output slope
    # in saturation is attributed to DIBL rather than the soft Fsat
    'fsat_flat': 0.95,
    # gds/gm above which saturation counts as DIBL-tilted (a
    # Vt-shift of DIBL·dVds moves Id by gm·DIBL·dVds ⇒ gds/gm ≈ DIBL)
    'gds_over_gm_max': 0.05,
    # half-step (V) of the central differences for m, gm, gds
    'diff_step_v': 0.005,
    # default grid for the (Vd, Vg) regime map
    'grid_max_v': 0.6,
    'grid_step_v': 0.03,
}
def _c(lhs, op, rhs, why):
    return {'lhs': lhs, 'op': op, 'rhs': rhs, 'why': why}
_ON = _c('vgs', '>=', 'vt_on', 'on: Vgs ≥ Vt + Vov_min (the fi-0 '
                                '"on" boundary, Vov_min = vov_decades·SS)')
_SAT = _c('vds', '>=', 'vdsat', 'saturated: Vds at or above the VS '
                                 'Vdsat knee (Fsat → 1)')
_M_OK = _c('m_ok', '==', 1, 'the exponent m is defined (Vov > 0 and '
                             'Id > 0 on both sides of the difference)')
SEED_FET_REGIMES = [
    {
        'name': 'subthreshold-exponential',
        'display_name': 'Subthreshold (exponential)',
        'order': 0,
        'description': 'Vgs below the model threshold Vt(Vds): the '
                       'current is the thermionic tail over the '
                       'barrier and grows one decade per SS = '
                       'n_ss·φt·ln10 of gate voltage — an '
                       'EXPONENTIAL law, so no power-law exponent '
                       'applies (m is undefined here by design). '
                       '[VS1] eq.(8) sets Vt; [KHA09] the Ff '
                       'blend.',
        'criteria_json': json.dumps([
            _c('vgs', '<', 'vt', 'below Vt(Vds) = vt0 - dVt - '
                                 'DIBL·Vds'),
        ]),
        'governing_equation': 'Id ∝ exp((Vgs - Vt)/(n_ss φt)),  '
                              'SS = n_ss φt ln10',
    },
    {
        'name': 'near-threshold',
        'display_name': 'Near threshold (Ff blend)',
        'order': 1,
        'description': 'Vt ≤ Vgs < Vt + Vov_min: neither the '
                       'exponential nor a power law holds cleanly — '
                       'the VS Ff function blends the two ([KHA09] '
                       'via [VS1]) while Id climbs its last '
                       'vov_decades decades. The fi-0 "transition" '
                       'band, carried here so the map has no hole.',
        'criteria_json': json.dumps([
            _c('vgs', '>=', 'vt', 'at or above Vt(Vds)'),
            _c('vgs', '<', 'vt_on', 'still below Vt + Vov_min'),
        ]),
        'governing_equation': 'Qxo = Cinv n_ss φt ln(1 + exp((Vgsi - '
                              '(Vt - αφt Ff))/(n_ss φt)))',
    },
    {
        'name': 'linear-triode',
        'display_name': 'Linear / triode (Id ∝ Vds)',
        'order': 2,
        'description': 'On, and Vds below the saturation voltage: '
                       'Fsat ≈ Vds/Vdsat so Id ≈ Qxo·v_xo·Vds/Vdsat '
                       '= Qxo·μ·Vds/Lg — the channel is a gate-'
                       'controlled RESISTOR (g_on = Id/Vds). This is '
                       'the leg the on-conductance term ([FC10] '
                       'g_on/G0) is read from.',
        'criteria_json': json.dumps([
            _ON,
            _c('vds', '<', 'vdsat', 'below the Vdsat knee: Fsat ≈ '
                                    'Vds/Vdsat'),
        ]),
        'governing_equation': 'Id ≈ Qxo v_xo (Vds/Vdsat) = Qxo μ Vds/Lg',
    },
    {
        'name': 'dibl-tilted-saturation',
        'display_name': 'Saturation, DIBL-tilted (gds ≈ gm·DIBL)',
        'order': 3,
        'description': 'On, past the Fsat knee (Fsat ≥ fsat_flat so '
                       'the residual output slope is NOT the soft '
                       'knee), yet gds/gm exceeds the knob: the '
                       'drain still lowers the barrier, Vt = vt0 - '
                       'dVt - DIBL·Vds ([VS1] eq.(8)), so Id keeps '
                       'rising at gm·DIBL per volt of Vds — a '
                       'short-channel gate-control loss that costs '
                       'intrinsic gain (gm/gds) and Ioff. Takes '
                       'precedence over the exponent regimes '
                       'because it is a defect of saturation, '
                       'whatever the Vov law.',
        'criteria_json': json.dumps([
            _ON, _SAT,
            _c('fsat', '>=', 'fsat_flat', 'the Fsat knee is over — '
                                          'slope left is DIBL'),
            _c('gds_over_gm', '>', 'gds_over_gm_max',
               'output conductance relative to gm above the knob '
               '(gds/gm ≈ DIBL in a velocity-saturated device)'),
        ]),
        'governing_equation': 'Vt = vt0 - dVt - DIBL·Vds  ⇒  '
                              'gds ≈ gm·DIBL  (Fsat → 1)',
    },
    {
        'name': 'velocity-saturated',
        'display_name': 'Velocity-saturated (Id ∝ Vov, m ≈ 1)',
        'order': 4,
        'description': 'On and saturated with the local exponent m '
                       '= dlnId/dlnVov inside the velocity-saturated '
                       'band [m_vs_lo, m_vs_hi]: carriers leave the '
                       'virtual source at v_xo, Id = Qxo·v_xo with '
                       'Qxo ∝ Vov — the ballistic/VS limit ([VS1] '
                       'eq.(9)-(10), [KHA09]; the injection picture '
                       'of [RAH03] and the mean-free-path '
                       'transmission of [LUN97]). A short-channel '
                       'signature: gm saturates at Cinv·v_xo '
                       'instead of growing with Vov.',
        'criteria_json': json.dumps([
            _ON, _SAT, _M_OK,
            _c('vov_exponent', '>=', 'm_vs_lo', 'm at or above the '
                                                'velocity-saturated '
                                                'band floor'),
            _c('vov_exponent', '<=', 'm_vs_hi', 'm at or below the '
                                                'band ceiling'),
        ]),
        'governing_equation': 'Id = Qxo v_xo,  Qxo ≈ Cinv (Vgsi - Vt) '
                              '⇒ m = dlnId/dlnVov ≈ 1',
    },
    {
        'name': 'square-law',
        'display_name': 'Square law (Id ∝ Vov², m ≈ 2)',
        'order': 5,
        'description': 'On and saturated with m inside the square-'
                       'law band [m_sq_lo, m_sq_hi]: the LONG-CHANNEL '
                       'pinch-off law Id = (μ Cinv/2Lg)(Vgs - Vt)², '
                       'where Vdsat = Vgs - Vt grows with the '
                       'overdrive. The VS model saturates by velocity '
                       '(Vdsat independent of Vov), so this band is '
                       'the textbook REFERENCE the reader compares '
                       'the device against; the F1 model cannot '
                       'land here on physics grounds, and a point '
                       'that does is a softplus/Ff corner, not '
                       'pinch-off — stated in the verdict.',
        'criteria_json': json.dumps([
            _ON, _SAT, _M_OK,
            _c('vov_exponent', '>=', 'm_sq_lo', 'm at or above the '
                                                'square-law band floor'),
            _c('vov_exponent', '<=', 'm_sq_hi', 'm at or below the '
                                                'band ceiling'),
        ]),
        'governing_equation': 'Id = (μ Cinv / 2Lg)(Vgs - Vt)²  '
                              '(Vds ≥ Vgs - Vt) ⇒ m ≈ 2',
    },
    {
        'name': 'transition-exponent',
        'display_name': 'Exponent crossover (1 < m < 2)',
        'order': 6,
        'description': 'On and saturated with m between the two '
                       'bands: neither purely velocity-limited nor '
                       'the long-channel square law — the crossover '
                       'where the mobility leg (μ/Lg) and the '
                       'injection leg (v_xo) contribute comparably '
                       '(the [VS1] Vdsat = v_xo Lg/μ balance).',
        'criteria_json': json.dumps([
            _ON, _SAT, _M_OK,
            _c('vov_exponent', '>', 'm_vs_hi', 'above the velocity-'
                                               'saturated band'),
            _c('vov_exponent', '<', 'm_sq_lo', 'below the square-law '
                                               'band'),
        ]),
        'governing_equation': 'Id ∝ Vov^m,  m_vs_hi < m < m_sq_lo',
    },
    {
        'name': 'contact-limited-sublinear',
        'display_name': 'Contact-limited (m < 1, Rc eats Vov)',
        'order': 7,
        'description': 'On and saturated with m BELOW the velocity-'
                       'saturated band: the drive grows sub-linearly '
                       'in the overdrive because the series contact '
                       'resistance drops Id·Rs off the gate and '
                       'Id·(Rs+Rd) off the drain (D9: Rc first-'
                       'class, never folded into μ), so each extra '
                       'volt of Vgs buys less internal Vov. The '
                       '[FC10] Rc-vs-Lg scaling is the lever.',
        'criteria_json': json.dumps([
            _ON, _SAT, _M_OK,
            _c('vov_exponent', '<', 'm_vs_lo', 'm below the velocity-'
                                               'saturated band floor'),
        ]),
        'governing_equation': 'Vgsi = Vgs - Id Rs,  Vdsi = Vds - '
                              'Id (Rs + Rd)  ⇒  m < 1',
    },
    {
        'name': 'super-square',
        'display_name': 'Above square law (m > m_sq_hi)',
        'order': 8,
        'description': 'On and saturated with m above the square-law '
                       'band: steeper than any drift law — in the F1 '
                       'model this can only be the softplus corner '
                       'just above Vt + Vov_min where Qxo is still '
                       'exponential-ish. Carried so every saturated '
                       'point has a regime and the map has no hole.',
        'criteria_json': json.dumps([
            _ON, _SAT, _M_OK,
            _c('vov_exponent', '>', 'm_sq_hi', 'm above the square-law '
                                               'band ceiling'),
        ]),
        'governing_equation': 'Id ∝ Vov^m,  m > m_sq_hi',
    },
    {
        'name': 'exponent-undefined',
        'display_name': 'Saturated, exponent undefined',
        'order': 9,
        'description': 'On and saturated but m could not be formed '
                       '(Vov ≤ 0 or Id ≤ 0 on a side of the '
                       'difference — e.g. Rc pushed Vgsi below Vt '
                       'although the terminal Vgs is past Vt + '
                       'Vov_min). A refusal as a row, not a guess.',
        'criteria_json': json.dumps([
            _ON, _SAT,
            _c('m_ok', '==', 0, 'the exponent could not be formed'),
        ]),
        'governing_equation': '(m undefined)',
    },
]
def vov_exponent(p, vgs_v, vds_v, knobs=None):
    """Central-difference log-slope m = dlnId/dlnVov at fixed Vd,
    Vov = Vgsi - Vt(Vds). Returns (m, reason) — m is None with the
    reason when Vov ≤ 0 or Id ≤ 0 on either side."""
    k = {**REGIME_KNOBS, **(knobs or {})}
    h = k['diff_step_v']
    f0 = frame_at(p, vgs_v, vds_v, knobs)
    if f0['vov'] <= 0.0:
        return None, f'Vov = {f0["vov"]:.4f} V ≤ 0 (no overdrive)'
    fa = frame_at(p, vgs_v - h, vds_v, knobs)
    fb = frame_at(p, vgs_v + h, vds_v, knobs)
    if fa['vov'] <= 0.0 or fb['vov'] <= 0.0:
        return None, 'Vov ≤ 0 on a side of the central difference'
    if fa['id_a'] <= 0.0 or fb['id_a'] <= 0.0:
        return None, 'Id ≤ 0 on a side of the central difference'
    dln_vov = math.log(fb['vov']) - math.log(fa['vov'])
    if dln_vov == 0.0:
        return None, 'Vov did not change across the difference'
    return ((math.log(fb['id_a']) - math.log(fa['id_a'])) / dln_vov,
            None)
def _id(p, vg, vd, knobs):
    return frame_at(p, vg, vd, knobs)['id_a']
def regime_frame(p, vgs_v, vds_v, knobs=None):
    """cnt_states.frame_at PLUS the regime quantities: vov_exponent
    (+ m_ok flag and refusal reason), gm, gds, gds_over_gm, fsat
    (already in frame_at) and the band knobs as frame keys so the
    criteria can cite them by name."""
    k = {**REGIME_KNOBS, **(knobs or {})}
    f = frame_at(p, vgs_v, vds_v, k)
    h = k['diff_step_v']
    gm = (_id(p, vgs_v + h, vds_v, k) - _id(p, vgs_v - h, vds_v, k)) / (2 * h)
    vd_lo = max(vds_v - h, 0.0)
    gds = ((_id(p, vgs_v, vds_v + h, k) - _id(p, vgs_v, vd_lo, k))
           / (vds_v + h - vd_lo))
    m, reason = vov_exponent(p, vgs_v, vds_v, k)
    f.update({
        'vov_exponent': m if m is not None else float('nan'),
        'm_ok': 1 if m is not None else 0,
        'm_refusal': reason,
        'gm': gm, 'gds': gds,
        'gds_over_gm': gds / gm if gm > 0 else float('inf'),
        'm_sq_lo': k['m_sq_lo'], 'm_sq_hi': k['m_sq_hi'],
        'm_vs_lo': k['m_vs_lo'], 'm_vs_hi': k['m_vs_hi'],
        'fsat_flat': k['fsat_flat'],
        'gds_over_gm_max': k['gds_over_gm_max'],
        'knobs': k,
    })
    return f
def _regime_defs(manager=None):
    """Seeded regime rows (manager rows win when present so edits on
    the page change the evaluation with zero code)."""
    rows = []
    if manager is not None:
        table = getattr(manager, 'objectTables', {}).get(
            'FETRegime') or {}
        for row in (table.values() if isinstance(table, dict)
                    else table):
            rows.append({
                'name': row.name, 'display_name': row.display_name,
                'order': row.order, 'description': row.description,
                'criteria_json': row.criteria_json,
                'governing_equation': row.governing_equation})
    if not rows:
        rows = [dict(s) for s in SEED_FET_REGIMES]
    return sorted(rows, key=lambda r: (r['order'], r['name']))
def classify_regime(frame, knobs=None, manager=None):
    """(regime name or None, every row's evaluation with numbers) —
    first row by order whose criteria ALL pass."""
    evaluations = []
    chosen = None
    for s in _regime_defs(manager):
        ev = evaluate_criteria(json.loads(s['criteria_json']), frame)
        passed = all(e['passed'] for e in ev) and bool(ev)
        evaluations.append({'regime': s['name'],
                            'display_name': s['display_name'],
                            'passed': passed, 'criteria': ev,
                            'governing_equation':
                                s['governing_equation']})
        if passed and chosen is None:
            chosen = s['name']
    return chosen, evaluations
def regime_at_bias(p, vgs_v, vds_v, knobs=None, manager=None):
    frame = regime_frame(p, vgs_v, vds_v, knobs)
    regime, evaluations = classify_regime(frame, knobs, manager)
    clean = {k: (None if isinstance(v, float) and not math.isfinite(v)
                 else v)
             for k, v in frame.items() if k != 'knobs'}
    return {'regime': regime, 'frame': clean, 'knobs': frame['knobs'],
            'evaluations': evaluations}
def _grid(k):
    n = int(round(k['grid_max_v'] / k['grid_step_v']))
    return [round(i * k['grid_step_v'], 6) for i in range(n + 1)]
def regime_map(p, vg_grid=None, vd_grid=None, knobs=None,
               manager=None):
    """One dot row per grid point, series = its regime (x = Vd,
    y = Vg) — the 2-D regime map on the (Vd, Vg) plane."""
    k = {**REGIME_KNOBS, **(knobs or {})}
    vg_grid = list(vg_grid) if vg_grid is not None else _grid(k)
    vd_grid = list(vd_grid) if vd_grid is not None else _grid(k)
    rows = []
    for vg in vg_grid:
        for vd in vd_grid:
            regime, _ = classify_regime(regime_frame(p, vg, vd, k),
                                        k, manager)
            rows.append({'series': regime or 'unclassified',
                         'style': 'dot', 'dash': False,
                         'x': vd, 'y': vg})
    return rows
def map_summary(rows):
    """{regime: fraction of grid points} (sums to 1) + counts."""
    counts = {}
    for r in rows:
        counts[r['series']] = counts.get(r['series'], 0) + 1
    n = len(rows) or 1
    return {'points': len(rows), 'counts': counts,
            'fractions': {s: c / n for s, c in counts.items()}}
def exponent_rows(p, vd=0.6, knobs=None, step=0.01, vgs_max=0.6):
    """Id–Vg exponent curve at fixed Vd: line 'm = dlnId/dlnVov'
    (x = Vgs, y = m; only where m is defined) + band rows shading
    the square-law and velocity-saturated bands over the x range +
    a guide at Vt — the reader sees which law the device obeys
    where."""
    k = {**REGIME_KNOBS, **(knobs or {})}
    rows = []
    n = int(round(vgs_max / step))
    for i in range(n + 1):
        vg = round(i * step, 6)
        m, _reason = vov_exponent(p, vg, vd, k)
        if m is None:
            continue
        rows.append({'series': 'm = dlnId/dlnVov', 'style': 'line',
                     'dash': False, 'x': vg, 'y': m})
    for label, lo, hi in (
            ('square-law band (m ≈ 2)', k['m_sq_lo'], k['m_sq_hi']),
            ('velocity-saturated band (m ≈ 1)', k['m_vs_lo'],
             k['m_vs_hi'])):
        for x in (0.0, vgs_max):
            rows.append({'series': label, 'style': 'band',
                         'dash': False, 'x': x, 'lo': lo, 'hi': hi})
    f = frame_at(p, 0.0, vd, k)
    rows.append({'series': 'Vt', 'style': 'guide', 'dash': True,
                 'x': f['vt'], 'label': 'Vt', 'y': None})
    rows.append({'series': 'Vt + Vov_min', 'style': 'guide',
                 'dash': True, 'x': f['vt_on'], 'label': 'Vt + Vov_min',
                 'y': None})
    return rows
OUTPUT_VG = (0.2, 0.3, 0.4, 0.5, 0.6)
def output_regime_rows(p, vg_list=OUTPUT_VG, knobs=None, step=0.02,
                       vds_max=0.6, manager=None):
    """The Id–Vd family (Id in µA) where each POINT's series is its
    regime, so the graph colours the curves by regime; the Vg of
    the point is carried as its label."""
    k = {**REGIME_KNOBS, **(knobs or {})}
    rows = []
    n = int(round(vds_max / step))
    for vg in vg_list:
        for i in range(n + 1):
            vd = round(i * step, 6)
            f = regime_frame(p, vg, vd, k)
            regime, _ = classify_regime(f, k, manager)
            rows.append({'series': regime or 'unclassified',
                         'style': 'dot', 'dash': False,
                         'x': vd, 'y': f['id_a'] * 1e6,
                         'label': f'Vg = {vg:g} V'})
    return rows
def _verdict(p, vdd, knobs, manager):
    k = {**REGIME_KNOBS, **(knobs or {})}
    pt = regime_at_bias(p, vdd, vdd, k, manager)
    fr = pt['frame']
    m = fr.get('vov_exponent')
    vt_on = fr['vt_on']
    if m is None:
        return (f'exponent undefined at (Vgs, Vds) = ({vdd:g}, {vdd:g}) V: '
                f'{fr.get("m_refusal")} — regime '
                f'{pt["regime"]}'), pt
    law = {
        'velocity-saturated': ('obeys the velocity-saturated law '
                               '(Id = Qxo·v_xo, m ≈ 1): short-channel, '
                               'not square-law — [VS1] eq.(9)-(10), '
                               '[RAH03]'),
        'square-law': ('lands in the long-channel square-law band '
                       '(m ≈ 2) — in the F1 VS model this is a '
                       'softplus/Ff corner, not pinch-off; treat as '
                       'a reference match, not physics'),
        'transition-exponent': ('sits in the exponent crossover '
                                '(1 < m < 2): mobility and injection '
                                'legs comparable — [VS1] Vdsat = '
                                'v_xo Lg/μ balance'),
        'contact-limited-sublinear': ('is contact-limited (m < 1): the '
                                      'series Rc eats the overdrive — '
                                      '[FC10] Rc scaling is the lever'),
        'dibl-tilted-saturation': ('saturates with a DIBL tilt (gds/gm '
                                   f'= {fr["gds_over_gm"]:.3f} > '
                                   f'{k["gds_over_gm_max"]:g}): Vt = '
                                   'vt0 - dVt - DIBL·Vds — [VS1] eq.(8)'),
        'linear-triode': ('is still in triode at Vdd (Vds < Vdsat): '
                          'Id ∝ Vds, the resistor leg'),
        'super-square': ('exceeds the square-law band (m > m_sq_hi): '
                         'the softplus corner just above Vt + Vov_min'),
    }.get(pt['regime'], f'is in regime {pt["regime"]}')
    return (f'{law} above Vt+Vov_min = {vt_on:.3f} V at Vdd = {vdd:g} V '
            f'(m≈{m:.2f}); Fsat = {fr["fsat"]:.2f}, '
            f'Vdsat = {fr["vdsat"]:.3f} V'), pt
def device_regimes_report(p, device, vgs=None, vds=None, knobs=None,
                          manager=None, vdd=0.6):
    """The /regimes payload: definitions, the map summary, the point
    classification (when vgs/vds given), the exponent at Vdd and a
    verdict sentence."""
    k = {**REGIME_KNOBS, **(knobs or {})}
    rows = regime_map(p, knobs=k, manager=manager)
    verdict, at_vdd = _verdict(p, vdd, k, manager)
    out = {
        'ok': True, 'device': device.name, 'fidelity': FIDELITY,
        'temperature_k': getattr(device, 'temperature_k', None),
        'knobs': k,
        'regimes': _regime_defs(manager),
        'map_summary': map_summary(rows),
        'exponent_at_vdd': {'vdd': vdd,
                            'm': at_vdd['frame']['vov_exponent'],
                            'regime': at_vdd['regime'],
                            'refusal': at_vdd['frame'].get('m_refusal')},
        'verdict': verdict,
        'note': ('m = dlnId/dlnVov by central difference; the VS '
                 'model saturates by velocity, so m ≈ 2 is a '
                 'reference band it cannot reach on physics grounds'),
    }
    if vgs is not None and vds is not None:
        out['point'] = regime_at_bias(p, vgs, vds, k, manager)
    return out
def _device_graph(kind, description, x_label, y_label,
                  y_type='linear'):
    """Same wrapped {graphConfig} form as cnt_device_viz._device_graph
    (copied, not imported — private name)."""
    return {
        'name': f'cnt-device-{kind}',
        'description': description + ' — data: /api/cntfet/'
                       'device/{name}/points?curve=' + kind,
        'source_class': 'AlignedCNTFETDevice',
        'definition': json.dumps({'graphConfig': {
            'renderStyle': 'lineY',
            'xDimension': 'x',
            'yDimensions': ['y'],
            'seriesDimension': 'series',
            'styleDimension': 'style',
            'seriesColors': [],
            'options': {'showLegend': True, 'showGrid': True,
                        'xLabel': x_label, 'yLabel': y_label,
                        'yType': y_type},
            'aggregation': None,
        }}),
    }
SEED_CNT_REGIME_GRAPHS = [
    _device_graph(
        'regime-map',
        'IV REGIME MAP on the (Vd, Vg) plane: every bias point '
        'coloured by the regime its criteria qualify — '
        'subthreshold / near-threshold / linear-triode / '
        'velocity-saturated / square-law / crossover / '
        'contact-limited / DIBL-tilted — so the reader sees at a '
        'glance where the device is a resistor, where it is '
        'velocity-limited, and whether any bias reaches the '
        'long-channel square law (the F1 VS model cannot)',
        'Vd (V)', 'Vg (V)'),
    _device_graph(
        'exponent',
        'Local drive-law exponent m = dlnId/dlnVov along Vg at Vdd, '
        'with the square-law band (m ≈ 2, long-channel pinch-off) '
        'and the velocity-saturated band (m ≈ 1, VS/ballistic '
        'limit) shaded and Vt / Vt + Vov_min as guides: which law '
        'the device obeys where, and how far the series Rc pulls m '
        'below 1',
        'Vg (V)', 'm = dlnId/dlnVov'),
    _device_graph(
        'output-regimes',
        'Output family Id(Vd) per gate bias with every point '
        'coloured by its regime: the triode leg, the Vdsat knee, '
        'and whether saturation is velocity-limited, '
        'contact-limited or DIBL-tilted — the same curves the '
        'output graph shows, now labelled by the law behind them',
        'Vd (V)', 'Id (uA)'),
]
def _build_map(id_fn, p, device, manager, knobs):
    return regime_map(p, knobs=knobs, manager=manager)
def _build_exponent(id_fn, p, device, manager, knobs):
    return exponent_rows(p, vd=0.6, knobs=knobs)
def _build_output(id_fn, p, device, manager, knobs):
    return output_regime_rows(p, knobs=knobs, manager=manager)
CURVE_BUILDERS = {
    'regime-map': _build_map,
    'exponent': _build_exponent,
    'output-regimes': _build_output,
}
