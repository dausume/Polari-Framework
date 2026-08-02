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

print('== suite: m1-3 scene layers ==')
from motors.clock_scene import (        # noqa: E402
    LAYER_KINDS, clock_scene_payload,
)
from motors.m1_scene import (           # noqa: E402
    M1_ALL_LAYERS, M1_BASE, M1_PART_BODIES, M1_PHASE_COILS,
    M1_VIEW_SCENES, SEED_M1_SCENE_LAYERS,
)
from motors.motor_shapes import (       # noqa: E402
    SEED_M1_SIM_SPACES,
)

_m1_space = next(s for s in SEED_M1_SIM_SPACES
                 if s['name'] == M1_BASE)
_scene_ids = {b['id'] for b in
              json.loads(_m1_space['definition'])['freestanding']}

check('TWO-MODULES-AGREE: the part→body map covers exactly the '
      'M1 part rows (motor_parts) — no orphan, no gap',
      set(M1_PART_BODIES)
      == {p['name'] for p in SEED_MOTOR_PARTS
          if p.get('design_ref') == M1_DESIGN})
check('TWO-MODULES-AGREE: every mapped body id exists in the '
      'motor-m1-viz sim space, and the map covers ALL 19 bodies',
      set(b for bodies in M1_PART_BODIES.values()
          for b in bodies) == _scene_ids
      and len(_scene_ids) == 19)
check('TWO-MODULES-AGREE: the phase→coil map pairs opposite '
      'coils exactly as m1_phase_electrics pairs teeth (k, k+3)',
      set(b for pair in M1_PHASE_COILS.values() for b in pair)
      == set(M1_PART_BODIES['m1-coils'])
      and all(len(pair) == 2
              for pair in M1_PHASE_COILS.values())
      and sorted(M1_PHASE_COILS) == ['0', '1', '2'])
check('phase-replay is a REGISTERED kind (the constructor will '
      'not silently downgrade it)',
      'phase-replay' in LAYER_KINDS
      and all(l['kind'] in LAYER_KINDS
              for l in SEED_M1_SCENE_LAYERS))
check('every M1 layer PINS its design in params — an M0 caller '
      'default can never color M1 bodies from the wrong bill',
      all(json.loads(l['params_json']).get('design') == M1_DESIGN
          for l in SEED_M1_SCENE_LAYERS))
check('every M1 view declares its scene: base motor-m1-viz, all '
      'M1 layers listed, non-empty defaultOn',
      set(M1_VIEW_SCENES) == {v['name'] for v in SEED_M1_VIEWS}
      and all(v['scene_json'] for v in SEED_M1_VIEWS)
      and all(json.loads(v['scene_json'])['base'] == M1_BASE
              and json.loads(v['scene_json'])['layers']
              == M1_ALL_LAYERS
              and json.loads(v['scene_json'])['defaultOn']
              for v in SEED_M1_VIEWS))

vm.objectTables['ClockSceneLayerDefinition'] = _table(
    SEED_M1_SCENE_LAYERS)
vm.objectTypingDict = {k: object() for k in vm.objectTables}
_sc = clock_scene_payload(vm, 'view-m1-sequencing')
_lay = {l['name']: l for l in _sc.get('layers', [])}
check('scene payload assembles: base motor-m1-viz, the sequence '
      'replay layer answers with the phase→coil geometry and is '
      'defaultOn for the sequencing view',
      _sc.get('ok') and _sc['baseScene'] == M1_BASE
      and _lay['layer-m1-sequence-replay'].get('ok')
      and _lay['layer-m1-sequence-replay']['geometry']
      ['phaseCoils'] == M1_PHASE_COILS
      and _lay['layer-m1-sequence-replay']['defaultOn'])
check('material coloring answers from part rows alone: every '
      'M1 body colored, no magnet in the legend (the point of '
      'the rung, visible)',
      _lay['layer-m1-material-coloring'].get('ok')
      and set(_lay['layer-m1-material-coloring']['bodies'])
      == _scene_ids
      and not any('ndfeb' in e['label'].lower()
                  or 'srfe' in e['label'].lower()
                  for e in _lay['layer-m1-material-coloring']
                  ['legend']))
check('a layer the fixture cannot feed refuses WITH its reason, '
      'never a blank canvas',
      all(l.get('refusal')
          for l in _sc.get('layers', []) if not l.get('ok')))

print('== suite: m1-4 composition splice ==')
from composition.composition_seed import (   # noqa: E402
    SEED_FAILURE_MODES, SEED_PART_COMPONENTS,
)
from motors.composition_splice import (      # noqa: E402
    composition_view, interface_specs, promotion_candidates,
)
from motors.m1_composition import (          # noqa: E402
    M1_INTERFACES, SEED_M1_COMPOSITION_NODES,
    SEED_M1_CONSTRUCTION_VARIANTS, SEED_M1_INTERFACES,
    SEED_M1_PART_COMPONENTS, SEED_M1_ROUTING_OPS,
    m1_construction_fork,
)
from motors.m1_scene import SEED_M1_SCENE_LAYERS as _L4  # noqa: E402

_fused = {s['name'] for s in M1_INTERFACES
          if not s['designed_separable']}
_gaps = [s for s in M1_INTERFACES
         if s['retention_scheme'] == 'none']

check('six M1 joints stated; members all real M1 part rows '
      '(two-modules-agree with motor_parts)',
      len(M1_INTERFACES) == 6
      and {m for s in M1_INTERFACES
           for m in (s['member_a'], s['member_b'])}
      <= {p['name'] for p in SEED_MOTOR_PARTS
          if p.get('design_ref') == M1_DESIGN})
check('the TWO designed non-contact gaps: zero DOF removed, '
      'retention none, and the working gap is one of them',
      len(_gaps) == 2
      and all(s['dof_removed'] == [] for s in _gaps)
      and {s['name'] for s in _gaps}
      == {'ifm1-working-gap', 'ifm1-coil-clearance'})
check('every M1 interface is THEORETICAL — made-and-measured '
      'does not leak onto an unbuilt machine',
      all(s.get('realization_level') == 'theoretical'
          and s.get('qualifying_act')
          for s in M1_INTERFACES))

cvw = composition_view(vm, M1_DESIGN)
check('the movement derives part-with-separable-sub-parts and '
      'MATCHES its declaration: mold-fused castings bound, '
      'shaft/coils/gaps separable',
      cvw.get('ok')
      and cvw['level']['derived']
      == 'part-with-separable-sub-parts'
      and cvw['level']['ok']
      and cvw['level']['declared'] == cvw['level']['derived']
      and set(cvw['level']['boundSet']) == _fused
      and len(cvw['level']['separableSet']) == 4)
check('parity holds: every M1 part exposed with its own material '
      'and shape refs (wrap, not port)',
      cvw['parity']['allMaterialsMatch']
      and cvw['parity']['allShapesMatch']
      and cvw['parity']['partCount'] == 6)
m0w = composition_view(vm, 'clock-lavet-m0')
check('M0 REGRESSION: still derives assembly (all five joints '
      'separable) with the made-and-measured default intact',
      m0w.get('ok') and m0w['level']['derived'] == 'assembly')

pc = promotion_candidates(vm, M1_DESIGN)
check('promotion: the winding→tooth joint is THE candidate; the '
      'mold-fused boundaries are listed as ALREADY promoted, '
      'not re-asked',
      pc.get('ok') and pc['promotable'] == ['ifm1-winding-tooth']
      and {a['interface'] for a in pc['alreadyPromoted']}
      == _fused)
check('both gaps are REFUSED candidates because their members '
      'move — the gate working',
      all(any('move relative' in b for b in c['blockers'])
          for c in pc['candidates']
          if c['interface'] in {'ifm1-working-gap',
                                'ifm1-coil-clearance'}))

_pc_all = {s['name']: types.SimpleNamespace(**s)
           for s in SEED_PART_COMPONENTS + SEED_M1_PART_COMPONENTS}
vm.objectTables['PartComponentDefinition'] = _pc_all
vm.objectTables['CompositionNode'] = _table(
    SEED_M1_COMPOSITION_NODES)
vm.objectTables['InterfaceDefinition'] = _table(SEED_M1_INTERFACES)
vm.objectTables['ConstructionVariantDefinition'] = _table(
    SEED_M1_CONSTRUCTION_VARIANTS)
vm.objectTables['FailureModeDefinition'] = _table(
    SEED_FAILURE_MODES)
vm.objectTypingDict = {k: object() for k in vm.objectTables}

fork = m1_construction_fork(vm)
_lv = {v['variant']: v['level'] for v in fork.get('variants', [])}
check('the FORK: both constructions of ONE functional part, '
      'levels DERIVED live — bobbin=assembly, promoted=part, '
      'both matching their declarations',
      fork.get('ok')
      and _lv['cv-m1-tooth-bobbin']['derived'] == 'assembly'
      and _lv['cv-m1-tooth-promoted']['derived'] == 'part'
      and all(l.get('ok') and l['declared'] == l['derived']
              for l in _lv.values())
      and 'SIX coils' in fork['batchFact'])
_cure = next(o for o in SEED_M1_ROUTING_OPS
             if o['name'] == 'op-m1tp-cure')
check('the PROMOTE op is consistent: consumes exactly the bobbin '
      'joints, fuses exactly the promoted one (two modules, one '
      'fact)',
      _cure['kind'] == 'promote'
      and set(json.loads(_cure['consumes_interface_refs_json']))
      == {i['name'] for i in SEED_M1_INTERFACES
          if i['node_ref'] == 'm1-tooth-bobbin'}
      and json.loads(_cure['fused_interface_refs_json'])
      == [i['name'] for i in SEED_M1_INTERFACES
          if i['node_ref'] == 'm1-tooth-promoted'])

vm.objectTables['ClockSceneLayerDefinition'] = _table(_L4)
vm.objectTypingDict = {k: object() for k in vm.objectTables}
_mech = clock_scene_payload(vm, 'view-m1-mechanical')
_mk = next(l for l in _mech['layers']
           if l['name'] == 'layer-m1-interface-markers')
check('the markers layer shows all SIX M1 joints on the M1 '
      'scene (interface set follows the layer\'s pinned design)',
      _mk.get('ok') and len(_mk['markers']) == 6
      and _mk['defaultOn'])

failed = _results.count(False)
print(f'\n{len(_results) - failed}/{len(_results)} checks passed')
raise SystemExit(1 if failed else 0)
