"""
@module pspp.custom.dataset_interpolation

The ONE generic reader for DigitizedDataset rows. Policies:
'linear' / 'log-linear' interpolate the single numeric independent
variable (after filtering by any discrete selectors); 'none' is
discrete lookup only. Out-of-range queries REFUSE naming the validity
domain and the dataset row (the knob) — extrapolation is UNSUPPORTED,
plan invariant I6. Every successful read returns a claim-shaped
evidence payload (evidence method 'interpolated' or 'literature' for
exact hits) with the interpolation band as honest uncertainty.
"""

import math


def _numeric_var(dataset, query):
    """The one numeric independent variable + the discrete selectors."""
    numeric, discrete = [], []
    for var in dataset['independentVariables']:
        sample = next((p[var] for p in dataset['points'] if var in p),
                      None)
        if isinstance(sample, (int, float)):
            numeric.append(var)
        else:
            discrete.append(var)
    if not numeric and dataset['points']:
        return None, discrete
    return (numeric[0] if numeric else None), discrete


def _refuse(dataset, reason, suggestion):
    return {
        'ok': False,
        'refusal': reason,
        'dataset': dataset['name'],
        'source': dataset['sourceReference'],
        'validityDomain': dataset['validityDomain'],
        'suggestion': suggestion,
    }


def read_dataset(dataset, query):
    """Read one dataset (dict from digitized_datasets.dataset_dict) at
    a query {var: value, selector: label}. Returns {ok, values, band,
    evidence, assumptions} or an evidence-bearing refusal."""
    if dataset['status'] != 'ready':
        return _refuse(
            dataset,
            f"dataset {dataset['name']!r} is {dataset['status']!r} — "
            'not readable until re-digitized',
            'replace the row with a straight-on photo/scan read '
            '(digitization_method + points), then set status=ready')
    if not dataset['points']:
        return _refuse(
            dataset, f"dataset {dataset['name']!r} has no points",
            'enter digitized points on the row (data entry, not code)')

    xVar, selectors = _numeric_var(dataset, query)
    missing = [s for s in selectors if s not in query]
    if missing:
        options = {s: sorted({str(p.get(s)) for p in dataset['points']})
                   for s in missing}
        return _refuse(
            dataset, f'query must pick {missing} (discrete selectors)',
            f'available: {options}')

    points = [p for p in dataset['points']
              if all(p.get(s) == query[s] for s in selectors)]
    if not points:
        options = {s: sorted({str(p.get(s)) for p in dataset['points']})
                   for s in selectors}
        return _refuse(
            dataset,
            f'no points match selectors '
            f'{ {s: query[s] for s in selectors} }',
            f'available: {options}')

    deps = dataset['dependentVariables']
    policy = dataset['interpolationPolicy']
    assumptions = []
    note = dataset['sourceConditions'].get('note', '')
    if note:
        assumptions.append(f'source note: {note}')
    if dataset['digitizationError']:
        assumptions.append(
            f"digitization error: {dataset['digitizationError']}")

    def payload(values, band, method, extra_assumptions=()):
        return {
            'ok': True,
            'values': values,
            'band': band,
            'evidence': {
                'method': method,
                'dataset': dataset['name'],
                'source': dataset['sourceReference'],
                'digitizationMethod': dataset['digitizationMethod'],
            },
            'assumptions': assumptions + list(extra_assumptions),
        }

    if xVar is None or policy == 'none':
        # Discrete lookup: exact match on every queried variable.
        exact = [p for p in points
                 if all(p.get(k) == v for k, v in query.items())]
        if len(exact) == 1:
            values = {d: exact[0][d] for d in deps if d in exact[0]}
            return payload(values, {d: [values[d], values[d]]
                                    for d in values}, 'literature')
        listed = sorted({p[xVar] for p in points}) if xVar else []
        return _refuse(
            dataset,
            f'policy is {policy!r}/discrete — only the listed entries '
            f'exist (no general law in the source)',
            f'query one of {xVar}={listed} exactly, or mark any '
            'in-between use explicitly estimated' if listed else
            'query the listed rows exactly')

    if xVar not in query:
        return _refuse(dataset, f'query is missing {xVar!r}',
                       f"pass {{'{xVar}': <value>}}")
    x = query[xVar]
    points = sorted(points, key=lambda p: p[xVar])
    xs = [p[xVar] for p in points]
    if x < xs[0] or x > xs[-1]:
        return _refuse(
            dataset,
            f'{xVar}={x} is outside the supported range '
            f'[{xs[0]}, {xs[-1]}] — extrapolation is UNSUPPORTED',
            f"stay inside the validity domain of {dataset['name']!r}, "
            'or load a source that covers this range as a new '
            'DigitizedDataset row')

    # Exact hit → the source value itself.
    for p in points:
        if p[xVar] == x:
            values = {d: p[d] for d in deps if d in p}
            return payload(values, {d: [values[d], values[d]]
                                    for d in values}, 'literature')

    lo = max((p for p in points if p[xVar] < x),
             key=lambda p: p[xVar])
    hi = min((p for p in points if p[xVar] > x),
             key=lambda p: p[xVar])
    t = (x - lo[xVar]) / (hi[xVar] - lo[xVar])
    values, band = {}, {}
    for d in deps:
        if d not in lo or d not in hi:
            continue
        if policy == 'log-linear' and lo[d] > 0 and hi[d] > 0:
            values[d] = math.exp(
                math.log(lo[d]) + t * (math.log(hi[d]) - math.log(lo[d])))
        else:
            values[d] = lo[d] + t * (hi[d] - lo[d])
        band[d] = [min(lo[d], hi[d]), max(lo[d], hi[d])]
    return payload(
        values, band, 'interpolated',
        [f'interpolated ({policy}) between {xVar}={lo[xVar]} and '
         f'{xVar}={hi[xVar]} — band spans the bracketing source points'])
