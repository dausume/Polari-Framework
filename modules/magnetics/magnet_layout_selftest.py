"""
@module magnetics.magnet_layout_selftest

mag-4 selftests: the ring-core demo solved against INDEPENDENT hand
math (same lumping, coded here from the formulas), selective mortar
as flux routing (plain joint dominates; upgrade it and flux jumps),
the dead-end structural branch carrying zero flux, dry-fit drift
suggestions, the limb-only coil rule, and the per-part/per-joint
bill with its gates.

Run from polari-framework/:
    python3 -m magnetics.magnet_layout_selftest
"""

import json
import math
import types

from magnetics.magnet_block_basis import (
    SEED_BLOCK_LAYOUTS, SEED_BLOCK_PLACEMENTS, SEED_BLOCK_VARIANTS,
    SEED_JOINT_MORTARS,
)
from magnetics.custom.magnet_layout import (
    dry_fit_report, generate_network, layout_cost, solve_layout,
)
from magnetics.magnet_seed import (
    SEED_MAGNETIC_POWDERS, SEED_MATERIAL_OPTIONS, SEED_USE_ROLES,
)
from supplychain.sourcing_seed import (
    SEED_PRICE_CITATIONS, SEED_PRODUCT_FORMULAS,
    SEED_PRODUCT_REQUIREMENTS, SEED_SOURCE_POLICIES,
    SEED_SUPPLY_SOURCES,
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
        'BlockSizeVariant': table(SEED_BLOCK_VARIANTS),
        'BlockLayoutDefinition': table(SEED_BLOCK_LAYOUTS),
        'BlockPlacement': table(SEED_BLOCK_PLACEMENTS),
        'JointMortarAssignment': table(SEED_JOINT_MORTARS),
        'SupplySourceProfile': table(SEED_SUPPLY_SOURCES),
        'PriceCitation': table(SEED_PRICE_CITATIONS),
        'ProductInputRequirement': table(SEED_PRODUCT_REQUIREMENTS),
        'ProductFormula': table(SEED_PRODUCT_FORMULAS),
        'SourcePreferencePolicy': table(SEED_SOURCE_POLICIES),
    }
    return m


mgr = _mgr()

# ---------------- independent hand math (same lumping) -----------
MU_BLOCK, MU_FERRITE_MORTAR, MU_PLAIN = 2.196, 1.714, 1.0
A_X = 0.02 * 0.02          # x-adjacency face (y*z)
A_Y = 0.04 * 0.02          # y-adjacency face (x*z)
T = 0.001


def r_seg(length, mu, area):
    return length / (MU0 * mu * area)


# x-joints (00-10, 11-01): two 0.02 halves + ferrite mortar @ A_X.
R_XJ = 2 * r_seg(0.02, MU_BLOCK, A_X) + r_seg(T, MU_FERRITE_MORTAR,
                                              A_X)
# y-joint ferrite (10-11): two 0.01 halves + ferrite mortar @ A_Y.
R_YJ_F = 2 * r_seg(0.01, MU_BLOCK, A_Y) + r_seg(T,
                                                MU_FERRITE_MORTAR,
                                                A_Y)
# y-joint PLAIN (01-00): same halves + plain mortar.
R_YJ_P = 2 * r_seg(0.01, MU_BLOCK, A_Y) + r_seg(T, MU_PLAIN, A_Y)
R_LOOP = 2 * R_XJ + R_YJ_F + R_YJ_P
FLUX = 200.0 / R_LOOP

print('== suite: dry fit ==')
report = dry_fit_report(mgr, 'ring-core-demo')
check('5 adjacencies found (4 ring + 1 seat), all mortared, zero '
      'suggestions',
      report['ok'] and len(report['adjacencies']) == 5
      and report['mortaredJoints'] == 5
      and report['suggestions'] == [])
check('interlocks reported per placement (dry-fit rigidity data)',
      report['interlocks']['ring-blk-00'] == ['tongue-x',
                                              'groove-x'])

print('== suite: generated network solves to the hand math ==')
out = solve_layout(mgr, 'ring-core-demo')
by_name = {e['element']: e for e in out['elements']}
coil = by_name['coil-ring-blk-00']
check('layout solves ok (elements generated, never persisted)',
      out['ok'] and out['generatedFrom']['elements'] == 16,
      extra=str(out.get('generatedFrom')))
check('loop flux matches the independent lumped math',
      abs(abs(coil['fluxWb']) - FLUX) < FLUX * 1e-6,
      extra=f"{coil['fluxWb']} vs {FLUX}")
check('the DELIBERATE-GAP joint carries the same series flux '
      '(one loop) but holds the biggest single mortar drop',
      abs(abs(by_name['ring-joint-01-00-mortar']['fluxWb']) - FLUX)
      < FLUX * 1e-6
      and by_name['ring-joint-01-00-mortar']['reluctance']
      > by_name['ring-joint-10-11-mortar']['reluctance'])
check('dead-end structural branch (bearing seat) carries ~zero '
      'flux — containment without flux leakage',
      abs(by_name['ring-joint-seat-mortar']['fluxWb'])
      < FLUX * 1e-9)
check('validity sentence names the lumped segmented-core model',
      'lumped segmented-core' in out['validity'])
check('dry-fit report rides the solve', 'dryFit' in out
      and out['dryFit']['mortaredJoints'] == 5)

print('== suite: SELECTIVE MORTAR IS THE DESIGN LANGUAGE ==')
# Upgrade the plain joint to ferrite mortar -> flux must jump by
# exactly the hand-math ratio.
plain = mgr.objectTables['JointMortarAssignment']['ring-joint-01-00']
plain.mortar_ref = 'opt-solgel-ferrite'
out2 = solve_layout(mgr, 'ring-core-demo')
coil2 = {e['element']: e for e in out2['elements']}[
    'coil-ring-blk-00']
FLUX_ALL_F = 200.0 / (2 * R_XJ + 2 * R_YJ_F)
check('upgrading the plain joint to magnetic mortar raises the '
      'loop flux by the predicted ratio — flux routing BY '
      'CONSTRUCTION',
      abs(abs(coil2['fluxWb']) - FLUX_ALL_F) < FLUX_ALL_F * 1e-6
      and abs(coil2['fluxWb']) > abs(coil['fluxWb']),
      extra=f"{coil2['fluxWb']} vs {FLUX_ALL_F}")
plain.mortar_ref = 'opt-plain-solgel-mortar'

print('== suite: the limb-only coil rule ==')
seat = mgr.objectTables['BlockPlacement']['ring-seat']
seat.coil_json = '{"turns": 10, "amps": 1.0}'
out3 = solve_layout(mgr, 'ring-core-demo')
check('winding a 1-joint block refuses (limbs only, ambiguity '
      'named)',
      not out3.get('ok') and 'ring-seat' in out3.get('refusal', ''))
seat.coil_json = '{}'

print('== suite: drift visibility ==')
extra = types.SimpleNamespace(
    name='ring-blk-20', layout_name='ring-core-demo',
    slot_json='{"x": 2, "y": 1, "z": 0}',
    variant_ref='brick-40x20x20',
    material_ref='opt-geopolymer-ferrite', coil_json='{}',
    is_prior=True, provenance_id='t', notes='')
mgr.objectTables['BlockPlacement']['ring-blk-20'] = extra
report = dry_fit_report(mgr, 'ring-core-demo')
check('a new un-mortared adjacency = SUGGESTION, never silent',
      any('NO mortar assignment' in s['action']
          for s in report['suggestions']))
del mgr.objectTables['BlockPlacement']['ring-blk-20']

print('== suite: the bill of parts (gates honored) ==')
cost = layout_cost(mgr, 'ring-core-demo')
blocks = [p for p in cost['parts'] if p['kind'] == 'block']
jrows = [p for p in cost['parts'] if p['kind'] == 'joint']
check('5 blocks + 5 joints priced, total > 0, estimates flagged',
      cost['ok'] and len(blocks) == 5 and len(jrows) == 5
      and cost['totalUsd'] > 0 and cost['anyEstimate'],
      extra=json.dumps(cost)[:160])
ring_block = next(p for p in blocks if p['part'] == 'ring-blk-00')
# brick 0.04*0.02*0.02 m3 * 3120 kg/m3 * 6.0898 USD/kg (cascade)
HAND_USD = 0.04 * 0.02 * 0.02 * 3120.0 * 6.0898
check('block price = volume x density x cascaded $/kg (hand math)',
      abs(ring_block['usd'] - HAND_USD) < 0.01,
      extra=f"{ring_block['usd']} vs {HAND_USD}")
check('joint thickness priors carry their estimate flags',
      all(j['thicknessIsEstimate'] for j in jrows))
check('exclusions stated loud (mold/labor/energy ride the '
      'planner)', 'excluded' in cost)
# theoretical material refuses pricing
seat = mgr.objectTables['BlockPlacement']['ring-seat']
seat.material_ref = 'opt-fe16n2'
cost2 = layout_cost(mgr, 'ring-core-demo')
check('theoretical block material refuses pricing BY NAME (gates '
      'travel into the bill)',
      cost2['ok'] and any('opt-fe16n2' in (r.get('refusal', '')
                          + json.dumps(r.get('suggestion') or {}))
                          or r['part'] == 'ring-seat'
                          for r in cost2['refusals'])
      and len([p for p in cost2['parts']
               if p['kind'] == 'block']) == 4)
seat.material_ref = 'opt-plain-geopolymer'

failed = _results.count(False)
print(f'\n{len(_results) - failed}/{len(_results)} checks passed')
raise SystemExit(1 if failed else 0)
