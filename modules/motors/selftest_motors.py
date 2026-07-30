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

failed = _results.count(False)
print(f'\n{len(_results) - failed}/{len(_results)} checks passed')
raise SystemExit(1 if failed else 0)
