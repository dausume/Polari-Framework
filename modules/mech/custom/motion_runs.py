"""
@module mech.custom.motion_runs

Runs over the 1-DOF engine (MECH_FREECAD_INTERCHANGE_PLAN §3.5, §9.1,
D-mxc-11): a MechMotionCase × MechLoadCase becomes a MechMotionRun that
RIDES core simulations — a SimulationRun of 'mech-motion-1dof' whose
MechMotionSimState rows `simulations.simulation_series.build_series`
reads, plus one MechMotionVector per signal, plus every check with its
number in report_json.

The drawer is the first consumer and its specifics live HERE, not in the
engine: the load case's masses become the normal force and the cantilever
moment about the cabinet front edge; the running gear decides who carries
that moment (a telescoping slide — in its tracks, reported against the
rating; a fixed runner — as a couple at the edge, so the friction normal
grows with extension, N(x) = W + 2·M(x)/overlap(x)).

Reproducibility (Dustin's standing rule): `inputs_sha256` fingerprints the
canonical JSON of everything the run read; a confirmation (sim | hardware
| person) is kept in confirmation_json with cmod's StructNodeConfirmation
keys and VOIDED, never deleted, by `void_if_changed` when the sha moves.

Persistence: rows are written straight into manager.objectTables (and
db.saveInstanceInDB when a db exists) — the core runner is a step-solution
executor for no-code MatrixEquation steps; this engine is Python, so the
SimulationRun is recorded as `status='complete'` with the rows landed,
exactly as seed_data records a precomputed trajectory. Nothing in core
simulations was changed.

Structural checks: `fem_model_ref` is NAMED on the run and executed by
materialsScience's fem_engine; no stress or deflection is computed here
(D-mxc-7).

@consumers mech.mech_motion_selftest, mech api (mxc-6 views), mxc-7 / mxc-8 consumers
"""
import datetime
import hashlib
import json
import math
from types import SimpleNamespace

from mech.custom.motion_engine import (
    ENGINE_VERSION, integrate, jerk_profile, minimum_constant_drive,
    quasi_static_pull, required_drive, time_to_reach,
)
from mech.mech_motion_basis import (
    MOTION_SIM_DEF, MechLoadCase, MechMotionCase, MechMotionRun,
    MechMotionSimState, MechMotionVector,
)

G = 9.80665

#: Every knob the drawer run reads, with its basis. A knob is an assumption
#: until a measured run replaces it.
DEFAULT_KNOBS = {
    'hand_effort_n': 20.0,          # a comfortable one-hand pull (knob)
    'detent_hold_n': 2.0,           # 'stays closed' threshold (knob)
    'smooth_jerk_m_s3': 500.0,      # peak jerk on the recorded grid (knob)
    'opens_tol_mm': 0.5,
    'detent': {'force': 3.0, 'width': 4.0, 'basis': 'knob — typical ball-slide self-close detent, unmeasured'},
    'default_mu': {'static': 0.03, 'kinetic': 0.02, 'basis': 'knob — ball slide 0.01–0.03 (plan §4), no contact row found'},
    'drawer_depth_mm': 300.0,       # overlap length of a fixed runner at x = 0 (knob)
    'engine_dt_s': 0.001,
    'viscous_c': 0.0,
}


# ---------------------------------------------------------------------------
# small helpers
# ---------------------------------------------------------------------------
def _j(v, default):
    if v is None or v == '':
        return default
    if isinstance(v, (dict, list)):
        return v
    try:
        return json.loads(v)
    except (TypeError, ValueError):
        return default


def _get(row, key, default=None):
    if row is None:
        return default
    if isinstance(row, dict):
        return row.get(key, default)
    return getattr(row, key, default)


def _table(manager, cls_name):
    return (getattr(manager, 'objectTables', {}) or {}).get(cls_name, {}) or {}


def _by_name(manager, cls_name, name):
    if not name:
        return None
    table = _table(manager, cls_name)
    if name in table:
        return table[name]
    return next((r for r in table.values() if _get(r, 'name') == name), None)


_SKIP_ATTRS = {'manager', 'branch', 'inTree', 'polariId', 'id'}


def row_dict(row):
    """Public, non-callable fields of a row (or dict) — the canonical view."""
    if row is None:
        return {}
    src = row if isinstance(row, dict) else vars(row)
    return {k: v for k, v in src.items()
            if not k.startswith('_') and k not in _SKIP_ATTRS and not callable(v)}


def _canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(',', ':'), default=str)


def _now():
    return datetime.datetime.now().isoformat(timespec='seconds')


def _is_real_manager(manager):
    return manager is not None and not isinstance(manager, SimpleNamespace)


def _upsert(manager, cls, fields):
    """Write one row by name into manager.objectTables[cls.__name__] (and
    the db when there is one). In-memory managers get real class instances
    without a manager; a live manager owns them."""
    cls_name = cls.__name__
    name = fields['name']
    table = manager.objectTables.setdefault(cls_name, {})
    row = table.get(name) or next((r for r in table.values() if _get(r, 'name') == name), None)
    if row is not None:
        for k, v in fields.items():
            setattr(row, k, v)
    else:
        # A live manager owns real rows; an in-memory manager (selftests)
        # gets plain rows with the same fields, as the pendulum selftest does.
        row = cls(manager=manager, **fields) if _is_real_manager(manager) else SimpleNamespace(**fields)
        table[name] = row
    db = getattr(manager, 'db', None)
    if db is not None and hasattr(db, 'saveInstanceInDB'):
        try:
            db.saveInstanceInDB(row)
        except Exception:  # noqa: BLE001 — the row stays in the tree; the db layer logs
            pass
    return row


# ---------------------------------------------------------------------------
# the load case → its resultant
# ---------------------------------------------------------------------------
def resultant(load_case, joint=None):
    """Total mass, the normal force (W) the running gear carries, and the
    moment about the joint's support (the cabinet front edge, x = 0 closed)
    as a function of extension x (mm):
        M(x) = Σ F_i · (x_i + x) / 1000     [N·m, + = cantilevering out]
    x_i from point_json.x_mm (negative = inside the cabinet). `mass` loads
    give F_i = m·g; `force` loads are taken as vertical (N); `pressure`
    loads need point_json.area_m2 and are otherwise listed as unsupported.
    Returns {total_mass_kg, total_force_n, moment_nm_closed, moment_nm_full,
    moment_fn(x_mm), items, unsupported, basis}."""
    loads = _j(_get(load_case, 'loads_json'), [])
    limits = _j(_get(joint, 'limits_json'), {}) if joint is not None else {}
    x_full = float(limits.get('length_max', 0.0) or 0.0)
    items, unsupported, mass, force = [], [], 0.0, 0.0
    for ld in loads:
        kind = ld.get('kind', 'mass')
        pt = ld.get('point_json', {}) or {}
        pt = _j(pt, {})
        x_i = float(pt.get('x_mm', 0.0) or 0.0)
        val = float(ld.get('value', 0.0) or 0.0)
        if kind == 'mass':
            f = val * G
            mass += val
        elif kind == 'force':
            f = val
        elif kind == 'pressure' and pt.get('area_m2'):
            f = val * float(pt['area_m2'])
        else:
            unsupported.append({'instance': ld.get('instance'), 'kind': kind,
                                'why': 'pressure needs point_json.area_m2'})
            continue
        force += f
        items.append({'instance': ld.get('instance'), 'kind': kind, 'value': val,
                      'force_n': f, 'x_mm': x_i, 'basis': ld.get('basis', '')})

    def moment_fn(x_mm):
        return sum(it['force_n'] * (it['x_mm'] + x_mm) for it in items) / 1000.0

    return {
        'total_mass_kg': mass, 'total_force_n': force,
        'moment_nm_closed': moment_fn(0.0), 'moment_nm_full': moment_fn(x_full),
        'moment_fn': moment_fn, 'items': items, 'unsupported': unsupported,
        'basis': 'Σ F_i (x_i + x) about the cabinet front edge; masses × g = ' + f'{G} m/s²',
    }


# ---------------------------------------------------------------------------
# resolving the assembly rows the run reads
# ---------------------------------------------------------------------------
def _find_contact(manager, motion_case):
    ref = _get(motion_case, 'contact_ref', '')
    if ref:
        return _by_name(manager, 'MechContact', ref)
    asm = _get(motion_case, 'assembly_ref', '')
    joint = _get(motion_case, 'joint_ref', '')
    cands = [r for r in _table(manager, 'MechContact').values()
             if _get(r, 'kind', '') == 'sliding' and _get(r, 'assembly_ref', asm) == asm]
    on_joint = [r for r in cands if _get(r, 'joint_ref', joint) == joint]
    cands = on_joint or cands
    return sorted(cands, key=lambda r: _get(r, 'name', ''))[0] if cands else None


_RATING_TABLES = ('MechPartInstance', 'MechPartVariant', 'MechPartFamily', 'MechPart')


def _find_slide_rating(manager, assembly_ref):
    """The slide's load_rating_json {dynamic_n, static_n, basis}, found on
    whichever catalogue / instance row of the assembly carries it."""
    for tbl in _RATING_TABLES:
        rows = sorted(_table(manager, tbl).values(), key=lambda r: _get(r, 'name', ''))
        for r in rows:
            rating = _j(_get(r, 'load_rating_json'), None)
            if rating and (_get(r, 'assembly_ref', assembly_ref) in ('', assembly_ref)):
                return rating, f"{tbl}:{_get(r, 'name', '')}"
    # mxc-1 catalogue (landed 2026-11-03): the rating sits on the slide's
    # rail FEATURE as {axial_n, shear_n, moment_nm, basis} (plan 3.2). Map
    # shear_n (the load the carriage carries) onto dynamic_n for the
    # no-bind check; static_n stays undetermined unless axial_n is given.
    variants = {_get(i, 'variant_ref', '') for i in _table(manager, 'MechPartInstance').values()
                if _get(i, 'assembly_ref', '') == assembly_ref}
    for f in sorted(_table(manager, 'MechFeature').values(), key=lambda r: _get(r, 'name', '')):
        if _get(f, 'variant_ref', '') not in variants or _get(f, 'role', '') != 'rider':
            continue
        lr = _j(_get(f, 'load_rating_json'), None) or {}
        if lr.get('shear_n') not in (None, -1):
            return ({'dynamic_n': float(lr['shear_n']),
                     'static_n': float(lr['axial_n']) if lr.get('axial_n') not in (None, -1) else -1,
                     'moment_nm': lr.get('moment_nm', -1),
                     'basis': f"{lr.get('basis', 'knob')} (MechFeature {_get(f, 'name', '')}: shear_n per slide)"},
                    f"MechFeature:{_get(f, 'name', '')}")
    return None, ''


def _assembly_rows(manager, motion_case):
    """Every row of the assembly the run's physics reads: joint, contacts,
    instances (+ the rating row). Dicts, for the sha."""
    asm = _get(motion_case, 'assembly_ref', '')
    out = {'joint': row_dict(_by_name(manager, 'MechJoint', _get(motion_case, 'joint_ref', '')))}
    out['contacts'] = sorted((row_dict(r) for r in _table(manager, 'MechContact').values()
                              if _get(r, 'assembly_ref', asm) == asm), key=lambda d: d.get('name', ''))
    out['instances'] = sorted((row_dict(r) for r in _table(manager, 'MechPartInstance').values()
                               if _get(r, 'assembly_ref', asm) == asm), key=lambda d: d.get('name', ''))
    rating, where = _find_slide_rating(manager, asm)
    out['slide_rating'] = {'rating': rating, 'row': where}
    return out


def inputs_sha256(motion_case, load_case, assembly_rows, engine_version=ENGINE_VERSION, knobs=None):
    """sha256 of the canonical JSON of everything the run READ. The load
    case's resultant_json is a computed output of the run, not an input,
    so it is left out (else every run would change its own sha)."""
    lc = row_dict(load_case)
    lc.pop('resultant_json', None)
    payload = {
        'motion_case': row_dict(motion_case), 'load_case': lc,
        'assembly': assembly_rows, 'engine_version': engine_version,
        'knobs': knobs or {},
    }
    return hashlib.sha256(_canonical(payload).encode('utf-8')).hexdigest()


def run_inputs_sha(manager, motion_case, load_case, knobs=None):
    """Exactly what run_polari fingerprints: (sha, the knob dict it hashed).
    Call it again later to see whether a run's confirmation still holds."""
    kn = dict(DEFAULT_KNOBS)
    kn.update(knobs or {})
    step_s = float(_get(motion_case, 'step_s', 0.01))
    dt = min(step_s, float(kn['engine_dt_s']))
    sha_knobs = {k: v for k, v in kn.items() if k != 'engine_dt_s'}
    sha_knobs['engine_dt_s'] = dt
    sha = inputs_sha256(motion_case, load_case, _assembly_rows(manager, motion_case),
                        ENGINE_VERSION, sha_knobs)
    return sha, sha_knobs


def confirm_run(run, by='sim', who='', words='', at=''):
    """Attach a confirmation (cmod StructNodeConfirmation keys) that holds
    for the run's CURRENT inputs_sha256."""
    conf = {'by': by, 'run': _get(run, 'name', ''), 'hex_sha256': _get(run, 'inputs_sha256', ''),
            'state': 'confirmed', 'voided_why': '', 'voided_at': '', 'who': who,
            'words': words, 'at': at or _now()}
    _set(run, 'confirmation_json', json.dumps(conf))
    return conf


def void_if_changed(run, current_sha, at=''):
    """Void the run's confirmation when the inputs sha moved. Returns the
    confirmation dict (voided or untouched), or None when there is none."""
    conf = _j(_get(run, 'confirmation_json'), {})
    if not conf:
        return None
    if conf.get('state') == 'confirmed' and conf.get('hex_sha256') != current_sha:
        conf['state'] = 'voided'
        conf['voided_at'] = at or _now()
        conf['voided_why'] = (f"inputs sha256 changed {str(conf.get('hex_sha256', ''))[:10]} → "
                              f"{str(current_sha)[:10]}")
        _set(run, 'confirmation_json', json.dumps(conf))
    return conf


def _set(row, key, value):
    if isinstance(row, dict):
        row[key] = value
    else:
        setattr(row, key, value)


# ---------------------------------------------------------------------------
# the model the drawer hands to the engine
# ---------------------------------------------------------------------------
def build_model(manager, motion_case, load_case, knobs=None):
    """Everything the engine needs, from rows + knobs. Returns (model,
    context) where context names what was resolved and every knob used."""
    kn = dict(DEFAULT_KNOBS)
    kn.update(knobs or {})
    joint = _by_name(manager, 'MechJoint', _get(motion_case, 'joint_ref', ''))
    limits = _j(_get(joint, 'limits_json'), {})
    jkind = _get(joint, 'kind', 'slider')
    rotary = jkind in ('revolute', 'cylindrical', 'gears', 'rotary')
    res = resultant(load_case, joint)
    contact = _find_contact(manager, motion_case)
    mu = _j(_get(contact, 'mu_json'), None) if contact is not None else None
    mu_basis = (mu or {}).get('basis', '') if mu else kn['default_mu']['basis']
    if not mu:
        mu = kn['default_mu']
    mu_s = float(mu.get('static', mu.get('kinetic', 0.0)) or 0.0)
    mu_k = float(mu.get('kinetic', mu_s) or 0.0)
    W = res['total_force_n']
    gear = _get(motion_case, 'running_gear', 'slide') or 'slide'
    depth = float(kn['drawer_depth_mm'])
    moment_fn = res['moment_fn']

    if gear == 'runner':
        def normal_fn(x_mm):
            overlap = max(depth - x_mm, 1.0) / 1000.0
            return W + 2.0 * max(0.0, moment_fn(x_mm)) / overlap
    else:
        def normal_fn(x_mm):
            return W

    # The detent is the slide's (self-close); a fixed runner has none.
    detent = _j(_get(joint, 'detent_json'), None) or (kn.get('detent') if gear == 'slide' else None) or None
    if rotary:
        lim = (limits.get('angle_min'), limits.get('angle_max'))
    else:
        lim = (limits.get('length_min', 0.0), limits.get('length_max'))
    model = {
        'coord': 'rotary' if rotary else 'linear',
        'inertia': res['total_mass_kg'],
        'limits': lim,
        'friction': {'mu_s': mu_s, 'mu_k': mu_k, 'normal_fn': normal_fn},
        'viscous_c': float(kn.get('viscous_c', 0.0) or 0.0),
        'detent': ({'force': float(detent.get('force', 0.0)), 'width': float(detent.get('width', 0.0))}
                   if detent else None),
        'load': 0.0,
        'gravity_component': 0.0,
        'side_force': W,
        'tip_moment_fn': moment_fn,
    }
    rating, rating_row = _find_slide_rating(manager, _get(motion_case, 'assembly_ref', ''))
    ctx = {
        'joint': _get(joint, 'name', ''), 'joint_kind': jkind, 'limits': limits,
        'contact': _get(contact, 'name', '') if contact is not None else '',
        'mu': {'static': mu_s, 'kinetic': mu_k, 'basis': mu_basis},
        'running_gear': gear, 'normal_closed_n': normal_fn(0.0),
        'normal_full_n': normal_fn(float(lim[1])) if lim[1] is not None else None,
        'resultant': {k: v for k, v in res.items() if k != 'moment_fn'},
        'detent': detent, 'slide_rating': rating, 'slide_rating_row': rating_row,
        'knobs': kn,
    }
    return model, ctx


def _drive_of(motion_case, model):
    kind = _get(motion_case, 'drive', 'position')
    formula = _get(motion_case, 'formula', '') or ''
    if kind == 'force':
        if formula:
            return {'kind': 'force', 'formula': formula}
        val = _get(motion_case, 'torque_nm', -1.0) if model['coord'] == 'rotary' else _get(motion_case, 'force_n', -1.0)
        return {'kind': 'force', 'value': float(val)}
    return {'kind': kind, 'formula': formula}


# ---------------------------------------------------------------------------
# the run
# ---------------------------------------------------------------------------
SIGNAL_FIELDS = (
    ('position_mm', 'q', 'mm'), ('velocity_mm_s', 'q_dot', 'mm/s'),
    ('accel_mm_s2', 'q_ddot', 'mm/s2'), ('pull_n', 'drive', 'N'),
    ('friction_n', 'friction', 'N'), ('normal_n', 'normal', 'N'),
    ('side_force_n', 'side_force', 'N'), ('tip_moment_nm', 'tip_moment_nm', 'N·m'),
    ('power_w', 'power_w', 'W'),
)
ROTARY_SIGNAL_FIELDS = (
    ('angle_rad', 'q', 'rad'), ('velocity_rad_s', 'q_dot', 'rad/s'),
    ('accel_rad_s2', 'q_ddot', 'rad/s2'), ('torque_nm', 'drive', 'N·m'),
    ('friction_n', 'friction', 'N·m'), ('normal_n', 'normal', 'N·m'),
    ('side_force_n', 'side_force', 'N'), ('tip_moment_nm', 'tip_moment_nm', 'N·m'),
    ('power_w', 'power_w', 'W'),
)


def _checks(motion_case, model, ctx, result, drive, duration, dt):
    """Every check named on the case, each with its number."""
    checks = _j(_get(motion_case, 'checks_json'), [])
    kn = ctx['knobs']
    lim_max = model['limits'][1]
    out = []
    for ch in checks:
        name = ch.get('name', '')
        knob = ch.get('knob')
        rec = {'name': name, 'criterion': ch.get('criterion', ''), 'knob': knob,
               'value': None, 'units': '', 'ok': False, 'note': ''}
        if name == 'opens fully':
            tol = float(kn['opens_tol_mm'])
            target = float(lim_max) if lim_max is not None else None
            rec['knob'] = target
            rec['value'] = result['summary']['q_max']
            rec['units'] = 'mm' if model['coord'] == 'linear' else 'rad'
            t_open = time_to_reach(result, target - tol) if target is not None else None
            rec['ok'] = target is not None and t_open is not None
            rec['note'] = (f'reached {target} within {t_open:.4f} s' if t_open is not None
                           else 'never reached the joint limit' if target is not None
                           else 'joint has no length_max')
            rec['t_open_s'] = t_open
        elif name == 'smooth':
            # Smoothness is a property of the MOTION, not of the drive's
            # discontinuities: the number is the peak jerk over the sliding
            # phase (both samples moving, no hard stop). The start step, the
            # static→kinetic breakaway and the stop are the input's and the
            # friction model's steps — stated in the note, never the value.
            u = 1000.0 if model['coord'] == 'linear' else 1.0
            jp = jerk_profile(result)
            jerk = jp['peak'] / u
            k = float(knob) if knob is not None else float(kn['smooth_jerk_m_s3'])
            rec.update(knob=k, value=jerk, units='m/s3' if model['coord'] == 'linear' else 'rad/s3',
                       ok=jerk < k,
                       note=(f"peak jerk over the sliding phase on the {result['record_dt']} s grid"
                             + (f" at t = {jp['peak_t']:.3f} s" if jp['peak_t'] is not None else
                                ' (no sliding phase — the body never moved freely)')
                             + f"; excluded transitions: start_jerk {jp['start_jerk'] / u:.1f}, "
                             f"breakaway_jerk {jp['breakaway_jerk'] / u:.1f}, stop_jerk {jp['stop_jerk'] / u:.1f}"
                             f" (every pair: {jp['peak_all'] / u:.1f})"))
            rec['start_jerk'] = jp['start_jerk'] / u
            rec['breakaway_jerk'] = jp['breakaway_jerk'] / u
            rec['stop_jerk'] = jp['stop_jerk'] / u
        elif name == 'no bind':
            peak_side = max((s['side_force'] for s in result['steps']), default=0.0)
            rating = ctx.get('slide_rating') or {}
            k = float(knob) if knob is not None else (float(rating.get('dynamic_n')) if rating.get('dynamic_n') else None)
            rec.update(knob=k, value=peak_side, units='N')
            if k is None:
                rec['ok'] = False
                rec['note'] = 'no slide load_rating_json found — unrated'
            else:
                rec['ok'] = peak_side < k
                rec['note'] = (f"load on the slides vs dynamic rating ({rating.get('basis', 'knob')}); "
                               f"tip moment at full extension {ctx['resultant']['moment_nm_full']:.3f} N·m")
        elif name == 'hand effort':
            k = float(knob) if knob is not None else float(kn['hand_effort_n'])
            if drive['kind'] == 'force' and lim_max is not None:
                qs = quasi_static_pull(model)
                F, t_r = minimum_constant_drive(model, float(lim_max) - float(kn['opens_tol_mm']),
                                                duration, dt, upper=max(200.0, 10 * k))
                rec.update(knob=k, value=qs['peak'], units='N' if model['coord'] == 'linear' else 'N·m',
                           ok=qs['peak'] < k,
                           note=(f"quasi-static pull to move it slowly over the whole travel: breakaway "
                                 f"{qs['breakaway']:.3f}, sliding peak {qs['peak_sliding']:.3f} at q = {qs['at_q']:.1f}; "
                                 f"the minimum CONSTANT pull that opens fully within {duration} s is "
                                 + (f'{F:.3f} (coasting on momentum, reaches at {t_r:.3f} s)' if F is not None
                                    else 'above the search ceiling')))
                rec['breakaway'] = qs['breakaway']
                rec['peak_sliding'] = qs['peak_sliding']
                rec['peak_friction'] = qs['peak_friction']
                rec['min_constant_pull'] = F
            else:
                rd = required_drive(model, drive, duration, dt, result['record_dt'])
                rec.update(knob=k, value=rd['peak_after_start'], units='N' if model['coord'] == 'linear' else 'N·m',
                           ok=rd['peak_after_start'] < k,
                           note=f"force required to follow the formula (peak after the start {rd['peak']:.3f} incl. the impulsive start)")
        elif name == 'stays closed':
            k = float(knob) if knob is not None else float(kn['detent_hold_n'])
            det = (model.get('detent') or {}).get('force', 0.0)
            rec.update(knob=k, value=det, units='N', ok=det > k,
                       note=(ctx.get('detent') or {}).get('basis', 'no detent on this joint'))
        elif name == 'deflection':
            rec['note'] = ("named only — the number comes from the FEMModelDefinition in "
                           "fem_model_ref, run by materialsScience fem_engine (D-mxc-7)")
            rec['ok'] = False
        else:
            rec['note'] = f'unknown check {name!r}'
        out.append(rec)
    return out


def run_polari(manager, motion_case, load_case, knobs=None, fem_model_ref='',
               run_name='', worker='', write_vectors=True):
    """Execute a motion case under a load case on Polari's engine and land
    every row: MechMotionRun, the core SimulationRun, MechMotionSimState
    per recorded step, MechMotionVector per signal. Returns {run, result,
    report, model, context, sim_run, inputs_sha256}."""
    mc_name = _get(motion_case, 'name', '')
    lc_name = _get(load_case, 'name', '')
    run_name = run_name or f'{mc_name}@{lc_name}'
    sim_run_name = f'{run_name}-sim'
    model, ctx = build_model(manager, motion_case, load_case, knobs)
    kn = ctx['knobs']
    duration = float(_get(motion_case, 'duration_s', 1.0))
    step_s = float(_get(motion_case, 'step_s', 0.01))
    dt = min(step_s, float(kn['engine_dt_s']))
    drive = _drive_of(motion_case, model)
    sha, sha_knobs = run_inputs_sha(manager, motion_case, load_case, knobs)
    started = _now()

    result = integrate(model, drive, duration, dt, step_s)
    checks = _checks(motion_case, model, ctx, result, drive, duration, dt)
    ok = all(c['ok'] for c in checks) if checks else True

    # --- core SimulationRun + per-step state rows (what build_series reads)
    sim_run = _upsert(manager, _SimulationRunCls(), {
        'name': sim_run_name, 'simulation_ref': MOTION_SIM_DEF, 'status': 'complete',
        'started_at': started, 'completed_at': _now(),
        'total_steps': int(round(duration / dt)), 'recorded_steps': len(result['steps']),
        'last_recorded_step': result['steps'][-1]['step'] if result['steps'] else 0,
        'error_message': '', 'label': f'mech motion {run_name}',
        'initial_conditions_overrides_json': '{}', 'time_step_seconds': step_s,
        'field_save_overrides_json': '{}',
        'parameter_overrides_json': json.dumps({'motion_case': mc_name, 'load_case': lc_name}),
        'coupled_run_refs_json': '{}',
    })
    for s in result['steps']:
        _upsert(manager, MechMotionSimState, {
            'name': f"{sim_run_name}-mech-motion-{s['step']}",
            'simulation_run_ref': sim_run_name, 'run_ref': run_name,
            'step': s['step'], 'time': s['t_s'], 't_s': s['t_s'], 'q': s['q'],
            'q_dot': s['q_dot'], 'q_ddot': s['q_ddot'], 'drive': s['drive'],
            'friction': s['friction'], 'normal': s['normal'], 'side_force': s['side_force'],
            'tip_moment_nm': s['tip_moment_nm'], 'power_w': s['power_w'],
            'at_limit': bool(s['at_limit']),
        })
    if write_vectors:
        fields = ROTARY_SIGNAL_FIELDS if model['coord'] == 'rotary' else SIGNAL_FIELDS
        for signal, field, units in fields:
            _upsert(manager, MechMotionVector, {
                'name': f'{run_name}:{signal}', 'run_ref': run_name, 'signal': signal,
                'samples_json': json.dumps([[s['t_s'], s[field]] for s in result['steps']]),
                'units': units, 'basis': 'polari engine',
            })

    # --- the mech run row: every check with its number
    report = {
        'checks': checks, 'ok': ok,
        'summary': dict(result['summary'], drive=drive, duration_s=duration, step_s=step_s,
                        engine_dt_s=dt, mass_kg=model['inertia'],
                        normal_closed_n=ctx['normal_closed_n'], normal_full_n=ctx['normal_full_n'],
                        moment_nm_closed=ctx['resultant']['moment_nm_closed'],
                        moment_nm_full=ctx['resultant']['moment_nm_full'],
                        mu=ctx['mu'], running_gear=ctx['running_gear']),
        'honesty': ('rigid body, 1 DOF, no compliance, no backlash dynamics; friction '
                    'and ratings are knobs until measured; FEM is named, not run here'),
    }
    provenance = {
        'rows': {'MechMotionCase': mc_name, 'MechLoadCase': lc_name,
                 'MechJoint': ctx['joint'], 'MechContact': ctx['contact'],
                 'slide_rating_row': ctx['slide_rating_row'], 'SimulationRun': sim_run_name},
        'knobs': sha_knobs, 'engine_version': ENGINE_VERSION,
        'contact_basis': ctx['mu']['basis'],
    }
    run = _upsert(manager, MechMotionRun, {
        'name': run_name, 'motion_case_ref': mc_name, 'load_case_ref': lc_name,
        'engine': 'polari', 'engine_version': ENGINE_VERSION, 'worker': worker,
        'simulation_run_ref': sim_run_name, 'fem_model_ref': fem_model_ref,
        'started': started, 'finished': _now(), 'ok': ok,
        'report_json': json.dumps(report), 'provenance_json': json.dumps(provenance),
        'freecad_artifact_sha': '', 'inputs_sha256': sha,
    })
    if not hasattr(run, 'confirmation_json') or not getattr(run, 'confirmation_json', ''):
        setattr(run, 'confirmation_json', '{}')
    void_if_changed(run, sha)
    _set(load_case, 'resultant_json', json.dumps({
        'total_mass_kg': ctx['resultant']['total_mass_kg'],
        'total_force_n': ctx['resultant']['total_force_n'],
        'moment_nm_closed': ctx['resultant']['moment_nm_closed'],
        'moment_nm_full': ctx['resultant']['moment_nm_full'],
        'basis': ctx['resultant']['basis'],
    }))
    return {'run': run, 'result': result, 'report': report, 'model': model,
            'context': ctx, 'sim_run': sim_run, 'inputs_sha256': sha}


def _SimulationRunCls():
    try:
        from simulations.simulation_run import SimulationRun
        return SimulationRun
    except Exception:  # noqa: BLE001 — core simulations absent: a plain row keeps the shape
        return type('SimulationRun', (), {'__init__': lambda self, **kw: self.__dict__.update(kw)})


# ---------------------------------------------------------------------------
# the FreeCAD comparison
# ---------------------------------------------------------------------------
def compare_to_freecad(run_out, csv_path, tol_mm=0.1, step_s=None, axis='z'):
    """Compare Polari's position(t) with a FreeCAD Motion CSV. Frame f ≥ 1
    of the CSV is t = (f − 1)·step (REFERENCE.json); frame 0 is the
    pre-motion placement and is REPORTED, never compared. `run_out` is
    run_polari's return (or a bare integrate() result / list of steps)."""
    from mech.custom.freecad_motion import csv_sha256, read_motion_csv
    if isinstance(run_out, dict) and 'result' in run_out:
        steps = run_out['result']['steps']
        step_s = step_s or run_out['result']['record_dt']
    elif isinstance(run_out, dict) and 'steps' in run_out:
        steps = run_out['steps']
        step_s = step_s or run_out.get('record_dt')
    else:
        steps = list(run_out)
    if step_s is None:
        raise ValueError('step_s is needed to place the CSV frames in time')
    frames = read_motion_csv(csv_path, step_s)
    by_t = {round(s['t_s'], 6): s['q'] for s in steps}
    compared, pre_motion, missing, worst = [], [], [], 0.0
    for fr in frames:
        if fr['t_s'] is None:
            pre_motion.append({'frame': fr['frame'], axis: fr[axis],
                               'note': 'pre-motion placement (the solved assembly before the formula applies)'})
            continue
        q = by_t.get(round(fr['t_s'], 6))
        if q is None:
            missing.append(fr['frame'])
            continue
        err = abs(q - fr[axis])
        worst = max(worst, err)
        compared.append({'frame': fr['frame'], 't_s': fr['t_s'], 'polari_mm': q,
                         'freecad_mm': fr[axis], 'err_mm': err})
    return {
        'ok': bool(compared) and worst <= tol_mm and not missing,
        'max_abs_err_mm': worst, 'tol_mm': tol_mm, 'compared': len(compared),
        'frames_total': len(frames), 'pre_motion_frames': pre_motion,
        'missing_frames': missing, 'samples': compared,
        'csv_sha256': csv_sha256(csv_path),
        'note': 'frame f≥1 ↔ t=(f−1)·step; frame 0 is FreeCAD\'s pre-motion placement, reported not asserted',
    }
