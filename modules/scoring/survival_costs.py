"""
@cross-cutting
@module scoring.survival_costs
@tags @xc:bindings

Survival-cost intake (scr-12a) — Dustin 2026-07-08: "walking people
through entering in their survival costs per month … rent, mortgage,
what is required to work like cars needed per person … ask them to go
into their bank app and go through the calendar for a month … also
ask for uncancellable subscriptions since those are a pseudo-tax".

CostCategory: the walkthrough IS an editable vocabulary — each
category row carries its own guidance text ('open your bank app…'),
a kind (survival / work-required / pseudo-tax / discretionary) and
the ScoreTerm its amounts land under. Editing the rows edits the
wizard (object-coherence). The pseudo-tax classification on
'uncancellable-subscriptions' is a KNOB on the row — a contestable
framing groups can vote on (scr-8/13), never baked-in fact.

submit_survival_profile: validates against the vocabulary, creates a
household ScoreSubject (pseudonymous contributor attribution) + one
ContextualizedValue per entered category under [location, month]
contexts — the profile is engine-native data the moment it lands.
Skipped categories are honest COMPLETENESS gaps, not errors.

survival_report: per-category stats across an area/month's household
profiles + subtotals by kind — "what does surviving here cost" and
"how much of that is pseudo-tax" in one read.

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - scoring.scoring_api (survival endpoints)
@see /OVERLAP_MAP.md
"""

import json

from objectTreeDecorators import treeObject, treeObjectInit
from scoring.scoring_basis import ContextualizedValue, ScoreSubject

CATEGORY_KINDS = ('survival', 'work-required', 'pseudo-tax',
                  'discretionary')

#: Below this many profiles an area statistic is a hint, not a
#: reading — flagged on the report.
SMALL_SAMPLE = 5


class CostCategory(treeObject):
    """One walkthrough step: what to enter and how to find it."""

    @treeObjectInit
    def __init__(
        self,
        # kebab-case unique key ('housing').
        name: str = '',
        display_name: str = '',
        description: str = '',
        # CATEGORY_KINDS entry — the classification KNOB.
        kind: str = 'survival',
        # The walkthrough prompt shown to the person.
        guidance: str = '',
        # Concrete examples ('rent, mortgage payment, lot fees').
        examples: str = '',
        # ScoreTerm the entered amounts land under.
        term_name: str = '',
        # Whether the survival baseline is incomplete without it.
        required: bool = True,
        sort_order: int = 100,
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.description = description
        self.kind = kind
        self.guidance = guidance
        self.examples = examples
        self.term_name = term_name
        self.required = required
        self.sort_order = sort_order
        self.notes = notes


class SurvivalCostProfile(treeObject):
    """One household's entered month of survival costs."""

    @treeObjectInit
    def __init__(
        self,
        # unique key ('household-<contributor>-<month>').
        name: str = '',
        # Contributor row (pseudonymous by its own knob).
        contributed_by: str = '',
        # ScoreContext names: where + when.
        location_context: str = '',
        month_context: str = '',
        # Household knobs.
        household_size: int = 1,
        workers: int = 1,
        cars_needed: int = 0,
        # {category: {'amount': $/month, 'notes': str}} (JSON).
        entries_json: str = '{}',
        # Category names skipped (JSON list) — honest gaps.
        skipped_json: str = '[]',
        total_monthly: float = None,
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.contributed_by = contributed_by
        self.location_context = location_context
        self.month_context = month_context
        self.household_size = household_size
        self.workers = workers
        self.cars_needed = cars_needed
        self.entries_json = entries_json
        self.skipped_json = skipped_json
        self.total_monthly = total_monthly
        self.notes = notes


def _rows(manager, class_name):
    table = (manager.objectTables or {}).get(class_name, {})
    return list(table.values()) if isinstance(table, dict) else list(table)


def _by_name(manager, class_name):
    return {getattr(r, 'name', ''): r for r in _rows(manager, class_name)}


def _parse(text, fallback):
    try:
        loaded = json.loads(text or fallback)
        return loaded if loaded is not None else json.loads(fallback)
    except Exception:
        return json.loads(fallback)


def _categories(manager):
    rows = _rows(manager, 'CostCategory')
    return sorted(rows, key=lambda r: (
        getattr(r, 'sort_order', 100), getattr(r, 'name', '')))


def survival_walkthrough(manager):
    """The wizard, generated FROM the vocabulary rows: household
    knobs first, then one step per category with its guidance."""
    steps = []
    for row in _categories(manager):
        steps.append({
            'category': getattr(row, 'name', ''),
            'displayName': getattr(row, 'display_name', ''),
            'kind': getattr(row, 'kind', 'survival'),
            'guidance': getattr(row, 'guidance', ''),
            'examples': getattr(row, 'examples', ''),
            'required': bool(getattr(row, 'required', True)),
            'description': getattr(row, 'description', ''),
        })
    if not steps:
        return {'ok': False,
                'error': 'no CostCategory rows',
                'suggestion': {'knob': 'CostCategory',
                               'action': 'seed/create the category '
                                         'vocabulary — the wizard is '
                                         'generated from it'}}
    return {
        'ok': True,
        'householdKnobs': [
            {'knob': 'household_size',
             'prompt': 'How many people live in your household?'},
            {'knob': 'workers',
             'prompt': 'How many of them work (or need to)?'},
            {'knob': 'cars_needed',
             'prompt': 'How many cars does the household NEED for '
                       'people to get to work — not own, need?'},
        ],
        'method': 'Open your bank app and go through ONE month of '
                  'the calendar, category by category — enter what '
                  'you actually paid at the end of the day, not '
                  'estimates. Skip anything that does not apply; '
                  'skips are recorded as gaps, never guessed.',
        'steps': steps,
        'note': 'this walkthrough is generated from the editable '
                'CostCategory rows — editing them edits the wizard',
    }


def submit_survival_profile(manager, payload):
    """One household's month → a profile row + engine-native values.

    payload: {'contributor': <Contributor name>,
              'location': <ScoreContext name>,
              'month': <timeframe ScoreContext name>,
              'household_size'/'workers'/'cars_needed': ints,
              'entries': {category: amount | {'amount', 'notes'}}}
    """
    contributor = payload.get('contributor', '')
    location = payload.get('location', '')
    month = payload.get('month', '')
    entries = payload.get('entries', {}) or {}
    if not contributor or not location or not month:
        return {'ok': False,
                'error': "payload needs 'contributor', 'location' "
                         "and 'month'"}
    contributors = _by_name(manager, 'Contributor')
    if contributor not in contributors:
        return {'ok': False,
                'error': f"no Contributor named '{contributor}'",
                'suggestion': {
                    'knob': 'Contributor',
                    'action': 'create your contributor row first — '
                              'pseudonyms are fine (pseudonymous '
                              'defaults true)'}}
    contexts = _by_name(manager, 'ScoreContext')
    missing_ctx = [c for c in (location, month) if c not in contexts]
    if missing_ctx:
        return {'ok': False,
                'error': f'unknown contexts: {missing_ctx}',
                'suggestion': {'knob': 'ScoreContext',
                               'action': 'create the location/month '
                                         'context rows (never '
                                         'auto-invented)'}}
    categories = {getattr(c, 'name', ''): c
                  for c in _categories(manager)}
    unknown = sorted(set(entries) - set(categories))
    if unknown:
        return {'ok': False,
                'error': f'unknown categories: {unknown}',
                'knownCategories': sorted(categories),
                'suggestion': {'knob': 'CostCategory',
                               'action': 'use the walkthrough '
                                         'vocabulary, or add the '
                                         'category row first'}}

    parsed, refused = {}, []
    for category, value in entries.items():
        raw = value.get('amount') if isinstance(value, dict) else value
        try:
            amount = float(raw)
        except (TypeError, ValueError):
            refused.append({'category': category,
                            'error': f"amount '{raw}' is not a "
                                     'number'})
            continue
        if amount < 0:
            refused.append({'category': category,
                            'error': 'negative amount refused'})
            continue
        parsed[category] = {
            'amount': amount,
            'notes': value.get('notes', '')
            if isinstance(value, dict) else ''}
    skipped = sorted(set(categories) - set(parsed))
    required_gaps = [c for c in skipped
                     if bool(getattr(categories[c], 'required',
                                     True))]
    total = sum(e['amount'] for e in parsed.values())

    profile_name = f'household-{contributor}-{month}'
    existing = _by_name(manager, 'SurvivalCostProfile')
    if profile_name in existing and not payload.get('overwrite'):
        return {'ok': False,
                'error': f"profile '{profile_name}' already exists",
                'suggestion': {'knob': 'overwrite',
                               'action': 'set true to replace this '
                                         "month's entries explicitly"}}

    subject_name = f'household-{contributor}'
    subjects = _by_name(manager, 'ScoreSubject')
    if subject_name not in subjects:
        ScoreSubject(name=subject_name,
                     display_name=f'Household of {contributor}',
                     kind='household',
                     description='survival-cost walkthrough subject',
                     manager=manager)

    if profile_name in existing:
        profile = existing[profile_name]
        profile.entries_json = json.dumps(parsed)
        profile.skipped_json = json.dumps(skipped)
        profile.total_monthly = total
        profile.location_context = location
        profile.month_context = month
        profile.household_size = int(
            payload.get('household_size', 1) or 1)
        profile.workers = int(payload.get('workers', 1) or 1)
        profile.cars_needed = int(
            payload.get('cars_needed', 0) or 0)
        try:
            manager.db.saveInstanceInDB(profile)
        except Exception:
            pass
    else:
        SurvivalCostProfile(
            name=profile_name, contributed_by=contributor,
            location_context=location, month_context=month,
            household_size=int(payload.get('household_size', 1) or 1),
            workers=int(payload.get('workers', 1) or 1),
            cars_needed=int(payload.get('cars_needed', 0) or 0),
            entries_json=json.dumps(parsed),
            skipped_json=json.dumps(skipped),
            total_monthly=total, manager=manager)

    # Engine-native values: one ContextualizedValue per entered
    # category, under [location, month] — medians/comparisons across
    # areas use the SAME machinery as every other score.
    values = _by_name(manager, 'ContextualizedValue')
    written = []
    for category, entry in parsed.items():
        term = getattr(categories[category], 'term_name', '') \
            or f'cost-{category}-monthly'
        value_name = f'{term}@{subject_name}-{month}'
        if value_name in values:
            row = values[value_name]
            row.pre_normalized_value = entry['amount']
            row.contributed_by = contributor
            try:
                manager.db.saveInstanceInDB(row)
            except Exception:
                pass
        else:
            ContextualizedValue(
                name=value_name, term_name=term,
                subject_name=subject_name,
                context_names_json=json.dumps([location, month]),
                pre_normalized_value=entry['amount'],
                source='survival-cost walkthrough',
                provenance_id=f'profile {profile_name}',
                contributed_by=contributor, manager=manager)
        written.append(value_name)

    return {
        'ok': True,
        'profile': profile_name,
        'subject': subject_name,
        'totalMonthly': round(total, 2),
        'entered': sorted(parsed),
        'skipped': skipped,
        'requiredGaps': required_gaps,
        'refused': refused,
        'valuesWritten': written,
        'note': ('skipped required categories make the survival '
                 'baseline incomplete — recorded as gaps, never '
                 'guessed' if required_gaps else
                 'survival baseline complete'),
    }


def survival_report(manager, location, month=''):
    """Across an area's household profiles (optionally one month):
    per-category stats + subtotals by category KIND."""
    categories = {getattr(c, 'name', ''): c
                  for c in _categories(manager)}
    if not categories:
        return {'ok': False, 'error': 'no CostCategory rows'}
    profiles = [
        p for p in _rows(manager, 'SurvivalCostProfile')
        if getattr(p, 'location_context', '') == location
        and (not month or getattr(p, 'month_context', '') == month)]
    if not profiles:
        return {'ok': False,
                'error': f"no SurvivalCostProfile rows for "
                         f"'{location}'"
                         + (f" in '{month}'" if month else ''),
                'suggestion': {
                    'knob': 'POST /api/scoring/survival/submit',
                    'action': 'walk through and submit household '
                              'profiles for this area'}}

    per_category, kind_totals = {}, {}
    totals = []
    for p in profiles:
        entries = _parse(getattr(p, 'entries_json', '{}'), '{}')
        totals.append(float(getattr(p, 'total_monthly', 0) or 0))
        for category, entry in entries.items():
            amount = float(entry.get('amount', 0))
            per_category.setdefault(category, []).append(amount)
    def stats(pool):
        ordered = sorted(pool)
        mid = len(ordered) // 2
        median = ordered[mid] if len(ordered) % 2 \
            else (ordered[mid - 1] + ordered[mid]) / 2
        return {'n': len(pool),
                'mean': round(sum(pool) / len(pool), 2),
                'median': round(median, 2)}
    category_stats = []
    for category in sorted(per_category):
        row = categories.get(category)
        kind = getattr(row, 'kind', 'survival') \
            if row is not None else 'unknown'
        s = stats(per_category[category])
        kind_totals.setdefault(kind, 0.0)
        kind_totals[kind] += s['mean']
        category_stats.append({
            'category': category,
            'displayName': getattr(row, 'display_name', category)
            if row is not None else category,
            'kind': kind, **s,
            'enteredBy': len(per_category[category]),
            'ofProfiles': len(profiles)})
    total_mean = sum(kind_totals.values())
    return {
        'ok': True,
        'location': location,
        'month': month or '(all months)',
        'profiles': len(profiles),
        'smallSample': len(profiles) < SMALL_SAMPLE,
        'totalMonthly': stats(totals),
        'categories': category_stats,
        'subtotalsByKind': {k: round(v, 2)
                            for k, v in sorted(kind_totals.items())},
        'pseudoTaxShare': round(
            kind_totals.get('pseudo-tax', 0.0) / total_mean, 4)
        if total_mean else None,
        'note': "subtotals sum per-category MEANS by the category's "
                'kind knob — reclassifying a category (e.g. whether '
                'uncancellable subscriptions are a pseudo-tax) is an '
                'edit to its CostCategory row, visible to everyone',
    }


#: One ScoreTerm per seeded category, so entered amounts are
#: engine-native (costs: lower is better under a burden reading).
def _cost_term(name, display, tags):
    return {
        'name': f'cost-{name}-monthly',
        'display_name': f'{display} (monthly cost)',
        'description': f'Household monthly {display.lower()} outlay '
                       'from the survival-cost walkthrough.',
        'category': 'cost-of-living', 'value_type': 'currency',
        'unit': '$/month', 'is_positive': False,
        'temporal_json': json.dumps(
            {'nature': 'flow', 'resample': 'sum'}),
        'abstract_tags_json': json.dumps(tags),
        'provenance_id': 'scr-12a survival-cost vocabulary',
    }


SEED_COST_TERMS = [
    _cost_term('housing', 'Housing', ['housing', 'cost-of-living']),
    _cost_term('utilities', 'Utilities',
               ['utilities', 'cost-of-living']),
    _cost_term('food', 'Food', ['food', 'cost-of-living']),
    _cost_term('transport-work', 'Work transport',
               ['transport', 'employment', 'cost-of-living']),
    _cost_term('healthcare', 'Healthcare',
               ['healthcare', 'cost-of-living']),
    _cost_term('childcare', 'Childcare',
               ['childcare', 'cost-of-living']),
    _cost_term('debt-minimums', 'Debt minimums',
               ['debt', 'cost-of-living']),
    _cost_term('uncancellable-subscriptions',
               'Uncancellable subscriptions',
               ['subscriptions', 'pseudo-tax', 'cost-of-living']),
]

SEED_COST_CATEGORIES = [
    {
        'name': 'housing', 'display_name': 'Housing',
        'kind': 'survival', 'sort_order': 10, 'required': True,
        'term_name': 'cost-housing-monthly',
        'guidance': 'Open your bank app and go through ONE month of '
                    'the calendar. Sum every housing payment you '
                    'actually made — the number that left your '
                    'account, not the lease figure.',
        'examples': 'rent, mortgage payment, lot fees, renters/home '
                    'insurance if paid monthly',
        'description': 'Where you sleep.',
    },
    {
        'name': 'utilities', 'display_name': 'Utilities',
        'kind': 'survival', 'sort_order': 20, 'required': True,
        'term_name': 'cost-utilities-monthly',
        'guidance': 'Same month, same calendar: electricity, gas, '
                    'water, sewage, trash, basic internet/phone '
                    '(needed to hold a job).',
        'examples': 'electric bill, water bill, phone plan, internet',
        'description': 'What keeps the household running.',
    },
    {
        'name': 'food', 'display_name': 'Food',
        'kind': 'survival', 'sort_order': 30, 'required': True,
        'term_name': 'cost-food-monthly',
        'guidance': 'Groceries only for the survival number — sum '
                    'the grocery charges across the month. Eating '
                    'out is discretionary unless work forces it.',
        'examples': 'grocery stores, food assistance copays',
        'description': 'Feeding the household.',
    },
    {
        'name': 'transport-work', 'display_name': 'Work transport',
        'kind': 'work-required', 'sort_order': 40, 'required': True,
        'term_name': 'cost-transport-work-monthly',
        'guidance': 'What it costs for the workers in the household '
                    'to GET to work: car payments and insurance for '
                    'the cars you NEED (you set how many earlier), '
                    'fuel, transit passes, parking.',
        'examples': 'car payment, car insurance, gas, bus pass, '
                    'parking',
        'description': 'Required to work — a cost of having a job.',
    },
    {
        'name': 'healthcare', 'display_name': 'Healthcare',
        'kind': 'survival', 'sort_order': 50, 'required': True,
        'term_name': 'cost-healthcare-monthly',
        'guidance': 'Premiums you pay directly, plus the month\'s '
                    'prescriptions and copays from the calendar.',
        'examples': 'insurance premium, prescriptions, copays',
        'description': 'Staying alive and able to work.',
    },
    {
        'name': 'childcare', 'display_name': 'Childcare',
        'kind': 'work-required', 'sort_order': 60, 'required': False,
        'term_name': 'cost-childcare-monthly',
        'guidance': 'Childcare that exists so the workers can work: '
                    'daycare, after-school care, a required sitter.',
        'examples': 'daycare, after-school program',
        'description': 'Required to work when children are in the '
                       'household.',
    },
    {
        'name': 'debt-minimums', 'display_name': 'Debt minimums',
        'kind': 'survival', 'sort_order': 70, 'required': False,
        'term_name': 'cost-debt-minimums-monthly',
        'guidance': 'The MINIMUM payments you cannot skip without '
                    'penalty: student loans, credit card minimums, '
                    'medical debt plans.',
        'examples': 'student loan payment, card minimum, medical '
                    'payment plan',
        'description': 'Contractually unavoidable this month.',
    },
    {
        'name': 'uncancellable-subscriptions',
        'display_name': 'Uncancellable subscriptions',
        'kind': 'pseudo-tax', 'sort_order': 80, 'required': False,
        'term_name': 'cost-uncancellable-subscriptions-monthly',
        'guidance': 'Go through the month\'s recurring charges and '
                    'pick the ones you have TRIED to cancel and '
                    'could not (dark-pattern cancellation flows, '
                    'contract lock-ins, fees to leave) — or that a '
                    'service you cannot practically live without '
                    'forces on you.',
        'examples': 'gym contract with buyout clause, bundled '
                    'services you cannot unbundle, cancellation-fee '
                    'lock-ins',
        'description': 'Recurring charges you cannot practically '
                       'escape. Classified pseudo-tax here — the '
                       'framing that corporate practice makes these '
                       'a private tax. The classification is this '
                       "row's kind knob: contestable, editable, "
                       'group-votable (scr-8/13).',
    },
]

#: Two demo households in texas, march 2022 (q1 frame exists).
SEED_SURVIVAL_PROFILES = [
    {
        'name': 'household-demo-citizen-jane-q1-2022',
        'contributed_by': 'demo-citizen-jane',
        'location_context': 'state-texas',
        'month_context': 'q1-2022',
        'household_size': 3, 'workers': 2, 'cars_needed': 2,
        'entries_json': json.dumps({
            'housing': {'amount': 1450.0, 'notes': 'rent'},
            'utilities': {'amount': 280.0, 'notes': ''},
            'food': {'amount': 640.0, 'notes': ''},
            'transport-work': {'amount': 720.0,
                               'notes': '2 cars: payments+insurance'
                                        '+gas'},
            'healthcare': {'amount': 310.0, 'notes': ''},
            'childcare': {'amount': 850.0, 'notes': 'daycare'},
            'uncancellable-subscriptions':
                {'amount': 45.0, 'notes': 'gym contract w/ buyout'},
        }),
        'skipped_json': json.dumps(['debt-minimums']),
        'total_monthly': 4295.0,
    },
    {
        'name': 'household-demo-research-group-q1-2022',
        'contributed_by': 'demo-research-group',
        'location_context': 'state-texas',
        'month_context': 'q1-2022',
        'household_size': 1, 'workers': 1, 'cars_needed': 1,
        'entries_json': json.dumps({
            'housing': {'amount': 1050.0, 'notes': ''},
            'utilities': {'amount': 190.0, 'notes': ''},
            'food': {'amount': 380.0, 'notes': ''},
            'transport-work': {'amount': 410.0, 'notes': '1 car'},
            'healthcare': {'amount': 260.0, 'notes': ''},
            'debt-minimums': {'amount': 220.0,
                              'notes': 'student loan'},
            'uncancellable-subscriptions':
                {'amount': 30.0, 'notes': 'bundled ISP add-on'},
        }),
        'skipped_json': json.dumps(['childcare']),
        'total_monthly': 2540.0,
    },
]
