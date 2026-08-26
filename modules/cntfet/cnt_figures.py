"""
@module cntfet.cnt_figures

Figure replicas (Dustin 2026-08-25): "we need to be sure we are
building out graphs similar to the graphs on the cited studies for
viewing and comparison when proofing these simulations work."

Every cited figure the model claims contact with becomes a
QUERYABLE chart payload on the SAME AXES as the publication —
paper points (digitized, with their D18 error bars) laid beside
the model curve computed in the anchor context, plus the residual
summary. A figure we have NOT digitized is a REFUSING entry that
names the missing step — absence is visible, never silent
(the DigitizedDataset discipline, now chart-shaped).

Payload shape is chart-ready for the cnt-2 SVG chart component
(series of {x, y} points + an axes spec with units/scale/ranges
taken from the publication axes), and readable through
api-json-panel until the replica chart lands in the frontend.

@consumers
  - cntfet.cnt_api (GET /api/cntfet/figures[/{figure_id}])
  - cntfet.selftest_cntfet
"""

import json
import types

from cntfet.cnt_bandstructure import eg_ev
# Same-package reuse of the anchor-context machinery — the replica
# MUST be computed in the exact context the residuals use, or the
# chart and the recorded numbers could disagree.
from cntfet.cnt_calibration import (
    _anchor_context_params, _curve_residuals,
)
from cntfet.cnt_digitized_fc10 import (
    ERROR_BUDGET, FIG7A_POINTS, OVERDRIVES_V, X_CALIBRATION,
    Y_CALIBRATION,
)
from cntfet.cnt_vs_model import (
    build_vs_params, vs_terminal_current, vxo_m_per_s,
)

_VS1 = ('Rakheja/Lundstrom/Antoniadis, IEEE TED 62(9) 2015 '
        '(arXiv:1503.04397 author copy)')
_FC10 = 'Franklin & Chen, Nat. Nanotech. 5, 858 (2010)'
_FIORI = ('Fiori/Iannaccone/Klimeck, IEDM 2005, '
          '10.1109/IEDM.2005.1609397 ((c) IEEE — cite+values '
          'bucket, PDF off-git)')


def _fig7a_axes():
    return {
        'x': {'label': 'Vds', 'unit': 'V', 'scale': 'linear',
              'min': 0.0, 'max': 0.4},
        'y': {'label': 'Id', 'unit': 'uA', 'scale': 'linear',
              'min': 0.0, 'max': 15.0},
        'from_publication': 'axis ranges read off the [VS1] '
                            'Fig.7(a) frame (tick-label '
                            'least-squares calibration, D18)',
    }


def _fig7a():
    """The flagship replica: digitized [VS1] Fig.7(a) points with
    their error budget beside the VS model computed in the anchor
    context (anchor Cox + Rs), per overdrive curve."""
    p = _anchor_context_params()
    paper, model = [], []
    for curve in sorted(FIG7A_POINTS, reverse=True):
        points = FIG7A_POINTS[curve]
        if not points:
            continue
        paper.append({
            'label': f'{curve} (paper)',
            'sigmaY_ua': ERROR_BUDGET['sigma_id_ua'],
            'points': [{'x': pt['vds_v'], 'y': pt['id_ua']}
                       for pt in points]})
        vg = p['vt0_v'] + OVERDRIVES_V[curve]
        grid = [i * 0.01 for i in range(41)]
        model.append({
            'label': f'{curve} (VS model, anchor context)',
            'points': [{'x': v, 'y': vs_terminal_current(
                vg, v, p)['id_a'] * 1e6} for v in grid]})
    anchor_like = types.SimpleNamespace(
        name='digitized-vs1-fig7a',
        raw_points_json=json.dumps(FIG7A_POINTS),
        normalizations_json=json.dumps(
            {'overdrives_v': OVERDRIVES_V}))
    return {
        'axes': _fig7a_axes(),
        'paperSeries': paper,
        'modelSeries': model,
        'residuals': _curve_residuals(anchor_like),
        'provenance': {'x_calibration': X_CALIBRATION,
                       'y_calibration': Y_CALIBRATION,
                       'error_budget': ERROR_BUDGET},
        'limits': ['model curves use the ANCHOR context (Cox '
                   '0.156 fF/um, Rs 5.5 kOhm), not the S1 device',
                   'paper symbols fused with the model line were '
                   'never extracted — gaps are a method limit, '
                   'not missing physics'],
    }


def _vxo_vs_lg():
    """v_xo vs Lg: the three [FC10] reported anchors against the
    eq.(9) curve — including the 3 um point the model MISSES by
    design (out-of-domain, l ~= Lg), plotted, not hidden."""
    lgs = [10.0 * (10 ** (i / 12.0)) for i in range(32)]
    return {
        'axes': {
            'x': {'label': 'Lg', 'unit': 'nm', 'scale': 'log',
                  'min': 10.0, 'max': 4000.0},
            'y': {'label': 'v_xo', 'unit': 'm/s',
                  'scale': 'linear', 'min': 0.0, 'max': 4.5e5},
            'from_publication': '[VS1] Fig.7 panel contexts '
                                '(a/b/c = 15/300/3000 nm)',
        },
        'paperSeries': [{
            'label': 'reported v_xo ([VS1] text, [FC10] data)',
            'points': [{'x': 15.0, 'y': 3.8e5},
                       {'x': 300.0, 'y': 1.7e5},
                       {'x': 3000.0, 'y': 0.47e5}]}],
        'modelSeries': [{
            'label': 'eq.(9) v_xo(Lg, d=1.2 nm)',
            'points': [{'x': lg, 'y': vxo_m_per_s(lg, 1.2)}
                       for lg in lgs]}],
        'residuals': [{'anchor': f'fc10-vxo-lg{int(lg)}',
                       'fractional': (vxo_m_per_s(lg, 1.2) - ref)
                       / ref}
                      for lg, ref in ((15.0, 3.8e5),
                                      (300.0, 1.7e5),
                                      (3000.0, 0.47e5))],
        'limits': ['the 3 um point misfits ~-40% BY DESIGN '
                   '(eq.(9) is out-of-domain when the mfp is '
                   'comparable to Lg) — plotted so the domain '
                   'edge is visible'],
    }


def _fig9_cgg():
    """Cgg(Vgs) shape vs [VS1] Fig.9: model-only — the paper curve
    is NOT digitized, so this is a shape-level comparison and says
    so (peak-then-decline is the quantum-capacitance signature the
    selftest pins)."""
    d_nm = 1.2526
    eg = eg_ev(d_nm)
    p = build_vs_params(
        {'diameter_nm': d_nm, 'eg_ev': eg}, {'lg_nm': 15.0},
        {'t_ox_nm': 3.0, 'k_ox': 16.0}, {'rc_ohm': 0.0},
        {'vt0_v': 0.3, 'efsd_ev': 0.1}, 300.0)
    from cntfet.cnt_charge import cgg_f
    extras = {'cinvb_f_per_m': p['cinvb_f_per_m'],
              'vtb_v': p['vtb_v']}
    grid = [i * 0.05 for i in range(29)]
    return {
        'axes': {
            'x': {'label': 'Vgs', 'unit': 'V', 'scale': 'linear',
                  'min': 0.0, 'max': 1.4},
            'y': {'label': 'Cgg', 'unit': 'F (per device)',
                  'scale': 'linear', 'min': 0.0, 'max': None},
            'from_publication': 'shape comparison only — [VS1] '
                                'Fig.9 axes not digitized',
        },
        'paperSeries': [],
        'modelSeries': [{
            'label': 'eq.(11) Cgg (S1 device context)',
            'points': [{'x': vg, 'y': cgg_f(vg, 0.0, p, extras)}
                       for vg in grid]}],
        'residuals': [],
        'limits': ['MODEL-ONLY: the [VS1] Fig.9 curve is not '
                   'digitized — the recorded claim is the SHAPE '
                   '(rise to a peak, then decline), pinned by the '
                   'selftest, not a point-wise residual'],
    }


def _d13_profile(manager):
    """The chip-1 coherence chart: the latest SCF run's converged
    Ec(x) profiles laid over the eq.(5) LAPLACE profile at the
    same bias — the expected characteristic (channel charge
    RAISES the barrier above its zero-charge seed) is visible,
    not asserted. Row-backed: refuses until an SCF run exists."""
    tables = getattr(manager, 'objectTables', None) or {}
    best, best_time = None, ''
    for row in (tables.get('CNTFETSimResult') or {}).values():
        if (getattr(row, 'physics_fidelity', '') == 'F3_NEGF_SCF'
                and getattr(row, 'ran_at', '') > best_time):
            best, best_time = row, row.ran_at
    if best is None:
        return {'refusal': 'no F3_NEGF_SCF result row yet — run '
                           '{action: f3-oracle, scf: true} first'}
    profiles = json.loads(best.metrics_json or '{}'
                          ).get('profiles') or []
    if not profiles:
        return {'refusal': f'result row {best.name} carries no '
                           f'profiles — re-run with the current '
                           f'worker'}
    from cntfet.cnt_derive import get_row, resolve_components
    from cntfet.cnt_constants import lit_value
    device = get_row(manager, 'AlignedCNTFETDevice', best.device)
    laplace_series = []
    if device is not None:
        rows, missing = resolve_components(manager, device)
        if not missing:
            geo, gate = rows['geometry'], rows['gate_stack']
            transport = rows['transport']
            # the worker's own analytic profile — pure numpy,
            # importable without the kwant venv
            from cntfet.kwant_worker import analytic_ec
            import numpy as np
            x_edge = (geo.lg_nm / 2.0
                      + lit_value('lof_over_tox') * gate.t_ox_nm)
            for prof in profiles[:4]:
                xs = np.array(prof['x_nm'])
                ec_l = analytic_ec(
                    xs, x_edge, transport.lambda_nm,
                    transport.vt0_v - prof['vg_v'],
                    transport.efsd_ev, prof['vd_v'])
                laplace_series.append({
                    'label': f"vg={prof['vg_v']} vd={prof['vd_v']}"
                             ' (Laplace eq.(5))',
                    'dashed': True,
                    'points': [{'x': float(x), 'y': float(e)}
                               for x, e in zip(xs, ec_l)]})
    scf_series = [{
        'label': f"vg={p['vg_v']} vd={p['vd_v']} (SCF)",
        'points': [{'x': x, 'y': e}
                   for x, e in zip(p['x_nm'], p['ec_ev'])]}
        for p in profiles[:4]]
    return {
        'axes': {
            'x': {'label': 'x', 'unit': 'nm', 'scale': 'linear',
                  'min': None, 'max': None},
            'y': {'label': 'Ec', 'unit': 'eV', 'scale': 'linear',
                  'min': None, 'max': None},
            'from_publication': 'our own D13 output — no paper '
                                'axes to replicate',
        },
        'paperSeries': [],
        'modelSeries': scf_series + laplace_series,
        'residuals': [],
        'sourceRow': best.name,
        'limits': ['the EXPECTED characteristic: the SCF profile '
                   'sits ABOVE its dashed Laplace seed inside the '
                   'gated region (charge raises the barrier; '
                   'self-limited at on-state)',
                   'profiles are the worker\'s ~48-node '
                   'downsample'],
    }


#: The registry: every figure the module cites for proofing, with
#: an honest status. 'replica' = paper points + model on paper
#: axes; 'model-only' = our curve, paper curve not digitized;
#: 'refusing' = nothing plottable yet, missing step named.
#: needs_manager entries are ROW-BACKED and refuse until their
#: run exists.
FIGURE_REGISTRY = [
    {'id': 'vs1-fig7a', 'status': 'replica',
     'title': '[VS1] Fig.7(a) — Id-Vds families, Lg 15 nm '
              '(digitized) vs VS model',
     'citation': {'source': _VS1, 'underlying_data': _FC10,
                  'doi': '10.1109/TED.2015.2457453',
                  'figure': 'Fig.7(a)'},
     'builder': _fig7a},
    {'id': 'fc10-vxo-vs-lg', 'status': 'replica',
     'title': 'v_xo vs Lg — [FC10] reported anchors vs eq.(9) '
              '(incl. the honest 3 um misfit)',
     'citation': {'source': _VS1, 'underlying_data': _FC10,
                  'doi': '10.1109/TED.2015.2457453',
                  'figure': 'Fig.7(a)-(c) contexts'},
     'builder': _vxo_vs_lg},
    {'id': 'vs1-fig9-cgg', 'status': 'model-only',
     'title': '[VS1] Fig.9 — Cgg(Vgs) quantum-capacitance shape '
              '(paper curve not digitized)',
     'citation': {'source': _VS1,
                  'doi': '10.1109/TED.2015.2457453',
                  'figure': 'Fig.9'},
     'builder': _fig9_cgg},
    {'id': 'd13-scf-profile', 'status': 'model-only',
     'title': 'D13 — converged SCF barrier vs its Laplace seed '
              '(row-backed)',
     'citation': {'source': 'polari cntfet chip-1 (own output)',
                  'doi': '', 'figure': 'Ec(x) profiles'},
     'needs_manager': True,
     'builder': _d13_profile},
    {'id': 'fiori05-transfer', 'status': 'refusing',
     'title': 'Fiori 2005 — ballistic NEGF transfer '
              'characteristics (NOT digitized)',
     'citation': {'source': _FIORI,
                  'doi': '10.1109/IEDM.2005.1609397',
                  'figure': 'transfer/output curves'},
     'refusal': 'curves not digitized — digitizing extracted '
                'values from the paper figures (cited rows, '
                'paper-storage rule) is the queued step; scalar '
                'anchors from the text are already in as '
                'NEGF-oracle-literature rows',
     'builder': None},
    {'id': 'fc10-original-idvg', 'status': 'refusing',
     'title': '[FC10] original Id-Vg families (NOT digitized)',
     'citation': {'source': _FC10, 'doi': '10.1038/nnano.2010.220',
                  'figure': 'original Id-Vg'},
     'refusal': 'only the [VS1] REPLOT of the [FC10] output '
                'data is digitized (vs1-fig7a); the original '
                'figures still refuse until they get the same '
                'D18 treatment',
     'builder': None},
]


def figure_points(figure_id, manager=None):
    """The figure flattened to LONG-FORM rows for the ORIGINAL
    graphs design (GraphDefinition + graph-renderer): one row per
    point with series/style/dash and the digitization error
    interval as y_lo/y_hi columns — exactly the dimensions the
    seeded GraphDefinition rows name. Refusals pass through."""
    fig = build_figure(figure_id, manager=manager)
    if not fig.get('ok'):
        return fig
    rows = []
    for series in fig.get('modelSeries', []):
        for pt in series['points']:
            rows.append({'series': series['label'],
                         'style': 'lineY',
                         'dash': bool(series.get('dashed')),
                         'x': pt['x'], 'y': pt['y'],
                         'y_lo': None, 'y_hi': None})
    for series in fig.get('paperSeries', []):
        sigma = series.get('sigmaY_ua') or 0
        for pt in series['points']:
            rows.append({'series': series['label'],
                         'style': 'dot', 'dash': False,
                         'x': pt['x'], 'y': pt['y'],
                         'y_lo': pt['y'] - sigma if sigma else None,
                         'y_hi': pt['y'] + sigma if sigma else None})
    return {'ok': True, 'figure': figure_id,
            'title': fig['title'], 'citation': fig['citation'],
            'limits': fig.get('limits', []),
            'residuals': fig.get('residuals', []),
            'rows': rows}


def _figure_graph(figure_id, description, x_label, y_label,
                  x_type='linear'):
    """One seeded GraphDefinition row in the wrapped {graphConfig}
    form the Graphs editor round-trips (the msim precedent) — the
    figure graphs stay CONFIGURABLE rows, not component code."""
    return {
        'name': f'cntfet-figure-{figure_id}',
        'description': description + ' — data: /api/cntfet/'
                       f'figures/{figure_id}/points',
        'source_class': 'CNTFETSimResult',
        'definition': json.dumps({'graphConfig': {
            'renderStyle': 'lineY',
            'xDimension': 'x',
            'yDimensions': ['y'],
            'seriesDimension': 'series',
            'styleDimension': 'style',
            'errorLoDimension': 'y_lo',
            'errorHiDimension': 'y_hi',
            'seriesColors': [],
            'options': {'showLegend': True, 'showGrid': True,
                        'xLabel': x_label, 'yLabel': y_label,
                        'xType': x_type},
            'aggregation': None,
        }}),
    }


#: GraphDefinition seeds for the replica figures — rendered by the
#: original graphs machinery, editable on the Graphs page.
SEED_CNTFET_FIGURE_GRAPHS = [
    _figure_graph(
        'vs1-fig7a',
        'Replica: [VS1] Fig.7(a) digitized Id-Vds families (with '
        'error bars) vs the VS model in the anchor context',
        'Vds (V)', 'Id (uA)'),
    _figure_graph(
        'fc10-vxo-vs-lg',
        'v_xo vs Lg: the [FC10] reported anchors vs eq.(9) — the '
        'out-of-domain 3 um misfit plotted, not hidden',
        'Lg (nm)', 'v_xo (m/s)', x_type='log'),
    _figure_graph(
        'vs1-fig9-cgg',
        'Cgg(Vgs) quantum-capacitance shape (model-only — the '
        '[VS1] Fig.9 curve is not digitized, the claim is the '
        'peak-then-decline shape)',
        'Vgs (V)', 'Cgg (F)'),
    _figure_graph(
        'd13-scf-profile',
        'D13: the converged SCF barrier vs its dashed Laplace '
        'seed (row-backed — refuses until an SCF run exists)',
        'x (nm)', 'Ec (eV)'),
]


def figures_index():
    """The proofing dashboard's table of contents: every cited
    figure with its honest status."""
    return {'ok': True, 'figures': [
        {k: f[k] for k in ('id', 'status', 'title', 'citation')}
        | ({'refusal': f['refusal']} if f['status'] == 'refusing'
           else {})
        for f in FIGURE_REGISTRY]}


def build_figure(figure_id, manager=None):
    """One figure's chart payload — or its refusal, verbatim."""
    entry = next((f for f in FIGURE_REGISTRY
                  if f['id'] == figure_id), None)
    if entry is None:
        return {'ok': False,
                'error': f'no figure "{figure_id}" — see '
                         f'/api/cntfet/figures for the registry'}
    if entry['status'] == 'refusing':
        return {'ok': False, 'id': entry['id'],
                'status': 'refusing', 'title': entry['title'],
                'citation': entry['citation'],
                'refusal': entry['refusal']}
    if entry.get('needs_manager'):
        if manager is None:
            return {'ok': False, 'id': entry['id'],
                    'status': 'refusing',
                    'title': entry['title'],
                    'citation': entry['citation'],
                    'refusal': 'row-backed figure needs the live '
                               'manager (API context)'}
        payload = entry['builder'](manager)
    else:
        payload = entry['builder']()
    if 'refusal' in payload:
        return {'ok': False, 'id': entry['id'],
                'status': 'refusing', 'title': entry['title'],
                'citation': entry['citation'],
                'refusal': payload['refusal']}
    payload.update({'ok': True, 'id': entry['id'],
                    'status': entry['status'],
                    'title': entry['title'],
                    'citation': entry['citation']})
    return payload
