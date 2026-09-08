"""
@cross-cutting
@module scoring.survival_costs_basis
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
# sap-2c INDEX (design §7): the classes live one-per-file under objects/survival_costs/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

import json
from objectTreeDecorators import treeObject, treeObjectInit
from scoring.scoring_basis import ContextualizedValue, ScoreSubject

from scoring.objects.survival_costs._shared import CATEGORY_KINDS, SEED_COST_CATEGORIES, SEED_COST_TERMS, SEED_SURVIVAL_PROFILES, SMALL_SAMPLE, _by_name, _categories, _cost_term, _parse, _rows, survival_report, survival_walkthrough  # noqa: F401
from scoring.objects.survival_costs.CostCategory import CostCategory  # noqa: F401
from scoring.objects.survival_costs.SurvivalCostProfile import SurvivalCostProfile  # noqa: F401

from scoring.scoring_basis import ContextualizedValue, ScoreSubject
import json

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
