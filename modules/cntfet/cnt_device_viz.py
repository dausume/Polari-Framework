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


def _device_id_fn(manager, name):
    """(id_fn, device, None) or (None, None, refusal). The refusal
    names the affordance, never a bare 404."""
    if manager is None:
        return None, None, _refuse('no manager — device rows are '
                                   'not reachable')
    device = get_row(manager, 'AlignedCNTFETDevice', name)
    if device is None:
        return None, None, _refuse(f'no device named "{name}"')
    if not getattr(device, 'derived_at', ''):
        return None, None, _refuse(
            f'device "{name}" never derived — POST '
            f'{{"action": "derive"}} to /api/cntfet/devices/'
            f'{name} first')
    rows, missing = resolve_components(manager, device)
    if missing:
        return None, None, _refuse(
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
    return (lambda vg, vd: vs_terminal_current(vg, vd, p)['id_a'],
            device, None)


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


def device_curve_points(manager, name, curve='transfer'):
    """The named-graph-panel data feed for one device."""
    id_fn, device, refusal = _device_id_fn(manager, name)
    if refusal is not None:
        return refusal
    rows = curve_rows_from_fn(id_fn, curve)
    if rows is None:
        return _refuse(f'unknown curve "{curve}" '
                       '(transfer | output)')
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
        'source_class': 'AlignedCNTFETDevice',
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
]
