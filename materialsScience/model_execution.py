"""
@module materialsScience.model_execution

Execution for FEM/DFT model definitions: capability-gate → resolve
bindings → run the registry engine → persist the result ON the model
row (object coherence — the same idiom execute_scale_definition uses
for EngineComputation rows).

Capability gating happens BEFORE the engine call so expensive-but-
unavailable calculations (dft-total-energy without a WITH_QE worker)
refuse cheaply, passing the capability layer's own suggestions through.
"""

import json
from datetime import datetime, timezone
from typing import Dict

from materialsScience.component_binding import (
    find_row, find_template, resolve_model, validate_model,
)


def _now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def find_model(manager, name):
    """A model definition by name, whichever specialized class holds it.
    Returns (row, class_name) or (None, '')."""
    for class_name in ('FEMModelDefinition', 'DFTModelDefinition',
                       'MDModelDefinition', 'MesoModelDefinition'):
        row = find_row(manager, class_name, name)
        if row is not None:
            return row, class_name
    return None, ''


def check_capability_requirements(template) -> Dict:
    """Map the template's dotted capability requirements onto the
    engines' honest capability() reports. Never raises."""
    try:
        requirements = json.loads(
            getattr(template, 'capability_requirements_json', '') or '[]')
    except (TypeError, ValueError):
        requirements = []
    missing = []
    suggestions = []
    from materialsScience.engines import (dft_engine, fem_engine,
                                          md_engine, meso_engine)
    caps = {'fem': fem_engine.capability(), 'dft': dft_engine.capability(),
            'md': md_engine.capability(),
            'meso': meso_engine.capability()}
    for req in requirements:
        parts = str(req).split('.')
        node = caps.get(parts[0])
        if node is None:
            missing.append({'requirement': req,
                            'error': f"unknown capability root "
                                     f"'{parts[0]}'"})
            continue
        for part in parts[1:]:
            node = (node or {}).get(part)
        available = (node or {}).get('available') \
            if isinstance(node, dict) else None
        if not available:
            missing.append({'requirement': req,
                            'detail': node if isinstance(node, dict)
                            else caps.get(parts[0])})
            layer = caps.get(parts[0]) or {}
            for s in ([layer.get('suggestion')] if layer.get('suggestion')
                      else []) + (layer.get('suggestions') or []):
                if s:
                    suggestions.append(s)
    return {'ok': not missing, 'missing': missing,
            'suggestions': suggestions}


def execute_model(manager, name, stage_context=None) -> Dict:
    """Execute a model definition end to end. Returns
    {'ok', 'model', 'modelClass', 'template', 'engine', 'inputs',
     'resolved', 'result'|'error'+'suggestion(s)', 'executedAt',
     'persisted'}.

    xsim-2: model executes count as sims under the strict single-writer
    policy — a standalone call takes a short lease through the gate;
    stage machinery / scale executes ride the ambient (or
    stage-context-carried) run context as tied children."""
    from simulationLocks.gate import simulation_gate
    from simulationLocks.run_context import from_stage_context
    with simulation_gate(manager, 'model', name,
                         run_context=from_stage_context(stage_context)
                         ) as slot:
        if not slot['ok']:
            return {'ok': False, 'model': name, 'queued': True,
                    'error': slot.get('error'),
                    'position': slot.get('position'),
                    'suggestion': slot.get('suggestion')}
        return _execute_model_body(manager, name, stage_context)


def _execute_model_body(manager, name, stage_context=None) -> Dict:
    model, model_class = find_model(manager, name)
    if model is None:
        return {'ok': False, 'model': name,
                'error': f"no FEMModelDefinition or DFTModelDefinition "
                         f"named '{name}'"}
    if not getattr(model, 'enabled', True):
        return {'ok': False, 'model': name,
                'error': f"'{name}' is disabled (enabled=False is a "
                         'knob on the row)'}
    template_ref = (getattr(model, 'physics_ref', '')
                    or getattr(model, 'calculation_ref', ''))
    template = find_template(manager, template_ref)
    if template is None:
        return {'ok': False, 'model': name,
                'error': f"template '{template_ref}' not found"}

    # Configuration errors refuse before any engine work.
    verdict = validate_model(manager, model)
    config_errors = [f for f in verdict['findings']
                     if f['level'] == 'error']
    if config_errors:
        return {'ok': False, 'model': name, 'template': template_ref,
                'error': 'model configuration invalid',
                'findings': config_errors,
                'suggestions': verdict['suggestions']}

    # Capability gate BEFORE resolving/solving.
    cap = check_capability_requirements(template)
    if not cap['ok']:
        return {'ok': False, 'model': name, 'template': template_ref,
                'engine': getattr(template, 'engine_key', ''),
                'error': 'required capability layer unavailable',
                'missing': cap['missing'],
                'suggestions': cap['suggestions']}

    resolution = resolve_model(manager, model, stage_context)
    if not resolution['ok']:
        return {'ok': False, 'model': name, 'template': template_ref,
                'engine': getattr(template, 'engine_key', ''),
                'error': 'binding resolution refused',
                'refusals': resolution['refusals'],
                'resolved': resolution['resolved']}

    from materialsScience.scale_execution import ENGINE_REGISTRY
    engine_key = getattr(template, 'engine_key', '')
    runner = ENGINE_REGISTRY.get(engine_key)
    if runner is None:
        return {'ok': False, 'model': name, 'template': template_ref,
                'engine': engine_key,
                'error': f"engine '{engine_key}' not in ENGINE_REGISTRY",
                'suggestion': {'evidence': sorted(ENGINE_REGISTRY)}}
    try:
        result = runner(resolution['inputs'])
    except Exception as e:                       # engine crash =
        result = {'ok': False, 'error': str(e)}  # honest refusal
    report = {'ok': bool(result.get('ok')), 'model': name,
              'modelClass': model_class, 'template': template_ref,
              'engine': engine_key,
              'inputs': resolution['inputs'],
              'resolved': resolution['resolved']}
    if result.get('ok'):
        payload = {k: v for k, v in result.items() if k != 'ok'}
        report['result'] = payload
        model.last_result_json = json.dumps(payload)
        model.last_executed_at = _now()
        report['executedAt'] = model.last_executed_at
        try:
            manager.db.saveInstanceInDB(model)
            report['persisted'] = True
        except Exception:
            report['persisted'] = False
    else:
        report['error'] = result.get('error', 'engine refused')
        for k in ('suggestion', 'suggestions'):
            if k in result:
                report[k] = result[k]
    return report
