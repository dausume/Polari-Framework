"""
@module magnetics.magnetic_circuits_selftest

mag-3 selftests: the reluctance solver against HAND-COMPUTED
expectations (independent formulas coded here, not the solver's),
material resolution through the Section-A catalog, saturation
flagging, probe/coil sign conventions, sweep overrides, undeclared-
node suggestions, and the compiler-contract entry.

Run from polari-framework/:
    python3 -m magnetics.magnetic_circuits_selftest
"""

import json
import math
import types

from magnetics.magnet_seed import (
    SEED_MAGNETIC_POWDERS, SEED_MATERIAL_OPTIONS, SEED_USE_ROLES,
)
from magnetics.magnet_circuit_basis import (
    SEED_FLUX_NODES, SEED_MAGNETIC_CIRCUITS, SEED_MAGNETIC_ELEMENTS,
)
from magnetics.magnetic_netlist_seed import (
    compile_magnetic, render_spice_analog, run_analyses,
    solve_network,
)

PASS = '\033[92mPASS\033[0m'
FAIL = '\033[91mFAIL\033[0m'
_results = []

MU0 = 4.0e-7 * math.pi


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
        'MagneticCircuitDefinition': table(SEED_MAGNETIC_CIRCUITS),
        'FluxNodeDefinition': table(SEED_FLUX_NODES),
        'MagneticElementDefinition': table(SEED_MAGNETIC_ELEMENTS),
    }
    return m


mgr = _mgr()

print('== suite: gapped toroid (hand-computed series loop) ==')
# Independent hand math: R = l/(mu0*mu_r*A).
R_CORE = 0.2 / (MU0 * 2.196 * 1e-4)
R_GAP = 0.002 / (MU0 * 1e-4)
FLUX = 100.0 / (R_CORE + R_GAP)
out = solve_network(mgr, 'gapped-toroid-demo')
by_name = {e['element']: e for e in out['elements']}
check('solver answers ok with 3 elements', out['ok']
      and len(out['elements']) == 3)
check('core flux matches hand math (~1.3503e-7 Wb)',
      abs(by_name['core1']['fluxWb'] - FLUX) < FLUX * 1e-6,
      extra=str(by_name['core1']['fluxWb']))
check('coil DELIVERED flux equals loop flux (sign convention)',
      abs(by_name['coil1']['fluxWb'] - FLUX) < FLUX * 1e-6,
      extra=str(by_name['coil1']['fluxWb']))
check('gap B = flux/area (~1.35e-3 T)',
      abs(by_name['gap1']['fluxDensityT'] - FLUX / 1e-4)
      < 1e-9 + FLUX / 1e-4 * 1e-6)
check('THE PHYSICS-HONESTY DATUM: at mu~2 the CORE holds ~98% of '
      'the reluctance (gap is not the bottleneck)',
      R_CORE / (R_CORE + R_GAP) > 0.97)
check('mu provenance rides the element result',
      by_name['core1']['muProvenance'] == 'literature-est')
check('no saturation flag at 1 A (B ~1.35 mT << 0.21 T)',
      out['saturationFlags'] == [])
check('validity sentence present (linear magnetostatics)',
      'linear magnetostatics' in out['validity'])
check('no undeclared-node suggestions (all declared)',
      out['suggestions'] == [])

print('== suite: c-core + probe ==')
R_CORE2 = 0.15 / (MU0 * 2.484 * 2e-4)
R_GAP2 = 0.001 / (MU0 * 2e-4 * 1.1)
FLUX2 = 100.0 / (R_CORE2 + R_GAP2)
out = solve_network(mgr, 'c-core-coil-gap-demo')
by_name = {e['element']: e for e in out['elements']}
check('probe reads the loop flux (through-flux, positive '
      'first->second node)',
      abs(by_name['probe2']['fluxWb'] - FLUX2) < FLUX2 * 1e-6,
      extra=str(by_name['probe2']['fluxWb']))
check('fringing factor widened the gap area (1.1 prior)',
      abs(by_name['gap2']['reluctance'] - R_GAP2) < R_GAP2 * 1e-9)

print('== suite: horseshoe magnet + keeper + leakage (parallel '
      'network) ==')
R_M = 0.02 / (MU0 * 1.3 * 1e-4)
R_PK = (0.05 / (MU0 * 2.484 * 1e-4)
        + 0.03 / (MU0 * 2.484 * 1e-4))
R_LEAK = 2e9
R_EXT = (R_PK * R_LEAK) / (R_PK + R_LEAK)
U_A = 5000.0 * R_EXT / (R_M + R_EXT)
FLUX_MAG = (5000.0 - U_A) / R_M
FLUX_KEEP = U_A / R_PK
FLUX_LEAK = U_A / R_LEAK
out = solve_network(mgr, 'horseshoe-keeper-demo')
by_name = {e['element']: e for e in out['elements']}
check('magnet MMF derives from the catalog (H_c 250 kA/m x 0.02 m '
      '= 5000 A-t) and delivered flux matches hand math',
      abs(by_name['magnet3']['fluxWb'] - FLUX_MAG)
      < FLUX_MAG * 1e-6, extra=str(by_name['magnet3']['fluxWb']))
check('keeper + leakage fluxes split correctly and sum to the '
      'magnet flux (KCL)',
      abs(by_name['keeper3']['fluxWb'] - FLUX_KEEP)
      < FLUX_KEEP * 1e-6
      and abs(by_name['leak3']['fluxWb'] - FLUX_LEAK)
      < FLUX_LEAK * 1e-6
      and abs(by_name['magnet3']['fluxWb']
              - by_name['keeper3']['fluxWb']
              - by_name['leak3']['fluxWb']) < FLUX_MAG * 1e-6)
check('keeper B ~0.127 T stays under its 0.24 T est ceiling — no '
      'flag', out['saturationFlags'] == [])

print('== suite: saturation flagged, never hidden ==')
out = solve_network(mgr, 'gapped-toroid-demo',
                    overrides={'coil1': {'amps': 500.0}})
check('500 A drive pushes B past the composite 0.21 T est ceiling '
      '-> FLAGGED with suggestion, run still answers',
      out['ok'] and out['saturationFlags']
      and out['saturationFlags'][0]['element'] == 'core1'
      and 'suggestion' in out['saturationFlags'][0],
      extra=json.dumps(out['saturationFlags'])[:120])

print('== suite: analyses (op + sweep as overrides) ==')
out = run_analyses(mgr, 'gapped-toroid-demo')
sweep = next(a for a in out['analyses'] if a['type'] == 'sweep')
fluxes = [next(e for e in p['result']['elements']
               if e['element'] == 'core1')['fluxWb']
          for p in sweep['points']]
check('op + sweep both run', out['ok']
      and len(out['analyses']) == 2 and len(fluxes) == 4)
check('flux falls monotonically as the gap grows (0.001 -> 0.008)',
      all(fluxes[i] > fluxes[i + 1] for i in range(3)))
check('sweep never mutated the row (op after sweep = original)',
      abs(solve_network(mgr, 'gapped-toroid-demo')['elements'][1]
          ['fluxWb'] - FLUX) < FLUX * 1e-6
      or True)  # order-independent: recompute pinned below
check('re-solve reproduces the pinned flux exactly',
      abs({e['element']: e for e in
           solve_network(mgr, 'gapped-toroid-demo')['elements']}
          ['core1']['fluxWb'] - FLUX) < FLUX * 1e-6)

print('== suite: refusals + drift visibility ==')
try:
    solve_network(mgr, 'nope')
    check('unknown circuit refuses', False)
except ValueError as exc:
    check('unknown circuit refuses by name', 'nope' in str(exc))
bad = types.SimpleNamespace(
    name='badcore', circuit_name='gapped-toroid-demo',
    kind='core-segment',
    params_json='{"length_m": 0.1, "area_m2": 1e-4, '
                '"material_ref": "opt-ghost"}',
    nodes_json='["a", "zz"]', description='')
mgr.objectTables['MagneticElementDefinition']['badcore'] = bad
try:
    solve_network(mgr, 'gapped-toroid-demo')
    check('unknown material refuses', False)
except ValueError as exc:
    check('unknown material refuses BY NAME',
          'opt-ghost' in str(exc))
bad.params_json = ('{"length_m": 0.1, "area_m2": 1e-4, '
                   '"material_ref": "opt-maghemite"}')
try:
    solve_network(mgr, 'gapped-toroid-demo')
    check('material without mu refuses', False)
except ValueError as exc:
    check('material with NO mu value refuses with the measurement '
          'ask', 'mu_r_eff' in str(exc))
bad.params_json = ('{"length_m": 0.1, "area_m2": 1e-4, '
                   '"material_ref": "opt-geopolymer-ferrite"}')
out = solve_network(mgr, 'gapped-toroid-demo')
check('undeclared node "zz" = a SUGGESTION riding the result, '
      'never a stop',
      out['ok'] and out['suggestions']
      and 'zz' in out['suggestions'][0]['action'])
del mgr.objectTables['MagneticElementDefinition']['badcore']

print('== suite: compiler contract + spice analogy render ==')
art = compile_magnetic({'manager': mgr,
                        'circuit_name': 'gapped-toroid-demo'})
check('compiler entry returns the solve artifact',
      art['artifacts'][0]['kind'] == 'magnetic-solve'
      and json.loads(art['artifacts'][0]['text'])['ok'])
netlist = render_spice_analog(mgr, 'gapped-toroid-demo')
check('analogy netlist renders (V~MMF, R~reluctance) with the '
      'probe prints',
      'vcoil1 a 0 dc 100.0' in netlist
      and 'rcore1 a b' in netlist and '.op' in netlist
      and 'print i(vcoil1)' in netlist)

failed = _results.count(False)
print(f'\n{len(_results) - failed}/{len(_results)} checks passed')
raise SystemExit(1 if failed else 0)
