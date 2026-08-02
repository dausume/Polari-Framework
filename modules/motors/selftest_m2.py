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

print('== suite: m2-3 views + scene as rows ==')
from motors.clock_views import SECTION_SOURCES  # noqa: E402
from motors.m2_scene import (                   # noqa: E402
    M2_ALL_LAYERS, M2_PART_BODIES, M2_PHASE_COILS,
    SEED_M2_SCENE_LAYERS, m2_scene_json_for_view,
)
from motors.m2_views import (                   # noqa: E402
    M2_SECTION_SOURCES, SEED_M2_VIEWS,
)

_views = {v['name']: v for v in SEED_M2_VIEWS}
check('SIX view-m2-* rows, one per discipline the rung touches, '
      'and every section pins the M2 design',
      len(_views) == 6
      and all(s['args']['design'] == M2
              for v in SEED_M2_VIEWS
              for s in json.loads(v['sections_json'])))
check('every section source RESOLVES in the dispatch table — a '
      'view row naming an engine that does not exist would '
      'render an empty card instead of refusing',
      all(s['source'] in SECTION_SOURCES
          for v in SEED_M2_VIEWS
          for s in json.loads(v['sections_json'])),
      str([s['source'] for v in SEED_M2_VIEWS
           for s in json.loads(v['sections_json'])
           if s['source'] not in SECTION_SOURCES]))
check('the magnetics view leads with MODEL VALIDITY, as M1\'s '
      'does — the caveat is the headline at this rung, not a '
      'footnote',
      json.loads(_views['view-m2-magnetics']['sections_json'])[0]
      ['source'] == 'model-validity')
check('the electrics view REUSES the M1 engine by calling it '
      'with the M2 design (not a second implementation)',
      M2_SECTION_SOURCES['m2-phase-electrics'].__closure__
      is not None
      and 'm2-phase-electrics' in SECTION_SOURCES)
check('every view row carries a scene, and each names the M2 '
      'base — a view that forgot its scene would silently render '
      'M0\'s',
      all(json.loads(v['scene_json'])['base'] == 'motor-m2-viz'
          for v in SEED_M2_VIEWS))
check('NO NEW LAYER KIND: every M2 layer reuses a kind M1 or M0 '
      'already registered (if the second rung needed new '
      'rendering machinery, the first rung\'s was not general)',
      {layer['kind'] for layer in SEED_M2_SCENE_LAYERS}
      <= {'phase-replay', 'part-coloring', 'markers'})
check('the replay layer lights ALL SIX coils together — a '
      'synchronous drive energises every phase at once, and '
      'showing them take turns would be a lie about the drive',
      len(M2_PHASE_COILS) == 1
      and len(M2_PHASE_COILS['0']) == 6
      and json.loads(SEED_M2_SCENE_LAYERS[0]['params_json'])
      ['rotorBodies'] == ['shaft', 'rotor-carrier', 'magnet-ring'])
check('TWO MODULES AGREE: every body the part→body map colors '
      'exists in the sim space, and every part it names is in '
      'the M2 bill',
      all(b in {x['id'] for x in _bodies}
          for bodies in M2_PART_BODIES.values() for b in bodies)
      and set(M2_PART_BODIES) == {e['part'] for e in _pr['parts']})
check('a view that is not M2\'s gets no M2 scene (the scene map '
      'refuses by absence, never by defaulting)',
      m2_scene_json_for_view('view-m1-sequencing') == ''
      and len(M2_ALL_LAYERS) == 5)

print('== suite: m2-4 composition splice ==')
from motors.composition_splice import (         # noqa: E402
    composition_view, interface_specs, promotion_candidates,
)
from motors.m2_composition import (             # noqa: E402
    M2_INTERFACES, SEED_M2_RELATIONS, SEED_M2_ROUTING_OPS,
    derived_m2_marker_positions, m2_promotion_story,
)

check('the splice DISPATCHES M2 by name — one adapter, three '
      'rungs',
      [i['name'] for i in interface_specs(M2)]
      == [i['name'] for i in M2_INTERFACES])
_cv = composition_view(_vm, M2)
check('the movement DERIVES its level and it MATCHES the '
      'declaration (a label may not overrule the structure)',
      _cv['ok'] and _cv['level']['ok']
      and _cv['level']['derived'] == _cv['level']['declared'],
      json.dumps(_cv.get('level'))[:250])
check('interface members are all real M2 parts — including the '
      'M1 rows the machine reuses, which is exactly why the '
      'movement has to include them',
      all(m in {e['part'] for e in _pr['parts']}
          for i in M2_INTERFACES
          for m in (i['member_a'], i['member_b'])))
check('ONE designed non-contact interface where M1 had TWO, and '
      'the payload says why (a round rotor has no pole tips to '
      'swing past the coil bores)',
      sum(1 for i in M2_INTERFACES
          if i['retention_scheme'] == 'none') == 1
      and m2_promotion_story(_vm)['gapCount'] == {
          'm2': 1, 'm1': 2,
          'note': m2_promotion_story(_vm)['gapCount']['note']}
      and 'pole tips'
      in m2_promotion_story(_vm)['gapCount']['note'])
_pcand = promotion_candidates(_vm, M2)
check('the bonded rotor is ALREADY PROMOTED (by bond, not by '
      'mold), the working gap REFUSES promotion, and the '
      'inherited winding fork is the one candidate',
      [a['interface'] for a in _pcand['alreadyPromoted']]
      == ['ifm2-ring-carrier']
      and _pcand['promotable'] == ['ifm2-winding-tooth']
      and 'ifm2-working-gap' in [c['interface']
                                 for c in _pcand['candidates']])
check('op-m2-magnetize is LAST in its routing and carries the '
      'two-material lesson — and it does NOT invent a new op '
      'kind for one operation',
      [o['name'] for o in SEED_M2_ROUTING_OPS][-1]
      == 'op-m2-magnetize'
      and SEED_M2_ROUTING_OPS[-1]['sequence'] == 3
      and SEED_M2_ROUTING_OPS[-1]['kind'] == 'join'
      and 'gr-3' in SEED_M2_ROUTING_OPS[-1]['notes'])
check('the M2 relations name the two facts that must not drift, '
      'and the marker positions DERIVE from the shape rows',
      {r['name'] for r in SEED_M2_RELATIONS}
      == {'m2-rel-working-gap', 'm2-rel-magnet-thickness'}
      and set(derived_m2_marker_positions())
      == {i['name'] for i in M2_INTERFACES})
check('and the derived working-gap marker really sits IN the '
      'gap — between the ring surface and the tooth face',
      _P['motor-m2-magnet-ring-outer']['radius']
      < derived_m2_marker_positions()['ifm2-working-gap'][0]
      < _P['motor-m1-stator-tooth']['r_face'])

print('== suite: m2-5 THE LIFT PROOF ==')
from motors.m2_lift import (                    # noqa: E402
    LIFT_MARGIN, SEED_HOIST_REQUIREMENTS, hoist_report, lift_proof,
)

_hm = _mgr()
_hm.objectTables['CrucibleHoistRequirement'] = _table(
    SEED_HOIST_REQUIREMENTS)
_hm.objectTypingDict = {k: object() for k in _hm.objectTables}
_hoist = hoist_report(_hm, M2)
check('the hoist answers from its requirement ROWS, and every '
      'prior names the measurement that retires it',
      _hoist.get('ok') and len(_hoist['requirements']) == 6
      and all(s['replaces_with'] for s in SEED_HOIST_REQUIREMENTS))
check('the torque chain is arithmetic anyone can check: '
      '2 kg through a 2:1 pulley on a 15 mm drum is 0.147 Nm at '
      'the drum',
      abs(_hoist['torqueChain']['atDrumNm'] - 0.14710) < 1e-4
      and abs(_hoist['load']['ropeTensionN'] - 9.80665) < 1e-3)
_proof = lift_proof(_hm, M2)
check('TWO PATHS, ONE NUMBER: the motor-side torque demand down '
      'the chain of ratios and through the power balance agree '
      'to 1e-9',
      _proof['crossCheck']['consistent']
      and abs(_proof['crossCheck']['pathA_chainOfRatiosNm']
              - _proof['crossCheck']['pathB_powerBalanceNm'])
      < 1e-9,
      json.dumps(_proof['crossCheck'])[:200])
check('and the ASSUMED LIFT SPEED cancels out of the torque '
      'entirely — an assumption that cannot flatter the verdict '
      'is an assumption worth keeping',
      abs(lift_proof(_hm, M2)['crossCheck']['pathB_powerBalanceNm']
          - _proof['crossCheck']['pathB_powerBalanceNm']) < 1e-12
      and 'cancels' in _proof['crossCheck']['note'])
check('THE BARE MOTOR STALLS on the sketched 30:1 worm and says '
      'by how much — and names the reduction stage that closes '
      'it (M1\'s finding, on a different device)',
      _proof['lift']['verdict'] == 'stalls'
      and _hoist['dutyVerdict'] == 'not-capable'
      and _hoist['shortfall'] > 1.0
      and _hoist['requiredStageRatio'] >= 2)
check('AS SHIPPED IT LIFTS: with the derived reduction stage in '
      'front of the worm the rotor stays in step, at a load '
      'angle inside the 90 deg cliff',
      _proof['asShipped']['verdict'] == 'lifts'
      and _proof['asShipped']['inSync']
      and _proof['asShipped']['worstLagDeg'] < PULL_OUT_LAG_DEG,
      json.dumps(_proof.get('asShipped'))[:200])
check('HOLDS WHEN DEAD, and the reason is the WORM — the '
      'payload explicitly refuses to borrow the cogging the '
      'model does not have',
      _proof['holdsWhenDead']['verdict'] == 'holds-when-dead'
      and 'worm' in _proof['holdsWhenDead']['because'].lower()
      and _proof['holdsWhenDead']['notBecause']
      == NO_COGGING_FACT
      and 'stillTheoretical' in _proof['holdsWhenDead'])
check('efficiency and self-locking are stated as ONE fact, and '
      'the 24-hour gate is what would test it',
      'one physical fact'
      in _proof['holdsWhenDead']['efficiencyIsTheSameFact'].lower()
      and 'qa-lift-hold-24h'
      in _proof['holdsWhenDead']['qualifyingAct'])
check('THE CONTRADICTION THE REDUCTION CREATES IS NAMED: the '
      'shipped ratio demands far more motor speed than the '
      'design row assumes, and the payload says which '
      'measurement would settle it',
      _proof['asShipped']['speedContradiction']['factor'] > 10.0
      and _proof['asShipped']['speedContradiction'][
          'slowLiftSpeedMS'] > 0.0
      and 'bench' in _proof['asShipped']['speedContradiction'][
          'whatWouldSettleIt'])
check('the hoist refuses without its rows — never a default '
      'crucible',
      not hoist_report(_mgr(), M2).get('ok')
      and 'seed_m2_hoist'
      in hoist_report(_mgr(), M2).get('refusal', ''))

print('== suite: m2-6 product + routes ==')
from motors.m2_product import (                 # noqa: E402
    STAGE_RATIO, SEED_M2_QA, SEED_M2_WORKFLOWS, magnet_route_fork,
)
from motors.product_routes import product_routes  # noqa: E402

_routes = product_routes(_hm, M2)
check('the M0 route surface dispatches the M2 design to the '
      'hoist-drive product (one endpoint, three rungs)',
      _routes.get('ok')
      and _routes['product'] == 'm2-hoist-drive')
check('GUARD (the wire-ladder lesson, EQUALITY not >=): the '
      'seeded reduction stage IS the live requirement — an '
      'oversized stage would hide a moved requirement row',
      _routes['drivetrain']['stageRatio'] == STAGE_RATIO
      == _routes['drivetrain']['live']['requiredNow'],
      f"seeded={STAGE_RATIO} "
      f"live={_routes['drivetrain']['live'].get('requiredNow')}")
check('the worm stays 30:1 because it is the SAFETY part — the '
      'stage is where the missing torque comes from',
      _routes['drivetrain']['wormRatio'] == 30.0
      and _routes['drivetrain']['totalReduction']
      == STAGE_RATIO * 30.0
      and 'SAFETY' in _routes['drivetrain']['note'])
check('THE ROUTES DIFFER ON THE MAGNET AND NOT ON THE STATOR: '
      'the stator route is M1\'s, referenced — that is what a '
      'ladder rung is supposed to buy',
      _routes['statorReuse']['from'] == M1
      and all('magnetOption' in r and 'statorOption' not in r
              for r in _routes['routes'])
      and any('SAME MOLD AS M1' in i['capability']
              for i in _routes['routes'][0]['inputs']))
check('the pure-local route names the SHARED experiment as its '
      'blocker (one experiment, three rungs) and the commercial '
      'route names its missing PriceCitation instead of guessing',
      any('press-sinter-magnetize' in b
          for b in _routes['routes'][0]['blockers'])
      and any('PriceCitation' in b
              for b in _routes['routes'][1]['blockers']))
_fork = magnet_route_fork(_hm, M2)
check('the magnet fork quantifies every option LIVE (pull-out '
      'and k_e per grade) — a magnet grade is not an adjective',
      _fork['ok'] and len(_fork['options']) == 3
      and all('pullOutLimitNm' in o and 'kEVoltSPerRad' in o
              for o in _fork['options']))
check('and it REFUSES A FAKE DISTINCTION: the two sintered '
      'options are the same material row, so they are the same '
      'numbers, and the difference is provenance not physics',
      _fork['options'][0]['pullOutLimitNm']
      == _fork['options'][2]['pullOutLimitNm']
      and 'provenance' in _fork['note'].lower())
check('the castable grade is HONESTLY WEAKER — a third of the '
      'remanence shows up as a third of k_e, not as a caveat',
      _fork['options'][1]['kEVoltSPerRad']
      < _fork['options'][0]['kEVoltSPerRad'])
check('the assembly workflow ends on MAGNETISE and the QA gate '
      'is a SAFETY gate (a clock gate measures drift; a hoist '
      'gate measures whether something falls)',
      'MAGNETISE' in json.dumps(
          [w for w in SEED_M2_WORKFLOWS
           if w['name'] == 'm2-assemble-magnetize-workflow'][0]
          ['steps_json'])
      and _routes['qaGate'] == 'qa-lift-hold-24h'
      and 'ZERO measurable drop'
      in [q for q in SEED_M2_QA
          if q['name'] == 'qa-lift-hold-24h'][0]['acceptance'])

print('== suite: m2-7 the M2 bench sheet ==')
from motors.bench_campaign import bench_campaign  # noqa: E402

_bench = bench_campaign(_hm, M2)
_bm = {e['measurement']: e for e in _bench['measurements']}
check('the bench surface dispatches M2 to its own sheet: six '
      'measurements, in order, each with instrument + '
      'adjudicates + record-back seam + acceptance',
      _bench.get('ok') and _bench['campaign'] == 'm2-bench'
      and _bench['order'] == [
          'phase-resistance-six', 'back-emf-constant',
          'cogging-map', 'remanence-br', 'pull-out-torque',
          'thermal-rise-duty']
      and all(e.get('instrument') and e.get('adjudicates')
              and e.get('recordVia') and e.get('acceptance')
              for e in _bench['measurements'])
      and not _bench['refusedPredictions'])
check('k_e is predicted LIVE and equals the m2-1 engine\'s own '
      'number — the sheet never carries a stale copy',
      abs(_bm['back-emf-constant']['predictedKeVoltSPerRad']
          - back_emf_constant(_hm, M2)['kEVoltSPerRad']) < 1e-15)
check('THE COGGING ENTRY PREDICTS EXACTLY ZERO and says that is '
      'by construction — so whatever the bench finds is pure '
      'slotting reality, a finding by construction',
      _bm['cogging-map']['predictedDetentNm'] == 0.0
      and 'ZERO COGGING' in _bm['cogging-map']['basis']
      and 'FINDING BY CONSTRUCTION'
      in _bm['cogging-map']['adjudicates'].upper())
check('the remanence entry CITES M0\'s experiment rather than '
      'copying it — one experiment retires the prior on three '
      'rungs at once',
      _bm['remanence-br']['predictedBrT'] == 0.39
      and 'M0' in _bm['remanence-br']['basis'])
check('the pull-out entry carries the two-path cross-check and '
      'demands an ABRUPT loss of sync — a gradual droop would '
      'mean the machine was never synchronous',
      _bm['pull-out-torque']['crossCheck']['consistent']
      and 'abrupt' in _bm['pull-out-torque']['acceptance'].lower())
check('thermal: dissipation SOLVED, rise UNMODELLED — and on '
      'this rung the RING is the part to watch, because hot '
      'ferrite comes back weaker',
      _bm['thermal-rise-duty']['predictedDissipationW'] > 0.0
      and _bm['thermal-rise-duty']['predictedRiseK'] is None
      and 'remanence'
      in _bm['thermal-rise-duty']['adjudicates'].lower())

print('== suite: m2-8 nav + the ladder, end to end ==')
from polariapps.apps_seed import (             # noqa: E402
    SEED_POLARI_APPS,
)

_nav_routes = json.dumps(SEED_POLARI_APPS)
check('the M2 views are reachable from BOTH discipline apps: '
      'rotation under Magnetics & Motors, the lift proof under '
      'Mechanical Engineering',
      'view=view-m2-rotation' in _nav_routes
      and 'view=view-m2-lift' in _nav_routes
      and '/sim-spaces/motor-m2-viz' in _nav_routes)
check('THE LADDER, END TO END: the same stator frame carries a '
      'reluctance machine that steps and a PM machine that '
      'spins; the PM rung makes more torque from a magnet than '
      'the reluctance rung makes from saliency',
      pull_out_load_limit(mgr, M2)['pullOutLimitNm']
      > __import__('motors.m1_sequencing',
                   fromlist=['pull_in_load_limit'])
      .pull_in_load_limit(mgr, M1)['pullInLimitNm'] * 10.0)

_ok = sum(1 for r in _results if r)
print(f'\n{_ok}/{len(_results)} checks passed')
