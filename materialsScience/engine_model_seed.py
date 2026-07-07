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
    'dft.molecular-energy': {'atoms', 'basis', 'xc', 'charge', 'spin'},
    'dft.bulk-structure': {'symbol', 'crystal', 'latticeA'},
    'dft.total-energy': {'symbol', 'crystal', 'latticeA', 'ecutwfc',
                         'kpts'},
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
