"""
@module cntfet.cnt_device_viz

fet-viz (Dustin 2026-08-26): in-page visualizations and
characterizations of the EXISTING FET device rows — per-object
([[per-object-display-config]]): the curves belong to the device,
served from device-scoped paths any display row can point at, and
rendered by the SAME seeded-GraphDefinition + named-graph-panel
machinery as the figure replicas. No new chart engine.

Surfaces (GET, wired in cnt_api):
  /api/cntfet/device/{name}/points?curve=transfer|output
      long-form rows (series/style/dash/x/y) matching the seeded
      graph dimensions — transfer = Id(Vg) per drain bias (log Y),
      output = Id(Vd) per gate bias.
  /api/cntfet/device/{name}/characterization
      the cnt_metrics family (SS/DIBL/Ion/Ioff/gm/G_on) with its
      spec, fidelity string, and REFUSALS VERBATIM.

Honesty rules: a device that was never derived REFUSES with the
derive affordance named (the D13 precedent — a refusing panel is
correct, an empty chart is a lie); every payload carries its
fidelity string (F1 compact model here — F3 curves stay
row-backed via the existing figure path); metrics that cannot be
measured come back None with the reason (cnt_metrics contract).

@consumers cnt_api, cnt_pages_seed (panel dataPaths),
  selftest_cntfet, polariServer (graph seed pass via
  SEED_CNT_DEVICE_GRAPHS concat)
"""

import json

from cntfet.cnt_derive import get_row, resolve_components
from cntfet.cnt_metrics import extract_metrics
from cntfet.cnt_vs_model import build_vs_params, vs_terminal_current

FIDELITY = ('F1 (VS_MINIMAL compact model — thermionic + Rc; '
            'F3/NEGF curves are row-backed via /api/cntfet/'
            'figures)')

#: Bias families for the two curve shapes (V). Sweeps stay inside
#: the S1 window (0..0.6 V) the model is calibrated on.
TRANSFER_VD = (0.05, 0.3, 0.6)
OUTPUT_VG = (0.2, 0.3, 0.4, 0.5, 0.6)
SWEEP_STEP = 0.02
SWEEP_MAX = 0.6


def _refuse(error):
    return {'ok': False, 'error': error}


def device_model(manager, name):
    """(id_fn, p, device, None) or (None, None, None, refusal) — the
    device's F1 model as a callable PLUS its VS parameter set, so
    consumers that need the characteristic equations themselves
    (cnt_states: Vt(Vds), Vdsat, n_ss·φt) read the same p the
    current came from. The refusal names the affordance, never a
    bare 404."""
    if manager is None:
        return None, None, None, _refuse(
            'no manager — device rows are not reachable')
    device = get_row(manager, 'AlignedCNTFETDevice', name)
    if device is None:
        # fp-2: a silicon MOSFET row answers the SAME contract (VS
        # parameterisation) so every fi/fv/fp surface works on it.
        try:
            from sifet.si_device import si_device_model
            if get_row(manager, 'SiliconMOSFET', name) is not None:
                return si_device_model(manager, name)
        except ImportError:
            pass
        return None, None, None, _refuse(f'no device named "{name}"')
    if not getattr(device, 'derived_at', ''):
        return None, None, None, _refuse(
            f'device "{name}" never derived — POST '
            f'{{"action": "derive"}} to /api/cntfet/devices/'
            f'{name} first')
    rows, missing = resolve_components(manager, device)
    if missing:
        return None, None, None, _refuse(
            f'missing component rows: {missing}')
    mat, geo = rows['material'], rows['geometry']
    gate, contact = rows['gate_stack'], rows['contact']
    transport = rows['transport']
    p = build_vs_params(
        {'diameter_nm': mat.diameter_nm, 'eg_ev': mat.eg_ev},
        {'lg_nm': geo.lg_nm},
        {'t_ox_nm': gate.t_ox_nm, 'k_ox': gate.k_ox},
        {'rc_ohm': contact.rc_ohm},
        {'vt0_v': transport.vt0_v, 'efsd_ev': transport.efsd_ev},
        device.temperature_k)
    # fp-6: polarity reaches the model. The p-twin is the EXACT
    # mirror ([VS1] premise ii): every characteristic is analysed in
    # the device's OWN polarity frame (|Vgs|, |Vds|), so its numbers
    # equal the n twin's and its SPICE card carries ptype = 1 (the
    # cell netlists already use that). Stated on p, not hidden.
    polarity = getattr(device, 'polarity', 'n') or 'n'
    p = {**p, 'polarity': polarity, 'ptype': 1 if polarity == 'p' else 0,
         'polarity_frame': ('mirrored: Id(vg, vd) here is |Id_p(-vg, '
                            '-vd)| — the device\'s own frame'
                            if polarity == 'p' else 'native n-frame')}
    # the id_fn evaluates the mirror-symmetric n-frame model (ptype 0);
    # p['ptype'] = 1 is for the SPICE card / cell netlists only
    p_eval = {**p, 'ptype': 0}
    return (lambda vg, vd: vs_terminal_current(vg, vd, p_eval)['id_a'],
            p, device, None)


def _device_id_fn(manager, name):
    """(id_fn, device, None) or (None, None, refusal)."""
    id_fn, _p, device, refusal = device_model(manager, name)
    return id_fn, device, refusal


def curve_rows_from_fn(id_fn, curve):
    """Pure: long-form rows for one curve family. Id in µA (the
    figure convention)."""
    rows = []
    sweep = []
    v = 0.0
    while v <= SWEEP_MAX + 1e-9:
        sweep.append(round(v, 4))
        v += SWEEP_STEP
    if curve == 'transfer':
        for vd in TRANSFER_VD:
            for vg in sweep:
                rows.append({'series': f'Vd = {vd:g} V',
                             'style': 'line', 'dash': False,
                             'x': vg,
                             'y': id_fn(vg, vd) * 1e6})
    elif curve == 'output':
        for vg in OUTPUT_VG:
            for vd in sweep:
                rows.append({'series': f'Vg = {vg:g} V',
                             'style': 'line', 'dash': False,
                             'x': vd,
                             'y': id_fn(vg, vd) * 1e6})
    else:
        return None
    return rows


def state_curve_rows(id_fn, p, curve, vd=0.6, manager=None):
    """fi-0/fi-1: the state-annotated families. 'transfer-states' =
    the Id(Vg) line at one Vd PLUS shaded state bands + boundary
    guides (styles band/guide — long-form, config-rendered);
    'output-states' = the output family PLUS the dashed Vdsat locus
    (linear/saturation boundary) as its own series."""
    from cntfet.cnt_states import output_boundary, state_band_rows
    rows = []
    if curve == 'transfer-states':
        ys = []
        for vg in _sweep():
            y = id_fn(vg, vd) * 1e6
            ys.append(y)
            rows.append({'series': f'Id, Vd = {vd:g} V',
                         'style': 'line', 'dash': False,
                         'x': vg, 'y': y})
        y_lo = max(min(ys), 1e-9)   # log-Y safe floor
        y_hi = max(ys)
        rows.extend(state_band_rows(p, vd, y_lo, y_hi,
                                    manager=manager))
        return rows
    if curve == 'output-states':
        rows = curve_rows_from_fn(id_fn, 'output')
        for vg in OUTPUT_VG:
            b = output_boundary(p, vg)
            if b['x'] is not None:
                rows.append({'series': 'Vdsat locus', 'style': 'dot',
                             'dash': True, 'x': b['x'],
                             'y': b['id_a'] * 1e6})
        return rows
    return None


def _sweep():
    sweep, v = [], 0.0
    while v <= SWEEP_MAX + 1e-9:
        sweep.append(round(v, 4))
        v += SWEEP_STEP
    return sweep


#: fi-3: Monte Carlo sample count behind the score-spread and
#: envelope curves (~4 s per 100 on the node; a knob via ?samples=).
DEFAULT_MC_SAMPLES = 100


def _montecarlo(manager, device, samples, seed):
    """One MC run for the fi-3 curves — no result row (a graph
    refresh is not an S3 act); refusals pass through as data."""
    from cntfet.cnt_montecarlo import monte_carlo
    if not hasattr(device, 'process_set'):
        # fp-2: a SiliconMOSFET row has no CNT process set — sample the
        # silicon variability PRIORS instead (same report shape).
        try:
            from sifet.si_montecarlo import monte_carlo as si_mc
            return si_mc(manager, device, sample_count=samples, seed=seed)
        except ImportError:
            pass
        return {'ok': False,
                'refusal': f'no stochastic (Monte Carlo) basis for '
                           f'"{getattr(device, "name", "?")}": the S3 '
                           'process rows (purity / alignment / Rc …) are '
                           'CNT-specific; a silicon variability basis '
                           '(Vt / Lg / tox distributions) is a sifet '
                           'follow-up'}
    return monte_carlo(manager, device, sample_count=samples,
                       seed=seed,
                       result_factory=lambda **f:
                       type('NoRow', (), {'name': 'unrecorded'})())


def score_curve_rows(manager, id_fn, p, device, curve, vd=0.6,
                     samples=DEFAULT_MC_SAMPLES, seed=1):
    """fi-2/fi-3 families. 'score-terms' = normalized value per
    term (dot; lo/hi = MC p05/p95 and best/worst-case dots when
    samples > 0) + hguide at 1.0; 'transfer-envelope' = the
    nominal Id(Vg) at Vd PLUS the MC p05–p95 and min–max bands;
    'cell-scores' = per characterized cell, the score and each
    term's normalized value. Returns (rows, refusal)."""
    from cntfet.cnt_scoring import (
        score_frame, score_from_frame, score_term_rows,
    )
    if curve == 'score-terms':
        result = score_from_frame(
            score_frame(id_fn, p, device.temperature_k), manager)
        spread = best = worst = None
        if samples > 0:
            mc = _montecarlo(manager, device, samples, seed)
            sc = (mc.get('score') or {}) if mc.get('ok') else {}
            if mc.get('ok') and sc.get('quantiles'):
                spread, best, worst = (sc['termSpread'], sc['best'],
                                       sc['worst'])
        return score_term_rows(result, spread, best, worst), None
    if curve == 'transfer-envelope':
        rows = []
        for vg in _sweep():
            rows.append({'series': f'nominal Id, Vd = {vd:g} V',
                         'style': 'line', 'dash': False, 'x': vg,
                         'y': id_fn(vg, vd) * 1e6})
        mc = _montecarlo(manager, device, max(samples, 1), seed)
        env = mc.get('envelope') if mc.get('ok') else None
        if env is None:
            return None, _refuse(
                mc.get('refusal') or mc.get('error')
                or 'no functional Monte Carlo sample for the '
                   'envelope')
        for lo_k, hi_k, label in (('p05', 'p95', 'MC p05–p95'),
                                  ('min', 'max', 'MC min–max')):
            for x, lo, hi in zip(env['vgs'], env[lo_k], env[hi_k]):
                rows.append({'series': label, 'style': 'band',
                             'dash': False, 'x': x,
                             'lo': max(lo, 1e-9), 'hi': max(hi, 1e-9)})
        return rows, None
    if curve == 'cell-scores':
        from cntfet.cnt_cell_scoring import cell_score_rows, score_cells
        report = score_cells(manager, device.name)
        if not report.get('ok'):
            return None, report
        return cell_score_rows(report), None
    if curve == 'compare':
        from cntfet.cnt_compare import compare_devices, compare_rows
        report = compare_devices(manager, device.name)
        if not report.get('ok'):
            return None, report
        return compare_rows(report), None
    return None, None


CURVES = ('transfer', 'output', 'transfer-states', 'output-states',
          'score-terms', 'transfer-envelope', 'cell-scores', 'compare')


def provenance(manager, subject_kind, name):
    """The compact evidence / proof-of-freedom block every FET and
    cell payload embeds (first-class, clickable via detailPath).
    None when the evidence module is absent — callers omit the key
    rather than fake it."""
    try:
        from cntfet.cnt_evidence import provenance_summary
    except ImportError:
        return None
    try:
        return provenance_summary(manager, subject_kind, name)
    except Exception as exc:   # a broken chain is reported, not hidden
        return {'error': f'provenance unavailable: {exc}'}


def extra_curve_builders():
    """fv arc: curve builders contributed by sibling modules, each
    `fn(id_fn, p, device, manager, knobs) -> rows`. A module that is
    absent simply contributes nothing (its curves refuse by name)."""
    builders = {}
    for mod in ('cnt_regimes', 'cnt_transport', 'cnt_fields',
                'cnt_power', 'cnt_taxonomy', 'cnt_ip', 'cnt_evidence'):
        try:
            module = __import__(f'cntfet.{mod}', fromlist=['CURVE_BUILDERS'])
            builders.update(getattr(module, 'CURVE_BUILDERS', {}))
        except ImportError:
            continue
    return builders


def extra_graph_seeds():
    """GraphDefinition seeds contributed by the fv modules."""
    seeds = []
    for mod, name in (('cnt_regimes', 'SEED_CNT_REGIME_GRAPHS'),
                      ('cnt_transport', 'SEED_CNT_TRANSPORT_GRAPHS'),
                      ('cnt_fields', 'SEED_CNT_FIELD_GRAPHS'),
                      ('cnt_power', 'SEED_CNT_POWER_GRAPHS'),
                      ('cnt_taxonomy', 'SEED_CNT_TAXONOMY_GRAPHS'),
                      ('cnt_ip', 'SEED_CNT_IP_GRAPHS'),
                      ('cnt_evidence', 'SEED_CNT_EVIDENCE_GRAPHS')):
        try:
            module = __import__(f'cntfet.{mod}', fromlist=[name])
            seeds.extend(getattr(module, name, []))
        except ImportError:
            continue
    return seeds


def device_curve_points(manager, name, curve='transfer', vd=0.6,
                        samples=DEFAULT_MC_SAMPLES, seed=1):
    """The named-graph-panel data feed for one device."""
    id_fn, p, device, refusal = device_model(manager, name)
    if refusal is not None:
        return refusal
    rows = curve_rows_from_fn(id_fn, curve)
    if rows is None:
        rows = state_curve_rows(id_fn, p, curve, vd=vd,
                                manager=manager)
    if rows is None:
        rows, refusal = score_curve_rows(manager, id_fn, p, device,
                                         curve, vd=vd,
                                         samples=samples, seed=seed)
        if refusal is not None:
            return refusal
    if rows is None:
        builder = extra_curve_builders().get(curve)
        if builder is not None:
            built = builder(id_fn, p, device, manager, None)
            # builders return rows, or (rows, refusal) like
            # score_curve_rows — a refusal passes through verbatim
            if isinstance(built, tuple):
                rows, refusal = built
                if refusal is not None:
                    return refusal
            else:
                rows = built
    if rows is None:
        return _refuse(f'unknown curve "{curve}" '
                       f'({" | ".join(CURVES)} | '
                       f'{" | ".join(sorted(extra_curve_builders()))})')
    return {'ok': True, 'device': name, 'curve': curve,
            'fidelity': FIDELITY,
            'temperature_k': device.temperature_k,
            'rows': rows}


def device_characterization(manager, name):
    """The metric family for one device — refusals verbatim."""
    id_fn, device, refusal = _device_id_fn(manager, name)
    if refusal is not None:
        return refusal
    metrics = extract_metrics(id_fn)
    return {'ok': True, 'device': name, 'fidelity': FIDELITY,
            'polarity': getattr(device, 'polarity', ''),
            'temperature_k': device.temperature_k,
            'metrics': metrics,
            'note': ('every metric the model cannot measure on '
                     'this device is None with its reason in '
                     'metrics.refusals — never a made-up number')}


def _device_graph(kind, description, x_label, y_label,
                  y_type='linear'):
    """Same wrapped {graphConfig} form as the figure graphs — ONE
    row per curve KIND, reused across devices by pointing a
    panel's dataPath at that device's endpoint."""
    return {
        'name': f'cnt-device-{kind}',
        'description': description + ' — data: /api/cntfet/'
                       'device/{name}/points?curve=' + kind,
        'source_class': 'AlignedCNTFETDevice',   # any FET (Si rows too)
        'definition': json.dumps({'graphConfig': {
            'renderStyle': 'lineY',
            'xDimension': 'x',
            'yDimensions': ['y'],
            'seriesDimension': 'series',
            'styleDimension': 'style',
            'seriesColors': [],
            'options': {'showLegend': True, 'showGrid': True,
                        'xLabel': x_label, 'yLabel': y_label,
                        'yType': y_type},
            'aggregation': None,
        }}),
    }


#: GraphDefinition seeds — per-KIND, device-agnostic (the panel's
#: dataPath picks the device), editable on the Graphs page.
SEED_CNT_DEVICE_GRAPHS = [
    _device_graph(
        'transfer',
        'Device transfer characteristic Id(Vg) per drain bias — '
        'log Y so the subthreshold decade band is visible',
        'Vg (V)', 'Id (uA)', y_type='log'),
    _device_graph(
        'output',
        'Device output characteristic Id(Vd) per gate bias',
        'Vd (V)', 'Id (uA)'),
    # fi-1: the intuition graphs — states shaded as bands, the
    # qualifying boundaries as labelled guides (rows from
    # cnt_states; styles band/guide are config-rendered).
    _device_graph(
        'transfer-states',
        'Operating STATES on the transfer curve: off / '
        'transition / on-linear / on-saturation shaded, with '
        'the qualifying boundaries Vt(Vds) and Vt + Vov_min as '
        'guides — what qualifies each state, on the curve it '
        'governs',
        'Vg (V)', 'Id (uA)', y_type='log'),
    _device_graph(
        'output-states',
        'Output family with the linear/saturation boundary: the '
        'Vdsat locus (Fsat knee) marks where each Vg curve stops '
        'behaving like a resistor',
        'Vd (V)', 'Id (uA)'),
    # fi-2/fi-3: scoring by characteristic equations + the
    # stochastic best/worst case (categorical x = the term; the
    # hguide at 1.0 is the ideal).
    _device_graph(
        'score-terms',
        'FET figures of merit normalized against their '
        'characteristic-equation ideals (dot = nominal; error '
        'interval = Monte Carlo p05–p95; dashed dots = best/worst '
        'case by score; rule at 1.0 = ideal)',
        'figure of merit', 'normalized (1 = ideal)'),
    _device_graph(
        'transfer-envelope',
        'Stochastic envelope: the nominal Id(Vg) at Vdd with the '
        'Monte Carlo p05–p95 and min–max bands from the bound '
        'process set\'s distributions — the best/worst-case '
        'devices live at the band edges',
        'Vg (V)', 'Id (uA)', y_type='log'),
    _device_graph(
        'cell-scores',
        'Standard cells scored against the driving FET\'s '
        'intrinsic limits (delay/τ, transition/τ, energy/C·V², '
        'FETs/min): score per cell + each term normalized; rule '
        'at 1.0 = ideal',
        'cell', 'normalized (1 = ideal)'),
    # fi-4: the competitive ranking — every FET on one axis, the
    # page's own device marked ◀; a device that fails the validity
    # proofs sits at 0 with the failed proofs as its label.
    _device_graph(
        'compare',
        'Competitive FET ranking: score + every term normalized for '
        'each FET (CNT and silicon) (◀ = this page\'s device); '
        'unprovable FETs sit at 0 with their failed proofs named; '
        'rule at 1.0 = ideal',
        'device', 'normalized (1 = ideal)'),
]
