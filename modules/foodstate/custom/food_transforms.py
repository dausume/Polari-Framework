"""
@module foodstate.custom.food_transforms

fsp-2 / mpa-0 — the transform engine v1 (MEAL_PLANNING_APP_PLAN.md):
derive a NEW FoodState from a stated transform, writing UNDERLYING
QUANTITIES as claims — never headline labels. The honesty ladder as
implemented rungs:

  rung 2  MASS BALANCE — exact bookkeeping given a STATED mass yield
          (yield_percent per 100 g in, or water_loss_fraction). All
          mass change is attributed to water (assumption A7, named on
          every claim); the vendored subset carries NO water rows, so
          the loss-exceeds-water check is SKIPPED AND NAMED (gap).
  rung 4  RETENTION FACTORS — the nmp-3 R6 engine applied per
          cooking-method code (cited bulk fallback, micronutrients).
  rung 3  cited mechanistic models (gelatinization, denaturation,
          cell integrity) — REGISTERED-UNIMPLEMENTED (I5): every
          transform lists them as refusals until a cited calibration
          is loaded. No invented kinetics.

Everything here is PURE COMPUTE over manager tables and returns seed
rows (MaterialState / MaterialProcessExecution / PropertyClaim on
pspp's own classes — zero schema changes); `apply_transform`
persists via moduleService.seed_upsert (derive-on-demand + cached, D5
— never a boot-seeded state explosion).

@consumers
  - foodstate.food_api (fsp-2 endpoints), nutrition meal-state seam
  - foodstate.food_transforms_selftest
@see AI-Notes/plans/MEAL_PLANNING_APP_PLAN.md §mpa-0
"""

import json

from nutrition.custom.recipe_analysis import (
    R6_CODE_BY_NUTRIENT, retention_description, retention_rows,
)

_PROV = 'fsp-2 transform engine v1 (MEAL_PLANNING_APP_PLAN.md mpa-0)'

#: nmp IngredientLine.method → food process vocabulary row. Grill and
#: sauté ride existing dry-heat rows with the mapping named — adding
#: a dedicated row is a data change, not a code change.
METHOD_PROCESS = {
    'boiled': 'food-boil',
    'steamed': 'food-steam',
    'fried': 'food-fry',
    'sauteed': 'food-fry',
    'grilled': 'food-bake',
    'baked': 'food-bake',
    'simmered': 'food-simmer',
    'roasted': 'food-bake',
}

#: Structure-model quantities every heating transform WOULD change —
#: registered-unimplemented (I5): refused by name until a cited
#: calibration is loaded (fsp-2 rung 3).
MODEL_RUNG_QUANTITIES = (
    'starch-gelatinization-fraction',
    'protein-denaturation-fraction',
    'cell-integrity',
)

_HEATING_TYPES = ('heating',)


def _rows(manager, table):
    return list((getattr(manager, 'objectTables', {}) or {})
                .get(table, {}).values())


def _g(row, attr, default=''):
    return getattr(row, attr, default)


def process_definition(manager, process_name):
    for row in _rows(manager, 'MaterialProcessDefinition'):
        if _g(row, 'name') == process_name:
            return row
    return None


def subject_composition(manager, subject_state_key):
    """{quantity: {'value','units','claim'}} from PropertyClaim rows
    on one subject."""
    out = {}
    for c in _rows(manager, 'PropertyClaim'):
        if _g(c, 'subject_state_key') != subject_state_key:
            continue
        out[_g(c, 'property_meaning_name')] = {
            'value': float(getattr(c, 'value', 0.0) or 0.0),
            'units': _g(c, 'units'),
            'evidence_method': _g(c, 'evidence_method'),
        }
    return out


def _state_seed(material_name, state_name, parent_key, stage,
                execution_name, note=''):
    return {
        'name': f'{material_name}#{state_name}',
        'material_name': material_name,
        'state_name': state_name,
        'is_canonical': False,
        'processing_stage': stage,
        'thermodynamic_phase': '',
        'composition_snapshot_json': '{}',
        'environmental_snapshot_json': '{}',
        'parent_state_ids_json': json.dumps([parent_key]),
        'producing_execution_id': execution_name,
        'validation_status': 'unvalidated',
        'provenance_id': _PROV,
        'notes': note,
    }


def _claim_seed(subject, quantity, value, units, evidence,
                assumptions, execution_name, confidence=''):
    return {
        'name': f'{subject}:{quantity}@L0',
        'subject_state_key': subject,
        'property_meaning_name': quantity,
        'scale_level': 0,
        'value': round(value, 6),
        'value_json': '',
        'units': units,
        'evidence_method': evidence,
        'assumptions_json': json.dumps(assumptions),
        'validity_json': json.dumps(
            {'basis': 'per-100g', 'state': subject.split('#', 1)[-1]}),
        'source_execution_id': execution_name,
        'confidence_json': confidence,
        'provenance_id': _PROV,
        'notes': '',
    }


def derive_transform(manager, process_name, subject_state_key,
                     params=None):
    """One transform edge: input state + stated parameters → output
    state seed + execution seed + derived claims + NAMED refusals.

    params:
      yield_percent        mass out per 100 g in (R6 cooking-yields
                           convention; >100 = water uptake). One of
                           yield_percent / water_loss_fraction is
                           REQUIRED for heating transforms — the
                           engine never invents kinetics (I5).
      water_loss_fraction  alternative statement of the same thing.
      retention_code       R6 code → rung-4 micronutrient retention.
      output_state_name    default '<parent-state>--<process>'.
      target_particle_size_m   chop only → structure claim (stated).
    """
    params = dict(params or {})
    definition = process_definition(manager, process_name)
    if definition is None:
        return {'ok': False,
                'error': f'no MaterialProcessDefinition named '
                         f'"{process_name}" — the food vocabulary is '
                         f'rows, add one there (fsp-0)'}
    if _g(definition, 'material_family') != 'food':
        return {'ok': False,
                'error': f'"{process_name}" is not a food-family '
                         f'process — this engine only runs the food '
                         f'vocabulary'}
    if _g(definition, 'execution_effect') == 'OBSERVATIONAL':
        return {'ok': False,
                'error': f'"{process_name}" is OBSERVATIONAL — a '
                         f'measurement attaches a MEASURED claim to '
                         f'the existing state (CRUDE PropertyClaim), '
                         f'it never derives one; this engine only '
                         f'runs TRANSFORMATIVE edges (I2)'}
    if '#' not in subject_state_key:
        return {'ok': False,
                'error': f'subject "{subject_state_key}" is not a '
                         f'"<material>#<state>" key'}
    composition = subject_composition(manager, subject_state_key)
    if not composition:
        return {'ok': False,
                'error': f'no claims on "{subject_state_key}" — '
                         f'fsp-1 coverage is the only honest input; '
                         f'vendor data for this material first'}

    material_name, parent_state = subject_state_key.split('#', 1)
    ptype = _g(definition, 'process_type')
    out_schema = {}
    try:
        out_schema = json.loads(
            _g(definition, 'output_state_schema_json', '{}') or '{}')
    except ValueError:
        pass
    stage = out_schema.get('stage', '')

    # ── the stated mass balance ─────────────────────────────
    yield_pct = params.get('yield_percent')
    wlf = params.get('water_loss_fraction')
    if yield_pct is None and wlf is not None:
        yield_pct = 100.0 * (1.0 - float(wlf))
    identity_pass = ptype in ('preparation',) and process_name in (
        'food-chop', 'food-wash')
    if yield_pct is None:
        if identity_pass:
            yield_pct = 100.0
        else:
            return {'ok': False,
                    'error': f'"{process_name}" needs a STATED mass '
                             f'yield (yield_percent or '
                             f'water_loss_fraction) — rung 2 is exact '
                             f'bookkeeping over stated inputs; the '
                             f'engine refuses to invent evaporation '
                             f'kinetics (I5). The R6 cooking-yields '
                             f'table is the cited source for typical '
                             f'values.'}
    yield_pct = float(yield_pct)
    if yield_pct <= 0:
        return {'ok': False,
                'error': f'yield_percent {yield_pct:g} is not a '
                         f'physical mass yield'}

    retention_code = str(params.get('retention_code', '') or '')
    ret = retention_rows(retention_code) if retention_code else {}
    ret_desc = (retention_description(retention_code)
                if retention_code else '')

    execution_name = params.get('execution_name') or (
        f'{subject_state_key}->{process_name}')
    out_state_name = params.get('output_state_name') or (
        f'{parent_state}--{process_name.replace("food-", "")}')
    out_subject = f'{material_name}#{out_state_name}'

    water_delta = yield_pct - 100.0  # +gain / -loss, g per 100 g in
    base_assumptions = [
        f'derived by {process_name} from {subject_state_key}',
        f'stated mass yield {yield_pct:g} g per 100 g input; all '
        f'mass change attributed to WATER (assumption A7)',
        'input water content itself is a vendor gap — the '
        'loss-exceeds-water sanity check is SKIPPED, named here',
    ]

    claims, refusals = [], []
    for quantity, entry in sorted(composition.items()):
        raw = entry['value']
        r6code = R6_CODE_BY_NUTRIENT.get(quantity)
        retained = raw
        evidence = 'mass-balance'
        assumptions = list(base_assumptions)
        if retention_code and r6code and r6code in ret:
            retained = raw * ret[r6code] / 100.0
            evidence = 'retention-factor'
            assumptions.append(
                f'R6 {retention_code} ({ret_desc}) retention '
                f'{ret[r6code]:g}% applied, then concentration')
        elif retention_code and quantity not in (
                'calories', 'protein', 'carbohydrate', 'healthy-fat'):
            assumptions.append(
                f'no R6 row for {quantity} under {retention_code} — '
                f'amount conserved (raw value), labeled')
        new_per100 = retained / yield_pct * 100.0
        assumptions.append(
            f'per-100g rebased: {retained:g} g-basis amount / '
            f'{yield_pct:g} g output × 100')
        claims.append(_claim_seed(
            out_subject, quantity, new_per100, entry['units'],
            evidence, assumptions, execution_name))

    if identity_pass:
        size = params.get('target_particle_size_m')
        if size is not None:
            claims.append(_claim_seed(
                out_subject, 'particle-size', float(size), 'm',
                'estimated',
                ['stated preparation target, not a measurement'],
                execution_name))
    if ptype in _HEATING_TYPES:
        for q in MODEL_RUNG_QUANTITIES:
            refusals.append({
                'quantity': q,
                'why': 'cited mechanistic model registered but NOT '
                       'implemented (I5) — no calibration loaded; '
                       'loading one is the only way this claim '
                       'appears (fsp-2 rung 3)'})

    execution = {
        'name': execution_name,
        'definition_name': process_name,
        'input_state_ids_json': json.dumps([subject_state_key]),
        'parameter_values_json': json.dumps(
            {k: v for k, v in params.items()
             if k not in ('execution_name',)}),
        'schedule_json': '[]',
        'device_id': '',
        'output_state_ids_json': json.dumps([out_subject]),
        'measured_observations_json': '{}',
        'status': 'executed',
        'provenance_id': _PROV,
        'notes': '',
    }
    state = _state_seed(material_name, out_state_name,
                        subject_state_key, stage, execution_name)
    return {
        'ok': True, 'schema': 'food-transform/1',
        'process': process_name,
        'inputState': subject_state_key,
        'outputState': state,
        'execution': execution,
        'claims': claims,
        'refusals': refusals,
        'massBalance': {'inputG': 100.0, 'outputG': yield_pct,
                        'waterDeltaG': round(water_delta, 3),
                        'basis': 'per 100 g input'},
        'honesty': 'underlying quantities only — measured > '
                   'mass-balance > cited model (refused, named) > '
                   'retention factor; cooking never writes headline '
                   'labels',
    }


def derive_mix(manager, inputs, output_material,
               output_state_name='mixed', execution_name=''):
    """Mass-weighted combination of input subjects → one mixed state.

    inputs: [{'subject': '<material>#<state>', 'grams': float}] —
    grams are the ACTUAL masses entering the mix (post-yield)."""
    if not inputs:
        return {'ok': False, 'error': 'no inputs to mix'}
    total = sum(float(i.get('grams', 0.0) or 0.0) for i in inputs)
    if total <= 0:
        return {'ok': False, 'error': 'mix has zero total mass'}
    execution_name = execution_name or (
        f'{output_material}#{output_state_name}<-food-mix')
    out_subject = f'{output_material}#{output_state_name}'
    weighted, units, missing = {}, {}, []
    for item in inputs:
        subject = item.get('subject', '')
        grams = float(item.get('grams', 0.0) or 0.0)
        comp = subject_composition(manager, subject)
        if not comp:
            missing.append(subject)
            continue
        for quantity, entry in comp.items():
            weighted[quantity] = (weighted.get(quantity, 0.0)
                                  + entry['value'] * grams / 100.0)
            units[quantity] = entry['units']
    if not weighted:
        return {'ok': False,
                'error': f'no claims on any mix input ({missing})'}
    assumptions = [
        'mass-weighted mean of input claims (food-mix, exact '
        'bookkeeping)',
        f'inputs: ' + ', '.join(
            f"{i.get('subject')}×{float(i.get('grams', 0) or 0):g}g"
            for i in inputs),
    ]
    if missing:
        assumptions.append(
            f'inputs WITHOUT claims contributed mass only (named): '
            f'{missing}')
    claims = [
        _claim_seed(out_subject, quantity,
                    amount / total * 100.0, units[quantity],
                    'mass-balance', assumptions, execution_name)
        for quantity, amount in sorted(weighted.items())]
    execution = {
        'name': execution_name,
        'definition_name': 'food-mix',
        'input_state_ids_json': json.dumps(
            [i.get('subject', '') for i in inputs]),
        'parameter_values_json': json.dumps(
            {'grams': {i.get('subject', ''):
                       float(i.get('grams', 0.0) or 0.0)
                       for i in inputs}}),
        'schedule_json': '[]', 'device_id': '',
        'output_state_ids_json': json.dumps([out_subject]),
        'measured_observations_json': '{}',
        'status': 'executed', 'provenance_id': _PROV, 'notes': '',
    }
    state = {
        'name': out_subject,
        'material_name': output_material,
        'state_name': output_state_name,
        'is_canonical': False,
        'processing_stage': 'mixed',
        'thermodynamic_phase': '',
        'composition_snapshot_json': '{}',
        'environmental_snapshot_json': '{}',
        'parent_state_ids_json': json.dumps(
            [i.get('subject', '') for i in inputs]),
        'producing_execution_id': execution_name,
        'validation_status': 'unvalidated',
        'provenance_id': _PROV,
        'notes': '',
    }
    return {'ok': True, 'schema': 'food-transform/1',
            'process': 'food-mix',
            'outputState': state, 'execution': execution,
            'claims': claims, 'refusals': [],
            'totalMassG': round(total, 1),
            'missingInputs': missing}


def template_state_chain(manager, template_name):
    """fsp-6 seam: one MealTemplate's process graph → per-line
    transform edges + the terminal prepared-food state, claims
    per-100g — PSPP establishing the meal's foundational properties.

    The per-meal amounts here MUST agree with the nmp-4 rollup (a
    two-modules-agree guard rides the selftest)."""
    template = None
    for row in _rows(manager, 'MealTemplate'):
        if _g(row, 'name') == template_name:
            template = row
            break
    if template is None:
        return {'ok': False,
                'error': f'no MealTemplate "{template_name}"'}
    try:
        recipes = json.loads(
            _g(template, 'recipe_names_json', '[]') or '[]')
    except ValueError:
        recipes = []
    lines = [l for l in _rows(manager, 'IngredientLine')
             if _g(l, 'recipe_name') in recipes]
    if not lines:
        return {'ok': False,
                'error': f'template "{template_name}" resolves no '
                         f'ingredient lines'}
    servings_by_recipe = {
        _g(r, 'name'): max(1.0, float(getattr(r, 'servings', 1.0)
                                      or 1.0))
        for r in _rows(manager, 'Recipe')}
    edges, mix_inputs, notes = [], [], []
    for line in sorted(lines, key=lambda l: (_g(l, 'recipe_name'),
                                             getattr(l, 'order', 0))):
        food = _g(line, 'food_name')
        grams = float(getattr(line, 'grams', 0.0) or 0.0)
        method = _g(line, 'method', 'raw') or 'raw'
        servings = servings_by_recipe.get(_g(line, 'recipe_name'),
                                          1.0)
        grams_per_meal = grams / servings
        subject = f'{food}#as-defined'
        if method == 'raw':
            mix_inputs.append({'subject': subject,
                               'grams': grams_per_meal})
            continue
        process = METHOD_PROCESS.get(method)
        if process is None:
            notes.append(f'{food}: method "{method}" has no process '
                         f'mapping — line kept raw, NAMED gap')
            mix_inputs.append({'subject': subject,
                               'grams': grams_per_meal})
            continue
        derived = derive_transform(manager, process, subject, {
            'yield_percent': float(
                getattr(line, 'yield_percent', 100.0) or 100.0),
            'retention_code': _g(line, 'retention_code'),
            'output_state_name': f'as-defined--{method}',
        })
        if not derived.get('ok'):
            notes.append(f'{food}: {derived.get("error")}')
            mix_inputs.append({'subject': subject,
                               'grams': grams_per_meal})
            continue
        edges.append(derived)
        cooked = grams_per_meal * float(
            getattr(line, 'yield_percent', 100.0) or 100.0) / 100.0
        mix_inputs.append(
            {'subject': derived['outputState']['name'],
             'grams': cooked,
             '_claims': derived['claims']})
    # the mix needs the derived claims visible — run it over an
    # overlay manager that carries the edge claims as rows.
    overlay_claims = {}
    base = (getattr(manager, 'objectTables', {}) or {}).get(
        'PropertyClaim', {})
    overlay_claims.update(base)
    next_id = len(overlay_claims) + 100000
    from types import SimpleNamespace
    for edge in edges:
        for c in edge['claims']:
            overlay_claims[next_id] = SimpleNamespace(**c)
            next_id += 1
    overlay = SimpleNamespace(objectTables={
        **(getattr(manager, 'objectTables', {}) or {}),
        'PropertyClaim': overlay_claims})
    mix = derive_mix(
        overlay,
        [{'subject': i['subject'], 'grams': i['grams']}
         for i in mix_inputs],
        output_material=template_name,
        output_state_name='prepared-food',
        execution_name=f'{template_name}#prepared-food<-chain')
    if not mix.get('ok'):
        return {'ok': False, 'error': f'mix failed: {mix["error"]}',
                'edges': len(edges), 'notes': notes}
    total_mass = mix['totalMassG']
    per_meal = {
        c['property_meaning_name']:
            round(c['value'] * total_mass / 100.0, 3)
        for c in mix['claims']}
    refusals = [r for e in edges for r in e['refusals']]
    return {
        'ok': True, 'schema': 'food-meal-chain/1',
        'template': template_name,
        'terminalState': mix['outputState'],
        'terminalClaims': mix['claims'],
        'edges': [{'process': e['process'],
                   'input': e['inputState'],
                   'output': e['outputState']['name'],
                   'massBalance': e['massBalance']} for e in edges],
        'mealMassG': total_mass,
        'perMealAmounts': per_meal,
        'modelRungRefusals': refusals,
        'notes': notes,
        'honesty': 'terminal claims are per-100g mass-balance + '
                   'retention arithmetic over FDC-cited raw claims; '
                   'structure-model quantities are refused by name '
                   'until cited calibrations load (I5)',
    }


def apply_transform(manager, derived):
    """Persist one derive_transform / derive_mix result through the
    proven upsert path (derive-on-demand + cached, D5)."""
    if not derived.get('ok'):
        return {'ok': False, 'error': 'refusing to persist a '
                                      'non-ok derivation'}
    try:
        from moduleService.seed_upsert import upsert_seed_pairs
        from pspp.material_states_basis import MaterialState
        from pspp.material_processes_basis import MaterialProcessExecution
        from pspp.claims_basis import PropertyClaim
    except ImportError as exc:
        return {'ok': False, 'persisted': False,
                'error': f'persistence path unavailable ({exc}) — '
                         f'derivation stays pure-compute'}
    pairs = [
        ('MaterialState', MaterialState, [derived['outputState']]),
        ('MaterialProcessExecution', MaterialProcessExecution,
         [derived['execution']]),
        ('PropertyClaim', PropertyClaim, derived['claims']),
    ]
    reports = upsert_seed_pairs(manager, pairs, tag='FoodTransform')
    return {'ok': True, 'persisted': True, 'reports': reports}
