"""
@module materialsScience.crystal_ops

Build + measure CrystalStructureDefinition rows (ssp-1): row/dict ->
ASE Atoms (space-group orbit expansion or literal P1 cell), headline
facts (formula, volume, density, nearest-neighbor distance), and the
bond list under the row's covalent-radius cutoff knob.

Pure functions over plain data — rows and dicts both work (the
window_dict idiom). Every invalid input is an honest refusal naming
the knob; nothing raises for bad user data.

@consumers
  - materialsScience.crystal_structure_api
  - materialsScience.crystal_snapshot (ssp-2 scene compiler)
  - materialsScience.selftest_crystal_structures
"""

import json

#: g/cm^3 per (amu / Angstrom^3) — one atomic mass unit per cubic
#: Angstrom in grams per cubic centimeter.
AMU_PER_A3_TO_G_CM3 = 1.66053906660

_MAX_SPACE_GROUP = 230


def structure_dict(row):
    """Plain dict view of a CrystalStructureDefinition row OR dict.
    Numeric fields fall back to their default only when absent/None —
    an explicit 0 stays 0 so validation can refuse it honestly.
    Idempotent: an already-converted dict passes through unchanged."""
    if isinstance(row, dict) and 'cellpar' in row:
        return row
    get = (row.get if isinstance(row, dict)
           else lambda k, d=None: getattr(row, k, d))

    def num(key, default, cast=float):
        value = get(key, None)
        return cast(default if value is None or value == ''
                    else value)

    return {
        'name': get('name', '') or '',
        'materialName': get('material_name', '') or '',
        'spaceGroup': num('space_group', 0, int),
        'setting': num('space_group_setting', 1, int),
        'cellpar': [num('cell_a', 0.0), num('cell_b', 0.0),
                    num('cell_c', 0.0), num('alpha', 90.0),
                    num('beta', 90.0), num('gamma', 90.0)],
        'basisJson': get('basis_json', '[]') or '[]',
        'bondCutoffScale': num('bond_cutoff_scale', 1.15),
    }


def _refuse(error, knob, action):
    return {'ok': False, 'error': error,
            'suggestion': {'knob': knob, 'action': action}}


def _parse_basis(struct):
    try:
        basis = json.loads(struct['basisJson'])
    except (TypeError, ValueError) as e:
        return None, _refuse(f'basis_json is not valid JSON: {e}',
                             'basis_json',
                             'store a JSON list of '
                             '{"element", "frac": [x, y, z]} sites')
    if not isinstance(basis, list) or not basis:
        return None, _refuse('basis_json holds no sites', 'basis_json',
                             'add at least one basis site '
                             '{"element": "Si", "frac": [0, 0, 0]}')
    from ase.data import chemical_symbols
    known = set(chemical_symbols[1:])
    for i, site in enumerate(basis):
        element = (site or {}).get('element', '')
        frac = (site or {}).get('frac', None)
        if element not in known:
            return None, _refuse(
                f"basis site {i} names unknown element {element!r}",
                'basis_json',
                'use a periodic-table symbol (case-sensitive, '
                "e.g. 'Fe')")
        if (not isinstance(frac, (list, tuple)) or len(frac) != 3
                or not all(isinstance(v, (int, float)) for v in frac)):
            return None, _refuse(
                f'basis site {i} ({element}) has no [x, y, z] '
                'fractional position', 'basis_json',
                'give "frac" as three numbers in [0, 1)')
        if not all(-1e-9 <= float(v) < 1.0 + 1e-9 for v in frac):
            return None, _refuse(
                f'basis site {i} ({element}) lies outside the cell: '
                f'frac={list(frac)}', 'basis_json',
                'fractional coordinates belong in [0, 1) — wrap the '
                'position into the cell')
    return basis, None


def _validate_cell(struct):
    a, b, c, alpha, beta, gamma = struct['cellpar']
    if min(a, b, c) <= 0:
        return _refuse(f'cell lengths must be positive '
                       f'(a={a}, b={b}, c={c})',
                       'cell_a/cell_b/cell_c',
                       'set the conventional cell lengths in Angstrom')
    if not all(0 < ang < 180 for ang in (alpha, beta, gamma)):
        return _refuse(f'cell angles must lie in (0, 180) degrees '
                       f'(alpha={alpha}, beta={beta}, gamma={gamma})',
                       'alpha/beta/gamma',
                       'set the conventional cell angles in degrees')
    sg = struct['spaceGroup']
    if not 0 <= sg <= _MAX_SPACE_GROUP:
        return _refuse(f'space_group {sg} is not an International '
                       f'Tables number', 'space_group',
                       'use 1-230, or 0 to take basis_json as the '
                       'literal full cell (no symmetry expansion)')
    return None


def build_atoms(row):
    """Build the conventional cell -> {'ok': True, 'atoms': Atoms}
    or an honest refusal dict."""
    struct = structure_dict(row)
    cell_refusal = _validate_cell(struct)
    if cell_refusal is not None:
        return cell_refusal
    basis, refusal = _parse_basis(struct)
    if refusal is not None:
        return refusal
    symbols = [site['element'] for site in basis]
    positions = [[float(v) for v in site['frac']] for site in basis]
    try:
        if struct['spaceGroup'] == 0:
            from ase import Atoms
            atoms = Atoms(symbols=symbols, scaled_positions=positions,
                          cell=struct['cellpar'], pbc=True)
        else:
            from ase.spacegroup import crystal
            atoms = crystal(
                symbols, basis=positions,
                spacegroup=struct['spaceGroup'],
                setting=struct['setting'],
                cellpar=struct['cellpar'],
                onduplicates='warn')
    except Exception as e:
        return _refuse(
            f'ASE could not build the structure: {e}',
            'space_group / space_group_setting / basis_json',
            'check that the Wyckoff coordinates match the stated '
            'space group and origin setting')
    return {'ok': True, 'atoms': atoms}


#: Conventional -> primitive cell cut vectors per centering letter
#: (the standard crystallographic centering matrices; R uses the
#: obverse hexagonal setting). 'P' needs no reduction.
CENTERING_CUTS = {
    'F': ((0, 0.5, 0.5), (0.5, 0, 0.5), (0.5, 0.5, 0)),
    'I': ((-0.5, 0.5, 0.5), (0.5, -0.5, 0.5), (0.5, 0.5, -0.5)),
    'A': ((1, 0, 0), (0, 0.5, 0.5), (0, -0.5, 0.5)),
    'B': ((0.5, 0, 0.5), (0, 1, 0), (-0.5, 0, 0.5)),
    'C': ((0.5, 0.5, 0), (-0.5, 0.5, 0), (0, 0, 1)),
    'R': ((2 / 3, 1 / 3, 1 / 3), (-1 / 3, 1 / 3, 1 / 3),
          (-1 / 3, -2 / 3, 1 / 3)),
}


def primitive_atoms(atoms, space_group):
    """Reduce a conventional cell to its primitive cell using the
    space group's centering letter (verified: fcc 4->1, bcc 2->1,
    diamond 8->2, spinel 56->14, corundum 30->10). space_group 0 or a
    P group returns the atoms unchanged."""
    if not space_group:
        return atoms
    try:
        from ase.spacegroup import Spacegroup
        letter = Spacegroup(int(space_group)).symbol.strip()[0]
    except Exception:
        return atoms
    vectors = CENTERING_CUTS.get(letter)
    if vectors is None:
        return atoms
    from ase.build import cut
    return cut(atoms, a=vectors[0], b=vectors[1], c=vectors[2])


def bond_pairs(atoms, cutoff_scale):
    """Bonded atom pairs [(i, j, distance)] with i < j, under the
    covalent-radius cutoff: bonded when
    d(i, j) <= cutoff_scale * (r_cov_i + r_cov_j)."""
    from ase.data import covalent_radii
    from ase.neighborlist import neighbor_list
    cutoffs = covalent_radii[atoms.numbers] * float(cutoff_scale)
    i_list, j_list, d_list = neighbor_list('ijd', atoms, cutoffs)
    pairs = []
    for i, j, d in zip(i_list, j_list, d_list):
        if i < j:
            pairs.append((int(i), int(j), round(float(d), 4)))
    pairs.sort()
    return pairs


def structure_facts(row):
    """Headline facts of a built structure — {'ok': True, 'facts': {}}
    or the build refusal passed through."""
    struct = structure_dict(row)
    built = build_atoms(row)
    if not built['ok']:
        return built
    atoms = built['atoms']
    volume = float(atoms.get_volume())
    density = (float(atoms.get_masses().sum()) / volume
               * AMU_PER_A3_TO_G_CM3)
    bonds = bond_pairs(atoms, struct['bondCutoffScale'])
    nn = min((d for _, _, d in bonds), default=None)
    first_atom_bonds = sum(1 for i, j, _ in bonds if 0 in (i, j))
    facts = {
        'formula': atoms.get_chemical_formula(),
        'nAtoms': len(atoms),
        'spaceGroup': struct['spaceGroup'],
        'cellpar': [round(v, 4) for v in struct['cellpar']],
        'cellVolumeA3': round(volume, 3),
        'densityGcm3': round(density, 3),
        'nearestNeighborA': nn,
        'coordinationOfAtom0': first_atom_bonds,
        'bondCount': len(bonds),
        'bondCutoffScale': struct['bondCutoffScale'],
        'bondRule': 'bonded when d <= scale * (r_cov_i + r_cov_j); '
                    'the scale is a knob on the row — coordination '
                    'counts follow it, they are not ground truth',
    }
    return {'ok': True, 'facts': facts, 'atoms': atoms, 'bonds': bonds}


def atoms_payload(atoms):
    """The built cell as plain JSON-ready data: cell vectors, per-atom
    symbols + fractional and cartesian positions."""
    cell = [[round(float(v), 5) for v in row] for row in atoms.cell]
    scaled = atoms.get_scaled_positions(wrap=True)
    cart = atoms.get_positions(wrap=True)
    return {
        'cell': cell,
        'atoms': [
            {'index': i,
             'element': atoms[i].symbol,
             'frac': [round(float(v), 5) for v in scaled[i]],
             'cart': [round(float(v), 5) for v in cart[i]]}
            for i in range(len(atoms))
        ],
    }


def build_report(row):
    """Everything the API/scene needs in one pass: facts + atom list +
    bonds — or the refusal."""
    result = structure_facts(row)
    if not result['ok']:
        return result
    payload = atoms_payload(result['atoms'])
    return {'ok': True,
            'facts': result['facts'],
            'cell': payload['cell'],
            'atoms': payload['atoms'],
            'bonds': [{'i': i, 'j': j, 'distanceA': d}
                      for i, j, d in result['bonds']]}


def refresh_built_facts(row, manager=None):
    """Recompute and cache the build on the row's built_facts_json
    (persisting when a manager with a db is supplied). Returns the
    build_report verdict."""
    report = build_report(row)
    if report['ok']:
        cache = {k: report[k] for k in ('facts', 'cell', 'atoms',
                                        'bonds')}
        try:
            row.built_facts_json = json.dumps(cache)
        except (AttributeError, TypeError):
            pass
        db = getattr(manager, 'db', None)
        if db is not None:
            try:
                db.saveInstanceInDB(row)
            except Exception:
                pass
    return report
