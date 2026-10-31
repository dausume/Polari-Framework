"""
@module pcb.custom.esd_iec

esd-4 (AI-Notes/plans/DRIVERS_AND_ESD_PLAN.md): IEC 61000-4-2'S OWN CONTACT DISCHARGE CURRENT - the equation under Figure 2 of the 2008 edition (§6.2),
scaled linearly with the level, and its PWL samples for ngspice (pcb.custom.esd_events re-exports these).

  iec_current(t, level_v)   the ideal current t seconds after the discharge starts
  iec_samples()             the PWL sample times (every one a solver breakpoint)
  iec_check(level_v)        Table 3's four numbers recomputed from the equation: (first peak, 10-90 % rise, I at 30 ns, I at 60 ns)
"""
import math

IEC = {'tau1': 1.1e-9, 'tau2': 2e-9, 'tau3': 12e-9, 'tau4': 37e-9, 'i1_a': 16.6, 'i2_a': 9.3, 'n': 1.8, 'at_v': 4000.0}


def iec_current(t, level_v):
    """IEC 61000-4-2:2008 §6.2: the ideal contact discharge current t seconds after it starts, scaled from 4 kV to level_v."""
    if t <= 0:
        return 0.0
    c = IEC
    n = c['n']
    k1 = math.exp(-c['tau1'] / c['tau2'] * (n * c['tau2'] / c['tau1']) ** (1 / n))
    k2 = math.exp(-c['tau3'] / c['tau4'] * (n * c['tau4'] / c['tau3']) ** (1 / n))
    a, b = (t / c['tau1']) ** n, (t / c['tau3']) ** n
    i = c['i1_a'] / k1 * a / (1 + a) * math.exp(-t / c['tau2']) + c['i2_a'] / k2 * b / (1 + b) * math.exp(-t / c['tau4'])
    return i * level_v / c['at_v']


def iec_samples():
    """The PWL sample times after the start: 50 ps to 5 ns, 250 ps to 30 ns, 2 ns to 200 ns, 10 ns to 400 ns (then 0)."""
    ts = [k * 50e-12 for k in range(1, 101)] + [5e-9 + k * 250e-12 for k in range(1, 101)] + [30e-9 + k * 2e-9 for k in range(1, 86)]
    return ts + [200e-9 + k * 10e-9 for k in range(1, 21)]


def iec_check(level_v=4000.0):
    """Table 3's four numbers recomputed from the equation: (first peak A, rise 10-90 % s, I at 30 ns A, I at 60 ns A), times from the 10 % point."""
    ts = [k * 1e-12 for k in range(1, 20001)]
    v = [iec_current(t, level_v) for t in ts]
    ip = max(v)
    t10 = next(t for t, x in zip(ts, v) if x >= 0.1 * ip)
    t90 = next(t for t, x in zip(ts, v) if x >= 0.9 * ip)
    return ip, t90 - t10, iec_current(t10 + 30e-9, level_v), iec_current(t10 + 60e-9, level_v)


def _pwl(t_event, level_v):
    pts = ['0 0', '%.12g 0' % t_event] + ['%.12g %.6g' % (t_event + t, iec_current(t, level_v)) for t in iec_samples()]
    pts.append('%.12g 0' % (t_event + 401e-9))
    lines, cur = [], 'Iesd 0 esd_m PWL('
    for p in pts:
        if len(cur) > 200:
            lines.append(cur)
            cur = '+'
        cur += ' ' + p
    return lines + [cur + ')']
