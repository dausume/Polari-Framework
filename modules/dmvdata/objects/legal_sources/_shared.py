"""@module dmvdata.objects.legal_sources._shared — what the legal_sources row classes share (constants, seeds, helpers); split from legal_sources_basis.py (sap-2c)."""

POLITICAL_GROUP_KINDS = ('party', 'pac', 'campaign', 'advocacy')
_NOT_OFFICIAL = ('NOT an official government source — a '
                 'non-government proxy, framed as such wherever it '
                 'is cited.')
SEED_NONPROFIT_SOURCES = [
    {'name': 'legal-services-corp', 'short_name': 'LSC',
     'full_name': 'Legal Services Corporation',
     'official_website': 'https://www.lsc.gov',
     'data_portal_url': 'https://civilcourtdata.lsc.gov',
     'ein': '', 'irs_subsection': '',
     'state_registered': 'DC',
     'irs_lookup_url': 'https://apps.irs.gov/app/eos/',
     'funding_transparency_url': 'https://www.lsc.gov/about-lsc',
     'description': 'Congressionally chartered nonprofit; its Civil '
                    'Court Data Initiative is the plan\'s flagged '
                    'PROXY for bulk eviction data where courts '
                    'publish none. ' + _NOT_OFFICIAL,
     'notes': 'EIN/subsection not looked up — use the IRS lookup '
              'URL, never invent identifiers.'},
    {'name': 'eviction-lab', 'short_name': '',
     'full_name': 'Eviction Lab (Princeton University)',
     'official_website': 'https://evictionlab.org',
     'data_portal_url': 'https://evictionlab.org/get-the-data/',
     'ein': '', 'irs_subsection': '',
     'state_registered': 'NJ',
     'irs_lookup_url': 'https://apps.irs.gov/app/eos/',
     'funding_transparency_url': 'https://evictionlab.org/about/',
     'description': 'Academic research lab; regional eviction '
                    'compilations the plan excluded from official '
                    'sourcing. ' + _NOT_OFFICIAL,
     'notes': 'A university lab, not a standalone 501(c)(3) — '
              'legal identity is the university\'s.'},
    {'name': 'harvard-jchs', 'short_name': 'JCHS',
     'full_name': 'Joint Center for Housing Studies '
                  '(Harvard University)',
     'official_website': 'https://www.jchs.harvard.edu',
     'data_portal_url': 'https://www.jchs.harvard.edu/'
                        'state-nations-housing-report',
     'ein': '', 'irs_subsection': '',
     'state_registered': 'MA',
     'irs_lookup_url': 'https://apps.irs.gov/app/eos/',
     'funding_transparency_url': 'https://www.jchs.harvard.edu/'
                                 'about',
     'description': "Publishes 'State of the Nation's Housing' — "
                    'referenced by the housing-affordability seed '
                    'provenance. ' + _NOT_OFFICIAL,
     'notes': 'A university center — legal identity is the '
              'university\'s.'},
]
SEED_POLITICAL_SOURCES = [
    {'name': 'democratic-party-platform', 'short_name': 'DNC',
     'full_name': 'Democratic National Committee (party platform)',
     'official_website': 'https://democrats.org',
     'group_kind': 'party', 'fec_committee_id': '',
     'fec_lookup_url': 'https://www.fec.gov/data/committees/',
     'jurisdiction_scope': 'national',
     'description': 'Party platform as a POSITION source (a '
                    'position document, not an FEC filing and not '
                    'a statistic). ' + _NOT_OFFICIAL,
     'notes': 'FEC committee id not looked up — resolve via the '
              'FEC lookup URL.'},
    {'name': 'republican-party-platform', 'short_name': 'RNC',
     'full_name': 'Republican National Committee (party platform)',
     'official_website': 'https://gop.com',
     'group_kind': 'party', 'fec_committee_id': '',
     'fec_lookup_url': 'https://www.fec.gov/data/committees/',
     'jurisdiction_scope': 'national',
     'description': 'Party platform as a POSITION source (a '
                    'position document, not an FEC filing and not '
                    'a statistic). ' + _NOT_OFFICIAL,
     'notes': 'FEC committee id not looked up — resolve via the '
              'FEC lookup URL.'},
]
SEED_COMPANY_SOURCES = []
SEED_INDIVIDUAL_SOURCES = []
