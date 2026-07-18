"""
@cross-cutting
@module scoring.dmv_col_seed
@tags @xc:bindings

DMV cost-of-living vocabulary (col-1 of
political-scorecard-node/DMV_COST_OF_LIVING_DATA_PLAN.md, Dustin
2026-07-16): the DC/Virginia/Maryland geography contexts + subjects,
the persona contexts (each carrying its PUMS-reproducible
definition), the obscure-factor ScoreTerms (housing longevity,
reported conditions, escape cost — every provenance names the exact
official product), the escape-cost/displacement extensions to the
scr-12a survival walkthrough, and the first LAW-AS-DATA values
(security-deposit caps cited to the official code hosts).

Provenance discipline: every quantitative row here is either a
STATUTORY CONSTANT cited to the official code host, or a VOCABULARY
row whose values arrive later through the API-profiler ingestion
(col-2/3) — no representative estimates, no invented numbers. The
one deliberate absence: Virginia has NO general cap on early-lease-
termination liability, so no VA value exists for
leasebreak-liability-cap — the gap IS the finding (see the term's
notes), never a fabricated number.

Idempotent-by-name, like every Polari seed.

@consumers
  - polariServer seed_pairs (wired by the main session, not here)
  - scoring.selftest_dmv_col
@see /OVERLAP_MAP.md
"""

import json

_PLAN = 'political-scorecard-node/DMV_COST_OF_LIVING_DATA_PLAN.md'

# --------------------------------------------------------------------
# Geography: contexts (location hierarchy) + subjects (jurisdiction).
# --------------------------------------------------------------------

#: key -> (display, state label, official geography note)
_DMV_JURISDICTIONS = {
    'dc': ('Washington, DC', 'District of Columbia',
           'District of Columbia (state-equivalent, FIPS 11)'),
    'va-arlington': ('Arlington County, VA', 'Virginia',
                     'Arlington County, Virginia (FIPS 51013)'),
    'va-alexandria': ('Alexandria City, VA', 'Virginia',
                      'Alexandria independent city, Virginia '
                      '(FIPS 51510)'),
    'va-fairfax': ('Fairfax County, VA', 'Virginia',
                   'Fairfax County, Virginia (FIPS 51059)'),
    'va-loudoun': ('Loudoun County, VA', 'Virginia',
                   'Loudoun County, Virginia (FIPS 51107)'),
    'va-prince-william': ('Prince William County, VA', 'Virginia',
                          'Prince William County, Virginia '
                          '(FIPS 51153)'),
    'md-montgomery': ('Montgomery County, MD', 'Maryland',
                      'Montgomery County, Maryland (FIPS 24031)'),
    'md-prince-georges': ("Prince George's County, MD", 'Maryland',
                          "Prince George's County, Maryland "
                          '(FIPS 24033)'),
    'md-frederick': ('Frederick County, MD', 'Maryland',
                     'Frederick County, Maryland (FIPS 24021)'),
    # col-2 alignment: dmvdata.DMV_JURISDICTIONS pulls these two as
    # well (Appendix C3 licensing jurisdictions) — the geography
    # vocabulary must cover every jurisdiction the pulls return.
    'md-howard': ('Howard County, MD', 'Maryland',
                  'Howard County, Maryland (FIPS 24027)'),
    'md-anne-arundel': ('Anne Arundel County, MD', 'Maryland',
                        'Anne Arundel County, Maryland '
                        '(FIPS 24003)'),
}

_VA_KEYS = [k for k in _DMV_JURISDICTIONS if k.startswith('va-')]
_MD_KEYS = [k for k in _DMV_JURISDICTIONS if k.startswith('md-')]

SEED_DMV_GEO_CONTEXTS = [
    {
        # The CBSA every federal metro product keys on (FMR area,
        # OEWS 47900, CPI, AHS oversample).
        'name': 'washington-msa-47900',
        'display_name': 'Washington-Arlington-Alexandria MSA',
        'context_type': 'location',
        'parent_name': 'country-usa',
        'value_json': json.dumps(
            {'granularity': 'metro', 'cbsa': '47900',
             'metro': 'Washington-Arlington-Alexandria, '
                      'DC-VA-MD-WV', 'country': 'USA'}),
        'notes': 'Census CBSA 47900 — the geography of OEWS/CPI/'
                 'AHS/FMR metro products.',
    },
    {
        # The plan's working region: DC + NoVA + MD suburbs (a
        # subset of the MSA — the MSA also reaches WV).
        'name': 'dmv-region',
        'display_name': 'DMV Region (DC + NoVA + MD suburbs)',
        'context_type': 'location',
        'parent_name': 'washington-msa-47900',
        'value_json': json.dumps(
            {'granularity': 'region',
             'jurisdictions': sorted(_DMV_JURISDICTIONS),
             'country': 'USA'}),
        'notes': f'The working rollup of {_PLAN} — 9 jurisdictions.',
    },
] + [
    {
        'name': key, 'display_name': display,
        'context_type': 'location',
        'parent_name': 'dmv-region',
        'value_json': json.dumps(
            {'granularity': 'county', 'county': display,
             'state': state, 'country': 'USA'}),
        'notes': official,
    }
    for key, (display, state, official) in _DMV_JURISDICTIONS.items()
]

SEED_DMV_SUBJECTS = [
    {'name': key, 'display_name': display, 'kind': 'jurisdiction',
     'description': f'{official} — DMV cost-of-living subject.'}
    for key, (display, _state, official) in _DMV_JURISDICTIONS.items()
]

#: Statute values below hold under current law — pinned to a year
#: timeframe so later amendments land as NEW values, never edits.
SEED_DMV_TIMEFRAMES = [
    {
        'name': 'year-2026', 'display_name': '2026',
        'context_type': 'timeframe',
        'value_json': json.dumps(
            {'start': '2026-01-01', 'end': '2026-12-31'}),
    },
]

# --------------------------------------------------------------------
# Personas: demographic contexts carrying PUMS-reproducible filters.
# --------------------------------------------------------------------

def _persona(name, display, definition, pums):
    return {
        'name': name, 'display_name': display,
        'context_type': 'demographic',
        'value_json': json.dumps({'persona': name, 'pums': pums}),
        'notes': f'{definition} (PUMS-cuttable: derivation '
                 f'reproducible from the filter in value_json; '
                 f'plan §2 of {_PLAN}).',
    }


SEED_PERSONA_CONTEXTS = [
    _persona('fresh-hs-graduate', 'Fresh high-school graduate',
             'age 18-21, high-school diploma no more than 2 years '
             'old, no degree, first-time full-time worker at '
             '10th-25th percentile wage',
             {'AGEP': '18-21', 'SCHL': 'HS diploma, no degree',
              'ESR': 'employed', 'WKHP': '>=35',
              'wage_percentile': '10-25 (OEWS 47900)'}),
    _persona('part-timer-2-roommates', 'Part-timer, 2 roommates',
             'part-time worker (<35h), 3-person nonfamily household '
             'sharing a 3BR at one third of gross rent',
             {'WKHP': '<35', 'RELSHIPP': '34 (housemate/roommate)',
              'household_size': 3, 'rent_share': 'GRNTP/3'}),
    _persona('part-timer-3-roommates', 'Part-timer, 3 roommates',
             'part-time worker (<35h), 4-person nonfamily household '
             'sharing a 4BR at one quarter of gross rent',
             {'WKHP': '<35', 'RELSHIPP': '34 (housemate/roommate)',
              'household_size': 4, 'rent_share': 'GRNTP/4'}),
    _persona('part-timer-4-roommates', 'Part-timer, 4 roommates',
             'part-time worker (<35h), 5-person nonfamily household '
             'sharing a 5BR at one fifth of gross rent',
             {'WKHP': '<35', 'RELSHIPP': '34 (housemate/roommate)',
              'household_size': 5, 'rent_share': 'GRNTP/5'}),
    _persona('single-fulltime-median', 'Single full-time worker '
             '(median entry wage)',
             '1-person household, full-time at area median wage for '
             'entry occupations',
             {'household_size': 1, 'WKHP': '>=35',
              'wage_percentile': '50 (OEWS 47900 entry '
                                 'occupations)'}),
    _persona('minimum-wage-fulltime', 'Minimum-wage full-time '
             'worker',
             '1-person household, jurisdiction minimum wage x 2080 '
             'hours — DC/MD/VA minimums DIFFER (official listing: '
             'https://www.dol.gov/agencies/whd/minimum-wage/state)',
             {'household_size': 1, 'WKHP': '>=35',
              'wage': 'jurisdiction minimum x 2080'}),
    _persona('young-family-starter', 'Young family (starter)',
             '2 adults + 1 child, one full-time + one part-time '
             'earner, 2BR unit',
             {'household': '2 adults 1 child',
              'WKHP': '>=35 and <35', 'bedrooms': 2}),
    _persona('fixed-income-senior', 'Fixed-income senior',
             '1-person household on the average Social Security '
             'benefit, 1BR unit',
             {'household_size': 1, 'income': 'SSA average benefit',
              'bedrooms': 1}),
]

# --------------------------------------------------------------------
# The obscure-factor terms (plan §5 + appendices A/B). Values arrive
# via the profiler (col-2/3); the two statutory terms get values HERE.
# --------------------------------------------------------------------

def _term(name, display, description, unit, is_positive, tags,
          provenance, value_type='rate', temporal=None, notes='',
          equivalent=()):
    row = {
        'name': name, 'display_name': display,
        'description': description,
        'category': 'housing', 'value_type': value_type,
        'unit': unit, 'is_positive': is_positive,
        'abstract_tags_json': json.dumps(tags),
        'provenance_id': provenance,
    }
    if temporal:
        row['temporal_json'] = json.dumps(temporal)
    if notes:
        row['notes'] = notes
    if equivalent:
        row['equivalent_terms_json'] = json.dumps(list(equivalent))
    return row


SEED_DMV_TERMS = [
    # -- longevity (deliberately CROSS-TREE tagged: housing +
    #    household-economics — depreciating housing capital — and
    #    labor-mobility where the plan says so) -------------------
    _term('housing-stock-median-age', 'Housing Stock Median Age',
          'Median age of the housing stock — how long the housing '
          'that people live in has lasted so far (long-lasting '
          'stock holds value; aging stock without upkeep decays '
          'into the inadequacy terms).',
          'years', False,
          ['housing', 'longevity', 'durability',
           'household-economics'],
          'Census ACS table B25035 (Median Year Structure Built), '
          'https://data.census.gov/table/ACSDT5Y2023.B25035',
          value_type='custom',
          temporal={'nature': 'stock', 'resample': 'last'}),
    _term('housing-inadequacy-rate', 'Housing Inadequacy Rate',
          'Share of occupied units severely or moderately '
          'inadequate per the official AHS ADEQUACY measure — how '
          'many households REPORT housing that fails basic '
          'standards.',
          '%', False,
          ['housing', 'living-conditions', 'longevity'],
          'Census/HUD American Housing Survey ADEQUACY variable — '
          'Washington metro is an AHS oversample; METRO-LEVEL ONLY '
          '(no county/tract), '
          'https://www.census.gov/programs-surveys/ahs.html',
          notes='Metro-level only — ACS deficiency terms are the '
                'small-area proxy (plan Appendix A4).'),
    _term('structural-problem-rate', 'Structural Problem Rate',
          'Share of units reporting structural problems (sagging '
          'roof ROOFSAG, water leaks LEAKO/LEAKI, crumbling '
          'foundation FNDCRUMB) — the leading indicator of how '
          'long the stock will keep lasting.',
          '%', False,
          ['housing', 'longevity', 'durability',
           'construction-quality', 'household-economics'],
          'Census/HUD AHS structural variables (ROOFSAG, ROOFSHIN, '
          'ROOFHOLE, LEAKO/LEAKI, FNDCRUMB), AHS Codebook 1997+',
          equivalent=('construction-quality-index',)),
    _term('demolition-turnover', 'Housing Loss / Turnover',
          'Units permanently lost (demolition/disaster) per HUD '
          'CINCH, with local raze permits as the jurisdiction '
          'signal — the end of a unit\'s longevity.',
          'units lost / 1,000 units', False,
          ['housing', 'longevity', 'supply'],
          'HUD CINCH (Components of Inventory Change), '
          'https://www.huduser.gov/portal/datasets/cinch.html + '
          'local raze/demolition permits (Open Data DC, '
          'dataMontgomery). NOTE: the federal demolition survey '
          '(C-45) was discontinued in the 1990s.',
          temporal={'nature': 'flow', 'resample': 'sum'}),
    # -- reported conditions ------------------------------------
    _term('overcrowding-rate', 'Overcrowding Rate',
          'Share of households with more than one occupant per '
          'room — the roommate-stacking distress signal.',
          '%', False,
          ['housing', 'living-conditions', 'crowding'],
          'Census ACS table B25014 (Tenure by Occupants per Room), '
          'https://data.census.gov/'),
    _term('plumbing-kitchen-deficiency-rate',
          'Plumbing/Kitchen Deficiency Rate',
          'Share of units lacking complete plumbing or kitchen '
          'facilities — the tract-level official proxy for poor '
          'living conditions.',
          '%', False,
          ['housing', 'living-conditions'],
          'Census ACS tables B25047-B25049 (plumbing) + '
          'B25051-B25053 (kitchen), https://data.census.gov/'),
    # -- price layer ---------------------------------------------
    _term('median-gross-rent', 'Median Gross Rent',
          'Median gross rent (rent + utilities), the ACS headline '
          'rent figure.',
          '$/month', False,
          ['housing', 'affordability', 'cost-of-living', 'rent'],
          'Census ACS table B25064, '
          'https://data.census.gov/table/ACSDT1Y2024.B25064'
          '?g=310XX00US47900',
          value_type='currency',
          temporal={'nature': 'stock', 'resample': 'mean'}),
    _term('rent-by-bedrooms', 'Median Gross Rent by Bedrooms',
          'Median gross rent by bedroom count — the roommate-math '
          'table (an N-roommate share is rent(N BR)/N).',
          '$/month', False,
          ['housing', 'rent', 'roommates', 'cost-of-living'],
          'Census ACS table B25031, https://data.census.gov/',
          value_type='currency'),
    _term('rent-burden-severe-share', 'Severe Rent Burden Share',
          'Share of renter households paying 50% or more of income '
          'in gross rent.',
          '%', False,
          ['housing', 'affordability', 'renters',
           'cost-of-living'],
          'Census ACS table B25070 (50%+ bracket), '
          'https://data.census.gov/',
          equivalent=('rent-burden-rate',)),
    _term('fair-market-rent-2br', 'Fair Market Rent (2BR)',
          'HUD 40th-percentile gross rent for a 2-bedroom unit in '
          'the Washington-Arlington-Alexandria HUD Metro FMR Area — '
          'the official "modest rent" benchmark.',
          '$/month', False,
          ['housing', 'rent', 'affordability'],
          'HUD Fair Market Rents FY2026, '
          'https://www.huduser.gov/portal/datasets/fmr.html',
          value_type='currency'),
    _term('entry-wage-p10', 'Entry Wage (10th percentile)',
          '10th-percentile hourly wage across occupations in metro '
          '47900 — the fresh-graduate/entry-level earning line the '
          'personas divide their costs by.',
          '$/hour', True,
          ['wages', 'employment', 'labor-mobility',
           'cost-of-living'],
          'BLS OEWS area 47900, '
          'https://www.bls.gov/oes/current/oes_47900.htm',
          value_type='currency'),
    # -- escape cost (law-as-data) -------------------------------
    _term('security-deposit-cap-months', 'Security Deposit Cap',
          'Statutory maximum security deposit, in months of rent — '
          'a direct, citable component of what it costs to LEAVE '
          'one rental for another (the new unit\'s deposit is due '
          'before the old one returns).',
          'months of rent', False,
          ['housing', 'escape-cost', 'tenant-law',
           'labor-mobility', 'cost-of-living'],
          'Statutory constants — per-jurisdiction citations ride '
          'each value row (DC Code / MD Real Property / VA Code).',
          value_type='ratio',
          temporal={'nature': 'stock', 'resample': 'last'}),
    _term('leasebreak-liability-cap', 'Lease-Break Liability Cap',
          'Statutory cap on what a tenant owes to terminate a '
          'lease early, in months of rent. NO GENERAL CAP EXISTS '
          'in DC, Maryland, or Virginia — only narrow carve-outs '
          '(MD military transfer: rent due + 30 days, RP §8-212.1; '
          'DV-victim terminations DC §42-3505.07 / VA §55.1-1236 / '
          'MD RP Title 8 Sub 5A).',
          'months of rent', False,
          ['housing', 'escape-cost', 'tenant-law',
           'labor-mobility'],
          'Statutory review 2026-07-16 (plan Appendix C4): '
          'VA Code §55.1-1226/-1235/-1236, MD RP §8-212.1, '
          'DC Code §42-3505.07.',
          notes='DELIBERATELY NO general-cap values seeded: none '
                'exist in statute for any DMV jurisdiction — '
                'Virginia\'s uncapped early-termination liability '
                'is the region\'s worst escape-cost exposure, and '
                'that GAP is the finding. Carve-outs are recorded '
                'here in the description, never as general values.'),
    _term('escape-cost-estimate', 'Escape Cost (estimate)',
          'Estimated one-time cost to escape a bad rental: '
          'statutory lease-break exposure + new unit deposit '
          '(security-deposit-cap-months x rent) + first month at '
          'FMR + movers. The FORMULA is a votable criterion '
          '(mechanism C) — this term holds its outputs.',
          '$', False,
          ['housing', 'escape-cost', 'cost-of-living',
           'labor-mobility', 'household-economics'],
          'Derived from statutory terms + HUD FMR (plan §5.4) — '
          'provenance on each value names the formula version.',
          value_type='currency'),
]

# --------------------------------------------------------------------
# scr-12a walkthrough extensions: the escape-cost reserve and
# displacement risk as CostCategories (+ their term-per-category
# rows, matching survival_costs' _cost_term idiom exactly).
# --------------------------------------------------------------------

SEED_ESCAPE_COST_TERMS = [
    {
        'name': 'cost-escape-reserve-monthly',
        'display_name': 'Escape reserve (monthly cost)',
        'description': 'Household monthly escape-reserve set-aside '
                       'from the survival-cost walkthrough.',
        'category': 'cost-of-living', 'value_type': 'currency',
        'unit': '$/month', 'is_positive': False,
        'temporal_json': json.dumps(
            {'nature': 'flow', 'resample': 'sum'}),
        'abstract_tags_json': json.dumps(
            ['housing', 'escape-cost', 'cost-of-living']),
        'provenance_id': 'col-1 DMV escape-cost vocabulary',
    },
    {
        'name': 'cost-displacement-monthly',
        'display_name': 'Displacement exposure (monthly cost)',
        'description': 'Household monthly displacement-exposure '
                       'outlay from the survival-cost walkthrough.',
        'category': 'cost-of-living', 'value_type': 'currency',
        'unit': '$/month', 'is_positive': False,
        'temporal_json': json.dumps(
            {'nature': 'flow', 'resample': 'sum'}),
        'abstract_tags_json': json.dumps(
            ['housing', 'displacement', 'cost-of-living']),
        'provenance_id': 'col-1 DMV escape-cost vocabulary',
    },
]

SEED_ESCAPE_COST_CATEGORIES = [
    {
        'name': 'escape-cost-reserve',
        'display_name': 'Escape reserve',
        'kind': 'survival', 'sort_order': 85, 'required': False,
        'term_name': 'cost-escape-reserve-monthly',
        'guidance': 'The ability to LEAVE is part of the cost of '
                    'living somewhere. Divide what it would cost '
                    'you to move out this year by 12: any early-'
                    'termination amount your lease names, plus a '
                    'new unit\'s security deposit and first month, '
                    'plus movers.',
        'examples': 'lease early-termination fee, new security '
                    'deposit, first month at the new place, moving '
                    'truck or movers',
        'description': 'What it costs to be ABLE to leave.',
    },
    {
        'name': 'displacement-risk',
        'display_name': 'Displacement exposure',
        'kind': 'survival', 'sort_order': 86, 'required': False,
        'term_name': 'cost-displacement-monthly',
        'guidance': 'Same month, same calendar: anything you paid '
                    'because staying was at risk — late fees on '
                    'rent, court or filing costs from an eviction '
                    'filing, costs of documenting bad conditions '
                    '(inspections, certified letters).',
        'examples': 'rent late fees, eviction-filing court costs, '
                    'inspection or documentation costs for '
                    'condition complaints',
        'description': 'What being at risk of losing housing '
                       'already costs.',
    },
]

# --------------------------------------------------------------------
# Law-as-data: the first statutory values (deposit caps), cited to
# the OFFICIAL code hosts. VA=2 months, MD=1 month, DC=1 month.
# --------------------------------------------------------------------

_DEPOSIT_CAPS = (
    [('dc', 1.0,
      'DC Code §42-3502.17 (max one month, 45-day return + '
      'interest), https://code.dccouncil.gov/us/dc/council/code/'
      'sections/42-3502.17')]
    + [(key, 1.0,
        'MD Real Property §8-203 (max ONE month post-2024 Renters\' '
        'Rights and Stabilization Act; 45-day return; treble '
        'damages), https://mgaleg.maryland.gov/mgawebsite/Laws/'
        'StatuteText?article=grp&section=8-203&enactments=false')
       for key in _MD_KEYS]
    + [(key, 2.0,
        'VA Code §55.1-1226 (max TWO months\' rent, 45-day '
        'return), https://law.lis.virginia.gov/vacode/title55.1/'
        'chapter12/section55.1-1226/')
       for key in _VA_KEYS]
)

SEED_STATUTE_VALUES = [
    {
        'name': f'security-deposit-cap-months@{key}-2026',
        'term_name': 'security-deposit-cap-months',
        'subject_name': key,
        'context_names_json': json.dumps([key, 'year-2026']),
        'pre_normalized_value': months,
        'source': 'official statute (law-as-data)',
        'provenance_id': citation,
    }
    for key, months, citation in _DEPOSIT_CAPS
]
