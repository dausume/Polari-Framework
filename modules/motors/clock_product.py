"""
@module motors.clock_product

mag-21: THE CLOCK AS A PRODUCT — one datasheet that composes every
analysis built so far and states, honestly, what this thing IS.

Dustin 2026-07-30 asked whether this is a wristwatch or pocket-watch
movement, and then: get it to a state where we are fully simulating
a clock as some kind of product.

THE FIRST ANSWER IS NO, AND THE NUMBERS SAY SO RATHER THAN taste.
The ROTOR is watch-scale (2 mm), which is what makes the question
reasonable. Everything else is not:
  - the seconds wheel is 72 mm across at module 0.3, so the
    MOVEMENT alone is wider than a pocket watch;
  - the drivable face works out at ~260 mm (gr-6);
  - and the POWER settles it. Our coil needs 3.64 V at 20 mA for a
    30 ms pulse: 0.6 mA average. A commercial quartz WALL clock
    averages ~15 uA and a WATCH ~1 uA. We are ~40x a wall clock and
    ~600x a watch. A watch cell (28 mAh) would last FOUR DAYS.
So: a WALL CLOCK movement — and a thirsty one. The reason is already
on record in the mag-11 part rows: our mu~2 castings make a coarse
detent that needs milliamp pulses where laminated steel needs
microamps. The power draw is the permeability gap, showing up as a
battery bill.

WHAT THIS MODULE DOES: it does not compute anything new. It COMPOSES
the existing analyses into one product view — movement class, power
and battery life, face size, bill of materials, true price per
year-of-timekeeping, and the failures that are still open — because
"is it a product?" is a question none of the individual reports can
answer alone.

Everything here either calls an existing analysis or an existing
equation row. Where an analysis is absent (module gated off) the
section reports its own absence rather than the product looking
complete.

@consumers motors.motor_api, motors.selftest_motors
"""

from magnetics.magnet_analysis import _named, _rows

#: Reference points, so "thirsty" is a comparison and not an
#: adjective. Literature-est averages for commercial movements.
POWER_REFERENCES = {
    'quartz-wristwatch': (1.0e-3, 'mA', 'a watch movement averages '
                                        '~1 uA; an SR626 cell runs '
                                        'it about two years'),
    'quartz-wall-clock': (15.0e-3, 'mA', 'a wall movement averages '
                                         '~15 uA; one AA runs it '
                                         '1-3 years'),
}

#: Cell capacities (mAh) for the battery-life table.
CELLS = {'AA-alkaline': 2500.0, 'AAA-alkaline': 1000.0,
         'CR2032-coin': 225.0, 'SR626-watch': 28.0}


def _pulse_duty(design, pulse_ms):
    import json
    try:
        drive = json.loads(getattr(design, 'drive_json', '') or '{}')
    except (TypeError, ValueError):
        drive = {}
    rate = float(drive.get('rate_hz', 1.0) or 1.0)
    return rate, (pulse_ms / 1000.0) * rate


def power_budget(manager, design_name='clock-lavet-m0',
                 pulse_ms=30.0):
    """What it draws, how long a cell lasts, and how that compares
    to movements you can buy."""
    design = _named(manager, 'MotorDesignDefinition', design_name)
    if design is None:
        return {'ok': False,
                'refusal': f'no MotorDesignDefinition named '
                           f'"{design_name}"'}
    from motors.motor_winding import winding_report
    w = winding_report(manager, design_name)
    if not w.get('ok'):
        return {'ok': False,
                'refusal': f'winding unknown, so power is unknown: '
                           f'{w.get("refusal")}'}
    rate, duty = _pulse_duty(design, pulse_ms)
    amps = w['amps']
    volts = w['voltageNeededV']
    avg_ma = amps * 1000.0 * duty
    peak_mw = volts * amps * 1000.0
    cells = {name: {'capacityMah': cap,
                    'monthsOfService': round(cap / avg_ma / 24
                                             / 30.4, 2)
                    if avg_ma else None}
             for name, cap in CELLS.items()}
    comparisons = {
        ref: {'theirAverageMa': val,
              'weAreThisManyTimesThirstier': round(avg_ma / val, 1),
              'note': note}
        for ref, (val, _, note) in POWER_REFERENCES.items()}
    return {
        'ok': True, 'design': design_name,
        'pulseMs': pulse_ms, 'rateHz': rate,
        'dutyPct': round(duty * 100.0, 2),
        'coilVoltageV': volts, 'coilCurrentA': amps,
        'averageCurrentMa': round(avg_ma, 4),
        'peakPowerMw': round(peak_mw, 2),
        'cells': cells, 'comparedTo': comparisons,
        'whyThirsty': (
            'the mu~2 castings make a COARSE detent, so the pulse '
            'must overwhelm it; laminated steel at mu~1e3-1e4 lets '
            'a commercial movement use microamps. The power draw IS '
            'the permeability gap, arriving as a battery bill.'),
        'validity': 'a rectangular pulse of the stated width at the '
                    'stated current; coil inductance, driver '
                    'quiescent draw and the quartz oscillator '
                    'itself are NOT included, and all three make '
                    'the real figure worse.',
    }


def movement_class(manager, design_name='clock-lavet-m0'):
    """IS this a watch? Answered from the numbers, not asserted."""
    pw = power_budget(manager, design_name)
    if not pw.get('ok'):
        return pw
    from gears.planetary import clock_face_sizing
    face = clock_face_sizing(manager, 'clock-train-m0')
    face_mm = face.get('maxFaceDiameterMm') if face.get('ok') else None
    # Largest wheel in the train decides how small the movement can
    # physically be.
    widest = 0.0
    for g in _rows(manager, 'GearDefinition'):
        if getattr(g, 'train_ref', '') != 'clock-train-m0':
            continue
        d = (float(getattr(g, 'module_mm', 1.0))
             * float(getattr(g, 'teeth', 1)))
        widest = max(widest, d)
    watch_months = pw['cells']['SR626-watch']['monthsOfService']
    return {
        'ok': True, 'design': design_name,
        'movementWidthMm': round(widest, 2),
        'drivableFaceMm': face_mm,
        'averageCurrentMa': pw['averageCurrentMa'],
        'watchCellMonths': watch_months,
        'isWatch': False,
        'classification': 'wall-clock movement',
        'why': (
            f'the rotor IS watch-scale (2 mm), which is why the '
            f'question is reasonable — but the widest wheel is '
            f'{round(widest, 1)} mm, so the MOVEMENT alone is wider '
            f'than a pocket watch; it drives a {face_mm} mm face; '
            f'and at {pw["averageCurrentMa"]} mA average a watch '
            f'cell would last {watch_months} months. It is a wall '
            f'clock, and a thirsty one.'),
        'howToMakeItAWatch': (
            'split the 1800:1 into more, smaller stages (the widest '
            'wheel is what sets the size), and close the '
            'permeability gap — fired ceramic or a steel stator — '
            'so the detent stops needing milliamps. Both changes '
            'are already on the shelf as escalation rungs.'),
    }


def product_datasheet(manager, design_name='clock-lavet-m0',
                      train_name='clock-train-m0'):
    """THE PRODUCT VIEW: every analysis composed into one answer to
    'is this a product, and what is it?'"""
    sections = {}
    gaps = []

    def section(key, fn):
        try:
            out = fn()
        except Exception as exc:            # noqa: BLE001
            out = {'ok': False, 'refusal': f'{type(exc).__name__}: '
                                           f'{exc}'}
        sections[key] = out
        if not out.get('ok'):
            gaps.append(f'{key}: {out.get("refusal", "")[:120]}')
        return out

    cls = section('classification',
                  lambda: movement_class(manager, design_name))
    power = section('power', lambda: power_budget(manager,
                                                  design_name))

    from gears.gear_kinematics import solve_train
    train = section('train', lambda: solve_train(manager,
                                                 train_name))
    from gears.planetary import clock_face_sizing, motion_works_ratio
    face = section('face', lambda: clock_face_sizing(manager,
                                                     train_name))
    section('handDrive', lambda: motion_works_ratio())

    from motors.motor_parts import part_report
    bom = section('billOfMaterials',
                  lambda: part_report(manager, design_name))

    from motors.motor_winding import winding_report
    section('winding', lambda: winding_report(manager, design_name))

    # Structural: the part we know is marginal.
    # mp0: the governing pinion is THIS design's own part row (the
    # M0b product carries a fired-ceramic pinion; grading the
    # as-built cast one against it was a stale hardcode). Legacy
    # name kept as the fallback for designs without part rows.
    pinion_part = next(
        (getattr(p, 'name', '')
         for p in (getattr(manager, 'objectTables', None)
                   or {}).get('MotorPartDefinition', {}).values()
         if getattr(p, 'design_ref', '') == design_name
         and getattr(p, 'function', '') == 'torque-transmission'),
        'lavet-v2-pinion')
    from motors.motor_fatigue import part_fatigue
    fat = section('pinionFatigue',
                  lambda: part_fatigue(manager, design_name,
                                       pinion_part))
    from motors.lifecycle_cost import cheapest_configuration
    price = section('truePrice',
                    lambda: cheapest_configuration(
                        manager, design_name, pinion_part))

    blockers = []
    if fat.get('ok') and not fat.get('passes'):
        blockers.append(
            f'the pinion FAILS fatigue at SF '
            f'{fat.get("fatigueSafetyFactor")} — it does not '
            f'survive clock duty in its current material')
    if power.get('ok'):
        wall = power['comparedTo']['quartz-wall-clock'][
            'weAreThisManyTimesThirstier']
        if wall > 5:
            blockers.append(
                f'power draw is {wall}x a commercial wall movement, '
                f'so a cell lasts months rather than years')
    if bom.get('ok') and bom.get('gaps'):
        blockers.append(f'{len(bom["gaps"])} part(s) cannot be '
                        f'costed or massed yet')

    # A verdict of NOT SHIPPABLE is only half an answer if a route
    # past it exists. mag-22 searched for one, so the product view
    # carries it rather than leaving the reader at the blockers.
    route = None
    if blockers:
        try:
            from motors.local_route import producible_clock
            route = producible_clock(manager, design_name,
                                     train_name)
        except Exception as exc:            # noqa: BLE001
            route = {'ok': False,
                     'refusal': f'{type(exc).__name__}: {exc}'}

    return {
        'ok': True, 'product': 'Lavet-type clock movement (M0)',
        'routePastTheBlockers': route,
        'design': design_name, 'train': train_name,
        'classification': (cls.get('classification')
                           if cls.get('ok') else None),
        'sections': sections,
        'headline': (
            f'a {cls.get("classification", "?")} driving a '
            f'{face.get("maxFaceDiameterMm")} mm face, '
            f'{bom.get("totalMassG")} g of parts, '
            f'{power.get("averageCurrentMa")} mA average — '
            f'{power.get("cells", {}).get("AA-alkaline", {}).get("monthsOfService")} '
            f'months on an AA'
            if all(x.get('ok') for x in (cls, face, bom, power))
            else 'incomplete — see gaps'),
        'shippable': not blockers,
        'blockers': blockers,
        'gaps': gaps,
        'verdict': (
            'NOT SHIPPABLE AS IS. ' + ' '.join(blockers)
            + (f' BUT A ROUTE EXISTS: {route["headline"]}'
               if route and route.get('answerable') else '')
            if blockers else
            'every composed check passes'),
        'honesty': (
            'this composes existing analyses and computes nothing '
            'new — so every caveat from every section still '
            'applies, and they COMPOUND. The material properties '
            'are literature-est, no casting of ours has been '
            'tested, and the fatigue exponent amplifies all of it. '
            'Treat this as a design review, not a datasheet you '
            'could hand a buyer.'),
    }
