"""
@module motors.product_routes_seed

mp0 (Dustin 2026-08-01): "finish off M0 work so it is a complete
product with both pure local and commercial sourcing routes" +
"complete business process workflows and purchase flows for making
the clock and selling it iteratively."

THE PRODUCT — clock-lavet-m0b: the M0 design carrying the SOLVED
winding (mag-25's simplest-case numbers, lifted verbatim: 9037
turns of 38 AWG in a 186.9 mm2 window, 2.37 mA, 0.65 V direct off
one cell, 4.0 years per AA, W2 drawing rung) and the product
material choices the analyses landed on (fired-ferrite-ceramic
stator, pressed SrFe12O19 rotor, fired-ceramic pinion — mag-16's
fatigue answer). The as-built M0 stays the physics control case.

TWO SOURCING ROUTES, both first-class and both honest:
  pure-local  — every input made here: fired parts, pressed
                magnet, LOCALLY DRAWN + oleoresinous-insulated
                wire. Its gaps are the route: the W2 drawing
                capability, the insulation window cost, the
                SrFe12O19 demonstration.
  commercial  — local manufacture with BOUGHT critical inputs
                (magnet wire from the mag-1 cited spools, a bought
                sintered magnet). Fewer gaps, more dependence; the
                bought-movement irony is NAMED, not hidden.

BUSINESS SPLICE — the making and selling of the clock as bizops
ROWS in the native idiom: production workflows with flagged labor
priors, the product formula + input requirements the purchase
flows read, a timekeeping QA gate, and the sell-ITERATIVELY loop
(batch -> market session -> record -> adjust) that
MarketSessionRecord already models.

@consumers motors.motor_api (/api/motors/product-routes),
motors.clock_views_basis (cost view section), motors.motors_selftest,
polariServer seed pass (upsert, with ClockAssemblySeed)
"""

import json

from moduleService.seed_upsert import upsert_seed_pairs

PROV = 'mp0'
M0B = 'clock-lavet-m0b'

#: mag-25's 38 AWG W2 candidate, lifted verbatim (MMF 21.45 A-turns
#: = 9037 x 2.3735 mA — the numbers cross-check by construction).
M0B_WINDING = {'coil_turns': 9037, 'wire_awg': 38,
               'bobbin_window_mm2': 186.9,
               'mean_turn_length_mm': 14.0,
               'coil_amps': 0.0023735}

SEED_M0B_DESIGNS = [
    {'name': M0B,
     'display_name': 'M0b — the wall-clock PRODUCT '
                     '(solved winding)',
     'description': 'The M0 mechanism as a shippable product: the '
                    'mag-25 solved winding (38 AWG, 9037 turns, '
                    '0.65 V direct off one AA, ~4 years) and the '
                    'product materials the analyses landed on. '
                    'The as-built clock-lavet-m0 stays the '
                    'control case; this row is what you would '
                    'MAKE.',
     'topology': 'lavet-clock-stepper', 'ladder_rung': 'M0',
     'tolerance_tier': 'T0',
     'params_json': json.dumps({
         'rotor_material': 'opt-srfe12o19',
         'stator_material': 'opt-fired-ferrite-ceramic',
         'rotor_diameter_m': 0.006, 'rotor_thickness_m': 0.002,
         'gap_base_m': 0.0008, 'gap_asym_m': 0.0004,
         'overlap_area_m2': 1.2e-5,
         **M0B_WINDING,
         'magnet_length_m': 0.002}),
     'drive_json': json.dumps({
         'supply': 'one-alkaline-cell', 'supply_voltage_v': 1.5,
         'pulse_ms': 30, 'rate_hz': 1.0,
         'direct_drive': True}),
     'build_requirements_json': json.dumps({
         'wire_rung': 'W2',
         'named_experiment': 'press + sinter + magnetize the '
                             'SrFe12O19 rotor',
         'kiln': 'cone 8-10'}),
     'is_prior': True, 'provenance_id': PROV,
     'notes': 'Winding numbers are mag-25 output, not retuned '
              'here; a bench-measured coil supersedes them.'},
]

#: The product part rows: same v2 geometry, product materials.
#: (Shapes are the as-built drawings until M0b gets its own.)
_P = {'design_ref': M0B, 'shape_units': 'mm', 'quantity': 1,
      'is_prior': True, 'provenance_id': PROV, 'notes': ''}
SEED_M0B_PARTS = [
    {**_P, 'name': 'm0b-stator',
     'display_name': 'Stator (fired ferrite ceramic)',
     'shape_ref': 'motor-m0v2-stator',
     'material_ref': 'opt-fired-ferrite-ceramic',
     'function': 'flux-shaping',
     'purpose': 'The flux path, with the window and the left air '
                'gap that make the Lavet flip directional.',
     'why_this_material': 'Firing the casting is the fatigue '
                          'answer (mag-16): the cast geopolymer '
                          'stator FAILED the ten-year check at SF '
                          '~1.5; fired ferrite ceramic is the '
                          'process we own that passes.'},
    {**_P, 'name': 'm0b-rotor-magnet',
     'display_name': 'Rotor magnet (pressed SrFe12O19)',
     'shape_ref': 'motor-m0v2-rotor-magnet',
     'material_ref': 'opt-srfe12o19',
     'function': 'torque-magnet-active',
     'purpose': 'The diametric magnet the field flips.',
     'why_this_material': 'The mag-22 route: press + sinter the '
                          'recipe-seeded powder, magnetize AFTER '
                          'assembly. THE named experiment the '
                          'product rests on.'},
    {**_P, 'name': 'm0b-coil',
     'display_name': 'Coil (9037 turns, 38 AWG)',
     'shape_ref': 'motor-m0v2-coil',
     'material_ref': 'opt-copper-magnet-wire',
     'function': 'mmf-source',
     'purpose': 'The solved winding: 0.65 V direct off one cell.',
     'why_this_material': 'Copper is the conductor either route '
                          'winds; the ROUTES differ on where the '
                          'wire comes from, not what it is.'},
    {**_P, 'name': 'm0b-pinion',
     'display_name': 'Rotor pinion (fired ceramic, 8t)',
     'shape_ref': 'motor-m0v2-pinion-gear',
     'material_ref': 'opt-fired-ceramic',
     'function': 'torque-transmission',
     'purpose': 'The driving gear of the train.',
     'why_this_material': 'The colliding role wants hardness; '
                          'fired ceramic is the makeable answer '
                          '(SF ~3 vs the cast 0.39 — carried '
                          'against the 4.0 unmeasured-brittle '
                          'bar as a NAMED residual risk).'},
    {**_P, 'name': 'm0b-bobbin-flanges',
     'display_name': 'Bobbin flanges',
     'shape_ref': 'motor-m0v2-bobbin-flange-a',
     'material_ref': 'opt-plain-geopolymer', 'quantity': 2,
     'function': 'structure',
     'purpose': 'Holds the winding window.',
     'why_this_material': 'Unloaded structure — the cheap cast '
                          'is fine here.'},
    {**_P, 'name': 'm0b-leads',
     'display_name': 'Coil leads',
     'shape_ref': 'motor-m0v2-lead-a',
     'material_ref': 'opt-copper-magnet-wire', 'quantity': 2,
     'function': 'electrical',
     'purpose': 'Coil terminations to the drive.',
     'why_this_material': 'Same wire as the winding.'},
]

# -------------------------------------------------------------------
# bizops splice: workflows, purchase inputs, QA, the selling loop
# -------------------------------------------------------------------

SEED_CLOCK_WORKFLOWS = [
    {'name': 'clock-fire-parts-workflow',
     'display_name': 'Cast + fire the stator and pinion',
     'product_item_ref': 'm0-wall-clock',
     'mold_strategy': 'ceramic-fired',
     'hours_per_unit_ref': 1.5, 'hours_per_mold_ref': 0.0,
     'passive_hours_per_batch': 14.0,
     'volume_exponent': 0.667,
     'steps_json': json.dumps(
         ['mix + cast (wax mold)', 'dry', 'fire cone 8-10 '
          '(passive)', 'grind faces', 'qa-visual-crack']),
     'is_prior': True, 'provenance_id': PROV,
     'notes': 'HOUR PRIORS ARE ESTIMATES until timed runs replace '
              'them.'},
    {'name': 'clock-magnet-press-workflow',
     'display_name': 'Press, sinter, magnetize the rotor',
     'product_item_ref': 'm0-wall-clock',
     'mold_strategy': 'ceramic-fired',
     'hours_per_unit_ref': 1.0, 'hours_per_mold_ref': 0.0,
     'passive_hours_per_batch': 10.0,
     'volume_exponent': 0.667,
     'steps_json': json.dumps(
         ['press SrFe12O19 powder', 'sinter (passive)',
          'assemble to arbor', 'MAGNETIZE (after assembly)',
          'qa-magnet-remanence']),
     'is_prior': True, 'provenance_id': PROV,
     'notes': 'THE named experiment — the first timed run of this '
              'workflow is the product\'s biggest de-risk.'},
    {'name': 'clock-wire-draw-workflow',
     'display_name': 'Draw + insulate magnet wire (pure-local '
                     'route only)',
     'product_item_ref': 'm0-wall-clock',
     'mold_strategy': 'ceramic-fired',
     'hours_per_unit_ref': 4.0, 'hours_per_mold_ref': 0.0,
     'passive_hours_per_batch': 2.0,
     'volume_exponent': 0.667,
     'steps_json': json.dumps(
         ['draw to 38 AWG (W2, carbide dies, batch anneal)',
          'oleoresinous dip + 180 C oven cure',
          'continuity + build check']),
     'is_prior': True, 'provenance_id': PROV,
     'notes': 'The commercial route SKIPS this workflow and buys '
              'the spool instead — that is the whole difference '
              'between the routes.'},
    {'name': 'clock-wind-assemble-workflow',
     'display_name': 'Wind the coil + final assembly',
     'product_item_ref': 'm0-wall-clock',
     'mold_strategy': 'ceramic-fired',
     'hours_per_unit_ref': 3.0, 'hours_per_mold_ref': 0.0,
     'passive_hours_per_batch': 0.0,
     'volume_exponent': 0.667,
     'steps_json': json.dumps(
         ['wind 9037 turns (38 AWG)', 'qa-wound-core-inductance',
          'assemble train + hands', 'qa-timekeeping-24h']),
     'is_prior': True, 'provenance_id': PROV,
     'notes': 'The inductance QA doubles as the LCR measurement '
              'that adjudicates the mag-23 model disagreement.'},
    {'name': 'clock-sell-iterate-workflow',
     'display_name': 'Sell iteratively (batch -> market -> learn)',
     'product_item_ref': 'm0-wall-clock',
     'mold_strategy': 'ceramic-fired',
     'hours_per_unit_ref': 0.5, 'hours_per_mold_ref': 0.0,
     'passive_hours_per_batch': 0.0,
     'volume_exponent': 0.667,
     'steps_json': json.dumps(
         ['quote/price from deal-pricing (min margin gate)',
          'small batch build', 'market/online session',
          'record MarketSessionRecord (offered vs sold vs price)',
          'adjust next batch from sell-through',
          'compliance gate: req-magnet-ingestion, req-emc-claim']),
     'is_prior': True, 'provenance_id': PROV,
     'notes': 'The stage-0 FEEDBACK loop: speculative batches '
              'become informed ones through recorded sessions, '
              'never through optimism.'},
]

#: Purchase-flow data: what one clock consumes. Quantities are
#: flagged priors; the wire mass derives from the ws-1 winding
#: math (150 m of 38 AWG ~ 11 g copper) and says so.
SEED_CLOCK_FORMULA = [
    {'name': 'm0-wall-clock-formula',
     'display_name': 'M0 wall clock (complete movement + hands)',
     'product_item_ref': 'm0-wall-clock',
     'components_json': json.dumps([
         {'item_ref': 'magnet-wire-copper', 'role': 'winding',
          'fraction': 0.06,
          'note': '~0.011 kg from the winding math object (150 m '
                  'of 38 AWG); the pure-local route MAKES this '
                  'via clock-wire-draw-workflow'},
         {'item_ref': 'srfe12o19-powder', 'role': 'rotor-magnet',
          'fraction': 0.11,
          'note': '~0.02 kg pressed rotor + waste margin (prior)'},
         {'item_ref': 'geopolymer-mix', 'role': 'structure',
          'fraction': 0.83,
          'note': '~0.15 kg castings before firing (prior); wax '
                  'mold set + the shipped AA cell ride the '
                  'workflows, not the mass formula'}]),
     'yield_fraction': 0.8, 'status': 'candidate',
     'is_prior': True, 'provenance_id': PROV,
     'notes': 'The purchase flow reads THIS row: per route, each '
              'component resolves to make-locally (a workflow) or '
              'buy (a cited price), never silently. Yield 0.8 = '
              'firing losses, a flagged prior.'},
]

SEED_CLOCK_QA = [
    {'name': 'qa-timekeeping-24h',
     'display_name': '24 h timekeeping check',
     'product_kind': 'm0-wall-clock',
     'method': 'Run the assembled movement 24 h against a '
               'reference clock; record missed steps as a '
               'MotorVerificationRun (kind=measured).',
     'acceptance': 'clock error <= 2 s / 24 h '
                   '(86400 pulses, <= 2 missed)',
     'frequency': 'per-unit',
     'is_prior': True, 'provenance_id': PROV,
     'notes': 'A PASSING record is what earns made-and-measured '
              'for the whole assembly — the timekeeping-proof '
              'endpoint predicts it, this measures it.'},
]


def seed_product_routes(manager):
    """All product rows via the upsert path. bizops/supplychain
    classes are guarded — absent modules skip loudly."""
    from motors.motor_basis import MotorDesignDefinition
    from motors.motor_parts_basis import (
        MotorPartDefinition, SEED_MOTOR_PARTS,
    )
    pairs = [
        ('MotorDesignDefinition', MotorDesignDefinition,
         SEED_M0B_DESIGNS),
        # SEED_MOTOR_PARTS rides along so the as-built material
        # fixes (coil/leads/index resolvable) converge on live
        # rows through the same pass.
        ('MotorPartDefinition', MotorPartDefinition,
         SEED_M0B_PARTS + SEED_MOTOR_PARTS),
    ]
    try:
        from bizops.bizops_basis import ProcessWorkflowDefinition
        pairs.append(('ProcessWorkflowDefinition',
                      ProcessWorkflowDefinition,
                      SEED_CLOCK_WORKFLOWS))
    except ImportError:
        pass
    try:
        from bizops.bizops_basis import QualityCheckDefinition
        pairs.append(('QualityCheckDefinition',
                      QualityCheckDefinition, SEED_CLOCK_QA))
    except ImportError:
        pass
    try:
        from supplychain.sourcing_basis import ProductFormula
        pairs.append(('ProductFormula', ProductFormula,
                      SEED_CLOCK_FORMULA))
    except ImportError:
        pass
    return upsert_seed_pairs(manager, pairs, tag='ProductSeed')


# -------------------------------------------------------------------
# The two routes
# -------------------------------------------------------------------

def _wire_price(manager):
    """The cited spool price for the commercial wire input."""
    for row in (getattr(manager, 'objectTables', None) or {}).get(
            'PriceCitation', {}).values():
        name = getattr(row, 'name', '')
        if 'wire' in name or 'awg' in name:
            return {'citation': name,
                    'price': getattr(row, 'price_usd', None)
                    or getattr(row, 'unit_price_usd', None),
                    'note': getattr(row, 'notes', '')[:120]}
    return None


def product_routes(manager, design_name=M0B):
    """The complete product, twice: every critical input resolved
    as MAKE (naming its workflow + capability rung) or BUY (naming
    its citation), with the route's own gaps and blockers kept in
    the payload. Neither route is preferred by the code — the
    comparison IS the product decision.

    m1-6: the M1 design dispatches to its own product (the axis
    drive) — same contract, its own rows and fork."""
    if design_name == 'reluctance-6s4p-m1':
        from motors.m1_product_seed import m1_product_routes
        return m1_product_routes(manager, design_name)
    if design_name == 'ferrite-pm-m2':
        from motors.m2_product_seed import m2_product_routes
        return m2_product_routes(manager, design_name)
    from motors.custom.motor_winding import winding_report
    winding = winding_report(manager, design_name)
    wire_buy = _wire_price(manager)

    common_make = [
        {'input': 'stator + pinion + wheels', 'source': 'make',
         'workflow': 'clock-fire-parts-workflow',
         'capability': 'kiln, cone 8-10 (owned rung)'},
        {'input': 'rotor magnet', 'source': 'make',
         'workflow': 'clock-magnet-press-workflow',
         'capability': 'press + sinter + magnetize',
         'gap': 'THE named experiment — undemonstrated'},
        {'input': 'winding + assembly', 'source': 'make',
         'workflow': 'clock-wind-assemble-workflow',
         'capability': 'hand winding, 9037 turns'},
    ]
    local = {
        'route': 'pure-local',
        'policy': 'local-made-only',
        'inputs': common_make + [
            {'input': 'magnet wire (38 AWG)', 'source': 'make',
             'workflow': 'clock-wire-draw-workflow',
             'capability': 'W2 drawing (carbide dies) + '
                           'oleoresinous insulation',
             'gap': 'W2 drawing capability unproven here; '
                    'insulation build costs window (mag-24 '
                    'square law)'},
        ],
        'blockers': [
            'SrFe12O19 press-sinter-magnetize undemonstrated',
            'W2 wire drawing undemonstrated',
        ],
        'note': 'every input made here — the gaps ARE the route; '
                'each names the workflow that would close it',
    }
    commercial = {
        'route': 'commercial',
        'policy': 'any',
        'inputs': common_make + [
            {'input': 'magnet wire (38 AWG)', 'source': 'buy',
             **({'priceCitation': wire_buy} if wire_buy else
                {'gap': 'no PriceCitation row matches magnet '
                        'wire — cite a spool before quoting'})},
            {'input': 'rotor magnet (alternative)',
             'source': 'buy',
             'gap': 'no cited commercial magnet source yet — the '
                    'pressed rotor stays the plan of record '
                    'until one is cited'},
        ],
        'blockers': [
            'SrFe12O19 press-sinter-magnetize undemonstrated '
            '(unless the bought-magnet citation lands)',
        ],
        'irony': 'a bought quartz movement costs ~$2 and keeps '
                 'better time — this product is judged as a '
                 'LOCAL-CAPABILITY product, and says so rather '
                 'than pretending to beat the factory',
    }
    return {
        'ok': True, 'design': design_name,
        'winding': ({
            'fitVerdict': winding.get('fitVerdict'),
            'voltageNeededV': winding.get('voltageNeededV'),
            'supplyVoltageV': winding.get('supplyVoltageV'),
            'driveAchievable': winding.get('driveAchievable'),
            'note': 'mag-25 solved numbers; a measured coil '
                    'supersedes them'}
            if winding.get('ok') else
            {'gap': winding.get('refusal', 'winding refused')}),
        'routes': [local, commercial],
        'formula': 'm0-wall-clock',
        'sellLoop': 'clock-sell-iterate-workflow',
        'qaGate': 'qa-timekeeping-24h',
        'note': 'both routes end at the same QA gate and the same '
                'selling loop — they differ only in where the '
                'critical inputs come from',
    }
