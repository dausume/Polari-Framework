"""
@module motors.selftest_motors

Section-C selftests: the ladder shape (easiest buildable sample
first, builder specs as data), design-time role checks, THE M0
CLOCK CONTROL CASE (alternating pulses advance 180 deg/step; a
same-polarity repeat honestly fails to advance; a dead coil takes
zero steps and the clock error says so), torque curves (reluctance
positive-mean, saliency-1 rotor has no reluctance torque, PM term
takes over, dual gap doubles), and torque_parity hand math.

Run from polari-framework/: python3 -m motors.selftest_motors
"""

import json
import types

from magnetics.magnet_seed import (
    SEED_MAGNETIC_POWDERS, SEED_MATERIAL_OPTIONS, SEED_USE_ROLES,
)
from motors.motor_basis import SEED_MOTOR_DESIGNS
from motors.motor_designer import (
    clock_sim, design_report, torque_curve, torque_parity,
)
from motors.motor_materials import material_accountability
from motors.motor_drive import (
    SEED_CONTROLLER_PROFILES, SEED_PHASE_BINDINGS,
    simplefoc_config,
)
from motors.motor_shapes import (
    SEED_MOTOR_PART_SHAPES, SEED_MOTOR_SIM_SPACES,
)
from motors.motor_verify import (
    record_verification_run, verification_summary,
)
from supplychain.sourcing_seed import (
    SEED_PRICE_CITATIONS, SEED_PRODUCT_FORMULAS,
    SEED_PRODUCT_REQUIREMENTS, SEED_SOURCE_POLICIES,
    SEED_SUPPLY_SOURCES,
)

PASS = '\033[92mPASS\033[0m'
FAIL = '\033[91mFAIL\033[0m'
_results = []


def check(label, cond, extra=''):
    _results.append(bool(cond))
    print(f'{PASS if cond else FAIL}: {label}'
          + (f'  [{extra}]' if extra and not cond else ''))


def _mgr():
    m = types.SimpleNamespace()

    def table(seed):
        return {s['name']: types.SimpleNamespace(**s) for s in seed}
    m.objectTables = {
        'MaterialUseRole': table(SEED_USE_ROLES),
        'MagneticMaterialOption': table(SEED_MATERIAL_OPTIONS),
        'MagneticPowderDefinition': table(SEED_MAGNETIC_POWDERS),
        'MotorDesignDefinition': table(SEED_MOTOR_DESIGNS),
        'MotorControllerProfile': table(SEED_CONTROLLER_PROFILES),
        'PhaseBindingDefinition': table(SEED_PHASE_BINDINGS),
        'SupplySourceProfile': table(SEED_SUPPLY_SOURCES),
        'PriceCitation': table(SEED_PRICE_CITATIONS),
        'ProductInputRequirement': table(SEED_PRODUCT_REQUIREMENTS),
        'ProductFormula': table(SEED_PRODUCT_FORMULAS),
        'SourcePreferencePolicy': table(SEED_SOURCE_POLICIES),
    }
    return m


mgr = _mgr()

print('== suite: the ladder shape ==')
check('four rungs seeded M0..M3', len(SEED_MOTOR_DESIGNS) == 4
      and [d['ladder_rung'] for d in SEED_MOTOR_DESIGNS]
      == ['M0', 'M1', 'M2', 'M3'])
check('every rung carries a builder spec (tools/materials/skills/'
      'hours) — samples people can build, easiest first',
      all(set(json.loads(d['build_requirements_json']))
          >= {'tools', 'materials', 'skills', 'rough_hours'}
          for d in SEED_MOTOR_DESIGNS)
      and json.loads(SEED_MOTOR_DESIGNS[0]
                     ['build_requirements_json'])['rough_hours']
      < json.loads(SEED_MOTOR_DESIGNS[3]
                   ['build_requirements_json'])['rough_hours'])

print('== suite: design-time role checks ==')
out = design_report(mgr, 'clock-lavet-m0')
check('M0 report: bonded-hexaferrite rotor VIABLE as torque-magnet,'
      ' geopolymer-ferrite stator viable conductor, zero flags',
      out['ok'] and out['flags'] == []
      and all(s['verdict'] == 'viable'
              for s in out['materialSlots']))
check('realization travels: rotor literature-demonstrated -> '
      'business NOT allowed (made-and-measured pending)',
      any(s['material'] == 'opt-bonded-hexaferrite-geopolymer'
          and not s['businessAllowed']
          for s in out['materialSlots']))
design = mgr.objectTables['MotorDesignDefinition']['clock-lavet-m0']
saved = design.params_json
design.params_json = saved.replace(
    'opt-bonded-hexaferrite-geopolymer', 'opt-magnetite-powder')
out = design_report(mgr, 'clock-lavet-m0')
check('a MAGNETITE rotor flags at design time (soft — fails '
      'torque-magnet) with the pick-from-viable suggestion',
      any(f.get('role') == 'torque-magnet'
          and f['verdict'] == 'unviable' for f in out['flags']))
design.params_json = saved

print('== suite: M0 clock sim — THE control case ==')
out = clock_sim(mgr, 'clock-lavet-m0', pulses=10)
check('10 alternating pulses -> 10 steps, zero missed, zero clock '
      'error',
      out['ok'] and out['stepsTaken'] == 10
      and out['stepsMissed'] == 0
      and out['clockComparison']['clockErrorS'] == 0.0,
      extra=json.dumps(out.get('clockComparison', {})))
check('each step advances ~180 deg (the Lavet stride)',
      all(150.0 < h['advancedDeg'] < 210.0
          for h in out['history'][1:]))
check('clock comparison speaks the verification method (the clock '
      'IS the instrument)',
      'instrument' in out['clockComparison']['note'])
out = clock_sim(mgr, 'clock-lavet-m0', pulses=6,
                alternating=False)
check('SAME-polarity pulses honestly fail to advance (the Lavet '
      'mechanism needs alternation) — misses counted, clock error '
      'nonzero',
      out['ok'] and out['stepsTaken'] <= 1
      and out['clockComparison']['clockErrorS'] >= 5.0,
      extra=json.dumps({'taken': out['stepsTaken']}))
design.params_json = saved.replace('"coil_amps": 0.02',
                                   '"coil_amps": 0.0')
out = clock_sim(mgr, 'clock-lavet-m0', pulses=10)
check('a DEAD coil takes zero steps; clock error = the full 10 s',
      out['ok'] and out['stepsTaken'] == 0
      and out['clockComparison']['clockErrorS'] == 10.0)
design.params_json = saved
check('quasi-static validity stated (no dynamics, rate not '
      'predicted)', 'QUASI-STATIC' in out['validity'])
out = clock_sim(mgr, 'reluctance-6s4p-m1')
check('clock sim refuses non-M0 topologies (it is the M0 rung)',
      not out['ok'] and 'M0' in out['refusal'])

print('== suite: torque curves M1..M3 ==')
m1 = torque_curve(mgr, 'reluctance-6s4p-m1')
check('M1 reluctance: positive mean torque at synchronous '
      'excitation, ripple reported, honesty rider present',
      m1['ok'] and m1['meanTorqueNm'] > 0
      and m1['ripplePct'] is not None
      and 'SMALL' in m1['validity'],
      extra=str(m1.get('meanTorqueNm')))
m2 = torque_curve(mgr, 'ferrite-pm-m2')
check('M2: saliency 1.0 kills the reluctance term; the PM term '
      'carries the torque (hexaferrite rotor MMF on record)',
      m2['ok'] and m2['pmMmfAt'] > 0 and m2['meanTorqueNm'] > 0)
m3 = torque_curve(mgr, 'dual-stator-axial-m3')
check('M3 dual-stator flagged dualGap with PM MMF',
      m3['ok'] and m3['dualGap'] and m3['pmMmfAt'] > 0)
# dual-gap doubling: same design with dual_gap stripped -> half.
d3 = mgr.objectTables['MotorDesignDefinition']['dual-stator-axial-m3']
saved3 = d3.params_json
d3.params_json = saved3.replace('"dual_gap": true',
                                '"dual_gap": false')
m3_single = torque_curve(mgr, 'dual-stator-axial-m3')
d3.params_json = saved3
check('dual gaps DOUBLE the mean torque vs the identical '
      'single-gap machine (the §2d parity lever, computed)',
      abs(m3['meanTorqueNm'] / m3_single['meanTorqueNm'] - 2.0)
      < 0.05,
      extra=f"{m3['meanTorqueNm']} vs {m3_single['meanTorqueNm']}")

print('== suite: torque_parity (§2d hand math) ==')
out = torque_parity(mgr, 'opt-sintered-hexaferrite')
check('sintered hexaferrite (0.39 T) vs NdFeB (1.3 T) -> ~3.33x '
      'area multiplier',
      out['ok'] and abs(out['areaMultiplierForParity'] - 3.333)
      < 0.01)
out = torque_parity(mgr, 'opt-sintered-hexaferrite',
                    dual_gap=True)
check('dual gap credits a clean 2x (-> ~1.67x)',
      abs(out['withDualGap'] - 1.667) < 0.01)
check('watermarks of BOTH rows + assumptions printed',
      'realization' in out['cheap']['watermark']
      and 'realization' in out['reference']['watermark']
      and 'equal electrical loading' in out['assumptions'])
out = torque_parity(mgr, 'opt-plain-geopolymer')
check('a material with no B_r refuses parity (nothing invented)',
      not out['ok'] and 'b_r_t' in out['refusal'])

print('== suite: material accountability (follow the derivation) ==')
out = material_accountability(mgr, 'clock-lavet-m0')
by_slot = {s['slot']: s for s in out['slots']}
check('M0 trail covers rotor + stator + WINDING (the wire is a '
      'real material)',
      out['ok'] and set(by_slot) == {'rotor_material',
                                     'stator_material',
                                     'winding_material'})
check('every property value carries its provenance tag',
      all(p['provenance'] for s in out['slots']
          for p in s.get('properties', [])))
stator = by_slot['stator_material']
check('stator mu follows to the msci FEM homogenization BY '
      'REFERENCE (geopolymer-ferrite-permeability model named)',
      stator['msci']['msciMaterialRef'] == 'geopolymer-ferrite')
check('stator supply trail: recipe + cascade with self-made '
      'intermediates named and the energy exclusion stated',
      any(r['name'] == 'magnetic-geopolymer-35vol-v0'
          for r in stator['supply']['recipes'])
      and 'EXCLUDED-LOUD' in stator['supply']['cascade']['note'])
winding = by_slot['winding_material']
check('winding follows to DATED magnet-wire citations with URLs',
      winding['supply']['citations']
      and all(c['url'] and c['observedAt']
              for c in winding['supply']['citations']))
rotor = by_slot['rotor_material']
check('rotor (derived composite, no own listing): honest note + '
      'the FILLER powder trail follows to the srfe12o19 recipes',
      rotor['supply']['itemRef'] is None
      and 'fillerSupply' in rotor
      and any(r['name'] == 'srfe12o19-solidstate-v0'
              for r in rotor['fillerSupply']['recipes']))
check('rotor realization travels (literature-demonstrated, '
      'business gated)', rotor['realizationLevel']
      == 'literature-demonstrated'
      and not rotor['businessAllowed'])
check('the trail note states the whole chain + absence honesty',
      'never' in out['trailNote'] and 'provenance' in
      out['trailNote'])

print('== suite: mag-6 drive (SimpleFOC as data) ==')
out = simplefoc_config(mgr, 'reluctance-6s4p-m1')
check('M1 config generates: pole pairs from the DESIGN row, '
      'limits from the profile, snippet says edit-the-rows',
      out['ok'] and out['polePairs'] == 2
      and 'BLDCMotor motor = BLDCMotor(2);' in out['configSnippet']
      and 'motor.current_limit = 1.0' in out['configSnippet']
      and 'edit the ROWS' in out['configSnippet'])
check('M1 phase bindings A/B/C on shield terminals; FPGA channel '
      'honestly named-not-wired',
      [b['phase'] for b in out['phaseBindings']] == ['A', 'B', 'C']
      and all('escalation' in b['fpgaPwmChannel']
              for b in out['phaseBindings']))
check('hardware honesty rider present (config-generation only)',
      'no hardware is acted on' in out['honesty'])
out = simplefoc_config(mgr, 'clock-lavet-m0')
check('M0 REFUSES FOC — a Lavet stepper wants a plain alternating '
      'pulse, and the refusal says so',
      not out['ok'] and '1 Hz alternating pulse' in out['refusal'])
out = simplefoc_config(mgr, 'dual-stator-axial-m3',
                       profile_name='mks-clone-default')
check('M3 with the named clone profile: 4 pole pairs, parallel '
      'note on bindings',
      out['ok'] and out['polePairs'] == 4
      and out['board'] == 'mks-dual-foc-clone')

print('== suite: verification-run recording seam (mag-7) ==')
# fixture typing dict: the create method inserts a SimpleNamespace
# row, same shape the odoo selftests fake _class_for with.
def _fake_typing(class_name):
    def create(manager=None, **kw):
        row = types.SimpleNamespace(**kw)
        manager.objectTables.setdefault(class_name, {})[
            kw.get('name', '')] = row
        return row
    return types.SimpleNamespace(getCreateMethod=lambda: create)


mgr.objectTables['MotorVerificationRun'] = {}
mgr.objectTypingDict = {
    'MotorVerificationRun': _fake_typing('MotorVerificationRun')}
out = record_verification_run(mgr, 'clock-lavet-m0',
                              'sim-quasi-static', 60, 60)
check('sim run records: duration DERIVED from commanded/rate '
      '(60 pulses @ 1 Hz = 60 s), zero clock error, honesty says '
      'sim is provenance not proof',
      out['ok'] and out['run']['durationS'] == 60.0
      and out['run']['clockErrorS'] == 0.0
      and 'not proof' in out['honesty'])
out = verification_summary(mgr, 'clock-lavet-m0')
check('summary: 1 sim run, made-and-measured still NOT earned',
      out['ok'] and out['simCount'] == 1
      and out['measuredCount'] == 0
      and out['madeAndMeasured'] is False
      and 'no measured run yet' in out['honesty'])
rep = design_report(mgr, 'clock-lavet-m0')
check('design report carries the verification block (earned state '
      'visible at design time)',
      rep['verification']['simCount'] == 1
      and rep['verification']['madeAndMeasured'] is False)
out = record_verification_run(mgr, 'clock-lavet-m0', 'measured',
                              3600, 3597, duration_s=3600.0,
                              notes='bench clock, 1 h soak')
check('measured run: clock error DERIVES from missed steps / rate '
      '(3 missed @ 1 Hz = 3 s)',
      out['ok'] and out['run']['clockErrorS'] == 3.0
      and out['run']['missedSteps'] == 3)
out = verification_summary(mgr, 'clock-lavet-m0')
check('made-and-measured EARNED by the measured row; honesty '
      'points at the clock error, not just the flag',
      out['madeAndMeasured'] is True and out['measuredCount'] == 1
      and 'clock error' in out['honesty'])
check('run names allocate per design (run-1, run-2)',
      [r['name'] for r in out['runs']]
      == ['clock-lavet-m0-run-1', 'clock-lavet-m0-run-2'])
out = record_verification_run(mgr, 'clock-lavet-m0', 'measured',
                              10, 12)
check('more steps than commanded REFUSES (a motor cannot '
      'over-step its command)',
      not out['ok'] and 'cannot take more steps' in out['refusal'])
out = record_verification_run(mgr, 'clock-lavet-m0', 'bench-guess',
                              10, 10)
check('unknown kind refuses, naming the valid kinds',
      not out['ok'] and 'sim-quasi-static' in out['refusal'])
out = record_verification_run(mgr, 'no-such-motor', 'measured',
                              10, 10)
check('unknown design refuses', not out['ok'])

print('== suite: motor scene row + capped meshes (mag-7) ==')
check('motor-m0-viz scene row seeded: freestandingOnly, six parts, '
      'coil entry references the CSG RING (not the solid outer)',
      len(SEED_MOTOR_SIM_SPACES) == 1
      and json.loads(SEED_MOTOR_SIM_SPACES[0]['definition'])
      .get('freestandingOnly') is True
      and [e['id'] for e in json.loads(
          SEED_MOTOR_SIM_SPACES[0]['definition'])['freestanding']]
      == ['pole-left', 'pole-right', 'coil', 'shaft', 'rotor-disc',
          'rotor-pointer']
      and any(e['shapeRef'] == 'mathshape:motor-m0-coil-ring'
              for e in json.loads(
                  SEED_MOTOR_SIM_SPACES[0]['definition'])
              ['freestanding']))
_shape_params = {s['name']: json.loads(s.get('parameters_json',
                                             '{}'))
                 for s in SEED_MOTOR_PART_SHAPES}
check('solid cylinders (rotor disc, shaft, coil outer) request end '
      'caps — a disc must not read as an open band',
      all(_shape_params[n].get('cap_base')
          and _shape_params[n].get('cap_top')
          for n in ('motor-m0-rotor-disc', 'motor-m0-shaft',
                    'motor-m0-coil-outer')))

print('== suite: mag-9 WINDING REALITY (the asserted amps) ==')
import math as _math  # noqa: E402
from motors.motor_winding import (  # noqa: E402
    AWG_DIAMETER_MM, RHO_CU_20C, gauge_sweep, winding_report,
)

mgrw = _mgr()
mgrw.objectTables['PriceCitation'] = {
    c['name']: types.SimpleNamespace(**c) for c in SEED_PRICE_CITATIONS}

_a30 = _math.pi * (AWG_DIAMETER_MM[30] / 2000.0) ** 2
check('resistance DERIVES from copper resistivity and reproduces '
      'the published 30 AWG value (0.3386 ohm/m) — the check that '
      'the constant is the right one',
      abs(RHO_CU_20C / _a30 - 0.3386) < 5e-4,
      extra=str(RHO_CU_20C / _a30))

out = winding_report(mgrw, 'clock-lavet-m0')
check('M0 winding: 1500 turns of 44 AWG on the stated 12 mm2 '
      'bobbin fills 0.56 — hand-windable',
      out['ok'] and abs(out['fillFactor'] - 0.5567) < 1e-3
      and out['fitVerdict'] == 'hand-windable',
      extra=str(out.get('fillFactor')))
check('M0 needs ~3.64 V to push 20 mA through ~182 ohm, and the '
      'seeded 12 V supply carries it',
      abs(out['resistanceOhm'] - 182.19) < 0.5
      and abs(out['voltageNeededV'] - 3.644) < 0.01
      and out['driveAchievable'] is True,
      extra=f"{out['resistanceOhm']} / {out['voltageNeededV']}")
check('the winding costs real money from the mag-1 CITED spool',
      bool(out['cost']) and out['cost']['wireCostUsd'] > 0
      and bool(out['cost']['citation']))
check('temperature is applied EXPLICITLY: the same coil at 100 C '
      'carries ~1.31x the resistance',
      abs(winding_report(mgrw, 'clock-lavet-m0',
                         temp_c=100.0)['resistanceOhm']
          / out['resistanceOhm'] - 1.3144) < 1e-3)
check('no temperature is PREDICTED — watts and watts/cm2 only, '
      'because no thermal model of a cast composite exists',
      'never a predicted temperature' in out['validity']
      and out['powerDissipatedW'] > 0)
check('back-EMF named as NOT modelled (a spinning machine needs '
      'more voltage than this)', 'back-EMF' in out['validity'])

for _d in ('reluctance-6s4p-m1', 'ferrite-pm-m2',
           'dual-stator-axial-m3'):
    _r = winding_report(mgrw, _d)
    check(f'{_d} is buildable as specified (fill '
          f'{_r["fillFactor"]}, {_r["voltageNeededV"]} V)',
          _r['ok'] and _r['buildable'] and _r['judgeable'],
          extra=str(_r.get('fitNote')))

out = winding_report(mgrw, 'clock-lavet-m0', awg=20)
check('20 AWG in the clock bobbin is IMPOSSIBLE — and because the '
      'bobbin is STATED, it may condemn the number it invalidates '
      'BY NAME',
      out['fitVerdict'] == 'IMPOSSIBLE' and not out['buildable']
      and any('clock-sim' in i for i in out['invalidates']),
      extra=str(out.get('fitVerdict')))

_saved = mgrw.objectTables['MotorDesignDefinition'][
    'clock-lavet-m0'].params_json
mgrw.objectTables['MotorDesignDefinition']['clock-lavet-m0'] \
    .params_json = _saved.replace('"bobbin_window_mm2": 12.0, ', '')
out = winding_report(mgrw, 'clock-lavet-m0', awg=20)
check('with the bobbin UNSTATED the verdict is window-unknown and '
      'invalidates NOTHING — our own crude assumption is not '
      'allowed to condemn somebody\'s design',
      out['fitVerdict'] == 'window-unknown'
      and out['invalidates'] == [] and out['judgeable'] is False
      and any('bobbin' in a for a in out['assumptions']),
      extra=str(out.get('fitVerdict')))
mgrw.objectTables['MotorDesignDefinition']['clock-lavet-m0'] \
    .params_json = _saved

out = winding_report(mgrw, 'reluctance-6s4p-m1',
                     supply_voltage_v=0.1)
check('a supply that cannot push the current says so, names the '
      'shortfall, and invalidates the torque curve BY NAME',
      out['driveAchievable'] is False
      and 'SHORT by' in out['driveNote']
      and any('torque curve' in i for i in out['invalidates']))

out = gauge_sweep(mgrw, 'reluctance-6s4p-m1')
check('the gauge sweep is a TABLE across every gauge with a '
      'recommendation, not an opinion',
      out['ok'] and len(out['gauges']) == len(AWG_DIAMETER_MM)
      and bool(out['recommended']) and 'SUGGESTION' in out['note'])
check('finer wire needs MORE voltage — the trade is visible in '
      'the table',
      next(g for g in out['gauges'] if g['awg'] == 34)
      ['voltageNeededV']
      > next(g for g in out['gauges'] if g['awg'] == 22)
      ['voltageNeededV'])
check('unknown gauge refuses with the valid list',
      not winding_report(mgrw, 'clock-lavet-m0',
                         awg=99).get('ok'))

print('== suite: mag-10 the REALISTIC Lavet geometry ==')
from motors.motor_shapes import (  # noqa: E402
    SEED_LAVET_PART_SHAPES, SEED_LAVET_SIM_SPACES,
)

_lavet = {p['name']: p for p in SEED_LAVET_PART_SHAPES}
check('the realistic set exists ALONGSIDE the schematic one — '
      'both kept, and the module says which is which',
      len(SEED_LAVET_PART_SHAPES) == 12
      and len(SEED_MOTOR_PART_SHAPES) == 8)
check('ONE bored stator plate (CSG box minus bore), not two '
      'floating pole shoes — the correction Dustin spotted from '
      'photographs',
      _lavet['motor-m0r-stator']['family'] == 'csg'
      and 'difference' in _lavet['motor-m0r-stator']['csg_json'])
check('the rotor is a 2 mm DIAMETRIC cylinder, not a disc with a '
      'pointer',
      json.loads(_lavet['motor-m0r-rotor']['parameters_json'])
      ['radius'] == 1.0
      and 'diameter' in _lavet['motor-m0r-rotor']['notes'])
check('the coil is a coaxial-cylinder difference, so it gets the '
      'EXACT tube mesh, and its bobbin is the SAME 12 mm2 the '
      'mag-9 winding check judges',
      _lavet['motor-m0r-coil']['family'] == 'csg'
      and '12 mm2' in _lavet['motor-m0r-coil']['notes'])
_pin = json.loads(_lavet['motor-m0r-pinion']['parameters_json'])
_wheel = json.loads(
    _lavet['motor-m0r-seconds-wheel']['parameters_json'])
check('pinion and seconds wheel are at TRUE relative size: 8t and '
      '240t at module 0.3 => 1.2 mm and 36 mm pitch radii (30:1, '
      'the clock-train-m0 first stage)',
      abs(_pin['radius'] - 1.2) < 1e-9
      and abs(_wheel['radius'] - 36.0) < 1e-9
      and abs(_wheel['radius'] / _pin['radius'] - 30.0) < 1e-9)
check('and they sit at the correct CENTRE DISTANCE (r1 + r2 = '
      '37.2 mm) — the same sum the gear solver derives',
      abs(_wheel['center'][0] - (_pin['radius']
                                 + _wheel['radius'])) < 1e-9,
      extra=str(_wheel['center'][0]))
check('teeth are NOT faked on the pinion — gear geometry is '
      'generated (gr-3), and drawing fake teeth would be the exact '
      '"close enough gear" mistake the mesh catalog refuses',
      'teeth not rendered' in _lavet['motor-m0r-pinion']['notes'])
check('the realistic scene row exists, freestandingOnly, with all '
      '8 bodies including the wheel it drives',
      len(SEED_LAVET_SIM_SPACES) == 1
      and json.loads(SEED_LAVET_SIM_SPACES[0]['definition'])
      ['freestandingOnly'] is True
      and len(json.loads(SEED_LAVET_SIM_SPACES[0]['definition'])
              ['freestanding']) == 8)

print('== suite: mag-10b Lavet v2 (from the reference photos) ==')
from motors.motor_shapes import (  # noqa: E402
    SEED_LAVET_V2_PART_SHAPES, SEED_LAVET_V2_SIM_SPACES,
)

_v2 = {p['name']: p for p in SEED_LAVET_V2_PART_SHAPES}
check('the stator is a squared-C: plate MINUS window MINUS bore '
      '(n-ary CSG difference), not a slab with a hole',
      _v2['motor-m0v2-stator']['family'] == 'csg'
      and len(json.loads(
          _v2['motor-m0v2-stator']['csg_json'])['shapes']) == 3)
_bore = json.loads(_v2['motor-m0v2-plate-bore']['parameters_json'])
_plate = json.loads(
    _v2['motor-m0v2-plate-blank']['parameters_json'])
check('the rotor bore is at ONE END of the plate, as in the '
      'reference — not centred',
      abs(_bore['center'][0]) > _plate['size'][0] * 0.3,
      extra=str(_bore['center'][0]))
_coil = json.loads(_v2['motor-m0v2-coil-outer']['parameters_json'])
check('the coil is a BIG flanged bobbin — half the plate length, '
      'the reference\'s most obvious correction to v1',
      _coil['height'] / _plate['size'][0] > 0.45
      and _coil['height'] > json.loads(
          _v2['motor-m0v2-coil-bore']['parameters_json'])['height']
      - 1.0,
      extra=f"coil {_coil['height']} vs plate {_plate['size'][0]}")
check('the bobbin has TWO flanges and TWO lead wires',
      all(n in _v2 for n in ('motor-m0v2-bobbin-flange-a',
                             'motor-m0v2-bobbin-flange-b',
                             'motor-m0v2-lead-a',
                             'motor-m0v2-lead-b')))
_mag = json.loads(_v2['motor-m0v2-rotor-magnet']['parameters_json'])
_pin = json.loads(_v2['motor-m0v2-rotor-pinion']['parameters_json'])
check('the rotor is STEPPED: magnet below, pinion above, sharing '
      'one axis',
      _pin['center'][2] > _mag['center'][2]
      and _pin['center'][0] == _mag['center'][0]
      and _pin['radius'] < _mag['radius'])
check('the rotor sits IN the bore (same axis, and it fits)',
      _mag['center'][0] == _bore['center'][0]
      and _mag['radius'] < _bore['radius'])
check('teeth are STILL not faked — the pitch cylinder says it is '
      'a pitch cylinder, and gr-3 generates the real ones',
      'PITCH cylinder only'
      in _v2['motor-m0v2-rotor-pinion']['notes'])
check('the v2 scene exists alongside v1 and the schematic — three '
      'geometries, each labelled for what it is',
      len(SEED_LAVET_V2_SIM_SPACES) == 1
      and len(json.loads(SEED_LAVET_V2_SIM_SPACES[0]['definition'])
              ['freestanding']) == 9)

print('== suite: mag-11 the per-part bill ==')
from motors.motor_parts import SEED_MOTOR_PARTS, part_report  # noqa
from motors.motor_shapes import SEED_LAVET_V2_PART_SHAPES as _V2S

mgrp = _mgr()
mgrp.objectTables['MotorPartDefinition'] = {
    p['name']: types.SimpleNamespace(**p) for p in SEED_MOTOR_PARTS}
mgrp.objectTables['MathShapeDefinition'] = {
    p['name']: types.SimpleNamespace(**p) for p in _V2S}
rep = part_report(mgrp, 'clock-lavet-m0')
_by = {p['part']: p for p in rep['parts']}
check('every piece carries a PURPOSE — what it is for in the '
      'clock, not just what it is',
      rep['ok'] and all(p['purpose'] for p in rep['parts']))
check('and a functional role, so two same-shaped parts with '
      'different jobs stay distinguishable',
      {'torque-producing', 'mmf-source', 'flux-shaping',
       'power-transmission'} <= set(rep['byFunction']))
check('volumes DERIVE from each part\'s own shape row — the bill '
      'and the 3D view cannot disagree',
      all(p['volumeCm3'] is not None for p in rep['parts']))
check('UNITS are explicit: the v2 geometry is authored in mm, and '
      'reading it as cm silently made a 1.1 kg clock motor — the '
      'whole motor is ~1.15 g',
      all(p['shapeUnits'] == 'mm' for p in rep['parts'])
      and 1.0 < rep['totalMassG'] < 1.5,
      extra=str(rep['totalMassG']))
check('mass = volume x the material row\'s density: the rotor '
      'magnet is ~0.106 g of bonded hexaferrite',
      abs(_by['lavet-v2-rotor-magnet']['massG'] - 0.1064) < 1e-3,
      extra=str(_by['lavet-v2-rotor-magnet']['massG']))
check('each part says WHY that material — the deciding property, '
      'not a description',
      'HARD magnetic'
      in _by['lavet-v2-rotor-magnet']['whyThisMaterial']
      and 'Non-magnetic ON PURPOSE'
      in _by['lavet-v2-pinion']['whyThisMaterial'])
check('material PROPERTIES resolve with their provenance tags',
      _by['lavet-v2-stator']['properties']
      and all(pr['provenance']
              for pr in _by['lavet-v2-stator']['properties']))
check('the viz-only index mark is listed but EXCLUDED from mass — '
      'a scribe is not a piece',
      _by['lavet-v2-index']['function'] == 'viz-only'
      and 'viz-only parts are excluded' in rep['massNote'])
check('parts whose material is a supplychain item (copper wire) '
      'report an honest GAP instead of a fake density',
      _by['lavet-v2-coil'].get('materialGap')
      and _by['lavet-v2-coil']['massG'] is None
      and any('lavet-v2-coil' in g for g in rep['gaps']))
check('a design with no part rows refuses and names the knob',
      not part_report(_mgr(), 'clock-lavet-m0').get('ok'))

print('== suite: mag-12 M1 + M3 geometry and parts ==')
import math as _m12  # noqa: E402
from motors.motor_shapes import (  # noqa: E402
    SEED_M1_PART_SHAPES, SEED_M1_SIM_SPACES,
    SEED_M3_PART_SHAPES, SEED_M3_SIM_SPACES,
)

_m1 = {p['name']: p for p in SEED_M1_PART_SHAPES}
_m3 = {p['name']: p for p in SEED_M3_PART_SHAPES}
_m1scene = json.loads(SEED_M1_SIM_SPACES[0]['definition'])
_m3scene = json.loads(SEED_M3_SIM_SPACES[0]['definition'])

# --- M1: the numbers come from the design's own params_json ---
_m1params = json.loads(
    mgr.objectTables['MotorDesignDefinition'][
        'reluctance-6s4p-m1'].params_json)
_tooth = json.loads(_m1['motor-m1-stator-tooth']['parameters_json'])
check('M1 tooth FACE matches the design\'s tooth_area_m2 (6.0 x '
      '6.7 mm = 40.2 mm2 vs the stated 4e-5 m2)',
      abs(_tooth['size'][1] * _tooth['size'][2]
          - _m1params['tooth_area_m2'] * 1e6) < 1.0,
      extra=str(_tooth['size'][1] * _tooth['size'][2]))
_pole = json.loads(_m1['motor-m1-rotor-pole']['parameters_json'])
_pole_tip = _pole['center'][0] + _pole['size'][0] / 2.0
_tooth_face = _tooth['center'][0] - _tooth['size'][0] / 2.0
check('M1 AIR GAP is the design\'s gap_base_m: tooth face at 12.6 '
      'mm minus pole tip at 12.0 mm = 0.6 mm',
      abs((_tooth_face - _pole_tip)
          - _m1params['gap_base_m'] * 1000.0) < 1e-6,
      extra=f'{_tooth_face} - {_pole_tip}')
check('M1 arrays by SCENE ROTATION, not by 14 near-identical shape '
      'rows: ONE tooth row placed 6 times, ONE pole row placed 4',
      sum(1 for b in _m1scene['freestanding']
          if b['shapeRef'].endswith('m1-stator-tooth')) == 6
      and sum(1 for b in _m1scene['freestanding']
              if b['shapeRef'].endswith('m1-rotor-pole')) == 4)
check('the 6 teeth are 60 deg apart and the 4 poles 90 deg — the '
      'slot/pole counts the design states',
      sorted(round(_m12.degrees(b['rotation'][2]))
             for b in _m1scene['freestanding']
             if b['shapeRef'].endswith('m1-stator-tooth'))
      == [0, 60, 120, 180, 240, 300]
      and sorted(round(_m12.degrees(b['rotation'][2]))
                 for b in _m1scene['freestanding']
                 if b['shapeRef'].endswith('m1-rotor-pole'))
      == [0, 90, 180, 270])
check('M1 yoke is a coaxial-cylinder difference, so it renders '
      'through the EXACT tube mesh rather than the blocky voxel '
      'fallback',
      _m1['motor-m1-yoke']['family'] == 'csg'
      and json.loads(_m1['motor-m1-yoke']['csg_json'])['op']
      == 'difference')
_cbore = json.loads(_m1['motor-m1-coil-bore']['parameters_json'])
check('M1 coil bore CLEARS its tooth (bore 5.0 mm vs the tooth\'s '
      '4.5 mm half-diagonal) — the coil actually fits',
      _cbore['radius']
      > _m12.hypot(_tooth['size'][1], _tooth['size'][2]) / 2.0,
      extra=str(_m12.hypot(_tooth['size'][1], _tooth['size'][2]) / 2))
check('six coils are placed, wired A-B-C-A-B-C = three phases of '
      'two',
      sum(1 for b in _m1scene['freestanding']
          if b['shapeRef'].endswith('m1-coil')) == 6)

# --- M3: the dual gap IS the rung ---
_m3params = json.loads(
    mgr.objectTables['MotorDesignDefinition'][
        'dual-stator-axial-m3'].params_json)
_ta = json.loads(_m3['motor-m3-stator-a-tooth']['parameters_json'])
_tb = json.loads(_m3['motor-m3-stator-b-tooth']['parameters_json'])
_rot = json.loads(_m3['motor-m3-rotor-disk']['parameters_json'])
check('M3 tooth face matches tooth_area_m2 (23 x 11 = 253 mm2 vs '
      'the stated 2.5e-4 m2)',
      abs(_ta['size'][0] * _ta['size'][1]
          - _m3params['tooth_area_m2'] * 1e6) < 5.0,
      extra=str(_ta['size'][0] * _ta['size'][1]))
_gap_a = ((_ta['center'][2] - _ta['size'][2] / 2.0)
          - _rot['height'] / 2.0)
_gap_b = ((-_rot['height'] / 2.0)
          - (_tb['center'][2] + _tb['size'][2] / 2.0))
check('M3 has TWO working gaps, each the design\'s gap_base_m '
      '(0.8 mm) — the doubled area that IS the SS2d thesis',
      abs(_gap_a - _m3params['gap_base_m'] * 1000.0) < 1e-6
      and abs(_gap_b - _m3params['gap_base_m'] * 1000.0) < 1e-6,
      extra=f'{_gap_a} / {_gap_b}')
check('and the two stators are SYMMETRIC about the rotor — an '
      'asymmetric pair would pull the rotor into one gap',
      abs(_ta['center'][2] + _tb['center'][2]) < 1e-9)
check('M3 arrays 12 teeth per stator at 30 deg and 8 rotor poles '
      'at 45 deg, matching teeth_per_stator and poles',
      sum(1 for b in _m3scene['freestanding']
          if b['shapeRef'].endswith('m3-stator-a-tooth'))
      == _m3params['teeth_per_stator']
      and sum(1 for b in _m3scene['freestanding']
              if b['shapeRef'].endswith('m3-stator-b-tooth'))
      == _m3params['teeth_per_stator']
      and sum(1 for b in _m3scene['freestanding']
              if b['shapeRef'].endswith('m3-rotor-pole'))
      == _m3params['poles'])
check('M3 rotor thickness is the design\'s magnet_length_m (6 mm)',
      abs(_rot['height'] - _m3params['magnet_length_m'] * 1000.0)
      < 1e-9)
check('M3 draws NO coils, and the scene SAYS WHY — a round tube is '
      'the wrong primitive for a trapezoidal axial-flux coil, and '
      'drawing the wrong shape is worse than drawing none',
      not any('coil' in b['shapeRef']
              for b in _m3scene['freestanding'])
      and 'trapezoidal' in SEED_M3_SIM_SPACES[0]['description'])

# --- part rows for both rungs ---
mgr12 = _mgr()
mgr12.objectTables['MotorPartDefinition'] = {
    p['name']: types.SimpleNamespace(**p) for p in SEED_MOTOR_PARTS}
mgr12.objectTables['MathShapeDefinition'] = {
    p['name']: types.SimpleNamespace(**p)
    for p in (SEED_M1_PART_SHAPES + SEED_M3_PART_SHAPES)}
for _design, _expect in (('reluctance-6s4p-m1', 6),
                         ('dual-stator-axial-m3', 7)):
    _rep = part_report(mgr12, _design)
    check(f'{_design}: {_expect} part rows, every one with a '
          f'purpose and mm units declared',
          _rep['ok'] and _rep['count'] == _expect
          and all(p['purpose'] and p['shapeUnits'] == 'mm'
                  for p in _rep['parts']),
          extra=str(_rep.get('count') or _rep.get('refusal')))
    check(f'{_design}: volumes derive from the shape rows, so the '
          f'bill and the 3D view cannot disagree',
          all(p['volumeCm3'] is not None for p in _rep['parts']))
_m1rep = {p['part']: p for p in
          part_report(mgr12, 'reluctance-6s4p-m1')['parts']}
check('M1 rotor poles are the TORQUE-PRODUCING part and the row '
      'says the mechanism needs no magnet at all',
      _m1rep['m1-rotor-poles']['function'] == 'torque-producing'
      and 'no magnet' in _m1rep['m1-rotor-poles']['purpose'])
check('M1 rotor wants SOFT magnetic material — the opposite of the '
      'M0 rotor, and the row explains why',
      'SOFT magnetic'
      in _m1rep['m1-rotor-poles']['whyThisMaterial'])
_m3rep = {p['part']: p for p in
          part_report(mgr12, 'dual-stator-axial-m3')['parts']}
check('M3 rotor carrier is non-magnetic ON PURPOSE (a ferrous one '
      'would short the magnets through the disk)',
      'Non-magnetic ON PURPOSE'
      in _m3rep['m3-rotor-disk']['whyThisMaterial'])
check('both rungs\' shafts are BOUGHT steel, reported as an '
      'honest gap rather than a faked density',
      _m1rep['m1-shaft']['massG'] is None
      and _m3rep['m3-shaft']['massG'] is None)

print('== suite: mag-15 stress — the CRITERION correction ==')
from motors.motor_stress import (  # noqa: E402
    failure_criterion, load_cases,
)
from gears.gear_seed import (  # noqa: E402
    SEED_GEARS as _GRS, SEED_GEAR_TRAINS as _GTR,
)

mgrs = _mgr()
mgrs.objectTables['GearTrainDefinition'] = {
    g['name']: types.SimpleNamespace(**g) for g in _GTR}
mgrs.objectTables['GearDefinition'] = {
    g['name']: types.SimpleNamespace(**g) for g in _GRS}
mgrs.objectTables['MotorPartDefinition'] = {}

fc = failure_criterion(mgrs, 'opt-geopolymer-ferrite')
check('a BRITTLE casting is judged by MAX PRINCIPAL stress, NOT '
      'von Mises — asking for von Mises and getting it here would '
      'be answering the question and getting the engineering wrong',
      fc['ok'] and fc['failureClass'] == 'brittle'
      and 'max-principal' in fc['criterion'])
check('and the reason is quantified: ~14x stronger in compression '
      'than tension, which is exactly the asymmetry von Mises is '
      'blind to',
      abs(fc['asymmetryRatio'] - 14.3) < 0.2
      and 'blind to hydrostatic' in fc['why'],
      extra=str(fc['asymmetryRatio']))
fc_cu = failure_criterion(mgrs, 'opt-copper-magnet-wire')
check('a DUCTILE metal IS judged by von Mises — the criterion '
      'matches the failure mode, and the asymmetry is 1.0x',
      fc_cu['failureClass'] == 'ductile'
      and 'von-Mises' in fc_cu['criterion']
      and abs(fc_cu['asymmetryRatio'] - 1.0) < 1e-9)
check('a material with no failure_class REFUSES rather than '
      'silently picking a criterion',
      not failure_criterion(mgrs, 'opt-magnetite-powder').get('ok')
      or failure_criterion(mgrs, 'opt-magnetite-powder')
      .get('failureClass') is not None)

lc = load_cases(mgrs, 'clock-lavet-m0')
check('loads DERIVE from the machine: tooth load F = T/r_pitch off '
      'the gear train it drives',
      lc['ok'] and any(c['case'] == 'tooth-load'
                       and abs(c['forceN'] - 8.333e-4) < 1e-6
                       for c in lc['cases']),
      extra=str([c.get('forceN') for c in lc['cases']]))
check('magnetic pull uses Maxwell stress B^2A/(2mu0) and says it '
      'is deliberately conservative (B taken as remanence)',
      any(c['case'] == 'magnetic-pull'
          and 'OVERSTATES' in c['note'] for c in lc['cases']))
check('THE HONEST HEADLINE: at clock scale ASSEMBLY governs, not '
      'operation — it will not break doing its job, it will break '
      'being built',
      lc['governingCase'] == 'assembly'
      and 'break being built' in lc['headline'],
      extra=lc['headline'][:90])
check('the handling force is a KNOB, and doubling it keeps it '
      'governing while the operating loads do not move',
      load_cases(mgrs, 'clock-lavet-m0',
                 handling_force_n=10.0)['maxAssemblyN'] == 10.0)
check('fatigue is named as NOT modelled — a clock steps ~31.5 '
      'million times a year and this check does not address that',
      'fatigue' in lc['validity'] and 'MILLION' in lc['validity'])
check('strength values are labelled literature-est for the CLASS, '
      'with our castings untested',
      'literature-est' in lc['validity']
      or 'none of our' in lc['validity'])

print('== suite: mag-15b FEM stress, judged correctly ==')
from motors.motor_stress import part_stress  # noqa: E402
from motors.motor_shapes import (  # noqa: E402
    SEED_LAVET_V2_PART_SHAPES as _V2SH,
)

mgrf = _mgr()
mgrf.objectTables['GearTrainDefinition'] = {
    g['name']: types.SimpleNamespace(**g) for g in _GTR}
mgrf.objectTables['GearDefinition'] = {
    g['name']: types.SimpleNamespace(**g) for g in _GRS}
mgrf.objectTables['MotorPartDefinition'] = {
    p['name']: types.SimpleNamespace(**p) for p in SEED_MOTOR_PARTS}
mgrf.objectTables['MathShapeDefinition'] = {
    p['name']: types.SimpleNamespace(**p) for p in _V2SH}

st = part_stress(mgrf, 'clock-lavet-m0', 'lavet-v2-stator')
check('FEM runs on a real part and returns the STRESS TENSOR, both '
      'criteria, and where each peaks',
      st['ok'] and st['stress']['vonMisesPa'] > 0
      and st['stress']['maxPrincipalPa'] > 0
      and st['stress']['maxPrincipalAtXY']
      and st['stress']['meanStressTensor'],
      extra=str(st.get('refusal'))[:80])
check('a BRITTLE part is judged by max principal, NOT von Mises — '
      'and BOTH numbers are reported so the choice is auditable',
      'max principal' in st['stress']['judgedBy']
      and st['stress']['judgedPa'] == st['stress']['maxPrincipalPa']
      and st['stress']['vonMisesPa'] != st['stress']['judgedPa'])
check('the stator SURVIVES the governing load with margin',
      st['passes'] and st['safetyFactor'] > 4.0,
      extra=str(st.get('safetyFactor')))
check('ASSEMBLY is the governing case, not operation',
      st['governingLoad']['case'] == 'assembly')

pin = part_stress(mgrf, 'clock-lavet-m0', 'lavet-v2-pinion')
check('THE FINDING: the small pinion is AT RISK under a finger '
      'press (SF ~2.5 against the 4.0 required for an unmeasured '
      'brittle casting) — a real actionable result, not a rubber '
      'stamp',
      pin['ok'] and not pin['passes']
      and 1.5 < pin['safetyFactor'] < 3.5
      and 'AT RISK' in pin['verdict'],
      extra=str(pin.get('safetyFactor')))
check('a higher handling force makes it worse — the knob moves the '
      'answer, so the answer is load-driven not decorative',
      part_stress(mgrf, 'clock-lavet-m0', 'lavet-v2-pinion',
                  handling_force_n=20.0)['safetyFactor']
      < pin['safetyFactor'])
check('plane-strain and plane-stress give DIFFERENT answers, so '
      'the assumption is a real knob',
      part_stress(mgrf, 'clock-lavet-m0', 'lavet-v2-stator',
                  assumption='plane-strain')['stress']['judgedPa']
      != st['stress']['judgedPa'])
check('the mesh is reported, and the validity names fatigue, '
      'flaws and mesh dependence as NOT covered',
      st['elements'] > 0 and 'fatigue' in st['validity']
      and 'worst flaw' in st['validity'])
check('a part whose material lacks E/nu REFUSES — a stress number '
      'without a stiffness is a fiction, not an estimate',
      not part_stress(mgrf, 'clock-lavet-m0',
                      'lavet-v2-coil').get('ok'))

print('== suite: mag-16 FATIGUE + substitution ==')
from motors.motor_fatigue import (  # noqa: E402
    fatigue_derate, part_fatigue, substitution_search,
)

de = fatigue_derate(mgrf, 'opt-geopolymer-ferrite', 3.16e8)
check('a brittle casting has NO endurance limit — subcritical crack '
      'growth keeps eating strength, and the Weibull scatter derate '
      'multiplies on top',
      de['ok'] and de['fatigueClass'] == 'brittle-scg'
      and de['scgOrEnduranceFactor'] < 0.30
      and de['weibullFactor'] < 0.60
      and de['totalDerate'] < 0.20,
      extra=str(de.get('totalDerate')))
check('steel DOES have a real endurance limit, and no Weibull '
      'derate applies to it',
      fatigue_derate(mgrf, 'opt-electrical-steel', 3.16e8)
      ['fatigueClass'] == 'ductile-endurance-limit')
check('copper has NO endurance limit and the payload says '
      'surviving 1e7 is not a promise about 1e9',
      'not a promise' in fatigue_derate(
          mgrf, 'opt-copper-magnet-wire', 3.16e8)['why'])

fs = part_fatigue(mgrf, 'clock-lavet-m0', 'lavet-v2-stator')
check('THE FINDING: the stator PASSED static at SF 10.5 and FAILS '
      'fatigue at ~1.5 — 3.2e8 clock cycles change the answer',
      fs['ok'] and not fs['passes']
      and fs['staticSafetyFactor'] > 4.0
      and fs['fatigueSafetyFactor'] < 4.0,
      extra=f"{fs.get('staticSafetyFactor')} -> "
            f"{fs.get('fatigueSafetyFactor')}")
fp = part_fatigue(mgrf, 'clock-lavet-m0', 'lavet-v2-pinion')
check('and the pinion falls BELOW 1.0 — it does not merely lack '
      'margin, it is predicted to fail',
      fp['fatigueSafetyFactor'] < 1.0, extra=str(fp['fatigueSafetyFactor']))
check('a shorter service life is less punishing — the cycle count '
      'genuinely drives the answer',
      part_fatigue(mgrf, 'clock-lavet-m0', 'lavet-v2-pinion',
                   years=0.1)['fatigueSafetyFactor']
      > fp['fatigueSafetyFactor'])
check('moisture/stress-corrosion named as making real n WORSE than '
      'the value used',
      'MOISTURE' in fs['validity'])

sub = substitution_search(mgrf, 'clock-lavet-m0',
                          'lavet-v2-pinion')
check('substitution ranks the whole catalog with geometry and load '
      'held FIXED, so it compares materials not designs',
      sub['ok'] and sub['count'] >= 8
      and 'held FIXED' in sub['honesty'])
check('steel and alumina top the ranking — which is exactly what '
      'real clock movements use for pinions',
      sub['candidates'][0]['material'] in ('opt-electrical-steel',
                                           'opt-alumina'))
check('AND THE USEFUL ANSWER: a MAKEABLE option clears it too — '
      'fired ferrite ceramic, i.e. the Table 8.8 fire-the-casting '
      'escalation rung we already have',
      sub['bestMakeable']
      and sub['bestMakeable']['fatigueSafetyFactor'] >= 4.0,
      extra=str((sub.get('bestMakeable') or {}).get('material')))
check('the current material is in the list and marked, so the '
      'comparison includes what we have now',
      any(c['isCurrent'] for c in sub['candidates']))

print('== suite: mag-17 ROLES by domain + intersectional ==')
from motors.part_roles import (  # noqa: E402
    DOMAINS, ROLE_REQUIREMENTS, part_role_report, screen_candidates,
)

check('roles are grouped by physical DOMAIN, and every role '
      'declares one',
      all(r.get('domain') in DOMAINS
          for r in ROLE_REQUIREMENTS.values())
      and {'mechanical', 'magnetic', 'electrical', 'intersectional'}
      <= {r['domain'] for r in ROLE_REQUIREMENTS.values()})
check('the SAME property can be demanded in opposite directions by '
      'different domains: flux-carrying wants HIGH mu, field-inert '
      'wants LOW — so one material is excellent in one role and '
      'disqualified in another',
      ROLE_REQUIREMENTS['flux-carrying']['checks'][0][1] == 'min'
      and ROLE_REQUIREMENTS['field-inert']['checks'][0][1] == 'max')

pin = part_role_report(mgrf, 'lavet-v2-pinion')
check('the pinion performs FOUR roles across two domains — '
      'mechanical (moving, colliding, press-fitted) plus an '
      'INTERSECTIONAL one',
      pin['ok'] and len(pin['roles']) == 4
      and any(r['domain'] == 'intersectional' for r in pin['roles']))
check('the intersectional field-buffered role DEMANDS the geometry '
      'be stated (field_buffer_mm) — without it the role is a '
      'loophole, not an argument',
      any('field_buffer_mm' in str(c.get('property'))
          for c in pin['viability']['checks']))

sc = screen_candidates(mgrf, 'lavet-v2-pinion')
check('THE FIX for the copper-pinion bug: copper is now UNVIABLE '
      'on hardness (it would wear as a tooth face), so a fatigue '
      'number alone can no longer recommend it',
      'opt-copper-magnet-wire' not in sc['viable'])
check('and BRASS is viable — which is what real clock movements '
      'actually use for pinions',
      'opt-brass-cuzn' in sc['viable'])

st = screen_candidates(mgrf, 'lavet-v2-stator')
check('galvanized bio-steel is VIABLE for the stator (mu~2000 '
      'carries flux far better than our mu~2 castings) and UNVIABLE '
      'for the pinion (ferromagnetic steals flux) — same material, '
      'opposite verdicts, decided by the ROLE',
      'opt-galvanized-bio-steel' in st['viable']
      and 'opt-galvanized-bio-steel' not in sc['viable'])
check('UNASSESSED is never a pass — a property nobody measured '
      'cannot clear a requirement',
      all(v != 'viable' for v in
          [x['verdict'] for x in sc['screened']
           if x['unassessedOn']]))

print('== suite: mag-18 contact / wear / eddy (the named gaps) ==')
from motors.contact_wear import (  # noqa: E402
    WEAR_K_BANDS, contact_stress, eddy_drag, wear_life,
)
from gears.gear_seed import (  # noqa: E402
    SEED_GEAR_MESHES as _GMS, SEED_GEAR_TYPES as _GTY,
    SEED_SHAFT_NODES as _GSN,
)

mgrc = _mgr()
for _cls, _seed in (('GearTrainDefinition', _GTR),
                    ('GearDefinition', _GRS),
                    ('GearMeshDefinition', _GMS),
                    ('MathShapeDefinition', _V2S),
                    ('MotorPartDefinition', SEED_MOTOR_PARTS)):
    mgrc.objectTables[_cls] = {r['name']:
                               types.SimpleNamespace(**r)
                               for r in _seed}

c = contact_stress(mgrc, 'clock-lavet-m0', 'lavet-v2-pinion')
check('Hertz contact: the whole tooth load rides a patch under a '
      'micron wide — which is WHY hardness and not bulk strength '
      'is what the colliding role demands',
      c['ok'] and c['contactHalfWidthUm'] * 2 < 1.0
      and c['peakPressureMpa'] > 1.0,
      extra=str(c.get('contactHalfWidthUm')))
check('a BRITTLE tooth is judged by the SURFACE TENSILE stress at '
      'the trailing edge, NOT the peak pressure — judging by p_max '
      'would flatter a ceramic badly, since it is 10-20x stronger '
      'in compression',
      c['judgedMpa'] == c['surfaceTensileMpa']
      and c['judgedMpa'] < c['peakPressureMpa']
      and 'trailing edge' in c['criterion'])
check('and on THAT criterion the contact itself passes (SF ~8) — '
      'so contact is not what threatens this tooth; fatigue is',
      c['passes'] and c['safetyFactor'] > 4.0,
      extra=str(c.get('safetyFactor')))

w = wear_life(mgrc, 'lavet-v2-pinion', sliding_distance_m=1.58e5,
              load_n=8.3e-4)
check('wear is reported as a BAND because the Archard coefficient '
      'spans six orders across pairs and lubrication — a single '
      'number would be a lie',
      w['ok'] and w['kBand'][1] / w['kBand'][0] >= 10
      and 'BAND and not a prediction' in w['honesty'])
check('THE FINDING: a DRY cast-on-cast pinion can lose ~1.5 mm3 in '
      'ten years — against a whole pinion of only ~7 mm3, i.e. a '
      'fifth of the part. This is the argument for oiling, or for '
      'brass',
      w['wornVolumeMm3Band'][1] > 1.0)
check('a lubricated metal pair is ~4 orders better, which is '
      'exactly why clock pivots are oiled',
      WEAR_K_BANDS['lubricated-metal'][1]
      < WEAR_K_BANDS['dry-brittle-on-brittle'][0] / 100)

e = eddy_drag(mgrc, 'lavet-v2-pinion', b_gap_t=0.005,
              frequency_hz=1.0)
check('eddy drag evaluates AT THE STATED BUFFER — the promise the '
      'field-buffered role made',
      e['ok'] and e['bufferMm'] == 2.6 and e['decayFactor'] < 0.1)
check('and the buffer works because loss goes as B SQUARED: the '
      'field cut is squared into the loss',
      'B SQUARED' in e['bufferHelps']
      and e['lossDensityWPerM3'] < 1e-12)
check('the 1/r^3 decay is named as the WEAKEST LINK with the '
      'honest upgrade (read B from the mag-fv field views) rather '
      'than presented as a result',
      'weakestLink' in e and 'field views' in e['weakestLink'])
mgrc.objectTables['MotorPartDefinition']['lavet-v2-stator'] \
    .field_buffer_mm = None
check('a part with NO stated buffer REFUSES the eddy check — the '
      'role demanded geometry and the analysis enforces it',
      not eddy_drag(mgrc, 'lavet-v2-stator', b_gap_t=0.005,
                    frequency_hz=1.0).get('ok'))

print('== suite: mag-19 TRUE PRICE per lifespan unit ==')
from motors.lifecycle_cost import (  # noqa: E402
    EXTRAPOLATION_CAP_CYCLES, cheapest_configuration,
    cost_per_lifespan_unit, fatigue_life_cycles, lifespan_unit_for,
)

u = lifespan_unit_for('timekeeper')
check('STEP ONE is choosing the UNIT, and the reasoning travels '
      'with it: a clock produces TIME KEPT, not runtime hours '
      '(it never stops) and not mass (it consumes nothing)',
      u['ok'] and u['unit'] == 'year-of-timekeeping'
      and 'never stops' in u['why'])
check('an undefined product kind REFUSES rather than guessing a '
      'denominator — picking it IS the modelling decision',
      not lifespan_unit_for('mystery-widget').get('ok'))

lf = fatigue_life_cycles(mgrc, 'opt-plain-geopolymer', 1.58)
check('life INVERTS the crack-growth law (N = (S/s)^n) instead of '
      'only passing/failing a fixed horizon',
      lf['ok'] and lf['model'] == 'brittle-scg'
      and 'N_fail' in lf['why'])
check('extrapolation is CAPPED: a law pushed far past any data is '
      'arithmetic, not knowledge, and the cap is reported as the '
      'cap',
      fatigue_life_cycles(mgrc, 'opt-alumina', 0.5)
      ['cyclesToFailure'] == EXTRAPOLATION_CAP_CYCLES)

cp = cost_per_lifespan_unit(mgrc, 'clock-lavet-m0',
                            'lavet-v2-pinion')
check('THE HEADLINE: the cast pinion costs ~1 cent upfront and over '
      '1.5 MILLION replacements in ten years — a true price near '
      '$1600 per year-of-timekeeping. The cheapest part is the most '
      'expensive product.',
      cp['ok'] and cp['upfrontUsd'] < 0.05
      and cp['costPerUnitUsd'] > 100,
      extra=f"upfront {cp.get('upfrontUsd')} true "
            f"{cp.get('costPerUnitUsd')}")
check('BOTH numbers are kept and the payload says which question '
      'each answers — upfront for low budget/urgency, per-unit as '
      'the true price',
      'low budget' in cp['bothNumbersNote']
      and 'true price' in cp['bothNumbersNote'])

rank = cheapest_configuration(
    mgrc, 'clock-lavet-m0', 'lavet-v2-pinion',
    costs_usd={'opt-brass-cuzn': 0.35, 'opt-alumina': 2.50,
               'opt-fired-ceramic': 0.08})
check('candidates are ROLE-SCREENED first: a material that cannot '
      'do the job is not made a bargain by being cheap',
      rank['ok'] and set(rank['roleViableOnly'])
      == {'opt-fired-ceramic', 'opt-alumina', 'opt-brass-cuzn'})
check('both orderings are produced so they CAN disagree, and a '
      'disagreement is reported as the finding',
      rank['cheapestTruePrice'] and rank['cheapestUpfront']
      and 'ordersDisagree' in rank)
check('capped and prior-based lifespans are FLAGGED in the '
      'ranking, so an unearned number cannot quietly win',
      any(c['lifeIsCapped'] for c in rank['candidates'])
      and any(c['lifeIsPrior'] for c in rank['candidates']))
check('the honesty rider says to trust the ORDERING, not the '
      'absolute number — the crack-growth exponent amplifies every '
      'input uncertainty',
      'ORDERING' in cp['honesty'])

print('== suite: mag-20 physics as CONFIGURATION, not code ==')
import math as _m2  # noqa: E402
from motors.physics_equations import (  # noqa: E402
    equation_catalog, evaluate_named,
)

cat = equation_catalog()
check('the closed-form physics is held as CONFIGURATION — LaTeX '
      'rows evaluated by the EXISTING no-code executor, not '
      're-implemented in Python',
      cat['count'] >= 12
      and all(e['latex'] and e['symbols'] for e in cat['equations']))
check('and the code/config boundary is stated as a DECISION: '
      'refusals, criterion selection, role predicates and units '
      'stay code; formulas do not',
      'policy' in cat['principle']
      and 're-implementing one are opposite acts'
      in cat['principle'])

ev = evaluate_named('eq-scg-life-cycles',
                    {'S': 2.25, 's': 1.58, 'n': 15})
check('the configured crack-growth life reproduces the Python '
      'result it replaces (~200 cycles) — the migration is '
      'verified, not asserted',
      ev['ok']
      and abs(ev['result']['result_numeric'] - 200.85) < 1.0,
      extra=str(ev['result'].get('result_numeric')))
check('the Weibull derate likewise matches (0.5627)',
      abs(evaluate_named('eq-weibull-survival-derate',
                         {'P': 0.99, 'm': 8})
          ['result']['result_numeric'] - 0.5627) < 1e-3)
check('and the planetary ratio: ring 132 / sun 12 -> 12:1',
      abs(evaluate_named('eq-planetary-ring-fixed',
                         {'R': 132, 'S': 12})
          ['result']['result_numeric'] - 12.0) < 1e-9)
check('pi is bound EXPLICITLY so the executor returns a number '
      'rather than a symbolic expression — the lesson from the '
      'first Hertz attempt',
      evaluate_named('eq-hertz-line-contact-pmax',
                     {'F': 0.833, 'E': 8.33e9, 'R': 3.97e-4,
                      'c': _m2.pi})['result']['result_numeric']
      > 1e6)
check('an unknown equation refuses and names what IS available',
      not evaluate_named('eq-nonsense', {}).get('ok'))
check('every equation documents what each symbol MEANS — a formula '
      'without its variable meanings is a puzzle, not a spec',
      all(all(v for v in e['symbols'].values())
          for e in cat['equations']))

print('== suite: mag-21 THE CLOCK AS A PRODUCT ==')
from motors.clock_product import (  # noqa: E402
    movement_class, power_budget, product_datasheet,
)

mgrp2 = _mgr()
for _c, _s in (('GearTrainDefinition', _GTR),
               ('GearDefinition', _GRS),
               ('GearMeshDefinition', _GMS),
               ('GearTypeDefinition', _GTY),
               ('ShaftNodeDefinition', _GSN),
               ('MathShapeDefinition', _V2S),
               ('MotorPartDefinition', SEED_MOTOR_PARTS),
               ('PriceCitation', SEED_PRICE_CITATIONS)):
    mgrp2.objectTables[_c] = {r['name']: types.SimpleNamespace(**r)
                              for r in _s}

pw = power_budget(mgrp2)
check('power is DERIVED from the winding, not asserted: 20 mA for '
      'a 30 ms pulse at 1 Hz = 3% duty = 0.6 mA average',
      pw['ok'] and abs(pw['dutyPct'] - 3.0) < 0.01
      and abs(pw['averageCurrentMa'] - 0.6) < 0.01,
      extra=str(pw.get('averageCurrentMa')))
check('battery life falls out of it — and an AA lasts MONTHS, not '
      'the years a bought movement gives',
      2 < pw['cells']['AA-alkaline']['monthsOfService'] < 12)

mc = movement_class(mgrp2)
check('THE ANSWER TO "is this a watch": NO, and by the numbers — '
      'the rotor IS watch-scale but the widest wheel is 180 mm, it '
      'drives a 260 mm face, and a watch cell would last days',
      mc['ok'] and mc['isWatch'] is False
      and mc['classification'] == 'wall-clock movement'
      and mc['watchCellMonths'] < 0.5,
      extra=str(mc.get('watchCellMonths')))
check('and it says HOW to make it a watch rather than just saying '
      'no — more, smaller stages plus closing the permeability gap',
      'smaller stages' in mc['howToMakeItAWatch']
      and 'permeability' in mc['howToMakeItAWatch'])
check('the power gap is explained by the PHYSICS already on record: '
      'mu~2 castings need mA where laminated steel needs uA',
      'permeability gap' in pw['whyThirsty'])

ds = product_datasheet(mgrp2)
check('the product view COMPOSES every analysis and all sections '
      'resolve',
      ds['ok'] and all(v.get('ok') for v in ds['sections'].values())
      and len(ds['sections']) >= 9)
check('and it reaches a PRODUCT verdict rather than a pile of '
      'numbers: NOT SHIPPABLE, with the blockers named',
      ds['shippable'] is False and len(ds['blockers']) >= 2
      and any('fatigue' in b for b in ds['blockers'])
      and any('power' in b or 'thirst' in b or 'cell' in b
              for b in ds['blockers']))
check('a verdict of NOT SHIPPABLE now carries the ROUTE past the '
      'blockers, because half an answer is naming a wall without '
      'naming the door',
      ds['routePastTheBlockers'] is not None
      and ds['routePastTheBlockers'].get('answerable') is True
      and 'A ROUTE EXISTS' in ds['verdict'])
check('the honesty rider says the caveats COMPOUND across composed '
      'sections and this is a design review, not a datasheet for a '
      'buyer',
      'COMPOUND' in ds['honesty']
      and 'not a datasheet' in ds['honesty'])

# ---- mag-22: the locally producible route ------------------------
print('\n-- mag-22 local route --')
from motors.part_roles import (               # noqa: E402
    PART_ROLE_ASSIGNMENTS, role_viability,
)
from motors.local_route import (          # noqa: E402
    locally_producible, minimum_drive_current, producible_clock,
    solve_local_route, turns_sweep,
)

lp = locally_producible(mgrp2)
check('the local set admits only recipe-seeded / made-and-measured '
      'options — a route we have, not a paper we read',
      lp['ok'] and lp['count'] >= 5
      and all(m['realizationLevel'] in
              ('recipe-seeded', 'made-and-measured')
              or m['promotion'] for m in lp['materials']))
check('NdFeB is excluded even though it would obviously work, '
      'because "it would work" is not an answer to "can we make it"',
      not any(m['material'] == 'opt-ndfeb'
              for m in lp['materials']))
check('a promotable material is carried with the DEMONSTRATION that '
      'would earn it, so reachable is never confused with achieved',
      any(m['promotion'] for m in lp['materials'])
      and all('MEASURE' in m['promotion']['demonstration']
              or 'measured' in m['promotion']['demonstration']
              for m in lp['materials'] if m['promotion']))

lr = solve_local_route(mgrp2)
check('a local route SOLVES, and the kiln is what unlocks it',
      lr['ok'] and lr['solved']
      and all(v['process'] == 'kiln-fire'
              for v in lr['route']['assignment'].values()))
check('a PERMANENT MAGNET can never be proposed as the field-inert '
      'pinion: mu_rec ~1.1 sails through a permeability-only check, '
      'so field-inert also disqualifies on stated REMANENCE',
      lr['route']['assignment']['lavet-v2-pinion']['material']
      == 'opt-fired-ceramic')
check('and the disqualifier does not demand the property EXIST — a '
      'structural ceramic states no remanence because it is not a '
      'magnet, and silence is not evidence of guilt',
      role_viability(mgrp2, 'opt-fired-ceramic',
                     PART_ROLE_ASSIGNMENTS['lavet-v2-pinion'],
                     part_row=mgrp2.objectTables[
                         'MotorPartDefinition']['lavet-v2-pinion'],
                     )['verdict']
      == 'viable')
check('the pinion clears fatigue once fired — the blocker that '
      'read as a materials limit was a FIRING choice (SF 0.39 -> >1)',
      lr['route']['assignment']['lavet-v2-pinion'][
          'fatigueSafetyFactor'] > 1.0)
check('copper is declared IMPORTED rather than quietly counted as '
      'local, because a route that hides its one import is not one',
      any('copper' in x.lower()
          for x in lr['route']['importedParts']))
check('the route is NOT claimed as fully proven today — it names '
      'the one demonstration it rests on',
      lr['route']['fullyProvenToday'] is False
      and len(lr['route']['demonstrationsRequired']) == 1)

md = minimum_drive_current(mgrp2)
check('the drive current is DERIVED by bisecting the existing step '
      'condition, not asserted — the design stated 0.02 A and never '
      'solved for it',
      md['ok'] and md['thresholdAmps'] < md['statedAmps']
      and md['designedAmps'] < md['statedAmps'])
check('and it carries a stated design MARGIN rather than shipping '
      'the bare stepping threshold',
      md['designedAmps'] > md['thresholdAmps'])

gap = minimum_drive_current(mgrp2, rotor_material='opt-carbonyl-iron')
check('a missing property is reported as a DATA GAP, never as a '
      'finding that the motor fails — the two are different claims',
      (gap['ok'] or gap.get('kind') in ('data-gap',
                                        'does-not-step')))

ts = turns_sweep(mgrp2)
check('the turns sweep holds the stepping MMF fixed and shows '
      'current falling as 1/N — the power lever the M0 never pulled',
      ts['ok'] and len(ts['candidates']) >= 4
      and ts['candidates'][-1]['ampsForSameMmf']
      < ts['candidates'][0]['ampsForSameMmf'])
check('and it reads winding_report\'s REAL fit verdict: the stated '
      '12 mm2 bobbin holds no candidate, not even the baseline',
      all(c['fitVerdict'] == 'IMPOSSIBLE' for c in ts['candidates'])
      and all(c['windowNeededMm2'] > c['statedWindowMm2']
              for c in ts['candidates']))

pc = producible_clock(mgrp2)
check('the composed answer reaches a WORKING clock: within 5x a '
      'commercial wall movement, years on a cell, not months',
      pc['ok'] and pc['answerable']
      and pc['winding']['timesThirstierThanWallClock'] <= 5.0
      and pc['winding']['aaYears'] > 2.0)
check('it states all three costs of "local": the import, the '
      'demonstration, and the processes',
      pc['imported'] and pc['mustDemonstrate']
      and pc['processesNeeded'])
check('inductance is no longer merely NAMED as a risk — mag-23 '
      'solved it, and the route says so with numbers instead of '
      'carrying a caveat it never discharged',
      'inductanceChecked' in pc
      and 'tau' in pc['inductanceChecked']
      and not any('INDUCTANCE is not modelled' in u
                  for u in pc['stillUnknown']))
check('and the caveat that REPLACED it is the real one: the lumped '
      'reluctance model is ~4.7x off at our castings mu~2',
      any('4.7x' in u or 'LUMPED' in u for u in pc['stillUnknown']))
check('and the counterintuitive finding is stated plainly: a '
      'stronger magnet makes power WORSE, because the magnet that '
      'makes the torque also makes the detent',
      'WORSE' in pc['honesty'] and 'detent' in pc['honesty'])

# ---- mag-23: inductance, actually solved ------------------------
print('\n-- mag-23 inductance (FEM + config) --')
from materialsScience.engines.fem_engine import (   # noqa: E402
    MU0, magnetostatic_capability, solve_magnetostatic_2d,
)
from motors.inductance import (                     # noqa: E402
    inductance_across_turns, model_validity, pulse_response,
    solve_inductance,
)

cap = magnetostatic_capability()
check('the magnetostatic solver states what it CANNOT do — '
      'saturation, eddy currents, hysteresis, 3D leakage',
      cap['ok'] and len(cap['doesNot']) >= 4
      and any('SATURATION' in d for d in cap['doesNot']))

# VALIDATION against a closed form: a gap-dominated C-core should
# approach N^2 mu0 A / g, exceeding it by fringing and leakage.
mm = 1e-3
_core = [{'x0': 5 * mm, 'y0': 5 * mm, 'x1': 35 * mm, 'y1': 35 * mm,
          'mu_r': 1e4},
         {'x0': 12 * mm, 'y0': 12 * mm, 'x1': 28 * mm, 'y1': 28 * mm,
          'mu_r': 1.0},
         {'x0': 28 * mm, 'y0': 19 * mm, 'x1': 35 * mm, 'y1': 21 * mm,
          'mu_r': 1.0}]
_coils = [{'x0': 12 * mm, 'y0': 15 * mm, 'x1': 16 * mm,
           'y1': 25 * mm, 'sign': 1},
          {'x0': 1 * mm, 'y0': 15 * mm, 'x1': 5 * mm, 'y1': 25 * mm,
           'sign': -1}]
_cut = ((20 * mm, 20 * mm), (37 * mm, 20 * mm))
fem = solve_magnetostatic_2d(40 * mm, 40 * mm, _core, _coils,
                             turns=100.0, current=0.1, depth=7 * mm,
                             refine=16, flux_cut=_cut)
_ideal = 100.0 ** 2 * MU0 * (7 * mm * 7 * mm) / (2 * mm)
check('VALIDATION: a gapped C-core lands within 1.2-2.5x of the '
      'closed-form ideal gap — ABOVE it, because the formula omits '
      'the fringing and window leakage the field solve captures',
      fem['ok'] and 1.2 < fem['inductanceH'] / _ideal < 2.5,
      extra=f"{fem['inductanceH'] / _ideal:.2f}x")
check('and L from stored ENERGY agrees with L from an independent '
      'flux CUT — two routes through one solution, not the same '
      'quadratic form computed twice',
      0.6 < fem['crossCheckRatio'] < 1.4,
      extra=str(round(fem['crossCheckRatio'], 3)))

coarse = solve_magnetostatic_2d(40 * mm, 40 * mm, _core, _coils,
                                turns=100.0, current=0.1,
                                depth=7 * mm, refine=4,
                                flux_cut=_cut)
check('the mesh is ALIGNED to region boundaries, so a coarse run '
      'stays within 15% of the fine one — a uniform mesh let '
      'elements straddle the gap and short it out, wrong by 150x',
      coarse['ok'] and coarse.get('meshAlignedToFeatures')
      and abs(coarse['inductanceH'] - fem['inductanceH'])
      / fem['inductanceH'] < 0.15)

one_sided = solve_magnetostatic_2d(40 * mm, 40 * mm, _core,
                                   [_coils[0]], turns=100.0,
                                   current=0.1, depth=7 * mm,
                                   refine=8)
check('a single-sided coil is WARNED about rather than silently '
      'solved: a planar slice cuts a real coil twice',
      one_sided['ok'] and any('ONE coil sign' in w
                              for w in one_sided['warnings']))
check('and no coil at all REFUSES, because a zero source would give '
      'an inductance that is purely a mesh artefact',
      solve_magnetostatic_2d(40 * mm, 40 * mm, _core, [],
                             turns=100.0, current=0.1)['ok'] is False)

ind = solve_inductance(mgrp2)
check('the M0 inductance solves from the design row\'s OWN stated '
      'pole area, gap and thickness — geometry that moves when the '
      'design moves',
      ind['ok'] and ind['inductanceH'] > 0
      and ind['geometry']['gapM'] > 0)

pr = pulse_response(mgrp2)
check('THE mag-22 QUESTION ANSWERED: the coil reaches its current '
      'well inside the 30 ms pulse (tau ~ tens of us), so '
      'inductance does NOT limit this drive',
      pr['ok'] and pr['pulseOverTau'] > 100
      and pr['fractionOfFinalReached'] > 0.99
      and pr['inductanceLimits'] is False)
check('and the RL arithmetic runs through CONFIGURED equation rows, '
      'not Python formulas retyped in this module',
      set(pr['equationsUsed']) >= {'eq-rl-time-constant',
                                   'eq-rl-current-rise'})

it = inductance_across_turns(mgrp2)
check('the deep-winding claim SURVIVES its own inductance: even at '
      'the deepest turns the pulse is many time constants',
      it['ok'] and it['claimSurvives']
      and it['worst']['pulseOverTau'] > 50)
check('and the tau scaling is MEASURED across the sweep rather than '
      'predicted from the naive floored-gauge argument',
      it['tauScaling'] is not None
      and 'MEASURED' in it['finding'])

mv = model_validity(mgrp2)
check('THE FINDING BEYOND INDUCTANCE: FEM and the lumped reluctance '
      'model agree to a constant once mu_r >= 200, and diverge ~4x '
      'at our castings\' mu~2 — a core that barely beats air does '
      'not CONFINE flux, so the network has no branch for it',
      mv['ok'] and mv['highMuAgreement'] is not None
      and mv['lowMuDisagreement'] > 2.5 * mv['highMuAgreement'])
check('and it says what would settle it: one LCR measurement on a '
      'wound core, ten minutes of bench time',
      'LCR' in mv['whatWouldSettleIt'])

# ---- mag-24: a research route to local magnet wire ---------------
print('\n-- mag-24 wire insulation --')
from motors.wire_insulation import (            # noqa: E402
    drawing_capability, insulated_winding_effect, insulation_catalog,
    local_wire_route,
)

cat = insulation_catalog()
check('the catalog carries the HISTORY as evidence: oleoresinous '
      'varnish WAS the industry standard until 1939, so an oil-based '
      'magnet wire enamel is the original, not a novelty',
      cat['ok'] and '1939' in cat['historyNote']
      and any(o['name'] == 'ins-oleoresinous-tung'
              for o in cat['options']))
check('every option carries a BLOCKER, including the ones we like — '
      'a candidate with no stated obstacle has not been thought '
      'about',
      all(o.get('blocker') for o in cat['options']))
check('nothing here is claimed above literature-demonstrated, '
      'because we have enamelled no wire',
      all(o['realization_level'] in ('literature-demonstrated',
                                     'buyable-cited')
          for o in cat['options']))

eff = insulated_winding_effect(mgrp2)
rows = {r['insulation']: r for r in eff['rows'] if r.get('ok')}
check('insulation build actually MOVES the window — an earlier pass '
      'patched a module global that was already bound as a default '
      'argument, so every candidate silently returned the same '
      'commercial figure',
      len({round(r['windowNeededMm2'], 1)
           for r in rows.values()}) >= 4)
check('COTTON is ruled out by arithmetic, not taste: at 0.075 mm '
      'build it needs ~3x the window because thickness enters as a '
      'SQUARE',
      rows['ins-cotton-covered']['windowVsCommercial'] > 2.5)
check('and sol-gel silica is the THINNEST local option — thinner '
      'than the commercial enamel it would replace',
      rows['ins-solgel-silica']['windowVsCommercial'] < 1.0)
check('but its brittleness is stated as the thing to TEST rather '
      'than assumed away, because a cracked ceramic film is a short',
      'BRITTLE' in rows['ins-solgel-silica']['flexibility'].upper()
      or 'BRITTLE' in rows['ins-solgel-silica']['blocker'])

draw = drawing_capability()
check('THE FINDING: insulation is the TRACTABLE half and DRAWING is '
      'the wall — the opposite of the intuitive order',
      draw['ok'] and draw['localCeilingAwg'] < draw['mag22NeedsAwg']
      and 'WALL' in draw['finding'].upper())

route = local_wire_route(mgrp2)
check('the research route orders the CHEAP decisive tests first — '
      'bend a sol-gel sample before building a draw bench',
      route['ok'] and len(route['researchOrder']) >= 4
      and all(s.get('proves') for s in route['researchOrder']))
check('and it states the honest expected outcome up front: '
      'insulation goes local, drawing does not, so BARE wire '
      'replaces finished magnet wire as the import — a smaller '
      'dependency, not a closed loop',
      'not the same as closing the loop' in
      route['honestExpectation'])

failed = _results.count(False)
print(f'\n{len(_results) - failed}/{len(_results)} checks passed')
raise SystemExit(1 if failed else 0)
