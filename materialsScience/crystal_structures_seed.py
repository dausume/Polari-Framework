"""
@module materialsScience.crystal_structures_seed

Seed CrystalStructureDefinition rows (ssp-1) — canonical, literature-
parameterized structures for materials the basis already knows, plus
two reference structures (Al, NaCl) kept as validation workhorses.
Every lattice constant carries its provenance; Wyckoff coordinates
state the origin setting their source used. All eight were built and
checked against literature density / nearest-neighbor values on
2026-07-23 (see selftest_crystal_structures for the bands).

@consumers
  - polariServer seed loop ('CrystalStructureDefinition' tuple)
  - materialsScience.selftest_crystal_structures
"""

import json

_PROV = 'ssp-1 literature transcription 2026-07-23'


def _structure(name, display, material, sg, cellpar, basis, *,
               setting=1, bond_scale=1.15, description='', notes=''):
    a, b, c, alpha, beta, gamma = cellpar
    return {
        'name': name, 'display_name': display,
        'description': description, 'material_name': material,
        'space_group': sg, 'space_group_setting': setting,
        'cell_a': a, 'cell_b': b, 'cell_c': c,
        'alpha': alpha, 'beta': beta, 'gamma': gamma,
        'basis_json': json.dumps(basis),
        'bond_cutoff_scale': bond_scale,
        'provenance_id': _PROV, 'notes': notes,
    }


SEED_CRYSTAL_STRUCTURES = [
    _structure(
        'silicon-diamond', 'Silicon (diamond cubic)', 'silicon',
        227, [5.431, 5.431, 5.431, 90, 90, 90],
        [{'element': 'Si', 'frac': [0, 0, 0], 'site': '8a'}],
        description='Diamond-cubic silicon — the band-structure '
                    'workhorse for the L4 periodic-DFT rung (ssp-5).',
        notes='a = 5.431 A (CODATA/standard value, 300 K). '
              'Fd-3m origin setting 1: Si at 8a (0,0,0).'),
    _structure(
        'aluminum-fcc', 'Aluminum (fcc)', '',
        225, [4.050, 4.050, 4.050, 90, 90, 90],
        [{'element': 'Al', 'frac': [0, 0, 0], 'site': '4a'}],
        bond_scale=1.2,
        description='Face-centered cubic aluminum — reference '
                    'structure (no material identity yet); the '
                    'lattice-constant/EOS validation case named in '
                    'FEM_DFT_LIBRARY_OPTIONS.md.',
        notes='a = 4.050 A (lit. 4.0495 A, 298 K). Metallic: the fcc '
              'nearest neighbor (a/sqrt(2) = 2.864 A) sits past '
              '1.15x the covalent-radius sum, hence the 1.2 cutoff '
              'knob.'),
    _structure(
        'alpha-iron-bcc', 'alpha-Iron (bcc)', 'plain-bio-steel',
        229, [2.866, 2.866, 2.866, 90, 90, 90],
        [{'element': 'Fe', 'frac': [0, 0, 0], 'site': '2a'}],
        bond_scale=1.1,
        description='Body-centered cubic alpha-iron — the base phase '
                    'of the bio-steel identities.',
        notes='a = 2.866 A (lit. 2.8665 A, 298 K). HONESTY: steel is '
              'a polycrystalline alloy with carbon interstitials and '
              'grain structure (L2 — a named gap); this row is the '
              'pure alpha-Fe unit cell only. Cutoff 1.1 keeps the '
              '8 first-shell neighbors (2.482 A) while the 6 '
              'second-shell atoms (2.866 A) stay unbonded.'),
    _structure(
        'nickel-fcc', 'Nickel (fcc)', 'nickel-metal',
        225, [3.524, 3.524, 3.524, 90, 90, 90],
        [{'element': 'Ni', 'frac': [0, 0, 0], 'site': '4a'}],
        bond_scale=1.2,
        description='Face-centered cubic nickel.',
        notes='a = 3.524 A (lit. 3.5240 A, 298 K).'),
    _structure(
        'rock-salt-nacl', 'Sodium chloride (rock salt)', '',
        225, [5.640, 5.640, 5.640, 90, 90, 90],
        [{'element': 'Na', 'frac': [0, 0, 0], 'site': '4a'},
         {'element': 'Cl', 'frac': [0.5, 0.5, 0.5], 'site': '4b'}],
        description='Rock-salt NaCl — the two-element teaching case '
                    '(ionic bonding, 6-fold octahedral coordination).',
        notes='a = 5.640 A (lit. 5.6402 A, 298 K). Reference '
              'structure, no material identity.'),
    _structure(
        'magnetite-spinel', 'Magnetite (inverse spinel)',
        'feox-nanoparticle',
        227, [8.396, 8.396, 8.396, 90, 90, 90],
        [{'element': 'Fe', 'frac': [0.125, 0.125, 0.125],
          'site': '8a'},
         {'element': 'Fe', 'frac': [0.5, 0.5, 0.5], 'site': '16d'},
         {'element': 'O', 'frac': [0.2549, 0.2549, 0.2549],
          'site': '32e'}],
        setting=2,
        description='Fe3O4 inverse spinel — the crystal behind the '
                    'LASiS FeOx nanoparticles and the ferrite '
                    'magnetic-composite work.',
        notes='a = 8.396 A, O parameter x = 0.2549 (Fd-3m ORIGIN '
              'CHOICE 2 — the setting literature Wyckoff tables '
              'use: Fe 8a (1/8,1/8,1/8), Fe 16d (1/2,1/2,1/2), '
              'O 32e). 56-atom cell, Z = 8. HONESTY: site charge '
              'ordering (Fe2+/Fe3+ on 16d) is electronic structure, '
              'not geometry — out of scope until the L4 rung.'),
    _structure(
        'corundum-alumina', 'Corundum (alpha-Al2O3)',
        'alumina-ceramic',
        167, [4.759, 4.759, 12.991, 90, 90, 120],
        [{'element': 'Al', 'frac': [0, 0, 0.3523], 'site': '12c'},
         {'element': 'O', 'frac': [0.3064, 0, 0.25], 'site': '18e'}],
        description='alpha-Al2O3 corundum, hexagonal setting of '
                    'R-3c — the crystal behind the alumina-ceramic '
                    'identity and the rhombohedral test case.',
        notes='a = 4.759 A, c = 12.991 A (hexagonal axes, 298 K); '
              'Al z = 0.3523, O x = 0.3064. 30-atom hexagonal cell, '
              'Z = 6. HONESTY: the sintered ceramic is '
              'polycrystalline with porosity (the L1 rows model '
              'that); this is the single-crystal lattice.'),
    _structure(
        'graphite-hexagonal', 'Graphite (Bernal AB)',
        'carbon-nanotube',
        194, [2.461, 2.461, 6.708, 90, 90, 120],
        [{'element': 'C', 'frac': [0, 0, 0.25], 'site': '2b'},
         {'element': 'C', 'frac': [1 / 3, 2 / 3, 0.25],
          'site': '2c'}],
        description='Bernal AB-stacked hexagonal graphite — the '
                    'parent sheet structure of the CNT identity.',
        notes='a = 2.461 A, c = 6.708 A (298 K); in-plane C-C '
              '1.421 A. HONESTY: a nanotube is this sheet ROLLED — '
              'chirality/curvature are not captured by the flat '
              'parent lattice; the CNT fragment-DFT models carry '
              'that caveat already. Interlayer bonding is van der '
              'Waals and correctly falls outside the covalent '
              'cutoff (bonds stay in-plane).'),
]
