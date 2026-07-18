"""
@cross-cutting
@module techtree.techtree_analysis

Pure tech-tree logic (tt-3): edge derivation from depends_on_json,
transient/primary designation (the tt-1 idiom over technologies),
per-segment DONE-TESTS, and the completion rollup (B4) following the
MultiScaleSimulationProfile conformance pattern — declarative
naming + conformance + evidence-bearing suggestions, never codegen,
never auto-applied.

First-cut done-criteria per segment kind (Dustin can tighten these
into explicit gates later — the seam is `_ASSIGNMENT_TESTS`):
  theory   — the referenced module has an enabled ModuleAssignment
             (any topology) or an installed PolariModule row.
  real     — RealArtifact proven AND both routes documented
             (commercial + open-source self-manufacture).
  business — BusinessModelDefinition self_sustaining with evidence.
  politics — PolicyDefinition with a stated policy and evidence.

The tt-6 content classes may not exist yet — every test reads
objectTables duck-typed, so a missing table is simply "not done",
with evidence saying exactly what is missing.

NO framework imports; `manager` is anything with objectTables, so
the selftest runs stdlib-only with SimpleNamespace rows.

@consumers
  - techtree.techtree_api / techtree.selftest_techtree
  - polari-platform-angular tech-tree render mode (tt-4)
"""

import json

from techtree.techtree_basis import SEGMENT_COLORS, SEGMENT_KINDS


def _rows(manager, class_name):
    table = (getattr(manager, 'objectTables', None) or {}).get(
        class_name, {})
    return list(table.values()) if isinstance(table, dict) else list(table)


def _scoped(manager, class_name, tree_name):
    return [r for r in _rows(manager, class_name)
            if getattr(r, 'tree_name', '') == tree_name]


def _loads(row, attr, default):
    try:
        text = getattr(row, attr, '') or ''
        return json.loads(text) if text else default
    except Exception:
        return default


def _named(manager, class_name, name):
    for row in _rows(manager, class_name):
        if getattr(row, 'name', '') == name:
            return row
    return None


def active_tree_name(manager):
    """The active TechTreeDefinition's name, falling back to the
    baseline tree, else ''."""
    fallback = ''
    for row in _rows(manager, 'TechTreeDefinition'):
        if getattr(row, 'is_active', False):
            return getattr(row, 'name', '')
        if getattr(row, 'is_baseline', False) and not fallback:
            fallback = getattr(row, 'name', '')
    return fallback


# ---------------------------------------------------------------------
# Edges: derived from depends_on_json, designated like tt-1.
# ---------------------------------------------------------------------

def sync_edges(manager, tree_name, edge_factory=None):
    """Materialize TechDependencyEdge rows from every node's
    depends_on_json (create missing, drop stale) and re-designate.

    edge_factory(name=..., ...) constructs new rows — the API passes
    the real class; the selftest passes SimpleNamespace. Pure over
    the tables; the caller persists."""
    desired = {}
    for node in _scoped(manager, 'TechNode', tree_name):
        for dep in _loads(node, 'depends_on_json', []):
            name = f'{getattr(node, "name", "")}->{dep}'
            desired[name] = (getattr(node, 'name', ''), dep)
    table = (getattr(manager, 'objectTables', None) or {}).setdefault(
        'TechDependencyEdge', {})
    existing = {getattr(r, 'name', ''): key for key, r in table.items()
                if getattr(r, 'tree_name', '') == tree_name}
    created, removed = [], []
    for name, (tech, dep) in desired.items():
        if name not in existing:
            row = (edge_factory or _plain_edge)(
                name=name, tree_name=tree_name, tech_node=tech,
                depends_on_tech=dep)
            # A real treeObject factory registers the row in
            # objectTables itself (keyed by id); only plain rows
            # (selftest SimpleNamespace) need inserting by hand.
            if not any(getattr(r, 'name', '') == name
                       for r in table.values()):
                table[name] = row
            created.append(name)
    for name, key in existing.items():
        if name not in desired:
            table.pop(key, None)
            removed.append(name)
    designation = designate_tech_transients(manager, tree_name)
    return {'ok': True, 'tree': tree_name, 'created': created,
            'removed': removed, 'designation': designation}


def _plain_edge(**fields):
    import types
    fields.setdefault('is_primary', False)
    fields.setdefault('is_transient', False)
    fields.setdefault('notes', '')
    return types.SimpleNamespace(**fields)


def designate_tech_transients(manager, tree_name):
    """Stamp is_primary/is_transient on tech dependency edges — the
    SAME deterministic, stable pass as the module graph (tt-1):
    keep a still-valid existing primary, else the alphabetically
    first dependent technology; the other N-1 copies are transient."""
    groups = {}
    for edge in _scoped(manager, 'TechDependencyEdge', tree_name):
        groups.setdefault(
            getattr(edge, 'depends_on_tech', ''), []).append(edge)
    changed = []
    for dep, edges in sorted(groups.items()):
        edges.sort(key=lambda e: getattr(e, 'tech_node', ''))
        existing = [e for e in edges if getattr(e, 'is_primary', False)]
        primary = existing[0] if existing else edges[0]
        for edge in edges:
            old = (getattr(edge, 'is_primary', False),
                   getattr(edge, 'is_transient', False))
            edge.is_primary = edge is primary
            edge.is_transient = edge is not primary
            if (edge.is_primary, edge.is_transient) != old:
                changed.append({'edge': getattr(edge, 'name', ''),
                                'isPrimary': edge.is_primary,
                                'isTransient': edge.is_transient})
    return {'groups': len(groups), 'changed': changed}


# ---------------------------------------------------------------------
# Per-assignment done-tests (B4 first cut) — each returns
# (done, evidence, knob, action); never raises, always honest.
# ---------------------------------------------------------------------

def _theory_done(manager, ref_name):
    for asg in _rows(manager, 'ModuleAssignment'):
        if (getattr(asg, 'module_name', '') == ref_name
                and getattr(asg, 'state', '') == 'enabled'):
            return (True,
                    f'module "{ref_name}" enabled on instance '
                    f'"{getattr(asg, "instance_name", "")}"', '', '')
    row = _named(manager, 'PolariModule', ref_name)
    if row is not None and getattr(row, 'status', '') == 'installed':
        return (True, f'PolariModule "{ref_name}" is installed', '', '')
    return (False,
            f'module "{ref_name}" has no enabled ModuleAssignment and '
            'no installed PolariModule row',
            'ModuleAssignment / PolariModule.status',
            f'`pol allocate {ref_name} <instance>` (topology) or '
            'install the module bundle')


def _real_done(manager, ref_name):
    row = _named(manager, 'RealArtifact', ref_name)
    if row is None:
        return (False, f'no RealArtifact named "{ref_name}"',
                'RealArtifact',
                'create the artifact row with CAD/hardware refs (tt-6)')
    missing = []
    if not getattr(row, 'proven', False):
        missing.append('not proven (no working-hardware evidence)')
    if not _loads(row, 'commercial_route_json', {}):
        missing.append('no commercial route')
    if not _loads(row, 'self_manufacture_route_json', {}):
        missing.append('no open-source self-manufacture route')
    if missing:
        return (False, f'RealArtifact "{ref_name}": '
                + '; '.join(missing),
                'RealArtifact.proven / *_route_json',
                'prove the design and document BOTH routes')
    return (True, f'RealArtifact "{ref_name}" proven with both '
            'routes documented', '', '')


def _business_done(manager, ref_name):
    row = _named(manager, 'BusinessModelDefinition', ref_name)
    if row is None:
        return (False,
                f'no BusinessModelDefinition named "{ref_name}"',
                'BusinessModelDefinition',
                'define the business model + scale ladder (tt-6)')
    if not getattr(row, 'self_sustaining', False):
        return (False, f'business model "{ref_name}" is not '
                'evidenced self-sustaining',
                'BusinessModelDefinition.self_sustaining',
                'record a BusinessOutcome that shows it sustaining')
    if not _loads(row, 'evidence_json', []):
        return (False, f'business model "{ref_name}" claims '
                'self-sustaining but carries no evidence',
                'BusinessModelDefinition.evidence_json',
                'attach the outcome evidence')
    return (True, f'business model "{ref_name}" self-sustaining '
            'with evidence', '', '')


def _politics_done(manager, ref_name):
    row = _named(manager, 'PolicyDefinition', ref_name)
    if row is None:
        return (False, f'no PolicyDefinition named "{ref_name}"',
                'PolicyDefinition',
                'define the policy + its effect on the business '
                'models (tt-6)')
    if not getattr(row, 'policy', ''):
        return (False, f'policy row "{ref_name}" has no policy text',
                'PolicyDefinition.policy', 'state the policy')
    if not _loads(row, 'evidence_json', []):
        return (False, f'policy "{ref_name}" carries no evidence of '
                'its effect', 'PolicyDefinition.evidence_json',
                'attach outcome examples')
    return (True, f'policy "{ref_name}" stated with evidence', '', '')


_ASSIGNMENT_TESTS = {
    'theory': _theory_done,
    'real': _real_done,
    'business': _business_done,
    'politics': _politics_done,
}


def assignment_report(manager, assignment):
    """One assignment's done-test result, evidence-bearing."""
    kind = getattr(assignment, 'segment_kind', '')
    ref = getattr(assignment, 'ref_name', '')
    test = _ASSIGNMENT_TESTS.get(kind)
    if test is None:
        return {'name': getattr(assignment, 'name', ''),
                'refName': ref, 'segmentKind': kind, 'done': False,
                'evidence': f'unknown segment kind "{kind}" — not one '
                            f'of {SEGMENT_KINDS}',
                'knob': 'TechSegmentAssignment.segment_kind',
                'action': 'pick a known segment kind'}
    done, evidence, knob, action = test(manager, ref)
    return {'name': getattr(assignment, 'name', ''), 'refName': ref,
            'segmentKind': kind, 'done': done, 'evidence': evidence,
            'knob': knob, 'action': action}


# ---------------------------------------------------------------------
# Completion rollup (B4): assignment -> segment -> node -> tree.
# ---------------------------------------------------------------------

def node_completion(manager, tree_name, node_name):
    """One node's derived segments + completion. Only PRESENT
    segments (>=1 assignment) exist; node completion is the
    weighted mean over present segments."""
    assignments = [a for a in _scoped(
        manager, 'TechSegmentAssignment', tree_name)
        if getattr(a, 'tech_node', '') == node_name]
    weights = {getattr(s, 'kind', ''): getattr(s, 'weight', 1.0)
               for s in _scoped(manager, 'TechSegment', tree_name)
               if getattr(s, 'tech_node', '') == node_name}
    segments = []
    for kind in SEGMENT_KINDS:
        mine = [assignment_report(manager, a) for a in assignments
                if getattr(a, 'segment_kind', '') == kind]
        if not mine:
            continue  # absent segments take no space (B1)
        done = sum(1 for r in mine if r['done'])
        segments.append({
            'kind': kind,
            'color': SEGMENT_COLORS[kind],
            'weight': weights.get(kind, 1.0),
            'assignments': mine,
            'done': done,
            'total': len(mine),
            'completion': done / len(mine),
        })
    total_weight = sum(s['weight'] for s in segments)
    completion = (sum(s['completion'] * s['weight'] for s in segments)
                  / total_weight) if total_weight else 0.0
    return {'node': node_name,
            'segmentsPresent': [s['kind'] for s in segments],
            'segments': segments,
            'completionLevel': completion,
            'gaps': [
                {'severity': 'info', 'check': 'segment-incomplete',
                 'subject': f'{node_name}:{r["segmentKind"]}',
                 'evidence': r['evidence'], 'knob': r['knob'],
                 'action': r['action']}
                for s in segments for r in s['assignments']
                if not r['done']]}


def tree_completion(manager, tree_name):
    """The whole tree's rollup: mean over nodes; the baseline is
    ACHIEVED only when every node is complete (and nodes exist)."""
    definition = _named(manager, 'TechTreeDefinition', tree_name)
    if definition is None:
        return {'ok': False,
                'error': f'no TechTreeDefinition named "{tree_name}"'}
    nodes = _scoped(manager, 'TechNode', tree_name)
    reports = [node_completion(manager, tree_name,
                               getattr(n, 'name', ''))
               for n in sorted(nodes,
                               key=lambda n: getattr(n, 'name', ''))]
    completion = (sum(r['completionLevel'] for r in reports)
                  / len(reports)) if reports else 0.0
    return {
        'ok': True, 'tree': tree_name,
        'title': (getattr(definition, 'title', '')
                  or getattr(definition, 'name', '')),
        'isBaseline': getattr(definition, 'is_baseline', False),
        'owner': getattr(definition, 'owner', ''),
        'nodes': reports,
        'completionLevel': completion,
        'baselineAchieved': bool(reports) and all(
            r['completionLevel'] >= 1.0 for r in reports),
        'gaps': [g for r in reports for g in r['gaps']],
    }


def baseline_report(manager):
    """The Open Source Economic Baseline across DOMAIN trees (tt-8):
    every TechTreeDefinition flagged is_baseline is one domain
    component (Electronics/Microelectronics, Raw Supply Chain, Open
    Source Economy & Politics, ...). Reaching the end of ALL of them,
    combined, is the OSEB — combined completion is the mean over the
    domain trees, achieved only when every tree is achieved."""
    trees = sorted(
        (t for t in _rows(manager, 'TechTreeDefinition')
         if getattr(t, 'is_baseline', False)),
        key=lambda t: getattr(t, 'name', ''))
    reports = []
    for tree in trees:
        name = getattr(tree, 'name', '')
        completion = tree_completion(manager, name)
        if not completion.get('ok'):
            continue
        reports.append({
            'name': name,
            'title': (getattr(tree, 'title', '') or name),
            'owner': getattr(tree, 'owner', ''),
            'completionLevel': completion['completionLevel'],
            'baselineAchieved': completion['baselineAchieved'],
            'nodeCount': len(completion['nodes']),
            'gapCount': len(completion['gaps']),
        })
    combined = (sum(r['completionLevel'] for r in reports)
                / len(reports)) if reports else 0.0
    return {
        'ok': True,
        'trees': reports,
        'completionLevel': combined,
        'baselineAchieved': bool(reports) and all(
            r['baselineAchieved'] for r in reports),
        'note': 'the OSEB = every baseline domain tree complete, '
                'combined',
    }


# ---------------------------------------------------------------------
# Validation + the render payload.
# ---------------------------------------------------------------------

def resolve_cross_refs(manager, node):
    """One node's cross-tree references, resolved for the renderer
    (tt-9): home-tree title + target-node title + an honest exists
    flag — the zoom-to chip's whole payload. Cross-tree relations
    are NEVER edges; they only name where the related work lives."""
    resolved = []
    trees = {getattr(t, 'name', ''): t
             for t in _rows(manager, 'TechTreeDefinition')}
    nodes = {getattr(n, 'name', ''): n
             for n in _rows(manager, 'TechNode')}
    for ref in _loads(node, 'cross_refs_json', []):
        if not isinstance(ref, dict):
            continue
        tree = ref.get('tree', '')
        target = ref.get('node', '')
        tree_row = trees.get(tree)
        node_row = nodes.get(target)
        resolved.append({
            'tree': tree,
            'node': target,
            'relation': ref.get('relation', ''),
            'treeTitle': (getattr(tree_row, 'title', '')
                          or tree) if tree_row else tree,
            'nodeTitle': (getattr(node_row, 'title', '')
                          or target) if node_row else target,
            'exists': tree_row is not None and node_row is not None
            and getattr(node_row, 'tree_name', '') == tree,
        })
    return resolved


def _finding(severity, check, subject, evidence, knob, action):
    return {'severity': severity, 'check': check, 'subject': subject,
            'evidence': evidence, 'knob': knob, 'action': action}


def validate_tree(manager, tree_name):
    """Structural findings over one tree's rows — every failure
    names the knob and the action (the aqp-1 idiom)."""
    definition = _named(manager, 'TechTreeDefinition', tree_name)
    if definition is None:
        return {'ok': False,
                'error': f'no TechTreeDefinition named "{tree_name}"'}
    findings = []
    nodes = {getattr(n, 'name', ''): n
             for n in _scoped(manager, 'TechNode', tree_name)}
    for node in nodes.values():
        for dep in _loads(node, 'depends_on_json', []):
            if dep not in nodes:
                findings.append(_finding(
                    'error', 'unknown-tech-dependency',
                    getattr(node, 'name', ''),
                    f'depends_on lists "{dep}" but no TechNode in '
                    f'tree "{tree_name}" has that name',
                    'TechNode.depends_on_json',
                    f'add a TechNode named "{dep}" or drop the dep'))
            if dep == getattr(node, 'name', ''):
                findings.append(_finding(
                    'error', 'self-dependency',
                    getattr(node, 'name', ''),
                    'a technology cannot depend on itself',
                    'TechNode.depends_on_json', 'drop the self-dep'))
    for node in nodes.values():
        for ref in resolve_cross_refs(manager, node):
            if not ref['exists']:
                findings.append(_finding(
                    'warn', 'dangling-cross-ref',
                    getattr(node, 'name', ''),
                    f'cross-tree ref points at "{ref["node"]}" in '
                    f'tree "{ref["tree"]}" but no such node exists '
                    'there',
                    'TechNode.cross_refs_json',
                    'add that node to its tree or drop the ref'))
    for asg in _scoped(manager, 'TechSegmentAssignment', tree_name):
        aname = getattr(asg, 'name', '')
        if getattr(asg, 'tech_node', '') not in nodes:
            findings.append(_finding(
                'error', 'assignment-unknown-node', aname,
                f'assignment targets node '
                f'"{getattr(asg, "tech_node", "")}" which does not '
                'exist in this tree',
                'TechSegmentAssignment.tech_node',
                'repoint the assignment or add the node'))
        if getattr(asg, 'segment_kind', '') not in SEGMENT_KINDS:
            findings.append(_finding(
                'error', 'unknown-segment-kind', aname,
                f'segment_kind '
                f'"{getattr(asg, "segment_kind", "")}" is not one of '
                f'{SEGMENT_KINDS}',
                'TechSegmentAssignment.segment_kind',
                'pick a known segment kind'))
        if not getattr(asg, 'ref_name', ''):
            findings.append(_finding(
                'error', 'assignment-without-ref', aname,
                'assignment fills a segment but references nothing',
                'TechSegmentAssignment.ref_name',
                'point it at a module/artifact/model/policy'))
    for seg in _scoped(manager, 'TechSegment', tree_name):
        if getattr(seg, 'kind', '') not in SEGMENT_KINDS:
            findings.append(_finding(
                'error', 'unknown-segment-kind',
                getattr(seg, 'name', ''),
                f'kind "{getattr(seg, "kind", "")}" is not one of '
                f'{SEGMENT_KINDS}', 'TechSegment.kind',
                'pick a known segment kind'))
    errors = [f for f in findings if f['severity'] == 'error']
    return {'ok': True, 'tree': tree_name, 'valid': not errors,
            'findings': findings, 'errorCount': len(errors),
            'warnCount': len(findings) - len(errors)}


def tree_payload(manager, tree_name):
    """Everything the tech-tree render mode draws (tt-4): nodes with
    derived segments/completion, designated dependency edges, and
    the tree rollup — one GET, no assembly client-side."""
    completion = tree_completion(manager, tree_name)
    if not completion.get('ok'):
        return completion
    designate_tech_transients(manager, tree_name)
    nodes = _scoped(manager, 'TechNode', tree_name)
    by_name = {r['node']: r for r in completion['nodes']}
    return {
        'ok': True, 'tree': {
            'name': tree_name,
            'title': completion['title'],
            'owner': completion['owner'],
            'isBaseline': completion['isBaseline'],
            'completionLevel': completion['completionLevel'],
            'baselineAchieved': completion['baselineAchieved'],
        },
        'segmentColors': dict(SEGMENT_COLORS),
        'nodes': [
            {'name': getattr(n, 'name', ''),
             'title': (getattr(n, 'title', '')
                       or getattr(n, 'name', '')),
             'description': getattr(n, 'description', ''),
             'dependsOn': _loads(n, 'depends_on_json', []),
             'crossRefs': resolve_cross_refs(manager, n),
             'layoutHints': _loads(n, 'layout_hints_json', {}),
             **{k: by_name.get(getattr(n, 'name', ''), {}).get(k)
                for k in ('segmentsPresent', 'segments',
                          'completionLevel', 'gaps')}}
            for n in sorted(nodes,
                            key=lambda n: getattr(n, 'name', ''))],
        'edges': [
            {'name': getattr(e, 'name', ''),
             'techNode': getattr(e, 'tech_node', ''),
             'dependsOnTech': getattr(e, 'depends_on_tech', ''),
             'isPrimary': getattr(e, 'is_primary', False),
             'isTransient': getattr(e, 'is_transient', False)}
            for e in _scoped(manager, 'TechDependencyEdge',
                             tree_name)],
        'gaps': completion['gaps'],
    }
