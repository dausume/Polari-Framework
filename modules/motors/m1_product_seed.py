"""
@module motors.m1_product_seed

m1-6: M1 as a PRODUCT — the axis-drive unit for the wax printer,
in the mp0 shapes (workflows, formula, QA gate, two routes), with
the differences M1 itself brings:

- NO MAGNET ON THE BILL — that is the rung's whole point, and the
  routes say so instead of leaving a silent hole where the
  magnet-press workflow used to be.
- THE ROUTE DIFFERENCE IS THE STATOR: cast geopolymer (mu~2,
  castable TODAY, honestly feeble) vs galvanized bio-steel vs
  fired ferrite — a THREE-WAY fork, each option quantified LIVE by
  the same holding-torque engine via material override, never by
  an adjective.
- THE DRIVETRAIN IS PART OF THE PRODUCT: m1-5 proved the bare
  motor not-capable (~65x short), so the unit ships motor + gear
  reduction. The seeded ratio is GUARD-TESTED against the live
  axis shortfall (two modules, one fact) — if a requirement row
  moves, the stale ratio fails the suite instead of shipping.
- THE FIRST REAL BATCH: four identical units per printer. Batch
  facts ride the workflow and formula rows; the sell-iterate loop
  is the same one (the product feeds the printer, the printer
  feeds the tree).

@consumers motors.product_routes_seed (dispatch), motors.m1_views_seed
(sourcing section), polariServer seed pass (seed_m1_product)
"""

import json
import math

from moduleService.seed_upsert import upsert_seed_pairs

M1_DESIGN = 'reluctance-6s4p-m1'
PRODUCT = 'm1-axis-drive'
UNITS_PER_PRINTER = 4
#: ceil(demand / (PULL-IN limit / 1.5)) at the seeded axis rows —
#: sized by the pull-in limit, NOT holding torque: the live probe
#: proved a holding-sized 98:1 still loses steps (pull-in is
#: ~0.17x holding, the m1-1 finding, widened by cons-3's exact
#: overlap). 265, down from 304, because widening the tooth arc
#: to satisfy the SRM arc rule also bought 18% more tooth face.
#: The selftest re-derives this from the LIVE axis report and
#: fails if they drift, EQUALITY not >= (the wire-ladder lesson:
#: a ratio that merely covers the need hides the need moving).
GEAR_RATIO = 265
PROV = 'm1-6'


SEED_M1_WORKFLOWS = [
    {'name': 'm1-cast-stator-rotor-workflow',
     'display_name': 'Cast the 6-tooth stator + salient rotor',
     'product_item_ref': PRODUCT,
     'mold_strategy': 'ceramic-fired',
     'hours_per_unit_ref': 2.0, 'hours_per_mold_ref': 0.0,
     'passive_hours_per_batch': 14.0,
     'volume_exponent': 0.667,
     'steps_json': json.dumps(
         ['mix + cast stator (one pour, six teeth)',
          'mix + cast rotor (one pour, four poles)', 'dry',
          'cure/fire per stator-fork option (passive)',
          'grind gap faces', 'qa-visual-crack',
          'hand-spin clearance check (ifm1-working-gap)']),
     'is_prior': True, 'provenance_id': PROV,
     'notes': 'ONE pour per casting — the mold-fused boundaries '
              '(m1-4) are made here. Batch of 8 castings = 4 '
              'units. HOUR PRIORS ARE ESTIMATES until timed.'},
    {'name': 'm1-wind-six-coils-workflow',
     'display_name': 'Wind six phase coils (300 turns, 26 AWG)',
     'product_item_ref': PRODUCT,
     'mold_strategy': 'ceramic-fired',
     'hours_per_unit_ref': 2.0, 'hours_per_mold_ref': 0.0,
     'passive_hours_per_batch': 0.0,
     'volume_exponent': 0.667,
     'steps_json': json.dumps(
         ['wind 6 x 300 turns on formers (cv-m1-tooth-bobbin '
          'construction unless the fork decides otherwise)',
          'qa-phase-resistance-six (records ALL six R — the '
          'imbalance seam, m1-7)', 'slide bobbins over teeth',
          'wire the three series pairs']),
     'is_prior': True, 'provenance_id': PROV,
     'notes': '26 AWG is W2-EASY (coarse) — no drawing drama; '
              '24 coils per printer batch.'},
    {'name': 'm1-gear-reduction-workflow',
     'display_name': 'Build the ~265:1 reduction',
     'product_item_ref': PRODUCT,
     'mold_strategy': 'ceramic-fired',
     'hours_per_unit_ref': 3.0, 'hours_per_mold_ref': 0.0,
     'passive_hours_per_batch': 14.0,
     'volume_exponent': 0.667,
     'steps_json': json.dumps(
         ['solve stages with the gears module (gr-1 train '
          'machinery; three ~7:1 stages)',
          'cast/fire gear blanks (pd-gears profiles — generate, '
          'never approximate)', 'assemble train',
          'backlash check (a positioning term, recorded)']),
     'is_prior': True, 'provenance_id': PROV,
     'notes': 'the m1-5 knob APPLIED, sized by PULL-IN (~202x '
              'demand/limit x 1.5 margin — holding torque would '
              'have said 98:1 and lost steps). Resolution '
              'multiplies by the ratio; travel speed falls by it '
              'and is honestly SLOW at the assumed 5 Hz rate — '
              'the dynamic model that would permit faster '
              'stepping is a named gap, and the bio-steel fork '
              'is the ratio\'s other knob.'},
    {'name': 'm1-axis-assemble-workflow',
     'display_name': 'Assemble + QA four axis units per printer',
     'product_item_ref': PRODUCT,
     'mold_strategy': 'ceramic-fired',
     'hours_per_unit_ref': 1.5, 'hours_per_mold_ref': 0.0,
     'passive_hours_per_batch': 0.0,
     'volume_exponent': 0.667,
     'steps_json': json.dumps(
         ['press rotor on shaft (608 bearing, mag-1 cited)',
          'mount reduction + couple M8 leadscrew',
          'SimpleFOC drive bring-up (the mag-6 profile)',
          'qa-positioning-100-steps PER UNIT',
          'record per-unit results (batch of four = the first '
          'real batch statistics)']),
     'is_prior': True, 'provenance_id': PROV,
     'notes': 'FOUR IDENTICAL UNITS is the first real batch — '
              'unit-to-unit spread feeds sell-iterate learning '
              'the single clock never could.'},
]

SEED_M1_FORMULA = [
    {'name': 'm1-axis-drive-formula',
     'display_name': 'M1 axis drive (motor + reduction), per unit',
     'product_item_ref': PRODUCT,
     'components_json': json.dumps([
         {'item_ref': 'geopolymer-mix', 'role': 'structure',
          'fraction': 0.70,
          'note': '~0.35 kg: stator + rotor castings AND the '
                  'gear blanks (prior); the stator fork can swap '
                  'this line, and the routes say for what'},
         {'item_ref': 'magnet-wire-copper', 'role': 'windings',
          'fraction': 0.15,
          'note': '~72 g DERIVED: 6 coils x 300 turns x 35 mm '
                  'MTL = 63 m of 26 AWG at 1.14 g/m — the '
                  'winding math object\'s number, not a guess'},
         {'item_ref': 'steel-hardware', 'role': 'shaft-bearing-'
                                               'leadscrew',
          'fraction': 0.15,
          'note': '8 mm shaft + 608 bearing + M8x1.25 rod — '
                  'hardware-store parts, both routes buy these '
                  '(mag-1 argument)'}]),
     'yield_fraction': 0.8, 'status': 'candidate',
     'is_prior': True, 'provenance_id': PROV,
     'notes': f'PER UNIT; a printer consumes '
              f'{UNITS_PER_PRINTER}x. NO MAGNET LINE — the '
              f'point of the rung, visible in the formula.'},
]

SEED_M1_QA = [
    {'name': 'qa-positioning-100-steps',
     'display_name': '100-step positioning check',
     'product_kind': PRODUCT,
     'method': 'Command +100 then -100 steps under axis load; '
               'measure landed position with calipers against '
               'commanded (the m1-5 proof, physically). Record '
               'as MotorVerificationRun (kind=measured).',
     'acceptance': 'position error <= 0.2 mm each way (the '
                   'axis-position-tolerance row), zero slips',
     'frequency': 'per-unit',
     'is_prior': True, 'provenance_id': PROV,
     'notes': 'the positioning-proof endpoint PREDICTS this; '
              'this measures it — a passing record per unit is '
              'what earns the batch made-and-measured.'},
    {'name': 'qa-phase-resistance-six',
     'display_name': 'Six-phase resistance record',
     'product_kind': PRODUCT,
     'method': 'Measure ALL SIX coil resistances before assembly '
               '(W2 multimeter); record each.',
     'acceptance': 'spread <= 5% of mean — the model predicts '
                   'IDENTICAL coils, so the spread is a '
                   'manufacturing finding (m1-7)',
     'frequency': 'per-unit',
     'is_prior': True, 'provenance_id': PROV,
     'notes': 'imbalance is only actionable while coils still '
              'swap (cv-m1-tooth-bobbin) — the fork rationale, '
              'as a QA row.'},
]


def stator_fork(manager, design_name=M1_DESIGN):
    """The THREE-WAY stator fork, each option quantified LIVE by
    the same engine (holding_torque with material override) —
    the m1-6 decision surface, evidence attached."""
    from motors.custom.m1_sequencing import holding_torque
    from motors.m1_positioning_basis import axis_report
    axis = axis_report(manager, design_name)
    demand = (axis.get('loadTorqueDemandNm')
              if axis.get('ok') else None)
    options = []
    for label, mat, story in (
            ('cast-geopolymer',
             '',   # design as seeded
             'castable TODAY — closes the cast-wind-drive-spin '
             'loop; honestly feeble at mu~2, which is why the '
             'reduction exists'),
            ('galvanized-bio-steel',
             'opt-galvanized-bio-steel',
             'the biocarbon-reduced steel route — a real soft '
             'conductor; needs the galvanizing/forming rung, '
             'named in its option row'),
            ('fired-ferrite',
             'opt-fired-ferrite-ceramic',
             'cone 8-10 kiln is an OWNED rung — the fired body '
             'trades castable-today for real permeability')):
        hold = holding_torque(manager, design_name,
                              stator_material=mat,
                              rotor_material=mat)
        if not hold.get('ok'):
            options.append({'option': label, 'story': story,
                            'gap': hold.get('refusal')})
            continue
        t = hold['peakTorqueNm']
        entry = {'option': label, 'story': story,
                 'holdingTorqueNm': t,
                 'evidence': 'holding_torque solved live with '
                             'this material in both slots'}
        if demand:
            entry['bareMotorCoversAxis'] = t > demand
            entry['reductionStillNeeded'] = (
                None if t > demand
                else math.ceil(demand / t * 1.5))
        options.append(entry)
    return {'ok': True, 'design': design_name,
            'axisDemandNm': demand, 'options': options,
            'note': 'no option is preferred by the code — the '
                    'numbers and the named capability gaps ARE '
                    'the decision surface; the magnet column is '
                    'ABSENT because M1 has none'}


def m1_product_routes(manager, design_name=M1_DESIGN):
    """The complete M1 product, twice — same contract as the M0
    routes (make names its workflow, buy names its citation, gaps
    stay in the payload), with the drivetrain included and the
    stator fork attached."""
    from motors.m1_positioning_basis import axis_report
    fork = stator_fork(manager, design_name)
    axis = axis_report(manager, design_name)
    drivetrain = {
        'gearRatio': GEAR_RATIO,
        'basis': 'ceil(demand / (pull-in limit / 1.5)) at the '
                 'seeded axis rows — sized by PULL-IN, never '
                 'holding torque; guard-tested against '
                 'axis_report so it cannot silently go stale',
        'live': ({'shortfall': axis.get('shortfall'),
                  'requiredNow': next(
                      (k['requiredRatio'] for k in
                       axis.get('knobs', [])
                       if 'requiredRatio' in k), None)}
                 if axis.get('ok') else
                 {'gap': axis.get('refusal')}),
        'note': 'the m1-5 verdict APPLIED: the unit ships motor + '
                'reduction; resolution improves by the ratio, '
                'speed falls by it (and was an assumption)'}
    common_make = [
        {'input': 'stator + rotor castings', 'source': 'make',
         'workflow': 'm1-cast-stator-rotor-workflow',
         'capability': 'casting (owned); fork option decides the '
                       'cure/fire leg'},
        {'input': 'six phase coils', 'source': 'make',
         'workflow': 'm1-wind-six-coils-workflow',
         'capability': 'hand winding, 300 turns x6 — 26 AWG, '
                       'W2-EASY (no drawing drama)'},
        {'input': 'gear reduction (~265:1)', 'source': 'make',
         'workflow': 'm1-gear-reduction-workflow',
         'capability': 'gr-1 train solve + cast/fired gears '
                       '(generate, never approximate)'},
        {'input': 'assembly + QA x4', 'source': 'make',
         'workflow': 'm1-axis-assemble-workflow',
         'capability': 'SimpleFOC bring-up (mag-6 profile)'},
    ]
    local = {
        'route': 'pure-local', 'policy': 'local-made-only',
        'statorOption': 'cast-geopolymer (today) -> '
                        'galvanized-bio-steel (when its rung '
                        'lands)',
        'inputs': common_make + [
            {'input': 'magnet wire (26 AWG)', 'source': 'make',
             'workflow': 'clock-wire-draw-workflow',
             'capability': 'coarse drawing — EASIER than the '
                           'clock\'s 38 AWG; same dies, fewer '
                           'passes'},
            {'input': 'leadscrew', 'source': 'make-adjacent',
             'note': 'M8x1.25 threaded rod from local hardware '
                     '(the axis-leadscrew-lead row\'s basis)'},
        ],
        'blockers': [
            'W2 wire drawing undemonstrated (shared with M0 — '
            'one rung unlocks both)',
            'bio-steel stator waits on the galvanizing/forming '
            'rung (named in its option row)',
        ],
        'note': 'NO MAGNET BLOCKER — compare the M0 route: the '
                'hardest M0 input simply does not exist here. '
                'That is what the rung is FOR.'}
    commercial = {
        'route': 'commercial', 'policy': 'any',
        'statorOption': 'fired-ferrite (owned kiln) or bought '
                        'electrical-steel laminations (uncited '
                        '— a gap, not an option, until a '
                        'PriceCitation lands)',
        'inputs': common_make + [
            {'input': 'magnet wire (26 AWG)', 'source': 'buy',
             'note': 'commodity spool; the M0 wire citation '
                     'machinery applies unchanged'},
            {'input': 'leadscrew (Tr8x8)', 'source': 'buy',
             'note': '6.4x the travel per rev of the M8 rod — '
                     'buys speed, costs resolution; steps/mm '
                     'DERIVES either way from the same row'},
        ],
        'blockers': [],
        'irony': 'a NEMA17 stepper costs ~$10 and beats this '
                 'motor outright — the unit is judged as a '
                 'LOCAL-CAPABILITY product on the bootstrap '
                 'chain (clock -> printer -> ...), and says so'}
    return {
        'ok': True, 'design': design_name, 'product': PRODUCT,
        'unitsPerPrinter': UNITS_PER_PRINTER,
        'drivetrain': drivetrain,
        'statorFork': fork,
        'routes': [local, commercial],
        'formula': 'm1-axis-drive-formula',
        'sellLoop': 'clock-sell-iterate-workflow',
        'qaGate': 'qa-positioning-100-steps',
        'note': 'both routes end at the same positioning QA gate '
                'and the SAME sell-iterate loop as the clock — '
                'the batch of four is the first real batch, and '
                'its spread is the first real statistics'}


def seed_m1_product(manager):
    """m1-6 rows via the upsert path; bizops/supplychain classes
    guarded exactly as the M0 product seeds are. Also converges
    the M1 SHAPE rows (mq-2): they were legacy-seeded insert-only,
    so the box→annular_sector/arc_faced_bar reshape never reached
    live rows until they rode the upsert path too — the
    ten-strikes gotcha, caught an eleventh time, on shapes."""
    pairs = []
    try:
        from mathshapes.shape_basis import MathShapeDefinition
        from motors.motor_shapes_seed import SEED_M1_PART_SHAPES
        pairs.append(('MathShapeDefinition', MathShapeDefinition,
                      SEED_M1_PART_SHAPES))
    except ImportError:
        pass
    try:
        from bizops.bizops_basis import ProcessWorkflowDefinition
        pairs.append(('ProcessWorkflowDefinition',
                      ProcessWorkflowDefinition,
                      SEED_M1_WORKFLOWS))
    except ImportError:
        pass
    try:
        from bizops.bizops_basis import QualityCheckDefinition
        pairs.append(('QualityCheckDefinition',
                      QualityCheckDefinition, SEED_M1_QA))
    except ImportError:
        pass
    try:
        from supplychain.sourcing_basis import ProductFormula
        pairs.append(('ProductFormula', ProductFormula,
                      SEED_M1_FORMULA))
    except ImportError:
        pass
    return upsert_seed_pairs(manager, pairs, tag='M1ProductSeed')
