"""
@cross-cutting
@module materialsScience.engines.dft_engine
@tags @xc:bindings

Quantum (scale level 4) DFT engine over ASE + Quantum ESPRESSO.

ASE (Atomic Simulation Environment, LGPL) is the pre-existing OO
calculator layer: structures are objects, DFT codes are pluggable
Calculators. Quantum ESPRESSO is the engine per Dustin's research
notes (celldm/Bohr workflow in 12-Computational-Methods; BoltzTraP/
AMSET/Wannier90 ride on QE output later).

Deliberate split of capability:
  - STRUCTURE layer (ASE importable): build crystal structures, count
    electrons, prepare QE input — works everywhere the image runs.
  - EXECUTION layer (pw.x binary + pseudopotentials present): actually
    run the SCF. The QE binary is NOT baked into the backend image
    (size); capability() says so honestly and points at the knob.
"""

import os
import shutil


def capability():
    """Honest two-layer capability report — never raises."""
    report = {
        'structureLayer': {'available': False, 'library': 'ase',
                           'version': ''},
        'executionLayer': {'available': False, 'binary': 'pw.x',
                           'pseudoDir': os.environ.get('ESPRESSO_PSEUDO', '')},
        'suggestions': [],
    }
    try:
        import ase
        report['structureLayer']['available'] = True
        report['structureLayer']['version'] = getattr(
            ase, '__version__', 'unknown')
    except Exception as e:
        report['suggestions'].append({
            'evidence': f'import ase failed: {e}',
            'knob': 'requirements.txt (ase) + image rebuild',
            'action': 'Rebuild the backend image — ase==3.24.0 is already '
                      'in requirements.txt.',
        })

    pwPath = shutil.which('pw.x')
    if pwPath:
        report['executionLayer']['available'] = True
        report['executionLayer']['path'] = pwPath
        if not report['executionLayer']['pseudoDir']:
            report['suggestions'].append({
                'evidence': 'pw.x found but ESPRESSO_PSEUDO is unset — '
                            'SCF runs need pseudopotential files.',
                'knob': 'ESPRESSO_PSEUDO env var (+ a mounted pseudo dir)',
                'action': 'Mount a pseudopotential directory (e.g. SSSP) '
                          'and set ESPRESSO_PSEUDO to it.',
            })
    else:
        report['suggestions'].append({
            'evidence': 'pw.x (Quantum ESPRESSO) not on PATH in this '
                        'container.',
            'knob': 'backend Dockerfile (apt quantum-espresso) or a '
                    'dedicated dft-worker service',
            'action': 'Add QE to the image or run a dft-worker sidecar; '
                      'the structure layer keeps working either way.',
        })
    return report


def build_bulk_structure(symbol, crystal=None, lattice_a=None):
    """Build a bulk crystal as an ASE Atoms object (structure layer).

    Returns {'ok': True, 'symbol', 'crystal', 'atomCount',
    'electronCount', 'cellVolume'} or an honest refusal with the
    capability suggestions. electronCount is what DensityFunctionalMaterial
    rows store — a level-4 MaterialScaleDefinition can point its
    parameters at this output.
    """
    cap = capability()
    if not cap['structureLayer']['available']:
        return {'ok': False, 'error': 'ASE unavailable',
                'suggestions': cap['suggestions']}
    from ase.build import bulk
    from ase.data import atomic_numbers

    kwargs = {}
    if crystal:
        kwargs['crystalstructure'] = crystal
    if lattice_a:
        kwargs['a'] = lattice_a
    try:
        atoms = bulk(symbol, **kwargs)
    except Exception as e:
        return {'ok': False, 'error': f'ase.build.bulk failed: {e}'}
    return {
        'ok': True,
        'symbol': symbol,
        'crystal': crystal or 'default',
        'atomCount': len(atoms),
        'electronCount': int(sum(atomic_numbers[a.symbol] for a in atoms)),
        'cellVolume': float(atoms.get_volume()),
    }


def total_energy(symbol, crystal=None, lattice_a=None, ecutwfc=30.0,
                 kpts=(3, 3, 3)):
    """SCF total energy via QE (execution layer) — or an honest refusal
    carrying the exact suggestions when pw.x / pseudopotentials are
    missing. Parameters mirror DensityFunctionalMaterial fields."""
    cap = capability()
    if not cap['executionLayer']['available'] \
            or not cap['executionLayer']['pseudoDir']:
        return {'ok': False,
                'error': 'DFT execution layer unavailable',
                'suggestions': cap['suggestions']}
    from ase.build import bulk
    from ase.calculators.espresso import Espresso, EspressoProfile

    kwargs = {}
    if crystal:
        kwargs['crystalstructure'] = crystal
    if lattice_a:
        kwargs['a'] = lattice_a
    atoms = bulk(symbol, **kwargs)
    profile = EspressoProfile(
        command=cap['executionLayer']['path'],
        pseudo_dir=cap['executionLayer']['pseudoDir'])
    atoms.calc = Espresso(
        profile=profile,
        input_data={'system': {'ecutwfc': ecutwfc}},
        kpts=kpts)
    try:
        energy = atoms.get_potential_energy()
    except Exception as e:
        return {'ok': False, 'error': f'QE SCF failed: {e}'}
    return {'ok': True, 'symbol': symbol, 'totalEnergyEv': float(energy),
            'ecutwfc': ecutwfc, 'kpts': list(kpts)}
