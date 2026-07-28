"""
@module supplychain.formula_analysis

Product formulas costed from CITED prices (src-2): requirement
coverage (every candidate per role, cited or research-gap), blend
cost per kg validated against the product's ProductInputRequirement,
and a cheapest-feasible-blend SUGGESTION — so 'material-cost-per-kg'
becomes a standard scoring term on simulation results and formula
search can chase affordability with evidence.

Stdlib only; duck-typed over manager.objectTables.
"""

import json

from supplychain.sourcing_analysis import (
    _loads, _named, _rows, price_compare,
)

#: The scoring-term identity every costing emits — is_positive False
#: (cheaper is better); registering the matching ScoreTerm row in the
#: scoring module is a one-row follow-up.
COST_TERM = {'term': 'material-cost-per-kg', 'unit': 'USD/kg',
             'is_positive': False}

FRACTION_TOLERANCE = 0.001


def _requirement_for(manager, product_item_ref):
    for row in _rows(manager, 'ProductInputRequirement'):
        if getattr(row, 'product_item_ref', '') == product_item_ref:
            return row
    return None


def _best_unit_price(manager, item_ref, policy_name='',
                     source_choice='cheapest'):
    """Best cited USD/kg for an item: 'cheapest' overall, or
    'preferred' = best-ranked available source's price."""
    compare = price_compare(manager, item_ref,
                            policy_name=policy_name)
    if not compare.get('ok'):
        return None
    kg_rows = [r for r in compare['rows']
               if r['normalizedUnit'] == 'USD/kg'
               and r['availability'] == 'available']
    if not kg_rows:
        return None
    if source_choice == 'preferred':
        pick = min(kg_rows, key=lambda r: (r['rank'],
                                           r['normalized']))
    else:
        pick = min(kg_rows, key=lambda r: r['normalized'])
    return pick


def requirement_coverage(manager, product_item_ref, policy_name=''):
    """Roles -> every candidate with its best cited USD/kg, or an
    explicit research-gap entry when uncited."""
    req = _requirement_for(manager, product_item_ref)
    if req is None:
        return {'ok': False,
                'refusal': f'no ProductInputRequirement for '
                           f'"{product_item_ref}"',
                'suggestion': {
                    'evidence': 'the full input map is data',
                    'knob': 'ProductInputRequirement rows',
                    'action': 'define the roles + candidates first'}}
    roles = []
    gaps = []
    for role in _loads(req, 'roles_json', []):
        candidates = []
        for item in role.get('candidates', []):
            best = _best_unit_price(manager, item,
                                    policy_name=policy_name)
            if best is None:
                made = make_cost(manager, item,
                                 policy_name=policy_name)
                if made is not None:
                    # Uncited but MAKEABLE from a seeded recipe —
                    # grounded, just not purchasable; not a gap.
                    candidates.append({
                        'item': item, 'cited': False,
                        'makeable': True,
                        'makeCostPerKg': made['usdPerKg'],
                        'makeFormula': made['formula']})
                    continue
                candidates.append({'item': item, 'cited': False})
                gaps.append({'role': role.get('role', ''),
                             'item': item,
                             'action': f'add a dated PriceCitation '
                                       f'for "{item}"'})
            else:
                candidates.append({
                    'item': item, 'cited': True,
                    'usdPerKg': best['normalized'],
                    'source': best['source'],
                    'rank': best['rank'],
                    'citation': best['citation'],
                    'observedAt': best['observedAt'],
                    'isEstimate': best['isEstimate']})
        roles.append({'role': role.get('role', ''),
                      'purpose': role.get('purpose', ''),
                      'minFraction': role.get('min_fraction', 0.0),
                      'maxFraction': role.get('max_fraction', 1.0),
                      'candidates': candidates})
    return {'ok': True, 'product': product_item_ref,
            'requirement': getattr(req, 'name', ''),
            'roles': roles, 'researchGaps': gaps}


def _validate_components(req, components):
    roles = {r.get('role', ''): r
             for r in _loads(req, 'roles_json', [])}
    total = 0.0
    seen_roles = {}
    for comp in components:
        role = roles.get(comp.get('role', ''))
        if role is None:
            return (f'component "{comp.get("item_ref", "?")}" names '
                    f'unknown role "{comp.get("role", "")}"')
        if comp.get('item_ref') not in role.get('candidates', []):
            return (f'"{comp.get("item_ref", "?")}" is not a '
                    f'candidate for role "{comp["role"]}" — extend '
                    'the ProductInputRequirement deliberately if it '
                    'should be')
        fraction = float(comp.get('fraction', 0.0))
        total += fraction
        seen_roles[comp['role']] = seen_roles.get(comp['role'],
                                                  0.0) + fraction
    if abs(total - 1.0) > FRACTION_TOLERANCE:
        return f'fractions sum to {round(total, 4)}, not 1.0'
    for role_name, role in roles.items():
        got = seen_roles.get(role_name, 0.0)
        lo = float(role.get('min_fraction', 0.0))
        hi = float(role.get('max_fraction', 1.0))
        if got < lo - FRACTION_TOLERANCE \
                or got > hi + FRACTION_TOLERANCE:
            return (f'role "{role_name}" filled at '
                    f'{round(got, 4)} — outside its '
                    f'[{lo}, {hi}] range')
    return None


def formula_cost(manager, formula, policy_name='',
                 source_choice='cheapest'):
    """Blend USD/kg for a ProductFormula (row or duck-typed), with
    per-component breakdown + the scoring-term block."""
    product = getattr(formula, 'product_item_ref', '')
    req = _requirement_for(manager, product)
    if req is None:
        return {'ok': False,
                'refusal': f'no ProductInputRequirement for '
                           f'"{product}" — cost without a '
                           'requirement map would hide missing '
                           'roles'}
    components = _loads(formula, 'components_json', [])
    problem = _validate_components(req, components)
    if problem:
        return {'ok': False,
                'refusal': f'formula '
                           f'"{getattr(formula, "name", "?")}" is '
                           f'infeasible: {problem}'}
    breakdown = []
    total = 0.0
    any_estimate = False
    for comp in components:
        best = _best_unit_price(manager, comp['item_ref'],
                                policy_name=policy_name,
                                source_choice=source_choice)
        if best is None:
            return {'ok': False,
                    'refusal': f'no cited USD/kg price for '
                               f'"{comp["item_ref"]}" — cost would '
                               'be a guess',
                    'suggestion': {
                        'evidence': 'prices are citations',
                        'knob': 'PriceCitation rows',
                        'action': f'cite "{comp["item_ref"]}" '
                                  '(dated, with URL)'}}
        contribution = round(comp['fraction'] * best['normalized'],
                             4)
        any_estimate = any_estimate or best['isEstimate']
        breakdown.append({
            'item': comp['item_ref'], 'role': comp['role'],
            'fraction': comp['fraction'],
            'usdPerKg': best['normalized'],
            'contribution': contribution,
            'source': best['source'], 'citation': best['citation'],
            'observedAt': best['observedAt'],
            'isEstimate': best['isEstimate']})
        total += contribution
    yf = float(getattr(formula, 'yield_fraction', 1.0) or 1.0)
    if not 0.0 < yf <= 1.0:
        return {'ok': False,
                'refusal': f'yield_fraction {yf} outside (0, 1]'}
    out_cost = round(total / yf, 4)
    return {'ok': True,
            'formula': getattr(formula, 'name', ''),
            'product': product,
            'sourceChoice': source_choice,
            'usdPerKg': out_cost,
            'inputBlendCostPerKg': round(total, 4),
            'yieldFraction': yf,
            'anyEstimate': any_estimate,
            'breakdown': breakdown,
            'scoreTerm': {**COST_TERM, 'value': out_cost,
                          'evidence': [b['citation']
                                       for b in breakdown]}}


def cheapest_blend(manager, product_item_ref, policy_name='',
                   source_choice='cheapest'):
    """Min-cost feasible fractions: every role at its min with its
    cheapest cited candidate, remainder poured into the cheapest
    roles up to their max. A SUGGESTION — material properties are
    not costed here, so print-validate before adopting."""
    coverage = requirement_coverage(manager, product_item_ref,
                                    policy_name=policy_name)
    if not coverage.get('ok'):
        return coverage
    picks = []
    for role in coverage['roles']:
        cited = [c for c in role['candidates'] if c.get('cited')]
        if not cited:
            if float(role.get('minFraction', 0.0)) == 0.0:
                # OPTIONAL role with nothing cited — filled at zero,
                # honestly absent from the cost optimum.
                continue
            return {'ok': False,
                    'refusal': f'role "{role["role"]}" has no cited '
                               'candidate — cheapest blend would be '
                               'a guess',
                    'researchGaps': coverage['researchGaps']}
        best = min(cited, key=lambda c: c['usdPerKg'])
        picks.append({'role': role['role'], 'item': best['item'],
                      'usdPerKg': best['usdPerKg'],
                      'fraction': float(role['minFraction']),
                      'max': float(role['maxFraction'])})
    remaining = round(1.0 - sum(p['fraction'] for p in picks), 6)
    if remaining < -FRACTION_TOLERANCE:
        return {'ok': False,
                'refusal': 'role minimum fractions already exceed '
                           '1.0 — the requirement is inconsistent'}
    for p in sorted(picks, key=lambda p: p['usdPerKg']):
        room = p['max'] - p['fraction']
        take = min(room, remaining)
        p['fraction'] = round(p['fraction'] + take, 6)
        remaining = round(remaining - take, 6)
        if remaining <= FRACTION_TOLERANCE:
            break
    if remaining > FRACTION_TOLERANCE:
        return {'ok': False,
                'refusal': 'role maximum fractions cannot reach '
                           '1.0 — the requirement is inconsistent'}
    total = round(sum(p['fraction'] * p['usdPerKg'] for p in picks),
                  4)
    return {'ok': True, 'product': product_item_ref,
            'sourceChoice': source_choice,
            'usdPerKg': total,
            'components': [{'item_ref': p['item'], 'role': p['role'],
                            'fraction': p['fraction']}
                           for p in picks],
            'scoreTerm': {**COST_TERM, 'value': total},
            'suggestion': {
                'evidence': 'cost-only optimum over cited prices — '
                            'material properties NOT considered',
                'knob': 'ProductFormula rows',
                'action': 'print-validate this blend before '
                          'adopting it as a formula'},
            'researchGaps': coverage['researchGaps']}


def make_cost(manager, item_ref, policy_name='',
              source_choice='cheapest', _visiting=None):
    """Cheapest cost to MAKE an item from its seeded ProductFormula
    rows (validated recipes only — the optimizer stays a suggestion),
    with components themselves resolved make-vs-buy recursively.
    None when the item has no costable formula. Cycle-guarded."""
    _visiting = _visiting or set()
    if item_ref in _visiting:
        return None
    best = None
    for f in _rows(manager, 'ProductFormula'):
        if getattr(f, 'product_item_ref', '') != item_ref:
            continue
        cost = cascaded_cost(manager, f, policy_name=policy_name,
                             source_choice=source_choice,
                             _visiting=_visiting | {item_ref})
        if cost.get('ok') and (best is None
                               or cost['usdPerKg']
                               < best['usdPerKg']):
            best = {'usdPerKg': cost['usdPerKg'],
                    'formula': cost['formula'],
                    'anyEstimate': cost['anyEstimate'],
                    'madeIntermediates': cost['madeIntermediates']}
    return best


def effective_unit_price(manager, item_ref, policy_name='',
                         source_choice='cheapest', _visiting=None):
    """min(buy it, make it) for an item — the intermediary seam.
    Returns a price row tagged via 'cited' or 'made'."""
    cited = _best_unit_price(manager, item_ref,
                             policy_name=policy_name,
                             source_choice=source_choice)
    made = make_cost(manager, item_ref, policy_name=policy_name,
                     source_choice=source_choice,
                     _visiting=_visiting)
    if cited is None and made is None:
        return None
    if made is None or (cited is not None
                        and cited['normalized']
                        <= made['usdPerKg']):
        return {**cited, 'via': 'cited'}
    return {'normalized': made['usdPerKg'], 'via': 'made',
            'source': f'self-made ({made["formula"]})',
            'citation': made['formula'],
            'observedAt': '', 'isEstimate': made['anyEstimate'],
            'madeIntermediates': made['madeIntermediates']}


def cascaded_cost(manager, formula, policy_name='',
                  source_choice='cheapest', _visiting=None):
    """formula_cost, but every component resolves make-vs-buy
    (effective_unit_price) — the true local-production cost once
    intermediaries like waterglass can be made in-house. Energy is
    NOT costed in v1; each made intermediate carries that caveat."""
    product = getattr(formula, 'product_item_ref', '')
    req = _requirement_for(manager, product)
    if req is None:
        return {'ok': False,
                'refusal': f'no ProductInputRequirement for '
                           f'"{product}"'}
    components = _loads(formula, 'components_json', [])
    problem = _validate_components(req, components)
    if problem:
        return {'ok': False,
                'refusal': f'formula '
                           f'"{getattr(formula, "name", "?")}" is '
                           f'infeasible: {problem}'}
    breakdown, made_intermediates = [], []
    total = 0.0
    any_estimate = False
    for comp in components:
        eff = effective_unit_price(manager, comp['item_ref'],
                                   policy_name=policy_name,
                                   source_choice=source_choice,
                                   _visiting=_visiting)
        if eff is None:
            return {'ok': False,
                    'refusal': f'"{comp["item_ref"]}" has neither a '
                               'cited price nor a costable make '
                               'formula',
                    'suggestion': {
                        'evidence': 'buy-or-make, never guess',
                        'knob': 'PriceCitation / ProductFormula',
                        'action': f'cite or define a recipe for '
                                  f'"{comp["item_ref"]}"'}}
        contribution = round(comp['fraction'] * eff['normalized'], 4)
        any_estimate = any_estimate or eff.get('isEstimate', False)
        if eff['via'] == 'made':
            made_intermediates.append(
                {'item': comp['item_ref'],
                 'formula': eff['citation'],
                 'usdPerKg': eff['normalized'],
                 'caveat': 'process energy NOT costed in v1'})
        breakdown.append({
            'item': comp['item_ref'], 'role': comp['role'],
            'fraction': comp['fraction'], 'via': eff['via'],
            'usdPerKg': eff['normalized'],
            'contribution': contribution,
            'source': eff.get('source', ''),
            'citation': eff.get('citation', '')})
        total += contribution
    yf = float(getattr(formula, 'yield_fraction', 1.0) or 1.0)
    if not 0.0 < yf <= 1.0:
        return {'ok': False,
                'refusal': f'yield_fraction {yf} outside (0, 1]'}
    out_cost = round(total / yf, 4)
    return {'ok': True,
            'formula': getattr(formula, 'name', ''),
            'product': product, 'sourceChoice': source_choice,
            'usdPerKg': out_cost,
            'inputBlendCostPerKg': round(total, 4),
            'yieldFraction': yf,
            'anyEstimate': any_estimate,
            'madeIntermediates': made_intermediates,
            'breakdown': breakdown,
            'scoreTerm': {**COST_TERM, 'value': out_cost,
                          'evidence': [b['citation']
                                       for b in breakdown]}}


def product_cost_comparison(manager, product_item_ref,
                            policy_name=''):
    """Our formulas vs the optimizer vs WHOLE-product substitutes —
    one table, caveats attached, so the cheap option never hides
    what it costs you (plastics, fumes, eco)."""
    req = _requirement_for(manager, product_item_ref)
    if req is None:
        return {'ok': False,
                'refusal': f'no ProductInputRequirement for '
                           f'"{product_item_ref}"'}
    rows = []
    for f in _rows(manager, 'ProductFormula'):
        if getattr(f, 'product_item_ref', '') != product_item_ref:
            continue
        cost = formula_cost(manager, f, policy_name=policy_name)
        if cost.get('ok'):
            rows.append({'kind': 'formula',
                         'name': getattr(f, 'name', ''),
                         'usdPerKg': cost['usdPerKg'],
                         'anyEstimate': cost['anyEstimate'],
                         'caveats': []})
        cascaded = cascaded_cost(manager, f,
                                 policy_name=policy_name)
        if cascaded.get('ok') and cascaded['madeIntermediates'] \
                and cost.get('ok') \
                and cascaded['usdPerKg'] < cost['usdPerKg'] * 0.99:
            rows.append({'kind': 'formula-with-made-intermediates',
                         'name': f'{getattr(f, "name", "")}'
                                 ' (+self-made inputs)',
                         'usdPerKg': cascaded['usdPerKg'],
                         'anyEstimate': cascaded['anyEstimate'],
                         'madeIntermediates':
                             cascaded['madeIntermediates'],
                         'caveats': ['intermediates made in-house — '
                                     'process energy NOT costed '
                                     'in v1']})
    cheapest = cheapest_blend(manager, product_item_ref,
                              policy_name=policy_name)
    if cheapest.get('ok'):
        rows.append({'kind': 'optimized-blend',
                     'name': 'cheapest-feasible-blend',
                     'usdPerKg': cheapest['usdPerKg'],
                     'anyEstimate': True,
                     'components': cheapest['components'],
                     'caveats': ['cost-only optimum — '
                                 'print-validate before adopting']})
    for sub in _loads(req, 'substitutes_json', []):
        best = _best_unit_price(manager, sub.get('item_ref', ''),
                                policy_name=policy_name)
        source = _named(manager, 'SupplySourceProfile',
                        best['source']) if best else None
        row = {'kind': 'substitute',
               'name': sub.get('item_ref', ''),
               'caveats': list(sub.get('caveats', [])),
               'notes': sub.get('notes', '')}
        if best is None:
            row['usdPerKg'] = None
            row['refusal'] = 'no cited price — comparison pending'
        else:
            row['usdPerKg'] = best['normalized']
            row['anyEstimate'] = best['isEstimate']
            row['citation'] = best['citation']
            row['observedAt'] = best['observedAt']
            if source is not None:
                row['ecoFriendly'] = bool(
                    getattr(source, 'is_eco_friendly', False))
        rows.append(row)
    priced = [r for r in rows if r.get('usdPerKg') is not None]
    result = {'ok': True, 'product': product_item_ref,
              'rows': sorted(rows,
                             key=lambda r: (r.get('usdPerKg')
                                            is None,
                                            r.get('usdPerKg') or 0))}
    if priced:
        best_ours = min((r for r in priced
                         if r['kind'] != 'substitute'),
                        key=lambda r: r['usdPerKg'], default=None)
        best_sub = min((r for r in priced
                        if r['kind'] == 'substitute'),
                       key=lambda r: r['usdPerKg'], default=None)
        if best_ours and best_sub:
            result['verdict'] = {
                'ours': {'name': best_ours['name'],
                         'usdPerKg': best_ours['usdPerKg']},
                'substitute': {'name': best_sub['name'],
                               'usdPerKg': best_sub['usdPerKg'],
                               'caveats': best_sub['caveats']},
                'oursCheaperPct': round(
                    100.0 * (best_sub['usdPerKg']
                             - best_ours['usdPerKg'])
                    / best_sub['usdPerKg'], 1)}
    return result


def formulas_catalog(manager, policy_name=''):
    rows = []
    for f in _rows(manager, 'ProductFormula'):
        cost = formula_cost(manager, f, policy_name=policy_name)
        rows.append({
            'name': getattr(f, 'name', ''),
            'displayName': getattr(f, 'display_name', ''),
            'product': getattr(f, 'product_item_ref', ''),
            'status': getattr(f, 'status', ''),
            'usdPerKg': cost.get('usdPerKg') if cost.get('ok')
            else None,
            'costRefusal': cost.get('refusal', ''),
        })
    return {'ok': True, 'formulas': sorted(rows,
                                           key=lambda r: r['name'])}
