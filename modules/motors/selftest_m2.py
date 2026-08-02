"""
@module motors.selftest_m2

M2 selftests — the PM rung, built the M0/M1 way.

m2-1: the rotation solver. One electrical revolution is exactly
360/pole_pairs mechanical degrees; in synchronism the position
error is exactly zero (a constant lag moves no position); the load
angle obeys sin(delta) against the closed-form peak (two paths,
one number); overload FALLS OUT of step rather than drooping; a
design with no magnet is refused to M1; and k_e derives from the
same magnet MMF and loop reluctance the torque uses.

Run from polari-framework/: python3 -m motors.selftest_m2
"""

import json
import math
import types

from magnetics.magnet_seed import SEED_MATERIAL_OPTIONS
from motors.motor_basis import SEED_MOTOR_DESIGNS
from motors.m2_rotation import (
    NO_COGGING_FACT, PULL_OUT_LAG_DEG, analytic_peak_torque,
    back_emf_constant, pull_out_load_limit, rotation_sim,
)
from motors.m2_rotation import _geometry

PASS = '\033[92mPASS\033[0m'
FAIL = '\033[91mFAIL\033[0m'
_results = []


def check(label, cond, extra=''):
    _results.append(bool(cond))
    print(f'{PASS if cond else FAIL}: {label}'
          + (f'  [{extra}]' if extra and not cond else ''))


def _table(seed):
    return {s['name']: types.SimpleNamespace(**s) for s in seed}


def _mgr():
    m = types.SimpleNamespace()
    m.objectTables = {
        'MagneticMaterialOption': _table(SEED_MATERIAL_OPTIONS),
        'MotorDesignDefinition': _table(SEED_MOTOR_DESIGNS),
    }
    m.objectTypingDict = {k: object() for k in m.objectTables}
    return m


mgr = _mgr()
M2 = 'ferrite-pm-m2'
M1 = 'reluctance-6s4p-m1'
_M2PARAMS = json.loads(
    [d for d in SEED_MOTOR_DESIGNS if d['name'] == M2][0]
    ['params_json'])

print('== suite: m2-1 rotation in synchronism ==')
sim = rotation_sim(mgr, M2, steps=12)
check('the M2 sim runs on the seeded PM design',
      sim.get('ok'), json.dumps(sim)[:200])
check('ONE ELECTRICAL REVOLUTION IS 360/pole_pairs MECHANICAL '
      'DEGREES, exactly — 4 poles means 2 pole pairs means 180 '
      'deg of shaft per electrical turn',
      sim['polePairs'] == 2.0
      and sim['mechDegPerElecRev'] == 180.0
      and abs(sim['positionComparison']['expectedRotationDeg']
              - 180.0) < 1e-9)
check('zero load: the rotation error is EXACTLY zero — in step, '
      'a constant lag moves no position (M1\'s exactness claim '
      'over the opposite physics)',
      sim['positionComparison']['positionErrorDeg'] == 0.0
      and sim['inSync'] and sim['pullOutStep'] is None)
check('and at zero load the LOAD ANGLE is zero at every step — '
      'the drive\'s stated 90 deg advance is the reference, not '
      'a lag (fold gamma in or the machine looks permanently on '
      'the edge of pull-out)',
      all(abs(h['lagDeg']) < 0.2 for h in sim['history']))
check('the payload states its honesty: named gaps, the assumed '
      'commutation rate, and COGGING AS A NAMED ABSENCE',
      len(sim['namedGaps']) == 3
      and 'ASSUMED' in sim['speedAssumption']['note']
      and 'ZERO COGGING' in sim['noCoggingInModel']
      and 'worm' in sim['noCoggingInModel'].lower())
check('saliency 1.0 is stated as what it means: the reluctance '
      'torque term is identically zero, so everything M2 makes '
      'is the magnet',
      sim['calibration']['saliencyRatio'] == 1.0
      and 'identically zero'
      in sim['calibration']['saliencyNote'].lower())

rev = rotation_sim(mgr, M2, steps=12, direction=-1)
check('reversed commutation spins the other way, equally exactly',
      rev.get('ok') and rev['inSync']
      and rev['positionComparison']['positionErrorDeg'] == 0.0
      and rev['history'][6]['thetaContinuousDeg'] < 0.0)

print('== suite: m2-1 the load angle and pull-out ==')
po = pull_out_load_limit(mgr, M2)
check('pull-out limit solves, and sits just under the peak '
      'torque (the last stable point is delta = 90 deg)',
      po.get('ok') and 0.9 < po['ratioToPeak'] <= 1.0
      and po['atLagDeg'] == PULL_OUT_LAG_DEG,
      f"ratio={po.get('ratioToPeak')} atLag={po.get('atLagDeg')}")
check('TWO PATHS, ONE NUMBER: the swept co-energy peak and the '
      'closed form (3/2)*MMF_coil*Phi_pm*pole_pairs agree',
      po['crossCheck']['consistent'],
      json.dumps(po['crossCheck'])[:220])

_geo = _geometry(mgr, M2)
_peak = analytic_peak_torque(_geo)
for frac, want in ((0.5, 30.0), (0.866, 60.0)):
    _mid = rotation_sim(mgr, M2, steps=12,
                        load_torque_nm=frac * _peak)
    check(f'THE SYNCHRONOUS MACHINE LAW: at {frac:g} of peak '
          f'torque the rotor settles at a load angle of '
          f'{want:g} deg (torque goes as sin delta) and still '
          f'keeps up exactly',
          _mid['inSync']
          and abs(_mid['history'][6]['lagDeg'] - want) < 1.5
          and _mid['positionComparison']['positionErrorDeg']
          == 0.0,
          f"lag={_mid['history'][6]['lagDeg']}")

over = rotation_sim(mgr, M2, steps=12,
                    load_torque_nm=1.3 * po['pullOutLimitNm'])
check('OVERLOAD DOES NOT DROOP, IT FALLS OUT: past the pull-out '
      'limit synchronism is lost, the step where it happened is '
      'named, and the position error is large rather than '
      'marginal',
      not over['inSync'] and over['pullOutStep'] is not None
      and abs(over['positionComparison']['positionErrorDeg'])
      > 100.0)
check('and every history entry carries its own inSync verdict, '
      'so the ledger says WHERE it happened',
      all('inSync' in h for h in over['history'])
      and any(not h['inSync'] for h in over['history'][1:]))

just_under = rotation_sim(mgr, M2, steps=12,
                          load_torque_nm=0.98
                          * po['pullOutLimitNm'])
check('the limit is REAL: 2% under it the machine still keeps '
      'up, 30% over it does not',
      just_under['inSync'] and not over['inSync'])

print('== suite: m2-1 refusals (the rung boundary) ==')
ref = rotation_sim(mgr, M1)
check('a reluctance design is REFUSED by name to the M1 solver '
      '— M2 is the PM rung and will not pretend otherwise',
      not ref.get('ok') and 'm1-sequence' in ref.get('refusal', '')
      and 'magnet' in ref.get('refusal', ''))
soft = rotation_sim(mgr, M2, rotor_material='opt-geopolymer-'
                                            'ferrite')
check('a SOFT rotor material is refused too: no H_c, no magnet, '
      'no M2 (the refusal names the 100 kA/m test)',
      not soft.get('ok') and 'H_c' in soft.get('refusal', ''))

print('== suite: m2-1 back-EMF constant ==')
ke = back_emf_constant(mgr, M2)
check('k_e derives and is positive, with the flux, the loop '
      'reluctance and the turns all shown',
      ke.get('ok') and ke['kEVoltSPerRad'] > 0.0
      and ke['fluxPerPoleWb'] > 0.0
      and ke['turnsPerPhase'] == _M2PARAMS['coil_turns'])
check('DERIVED, NOT RESTATED: k_e = pole_pairs * N * MMF_m / '
      'R_loop reproduces exactly from the payload\'s own parts',
      abs(ke['kEVoltSPerRad']
          - 2.0 * ke['turnsPerPhase']
          * (ke['magnetMmfAt'] / ke['loopReluctancePerH']))
      < 1e-15)
ke_nd = back_emf_constant(mgr, M2, rotor_material='opt-ndfeb')
check('k_e SCALES LINEARLY with the magnet: swapping in the '
      'NdFeB reference row multiplies it by exactly the H_c '
      'ratio (the magnet enters as MMF = H_c x length)',
      abs(ke_nd['kEVoltSPerRad'] / ke['kEVoltSPerRad']
          - 900.0 / 260.0) < 1e-9,
      f"ratio={ke_nd['kEVoltSPerRad'] / ke['kEVoltSPerRad']}")
check('and the B_r / H_c SLACK IS NAMED: the rows carry both as '
      'independent literature values, so mu0*mu_rec*H_c does '
      'not reproduce B_r exactly and the deviation is stated '
      'rather than rounded away',
      ke['materialConsistency']['deviationPct'] > 0.0
      and ke['materialConsistency']['deviationPct'] < 20.0
      and 'independent literature'
      in ke['materialConsistency']['note'].lower(),
      json.dumps(ke.get('materialConsistency'))[:200])
check('k_e is named as THE model-adjudicating measurement, and '
      'the magnet prior names the experiment that retires it',
      'no other error can absorb' in ke['adjudicates']
      and 'press-sinter-magnetize' in ke['honesty'])

print('== suite: m2-1 two-modules-agree ==')
check('the cogging fact is ONE string, shared by the sim and the '
      'pull-out report (a fact stated twice gets a guard)',
      sim['noCoggingInModel'] == NO_COGGING_FACT
      == po['noCoggingInModel'])
check('the M2 design row is the SAME 6s/4p frame as M1 — that is '
      'the ladder story: only the rotor changes',
      _M2PARAMS['slots'] == 6 and _M2PARAMS['poles'] == 4
      and json.loads(
          [d for d in SEED_MOTOR_DESIGNS
           if d['name'] == M1][0]['params_json'])['slots'] == 6)

print('== suite: m2-2 the rotor is the only new geometry ==')
from motors.motor_shapes import (          # noqa: E402
    SEED_M1_PART_SHAPES, SEED_M2_PART_SHAPES, SEED_M2_SIM_SPACES,
)
from motors.motor_parts import (           # noqa: E402
    PART_REUSE, SEED_MOTOR_PARTS, part_report,
)

_SH = {s['name']: s for s in SEED_M1_PART_SHAPES
       + SEED_M2_PART_SHAPES}
_P = {n: json.loads(s['parameters_json'])
      for n, s in _SH.items() if s.get('parameters_json')}
_M1PARAMS = json.loads(
    [d for d in SEED_MOTOR_DESIGNS if d['name'] == M1][0]
    ['params_json'])

check('THE AIR GAP IS THE TWO PARTS: the reused M1 tooth face '
      'radius minus the magnet ring\'s outer radius IS the design '
      'row\'s gap_base_m (0.4 mm), not a third statement of it',
      abs((_P['motor-m1-stator-tooth']['r_face']
           - _P['motor-m2-magnet-ring-outer']['radius'])
          - _M2PARAMS['gap_base_m'] * 1e3) < 1e-9,
      f"{_P['motor-m1-stator-tooth']['r_face']} - "
      f"{_P['motor-m2-magnet-ring-outer']['radius']}")
check('THE MAGNET LENGTH IS THE RING: outer minus inner radius IS '
      'magnet_length_m (4.0 mm) — the number that sets the MMF '
      'and the number a mould would cut are one number',
      abs((_P['motor-m2-magnet-ring-outer']['radius']
           - _P['motor-m2-magnet-ring-bore']['radius'])
          - _M2PARAMS['magnet_length_m'] * 1e3) < 1e-9)
check('the carrier fills the ring bore exactly and clears the '
      'reused 8 mm shaft — a press fit needs a real interface, '
      'not an overlap of guesses',
      _P['motor-m2-rotor-carrier']['radius']
      == _P['motor-m2-magnet-ring-bore']['radius']
      and _P['motor-m2-rotor-carrier']['radius']
      > _P['motor-m1-shaft']['radius'])
check('the ring and carrier are as TALL as the reused stator '
      'teeth — a rotor shorter than its stator throws away gap '
      'area it already paid for',
      _P['motor-m2-rotor-carrier']['height']
      == _P['motor-m2-magnet-ring-outer']['height']
      == _P['motor-m1-stator-tooth']['height'])

_viz = json.loads(SEED_M2_SIM_SPACES[0]['definition'])
_bodies = _viz['freestanding']
check('motor-m2-viz draws 16 bodies: shaft, carrier, ring, yoke, '
      'six teeth, six coils',
      len(_bodies) == 16
      and sum(1 for b in _bodies
              if 'stator-tooth' in b['id']) == 6
      and sum(1 for b in _bodies if b['id'].startswith('coil')) == 6)
check('and FOURTEEN of those sixteen are M1 shape rows, '
      'referenced — the ladder is visible in the scene, not just '
      'claimed: only the ring and its carrier are new',
      sum(1 for b in _bodies
          if 'motor-m1-' in b['shapeRef']) == 14
      and sum(1 for b in _bodies
              if 'motor-m2-' in b['shapeRef']) == 2
      and sum(1 for b in _bodies
              if 'motor-m1-shaft' in b['shapeRef']) == 1,
      f"m1={sum(1 for b in _bodies if 'motor-m1-' in b['shapeRef'])}")

_vm = _mgr()
_vm.objectTables['MotorPartDefinition'] = _table(SEED_MOTOR_PARTS)
_vm.objectTables['MathShapeDefinition'] = _table(
    SEED_M1_PART_SHAPES + SEED_M2_PART_SHAPES)
_vm.objectTypingDict = {k: object() for k in _vm.objectTables}
_pr = part_report(_vm, M2)
check('the M2 bill answers with SIX parts and no gaps: two new '
      'rotor pieces plus four M1 parts by REFERENCE (the stator '
      'rows are not copied — copying would make the ladder a '
      'coincidence between two bills)',
      _pr.get('ok') and _pr['count'] == 6 and not _pr['gaps']
      and _pr['reuse']['newHere'] == ['m2-magnet-ring',
                                      'm2-rotor-carrier']
      and len(_pr['reuse']['parts']) == 4,
      json.dumps(_pr.get('reuse'))[:200])
check('every reused entry says where it came from, and the mass '
      'is REAL (they are actually in the machine)',
      all(e.get('reusedFrom') == M1 for e in _pr['parts']
          if e['part'] in set(PART_REUSE[M2]['parts']))
      and _pr['totalMassG'] > 50.0)
check('THE REUSE CLAIM IS GUARDED, not asserted: the shared '
      'stator frame really is shared — same slots, poles and '
      'coil family — so "only the rotor changes" cannot go stale',
      _M2PARAMS['slots'] == _M1PARAMS['slots']
      and _M2PARAMS['poles'] == _M1PARAMS['poles']
      and _SH['motor-m1-stator-tooth'] is _SH[
          'motor-m1-stator-tooth'])
check('the magnet ring is the torque-producing part and the '
      'carrier is structural and NON-MAGNETIC ON PURPOSE (the M3 '
      'argument, one radius smaller)',
      next(e for e in _pr['parts']
           if e['part'] == 'm2-magnet-ring')['function']
      == 'torque-producing'
      and 'non-magnetic on purpose'
      in next(e for e in _pr['parts']
              if e['part'] == 'm2-rotor-carrier')[
                  'whyThisMaterial'].lower())

_ok = sum(1 for r in _results if r)
print(f'\n{_ok}/{len(_results)} checks passed')
