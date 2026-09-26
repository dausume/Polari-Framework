"""
@module tensortree.custom.tensortree_discover

WHICH MAPPINGS CAN THIS SELECTION TAKE (plan §15, §F3): hard filters, then a CONFIGURED score.
tt-13 (2026-09-26): discovery ACROSS trees — mappings written for another node are candidates when every dim they need exists
here by name AND unit (the §F3 units filter, hard: a different unit is inapplicable, an unrecorded unit is inapplicable and says
which side is silent); they carry `cross_tree`, `source_node`, `units` and a lower context term.

Candidate only if: the mapping's source node is the selection's node, every source dim the mapping needs is
present in the selection, and the selection lies inside the mapping's validity domain (per dim, when given).
An invalid mapping is NEVER rescued by a score. Survivors are ranked by

    Score = w_E·E + w_D·D + w_V·V + w_C·C + w_U·(1 − U)

with the weights and the evidence map read from the default TensorDiscoveryPolicy row (knobs, not constants).
The answer is a SUGGESTION list with the evidence on each row; the user chooses.
"""
import json

DEFAULT_POLICY = {'w_evidence': 0.30, 'w_dims': 0.25, 'w_validity': 0.25, 'w_context': 0.10, 'w_uncertainty': 0.10,
                  'evidence_map': {'measured': 1.0, 'validated': 0.85, 'implemented': 0.65, 'analytical': 0.4,
                                   'proposed': 0.2, 'none': 0.1}}


def _rows(manager, cls):
    return list((getattr(manager, 'objectTables', {}) or {}).get(cls, {}).values())


def _j(s, default):
    try:
        v = json.loads(s or '')
        return v if v is not None else default
    except Exception:
        return default


def policy(manager):
    rows = [p for p in _rows(manager, 'TensorDiscoveryPolicy') if getattr(p, 'is_default', False)]
    if not rows:
        return dict(DEFAULT_POLICY)
    p = rows[0]
    return {'w_evidence': float(getattr(p, 'w_evidence', .3)), 'w_dims': float(getattr(p, 'w_dims', .25)),
            'w_validity': float(getattr(p, 'w_validity', .25)), 'w_context': float(getattr(p, 'w_context', .1)),
            'w_uncertainty': float(getattr(p, 'w_uncertainty', .1)),
            'evidence_map': _j(getattr(p, 'evidence_map_json', '{}'), DEFAULT_POLICY['evidence_map']) or DEFAULT_POLICY['evidence_map']}


def evidence_score(mapping, pol):
    """evidence_level (none|analytical|simulated|measured) and mapping_status (proposed|implemented|validated)
    together: a simulated+validated row scores 'validated'; measured wins; a proposed row with no evidence is 'proposed'."""
    lvl = str(getattr(mapping, 'evidence_level', 'none') or 'none'); st = str(getattr(mapping, 'mapping_status', 'proposed') or 'proposed')
    m = pol['evidence_map']
    if lvl == 'measured': key = 'measured'
    elif lvl == 'simulated': key = 'validated' if st == 'validated' else 'implemented'
    elif lvl == 'analytical': key = 'analytical'
    else: key = 'implemented' if st in ('implemented', 'validated') else ('proposed' if st == 'proposed' else 'none')
    return float(m.get(key, m.get('none', 0.1))), key


def _validity_coverage(mapping, ranges):
    """1.0 when the selection lies inside the mapping's validity domain on every dim it states; the fraction of
    covered extent otherwise; None = OUTSIDE on some dim (a hard failure)."""
    dom = _j(getattr(mapping, 'validity_json', '{}'), {})
    if not isinstance(dom, dict) or not dom:
        return 0.5   # no stated domain: neither proven nor refused
    covs = []
    for dim, lim in dom.items():
        sel = ranges.get(dim)
        if sel is None or not (isinstance(lim, list) and len(lim) == 2):
            continue
        lo, hi = float(lim[0]), float(lim[1]); slo, shi = float(sel[0]), float(sel[1])
        if shi < lo or slo > hi:
            return None
        inside = min(shi, hi) - max(slo, lo); ext = max(shi - slo, 1e-12)
        covs.append(max(0.0, min(1.0, inside / ext)))
        if slo < lo or shi > hi:
            return None
    return sum(covs) / len(covs) if covs else 0.5


def node_dim_units(manager, node_name):
    """tt-13: {short dim name: unit} for one node — from its LocalizedDimension rows (`field.T` → `T`, localizing TensorDimension
    `dimension`) through the node's Tensor: a TensorDimension row (tensor == the node's tensor, name == dimension) or the Tensor's
    dimensions_json entry; '' when no unit is recorded anywhere (unknown, said so — never assumed compatible)."""
    node = next((n for n in _rows(manager, 'TensorNode') if str(n.name) == node_name), None)
    tensor = str(getattr(node, 'tensor', '') or '') if node is not None else ''
    tdims = {str(d.name): str(getattr(d, 'unit', '') or '') for d in _rows(manager, 'TensorDimension') if str(getattr(d, 'tensor', '')) == tensor}
    trow = next((t for t in _rows(manager, 'Tensor') if str(t.name) == tensor), None)
    for e in _j(getattr(trow, 'dimensions_json', '[]'), []) if trow is not None else []:
        if isinstance(e, dict) and e.get('name') and not tdims.get(str(e['name'])):
            tdims[str(e['name'])] = str(e.get('unit', '') or '')
    out = {}
    for ld in _rows(manager, 'LocalizedDimension'):
        if str(getattr(ld, 'node', '')) != node_name:
            continue
        short = str(ld.name).split('.')[-1]; dim = str(getattr(ld, 'dimension', '') or short)
        out[short] = tdims.get(dim, tdims.get(short, ''))
    return out


def _unit_norm(u):
    return str(u or '').strip().lower().replace('µ', 'u')


def discover(manager, selection, context_node='', context_mapping=''):
    """`context_mapping` = the link the person arrived through (a follow): the propose door then offers the chain pair too."""
    from tensortree.custom import tensortree_logic as _logic
    node = str(getattr(selection, 'node', '') or ''); ranges = _j(getattr(selection, 'ranges_json', '{}'), {})
    have = set(ranges.keys()); pol = policy(manager)
    out, inapplicable, refuted = [], [], []   # three words for three things: not defined here | falsified | scored
    for m in _rows(manager, 'TensorMapping'):
        name = str(getattr(m, 'name', ''))
        if str(getattr(m, 'source_node', '') or '') != node:
            continue
        need = [str(d) for d in _j(getattr(m, 'source_dims_json', '[]'), [])]
        missing = [d for d in need if d not in have]
        if missing:
            inapplicable.append({'mapping': name, 'kind': 'dims-not-in-selection', 'why': 'not defined on this selection: it needs dims the selection does not have (%s)' % ', '.join(missing)}); continue
        V = _validity_coverage(m, ranges)
        if V is None:
            inapplicable.append({'mapping': name, 'kind': 'outside-validity', 'why': 'not defined on this state space: the selection lies outside the mapping\'s validity domain (the model shifts with the state, it is not falsified)'}); continue
        # pf-0 / D-pf-3: a mapping with a genuinely FALSIFIED obligation (a counterexample exists) is set aside as refuted;
        # an open or undetermined one is shown with its badge and still scored
        try:
            from tensortree.custom.tensortree_logic import of_mapping
            logic = of_mapping(manager, name)
        except Exception:   # pragma: no cover
            logic = {'available': False, 'refuted': [], 'open': [], 'ok': [], 'badge': 'unavailable'}
        if logic['refuted']:
            r0 = logic['refuted'][0]
            refuted.append({'mapping': name, 'kind': 'obligation-refuted', 'why': 'falsified: obligation %s (%s) has a counterexample %s' % (r0['name'], r0['rule'], r0.get('counterexample')), 'logic': logic['badge']}); continue
        E, ekey = evidence_score(m, pol)
        D = (len(need) / max(len(have), 1)) if need else 0.5
        C = 1.0 if (context_node and str(getattr(m, 'target_node', '')) == context_node) else 0.5
        unc = _j(getattr(m, 'uncertainty_json', '{}'), {})
        U = float(unc.get('relative', 0.0)) if isinstance(unc, dict) else 0.0
        U = max(0.0, min(1.0, U))
        score = (pol['w_evidence'] * E + pol['w_dims'] * D + pol['w_validity'] * V + pol['w_context'] * C
                 + pol['w_uncertainty'] * (1.0 - U))
        out.append({'mapping': name, 'kind': str(getattr(m, 'kind', '')), 'target_node': str(getattr(m, 'target_node', '')),
                    'score': round(score, 4), 'terms': {'E': round(E, 3), 'D': round(D, 3), 'V': round(V, 3), 'C': C, 'U': U},
                    'evidence': ekey, 'evidence_ref': str(getattr(m, 'evidence_ref', '') or ''),
                    'mapping_status': str(getattr(m, 'mapping_status', '')), 'evidence_level': str(getattr(m, 'evidence_level', '')),
                    'loss_note': str(getattr(m, 'loss_note', '') or ''),
                    'logic': logic['badge'], 'open_obligations': [o['name'] for o in logic['open']],
                    'propose': _logic.propose_door(name, str(getattr(selection, 'name', '')), via=context_mapping)})
    # ---- tt-13: DISCOVERY ACROSS TREES — a mapping whose source is ANOTHER node is a candidate here when every dim it needs
    # exists on this selection's node WITH THE SAME UNIT (the §F3 "units compatible" filter, a hard one): the same dim name in a
    # different unit is inapplicable and says both units; a dim with no unit recorded on either side is inapplicable and says
    # which side is silent — never assumed compatible. Cross-tree candidates carry `cross_tree` + `source_node`, a lower
    # context term (C = 0.25: a mapping written for another node), and the same validity / obligation filters.
    units_here = node_dim_units(manager, node)
    units_cache = {}
    cross = 0
    for m in _rows(manager, 'TensorMapping'):
        name = str(getattr(m, 'name', '')); src = str(getattr(m, 'source_node', '') or '')
        if not src or src == node:
            continue
        need = [str(d) for d in _j(getattr(m, 'source_dims_json', '[]'), [])]
        if not need or any(d not in have for d in need):
            continue   # not even the dims: not a cross-tree candidate, and not worth a row of refusals per mapping in the instance
        if src not in units_cache:
            units_cache[src] = node_dim_units(manager, src)
        units_src = units_cache[src]
        unknown = [d for d in need if not units_here.get(d) or not units_src.get(d)]
        if unknown:
            inapplicable.append({'mapping': name, 'kind': 'units-unknown', 'cross_tree': True, 'source_node': src,
                                 'why': 'written for node %s; the dims match by name (%s) but no unit is recorded for %s on %s — compatibility cannot be said, so it is not assumed' % (
                                     src, ', '.join(need), ', '.join(unknown), ' / '.join(sorted({('this node' if not units_here.get(d) else '') or ('node ' + src) for d in unknown} - {''})))}); continue
        bad = [(d, units_here[d], units_src[d]) for d in need if _unit_norm(units_here[d]) != _unit_norm(units_src[d])]
        if bad:
            inapplicable.append({'mapping': name, 'kind': 'units-incompatible', 'cross_tree': True, 'source_node': src,
                                 'why': 'written for node %s; the dims match by name but not by unit: %s' % (src, '; '.join('%s is %s here, %s there' % b for b in bad))}); continue
        V = _validity_coverage(m, ranges)
        if V is None:
            inapplicable.append({'mapping': name, 'kind': 'outside-validity', 'cross_tree': True, 'source_node': src, 'why': 'written for node %s (dims and units match); the selection lies outside its validity domain' % src}); continue
        try:
            from tensortree.custom.tensortree_logic import of_mapping
            logic = of_mapping(manager, name)
        except Exception:   # pragma: no cover
            logic = {'available': False, 'refuted': [], 'open': [], 'ok': [], 'badge': 'unavailable'}
        if logic['refuted']:
            r0 = logic['refuted'][0]
            refuted.append({'mapping': name, 'kind': 'obligation-refuted', 'cross_tree': True, 'source_node': src, 'why': 'falsified: obligation %s (%s) has a counterexample %s' % (r0['name'], r0['rule'], r0.get('counterexample')), 'logic': logic['badge']}); continue
        E, ekey = evidence_score(m, pol)
        D = len(need) / max(len(have), 1)
        C = 0.25   # a mapping written for another node: relevant here only through the shared dims and units — said so in the terms
        unc = _j(getattr(m, 'uncertainty_json', '{}'), {})
        U = max(0.0, min(1.0, float(unc.get('relative', 0.0)) if isinstance(unc, dict) else 0.0))
        score = pol['w_evidence'] * E + pol['w_dims'] * D + pol['w_validity'] * V + pol['w_context'] * C + pol['w_uncertainty'] * (1.0 - U)
        out.append({'mapping': name, 'kind': str(getattr(m, 'kind', '')), 'target_node': str(getattr(m, 'target_node', '')), 'cross_tree': True, 'source_node': src,
                    'units': {d: units_here[d] for d in need}, 'score': round(score, 4), 'terms': {'E': round(E, 3), 'D': round(D, 3), 'V': round(V, 3), 'C': C, 'U': U},
                    'evidence': ekey, 'evidence_ref': str(getattr(m, 'evidence_ref', '') or ''), 'mapping_status': str(getattr(m, 'mapping_status', '')), 'evidence_level': str(getattr(m, 'evidence_level', '')),
                    'loss_note': str(getattr(m, 'loss_note', '') or ''), 'logic': logic['badge'], 'open_obligations': [o['name'] for o in logic['open']],
                    'why_here': 'written for %s; every dim it needs (%s) exists on this node with the same unit (%s)' % (src, ', '.join(need), ', '.join('%s: %s' % (d, units_here[d]) for d in need)),
                    'propose': _logic.propose_door(name, str(getattr(selection, 'name', '')), via=context_mapping)})
        cross += 1
    out.sort(key=lambda r: -r['score'])
    return {'selection': str(getattr(selection, 'name', '')), 'node': node, 'candidates': out, 'inapplicable': inapplicable, 'refuted': refuted,
            'refused': inapplicable + refuted,   # the pre-2026-09-25 key, kept for readers: the union, each entry saying which it is
            'cross_tree_candidates': cross, 'units_here': units_here,
            'policy': pol, 'note': 'inapplicable = not defined on this selection\'s state space (dims, validity) — the model shifts with the state, nothing is falsified; '
                                   'refuted = a proof obligation with a counterexample; the score only ORDERS applicable candidates — the user chooses'}
