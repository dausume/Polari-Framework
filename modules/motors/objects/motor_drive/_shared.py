"""@module motors.objects.motor_drive._shared — what the motor_drive row classes share (constants, seeds, helpers); split from motor_drive_basis.py (sap-2c)."""
from magnetics.custom.magnet_analysis import _named, _rows
import json

CONTROLLER_BOARDS = ('simplefoc-shield-v2', 'simplefoc-mini',
                     'mks-dual-foc-clone')
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
