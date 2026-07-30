"""
@module gears.gear_motor

gr-5: THE MOTOR SPLICE (GEARS_PLAN §5) — motor logic meeting gear
logic, which is the whole point of the gears arc.

Our cast-ferrite motors are honestly FEEBLE (mu~2 physics; the motor
reports say so themselves). Gearing is exactly how a feeble-but-cheap
motor becomes a useful actuator — and this module refuses to show
that win without its price: the speed given up, the efficiency lost,
and the backlash added, on the same payload.

THE SPEED HONESTY, stated on every result: the motor sim is
QUASI-STATIC and does not predict speed. So:
  - M0 (Lavet stepper) speed IS known — the drive rate sets it
    (one 180 deg step per pulse => 30 x rate_hz rpm), and that is
    why the clock train is the acceptance case;
  - M1-M3 speed is an ASSUMPTION the caller supplies (or the design's
    drive rate as a stand-in), never a prediction. The payload says
    which of the two it used.

Torque, by contrast, transforms EXACTLY: ratio x efficiency, and the
underlying motor watermarks (realization level, parity multipliers,
mu~2 smallness) travel through unchanged.

@consumers gears.gear_api, gears.selftest_gears
"""

from gears.gear_kinematics import _named, solve_train

#: A Lavet stepper advances 180 degrees per pulse => half a
#: revolution per pulse => 0.5 * rate_hz rev/s => x60 rpm.
LAVET_RPM_PER_HZ = 30.0


def _loads(row, attr, default):
    import json
    try:
        return json.loads(getattr(row, attr, '') or '')
    except (TypeError, ValueError):
        return default


def _refuse(refusal, suggestion=None):
    out = {'ok': False, 'refusal': refusal}
    if suggestion:
        out['suggestion'] = suggestion
    return out


def _motor_drive(manager, design, speed_rpm_override):
    """(torque_points, speed_rpm, speed_basis, motor_meta) or a
    refusal dict. torque_points is [(label, torque_nm), ...] — the
    envelope the train is solved at, not a single flattering
    number."""
    from motors.motor_designer import torque_curve

    topology = getattr(design, 'topology', '')
    drive = _loads(design, 'drive_json', {})
    rate_hz = float(drive.get('rate_hz', 0.0) or 0.0)
    meta = {
        'design': getattr(design, 'name', ''),
        'ladderRung': getattr(design, 'ladder_rung', ''),
        'topology': topology,
        'toleranceTier': getattr(design, 'tolerance_tier', ''),
    }

    if topology == 'lavet-clock-stepper':
        # The stepper's speed is EXACT (the drive rate sets it), but
        # its "torque" is a co-energy amplitude that exists only
        # during a pulse — not a continuous rating. So the train is
        # solved at the stated input torque and the payload says
        # exactly that rather than inventing a continuous number.
        speed = (speed_rpm_override if speed_rpm_override is not None
                 else rate_hz * LAVET_RPM_PER_HZ)
        meta['stepRateHz'] = rate_hz
        return (None, speed,
                (f'EXACT: a Lavet stepper advances 180 deg per '
                 f'pulse, so {rate_hz} Hz = {speed} rpm — this is '
                 f'the one rung whose speed is not an assumption'
                 if speed_rpm_override is None else
                 'caller-supplied override'),
                meta)

    curve = torque_curve(manager, getattr(design, 'name', ''))
    if not curve.get('ok'):
        return _refuse(
            f'motor "{getattr(design, "name", "?")}" has no usable '
            f'torque curve: {curve.get("refusal")}')
    torques = [p['torqueNm'] for p in curve.get('curve', [])]
    points = [('mean', curve.get('meanTorqueNm', 0.0)),
              ('peak', curve.get('peakTorqueNm', 0.0))]
    if torques:
        points.append(('worst-case-in-curve', min(torques)))
    speed = (speed_rpm_override if speed_rpm_override is not None
             else rate_hz * 60.0)
    meta.update({
        'meanTorqueNm': curve.get('meanTorqueNm'),
        'peakTorqueNm': curve.get('peakTorqueNm'),
        'ripplePct': curve.get('ripplePct'),
        'dualGap': curve.get('dualGap'),
        'motorValidity': curve.get('validity', ''),
    })
    basis = ('caller-supplied override' if speed_rpm_override
             is not None else
             f'ASSUMED from the design drive rate ({rate_hz} Hz x '
             f'60) — the quasi-static motor model does NOT predict '
             f'speed; supply speedRpm to state your own')
    return (points, speed, basis, meta)


def motor_driven_train(manager, train_name, design_name='',
                       speed_rpm=None, required_output_torque_nm=None):
    """Drive a gear train from a REAL motor design. Returns the
    output envelope (one solve per torque point), the price of the
    ratio, and — when a duty is stated — which side binds."""
    train = _named(manager, 'GearTrainDefinition', train_name)
    if train is None:
        return _refuse(f'no GearTrainDefinition named '
                       f'"{train_name}"')
    design_ref = design_name or getattr(train, 'motor_design_ref',
                                        '')
    if not design_ref:
        return _refuse(
            f'train "{train_name}" names no motor design and none '
            f'was given',
            {'knob': 'GearTrainDefinition.motor_design_ref',
             'action': 'set the motor, or pass ?design='})
    design = _named(manager, 'MotorDesignDefinition', design_ref)
    if design is None:
        return _refuse(
            f'no MotorDesignDefinition named "{design_ref}" — is '
            f'the motors module enabled?',
            {'knob': 'POLARI_MODULES',
             'action': 'enable motors (it owns the ladder)'})

    drive = _motor_drive(manager, design, speed_rpm)
    if isinstance(drive, dict):          # a refusal
        return drive
    points, speed, speed_basis, meta = drive

    if points is None:
        # M0: solve once at the train's stated torque.
        points = [('stated-on-train',
                   float(getattr(train, 'input_torque_nm', 0.0)))]
        torque_basis = ('the stepper\'s pulse torque is a co-energy '
                        'AMPLITUDE, not a continuous rating — the '
                        'train is solved at the torque stated on '
                        'the train row and this line says so')
    else:
        torque_basis = ('from the motor\'s own torque curve '
                        '(quasi-static partial derivative at held '
                        'currents — the motor report\'s validity '
                        'travels below)')

    envelope = []
    base = None
    for label, torque in points:
        solved = solve_train(manager, train_name,
                             input_torque_nm=torque,
                             input_speed_rpm=speed)
        if not solved.get('ok'):
            return solved
        base = base or solved
        envelope.append({
            'point': label,
            'motorTorqueNm': torque,
            'outputTorqueNm': solved['outputTorqueNm'],
            'outputSpeedRpm': solved['outputSpeedRpm'],
        })

    duty = None
    if required_output_torque_nm is not None:
        need = float(required_output_torque_nm)
        # Judge against the WORST point available, not the peak —
        # a drive that only meets its duty at peak torque does not
        # meet it.
        worst = min(e['outputTorqueNm'] for e in envelope)
        best = max(e['outputTorqueNm'] for e in envelope)
        met = worst >= need
        if met:
            binding = None
            note = (f'duty met at every point of the envelope '
                    f'(worst {worst} Nm >= required {need} Nm)')
        elif best >= need:
            binding = 'motor-torque-ripple'
            note = (f'duty met at the BEST point ({best} Nm) but '
                    f'NOT the worst ({worst} Nm) — the machine '
                    f'would stall at the wrong rotor angle; treat '
                    f'this as unmet')
        else:
            binding = 'motor-torque'
            deficit = need / best if best else float('inf')
            note = (f'duty NOT met: needs {need} Nm, best available '
                    f'{best} Nm. The binding constraint is the '
                    f'MOTOR: it needs ~{round(deficit, 2)}x more '
                    f'torque, or the train needs ~{round(deficit, 2)}'
                    f'x more ratio (and you pay for it in speed)')
        duty = {'requiredOutputTorqueNm': need, 'met': met,
                'worstAvailableNm': worst, 'bestAvailableNm': best,
                'bindingConstraint': binding, 'note': note,
                'unmodeled': 'friction, seal drag, and starting '
                             'torque are NOT in this comparison — '
                             'a duty met by a hair is not met'}

    return {
        'ok': True,
        'train': train_name,
        'motor': meta,
        'inputSpeedRpm': speed,
        'speedBasis': speed_basis,
        'torqueBasis': torque_basis,
        'totalRatio': base['totalRatio'],
        'totalEfficiency': base['totalEfficiency'],
        'outputBacklashMm': base['outputBacklashMm'],
        'envelope': envelope,
        'shafts': base['shafts'],
        'meshes': base['meshes'],
        'duty': duty,
        'priceOfTheRatio': {
            'speedDividedBy': base['totalRatio'],
            'efficiencyMultiplier': base['totalEfficiency'],
            'backlashAddedMm': base['outputBacklashMm'],
            'note': 'gearing is how a cheap feeble motor becomes a '
                    'useful actuator — these three numbers are '
                    'what it costs, and they are never omitted',
        },
        'validity': base['validity'],
    }
