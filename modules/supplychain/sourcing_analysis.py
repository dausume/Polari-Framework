"""
@module supplychain.sourcing_analysis

Duck-typed analysis over the sourcing rows: normalize cited prices,
rank sources by the active preference policy, compare prices across
sources (the spread, and what preference COSTS), and flag scenario
price drift as evidence-bearing suggestions — never auto-applied.

Stdlib only; takes any manager exposing .objectTables.
"""

import json

#: Mass units convertible to kg. Items priced per piece ('unit',
#: 'kit') only compare against the same unit — mixing dimensions is
#: refused honestly, never guessed.
MASS_TO_KG = {'kg': 1.0, 'g': 0.001, 'lb': 0.45359237,
              'oz': 0.028349523}


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


def normalized_price(citation):
    """(value, unit_label) — USD/kg for mass units, USD/<unit> for
    piece units; None when the citation can't be normalized."""
    price = float(getattr(citation, 'price', 0.0) or 0.0)
    amount = float(getattr(citation, 'amount', 0.0) or 0.0)
    unit = (getattr(citation, 'amount_unit', '') or '').lower()
    if price <= 0 or amount <= 0:
        return None, ''
    if unit in MASS_TO_KG:
        return round(price / (amount * MASS_TO_KG[unit]), 4), 'USD/kg'
    return round(price / amount, 4), f'USD/{unit}'


def active_policy(manager, policy_name=''):
    if policy_name:
        return _named(manager, 'SourcePreferencePolicy', policy_name)
    for row in _rows(manager, 'SourcePreferencePolicy'):
        if getattr(row, 'is_active', False):
            return row
    return None


def rank_source(source, policy):
    """First-match-wins over the rules; (rank, label)."""
    if policy is None:
        return 99, 'no policy'
    for rule in _loads(policy, 'rules_json', []):
        require = rule.get('require', {})
        if all(bool(getattr(source, flag, False)) == bool(want)
               for flag, want in require.items()):
            return rule.get('rank', 99), rule.get('label', '')
    return getattr(policy, 'default_rank', 99), 'unranked'


def source_catalog(manager, policy_name=''):
    """All sources with flags, overlap labels, rank, and both sides
    of the loop (supplies + demands)."""
    policy = active_policy(manager, policy_name)
    rows = []
    for s in _rows(manager, 'SupplySourceProfile'):
        rank, label = rank_source(s, policy)
        overlap = [flag for flag in
                   ('open_source', 'commercial', 'local', 'polari',
                    'eco_friendly')
                   if getattr(s, f'is_{flag}', False)]
        rows.append({
            'name': getattr(s, 'name', ''),
            'displayName': getattr(s, 'display_name', ''),
            'supplier': getattr(s, 'supplier_name', ''),
            'url': getattr(s, 'url', ''),
            'categories': overlap,
            'availability': getattr(s, 'availability', ''),
            'rank': rank, 'rankLabel': label,
            'supplies': _loads(s, 'supplies_json', []),
            'demands': _loads(s, 'demands_json', []),
            'businessModelRef': getattr(s, 'business_model_ref', ''),
            'notes': getattr(s, 'notes', ''),
        })
    rows.sort(key=lambda r: (r['rank'], r['name']))
    return {'ok': True,
            'policy': getattr(policy, 'name', '') if policy else '',
            'sources': rows}


def price_compare(manager, item_ref, policy_name=''):
    """Every citation for an item, normalized and policy-ranked —
    the spread, and what preferring the ladder actually costs."""
    policy = active_policy(manager, policy_name)
    citations = [c for c in _rows(manager, 'PriceCitation')
                 if getattr(c, 'item_ref', '') == item_ref]
    if not citations:
        return {'ok': False,
                'refusal': f'no price citations for "{item_ref}" — '
                           'cite a price (with date + URL) first',
                'suggestion': {
                    'evidence': 'prices are citations, never bare '
                                'numbers',
                    'knob': 'PriceCitation rows',
                    'action': 'add a dated citation for the item'}}
    rows, skipped = [], []
    for c in citations:
        value, unit_label = normalized_price(c)
        if value is None:
            skipped.append(getattr(c, 'name', ''))
            continue
        source = _named(manager, 'SupplySourceProfile',
                        getattr(c, 'source_ref', ''))
        rank, label = rank_source(source, policy) if source \
            else (99, 'unknown source')
        rows.append({
            'citation': getattr(c, 'name', ''),
            'source': getattr(c, 'source_ref', ''),
            'availability': getattr(source, 'availability', '?')
            if source else '?',
            'rank': rank, 'rankLabel': label,
            'price': getattr(c, 'price', 0.0),
            'amount': getattr(c, 'amount', 0.0),
            'amountUnit': getattr(c, 'amount_unit', ''),
            'normalized': value, 'normalizedUnit': unit_label,
            'observedAt': getattr(c, 'observed_at', ''),
            'citationUrl': getattr(c, 'citation_url', ''),
            'isEstimate': bool(getattr(c, 'is_estimate', False)),
        })
    if not rows:
        return {'ok': False,
                'refusal': f'citations for "{item_ref}" exist but '
                           'none normalize (bad amount/unit)',
                'skipped': skipped}
    units = {r['normalizedUnit'] for r in rows}
    result = {'ok': True, 'item': item_ref,
              'policy': getattr(policy, 'name', '') if policy else '',
              'rows': sorted(rows, key=lambda r: (r['rank'],
                                                  r['normalized'])),
              'skipped': skipped}
    if len(units) > 1:
        result['note'] = (f'mixed units {sorted(units)} — spread '
                          'computed per unit-dimension only')
    for unit_label in units:
        sub = [r for r in rows if r['normalizedUnit'] == unit_label]
        cheapest = min(sub, key=lambda r: r['normalized'])
        priciest = max(sub, key=lambda r: r['normalized'])
        available = [r for r in sub
                     if r['availability'] == 'available']
        preferred = min(available,
                        key=lambda r: (r['rank'], r['normalized'])) \
            if available else None
        spread = {
            'unit': unit_label,
            'cheapest': {'source': cheapest['source'],
                         'value': cheapest['normalized']},
            'priciest': {'source': priciest['source'],
                         'value': priciest['normalized']},
            'spreadPct': round(
                100.0 * (priciest['normalized']
                         - cheapest['normalized'])
                / cheapest['normalized'], 1),
        }
        if preferred:
            spread['preferredAvailable'] = {
                'source': preferred['source'],
                'rank': preferred['rank'],
                'value': preferred['normalized'],
                'preferencePremiumPct': round(
                    100.0 * (preferred['normalized']
                             - cheapest['normalized'])
                    / cheapest['normalized'], 1)}
        result.setdefault('spread', []).append(spread)
    return result


def preferred_source(manager, item_ref, policy_name=''):
    """Top-of-ladder AVAILABLE source for an item + the potential
    sources above it (suggestions to develop, never auto-picked)."""
    compare = price_compare(manager, item_ref,
                            policy_name=policy_name)
    if not compare.get('ok'):
        return compare
    rows = compare['rows']
    available = [r for r in rows if r['availability'] == 'available']
    if not available:
        return {'ok': False,
                'refusal': f'no AVAILABLE source cited for '
                           f'"{item_ref}" — only potential ones',
                'potential': rows}
    best = min(available, key=lambda r: (r['rank'], r['normalized']))
    better_potential = [
        r for r in rows if r['availability'] == 'potential'
        and r['rank'] < best['rank']]
    out = {'ok': True, 'item': item_ref, 'preferred': best}
    if better_potential:
        out['suggestion'] = {
            'evidence': f'{len(better_potential)} potential '
                        f'source(s) would outrank '
                        f'{best["source"]} on the ladder',
            'knob': 'SupplySourceProfile.availability',
            'action': 'develop the potential source(s): '
                      + ', '.join(r['source']
                                  for r in better_potential)}
    return out


def scenario_price_drift(manager, scenario, policy_name=''):
    """Compare a scenario's pinned driver prices against the best
    cited price for each product's item_ref — drift is an
    evidence-bearing SUGGESTION, never an edit."""
    try:
        seed_spec = json.loads(getattr(scenario, 'seed_spec_json',
                                       '') or '{}')
        driver = json.loads(getattr(scenario, 'driver_spec_json',
                                    '') or '{}')
    except ValueError as exc:
        return {'ok': False, 'refusal': f'scenario JSON invalid: '
                                        f'{exc}'}
    item_by_ref = {p['ref']: p.get('item_ref', '')
                   for p in seed_spec.get('products', [])}
    findings = []
    for po in driver.get('per_cycle', {}).get('purchases', []):
        for line in po.get('lines', []):
            item = item_by_ref.get(line['ref'], '')
            if not item:
                continue
            compare = price_compare(manager, item,
                                    policy_name=policy_name)
            if not compare.get('ok'):
                findings.append({
                    'product': line['ref'], 'item': item,
                    'kind': 'uncited',
                    'evidence': compare.get('refusal', ''),
                    'action': 'add a PriceCitation for the item'})
                continue
            kg_rows = [r for r in compare['rows']
                       if r['normalizedUnit'] == 'USD/kg']
            if not kg_rows:
                continue
            best = min(kg_rows, key=lambda r: r['normalized'])
            pinned = float(line.get('price_unit', 0.0))
            if pinned <= 0:
                continue
            drift_pct = round(100.0 * (best['normalized'] - pinned)
                              / pinned, 1)
            if abs(drift_pct) >= 10.0:
                findings.append({
                    'product': line['ref'], 'item': item,
                    'kind': 'price-drift',
                    'pinnedPricePerKg': pinned,
                    'bestCitedPerKg': best['normalized'],
                    'driftPct': drift_pct,
                    'citation': best['citation'],
                    'observedAt': best['observedAt'],
                    'isEstimate': best['isEstimate'],
                    'evidence': f'scenario pins {pinned}/kg; best '
                                f'citation is '
                                f'{best["normalized"]}/kg '
                                f'({best["citation"]})',
                    'action': f'consider repinning '
                              f'{line["ref"]} to '
                              f'{best["normalized"]}/kg — '
                              'deliberate edit, never automatic'})
    return {'ok': True, 'scenario': getattr(scenario, 'name', ''),
            'inDrift': bool(findings), 'findings': findings}
