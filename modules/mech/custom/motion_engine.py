"""
@module mech.custom.motion_engine

THE 1-DOF engine of Polari's mech module (MECH_FREECAD_INTERCHANGE_PLAN §3.5,
§9.1, D-mxc-4, D-mxc-11). One integrator, linear AND rotary, with nothing
of any consumer inside it: the drawer (mxc-4), the M1 printer axis (mxc-8)
and the clock rotor (mxc-7) each hand it a `model` dict and a `drive`.

    M·q̈ = F_drive − F_friction(μ, N, sign q̇) − c·q̇ − F_detent(q) − F_load − F_gravity

HONESTY — what this is and is not
- A rigid body with ONE degree of freedom. No compliance, no backlash
  dynamics (yet), no contact stiffness: a joint limit is an inelastic hard
  stop (velocity → 0, `at_limit` set). No 3-D reactions: the lateral load
  (`side_force`) and the cantilever moment (`tip_moment_nm`) are reported
  from the model's own functions, they do not feed back into the motion.
- Friction is Coulomb with distinct static / kinetic levels and a
  STICK/SLIP treatment (Karnopp-style):
    * stuck (|q̇| = 0): the body stays stuck while |F_net| ≤ F_s = μ_s·N and
      the friction force exactly cancels F_net; it breaks away when
      |F_net| > F_s, then kinetic friction F_k = μ_k·N opposes the motion;
    * sliding: F_k opposes sign(q̇); if the step would carry q̇ through
      zero the body is stopped EXACTLY at the zero crossing (q advanced by
      the stopping distance) and re-enters the stick test next step.
  The normal force may depend on position (`friction.normal_fn`) — a drawer
  on fixed runners binds harder the further it is out.
- Integration is velocity-Verlet (q += q̇·dt + ½q̈·dt², q̇ += q̈·dt) with the
  acceleration taken at the start of the step; it is exact for a constant
  net force, which is what the hand-computed selftests pin (x = ½(F/m)t² to
  1e-6). The viscous term is therefore explicit — keep c·dt/M ≪ 1.
- Units: a linear joint integrates in SI metres internally and reports
  `q` in mm (FreeCAD's unit, and the joint's limits_json unit); a rotary
  joint works in rad throughout. Forces are N, torques N·m, time s.
- The drive formula is parsed by a tiny SAFE evaluator (no eval) that
  accepts exactly what FreeCAD's Motion Formula accepts: `time`, + - * /
  ^, parentheses, sin, cos (plus tan, sqrt, abs, exp, pi) — and REFUSES
  min / max by name, because FreeCAD silently produces 0 frames for them
  (verified on econ, 2026-11-03). So a formula that runs here exports.

@consumers mech.custom.motion_runs (drawer), motors M1 (mxc-8), motors/gears clock rotor (mxc-7)
"""
import math

ENGINE_VERSION = 'mech.motion_engine 1'

#: Velocity below which the body is treated as at rest for the stick test.
V_EPS = 1e-9

# ---------------------------------------------------------------------------
# Formula evaluator — FreeCAD Motion Formula syntax, no eval.
# ---------------------------------------------------------------------------
_FUNCS = {
    'sin': math.sin, 'cos': math.cos, 'tan': math.tan,
    'sqrt': math.sqrt, 'abs': abs, 'exp': math.exp,
}
_REFUSED = ('min', 'max', 'clamp', 'if')


class FormulaError(ValueError):
    """A formula FreeCAD's Motion object (and therefore this engine) refuses."""


def _tokenize(text):
    out, i, n = [], 0, len(text)
    while i < n:
        ch = text[i]
        if ch.isspace():
            i += 1
        elif ch.isdigit() or ch == '.':
            j = i
            while j < n and (text[j].isdigit() or text[j] in '.eE'
                             or (text[j] in '+-' and text[j - 1] in 'eE')):
                j += 1
            out.append(('num', float(text[i:j])))
            i = j
        elif ch.isalpha() or ch == '_':
            j = i
            while j < n and (text[j].isalnum() or text[j] == '_'):
                j += 1
            out.append(('id', text[i:j]))
            i = j
        elif ch in '+-*/^(),':
            out.append((ch, ch))
            i += 1
        else:
            raise FormulaError(f'unexpected character {ch!r} in formula {text!r}')
    return out


class _Parser:
    def __init__(self, text):
        self.text = text
        self.toks = _tokenize(text)
        self.pos = 0

    def peek(self):
        return self.toks[self.pos] if self.pos < len(self.toks) else (None, None)

    def take(self, kind=None):
        tok = self.peek()
        if kind is not None and tok[0] != kind:
            raise FormulaError(f'expected {kind!r} in formula {self.text!r}')
        self.pos += 1
        return tok

    def parse(self):
        fn = self.expr()
        if self.peek()[0] is not None:
            raise FormulaError(f'trailing input in formula {self.text!r}')
        return fn

    def expr(self):
        fn = self.term()
        while self.peek()[0] in ('+', '-'):
            op = self.take()[0]
            rhs = self.term()
            lhs = fn
            fn = ((lambda t, a=lhs, b=rhs: a(t) + b(t)) if op == '+'
                  else (lambda t, a=lhs, b=rhs: a(t) - b(t)))
        return fn

    def term(self):
        fn = self.power()
        while self.peek()[0] in ('*', '/'):
            op = self.take()[0]
            rhs = self.power()
            lhs = fn
            fn = ((lambda t, a=lhs, b=rhs: a(t) * b(t)) if op == '*'
                  else (lambda t, a=lhs, b=rhs: a(t) / b(t)))
        return fn

    def power(self):
        base = self.unary()
        if self.peek()[0] == '^':
            self.take()
            exp = self.power()          # right-associative
            return lambda t, a=base, b=exp: a(t) ** b(t)
        return base

    def unary(self):
        if self.peek()[0] == '-':
            self.take()
            inner = self.unary()
            return lambda t, a=inner: -a(t)
        if self.peek()[0] == '+':
            self.take()
            return self.unary()
        return self.atom()

    def atom(self):
        kind, val = self.peek()
        if kind == 'num':
            self.take()
            return lambda t, v=val: v
        if kind == '(':
            self.take()
            inner = self.expr()
            self.take(')')
            return inner
        if kind == 'id':
            self.take()
            if val == 'time':
                return lambda t: t
            if val == 'pi':
                return lambda t: math.pi
            if val in _REFUSED:
                raise FormulaError(
                    f'{val}() is not in FreeCAD\'s Motion formula language '
                    f'(FreeCAD gives 0 frames, no error) — express the stop as '
                    f'a joint limit, not a formula clamp: {self.text!r}')
            if val in _FUNCS:
                self.take('(')
                arg = self.expr()
                self.take(')')
                return lambda t, f=_FUNCS[val], a=arg: f(a(t))
            raise FormulaError(f'unknown identifier {val!r} in formula {self.text!r}')
        raise FormulaError(f'unexpected token {val!r} in formula {self.text!r}')


def parse_formula(text):
    """Compile a FreeCAD Motion formula of `time` into a callable f(t).
    Raises FormulaError for anything FreeCAD would refuse."""
    text = (text or '').strip()
    if not text:
        raise FormulaError('empty formula')
    return _Parser(text).parse()


# ---------------------------------------------------------------------------
# Model helpers
# ---------------------------------------------------------------------------
def _scale(model):
    """Internal SI unit per reported unit: 1e-3 (mm → m) or 1 (rad)."""
    return 1e-3 if model.get('coord', 'linear') == 'linear' else 1.0


def _const_or_fn(model, key, q_units, default=0.0):
    fn = model.get(key + '_fn')
    if callable(fn):
        return float(fn(q_units))
    return float(model.get(key, default) or 0.0)


def _coulomb(model, q_units):
    """(F_static_max, F_kinetic, normal) at position q (reported units).
    friction = {mu_s, mu_k, normal | torque | normal_fn} or {static, kinetic}."""
    fr = model.get('friction') or {}
    if 'static' in fr or 'kinetic' in fr:
        fs = float(fr.get('static', fr.get('kinetic', 0.0)) or 0.0)
        fk = float(fr.get('kinetic', fs) or 0.0)
        return fs, fk, float(fr.get('normal', 0.0) or 0.0)
    normal_fn = fr.get('normal_fn')
    if callable(normal_fn):
        normal = float(normal_fn(q_units))
    else:
        normal = float(fr.get('normal', fr.get('torque', 0.0)) or 0.0)
    mu_k = float(fr.get('mu_k', 0.0) or 0.0)
    mu_s = float(fr.get('mu_s', mu_k) or 0.0)
    return mu_s * normal, mu_k * normal, normal


def _detent(model, q_si, scale):
    """Restoring force of a detent at `position` (default: the lower limit)
    that holds with `force` and decays linearly to zero over `width`
    (reported units). Positive = opposes leaving the detent."""
    d = model.get('detent')
    if not d:
        return 0.0
    force = float(d.get('force', 0.0) or 0.0)
    width = float(d.get('width', 0.0) or 0.0) * scale
    lo, _ = _limits(model, scale)
    pos = d.get('position')
    pos = (float(pos) * scale) if pos is not None else (lo if lo is not None else 0.0)
    if width <= 0 or force <= 0:
        return 0.0
    dq = q_si - pos
    if 0.0 <= dq < width:
        return force * (1.0 - dq / width)
    return 0.0


def _limits(model, scale):
    lim = model.get('limits') or (None, None)
    lo = None if lim[0] is None else float(lim[0]) * scale
    hi = None if lim[1] is None else float(lim[1]) * scale
    return lo, hi


def _drive_fn(drive, scale):
    """Normalise a drive spec to (kind, f(t) in SI units of its kind)."""
    kind = (drive or {}).get('kind', 'force')
    if kind not in ('position', 'velocity', 'force'):
        raise ValueError(f'unknown drive kind {kind!r}')
    formula = (drive or {}).get('formula', '')
    if kind == 'force':
        if formula:
            g = parse_formula(formula)
            return kind, g
        val = float((drive or {}).get('value', 0.0) or 0.0)
        return kind, (lambda t, v=val: v)
    g = parse_formula(formula)
    units = (drive or {}).get('units', '')
    # FreeCAD's Angular motion formula is in degrees; rotary callers may
    # say units='rad'. Linear formulas are mm (FreeCAD) unless units='m'.
    if units == 'deg' or (scale == 1.0 and units != 'rad'):
        k = math.pi / 180.0
    elif units == 'm':
        k = 1.0
    else:
        k = scale
    return kind, (lambda t, f=g, kk=k: f(t) * kk)


# ---------------------------------------------------------------------------
# The integrator
# ---------------------------------------------------------------------------
def integrate(model, drive, t_end, dt, record_dt=None):
    """Integrate the 1-DOF model under `drive` from t = 0 to t_end.

    model (dict):
      coord          'linear' | 'rotary'
      inertia        kg | kg·m²
      limits         (min, max) in mm | rad; None = unbounded
      friction       {mu_s, mu_k, normal (N) | torque (N·m) | normal_fn(q)}
                     or {static, kinetic} (levels given directly)
      viscous_c      N·s/m | N·m·s/rad
      detent         {force, width[, position]} optional
      load           constant opposing force / torque (N | N·m)
      gravity_component  signed constant subtracted from the drive (N | N·m)
      side_force / side_force_fn(q)    reported (N)
      tip_moment_fn(q)                 reported (N·m)
      q0, v0         initial state (reported units)
    drive (dict):
      {kind: 'force', value: F} | {kind: 'force', formula: 'F(time)'}
      {kind: 'position', formula: 'q(time)'}   mm (deg for rotary; units='rad')
      {kind: 'velocity', formula: 'v(time)'}   mm/s (deg/s for rotary)
    Returns {'steps': [per-step dicts in the MechMotionSimState field names],
             'coord', 'units', 'summary', 'engine_version', 'dt'}.
    """
    coord = model.get('coord', 'linear')
    scale = _scale(model)
    M = float(model.get('inertia', 0.0) or 0.0)
    if M <= 0:
        raise ValueError('model.inertia must be > 0')
    c = float(model.get('viscous_c', 0.0) or 0.0)
    load = float(model.get('load', 0.0) or 0.0)
    grav = float(model.get('gravity_component', 0.0) or 0.0)
    lo, hi = _limits(model, scale)
    kind, f = _drive_fn(drive, scale)
    record_dt = record_dt or dt
    n_steps = int(round(t_end / dt))
    rec_every = max(1, int(round(record_dt / dt)))

    q = float(model.get('q0', 0.0) or 0.0) * scale
    v = float(model.get('v0', 0.0) or 0.0)
    if lo is not None and q < lo:
        q = lo
    if hi is not None and q > hi:
        q = hi

    steps = []
    at_limit_first_t = None
    stuck_now = False

    def clamp(qq, vv):
        hit = False
        if hi is not None and qq >= hi:
            if qq > hi or vv > 0:
                hit = qq > hi or vv > 0
            qq, vv = hi, (0.0 if vv > 0 else vv)
        if lo is not None and qq <= lo:
            if qq < lo or vv < 0:
                hit = True
            qq, vv = lo, (0.0 if vv < 0 else vv)
        return qq, vv, hit

    def record(i, t, q, v, a, F_drive, F_fric, normal, hit):
        q_units = q / scale
        steps.append({
            'step': len(steps), 't_s': t, 'q': q_units, 'q_dot': v / scale,
            'q_ddot': a / scale, 'drive': F_drive, 'friction': F_fric,
            'normal': normal,
            'side_force': _const_or_fn(model, 'side_force', q_units),
            'tip_moment_nm': _const_or_fn(model, 'tip_moment', q_units),
            'power_w': F_drive * v, 'at_limit': bool(hit),
        })

    h = dt
    for i in range(n_steps + 1):
        t = i * dt
        q_units = q / scale
        Fs, Fk, normal = _coulomb(model, q_units)
        F_det = _detent(model, q, scale)
        hit = False

        if kind == 'force':
            F_drive = float(f(t))
            F_ext = F_drive - load - grav - c * v - F_det
            if abs(v) < V_EPS:
                v = 0.0
                if abs(F_ext) <= Fs:
                    F_fric, a = -F_ext, 0.0
                    stuck_now = True
                else:
                    F_fric = -math.copysign(Fk, F_ext)
                    a = (F_ext + F_fric) / M
                    stuck_now = False
            else:
                F_fric = -math.copysign(Fk, v)
                a = (F_ext + F_fric) / M
                stuck_now = False
            # Hard stop: a body resting on a limit cannot accelerate into it.
            if hi is not None and q >= hi and a > 0 and v <= 0:
                a, F_fric, hit = 0.0, -F_ext, True
            if lo is not None and q <= lo and a < 0 and v >= 0:
                a, F_fric, hit = 0.0, -F_ext, True
            if i % rec_every == 0:
                record(i, t, q, v, a, F_drive, F_fric, normal, hit)
            if i == n_steps:
                break
            # velocity-Verlet step with an exact stop at a friction zero crossing
            v_new = v + a * h
            if v != 0.0 and (v_new == 0.0 or (v_new > 0) != (v > 0)):
                t_stop = -v / a if a != 0 else 0.0
                q = q + v * t_stop + 0.5 * a * t_stop * t_stop
                v = 0.0
            else:
                q = q + v * h + 0.5 * a * h * h
                v = v_new
            q, v, _hit2 = clamp(q, v)
            if _hit2 and at_limit_first_t is None:
                at_limit_first_t = t + h
        else:
            # Kinematic drive: q(t) (or ∫v dt) is prescribed; the engine
            # reports the force REQUIRED to follow it (inverse dynamics).
            if kind == 'position':
                def qp(tt):
                    qq = float(f(max(tt, 0.0)))
                    qq2, _, _ = clamp(qq, 0.0)
                    return qq2
                q_prev = qp(t - h) if t - h >= 0 else qp(0.0)
                q_here = qp(t)
                q_next = qp(t + h)
                v = (q_next - q_prev) / (2 * h)
                a = (q_next - 2 * q_here + q_prev) / (h * h)
                hit = (hi is not None and float(f(t)) >= hi) or (lo is not None and float(f(t)) <= lo)
                q = q_here
            else:   # velocity
                v_here = float(f(t))
                a = (float(f(t + h)) - (float(f(t - h)) if t - h >= 0 else v_here)) / (2 * h if t - h >= 0 else h)
                q_next = q + v_here * h
                q_next, v_c, hit = clamp(q_next, v_here)
                v = v_c if hit else v_here
            if abs(v) < V_EPS:
                F_fric = 0.0
                F_drive = load + grav + F_det + M * a
                if abs(F_drive) <= Fs:
                    F_fric, F_drive = -F_drive, 0.0
                else:
                    F_drive = F_drive + math.copysign(Fk, F_drive)
                    F_fric = -math.copysign(Fk, F_drive)
            else:
                F_fric = -math.copysign(Fk, v)
                F_drive = M * a - F_fric + c * v + F_det + load + grav
            if hit and at_limit_first_t is None:
                at_limit_first_t = t
            if i % rec_every == 0:
                record(i, t, q, v, a, F_drive, F_fric, normal, hit)
            if i == n_steps:
                break
            if kind == 'velocity':
                q = q_next

    qs = [s['q'] for s in steps]
    units = ({'q': 'mm', 'q_dot': 'mm/s', 'q_ddot': 'mm/s2', 'drive': 'N',
              'friction': 'N', 'normal': 'N', 'side_force': 'N',
              'tip_moment_nm': 'N·m', 'power_w': 'W'} if coord == 'linear' else
             {'q': 'rad', 'q_dot': 'rad/s', 'q_ddot': 'rad/s2', 'drive': 'N·m',
              'friction': 'N·m', 'normal': 'N·m', 'side_force': 'N',
              'tip_moment_nm': 'N·m', 'power_w': 'W'})
    summary = {
        'q_max': max(qs) if qs else None,
        'q_min': min(qs) if qs else None,
        'q_end': qs[-1] if qs else None,
        'peak_drive': max((abs(s['drive']) for s in steps), default=0.0),
        'peak_speed': max((abs(s['q_dot']) for s in steps), default=0.0),
        'at_limit_first_t_s': at_limit_first_t,
        'stuck_at_end': bool(stuck_now) if kind == 'force' else None,
        'n_recorded': len(steps),
    }
    return {'steps': steps, 'coord': coord, 'units': units, 'summary': summary,
            'engine_version': ENGINE_VERSION, 'dt': dt, 'record_dt': record_dt,
            'drive_kind': kind}


# ---------------------------------------------------------------------------
# Derived helpers every consumer needs
# ---------------------------------------------------------------------------
def time_to_reach(result, target):
    """First recorded time at which q ≥ target (reported units), else None."""
    for s in result['steps']:
        if s['q'] >= target - 1e-9:
            return s['t_s']
    return None


def peak_jerk(result):
    """Peak |d(q̈)/dt| over the RECORDED grid, in reported units/s³, every
    pair included (transitions too). jerk_profile() is the 'smooth' number."""
    return jerk_profile(result)['peak_all']


def jerk_profile(result):
    """Jerk = Δq̈/Δt on the RECORDED grid, split into what the drive's
    discontinuities cause and what the motion itself does — the 'smooth'
    check reads `peak` (the motion), the note reports the rest:
      peak           peak jerk over the SLIDING phase only: both samples
                     moving (|q̇| > 0), neither on a hard stop
      start_jerk     the first grid pair (a step force at t = 0, or the
                     impulsive start of a formula such as '100*time')
      breakaway_jerk largest jerk across a rest → moving pair (static
                     friction letting go: q̈ jumps from 0 to (F − μ_k N)/M)
      stop_jerk      largest jerk into a hard stop / a stop by friction
      peak_all       the old definition, every pair
    A step force is the INPUT's discontinuity, not drawer motion quality,
    so it is excluded from `peak` by construction and still stated."""
    st = result['steps']
    out = {'peak': 0.0, 'peak_t': None, 'start_jerk': 0.0, 'breakaway_jerk': 0.0,
           'stop_jerk': 0.0, 'peak_all': 0.0, 'sliding_pairs': 0}
    for i, (a, b) in enumerate(zip(st, st[1:])):
        dtt = b['t_s'] - a['t_s']
        if dtt <= 0:
            continue
        j = abs(b['q_ddot'] - a['q_ddot']) / dtt
        out['peak_all'] = max(out['peak_all'], j)
        a_rest, b_rest = abs(a['q_dot']) < V_EPS, abs(b['q_dot']) < V_EPS
        if i == 0:
            out['start_jerk'] = j
        if a_rest and not b_rest:
            out['breakaway_jerk'] = max(out['breakaway_jerk'], j)
        if (b_rest and not a_rest) or a['at_limit'] or b['at_limit']:
            out['stop_jerk'] = max(out['stop_jerk'], j)
        if i > 0 and not a_rest and not b_rest and not a['at_limit'] and not b['at_limit']:
            out['sliding_pairs'] += 1
            if j > out['peak']:
                out['peak'], out['peak_t'] = j, b['t_s']
    return out


def required_drive(model, profile, t_end, dt, record_dt=None):
    """Inverse dynamics: the force (torque) needed to follow a position
    profile — the hand-effort number for a prescribed opening. `profile` is
    a FreeCAD-syntax position formula or a position/velocity drive dict.
    Returns {peak, peak_t, peak_after_start, mean, samples [(t, F)], result}.
    `peak_after_start` skips the first two samples, where a formula that
    starts with a velocity step (e.g. '100*time') has its impulsive start."""
    drive = profile if isinstance(profile, dict) else {'kind': 'position', 'formula': profile}
    res = integrate(model, drive, t_end, dt, record_dt)
    samples = [(s['t_s'], s['drive']) for s in res['steps']]
    peak_i = max(range(len(samples)), key=lambda i: abs(samples[i][1])) if samples else None
    later = samples[2:] if len(samples) > 2 else samples
    return {
        'peak': abs(samples[peak_i][1]) if samples else 0.0,
        'peak_t': samples[peak_i][0] if samples else None,
        'peak_after_start': max((abs(v) for _, v in later), default=0.0),
        'mean': (sum(abs(v) for _, v in samples) / len(samples)) if samples else 0.0,
        'samples': samples, 'result': res,
    }


def minimum_constant_drive(model, target, t_end, dt, upper=1000.0, tol=1e-3):
    """Smallest constant drive (N | N·m) that carries q from its start to
    `target` within t_end — bisection on integrate(). Returns (F, t_reach)
    or (None, None) when even `upper` does not reach it."""
    def reaches(F):
        res = integrate(model, {'kind': 'force', 'value': F}, t_end, dt)
        return time_to_reach(res, target)
    if reaches(upper) is None:
        return None, None
    lo_f, hi_f = 0.0, upper
    while hi_f - lo_f > tol:
        mid = 0.5 * (lo_f + hi_f)
        if reaches(mid) is None:
            lo_f = mid
        else:
            hi_f = mid
    return hi_f, reaches(hi_f)


def quasi_static_pull(model, q_from=None, q_to=None, n=251):
    """The HAND-EFFORT number: the drive needed to move the body SLOWLY
    (no inertia) over [q_from, q_to] — the breakaway at the start
    (μ_s·N(q0) + detent + load + gravity) and the kinetic level μ_k·N(q)
    + c·0 + load + gravity sampled along the travel. The slowest pull is
    the hardest when the normal force grows with extension (a fixed
    runner), whereas a constant dynamic pull can coast past it on momentum —
    so this, not minimum_constant_drive, is what a hand feels.
    Returns {breakaway, peak_sliding, at_q, peak, samples [(q, F)]}."""
    scale = _scale(model)
    lo, hi = _limits(model, scale)
    q0 = float(q_from) if q_from is not None else (lo / scale if lo is not None else 0.0)
    q1 = float(q_to) if q_to is not None else (hi / scale if hi is not None else q0)
    load = float(model.get('load', 0.0) or 0.0) + float(model.get('gravity_component', 0.0) or 0.0)
    Fs0, _, _ = _coulomb(model, q0)
    breakaway = Fs0 + _detent(model, q0 * scale, scale) + load
    samples, peak_sliding, at_q, peak_friction = [], 0.0, q0, 0.0
    for i in range(n):
        q = q0 + (q1 - q0) * i / max(n - 1, 1)
        _, Fk, _ = _coulomb(model, q)
        F = Fk + _detent(model, q * scale, scale) + load
        samples.append((q, F))
        peak_friction = max(peak_friction, Fk)
        if F > peak_sliding:
            peak_sliding, at_q = F, q
    # peak_sliding includes the detent and load along the travel;
    # peak_friction is the kinetic friction level alone.
    return {'breakaway': breakaway, 'peak_sliding': peak_sliding, 'at_q': at_q,
            'peak_friction': peak_friction, 'peak': max(breakaway, peak_sliding),
            'samples': samples}


def reflected_inertia(J_list, ratios):
    """Inertia seen at the INPUT shaft of a train. J_list[0] sits on the
    input shaft; J_list[k] on the shaft after stage k; ratios[k] is stage
    k's speed reduction (ω_in / ω_out, > 1 for a reduction). A body behind
    a 12:1 reduction is felt 1/144 as large:
        J_ref = J_0 + Σ_k J_k / (Π_{i≤k} r_i)²
    (gears' solve_train stays the ratio authority — pass its ratios here.)"""
    J_list = list(J_list)
    ratios = list(ratios)
    if len(J_list) != len(ratios) + 1:
        raise ValueError('J_list needs one entry more than ratios (input shaft first)')
    total = float(J_list[0])
    cum = 1.0
    for k, r in enumerate(ratios):
        cum *= float(r)
        total += float(J_list[k + 1]) / (cum * cum)
    return total
