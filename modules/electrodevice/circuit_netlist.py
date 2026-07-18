"""
@module electrodevice.circuit_netlist

ncg-4: the DATA-DRIVEN netlist generator + runner — circuit rows in,
SPICE out, through the registered 'circuit-netlist' compiler. The
hand-coded renderers in spice_run.py stay until the row form proves
byte-equivalent currents (the regression this module's selftest
pins); new circuits are rows from day one.

Honesty rules: a 'device' component whose ElectronicDeviceDefinition
was never derived is a plain error naming the derive act; pins on
UNDECLARED nets are a suggestion riding the result (declare the
CircuitNetDefinition row or fix the typo); ngspice absence is the
capability-honest error spice_run already speaks.
"""

import json
import os
import re
import subprocess
import tempfile

from electrodevice.spice_run import LED_MODEL, capability, ngspice_bin

_NAME_VALUE = re.compile(r'^([a-z0-9_()\[\].]+)\s*=\s*'
                         r'([-+0-9.eE]+)', re.IGNORECASE | re.MULTILINE)


def _rows(manager, class_name):
    table = (manager.objectTables or {}).get(class_name, {})
    return list(table.values()) if isinstance(table, dict) else list(table)


def circuit_rows(manager, circuit_name):
    circuit = next((c for c in _rows(manager, 'CircuitDefinition')
                    if getattr(c, 'name', '') == circuit_name), None)
    if circuit is None:
        raise ValueError(f"no CircuitDefinition named "
                         f"'{circuit_name}'")
    components = sorted(
        (c for c in _rows(manager, 'CircuitComponentDefinition')
         if getattr(c, 'circuit_name', '') == circuit_name),
        key=lambda c: getattr(c, 'name', ''))
    if not components:
        raise ValueError(f"circuit '{circuit_name}' has no "
                         f'CircuitComponentDefinition rows')
    nets = [n for n in _rows(manager, 'CircuitNetDefinition')
            if getattr(n, 'circuit_name', '') == circuit_name]
    return circuit, components, nets


def _device_card(manager, device_name):
    from electrodevice.device_derive import render_card, subckt_name
    device = next((d for d in _rows(manager,
                                    'ElectronicDeviceDefinition')
                   if getattr(d, 'name', '') == device_name), None)
    if device is None:
        raise ValueError(f"component references unknown device "
                         f"'{device_name}'")
    card = render_card(device)
    if card is None:
        raise ValueError(
            f"device '{device_name}' has never been derived — POST "
            f'{{"action": "derive"}} to '
            f'/api/electrodevice/devices/{device_name} first')
    return card, subckt_name(device)


_PREFIX = {'vsource': 'V', 'resistor': 'R', 'capacitor': 'C',
           'inductor': 'L', 'diode': 'D', 'led': 'D', 'device': 'X'}


def _require(component, params, key):
    """A missing electrical value is a plain error naming the row
    and the param — NEVER a silent default (a defaulted vsource is a
    dead source that runs 'successfully')."""
    if key not in params:
        raise ValueError(
            f"component '{component.name}' ({component.kind}): "
            f'params_json is missing required {key!r} — set it on '
            f'the row')
    return params[key]


def _element_line(component, pins, params, sub=None):
    kind = component.kind
    # Row names are kebab-case; SPICE element names are not.
    ref = _PREFIX[kind] + component.name.replace('-', '_')
    nodes = ' '.join(pins)
    if kind == 'vsource':
        return f"{ref} {nodes} DC {_require(component, params, 'dc')}"
    if kind == 'resistor':
        return (f'{ref} {nodes} '
                f"{_require(component, params, 'ohms')}")
    if kind == 'capacitor':
        ic = (f" ic={params['ic']}" if 'ic' in params else '')
        return (f'{ref} {nodes} '
                f"{_require(component, params, 'farads')}{ic}")
    if kind == 'inductor':
        return (f'{ref} {nodes} '
                f"{_require(component, params, 'henries')}")
    if kind in ('diode', 'led'):
        model = params.get('model', 'polari_led')
        return f'{ref} {nodes} {model}'
    return f'{ref} {nodes} {sub}'


def render_circuit(manager, circuit_name):
    """Rows -> {'netlist', 'suggestions'} (compiler-ready)."""
    circuit, components, nets = circuit_rows(manager, circuit_name)
    declared = {getattr(n, 'net', '') for n in nets} | {'0'}
    cards, lines, undeclared = [], [], set()
    needs_led_model = False
    for component in components:
        kind = getattr(component, 'kind', '')
        if kind not in _PREFIX:
            kinds = ', '.join(sorted(_PREFIX))
            raise ValueError(
                f"component '{component.name}': unknown kind "
                f"'{kind}' (kinds: {kinds})")
        params = json.loads(getattr(component, 'params_json', '{}')
                            or '{}')
        pins = json.loads(getattr(component, 'pins_json', '[]')
                          or '[]')
        undeclared |= {p for p in pins if p not in declared}
        sub = None
        if kind == 'device':
            card, sub = _device_card(manager, component.device_name)
            if card not in cards:
                cards.append(card)
        if kind in ('diode', 'led') \
                and params.get('model', 'polari_led') == 'polari_led':
            needs_led_model = True
        lines.append(_element_line(component, pins, params, sub))
    analyses = json.loads(getattr(circuit, 'analyses_json', '[]')
                          or '[]')
    probes = json.loads(getattr(circuit, 'probes_json', '[]') or '[]')
    control = ['.control']
    uses_ic = any('ic=' in line for line in lines)
    for analysis in analyses:
        if not isinstance(analysis, dict) or 'type' not in analysis:
            raise ValueError(
                f"circuit '{circuit_name}': analysis entries must "
                f'be dicts with a "type" — got {analysis!r}')
        if analysis['type'] == 'op':
            control.append('op')
            control += [f'print {p}' for p in probes]
        elif analysis['type'] == 'tran':
            if 'args' not in analysis:
                raise ValueError(
                    f"circuit '{circuit_name}': tran analysis needs "
                    f'"args" (e.g. "0.1m 60m")')
            control.append(f"tran {analysis['args']}"
                           + (' uic' if uses_ic else ''))
            if analysis.get('meas'):
                control.append(f"meas {analysis['meas']}")
        else:
            raise ValueError(
                f"circuit '{circuit_name}': unknown analysis type "
                f"'{analysis['type']}'")
    control += ['quit', '.endc']
    netlist = '\n'.join(
        [f'* Generated by Polari electrodevice.circuit_netlist from '
         f'circuit rows "{circuit_name}" — edit the rows, not this '
         f'file.']
        + cards + ([LED_MODEL] if needs_led_model else [])
        + lines + control + ['.end', ''])
    suggestions = []
    if undeclared:
        suggestions.append({
            'knob': 'CircuitNetDefinition',
            'action': f'nets {sorted(undeclared)} are wired but '
                      f'undeclared — declare them (or fix the pin '
                      f'typo)'})
    return {'netlist': netlist, 'suggestions': suggestions}


def compile_circuit(domain_rows):
    """Compiler-contract entry ('circuit-netlist'):
    {'manager', 'circuit_name'} -> netlist artifact."""
    manager = domain_rows['manager']
    circuit_name = domain_rows['circuit_name']
    rendered = render_circuit(manager, circuit_name)
    return {'definition': None,
            'artifacts': [{'kind': 'spice-netlist',
                           'name': f'{circuit_name}.cir',
                           'text': rendered['netlist']}],
            'suggestions': rendered['suggestions']}


SEED_CIRCUIT_COMPILER = {
    'name': 'circuit-netlist',
    'domain': 'circuit',
    'compiler_ref': 'electrodevice.circuit_netlist:compile_circuit',
    'description': 'CircuitComponentDefinition/CircuitNetDefinition '
                   'rows -> a runnable SPICE netlist; device '
                   'components pull their msci-derived subckt cards '
                   '(provenance attached).',
    'enabled': True,
}


def run_netlist(netlist, label='circuit'):
    """Run any generated netlist via ngspice -> {'ok',
    'measurements'} (flat name->value; one print/meas per line).
    Shared by circuits (ncg-4) and breadboards (ncg-5)."""
    binary = ngspice_bin()
    if binary is None:
        return {'ok': False,
                'error': 'ngspice not available on this node',
                'capability': capability()}
    with tempfile.TemporaryDirectory() as td:
        path = os.path.join(td, f'{label}.cir')
        with open(path, 'w') as fh:
            fh.write(netlist)
        proc = subprocess.run([binary, '-b', path],
                              capture_output=True, text=True,
                              timeout=120)
    measurements = {name.lower(): float(value) for name, value
                    in _NAME_VALUE.findall(proc.stdout or '')}
    ok = proc.returncode == 0 and bool(measurements)
    result = {'ok': ok, 'measurements': measurements}
    if not ok:
        result['error'] = ('ngspice produced no parseable '
                           'measurements; tail: '
                           + (proc.stdout or proc.stderr
                              or '')[-300:])
    return result


def run_circuit(manager, circuit_name):
    """Render from rows and RUN via ngspice."""
    try:
        rendered = render_circuit(manager, circuit_name)
    except ValueError as exc:
        return {'ok': False, 'error': str(exc)}
    except KeyError as exc:  # defense: a row shape we didn't foresee
        return {'ok': False,
                'error': f'circuit rows are missing required key '
                         f'{exc} — check the row json fields'}
    result = run_netlist(rendered['netlist'], label=circuit_name)
    result.update({'circuit': circuit_name,
                   'netlist': rendered['netlist'],
                   'suggestions': rendered['suggestions']})
    return result
