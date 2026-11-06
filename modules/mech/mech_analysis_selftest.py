"""
@module mech.mech_analysis_selftest

The mech engines reached the Polari way — as AnalysisDefinition rows
called by name (polariNoCode.analysis_calls.call_analysis) and as
no-code solutions run by the real SolutionExecutionEngine — over the
FULL real seed set (catalogue, materials, fixtures, cases). Hand-
expected values come from the group selftests:

  mfx-1 mobility 0 · mfx-3 one free DOF (the drawer, tz) · T-nut slot6-M5
  rider ↔ 2020 slot-B6/20 channel pairs, M6 T-nut refused · the
  deep-groove bearing default steel_carbon is viable · the loaded drawer
  run (8 bins, 1.5 kg) passes every check with hand effort 3.777 N ·
  the wooden runner fails hand effort (62.47 N) · '100*time' matches
  FreeCAD within 1e-9 mm over 16 frames · unknown names refuse by name.

Run from polari-framework/:  PYTHONPATH=.:modules python3 -m mech.mech_analysis_selftest
"""
import types

from polariNoCode import graph_builder as gb
from polariNoCode.analysis_calls import call_analysis

from mech.mech_analysis_seed import SEED_MECH_ANALYSES, SEED_MECH_SOLUTIONS, mech_analysis_seed_pairs
from mech.mech_motion_seed import mech_seed_pairs

PASS = '\033[92mPASS\033[0m'
FAIL = '\033[91mFAIL\033[0m'
_results = []


def check(label, cond, extra=''):
    _results.append(bool(cond))
    print(f'{PASS if cond else FAIL}: {label}' + (f'  [{extra}]' if extra and not cond else ''))


def _mgr():
    tables = {n: {r['name']: types.SimpleNamespace(**r) for r in rows}
              for n, c, rows in list(mech_seed_pairs()) + mech_analysis_seed_pairs()}
    tables['SimulationRun'] = {}
    return types.SimpleNamespace(idList=[], objectTables=tables)


mgr = _mgr()

print('== rows ==')
check('9 analyses seeded, one callable each, all resolvable',
      len(SEED_MECH_ANALYSES) == 9 and all(
          __import__('polariNoCode.analysis_calls', fromlist=['resolve_callable']).resolve_callable(a['callable_ref'])
          for a in SEED_MECH_ANALYSES))
check('9 solutions seeded, each DirectInvocation → AnalysisCall → ReturnValue', len(SEED_MECH_SOLUTIONS) == 9 and all(
    [s['stateClass'] for s in __import__('json').loads(sol['definition'])['stateInstances']]
    == ['DirectInvocation', 'AnalysisCall', 'ReturnValue'] for sol in SEED_MECH_SOLUTIONS))

print('== catalogue ==')
fam = call_analysis(mgr, 'mech-catalogue-family', {})
check('family list: 25 families, 401 variants', fam['ok'] and fam['count'] == 25
      and sum(f['variant_count'] for f in fam['families']) == 401, str(fam.get('count')))
check('provenance stamped under _analysis', fam['_analysis']['name'] == 'mech-catalogue-family')
var = call_analysis(mgr, 'mech-catalogue-variant', {'variant': 'iso4762-M5x10'})
check('iso4762-M5x10: head Ø 8.5, k 5, 2 features', var['ok'] and var['variant']['dims_json']['dk_max'] == 8.5
      and var['variant']['dims_json']['k'] == 5 and len(var['features']) == 2)
p = call_analysis(mgr, 'mech-pairing', {'variant_a': 'tnut-sliding-slot6-M5', 'feature_a': 'slot',
                                        'variant_b': 'extrusion-2020-L300', 'feature_b': 'slot:+x:0'})
check('T-nut slot6-M5 rider pairs with 2020 slot-B6/20 channel', p.get('ok') is True, str(p)[:160])
p6 = call_analysis(mgr, 'mech-pairing', {'variant_a': 'tnut-sliding-slot8-M6', 'feature_a': 'slot',
                                         'variant_b': 'extrusion-2020-L300', 'feature_b': 'slot:+x:0'})
check('M6 slot-8 T-nut in a B6/20 slot refused with a reason', p6.get('ok') is False and p6.get('reason'), str(p6)[:160])
miss = call_analysis(mgr, 'mech-catalogue-variant', {'variant': 'no-such-part'})
check('unknown variant refuses by name with a suggestion', miss['ok'] is False and 'suggestion' in miss)

print('== materials ==')
pref = call_analysis(mgr, 'mech-material-preference', {'preference': 'deep_groove_ball_bearing'})
ids = (pref.get('check') or {}).get('ids') or {}
check('bearing preference: steel_carbon default viable, legacy list present',
      pref['ok'] and ids.get('steel_carbon', {}).get('viable') is True and pref.get('legacy'), str(list(ids))[:120])

print('== assemblies ==')
d1 = call_analysis(mgr, 'mech-assembly-dof', {'assembly': 'mfx-1'})
check('mfx-1 mobility 0, nothing under-constrained', d1['ok'] and d1['assembly_mobility'] == 0 and not d1['under_constrained'])
d3 = call_analysis(mgr, 'mech-assembly-dof', {'assembly': 'mfx-3-drawer-cassette'})
check('mfx-3 mobility 1 (the drawer along tz)', d3['ok'] and d3['assembly_mobility'] == 1, str(d3.get('assembly_mobility')))
c1 = call_analysis(mgr, 'mech-assembly-check', {'assembly': 'mfx-1'})
check('mfx-1 fit checks: no conflicts against the real catalogue', c1['ok'] and c1['conflict_count'] == 0,
      str([c['kind'] for c in c1.get('conflicts', [])]))
c3 = call_analysis(mgr, 'mech-assembly-check', {'assembly': 'mfx-3-drawer-cassette'})
check('mfx-3 fit checks: no conflicts', c3['ok'] and c3['conflict_count'] == 0, str([c['kind'] for c in c3.get('conflicts', [])]))

print('== motion ==')
loaded = call_analysis(mgr, 'mech-motion-run', {'motion_case': 'open-pull-loaded', 'load_case': 'mfx-3-8-bins'})
checks = {c['name']: c for c in (loaded.get('report') or {}).get('checks', [])}
check('loaded drawer: every check passes', loaded['ok'] and loaded['report']['ok'] is True, str({k: v['ok'] for k, v in checks.items()}))
check('loaded drawer: hand effort 3.777 N', abs(checks.get('hand effort', {}).get('value', 0) - 3.777) < 0.01,
      str(checks.get('hand effort', {}).get('value')))
check('run row landed with inputs_sha256', loaded['run']['name'] == 'open-pull-loaded@mfx-3-8-bins' and len(loaded['inputs_sha256']) == 64)
check('151 MechMotionSimState rows landed for it', loaded['steps'] == 151 and len(mgr.objectTables['MechMotionSimState']) >= 151)
legacy = call_analysis(mgr, 'mech-motion-run', {'motion_case': 'legacy-wooden-runner', 'load_case': 'mfx-3-8-bins'})
lchecks = {c['name']: c for c in legacy['report']['checks']}
check('wooden runner: hand effort fails at 62.47 N, stays closed fails, the rest pass',
      legacy['report']['ok'] is False and lchecks['hand effort']['ok'] is False
      and abs(lchecks['hand effort']['value'] - 62.474) < 0.01 and lchecks['stays closed']['ok'] is False
      and all(v['ok'] for k, v in lchecks.items() if k not in ('hand effort', 'stays closed')))
pos = call_analysis(mgr, 'mech-motion-run', {'motion_case': 'open-position-100t', 'load_case': 'mfx-3-empty'})
cmp_ = call_analysis(mgr, 'mech-freecad-compare', {'run': pos['run']['name']})
check("'100*time' matches the FreeCAD reference within 1e-9 mm over 16 frames",
      cmp_['ok'] and cmp_['compared'] == 16 and cmp_['max_abs_err_mm'] < 1e-9, str(cmp_.get('max_abs_err_mm')))
nocase = call_analysis(mgr, 'mech-motion-run', {'motion_case': 'no-such-case'})
check('unknown motion case refuses by name', nocase['ok'] is False and 'suggestion' in nocase)

print('== as no-code solutions (the real engine) ==')
sol = next(s for s in SEED_MECH_SOLUTIONS if s['name'] == 'mech-run-assembly-dof')
trace = gb.execute(__import__('json').loads(sol['definition']), manager=mgr, params={'assembly': 'mfx-1'})
ret = getattr(trace, 'final_return_value', None)
check('mech-run-assembly-dof via SolutionExecutionEngine returns mobility 0',
      isinstance(ret, dict) and ret.get('assembly_mobility') == 0, str(type(trace).__name__) + ' ' + str(ret)[:120])

n = sum(_results)
print(f'\n{n}/{len(_results)} checks passed')
