"""@module dmvdata.objects.gov_sources._shared — what the gov_sources row classes share (constants, seeds, helpers); split from gov_sources_basis.py (sap-2c)."""
import json
import re
import threading
from urllib.parse import urlparse

JURISDICTIONS = ('federal', 'dc', 'virginia', 'maryland', 'local')
SOURCE_TABLES = {
    'GovSource': 'government',
    'NonProfitSource': 'nonprofit',
    'CompanySource': 'company',
    'PoliticalGroupSource': 'political-group',
    'IndividualSource': 'individual',
    # Not every citable source is an organization. A specific
    # peer-reviewed ARTICLE and a press piece by a credentialed
    # author are both legitimate sources and neither is
    # governmental; without these two, citing them meant either
    # mis-filing them as a GovSource or losing the link entirely.
    'AcademicSource': 'academic',
    'JournalisticSource': 'journalistic',
}
_RETRIEVAL_LOCK = threading.Lock()
def _rows(manager, class_name):
    table = (manager.objectTables or {}).get(class_name, {})
    return list(table.values()) if isinstance(table, dict) else list(table)
def find_source(manager, source_name):
    """(row, kind) across EVERY legal source table — government
    first; (None, None) when no table holds the name."""
    for class_name, kind in SOURCE_TABLES.items():
        row = next((s for s in _rows(manager, class_name)
                    if getattr(s, 'name', '') == source_name), None)
        if row is not None:
            return row, kind
    return None, None
def _source(manager, source_name):
    return find_source(manager, source_name)[0]
def _known_sources(manager):
    return sorted(getattr(s, 'name', '')
                  for class_name in SOURCE_TABLES
                  for s in _rows(manager, class_name))
def _acronym_of(source):
    """GovSource rows carry `acronym`; the legal siblings carry
    `short_name` — one accessor for the matching/glossary layer."""
    return (getattr(source, 'acronym', '')
            or getattr(source, 'short_name', ''))
def _legal_identity(source, kind):
    """The per-type legal-identity fields (the verification-registry
    pointers) as a plain dict; {} for government rows."""
    fields_by_kind = {
        'nonprofit': ('ein', 'irs_subsection', 'state_registered',
                      'irs_lookup_url', 'funding_transparency_url'),
        'company': ('legal_name', 'state_of_incorporation',
                    'registry_id', 'registry_url', 'ticker',
                    'industry'),
        'political-group': ('group_kind', 'fec_committee_id',
                            'fec_lookup_url', 'jurisdiction_scope'),
        'individual': ('person_name', 'affiliation', 'credentials',
                       'contributor_name'),
    }
    return {field: getattr(source, field, '')
            for field in fields_by_kind.get(kind, ())}
def _identity_summary(source, kind):
    """A one-line stand-in for the glossary's agency column on
    non-government rows."""
    identity = _legal_identity(source, kind)
    if kind == 'nonprofit':
        state = identity.get('state_registered', '')
        return f'nonprofit{f" ({state})" if state else ""}'
    if kind == 'company':
        return identity.get('legal_name') or 'company'
    if kind == 'political-group':
        return (f"political group "
                f"({identity.get('group_kind', '') or 'unspecified'})")
    if kind == 'individual':
        return identity.get('affiliation') or 'individual'
    return ''
def validate_source_names(manager):
    """Cross-type NAME collisions — one namespace over all five
    tables; {} when clean."""
    seen = {}
    for class_name, kind in SOURCE_TABLES.items():
        for row in _rows(manager, class_name):
            seen.setdefault(getattr(row, 'name', ''), []).append(kind)
    return {name: kinds for name, kinds in seen.items()
            if len(kinds) > 1}
def _domains(source):
    found = set()
    for url in (getattr(source, 'official_website', ''),
                getattr(source, 'data_portal_url', '')):
        if not url:
            continue
        host = urlparse(url).netloc or url
        host = host.lower().lstrip('www.')
        if host:
            found.add(host)
    return found
def _match_evidence(source, text):
    """Why `text` (a provenance/source string) points at `source` —
    [] when it does not."""
    if not text:
        return []
    evidence = []
    acronym = _acronym_of(source)
    if acronym and re.search(
            rf'(?<![A-Za-z0-9]){re.escape(acronym)}(?![A-Za-z0-9])',
            text):
        evidence.append(f"acronym '{acronym}' (word-boundary)")
    full_name = getattr(source, 'full_name', '')
    if full_name and full_name.lower() in text.lower():
        evidence.append(f"full name '{full_name}'")
    lowered = text.lower()
    for domain in sorted(_domains(source)):
        if domain in lowered:
            evidence.append(f"official domain '{domain}'")
    return evidence
def terms_from_source(manager, source_name):
    """Which ScoreTerms ORIGINATE from this source (matched via the
    terms' own provenance AND their values' provenance), with
    per-term evidence + how many stored values trace to it."""
    source, _kind = find_source(manager, source_name)
    if source is None:
        return {'ok': False,
                'error': f"no source named '{source_name}' in any "
                         f'legal source table',
                'knownSources': _known_sources(manager)}
    matched = {}
    for term in _rows(manager, 'ScoreTerm'):
        text = ' '.join([getattr(term, 'provenance_id', '') or '',
                         getattr(term, 'source', '') or ''])
        evidence = _match_evidence(source, text)
        if evidence:
            matched[getattr(term, 'name', '')] = {
                'matchedBy': evidence, 'via': 'term provenance'}
    value_count = 0
    for value in _rows(manager, 'ContextualizedValue'):
        text = ' '.join([getattr(value, 'provenance_id', '') or '',
                         getattr(value, 'source', '') or ''])
        evidence = _match_evidence(source, text)
        if not evidence:
            continue
        value_count += 1
        term_name = getattr(value, 'term_name', '')
        if term_name and term_name not in matched:
            matched[term_name] = {'matchedBy': evidence,
                                  'via': 'value provenance'}
    return {'ok': True, 'source': source_name,
            'terms': [dict({'term': name}, **info)
                      for name, info in sorted(matched.items())],
            'valueCount': value_count}
def source_glossary(manager):
    """The easy acronym lookup — sorted, acronym-first (rows without
    a real acronym sort by full name; we never invent acronyms).
    Spans EVERY legal source type, each entry labeled by kind."""
    entries = []
    for class_name, kind in SOURCE_TABLES.items():
        for source in _rows(manager, class_name):
            entries.append({
                'name': getattr(source, 'name', ''),
                'kind': kind,
                'acronym': _acronym_of(source),
                'fullName': getattr(source, 'full_name', ''),
                'agency': (getattr(source, 'agency', '')
                           if kind == 'government'
                           else _identity_summary(source, kind)),
                'jurisdiction': getattr(source, 'jurisdiction', ''),
                'website': getattr(source, 'official_website', ''),
                'requiresKey': bool(
                    getattr(source, 'requires_api_key', False)),
                'apiKeyEnv': getattr(source, 'api_key_env', ''),
            })
    return sorted(entries,
                  key=lambda e: (e['acronym'] or e['fullName'],
                                 e['jurisdiction']))
def _retrieval_dict(row):
    group = getattr(row, 'retrieved_by_group', '')
    return {
        'name': getattr(row, 'name', ''),
        'source': getattr(row, 'source_name', ''),
        'endpoint': getattr(row, 'endpoint_name', ''),
        'what': getattr(row, 'what', ''),
        'retrievedAt': getattr(row, 'retrieved_at', ''),
        'retrievedBy': getattr(row, 'retrieved_by', ''),
        'retrievedByGroup': group or None,
        'origin': (f'group:{group}' if group
                   else f'individual:'
                        f"{getattr(row, 'retrieved_by', '')}"),
        'rowCount': getattr(row, 'row_count', 0),
        'provenanceUrl': getattr(row, 'provenance_url', ''),
    }
def retrievals_for(manager, source_name):
    rows = sorted((r for r in _rows(manager, 'SourceRetrieval')
                   if getattr(r, 'source_name', '') == source_name),
                  key=lambda r: getattr(r, 'retrieved_at', ''))
    return [_retrieval_dict(r) for r in rows]
def source_report(manager, source_name):
    """One source's full card: expansion, website, key requirement,
    registered endpoints, duplication attributions, and the terms
    that originate from it — for ANY legal source kind, with
    non-government kinds framed honestly."""
    source, kind = find_source(manager, source_name)
    if source is None:
        return {'ok': False,
                'error': f"no source named '{source_name}' in any "
                         f'legal source table',
                'knownSources': _known_sources(manager)}
    endpoint_names = json.loads(
        getattr(source, 'api_endpoint_names_json', '[]') or '[]')
    registered = {getattr(e, 'name', '')
                  for e in _rows(manager, 'APIEndpoint')}
    endpoints = [{'name': n,
                  'registered': n in registered}
                 for n in endpoint_names]
    origins = terms_from_source(manager, source_name)
    report = {
        'ok': True,
        'name': source_name,
        'kind': kind,
        'acronym': _acronym_of(source),
        'fullName': getattr(source, 'full_name', ''),
        'agency': getattr(source, 'agency', ''),
        'parentSource': getattr(source, 'parent_source', '') or None,
        'jurisdiction': getattr(source, 'jurisdiction', ''),
        'officialWebsite': getattr(source, 'official_website', ''),
        'dataPortal': getattr(source, 'data_portal_url', ''),
        'requiresApiKey': bool(getattr(source, 'requires_api_key',
                                       False)),
        'apiKeyEnv': getattr(source, 'api_key_env', '') or None,
        'endpoints': endpoints,
        'retrievals': retrievals_for(manager, source_name),
        'originatingTerms': origins.get('terms', []),
        'originatingValueCount': origins.get('valueCount', 0),
    }
    if kind != 'government':
        report['legalIdentity'] = _legal_identity(source, kind)
        report['framing'] = ('non-government source — not an '
                             'official statistic origin')
    return report
def _src(name, acronym, full_name, agency, jurisdiction, website,
         portal='', parent='', key=False, key_env='', endpoints=(),
         description='', notes=''):
    return {'name': name, 'acronym': acronym, 'full_name': full_name,
            'agency': agency, 'parent_source': parent,
            'jurisdiction': jurisdiction,
            'official_website': website, 'data_portal_url': portal,
            'requires_api_key': key, 'api_key_env': key_env,
            'api_endpoint_names_json': json.dumps(list(endpoints)),
            'description': description, 'notes': notes}
SEED_GOV_SOURCES = [
    # ---- federal: Census family ------------------------------------
    _src('census-bureau', 'USCB', 'United States Census Bureau',
         'U.S. Department of Commerce', 'federal',
         'https://www.census.gov', 'https://data.census.gov',
         key=True, key_env='POLARI_CENSUS_API_KEY',
         description='The federal statistical agency behind ACS/'
                     'AHS/BPS/Pulse; its data API requires a free '
                     'key (observed live 2026-07-16).'),
    _src('census-acs', 'ACS', 'American Community Survey',
         'U.S. Census Bureau', 'federal',
         'https://www.census.gov/programs-surveys/acs',
         'https://data.census.gov', parent='census-bureau',
         key=True, key_env='POLARI_CENSUS_API_KEY',
         endpoints=('census-acs5-b25064', 'census-acs5-b25031',
                    'census-acs5-b25070', 'census-acs5-b25035',
                    'census-acs5-b25014'),
         description='Annual rent/tenure/crowding/year-built tables '
                     'to tract level (plan Appendix B1).'),
    _src('census-pums', 'PUMS', 'Public Use Microdata Sample',
         'U.S. Census Bureau', 'federal',
         'https://www.census.gov/programs-surveys/acs/microdata.html',
         parent='census-acs',
         description='The microdata that cuts to arbitrary personas '
                     '(RELSHIPP=34 = housemate/roommate).'),
    _src('census-ahs', 'AHS', 'American Housing Survey',
         'U.S. Census Bureau (HUD-sponsored)', 'federal',
         'https://www.census.gov/programs-surveys/ahs.html',
         parent='census-bureau',
         description='Biennial housing adequacy + structural '
                     'condition; Washington metro is an oversample.',
         notes='Joint Census/HUD product.'),
    _src('census-bps', 'BPS', 'Building Permits Survey',
         'U.S. Census Bureau', 'federal',
         'https://www.census.gov/permits', parent='census-bureau',
         description='New residential authorizations to '
                     'permit-issuing place (turnover inflow).'),
    _src('census-pulse', 'HPS', 'Household Pulse Survey',
         'U.S. Census Bureau', 'federal',
         'https://www.census.gov/programs-surveys/'
         'household-pulse-survey.html', parent='census-bureau',
         description='Self-reported housing insecurity/conditions; '
                     'successor HTOPS is national-only.'),
    # ---- federal: HUD family ---------------------------------------
    _src('hud', 'HUD',
         'U.S. Department of Housing and Urban Development',
         'U.S. Department of Housing and Urban Development',
         'federal', 'https://www.hud.gov',
         'https://www.huduser.gov',
         key=True, key_env='POLARI_HUD_API_TOKEN',
         description='FMR/Income Limits/CHAS/REAC datasets; the '
                     'huduser API takes a free token.'),
    _src('hud-fmr', 'FMR', 'Fair Market Rents', 'HUD', 'federal',
         'https://www.huduser.gov/portal/datasets/fmr.html',
         parent='hud', key=True, key_env='POLARI_HUD_API_TOKEN',
         endpoints=('hud-fmr-dc-metro',),
         description='40th-percentile gross rent 0-4BR, DC HUD '
                     'Metro FMR Area, annual.'),
    _src('hud-safmr', 'SAFMR', 'Small Area Fair Market Rents',
         'HUD', 'federal',
         'https://www.huduser.gov/portal/datasets/fmr/smallarea/'
         'index.html', parent='hud-fmr',
         description='FMRs by ZIP — the DC metro is a mandatory '
                     'SAFMR area.'),
    _src('hud-il', 'IL', 'Income Limits', 'HUD', 'federal',
         'https://www.huduser.gov/portal/datasets/il.html',
         parent='hud', key=True, key_env='POLARI_HUD_API_TOKEN',
         endpoints=('hud-income-limits-dc-metro',),
         description='30/50/80% AMI by household size — the '
                     '"low income" definition per profile size.'),
    _src('hud-chas', 'CHAS',
         'Comprehensive Housing Affordability Strategy', 'HUD',
         'federal', 'https://www.huduser.gov/portal/datasets/cp.html',
         parent='hud',
         description='Income × cost burden × housing problems to '
                     'tract level (ACS special tab).'),
    _src('hud-reac', 'REAC', 'Real Estate Assessment Center '
         '(NSPIRE physical inspection scores)', 'HUD', 'federal',
         'https://www.huduser.gov/portal/datasets/pis.html',
         parent='hud',
         description='Property-level inspection scores for assisted '
                     'multifamily + public housing.',
         notes='NSPIRE protocol replaced UPCS in 2023 — scores not '
               'comparable across the change.'),
    _src('hud-cinch', 'CINCH', 'Components of Inventory Change',
         'HUD', 'federal',
         'https://www.huduser.gov/portal/datasets/cinch.html',
         parent='hud',
         description='The only official housing-LOSS measure '
                     '(demolition/disaster), biennial.'),
    # ---- federal: BLS family ---------------------------------------
    _src('bls', 'BLS', 'Bureau of Labor Statistics',
         'U.S. Department of Labor', 'federal',
         'https://www.bls.gov', key=False,
         key_env='POLARI_BLS_API_KEY',
         description='CPI/CEX/OEWS/CPS/LAUS; public API v2 works '
                     'keyless at low volume.',
         notes='Optional key raises rate limits.'),
    _src('bls-cpi', 'CPI', 'Consumer Price Index', 'BLS', 'federal',
         'https://www.bls.gov/regions/mid-atlantic/news-release/'
         'consumerpriceindex_washingtondc.htm', parent='bls',
         endpoints=('bls-cpi-washington',),
         description='Washington-Arlington-Alexandria series '
                     '(CUURS35ASA0), bimonthly — trend, not levels.'),
    _src('bls-cex', 'CEX', 'Consumer Expenditure Surveys', 'BLS',
         'federal', 'https://www.bls.gov/cex/', parent='bls',
         description='Washington-metro budget shares in DOLLARS '
                     '(2-yr averages) + PUMD microdata.'),
    _src('bls-oews', 'OEWS',
         'Occupational Employment and Wage Statistics', 'BLS',
         'federal', 'https://www.bls.gov/oes/current/oes_47900.htm',
         parent='bls',
         description='Wage percentiles per occupation for metro '
                     '47900 — 10th/25th = the entry-level line.'),
    _src('bls-cps', 'CPS', 'Current Population Survey', 'BLS',
         'federal', 'https://www.bls.gov/cps/', parent='bls',
         description='Youth labor force status by age; joint with '
                     'Census.'),
    _src('bls-laus', 'LAUS', 'Local Area Unemployment Statistics',
         'BLS', 'federal', 'https://www.bls.gov/lau/', parent='bls',
         description='Metro/county unemployment.'),
    # ---- federal: others -------------------------------------------
    _src('usda-fns', 'FNS', 'Food and Nutrition Service',
         'U.S. Department of Agriculture', 'federal',
         'https://www.fns.usda.gov/research/cnpp/usda-food-plans/'
         'cost-food-monthly-reports',
         description='Thrifty/Low/Moderate/Liberal monthly food '
                     'plans by age-sex (national dollars).'),
    _src('hhs-aspe', 'ASPE', 'Office of the Assistant Secretary '
         'for Planning and Evaluation',
         'U.S. Department of Health and Human Services', 'federal',
         'https://aspe.hhs.gov/topics/poverty-economic-mobility/'
         'poverty-guidelines',
         description='The annual poverty guidelines '
                     '(2026: $15,960 + $5,680/person).'),
    _src('eia', 'EIA', 'U.S. Energy Information Administration',
         'U.S. Department of Energy', 'federal',
         'https://www.eia.gov', key=True,
         key_env='POLARI_EIA_API_KEY',
         endpoints=('eia-residential-electricity',),
         description='Residential electricity/gas prices by state, '
                     'monthly; API v2 requires a free key.'),
    _src('eia-recs', 'RECS',
         'Residential Energy Consumption Survey', 'EIA', 'federal',
         'https://www.eia.gov/consumption/residential/',
         parent='eia',
         description='Household energy expenditure, state estimates '
                     'since 2020.'),
    _src('fta-ntd', 'NTD', 'National Transit Database',
         'Federal Transit Administration (USDOT)', 'federal',
         'https://www.transit.dot.gov/ntd',
         description='WMATA fare revenues + ridership -> derived '
                     'average fare per trip.'),
    _src('bts', 'BTS', 'Bureau of Transportation Statistics',
         'U.S. Department of Transportation', 'federal',
         'https://www.bts.gov',
         description='Household transportation cost context '
                     '(LATCH, dated 2017).'),
    _src('osha', 'OSHA',
         'Occupational Safety and Health Administration',
         'U.S. Department of Labor', 'federal',
         'https://www.osha.gov', 'https://enforcedata.dol.gov',
         endpoints=('osha-enforcement-construction',),
         description='Inspections/violations by construction '
                     'employer (NAICS 23) — builder-quality signal.'),
    _src('nist', 'NIST',
         'National Institute of Standards and Technology',
         'U.S. Department of Commerce', 'federal',
         'https://www.nist.gov',
         description='Handbook 135 life-cycle-cost methodology + '
                     'BLCC (methodology, not component lifetimes).'),
    # ---- District of Columbia --------------------------------------
    _src('dc-ota', 'OTA', 'Office of the Tenant Advocate',
         'District of Columbia', 'dc', 'https://ota.dc.gov',
         'https://ota.dc.gov/page/monthly-eviction-data',
         description='Monthly scheduled/executed eviction counts '
                     '(DC has NO bulk case-level data) + rent-cap '
                     'parameters.'),
    _src('dc-dhcd-rad', 'RAD', 'Rental Accommodations Division '
         '(DC DHCD)', 'DC Department of Housing and Community '
         'Development', 'dc', 'https://dhcd.dc.gov/rentcontrol',
         'https://rentregistry.dc.gov',
         description='DC rent control: the Rent Registry (every '
                     'covered unit + provider identity) and '
                     'rent-increase petitions.'),
    _src('dc-dob', 'DOB', 'Department of Buildings',
         'District of Columbia', 'dc', 'https://dob.dc.gov',
         'https://scout.dcra.dc.gov',
         description='Housing code violations searchable BY '
                     'LANDLORD NAME; contractor licensing (SCOUT).'),
    _src('dc-ora', 'ORA', 'Office of Revenue Analysis',
         'DC Office of the Chief Financial Officer', 'dc',
         'https://ora-cfo.dc.gov/page/tax-burden-studies',
         description='Annual tax rates/burdens comparisons — DC vs '
                     '50 states and vs the NoVA/MD suburbs.'),
    _src('dc-octo-opendata', 'OCTO', 'Office of the Chief '
         'Technology Officer (Open Data DC)',
         'District of Columbia', 'dc', 'https://opendata.dc.gov',
         endpoints=('dc-basic-business-licenses',),
         description='Rental licenses (BBL), violations, permits, '
                     '311 — DC open-data host.'),
    # ---- Virginia ----------------------------------------------------
    _src('va-dpor', 'DPOR', 'Department of Professional and '
         'Occupational Regulation', 'Commonwealth of Virginia',
         'virginia', 'https://www.dpor.virginia.gov',
         'https://dporweb.dpor.virginia.gov/LicenseLookup/'
         'DisciplinaryActionsSearch',
         description='Contractor licenses + disciplinary actions '
                     'since 2002 — builder-quality signal.'),
    _src('va-oes', 'OES', 'Office of the Executive Secretary '
         '(Supreme Court of Virginia)',
         'Supreme Court of Virginia', 'virginia',
         'https://www.vacourts.gov/courtadmin/aoc/djs/programs/'
         'cpss/csi/gd/home',
         description='Unlawful-detainer filings/dispositions by '
                     'locality — daily Power BI, no bulk case '
                     'data.'),
    _src('va-dhcd', 'DHCD', 'Department of Housing and Community '
         'Development', 'Commonwealth of Virginia', 'virginia',
         'https://www.dhcd.virginia.gov',
         description='VRLTA landlord-tenant guidance + rental '
                     'assistance programs.'),
    _src('fairfax-dta', 'DTA', 'Department of Tax Administration '
         '(Fairfax County)', 'Fairfax County, Virginia', 'local',
         'https://data-fairfaxcountygis.opendata.arcgis.com',
         endpoints=('fairfax-dwelling-data',),
         description='Parcel-level dwelling data incl. YEAR BUILT '
                     '(housing-stock age).'),
    # ---- Maryland ------------------------------------------------------
    _src('md-sdat', 'SDAT', 'State Department of Assessments and '
         'Taxation', 'State of Maryland', 'maryland',
         'https://sdat.dat.maryland.gov/RealProperty/Pages/'
         'default.aspx', 'https://opendata.maryland.gov',
         description='Statewide parcel data: OWNER NAME + YEAR '
                     'BUILT (the rent-stabilization coverage '
                     'field).'),
    _src('md-mhic', 'MHIC', 'Maryland Home Improvement Commission',
         'Maryland Department of Labor', 'maryland',
         'https://labor.maryland.gov/license/mhic/mhicdisc.shtml',
         description='Contractor licensing + published disciplinary '
                     'actions per fiscal year.'),
    _src('md-judiciary', '', 'Maryland Judiciary '
         '(District Court of Maryland)', 'State of Maryland',
         'maryland', 'https://www.mdcourts.gov/dashboards',
         'https://opendata.maryland.gov/Housing/District-Court-of-'
         'Maryland-Eviction-Case-Data/mvqb-b4hf',
         endpoints=('md-eviction-cases',),
         description='THE regional standout: statewide CASE-LEVEL '
                     'eviction data since Jan 2023.',
         notes='No common acronym — never invent one.'),
    _src('md-dhcd', 'DHCD', 'Department of Housing and Community '
         'Development', 'State of Maryland', 'maryland',
         'https://dhcd.maryland.gov',
         description="Tenants' Bill of Rights, deposit calculator, "
                     'statutory eviction reporting host.'),
    _src('moco-dhca', 'DHCA', 'Department of Housing and Community '
         'Affairs (Montgomery County)',
         'Montgomery County, Maryland', 'local',
         'https://www.montgomerycountymd.gov/dhca/',
         'https://data.montgomerycountymd.gov',
         endpoints=('moco-housing-violations',
                    'moco-rental-licenses'),
         description='The region-richest official rent data: '
                     'mandatory annual rental survey + licensing + '
                     'violations + rent stabilization.'),
    _src('pg-dpie', 'DPIE', 'Department of Permitting, Inspections '
         'and Enforcement (Prince George\'s County)',
         "Prince George's County, Maryland", 'local',
         'https://www.princegeorgescountymd.gov/departments-offices/'
         'permitting-inspections-and-enforcement',
         'https://data.princegeorgescountymd.gov',
         endpoints=('pg-housing-violations',),
         description='Rental licensing + housing inspection '
                     'violations + rent stabilization enforcement.'),
]
