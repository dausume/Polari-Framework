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
M1 = 'reluctance-6s4p-m1'
M2 = 'ferrite-pm-m2'


def _entry(name, instrument, adjudicates, record_via, acceptance,
           prediction):
    out = {'measurement': name, 'instrument': instrument,
           'adjudicates': adjudicates, 'recordVia': record_via,
           'acceptance': acceptance}
    out.update(prediction if isinstance(prediction, dict)
               else {'prediction': prediction})
    return out


def bench_campaign(manager, design_name=PRODUCT):
    """The ordered W2 bench protocol with live predictions.
    m1-7: the M1 design dispatches to its own sheet."""
    if design_name == M1:
        return m1_bench_campaign(manager, design_name)
    if design_name == M2:
        return m2_bench_campaign(manager, design_name)
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
        entry_b = props.get('b_r_t') or {}
        br = entry_b.get('value')
        pred = ({'predictedRemanenceT': br,
                 'provenance': entry_b.get('provenance', ''),
                 'note': entry_b.get('note', ''),
                 'basis': 'opt-srfe12o19 catalog claim '
                          '(literature prior — this measurement '
                          'is what turns it into a made number)'}
                if br else
                {'refusal': 'opt-srfe12o19 states no b_r_t — '
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
        pred = ({'predictedThresholdMa':
                 round((mdc.get('thresholdAmps') or 0) * 1000.0,
                       4),
                 'designedMaWithMargin':
                 round((mdc.get('designedAmps') or 0) * 1000.0,
                       4),
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

    return _campaign(design_name, 'w2-bench', entries,
                     'The build steps themselves are the mp0 '
                     'workflows (clock-fire-parts, '
                     'clock-magnet-press, clock-wind-assemble); '
                     'this sheet is the MEASUREMENT half.')


def m1_bench_campaign(manager, design_name=M1):
    """m1-7: the M1 bench sheet. What is DIFFERENT from the clock:
    six of everything (imbalance is a FINDING — the model builds
    identical phases, only the bench can see spread), torque as a
    number instead of a step/no-step, the step angle as the
    positioning proof's physical half, and a thermal question the
    model honestly does not answer."""
    entries = []

    # 1+2. Per-phase R and L — SIX of each, spread is the finding.
    try:
        from motors.m1_views import m1_phase_electrics
        pe = m1_phase_electrics(manager, design_name)
        pred_r = ({'predictedPhaseOhm':
                   pe['phases'][0]['rPhaseOhm'],
                   'predictedSpread': 0.0,
                   'basis': 'm1_phase_electrics: the same winding '
                            'engine, two coils in series — the '
                            'model builds SIX IDENTICAL phases, '
                            'so any measured spread is a '
                            'manufacturing finding with a '
                            'per-coil paper trail'}
                  if pe.get('ok') else
                  {'refusal': pe.get('refusal', 'refused')})
    except Exception as e:
        pred_r = {'refusal': f'raised: {e}'}
    entries.append(_entry(
        'phase-resistance-six', 'multimeter (any) — ALL SIX coils',
        'coil-to-coil manufacturing spread: the model cannot '
        'predict imbalance, which is exactly why all six are '
        'measured, not one',
        {'row': 'QualityCheckRecord',
         'check': 'qa-phase-resistance-six'},
        'each within 15% of prediction; SPREAD <= 5% of mean — '
        'above that, the winding process (not the design) is the '
        'finding', pred_r))
    try:
        from motors.inductance import solve_inductance
        fem = solve_inductance(manager, design_name)
        pred_l = ({'predictedL': fem.get('inductanceH')
                   or fem.get('L_h') or fem.get('L'),
                   'basis': 'the mag-23 machinery on the M1 '
                            'winding'}
                  if fem.get('ok') else
                  {'refusal': fem.get('refusal',
                                      'inductance refused'),
                   'note': 'at mu~2 the lumped network is outside '
                           'its validity regime (mag-23) — six '
                           'MEASURED L values are the answer, '
                           'not a better guess'})
    except Exception as e:
        pred_l = {'refusal': f'raised: {e}'}
    entries.append(_entry(
        'phase-inductance-six',
        'tech-node: research-tools/inductance-test-rig — ALL SIX',
        'feeds the SAME mag-23 adjudication the clock L does — '
        'six more points on the low-mu validity map, plus the '
        'phase-to-phase spread',
        {'row': 'QualityCheckRecord',
         'check': 'qa-phase-resistance-six',
         'alsoUpdates': 'model_validity trust ordering (mag-23)'},
        'report all six; no pass band — the measurements '
        'ADJUDICATE the models', pred_l))

    # 3. Holding torque — the number the axis duty rests on.
    try:
        from motors.m1_sequencing import holding_torque
        hold = holding_torque(manager, design_name)
        pred_h = ({'predictedNm': hold['peakTorqueNm'],
                   'basis': 'the m1-1 co-energy scan at rated '
                            'current — honestly feeble at mu~2, '
                            'and the whole m1-5 verdict rests on '
                            'this number being roughly right'}
                  if hold.get('ok') else
                  {'refusal': hold.get('refusal', 'refused')})
    except Exception as e:
        pred_h = {'refusal': f'raised: {e}'}
    entries.append(_entry(
        'holding-torque-rated',
        'lever + gram scale (W2): stall the energized rotor '
        'through a known arm',
        'the reluctance network\'s torque amplitude on exactly '
        'the low-mu material where the model is weakest — and '
        'the number the positioning duty verdict (m1-5) divides '
        'by',
        {'row': 'MotorVerificationRun',
         'api': 'POST /api/motors/verify/' + M1,
         'kind': 'measured'},
        'within 2x of prediction (ratios survive the low-mu '
        'caveat better than absolutes)', pred_h))

    # 4. Step angle over a revolution — the proof's physical half.
    try:
        from motors.m1_sequencing import STEP_DEG, sequence_sim
        seq = sequence_sim(manager, design_name, steps=12)
        band = seq.get('alignmentBand', {})
        pred_s = ({'predictedStepDeg': STEP_DEG,
                   'predictedFullRevDeg':
                   seq['positionComparison']
                   ['actualRotationDeg'],
                   'predictedRestBandDeg': band.get('bandDeg'),
                   'basis': '360/(3 phases x 4 poles) — the m1-1 '
                            'arithmetic, pinned both ways in the '
                            'selftest. The cumulative angle falls '
                            'a band half-width short of 360 '
                            'because rest is a BAND (cons-3): '
                            'beta_r - beta_s of flat, zero-torque '
                            'alignment out of the two shape rows.'}
                  if seq.get('ok') else
                  {'refusal': seq.get('refusal', 'refused')})
    except Exception as e:
        pred_s = {'refusal': f'raised: {e}'}
    entries.append(_entry(
        'step-angle-revolution',
        'printed protractor + pointer on the shaft: 12 commanded '
        'steps, landed angle recorded at each',
        'the POSITIONING PROOF\'s physical half: per-step angle '
        'accuracy is what steps/mm rests on, and a slipped pole '
        '(-60 deg, the no-detent failure) is unmistakable on a '
        'protractor',
        {'row': 'MotorVerificationRun',
         'api': 'POST /api/motors/verify/' + M1,
         'kind': 'measured',
         'qaGate': 'qa-positioning-100-steps'},
        'each landed angle within 2 deg of n x 30; cumulative '
        '360 minus the rest band (+- 2) after 12 steps; ZERO '
        'slips', pred_s))

    # 4b. THE REST BAND itself — cons-3 predicts a number a
    # printed protractor can actually resolve, so the arc
    # geometry becomes directly falsifiable.
    entries.append(_entry(
        'reversal-backlash-band',
        'same protractor: step forward to a landing, record the '
        'angle, then command ONE step in each direction back to '
        'the same phase and record again — the difference is the '
        'lost motion',
        'THE MOST FALSIFIABLE THING cons-3 says: the exact arc '
        'overlap predicts a flat, zero-torque alignment exactly '
        'beta_r - beta_s wide, so a reversal must lose that '
        'angle and nothing more. It is a geometry claim with no '
        'material property in it — if the bench finds a much '
        'smaller band, fringing is doing more than the lumped '
        'model allows; a much larger one indicts the castings\' '
        'arcs, not the physics.',
        {'row': 'MotorVerificationRun',
         'api': 'POST /api/motors/verify/' + M1,
         'kind': 'measured'},
        'lost motion within 1 deg of the predicted band; '
        'repeatable over 5 reversals',
        (({'predictedBandDeg': band.get('bandDeg'),
           'fromArcs': band.get('fromArcs'),
           'basis': 'beta_r - beta_s straight out of the rotor '
                    'pole and stator tooth shape rows — no '
                    'material property enters it'})
         if seq.get('ok') else {'refusal': 'sequencing refused'})))

    # 5. Thermal rise at duty — the model honestly does not know.
    try:
        from motors.m1_views import m1_phase_electrics
        pe = m1_phase_electrics(manager, design_name)
        if pe.get('ok'):
            r_phase = pe['phases'][0]['rPhaseOhm']
            amps = 0.5
            pred_t = {
                'predictedDissipationW':
                round(amps * amps * r_phase, 3),
                'predictedRiseK': None,
                'basis': 'I^2 R at rated current, ONE phase on at '
                         'a time (the SRM duty) — dissipation is '
                         'solved; the RISE is UNMODELED (no '
                         'thermal model exists in this stack, '
                         'named, not estimated)'}
        else:
            pred_t = {'refusal': pe.get('refusal', 'refused')}
    except Exception as e:
        pred_t = {'refusal': f'raised: {e}'}
    entries.append(_entry(
        'thermal-rise-duty',
        'thermocouple on a tooth (the W2 thermocouple — the same '
        'wire rung that makes the kiln controllable) + 30 min at '
        'stepping duty',
        'whether continuous duty cooks the enamel or the '
        'geopolymer — the first thermal FACT in the motor stack, '
        'measured where no model exists',
        {'row': 'MotorVerificationRun',
         'api': 'POST /api/motors/verify/' + M1,
         'kind': 'measured'},
        'rise <= 40 K at rated duty (enamel class prior, NAMED) '
        '— above it, duty cycle becomes a design row', pred_t))

    return _campaign(
        design_name, 'm1-bench', entries,
        'The build steps are the m1-6 workflows (cast, wind-six, '
        'gear-reduction, assemble); this sheet is the MEASUREMENT '
        'half. SIX-of-everything is the difference from the '
        'clock: unit statistics begin here.')


def m2_bench_campaign(manager, design_name=M2):
    """m2-7: the M2 bench sheet. What is DIFFERENT from M1: the
    magnet is on the bill, so two measurements exist that could
    not before — the BACK-EMF CONSTANT, which isolates the
    magnet-and-turns product from everything else and is
    therefore the model-adjudicating measurement of the rung, and
    the COGGING MAP, where the model predicts exactly zero and so
    whatever the bench finds is pure slotting reality: a finding
    by construction."""
    entries = []

    # 1. Per-phase R, six of them — imbalance is the finding.
    try:
        from motors.m1_views import m1_phase_electrics
        pe = m1_phase_electrics(manager, design_name)
        pred_r = ({'predictedPhaseOhm':
                   pe['phases'][0]['rPhaseOhm'],
                   'predictedSpread': 0.0,
                   'basis': 'm1_phase_electrics on the M2 design '
                            'row (200 t of 22 AWG) — the SAME '
                            'engine M1 uses, called with a '
                            'different design; the model builds '
                            'six identical phases, so any spread '
                            'is a manufacturing finding'}
                  if pe.get('ok') else
                  {'refusal': pe.get('refusal', 'refused')})
    except Exception as e:
        pred_r = {'refusal': f'raised: {e}'}
    entries.append(_entry(
        'phase-resistance-six', 'multimeter (any)',
        'the winding engine at a coarser gauge — and the SPREAD, '
        'which no model can predict because the model builds six '
        'identical coils',
        {'row': 'MotorVerificationRun',
         'api': 'POST /api/motors/verify/' + M2,
         'kind': 'measured',
         'qaGate': 'qa-phase-resistance-six'},
        'each phase within 10% of prediction; spread across the '
        'six <= 5% of their mean', pred_r))

    # 2. THE ONE THAT ADJUDICATES: back-EMF constant.
    try:
        from motors.m2_rotation import back_emf_constant
        ke = back_emf_constant(manager, design_name)
        pred_k = ({'predictedKeVoltSPerRad':
                   ke['kEVoltSPerRad'],
                   'predictedFluxWb': ke['fluxPerPoleWb'],
                   'magnetBrT': ke.get('magnetBrT'),
                   'materialConsistency':
                   ke.get('materialConsistency'),
                   'basis': ke['derivation']}
                  if ke.get('ok') else
                  {'refusal': ke.get('refusal', 'refused')})
    except Exception as e:
        pred_k = {'refusal': f'raised: {e}'}
    entries.append(_entry(
        'back-emf-constant', 'oscilloscope + a hand (spin the '
        'rotor at a timed rate, scope one phase open-circuit)',
        'THE MODEL-ADJUDICATING MEASUREMENT OF THIS RUNG: k_e '
        'isolates the magnet-and-turns product from resistance, '
        'inductance, load and friction — nothing else can absorb '
        'a disagreement. If it comes in low, either the magnet '
        'prior is wrong or the magnetiser did not take, and the '
        'B_r entry below separates those two.',
        {'row': 'MotorVerificationRun',
         'api': 'POST /api/motors/verify/' + M2,
         'kind': 'measured',
         'qaGate': 'qa-back-emf-spin'},
        'within 2x of prediction (ratios survive the lumped-model '
        'caveat better than absolutes); a NULL reading is a '
        'failed magnetisation, not a model error', pred_k))

    # 3. THE COGGING MAP — the model says zero, by construction.
    try:
        from motors.m2_rotation import (
            NO_COGGING_FACT, pull_out_load_limit,
        )
        po = pull_out_load_limit(manager, design_name)
        pred_c = {'predictedDetentNm': 0.0,
                  'predictedPeakTorqueNm': (po.get('peakTorqueNm')
                                            if po.get('ok')
                                            else None),
                  'basis': NO_COGGING_FACT}
    except Exception as e:
        pred_c = {'refusal': f'raised: {e}'}
    entries.append(_entry(
        'cogging-map', 'torque wrench or a string-and-weight on '
        'the shaft, unpowered, every 5 deg through one '
        'revolution',
        'A FINDING BY CONSTRUCTION: the model predicts EXACTLY '
        'ZERO detent (a first-harmonic gap model of a round ring '
        'has no slotting in it), so whatever the bench measures '
        'is pure slotting reality with no model to argue with. '
        'It also sets the floor on smooth running — and it is '
        'NOT what holds the crucible up, which is the worm.',
        {'row': 'MotorVerificationRun',
         'api': 'POST /api/motors/verify/' + M2,
         'kind': 'measured'},
        'record the map whatever it is; a peak above 10% of the '
        'predicted running torque means slotting matters and the '
        'model needs a term it does not have', pred_c))

    # 4. Remanence — the shared M0 experiment.
    try:
        from magnetics.magnet_analysis import _named
        opt = _named(manager, 'MagneticMaterialOption',
                     'opt-sintered-hexaferrite')
        import json as _json
        props = _json.loads(getattr(opt, 'properties_json', '')
                            or '{}') if opt is not None else {}
        b_r = (props.get('b_r_t') or {}).get('value')
        pred_b = ({'predictedBrT': b_r,
                   'provenance': (props.get('b_r_t') or {})
                   .get('provenance'),
                   'basis': 'the material row prior — the SAME '
                            'entry M0 carries: one experiment '
                            '(press, sinter, magnetise, measure) '
                            'retires the prior on M0, M2 and M3 '
                            'at once'}
                  if b_r else
                  {'refusal': 'no b_r_t on the hexaferrite row'})
    except Exception as e:
        pred_b = {'refusal': f'raised: {e}'}
    entries.append(_entry(
        'remanence-br', 'gaussmeter or a calibrated pull test on '
        'the sintered blank, BEFORE assembly',
        'the literature prior every torque and k_e number on this '
        'rung rides — and measuring it on the BLANK separates a '
        'weak magnet from a failed magnetisation, which the '
        'assembled k_e cannot',
        {'row': 'MotorVerificationRun',
         'api': 'POST /api/motors/verify/' + M2,
         'kind': 'measured'},
        'within the 0.2-0.4 T class band for sintered '
        'hexaferrite; below it, the sinter or the powder is the '
        'problem', pred_b))

    # 5. Pull-out torque — the duty limit, physically.
    try:
        from motors.m2_rotation import pull_out_load_limit as _po
        po2 = _po(manager, design_name)
        pred_p = ({'predictedPullOutNm': po2['pullOutLimitNm'],
                   'predictedPeakNm': po2['peakTorqueNm'],
                   'atLagDeg': po2['atLagDeg'],
                   'crossCheck': po2.get('crossCheck'),
                   'basis': po2['basis']}
                  if po2.get('ok') else
                  {'refusal': po2.get('refusal', 'refused')})
    except Exception as e:
        pred_p = {'refusal': f'raised: {e}'}
    entries.append(_entry(
        'pull-out-torque', 'a rope, a pulley and known weights on '
        'the shaft while the drive runs at a fixed rate',
        'THE duty number the hoist is sized against — and the '
        'failure mode is the point: past it the machine does not '
        'slow down, it falls out of step and drops the load. The '
        'measurement is a step change, not a curve.',
        {'row': 'MotorVerificationRun',
         'api': 'POST /api/motors/verify/' + M2,
         'kind': 'measured'},
        'within 2x of prediction, and the LOSS OF SYNC must be '
        'abrupt — a gradual droop would mean the machine is not '
        'running synchronously at all', pred_p))

    # 6. Thermal rise at duty — no model, honestly.
    try:
        from motors.m1_views import m1_phase_electrics as _pe
        pe2 = _pe(manager, design_name)
        if pe2.get('ok'):
            r_phase = pe2['phases'][0]['rPhaseOhm']
            import json as _json2
            from motors.motor_designer import _design, _loads
            amps = float(_loads(_design(manager, design_name),
                                'params_json', {})['coil_amps'])
            pred_t = {'predictedDissipationW': r_phase * amps ** 2,
                      'predictedRiseK': None,
                      'basis': 'I^2R with all three phases '
                               'carrying — SOLVED. The '
                               'temperature RISE is not modelled '
                               'at all: no thermal path, no '
                               'convection, no mass.'}
        else:
            pred_t = {'refusal': pe2.get('refusal', 'refused')}
    except Exception as e:
        pred_t = {'refusal': f'raised: {e}'}
    entries.append(_entry(
        'thermal-rise-duty', 'thermocouple (the W2 instrument the '
        'wire rung unlocks) on a coil and on the magnet ring',
        'dissipation is SOLVED and rise is UNMODELLED — and on '
        'THIS rung the ring is the part to watch: ferrite loses '
        'remanence with temperature and comes back weaker, so a '
        'hot hoist is a hoist that lifts less next time',
        {'row': 'MotorVerificationRun',
         'api': 'POST /api/motors/verify/' + M2,
         'kind': 'measured'},
        'coil rise <= 40 K (enamel class prior, NAMED); ring '
        'temperature well under the ferrite Curie margin — above '
        'it, duty cycle becomes a design row', pred_t))

    return _campaign(
        design_name, 'm2-bench', entries,
        'The build steps are the m2-6 workflows (press-sinter, '
        'worm stage, assemble-then-MAGNETISE); this sheet is the '
        'MEASUREMENT half. The magnet is what is new, and it '
        'brings both the measurement that adjudicates the model '
        '(k_e) and the one the model refuses to make (cogging).')


def _campaign(design_name, campaign, entries, closing_note):
    refused = [e['measurement'] for e in entries
               if e.get('refusal')]
    return {
        'ok': True, 'design': design_name,
        'campaign': campaign,
        'order': [e['measurement'] for e in entries],
        'measurements': entries,
        'refusedPredictions': refused,
        'note': 'predictions are computed LIVE at request time — '
                'a re-seeded material or a retuned winding '
                'changes the sheet, never a stale copy. '
                + closing_note,
    }
