"""
@cross-cutting
@module materialsScience.batch_refine
@tags @xc:bindings

BATCH-INCREMENTAL refinement toward targets (Dustin's directive:
"go in batch-increments stepping through trying to hit targets, and/or
using a scoring approach to get as close as possible").

Complements composite_search's exhaustive grid: instead of sweeping
everything, start from a formulation and take the best scoring step
each BATCH — every batch proposes neighbors (± loadingStep on each
component, adding an unused additive at one step, dropping a
component), scores them all, and moves to the best. Stops when targets
are MET, when a batch offers no improvement (CONVERGED — the honest
"as close as possible" answer), or at maxBatches.

The whole trajectory is returned batch by batch (explainability: you
can see WHICH increment moved WHAT), and gap_analysis names, per unmet
target, which additives could still close the distance — evidence-
bearing suggestions, never auto-applied.

Same thermal gate as the grid search: neighbors whose processing
window closes are refused, not silently skipped.
"""

from materialsScience.formulation_math import (
    predict_formulation_properties, score_against_targets,
)


def _score(components, effects, base_properties, targets,
           thermal=None):
    predicted = predict_formulation_properties(
        components, effects, base_properties)['predicted']
    verdict = score_against_targets(predicted, targets)
    result = {'components': components, 'predicted': predicted,
              'meets': verdict['meets'], 'score': verdict['score'],
              'violations': list(verdict['violations']),
              'unpredicted': verdict['unpredicted']}
    if thermal is not None:
        thermalVerdict = thermal(components)
        result['thermal'] = thermalVerdict
        if not thermalVerdict['ok']:
            result['meets'] = False
            result['violations'].append({
                'type': 'thermal-window',
                'detail': thermalVerdict.get('refusal', 'window closed')})
    return result


def _neighbors(components, additives, loadingStep, perAdditiveCap,
               maxTotalLoad):
    """All single-increment moves from a formulation."""
    current = {c['materialId']: c['weightPercent'] for c in components}
    total = sum(current.values())
    moves = []
    # Seeded maxLoadingPercent (typical-loading ranges) caps each
    # additive; the perAdditiveCap knob is the ceiling either way.
    caps = {a['id']: min(float(a.get('maxLoadingPercent') or 0.0)
                         or float(perAdditiveCap),
                         float(perAdditiveCap))
            for a in additives}

    def asComponents(loadings):
        return [{'materialId': mid, 'weightPercent': round(w, 6)}
                for mid, w in sorted(loadings.items()) if w > 0]

    for mid in current:
        up = dict(current)
        up[mid] = current[mid] + loadingStep
        if up[mid] <= caps.get(mid, perAdditiveCap) + 1e-9 \
                and total + loadingStep <= maxTotalLoad + 1e-9:
            moves.append(('increase ' + mid, asComponents(up)))
        down = dict(current)
        down[mid] = current[mid] - loadingStep
        label = ('drop ' if down[mid] <= 1e-9 else 'decrease ') + mid
        moves.append((label, asComponents(down)))

    for additive in additives:
        mid = additive['id']
        if mid in current:
            continue
        if total + loadingStep > maxTotalLoad + 1e-9:
            continue
        add = dict(current)
        add[mid] = loadingStep
        moves.append(('add ' + mid, asComponents(add)))
    return moves


def refine_formulation(base_properties, targets, additives, effects,
                       start_components=(), loadingStep=2.5,
                       minLoadingStep=None,
                       perAdditiveCap=20.0, maxTotalLoad=30.0,
                       maxBatches=40, thermal_profiles=None,
                       process=None, base_material_name='',
                       thermal_knobs=None):
    """Batch-incremental stepping with ADAPTIVE increments. Returns
    {'outcome': 'met'|'converged'|'batch-limit', 'best', 'trajectory',
    'batches', 'gapAnalysis'}.

    When a batch offers no improvement at the current increment, the
    step HALVES (down to minLoadingStep, default loadingStep/8) and
    stepping continues — coarse strides toward the target, fine strides
    to land inside tight optimum bands. Only when the finest step
    offers nothing is the outcome 'converged' (the honest closest-
    approach answer). trajectory[i] = {'batch', 'move', 'score',
    'meets'} including 'halve step to X' entries — the whole path is
    inspectable.
    """
    thermal = None
    if process is not None:
        from materialsScience.composite_search import thermal_name
        from materialsScience.thermal_windows import (
            machinable_verdict, printable_verdict,
        )
        gateFn = (printable_verdict if process == '3d-print'
                  else machinable_verdict)
        profiles = thermal_profiles or {}
        knobs = thermal_knobs or {}
        additiveById = {a['id']: a for a in additives}

        def thermal(components):
            names = ([base_material_name] if base_material_name else []) \
                + [thermal_name(additiveById[c['materialId']])
                   for c in components
                   if c['materialId'] in additiveById]
            return gateFn(names, profiles, **knobs)

    quantified = {e['additiveId'] for e in effects
                  if e.get('effectPerWeightPercent')}
    usable = [a for a in additives if a['id'] in quantified]

    if minLoadingStep is None:
        minLoadingStep = loadingStep / 8.0
    step = float(loadingStep)

    current = _score(list(start_components), effects, base_properties,
                     targets, thermal)
    trajectory = [{'batch': 0, 'move': 'start', 'score': current['score'],
                   'meets': current['meets']}]
    outcome = 'batch-limit'

    for batch in range(1, maxBatches + 1):
        if current['meets']:
            outcome = 'met'
            break
        candidates = []
        for move, components in _neighbors(
                current['components'], usable, step,
                perAdditiveCap, maxTotalLoad):
            scored = _score(components, effects, base_properties,
                            targets, thermal)
            scored['move'] = move
            candidates.append(scored)
        # Meets beats score; thermal-closed candidates can never lead.
        best = max(candidates, key=lambda c: (c['meets'], c['score'])) \
            if candidates else None
        if best is None or (best['meets'], best['score']) \
                <= (current['meets'], current['score']):
            # Plateau at this increment — refine the stride before
            # giving up (coarse to approach, fine to land in-band).
            if step / 2.0 >= minLoadingStep - 1e-12:
                step = step / 2.0
                trajectory.append({'batch': batch,
                                   'move': f'halve step to {step}',
                                   'score': current['score'],
                                   'meets': current['meets']})
                continue
            outcome = 'converged'
            break
        current = best
        trajectory.append({'batch': batch, 'move': best['move'],
                           'score': best['score'],
                           'meets': best['meets']})
    else:
        batch = maxBatches
    if current['meets']:
        outcome = 'met'

    return {
        'outcome': outcome,
        'best': current,
        'trajectory': trajectory,
        'batches': trajectory[-1]['batch'],
        'gapAnalysis': gap_analysis(current, targets, effects),
    }


def gap_analysis(candidate, targets, effects):
    """Per unmet target: how far off, and which additives could still
    move that property (evidence-bearing, never auto-applied)."""
    predicted = candidate['predicted']
    moversByProp = {}
    for effect in effects:
        perPercent = float(effect.get('effectPerWeightPercent', 0) or 0)
        if perPercent:
            moversByProp.setdefault(effect['propertyName'], []).append(
                {'additiveId': effect['additiveId'],
                 'effectPerWeightPercent': perPercent})
    gaps = []
    for target in targets:
        prop = target['propertyName']
        optimum = target.get('optimumValue')
        if prop not in predicted:
            gaps.append({
                'propertyName': prop, 'status': 'unpredicted',
                'evidence': 'no quantified PropertyEffect moves this '
                            'property — the search cannot see it',
                'movers': [],
            })
            continue
        value = predicted[prop]
        rangeMin = target.get('optimumRangeMin')
        rangeMax = target.get('optimumRangeMax')
        inRange = (rangeMin is not None and rangeMax is not None
                   and rangeMin <= value <= rangeMax)
        if inRange or (optimum is not None and value == optimum):
            continue
        wanted = optimum if optimum is not None else rangeMin
        delta = (wanted - value) if wanted is not None else 0.0
        movers = sorted(
            (m for m in moversByProp.get(prop, [])
             if m['effectPerWeightPercent'] * delta > 0),
            key=lambda m: -abs(m['effectPerWeightPercent']))
        gaps.append({
            'propertyName': prop, 'status': 'off-target',
            'value': value, 'wanted': wanted, 'delta': delta,
            'movers': movers[:3],
        })
    return gaps
