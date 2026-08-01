"""
@module motors.bench_campaign

bench-1 (Dustin 2026-08-01, "go ahead on it"): the W2 BENCH
CAMPAIGN — the named next advancement past M0 is a physical build
and measurement, which stays a HUMAN act. What the system carries
is everything around it: an ordered measurement protocol where
every entry states

  - WHAT to measure and with WHICH instrument (a tech-tree node —
    the bench maps onto capabilities we already model),
  - the PREDICTION, computed LIVE from the engines at request time
    (never a stale copy) — and where two models disagree, BOTH
    predictions with the ratio, so the measurement lands in a
    decided context instead of confirming whichever number it is
    closest to,
  - the acceptance band and WHAT THE MEASUREMENT ADJUDICATES,
  - the exact record-back seam (the API/rows that receive the
    result) — a measured MotorVerificationRun and QA records are
    how made-and-measured gets EARNED.

An engine that cannot predict refuses inside its entry; the
campaign never silently shortens.

@consumers motors.motor_api (/api/motors/bench-campaign),
motors.clock_views (motion-view section), motors.selftest_motors
"""

PRODUCT = 'clock-lavet-m0b'
CONTROL = 'clock-lavet-m0'


def _entry(name, instrument, adjudicates, record_via, acceptance,
           prediction):
    out = {'measurement': name, 'instrument': instrument,
           'adjudicates': adjudicates, 'recordVia': record_via,
           'acceptance': acceptance}
    out.update(prediction if isinstance(prediction, dict)
               else {'prediction': prediction})
    return out


def bench_campaign(manager, design_name=PRODUCT):
    """The ordered W2 bench protocol with live predictions."""
    entries = []

    # 1. Coil resistance — the cheapest sanity gate.
    try:
        from motors.motor_winding import winding_report
        wr = winding_report(manager, design_name)
        pred = ({'predictedOhm': wr.get('resistanceOhm'),
                 'predictedVoltageV': wr.get('voltageNeededV'),
                 'basis': 'winding_report from the design row '
                          '(mag-25 solved numbers)'}
                if wr.get('ok') else
                {'refusal': wr.get('refusal', 'winding refused')})
    except Exception as e:
        pred = {'refusal': f'raised: {e}'}
    entries.append(_entry(
        'coil-resistance', 'multimeter (any)',
        'whether the wound coil matches the solved winding at all '
        '— catches turn-count and gauge errors before anything '
        'subtle',
        {'row': 'QualityCheckRecord',
         'check': 'qa-wound-core-inductance'},
        'within 15% of prediction (temperature-corrected)', pred))

    # 2. Inductance — THE adjudicating measurement (mag-23).
    try:
        from motors.inductance import model_validity, solve_inductance
        fem = solve_inductance(manager, CONTROL)
        val = model_validity(manager, CONTROL)
        if fem.get('ok'):
            pred = {
                'predictedFem': {
                    'L': fem.get('inductanceH')
                    or fem.get('L_h') or fem.get('L'),
                    'basis': '2D FEM magnetostatics, '
                             'feature-aligned mesh, flux-cut '
                             'cross-checked'},
                'predictedLumped': {
                    'ratioFemOverLumped': (val.get('ratio')
                                           or (val.get('summary')
                                               or {}).get('ratio')),
                    'basis': 'lumped reluctance network'},
                'note': 'the two models DISAGREE at low mu (the '
                        'mag-23 finding: the lumped model stops '
                        'applying, ~4.6x at mu~2) — this ONE '
                        'measurement decides which number the '
                        'whole stack should trust',
            }
        else:
            pred = {'refusal': fem.get('refusal',
                                       'FEM inductance refused')}
    except Exception as e:
        pred = {'refusal': f'raised: {e}'}
    entries.append(_entry(
        'wound-core-inductance',
        'tech-node: research-tools/inductance-test-rig (LCR or '
        'ring-down)',
        'the mag-23 4.6x model disagreement on exactly the low-mu '
        'materials we can make — the highest-value single '
        'measurement in the magnetics stack',
        {'row': 'QualityCheckRecord',
         'check': 'qa-wound-core-inductance',
         'alsoUpdates': 'model_validity trust ordering'},
        'report the measured L; there is no pass band — the '
        'measurement ADJUDICATES the models, not the coil', pred))

    # 3. Rotor remanence — the named experiment's number.
    try:
        from magnetics.magnet_analysis import _named
        opt = _named(manager, 'MagneticMaterialOption',
                     'opt-srfe12o19')
        import json as _j
        props = (_j.loads(getattr(opt, 'properties_json', '')
                          or '{}') if opt else {})
        br = (props.get('remanence_t') or {}).get('value')
        pred = ({'predictedRemanenceT': br,
                 'basis': 'opt-srfe12o19 catalog claim '
                          '(literature prior — this measurement '
                          'is what turns it into a made number)'}
                if br else
                {'refusal': 'opt-srfe12o19 states no remanence — '
                            'seed the property before comparing'})
    except Exception as e:
        pred = {'refusal': f'raised: {e}'}
    entries.append(_entry(
        'rotor-remanence',
        'tech-node: research-tools/hall-gaussmeter',
        'THE named experiment: press + sinter + magnetize from '
        'our own powder — the whole pure-local route rests on '
        'this row becoming measured',
        {'row': 'QualityCheckRecord',
         'check': 'qa-magnet-remanence',
         'alsoUpdates': 'mag-12 realization promotion (evidence '
                        '-> suggested rung, never auto-applied)'},
        'B_r within the catalog band; BELOW band still valuable — '
        'record it, the promotion tool decides nothing silently',
        pred))

    # 4. Minimum drive current — bisected prediction vs bench.
    try:
        from motors.local_route import minimum_drive_current
        mdc = minimum_drive_current(manager, CONTROL)
        pred = ({'predictedMinMa': (mdc.get('minAmps') or 0)
                 * 1000.0 if mdc.get('ok') else None,
                 'basis': 'bisection of the clock_sim step '
                          'condition (mag-22 — the stated 20 mA '
                          'was never solved for)'}
                if mdc.get('ok') else
                {'refusal': mdc.get('refusal', 'bisect refused')})
    except Exception as e:
        pred = {'refusal': f'raised: {e}'}
    entries.append(_entry(
        'minimum-drive-current',
        'bench supply + series resistor, reduce until steps miss',
        'whether the co-energy torque model predicts the real '
        'step threshold — the sim\'s own validity check',
        {'row': 'MotorVerificationRun',
         'api': 'POST /api/motors/verify/' + CONTROL,
         'kind': 'measured'},
        'within 2x of prediction (the model carries low-mu '
        'caveats; ratios survive better than absolutes)', pred))

    # 5. The 24 h timekeeping run — the product QA gate.
    try:
        from motors.clock_assembly import timekeeping_proof
        proof = timekeeping_proof(manager, pulses=300)
        pred = ({'predictedVerdict': proof.get('verdict'),
                 'predictedMissed': proof.get('stepsMissed'),
                 'basis': 'sim steps through the solved train '
                          '(the as-3 proof, exact when nothing '
                          'misses)'}
                if proof.get('ok') else
                {'refusal': proof.get('refusal', 'proof refused')})
    except Exception as e:
        pred = {'refusal': f'raised: {e}'}
    entries.append(_entry(
        'timekeeping-24h',
        'reference clock + the assembled movement',
        'the PRODUCT itself: does the whole assembly keep time — '
        'a passing measured run is what earns made-and-measured',
        {'row': 'MotorVerificationRun',
         'api': 'POST /api/motors/verify/' + CONTROL,
         'kind': 'measured',
         'qaGate': 'qa-timekeeping-24h'},
        '<= 2 s error per 24 h (86400 pulses, <= 2 missed)', pred))

    refused = [e['measurement'] for e in entries
               if e.get('refusal')]
    return {
        'ok': True, 'design': design_name,
        'campaign': 'w2-bench',
        'order': [e['measurement'] for e in entries],
        'measurements': entries,
        'refusedPredictions': refused,
        'note': 'predictions are computed LIVE at request time — '
                'a re-seeded material or a retuned winding changes '
                'the sheet, never a stale copy. The build steps '
                'themselves are the mp0 workflows '
                '(clock-fire-parts, clock-magnet-press, '
                'clock-wind-assemble); this sheet is the '
                'MEASUREMENT half.',
    }
