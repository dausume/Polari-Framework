"""
@module materialsScience.component_binding

Binding validation + resolution for FEM/DFT model definitions — the
seam that makes a model definition CONFIGURATION rather than data
entry ([[object-coherence]]): a slot's value may live on another
object in the tree, and editing THAT object changes what the next
execution reads.

Binding kinds (anywhere inside a model's section JSON; bare literals
are treated as {"kind": "value"} for ergonomics):
    {"kind": "value", "value": ...}
    {"kind": "objectRef", "className": ..., "name": ...,
     "path": "parameters_json.inputs.matrixK"}
        — find the row by class+name in manager.objectTables, then walk
          the dotted path: attributes first; any string value along the
          way is json.loads'd and walked as dict keys / integer list
          indices. Refusals list the keys that WERE available.
    {"kind": "stageDerived", "stage": "<stageKey>", "key": "<flatKey>"}
        — resolved from a stage-context dict (built by the msim stage
          machinery in msci-16); absent context refuses with "run/gate
          the upstream stage first".

`validate_model` checks a model's sections against its template's
typed schema (required/type/min/max + FEM domain/BC honesty).
`resolve_model` produces the engine-input dict with per-param
provenance and per-param honest refusals.
"""

import json
from typing import Any, Dict, List, Optional, Tuple


def _parse(blob, default):
    try:
        parsed = json.loads(blob or '')
        return parsed if isinstance(parsed, type(default)) else default
    except (TypeError, ValueError):
        return default


def _rows(manager, class_name):
    table = (getattr(manager, 'objectTables', None) or {}).get(
        class_name, {}) or {}
    return list(table.values()) if isinstance(table, dict) else list(table)


def find_row(manager, class_name, name):
    return next((r for r in _rows(manager, class_name)
                 if getattr(r, 'name', '') == name), None)


def find_template(manager, name):
    return find_row(manager, 'EngineModelTemplate', name)


# ---------------------------------------------------------------------
# Section access + binding resolution
# ---------------------------------------------------------------------

_MODEL_SECTION_FIELDS = {
    # FEMModelDefinition sections
    'domain': 'domain_json',
    'materials': 'materials_json',
    'boundaryConditions': 'boundary_conditions_json',
    'sourceTerms': 'source_terms_json',
    'mesh': 'mesh_json',
    'solver': 'solver_json',
    # DFTModelDefinition sections
    'structure': 'structure_json',
    'method': 'method_json',
    'accuracy': 'accuracy_json',
    # MD / Meso model sections (msci-26)
    'system': 'system_json',
    'thermodynamicState': 'thermodynamic_state_json',
    'integration': 'integration_json',
    'sampling': 'sampling_json',
}


def _section_value(model_row, dotted_path):
    """Fetch the RAW (possibly binding-dict) value at a section path
    like 'materials.matrix.thermalConductivity'. Returns (found, value,
    available) — `available` lists the keys present at the deepest
    reached level (refusal evidence)."""
    parts = dotted_path.split('.')
    section_field = _MODEL_SECTION_FIELDS.get(parts[0])
    if section_field is None:
        return False, None, sorted(_MODEL_SECTION_FIELDS)
    container = _parse(getattr(model_row, section_field, '') or '', {})
    if not isinstance(container, (dict, list)):
        return False, None, []
    node = container
    for part in parts[1:]:
        if isinstance(node, list):
            try:
                node = node[int(part)]
                continue
            except (ValueError, IndexError):
                return False, None, [f'[0..{len(node) - 1}]']
        if not isinstance(node, dict) or part not in node:
            available = sorted(node) if isinstance(node, dict) else []
            return False, None, available
        node = node[part]
    return True, node, []


def _is_binding(value) -> bool:
    return isinstance(value, dict) and 'kind' in value


def resolve_binding(manager, value, stage_context=None
                    ) -> Tuple[bool, Any, Optional[Dict]]:
    """Resolve one raw section value (literal or binding dict) →
    (ok, concrete_value, refusal|None). Provenance rides on the refusal
    or is added by the caller."""
    if not _is_binding(value):
        return True, value, None
    kind = value.get('kind')
    if kind == 'value':
        return True, value.get('value'), None
    if kind == 'objectRef':
        if 'authority' in value:
            # xsim-1: authority-carrying refs ride the ONE resolution
            # ladder; bare refs keep the untouched local path below.
            from polariRefs.resolver import resolve_ref_value
            return resolve_ref_value(manager, value, stage_context)
        class_name = value.get('className', '')
        row_name = value.get('name', '')
        path = value.get('path', '')
        row = find_row(manager, class_name, row_name)
        if row is None:
            return False, None, {
                'error': f"objectRef: no {class_name} named '{row_name}'",
                'suggestion': {'knob': 'binding.name',
                               'action': 'point it at an existing row'}}
        node: Any = row
        for part in path.split('.') if path else []:
            if isinstance(node, str):
                # A JSON-blob field along the path: parse and keep
                # walking; a non-JSON string cannot be descended into.
                try:
                    node = json.loads(node)
                except (TypeError, ValueError):
                    return False, None, {
                        'error': f"objectRef path '{path}' hit a "
                                 f"non-JSON string before '{part}'"}
            if isinstance(node, list):
                try:
                    node = node[int(part)]
                    continue
                except (ValueError, IndexError):
                    return False, None, {
                        'error': f"objectRef path '{path}' failed at "
                                 f"'{part}' (list of {len(node)})"}
            if isinstance(node, dict):
                if part not in node:
                    return False, None, {
                        'error': f"objectRef path '{path}' failed at "
                                 f"'{part}'",
                        'availableKeys': sorted(node)[:20]}
                node = node[part]
                continue
            if hasattr(node, part):
                node = getattr(node, part)
                continue
            return False, None, {
                'error': f"objectRef path '{path}' failed at '{part}' "
                         f"on {type(node).__name__}"}
        # A terminal JSON string that parses to a scalar stays a string;
        # bindings target scalars/lists, not blobs — hand back as-is.
        return True, node, None
    if kind == 'stageDerived':
        stage = value.get('stage', '')
        key = value.get('key', '')
        flat_key = f'{stage}.{key}' if stage else key
        if not stage_context:
            return False, None, {
                'error': f"stageDerived '{flat_key}' has no stage "
                         'context — run/gate the upstream stage first '
                         '(this binding only resolves inside a '
                         'multi-scale stage)'}
        if flat_key not in stage_context:
            return False, None, {
                'error': f"stageDerived '{flat_key}' not in the stage "
                         'context',
                'availableKeys': sorted(stage_context)[:25]}
        return True, stage_context[flat_key], None
    return False, None, {'error': f"unknown binding kind '{kind}'",
                         'suggestion': {'knob': 'binding.kind',
                                        'action': "one of 'value', "
                                                  "'objectRef', "
                                                  "'stageDerived'"}}


def _coerce(value, schema_entry):
    """Schema-typed coercion. Returns (ok, coerced, error|None)."""
    t = schema_entry.get('type', 'number')
    try:
        if t == 'number':
            coerced = float(value)
        elif t == 'integer':
            coerced = int(value)
        elif t == 'string':
            coerced = str(value)
        elif t == 'vector':
            if not isinstance(value, (list, tuple)):
                return False, None, 'expected a list'
            coerced = [float(v) for v in value]
        else:
            coerced = value
    except (TypeError, ValueError) as e:
        return False, None, f'not a {t}: {e}'
    if t in ('number', 'integer'):
        lo, hi = schema_entry.get('min'), schema_entry.get('max')
        if lo is not None and coerced < lo:
            return False, None, f'below min {lo}'
        if hi is not None and coerced > hi:
            return False, None, f'above max {hi}'
    return True, coerced, None


# ---------------------------------------------------------------------
# Validation (configuration-time) + resolution (execution-time)
# ---------------------------------------------------------------------

# What the CURRENT engines honestly support per section (FEM).
_FEM_SUPPORTED = {
    'domainShapes': ('unit-square',),
    'inclusionShapes': ('circle',),
    'bcTypes': ('dirichlet',),
}


def validate_model(manager, model_row) -> Dict:
    """Configuration-time check of a model definition against its
    template schema (+ FEM domain/BC honesty). No resolution of
    objectRef/stageDerived values here — existence of the binding is
    enough at configure time; resolve_model does the live lookups."""
    findings: List[Dict] = []
    suggestions: List[Dict] = []
    template_ref = (getattr(model_row, 'physics_ref', '')
                    or getattr(model_row, 'calculation_ref', ''))
    template = find_template(manager, template_ref)
    if template is None:
        return {'ok': False,
                'findings': [{'level': 'error', 'param': '',
                              'message': f"template '{template_ref}' "
                                         'not found',
                              'evidence': {}}],
                'suggestions': [{'knob': 'physics_ref/calculation_ref',
                                 'action': 'name an EngineModelTemplate '
                                           'row'}]}
    schema = _parse(getattr(template, 'parameter_schema_json', ''), [])
    section_map = _parse(getattr(template, 'section_map_json', ''), {})
    for entry in schema:
        key = entry.get('key', '')
        path = section_map.get(key, '')
        found, raw, available = _section_value(model_row, path) \
            if path else (False, None, [])
        if not found:
            if entry.get('required'):
                findings.append({
                    'level': 'error', 'param': key,
                    'message': f"required parameter '{key}' unfilled "
                               f"(section path '{path}')",
                    'evidence': {'availableAtPath': available}})
                suggestions.append({
                    'knob': path,
                    'action': f"set a value or binding for '{key}'",
                    'reason': entry.get('description', '')})
            elif entry.get('default') is None:
                findings.append({
                    'level': 'warning', 'param': key,
                    'message': f"optional '{key}' unfilled and the "
                               'schema has no default',
                    'evidence': {'path': path}})
            continue
        if _is_binding(raw):
            continue   # bindings resolve at execution time
        ok, _, err = _coerce(raw, entry)
        if not ok:
            findings.append({
                'level': 'error', 'param': key,
                'message': f"literal value for '{key}' invalid: {err}",
                'evidence': {'value': raw,
                             'schema': {k: entry.get(k) for k in
                                        ('type', 'min', 'max', 'unit')}}})
    # FEM section honesty (only for FEM models).
    if getattr(model_row, 'physics_ref', ''):
        domain = _parse(getattr(model_row, 'domain_json', ''), {})
        shape = domain.get('shape')
        if shape and shape not in _FEM_SUPPORTED['domainShapes']:
            findings.append({
                'level': 'error', 'param': 'domain.shape',
                'message': f"domain shape '{shape}' is not supported by "
                           'the current FEM engines',
                'evidence': {'supported':
                             list(_FEM_SUPPORTED['domainShapes'])}})
        inclusion_shape = (domain.get('inclusion') or {}).get('shape')
        if inclusion_shape and inclusion_shape not in \
                _FEM_SUPPORTED['inclusionShapes']:
            findings.append({
                'level': 'error', 'param': 'domain.inclusion.shape',
                'message': f"inclusion shape '{inclusion_shape}' is not "
                           'supported yet',
                'evidence': {'supported':
                             list(_FEM_SUPPORTED['inclusionShapes'])}})
        for bc in _parse(getattr(model_row, 'boundary_conditions_json',
                                 ''), []):
            if bc.get('type') not in _FEM_SUPPORTED['bcTypes']:
                findings.append({
                    'level': 'error',
                    'param': f"boundaryConditions[{bc.get('boundary')}]",
                    'message': f"boundary type '{bc.get('type')}' is "
                               'not supported by the current engines',
                    'evidence': {'supported':
                                 list(_FEM_SUPPORTED['bcTypes'])}})
        solver = _parse(getattr(model_row, 'solver_json', ''), {})
        if solver:
            findings.append({
                'level': 'note', 'param': 'solver',
                'message': 'solver knobs are declared but the current '
                           'engines use their internal defaults — the '
                           'section is recorded, not consumed yet',
                'evidence': {'declared': sorted(solver)}})
    # DFT honesty notes.
    if getattr(model_row, 'calculation_ref', ''):
        method = _parse(getattr(model_row, 'method_json', ''), {})
        if method.get('pseudopotentials'):
            findings.append({
                'level': 'note', 'param': 'method.pseudopotentials',
                'message': 'pseudopotentials only apply to the QE '
                           'execution layer (dft-total-energy with a '
                           'WITH_QE worker build)',
                'evidence': {}})
    errors = [f for f in findings if f['level'] == 'error']
    return {'ok': not errors, 'findings': findings,
            'suggestions': suggestions, 'template': template_ref}


def resolve_model(manager, model_row, stage_context=None) -> Dict:
    """Execution-time resolution: every schema slot → a concrete engine
    input, with per-param provenance and honest refusals.

    Returns {'ok', 'inputs': {key: value},
             'resolved': {key: {'kind', 'source', 'value'}},
             'refusals': [{param, error, ...}]}."""
    template_ref = (getattr(model_row, 'physics_ref', '')
                    or getattr(model_row, 'calculation_ref', ''))
    template = find_template(manager, template_ref)
    if template is None:
        return {'ok': False, 'inputs': {}, 'resolved': {},
                'refusals': [{'param': '',
                              'error': f"template '{template_ref}' "
                                       'not found'}]}
    schema = _parse(getattr(template, 'parameter_schema_json', ''), [])
    section_map = _parse(getattr(template, 'section_map_json', ''), {})
    inputs: Dict[str, Any] = {}
    resolved: Dict[str, Dict] = {}
    refusals: List[Dict] = []
    for entry in schema:
        key = entry.get('key', '')
        path = section_map.get(key, '')
        found, raw, _ = _section_value(model_row, path) \
            if path else (False, None, [])
        if not found:
            if entry.get('default') is not None:
                inputs[key] = entry['default']
                resolved[key] = {'kind': 'default',
                                 'source': 'template schema',
                                 'value': entry['default']}
            elif entry.get('required'):
                refusals.append({
                    'param': key,
                    'error': f"required '{key}' unfilled at '{path}'"})
            continue
        ok, value, refusal = resolve_binding(manager, raw, stage_context)
        if not ok:
            refusals.append({'param': key, **(refusal or {})})
            continue
        ok2, coerced, err = _coerce(value, entry)
        if not ok2:
            refusals.append({
                'param': key,
                'error': f"resolved value for '{key}' invalid: {err}",
                'resolvedValue': value})
            continue
        inputs[key] = coerced
        if _is_binding(raw):
            src = raw.get('kind')
            detail = (f"{raw.get('className')}/{raw.get('name')}."
                      f"{raw.get('path')}" if src == 'objectRef'
                      else f"{raw.get('stage')}.{raw.get('key')}"
                      if src == 'stageDerived' else 'literal')
            resolved[key] = {'kind': src, 'source': detail,
                             'value': coerced}
        else:
            resolved[key] = {'kind': 'literal', 'source': path,
                             'value': coerced}
    return {'ok': not refusals, 'inputs': inputs, 'resolved': resolved,
            'refusals': refusals}
