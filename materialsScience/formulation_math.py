"""
@cross-cutting
@module materialsScience.formulation_math
@tags @xc:bindings

Rules-of-mixtures math for formulations — the computation the legacy
schema always implied but never implemented (PropertyEffect carries
effectPerWeightPercent and FormulationComponent carries weightPercent,
yet nothing multiplied them).

Three pure layers, engine-agnostic (dicts in, dicts out) so both the
CRUDE/API surface and the multi-solution stage search can drive them:

  1. predict_formulation_properties — level-0 LINEAR blend:
     predicted[prop] = base[prop] + Σ weight% × effectPerWeightPercent
  2. mixture_bounds — classical Voigt (upper) / Reuss (lower) bounds
     for a property over constituents with volume fractions; 'hybrid'
     returns the Hill average. The `rule` is a knob, not a default.
  3. score_against_targets — PropertyTarget semantics: hard min/max are
     VIOLATIONS (verdict-level), optimum + weight give the score.

@consumers
  - materialsScience.selftest_materials_basis
  - (next phase) wax-composite target search over formulations
@see /OVERLAP_MAP.md
"""


def predict_formulation_properties(components, effects, base_properties=None):
    """Level-0 linear blend.

    components: [{'materialId': str, 'weightPercent': float}, ...]
        (FormulationComponent rows, additive/compatibilizer roles)
    effects: [{'additiveId': str, 'propertyName': str,
               'effectPerWeightPercent': float}, ...] (PropertyEffect
        rows; additiveId matches components' materialId)
    base_properties: {propertyName: baseValue} of the base material
        (missing props blend from 0 — deltas-only mode).

    Returns {'predicted': {prop: value}, 'contributions':
        {prop: [{'materialId', 'weightPercent', 'delta'}, ...]}} —
    contributions keep the math inspectable (explainability).
    """
    predicted = dict(base_properties or {})
    contributions = {}
    effectsByAdditive = {}
    for eff in effects:
        effectsByAdditive.setdefault(str(eff['additiveId']), []).append(eff)

    for comp in components:
        materialId = str(comp.get('materialId', ''))
        weight = float(comp.get('weightPercent', 0.0) or 0.0)
        if weight == 0.0:
            continue
        for eff in effectsByAdditive.get(materialId, []):
            prop = eff['propertyName']
            perPercent = float(eff.get('effectPerWeightPercent', 0.0) or 0.0)
            if perPercent == 0.0:
                # Unquantified effect rows (intent-only seeds) must not
                # count as predictions — a phantom zero-delta would let
                # score_against_targets treat the property as known.
                continue
            delta = weight * perPercent
            predicted[prop] = predicted.get(prop, 0.0) + delta
            contributions.setdefault(prop, []).append({
                'materialId': materialId,
                'weightPercent': weight,
                'delta': delta,
            })
    return {'predicted': predicted, 'contributions': contributions}


def mixture_bounds(values, volume_fractions, rule='hybrid'):
    """Classical rules-of-mixtures bounds for ONE property.

    values: per-constituent property values (all > 0 for Reuss)
    volume_fractions: same length, should sum to ~1 (validated)
    rule knob: 'voigt' (upper bound), 'reuss' (lower bound),
        'hybrid' (Voigt-Reuss-Hill average)

    Returns {'voigt', 'reuss', 'value', 'rule'}.
    """
    if len(values) != len(volume_fractions) or not values:
        raise ValueError('values and volume_fractions must be equal-length, non-empty')
    total = sum(volume_fractions)
    if not (0.99 <= total <= 1.01):
        raise ValueError(f'volume fractions sum to {total}, expected ~1.0')

    voigt = sum(v * f for v, f in zip(values, volume_fractions))
    if any(v <= 0 for v in values):
        reuss = None   # harmonic mean undefined at/below zero
    else:
        reuss = 1.0 / sum(f / v for v, f in zip(values, volume_fractions))

    if rule == 'voigt':
        value = voigt
    elif rule == 'reuss':
        value = reuss
    elif rule == 'hybrid':
        value = (voigt + reuss) / 2.0 if reuss is not None else voigt
    else:
        raise ValueError(f"unknown mixture rule '{rule}' "
                         "(knobs: voigt | reuss | hybrid)")
    return {'voigt': voigt, 'reuss': reuss, 'value': value, 'rule': rule}


def score_against_targets(predicted, targets):
    """Score predicted properties against PropertyTarget rows.

    predicted: {propertyName: value}
    targets: [{'propertyName': str, 'optimumValue': float|None,
               'optimumRangeMin'/'optimumRangeMax': float|None,
               'hardMinimum'/'hardMaximum': float|None,
               'weight': float}, ...]

    Hard bounds are verdict-level: any breach → meets=False, listed in
    'violations' with evidence. The score (0-1) is the weighted mean of
    per-target closeness: 1.0 inside the optimum range / at the
    optimum, decaying with relative distance. Unpredicted targets score
    0 and are listed in 'unpredicted' (honest, not assumed-met).

    'meets' additionally requires every RANGE-defined target to be IN
    its band (inBand) — respecting hard bounds alone is not hitting the
    target. Optimum-only targets guide the score but don't gate meets
    (exact equality would be unreachable).
    """
    violations, perTarget, unpredicted = [], [], []
    weightTotal, weightedScore = 0.0, 0.0

    for target in targets:
        prop = target['propertyName']
        weight = float(target.get('weight', 1.0) or 1.0)
        weightTotal += weight
        if prop not in predicted:
            unpredicted.append(prop)
            continue
        value = float(predicted[prop])

        hardMin = target.get('hardMinimum')
        hardMax = target.get('hardMaximum')
        if hardMin is not None and value < float(hardMin):
            violations.append({'propertyName': prop, 'value': value,
                               'bound': 'hardMinimum', 'limit': float(hardMin)})
        if hardMax is not None and value > float(hardMax):
            violations.append({'propertyName': prop, 'value': value,
                               'bound': 'hardMaximum', 'limit': float(hardMax)})

        rangeMin = target.get('optimumRangeMin')
        rangeMax = target.get('optimumRangeMax')
        optimum = target.get('optimumValue')
        inBand = None
        if rangeMin is not None and rangeMax is not None:
            inBand = bool(float(rangeMin) <= value <= float(rangeMax))
        # Distance scale for the closeness gradient: the hard-bound
        # span when both bounds exist (keeps a usable gradient across
        # the whole feasible region — a tiny optimum must not flatten
        # the landscape for the batch stepper), else |optimum|/edge.
        wanted = (float(optimum) if optimum is not None
                  else float(rangeMin) if rangeMin is not None
                  else float(rangeMax) if rangeMax is not None else None)
        scaleCandidates = []
        if hardMin is not None and hardMax is not None \
                and float(hardMax) > float(hardMin):
            scaleCandidates.append(float(hardMax) - float(hardMin))
        if wanted is not None:
            for bound in (hardMin, hardMax):
                if bound is not None and float(bound) != wanted:
                    scaleCandidates.append(abs(float(bound) - wanted))
        if optimum is not None and float(optimum) != 0:
            scaleCandidates.append(abs(float(optimum)))
        if rangeMin is not None or rangeMax is not None:
            edge = float(rangeMin if rangeMin is not None else rangeMax)
            if edge != 0:
                scaleCandidates.append(abs(edge))
        scale = max(scaleCandidates) if scaleCandidates else 0.0
        if inBand:
            closeness = 1.0
        elif wanted is None or scale == 0.0:
            closeness = 1.0 if (wanted is not None and value == wanted) \
                else 0.0
        else:
            closeness = max(0.0, 1.0 - abs(value - wanted) / scale)
        weightedScore += weight * closeness
        perTarget.append({'propertyName': prop, 'value': value,
                          'closeness': closeness, 'weight': weight,
                          'inBand': inBand})

    outOfBand = [t for t in perTarget if t['inBand'] is False]
    return {
        'meets': not violations and not unpredicted and not outOfBand,
        'score': (weightedScore / weightTotal) if weightTotal else 0.0,
        'violations': violations,
        'unpredicted': unpredicted,
        'perTarget': perTarget,
    }
