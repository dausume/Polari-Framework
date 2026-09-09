"""
@module voron.custom.printer_cfg

Render Klipper's printer.cfg for one PrinterDefinition + its PrinterBoard
rows. Pure: rows (or dicts) in, (text, refusals) out — refusals are NAMED
reasons and an empty list means the text is complete; nothing is guessed
(no /dev/ttyACM0 for an unmeasured serial, no pin map for an unmapped
board). Mode `real`: one `[mcu …]` per board (usb → `serial:` by-id path,
canbus → `canbus_uuid:`), the Voron reference pin mapping from
board_pins, the leveling section per model ([quad_gantry_level] for 2.4,
[z_tilt] for Trident). Mode `sim`: ONLY the Linux host MCU as the primary
`[mcu]` (Klipper requires one) and `kinematics: none` — the stack runs,
the printer does not move.
"""
from voron.custom.board_pins import MAIN_BOARD_PINS, TOOLHEAD_BOARD_PINS, Z_STEPPERS

MODELS = tuple(Z_STEPPERS)
MODES = ('real', 'sim')
PROBES = ('tap', 'klicky', 'none')
#: extruder → (rotation_distance, gear_ratio) — the reference values from the Voron / Galileo configs
EXTRUDERS = {'clockwork2': ('22.6789511', '50:10'), 'galileo2': ('47.088', '9:1')}
#: Z rotation_distance (+ gear ratio) per model — belted Z on the 2.4, TR8x4 leadscrews on the Trident, TR8x8 on the V0
Z_DRIVE = {'voron-2.4': ('40', '80:16'), 'voron-trident': ('4', ''), 'voron-0': ('8', ''), 'equivalent-corexy': ('8', '')}
PRINTER_DATA = '/home/printer/printer_data'
HOST_MCU_SERIAL = '/tmp/klipper_host_mcu'
MACROS_FILE = 'macros-voron-standard.cfg'


def _g(obj, key, default=None):
    return obj.get(key, default) if isinstance(obj, dict) else getattr(obj, key, default)


def _mcu_section(b, primary=False):
    name = _g(b, 'mcu_name', '') or 'mcu'
    head = '[mcu]' if primary or name == 'mcu' else '[mcu %s]' % name
    conn = _g(b, 'connection', '')
    if conn == 'canbus':
        return [head, 'canbus_uuid: %s' % _g(b, 'canbus_uuid', ''), '']
    if conn == 'linux':
        return [head, 'serial: %s' % HOST_MCU_SERIAL, '']
    return [head, 'serial: %s' % _g(b, 'serial_by_id', ''), 'restart_method: command', '']


def _stepper(section, pins, extra, current='0.8'):
    out = ['[%s]' % section, 'step_pin: %s' % pins['step'], 'dir_pin: %s' % pins['dir'], 'enable_pin: %s' % pins['enable']]
    out += extra + ['', '[tmc2209 %s]' % section, 'uart_pin: %s' % pins['uart'], 'interpolate: False',
                    'run_current: %s' % current, 'sense_resistor: 0.110', 'stealthchop_threshold: 0', '']
    return out


def _check(printer, boards):
    """The named refusals shared by both modes + the real-mode ones."""
    refusals = []
    model, mode, probe = _g(printer, 'model', ''), _g(printer, 'mode', ''), _g(printer, 'probe', 'none')
    if model not in MODELS:
        refusals.append('unknown model %r (one of %s)' % (model, MODELS))
    if mode not in MODES:
        refusals.append('unknown mode %r (one of %s)' % (mode, MODES))
    dims = [int(_g(printer, k, 0) or 0) for k in ('bed_x_mm', 'bed_y_mm', 'bed_z_mm')]
    if min(dims) <= 0:
        refusals.append('bed dimensions must be > 0 mm (got x/y/z %s/%s/%s)' % tuple(dims))
    if mode == 'sim':
        if not any(_g(b, 'connection', '') == 'linux' for b in boards):
            refusals.append("sim mode needs a board with connection 'linux' (the Klipper Linux host MCU built by the provisioner)")
        return refusals
    if mode != 'real':
        return refusals
    mains = [b for b in boards if _g(b, 'role', '') == 'main']
    if not mains:
        refusals.append("real mode needs a board with role 'main' (the printer's boards include no main board)")
    for b in mains:
        if (_g(b, 'mcu_name', '') or 'mcu') != 'mcu':
            refusals.append("main board %r must have mcu_name 'mcu' (Klipper's required primary [mcu] section), got %r" % (_g(b, 'name', ''), _g(b, 'mcu_name', '')))
        if _g(b, 'model', '') not in MAIN_BOARD_PINS:
            refusals.append('no reference pin map for main board model %r (mapped: %s)' % (_g(b, 'model', ''), ', '.join(sorted(MAIN_BOARD_PINS))))
    for b in boards:
        conn = _g(b, 'connection', '')
        if conn == 'usb' and not _g(b, 'serial_by_id', ''):
            refusals.append('usb board %r has no serial_by_id — measure it: pol hwmap scan on the device' % _g(b, 'name', ''))
        if conn == 'canbus' and not _g(b, 'canbus_uuid', ''):
            refusals.append('canbus board %r has no canbus_uuid — measure it: klipper/scripts/canbus_query.py can0 in the guest' % _g(b, 'name', ''))
        if _g(b, 'role', '') == 'toolhead' and _g(b, 'model', '') not in TOOLHEAD_BOARD_PINS:
            refusals.append('no reference pin map for toolhead board model %r (mapped: %s)' % (_g(b, 'model', ''), ', '.join(sorted(TOOLHEAD_BOARD_PINS))))
    if _g(printer, 'extruder', '') not in EXTRUDERS:
        refusals.append('no reference gear ratio for extruder %r (mapped: %s)' % (_g(printer, 'extruder', ''), ', '.join(sorted(EXTRUDERS))))
    if probe not in PROBES:
        refusals.append('unknown probe %r (one of %s)' % (probe, PROBES))
    elif probe == 'none' and Z_STEPPERS.get(model, 1) > 1:
        refusals.append('model %s levels with a probe ([quad_gantry_level]/[z_tilt]) — probe is none' % model)
    return refusals


def _sim(printer, boards):
    host = next(b for b in boards if _g(b, 'connection', '') == 'linux')
    return ['# SIM MODE: no motion physics; the stack runs, the printer does not move.',
            '# Only the Linux host MCU (%s) is configured; Klipper requires a primary [mcu] section, so it takes that' % _g(host, 'name', ''),
            "# name here (the board's mcu_name %r is used in real mode only). No steppers, heaters, fans or probe exist:" % _g(host, 'mcu_name', ''),
            '# kinematics none is what Klipper accepts without steppers; G-code streams, macros run, nothing moves or heats.', ''] + \
        _mcu_section(host, primary=True) + \
        ['[printer]', 'kinematics: none', 'max_velocity: %s' % _g(printer, 'max_velocity', 300), 'max_accel: %s' % _g(printer, 'max_accel', 3000), '']


def _real(printer, boards):
    model, probe = _g(printer, 'model'), _g(printer, 'probe', 'none')
    bx, by, bz = (int(_g(printer, k)) for k in ('bed_x_mm', 'bed_y_mm', 'bed_z_mm'))
    main = next(b for b in boards if _g(b, 'role', '') == 'main')
    tool = next((b for b in boards if _g(b, 'role', '') == 'toolhead'), None)
    mp = MAIN_BOARD_PINS[_g(main, 'model')]
    out = ['# PINS: the BTT Octopus 1.1 reference mapping (Voron project Klipper configurations) for the main board%s.'
           % (' and the %s reference mapping for the toolhead board' % _g(tool, 'model') if tool else ''),
           '# They are documented defaults, NOT your wiring: every pin MUST be checked before the first power-on.', '']
    for b in boards:
        if _g(b, 'connection', '') == 'linux':
            out.append('# board %r omitted: the Linux host MCU is only built in sim mode' % _g(b, 'name', ''))
            out.append('')
            continue
        out += _mcu_section(b)
    out += ['[printer]', 'kinematics: %s' % _g(printer, 'kinematics', 'corexy'), 'max_velocity: %s' % _g(printer, 'max_velocity', 300),
            'max_accel: %s' % _g(printer, 'max_accel', 3000), 'max_z_velocity: 15', 'max_z_accel: 350', 'square_corner_velocity: 5.0', '']
    xy = ['rotation_distance: 40', 'microsteps: 32', 'full_steps_per_rotation: 200']
    out += _stepper('stepper_x', mp['stepper_x'], xy + ['endstop_pin: %s' % mp['stepper_x']['endstop'], 'position_min: 0', 'position_endstop: %d' % bx,
                                                       'position_max: %d' % bx, 'homing_speed: 25', 'homing_retract_dist: 5', 'homing_positive_dir: true'])
    out += _stepper('stepper_y', mp['stepper_y'], xy + ['endstop_pin: %s' % mp['stepper_y']['endstop'], 'position_min: 0', 'position_endstop: %d' % by,
                                                       'position_max: %d' % by, 'homing_speed: 25', 'homing_retract_dist: 5', 'homing_positive_dir: true'])
    zrot, zgear = Z_DRIVE[model]
    z = ['rotation_distance: %s' % zrot] + (['gear_ratio: %s' % zgear] if zgear else []) + ['microsteps: 32']
    if probe == 'tap':
        zend = ['endstop_pin: probe:z_virtual_endstop']
    else:
        zend = ['endstop_pin: %s' % mp['stepper_z']['endstop'], 'position_endstop: 0.5   # MEASURE with Z_ENDSTOP_CALIBRATE']
    out += _stepper('stepper_z', mp['stepper_z'], z + zend + ['position_max: %d' % bz, 'position_min: -5', 'homing_speed: 8',
                                                             'second_homing_speed: 3', 'homing_retract_dist: 3'])
    for i in range(1, Z_STEPPERS[model]):
        out += _stepper('stepper_z%d' % i, mp['stepper_z%d' % i], z)
    tp = TOOLHEAD_BOARD_PINS[_g(tool, 'model')] if tool else mp
    pre = ('%s:' % _g(tool, 'mcu_name')) if tool else ''
    rot, gear = EXTRUDERS[_g(printer, 'extruder')]
    ep = tp['extruder']
    out += ['[extruder]', 'step_pin: %s' % _prefix(pre, ep['step']), 'dir_pin: %s' % _prefix(pre, ep['dir']),
            'enable_pin: %s' % _prefix(pre, ep['enable']), 'rotation_distance: %s   # %s reference; calibrate' % (rot, _g(printer, 'extruder')),
            'gear_ratio: %s' % gear, 'microsteps: 32', 'full_steps_per_rotation: 200', 'nozzle_diameter: 0.400', 'filament_diameter: 1.75',
            'heater_pin: %s' % _prefix(pre, ep['heater']), 'sensor_type: ATC Semitec 104NT-4-R025H42G', 'sensor_pin: %s' % _prefix(pre, ep['sensor']),
            'min_temp: 10', 'max_temp: 270', 'max_power: 1.0', 'min_extrude_temp: 170', 'control: pid   # run PID_CALIBRATE',
            'pid_kp: 26.213', 'pid_ki: 1.304', 'pid_kd: 131.721', 'pressure_advance: 0.05', 'pressure_advance_smooth_time: 0.040', '',
            '[tmc2209 extruder]', 'uart_pin: %s' % _prefix(pre, ep['uart']), 'interpolate: false', 'run_current: 0.5', 'sense_resistor: 0.110',
            'stealthchop_threshold: 0', '',
            '[heater_bed]', 'heater_pin: %s' % mp['heater_bed']['heater'], 'sensor_type: Generic 3950', 'sensor_pin: %s' % mp['heater_bed']['sensor'],
            'max_power: 0.6', 'min_temp: 0', 'max_temp: 120', 'control: pid   # run PID_CALIBRATE', 'pid_kp: 58.437', 'pid_ki: 2.347', 'pid_kd: 363.769', '']
    if probe == 'tap':
        out += ['[probe]   # Voron Tap: the toolhead is the probe; Z homes on it (z_virtual_endstop)', 'pin: %s' % _prefix(pre, tp['probe']),
                'x_offset: 0', 'y_offset: 0', 'z_offset: -0.5   # calibrate with PROBE_CALIBRATE', 'speed: 10.0', 'samples: 3', 'samples_result: median',
                'sample_retract_dist: 3.0', 'samples_tolerance: 0.006', 'samples_tolerance_retries: 3', 'activate_gcode:',
                '    {% set PROBE_TEMP = 150 %}', "    {% set ACTUAL_TEMP = printer.extruder.temperature %}",
                "    {% if ACTUAL_TEMP > PROBE_TEMP + 5 %}", "        { action_respond_info('Extruder temperature target of %.1fC is too high, lowering to %.1fC' % (ACTUAL_TEMP, PROBE_TEMP)) }",
                '        M109 S{ PROBE_TEMP }', '    {% endif %}', '']
    elif probe == 'klicky':
        out += ['[probe]   # Klicky: MEASURE x/y/z offsets for your mount (PROBE_CALIBRATE); the dock macros are not rendered here',
                'pin: %s' % _prefix(pre, tp['probe']), 'x_offset: 0', 'y_offset: 25.0   # reference value, MEASURE', 'z_offset: 0   # PROBE_CALIBRATE',
                'speed: 10.0', 'samples: 3', 'samples_result: median', 'sample_retract_dist: 3.0', 'samples_tolerance: 0.006', 'samples_tolerance_retries: 3', '']
    out += ['[fan]', 'pin: %s' % _prefix(pre, tp['part_fan']), 'kick_start_time: 0.5', 'off_below: 0.10', '',
            '[heater_fan hotend_fan]', 'pin: %s' % _prefix(pre, tp['hotend_fan']), 'max_power: 1.0', 'kick_start_time: 0.5', 'heater: extruder',
            'heater_temp: 50.0', '',
            '[controller_fan controller_fan]', 'pin: %s' % mp['controller_fan'], 'kick_start_time: 0.5', 'heater: heater_bed', '',
            '[idle_timeout]', 'timeout: 1800', '']
    if probe != 'none':
        out += ['[safe_z_home]', 'home_xy_position: %d,%d' % (bx // 2, by // 2), 'speed: 100', 'z_hop: 10', '']
    if model == 'voron-2.4':
        out += ['[quad_gantry_level]   # gantry corners + probe points derived from the bed size (the Voron reference points for 350)',
                'gantry_corners:', '    -60,-10', '    %d,%d' % (bx + 60, by + 70), 'points:', '    50,25', '    50,%d' % (by - 75),
                '    %d,%d' % (bx - 50, by - 75), '    %d,25' % (bx - 50), 'speed: 100', 'horizontal_move_z: 10', 'retries: 5',
                'retry_tolerance: 0.0075', 'max_adjust: 10', '']
    elif model == 'voron-trident':
        out += ['[z_tilt]   # z positions + probe points derived from the bed size (the Voron reference points for 350)',
                'z_positions:', '    -50,18', '    %d,%d' % (bx // 2, by + 48), '    %d,18' % (bx + 50), 'points:', '    30,5',
                '    %d,%d' % (bx // 2, by - 55), '    %d,5' % (bx - 30), 'speed: 200', 'horizontal_move_z: 10', 'retries: 5', 'retry_tolerance: 0.0075', '']
    if probe != 'none':
        out += ['[bed_mesh]', 'speed: 300', 'horizontal_move_z: 5', 'mesh_min: 40,40', 'mesh_max: %d,%d' % (bx - 40, by - 40), 'probe_count: 5,5',
                'algorithm: bicubic', '']
    return out


def _prefix(pre, pin):
    """Put the toolhead mcu prefix AFTER the modifier characters (^, !, ~): '!PD2' → '!EBBCan:PD2'."""
    mods = ''
    while pin and pin[0] in '^!~':
        mods, pin = mods + pin[0], pin[1:]
    return '%s%s%s' % (mods, pre, pin)


def render_printer_cfg(printer, boards):
    """printer: a PrinterDefinition row or dict; boards: its PrinterBoard rows
    or dicts (all roles; the renderer picks per mode). Returns (cfg_text,
    refusals) — an empty refusals list means the cfg is complete."""
    boards = list(boards or [])
    refusals = _check(printer, boards)
    if refusals:
        return '', refusals
    mode = _g(printer, 'mode')
    out = ['# Klipper printer.cfg — rendered by voron.custom.printer_cfg from PrinterDefinition %r' % _g(printer, 'name', ''),
           '# model %s, kinematics %s, bed %sx%sx%s mm, mode %s, %d board row(s)' % (
               _g(printer, 'model'), _g(printer, 'kinematics', 'corexy'), _g(printer, 'bed_x_mm'), _g(printer, 'bed_y_mm'), _g(printer, 'bed_z_mm'), mode, len(boards)), '']
    out += _sim(printer, boards) if mode == 'sim' else _real(printer, boards)
    out += ['[virtual_sdcard]', 'path: %s/gcodes' % PRINTER_DATA, '', '[display_status]', '', '[pause_resume]', '',
            '[include %s]' % MACROS_FILE, '']
    return '\n'.join(out), []
