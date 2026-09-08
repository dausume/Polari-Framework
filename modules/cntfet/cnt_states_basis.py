"""
@module cntfet.cnt_states_basis

fi-0 (2026-08-26): FET operating STATES as data, and the
characteristic-equation criteria that QUALIFY a bias point for a
state — the foundation the intuition graphs (fi-1), the scoring
terms (fi-2) and the stochastic best/worst cases (fi-3) all cite.
Plan: AI-Notes/plans/FET_INTUITION_PLAN.md.

Every quantity a criterion compares is computed from the SAME VS
parameter set p the device's current comes from
(cnt_device_viz.device_model), so "why is this point in that
state" is answered with the model's own equations:

  Vt(Vds)   = vt0 - dVt - DIBL·Vds                    [VS1] eq.(8)
  φt        = kT/q;  n_ss the subthreshold ideality
  SS        = n_ss φt ln10           (60 mV/dec floor at n_ss = 1)
  Vov_min   = vov_decades · SS       (knob: decades of Id above the
                                     Vt crossing before "on")
  Ff        = 1/(1 + exp((Vgsi - (Vt - αφt/2))/(αφt)))  [VS1]
  Vdsat     = (v_xo Lg/μ)(1 - Ff) + φt Ff              [VS1]
  Fsat      = x/(1+|x|^β)^(1/β),  x = Vdsi/Vdsat

States (ordered along a rising-Vgs sweep):
  off            Vgs < Vt(Vds): Id is the subthreshold tail
                 Id ≈ Ioff·10^((Vgs-Vt)/SS) — SS rules everything
  transition-on  Vt ≤ Vgs < Vt + Vov_min: the barrier is collapsing
                 (Ff 1→0); Id climbs the last decades to "on"
  transition-off same band on a FALLING sweep (F1 is hysteresis-free
                 so the bounds are identical — stated, not hidden)
  on-linear      Vgs ≥ Vt + Vov_min and Vds < Vdsat: Fsat ≈ x, Id
                 ∝ Vds (the resistor-like leg of Id-Vd)
  on-saturation  Vgs ≥ Vt + Vov_min and Vds ≥ Vdsat: Fsat → 1,
                 Id = Qxo v_xo (velocity-saturated plateau)

Criteria are DATA (FETOperatingState.criteria_json): lists of
{lhs, op, rhs, why} over a named frame of numbers, evaluated by
`evaluate_criteria` — the same rows the page tables show, so the
"what qualifies" list is never a hidden branch in code. Knobs are
explicit (STATE_KNOBS) and every result carries them plus the F1
fidelity string.

@consumers
  - cntfet.cnt_api (GET /api/cntfet/device/{name}/states)
  - cntfet.cnt_device_viz_seed (state band / guide rows for fi-1 graphs)
  - cntfet.cntfet_selftest
  - polariServer (FETOperatingState registration + SEED_FET_STATES)
"""

import json
import math

from objectTreeDecorators import treeObject, treeObjectInit

from cntfet.custom.cnt_vs_model import _logistic, vs_terminal_current

LN10 = math.log(10.0)

FIDELITY = ('F1 (VS_MINIMAL compact model): states and boundaries '
            'are the model\'s own equations at the device\'s '
            'derived parameters; F3/NEGF re-grading is row-backed '
            'work, not a hidden fallback')

#: Explicit knobs (every result echoes the values it used).
STATE_KNOBS = {
    # decades of Id above the Vt crossing before the device counts
    # as "on" — Vov_min = vov_decades · SS
    'vov_decades': 3.0,
    # 'model' = the VS Fsat knee (Vdsat from p — default);
    # 'textbook' = Vgs - Vt (the long-channel square-law boundary,
    # shown as the dashed alternative on the output graph)
    'vdsat_criterion': 'model',
}

OPS = {
    '<': lambda a, b: a < b,
    '<=': lambda a, b: a <= b,
    '>': lambda a, b: a > b,
    '>=': lambda a, b: a >= b,
    '==': lambda a, b: a == b,
}


class FETOperatingState(treeObject):
    """One operating state of a FET as a ROW: its ordering along a
    rising-Vgs sweep, the physics ("why"), and the qualifying
    criteria as data (see module docstring)."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        display_name: str = '',
        order: int = 0,
        # 'rising' | 'falling' | 'any' — which sweep direction the
        # state is defined on (transition-on vs transition-off)
        direction: str = 'any',
        description: str = '',
        # JSON list of {lhs, op, rhs, why}; lhs/rhs are frame keys
        # (see frame_at) or numbers. ALL must pass.
        criteria_json: str = '[]',
        # the characteristic equation(s) that govern Id here
        governing_equation: str = '',
        fidelity: str = FIDELITY,
        origin: str = 'seeded',
        notes: str = '',
        is_prior: bool = True,
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.order = order
        self.direction = direction
        self.description = description
        self.criteria_json = criteria_json
        self.governing_equation = governing_equation
        self.fidelity = fidelity
        self.origin = origin
        self.notes = notes
        self.is_prior = is_prior


def _c(lhs, op, rhs, why):
    return {'lhs': lhs, 'op': op, 'rhs': rhs, 'why': why}


SEED_FET_STATES = [
    {
        'name': 'off',
        'display_name': 'Off (subthreshold)',
        'order': 0, 'direction': 'any',
        'description': 'The gate has not pulled the channel barrier '
                       'below the source Fermi level: the current is '
                       'the thermionic tail over the barrier, falling '
                       'one decade per SS of gate voltage. Ioff is '
                       'this state at Vgs = 0.',
        'criteria_json': json.dumps([
            _c('vgs', '<', 'vt', 'below the model threshold Vt(Vds) '
                                 '= vt0 - dVt - DIBL·Vds'),
        ]),
        'governing_equation': 'Id ≈ Ioff · 10^((Vgs - Vt)/SS),  '
                              'SS = n_ss·φt·ln10',
    },
    {
        'name': 'transition-on',
        'display_name': 'Transitioning on (near-threshold)',
        'order': 1, 'direction': 'rising',
        'description': 'Vgs has crossed Vt but the barrier is still '
                       'collapsing (the VS Ff function runs 1 → 0): '
                       'Id climbs its last vov_decades decades before '
                       'it is counted as "on". Vov_min = vov_decades '
                       '· SS makes "switched" a stated quantity, not '
                       'a feeling.',
        'criteria_json': json.dumps([
            _c('vgs', '>=', 'vt', 'at or above Vt(Vds)'),
            _c('vgs', '<', 'vt_on', 'still below Vt + Vov_min'),
        ]),
        'governing_equation': 'Qxo = Cinv n_ss φt ln(1 + exp((Vgsi - '
                              '(Vt - αφt Ff))/(n_ss φt)))',
    },
    {
        'name': 'transition-off',
        'display_name': 'Transitioning off (near-threshold, falling)',
        'order': 1, 'direction': 'falling',
        'description': 'The same near-threshold band traversed on a '
                       'falling Vgs sweep. The F1 compact model is '
                       'hysteresis-free, so the bounds are identical '
                       'to transition-on; a measured device with '
                       'trap-induced hysteresis would split them — '
                       'that is data this row would carry, not a '
                       'hidden branch.',
        'criteria_json': json.dumps([
            _c('vgs', '>=', 'vt', 'at or above Vt(Vds)'),
            _c('vgs', '<', 'vt_on', 'below Vt + Vov_min'),
        ]),
        'governing_equation': 'as transition-on (F1: no hysteresis)',
    },
    {
        'name': 'on-linear',
        'display_name': 'On — linear (resistive)',
        'order': 2, 'direction': 'any',
        'description': 'Fully on and the drain bias is below the '
                       'saturation voltage: Fsat ≈ Vds/Vdsat, so Id '
                       'grows ~linearly with Vds — the channel acts '
                       'as a resistor g_on = Id/Vds.',
        'criteria_json': json.dumps([
            _c('vgs', '>=', 'vt_on', 'on: Vgs ≥ Vt + Vov_min'),
            _c('vds', '<', 'vdsat', 'below the saturation voltage'),
        ]),
        'governing_equation': 'Id = Qxo v_xo Fsat,  Fsat ≈ Vds/Vdsat '
                              '(x ≪ 1)',
    },
    {
        'name': 'on-saturation',
        'display_name': 'On — saturated (velocity-limited)',
        'order': 3, 'direction': 'any',
        'description': 'Fully on and Vds at or above Vdsat: carriers '
                       'leave the virtual source at v_xo and Fsat → '
                       '1; Id plateaus at Qxo·v_xo and only DIBL '
                       'still tilts it with Vds.',
        'criteria_json': json.dumps([
            _c('vgs', '>=', 'vt_on', 'on: Vgs ≥ Vt + Vov_min'),
            _c('vds', '>=', 'vdsat', 'at or above the saturation '
                                     'voltage'),
        ]),
        'governing_equation': 'Id → Qxo v_xo  (Fsat → 1)',
    },
]


# ── the frame: every number a criterion may cite ───────────────────

def model_vt(p, vds_v):
    """Vt(Vds) — the VS model's own threshold at this drain bias."""
    return p['vt0_v'] - p['dvt_v'] - p['dibl_v_per_v'] * vds_v


def subthreshold_swing_v(p):
    """SS in V/dec from the model's n_ss and φt."""
    return p['n_ss'] * p['phit_v'] * LN10


def model_vdsat(p, vgsi_v, vdsi_v):
    """Vdsat at the internal biases, exactly as vs_channel_current
    forms it (mirrored, not re-derived)."""
    phit = p['phit_v']
    vt = model_vt(p, vdsi_v)
    ff = _logistic(-(vgsi_v - (vt - p['alpha'] * phit / 2.0))
                   / (p['alpha'] * phit))
    vdsat_strong = p['vxo_m_per_s'] * p['lg_m'] / p['mu_m2_per_vs']
    return vdsat_strong * (1.0 - ff) + phit * ff, ff


def frame_at(p, vgs_v, vds_v, knobs=None):
    """All named quantities at one terminal bias point."""
    k = {**STATE_KNOBS, **(knobs or {})}
    sol = vs_terminal_current(vgs_v, vds_v, p)
    vgsi, vdsi = sol['vgsi_v'], sol['vdsi_v']
    vt = model_vt(p, vdsi)
    ss_v = subthreshold_swing_v(p)
    vov_min = k['vov_decades'] * ss_v
    vdsat_model, ff = model_vdsat(p, vgsi, vdsi)
    vdsat_textbook = max(vgsi - vt, 0.0)
    vdsat = (vdsat_model if k['vdsat_criterion'] == 'model'
             else vdsat_textbook)
    x = vdsi / vdsat if vdsat > 0 else float('inf')
    fsat = (x / (1.0 + abs(x) ** p['beta']) ** (1.0 / p['beta'])
            if math.isfinite(x) else 1.0)
    return {
        'vgs': vgs_v, 'vds': vds_v,
        'vgsi': vgsi, 'vdsi': vdsi,
        'id_a': sol['id_a'],
        'vt': vt,
        'ss_v_per_dec': ss_v,
        'vov_min': vov_min,
        'vt_on': vt + vov_min,
        'vov': vgsi - vt,
        'ff': ff,
        'vdsat': vdsat,
        'vdsat_model': vdsat_model,
        'vdsat_textbook': vdsat_textbook,
        'fsat': fsat,
        'knobs': k,
    }


# ── evaluation ─────────────────────────────────────────────────────

def _resolve(frame, token):
    if isinstance(token, (int, float)):
        return float(token), str(token)
    if token in frame:
        return float(frame[token]), token
    raise KeyError(token)


def evaluate_criteria(criteria, frame):
    """[{lhs, op, rhs, lhs_value, rhs_value, passed, why}] — every
    comparison with its numbers, so a failed criterion says exactly
    which inequality missed by how much."""
    out = []
    for c in criteria:
        try:
            lv, ln = _resolve(frame, c['lhs'])
            rv, rn = _resolve(frame, c['rhs'])
            fn = OPS[c['op']]
        except KeyError as exc:
            out.append({**c, 'passed': False,
                        'error': f'unknown frame key or op: {exc}'})
            continue
        out.append({'lhs': ln, 'op': c['op'], 'rhs': rn,
                    'lhs_value': lv, 'rhs_value': rv,
                    'margin': lv - rv,
                    'passed': bool(fn(lv, rv)),
                    'why': c.get('why', '')})
    return out


def _state_defs(manager=None):
    """Seeded state rows (manager rows win when present so edits on
    the page change the evaluation with zero code)."""
    rows = []
    if manager is not None:
        table = getattr(manager, 'objectTables', {}).get(
            'FETOperatingState') or {}
        for row in (table.values() if isinstance(table, dict)
                    else table):
            rows.append({
                'name': row.name, 'display_name': row.display_name,
                'order': row.order, 'direction': row.direction,
                'description': row.description,
                'criteria_json': row.criteria_json,
                'governing_equation': row.governing_equation})
    if not rows:
        rows = [dict(s) for s in SEED_FET_STATES]
    return sorted(rows, key=lambda r: (r['order'], r['name']))


def classify(frame, direction='rising', manager=None):
    """The state a frame is in (first row whose criteria ALL pass,
    filtered by sweep direction) plus every row's evaluation."""
    evaluations = []
    chosen = None
    for s in _state_defs(manager):
        if s['direction'] not in ('any', direction):
            continue
        ev = evaluate_criteria(json.loads(s['criteria_json']), frame)
        passed = all(e['passed'] for e in ev) and bool(ev)
        evaluations.append({'state': s['name'],
                            'display_name': s['display_name'],
                            'passed': passed, 'criteria': ev,
                            'governing_equation':
                                s['governing_equation']})
        if passed and chosen is None:
            chosen = s['name']
    return chosen, evaluations


def state_at_bias(p, vgs_v, vds_v, direction='rising', knobs=None,
                  manager=None):
    frame = frame_at(p, vgs_v, vds_v, knobs)
    state, evaluations = classify(frame, direction, manager)
    return {'state': state, 'direction': direction,
            'frame': {k: v for k, v in frame.items() if k != 'knobs'},
            'knobs': frame['knobs'], 'evaluations': evaluations}


# ── boundaries ("what qualifies") along sweeps ─────────────────────

def transfer_boundaries(p, vds_v, knobs=None):
    """Ordered Vgs boundaries at a fixed Vds — the guides on the
    transfer graph. Uses the frame at the boundary's own Vgs so Rc
    drops are honoured (internal vs terminal bias stated)."""
    f = frame_at(p, 0.0, vds_v, knobs)
    vt = f['vt']
    vt_on = f['vt_on']
    return [
        {'x': vt, 'label': 'Vt', 'from': 'off',
         'to': 'transition-on',
         'equation': 'Vt(Vds) = vt0 - dVt - DIBL·Vds',
         'value_v': vt},
        {'x': vt_on, 'label': 'Vt + Vov_min', 'from': 'transition-on',
         'to': 'on',
         'equation': f'Vov_min = {f["knobs"]["vov_decades"]:g}·SS, '
                     f'SS = {f["ss_v_per_dec"]*1e3:.1f} mV/dec',
         'value_v': vt_on},
    ]


def output_boundary(p, vgs_v, knobs=None, step=0.005, vds_max=0.6):
    """The Vds at which a fixed-Vgs output curve crosses Vdsat —
    the linear/saturation boundary (dashed locus on the output
    graph). Bisection-free: first grid point with Vdsi ≥ Vdsat."""
    v = 0.0
    while v <= vds_max + 1e-12:
        f = frame_at(p, vgs_v, v, knobs)
        if f['vdsi'] >= f['vdsat']:
            return {'vgs': vgs_v, 'x': v, 'vdsat': f['vdsat'],
                    'id_a': f['id_a']}
        v += step
    return {'vgs': vgs_v, 'x': None, 'vdsat': None, 'id_a': None,
            'refusal': f'no saturation inside Vds ≤ {vds_max} V'}


def transitions_on_sweep(p, vds_v, direction='rising', knobs=None,
                         step=0.005, vgs_max=0.6, manager=None):
    """Walk a Vgs sweep and record every state change with the
    criterion that flipped — the outline of the switching event."""
    vs = [round(i * step, 6) for i in range(int(vgs_max / step) + 1)]
    if direction == 'falling':
        vs = list(reversed(vs))
    events = []
    prev = None
    for vg in vs:
        state, evs = classify(frame_at(p, vg, vds_v, knobs),
                              direction, manager)
        if state != prev:
            flipped = []
            if prev is not None:
                before = next((e for e in evs if e['state'] == prev),
                              None)
                if before:
                    flipped = [c for c in before['criteria']
                               if not c['passed']]
            events.append({'vgs': vg, 'from': prev, 'to': state,
                           'flipped': flipped})
            prev = state
    return events


# ── long-form rows for the fi-1 graphs ─────────────────────────────

def state_band_rows(p, vds_v, y_lo, y_hi, knobs=None, vgs_max=0.6,
                    direction='rising', manager=None):
    """Shaded x-intervals per state (style 'band', lo/hi = the
    graph's y-range) + guide rows at the boundaries (style 'guide').
    Consumed by cnt_device_viz curve 'transfer-states'."""
    rows = []
    events = transitions_on_sweep(p, vds_v, direction, knobs,
                                  vgs_max=vgs_max, manager=manager)
    for i, ev in enumerate(events):
        x0 = ev['vgs']
        x1 = events[i + 1]['vgs'] if i + 1 < len(events) else vgs_max
        if ev['to'] is None:
            continue
        for x in (x0, x1):
            rows.append({'series': ev['to'], 'style': 'band',
                         'dash': False, 'x': x, 'lo': y_lo,
                         'hi': y_hi})
    for b in transfer_boundaries(p, vds_v, knobs):
        rows.append({'series': b['label'], 'style': 'guide',
                     'dash': True, 'x': b['x'], 'label': b['label'],
                     'y': None})
    return rows


def device_states_report(p, device, vds_v=0.6, vgs_v=None,
                         direction='rising', knobs=None,
                         manager=None):
    """The /states payload: definitions, boundaries, sweep events,
    and (when vgs is given) the point classification."""
    out = {
        'ok': True, 'device': device.name, 'fidelity': FIDELITY,
        'temperature_k': device.temperature_k,
        'knobs': {**STATE_KNOBS, **(knobs or {})},
        'states': _state_defs(manager),
        'vds': vds_v,
        'boundaries': transfer_boundaries(p, vds_v, knobs),
        'events': transitions_on_sweep(p, vds_v, direction, knobs,
                                       manager=manager),
        'output_boundaries': [output_boundary(p, vg, knobs)
                              for vg in (0.2, 0.3, 0.4, 0.5, 0.6)],
    }
    if vgs_v is not None:
        out['point'] = state_at_bias(p, vgs_v, vds_v, direction,
                                     knobs, manager)
    return out
