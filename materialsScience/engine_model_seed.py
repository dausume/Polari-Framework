"""
@module materialsScience.engine_model_seed

Seeds for the engine-model layer:

  SEED_ENGINE_MODEL_TEMPLATES — the 5-row catalog covering every
  ENGINE_REGISTRY entry, with typed section-tagged parameter schemas
  (FEM: domain/materials/boundaryConditions/sourceTerms/mesh/solver;
  DFT: structure/method/accuracy) transcribed from the verified engine
  signatures.

  SEED_FEM_MODELS / SEED_DFT_MODELS — the two configured proof models:
    wax-thermal-continuum   FEM homogenization whose material
                            conductivities are objectRef-BOUND to the
                            live beeswax-carnauba-blend@L1 row (edit
                            the row, the model reads the new values —
                            the object-coherence proof).
    paraffin-quantum-energy DFT molecular energy whose structure/method
                            are bound to the paraffin-wax@L4 row's
                            propane-fragment inputs.

Module-top assertions keep the catalog honest against the registry
(profile-seed pattern): every engine_key exists, every schema key is a
key the registry lambda actually reads.
"""

import json

from materialsScience.scale_execution import ENGINE_REGISTRY

# The camelCase input keys each registry lambda reads — schema keys must
# be a subset (assertion below keeps template and engine in lockstep).
_REGISTRY_INPUT_KEYS = {
    'fem.conduction': {'thermalConductivity', 'heatSource', 'refine'},
    'fem.effective-conductivity': {'matrixK', 'inclusionK',
                                   'volumeFraction', 'refine'},
    'fem.effective-permeability': {'matrixMu', 'inclusionMu',
                                   'volumeFraction', 'refine'},
    'analytic.percolation-conductivity': {
        'matrixSigma', 'fillerSigma', 'volumeFraction',
        'percolationThreshold', 'transportExponent'},
    'dft.molecular-energy': {'atoms', 'basis', 'xc', 'charge', 'spin'},
    'dft.bulk-structure': {'symbol', 'crystal', 'latticeA'},
    'dft.total-energy': {'symbol', 'crystal', 'latticeA', 'ecutwfc',
                         'kpts'},
    'md.lj-melt': {'density', 'temperature', 'nParticles', 'steps',
                   'equilibration', 'dt', 'thermostat', 'seed'},
    'md.bead-spring-melt': {'chainLength', 'nChains', 'density',
                            'temperature', 'steps', 'equilibration',
                            'dt', 'seed'},
    'meso.rod-percolation': {'aspectRatio', 'nRods', 'trials',
                             'iterations', 'seed'},
    'meso.dipolar-chaining': {'couplingLambda', 'volumeFraction',
                              'nParticles', 'steps', 'dt', 'seed'},
}
assert set(_REGISTRY_INPUT_KEYS) <= set(ENGINE_REGISTRY), (
    'engine_model_seed names engines missing from ENGINE_REGISTRY')


def _schema(entries):
    return json.dumps(entries)


SEED_ENGINE_MODEL_TEMPLATES = [
    {
        'name': 'fem-steady-conduction',
        'display_name': 'FEM — steady heat conduction',
        'description': (
            'Steady-state heat conduction on a unit-square domain with '
            'homogeneous Dirichlet boundaries and a uniform volumetric '
            'source (scikit-fem, in-image). Outputs the temperature '
            'field statistics.'
        ),
        'engine_kind': 'fem', 'engine_key': 'fem.conduction',
        'parameter_schema_json': _schema([
            {'section': 'materials', 'key': 'thermalConductivity',
             'type': 'number', 'unit': 'W/m·K', 'required': True,
             'min': 1e-9,
             'description': "the domain material's thermal conductivity"},
            {'section': 'sourceTerms', 'key': 'heatSource',
             'type': 'number', 'unit': 'W/m³', 'required': False,
             'default': 1.0,
             'description': 'uniform volumetric heat source'},
            {'section': 'mesh', 'key': 'refine', 'type': 'integer',
             'required': False, 'default': 4, 'min': 1, 'max': 8,
             'description': 'uniform mesh refinement level'},
        ]),
        'section_map_json': json.dumps({
            'thermalConductivity': 'materials.domain.thermalConductivity',
            'heatSource': 'sourceTerms.heatSource',
            'refine': 'mesh.refine',
        }),
        'outputs_json': json.dumps([
            {'key': 'maxTemperature', 'type': 'number', 'unit': 'K·m²/W',
             'description': 'peak of the normalized temperature field'},
            {'key': 'meanTemperature', 'type': 'number',
             'unit': 'K·m²/W', 'description': 'field mean'},
            {'key': 'degreesOfFreedom', 'type': 'integer',
             'description': 'solver DOF count'},
            {'key': 'elements', 'type': 'integer',
             'description': 'mesh element count'},
        ]),
        'cost_class': 'cheap',
        'capability_requirements_json': json.dumps(['fem']),
        'notes': 'Unit-square/Dirichlet-0 only today — other domains '
                 'and BC types validate as honest refusals.',
        'enabled': True,
    },
    {
        'name': 'fem-effective-conductivity',
        'display_name': 'FEM — 2-phase effective conductivity '
                        '(homogenization)',
        'description': (
            'Numerical homogenization of a 2-phase unit cell: circular '
            'inclusion in a square matrix, unit temperature gradient; '
            'outputs the effective conductivity with its Voigt/Reuss '
            'bounds (Maxwell-Garnett-validated engine).'
        ),
        'engine_kind': 'fem', 'engine_key': 'fem.effective-conductivity',
        'parameter_schema_json': _schema([
            {'section': 'materials', 'key': 'matrixK', 'type': 'number',
             'unit': 'W/m·K', 'required': True, 'min': 1e-9,
             'description': 'matrix-phase thermal conductivity'},
            {'section': 'materials', 'key': 'inclusionK',
             'type': 'number', 'unit': 'W/m·K', 'required': True,
             'min': 1e-9,
             'description': 'inclusion-phase thermal conductivity'},
            {'section': 'domain', 'key': 'volumeFraction',
             'type': 'number', 'required': True, 'min': 1e-9, 'max': 0.6,
             'description': 'inclusion volume fraction — the engine '
                            'constrains to (0, 0.6)'},
            {'section': 'mesh', 'key': 'refine', 'type': 'integer',
             'required': False, 'default': 5, 'min': 1, 'max': 8,
             'description': 'unit-cell mesh refinement level'},
        ]),
        'section_map_json': json.dumps({
            'matrixK': 'materials.matrix.thermalConductivity',
            'inclusionK': 'materials.inclusion.thermalConductivity',
            'volumeFraction': 'domain.inclusion.volumeFraction',
            'refine': 'mesh.refine',
        }),
        'outputs_json': json.dumps([
            {'key': 'effectiveK', 'type': 'number', 'unit': 'W/m·K',
             'description': 'homogenized effective conductivity'},
            {'key': 'voigtBound', 'type': 'number', 'unit': 'W/m·K',
             'description': 'upper (parallel) mixing bound'},
            {'key': 'reussBound', 'type': 'number', 'unit': 'W/m·K',
             'description': 'lower (series) mixing bound'},
            {'key': 'withinBounds', 'type': 'boolean',
             'description': 'sanity: k_eff inside Voigt/Reuss'},
            {'key': 'actualVolumeFraction', 'type': 'number',
             'description': 'meshed inclusion fraction actually used'},
            {'key': 'elements', 'type': 'integer',
             'description': 'mesh element count'},
        ]),
        'cost_class': 'moderate',
        'capability_requirements_json': json.dumps(['fem']),
        'notes': 'wt% is often used as vol% upstream — flag that '
                 'assumption wherever the caller does it.',
        'enabled': True,
    },
    {
        'name': 'fem-effective-permeability',
        'display_name': 'FEM — 2-phase effective permeability '
                        '(magnetostatic homogenization)',
        'description': (
            'Effective RELATIVE PERMEABILITY of a 2-phase unit cell '
            '(magnetic filler in a non/weakly-magnetic matrix) via the '
            'k <-> mu Laplace analogy: magnetostatic scalar-potential '
            'transport is the SAME equation as steady conduction, so '
            'the Maxwell-Garnett-validated homogenization engine '
            'computes it — outputs named in mu so the analogy is '
            'explicit. For SOFT magnetic fillers (flux guides, tuned '
            'magnetic structures); HARD-magnet remanence/coercivity '
            'are hysteresis quantities this engine does NOT model.'
        ),
        'engine_kind': 'fem', 'engine_key': 'fem.effective-permeability',
        'parameter_schema_json': _schema([
            {'section': 'materials', 'key': 'matrixMu', 'type': 'number',
             'unit': 'mu_r', 'required': True, 'min': 1e-9,
             'description': 'matrix relative permeability (~1 for '
                            'ceramics/polymers/geopolymer/silica)'},
            {'section': 'materials', 'key': 'inclusionMu',
             'type': 'number', 'unit': 'mu_r', 'required': True,
             'min': 1e-9,
             'description': 'filler relative permeability (soft '
                            'ferrites: hundreds-thousands)'},
            {'section': 'domain', 'key': 'volumeFraction',
             'type': 'number', 'required': True, 'min': 1e-9, 'max': 0.6,
             'description': 'filler volume fraction — engine-'
                            'constrained to (0, 0.6)'},
            {'section': 'mesh', 'key': 'refine', 'type': 'integer',
             'required': False, 'default': 5, 'min': 1, 'max': 8,
             'description': 'unit-cell mesh refinement level'},
        ]),
        'section_map_json': json.dumps({
            'matrixMu': 'materials.matrix.relativePermeability',
            'inclusionMu': 'materials.inclusion.relativePermeability',
            'volumeFraction': 'domain.inclusion.volumeFraction',
            'refine': 'mesh.refine',
        }),
        'outputs_json': json.dumps([
            {'key': 'effectiveMu', 'type': 'number', 'unit': 'mu_r',
             'description': 'homogenized effective relative '
                            'permeability'},
            {'key': 'voigtBoundMu', 'type': 'number', 'unit': 'mu_r',
             'description': 'upper (parallel) mixing bound'},
            {'key': 'reussBoundMu', 'type': 'number', 'unit': 'mu_r',
             'description': 'lower (series) mixing bound'},
            {'key': 'withinBounds', 'type': 'boolean',
             'description': 'sanity: mu_eff inside the bounds'},
            {'key': 'actualVolumeFraction', 'type': 'number',
             'description': 'meshed filler fraction actually used'},
            {'key': 'elements', 'type': 'integer',
             'description': 'mesh element count'},
        ]),
        'cost_class': 'moderate',
        'capability_requirements_json': json.dumps(['fem']),
        'notes': 'Scalar Laplace analogy — valid for linear '
                 'magnetostatics well below saturation; hysteresis, '
                 'remanence, and saturation are OUT of scope (said '
                 'here, not silently wrong).',
        'enabled': True,
    },
    {
        'name': 'percolation-conductivity',
        'display_name': 'Percolation — conductive-filler composite '
                        'conductivity',
        'description': (
            'Effective ELECTRICAL conductivity across the percolation '
            'transition: below the threshold the composite conducts '
            'like the matrix (isolated filler — the FEM homogenization '
            'regime, confirmed at 1e19 contrast); above it the '
            'connected filler network follows the classical power law '
            'sigma_f*((vf-vf_c)/(1-vf_c))^t. THE model for CNT and '
            'conductive-nanoparticle composites, where homogenization '
            'is blind to the threshold. Pure python, always available.'
        ),
        'engine_kind': 'fem', 'engine_key':
            'analytic.percolation-conductivity',
        'parameter_schema_json': _schema([
            {'section': 'materials', 'key': 'matrixSigma',
             'type': 'number', 'unit': 'S/m', 'required': True,
             'min': 1e-30,
             'description': 'matrix electrical conductivity'},
            {'section': 'materials', 'key': 'fillerSigma',
             'type': 'number', 'unit': 'S/m', 'required': True,
             'min': 1e-30,
             'description': 'filler electrical conductivity (CNT '
                            'axial ~1e6)'},
            {'section': 'domain', 'key': 'volumeFraction',
             'type': 'number', 'required': True, 'min': 1e-9,
             'max': 0.999,
             'description': 'filler volume fraction'},
            {'section': 'domain', 'key': 'percolationThreshold',
             'type': 'number', 'required': False, 'default': 0.005,
             'min': 1e-9, 'max': 0.999,
             'description': 'vf_c — high-aspect CNTs percolate at '
                            '0.0005-0.01 (literature)'},
            {'section': 'solver', 'key': 'transportExponent',
             'type': 'number', 'required': False, 'default': 2.0,
             'min': 0.5, 'max': 4.0,
             'description': 't — ~1.3 (2D) to ~2-3 (3D networks)'},
        ]),
        'section_map_json': json.dumps({
            'matrixSigma': 'materials.matrix.electricalConductivity',
            'fillerSigma': 'materials.inclusion.electricalConductivity',
            'volumeFraction': 'domain.inclusion.volumeFraction',
            'percolationThreshold': 'domain.inclusion.'
                                    'percolationThreshold',
            'transportExponent': 'solver.transportExponent',
        }),
        'outputs_json': json.dumps([
            {'key': 'effectiveSigma', 'type': 'number', 'unit': 'S/m',
             'description': 'effective electrical conductivity'},
            {'key': 'regime', 'type': 'string',
             'description': 'below-threshold | above-threshold'},
            {'key': 'onsetMargin', 'type': 'number',
             'description': 'vf - vf_c (negative = insulating side)'},
            {'key': 'conductivityGain', 'type': 'number',
             'description': 'sigma_eff / sigma_matrix'},
            {'key': 'validity', 'type': 'string',
             'description': 'the honesty line — order-of-magnitude '
                            'analysis, not a measurement'},
        ]),
        'cost_class': 'cheap',
        'capability_requirements_json': '[]',
        'notes': 'Classical percolation is an idealization — interface '
                 'resistance, waviness, and dispersion shift real '
                 'values; the validity line travels with every result.',
        'enabled': True,
    },
    {
        'name': 'dft-molecular-energy',
        'display_name': 'DFT — molecular SCF energy',
        'description': (
            'Kohn-Sham SCF total energy of a molecule (pyscf RKS; '
            'local library or the msci-engines worker). Structure is a '
            'pyscf geometry string; method is basis + XC functional + '
            'charge/spin.'
        ),
        'engine_kind': 'dft', 'engine_key': 'dft.molecular-energy',
        'parameter_schema_json': _schema([
            {'section': 'structure', 'key': 'atoms', 'type': 'string',
             'required': True,
             'description': "pyscf geometry string, e.g. "
                            "'C 0 0 0; H 0.63 0.63 0.63; ...'"},
            {'section': 'method', 'key': 'basis', 'type': 'string',
             'required': False, 'default': '6-31g',
             'description': 'Gaussian basis set (6-31g, cc-pVDZ, …)'},
            {'section': 'method', 'key': 'xc', 'type': 'string',
             'required': False, 'default': 'b3lyp',
             'description': 'exchange-correlation functional'},
            {'section': 'method', 'key': 'charge', 'type': 'integer',
             'required': False, 'default': 0,
             'description': 'total molecular charge'},
            {'section': 'method', 'key': 'spin', 'type': 'integer',
             'required': False, 'default': 0,
             'description': '2S (number of unpaired electrons)'},
        ]),
        'section_map_json': json.dumps({
            'atoms': 'structure.atoms',
            'basis': 'method.basis',
            'xc': 'method.xc',
            'charge': 'method.charge',
            'spin': 'method.spin',
        }),
        'outputs_json': json.dumps([
            {'key': 'totalEnergyHa', 'type': 'number', 'unit': 'Ha',
             'description': 'SCF total energy (Hartree)'},
            {'key': 'converged', 'type': 'boolean',
             'description': 'SCF convergence flag'},
            {'key': 'engine', 'type': 'string',
             'description': 'which ladder rung computed it '
                            '(local pyscf | worker)'},
            {'key': 'atomCount', 'type': 'integer', 'description': ''},
            {'key': 'electronCount', 'type': 'integer',
             'description': ''},
            # Frontier orbitals (msci-23) — the donor/acceptor
            # evidence for semiconductor bias analysis.
            {'key': 'homoEv', 'type': 'number', 'unit': 'eV',
             'description': 'highest occupied Kohn-Sham level (n-type '
                            'dopants raise it)'},
            {'key': 'lumoEv', 'type': 'number', 'unit': 'eV',
             'description': 'lowest unoccupied Kohn-Sham level '
                            '(p-type dopants lower it)'},
            {'key': 'gapEv', 'type': 'number', 'unit': 'eV',
             'description': 'HOMO-LUMO gap (approximate frontier '
                            'levels, not measured IP/EA)'},
        ]),
        'cost_class': 'expensive',
        'capability_requirements_json': json.dumps(
            ['dft.molecularLayer']),
        'notes': 'accuracy.ecutwfc/kpts are plane-wave knobs — ignored '
                 'by molecular calculations (validation notes it).',
        'enabled': True,
    },
    {
        'name': 'dft-bulk-structure',
        'display_name': 'DFT — bulk structure facts (ASE)',
        'description': (
            'Build a bulk crystal structure (ASE) and report its '
            'structural facts — atom/electron counts, cell volume. '
            'Cheap; no SCF.'
        ),
        'engine_kind': 'dft', 'engine_key': 'dft.bulk-structure',
        'parameter_schema_json': _schema([
            {'section': 'structure', 'key': 'symbol', 'type': 'string',
             'required': True,
             'description': "element symbol, e.g. 'Al'"},
            {'section': 'structure', 'key': 'crystal', 'type': 'string',
             'required': False,
             'description': "crystal system ('fcc', 'bcc', …); ASE "
                            'default when omitted'},
            {'section': 'structure', 'key': 'latticeA', 'type': 'number',
             'unit': 'Å', 'required': False,
             'description': 'lattice constant a; ASE default when '
                            'omitted'},
        ]),
        'section_map_json': json.dumps({
            'symbol': 'structure.symbol',
            'crystal': 'structure.crystal',
            'latticeA': 'structure.latticeA',
        }),
        'outputs_json': json.dumps([
            {'key': 'atomCount', 'type': 'integer', 'description': ''},
            {'key': 'electronCount', 'type': 'integer',
             'description': ''},
            {'key': 'cellVolume', 'type': 'number', 'unit': 'Å³',
             'description': 'unit-cell volume'},
        ]),
        'cost_class': 'cheap',
        'capability_requirements_json': json.dumps(
            ['dft.structureLayer']),
        'notes': '',
        'enabled': True,
    },
    {
        'name': 'dft-total-energy',
        'display_name': 'DFT — periodic total energy (Quantum ESPRESSO)',
        'description': (
            'Plane-wave SCF total energy of a bulk crystal via the QE '
            'pw.x execution layer (ASE Espresso calculator). REFUSES '
            'honestly until a WITH_QE engine build + pseudopotentials '
            'are available — the template exists so periodic solids '
            'have their honest home now.'
        ),
        'engine_kind': 'dft', 'engine_key': 'dft.total-energy',
        'parameter_schema_json': _schema([
            {'section': 'structure', 'key': 'symbol', 'type': 'string',
             'required': True, 'description': 'element symbol'},
            {'section': 'structure', 'key': 'crystal', 'type': 'string',
             'required': False, 'description': 'crystal system'},
            {'section': 'structure', 'key': 'latticeA', 'type': 'number',
             'unit': 'Å', 'required': False,
             'description': 'lattice constant a'},
            {'section': 'accuracy', 'key': 'ecutwfc', 'type': 'number',
             'unit': 'Ry', 'required': False, 'default': 30.0,
             'description': 'plane-wave kinetic-energy cutoff'},
            {'section': 'accuracy', 'key': 'kpts', 'type': 'vector',
             'required': False, 'default': [3, 3, 3],
             'description': 'Monkhorst-Pack k-point mesh'},
        ]),
        'section_map_json': json.dumps({
            'symbol': 'structure.symbol',
            'crystal': 'structure.crystal',
            'latticeA': 'structure.latticeA',
            'ecutwfc': 'accuracy.ecutwfc',
            'kpts': 'accuracy.kpts',
        }),
        'outputs_json': json.dumps([
            {'key': 'totalEnergyEv', 'type': 'number', 'unit': 'eV',
             'description': 'SCF total energy'},
            {'key': 'ecutwfc', 'type': 'number', 'unit': 'Ry',
             'description': 'cutoff actually used'},
            {'key': 'kpts', 'type': 'vector',
             'description': 'k-mesh actually used'},
        ]),
        'cost_class': 'expensive',
        'capability_requirements_json': json.dumps(
            ['dft.executionLayer']),
        'notes': 'Needs pw.x locally or a WITH_QE=1 msci-engines build '
                 '+ pseudopotentials.',
        'enabled': True,
    },
    {
        'name': 'md-lj-melt',
        'display_name': 'MD — Lennard-Jones melt (L3 reference fluid)',
        'description': (
            'Atomistic reference: LJ particles in reduced units, '
            'velocity-Verlet + Langevin thermostat, virial pressure. '
            'THE validation rung for every L3 claim — and the '
            'thermodynamic-state probe for simple melts once '
            'epsilon/sigma are chosen with provenance.'
        ),
        'engine_kind': 'md', 'engine_key': 'md.lj-melt',
        'parameter_schema_json': _schema([
            {'section': 'thermodynamicState', 'key': 'density',
             'type': 'number', 'required': True, 'min': 0.01,
             'max': 1.2, 'description': 'reduced density rho*'},
            {'section': 'thermodynamicState', 'key': 'temperature',
             'type': 'number', 'required': True, 'min': 0.1,
             'max': 10.0, 'description': 'reduced temperature T*'},
            {'section': 'system', 'key': 'nParticles',
             'type': 'number', 'required': False, 'default': 256,
             'min': 32, 'max': 2048, 'description': 'particle count'},
            {'section': 'integration', 'key': 'steps',
             'type': 'number', 'required': False, 'default': 3000,
             'min': 200, 'max': 50000, 'description': 'MD steps'},
            {'section': 'integration', 'key': 'equilibration',
             'type': 'number', 'required': False, 'default': 1000,
             'min': 0, 'max': 20000,
             'description': 'discarded equilibration steps'},
            {'section': 'integration', 'key': 'dt', 'type': 'number',
             'required': False, 'default': 0.005, 'min': 0.0005,
             'max': 0.01, 'description': 'reduced timestep'},
            {'section': 'integration', 'key': 'thermostat',
             'type': 'string', 'required': False,
             'default': 'langevin',
             'description': "'langevin' | 'none' (NVE drift check)"},
            {'section': 'integration', 'key': 'seed', 'type': 'number',
             'required': False, 'default': 1234,
             'description': 'RNG seed'},
        ]),
        'section_map_json': json.dumps({
            'density': 'thermodynamicState.density',
            'temperature': 'thermodynamicState.temperature',
            'nParticles': 'system.nParticles',
            'steps': 'integration.steps',
            'equilibration': 'integration.equilibration',
            'dt': 'integration.dt',
            'thermostat': 'integration.thermostat',
            'seed': 'integration.seed',
        }),
        'outputs_json': json.dumps([
            {'key': 'measuredTemperature', 'type': 'number',
             'description': 'sampled kinetic T* (thermostat check)'},
            {'key': 'potentialPerParticle', 'type': 'number',
             'description': 'U*/N'},
            {'key': 'pressure', 'type': 'number',
             'description': 'virial pressure P*'},
            {'key': 'idealGasPressure', 'type': 'number',
             'description': 'rho*T* baseline'},
            {'key': 'validity', 'type': 'string',
             'description': 'reduced-units honesty line'},
        ]),
        'cost_class': 'moderate',
        'capability_requirements_json': json.dumps(['md']),
        'notes': 'Reduced LJ units — mapping to a real material means '
                 'choosing epsilon/sigma WITH provenance; force-field '
                 'MD (TraPPE/GAFF via OpenMM/LAMMPS) is the named gap.',
        'enabled': True,
    },
    {
        'name': 'md-bead-spring-melt',
        'display_name': 'MD — Kremer-Grest bead-spring melt (L3 '
                        'polymer)',
        'description': (
            'Coarse-grained polymer melt: FENE bonds + WCA beads — '
            'chain conformation (Rg, end-to-end, bond length) for '
            'printable-wax-class melts, ~3 CH2 per bead.'
        ),
        'engine_kind': 'md', 'engine_key': 'md.bead-spring-melt',
        'parameter_schema_json': _schema([
            {'section': 'system', 'key': 'chainLength',
             'type': 'number', 'required': True, 'min': 2, 'max': 100,
             'description': 'beads per chain'},
            {'section': 'system', 'key': 'nChains', 'type': 'number',
             'required': True, 'min': 2, 'max': 200,
             'description': 'number of chains'},
            {'section': 'thermodynamicState', 'key': 'density',
             'type': 'number', 'required': False, 'default': 0.85,
             'min': 0.4, 'max': 1.2,
             'description': 'reduced bead density (melt ~0.85)'},
            {'section': 'thermodynamicState', 'key': 'temperature',
             'type': 'number', 'required': False, 'default': 1.0,
             'min': 0.1, 'max': 5.0, 'description': 'reduced T*'},
            {'section': 'integration', 'key': 'steps',
             'type': 'number', 'required': False, 'default': 3000,
             'min': 200, 'max': 50000, 'description': 'MD steps'},
            {'section': 'integration', 'key': 'equilibration',
             'type': 'number', 'required': False, 'default': 1000,
             'min': 0, 'max': 20000,
             'description': 'discarded equilibration steps'},
            {'section': 'integration', 'key': 'dt', 'type': 'number',
             'required': False, 'default': 0.004, 'min': 0.0005,
             'max': 0.008,
             'description': 'reduced timestep (FENE-safe)'},
            {'section': 'integration', 'key': 'seed', 'type': 'number',
             'required': False, 'default': 1234,
             'description': 'RNG seed'},
        ]),
        'section_map_json': json.dumps({
            'chainLength': 'system.chainLength',
            'nChains': 'system.nChains',
            'density': 'thermodynamicState.density',
            'temperature': 'thermodynamicState.temperature',
            'steps': 'integration.steps',
            'equilibration': 'integration.equilibration',
            'dt': 'integration.dt',
            'seed': 'integration.seed',
        }),
        'outputs_json': json.dumps([
            {'key': 'meanBondLength', 'type': 'number',
             'description': 'FENE bond length (KG lit ~0.97 sigma)'},
            {'key': 'radiusOfGyration', 'type': 'number',
             'description': 'chain Rg'},
            {'key': 'endToEndDistance', 'type': 'number',
             'description': 'chain end-to-end distance'},
            {'key': 'measuredTemperature', 'type': 'number',
             'description': 'sampled kinetic T*'},
            {'key': 'validity', 'type': 'string',
             'description': 'coarse-grained honesty line'},
        ]),
        'cost_class': 'moderate',
        'capability_requirements_json': json.dumps(['md']),
        'notes': 'A CHAIN model, not a chemical force field — bead-to-'
                 'monomer mapping carries provenance.',
        'enabled': True,
    },
    {
        'name': 'meso-rod-percolation',
        'display_name': 'Meso — rod-network percolation threshold '
                        '(L2)',
        'description': (
            'Monte-Carlo spanning of soft-core rods: DERIVES the '
            'percolation threshold the L1 CNT conductivity models '
            'take as a literature assumption (0.005). Bisection to '
            '50%% spanning; Balberg slender-rod limit reported.'
        ),
        'engine_kind': 'meso', 'engine_key': 'meso.rod-percolation',
        'parameter_schema_json': _schema([
            {'section': 'system', 'key': 'aspectRatio',
             'type': 'number', 'required': True, 'min': 2,
             'max': 200, 'description': 'rod length/diameter'},
            {'section': 'system', 'key': 'nRods', 'type': 'number',
             'required': False, 'default': 300, 'min': 50,
             'max': 2000,
             'description': 'rods per trial (finite-size knob)'},
            {'section': 'sampling', 'key': 'trials', 'type': 'number',
             'required': False, 'default': 8, 'min': 2, 'max': 32,
             'description': 'MC trials per bisection point'},
            {'section': 'sampling', 'key': 'iterations',
             'type': 'number', 'required': False, 'default': 9,
             'min': 4, 'max': 16,
             'description': 'bisection iterations'},
            {'section': 'sampling', 'key': 'seed', 'type': 'number',
             'required': False, 'default': 1234,
             'description': 'RNG seed'},
        ]),
        'section_map_json': json.dumps({
            'aspectRatio': 'system.aspectRatio',
            'nRods': 'system.nRods',
            'trials': 'sampling.trials',
            'iterations': 'sampling.iterations',
            'seed': 'sampling.seed',
        }),
        'outputs_json': json.dumps([
            {'key': 'percolationThreshold', 'type': 'number',
             'description': 'derived vf_c (upper bound — waviness '
                            'and attraction lower it)'},
            {'key': 'slenderRodLimit', 'type': 'number',
             'description': '0.7/aspect (Balberg 1984)'},
            {'key': 'ratioToLimit', 'type': 'number',
             'description': 'vf_c / slender limit'},
            {'key': 'validity', 'type': 'string',
             'description': 'finite-size + straight-rod honesty '
                            'line'},
        ]),
        'cost_class': 'moderate',
        'capability_requirements_json': json.dumps(['meso']),
        'notes': 'Feeds the L1 percolation models: the derived vf_c '
                 'closes their stated assumption via an objectRef '
                 'binding (msci-26 closing move).',
        'enabled': True,
    },
    {
        'name': 'meso-dipolar-chaining',
        'display_name': 'Meso — dipolar particle chaining (L2 '
                        'magnetics)',
        'description': (
            'Overdamped Brownian dynamics of field-pinned dipoles '
            '(WCA cores): do ferrite particles CHAIN in a melt? '
            'Cluster stats + field alignment + a chainsFormed '
            'verdict — the microstructure question behind tuned '
            'magnetic composites.'
        ),
        'engine_kind': 'meso', 'engine_key': 'meso.dipolar-chaining',
        'parameter_schema_json': _schema([
            {'section': 'system', 'key': 'couplingLambda',
             'type': 'number', 'required': True, 'min': 0, 'max': 20,
             'description': 'dipolar coupling lambda (chaining '
                            'onsets ~2)'},
            {'section': 'system', 'key': 'volumeFraction',
             'type': 'number', 'required': True, 'min': 0.005,
             'max': 0.3, 'description': 'particle volume fraction'},
            {'section': 'system', 'key': 'nParticles',
             'type': 'number', 'required': False, 'default': 150,
             'min': 20, 'max': 600, 'description': 'particle count'},
            {'section': 'integration', 'key': 'steps',
             'type': 'number', 'required': False, 'default': 6000,
             'min': 500, 'max': 40000,
             'description': 'BD steps (low vf needs MORE — '
                            'kinetics-limited)'},
            {'section': 'integration', 'key': 'dt', 'type': 'number',
             'required': False, 'default': 0.002, 'min': 0.0002,
             'max': 0.005, 'description': 'BD timestep'},
            {'section': 'integration', 'key': 'seed',
             'type': 'number', 'required': False, 'default': 1234,
             'description': 'RNG seed'},
        ]),
        'section_map_json': json.dumps({
            'couplingLambda': 'system.couplingLambda',
            'volumeFraction': 'system.volumeFraction',
            'nParticles': 'system.nParticles',
            'steps': 'integration.steps',
            'dt': 'integration.dt',
            'seed': 'integration.seed',
        }),
        'outputs_json': json.dumps([
            {'key': 'meanClusterSize', 'type': 'number',
             'description': 'mean cluster size (particles)'},
            {'key': 'chainedFraction', 'type': 'number',
             'description': 'fraction in chains of >= 3'},
            {'key': 'fieldAlignment', 'type': 'number',
             'description': 'mean cos of chain-field angle'},
            {'key': 'chainsFormed', 'type': 'boolean',
             'description': 'chainedFraction > 0.5 AND alignment '
                            '> 0.6'},
            {'key': 'validity', 'type': 'string',
             'description': 'pinned-dipole + kinetics honesty line'},
        ]),
        'cost_class': 'moderate',
        'capability_requirements_json': json.dumps(['meso']),
        'notes': 'Kinetics-limited below vf ~0.1: read fieldAlignment '
                 '(structure) separately from chainedFraction '
                 '(aggregation kinetics) or raise steps.',
        'enabled': True,
    },
]

# Schema keys must match what each registry lambda reads.
for _tpl in SEED_ENGINE_MODEL_TEMPLATES:
    _keys = {e['key'] for e in json.loads(_tpl['parameter_schema_json'])}
    assert _keys == _REGISTRY_INPUT_KEYS[_tpl['engine_key']], (
        f"{_tpl['name']}: schema keys {_keys} != registry inputs "
        f"{_REGISTRY_INPUT_KEYS[_tpl['engine_key']]}")
    _map_keys = set(json.loads(_tpl['section_map_json']))
    assert _map_keys == _keys, (
        f"{_tpl['name']}: section_map keys != schema keys")


SEED_FEM_MODELS = [{
    'name': 'wax-thermal-continuum',
    'display_name': 'Wax blend — continuum thermal homogenization',
    'description': (
        'Effective thermal conductivity of the beeswax-carnauba blend: '
        'both phase conductivities are BOUND to the live '
        'beeswax-carnauba-blend@L1 row (edit that row, this model '
        'reads the new values). The 20% volume fraction is a literal '
        '(the L0 fraction list is a composition, not a single value).'
    ),
    'physics_ref': 'fem-effective-conductivity',
    'domain_json': json.dumps({
        'shape': 'unit-square',
        'inclusion': {'shape': 'circle',
                      'volumeFraction': {'kind': 'value', 'value': 0.2}},
    }),
    'materials_json': json.dumps({
        'matrix': {'thermalConductivity': {
            'kind': 'objectRef',
            'className': 'MaterialScaleDefinition',
            'name': 'beeswax-carnauba-blend@L1',
            'path': 'parameters_json.inputs.matrixK'}},
        'inclusion': {'thermalConductivity': {
            'kind': 'objectRef',
            'className': 'MaterialScaleDefinition',
            'name': 'beeswax-carnauba-blend@L1',
            'path': 'parameters_json.inputs.inclusionK'}},
    }),
    'boundary_conditions_json': json.dumps([
        {'boundary': 'x-faces', 'type': 'dirichlet',
         'value': 'unit temperature difference'},
    ]),
    'source_terms_json': '{}',
    'mesh_json': json.dumps({'refine': 5}),
    'solver_json': '{}',
    'notes': 'Seeded proof model for the engine-model layer (msci-15).',
    'enabled': True,
}]

SEED_DFT_MODELS = [{
    'name': 'paraffin-quantum-energy',
    'display_name': 'Paraffin fragment — molecular SCF energy',
    'description': (
        'Molecular DFT energy of the paraffin representative fragment '
        '(propane — the honest stand-in the L4 row declares). '
        'Structure and method are BOUND to the paraffin-wax@L4 row.'
    ),
    'calculation_ref': 'dft-molecular-energy',
    'structure_json': json.dumps({
        'kind': 'molecule',
        'atoms': {'kind': 'objectRef',
                  'className': 'MaterialScaleDefinition',
                  'name': 'paraffin-wax@L4',
                  'path': 'parameters_json.inputs.atoms'},
    }),
    'method_json': json.dumps({
        'basis': {'kind': 'objectRef',
                  'className': 'MaterialScaleDefinition',
                  'name': 'paraffin-wax@L4',
                  'path': 'parameters_json.inputs.basis'},
        'xc': {'kind': 'objectRef',
               'className': 'MaterialScaleDefinition',
               'name': 'paraffin-wax@L4',
               'path': 'parameters_json.inputs.xc'},
        'charge': 0,
        'spin': 0,
    }),
    'accuracy_json': '{}',
    'notes': 'Seeded proof model for the engine-model layer (msci-15).',
    'enabled': True,
}]
