"""
@module motors.motor_drive_basis

mag-6: DRIVE AS DATA — SimpleFOC first (Dustin: the open-source FOC
stack IS the v1 controller; rank open-source-non-polari — exactly
what stage 0/1 should buy, not build), FPGA timing = the escalation
rung, named not promised.

- MotorControllerProfile rows: board + firmware params as DATA so a
  design GENERATES its SimpleFOC config snippet (pole pairs from
  the design's own params, AS5600 sensor, current/voltage limits).
- PhaseBindingDefinition rows: motor phase -> shield terminal (the
  level_bridge mirror); the FPGA PWM channel column exists for the
  escalation and stays empty until that rung is real.
- Honesty: M0's Lavet stepper needs NO FOC (a 1 Hz alternating
  pulse source drives it — 555/Arduino class); asking for its FOC
  config REFUSES saying exactly that. Hardware-facing rows are
  knobs + suggestions, never auto-acting; simulation-only until
  hardware tiers say otherwise.

@consumers motors.motor_api, polariServer
"""

import json

from objectTreeDecorators import treeObject, treeObjectInit

from magnetics.custom.magnet_analysis import _named, _rows

CONTROLLER_BOARDS = ('simplefoc-shield-v2', 'simplefoc-mini',
                     'mks-dual-foc-clone')


class MotorControllerProfile(treeObject):
    @treeObjectInit
    def __init__(self, name='', display_name='',
                 board='simplefoc-shield-v2', sensor='as5600-i2c',
                 supply_voltage_v=12.0, current_limit_a=1.0,
                 voltage_limit_v=6.0, velocity_limit_rad_s=20.0,
                 item_ref='simplefoc-driver-board',
                 is_prior=True, provenance_id='', notes='',
                 manager=None):
        self.name = name
        self.display_name = display_name
        self.board = (board if board in CONTROLLER_BOARDS
                      else 'simplefoc-shield-v2')
        self.sensor = sensor
        self.supply_voltage_v = supply_voltage_v
        self.current_limit_a = current_limit_a
        self.voltage_limit_v = voltage_limit_v
        self.velocity_limit_rad_s = velocity_limit_rad_s
        #: supplychain vocabulary — the mag-1 citations price it.
        self.item_ref = item_ref
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes


class PhaseBindingDefinition(treeObject):
    @treeObjectInit
    def __init__(self, name='', design_ref='', phase='A',
                 shield_terminal='', fpga_pwm_channel='',
                 is_prior=True, provenance_id='', notes='',
                 manager=None):
        self.name = name
        self.design_ref = design_ref
        self.phase = phase
        self.shield_terminal = shield_terminal
        #: EMPTY until the FPGA escalation rung is real — named,
        #: not promised (hardware architecture seam).
        self.fpga_pwm_channel = fpga_pwm_channel
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes


SEED_CONTROLLER_PROFILES = [
    {'name': 'simplefoc-v2-default',
     'display_name': 'SimpleFOC Shield v2 — bench defaults',
     'board': 'simplefoc-shield-v2', 'sensor': 'as5600-i2c',
     'supply_voltage_v': 12.0, 'current_limit_a': 1.0,
     'voltage_limit_v': 6.0, 'velocity_limit_rad_s': 20.0,
     'item_ref': 'simplefoc-driver-board',
     'is_prior': True, 'provenance_id': 'mag-6',
     'notes': 'Official board EUR 20 (out of stock at cite time — '
              'clone est \$30.49, mag-1); conservative bench '
              'limits, every value a knob.'},
    {'name': 'mks-clone-default',
     'display_name': 'MKS clone — bench defaults',
     'board': 'mks-dual-foc-clone', 'sensor': 'as5600-i2c',
     'supply_voltage_v': 12.0, 'current_limit_a': 1.5,
     'voltage_limit_v': 7.0, 'velocity_limit_rad_s': 30.0,
     'item_ref': 'simplefoc-driver-board',
     'is_prior': True, 'provenance_id': 'mag-6', 'notes': ''},
]

#: M1's three phases on the shield; M3 wires its two stator sets in
#: PARALLEL onto one controller (v1 per the plan; two synced
#: controllers = v2).
SEED_PHASE_BINDINGS = [
    {'name': f'm1-phase-{p.lower()}', 'design_ref':
     'reluctance-6s4p-m1', 'phase': p,
     'shield_terminal': t, 'fpga_pwm_channel': '',
     'is_prior': True, 'provenance_id': 'mag-6', 'notes': ''}
    for p, t in (('A', 'M1-A'), ('B', 'M1-B'), ('C', 'M1-C'))
] + [
    {'name': f'm3-phase-{p.lower()}', 'design_ref':
     'dual-stator-axial-m3', 'phase': p, 'shield_terminal': t,
     'fpga_pwm_channel': '',
     'is_prior': True, 'provenance_id': 'mag-6',
     'notes': 'both stator sets in parallel (v1); two synced '
              'controllers = the v2 control-authority story'}
    for p, t in (('A', 'M1-A'), ('B', 'M1-B'), ('C', 'M1-C'))
]


def simplefoc_config(manager, design_name, profile_name=''):
    """Generate the SimpleFOC Arduino config snippet for a design —
    pole pairs from the design row, sensor/limits from the profile.
    M0 refuses: a Lavet stepper is driven by a plain alternating
    pulse, FOC is the wrong tool and the refusal says so."""
    design = _named(manager, 'MotorDesignDefinition', design_name)
    if design is None:
        return {'ok': False,
                'refusal': f'no MotorDesignDefinition named '
                           f'"{design_name}"'}
    if getattr(design, 'topology', '') == 'lavet-clock-stepper':
        return {'ok': False,
                'refusal': 'M0 Lavet stepper needs NO FOC — drive '
                           'it with a 1 Hz alternating pulse '
                           '(555/Arduino class, in its build '
                           'requirements); FOC starts at M1',
                'suggestion': {'knob': 'design selection',
                               'action': 'ask for M1..M3'}}
    profiles = _rows(manager, 'MotorControllerProfile')
    profile = (_named(manager, 'MotorControllerProfile',
                      profile_name) if profile_name
               else (profiles[0] if profiles else None))
    if profile is None:
        return {'ok': False,
                'refusal': 'no MotorControllerProfile row — seed '
                           'or name one'}
    params = json.loads(getattr(design, 'params_json', '{}') or
                        '{}')
    pole_pairs = int(params.get('poles', 4)) // 2
    bindings = [b for b in _rows(manager, 'PhaseBindingDefinition')
                if getattr(b, 'design_ref', '') == design_name]
    snippet = '\n'.join([
        '// GENERATED from MotorDesignDefinition '
        f'"{design_name}" + profile '
        f'"{getattr(profile, "name", "")}" — edit the ROWS, not '
        'this file.',
        '#include <SimpleFOC.h>',
        f'BLDCMotor motor = BLDCMotor({pole_pairs});',
        'BLDCDriver3PWM driver = BLDCDriver3PWM(9, 5, 6, 8);',
        'MagneticSensorI2C sensor = MagneticSensorI2C('
        'AS5600_I2C);',
        'void setup() {',
        '  sensor.init(); motor.linkSensor(&sensor);',
        f'  driver.voltage_power_supply = '
        f'{getattr(profile, "supply_voltage_v", 12.0)};',
        '  driver.init(); motor.linkDriver(&driver);',
        f'  motor.voltage_limit = '
        f'{getattr(profile, "voltage_limit_v", 6.0)};',
        f'  motor.current_limit = '
        f'{getattr(profile, "current_limit_a", 1.0)};',
        f'  motor.velocity_limit = '
        f'{getattr(profile, "velocity_limit_rad_s", 20.0)};',
        '  motor.controller = MotionControlType::velocity;',
        '  motor.init(); motor.initFOC();',
        '}',
        'void loop() { motor.loopFOC(); motor.move(2.0); }',
    ])
    return {'ok': True, 'design': design_name,
            'profile': getattr(profile, 'name', ''),
            'board': getattr(profile, 'board', ''),
            'polePairs': pole_pairs,
            'phaseBindings': [
                {'phase': getattr(b, 'phase', ''),
                 'shieldTerminal': getattr(b, 'shield_terminal',
                                           ''),
                 'fpgaPwmChannel': getattr(b, 'fpga_pwm_channel',
                                           '') or
                 '(escalation rung — named, not wired)'}
                for b in sorted(bindings,
                                key=lambda b: getattr(b, 'phase',
                                                      ''))],
            'configSnippet': snippet,
            'honesty': 'simulation/config-generation only — no '
                       'hardware is acted on; flashing and wiring '
                       'are the builder\'s explicit steps; dual-'
                       'stator v1 parallels both sets on one '
                       'controller'}
