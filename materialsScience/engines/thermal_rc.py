"""
@cross-cutting
@module materialsScience.engines.thermal_rc

A part's OWN thermal behaviour over time, the way its datasheet states it: the transient thermal impedance Zth(t) from the
junction to a reference (the case, the board, the leads) given as a FOSTER network - pairs (R_i K/W, tau_i s):

    Zth(t) = sum_i R_i (1 - exp(-t / tau_i))         Zth(inf) = sum_i R_i = the steady Rth

This is the standard datasheet form (JEDEC JESD51-14 measures Zth; vendors fit it as Foster pairs - e.g. Nexperia AN11261
"Using RC Thermal models", Infineon AN2008-03 "Thermal equivalent circuit models"). Used as datasheets intend it: the
junction's rise ABOVE THE REFERENCE for a given power, by superposition (Duhamel), with the reference's own temperature
coming from elsewhere (here: the board under the part, from the plate FEM).

    junction_trajectory(stages, times, powers) - the rise above the reference at every time, for a power that is
        constant over each step (t_{n-1}, t_n]: each stage is a first-order lag, updated EXACTLY per step
            x_i(t_n) = x_i(t_{n-1}) e^(-dt/tau_i) + R_i P_n (1 - e^(-dt/tau_i))
        - no time-step error at all for piecewise-constant power, however short tau_i is.

What it does NOT do (said, never hidden): a Foster network's inner nodes are not places in the part, so it cannot be
wired INTO another network (that needs a Cauer ladder; AN2008-03). Here the coupling is one way: the board sets the
reference, the part's power heats the board as a source, and the network adds the part's own rise on top. That is exact
when the datasheet's reference is the place the board model gives (Zth junction-to-board, or to a case soldered down),
and an approximation otherwise.
"""
import math


def check_stages(stages):
    """'' when every stage is (R >= 0, tau > 0) and finite, else the reason in words."""
    for i, st in enumerate(stages or ()):
        try:
            r, tau = float(st[0]), float(st[1])
        except (TypeError, ValueError, IndexError):
            return 'stage %d is not a pair (R K/W, tau s): %r' % (i + 1, st)
        if not (math.isfinite(r) and math.isfinite(tau)) or r < 0 or tau <= 0:
            return 'stage %d needs R >= 0 K/W and tau > 0 s, got R = %r, tau = %r' % (i + 1, r, tau)
    return ''


def zth(stages, t):
    """Zth(t) in K/W - the rise above the reference per watt, t seconds after a constant power is switched on."""
    return sum(r * (1.0 - math.exp(-t / tau)) for r, tau in stages)


def rth(stages):
    """The steady junction-to-reference resistance, sum R_i (K/W)."""
    return sum(r for r, _ in stages)


def junction_trajectory(stages, times, powers):
    """Rise above the reference at times[n], for power powers[n] held over (times[n-1], times[n]] (times[0] is the start, powers[0] unused).
    Exact for piecewise-constant power (each stage a first-order lag solved in closed form)."""
    x = [0.0] * len(stages)
    out = [0.0]
    for n in range(1, len(times)):
        dt, p = times[n] - times[n - 1], powers[n]
        for i, (r, tau) in enumerate(stages):
            a = math.exp(-dt / tau)
            x[i] = x[i] * a + r * p * (1.0 - a)
        out.append(sum(x))
    return out
