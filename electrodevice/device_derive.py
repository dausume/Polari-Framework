"""
@module electrodevice.device_derive

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
  - electrodevice.spice_run (subckt for netlists)
  - electrodevice.selftest_electrodevice
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


def derive_device(manager, device, executor=None):
    """Run the material sim and stamp the device parameters.
    `executor` injects a fake in selftests; production uses the real
    msci execute_model."""
    if executor is None:
        from materialsScience.model_execution import execute_model
        executor = execute_model
    if getattr(device, 'device_type', '') != 'resistor':
        return {'ok': False,
                'error': f'device_type "{device.device_type}" not '
                         'supported yet (resistor only — capacitor/'
                         'diode are the next rungs)'}
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


def render_card(device):
    """The embeddable SPICE abstraction (.subckt) of the device."""
    if not device.derived_at:
        return None
    prov = json.loads(device.provenance_json or '{}')
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
