"""
@module tensortree.custom.tensortree_scale

THE SCALE TREE OF A MATERIAL, AS A READING (tt-4 / plan §C Phase 7, §B6): one rooted view built from rows that
already exist — never a second materials database.

    nodes       one per MaterialScaleDefinition level the material HAS (L0 experimental … L4 quantum, status
                defined|partial), with the level's engine and cost class from the MultiScaleSimulationProfile's
                fidelity ladder when one names the level
    unresolved  one per level the material does NOT have (unresolved_kind = structural: "nothing is defined at
                this scale yet"), so the tree is honest about its gaps
    mappings    one `kind=scale` TensorMapping per pspp ScaleTransferDefinition touching the material — BY
                REFERENCE (scale_transfer_ref); status/method/assumptions are the transfer's, not copied
    root        the coarsest level present (experimental if it exists — what was measured)

`scale_tree(manager, material)` returns the view; `materialise(manager, material)` writes it as tensortree rows
(a person's action, so the tree can be selected on and discovered over like any other) — idempotent by name.
Accountability comes from materialsScience.scale_presence when it is importable (what is defined where).
"""
import json

LEVELS = {0: 'experimental', 1: 'continuum', 2: 'mesoscale', 3: 'atomistic', 4: 'quantum'}


def _rows(manager, cls):
    return list((getattr(manager, 'objectTables', {}) or {}).get(cls, {}).values())


def _j(s, d):
    try:
        v = json.loads(s or '')
        return v if v is not None else d
    except Exception:
        return d


def _ladder(manager, material):
    """{level: {engines, costClass, purpose}} from the first MultiScaleSimulationProfile whose ladder names levels."""
    out = {}
    for p in _rows(manager, 'MultiScaleSimulationProfile'):
        for rung in _j(getattr(p, 'fidelity_ladder_json', '[]'), []):
            lvl = rung.get('level')
            try:
                lvl = int(str(lvl).lstrip('L'))
            except Exception:
                continue
            out.setdefault(lvl, {'engines': rung.get('engines', []), 'costClass': rung.get('costClass', ''), 'purpose': rung.get('purpose', ''), 'profile': str(getattr(p, 'name', ''))})
    return out


def scale_tree(manager, material):
    defs = [d for d in _rows(manager, 'MaterialScaleDefinition') if str(getattr(d, 'material_name', '')) == material]
    if not defs:
        return {'ok': False, 'material': material, 'error': 'no MaterialScaleDefinition rows for %r — the materials model does not know this material' % material}
    ladder = _ladder(manager, material)
    present = {}
    for d in defs:
        lvl = int(getattr(d, 'scale_level', 0) or 0)
        present[lvl] = {'name': str(d.name), 'status': str(getattr(d, 'status', '')), 'category': str(getattr(d, 'scale_category', LEVELS.get(lvl, ''))),
                        'definition_class': str(getattr(d, 'definition_class', '') or ''), 'definition_ref': str(getattr(d, 'definition_ref', '') or ''),
                        'derivation_method': str(getattr(d, 'derivation_method', '') or ''), 'derived_from': str(getattr(d, 'derived_from_name', '') or ''),
                        'state_key': str(getattr(d, 'state_key', '') or ''), 'fidelity': ladder.get(lvl, {})}
    root_level = min(present)
    tree = '%s@scale' % material
    nodes, unresolved = [], []
    for lvl in range(5):
        if lvl in present:
            p = present[lvl]
            nodes.append({'name': '%s@L%d' % (material, lvl), 'level': lvl, 'category': LEVELS[lvl], 'parent': '' if lvl == root_level else '%s@L%d' % (material, root_level),
                          'status_msci': p['status'], 'definition_class': p['definition_class'], 'definition_ref': p['definition_ref'],
                          'derivation_method': p['derivation_method'], 'fidelity': p['fidelity'], 'state_key': p['state_key']})
        else:
            unresolved.append({'name': '%s@L%d' % (material, lvl), 'level': lvl, 'category': LEVELS[lvl], 'parent': '%s@L%d' % (material, root_level),
                               'unresolved_kind': 'structural', 'why': 'no MaterialScaleDefinition at this scale yet', 'fidelity': ladder.get(lvl, {})})
    # a pspp state key is a canonical subject '<material>#<state>' (or the bare material); match on the material
    state_keys = {p['state_key'] for p in present.values() if p['state_key']} | {material}
    _mine = lambda key: str(key) in state_keys or str(key).split('#', 1)[0] == material
    mappings = []
    for t in _rows(manager, 'ScaleTransferDefinition'):
        if not _mine(getattr(t, 'source_state_key', '')) and not _mine(getattr(t, 'target_state_key', '')):
            continue
        src, dst = int(getattr(t, 'source_scale', 0) or 0), int(getattr(t, 'target_scale', 0) or 0)
        st = str(getattr(t, 'status', 'declared') or 'declared')
        mappings.append({'name': str(t.name), 'kind': 'scale', 'source_node': '%s@L%d' % (material, src), 'target_node': '%s@L%d' % (material, dst),
                         'scale_transfer_ref': str(t.name), 'method': str(getattr(t, 'transfer_method', '')), 'transfer_status': st,
                         'validity_json': str(getattr(t, 'validity_json', '{}') or '{}'), 'uncertainty_json': str(getattr(t, 'uncertainty_json', '{}') or '{}'),
                         'assumptions': _j(getattr(t, 'assumptions_json', '[]'), []), 'transported': _j(getattr(t, 'transported_json', '[]'), []),
                         # the transfer's status → the two statuses (§F2): executed = implemented + simulated; validated → validated; declared → proposed/none
                         'mapping_status': {'executed': 'implemented', 'validated': 'validated', 'declared': 'proposed'}.get(st, 'proposed'),
                         'evidence_level': {'executed': 'simulated', 'validated': 'simulated', 'declared': 'none'}.get(st, 'none'),
                         'evidence_ref': 'pspp ScaleTransferDefinition %s (%s)' % (t.name, st) if st != 'declared' else ''})
    acct = None
    try:
        from materialsScience.scale_presence import scale_profile
        prof = scale_profile(manager, material)
        acct = {'defined': prof.get('defined', []), 'partial': prof.get('partial', [])} if isinstance(prof, dict) else None
    except Exception:
        acct = None
    return {'ok': True, 'material': material, 'tree': tree, 'root': '%s@L%d' % (material, root_level), 'view_kind': 'scale',
            'nodes': nodes, 'unresolved': unresolved, 'mappings': mappings, 'accountability': acct,
            'note': 'a READING of MaterialScaleDefinition + ScaleTransferDefinition (+ the fidelity ladder); nothing copied. materialise() persists it as tensortree rows.'}


def materialise(manager, material, make=None):
    """Persist the view as rows (idempotent by name). Returns what was written.
    `make(cls, cls_name, **fields)` builds a new row — the default constructs the treeObject on the manager; a
    selftest with a fake manager passes its own."""
    from tensortree.tensortree_basis import TensorTreeDefinition, TensorNode, UnresolvedTensorSpace, TensorMapping
    v = scale_tree(manager, material)
    if not v.get('ok'):
        return v
    db = getattr(manager, 'db', None)
    make = make or (lambda cls, cls_name, **fields: cls(manager=manager, **fields))
    def upsert(cls, cls_name, **fields):
        row = next((r for r in _rows(manager, cls_name) if str(getattr(r, 'name', '')) == fields['name']), None)
        if row is None:
            row = make(cls, cls_name, **fields)
        else:
            for k, val in fields.items():
                setattr(row, k, val)
        if db is not None and hasattr(db, 'saveInstanceInDB'):
            db.saveInstanceInDB(row)
        return row
    written = {'tree': v['tree'], 'nodes': 0, 'unresolved': 0, 'mappings': 0}
    upsert(TensorTreeDefinition, 'TensorTreeDefinition', name=v['tree'], description='the scale tree of %s, materialised from the materials model' % material,
           tensor='', root_node=v['root'], view_kind='scale', status='partial', notes='tt-4: nodes = MaterialScaleDefinition levels; mappings = pspp ScaleTransferDefinition by reference')
    for n in v['nodes']:
        upsert(TensorNode, 'TensorNode', name=n['name'], description='', tree=v['tree'], parent=n['parent'], title='%s at L%d (%s)' % (material, n['level'], n['category']),
               tensor='', dims_json='[]', binding_ref='', global_params_json=json.dumps({'level': n['level'], 'msci_status': n['status_msci'], 'definition_ref': n['definition_ref'], 'fidelity': n['fidelity']}),
               status='unresolved', notes='a scale level: its VALUES are the msci definition it names (%s); no tensor bound yet' % (n['definition_class'] or '?'))
        written['nodes'] += 1
    for u in v['unresolved']:
        upsert(UnresolvedTensorSpace, 'UnresolvedTensorSpace', name=u['name'], description='', tree=v['tree'], parent=u['parent'], title='%s at L%d (%s)' % (material, u['level'], u['category']),
               unresolved_kind='structural', known_dims_json='[]', known_semantics_json=json.dumps({'level': u['level'], 'category': u['category']}), constraints_json='[]',
               candidate_mappings_json='[]', candidate_bindings_json='[]', hypotheses_json='[]', evidence_json='[]',
               open_questions_json=json.dumps(['%s: which engine defines %s here? (%s)' % (u['why'], material, json.dumps(u['fidelity']) if u['fidelity'] else 'no ladder rung')]), notes='')
        written['unresolved'] += 1
    for mp in v['mappings']:
        upsert(TensorMapping, 'TensorMapping', name=mp['name'], description='', kind='scale', source_node=mp['source_node'], source_dims_json='[]', target_node=mp['target_node'], target_dims_json='[]',
               expression_ref='', coupling_ref='', scale_transfer_ref=mp['scale_transfer_ref'], validity_json=mp['validity_json'], units='', conservation_json='[]',
               loss_note='a scale transfer is lossy by nature: see the transfer\'s assumptions', reconstruction_error=0.0, error_method='', uncertainty_json=mp['uncertainty_json'],
               mapping_status=mp['mapping_status'], evidence_level=mp['evidence_level'], evidence_ref=mp['evidence_ref'], provenance='pspp ScaleTransferDefinition, by reference', notes=mp['method'])
        written['mappings'] += 1
    return {'ok': True, 'written': written, 'view': v}
