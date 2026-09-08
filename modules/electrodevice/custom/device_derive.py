"""
@module electrodevice.custom.device_derive

Derivation engine: EXECUTE the device's msci material model (the same
`execute_model` the /api/msci/models API uses — previously-simulated
material data, never hand-typed constants), turn transport properties
into device parameters, and render the SPICE abstraction.

resistor: R = L / (sigma_eff * A) with sigma_eff = the percolation
model's effectiveSigma. Provenance (model inputs, outputs, formula,
and the sim's own validity note) is stamped on the device row AND
into the SPICE card's comments — the netlist says where its numbers
came from.

@consumers
  - electrodevice.device_api (derive/card knob acts)
  - electrodevice.custom.spice_run (subckt for netlists)
  - electrodevice.electrodevice_selftest
"""

import json
from datetime import datetime, timezone


def _now():
    return datetime.now(timezone.utc).isoformat()


def _rows(manager, class_name):
    tables = getattr(manager, 'objectTables', None) or {}
    return (tables.get(class_name) or {})


def _save(manager, row):
    try:
        db = getattr(manager, 'db', None)
        if db is not None:
            db.saveInstanceInDB(row)
    except Exception:
        pass


def get_device(manager, name):
    for row in _rows(manager, 'ElectronicDeviceDefinition').values():
        if getattr(row, 'name', '') == name:
            return row
    return None


def subckt_name(device):
    return 'polari_' + device.name.replace('-', '_')


VDD_REF = 3.3  # the FPGA rail the switching heuristics reference


def derive_device(manager, device, executor=None):
    """Run the material sim(s) and stamp the device parameters.
    `executor` injects a fake in selftests; production uses the real
    msci execute_model."""
    if executor is None:
        from materialsScience.model_execution import execute_model
        executor = execute_model
    kind = getattr(device, 'device_type', '')
    if kind in ('nfet', 'pfet'):
        return _derive_transistor(manager, device, executor)
    if kind != 'resistor':
        return {'ok': False,
                'error': f'device_type "{device.device_type}" not '
                         'supported yet (resistor | nfet | pfet — '
                         'capacitor/diode are the next rungs)'}
    report = executor(manager, device.sim_model)
    if not report.get('ok'):
        return {'ok': False,
                'error': f'material sim "{device.sim_model}" refused',
                'simReport': {k: v for k, v in report.items()
                              if k != 'resolved'}}
    result = report.get('result') or {}
    sigma = float(result.get('effectiveSigma') or 0.0)
    if sigma <= 0.0:
        return {'ok': False,
                'error': 'material sim yielded no positive '
                         'effectiveSigma — below percolation '
                         'threshold? (sweep volumeFraction)',
                'simResult': result}
    length = float(device.length_m)
    area = float(device.cross_section_m2)
    resistance = length / (sigma * area)
    provenance = {
        'simModel': device.sim_model,
        'engine': report.get('engine', ''),
        'simInputs': report.get('inputs', {}),
        'effectiveSigma_S_per_m': sigma,
        'formula': 'R = L / (sigma_eff * A)',
        'length_m': length,
        'cross_section_m2': area,
        'simValidity': result.get('validity', ''),
        'simNote': result.get('note', ''),
    }
    device.sigma_s_per_m = sigma
    device.resistance_ohm = resistance
    device.derived_at = _now()
    device.provenance_json = json.dumps(provenance)
    _save(manager, device)
    return {'ok': True, 'device': device.name,
            'sigma_S_per_m': sigma, 'resistance_ohm': resistance,
            'provenance': provenance}


def _derive_transistor(manager, device, executor):
    """CNT-network FET with a sol-gel gate: on-state channel from
    the percolation sim; threshold sign/magnitude from the derived
    SemiconductorProfile; off-state from the matrix conductivity the
    SAME sim declares. All heuristics named in provenance."""
    from electrodevice.semiconductor_basis import get_profile
    profile = get_profile(manager,
                          getattr(device, 'semiconductor_profile',
                                  ''))
    if profile is None or not getattr(profile, 'derived_at', ''):
        return {'ok': False,
                'error': 'semiconductor profile '
                         f'"{device.semiconductor_profile}" missing '
                         'or never derived',
                'suggestion': {
                    'knob': '/api/electrodevice/semiconductors/'
                            f'{device.semiconductor_profile}',
                    'how': 'POST {"action": "derive"} first'}}
    report = executor(manager, device.sim_model)
    if not report.get('ok'):
        return {'ok': False,
                'error': f'channel sim "{device.sim_model}" refused'}
    result = report.get('result') or {}
    sigma_on = float(result.get('effectiveSigma') or 0.0)
    sigma_off = float(result.get('matrixSigma')
                      or (report.get('inputs') or {})
                      .get('matrixSigma') or 0.0)
    if sigma_on <= 0.0 or sigma_off <= 0.0:
        return {'ok': False,
                'error': 'channel sim lacks on/off conductivities',
                'simResult': result}
    length = float(device.length_m)
    area = float(device.cross_section_m2)
    r_on = length / (sigma_on * area)
    r_off = length / (sigma_off * area)
    gap = float(profile.gap_ev)
    polarity = 1.0 if device.device_type == 'nfet' else -1.0
    vto = polarity * gap / 4.0
    if abs(vto) >= VDD_REF:
        return {'ok': False,
                'error': f'|VTO| {abs(vto):.2f} V >= the {VDD_REF} V '
                         'rail — the gate cannot switch this channel',
                'suggestion': {'knob': 'semiconductor_profile',
                               'how': 'a smaller-gap variant, or '
                                      'raise the rail'}}
    kp = 1.0 / (r_on * (VDD_REF - abs(vto)))
    eps_r, eps_src, eps_context = _dielectric_epsilon(
        manager, device.dielectric_material)
    provenance = {
        'channelSim': device.sim_model,
        'engine': report.get('engine', ''),
        'sigmaOn_S_per_m': sigma_on,
        'sigmaOff_S_per_m': sigma_off,
        'semiconductorProfile': profile.name,
        'gapEv': gap, 'carrierType': profile.carrier_type,
        'formulas': {
            'Ron': 'L/(sigma_on*A) — percolating network',
            'Roff': 'L/(sigma_off*A) — matrix-only leakage',
            'VTO': 'sign(type) * gap/4 — HEURISTIC frontier-gap -> '
                   'switching threshold (order-of-magnitude)',
            'KP': f'1/(Ron*(VDD-|VTO|)) at VDD={VDD_REF} — triode '
                  'on-resistance match',
        },
        'dielectric': {'material': device.dielectric_material,
                       'epsilonR': eps_r, 'source': eps_src,
                       'measurementContext': eps_context,
                       'thickness_m': device.dielectric_thickness_m},
        'simValidity': result.get('validity', ''),
        'profileHonesty': json.loads(
            profile.provenance_json or '{}').get('honesty', ''),
    }
    device.sigma_s_per_m = sigma_on
    device.r_on_ohm = r_on
    device.r_off_ohm = r_off
    device.threshold_v = vto
    device.kp_a_per_v2 = kp
    device.resistance_ohm = r_on
    device.derived_at = _now()
    device.provenance_json = json.dumps(provenance)
    _save(manager, device)
    return {'ok': True, 'device': device.name,
            'threshold_v': vto, 'kp_a_per_v2': kp,
            'r_on_ohm': r_on, 'r_off_ohm': r_off,
            'onOffRatio': r_off / r_on, 'provenance': provenance}


def _dielectric_epsilon(manager, material_name):
    """Gate epsilon_r from a material property row — structured
    records ({value, frequency_hz, temperature_c, measurement_method,
    confidence}) return their measurement CONTEXT alongside the
    number so it rides device provenance and the validator can grade
    confidence. Falls back to a LABELED literature constant (the
    validator flags it — the data gap stays visible)."""
    try:
        tables = getattr(manager, 'objectTables', None) or {}
        for row in (tables.get('MaterialScaleDefinition')
                    or {}).values():
            if getattr(row, 'material_name', '') != material_name:
                continue
            props = json.loads(getattr(row, 'parameters_json', '{}')
                               or '{}')
            for key in ('relativePermittivity', 'dielectricConstant',
                        'epsilonR'):
                if key in props:
                    value = props[key]
                    context = {}
                    if isinstance(value, dict):
                        context = {k: v for k, v in value.items()
                                   if k != 'value'}
                        value = value.get('value')
                    if isinstance(value, (list, tuple)):
                        value = sum(value) / len(value)
                    return float(value), 'material-row', context
    except Exception:
        pass
    return 3.9, 'literature-fallback (fused silica ~3.9)', {}


def render_card(device):
    """The embeddable SPICE abstraction (.subckt) of the device."""
    if not device.derived_at:
        return None
    prov = json.loads(device.provenance_json or '{}')
    if getattr(device, 'device_type', '') in ('nfet', 'pfet'):
        return _render_fet_card(device, prov)
    r = float(device.resistance_ohm)
    return '\n'.join([
        f'* Polari SpiceModelCard — {device.name}',
        f'* DERIVED from simulated material data '
        f'({prov.get("simModel", "?")} via '
        f'{prov.get("engine", "?")}), {device.derived_at}',
        f'* sigma_eff = {device.sigma_s_per_m:.6g} S/m; '
        f'{prov.get("formula", "")} with L='
        f'{device.length_m:g} m, A={device.cross_section_m2:g} m^2',
        f'* validity: {prov.get("simValidity", "")[:100]}',
        f'.subckt {subckt_name(device)} n1 n2',
        f'R1 n1 n2 {r:.6g}',
        '.ends',
        '',
    ])


def _render_fet_card(device, prov):
    kind = 'NMOS' if device.device_type == 'nfet' else 'PMOS'
    sub = subckt_name(device)
    return '\n'.join([
        f'* Polari SpiceModelCard — {device.name} ({kind} switch)',
        f'* DERIVED from simulated material data: channel '
        f'{prov.get("channelSim", "?")}, semiconductor profile '
        f'{prov.get("semiconductorProfile", "?")} (gap '
        f'{prov.get("gapEv", 0):.3f} eV, {prov.get("carrierType")}'
        f'-type), {device.derived_at}',
        f'* Ron {device.r_on_ohm:.6g} / Roff {device.r_off_ohm:.6g} '
        f'ohm; VTO {device.threshold_v:+.3f} V (gap/4 heuristic); '
        f'KP {device.kp_a_per_v2:.6g} A/V^2',
        f'* gate: {prov.get("dielectric", {}).get("material", "?")} '
        f'eps_r {prov.get("dielectric", {}).get("epsilonR", "?")} '
        f'({prov.get("dielectric", {}).get("source", "?")})',
        f'* validity: rough DIGITAL-SEGMENT abstraction — level-1 '
        f'MOSFET; see provenance formulas',
        f'.model {sub}_m {kind}(LEVEL=1 VTO={device.threshold_v:.4g} '
        f'KP={device.kp_a_per_v2:.6g} LAMBDA=0.01)',
        f'.subckt {sub} d g s',
        f'M1 d g s s {sub}_m W=1u L=1u',
        f'R1 d s {device.r_off_ohm:.6g}',
        '.ends',
        '',
    ])


def make_card_row(manager, device, card_factory=None):
    """Version the card as a row (append-only like the contracts)."""
    text = render_card(device)
    if text is None:
        return {'ok': False,
                'error': f'device "{device.name}" has never been '
                         'derived — POST {"action": "derive"} first'}
    versions = [r for r in _rows(manager, 'SpiceModelCard').values()
                if getattr(r, 'device_name', '') == device.name]
    version = max([int(getattr(r, 'version', 0)) for r in versions],
                  default=0) + 1
    if card_factory is None:
        from electrodevice.device_basis import SpiceModelCard
        card_factory = SpiceModelCard
    row = card_factory(
        name=f'{device.name}-spice-v{version}',
        device_name=device.name, version=version, card_text=text,
        derived_from_json=device.provenance_json,
        generated_at=_now(), manager=manager)
    _save(manager, row)
    return {'ok': True, 'card': row.name, 'version': version,
            'cardText': text, 'row': row}
