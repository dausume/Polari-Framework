"""
Self-test for CrystalStructureDefinition + crystal_ops (ssp-1).

Physics-invariant checks against literature values (generous bands):
every seed builds; cubic volumes = a^3; fcc/bcc/diamond nearest
neighbors and coordinations; densities within literature bands;
refusal shapes name their knobs.

Run from polari-framework/:
    python3 -m materialsScience.selftest_crystal_structures
"""

import json
import sys
from types import SimpleNamespace

from materialsScience import crystal_ops
from materialsScience.crystal_structures_seed import (
    SEED_CRYSTAL_STRUCTURES,
)

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


def _seed(name):
    return next(s for s in SEED_CRYSTAL_STRUCTURES
                if s['name'] == name)


def _facts(name):
    verdict = crystal_ops.structure_facts(_seed(name))
    return verdict['facts'] if verdict['ok'] else None


def test_all_seeds_build():
    print('[every seed builds]')
    check('eight structures seeded',
          len(SEED_CRYSTAL_STRUCTURES) == 8)
    for seed in SEED_CRYSTAL_STRUCTURES:
        verdict = crystal_ops.structure_facts(seed)
        check(f"{seed['name']} builds",
              verdict['ok'] and verdict['facts']['nAtoms'] > 0)


def test_geometry_invariants():
    print('[geometry invariants]')
    al = _facts('aluminum-fcc')
    check('Al fcc: 4 atoms in the conventional cell',
          al and al['nAtoms'] == 4)
    check('Al fcc: volume = a^3',
          al and abs(al['cellVolumeA3'] - 4.05 ** 3) < 0.05)
    check('Al fcc: nearest neighbor a/sqrt(2) ~ 2.864 A',
          al and abs(al['nearestNeighborA'] - 2.864) < 0.01)
    check('Al fcc: coordination 12',
          al and al['coordinationOfAtom0'] == 12)
    fe = _facts('alpha-iron-bcc')
    check('alpha-Fe bcc: 2 atoms', fe and fe['nAtoms'] == 2)
    check('alpha-Fe bcc: nearest neighbor a*sqrt(3)/2 ~ 2.482 A',
          fe and abs(fe['nearestNeighborA'] - 2.482) < 0.01)
    check('alpha-Fe bcc: coordination 8 (cutoff 1.1 excludes the '
          'second shell)', fe and fe['coordinationOfAtom0'] == 8)
    si = _facts('silicon-diamond')
    check('Si diamond: 8 atoms', si and si['nAtoms'] == 8)
    check('Si diamond: coordination 4',
          si and si['coordinationOfAtom0'] == 4)
    check('Si diamond: bond length a*sqrt(3)/4 ~ 2.352 A',
          si and abs(si['nearestNeighborA'] - 2.352) < 0.01)
    nacl = _facts('rock-salt-nacl')
    check('NaCl: Na4Cl4 conventional cell',
          nacl and nacl['nAtoms'] == 8)
    check('NaCl: octahedral coordination 6',
          nacl and nacl['coordinationOfAtom0'] == 6)
    check('NaCl: Na-Cl distance a/2 = 2.82 A',
          nacl and abs(nacl['nearestNeighborA'] - 2.82) < 0.01)
    graphite = _facts('graphite-hexagonal')
    check('graphite: in-plane C-C ~ 1.421 A',
          graphite and abs(graphite['nearestNeighborA'] - 1.421)
          < 0.005)
    check('graphite: 3-coordinated (interlayer stays unbonded)',
          graphite and graphite['coordinationOfAtom0'] == 3)


def test_density_bands():
    print('[density vs literature]')
    bands = {
        'aluminum-fcc': (2.65, 2.75),        # lit 2.70
        'alpha-iron-bcc': (7.7, 8.0),        # lit 7.87
        'nickel-fcc': (8.8, 9.0),            # lit 8.91
        'silicon-diamond': (2.30, 2.36),     # lit 2.329
        'rock-salt-nacl': (2.1, 2.25),       # lit 2.165
        'magnetite-spinel': (5.0, 5.4),      # lit 5.17-5.2
        'corundum-alumina': (3.9, 4.1),      # lit 3.98
        'graphite-hexagonal': (2.2, 2.32),   # lit 2.26
    }
    for name, (lo, hi) in bands.items():
        facts = _facts(name)
        check(f'{name}: density {facts["densityGcm3"] if facts else "?"}'
              f' in [{lo}, {hi}]',
              facts and lo <= facts['densityGcm3'] <= hi)


def test_stoichiometry():
    print('[symmetry-expanded stoichiometry]')
    mag = _facts('magnetite-spinel')
    check('magnetite: Fe24O32 (Z=8 spinel from 3 Wyckoff sites)',
          mag and mag['formula'] == 'Fe24O32')
    cor = _facts('corundum-alumina')
    check('corundum: Al12O18 (Z=6 from 2 Wyckoff sites)',
          cor and cor['formula'] == 'Al12O18')


def test_report_payload():
    print('[build report payload]')
    report = crystal_ops.build_report(_seed('rock-salt-nacl'))
    check('report carries cell + atoms + bonds',
          report['ok'] and len(report['cell']) == 3
          and len(report['atoms']) == 8 and len(report['bonds']) > 0)
    atom = report['atoms'][0]
    check('atom entries carry element + frac + cart',
          atom['element'] in ('Na', 'Cl') and len(atom['frac']) == 3
          and len(atom['cart']) == 3)
    bond = report['bonds'][0]
    check('bond entries carry i/j/distance',
          {'i', 'j', 'distanceA'} <= set(bond))
    row = SimpleNamespace(**_seed('rock-salt-nacl'),
                          built_facts_json='{}')
    verdict = crystal_ops.refresh_built_facts(row)
    cached = json.loads(row.built_facts_json)
    check('refresh_built_facts caches the build ON the row',
          verdict['ok'] and cached.get('facts', {}).get('nAtoms') == 8)


def test_refusals():
    print('[honest refusals]')
    base = dict(_seed('aluminum-fcc'))

    bad = dict(base, basis_json=json.dumps(
        [{'element': 'Xx', 'frac': [0, 0, 0]}]))
    verdict = crystal_ops.build_atoms(bad)
    check('unknown element refuses naming basis_json',
          not verdict['ok']
          and verdict['suggestion']['knob'] == 'basis_json')

    bad = dict(base, basis_json='[]')
    verdict = crystal_ops.build_atoms(bad)
    check('empty basis refuses',
          not verdict['ok'] and 'no sites' in verdict['error'])

    bad = dict(base, basis_json=json.dumps(
        [{'element': 'Al', 'frac': [1.4, 0, 0]}]))
    verdict = crystal_ops.build_atoms(bad)
    check('out-of-cell fractional position refuses',
          not verdict['ok'] and 'outside the cell' in verdict['error'])

    bad = dict(base, alpha=0.0)
    verdict = crystal_ops.build_atoms(bad)
    check('degenerate cell angle refuses naming the angle knob',
          not verdict['ok']
          and 'alpha' in verdict['suggestion']['knob'])

    bad = dict(base, cell_a=-1.0)
    verdict = crystal_ops.build_atoms(bad)
    check('negative cell length refuses',
          not verdict['ok'] and 'positive' in verdict['error'])

    bad = dict(base, space_group=300)
    verdict = crystal_ops.build_atoms(bad)
    check('space group 300 refuses naming 1-230',
          not verdict['ok']
          and '1-230' in verdict['suggestion']['action'])

    bad = dict(base, basis_json='not json')
    verdict = crystal_ops.build_atoms(bad)
    check('unparseable basis_json refuses',
          not verdict['ok'] and 'not valid JSON' in verdict['error'])


def test_p1_literal_cell():
    print('[space_group 0 = literal P1 cell]')
    p1 = {
        'name': 'p1-test', 'space_group': 0,
        'cell_a': 3.0, 'cell_b': 3.0, 'cell_c': 3.0,
        'alpha': 90.0, 'beta': 90.0, 'gamma': 90.0,
        'basis_json': json.dumps([
            {'element': 'C', 'frac': [0, 0, 0]},
            {'element': 'C', 'frac': [0.5, 0.5, 0.5]},
        ]),
        'bond_cutoff_scale': 1.15,
    }
    verdict = crystal_ops.structure_facts(p1)
    check('literal cell builds with exactly the listed atoms',
          verdict['ok'] and verdict['facts']['nAtoms'] == 2)


def main():
    test_all_seeds_build()
    test_geometry_invariants()
    test_density_bands()
    test_stoichiometry()
    test_report_payload()
    test_refusals()
    test_p1_literal_cell()
    print(f'\n{PASS} passed, {FAIL} failed')
    return 1 if FAIL else 0


if __name__ == '__main__':
    sys.exit(main())
