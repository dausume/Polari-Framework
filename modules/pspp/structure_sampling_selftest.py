"""
Self-test for pspp.custom.structure_sampling + structure_scene (gsp-2/gsp-3)
— determinism, convergence toward the target Q distribution, charge
balance, honesty counters, and the scene compile.

Run from polari-framework/ (modules/ on the path):
    python3 -m pspp.structure_sampling_selftest
"""

import json
import sys

from pspp.custom.structure_sampling import build_geopolymer_sample
from pspp.custom.structure_scene import (
    TERMINAL_O_MATERIAL, geopolymer_materials, scene_definition,
)

PASS = 0
FAIL = 0

#: a Q2-dominant slurry-ish target used throughout
TARGET = {'Q0': 0.05, 'Q1': 0.15, 'Q2': 0.40, 'Q3': 0.25, 'Q4': 0.15}


def check(label, condition):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f'  ok: {label}')
    else:
        FAIL += 1
        print(f'  FAIL: {label}')


def test_determinism():
    print('[determinism]')
    a = build_geopolymer_sample(TARGET, n_tetrahedra=40, seed=7)
    b = build_geopolymer_sample(TARGET, n_tetrahedra=40, seed=7)
    c = build_geopolymer_sample(TARGET, n_tetrahedra=40, seed=8)
    check('two runs, same seed -> identical clusters',
          a == b)
    check('different seed -> different cluster',
          a['atoms'] != c['atoms'])


def test_convergence():
    print('[achieved -> target with N]')
    def error(n):
        sample = build_geopolymer_sample(TARGET, n_tetrahedra=n,
                                         seed=3)
        return sum(abs(sample['achievedQ'][m] - sample['targetQ'][m])
                   for m in TARGET)
    small, large = error(20), error(300)
    check(f'L1 error shrinks with N ({small:.3f} -> {large:.3f})',
          large < small or large < 0.05)
    sample = build_geopolymer_sample(TARGET, n_tetrahedra=300, seed=3)
    check('achieved fractions sum ~1',
          abs(sum(sample['achievedQ'].values()) - 1.0) < 0.02)
    check('honesty block present',
          sample['honesty']['sampleNotStructure'] is True)


def test_structure_integrity():
    print('[cluster integrity]')
    sample = build_geopolymer_sample(TARGET, n_tetrahedra=60, seed=1,
                                     cation='Na', si_al_ratio=2.0)
    atoms, bonds = sample['atoms'], sample['bonds']
    check('every bond index in range',
          all(0 <= i < len(atoms) and 0 <= j < len(atoms)
              for i, j in bonds))
    centers = [a for a in atoms if a['role'] == 'tetrahedral-center']
    check('one center per tetrahedron',
          len(centers) == sample['counts']['tetrahedra'])
    aluminum = [a for a in centers if a['element'] == 'Al']
    cations = [a for a in atoms
               if a['role'] == 'charge-balancing-cation']
    check(f'one cation per Al ({len(aluminum)} Al)',
          len(cations) == len(aluminum) and len(aluminum) > 0)
    check('cations are Na', all(a['element'] == 'Na'
                                for a in cations))
    # every tetrahedron sees exactly 4 oxygens (bridging shared)
    bridging = sample['counts']['bridgingO']
    terminal = sample['counts']['terminalO']
    check('oxygen arm accounting: 2*bridging + terminal = 4*N',
          2 * bridging + terminal
          == 4 * sample['counts']['tetrahedra'])
    check('loewenstein violations counted (not hidden)',
          'loewensteinViolations' in sample['honesty'])
    # geometry sanity — the collapsed-cluster regression guard:
    # tetrahedral centers must never overlap (bonded target 3.06 A)
    import numpy as np
    pos = np.array([a['position'] for a in centers])
    dist = np.linalg.norm(pos[None, :, :] - pos[:, None, :], axis=-1)
    np.fill_diagonal(dist, np.inf)
    min_tt = float(dist.min())
    check(f'no overlapping tetrahedra (min T-T {min_tt:.2f} A > 2.0)',
          min_tt > 2.0)


def test_refusals():
    print('[refusals]')
    check('empty distribution refuses',
          build_geopolymer_sample({}, seed=1).get('ok') is False)
    check('oversized N refuses',
          build_geopolymer_sample(TARGET, n_tetrahedra=100000,
                                  seed=1).get('ok') is False)
    check('unknown cation refuses',
          build_geopolymer_sample(TARGET, cation='Cs',
                                  seed=1).get('ok') is False)


def test_scene():
    print('[scene compile (gsp-3)]')
    sample = build_geopolymer_sample(TARGET, n_tetrahedra=30, seed=2,
                                     si_al_ratio=2.0)
    verdict = scene_definition(sample, 'geopolymer-sample-test')
    check('scene ok', verdict.get('ok') is True)
    if not verdict.get('ok'):
        return
    scene = verdict['scene']
    definition = json.loads(scene['definition'])
    check('freestandingOnly scene',
          definition['freestandingOnly'] is True)
    entries = definition['freestanding']
    spheres = [e for e in entries if e['shapeRef'] == 'sphere']
    cylinders = [e for e in entries if e['shapeRef'] == 'cylinder']
    check('one sphere per atom',
          len(spheres) == len(sample['atoms']))
    check('one cylinder per bond',
          len(cylinders) == len(sample['bonds']))
    check('terminal O styled distinctly',
          any(e['styleRef'] == TERMINAL_O_MATERIAL for e in spheres))
    check('description says sample-not-structure',
          'Not THE structure' in scene['description'])
    materials = geopolymer_materials(sample)
    names = {m['name'] for m in materials}
    check('materials cover elements + terminal style',
          {'element-si', 'element-o', 'element-na',
           TERMINAL_O_MATERIAL} <= names)


def main():
    test_determinism()
    test_convergence()
    test_structure_integrity()
    test_refusals()
    test_scene()
    print(f'\n{PASS} passed, {FAIL} failed')
    return 1 if FAIL else 0


if __name__ == '__main__':
    sys.exit(main())
