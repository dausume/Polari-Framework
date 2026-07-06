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
    if getattr(row, 'definition_class', '') != 'EngineComputation':
        return {'ok': False, 'name': name,
                'error': f"'{name}' is not an EngineComputation row "
                         f"(definition_class="
                         f"'{getattr(row, 'definition_class', '')}') — only "
                         "engine-backed definitions are executable."}
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
