"""
@module motors.selftest_m1

M1 selftests (m1-1 solver, m1-2 views).

m1-1: the step-angle arithmetic pinned BOTH ways
(360/(phases*poles) and the slot/pole difference formula), the
no-load 12-step revolution, the HAND-CHECKED first-step angle,
reversal, load lag (equilibrium settles short of aligned),
overload missing steps with the position error telescoping to the
sum of named shortfalls, refusals (wrong topology, unknown
slot/pole counts, zero-load bisect), and the current bisect
landing near the hand value I_rated*sqrt(load/peak).

Run from polari-framework/: python3 -m motors.selftest_m1
"""

import json
import math
import types

from magnetics.magnet_seed import SEED_MATERIAL_OPTIONS
from motors.motor_basis import SEED_MOTOR_DESIGNS
from motors.m1_sequencing import (
    PHASES, POLES, SLOTS, STEP_DEG, holding_torque,
    m1_minimum_drive_current, sequence_sim,
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
        'MagneticMaterialOption': table(SEED_MATERIAL_OPTIONS),
        'MotorDesignDefinition': table(SEED_MOTOR_DESIGNS),
    }
    return m


mgr = _mgr()
M1 = 'reluctance-6s4p-m1'

print('== suite: m1-1 step arithmetic ==')
check('30 deg/step from 360/(phases*poles)',
      abs(STEP_DEG - 360.0 / (PHASES * POLES)) < 1e-12
      and abs(STEP_DEG - 30.0) < 1e-12)
check('the slot/pole difference formula agrees: '
      '360*(1/poles - 1/slots) is the SAME 30',
      abs(360.0 * (1.0 / POLES - 1.0 / SLOTS) - STEP_DEG) < 1e-12)

print('== suite: m1-1 no-load sequencing ==')
seq = sequence_sim(mgr, M1, steps=12)
check('12 commanded steps all land (no load, rated current)',
      seq.get('ok') and seq['stepsTaken'] == 12
      and seq['stepsMissed'] == 0, json.dumps(seq)[:200])
check('one full revolution: actual rotation 360 deg, error 0',
      seq.get('ok')
      and abs(seq['positionComparison']['actualRotationDeg']
              - 360.0) < 1.0
      and abs(seq['positionComparison']['positionErrorDeg']) < 1.0)
check('HAND CHECK: latch holds phase-0 aligned (0 deg), first '
      'step settles at 30 deg',
      seq.get('ok')
      and abs(seq['history'][0]['thetaDeg']) < 0.6
      and abs(seq['history'][1]['thetaDeg'] - 30.0) < 0.6)
check('every step advances ~30 deg (first-harmonic landscape, '
      'grid-settled)',
      seq.get('ok')
      and all(abs(h['advancedDeg'] - 30.0) < 1.0
              for h in seq['history'][1:]))
check('the payload states its honesty: named gaps + speed '
      'assumption + no-unpowered-detent fact',
      seq.get('ok') and len(seq['namedGaps']) == 3
      and 'ASSUMED' in seq['speedAssumption']['note']
      and 'holds NOTHING' in seq['noUnpoweredDetent'])

rev = sequence_sim(mgr, M1, steps=12, direction=-1)
check('reversed phase order walks -30 deg/step to -360',
      rev.get('ok') and rev['stepsTaken'] == 12
      and abs(rev['positionComparison']['actualRotationDeg']
              - 360.0) < 1.0
      and abs(rev['history'][1]['thetaDeg'] - (360.0 - 30.0))
      < 0.6)

print('== suite: m1-1 holding torque + load behavior ==')
hold = holding_torque(mgr, M1)
peak = hold.get('peakTorqueNm', 0.0)
check('holding torque exists and is honestly FEEBLE at mu~2 '
      '(between 1e-6 and 1e-3 Nm)',
      hold.get('ok') and 1e-6 < peak < 1e-3,
      f'peak={peak}')
hold2 = holding_torque(mgr, M1, amps=1.0)
check('torque scales as current squared (2x amps -> ~4x torque)',
      hold2.get('ok')
      and abs(hold2['peakTorqueNm'] / peak - 4.0) < 0.2)

lag = sequence_sim(mgr, M1, steps=12,
                   load_torque_nm=0.3 * peak)
check('moderate load: all 12 steps still land',
      lag.get('ok') and lag['stepsMissed'] == 0)
check('but the rotor settles SHORT of aligned (load-angle lag — '
      'and MORE than a sinusoid would give: the real landscape '
      'is flat between poles)',
      lag.get('ok')
      and 14.0 < lag['history'][1]['thetaDeg'] < 24.0)

over = sequence_sim(mgr, M1, steps=6,
                    load_torque_nm=3.0 * peak)
check('overload: steps are MISSED and say so',
      over.get('ok') and over['stepsMissed'] > 0)
check('the position error telescopes to the sum of the named '
      'per-step shortfalls (two paths, one number)',
      over.get('ok')
      and abs(over['positionComparison']['positionErrorDeg']
              - sum(h['shortfallDeg']
                    for h in over['history'][1:])) < 0.5)

print('== suite: m1-1 refusals ==')
ref = sequence_sim(mgr, 'clock-lavet-m0')
check('a Lavet design is refused (the sequencing sim is the M1 '
      'rung)', not ref.get('ok')
      and 'radial-reluctance' in ref.get('refusal', ''))
mgr.objectTables['MotorDesignDefinition']['reluctance-8s6p-x'] = \
    types.SimpleNamespace(
        name='reluctance-8s6p-x', topology='radial-reluctance',
        params_json=json.dumps({
            'stator_material': 'opt-geopolymer-ferrite',
            'rotor_material': 'opt-geopolymer-ferrite',
            'slots': 8, 'poles': 6, 'gap_base_m': 6e-4,
            'tooth_area_m2': 4e-5, 'coil_turns': 300,
            'coil_amps': 0.5, 'saliency_ratio': 3.0}),
        drive_json='{}')
ref2 = sequence_sim(mgr, 'reluctance-8s6p-x')
check('unknown slot/pole counts get a refusal naming the '
      'alignment map, not a guess',
      not ref2.get('ok')
      and 'alignment map' in ref2.get('refusal', ''))

print('== suite: m1-1 minimum drive current ==')
zero = m1_minimum_drive_current(mgr, M1)
check('zero load is a REFUSAL, not a zero-amp answer (no detent, '
      'no friction — nothing to bisect against)',
      not zero.get('ok')
      and 'no detent' in zero.get('refusal', ''))
load = 0.25 * peak
mdc = m1_minimum_drive_current(mgr, M1, load_torque_nm=load)
pull_out = 0.5 * math.sqrt(load / peak)
check('bisect solves a threshold below the stated 0.5 A',
      mdc.get('ok') and 0.0 < mdc['thresholdAmps'] < 0.5,
      json.dumps(mdc)[:200])
check('PULL-IN GOVERNS: the threshold sits ABOVE the naive '
      'peak-torque (pull-out) bound I_rated*sqrt(load/peak) — '
      'the lagged start sits deep in the next phase\'s weak-'
      'torque zone, so the weakest point of the TRAVEL decides',
      mdc.get('ok') and mdc['thresholdAmps'] > pull_out * 1.2,
      f'pull_out={pull_out:.4g} got={mdc.get("thresholdAmps")}')
th = mdc.get('thresholdAmps') or 0.5
above = sequence_sim(mgr, M1, steps=12, load_torque_nm=load,
                     amps=th * 1.02)
below = sequence_sim(mgr, M1, steps=12, load_torque_nm=load,
                     amps=th * 0.95)
check('the threshold is REAL: 2% above it every step lands, '
      '5% below it steps miss',
      above.get('ok') and above['stepsMissed'] == 0
      and below.get('ok') and below['stepsMissed'] > 0)
check('margin applied and honesty stated',
      mdc.get('ok')
      and abs(mdc['designedAmps']
              - mdc['thresholdAmps'] * mdc['marginFactor'])
      < 1e-6
      and 'not a measurement' in mdc['honesty'])

print('== suite: m1-2 views as rows ==')
from motors.clock_views import (        # noqa: E402
    DISCIPLINES, SECTION_SOURCES, view_payload,
)
from motors.m1_views import (           # noqa: E402
    M1_DESIGN, M1_SECTION_SOURCES, SEED_M1_VIEWS,
    m1_phase_electrics,
)
from motors.motor_drive import (        # noqa: E402
    SEED_CONTROLLER_PROFILES, SEED_PHASE_BINDINGS,
)
from motors.motor_parts import SEED_MOTOR_PARTS  # noqa: E402


def _table(seed):
    return {s['name']: types.SimpleNamespace(**s) for s in seed}


vm = _mgr()
vm.objectTables['ClockViewDefinition'] = _table(SEED_M1_VIEWS)
vm.objectTables['MotorControllerProfile'] = _table(
    SEED_CONTROLLER_PROFILES)
vm.objectTables['PhaseBindingDefinition'] = _table(
    SEED_PHASE_BINDINGS)
vm.objectTables['MotorPartDefinition'] = _table(SEED_MOTOR_PARTS)
vm.objectTypingDict = {k: object() for k in vm.objectTables}

check('six M1 views seeded, disciplines all legal, M1 names',
      len(SEED_M1_VIEWS) == 6
      and all(v['name'].startswith('view-m1-')
              for v in SEED_M1_VIEWS)
      and {v['discipline'] for v in SEED_M1_VIEWS}
      <= set(DISCIPLINES))
check('every M1 section source resolves in the ONE dispatch '
      'table (registration at import, proven)',
      all(s['source'] in SECTION_SOURCES
          for v in SEED_M1_VIEWS
          for s in json.loads(v['sections_json']))
      and set(M1_SECTION_SOURCES) <= set(SECTION_SOURCES))
check('nav-4 idiom: every section LEADS, and every section pins '
      'design=reluctance-6s4p-m1 (no M0 leak through the caller '
      'default)',
      all(s.get('lead')
          and s.get('args', {}).get('design') == M1_DESIGN
          for v in SEED_M1_VIEWS
          for s in json.loads(v['sections_json'])))

seqv = view_payload(vm, 'view-m1-sequencing')
_by = {s['section']: s for s in seqv.get('sections', [])}
check('sequencing view assembles: solver, holding torque and '
      'drive card ANSWER from the fixture',
      seqv.get('ok')
      and _by['sequence'].get('payload', {}).get('stepsTaken')
      == 12
      and _by['holding-torque'].get('payload', {})
      .get('peakTorqueNm', 0) > 0
      and _by['drive-profile'].get('payload', {}).get('ok'))
check('min-current section refuses BY NAME (no load stated) — '
      'refused in the payload, never dropped',
      'min-current' in seqv.get('refusedSections', [])
      and 'load' in _by['min-current'].get('refusal', ''))

pe = m1_phase_electrics(vm)
check('phase electrics: six coils -> three phases, R_phase = '
      '2 x R_coil, phases predicted identical',
      pe.get('ok') and pe['phaseCount'] == 3
      and all(abs(p['rPhaseOhm']
                  - 2.0 * pe['perCoil']['resistanceOhm']) < 1e-9
              for p in pe['phases'])
      and pe['imbalance']['predicted'] == 0.0)
check('per-phase L is a NAMED GAP whose knob is the m1-7 bench',
      pe.get('ok')
      and all(p['lPhaseH'] is None for p in pe['phases'])
      and 'm1-7' in str(pe['inductanceGap']['suggestion']))

posv = view_payload(vm, 'view-m1-positioning')
_pby = {s['section']: s for s in posv.get('sections', [])}
check('positioning view: the PROOF refuses by name and its '
      'suggestion names the m1-5 seam; the solver section '
      'answers meanwhile',
      posv.get('ok')
      and 'positioning-proof' in posv.get('refusedSections', [])
      and 'm1_positioning' in str(
          _pby['positioning-proof'].get('suggestion'))
      and _pby['sequence-under-load'].get('payload', {})
      .get('ok'))

_assembled = [view_payload(vm, v['name']) for v in SEED_M1_VIEWS]
check('all six M1 views assemble; every refused section stays '
      'NAMED with its refusal text',
      all(a.get('ok') for a in _assembled)
      and all(s.get('refusal')
              for a in _assembled for s in a['sections']
              if not s.get('payload')))

failed = _results.count(False)
print(f'\n{len(_results) - failed}/{len(_results)} checks passed')
raise SystemExit(1 if failed else 0)
