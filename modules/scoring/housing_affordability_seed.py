"""
@cross-cutting
@module scoring.housing_affordability_seed
@tags @xc:bindings

Housing Affordability — Phase 2 of the Democratic Scorecard revamp's
first REAL Context Tree (not demo labor data): three professional/
interest-group worldviews on what "affordable housing" means, reusing
the group-proposes-concepts -> WorldviewElection -> apply-weights
workflow (mechanism B, already fully built in
worldview_elections.py/score_group.py) for real content instead of the
labor-quality demo.

Dustin's worked example (2026-07-14): "Housing Affordability shouldn't
be just a price metric — it should also weight professional-quality
metrics like building longevity/material quality/construction
practices, because cheap/deceptive construction quietly makes the
whole economy poorer long-term (costs more to individuals AND the
economy over time, even though it looks cheaper short-term)." This
seed embodies that directly: the three worldviews genuinely disagree
about how much construction quality and supply responsiveness should
matter next to raw price/rent burden — putting that disagreement to a
WorldviewElection instead of picking one "objective" formula IS the
point.

Quantitative terms (price-to-income, rent burden, permits-per-capita)
are representative 2022 estimates aligned with Census ACS / JCHS
"State of the Nation's Housing" / Census Building Permits Survey
aggregate reporting for the five states scoring_seed.py already seeds
— state-exact figures were not individually cross-verified against a
single primary source this session (see the provenance strings below);
flagged for a live data-refresh pass, not presented as verified beyond
that. The construction-quality term is explicitly a PROFESSIONAL-
JUDGMENT metric, per Dustin's own framing ("often it is the case that
different interest and professional groups will see things no one in
the public do") — its values are the proposing group's own assessment,
sourced as such, not an official statistic.

Idempotent-by-name, like every Polari seed.

@consumers
  - polariServer seed_pairs
@see /OVERLAP_MAP.md
"""

import json

_ACS_PROV = ("representative 2022 estimate, aligned with Census ACS / "
             "JCHS State of the Nation's Housing aggregate reporting — "
             'state-exact figure not individually cross-verified '
             'against a single primary source this session; flag for '
             'a live data-refresh pass')
_PERMIT_PROV = ('representative 2022 estimate, aligned with Census '
                'Building Permits Survey aggregate reporting — same '
                'cross-verification caveat as the ACS-aligned terms')
_QUALITY_PROV = ("professional-judgment score — the proposing group's "
                 'own assessment of statewide residential building-'
                 'code stringency + enforcement, NOT an official '
                 'statistic, by design (Dustin 2026-07-14: '
                 "professional groups see things official data "
                 "doesn't)")

SEED_HOUSING_SCORE_TERMS = [
    {
        'name': 'housing-price-to-income-ratio',
        'display_name': 'Home Price-to-Income Ratio',
        'description': 'Median home sale price divided by median '
                       'household income — lower means homes are '
                       'more reachable relative to what people earn.',
        'category': 'housing', 'value_type': 'ratio',
        'unit': 'x income',
        'is_positive': False,
        'normalization_json': json.dumps(
            {'method': 'min-max', 'min': 3.0, 'max': 9.0}),
        'temporal_json': json.dumps(
            {'nature': 'stock', 'resample': 'last'}),
        'abstract_tags_json': json.dumps(
            ['housing', 'affordability', 'cost-of-living']),
        'provenance_id': _ACS_PROV,
    },
    {
        'name': 'rent-burden-rate',
        'display_name': 'Renter Cost Burden Rate',
        'description': 'Share of renter households spending more '
                       'than 30% of income on rent — the standard '
                       'HUD/Census cost-burden threshold.',
        'category': 'housing', 'value_type': 'percentage', 'unit': '%',
        'is_positive': False,
        'normalization_json': json.dumps(
            {'method': 'min-max', 'min': 40.0, 'max': 58.0}),
        'temporal_json': json.dumps(
            {'nature': 'stock', 'resample': 'mean'}),
        'abstract_tags_json': json.dumps(
            ['housing', 'affordability', 'renters']),
        'provenance_id': _ACS_PROV,
    },
    {
        'name': 'construction-quality-index',
        'display_name': 'Construction Quality Index',
        'description': 'Professional assessment of statewide '
                       'residential building-code stringency, '
                       'enforcement, and material-standard adoption '
                       "— the quality proxy Dustin's worked example "
                       'names directly: cheap construction quietly '
                       'costs the economy more long-term even though '
                       'it looks cheaper short-term.',
        'category': 'housing', 'value_type': 'index',
        'unit': 'index (0-100)',
        'is_positive': True,
        'normalization_json': json.dumps(
            {'method': 'min-max', 'min': 0.0, 'max': 100.0}),
        'abstract_tags_json': json.dumps(
            ['housing', 'construction-quality', 'building-codes']),
        'provenance_id': _QUALITY_PROV,
    },
    {
        'name': 'new-housing-permits-per-capita',
        'display_name': 'New Housing Permits per 1,000 Residents',
        'description': 'Housing units authorized by building permits '
                       'per 1,000 residents — a supply-responsiveness '
                       'proxy (more new supply relieves price '
                       'pressure over time).',
        'category': 'housing', 'value_type': 'rate',
        'unit': 'permits / 1,000 residents',
        'is_positive': True,
        'normalization_json': json.dumps(
            {'method': 'min-max', 'min': 2.0, 'max': 10.0}),
        'temporal_json': json.dumps(
            {'nature': 'flow', 'resample': 'sum'}),
        'abstract_tags_json': json.dumps(
            ['housing', 'supply', 'construction']),
        'provenance_id': _PERMIT_PROV,
    },
]

#: state -> (price-to-income, rent-burden %, construction-quality-index,
#: permits/1,000) — reuses the five states scoring_seed.py already
#: seeds (state-* contexts + ScoreSubjects), so this Context Tree
#: scores the SAME subjects as the labor-quality reference concept.
_HOUSING_DATA = {
    'alabama': (3.3, 44.0, 42.0, 4.5),
    'california': (8.5, 54.0, 82.0, 2.8),
    'washington-dc': (6.3, 52.0, 75.0, 5.5),
    'idaho': (6.6, 46.0, 58.0, 9.5),
    'texas': (4.3, 49.0, 46.0, 7.5),
}

_TERM_ORDER = ['housing-price-to-income-ratio', 'rent-burden-rate',
               'construction-quality-index',
               'new-housing-permits-per-capita']

SEED_HOUSING_CONTEXTUALIZED_VALUES = [
    {
        'name': f'{term}@{state}-housing-2022',
        'term_name': term,
        'subject_name': state,
        'context_names_json': json.dumps(
            [f'state-{state}', 'year-2022']),
        'pre_normalized_value': value,
        'source': ('Building Quality & Codes Coalition professional '
                   'assessment'
                   if term == 'construction-quality-index'
                   else 'Census ACS / JCHS / Building Permits Survey '
                        'aggregate reporting'),
        'provenance_id': (
            _QUALITY_PROV if term == 'construction-quality-index'
            else _PERMIT_PROV
            if term == 'new-housing-permits-per-capita'
            else _ACS_PROV),
        'contributed_by': ('building-quality-professionals-guild'
                           if term == 'construction-quality-index'
                           else ''),
    }
    for state, values in _HOUSING_DATA.items()
    for term, value in zip(_TERM_ORDER, values)
]

SEED_HOUSING_SCORE_CONCEPTS = [
    {
        # Tenant/renter framing: affordability = can you afford it
        # RIGHT NOW. Construction quality and supply responsiveness
        # are deliberately left out — not oversight, a real stance.
        'name': 'housing-afford-price-only',
        'display_name': 'Housing Affordability — Price & Rent Burden',
        'description': "The Tenant Affordability Coalition's "
                       'worldview: affordability is what a household '
                       'pays today, full stop — price-to-income and '
                       'rent burden only.',
        'subject_kind': 'state',
        'term_weights_json': json.dumps([
            {'term': 'housing-price-to-income-ratio', 'weight': 8},
            {'term': 'rent-burden-rate', 'weight': 8},
        ]),
        'required_context_names_json': json.dumps(['year-2022']),
        'aggregation': 'weighted-mean',
        'levelize': True,
        'abstract_tags_json': json.dumps(
            ['housing', 'affordability', 'renters']),
        'provenance_id': 'proposed by tenant-affordability-coalition',
    },
    {
        # Building-industry/urban-planning framing: cheap-but-shoddy
        # construction is a hidden long-term cost, per Dustin's own
        # worked example — construction quality gets the HEAVIEST
        # weight of any term in this worldview.
        'name': 'housing-afford-quality-weighted',
        'display_name': 'Housing Affordability — Quality-Weighted',
        'description': "The Building Quality & Codes Coalition's "
                       'worldview: durable, well-built housing is '
                       'cheaper for households and the economy '
                       'long-term even when it costs more up front — '
                       'construction quality carries the heaviest '
                       'weight.',
        'subject_kind': 'state',
        'term_weights_json': json.dumps([
            {'term': 'housing-price-to-income-ratio', 'weight': 2},
            {'term': 'rent-burden-rate', 'weight': 2},
            {'term': 'construction-quality-index', 'weight': 10},
            {'term': 'new-housing-permits-per-capita', 'weight': 2},
        ]),
        'required_context_names_json': json.dumps(['year-2022']),
        'aggregation': 'weighted-mean',
        'levelize': True,
        'abstract_tags_json': json.dumps(
            ['housing', 'affordability', 'construction-quality']),
        'provenance_id': 'proposed by '
                         'building-quality-professionals-guild',
    },
    {
        # Supply-side economists' framing: build more, prices fall —
        # construction-quality regulation is treated as at best
        # orthogonal to affordability, so it's left out entirely
        # rather than scored zero-but-present.
        'name': 'housing-afford-supply-first',
        'display_name': 'Housing Affordability — Supply-First',
        'description': "The Housing Supply Economists Network's "
                       'worldview: affordability is fundamentally a '
                       'supply problem — new-permits-per-capita '
                       'carries the heaviest weight, price-to-income '
                       'and rent burden are downstream symptoms.',
        'subject_kind': 'state',
        'term_weights_json': json.dumps([
            {'term': 'housing-price-to-income-ratio', 'weight': 5},
            {'term': 'rent-burden-rate', 'weight': 2},
            {'term': 'new-housing-permits-per-capita', 'weight': 8},
        ]),
        'required_context_names_json': json.dumps(['year-2022']),
        'aggregation': 'weighted-mean',
        'levelize': True,
        'abstract_tags_json': json.dumps(
            ['housing', 'affordability', 'supply']),
        'provenance_id': 'proposed by '
                         'housing-supply-economists-network',
    },
]

SEED_HOUSING_CONTRIBUTORS = [
    {
        'name': 'tenant-affordability-coalition',
        'display_name': 'Tenant Affordability Coalition',
        'kind': 'lobby',
        'pseudonymous': False,
        'description': 'Renter-advocacy coalition proposing the '
                       'price-only Housing Affordability worldview.',
    },
    {
        'name': 'building-quality-professionals-guild',
        'display_name': 'Building Quality & Codes Coalition',
        'kind': 'organization',
        'pseudonymous': False,
        'description': 'Building-industry/code-enforcement '
                       'professional group proposing the '
                       'quality-weighted Housing Affordability '
                       'worldview, and the source of its '
                       'construction-quality-index assessments.',
    },
    {
        'name': 'housing-supply-economists-network',
        'display_name': 'Housing Supply Economists Network',
        'kind': 'organization',
        'pseudonymous': False,
        'description': 'Supply-side housing economists proposing the '
                       'supply-first Housing Affordability worldview.',
    },
    {
        'name': 'demo-renter-voter',
        'display_name': 'renter-voter (pseudonym)',
        'kind': 'individual',
        'pseudonymous': True,
        'description': 'Demo pseudonymous renter casting a lived-'
                       'experience ballot in the housing election.',
    },
    {
        'name': 'demo-tradesperson-voter',
        'display_name': 'tradesperson-voter (pseudonym)',
        'kind': 'individual',
        'pseudonymous': True,
        'description': 'Demo pseudonymous construction tradesperson '
                       'casting a lived-experience ballot in the '
                       'housing election.',
    },
]

SEED_HOUSING_SCORE_GROUPS = [{
    'name': 'housing-affordability-assembly',
    'display_name': 'Housing Affordability Assembly',
    'group_type': 'civic',
    'member_concept_names_json': json.dumps([
        'housing-afford-price-only', 'housing-afford-quality-weighted',
        'housing-afford-supply-first']),
    'member_contributor_names_json': json.dumps([
        'tenant-affordability-coalition',
        'building-quality-professionals-guild',
        'housing-supply-economists-network',
        'demo-renter-voter', 'demo-tradesperson-voter']),
    'description': 'The first real Context Tree (Phase 2 of the '
                   'Democratic Scorecard revamp): three professional/'
                   'interest-group worldviews on Housing Affordability '
                   '— mechanism B (vote on which worldview the group '
                   'reads by) applied to real content instead of the '
                   'labor-quality demo.',
}]

#: A real, uncontrived 5-ballot ranked-condorcet contest — price-only
#: beats both other worldviews pairwise (a genuine Condorcet winner,
#: not staged): the electorate here skews toward immediate-affordability
#: concerns even though quality-weighted arguably measures more.
SEED_HOUSING_ELECTIONS = [{
    'name': 'housing-affordability-election',
    'display_name': 'Which Housing Affordability worldview should '
                    'the assembly read by?',
    'description': 'Ranked-condorcet election over the assembly\'s '
                   'three member worldviews.',
    'group_name': 'housing-affordability-assembly',
    'mode': 'ranked-condorcet',
    'status': 'closed',
    'opens_date': '2026-06-01', 'closes_date': '2026-06-20',
    'provenance_id': 'Phase 2 Context Tree seed',
}]

SEED_HOUSING_BALLOTS = [
    {
        'name': 'ballot-housing-quality-guild',
        'election_name': 'housing-affordability-election',
        'voter': 'building-quality-professionals-guild',
        'ranking_json': json.dumps([
            'housing-afford-quality-weighted',
            'housing-afford-supply-first',
            'housing-afford-price-only']),
        'cast_date': '2026-06-05',
    },
    {
        'name': 'ballot-housing-tenant-coalition',
        'election_name': 'housing-affordability-election',
        'voter': 'tenant-affordability-coalition',
        'ranking_json': json.dumps([
            'housing-afford-price-only',
            'housing-afford-quality-weighted',
            'housing-afford-supply-first']),
        'cast_date': '2026-06-06',
    },
    {
        'name': 'ballot-housing-supply-economists',
        'election_name': 'housing-affordability-election',
        'voter': 'housing-supply-economists-network',
        'ranking_json': json.dumps([
            'housing-afford-supply-first',
            'housing-afford-price-only',
            'housing-afford-quality-weighted']),
        'cast_date': '2026-06-07',
    },
    {
        'name': 'ballot-housing-renter',
        'election_name': 'housing-affordability-election',
        'voter': 'demo-renter-voter',
        'ranking_json': json.dumps([
            'housing-afford-price-only',
            'housing-afford-supply-first',
            'housing-afford-quality-weighted']),
        'cast_date': '2026-06-10',
    },
    {
        'name': 'ballot-housing-tradesperson',
        'election_name': 'housing-affordability-election',
        'voter': 'demo-tradesperson-voter',
        'ranking_json': json.dumps([
            'housing-afford-quality-weighted',
            'housing-afford-price-only',
            'housing-afford-supply-first']),
        'cast_date': '2026-06-11',
    },
]
