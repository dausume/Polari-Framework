"""
@module motors.m2_product

m2-6: M2 as a PRODUCT — the hoist drive for the crucible hoist,
in the same mp0 shapes (workflows, formula, QA gate, two routes),
with the differences M2 itself brings:

- THE ROUTE DIFFERENCE IS THE MAGNET, and only the magnet. The
  stator route is M1's, unchanged and referenced — same molds,
  same coil workflow, same wire. That is the ladder paying off:
  the second machine costs one new mold, one bond and a magnet.
- THE MAGNET ROUTE IS M0'S NAMED EXPERIMENT. Pure-local means
  press-sinter-magnetize SrFe12O19, which is the SAME workflow
  the clock rung already carries — cited, not copied. Commercial
  means a bought ferrite ring, which needs a PriceCitation row
  and honestly does not have one yet.
- THE UNIT SHIPS A REDUCTION STAGE, like M1's. The m2-5 proof
  says the bare motor is 5.7x short on a 30:1 worm, so a spur
  stage goes in front of it; STAGE_RATIO is guard-tested against
  the LIVE lift report so a moved requirement row fails the suite
  instead of shipping stale.
- MAGNETISE LAST. The assembly workflow ends on op-m2-magnetize
  (m2-4), because every earlier step is easier while the ring is
  still inert.
- THE QA GATE IS A SAFETY GATE: hold a suspended crucible for 24
  hours with the power off. A timekeeping gate measures drift; a
  hoist gate measures whether something falls.

@consumers motors.product_routes (dispatch), motors.m2_views
(sourcing section), polariServer seed pass (seed_m2_product)
"""

import json
import math

from composition.seed_upsert import upsert_seed_pairs

M2_DESIGN = 'ferrite-pm-m2'
M1_DESIGN = 'reluctance-6s4p-m1'
PRODUCT = 'm2-hoist-drive'
UNITS_PER_HOIST = 1
#: ceil(duty x margin / pull-out limit) at the seeded hoist rows —
#: the reduction stage that goes BETWEEN the motor and the
#: self-locking worm. The worm stays 30:1 because that is the
#: self-locking arrangement the safety argument rests on. The
#: selftest re-derives this from the LIVE lift report and fails on
#: EQUALITY, not >=, so an oversized stage cannot hide a moved
#: requirement (the wire-ladder lesson, M1's guard).
STAGE_RATIO = 6
PROV = 'm2-6'


SEED_M2_WORKFLOWS = [
    {'name': 'm2-press-sinter-ring-workflow',
     'display_name': 'Press + sinter the ferrite rotor ring',
     'product_item_ref': PRODUCT,
     'mold_strategy': 'ceramic-fired',
     'hours_per_unit_ref': 1.5, 'hours_per_mold_ref': 0.0,
     'passive_hours_per_batch': 16.0,
     'volume_exponent': 0.667,
     'steps_json': json.dumps(
         ['mill + mix SrFe12O19 powder with binder (the M0 '
          'magnet route\'s own recipe — cited, not re-derived)',
          'press the ring in a die (annular, 12.2/8.2 mm)',
          'burn out binder, sinter to closed porosity (kiln, '
          'passive)',
          'measure B_r on the sintered blank BEFORE assembly — '
          'the bench entry that retires the literature prior',
          'lap the outer diameter to the gap budget']),
     'is_prior': True, 'provenance_id': PROV,
     'notes': 'SHARED WITH M0: this is the same press-sinter-'
              'magnetize experiment the clock rung named, at a '
              'different shape. One experiment, three rungs — '
              'and the magnetise step is deliberately NOT here '
              '(it happens after assembly, op-m2-magnetize).'},
    {'name': 'm2-worm-stage-workflow',
     'display_name': 'Build the reduction + self-locking worm '
                     'stage',
     'product_item_ref': PRODUCT,
     'mold_strategy': 'ceramic-fired',
     'hours_per_unit_ref': 4.0, 'hours_per_mold_ref': 0.0,
     'passive_hours_per_batch': 14.0,
     'volume_exponent': 0.667,
     'steps_json': json.dumps(
         ['solve the spur pair with the gears module (gr-1 train '
          'machinery; involute profiles generated, never '
          'approximated)',
          'cast/fire the spur blanks and the worm wheel',
          'cut or cast the single-start worm',
          'assemble; check backlash (a lift term, recorded)',
          'BACK-DRIVE TEST: hang the load and try to turn the '
          'drum by hand — the self-locking claim, tested before '
          'anyone trusts it']),
     'is_prior': True, 'provenance_id': PROV,
     'notes': 'the m2-5 knob APPLIED. The worm is the SAFETY '
              'part: its lossiness is what holds the crucible up '
              'when the power dies, so the back-drive test is '
              'not optional.'},
    {'name': 'm2-assemble-magnetize-workflow',
     'display_name': 'Assemble the rotor, then magnetise it',
     'product_item_ref': PRODUCT,
     'mold_strategy': 'ceramic-fired',
     'hours_per_unit_ref': 2.0, 'hours_per_mold_ref': 0.0,
     'passive_hours_per_batch': 12.0,
     'volume_exponent': 0.667,
     'steps_json': json.dumps(
         ['bond the INERT ring to the cast carrier (op-m2-bond), '
          'concentric within the 0.4 mm gap budget',
          'cure the bond (passive)',
          'press the rotor onto the reused 8 mm shaft '
          '(op-m2-press-shaft)',
          'MAGNETISE in a four-pole fixture (op-m2-magnetize) — '
          'LAST, because a magnetised ring grabs every tool and '
          'collects swarf in the gap it is about to run in',
          'slide the six M1 bobbins on, wire the three phases '
          '(m1-wind-six-coils-workflow makes them)',
          'SimpleFOC + rotor-position sensor bring-up',
          'qa-lift-hold-24h']),
     'is_prior': True, 'provenance_id': PROV,
     'notes': 'THE ORDER IS THE CONTENT: the gr-3 two-material '
              'lesson (magnetise after joining) as a workflow, '
              'and the arch-4 op rows say the same thing in the '
              'routing.'},
]

SEED_M2_FORMULA = [
    {'name': 'm2-hoist-drive-formula',
     'display_name': 'M2 hoist drive (motor + stage + worm), per '
                     'unit',
     'product_item_ref': PRODUCT,
     'components_json': json.dumps([
         {'item_ref': 'geopolymer-mix', 'role': 'structure',
          'fraction': 0.55,
          'note': 'stator castings (M1\'s molds), the '
                  'non-magnetic carrier, and the gear blanks — '
                  'the reused stator is why this line is smaller '
                  'than a new machine\'s would be'},
         {'item_ref': 'ceramic-ring-magnet', 'role': 'rotor-'
                                                    'magnet',
          'fraction': 0.15,
          'note': '~8.5 g of sintered hexaferrite DERIVED from '
                  'the ring shape row and the option density — '
                  'THE line M1\'s formula does not have, and the '
                  'whole difference between the rungs'},
         {'item_ref': 'magnet-wire-copper', 'role': 'windings',
          'fraction': 0.15,
          'note': '6 coils x 200 turns x 35 mm MTL of 22 AWG — '
                  'coarser wire than M1 at fewer turns, which is '
                  'the same winding math object answering a '
                  'different design row'},
         {'item_ref': 'steel-hardware', 'role': 'shaft-bearing-'
                                               'drum',
          'fraction': 0.15,
          'note': '8 mm shaft + 608 bearing + drum and rope — '
                  'both routes buy these (the mag-1 argument)'}]),
     'yield_fraction': 0.8, 'status': 'candidate',
     'is_prior': True, 'provenance_id': PROV,
     'notes': f'PER UNIT; a hoist consumes {UNITS_PER_HOIST}. '
              f'The magnet line is the rung.'},
]

SEED_M2_QA = [
    {'name': 'qa-lift-hold-24h',
     'display_name': '24-hour powered-off hold',
     'product_kind': PRODUCT,
     'method': 'Lift the full crucible to working height, cut '
               'power at the drive, and leave it for 24 hours '
               'with a marked reference on the rope. Measure the '
               'drop. Then, with the load still hanging, try to '
               'back-drive the drum by hand. Record as '
               'MotorVerificationRun (kind=measured).',
     'acceptance': 'ZERO measurable drop in 24 h and no hand '
                   'back-drive — the self-locking claim, or the '
                   'hoist does not ship',
     'frequency': 'per-unit',
     'is_prior': True, 'provenance_id': PROV,
     'notes': 'THE SAFETY GATE, and the reason it is per-unit: '
              'the clock\'s 24-hour gate measures drift, this '
              'one measures whether 2 kg of hot metal stays in '
              'the air. It tests the WORM, not the motor — the '
              'model predicts no cogging at all and the product '
              'does not need any.'},
    {'name': 'qa-back-emf-spin',
     'display_name': 'Hand-spin back-EMF check',
     'product_kind': PRODUCT,
     'method': 'Spin the assembled rotor by hand at a timed '
               'rate, scope one phase, record peak volts and '
               'rev/s. Compare with the m2-1 k_e prediction.',
     'acceptance': 'within 2x of prediction (ratios survive the '
                   'lumped-model caveat better than absolutes); '
                   'a null reading means the magnetiser did not '
                   'take, which is the failure this catches '
                   'before assembly goes further',
     'frequency': 'per-unit',
     'is_prior': True, 'provenance_id': PROV,
     'notes': 'the cheapest possible test that the magnetise '
              'step worked at all — a scope, a hand, and the one '
              'number the model cannot fudge.'},
]


def magnet_route_fork(manager, design_name=M2_DESIGN):
    """THE M2 decision surface: where the magnet comes from. Both
    options quantified LIVE by the same engine (pull-out with a
    material override), because a magnet grade is not an
    adjective."""
    from motors.m2_rotation import back_emf_constant
    from motors.m2_rotation import pull_out_load_limit
    options = []
    for label, mat, story in (
            ('press-sinter-local', 'opt-sintered-hexaferrite',
             'OUR OWN SrFe12O19, pressed and sintered in the '
             'kiln rung we already own — the same named '
             'experiment M0 carries, at a ring shape. The B_r is '
             'a literature prior until that experiment runs.'),
            ('bonded-castable', 'opt-bonded-hexaferrite-'
                                'geopolymer',
             'the CASTABLE grade — hexaferrite powder in '
             'geopolymer, which needs no die and no sinter, but '
             'gives roughly a third of the remanence. It is what '
             'we could make this week.'),
            ('bought-ferrite-ring', 'opt-sintered-hexaferrite',
             'a commodity ceramic ring magnet, the same class of '
             'part in every cheap BLDC fan. Buyable-cited in '
             'mag-1; a PriceCitation row is what turns the cited '
             'tier into a costed line.')):
        po = pull_out_load_limit(manager, design_name,
                                 rotor_material=mat)
        ke = back_emf_constant(manager, design_name,
                               rotor_material=mat)
        entry = {'option': label, 'material': mat, 'story': story}
        if po.get('ok'):
            entry['pullOutLimitNm'] = po['pullOutLimitNm']
        else:
            entry['gap'] = po.get('refusal')
        if ke.get('ok'):
            entry['kEVoltSPerRad'] = ke['kEVoltSPerRad']
            entry['magnetBrT'] = ke.get('magnetBrT')
        options.append(entry)
    return {
        'ok': True, 'design': design_name, 'options': options,
        'note': 'the two SINTERED options are the same material '
                'row and therefore the same numbers — the '
                'difference between them is not physics but '
                'PROVENANCE (our kiln vs a purchase order), and '
                'pretending otherwise would be the kind of fake '
                'distinction the routes exist to avoid',
        'sharedExperiment': 'press-sinter-magnetize SrFe12O19 is '
                            'ONE experiment shared with M0; its '
                            'B_r measurement retires the prior '
                            'on every rung at once'}


def m2_product_routes(manager, design_name=M2_DESIGN):
    """The complete M2 product, twice — same contract as the M0
    and M1 routes (make names its workflow, buy names its
    citation, gaps stay in the payload), with the drivetrain
    included and the magnet fork attached."""
    from motors.m2_lift import hoist_report
    fork = magnet_route_fork(manager, design_name)
    hoist = hoist_report(manager, design_name)
    drivetrain = {
        'stageRatio': STAGE_RATIO,
        'wormRatio': (hoist['torqueChain']['wormRatio']
                      if hoist.get('ok') else None),
        'totalReduction': (STAGE_RATIO
                           * hoist['torqueChain']['wormRatio']
                           if hoist.get('ok') else None),
        'basis': 'ceil(duty x 1.5 margin / pull-out limit) at the '
                 'seeded hoist rows — sized by PULL-OUT, the '
                 'limit past which a synchronous machine does not '
                 'droop but drops its load; guard-tested against '
                 'hoist_report so it cannot silently go stale',
        'live': ({'shortfall': hoist.get('shortfall'),
                  'requiredNow': hoist.get('requiredStageRatio')}
                 if hoist.get('ok') else
                 {'gap': hoist.get('refusal')}),
        'note': 'the m2-5 verdict APPLIED: the unit ships motor + '
                'spur stage + self-locking worm. The worm stays '
                '30:1 because that is the SAFETY part; the spur '
                'stage is where the missing torque comes from.'}
    common_make = [
        {'input': 'stator castings (yoke + six teeth)',
         'source': 'make', 'workflow':
         'm1-cast-stator-rotor-workflow',
         'capability': 'THE SAME MOLD AS M1 — the stator is not '
                       'redesigned, it is reused (PART_REUSE); '
                       'only the rotor cavity of that workflow '
                       'goes unused'},
        {'input': 'six phase coils (200 t, 22 AWG)',
         'source': 'make', 'workflow': 'm1-wind-six-coils-workflow',
         'capability': 'hand winding on M1\'s bobbins — 22 AWG is '
                       'coarser than M1\'s 26, so W2-EASIER '
                       'again'},
        {'input': 'non-magnetic rotor carrier', 'source': 'make',
         'workflow': 'm1-cast-stator-rotor-workflow',
         'capability': 'plain geopolymer, cast — magnetically '
                       'useless on purpose'},
        {'input': f'reduction stage ({STAGE_RATIO}:1) + '
                  f'self-locking worm (30:1)',
         'source': 'make', 'workflow': 'm2-worm-stage-workflow',
         'capability': 'gr-1 train solve + cast/fired gears; the '
                       'worm is the safety part and gets the '
                       'back-drive test'},
        {'input': 'assembly + magnetise + QA', 'source': 'make',
         'workflow': 'm2-assemble-magnetize-workflow',
         'capability': 'four-pole magnetising fixture (W2) — the '
                       'one new tool this rung actually needs'},
    ]
    local = {
        'route': 'pure-local', 'policy': 'local-made-only',
        'magnetOption': 'press-sinter-local (our SrFe12O19) -> '
                        'bonded-castable as the fallback that '
                        'needs no die',
        'inputs': common_make + [
            {'input': 'ferrite rotor ring', 'source': 'make',
             'workflow': 'm2-press-sinter-ring-workflow',
             'capability': 'THE named experiment, shared with M0 '
                           '— press, sinter, and (after '
                           'assembly) magnetise'},
            {'input': 'magnet wire (22 AWG)', 'source': 'make',
             'workflow': 'clock-wire-draw-workflow',
             'capability': 'coarser than either earlier rung — '
                           'the easiest drawing on the ladder'},
        ],
        'blockers': [
            'press-sinter-magnetize is UNDEMONSTRATED: no '
            'measured B_r, no proven die, no magnetiser built. '
            'This is the same blocker M0 carries, and one '
            'experiment clears it for both.',
            'W2 wire drawing undemonstrated (shared with M0/M1)',
        ],
        'note': 'the STATOR carries no new blockers at all — it '
                'is M1\'s, already routed. The entire pure-local '
                'risk of this rung is the magnet.'}
    commercial = {
        'route': 'commercial', 'policy': 'any',
        'magnetOption': 'bought-ferrite-ring (buyable-cited in '
                        'mag-1; needs a PriceCitation row to be '
                        'a costed line rather than a claim)',
        'inputs': common_make + [
            {'input': 'ferrite ring magnet', 'source': 'buy',
             'note': 'commodity ceramic ring — the exact part in '
                     'every cheap BLDC fan rotor. UNCITED PRICE: '
                     'a gap, stated, not an estimate'},
            {'input': 'magnet wire (22 AWG)', 'source': 'buy',
             'note': 'commodity spool; the M0 wire citation '
                     'machinery applies unchanged'},
        ],
        'blockers': [
            'no PriceCitation row for the ring magnet — the '
            'commercial route cannot be costed honestly until '
            'one lands',
        ],
        'irony': 'a $15 gear motor lifts 2 kg and holds it, and '
                 'a $10 hoist winch exists — the unit is judged '
                 'as a LOCAL-CAPABILITY product on the bootstrap '
                 'chain (clock -> printer -> HOIST -> drill), '
                 'and says so. The hoist is what lets the '
                 'foundry pour without a second person.'}
    return {
        'ok': True, 'design': design_name, 'product': PRODUCT,
        'unitsPerHoist': UNITS_PER_HOIST,
        'drivetrain': drivetrain,
        'magnetFork': fork,
        'statorReuse': {
            'from': M1_DESIGN,
            'note': 'the stator route is M1\'s, referenced not '
                    'restated: same molds, same coil workflow, '
                    'same wire drawing. THAT is what a ladder '
                    'rung is supposed to buy.'},
        'routes': [local, commercial],
        'formula': 'm2-hoist-drive-formula',
        'sellLoop': 'clock-sell-iterate-workflow',
        'qaGate': 'qa-lift-hold-24h',
        'note': 'both routes end at the same SAFETY gate: hold a '
                'suspended crucible for 24 hours with the power '
                'off. A clock gate measures drift; a hoist gate '
                'measures whether something falls.'}


def seed_m2_product(manager):
    """m2-6 rows via the upsert path; bizops/supplychain classes
    guarded exactly as the M0/M1 product seeds are."""
    pairs = []
    try:
        from bizops.bizops_basis import ProcessWorkflowDefinition
        pairs.append(('ProcessWorkflowDefinition',
                      ProcessWorkflowDefinition,
                      SEED_M2_WORKFLOWS))
    except ImportError:
        pass
    try:
        from bizops.bizops_basis import QualityCheckDefinition
        pairs.append(('QualityCheckDefinition',
                      QualityCheckDefinition, SEED_M2_QA))
    except ImportError:
        pass
    try:
        from supplychain.sourcing_basis import ProductFormula
        pairs.append(('ProductFormula', ProductFormula,
                      SEED_M2_FORMULA))
    except ImportError:
        pass
    if not pairs:
        return [{'class': 'ProcessWorkflowDefinition',
                 'inserted': [], 'updated': [],
                 'errors': ['bizops/supplychain not importable']}]
    return upsert_seed_pairs(manager, pairs, tag='M2ProductSeed')
