"""
@module tensortree.custom.tensortree_couple

A SimulationCouplingDefinition CREATED FROM a `kind=coupling` TensorMapping (tt-7; plan §F6 "kind=scale|coupling
ALSO written as SimulationCouplingDefinition"). The tree is where a person declares that one node's values feed
another node's step; the coupling row is what the runner executes. Everything the runner needs is DERIVED from
rows that already exist, and whatever cannot be derived is refused by name — never guessed:

    source_class_name / source_simulation_ref   ← the source node's Tensor (storage engine matrixfield:<Class>:…
                                                   or simstate:<Class>:…) → the class → its simulation_definition_name
    target_class_name / target_simulation_ref   ← the target node's Tensor, the same way
    sampler_equation_ref                        ← body.sampler_equation_ref, else the mapping's expression_ref's
                                                   `matrix_equation_ref` (a saved MatrixEquationDefinition; must exist)
    config_json.sampler.operands                ← the source field (matrixfield's field) as `source_field_json`,
                                                   the target's position fields (its dims on channels position.x/y/z)
    config_json.inject                          ← the mapping's target_dims, in order, as sample_element 0..n-1
    config_json.defaults                        ← 0.0 per injected key (soft-degrade: no source run → inert)

`propose(manager, mapping_name, body)` computes the row + what is missing (a dry run; GET). `couple(manager,
mapping_name, body, make)` writes it, sets `mapping.coupling_ref`, and moves mapping_status to `implemented`
(a runner can execute the row) — evidence_level is NOT touched: nothing has run yet, and a coupling only
becomes `simulated` evidence when a run pairs to it and steps. Refusals: kind ≠ coupling (422), already
coupled (409, names the coupling), missing pieces (422, each named).
"""
import json
import re

POSITION_CHANNELS = ('position.x', 'position.y', 'position.z')


def _rows(manager, cls):
    return list((getattr(manager, 'objectTables', {}) or {}).get(cls, {}).values())


def _by_name(manager, cls, name):
    return next((r for r in _rows(manager, cls) if str(getattr(r, 'name', '')) == str(name)), None)


def _j(s, d):
    try:
        v = json.loads(s or '')
        return v if v is not None else d
    except Exception:
        return d


def _class_of_tensor(t):
    """(class_name, field) from an engine storage ref, or (None, None) with the reason in field."""
    ref = str(getattr(t, 'storage_ref', '') or '')
    parts = ref.split(':')
    if str(getattr(t, 'storage_kind', '')) != 'engine' or len(parts) != 4 or parts[0] not in ('matrixfield', 'simstate'):
        return None, 'tensor %s has storage %s:%s — a coupling needs an engine tensor over a sim-state class (matrixfield:<Class>:… or simstate:<Class>:…)' % (getattr(t, 'name', '?'), getattr(t, 'storage_kind', ''), ref)
    return parts[1], parts[3]


def _sim_def_of_class(manager, class_name):
    typing = (getattr(manager, 'objectTypingDict', {}) or {}).get(class_name)
    cls = getattr(typing, 'classDefinition', None) if typing is not None else None
    if cls is None:
        for inst in (getattr(manager, 'objectTables', {}) or {}).get(class_name, {}).values():
            cls = inst.__class__
            break
    return str(getattr(cls, 'simulation_definition_name', '') or '') if cls is not None else ''


def _node_side(manager, node_name, role, missing):
    node = _by_name(manager, 'TensorNode', node_name)
    if node is None:
        missing.append('%s node %r is not a TensorNode on this instance' % (role, node_name)); return {}
    t = _by_name(manager, 'Tensor', str(getattr(node, 'tensor', '') or ''))
    if t is None:
        missing.append('%s node %r names no Tensor (tensor=%r)' % (role, node_name, getattr(node, 'tensor', ''))); return {'node': node}
    cls, field = _class_of_tensor(t)
    if cls is None:
        missing.append('%s: %s' % (role, field)); return {'node': node, 'tensor': t}
    sim = _sim_def_of_class(manager, cls)
    if not sim:
        missing.append('%s class %s declares no simulation_definition_name (is it a sim-state class this instance loaded?)' % (role, cls))
    return {'node': node, 'tensor': t, 'class_name': cls, 'field': field, 'simulation_ref': sim}


def _position_fields(manager, node):
    """The target's position fields, x→y→z, from its LocalizedDimensions on the position channels."""
    dims = {str(getattr(d, 'name', '')): d for d in _rows(manager, 'LocalizedDimension')}
    want = [str(x) for x in _j(getattr(node, 'dims_json', '[]'), [])]
    out = {}
    for dn in want:
        d = dims.get(dn)
        ch = str(getattr(d, 'channel', '') or '') if d is not None else ''
        if ch in POSITION_CHANNELS:
            out[ch] = str(getattr(d, 'dimension', '') or '').split('.')[-1] or str(getattr(d, 'name', '')).split('.')[-1]
    return [out[c] for c in POSITION_CHANNELS if c in out]


def _slug(name):
    return re.sub(r'[^a-z0-9]+', '-', str(name).lower().replace('→', '-to-')).strip('-')


def propose(manager, mapping_name, body=None):
    body = body if isinstance(body, dict) else {}
    m = _by_name(manager, 'TensorMapping', mapping_name)
    if m is None:
        return {'ok': False, 'status': 404, 'error': 'no TensorMapping %r' % mapping_name}
    if str(getattr(m, 'kind', '')) != 'coupling':
        return {'ok': False, 'status': 422, 'error': 'mapping %s is kind=%s — only a kind=coupling mapping becomes a SimulationCouplingDefinition (a scale mapping is a PSPP transfer by reference)' % (mapping_name, getattr(m, 'kind', ''))}
    existing = str(getattr(m, 'coupling_ref', '') or '')
    missing, notes = [], []
    src = _node_side(manager, str(getattr(m, 'source_node', '')), 'source', missing)
    tgt = _node_side(manager, str(getattr(m, 'target_node', '')), 'target', missing)
    sampler = str(body.get('sampler_equation_ref') or '')
    if not sampler:
        e = _by_name(manager, 'TensorMathExpression', str(getattr(m, 'expression_ref', '') or ''))
        sampler = str(getattr(e, 'matrix_equation_ref', '') or '') if e is not None else ''
        if sampler:
            notes.append('sampler taken from the mapping\'s expression %s → matrix_equation_ref %s' % (e.name, sampler))
    if not sampler:
        missing.append('a sampler equation: pass sampler_equation_ref (a saved MatrixEquationDefinition) or give the mapping an expression_ref whose matrix_equation_ref is set')
    elif _rows(manager, 'MatrixEquationDefinition') and _by_name(manager, 'MatrixEquationDefinition', sampler) is None:
        missing.append('sampler equation %r is not a saved MatrixEquationDefinition on this instance' % sampler)
    inject_keys = [str(k) for k in _j(getattr(m, 'target_dims_json', '[]'), [])]
    if not inject_keys:
        missing.append('the mapping names no target_dims — those are the context keys the coupling injects')
    pos_fields = _position_fields(manager, tgt['node']) if tgt.get('node') is not None else []
    if tgt.get('node') is not None and not pos_fields:
        missing.append('target node %s has no LocalizedDimension on position.x/y/z — the sampler needs the target\'s position fields' % getattr(m, 'target_node', ''))
    config = body.get('config') if isinstance(body.get('config'), dict) else None
    if config is None:
        config = {'sampler': {'operands': {'cells': {'kind': 'source_field_json', 'field': src.get('field', '')},
                                           'pos': {'kind': 'target_fields', 'fields': pos_fields}}},
                  'inject': {k: {'kind': 'sample_element', 'index': i} for i, k in enumerate(inject_keys)},
                  'defaults': {k: 0.0 for k in inject_keys}}
    else:
        notes.append('config taken from the request body as given')
    name = str(body.get('name') or ('tt-%s' % _slug(mapping_name)))
    row = {'name': name,
           'description': str(body.get('description') or ('Created from TensorMapping %s: %s → %s. %s' % (mapping_name, getattr(m, 'source_node', ''), getattr(m, 'target_node', ''), getattr(m, 'loss_note', '') or ''))).strip(),
           'target_simulation_ref': tgt.get('simulation_ref', ''), 'target_class_name': tgt.get('class_name', ''),
           'source_simulation_ref': src.get('simulation_ref', ''), 'source_class_name': src.get('class_name', ''),
           'sampler_equation_ref': sampler, 'config_json': json.dumps(config), 'enabled': bool(body.get('enabled', True))}
    return {'ok': not missing, 'status': 200 if not missing else 422, 'mapping': mapping_name, 'already_coupled_to': existing, 'coupling': row, 'missing': missing, 'notes': notes,
            'derived_from': {'source': {'node': getattr(m, 'source_node', ''), 'tensor': getattr(src.get('tensor'), 'name', None), 'class': src.get('class_name'), 'simulation': src.get('simulation_ref')},
                             'target': {'node': getattr(m, 'target_node', ''), 'tensor': getattr(tgt.get('tensor'), 'name', None), 'class': tgt.get('class_name'), 'simulation': tgt.get('simulation_ref'), 'position_fields': pos_fields}},
            'note': 'a dry run: nothing written. POST to create; the run-level pairing (which source RUN feeds which target run) stays on SimulationRun.coupled_run_refs_json, so the new coupling is inert until a run names it.'}


def couple(manager, mapping_name, body=None, make=None):
    p = propose(manager, mapping_name, body)
    if p.get('already_coupled_to') and not (body or {}).get('force'):   # the more useful refusal first
        return {'ok': False, 'status': 409, 'error': 'mapping %s already names coupling %r — pass force to create another beside it' % (mapping_name, p['already_coupled_to']), 'coupling_ref': p['already_coupled_to']}
    if not p.get('ok'):
        return p
    if _by_name(manager, 'SimulationCouplingDefinition', p['coupling']['name']) is not None:
        return {'ok': False, 'status': 409, 'error': 'a SimulationCouplingDefinition named %r already exists — pass a different name' % p['coupling']['name']}
    from simulations.simulation_coupling_definition import SimulationCouplingDefinition
    make = make or (lambda cls, **fields: cls(manager=manager, **fields))
    row = make(SimulationCouplingDefinition, **p['coupling'])
    m = _by_name(manager, 'TensorMapping', mapping_name)
    m.coupling_ref = p['coupling']['name']
    if str(getattr(m, 'mapping_status', '')) == 'proposed':
        m.mapping_status = 'implemented'   # a runner can execute it now; evidence stays what it was until a run steps it
    m.provenance = (str(getattr(m, 'provenance', '') or '') + ' | coupling row created from this mapping (tt-7)').strip(' |')
    db = getattr(manager, 'db', None)
    if db is not None and hasattr(db, 'saveInstanceInDB'):
        db.saveInstanceInDB(row); db.saveInstanceInDB(m)
    p.update({'status': 201, 'created': p['coupling']['name'], 'mapping_status': str(getattr(m, 'mapping_status', '')), 'evidence_level': str(getattr(m, 'evidence_level', '')),
              'note': 'created. evidence_level untouched: nothing has run through this coupling yet — pair a SimulationRun to it (coupled_run_refs_json) and step it, then the mapping may claim simulated evidence.'})
    return p
