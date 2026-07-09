"""
@cross-cutting
@module aquaponics.vermicompost_analysis
@tags @xc:bindings

aqp-7 kinetics — an ABSTRACT box-model of vermicompost enrichment
(NOT microbial CFD). Duck-typed manager (anything with .objectTables)
so selftests run stdlib-only.

CompostLoopState (cells_json convention) carries the running bed pool;
`simulate_enrichment` integrates two coupled processes over a timeline:

  Mineralization (bed pool grows soluble):
      dPool_s/dt = k_min(T) · substrate_s
    first-order release, k_min temperature-scaled by Q10 from the
    profile's 20 C rate. Runs ALWAYS (both modes, on and off windows).

  Leaching (water carries pool away — only while flowing):
      leach_s = min(pool_s,
                    transfer_coeff · flow_L_hr · dt_hr · (C_bin_s − 0))
    a contact-time-limited, gradient-driven mass-transfer term
    (incoming water assumed nutrient-poor relative to the bed, so the
    gradient is ~C_bin). Never leaches more than the pool holds.

Two modes = two schedule integrators over the SAME kinetics:
  direct   : water flows every step -> steady enrichment at loop flow.
  periodic : water flows only during on_minutes each cycle_hours;
             between windows the pool RECHARGES (mineralization
             continues, no leaching) -> pulses of higher enrichment.

Every rate constant is an ABSTRACT PRIOR; results carry `priorsNote`
with the literature ranges (honest-absence — no pseudo-precision).

@consumers
  - aquaponics.vermicompost_api / scoring (enrichment_result_json)
@see /AQUAPONICS_PHASE2_PLAN.md §aqp-7
"""

import json

#: Literature ranges for the abstract priors (carried in every result
#: so the numbers never read as measured).
PRIOR_RANGES = {
    'k_min_per_day_20c': '0.01-0.05 /day (vermicompost N mineralization)',
    'q10': '1.8-2.5 (soil biological Q10)',
    'transfer_coeff_per_hr': '0.05-0.30 /hr (packed-bed leaching, '
                             'contact-time limited)',
}


def _rows(manager, class_name):
    table = (getattr(manager, 'objectTables', None) or {}).get(
        class_name, {})
    return list(table.values()) if isinstance(table, dict) \
        else list(table)


def _named(manager, class_name, name):
    for row in _rows(manager, class_name):
        if getattr(row, 'name', '') == name:
            return row
    return None


def _f(row, attr, default=0.0):
    value = getattr(row, attr, default)
    try:
        return float(default if value is None else value)
    except (TypeError, ValueError):
        return float(default)


def _parse(text, fallback='{}'):
    try:
        loaded = json.loads(text or fallback)
        return loaded if loaded is not None else json.loads(fallback)
    except Exception:
        return json.loads(fallback)


def k_min_at(profile, temperature_c):
    """Temperature-scaled first-order mineralization rate (per day)."""
    base = _f(profile, 'k_min_per_day_20c', 0.03)
    q10 = _f(profile, 'q10', 2.0) or 2.0
    return base * (q10 ** ((float(temperature_c) - 20.0) / 10.0))


def moisture_suitability(moisture, optimum=0.8, width=0.25):
    """0-1 factor: worm-bed mineralization peaks near the moisture
    target and falls off either side (a simple tent curve)."""
    deficit = abs(float(moisture) - optimum) / width
    return max(0.0, 1.0 - deficit)


def steady_release(manager, bin_name):
    """The bed's soluble release profile (mg/kg bed) scaled by maturity
    + moisture + worm activity — the 'source' the water enriches from,
    with no flow yet. Honest refusal when rows are missing."""
    bin_row = _named(manager, 'CompostBinDefinition', bin_name)
    if bin_row is None:
        return {'ok': False,
                'error': f"no CompostBinDefinition named '{bin_name}'"}
    profile = _named(manager, 'VermicompostProfile',
                     getattr(bin_row, 'release_profile_name', ''))
    if profile is None:
        return {'ok': False,
                'error': f"bin '{bin_name}' has no VermicompostProfile "
                         f"(release_profile_name="
                         f"'{getattr(bin_row, 'release_profile_name', '')}')",
                'suggestion': {
                    'knob': 'CompostBinDefinition.release_profile_name',
                    'action': 'point it at a VermicompostProfile row',
                    'evidence': 'the release profile IS the nutrient '
                                'source; without it there is nothing to '
                                'leach'}}
    pool = _parse(getattr(profile, 'concentrations_json', '{}'))
    moisture = moisture_suitability(
        _f(bin_row, 'moisture_target', 0.8))
    maturity = min(1.0, _f(bin_row, 'maturity_days', 60.0) / 60.0)
    worm = min(1.5, 0.5 + _f(bin_row, 'worm_density', 0.1) * 5.0)
    activity = moisture * maturity * worm
    release = {sp: round(float(v) * activity, 4)
               for sp, v in pool.items()}
    return {'ok': True, 'binName': bin_name,
            'releaseMgPerKgBed': release,
            'activityFactor': round(activity, 4),
            'activityBreakdown': {'moisture': round(moisture, 3),
                                  'maturity': round(maturity, 3),
                                  'wormActivity': round(worm, 3)},
            'priorsFlagged': bool(getattr(profile, 'priors_flagged',
                                          True)),
            'priorsNote': PRIOR_RANGES}


def _bed_pool_mg(manager, bin_row, profile):
    """Total soluble pool available (mg) = release conc × bed mass,
    scaled by bed activity."""
    release = steady_release(manager, getattr(bin_row, 'name', ''))
    if not release.get('ok'):
        return None, release
    bed_mass = _f(bin_row, 'bed_mass_kg', 12.0)
    return ({sp: v * bed_mass
             for sp, v in release['releaseMgPerKgBed'].items()},
            release)


def simulate_enrichment(manager, bin_name, mode=None, hours=24.0,
                        dt_hours=0.5, flow_l_per_hr=None,
                        water_volume_l=None):
    """Integrate the bed pool + leaching over `hours`. Returns per-
    species enrichment timeline, cycle-averaged delivery, pulse peaks,
    and the limiting factor.

    mode: overrides the bin's mode; hours/dt_hours set the timeline;
    flow_l_per_hr overrides the loop flow (else a default). Enrichment
    is expressed as mg leached per litre of water passing (the
    concentration the water GAINS)."""
    bin_row = _named(manager, 'CompostBinDefinition', bin_name)
    if bin_row is None:
        return {'ok': False,
                'error': f"no CompostBinDefinition named '{bin_name}'"}
    mode = mode or getattr(bin_row, 'mode', 'direct')
    if mode not in ('direct', 'periodic'):
        return {'ok': False,
                'error': f"mode must be direct|periodic, got '{mode}'"}
    profile = _named(manager, 'VermicompostProfile',
                     getattr(bin_row, 'release_profile_name', ''))
    if profile is None:
        return steady_release(manager, bin_name)   # carries the refusal

    pool, release = _bed_pool_mg(manager, bin_row, profile)
    if pool is None:
        return release
    substrate = dict(pool)          # bound pool feeding mineralization
    soluble = {sp: 0.0 for sp in pool}   # currently-leachable soluble
    flow = float(flow_l_per_hr) if flow_l_per_hr is not None \
        else 1.5
    temperature = _f(bin_row, 'temperature_c', 20.0)
    k_min_day = k_min_at(profile, temperature) \
        * moisture_suitability(_f(bin_row, 'moisture_target', 0.8))
    transfer = _f(profile, 'transfer_coeff_per_hr', 0.15)
    on_minutes = _f(bin_row, 'on_minutes', 20.0)
    cycle_hours = _f(bin_row, 'cycle_hours', 6.0) or 6.0

    steps = max(1, int(round(float(hours) / float(dt_hours))))
    timeline = []
    cumulative = {sp: 0.0 for sp in pool}
    pulse_peak = {sp: 0.0 for sp in pool}
    volume_passed = 0.0
    for i in range(steps):
        t = i * dt_hours
        # Mineralization: bound substrate -> soluble pool (always).
        for sp in pool:
            released = k_min_day * (dt_hours / 24.0) * substrate[sp]
            released = min(released, substrate[sp])
            substrate[sp] -= released
            soluble[sp] += released
        # Is water flowing this step?
        if mode == 'direct':
            flowing = True
        else:
            phase_h = t % cycle_hours
            flowing = phase_h < (on_minutes / 60.0)
        gained = {sp: 0.0 for sp in pool}
        if flowing and flow > 0:
            water_l = flow * dt_hours
            volume_passed += water_l
            for sp in pool:
                leach = min(soluble[sp],
                            transfer * flow * dt_hours * soluble[sp])
                soluble[sp] -= leach
                cumulative[sp] += leach
                conc = leach / water_l if water_l > 0 else 0.0
                gained[sp] = conc
                pulse_peak[sp] = max(pulse_peak[sp], conc)
        timeline.append({'timeHr': round(t, 3), 'flowing': flowing,
                         'gainedMgPerL': {sp: round(v, 5)
                                          for sp, v in gained.items()}})

    avg_conc = {sp: round(cumulative[sp] / volume_passed, 5)
                if volume_passed > 0 else 0.0 for sp in pool}
    limiting = _limiting_species(cumulative, pool)
    return {
        'ok': True, 'binName': bin_name, 'mode': mode,
        'hours': float(hours), 'flowLPerHr': flow,
        'cumulativeLeachedMg': {sp: round(v, 4)
                                for sp, v in cumulative.items()},
        'cycleAveragedMgPerL': avg_conc,
        'pulsePeakMgPerL': {sp: round(v, 5)
                            for sp, v in pulse_peak.items()},
        'waterVolumePassedL': round(volume_passed, 3),
        'timeline': timeline,
        'limitingFactor': limiting,
        'priorsFlagged': True, 'priorsNote': PRIOR_RANGES,
        'note': 'ABSTRACT box-model: first-order mineralization + '
                'contact-time-limited leaching. Rate constants are '
                'literature-range priors, not measured.',
    }


def _limiting_species(cumulative, pool):
    """The species whose bed pool is most nearly exhausted (the bound
    on delivery). Named, honest-absence idiom."""
    ratios = {sp: (cumulative[sp] / pool[sp]) if pool.get(sp) else 0.0
              for sp in pool}
    if not ratios:
        return 'empty release profile — nothing to leach'
    sp, frac = max(ratios.items(), key=lambda kv: kv[1])
    if frac < 0.05:
        return None    # far from pool-limited; flow/contact bounds it
    return (f'{sp} pool {frac * 100:.0f}% depleted over the run — '
            f'delivery becomes pool-limited (knob: bed_mass_kg / '
            f'maturity_days / release profile)')


def compare_modes(manager, bin_name, hours=24.0, flow_l_per_hr=None):
    """direct vs periodic side by side with an evidence-bearing
    recommendation (knobs-and-suggestions — recommend, don't impose)."""
    direct = simulate_enrichment(manager, bin_name, mode='direct',
                                 hours=hours, flow_l_per_hr=flow_l_per_hr)
    if not direct.get('ok'):
        return direct
    periodic = simulate_enrichment(manager, bin_name, mode='periodic',
                                   hours=hours,
                                   flow_l_per_hr=flow_l_per_hr)
    if not periodic.get('ok'):
        return periodic

    def _total(result):
        return sum(result['cumulativeLeachedMg'].values())

    def _peak(result):
        return max(result['pulsePeakMgPerL'].values() or [0.0])

    direct_total, periodic_total = _total(direct), _total(periodic)
    if periodic_total >= direct_total * 0.6 \
            and _peak(periodic) > _peak(direct) * 1.3:
        rec, why = 'periodic', (
            'periodic delivers stronger per-pulse concentration '
            f'({_peak(periodic):.4g} vs {_peak(direct):.4g} mg/L peak) '
            'while the bed recharges between windows — good when the '
            'plant benefits from intermittent high-dose feeding and '
            'you want to conserve pump runtime')
    else:
        rec, why = 'direct', (
            'direct delivers more total enrichment '
            f'({direct_total:.4g} vs {periodic_total:.4g} mg over '
            f'{hours:.0f} h) at steady concentration — good for '
            'continuous baseline feeding')
    return {
        'ok': True, 'binName': bin_name, 'hours': float(hours),
        'direct': {'totalLeachedMg': round(direct_total, 4),
                   'cycleAveragedMgPerL': direct['cycleAveragedMgPerL'],
                   'pulsePeakMgPerL': direct['pulsePeakMgPerL']},
        'periodic': {'totalLeachedMg': round(periodic_total, 4),
                     'cycleAveragedMgPerL':
                         periodic['cycleAveragedMgPerL'],
                     'pulsePeakMgPerL': periodic['pulsePeakMgPerL']},
        'recommendation': rec, 'why': why,
        'knob': 'CompostBinDefinition.mode (+ on_minutes / cycle_hours '
                'for periodic)',
        'priorsFlagged': True, 'priorsNote': PRIOR_RANGES,
    }


# Coupling out: the enriched water raises the pot's input nutrient
# profile (feeds aqp-6 system_survival/impact).

# aqp-2 NutrientSpecies names -> WaterDefinition solution keys are the
# same vocabulary; enrichment adds mg/L onto the base water profile.
def enriched_water_profile(manager, loop_name, hours=24.0):
    """Compose the bin's cycle-averaged enrichment ONTO the bound pot
    system's water profile — the input the pot actually draws.

    Returns base vs enriched concentrations per species + the uplift,
    or an honest refusal."""
    loop = _named(manager, 'CompostLoopDefinition', loop_name)
    if loop is None:
        return {'ok': False,
                'error': f"no CompostLoopDefinition named '{loop_name}'"}
    bin_name = getattr(loop, 'bin_name', '')
    pot_system = _named(manager, 'PotSystemDefinition',
                        getattr(loop, 'pot_system_name', ''))
    mode = getattr(loop, 'mode', '') or None
    # Prefer the bound water's real flow; else the loop's assumed knob.
    flow = _f(loop, 'assumed_flow_l_per_hr', 1.5)
    base_profile = {}
    water_name = ''
    if pot_system is not None:
        water = _named(manager, 'WaterDefinition',
                       getattr(pot_system, 'water_name', ''))
        if water is not None:
            water_name = getattr(water, 'name', '')
            flow = _f(water, 'flow_rate_l_per_hr', flow) or flow
            np_row = _named(manager, 'NutrientProfile',
                            getattr(water, 'nutrient_profile_name', ''))
            if np_row is not None:
                base_profile = _parse(
                    getattr(np_row, 'concentrations_json', '{}'))

    sim = simulate_enrichment(manager, bin_name, mode=mode, hours=hours,
                              flow_l_per_hr=flow)
    if not sim.get('ok'):
        return sim
    uplift = sim['cycleAveragedMgPerL']
    species = set(base_profile) | set(uplift)
    enriched = {sp: round(float(base_profile.get(sp, 0.0))
                          + float(uplift.get(sp, 0.0)), 4)
                for sp in species}
    return {
        'ok': True, 'loopName': loop_name, 'binName': bin_name,
        'waterName': water_name, 'mode': sim['mode'],
        'flowLPerHr': flow,
        'baseMgPerL': {sp: round(float(base_profile.get(sp, 0.0)), 4)
                       for sp in species},
        'upliftMgPerL': {sp: round(float(uplift.get(sp, 0.0)), 4)
                         for sp in species},
        'enrichedMgPerL': enriched,
        'flowSource': f'WaterDefinition.flow_rate_l_per_hr ({water_name})'
                      if water_name else
                      'CompostLoopDefinition.assumed_flow_l_per_hr '
                      '(pending aqp-3 hydraulics)',
        'priorsFlagged': True, 'priorsNote': PRIOR_RANGES,
    }
