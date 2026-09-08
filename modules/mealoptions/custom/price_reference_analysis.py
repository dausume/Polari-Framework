"""
@module mealoptions.custom.price_reference_analysis

mo-2 — the two computations over PriceReference rows (imports ONLY
mealoptions + stdlib; the instance-side caller that reads live
PriceObservation rows is nutrition.custom.market_analysis):

  aggregate_references  normalized price entries (nutrition's
                        normalized_prices shape) → PriceReference row
                        dicts grouped per (food, month, source_type,
                        chain_name-if-chain, region); median / min /
                        max / sample_count; person, place and day
                        STRIPPED (PRIVACY_STRIPPED_FIELDS).
  price_advice          "advice about cost difference between kroger
                        vs farmer market vs X" with the LOCAL-FIRST
                        knob (plan §2, D4): a local / independent
                        source within `local_preference_pct` of the
                        cheapest chain median is recommended first;
                        0 = strict cheapest. The ranking states which
                        rule decided each row.

Every number is derived from the references handed in; the only
prior is the knob, labelled on the payload.
"""

from collections import Counter

from mealoptions.price_reference_basis import (
    CHAIN_KINDS, LOCAL_KINDS, OWNERSHIP_KINDS, PROVENANCE_AGGREGATED,
    VARIES_BY_VENDOR_NOTE, reference_name,
)

LOCAL_PREFERENCE_DEFAULT_PCT = 10.0
LOCAL_PREFERENCE_LABEL = ('10 % convention prior — Dustin 2026-09-03: '
                          'prioritise local and independent over '
                          'monopolies; 0 = strict cheapest')

_MISSING = object()


def _get(row, key, default=None):
    """Field of a dict OR an object (the API hands rows, the export
    hands dicts)."""
    if isinstance(row, dict):
        return row.get(key, default)
    value = getattr(row, key, _MISSING)
    return default if value is _MISSING else value


def _median(values):
    values = sorted(values)
    n = len(values)
    if not n:
        return 0.0
    mid = n // 2
    if n % 2:
        return float(values[mid])
    return (values[mid - 1] + values[mid]) / 2.0


def _month_of(observed_date):
    """'YYYY-MM-DD' (or 'YYYY-MM') → 'YYYY-MM'; '' when undated or
    malformed — a reference month needs a real date."""
    text = (observed_date or '').strip()
    if len(text) < 7 or text[4] != '-':
        return ''
    year, month = text[:4], text[5:7]
    if not (year.isdigit() and month.isdigit() and 1 <= int(month) <= 12):
        return ''
    return f'{year}-{month}'


def _source_type(entry):
    kind = (entry.get('ownershipKind') or 'other').strip()
    return kind if kind in OWNERSHIP_KINDS else 'other'


def aggregate_references(normalized_entries, today=None):
    """normalized_prices entries → PriceReference row dicts.

    Grouping key = (food, month, source_type, chain_name if the
    source is a chain kind else '', region_label as typed or
    'unstated'). Entries without a parseable observedDate are left
    out (no day → no month; the caller reports them). `today` is
    accepted for signature parity with the callers; nothing here
    depends on the clock.
    """
    groups = {}
    for entry in normalized_entries:
        month = _month_of(entry.get('observedDate', ''))
        if not month:
            continue
        source_type = _source_type(entry)
        chain = (entry.get('chainName') or '').strip() \
            if source_type in CHAIN_KINDS else ''
        region = (entry.get('region') or '').strip() or 'unstated'
        key = (entry.get('food', ''), month, source_type, chain, region)
        groups.setdefault(key, []).append(entry)

    rows = []
    for (food, month, source_type, chain, region), entries in \
            sorted(groups.items()):
        currency = Counter(e.get('currency') or 'USD'
                           for e in entries).most_common(1)[0][0]
        same = [e for e in entries
                if (e.get('currency') or 'USD') == currency]
        prices = [float(e.get('pricePerKg') or 0.0) for e in same]
        local = source_type in LOCAL_KINDS
        prior_mixed = any(
            (e.get('weightBasis') or '') != 'exact-unit-conversion'
            for e in same)
        notes = []
        if local:
            notes.append(VARIES_BY_VENDOR_NOTE)
        if prior_mixed:
            notes.append('at least one sample rode a labelled unit-weight '
                         'prior (count package → grams)')
        if len(same) != len(entries):
            notes.append(f'{len(entries) - len(same)} sample(s) in another '
                         f'currency excluded')
        if all(e.get('isDemo') for e in same):
            notes.append('derived from demo observations only')
        rows.append({
            'name': reference_name(food, month, source_type, chain, region),
            'food_name': food,
            'month': month,
            'source_type': source_type,
            'chain_name': chain,
            'region_label': region,
            'currency': currency,
            'price_per_kg_median': round(_median(prices), 2),
            'price_per_kg_min': round(min(prices), 2),
            'price_per_kg_max': round(max(prices), 2),
            'sample_count': len(same),
            'weight_basis': 'prior-mixed' if prior_mixed else 'exact',
            'varies_by_vendor': local,
            'provenance_id': PROVENANCE_AGGREGATED,
            'is_prior': True,
            'notes': '; '.join(notes),
        })
    return rows


def _record(ref):
    return {
        'sourceType': _get(ref, 'source_type', 'other'),
        'chainName': _get(ref, 'chain_name', '') or '',
        'region': _get(ref, 'region_label', 'unstated') or 'unstated',
        'medianPerKg': float(_get(ref, 'price_per_kg_median', 0.0) or 0.0),
        'sampleCount': int(_get(ref, 'sample_count', 0) or 0),
        'variesByVendor': bool(_get(ref, 'varies_by_vendor', False)),
        'isLocal': _get(ref, 'source_type', 'other') in LOCAL_KINDS,
        'rule': '',
    }


def price_advice(references, food_name,
                 local_preference_pct=LOCAL_PREFERENCE_DEFAULT_PCT,
                 month=None):
    """Rank a food's references by median $/kg with the local-first
    rule; `month` None = the latest month on file for that food."""
    try:
        pct = float(local_preference_pct)
    except (TypeError, ValueError):
        pct = LOCAL_PREFERENCE_DEFAULT_PCT
    pct = max(0.0, pct)
    knob = {'localPreferencePct': pct, 'label': LOCAL_PREFERENCE_LABEL}
    why = (f'a local / independent source is recommended when its median '
           f'is within {pct:g} % of the cheapest chain median; 0 % is '
           f'strict cheapest')

    mine = [r for r in references if _get(r, 'food_name', '') == food_name]
    if not mine:
        return {'ok': False, 'food': food_name, 'month': month or '',
                'ranking': [], 'recommended': None,
                'whyLocalFirst': why, 'knob': knob,
                'honesty': [f'no price references for "{food_name}" — '
                            f'nothing to rank'],
                'error': f'no price references for "{food_name}"'}
    months = sorted({_get(r, 'month', '') for r in mine})
    month = month or months[-1]
    in_month = [r for r in mine if _get(r, 'month', '') == month]
    if not in_month:
        return {'ok': False, 'food': food_name, 'month': month,
                'ranking': [], 'recommended': None,
                'whyLocalFirst': why, 'knob': knob,
                'honesty': [f'no references for "{food_name}" in {month}; '
                            f'months on file: {", ".join(months)}'],
                'error': f'no references for "{food_name}" in {month}'}

    ranking = sorted((_record(r) for r in in_month),
                     key=lambda rec: (rec['medianPerKg'], rec['sourceType'],
                                      rec['chainName']))
    chains = [rec for rec in ranking if not rec['isLocal']]
    locals_ = [rec for rec in ranking if rec['isLocal']]
    cheapest = ranking[0]
    cheapest_chain = chains[0] if chains else None
    recommended = None
    if cheapest_chain is not None and locals_:
        band = cheapest_chain['medianPerKg'] * (1.0 + pct / 100.0)
        within = [rec for rec in locals_ if rec['medianPerKg'] <= band]
        if within:
            recommended = within[0]
            recommended['rule'] = (
                'recommended: cheapest local source within '
                f'{pct:g} % of the cheapest chain median '
                f'({cheapest_chain["medianPerKg"]:.2f})')
    if recommended is None:
        recommended = cheapest
        recommended['rule'] = ('recommended: cheapest overall'
                               if pct == 0 or not locals_
                               or cheapest_chain is None
                               else 'recommended: cheapest overall — no '
                                    f'local source within {pct:g} % of '
                                    'the cheapest chain median')
    for rec in ranking:
        if rec['rule']:
            continue
        if rec is cheapest_chain:
            rec['rule'] = 'cheapest chain median (the band\'s anchor)'
        elif rec['isLocal'] and cheapest_chain is not None:
            rec['rule'] = (f'local, above the {pct:g} % band'
                           if rec['medianPerKg'] > cheapest_chain[
                               'medianPerKg'] * (1.0 + pct / 100.0)
                           else 'local, within the band but not the '
                                'cheapest local')
        else:
            rec['rule'] = 'ranked by median $/kg'

    honesty = [
        'medians are aggregated from user-entered observations by '
        'month, source type and coarse region; purchaser, place and '
        'day were stripped before aggregation',
        f'{len(in_month)} reference row(s) for {month}; sample counts '
        'ride each row — a single sample is a single price, not a '
        'market',
    ]
    if any(rec['variesByVendor'] for rec in ranking):
        honesty.append(f'local / independent rows: {VARIES_BY_VENDOR_NOTE}')
    if cheapest_chain is None:
        honesty.append('no chain reference this month — the band has no '
                       'anchor, so the cheapest source is recommended')
    return {
        'ok': True,
        'food': food_name,
        'month': month,
        'ranking': ranking,
        'recommended': recommended,
        'recommendedSource': (recommended['chainName']
                              or recommended['sourceType']),
        'recommendedMedianPerKg': recommended['medianPerKg'],
        'recommendedRule': recommended['rule'],
        'whyLocalFirst': why,
        'knob': knob,
        'honesty': honesty,
    }
