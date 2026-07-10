"""
@cross-cutting
@module materialsScience.scale_execution
@tags @xc:bindings

EXECUTION of MaterialScaleDefinitions — the step that makes a scale row
computed data instead of a label.

A row whose definition_class is 'EngineComputation' carries in
parameters_json:
    {"engine": "<registry key>", "inputs": {...}}
Executing it dispatches to the engine registry (fem/dft modules — which
themselves ladder local → msci-engines worker → honest refusal), stores
the result back INTO the row (parameters_json['result'] + executed
status), and persists it. The result lives AT the object (object
coherence): inspectable via CRUDE like any other field.

Refusals are never silent: unknown engines list the registry, engine
refusals pass through their suggestions untouched.

@consumers
  - materialsScience.scale_execution_api (POST /api/msci/...)
  - materialsScience.selftest_scale_execution
@see /OVERLAP_MAP.md
"""

import json

from materialsScience.engines import dft_engine, fem_engine
from materialsScience.engines import md_engine, meso_engine
from materialsScience.engines import transport_engine


def _permeability_from_conductivity(result):
    """The k <-> mu Laplace analogy (msci-22): magnetostatic effective
    permeability of a 2-phase composite satisfies the SAME scalar
    Laplace/transport equation the validated thermal homogenization
    solves — only the symbol changes. Rename the outputs honestly so a
    permeability result never masquerades as a conductivity."""
    if not result.get('ok'):
        return result
    renamed = {'ok': True,
               'effectiveMu': result.get('effectiveK'),
               'voigtBoundMu': result.get('voigtBound'),
               'reussBoundMu': result.get('reussBound'),
               'withinBounds': result.get('withinBounds'),
               'actualVolumeFraction': result.get(
                   'actualVolumeFraction'),
               'elements': result.get('elements'),
               'analogy': 'scalar Laplace transport: mu <-> k (same '
                          'engine as fem.effective-conductivity)'}
    return renamed


#: registry key -> callable(dict inputs) -> result dict with 'ok'
ENGINE_REGISTRY = {
    'fem.conduction': lambda inputs: fem_engine.solve_steady_conduction(
        thermal_conductivity=float(inputs.get('thermalConductivity', 0.0)),
        heat_source=float(inputs.get('heatSource', 1.0)),
        refine=int(inputs.get('refine', 4))),
    'dft.molecular-energy': lambda inputs: dft_engine.molecular_energy(
        atoms=inputs.get('atoms', ''),
        basis=inputs.get('basis', '6-31g'),
        xc=inputs.get('xc', 'b3lyp'),
        charge=int(inputs.get('charge', 0)),
        spin=int(inputs.get('spin', 0))),
    'fem.effective-conductivity': lambda inputs:
        fem_engine.effective_conductivity(
            matrix_k=float(inputs.get('matrixK', 0.0)),
            inclusion_k=float(inputs.get('inclusionK', 0.0)),
            volume_fraction=float(inputs.get('volumeFraction', 0.0)),
            refine=int(inputs.get('refine', 5))),
    # Magnetostatics via the k<->mu Laplace analogy (msci-22): the SAME
    # validated homogenization solve computes effective RELATIVE
    # PERMEABILITY of a 2-phase magnetic composite; outputs renamed so
    # the analogy is explicit, never silent.
    'fem.effective-permeability': lambda inputs:
        _permeability_from_conductivity(fem_engine.effective_conductivity(
            matrix_k=float(inputs.get('matrixMu', 0.0)),
            inclusion_k=float(inputs.get('inclusionMu', 0.0)),
            volume_fraction=float(inputs.get('volumeFraction', 0.0)),
            refine=int(inputs.get('refine', 5)))),
    # Percolation (msci-23): the conductive-filler regime continuum
    # homogenization cannot see — classical power law, pure python,
    # always available. For CNT/conductive-particle composites.
    'analytic.percolation-conductivity': lambda inputs:
        transport_engine.percolation_conductivity(
            matrix_sigma=float(inputs.get('matrixSigma', 0.0)),
            filler_sigma=float(inputs.get('fillerSigma', 0.0)),
            volume_fraction=float(inputs.get('volumeFraction', 0.0)),
            percolation_threshold=float(
                inputs.get('percolationThreshold', 0.005)),
            transport_exponent=float(
                inputs.get('transportExponent', 2.0))),
    # The remaining dft_engine surfaces, registered for uniformity so
    # every engine function is template-addressable. Both are
    # capability-gated and refuse honestly when their layer is absent
    # (bulk-structure needs ASE only; total-energy needs pw.x/WITH_QE).
    'dft.bulk-structure': lambda inputs: dft_engine.build_bulk_structure(
        symbol=inputs.get('symbol', ''),
        crystal=inputs.get('crystal') or None,
        lattice_a=(float(inputs['latticeA'])
                   if inputs.get('latticeA') else None)),
    'dft.total-energy': lambda inputs: dft_engine.total_energy(
        symbol=inputs.get('symbol', ''),
        crystal=inputs.get('crystal') or None,
        lattice_a=(float(inputs['latticeA'])
                   if inputs.get('latticeA') else None),
        ecutwfc=float(inputs.get('ecutwfc', 30.0)),
        kpts=tuple(int(k) for k in inputs.get('kpts', (3, 3, 3)))),
    # L3 atomistic MD (msci-25): pure-numpy reduced-unit engines —
    # always available; force-field MD (TraPPE/GAFF) is the named gap.
    'md.lj-melt': lambda inputs: md_engine.lj_melt(
        density=float(inputs.get('density', 0.8)),
        temperature=float(inputs.get('temperature', 1.0)),
        n_particles=int(inputs.get('nParticles', 256)),
        steps=int(inputs.get('steps', 3000)),
        equilibration=int(inputs.get('equilibration', 1000)),
        dt=float(inputs.get('dt', 0.005)),
        thermostat=inputs.get('thermostat', 'langevin'),
        seed=int(inputs.get('seed', 1234))),
    'md.bead-spring-melt': lambda inputs: md_engine.bead_spring_melt(
        chain_length=int(inputs.get('chainLength', 10)),
        n_chains=int(inputs.get('nChains', 20)),
        density=float(inputs.get('density', 0.85)),
        temperature=float(inputs.get('temperature', 1.0)),
        steps=int(inputs.get('steps', 3000)),
        equilibration=int(inputs.get('equilibration', 1000)),
        dt=float(inputs.get('dt', 0.004)),
        seed=int(inputs.get('seed', 1234))),
    # L2 mesoscale (msci-25): rod-network percolation MC + dipolar
    # chaining BD; DPD/hydrodynamics is the named gap.
    'meso.rod-percolation': lambda inputs:
        meso_engine.rod_percolation_threshold(
            aspect_ratio=float(inputs.get('aspectRatio', 20.0)),
            n_rods=int(inputs.get('nRods', 300)),
            trials=int(inputs.get('trials', 8)),
            iterations=int(inputs.get('iterations', 9)),
            seed=int(inputs.get('seed', 1234))),
    'meso.dipolar-chaining': lambda inputs:
        meso_engine.dipolar_chaining(
            coupling_lambda=float(inputs.get('couplingLambda', 4.0)),
            volume_fraction=float(inputs.get('volumeFraction', 0.1)),
            n_particles=int(inputs.get('nParticles', 150)),
            steps=int(inputs.get('steps', 6000)),
            dt=float(inputs.get('dt', 0.002)),
            seed=int(inputs.get('seed', 1234))),
}


def _find_row(manager, name):
    table = (manager.objectTables or {}).get('MaterialScaleDefinition', {})
    rows = table.values() if isinstance(table, dict) else table
    for row in rows:
        if getattr(row, 'name', '') == name:
            return row
    return None


def execute_scale_definition(manager, name):
    """Run the engine computation a MaterialScaleDefinition points at.

    Returns {'ok', 'name', 'engine', 'result'|'error'+'suggestion(s)'}.
    On success the row itself is updated (result stored, status
    partial→defined) and persisted.
    """
    row = _find_row(manager, name)
    if row is None:
        return {'ok': False, 'name': name,
                'error': f"no MaterialScaleDefinition named '{name}'"}
    definition_class = getattr(row, 'definition_class', '')
    if definition_class in ('FEMModelDefinition', 'DFTModelDefinition'):
        # A scale level backed by a configured model definition: run it
        # through the model executor, then store the result on THIS row
        # exactly like an EngineComputation (scale_presence gates and
        # the existing UI see no difference).
        from materialsScience.model_execution import execute_model
        model_report = execute_model(
            manager, getattr(row, 'definition_ref', ''))
        if not model_report.get('ok'):
            return {'ok': False, 'name': name, **{
                k: v for k, v in model_report.items()
                if k not in ('ok',)}}
        try:
            params = json.loads(
                getattr(row, 'parameters_json', '{}') or '{}')
        except Exception:
            params = {}
        params['result'] = model_report.get('result', {})
        params['engine'] = model_report.get('engine', '')
        row.parameters_json = json.dumps(params)
        if getattr(row, 'status', '') == 'partial':
            row.status = 'defined'
        try:
            manager.db.saveInstanceInDB(row)
            persisted = True
        except Exception:
            persisted = False
        return {'ok': True, 'name': name,
                'engine': model_report.get('engine', ''),
                'model': model_report.get('model', ''),
                'result': model_report.get('result', {}),
                'status': getattr(row, 'status', ''),
                'persisted': persisted}
    if definition_class != 'EngineComputation':
        return {'ok': False, 'name': name,
                'error': f"'{name}' is not an executable row "
                         f"(definition_class='{definition_class}') — "
                         "EngineComputation, FEMModelDefinition, and "
                         "DFTModelDefinition rows are executable."}
    try:
        params = json.loads(getattr(row, 'parameters_json', '{}') or '{}')
    except Exception as e:
        return {'ok': False, 'name': name,
                'error': f'parameters_json is not valid JSON: {e}'}

    engineKey = params.get('engine', '')
    runner = ENGINE_REGISTRY.get(engineKey)
    if runner is None:
        return {'ok': False, 'name': name, 'engine': engineKey,
                'error': f"unknown engine '{engineKey}'",
                'suggestion': {
                    'evidence': f'the registry knows: '
                                f'{sorted(ENGINE_REGISTRY)}',
                    'knob': "parameters_json['engine']",
                    'action': 'set it to one of the registry keys',
                }}

    result = runner(params.get('inputs', {}) or {})
    if not result.get('ok'):
        # Pass the engine's own honest refusal through untouched.
        return {'ok': False, 'name': name, 'engine': engineKey, **{
            k: v for k, v in result.items() if k != 'ok'}}

    params['result'] = result
    row.parameters_json = json.dumps(params)
    if getattr(row, 'status', '') == 'partial':
        row.status = 'defined'
    persisted = False
    db = getattr(manager, 'db', None)
    if db is not None:
        try:
            persisted = bool(db.saveInstanceInDB(row))
        except Exception:
            persisted = False
    return {'ok': True, 'name': name, 'engine': engineKey,
            'result': result, 'status': row.status, 'persisted': persisted}
