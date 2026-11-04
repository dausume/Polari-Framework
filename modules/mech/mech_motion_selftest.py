"""
@module mech.mech_motion_selftest

mxc-4 selftests. Everything asserted here is HAND-COMPUTED first:

  frictionless  F = 2 N on m = 0.5 kg: a = 4 m/s² → x(1 s) = 2 m = 2000 mm
  static hold   m = 1 kg, N = 9.80665 N, μ_s 0.3 → F_s = 2.942 N:
                F = 2.9 N stays put, F = 3.0 N breaks away
  freecad       '100*time' → q(t) = 100 t mm; CSV frame f ≥ 1 is t = (f−1)·0.1
                → z = 10 (f−1): frame 5 → 40, frame 10 → 90, frame 16 → 150
  hard stop     50 N on 1.2 kg, limit 250 mm: a = 41.5 m/s², hits at
                t = √(2·0.25/41.5) = 0.110 s, then v = 0, at_limit
  5 N unloaded  m 1.2 kg, μ_k 0.02: F_k = 0.02·11.768 = 0.2354 N,
                a = (5 − 0.2354)/1.2 = 3.9705 m/s² → t(250 mm) = √(0.5/3.9705) = 0.3549 s
  loaded        2.64 kg → W = 25.89 N, breakaway μ_s·W + detent 3 N = 0.777 + 3 = 3.78 N
  runner        depth 300, x = 250: overlap 50 mm; M(250) = 3.816 N·m;
                N = 25.89 + 2·3.816/0.05 = 178.5 N; F_k = 0.35·178.5 = 62.5 N > 20 N
  rotary        J 1e-5, T 1e-4 → α = 10 rad/s² → θ(1 s) = 5 rad
  reflected     12:1 → 1/144

Run from polari-framework/:  PYTHONPATH=.:modules python3 -m mech.mech_motion_selftest
"""
import inspect
import json
import math
import os
import types

from mech.custom.motion_engine import (
    FormulaError, integrate, minimum_constant_drive, parse_formula,
    reflected_inertia, required_drive, time_to_reach,
)
from mech.custom.motion_runs import (
    G, build_model, compare_to_freecad, confirm_run, resultant,
    run_inputs_sha, run_polari, void_if_changed,
)
from mech.mech_motion_basis import MechMotionRun, MechMotionSimState, MechMotionVector
from mech.mech_motion_seed import (
    ASSEMBLY, BALL_SLIDE_MU, JOINT, MOTION_KNOBS, SEED_MECH_LOAD_CASES,
    SEED_MECH_MOTION_CASES, SEED_MECH_MOTION_CONTACTS, SEED_MECH_SIM_DEFINITIONS,
)

PASS = '\033[92mPASS\033[0m'
FAIL = '\033[91mFAIL\033[0m'
_results = []

REF_CSV = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'custom', 'reference', 'mfx0_motion_econ.csv')


def check(label, cond, extra=''):
    _results.append(bool(cond))
    print(f'{PASS if cond else FAIL}: {label}' + (f'  [{extra}]' if extra else ''))


def _rows(seed):
    return {s['name']: types.SimpleNamespace(**s) for s in seed}


def _mgr():
    """Minimal in-memory manager with the mxc-2 naming contract rows — the
    sibling seeds are NOT imported (they are built in parallel)."""
    joint = {'name': JOINT, 'assembly_ref': ASSEMBLY, 'kind': 'slider',
             'limits_json': json.dumps({'length_min': 0, 'length_max': 250}),
             'dof_json': json.dumps(['tz'])}
    contacts = [{'name': 'mfx-3-slide-left-contact', 'assembly_ref': ASSEMBLY, 'joint_ref': JOINT,
                 'kind': 'sliding', 'instance_a': 'drawer-box', 'instance_b': 'slide-left',
                 'mu_json': json.dumps(BALL_SLIDE_MU)},
                {'name': 'mfx-3-slide-right-contact', 'assembly_ref': ASSEMBLY, 'joint_ref': JOINT,
                 'kind': 'sliding', 'instance_a': 'drawer-box', 'instance_b': 'slide-right',
                 'mu_json': json.dumps(BALL_SLIDE_MU)}] + SEED_MECH_MOTION_CONTACTS
    instances = [{'name': n, 'assembly_ref': ASSEMBLY} for n in ('drawer-box', 'slide-left', 'slide-right')]
    instances[1]['load_rating_json'] = json.dumps({'dynamic_n': 343.0, 'static_n': 490.0, 'basis': 'knob'})
    instances[2]['load_rating_json'] = instances[1]['load_rating_json']
    return types.SimpleNamespace(objectTables={
        'MechAssembly': _rows([{'name': ASSEMBLY, 'kind': 'drawer_cassette'}]),
        'MechJoint': _rows([joint]),
        'MechContact': _rows(contacts),
        'MechPartInstance': _rows(instances),
        'MechLoadCase': _rows(SEED_MECH_LOAD_CASES),
        'MechMotionCase': _rows(SEED_MECH_MOTION_CASES),
        'SimulationDefinition': _rows(SEED_MECH_SIM_DEFINITIONS),
        'SimulationRun': {}, 'MechMotionRun': {}, 'MechMotionSimState': {}, 'MechMotionVector': {},
    })


def _written_fields(cls):
    """The fields run_polari wrote into the in-memory table of `cls`."""
    table = mgr.objectTables[cls.__name__]
    return set().union(*(vars(r).keys() for r in table.values())) if table else set()


def _case(mgr, name):
    return mgr.objectTables['MechMotionCase'][name]


def _load(mgr, name):
    return mgr.objectTables['MechLoadCase'][name]


print('== suite: the formula language is FreeCAD\'s ==')
f = parse_formula('100*time')
check("'100*time' at 0.5 s = 50", abs(f(0.5) - 50) < 1e-12)
g = parse_formula('2*(time+1)^2 - cos(0)')
check("'2*(time+1)^2 - cos(0)' at 1 s = 7", abs(g(1.0) - 7) < 1e-12, str(g(1.0)))
try:
    parse_formula('250*min(time,1)')
    check('min() refused by name (FreeCAD gives 0 frames for it)', False)
except FormulaError as e:
    check('min() refused by name (FreeCAD gives 0 frames for it)', 'min()' in str(e))

print('\n== suite: the integrator, hand-computed ==')
res = integrate({'coord': 'linear', 'inertia': 0.5, 'limits': (None, None)},
                {'kind': 'force', 'value': 2.0}, 1.0, 1e-3)
x_end = res['steps'][-1]['q']
check('frictionless F=2 N on 0.5 kg: x(1 s) = ½(F/m)t² = 2000 mm to 1e-6',
      abs(x_end - 2000.0) < 1e-6, f'{x_end:.9f}')

hold = {'coord': 'linear', 'inertia': 1.0, 'limits': (None, None),
        'friction': {'mu_s': 0.3, 'mu_k': 0.2, 'normal': G}}
r_hold = integrate(hold, {'kind': 'force', 'value': 2.9}, 0.5, 1e-3)
r_slip = integrate(hold, {'kind': 'force', 'value': 3.0}, 0.5, 1e-3)
check('static friction holds 1 kg at F = 2.9 N < μ_s·N = 2.942 N (x stays 0, friction = −F)',
      r_hold['steps'][-1]['q'] == 0.0 and abs(r_hold['steps'][-1]['friction'] + 2.9) < 1e-12)
x_slip = r_slip['steps'][-1]['q']
# a = (3.0 − 0.2·9.80665)/1 = 1.03867 → x(0.5) = ½·a·0.25 = 0.129834 m
check('F = 3.0 N breaks away: x(0.5 s) = ½(3−μ_k N)t² = 129.834 mm',
      abs(x_slip - 129.834) < 0.01, f'{x_slip:.4f}')

stop = integrate({'coord': 'linear', 'inertia': 1.2, 'limits': (0, 250)},
                 {'kind': 'force', 'value': 50.0}, 1.5, 1e-3, 0.01)
last = stop['steps'][-1]
hit = [s for s in stop['steps'] if s['at_limit']]
check('hard stop at 250 mm: q_end = 250, v = 0, at_limit set',
      abs(last['q'] - 250) < 1e-9 and last['q_dot'] == 0.0 and bool(hit),
      f"first hit t={stop['summary']['at_limit_first_t_s']:.3f} s (hand 0.110)")
check('hard stop time ≈ √(2·0.25/41.67) = 0.110 s',
      abs(stop['summary']['at_limit_first_t_s'] - math.sqrt(0.5 / (50 / 1.2))) < 2e-3)

rot = integrate({'coord': 'rotary', 'inertia': 1e-5, 'limits': (None, None)},
                {'kind': 'force', 'value': 1e-4}, 1.0, 1e-3)
check('rotary: J θ̈ = T, J 1e-5, T 1e-4 → θ(1 s) = 5 rad',
      abs(rot['steps'][-1]['q'] - 5.0) < 1e-9, f"{rot['steps'][-1]['q']:.9f}")
check('reflected inertia through a 12:1 train scales by 1/144',
      abs(reflected_inertia([0.0, 1.0], [12]) - 1 / 144) < 1e-15
      and abs(reflected_inertia([1e-6, 2e-3, 5e-2], [3, 4]) - (1e-6 + 2e-3 / 9 + 5e-2 / 144)) < 1e-15)

pos = integrate({'coord': 'linear', 'inertia': 1.2, 'limits': (0, 250),
                 'friction': {'mu_s': 0.03, 'mu_k': 0.02, 'normal': 1.2 * G}},
                {'kind': 'position', 'formula': '100*time'}, 1.5, 1e-3, 0.1)
check("position drive '100*time': q(1.0 s) = 100 mm, v = 100 mm/s, required pull = μ_k·N = 0.235 N",
      abs(pos['steps'][10]['q'] - 100) < 1e-9 and abs(pos['steps'][10]['q_dot'] - 100) < 1e-6
      and abs(pos['steps'][10]['drive'] - 0.02 * 1.2 * G) < 1e-6,
      f"drive={pos['steps'][10]['drive']:.4f}")

print('\n== suite: the mfx-3 drawer runs ==')
mgr = _mgr()
lc = _load(mgr, 'mfx-3-8-bins')
jt = mgr.objectTables['MechJoint'][JOINT]
rs = resultant(lc, jt)
check('resultant: 1.2 + 8×0.18 = 2.64 kg, W = 25.890 N',
      abs(rs['total_mass_kg'] - 2.64) < 1e-12 and abs(rs['total_force_n'] - 2.64 * G) < 1e-9)
check('moment about the front edge at full extension = 3.816 N·m (box 1.471 + bins 2.345)',
      abs(rs['moment_nm_full'] - 3.8158) < 2e-3, f"{rs['moment_nm_full']:.4f}")
check('closed, every mass is inside the cabinet: moment negative',
      rs['moment_nm_closed'] < 0, f"{rs['moment_nm_closed']:.4f}")

# FreeCAD reference: position drive on the empty drawer, compared frame by frame
fc = run_polari(mgr, _case(mgr, 'open-position-100t'), _load(mgr, 'mfx-3-empty'), knobs=MOTION_KNOBS)
cmp_ = compare_to_freecad(fc, REF_CSV, tol_mm=0.1)
check("'100*time' reproduces the FreeCAD CSV steady portion within 0.1 mm (16 frames)",
      cmp_['ok'] and cmp_['compared'] == 16, f"max err {cmp_['max_abs_err_mm']:.4f} mm")
print(f"      pre-motion frames reported, not asserted: {cmp_['pre_motion_frames']}")
hand_pos = next(c for c in fc['report']['checks'] if c['name'] == 'hand effort')
print(f"      force to follow 100 mm/s with the empty box: {hand_pos['value']:.3f} N "
      f"(impulsive start {hand_pos['note']})")

# unloaded, 5 N
u = run_polari(mgr, _case(mgr, 'open-pull-5n'), _load(mgr, 'mfx-3-empty'), knobs=MOTION_KNOBS)
opens = next(c for c in u['report']['checks'] if c['name'] == 'opens fully')
t_open = opens['t_open_s']
# hand: no detent → 0.3549 s; the seeded 3 N / 4 mm detent costs a little at the start
bare = integrate({'coord': 'linear', 'inertia': 1.2, 'limits': (0, 250),
                  'friction': {'mu_s': 0.03, 'mu_k': 0.02, 'normal': 1.2 * G}},
                 {'kind': 'force', 'value': 5.0}, 1.5, 1e-3)
t_bare = time_to_reach(bare, 250)
a_hand = (5 - 0.02 * 1.2 * G) / 1.2
check('unloaded ball-slide drawer (μ_k 0.02, 1.2 kg) opens 250 mm under 5 N: t = √(2·0.25/3.9705) = 0.355 s (no detent)',
      t_bare is not None and abs(t_bare - math.sqrt(0.5 / a_hand)) < 2e-3, f'{t_bare:.4f} s')
check('…and within the 1.5 s duration with the 3 N detent (run row ok on "opens fully")',
      opens['ok'] and t_open is not None and t_open < 1.5, f'{t_open:.4f} s')
print(f'      COMPUTED: 5 N unloaded opens fully at t = {t_open:.4f} s (detent) / {t_bare:.4f} s (no detent)')
hand_u = next(c for c in u['report']['checks'] if c['name'] == 'hand effort')
print(f"      minimum pull to open the empty drawer within 1.5 s: {hand_u['value']:.3f} N")

# loaded
ld = run_polari(mgr, _case(mgr, 'open-pull-loaded'), _load(mgr, 'mfx-3-8-bins'), knobs=MOTION_KNOBS)
hand_l = next(c for c in ld['report']['checks'] if c['name'] == 'hand effort')
breakaway = 0.03 * 2.64 * G + 3.0
check('loaded (2.64 kg) needs < 20 N: the pull is the breakaway μ_s·W + detent = 3.777 N (sliding only 0.518 N)',
      hand_l['ok'] and abs(hand_l['value'] - breakaway) < 1e-6 and abs(hand_l['peak_friction'] - 0.02 * 2.64 * G) < 1e-6,
      f"{hand_l['value']:.3f} N")
print(f"      COMPUTED: loaded pull needed = {hand_l['value']:.3f} N (knob 20 N); "
      f"minimum constant pull to arrive in 1.5 s = {hand_l['min_constant_pull']:.3f} N")
nobind = next(c for c in ld['report']['checks'] if c['name'] == 'no bind')
check('no bind: W = 25.9 N on the slides < 343 N dynamic rating (knob), tip moment 3.816 N·m stated',
      nobind['ok'] and abs(nobind['value'] - 2.64 * G) < 1e-6, nobind['note'])
closed = next(c for c in ld['report']['checks'] if c['name'] == 'stays closed')
check('stays closed: detent 3 N > 2 N knob', closed['ok'] and closed['value'] == 3.0)
smooth = next(c for c in ld['report']['checks'] if c['name'] == 'smooth')
# A step force applied at t = 0 already shows q̈ = (F − F_k − detent)/M on the
# t = 0 sample, so the breakaway pair carries ~no jerk; the big transition is
# the hard STOP: q̈ = (20 − 0.518)/2.64 = 7.380 m/s² → 0 over one 0.01 s grid
# step = 738.0 m/s³. Neither counts toward smoothness; both are reported.
stop_hand = (20 - 0.02 * 2.64 * G) / 2.64 / 0.01
check('smooth is the SLIDING phase: loaded run passes (< 500 m/s³) while the hard-stop step (738 m/s³) is reported, not counted',
      smooth['ok'] and smooth['value'] < 500 and abs(smooth['stop_jerk'] - stop_hand) < 0.5
      and smooth['stop_jerk'] > smooth['value'] and smooth['breakaway_jerk'] < 50,
      f"sliding peak {smooth['value']:.1f}, breakaway {smooth['breakaway_jerk']:.1f}, stop {smooth['stop_jerk']:.1f} m/s³ (hand {stop_hand:.1f})")
check('loaded ball-slide run: every check passes (run row ok)', ld['run'].ok is True,
      ', '.join(f"{c['name']}={'ok' if c['ok'] else 'FAIL'}" for c in ld['report']['checks']))

# legacy wooden runner
lg = run_polari(mgr, _case(mgr, 'legacy-wooden-runner'), _load(mgr, 'mfx-3-8-bins'), knobs=MOTION_KNOBS)
model_lg, ctx_lg = build_model(mgr, _case(mgr, 'legacy-wooden-runner'), _load(mgr, 'mfx-3-8-bins'), MOTION_KNOBS)
n_full = model_lg['friction']['normal_fn'](250.0)
check('runner normal at 250 mm = W + 2·M/overlap = 25.89 + 2·3.816/0.05 = 178.5 N',
      abs(n_full - (2.64 * G + 2 * rs['moment_nm_full'] / 0.05)) < 1e-6 and abs(n_full - 178.5) < 0.2,
      f'{n_full:.2f} N')
hand_lg = next(c for c in lg['report']['checks'] if c['name'] == 'hand effort')
check('legacy wooden runner (μ 0.35) needs > 20 N: quasi-static pull peaks at μ_k·N(250) = 62.5 N',
      hand_lg['value'] is not None and hand_lg['value'] > 20.0 and not hand_lg['ok']
      and abs(hand_lg['value'] - 0.35 * n_full) < 1e-6 and abs(hand_lg['breakaway'] - 0.5 * 2.64 * G) < 1e-6,
      f"{hand_lg['value']:.2f} N")
print(f"      COMPUTED: legacy runner pull needed = {hand_lg['value']:.2f} N slowly (breakaway "
      f"{hand_lg['breakaway']:.2f} N; a constant {hand_lg['min_constant_pull']:.2f} N still arrives in 1.5 s by coasting) "
      f"vs ball slide loaded {hand_l['value']:.3f} N")
check('the legacy run reports it: run row ok = False', lg['run'].ok is False)

print('\n== suite: rows ride core simulations ==')
from simulations.simulation_series import build_series  # noqa: E402  (import here: core, unchanged)
series = build_series(mgr, u['sim_run'].name, 'MechMotionSimState', ['q', 'q_dot'])
qs = series['fields']['q']
check('build_series reads the MechMotionSimState rows back as a (t, q) series',
      len(series['steps']) == len(u['result']['steps']) == 151
      and abs(series['times'][-1] - 1.5) < 1e-9 and abs(qs[-1] - 250) < 1e-9,
      f"{len(qs)} steps, q_end={qs[-1]}")
check('the run names its SimulationRun and the SimulationRun is complete with the step count',
      u['run'].simulation_run_ref == u['sim_run'].name and u['sim_run'].status == 'complete'
      and u['sim_run'].recorded_steps == 151)
vec = mgr.objectTables['MechMotionVector'].get('open-pull-5n@mfx-3-empty:position_mm')
check("vector '<run>:position_mm' extracted from the rows", vec is not None
      and json.loads(vec.samples_json)[-1][1] == qs[-1])
check('every check lands in report_json with its number',
      all(c['value'] is not None for c in json.loads(u['run'].report_json)['checks']))
check('fem_model_ref is named only (empty here) — no stress code in mech', u['run'].fem_model_ref == '')

print('\n== suite: reproducible by sha256, confirmations voided on change ==')
mc = _case(mgr, 'open-pull-loaded')
sha_a, _ = run_inputs_sha(mgr, mc, lc, MOTION_KNOBS)
sha_b, _ = run_inputs_sha(mgr, mc, lc, dict(MOTION_KNOBS))
check('same inputs → same sha (and the run row carries it)',
      sha_a == sha_b == ld['run'].inputs_sha256 == ld['inputs_sha256'] and len(sha_a) == 64, sha_a[:10])
check('the sha covers the rows: an unrelated motion case hashes differently',
      run_inputs_sha(mgr, _case(mgr, 'open-pull-5n'), lc, MOTION_KNOBS)[0] != sha_a)
check('row classes accept every field run_polari writes (constructor signatures)',
      all(set(k for k in _written_fields(c)) <= set(inspect.signature(c.__init__).parameters)
          for c in (MechMotionRun, MechMotionSimState, MechMotionVector)))
conf = confirm_run(ld['run'], by='person', who='selftest', words='watched the loaded drawer open')
check('a confirmation holds for the run\'s inputs sha (StructNodeConfirmation keys)',
      conf['state'] == 'confirmed' and conf['hex_sha256'] == ld['inputs_sha256']
      and set(conf) >= {'by', 'run', 'hex_sha256', 'state', 'voided_why', 'who', 'words', 'at', 'voided_at'})
left = mgr.objectTables['MechContact']['mfx-3-slide-left-contact']
left.mu_json = json.dumps(dict(BALL_SLIDE_MU, kinetic=0.025))
sha_c, _ = run_inputs_sha(mgr, mc, lc, MOTION_KNOBS)
check('changing μ → different sha', sha_c != sha_a)
voided = void_if_changed(ld['run'], sha_c)
check('…and the prior confirmation is reported voided (never deleted)',
      voided['state'] == 'voided' and 'sha256 changed' in voided['voided_why']
      and json.loads(ld['run'].confirmation_json)['state'] == 'voided', voided['voided_why'])
unchanged = void_if_changed(u['run'], u['inputs_sha256'])
check('a run with no confirmation is untouched', unchanged is None)

print()
n = sum(1 for r in _results if r)
print(f'{n}/{len(_results)} checks passed')
raise SystemExit(0 if n == len(_results) else 1)
