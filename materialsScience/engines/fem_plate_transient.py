"""
@cross-cutting
@module materialsScience.engines.fem_plate_transient

The thin plate of fem_plate_thermal OVER TIME - the same discrete plate (fem_plate_thermal._build: the mesh, the stiffness
+ face-loss matrix A, one load vector per source), plus its heat capacity. The textbook transient fin equation:

    C dtheta/dt - div( K grad(theta) ) + 2 h theta = q''(t)      on the plate, edges insulated, theta(0) = 0
    C = the plate's heat capacity per unit area, sum rho_i c_i t_i (J/m2K): the base sheet, plus regions ('add_c_sheet')
        and lines ('c_line' = rho c A, J/(m K)) where they lie

Time stepping is BACKWARD (implicit) EULER - the standard unconditionally stable scheme for the heat equation:

    (M/dt + A) theta_n = (M/dt) theta_{n-1} + sum_s P_s(t_n) b_s

with M the consistent mass matrix of C. Its error is first order in dt, so the step grows from small to large: within
each stretch between two switching instants the step starts at dt0 and doubles every PER_BLOCK steps (a factorisation
is reused for every step of the same length). Every switching instant of every source is a step boundary, so the power
is constant inside each step.

Power over time per source: 'power_w' while on; 'on_s' = 0 -> on for the whole run; 'on_s' > 0 and 'period_s' = 0 -> one
pulse of on_s; 'period_s' > 0 -> on for on_s at the start of every period (a duty cycle on_s / period_s).

Checks on every run, like the steady solver's:
  - ENERGY: what went in = what is stored (integral of C theta) + what left the faces (integrated over time). With
    backward Euler and P1 elements this holds to solver precision (the constant function is in the space), so it is a
    true check of the assembly, reported as balanceError.
  - LONG-TIME LIMIT: a source left on approaches the steady solve (steadyMaxRise is returned beside it).
"""
from materialsScience.engines.fem_plate_thermal import _build, _lost_w, _per_source, _map

PER_BLOCK = 8
BLOCKS = 10
MAX_STEPS = 20000


def power_at(src, t):
    """The source's power (W) at time t (s)."""
    p, on, period = float(src['power_w']), float(src.get('on_s') or 0), float(src.get('period_s') or 0)
    if on <= 0:
        return p
    if period > 0:
        return p if (t % period) < on else 0.0
    return p if t < on else 0.0


def switching_times(sources, t_end):
    """Every instant some source switches on or off inside (0, t_end)."""
    out = set()
    for s in sources:
        on, period = float(s.get('on_s') or 0), float(s.get('period_s') or 0)
        if on <= 0:
            continue
        if period <= 0:
            out.add(on)
            continue
        k = 0
        while k * period < t_end:
            out.update((k * period, k * period + on))
            k += 1
            if len(out) > MAX_STEPS:
                break
    return sorted(t for t in out if 0 < t < t_end)


def time_grid(t_end, breaks):
    """Step boundaries: each stretch between switching instants starts at dt0 and doubles every PER_BLOCK steps."""
    dt0 = t_end / (PER_BLOCK * (2 ** BLOCKS - 1))
    times = [0.0]
    for a, b in zip([0.0] + breaks, breaks + [t_end]):
        t, dt, k = a, dt0, 0
        while t < b - 1e-12 * t_end:
            step = min(dt, b - t)
            if b - (t + step) < 0.25 * dt:  # no sliver step at the end of a stretch
                step = b - t
            t += step
            times.append(t)
            k += 1
            if k % PER_BLOCK == 0:
                dt *= 2
            if len(times) > MAX_STEPS:
                return times, dt0
    return times, dt0


def solve_plate_transient_2d(width, height, base_k_sheet, base_c_sheet, h, t_end, sources=(), regions=(), lines=(), outline=None, holes=(),
                             refine=6, grid=(24, 0)):
    """Temperature rise of the plate over (0, t_end] s for sources switched as their on_s / period_s say.

    Returns {'ok', 'times', 'maxRise' (per time), 'sources': [{name, power_w, on_s, period_s, meanRise: per time, peakMeanRise, peakAt}],
    'powers': {name: per time}, 'peakRise', 'peakAt', 'finalMap', 'peakMap', 'steadyMaxRise', 'inputJ', 'storedJ', 'lostJ', 'balanceError',
    'plateTimeConstant', 'steps', 'factorisations', 'dt0', 'dofs', 'notes'} or {'ok': False, 'error'}.
    """
    if base_c_sheet <= 0:
        return {'ok': False, 'error': 'the plate needs a heat capacity per area > 0 J/(m2 K), got %r' % base_c_sheet}
    if not t_end or t_end <= 0:
        return {'ok': False, 'error': 'the run needs a length t_end > 0 s, got %r' % t_end}
    for s in sources:
        if float(s.get('on_s') or 0) < 0 or float(s.get('period_s') or 0) < 0:
            return {'ok': False, 'error': 'source %r: on_s and period_s must be >= 0' % s.get('name')}
        if float(s.get('period_s') or 0) > 0 and not float(s.get('on_s') or 0) > 0:
            return {'ok': False, 'error': 'source %r: a period needs an on time (on_s > 0)' % s.get('name')}
    breaks = switching_times(sources, t_end)
    times, dt0 = time_grid(t_end, breaks)
    if len(times) > MAX_STEPS:
        return {'ok': False, 'error': 'more than %d time steps (%d switching instants in %g s) - shorten the run or lengthen the period'
                                      % (MAX_STEPS, len(breaks), t_end)}
    b = _build(width, height, base_k_sheet, h, sources, regions, lines, outline, holes, refine, base_c_sheet=base_c_sheet)
    if not b.get('ok'):
        return b

    import numpy as np
    from scipy.sparse.linalg import splu
    from skfem import solve
    A, M, mesh, areas = b['A'].tocsc(), b['M'].tocsc(), b['mesh'], b['areas']
    ones = np.ones(A.shape[0])
    c_row = M.T @ ones                     # stored energy = c_row . theta
    lost_row = (b['A'].T @ ones)           # the stiffness part sums to zero on a constant: 1^T A theta = integral of 2 h theta
    names = [s.get('name', '') for s in sources]
    avg = []                               # the mean rise over a source's own area as a row vector on the nodes (P1: element mean = nodal mean)
    for inside in b['covered']:
        w = np.zeros(A.shape[0])
        np.add.at(w, mesh.t[:, inside].ravel(), np.repeat(areas[inside] / 3.0, 3))
        avg.append(w / areas[inside].sum())

    lus, theta = {}, np.zeros(A.shape[0])
    rec_t, rec_max = [0.0], [0.0]
    rec_src = [[0.0] for _ in sources]
    rec_p = [[0.0] for _ in sources]
    lost_j = input_j = 0.0
    peak, peak_at, peak_theta = 0.0, 0.0, theta.copy()
    for n in range(1, len(times)):
        t0, t1 = times[n - 1], times[n]
        dt = t1 - t0
        key = float('%.9g' % dt)
        if key not in lus:
            lus[key] = splu((M / dt + A).tocsc())
        ps = [power_at(s, 0.5 * (t0 + t1)) for s in sources]
        rhs = (M @ theta) / dt + sum((p * ld for p, ld in zip(ps, b['loads'])), np.zeros(A.shape[0]))
        theta = lus[key].solve(rhs)
        lost_j += dt * float(lost_row @ theta)
        input_j += dt * sum(ps)
        mx = float(theta.max())
        rec_t.append(t1)
        rec_max.append(mx)
        for i, p in enumerate(ps):
            rec_src[i].append(float(avg[i] @ theta))
            rec_p[i].append(p)
        if mx > peak:
            peak, peak_at, peak_theta = mx, t1, theta.copy()

    stored_j = float(c_row @ theta)
    on_powers = [float(s['power_w']) for s in sources]
    steady = solve(b['A'], sum((p * ld for p, ld in zip(on_powers, b['loads'])), np.zeros(A.shape[0])))
    plate_area = float(areas.sum())
    c_mean = float(np.sum(b['c_elem'] * areas) / plate_area)
    out_src = []
    for i, s in enumerate(sources):
        k = int(np.argmax(rec_src[i]))
        out_src.append({'name': names[i], 'power_w': on_powers[i], 'on_s': float(s.get('on_s') or 0), 'period_s': float(s.get('period_s') or 0),
                        'meanRise': rec_src[i], 'peakMeanRise': rec_src[i][k], 'peakAt': rec_t[k]})
    return {
        'ok': True, 'times': rec_t, 'maxRise': rec_max, 'sources': out_src, 'powers': {names[i]: rec_p[i] for i in range(len(sources))},
        'peakRise': peak, 'peakAt': peak_at, 'finalMap': _map(b, theta, grid), 'peakMap': _map(b, peak_theta, grid),
        'finalSources': _per_source(b, theta, on_powers, names),
        'steadyMaxRise': float(steady.max()), 'inputJ': input_j, 'storedJ': stored_j, 'lostJ': lost_j,
        'balanceError': abs(stored_j + lost_j - input_j) / input_j if input_j > 0 else 0.0,
        'plateTimeConstant': c_mean / (2.0 * h), 'steps': len(rec_t) - 1, 'factorisations': len(lus), 'dt0': dt0,
        'dofs': int(A.shape[0]), 'lostFinalW': _lost_w(b, theta),
        'notes': ('transient thin-plate fin equation by backward Euler (first order in dt; the step starts at %.3g s and doubles every %d steps '
                  'between switching instants); C = rho c t per area, mean %.4g J/(m2 K); the plate\'s own time constant C/(2h) = %.4g s'
                  % (dt0, PER_BLOCK, c_mean, c_mean / (2.0 * h))),
    }
