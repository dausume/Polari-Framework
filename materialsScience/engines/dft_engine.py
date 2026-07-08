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
        'molecularLayer': {'available': False, 'library': 'pyscf',
                           'via': ''},
        'executionLayer': {'available': False, 'binary': 'pw.x',
                           'pseudoDir': os.environ.get('ESPRESSO_PSEUDO', '')},
        'suggestions': [],
    }
    try:
        import pyscf
        report['molecularLayer']['available'] = True
        report['molecularLayer']['via'] = f'local pyscf {pyscf.__version__}'
    except Exception:
        from materialsScience.engines.remote import (
            remote_capability, unavailable_suggestion)
        remote = remote_capability()
        pyscfRemote = (remote or {}).get('engines', {}).get('pyscf', {})
        if pyscfRemote.get('available'):
            report['molecularLayer']['available'] = True
            report['molecularLayer']['via'] = (
                f"msci-engines worker (pyscf {pyscfRemote.get('version')})")
        else:
            report['suggestions'].append(unavailable_suggestion(
                'pyscf is not importable here (Alpine base image) and no '
                'reachable msci-engines worker is configured.'))
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


def molecular_energy(atoms, basis='6-31g', xc='b3lyp', charge=0, spin=0):
    """Molecular DFT total energy — the wax-chemistry workhorse.

    atoms: pyscf geometry string ('C 0 0 0; H 0 0 1.09; ...').

    Engine ladder (each a knob, refusals honest): local pyscf when the
    image has it (Debian workers), else the msci-engines worker via
    MSCI_ENGINES_URL, else a refusal carrying the exact knob to turn.
    """
    try:
        from pyscf import gto, dft as pyscf_dft
        mol = gto.M(atom=atoms, basis=basis, charge=charge, spin=spin,
                    verbose=0)
        mf = pyscf_dft.RKS(mol)
        mf.xc = xc
        energy = mf.kernel()
        result = {'ok': True, 'engine': 'pyscf(local)',
                  'totalEnergyHa': float(energy),
                  'converged': bool(mf.converged), 'basis': basis,
                  'xc': xc, 'atomCount': mol.natm,
                  'electronCount': int(mol.nelectron)}
        result.update(frontier_orbitals_from_scf(mf))
        return result
    except ImportError:
        pass   # Alpine base image — delegate to the engines worker
    except Exception as e:
        return {'ok': False, 'error': f'pyscf failed: {e}'}

    from materialsScience.engines.remote import remote_post
    return remote_post('/dft/molecular-energy', {
        'atoms': atoms, 'basis': basis, 'xc': xc,
        'charge': charge, 'spin': spin})


_HA_TO_EV = 27.211386245988


def frontier_orbitals_from_scf(mf):
    """HOMO/LUMO/gap in eV from a converged SCF (msci-23) — the
    donor/acceptor evidence the semiconductor 'bias-property' analysis
    reads: n-type dopants raise the HOMO (donor states), p-type
    dopants lower the LUMO (acceptor states). Kohn-Sham orbital
    energies — approximate frontier levels, not measured IP/EA (the
    note travels with the numbers). Shared by the local ladder rung
    and the msci-engines worker service."""
    try:
        occupied = [float(e) for e, o in zip(mf.mo_energy, mf.mo_occ)
                    if o > 0]
        virtual = [float(e) for e, o in zip(mf.mo_energy, mf.mo_occ)
                   if o == 0]
        if not occupied or not virtual:
            return {}
        homo = max(occupied) * _HA_TO_EV
        lumo = min(virtual) * _HA_TO_EV
        return {'homoEv': homo, 'lumoEv': lumo, 'gapEv': lumo - homo,
                'frontierNote': 'Kohn-Sham orbital energies — '
                                'approximate frontier levels for '
                                'donor/acceptor comparison, not '
                                'measured IP/EA'}
    except Exception:
        return {}


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
