"""
@module climate.custom.co2_trend

Velocity, acceleration and projection over a CO2 series
(CO2_HEALTH_PLAN.md §4). The series arrives as plain points —
[{'year','value','uncertainty'}] — because the objects own the
provenance and this file owns only the arithmetic.

THREE RULES THIS FILE ENFORCES, all from the plan:

1. ACCELERATION IS FITTED, NEVER EYEBALLED. A least-squares fit
   over a STATED window, with the fit's own standard errors, and
   a flat refusal when the window is too short to carry a second
   derivative. Too few years does not become a small number; it
   becomes a refusal that names the count and the minimum.

2. THE BAND IS THE DELIVERABLE. `crossing_band` runs the linear
   and the quadratic fit and reports BOTH crossings. The gap
   between them IS the finding — acceleration is what moves a
   crossing date earlier, and printing one number with no band
   is the documented failure mode of this page.

3. THE PUBLISHER'S OWN VELOCITY IS A SECOND PATH. NOAA publishes
   an annual growth rate directly; `velocity_from_source` reads
   it and `compare_velocity` sets it against the fitted slope.
   When those two disagree beyond tolerance the disagreement is
   a FINDING about the window or the ingest — never a pair of
   numbers to average together.

The fit centres its x axis on the LAST year of the window, so
`level` is the value AT the window end and the projection's
constant term is exact rather than an extrapolation back to
year zero.

Pure stdlib: the normal equations are built and solved here
(Gauss-Jordan with partial pivoting) so the module works on a
node with no numpy installed.

@consumers climate.co2_projection, climate.co2_indoor_seed,
climate.climate_views_seed, climate.climate_api, climate.selftest_co2
"""

import math

#: Minimum points a fit will accept, by method. Below these the
#: engine refuses; ingesting more years is what retires the
#: refusal.
MIN_POINTS = {'linear': 3, 'quadratic': 5}

#: Number of free parameters per method.
N_PARAMS = {'linear': 2, 'quadratic': 3}

#: An |acceleration| below this is treated as exactly zero when
#: solving for a crossing, so a quadratic with a vanishing second
#: derivative degrades to the linear solution instead of dividing
#: by a number near zero.
ACCEL_EPSILON = 1e-12


def _refuse(text):
    """Every failure leaves by this door."""
    return {'ok': False, 'refusal': text}


def _clean_points(points, window_from=None, window_to=None):
    """Coerce, window and sort. Returns (rows, refusal)."""
    if not isinstance(points, (list, tuple)):
        return None, _refuse(
            'points must be a list of {year, value} rows; pass '
            'the ingested series rows and this refusal retires')
    rows = []
    for raw in points:
        if not isinstance(raw, dict):
            continue
        try:
            year = float(raw.get('year'))
            value = float(raw.get('value'))
        except (TypeError, ValueError):
            continue
        if math.isnan(year) or math.isnan(value):
            continue
        try:
            unc = float(raw.get('uncertainty') or 0.0)
        except (TypeError, ValueError):
            unc = 0.0
        if window_from is not None and year < float(window_from):
            continue
        if window_to is not None and year > float(window_to):
            continue
        rows.append({'year': year, 'value': value,
                     'uncertainty': unc})
    rows.sort(key=lambda r: r['year'])
    return rows, None


def _solve_with_inverse(matrix, rhs):
    """Gauss-Jordan on [A | I | b]. Returns (x, inverse) or
    (None, None) when the matrix is singular."""
    n = len(matrix)
    aug = []
    for i in range(n):
        row = [float(v) for v in matrix[i]]
        row += [1.0 if i == j else 0.0 for j in range(n)]
        row.append(float(rhs[i]))
        aug.append(row)
    for col in range(n):
        pivot = col
        for r in range(col + 1, n):
            if abs(aug[r][col]) > abs(aug[pivot][col]):
                pivot = r
        if abs(aug[pivot][col]) < 1e-300:
            return None, None
        aug[col], aug[pivot] = aug[pivot], aug[col]
        scale = aug[col][col]
        aug[col] = [v / scale for v in aug[col]]
        for r in range(n):
            if r == col:
                continue
            factor = aug[r][col]
            if factor == 0.0:
                continue
            aug[r] = [a - factor * b
                      for a, b in zip(aug[r], aug[col])]
    solution = [aug[i][2 * n] for i in range(n)]
    inverse = [[aug[i][n + j] for j in range(n)]
               for i in range(n)]
    return solution, inverse


def fit_trend(points, method='quadratic', window_from=None,
              window_to=None):
    """Least-squares fit of level, velocity and acceleration over
    a stated window. x is centred on the window's LAST year."""
    try:
        method = str(method or 'quadratic').lower()
        if method not in MIN_POINTS:
            return _refuse(
                f'unknown fit method {method!r}; this engine '
                f'knows only linear and quadratic — a new method '
                f'row would retire this refusal')
        rows, bad = _clean_points(points, window_from, window_to)
        if bad is not None:
            return bad
        need = MIN_POINTS[method]
        n = len(rows)
        if n < need:
            return _refuse(
                f'{n} usable points in this window, {need} are '
                f'the minimum for a {method} fit; this engine '
                f'refuses to fit acceleration from too few years '
                f'rather than returning a number. Ingesting more '
                f'years of the series retires this refusal')
        base = rows[-1]['year']
        order = 2 if method == 'quadratic' else 1
        p = N_PARAMS[method]
        xs = [r['year'] - base for r in rows]
        ys = [r['value'] for r in rows]
        #: Normal equations: sums of x^(i+j) and x^i * y.
        powers = [0.0] * (2 * order + 1)
        for x in xs:
            term = 1.0
            for k in range(2 * order + 1):
                powers[k] += term
                term *= x
        rhs = [0.0] * p
        for x, y in zip(xs, ys):
            term = 1.0
            for k in range(p):
                rhs[k] += term * y
                term *= x
        matrix = [[powers[i + j] for j in range(p)]
                  for i in range(p)]
        coeffs, inverse = _solve_with_inverse(matrix, rhs)
        if coeffs is None:
            return _refuse(
                'the normal matrix is singular for this window — '
                'the years are degenerate (a single repeated '
                'year, or fewer distinct years than parameters); '
                'a window spanning distinct years retires this')
        level = coeffs[0]
        velocity = coeffs[1]
        accel = 2.0 * coeffs[2] if order == 2 else 0.0
        residuals = []
        for x, y in zip(xs, ys):
            model = 0.0
            term = 1.0
            for c in coeffs:
                model += c * term
                term *= x
            residuals.append(y - model)
        ssr = sum(r * r for r in residuals)
        rms = math.sqrt(ssr / n) if n else 0.0
        note = ''
        if n <= p:
            v_err = 0.0
            a_err = 0.0
            note = (f'{n} points for {p} parameters leaves no '
                    f'residual degrees of freedom; the standard '
                    f'errors are reported as 0.0 because they '
                    f'are UNDEFINED, not because the fit is '
                    f'certain')
        else:
            var = ssr / (n - p)
            v_diag = inverse[1][1]
            v_err = math.sqrt(max(var * v_diag, 0.0))
            if order == 2:
                a_diag = inverse[2][2]
                a_err = 2.0 * math.sqrt(max(var * a_diag, 0.0))
            else:
                a_err = 0.0
        out = {
            'ok': True,
            'method': method,
            'level': level,
            'velocity': velocity,
            'acceleration': accel,
            'velocityStderr': v_err,
            'accelerationStderr': a_err,
            'residualRms': rms,
            'nPoints': n,
            'windowFromYear': rows[0]['year'],
            'windowToYear': rows[-1]['year'],
            'baseYear': base,
        }
        if note:
            out['note'] = note
        return out
    except Exception as exc:                 # never raise out
        return _refuse(f'trend fit failed internally: {exc}')


def project(fit, year):
    """C(t) = level + v*dt + 0.5*a*dt^2, dt = year - baseYear."""
    try:
        if not isinstance(fit, dict) or not fit.get('ok'):
            return _refuse(
                'cannot project from a fit that did not succeed; '
                'the fit refusal above is the one to answer')
        target_year = float(year)
        dt = target_year - float(fit['baseYear'])
        value = (float(fit['level'])
                 + float(fit['velocity']) * dt
                 + 0.5 * float(fit['acceleration']) * dt * dt)
        return {'ok': True, 'year': target_year, 'value': value}
    except Exception as exc:
        return _refuse(f'projection failed internally: {exc}')


def crossing_year(fit, target, horizon_years=200):
    """First year at or after baseYear where the fit reaches
    `target`. The band, not this number alone, is the finding."""
    try:
        if not isinstance(fit, dict) or not fit.get('ok'):
            return _refuse(
                'cannot solve a crossing from a fit that did not '
                'succeed; answer the fit refusal first')
        target = float(target)
        horizon = float(horizon_years)
        level = float(fit['level'])
        v = float(fit['velocity'])
        a = float(fit['acceleration'])
        base = float(fit['baseYear'])
        if target <= level:
            return {'ok': True, 'alreadyCrossed': True,
                    'crossingYear': None, 'yearsAway': 0.0,
                    'note': 'already at or above this level'}
        gap = target - level
        if abs(a) <= ACCEL_EPSILON:
            if v <= 0.0:
                return _refuse(
                    'the series is not rising; no crossing. A '
                    'window in which the fitted velocity is '
                    'positive would retire this refusal')
            dt = gap / v
        else:
            disc = v * v + 2.0 * a * gap
            if disc < 0.0:
                return _refuse(
                    'no real crossing: this fit turns over before '
                    'it reaches the target, so the quadratic has '
                    'no root. A different window — or a target '
                    'below the fit turning point — retires this')
            root = math.sqrt(disc)
            candidates = [(-v + root) / a, (-v - root) / a]
            positive = sorted(c for c in candidates if c > 0.0)
            if not positive:
                return _refuse(
                    'no crossing at or after the window end: '
                    'every root of this fit lies in the past. A '
                    'window ending nearer the present retires it')
            dt = positive[0]
        if dt > horizon:
            return _refuse(
                f'crossing falls beyond the '
                f'{int(horizon)}-year horizon; a quadratic fit '
                f'is not a climate model and will not print a '
                f'year for 2300')
        return {'ok': True, 'alreadyCrossed': False,
                'crossingYear': base + dt, 'yearsAway': dt}
    except Exception as exc:
        return _refuse(f'crossing solve failed internally: {exc}')


def crossing_band(fits, target, horizon_years=200):
    """Run both fits at one target and report the BAND. A single
    crossing year with no band is the failure mode."""
    try:
        if not isinstance(fits, dict):
            return _refuse(
                "fits must be {'linear': fit, 'quadratic': fit}; "
                'pass both fits and this refusal retires')
        note = ('the linear and quadratic fits bracket the '
                'crossing; acceleration moves it earlier')
        results = {}
        for key in ('linear', 'quadratic'):
            fit = fits.get(key)
            if not isinstance(fit, dict):
                results[key] = _refuse(
                    f'no {key} fit was supplied; fit it and this '
                    f'side of the band appears')
            else:
                results[key] = crossing_year(fit, target,
                                             horizon_years)
        years = []
        for key in ('linear', 'quadratic'):
            res = results[key]
            if res.get('ok') and res.get('crossingYear') is not None:
                years.append(float(res['crossingYear']))
        payload = {
            'ok': True,
            'target': float(target),
            'linear': results['linear'],
            'quadratic': results['quadratic'],
            'note': note,
        }
        if len(years) == 2:
            payload['low'] = min(years)
            payload['high'] = max(years)
            payload['bandWidthYears'] = max(years) - min(years)
            payload['oneSided'] = False
        elif len(years) == 1:
            payload['low'] = years[0]
            payload['high'] = years[0]
            payload['bandWidthYears'] = 0.0
            payload['oneSided'] = True
            payload['note'] = (
                note + ' — but only ONE side solved here, so this '
                'is a one-sided band, not a bracket; the other '
                "fit's refusal is carried beside it")
        else:
            # NO side solved. Returning ok=True here would be a
            # success that carries no answer — the exact shape
            # that lets a null reach a rendered page or an
            # exported document as the string "None". A band with
            # no bounds is a refusal, and it names both sides'
            # reasons so the caller can see WHY (usually: the
            # target is beyond the projection horizon).
            reasons = '; '.join(
                f'{key}: {results[key].get("refusal", "no crossing")}'
                for key in ('linear', 'quadratic'))
            return {
                'ok': False, 'target': float(target),
                'linear': results['linear'],
                'quadratic': results['quadratic'],
                'low': None, 'high': None, 'bandWidthYears': None,
                'oneSided': False,
                'refusal': (f'neither fit produced a crossing year '
                            f'for {float(target)} — {reasons}'),
            }
        return payload
    except Exception as exc:
        return _refuse(f'crossing band failed internally: {exc}')


def velocity_from_source(growth_points, window_from=None,
                         window_to=None):
    """The publisher's OWN growth-rate series — NOAA publishes an
    annual CO2 growth rate directly, so this path never touches
    the level fit."""
    try:
        rows, bad = _clean_points(growth_points, window_from,
                                  window_to)
        if bad is not None:
            return bad
        n = len(rows)
        if n < 1:
            return _refuse(
                'no published growth-rate points in this window; '
                'ingesting the growth-rate series retires this')
        values = [r['value'] for r in rows]
        mean = sum(values) / n
        if n > 1:
            var = sum((v - mean) ** 2 for v in values) / (n - 1)
            sd = math.sqrt(var)
        else:
            sd = 0.0
        return {
            'ok': True,
            'meanVelocity': mean,
            'stdDev': sd,
            'nPoints': n,
            'windowFromYear': rows[0]['year'],
            'windowToYear': rows[-1]['year'],
        }
    except Exception as exc:
        return _refuse(f'source velocity failed internally: {exc}')


def compare_velocity(fitted_velocity, source_velocity,
                     tolerance=0.15):
    """Two independent paths to one quantity. Disagreement is a
    finding, not an averaging problem."""
    try:
        fitted = float(fitted_velocity)
        source = float(source_velocity)
        tol = abs(float(tolerance))
        denom = abs(source)
        if denom < 1e-12:
            return _refuse(
                'the published velocity is zero, so a relative '
                'difference has no meaning; a non-zero '
                'growth-rate window retires this refusal')
        rel = abs(fitted - source) / denom
        agree = rel <= tol
        if agree:
            verdict = (
                f'the fitted slope and the published growth rate '
                f'agree to {rel * 100:.1f} percent, inside the '
                f'{tol * 100:.0f} percent tolerance — two '
                f'independent paths landing on one number')
        else:
            verdict = (
                f'DISAGREEMENT IS A FINDING: the fitted slope and '
                f'the published growth rate differ by '
                f'{rel * 100:.1f} percent, beyond the '
                f'{tol * 100:.0f} percent tolerance. Something '
                f'about the window, the ingest or the published '
                f'definition is different — name it. Do NOT '
                f'average the two numbers away')
        return {
            'ok': True,
            'agree': agree,
            'fitted': fitted,
            'source': source,
            'relativeDifference': rel,
            'tolerance': tol,
            'verdict': verdict,
        }
    except Exception as exc:
        return _refuse(
            f'velocity comparison failed internally: {exc}')
