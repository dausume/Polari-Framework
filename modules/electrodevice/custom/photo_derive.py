"""
@module electrodevice.custom.photo_derive

Tuning + optimization engines for the photo devices.

Sensor tuning: EXECUTE each candidate fragment sim (or read its
structured gap record), map gap -> absorption edge (lambda =
1240/E_gap nm), pick the candidate whose edge best matches the
target wavelength; the orientation knob contributes the classical
dipole coupling factor (aligned: cos^2 theta; random: 1/3).

Solar optimization: blackbody ULTIMATE efficiency — sun as a 5778 K
blackbody, every photon above the gap yields exactly E_gap:
u(Eg) = Eg * N_photons(E>Eg) / P_total. This is the physics CEILING
before radiative/thermodynamic (Shockley-Queisser), transport, and
processing losses — the loss ladder is stated, never hidden.

@consumers
  - electrodevice.device_api (tune / optimize acts)
  - electrodevice.electrodevice_selftest
"""

import json
import math
from datetime import datetime, timezone

HC_EV_NM = 1239.84


def _now():
    return datetime.now(timezone.utc).isoformat()


def _rows(manager, class_name):
    tables = getattr(manager, 'objectTables', None) or {}
    return (tables.get(class_name) or {})


def _save(manager, row):
    try:
        db = getattr(manager, 'db', None)
        if db is not None:
            db.saveInstanceInDB(row)
    except Exception:
        pass


def get_absorber(manager, name):
    for row in _rows(manager, 'PhotoAbsorberDefinition').values():
        if getattr(row, 'name', '') == name:
            return row
    return None


def get_stack(manager, name):
    for row in _rows(manager, 'SolarStackDefinition').values():
        if getattr(row, 'name', '') == name:
            return row
    return None


def _candidate_gap(manager, candidate, executor):
    """A candidate's gap: executed sim (provenance = the run) or its
    structured literature record (provenance = the record)."""
    if candidate.get('simModel'):
        report = executor(manager, candidate['simModel'])
        if not report.get('ok'):
            return None, {'refused': candidate['simModel'],
                          'error': str(report.get('error', ''))[:120]}
        result = report.get('result') or {}
        gap = float(result.get('gapEv') or 0.0)
        return gap, {'source': 'executed-sim',
                     'simModel': candidate['simModel'],
                     'engine': report.get('engine', ''),
                     'honesty': result.get('frontierNote', '')}
    record = candidate.get('gapRecord') or {}
    if record.get('value'):
        return float(record['value']), {
            'source': 'structured-record', 'record': record}
    return None, {'error': 'candidate has neither simModel nor '
                           'gapRecord'}


def orientation_factor(orientation, angle_deg):
    """Classical dipole coupling of aligned absorbers to polarized
    light: cos^2(theta); an unaligned film averages to 1/3."""
    if orientation == 'aligned':
        return math.cos(math.radians(angle_deg)) ** 2
    return 1.0 / 3.0


def tune_absorber(manager, absorber, executor=None):
    """The tune act: run the ladder, pick the best edge match."""
    if executor is None:
        from materialsScience.model_execution import execute_model
        executor = execute_model
    candidates = json.loads(absorber.candidates_json or '[]')
    if not candidates:
        return {'ok': False, 'error': 'no candidates on the row'}
    target = float(absorber.target_wavelength_nm)
    ladder, skipped = [], []
    for cand in candidates:
        gap, prov = _candidate_gap(manager, cand, executor)
        if gap is None or gap <= 0:
            skipped.append({'candidate': cand.get('name'), **prov})
            continue
        edge = HC_EV_NM / gap
        ladder.append({'candidate': cand['name'], 'gapEv': gap,
                       'absorptionEdge_nm': edge,
                       'matchError_nm': abs(edge - target),
                       'provenance': prov})
    if not ladder:
        return {'ok': False, 'error': 'every candidate refused',
                'skipped': skipped}
    ladder.sort(key=lambda c: c['matchError_nm'])
    best = ladder[0]
    factor = orientation_factor(absorber.orientation,
                                absorber.polarization_angle_deg)
    absorber.chosen_candidate = best['candidate']
    absorber.chosen_gap_ev = best['gapEv']
    absorber.absorption_edge_nm = best['absorptionEdge_nm']
    absorber.match_error_nm = best['matchError_nm']
    absorber.orientation_factor = factor
    absorber.derived_at = _now()
    absorber.provenance_json = json.dumps({
        'ladder': ladder, 'skipped': skipped,
        'edgeFormula': 'lambda = 1239.84 / gapEv nm (KS gap as the '
                       'optical edge — a stand-in; TD-DFT excitation '
                       'energies are the named upgrade)',
        'orientation': {'mode': absorber.orientation,
                        'angle_deg':
                            absorber.polarization_angle_deg,
                        'factor': factor,
                        'model': 'classical dipole cos^2 coupling; '
                                 'random film = 1/3'},
    })
    _save(manager, absorber)
    return {'ok': True, 'absorber': absorber.name,
            'chosen': best['candidate'],
            'gapEv': best['gapEv'],
            'absorptionEdge_nm': round(best['absorptionEdge_nm'], 1),
            'target_nm': target,
            'matchError_nm': round(best['matchError_nm'], 1),
            'orientationFactor': round(factor, 3),
            'ladder': [{k: (round(v, 2) if isinstance(v, float)
                            else v)
                        for k, v in c.items() if k != 'provenance'}
                       for c in ladder],
            'skipped': skipped}


# ---- solar: blackbody ultimate efficiency ---------------------------

def ultimate_efficiency(gap_ev, t_sun_k=5778.0, points=4000):
    """u(Eg) = Eg * N(E>Eg) / P_total for a T_sun blackbody photon
    flux — the pre-Shockley-Queisser ceiling."""
    if gap_ev <= 0:
        return 0.0
    kt = 8.617333262e-5 * t_sun_k   # eV
    e_hi = 30.0 * kt
    n = p = 0.0
    de = e_hi / points
    for i in range(1, points):
        e = i * de
        # photon flux density ~ E^2/(exp(E/kT)-1); power ~ E^3/(...)
        w = 1.0 / (math.exp(e / kt) - 1.0)
        p += (e ** 3) * w * de
        if e >= gap_ev:
            n += (e ** 2) * w * de
    return (gap_ev * n) / p if p > 0 else 0.0


OMEGA_SUN = 6.87e-5   # sr — the sun's solid angle, unconcentrated
KT_CELL_EV = 0.025852  # 300 K


def _photon_integral(gap_ev, kt):
    """N(Eg,T) = int_Eg E^2/(exp(E/kT)-1) dE. Numeric for the hot
    (solar) side; Boltzmann-analytic for the cold side (exp(-Eg/kTc)
    underflows numeric grids)."""
    if gap_ev / kt > 30.0:
        x = gap_ev / kt
        return math.exp(-x) * kt * (gap_ev ** 2 + 2 * gap_ev * kt
                                    + 2 * kt ** 2)
    n = 0.0
    e_hi = gap_ev + 40.0 * kt
    points = 4000
    de = (e_hi - gap_ev) / points
    for i in range(points):
        e = gap_ev + (i + 0.5) * de
        n += (e ** 2) / (math.exp(e / kt) - 1.0) * de
    return n


def detailed_balance_efficiency(gap_ev, t_sun_k=5778.0,
                                t_cell_k=300.0):
    """The single-junction Shockley-Queisser limit, unconcentrated:
    J_sc from the solar solid angle, radiative dark current from the
    300 K cell emitting into the hemisphere, max-power point scanned.
    Peaks ~31%% near 1.2-1.3 eV for a 5778 K blackbody sun (the
    commonly quoted 33.7%% uses the AM1.5G spectrum)."""
    if gap_ev <= 0:
        return 0.0
    kt_s = 8.617333262e-5 * t_sun_k
    kt_c = 8.617333262e-5 * t_cell_k
    j_sc = OMEGA_SUN * _photon_integral(gap_ev, kt_s)
    j_0 = math.pi * _photon_integral(gap_ev, kt_c)
    if j_0 <= 0 or j_sc <= 0:
        return 0.0
    # P_in: full solar power through the same solid angle
    kt = kt_s
    p_in = 0.0
    points = 4000
    e_hi = 30.0 * kt
    de = e_hi / points
    for i in range(1, points):
        e = i * de
        p_in += (e ** 3) / (math.exp(e / kt) - 1.0) * de
    p_in *= OMEGA_SUN
    v_oc = kt_c * math.log(j_sc / j_0 + 1.0)
    best = 0.0
    for i in range(1, 2000):
        v = v_oc * i / 2000.0
        j = j_sc - j_0 * (math.exp(v / kt_c) - 1.0)
        if j <= 0:
            break
        best = max(best, j * v)
    return best / p_in


def optimize_stack(manager, stack, executor=None):
    """Rank absorber candidates by ultimate efficiency, stamp the
    winner, and state the loss ladder honestly."""
    if executor is None:
        from materialsScience.model_execution import execute_model
        executor = execute_model
    candidates = json.loads(stack.absorber_candidates_json or '[]')
    if not candidates:
        return {'ok': False, 'error': 'no absorber candidates'}
    ranked, skipped = [], []
    for cand in candidates:
        gap, prov = _candidate_gap(manager, cand, executor)
        if gap is None or gap <= 0:
            skipped.append({'candidate': cand.get('name'), **prov})
            continue
        entry = {'candidate': cand['name'], 'gapEv': gap,
                 'sqLimit':
                     round(detailed_balance_efficiency(gap), 4),
                 'ultimateEfficiency':
                     round(ultimate_efficiency(gap), 4),
                 'absorptionEdge_nm': round(HC_EV_NM / gap, 1),
                 'communitySource': cand.get('source', ''),
                 'provenance': prov}
        if cand.get('demonstrated'):
            entry['demonstrated'] = cand['demonstrated']
        if cand.get('caveats'):
            entry['caveats'] = cand['caveats']
        ranked.append(entry)
    if not ranked:
        return {'ok': False, 'error': 'every candidate refused',
                'skipped': skipped}
    # Rank by the DETAILED-BALANCE limit — the physical single-
    # junction ceiling; 'ultimate' stays visible as the pre-detailed-
    # balance bound it is (Dustin's 43%%-vs-limits challenge).
    ranked.sort(key=lambda c: -c['sqLimit'])
    policy = getattr(stack, 'selection_policy', 'sq-limit') \
        or 'sq-limit'
    physics_best = ranked[0]
    demo_best = max(ranked, key=lambda c:
                    (c.get('demonstrated') or {}).get('value', 0.0))
    best = (demo_best if policy == 'demonstrated'
            else physics_best)
    suggestion = None
    if physics_best['candidate'] != demo_best['candidate']:
        suggestion = {
            'knob': f'SolarStackDefinition "{stack.name}" '
                    'selection_policy (sq-limit | demonstrated)',
            'why': f"the physics ceiling favors "
                   f"{physics_best['candidate']} (SQ "
                   f"{physics_best['sqLimit'] * 100:.1f}%) but "
                   f"demonstrated results favor "
                   f"{demo_best['candidate']} "
                   f"({(demo_best.get('demonstrated') or {}) .get('value', 0) * 100:.1f}% shown; see its caveats)",
            'how': 'flip the knob and re-optimize; both readings '
                   'stay in the ranking either way',
        }
    layers = sorted(
        (r for r in _rows(manager, 'SolarLayerDefinition').values()
         if getattr(r, 'stack_name', '') == stack.name),
        key=lambda r: int(getattr(r, 'position', 0)))
    stack.chosen_absorber = best['candidate']
    stack.chosen_gap_ev = best['gapEv']
    stack.ultimate_efficiency = best['sqLimit']
    stack.derived_at = _now()
    stack.provenance_json = json.dumps({
        'ranking': ranked, 'skipped': skipped,
        'model': 'RANKED BY the detailed-balance (Shockley-'
                 'Queisser) single-junction limit, 5778K blackbody '
                 'sun, unconcentrated, 300K cell, radiative-only '
                 'dark current — the PHYSICAL ceiling (~31% peak '
                 'near 1.2-1.3 eV; AM1.5G gives the familiar '
                 '33.7%). ultimateEfficiency is also reported: SQ '
                 'their own pre-detailed-balance bound (~44% peak) '
                 '— NOT a panel efficiency. Below both: transport/'
                 'recombination, reflection, and community-grade '
                 'processing; realistic homemade Cu2O ~1%, dye '
                 'cells a few %.',
    })
    _save(manager, stack)
    report_out = {'ok': True, 'stack': stack.name,
            'selectionPolicy': policy,
            'chosen': best['candidate'],
            'gapEv': best['gapEv'],
            'sqLimit': best['sqLimit'],
            'ultimateEfficiency': best['ultimateEfficiency'],
            'ranking': [{k: v for k, v in c.items()
                         if k != 'provenance'} for c in ranked],
            'skipped': skipped,
            'layers': [{'position': l.position, 'role': l.role,
                        'material': l.material,
                        'thickness_m': l.thickness_m,
                        'communitySource': l.community_source}
                       for l in layers]}
    if suggestion:
        report_out['suggestion'] = suggestion
    return report_out
