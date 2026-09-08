"""
Self-test for mtt-2 Part B sinter-3: the plan-first L2 structure
descriptors the sintering engine writes (grain-domain + pore-network),
including the mandatory-core honesty and the refusals.

Run from polari-framework/ (modules/ on the path):
    python3 -m pspp.sintering_structure_selftest
"""

import sys

from pspp.material_structure_basis import MANDATORY_DESCRIPTORS
from pspp.custom.sintering_structure import plan_sinter_structure

PASS = 0
FAIL = 0


def check(label, condition):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f'  ok: {label}')
    else:
        FAIL += 1
        print(f'  FAIL: {label}')


def test_plan():
    print('[sinter-3: L2 structure plan from a firing outcome]')
    plan = plan_sinter_structure(
        'alumina#fired-1600', relative_density=0.98,
        grain_size_um=5.0, theoretical_density_g_cm3=3.98)
    check('plan ok', plan['ok'])
    rows = {r['domain_type']: r for r in plan['proposedRows']}
    check('grain-domain + pore-network rows proposed',
          'grain-domain' in rows and 'capillary-pore' in rows)
    grain = rows['grain-domain']
    check('grain row is L2 with a grainSize descriptor',
          grain['scale_level'] == 2
          and grain['descriptors_json']['grainSize'] == 5.0)
    check('porosity = 1 − relative density',
          abs(grain['descriptors_json']['totalPorosity'] - 0.02)
          < 1e-9)
    check('bulkDensity = theoretical × ρ when theoretical given',
          abs(grain['descriptors_json']['bulkDensity']
              - 3.98 * 0.98) < 1e-6)
    check('characteristic length band brackets the grain size',
          grain['characteristic_length_min_m'] < 5.0e-6
          < grain['characteristic_length_max_m'])
    check('pore row carries the same porosity',
          abs(rows['capillary-pore']['descriptors_json']
              ['totalPorosity'] - 0.02) < 1e-9)


def test_core_honesty():
    print('[sinter-3: mandatory-core honesty]')
    plan = plan_sinter_structure('zirconia#fired', 0.95, 0.8)
    grain = next(r for r in plan['proposedRows']
                 if r['domain_type'] == 'grain-domain')
    # Every mandatory descriptor except bulkDensity is present; bulk is
    # honestly ABSENT when no theoretical density was supplied.
    present = set(grain['descriptors_json'])
    check('mandatory core present except an honestly-absent bulk',
          {d for d in MANDATORY_DESCRIPTORS if d != 'bulkDensity'}
          <= present)
    check('bulkDensity omitted (not invented) without theoretical '
          'density', 'bulkDensity' not in grain['descriptors_json'])
    check('plan states it is proposal-only (never auto-applied)',
          'plan-first' in plan['note'])


def test_refusals():
    print('[sinter-3: refusals]')
    check('no state_key refuses',
          plan_sinter_structure('', 0.9, 2.0)['ok'] is False)
    check('missing density/grain refuses',
          plan_sinter_structure('x#y', None, 2.0)['ok'] is False)
    check('out-of-range relative density refuses',
          plan_sinter_structure('x#y', 1.5, 2.0)['ok'] is False)
    check('non-positive grain size refuses',
          plan_sinter_structure('x#y', 0.9, 0)['ok'] is False)


def main():
    test_plan()
    test_core_honesty()
    test_refusals()
    print(f'\n{PASS} passed, {FAIL} failed')
    return 1 if FAIL else 0


if __name__ == '__main__':
    sys.exit(main())
