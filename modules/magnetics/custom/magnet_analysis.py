"""
@module magnetics.custom.magnet_analysis

Duck-typed analysis over the Section-A rows: realization-ladder gates,
derived role viability (predicates vs property values — never
hand-stamped), the ONE vol%<->wt% conversion (densities as data,
refusing when missing), the quick analytic composite predictors
(Maxwell-Garnett / Bruggeman — the VALIDATED msci
fem.effective-permeability engine is the L1 confirmation run, not
forked here), and the laddered "best option for role R" answer.

Stdlib only; takes any manager exposing .objectTables.
"""

import json

#: Matrix priors for the composite predictor — densities are DATA
#: with est flags, mu_r=1 (all four matrices are non-magnetic).
#: item_ref ties each matrix to the supplychain cost vocabulary.
MATRIX_PRIORS = {
    'geopolymer': {'density_kg_m3': 2000.0, 'mu_r': 1.0,
                   'is_estimate': True, 'item_ref': 'geopolymer-mix'},
    'sol-gel': {'density_kg_m3': 2000.0, 'mu_r': 1.0,
                'is_estimate': True, 'item_ref': 'silica-xerogel'},
    'ceramic': {'density_kg_m3': 2500.0, 'mu_r': 1.0,
                'is_estimate': True, 'item_ref': ''},
    'wax': {'density_kg_m3': 930.0, 'mu_r': 1.0,
            'is_estimate': True,
            'item_ref': 'natural-print-wax-blend'},
}

_OPS = {
    '>=': lambda a, b: a >= b, '<=': lambda a, b: a <= b,
    '>': lambda a, b: a > b, '<': lambda a, b: a < b,
    '==': lambda a, b: a == b,
}


def _rows(manager, class_name):
    return list(getattr(manager, 'objectTables', {}).get(
        class_name, {}).values())


def _named(manager, class_name, name):
    for row in _rows(manager, class_name):
        if getattr(row, 'name', None) == name:
            return row
    return None


def _loads(row, attr, default):
    try:
        return json.loads(getattr(row, attr, '') or '')
    except ValueError:
        return default


# ---------------------------------------------------------------- #
# Realization ladder gates
# ---------------------------------------------------------------- #

def buyable_cited(manager, item_ref):
    """True when ANY PriceCitation names the item — the orthogonal
    flag of the ladder, derived live, never stored."""
    if not item_ref:
        return False
    return any(getattr(c, 'item_ref', '') == item_ref
               for c in _rows(manager, 'PriceCitation'))


def recipe_seeded(manager, item_ref):
    if not item_ref:
        return False
    return any(getattr(f, 'product_item_ref', '') == item_ref
               for f in _rows(manager, 'ProductFormula'))


def gates_for(manager, option):
    """The three use-gates for one catalog option. Simulation is open
    at EVERY level — the watermark travels on every result."""
    level = getattr(option, 'realization_level', 'theoretical')
    item = getattr(option, 'item_ref', '')
    cited = buyable_cited(manager, item)
    recipe = recipe_seeded(manager, item)
    costable = cited or recipe
    made = level == 'made-and-measured'
    out = {
        'realizationLevel': level,
        'buyableCited': cited,
        'recipeSeeded': recipe,
        'simulation': {
            'allowed': True,
            'watermark': f'realization={level}'
                         + ('' if made else
                            ' — simulated properties, not ours yet')},
        'costing': {'allowed': costable},
        'business': {'allowed': made},
    }
    if not costable:
        out['costing']['refusal'] = (
            f'"{getattr(option, "name", "?")}" has neither a cited '
            'price nor a seeded recipe — costing would be a guess')
        out['costing']['suggestion'] = {
            'evidence': 'cost gate = cited-or-recipe',
            'knob': 'PriceCitation / ProductFormula',
            'action': f'cite or seed a recipe for "{item}"'
                      if item else
                      'give the option an item_ref, then cite it'}
    if not made:
        out['business']['refusal'] = (
            'business/planner use needs made-and-measured — '
            'readiness for materials is EARNED (XRD/hall/inductance '
            'rows), exactly like product readiness')
    return out


# ---------------------------------------------------------------- #
# Derived role viability (mag-2r)
# ---------------------------------------------------------------- #

def _prop_value(option, prop):
    props = _loads(option, 'properties_json', {})
    entry = props.get(prop)
    if isinstance(entry, dict):
        return entry.get('value'), entry.get('provenance', '')
    return None, ''


def _check_clause(option, clauses):
    """(verdict, deciding, missing) over an 'all' clause list."""
    deciding, missing = [], []
    verdict = 'viable'
    for c in clauses:
        val, prov = _prop_value(option, c.get('prop', ''))
        if val is None:
            missing.append(c.get('prop', ''))
            continue
        ok = _OPS.get(c.get('op', '>='), _OPS['>='])(
            float(val), float(c.get('value', 0)))
        deciding.append({'prop': c.get('prop'), 'value': val,
                         'provenance': prov, 'op': c.get('op'),
                         'threshold': c.get('value'), 'holds': ok})
        if not ok:
            verdict = 'unviable'
    if missing and verdict != 'unviable':
        verdict = 'unassessed'
    return verdict, deciding, missing


def role_viability(manager, option, role):
    """viable | unviable | unassessed for one (option, role) pair,
    DERIVED from property rows vs the role's predicate knobs.
    Missing data = unassessed + the measurement ask. Overrides are
    honored only WITH their reason, and are labeled as overrides."""
    role_name = getattr(role, 'name', '')
    overrides = _loads(option, 'role_overrides_json', {})
    if role_name in overrides:
        ov = overrides[role_name]
        if ov.get('reason'):
            return {'ok': True, 'role': role_name,
                    'verdict': ov.get('verdict', 'unviable'),
                    'via': 'override', 'reason': ov['reason'],
                    'honestyNote': getattr(role, 'honesty_note', '')}
        # a reasonless override is ignored — silence is not evidence
    predicates = _loads(role, 'predicates_json', {})
    forms = set(_loads(option, 'forms_json', []))
    role_forms = set(_loads(role, 'applicable_forms_json', []))
    form_overlap = sorted(forms & role_forms) if role_forms else \
        sorted(forms)
    if role_forms and not form_overlap:
        return {'ok': True, 'role': role_name, 'verdict': 'unviable',
                'via': 'form', 'reason':
                    f'no form overlap (option: {sorted(forms)}, '
                    f'role wants: {sorted(role_forms)})',
                'honestyNote': getattr(role, 'honesty_note', '')}
    if 'any' in predicates:
        best = None
        for mech in predicates['any']:
            verdict, deciding, missing = _check_clause(
                option, mech.get('all', []))
            cand = {'verdict': verdict, 'deciding': deciding,
                    'missing': missing,
                    'mechanism': mech.get('mechanism', '')}
            order = {'viable': 0, 'unassessed': 1, 'unviable': 2}
            if best is None or order[verdict] < order[best['verdict']]:
                best = cand
        result = best or {'verdict': 'unassessed', 'deciding': [],
                          'missing': [], 'mechanism': ''}
    else:
        verdict, deciding, missing = _check_clause(
            option, predicates.get('all', []))
        result = {'verdict': verdict, 'deciding': deciding,
                  'missing': missing, 'mechanism': ''}
    out = {'ok': True, 'role': role_name, 'via': 'derived',
           'forms': form_overlap,
           'honestyNote': getattr(role, 'honesty_note', ''),
           **result}
    if result['verdict'] == 'unassessed':
        out['suggestion'] = {
            'evidence': 'missing property data — never assumed '
                        'viable',
            'knob': 'MagneticMaterialOption.properties_json',
            'action': 'measure or cite: '
                      + ', '.join(result['missing'])}
    return out


def viability_matrix(manager, role_name='', form=''):
    """All (option, role) verdicts, optionally filtered; the casual
    search backend (mag-2r): role+form -> viable list with the
    deciding numbers shown."""
    roles = _rows(manager, 'MaterialUseRole')
    if role_name:
        roles = [r for r in roles
                 if getattr(r, 'name', '') == role_name]
        if not roles:
            return {'ok': False,
                    'refusal': f'no MaterialUseRole named '
                               f'"{role_name}"'}
    rows = []
    for opt in _rows(manager, 'MagneticMaterialOption'):
        if form and form not in _loads(opt, 'forms_json', []):
            continue
        for role in roles:
            v = role_viability(manager, opt, role)
            if form and v.get('via') == 'derived' \
                    and form not in v.get('forms', []):
                continue
            gates = gates_for(manager, opt)
            rows.append({
                'option': getattr(opt, 'name', ''),
                'displayName': getattr(opt, 'display_name', ''),
                'family': getattr(opt, 'family', ''),
                'realizationLevel': gates['realizationLevel'],
                'buyableCited': gates['buyableCited'],
                'referenceOnly': getattr(opt, 'is_reference_only',
                                         False),
                **{k: v[k] for k in ('role', 'verdict', 'via',
                                     'mechanism', 'honestyNote')
                   if k in v},
                'deciding': v.get('deciding', []),
                'missing': v.get('missing', []),
            })
    order = {'viable': 0, 'unassessed': 1, 'unviable': 2}
    rows.sort(key=lambda r: (r['role'],
                             order.get(r['verdict'], 3),
                             r['option']))
    return {'ok': True, 'role': role_name, 'form': form,
            'rows': rows,
            'counts': {k: sum(1 for r in rows if r['verdict'] == k)
                       for k in ('viable', 'unassessed', 'unviable')}}


# ---------------------------------------------------------------- #
# vol% <-> wt% — THE one conversion (mag-1 note)
# ---------------------------------------------------------------- #

def wt_from_vol(vol_fraction, filler_density, matrix_density):
    """Mass fraction of filler from volume fraction. Refuses (None)
    without both densities — never guesses."""
    if not filler_density or not matrix_density:
        return None
    fm = vol_fraction * filler_density
    mm = (1.0 - vol_fraction) * matrix_density
    return round(fm / (fm + mm), 4)


def vol_from_wt(wt_fraction, filler_density, matrix_density):
    if not filler_density or not matrix_density:
        return None
    fv = wt_fraction / filler_density
    mv = (1.0 - wt_fraction) / matrix_density
    return round(fv / (fv + mv), 4)


# ---------------------------------------------------------------- #
# Composite predictors (mag-2t) — quick analytic estimates; the
# validated msci FEM engine is the confirmation run (object
# coherence: referenced by registry name, physics not forked).
# ---------------------------------------------------------------- #

FEM_CONFIRMATION_REF = 'fem-effective-permeability'


def maxwell_garnett(mu_matrix, mu_inclusion, vol_fraction):
    """Dilute-limit effective mu (spherical inclusions)."""
    num = 2 * (mu_inclusion - mu_matrix) * vol_fraction
    den = (mu_inclusion + 2 * mu_matrix
           - (mu_inclusion - mu_matrix) * vol_fraction)
    return round(mu_matrix * (1 + num / den), 4)


def bruggeman(mu_matrix, mu_inclusion, vol_fraction, tol=1e-9):
    """Symmetric effective-medium mu via bisection on the Bruggeman
    condition — better past the dilute limit."""
    def f(mu_e):
        return (vol_fraction * (mu_inclusion - mu_e)
                / (mu_inclusion + 2 * mu_e)
                + (1 - vol_fraction) * (mu_matrix - mu_e)
                / (mu_matrix + 2 * mu_e))
    lo, hi = min(mu_matrix, mu_inclusion), max(mu_matrix,
                                               mu_inclusion)
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if f(lo) * f(mid) <= 0:
            hi = mid
        else:
            lo = mid
        if hi - lo < tol:
            break
    return round(0.5 * (lo + hi), 4)


def composite_predict(manager, powder_name, matrix_name,
                      vol_fraction):
    """powder row + matrix choice + vol% -> predicted mu_eff (both
    estimators), density, wt%, and $/kg-if-real (cost gate honored:
    theoretical powders refuse costing, naming the hunt)."""
    powder = _named(manager, 'MagneticPowderDefinition', powder_name)
    if powder is None:
        return {'ok': False,
                'refusal': f'no MagneticPowderDefinition named '
                           f'"{powder_name}"'}
    matrix = MATRIX_PRIORS.get(matrix_name)
    if matrix is None:
        return {'ok': False,
                'refusal': f'unknown matrix "{matrix_name}" — one '
                           f'of {sorted(MATRIX_PRIORS)}'}
    if not (0.0 < vol_fraction < 1.0):
        return {'ok': False,
                'refusal': 'vol_fraction must be in (0, 1)'}
    mu_i = getattr(powder, 'mu_i', None)
    rho_p = getattr(powder, 'density_kg_m3', None)
    if mu_i is None or rho_p is None:
        return {'ok': False,
                'refusal': f'"{powder_name}" is missing '
                           f'{"mu_i" if mu_i is None else ""}'
                           f'{"density" if rho_p is None else ""} — '
                           'predict would be a guess',
                'suggestion': {
                    'evidence': 'unknown = None + ask, never a guess',
                    'knob': 'MagneticPowderDefinition',
                    'action': 'fill mu_i/density from literature '
                              '(est-tagged) or measurement'}}
    mu_m = matrix['mu_r']
    mg = maxwell_garnett(mu_m, float(mu_i), vol_fraction)
    br = bruggeman(mu_m, float(mu_i), vol_fraction)
    wt = wt_from_vol(vol_fraction, float(rho_p),
                     matrix['density_kg_m3'])
    density = round(vol_fraction * float(rho_p)
                    + (1 - vol_fraction) * matrix['density_kg_m3'], 1)
    theoretical = bool(getattr(powder, 'is_theoretical', False))
    out = {
        'ok': True, 'powder': powder_name, 'matrix': matrix_name,
        'volFraction': vol_fraction, 'wtFraction': wt,
        'predictedMuEff': {'maxwellGarnett': mg, 'bruggeman': br},
        'compositeDensityKgM3': density,
        'watermark': ('THEORETICAL powder — simulation-only '
                      'hypothesis' if theoretical else
                      f'powder provenance: '
                      f'{getattr(powder, "property_provenance", "")}'),
        'confirmationRun': {
            'engine': FEM_CONFIRMATION_REF,
            'note': 'analytic estimate — the validated msci FEM '
                    'homogenization is the L1 confirmation run'},
        'validity': 'linear magnetostatics only; hysteresis/'
                    'remanence out of scope; percolation of '
                    'CONDUCTIVE fillers is the msci-23 engine\'s '
                    'axis',
    }
    if matrix['is_estimate']:
        out['matrixDensityEstimate'] = True
    # cost-if-real, through the supplychain cascade
    if theoretical:
        out['costing'] = {
            'allowed': False,
            'refusal': 'theoretical powder — no citation can exist',
            'suggestion': {
                'evidence': 'the design output IS the sourcing ask',
                'knob': 'PriceCitation',
                'action': 'find/cite a real powder in this property '
                          'box (SrFe12O19, NiZn, MnZn are the real '
                          'boxes to check first)'}}
        return out
    item = getattr(powder, 'item_ref', '')
    try:
        from supplychain.custom.formula_analysis import effective_unit_price
        filler = effective_unit_price(manager, item) if item else None
        m_item = matrix.get('item_ref', '')
        matrix_price = (effective_unit_price(manager, m_item)
                        if m_item else None)
    except ImportError:
        filler = matrix_price = None
    if filler is None or matrix_price is None or wt is None:
        missing = item if filler is None else \
            matrix.get('item_ref', '(matrix has no item_ref)')
        out['costing'] = {
            'allowed': False,
            'refusal': f'no cited-or-makeable price for "{missing}"'}
        return out
    usd = round(wt * filler['normalized']
                + (1 - wt) * matrix_price['normalized'], 4)
    out['costing'] = {
        'allowed': True, 'usdPerKg': usd,
        'filler': {'item': item, 'via': filler['via'],
                   'usdPerKg': filler['normalized']},
        'matrix': {'item': matrix.get('item_ref', ''),
                   'via': matrix_price['via'],
                   'usdPerKg': matrix_price['normalized']},
        'anyEstimate': bool(filler.get('isEstimate')
                            or matrix_price.get('isEstimate')
                            or matrix['is_estimate'])}
    return out


# ---------------------------------------------------------------- #
# Laddered answers (mag-2t): best option per realization level
# ---------------------------------------------------------------- #

#: Figure of merit per role: (property, higher_is_better).
ROLE_MERIT = {
    'torque-magnet': ('b_r_t', True),
    'magnetic-bearing': ('b_r_t', True),
    'magnetic-conductor': ('mu_r_eff', True),
    'electric-conductor-power': ('sigma_s_m', True),
    'electric-conductor-signal': ('sigma_s_m', True),
    'in-matrix-sensing': ('sigma_s_m', True),
}


def laddered_answer(manager, role_name, form=''):
    """Best VIABLE option per realization level for a role — the
    short-term build and long-term research target in ONE report,
    each row watermarked with its level."""
    matrix = viability_matrix(manager, role_name, form)
    if not matrix.get('ok'):
        return matrix
    merit_prop, _higher = ROLE_MERIT.get(role_name,
                                         ('mu_r_eff', True))
    ladder = {}
    for row in matrix['rows']:
        if row['verdict'] != 'viable':
            continue
        opt = _named(manager, 'MagneticMaterialOption', row['option'])
        val, _prov = _prop_value(opt, merit_prop)
        level = row['realizationLevel']
        current = ladder.get(level)
        if val is not None and (current is None
                                or val > current['merit']):
            ladder[level] = {'option': row['option'],
                             'displayName': row['displayName'],
                             'merit': val,
                             'meritProp': merit_prop,
                             'buyableCited': row['buyableCited'],
                             'referenceOnly': row['referenceOnly'],
                             'watermark': f'realization={level}'}
    from magnetics.magnet_basis import REALIZATION_LEVELS
    return {'ok': True, 'role': role_name, 'form': form,
            'meritProperty': merit_prop,
            'ladder': [{'level': lv, **ladder[lv]}
                       for lv in reversed(REALIZATION_LEVELS)
                       if lv in ladder],
            'note': 'one report, every rung watermarked — the '
                    'best build TODAY and the research target '
                    'appear together'}
