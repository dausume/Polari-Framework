"""
@module electrodevice.level_bridge

ncg-6: the CROSS-LEVEL COUPLING — "the FPGA design you drew drives
the circuit you plugged in." A PinBindingDefinition row declares
that one bit of a LogicBlockDesign output node drives one voltage
source (a breadboard placement or a circuit component): logic 1 =
vdd on that source, logic 0 = 0 V. Driving a circuit = evaluate the
design (hwdigital.logic_sim, the same reference the verilated bench
answers to), set the bound sources, run the netlist, and judge LED
currents against the honest window — the verdict rides back as an
EVIDENCE-BEARING SUGGESTION on the result, never an auto-applied
change ([[knobs-and-suggestions]]).

This generalizes hwsim-led's `<register>_pins` trick from one
hand-wired register to ANY design output × ANY circuit source.

@consumers
  - electrodevice.circuit_api (the drive act)
  - polariNoCode.nocode_tests (circuit test subjects, ncg-6)
  - polariServer (registration + seed)
"""

import json

from objectTreeDecorators import treeObject, treeObjectInit

from electrodevice.spice_run import LED_MAX_A, LED_MIN_A


class PinBindingDefinition(treeObject):
    """One design-output bit -> one driven source. A row, so the
    coupling is inspectable and editable AT the object."""

    @treeObjectInit
    def __init__(self, name: str = '', design_name: str = '',
                 output_node: str = '', bit: int = 0,
                 # 'placement' (ComponentPlacement) or 'component'
                 # (CircuitComponentDefinition); the target must be
                 # a 'vsource'.
                 target_kind: str = 'placement',
                 target_name: str = '', vdd: float = 3.3,
                 description: str = '', manager=None):
        self.name = name
        self.design_name = design_name
        self.output_node = output_node
        self.bit = bit
        self.target_kind = target_kind
        self.target_name = target_name
        self.vdd = vdd
        self.description = description


_TARGET_TABLE = {'placement': 'ComponentPlacement',
                 'component': 'CircuitComponentDefinition'}


def _rows(manager, class_name):
    table = (manager.objectTables or {}).get(class_name, {})
    return list(table.values()) if isinstance(table, dict) else list(table)


def bindings_for(manager, design_name):
    return sorted(
        (b for b in _rows(manager, 'PinBindingDefinition')
         if getattr(b, 'design_name', '') == design_name),
        key=lambda b: getattr(b, 'name', ''))


def _apply_binding(manager, binding, outputs, specs):
    """Set one bound source for THIS run. The mutation is TRANSIENT:
    the caller snapshots+restores params_json around the ngspice run
    — the authored row must read back unchanged after a drive.
    Returns (applied_entry, target_row, original_params_json)."""
    table_name = _TARGET_TABLE.get(getattr(binding, 'target_kind',
                                           ''))
    if table_name is None:
        raise ValueError(
            f"binding '{binding.name}': target_kind must be "
            f"'placement' or 'component'")
    target = next((t for t in _rows(manager, table_name)
                   if getattr(t, 'name', '')
                   == binding.target_name), None)
    if target is None:
        raise ValueError(f"binding '{binding.name}': no "
                         f'{table_name} named '
                         f"'{binding.target_name}'")
    if getattr(target, 'kind', '') != 'vsource':
        raise ValueError(
            f"binding '{binding.name}': target "
            f"'{binding.target_name}' is a "
            f"'{getattr(target, 'kind', '')}' — only vsource "
            f'targets can be driven')
    if binding.output_node not in outputs:
        raise ValueError(
            f"binding '{binding.name}': design has no output node "
            f"'{binding.output_node}' (outputs: "
            f'{sorted(outputs)})')
    width = specs[binding.output_node]['width']
    if not 0 <= int(binding.bit) < width:
        raise ValueError(
            f"binding '{binding.name}': bit {binding.bit} is "
            f"outside output '{binding.output_node}' "
            f'(width {width}, bits 0..{width - 1})')
    bit = (outputs[binding.output_node] >> int(binding.bit)) & 1
    volts = float(binding.vdd) if bit else 0.0
    original = getattr(target, 'params_json', '{}') or '{}'
    params = json.loads(original)
    params['dc'] = volts
    target.params_json = json.dumps(params)
    return ({'binding': binding.name, 'bit': bit, 'volts': volts,
             'target': binding.target_name}, target, original)


def _led_verdict(measurements):
    """Judge probed CURRENTS against the LED window — voltage (or
    other) probes are ignored, a 3.3 V rail is not a 3300 mA leg.
    Sources at 0 V legitimately conduct ~nothing — only driven legs
    (|I| above a tenth of the window floor) are judged."""
    lit, out_of_range = [], []
    for name, value in measurements.items():
        if not name.startswith('i('):
            continue
        amps = abs(value)
        if amps < LED_MIN_A / 10:
            continue
        lit.append(name)
        if not LED_MIN_A <= amps <= LED_MAX_A:
            out_of_range.append(f'{name}={amps * 1e3:.3f}mA')
    if not lit:
        return 'no-legs-driven', None
    if out_of_range:
        return 'current-out-of-range', {
            'knob': 'the driven device geometry '
                    '(/api/electrodevice/devices/{name}) or the '
                    'binding vdd',
            'action': f'legs outside the {LED_MIN_A * 1e3:.0f}-'
                      f'{LED_MAX_A * 1e3:.0f} mA LED window: '
                      f'{", ".join(out_of_range)}'}
    return 'all-driven-legs-in-range', None


#: The drive act clocks a bounded number of steps per call — an
#: unbounded steps payload would pin the worker re-settling the
#: whole design a billion times.
MAX_DRIVE_STEPS = 10000


def drive_boards_from_design(manager, design_name, inputs,
                             board_names, steps=0, probes=None):
    """Evaluate the design -> set every bound source (TRANSIENTLY —
    the authored rows are restored after the run) -> run the boards
    -> LED-window verdict + suggestion. `steps` clocks a clocked
    design before reading outputs. With `probes` omitted, one
    current probe per bound source is generated, so the act works
    standalone."""
    from hwdigital.logic_sim import LogicSimulator, design_specs
    from electrodevice.breadboard_netlist import run_breadboards
    try:
        steps = int(steps)
    except (TypeError, ValueError):
        return {'ok': False,
                'error': f'steps must be an integer, got {steps!r}'}
    if not 0 <= steps <= MAX_DRIVE_STEPS:
        return {'ok': False,
                'error': f'steps={steps} refused — the drive act '
                         f'clocks at most {MAX_DRIVE_STEPS} steps '
                         f'per call'}
    if inputs is not None and not isinstance(inputs, dict):
        return {'ok': False,
                'error': f'inputs must be a dict of '
                         f'{{input node: int}}, got '
                         f'{type(inputs).__name__}'}
    bad_values = [k for k, v in (inputs or {}).items()
                  if not isinstance(v, int)]  # bool is int (0/1) —
    if bad_values:                            # fine as a logic level
        return {'ok': False,
                'error': f'input values must be ints '
                         f'(bad: {sorted(bad_values)})'}
    touched = []
    try:
        try:
            specs = design_specs(manager, design_name)
            sim = LogicSimulator(specs)
            sim.set_inputs(**(inputs or {}))
            for _ in range(steps):
                sim.step()
            outputs = sim.outputs()
            bindings = bindings_for(manager, design_name)
            if not bindings:
                return {'ok': False,
                        'error': f"design '{design_name}' has no "
                                 f'PinBindingDefinition rows',
                        'suggestion': {
                            'knob': 'PinBindingDefinition',
                            'action': 'bind an output node bit to a '
                                      'vsource placement/component'}}
            applied = []
            for binding in bindings:
                entry, target, original = _apply_binding(
                    manager, binding, outputs, specs)
                # Snapshot FIRST-so a failing later binding still
                # restores the earlier ones (no partial mutation
                # survives an error).
                touched.append((target, original))
                applied.append(entry)
        except ValueError as exc:
            return {'ok': False, 'error': str(exc)}
        if probes is None:
            probes = [f"i(v{e['target'].replace('-', '_')})"
                      for e in applied]
        run = run_breadboards(manager, board_names, probes=probes)
        if not run.get('ok'):
            return run
        verdict, suggestion = _led_verdict(run['measurements'])
        result = {'ok': True, 'design': design_name,
                  'designOutputs': outputs, 'applied': applied,
                  'verdict': verdict,
                  'measurements': run['measurements'],
                  'boards': board_names}
        if run.get('suggestions'):
            result['boardSuggestions'] = run['suggestions']
        if suggestion:
            result['suggestion'] = suggestion
        return result
    finally:
        # The drive is an ACT, not an edit: put the authored voltage
        # back on every touched row, whatever path we exited by.
        for target, original in touched:
            target.params_json = original


SEED_PIN_BINDINGS = [
    # demo-counter2 bit 0 drives the single-board LED branch: odd
    # counts light it, even counts leave it dark.
    {'name': 'bind-counter2-bit0-led', 'design_name': 'demo-counter2',
     'output_node': 'cnt2-q', 'bit': 0,
     'target_kind': 'placement', 'target_name': 'bba-vpin',
     'vdd': 3.3,
     'description': 'counter LSB blinks the breadboard LED'},
]
