"""
@cross-cutting
@module nutrition.weight_trajectory
@tags @xc:bindings

nmp-6 — the dynamic energy-balance weight model, implemented from
the PUBLISHED equations (Chow & Hall 2008 PLoS Comput Biol; Hall et
al. 2011 Lancet "Quantification of the effect of energy imbalance
on bodyweight") — deliberately NOT NIH's own implementation (their
code needs a license; the science does not).

The model (two compartments, daily steps):
  body = fat mass F + lean mass L
  energy partition (Forbes dL/dF = C/F, C = 10.4 kg), as the
    ENERGY fraction going to lean:
      p = C x rho_L / (C x rho_L + F x rho_F)
    — the fatter the body, the smaller the lean share; the
    effective energy density of weight change lands near the
    classic ~7700 kcal/kg for typical adults and RISES with
    leanness (Chow & Hall 2008 partitioning)
  dF/dt = (1 - p) x (EI - TEE) / rho_F,  rho_F = 9441 kcal/kg
  dL/dt =      p  x (EI - TEE) / rho_L,  rho_L = 1816 kcal/kg
  TEE = K + gamma_F x F + gamma_L x L + delta x BW + TEF + AT
    gamma_F = 3.2, gamma_L = 22 kcal/kg/day (tissue metabolic rates)
    delta x BW = physical activity PROPORTIONAL TO BODY WEIGHT (the
      term that makes the long-run slope land on the Lancet
      ~22-25 kcal/day per kg rule) — delta calibrated from the
      person: activity energy at baseline = TDEE - BMR - TEF,
      divided by starting weight
    TEF = 0.1 x EI (thermic effect of food)
    AT  = beta x (EI - EI_baseline), beta = 0.14 (adaptive
          thermogenesis, Lancet value)
  K absorbs the residual resting energy so the person starts in
  steady state at their current TDEE (the nut-3/nmp-1 value,
  minutes-mode aware).

Initial fat mass: measured body_fat_fraction wins; else the
Deurenberg 1991 BMI estimate (labeled prior).

The 3500-kcal/lb rule exists ONLY as a labeled naive toggle — it
over-predicts long-term loss roughly 2x because it ignores the
shrinking body's shrinking expenditure; the result says so.

Timing note (decision 14): NOTHING here reads meal or exercise
CLOCK times — energy balance only.

@consumers
  - nutrition.nutrition_api
@see AI-Notes/plans/NUTRITION_MEAL_PLANNING_PLAN.md §nmp-6
"""

from nutrition.person_analysis import _f, _rows, bmr, tdee

# published constants (kcal, kg) — every one a tunable argument.
RHO_F = 9441.0     # energy density of fat tissue (39.5 MJ/kg)
RHO_L = 1816.0     # energy density of lean tissue (7.6 MJ/kg)
GAMMA_F = 3.2      # kcal/kg/day fat-tissue metabolic rate
GAMMA_L = 22.0     # kcal/kg/day lean-tissue metabolic rate
FORBES_C = 10.4    # kg, Forbes partition constant
BETA_AT = 0.14     # adaptive thermogenesis fraction (Lancet 2011)
TEF_FRACTION = 0.1
DEFAULT_HORIZON_WEEKS = 12   # Q4 default projection window


def _initial_fat_mass(person):
    bf = _f(person, 'body_fat_fraction', 0.0)
    kg = _f(person, 'weight_kg', 70.0)
    if bf > 0:
        return kg * bf, 'measured body_fat_fraction'
    h_m = _f(person, 'height_cm', 170.0) / 100.0
    bmi = kg / (h_m * h_m) if h_m > 0 else 24.0
    age = _f(person, 'age_years', 30.0)
    sex = getattr(person, 'sex', 'any')
    sex_term = 16.2 if sex == 'male' else 5.4 if sex == 'female' \
        else 10.8
    frac = max(0.05, min(0.6,
                         (1.2 * bmi + 0.23 * age - sex_term) / 100.0))
    return kg * frac, ('Deurenberg 1991 BMI estimate (prior — set '
                       'body_fat_fraction to override)')


def project_weight(person, daily_intake_kcal, horizon_weeks=None,
                   beta_at=BETA_AT, include_naive=False):
    """Daily-step projection of the Hall/Chow model.

    daily_intake_kcal: the planned intake (e.g. a plan's average
    day, or the nmp-1 envelope target). Returns weekly points with
    an uncertainty band (baseline expenditure +-10%, a labeled
    convention — the model's real spread is dominated by how well
    TDEE is known)."""
    weeks = int(DEFAULT_HORIZON_WEEKS if horizon_weeks is None
                else horizon_weeks)
    if weeks <= 0 or weeks > 520:
        return {'ok': False,
                'error': 'horizon_weeks must be 1..520'}
    ei = float(daily_intake_kcal)
    if ei <= 0:
        return {'ok': False, 'error': 'daily_intake_kcal must be > 0'}
    base = tdee(person)
    rmr0 = bmr(person)['value']
    f0, f_basis = _initial_fat_mass(person)
    w0 = _f(person, 'weight_kg', 70.0)
    l0 = w0 - f0

    def run(tdee0):
        # calibration: activity scales with body weight; K absorbs
        # the residual resting energy. At baseline the person is in
        # steady state at tdee0.
        activity0 = max(0.0, tdee0 - rmr0 - TEF_FRACTION * tdee0)
        delta = activity0 / w0 if w0 > 0 else 0.0
        k = rmr0 - GAMMA_F * f0 - GAMMA_L * l0
        f, l = f0, l0
        points = [w0]
        for day in range(1, weeks * 7 + 1):
            at = beta_at * (ei - tdee0)
            tee = (k + GAMMA_F * f + GAMMA_L * l
                   + delta * (f + l)
                   + TEF_FRACTION * ei + at)
            imbalance = ei - tee
            # Forbes energy partition (see header): lean share of
            # the ENERGY imbalance
            fc = FORBES_C * RHO_L
            p = fc / (fc + max(f, 0.1) * RHO_F)
            f += (1 - p) * imbalance / RHO_F
            l += p * imbalance / RHO_L
            f, l = max(f, 1.0), max(l, 20.0)
            if day % 7 == 0:
                points.append(round(f + l, 2))
        return points

    mid = run(base['value'])
    lo_band = run(base['value'] * 1.10)   # higher burn -> lower curve
    hi_band = run(base['value'] * 0.90)
    result = {
        'ok': True, 'person': getattr(person, 'name', ''),
        'horizonWeeks': weeks,
        'dailyIntakeKcal': ei,
        'baselineTdee': base['value'], 'tdeeMode': base.get('mode'),
        'initialWeightKg': w0,
        'initialFatMassKg': round(f0, 1), 'fatMassBasis': f_basis,
        'weeks': list(range(weeks + 1)),
        'projectedKg': mid,
        'bandLowKg': [min(a, b) for a, b in zip(lo_band, hi_band)],
        'bandHighKg': [max(a, b) for a, b in zip(lo_band, hi_band)],
        'bandBasis': 'baseline TDEE +-10% (convention band — the '
                     'dominant real uncertainty is how well TDEE '
                     'is known)',
        'model': 'Chow & Hall 2008 / Hall 2011 Lancet, implemented '
                 'from the published equations',
        'constants': {'rhoF': RHO_F, 'rhoL': RHO_L,
                      'gammaF': GAMMA_F, 'gammaL': GAMMA_L,
                      'forbesC': FORBES_C, 'betaAT': beta_at,
                      'tefFraction': TEF_FRACTION},
        'honesty': 'energy-balance only — meal/exercise timing has '
                   'no term here (decision 14)',
    }
    goal_rate = _f(person, 'goal_rate_kg_per_week', 0.0)
    goal = getattr(person, 'goal', 'maintain')
    if goal in ('lose', 'gain') and goal_rate > 0:
        sign = -1.0 if goal == 'lose' else 1.0
        result['goalLineKg'] = [
            round(w0 + sign * goal_rate * wk, 2)
            for wk in range(weeks + 1)]
    if include_naive:
        # the labeled naive rule: 3500 kcal per pound, linear —
        # documented as over-predicting long-term change ~2x.
        deficit = base['value'] - ei
        result['naive3500Kg'] = [
            round(w0 - deficit * 7 * wk / 3500.0 * 0.4536, 2)
            for wk in range(weeks + 1)]
        result['naive3500Label'] = (
            'NAIVE estimate (3500 kcal/lb, linear): ignores the '
            'shrinking body\'s shrinking expenditure — '
            'over-predicts long-term change roughly 2x')
    return result


def observed_vs_projected(manager, person, daily_intake_kcal,
                          horizon_weeks=None):
    """Projection + the person's WeightObservations + drift."""
    proj = project_weight(person, daily_intake_kcal, horizon_weeks)
    if not proj.get('ok'):
        return proj
    obs = sorted(
        [o for o in _rows(manager, 'WeightObservation')
         if getattr(o, 'person_name', '')
         == getattr(person, 'name', '')],
        key=lambda o: (getattr(o, 'day_index', 0),
                       getattr(o, 'date', '')))
    observations, drifts = [], []
    for o in obs:
        day = getattr(o, 'day_index', 0)
        entry = {'date': getattr(o, 'date', ''),
                 'dayIndex': day,
                 'weightKg': _f(o, 'weight_kg', 0.0),
                 'context': getattr(o, 'context', '')}
        wk = day / 7.0
        if 0 < day and wk <= proj['horizonWeeks']:
            lo_wk, hi_wk = int(wk), min(int(wk) + 1,
                                        proj['horizonWeeks'])
            frac = wk - lo_wk
            interp = (proj['projectedKg'][lo_wk] * (1 - frac)
                      + proj['projectedKg'][hi_wk] * frac)
            entry['projectedKg'] = round(interp, 2)
            entry['driftKg'] = round(entry['weightKg'] - interp, 2)
            drifts.append(entry['driftKg'])
        observations.append(entry)
    proj['observations'] = observations
    if drifts:
        mean_drift = sum(drifts) / len(drifts)
        proj['meanDriftKg'] = round(mean_drift, 2)
        if abs(mean_drift) > 1.0:
            proj['driftSuggestion'] = (
                f'observations run {mean_drift:+.1f} kg vs the '
                f'projection — the baseline TDEE or intake estimate '
                f'is likely off; tune metabolism_factor or check '
                f'the plan\'s real intake (knobs stay yours — '
                f'nothing recalibrates silently)')
    return proj
