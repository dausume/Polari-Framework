"""
@module tensortree.custom.explain

A MAPPING OR NODE, EXPLAINED (bp-3): what the step does in words, where it holds, what it loses, how it was checked,
and how to run it again. Read by GET /api/explain; shown on /object/:class/:name.
"""
import json

KIND_WORDS = {'projection': 'keeps some dimensions and drops the rest', 'reconstruction': 'rebuilds the fuller view from a reduced one',
              'decomposition': 'splits the data into simpler parts', 'aggregation': 'summarises many values into fewer', 'restriction': 'keeps only a range of an index',
              'scale': 'moves between scales of description', 'operator': 'applies a physical or mathematical law', 'coupling': 'feeds one simulation\'s values into another'}
LEVEL_WORDS = {'none': 'nothing has checked it', 'analytical': 'it follows from a formula', 'simulated': 'a simulation produced the numbers that agree with it', 'measured': 'it was measured'}


def _j(row, field, default):
    try:
        v = json.loads(getattr(row, field, '') or json.dumps(default))
    except Exception:
        v = default
    return v


def explain_mapping(manager, row):
    kind = str(getattr(row, 'kind', ''))
    validity = _j(row, 'validity_json', {})
    src, tgt = str(getattr(row, 'source_node', '')), str(getattr(row, 'target_node', ''))
    sdims, tdims = _j(row, 'source_dims_json', []), _j(row, 'target_dims_json', [])
    level = str(getattr(row, 'evidence_level', '') or 'none')
    steps = ['cd polari-rf-node/polari-framework', 'PYTHONPATH=.:modules python3 modules/tensortree/tensortree_selftest.py      # re-derives every seeded mapping and its checks']
    if getattr(row, 'coupling_ref', ''):
        steps.append('POST /api/tensortree/mappings/%s/couple      # (re)creates the runner\'s coupling row and executes it once (simulated evidence)' % row.name)
    if getattr(row, 'expression_ref', ''):
        steps.append('POST /api/tensormath/evaluate {"expression": "%s"}      # the expression this mapping computes' % getattr(row, 'expression_ref', ''))
    steps.append('POST /api/tensortree/mappings/%s/prove      # generates and checks the proof obligations the rules demand of it' % row.name)
    return {'in one sentence': '%s takes %s from the view %s and produces %s on the view %s — a %s mapping (%s).' % (row.name, ', '.join(map(str, sdims)) or 'its dims', src, ', '.join(map(str, tdims)) or 'its dims', tgt, kind, KIND_WORDS.get(kind, kind)),
            'what was done': (str(getattr(row, 'description', '') or '') + ' It holds where %s. What it loses: %s.' % (
                '; '.join('%s is within %s' % (k, v) for k, v in validity.items()) if isinstance(validity, dict) and validity else 'no domain is stated',
                str(getattr(row, 'loss_note', '') or 'nothing stated'))).strip(),
            'inputs': {'from view (source node)': src, 'consumes (source dims)': ', '.join(map(str, sdims)), 'to view (target node)': tgt, 'produces (target dims)': ', '.join(map(str, tdims)),
                       'computed by': str(getattr(row, 'expression_ref', '') or getattr(row, 'coupling_ref', '') or 'not stated'), 'units': str(getattr(row, 'units', '') or '')},
            'result': 'status %s · evidence %s%s' % (getattr(row, 'mapping_status', ''), level, (' · reconstruction error %s (%s)' % (getattr(row, 'reconstruction_error'), getattr(row, 'error_method') or 'method unstated')) if getattr(row, 'reconstruction_error', None) not in (None, '', 0, 0.0) else ''),
            'how to reproduce': steps, 'evidence': str(getattr(row, 'evidence_ref', '') or 'none recorded'),
            'how far to trust it': '%s; its proof obligations (the logic between it and its neighbours) are listed on the mathproofs page under ob:…:%s' % (LEVEL_WORDS.get(level, level), row.name),
            'related': [{'class': 'TensorNode', 'name': src}, {'class': 'TensorNode', 'name': tgt}]}


def explain_node(manager, row):
    dims = _j(row, 'dims_json', [])
    gp = _j(row, 'global_params_json', {})
    return {'in one sentence': '%s is the view "%s" of the tensor %s in the tree %s; it is %s.' % (row.name, getattr(row, 'title', ''), getattr(row, 'tensor', ''), getattr(row, 'tree', ''), getattr(row, 'status', '')),
            'what was done': 'Its %d dimensions (%s) were each bound to a visual channel; the validator sets the status: resolved only when every dimension has a coherent binding. It renders through the binding %s%s.'
                             % (len(dims), ', '.join(map(str, dims)), getattr(row, 'binding_ref', '') or '—', (' in the sim space %s' % gp.get('sim_space')) if isinstance(gp, dict) and gp.get('sim_space') else ''),
            'inputs': {'tree': str(getattr(row, 'tree', '')), 'parent view': str(getattr(row, 'parent', '') or 'the root'), 'tensor': str(getattr(row, 'tensor', '')), 'dimensions': ', '.join(map(str, dims)),
                       'binding': str(getattr(row, 'binding_ref', '')), 'constants across the view': json.dumps(gp) if gp else '—'},
            'result': str(getattr(row, 'status', '')),
            'how to reproduce': ['GET /api/tensortree/trees/%s/validate      # re-runs the validator that sets this status' % getattr(row, 'tree', ''), 'GET /api/tensortree/trees/%s/view      # the reading the panel draws' % getattr(row, 'tree', '')],
            'how far to trust it': 'the status is computed, never typed in',
            'related': [{'class': 'TensorTreeDefinition', 'name': str(getattr(row, 'tree', ''))}] + ([{'class': 'TensorNode', 'name': str(getattr(row, 'parent'))}] if getattr(row, 'parent', '') else [])}


EXPLAINERS = {'TensorMapping': explain_mapping, 'TensorNode': explain_node}
