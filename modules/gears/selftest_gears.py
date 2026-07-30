"""
@module gears.selftest_gears

gr-1 selftests. Everything asserted here is HAND-COMPUTED first:

  two-stage-spur-demo: 12t -> 36t (3:1), then 12t -> 48t (4:1).
    total ratio      = 3 x 4 = 12
    output speed     = 600 rpm / 12 = 50 rpm
    TWO external meshes reverse => output turns the SAME way as
      the input (sign +), which is the direction bug this suite
      exists to catch
    total efficiency = 0.975^2 = 0.950625
    output torque    = 0.01 Nm x 12 x 0.950625 = 0.11407500 Nm
    centre distance stage 1 = 1.0 x (12 + 36) / 2 = 24.0 mm

  clock-train-m0: 8t -> 240t (30:1), 10t -> 600t (60:1).
    rotor 30 rpm -> seconds shaft exactly 1 rpm (the seconds hand)
    -> minute shaft 1/60 rpm = ONE TURN PER HOUR. That is the
    acceptance arithmetic for gr-5: the clock is the instrument.

Run from polari-framework/:  PYTHONPATH=.:modules python3 -m
gears.selftest_gears
"""

import types

from gears.gear_kinematics import (
    solve_train, train_catalog, type_catalog,
)
from gears.gear_seed import (
    SEED_GEAR_MESHES, SEED_GEAR_TRAINS, SEED_GEAR_TYPES,
    SEED_GEARS, SEED_SHAFT_NODES,
)

PASS = '\033[92mPASS\033[0m'
FAIL = '\033[91mFAIL\033[0m'
_results = []


def check(label, cond, extra=''):
    _results.append(bool(cond))
    print(f'{PASS if cond else FAIL}: {label}'
          + (f'  [{extra}]' if extra and not cond else ''))


def _mgr():
    def table(seed):
        return {s['name']: types.SimpleNamespace(**s) for s in seed}
    return types.SimpleNamespace(objectTables={
        'GearTypeDefinition': table(SEED_GEAR_TYPES),
        'GearTrainDefinition': table(SEED_GEAR_TRAINS),
        'GearDefinition': table(SEED_GEARS),
        'GearMeshDefinition': table(SEED_GEAR_MESHES),
        'ShaftNodeDefinition': table(SEED_SHAFT_NODES),
        'GearVerificationRun': {},
    })


mgr = _mgr()

print('== suite: the type taxonomy is DATA ==')
cat = type_catalog(mgr)
by_type = {t['name']: t for t in cat['types']}
check('eight gear types seeded', cat['count'] == 8,
      extra=str(cat['count']))
check('every type states BOTH ends of its efficiency band (no '
      'quietly-flattering midpoint)',
      all(t['efficiencyPrior'][0] is not None
          and t['efficiencyPrior'][1] is not None
          and t['efficiencyPrior'][0] <= t['efficiencyPrior'][1]
          for t in cat['types']))
check('the worm band is WIDE on purpose (0.30-0.90) — that spread '
      'is what decides whether a worm design is sane',
      by_type['worm']['efficiencyPrior'] == [0.30, 0.90])
check('internal (ring) meshes do NOT reverse direction; spur does',
      by_type['internal']['reversesDirection'] is False
      and by_type['spur']['reversesDirection'] is True)
check('worm can self-lock, spur cannot — a TYPE capability, never '
      'a per-design claim',
      by_type['worm']['canSelfLock'] is True
      and by_type['spur']['canSelfLock'] is False)
check('every type says how it would be MADE in our stack',
      all(t['makeabilityNote'] for t in cat['types']))
check('geometry gate honest: only spur has a generator; the rest '
      'simulate but refuse to draw',
      by_type['spur']['geometryGenerator'] == 'involute-spur'
      and by_type['planetary']['geometryGenerator'] is None
      and 'NOT built' in by_type['planetary']['geometryNote'])
check('chainability is explicit: spur/worm chain in gr-1, '
      'planetary and cycloidal do NOT (their algebra is gr-6)',
      by_type['spur']['chainable'] and by_type['worm']['chainable']
      and not by_type['planetary']['chainable']
      and not by_type['cycloidal']['chainable'])

print('== suite: the two-stage reduction (hand-computed) ==')
out = solve_train(mgr, 'two-stage-spur-demo')
check('solve ok', out.get('ok'), extra=str(out.get('refusal')))
check('total ratio is exactly 12 (3:1 x 4:1 — the compound shaft '
      'is what multiplies them)',
      abs(out['totalRatio'] - 12.0) < 1e-9,
      extra=str(out.get('totalRatio')))
check('output speed 600/12 = 50 rpm, POSITIVE: two external '
      'reversals cancel, so the output turns the same way as the '
      'input',
      abs(out['outputSpeedRpm'] - 50.0) < 1e-9,
      extra=str(out.get('outputSpeedRpm')))
check('total efficiency = 0.975^2 = 0.950625',
      abs(out['totalEfficiency'] - 0.950625) < 1e-9,
      extra=str(out.get('totalEfficiency')))
check('output torque = 0.01 x 12 x 0.950625 = 0.1140750 Nm',
      abs(out['outputTorqueNm'] - 0.11407500) < 1e-9,
      extra=str(out.get('outputTorqueNm')))
check('POWER CONSERVED: in = out + losses (no ratio invents '
      'torque, and the solve CHECKS rather than asserts)',
      out['power']['conserved'] is True,
      extra=str(out['power']))
check('the payload states the price of the ratio on the same line '
      'as the output torque',
      'speed given up' in out['power']['note'])
mid = next(s for s in out['shafts'] if s['shaft'] == 'shaft-mid')
check('the intermediate shaft is REVERSED (one mesh in), speed '
      '600/3 = 200 rpm',
      abs(abs(mid['speedRpm']) - 200.0) < 1e-9
      and mid['speedRpm'] < 0,
      extra=str(mid['speedRpm']))
check('compound shaft carries ONE speed for both its gears — that '
      'is what makes the stages multiply',
      abs(mid['ratioFromInput'] - 3.0) < 1e-9)
m1 = out['meshes'][0]
check('stage-1 centre distance = module x (N1+N2)/2 = 24.0 mm, '
      'derived and labelled',
      abs(m1['centreDistanceMm'] - 24.0) < 1e-9
      and 'derived' in m1['centreDistanceNote'],
      extra=str(m1['centreDistanceMm']))
check('mesh efficiency labelled NOT a prior when the row states '
      'it', m1['efficiencyIsPrior'] is False)
check('backlash ACCUMULATES down the train and is reported at the '
      'output (cast T0 parts have a lot of it)',
      out['outputBacklashMm'] > 0.3,
      extra=str(out.get('outputBacklashMm')))
check('quasi-static validity stated on every solve',
      'QUASI-STATIC' in out['validity']
      and 'Inertia' in out['validity'])

print('== suite: THE CLOCK TRAIN (verified against time) ==')
out = solve_train(mgr, 'clock-train-m0')
check('clock solve ok', out.get('ok'),
      extra=str(out.get('refusal')))
secs = next(s for s in out['shafts']
            if s['shaft'] == 'shaft-second')
check('the SECONDS shaft turns at exactly 1 rpm from a 30 rpm '
      'rotor (8t -> 240t = 30:1) — one turn per minute',
      abs(abs(secs['speedRpm']) - 1.0) < 1e-9,
      extra=str(secs['speedRpm']))
check('the MINUTE shaft turns once per HOUR (1/60 rpm) — the '
      'acceptance arithmetic for gr-5. Tight tolerance ON PURPOSE: '
      '9-dp rounding quantized this and the fix was the solver, '
      'not this number (the mag-3 rounding lesson)',
      abs(abs(out['outputSpeedRpm']) - (1.0 / 60.0)) < 1e-12,
      extra=str(out.get('outputSpeedRpm')))
check('over a full HOUR the minute shaft completes 1.000 turns to '
      'better than a milliturn — the clock IS the instrument',
      abs(abs(out['outputSpeedRpm']) * 60.0 - 1.0) < 1e-3,
      extra=str(abs(out['outputSpeedRpm']) * 60.0))
check('total clock ratio = 30 x 60 = 1800',
      abs(out['totalRatio'] - 1800.0) < 1e-9,
      extra=str(out.get('totalRatio')))
check('clock meshes use the type PRIOR band (no override) and say '
      'so loudly',
      all(m['efficiencyIsPrior'] for m in out['meshes'])
      and all('PRIOR' in m['efficiencyNote']
              for m in out['meshes']))
check('the clock train references its motor design, so gr-5 can '
      'drive it from the real torque curve',
      next(t for t in train_catalog(mgr)['trains']
           if t['name'] == 'clock-train-m0')['motorDesignRef']
      == 'clock-lavet-m0')

print('== suite: overrides + refusal ladder ==')
out = solve_train(mgr, 'two-stage-spur-demo', input_torque_nm=0.02,
                  input_speed_rpm=1200.0)
check('stated drive can be OVERRIDDEN (the door gr-5 drives a '
      'motor curve through): 2x torque and 2x speed scale through',
      abs(out['outputTorqueNm'] - 0.22815) < 1e-9
      and abs(out['outputSpeedRpm'] - 100.0) < 1e-9,
      extra=f"{out['outputTorqueNm']} / {out['outputSpeedRpm']}")
check('unknown train refuses by name',
      not solve_train(mgr, 'nope').get('ok'))

mgr2 = _mgr()
mgr2.objectTables['GearDefinition']['demo-pinion-a'].gear_type_ref \
    = 'planetary'
out = solve_train(mgr2, 'two-stage-spur-demo')
check('a type the solver cannot chain REFUSES with its ratio law '
      'named — guessing a ratio would be worse than refusing',
      not out.get('ok') and 'does not chain' in out['refusal']
      and 'N_ring' in out['suggestion']['evidence'])

mgr3 = _mgr()
mgr3.objectTables['GearDefinition']['demo-pinion-b'].shaft_ref \
    = 'shaft-orphan'
out = solve_train(mgr3, 'two-stage-spur-demo')
check('a disconnected train refuses (unreachable mesh named), '
      'never silently solves half of itself',
      not out.get('ok') and 'not reachable' in out['refusal'])

mgr4 = _mgr()
mgr4.objectTables['GearMeshDefinition']['demo-mesh-1'] \
    .driving_gear_ref = 'no-such-gear'
check('a mesh naming a missing gear refuses',
      not solve_train(mgr4, 'two-stage-spur-demo').get('ok'))

mgr5 = _mgr()
mgr5.objectTables['ShaftNodeDefinition'].pop('demo-shaft-mid')
out = solve_train(mgr5, 'two-stage-spur-demo')
check('an UNDECLARED shaft is a SUGGESTION, not a failure (the '
      'mag-3 flux-node rule): the train still solves',
      out.get('ok')
      and any('shaft-mid' in s['evidence']
              for s in out['suggestions']))

print('== suite: internal mesh direction + centre distance ==')
mgr6 = _mgr()
mgr6.objectTables['GearDefinition']['demo-wheel-a'].gear_type_ref \
    = 'internal'
mgr6.objectTables['GearMeshDefinition']['demo-mesh-1'] \
    .is_internal = True
out = solve_train(mgr6, 'two-stage-spur-demo')
mid = next(s for s in out['shafts'] if s['shaft'] == 'shaft-mid')
check('an INTERNAL mesh does not reverse: the mid shaft now turns '
      'the same way as the input (the classic silent bug, caught)',
      out.get('ok') and mid['speedRpm'] > 0,
      extra=str(mid['speedRpm']))
check('internal centre distance is a DIFFERENCE of pitch radii '
      '(18 - 6 = 12 mm), not a sum',
      abs(out['meshes'][0]['centreDistanceMm'] - 12.0) < 1e-9,
      extra=str(out['meshes'][0]['centreDistanceMm']))

failed = _results.count(False)
print(f'\n{len(_results) - failed}/{len(_results)} checks passed')
raise SystemExit(1 if failed else 0)
