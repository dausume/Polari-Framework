"""
@cross-cutting
@module materialsScience.composite_search
@tags @xc:bindings

Track C: TARGET-SEEKING SEARCH over wax-composite formulations.

Sweeps additive combinations + loadings (grid), predicts each
candidate's properties with formulation_math's linear blend, scores
against a TargetMaterialProfile's PropertyTargets, and ranks. Knobs
mirror the multi-solution stage search: stopPolicy 'first-winner' |
'exhaustive', continueAfterWinner, and the grid/loading caps.

HONESTY CONTRACT (the seeded data is thin and the search says so):
  - only 28/62 seeded PropertyEffects carry effectPerWeightPercent;
    targets whose property no additive can move are reported in each
    verdict's 'unpredicted', never assumed met;
  - base-material property values are NOT in the seeds — callers supply
    them (Dustin's 'manually entered property values' path); they are
    echoed into 'assumptions';
  - seeded additives carry no maxLoadingPercent — the perAdditiveCap
    knob applies and is listed in 'assumptions';
  - hard bounds of 0.0 in the seed JSON mean 'no bound' (the seed
    convention) and are normalized to None.

Pure functions over plain dicts — usable from selftests, the API layer,
and (later) dask-parallel attempt fan-out.
"""

import itertools
import json
import os

from materialsScience.formulation_math import (
    predict_formulation_properties, score_against_targets,
)

_LEGACY_DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'modules', 'polariMaterialsScienceModule', 'initialData')


def load_legacy_seed_data(dataDir=None):
    """The legacy module's JSON seeds as plain dicts:
    {'additives', 'effects', 'profiles', 'targets', 'compatibilizers'}."""
    dataDir = dataDir or _LEGACY_DATA_DIR
    def read(name):
        with open(os.path.join(dataDir, name)) as f:
            return json.load(f)
    return {
        'additives': read('materialAdditives.json'),
        'effects': read('propertyEffects.json'),
        'profiles': read('targetMaterialProfiles.json'),
        'targets': read('propertyTargets.json'),
        'compatibilizers': read('compatibilizers.json'),
    }


def normalize_targets(targetRows):
    """Seed convention: hard bounds of 0.0 mean 'no bound'; optimum
    range collapsed to the optimum when min==max."""
    normalized = []
    for row in targetRows:
        normalized.append({
            'propertyName': row['propertyName'],
            'optimumValue': row.get('optimumValue'),
            'optimumRangeMin': row.get('optimumRangeMin'),
            'optimumRangeMax': row.get('optimumRangeMax'),
            'hardMinimum': row.get('hardMinimum') or None,
            'hardMaximum': row.get('hardMaximum') or None,
            'weight': row.get('weight', 1.0),
        })
    return normalized


def predictable_properties(effects):
    return sorted({e['propertyName'] for e in effects
                   if e.get('effectPerWeightPercent')})


def thermal_name(additive):
    """Map an additive row to its ThermalProcessingProfile name
    ('Carnauba Wax' -> 'carnauba-wax')."""
    return str(additive.get('name', '')).strip().lower().replace(' ', '-')


def search_composites(base_properties, targets, additives, effects,
                      compatibilizers=(),
                      maxAdditives=2, loadingStep=5.0,
                      perAdditiveCap=20.0, maxTotalLoad=30.0,
                      stopPolicy='exhaustive', continueAfterWinner=True,
                      maxCandidates=20000,
                      base_material_name='', thermal_profiles=None,
                      process=None, thermal_knobs=None):
    """Grid search over formulations of a base + up to maxAdditives.

    base_properties: {prop: value} — MANUALLY ENTERED (echoed into
        assumptions; nothing is invented for missing props).
    targets: normalized PropertyTarget dicts (normalize_targets).
    additives/effects/compatibilizers: legacy-seed-shaped dicts.

    Knobs: maxAdditives, loadingStep (wt%), perAdditiveCap (stands in
    for the absent seed maxLoadingPercent), maxTotalLoad,
    stopPolicy 'first-winner'|'exhaustive', continueAfterWinner (only
    read for first-winner), maxCandidates (hard sweep cap — hit is
    reported, never silent).

    Thermal gate (Dustin's no-volatiles rule, thermal_windows.py):
    pass process='3d-print'|'cnc-machine' + thermal_profiles (from
    ThermalProcessingProfile rows) + base_material_name; combos whose
    processing window is empty/unknown carry a 'thermal-window'
    violation and can never be winners. thermal_knobs forwards
    marginC/minWindowWidthC/shopTempC/frictionMarginC.

    Returns {'ranked': [...], 'winners': [...], 'evaluated', 'sweepCapped',
    'assumptions', 'predictableProperties'} — ranked by (meets, score).
    """
    if stopPolicy not in ('first-winner', 'exhaustive'):
        raise ValueError("stopPolicy must be 'first-winner' | 'exhaustive'")
    # Only additives that can move at least one property are worth
    # sweeping; the rest would add identical no-op candidates.
    quantifiedAdditiveIds = {e['additiveId'] for e in effects
                             if e.get('effectPerWeightPercent')}
    usable = [a for a in additives if a['id'] in quantifiedAdditiveIds]
    compatibilizerId = (compatibilizers[0]['id']
                        if compatibilizers else None)

    loadings = []
    step = float(loadingStep)
    current = step
    while current <= perAdditiveCap + 1e-9:
        loadings.append(round(current, 6))
        current += step

    assumptions = [
        f'base properties manually supplied: {sorted(base_properties)}',
        f'perAdditiveCap={perAdditiveCap} wt% stands in for '
        f'maxLoadingPercent (absent from the seed rows)',
        f'linear blend model (level-0 rules of mixtures)',
    ]

    thermalGate = None
    if process is not None:
        from materialsScience.thermal_windows import (
            machinable_verdict, printable_verdict,
        )
        gateFn = (printable_verdict if process == '3d-print'
                  else machinable_verdict if process == 'cnc-machine'
                  else None)
        if gateFn is None:
            raise ValueError(
                f"unknown process '{process}' (3d-print | cnc-machine)")
        profiles = thermal_profiles or {}
        knobs = thermal_knobs or {}
        assumptions.append(
            f"thermal gate '{process}' active (no-volatiles rule, "
            f"profiles from Dustin's Base Wax Properties notes)")

        def thermalGate(combo):
            names = ([base_material_name] if base_material_name else []) \
                + [thermal_name(a) for a in combo]
            return gateFn(names, profiles, **knobs)

    evaluated = 0
    sweepCapped = False
    ranked = []
    winners = []
    done = False
    for count in range(1, maxAdditives + 1):
        if done:
            break
        for combo in itertools.combinations(usable, count):
            if done:
                break
            # The thermal window depends on WHICH materials are present,
            # not their fractions — gate once per combo.
            thermalVerdict = thermalGate(combo) if thermalGate else None
            for weights in itertools.product(loadings, repeat=count):
                if sum(weights) > maxTotalLoad + 1e-9:
                    continue
                if evaluated >= maxCandidates:
                    sweepCapped = True
                    done = True
                    break
                evaluated += 1
                components = [
                    {'materialId': additive['id'], 'weightPercent': w}
                    for additive, w in zip(combo, weights)]
                # compatibilizerRequired additives pull the
                # compatibilizer in at a fixed 2 wt% (assumption).
                needsCompat = any(a.get('compatibilizerRequired')
                                  for a in combo)
                if needsCompat:
                    if compatibilizerId is None:
                        continue   # can't form this candidate honestly
                    components.append({'materialId': compatibilizerId,
                                       'weightPercent': 2.0})
                prediction = predict_formulation_properties(
                    components, effects, base_properties)
                verdict = score_against_targets(
                    prediction['predicted'], targets)
                candidate = {
                    'components': components,
                    'predicted': prediction['predicted'],
                    'meets': verdict['meets'],
                    'score': verdict['score'],
                    'violations': list(verdict['violations']),
                    'unpredicted': verdict['unpredicted'],
                }
                if thermalVerdict is not None:
                    candidate['thermal'] = thermalVerdict
                    if not thermalVerdict['ok']:
                        candidate['meets'] = False
                        candidate['violations'].append({
                            'type': 'thermal-window',
                            'process': thermalVerdict['process'],
                            'detail': thermalVerdict.get(
                                'refusal',
                                'missing thermal profiles: '
                                + ', '.join(thermalVerdict.get(
                                    'missingProfiles', []))),
                        })
                ranked.append(candidate)
                if candidate['meets']:
                    winners.append(candidate)
                    if stopPolicy == 'first-winner' \
                            and not continueAfterWinner:
                        done = True
                        break

    ranked.sort(key=lambda c: (not c['meets'], -c['score']))
    return {
        'ranked': ranked[:50],
        'winners': winners,
        'evaluated': evaluated,
        'sweepCapped': sweepCapped,
        'assumptions': assumptions,
        'predictableProperties': predictable_properties(effects),
    }


def search_for_profile(profileId, base_properties, seedData=None,
                       **knobs):
    """Convenience: run search_composites against a seeded
    TargetMaterialProfile (e.g. 'profile-min-viable-wax-filament')."""
    data = seedData or load_legacy_seed_data()
    targetRows = [t for t in data['targets']
                  if t['profileId'] == profileId]
    if not targetRows:
        known = sorted({t['profileId'] for t in data['targets']})
        return {'ok': False,
                'error': f"no PropertyTargets for profile '{profileId}'",
                'knownProfiles': known}
    result = search_composites(
        base_properties, normalize_targets(targetRows),
        data['additives'], data['effects'], data['compatibilizers'],
        **knobs)
    result['ok'] = True
    result['profileId'] = profileId
    return result
