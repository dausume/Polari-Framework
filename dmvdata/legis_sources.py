"""
@module dmvdata.legis_sources

Legislative-body API registrations (Dustin 2026-07-16: legislation
"should be retrieved from public apis if possible"). Kept OUT of
source_seed.py — this is the LEGISLATION intake, a different concern
from the cost-of-living statistics intake.

What actually exists per body (web-verified 2026-07-16):
  * Congress.gov API v3 (Library of Congress) — REAL, key required
    (free Data.gov signup, 5000 req/hr): /v3/bill, /v3/member, and
    /v3/house-vote roll calls incl. the member-votes level (who
    voted yes/no — exactly the roster LegislativeVoteEvent stores).
  * Virginia LIS — REAL developers portal (lis.virginia.gov/
    developers), 40+ APIs incl. Legislation and Person, key by
    registration.
  * DC LIMS — an API base responds at lims.dccouncil.gov/api, but
    endpoint documentation is sparse/legacy; registered
    reference-only (persistData=False) until col-3 verifies routes.
  * Maryland General Assembly — NO official public API or bulk
    download found; mgaleg.maryland.gov registered reference-only
    with that stated honestly (third-party aggregators exist but
    are out of scope — official sources only).

Auth discipline: env-knob pointers only ('env:<VAR>'), never literal
keys — repos are PUBLIC.

@consumers
  - polariServer (registration + seed, wired by the main session)
  - scoring.legislation (the rows these APIs would populate)
"""

SEED_LEGIS_DOMAINS = [
    {'name': 'congress-gov-api',
     'displayName': 'Congress.gov API (Library of Congress)',
     'host': 'api.congress.gov', 'protocol': 'https',
     'description': 'Official federal legislation API v3: bills, '
                    'members, House roll-call votes. Key via env '
                    'POLARI_CONGRESS_API_KEY (free Data.gov '
                    'signup, 5000 req/hr).',
     'tags': ['official', 'federal', 'legislation']},
    {'name': 'dc-lims',
     'displayName': 'DC Council LIMS',
     'host': 'lims.dccouncil.gov', 'protocol': 'https',
     'description': 'DC Legislation Information Management System '
                    '(every Council measure since 1989). An API '
                    'base responds at /api but endpoint docs are '
                    'sparse — verify routes before persisted '
                    'pulls.',
     'tags': ['official', 'dc', 'legislation']},
    {'name': 'va-lis',
     'displayName': 'Virginia Legislative Information System',
     'host': 'lis.virginia.gov', 'protocol': 'https',
     'description': 'VA General Assembly bills, votes, members. '
                    'REAL developer portal (/developers, 40+ APIs); '
                    'key by registration via env '
                    'POLARI_VA_LIS_API_KEY.',
     'tags': ['official', 'virginia', 'legislation']},
    {'name': 'md-mga',
     'displayName': 'Maryland General Assembly website',
     'host': 'mgaleg.maryland.gov', 'protocol': 'https',
     'description': 'MD legislation/votes — NO official public API '
                    'or bulk download exists (verified 2026-07-16); '
                    'reference + manual-entry evidence source only.',
     'tags': ['official', 'maryland', 'legislation',
              'reference-only']},
]

SEED_LEGIS_ENDPOINTS = [
    {'name': 'congress-bills',
     'displayName': 'Congress.gov bills (list by congress/type)',
     'domainName': 'congress-gov-api',
     'endpointPath': '/v3/bill/119/hr?format=json',
     'httpMethod': 'GET',
     'description': 'Bill list level — feeds LegislationRecord '
                    'rows (entry_mode api). Docs: '
                    'https://github.com/LibraryOfCongress/'
                    'api.congress.gov',
     'persistData': True, 'polariClassName': 'LegislationRecord',
     'authType': 'apikey',
     'authConfig': 'env:POLARI_CONGRESS_API_KEY'},
    {'name': 'congress-members',
     'displayName': 'Congress.gov members',
     'domainName': 'congress-gov-api',
     'endpointPath': '/v3/member?format=json',
     'httpMethod': 'GET',
     'description': 'Member roster (BioGuide ids) — feeds '
                    'legislator ScoreSubject rows.',
     'persistData': True, 'polariClassName': 'ScoreSubject',
     'authType': 'apikey',
     'authConfig': 'env:POLARI_CONGRESS_API_KEY'},
    {'name': 'congress-house-votes',
     'displayName': 'Congress.gov House roll-call votes',
     'domainName': 'congress-gov-api',
     'endpointPath': '/v3/house-vote/119?format=json',
     'httpMethod': 'GET',
     'description': 'Roll calls incl. the MEMBER-VOTES level (who '
                    'voted yes/no) — feeds LegislativeVoteEvent '
                    'rosters (entry_mode api).',
     'persistData': True,
     'polariClassName': 'LegislativeVoteEvent',
     'authType': 'apikey',
     'authConfig': 'env:POLARI_CONGRESS_API_KEY'},
    {'name': 'va-lis-legislation',
     'displayName': 'Virginia LIS Legislation API',
     'domainName': 'va-lis',
     'endpointPath': '/developers/Legislation',
     'httpMethod': 'GET',
     'description': 'VA bills/resolutions API (portal-documented; '
                    'exact REST path issued with the API key '
                    'registration).',
     'persistData': True, 'polariClassName': 'LegislationRecord',
     'authType': 'apikey', 'authConfig': 'env:POLARI_VA_LIS_API_KEY'},
    {'name': 'dc-lims-api',
     'displayName': 'DC LIMS API base',
     'domainName': 'dc-lims', 'endpointPath': '/api',
     'httpMethod': 'GET',
     'description': 'API base responds; endpoint docs sparse — '
                    'reference-only until routes verified '
                    '(col-3).',
     'persistData': False, 'polariClassName': '',
     'authType': 'none', 'authConfig': ''},
    {'name': 'md-mga-site',
     'displayName': 'Maryland General Assembly (reference only)',
     'domainName': 'md-mga',
     'endpointPath': '/mgawebsite/Search/Legislation',
     'httpMethod': 'GET',
     'description': 'NO official API/bulk exists — evidence URLs '
                    'for MANUAL legislation entry come from here.',
     'persistData': False, 'polariClassName': '',
     'authType': 'none', 'authConfig': ''},
]

#: GovSource-shaped dicts (the acronym glossary rows) — wired by the
#: main session into SEED_GOV_SOURCES' class tuple.
SEED_LEGIS_GOV_SOURCES = [
    {'name': 'congress-gov', 'acronym': '',
     'full_name': 'Congress.gov',
     'agency': 'Library of Congress', 'parent_source': '',
     'jurisdiction': 'federal',
     'official_website': 'https://www.congress.gov',
     'data_portal_url': 'https://api.congress.gov/',
     'requires_api_key': True,
     'api_key_env': 'POLARI_CONGRESS_API_KEY',
     'api_endpoint_names_json': '["congress-bills", '
                                '"congress-members", '
                                '"congress-house-votes"]',
     'description': 'Official federal legislative information '
                    'system: bills, members, roll-call votes '
                    '(API v3).'},
    {'name': 'dc-lims', 'acronym': 'LIMS',
     'full_name': 'Legislation Information Management System',
     'agency': 'Council of the District of Columbia',
     'parent_source': '', 'jurisdiction': 'dc',
     'official_website': 'https://lims.dccouncil.gov/',
     'data_portal_url': 'https://lims.dccouncil.gov/api',
     'requires_api_key': False, 'api_key_env': '',
     'api_endpoint_names_json': '["dc-lims-api"]',
     'description': 'Every DC Council measure since 1989; API '
                    'endpoint docs sparse (reference-only for '
                    'now).'},
    {'name': 'va-lis', 'acronym': 'LIS',
     'full_name': 'Legislative Information System',
     'agency': 'Virginia Division of Legislative Automated '
               'Systems',
     'parent_source': '', 'jurisdiction': 'virginia',
     'official_website': 'https://lis.virginia.gov/',
     'data_portal_url': 'https://lis.virginia.gov/developers',
     'requires_api_key': True,
     'api_key_env': 'POLARI_VA_LIS_API_KEY',
     'api_endpoint_names_json': '["va-lis-legislation"]',
     'description': 'VA General Assembly bills/votes/members — '
                    '40+ documented APIs, key by registration.'},
    {'name': 'md-mga', 'acronym': 'MGA',
     'full_name': 'Maryland General Assembly',
     'agency': 'Maryland General Assembly', 'parent_source': '',
     'jurisdiction': 'maryland',
     'official_website': 'https://mgaleg.maryland.gov',
     'data_portal_url': '',
     'requires_api_key': False, 'api_key_env': '',
     'api_endpoint_names_json': '["md-mga-site"]',
     'description': 'MD legislation/votes; NO official public API '
                    'or bulk download (verified 2026-07-16) — '
                    'manual-entry evidence source.'},
]
