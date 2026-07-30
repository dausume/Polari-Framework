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

failed = _results.count(False)
print(f'\n{len(_results) - failed}/{len(_results)} checks passed')
raise SystemExit(1 if failed else 0)
