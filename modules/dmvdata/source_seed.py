"""
@module dmvdata.source_seed

col-2 (DMV_COST_OF_LIVING_DATA_PLAN.md §7-revised): the plan's
PROFILER-READY official sources as APIDomain/APIEndpoint rows —
registration is DATA, so adding a government source is adding rows,
never code. Every endpoint's description cites its plan-appendix
source; endpoints that need credentials carry the ENV-KNOB NAME in
authConfig as 'env:<VAR>' (a pointer, never a literal key — repos
are PUBLIC).

@consumers
  - dmvdata.custom.census_pull (the first end-to-end slice)
  - polariServer (registration + seed, wired by the main session)
"""

#: DMV jurisdiction FIPS — DC + 5 NoVA + 5 MD suburbs (plan §2 +
#: Appendix C3's Howard/Anne Arundel licensing jurisdictions).
DMV_JURISDICTIONS = [
    {'context': 'dc', 'display': 'District of Columbia',
     'state': '11', 'county': '001'},
    {'context': 'va-arlington', 'display': 'Arlington County, VA',
     'state': '51', 'county': '013'},
    {'context': 'va-alexandria', 'display': 'Alexandria city, VA',
     'state': '51', 'county': '510'},
    {'context': 'va-fairfax', 'display': 'Fairfax County, VA',
     'state': '51', 'county': '059'},
    {'context': 'va-loudoun', 'display': 'Loudoun County, VA',
     'state': '51', 'county': '107'},
    {'context': 'va-prince-william',
     'display': 'Prince William County, VA',
     'state': '51', 'county': '153'},
    {'context': 'md-montgomery', 'display': 'Montgomery County, MD',
     'state': '24', 'county': '031'},
    {'context': 'md-prince-georges',
     'display': "Prince George's County, MD",
     'state': '24', 'county': '033'},
    {'context': 'md-frederick', 'display': 'Frederick County, MD',
     'state': '24', 'county': '021'},
    {'context': 'md-howard', 'display': 'Howard County, MD',
     'state': '24', 'county': '027'},
    {'context': 'md-anne-arundel',
     'display': 'Anne Arundel County, MD',
     'state': '24', 'county': '003'},
]

SEED_API_DOMAINS = [
    {'name': 'census-api', 'displayName': 'U.S. Census Bureau API',
     'host': 'api.census.gov', 'protocol': 'https',
     'description': 'ACS tables + PUMS (plan Appendix B1). No key '
                    'needed at low volume.',
     'tags': ['official', 'federal', 'dmv-col']},
    {'name': 'huduser-api', 'displayName': 'HUD USER API',
     'host': 'www.huduser.gov', 'protocol': 'https',
     'description': 'Fair Market Rents / Income Limits API (plan '
                    'Appendix B3). Token via env '
                    'POLARI_HUD_API_TOKEN.',
     'tags': ['official', 'federal', 'dmv-col']},
    {'name': 'eia-api', 'displayName': 'U.S. EIA API v2',
     'host': 'api.eia.gov', 'protocol': 'https',
     'description': 'Residential electricity/gas prices by state '
                    '(plan Appendix B5). Key via env '
                    'POLARI_EIA_API_KEY.',
     'tags': ['official', 'federal', 'dmv-col']},
    {'name': 'bls-api', 'displayName': 'BLS Public Data API v2',
     'host': 'api.bls.gov', 'protocol': 'https',
     'description': 'CPI Washington series (plan Appendix B4). '
                    'Optional key env POLARI_BLS_API_KEY raises '
                    'rate limits.',
     'tags': ['official', 'federal', 'dmv-col']},
    {'name': 'md-opendata', 'displayName': 'Maryland Open Data (SODA)',
     'host': 'opendata.maryland.gov', 'protocol': 'https',
     'description': 'Statewide datasets incl. the case-level '
                    'eviction data (plan Appendix C3).',
     'tags': ['official', 'state-md', 'dmv-col']},
    {'name': 'moco-opendata',
     'displayName': 'dataMontgomery (SODA)',
     'host': 'data.montgomerycountymd.gov', 'protocol': 'https',
     'description': 'Montgomery County housing datasets (plan '
                    'Appendices A3/C3).',
     'tags': ['official', 'local-md', 'dmv-col']},
    {'name': 'pg-opendata',
     'displayName': "Prince George's Open Data (SODA)",
     'host': 'data.princegeorgescountymd.gov', 'protocol': 'https',
     'description': 'PG County housing inspection violations (plan '
                    'Appendix C3).',
     'tags': ['official', 'local-md', 'dmv-col']},
    {'name': 'dc-opendata', 'displayName': 'Open Data DC (ArcGIS)',
     'host': 'opendata.dc.gov', 'protocol': 'https',
     'description': 'DC rental licenses (BBL), violations, permits, '
                    '311 (plan Appendices A2/C1).',
     'tags': ['official', 'local-dc', 'dmv-col']},
    {'name': 'fairfax-gis',
     'displayName': 'Fairfax County GIS Open Data (ArcGIS)',
     'host': 'data-fairfaxcountygis.opendata.arcgis.com',
     'protocol': 'https',
     'description': 'Dwelling data incl. year built (plan Appendix '
                    'C2).',
     'tags': ['official', 'local-va', 'dmv-col']},
    {'name': 'dol-enforcement',
     'displayName': 'DOL Enforcement Data (OSHA)',
     'host': 'enforcedata.dol.gov', 'protocol': 'https',
     'description': 'OSHA inspections/violations by construction '
                    'employer (plan Appendix A2).',
     'tags': ['official', 'federal', 'dmv-col']},
]

_ACS = ('/data/2023/acs/acs5?get=NAME,{table}_001E'
        '&for=county:{counties}&in=state:{state}')

def _acs_endpoint(table, what):
    return {
        'name': f'census-acs5-{table.lower()}',
        'displayName': f'ACS 5-yr {table} ({what})',
        'domainName': 'census-api',
        'endpointPath': _ACS.replace('{table}', table),
        'httpMethod': 'GET',
        'description': f'Census ACS 5-year table {table} — {what} '
                       f'(plan Appendix B1). Path is a template: '
                       f'fill counties/state per DMV_JURISDICTIONS. '
                       f'Key is FREE '
                       f'(api.census.gov/data/key_signup.html).',
        'persistData': True,
        'polariClassName': f'Acs{table}Row',
        # Observed live 2026-07-16: keyless requests get 'Missing
        # Key' — a free key via the env knob is required.
        'authType': 'apikey',
        'authConfig': 'env:POLARI_CENSUS_API_KEY',
    }

SEED_API_ENDPOINTS = [
    _acs_endpoint('B25064', 'median gross rent'),
    _acs_endpoint('B25031', 'median gross rent by bedrooms'),
    _acs_endpoint('B25070', 'gross rent as % of household income'),
    _acs_endpoint('B25035', 'median year structure built'),
    _acs_endpoint('B25014', 'occupants per room (crowding)'),
    {'name': 'hud-fmr-dc-metro',
     'displayName': 'HUD Fair Market Rents (DC HUD Metro FMR Area)',
     'domainName': 'huduser-api',
     'endpointPath': '/hudapi/public/fmr/data/METRO47900M47900',
     'httpMethod': 'GET',
     'description': 'FY Fair Market Rents 0-4BR for the '
                    'Washington-Arlington-Alexandria HUD Metro FMR '
                    'Area (plan Appendix B3).',
     'persistData': True, 'polariClassName': 'HudFmrRow',
     'authType': 'bearer', 'authConfig': 'env:POLARI_HUD_API_TOKEN'},
    {'name': 'hud-income-limits-dc-metro',
     'displayName': 'HUD Income Limits (DC metro)',
     'domainName': 'huduser-api',
     'endpointPath': '/hudapi/public/il/data/METRO47900M47900',
     'httpMethod': 'GET',
     'description': '30/50/80% AMI by household size (plan Appendix '
                    'B3).',
     'persistData': True, 'polariClassName': 'HudIncomeLimitRow',
     'authType': 'bearer', 'authConfig': 'env:POLARI_HUD_API_TOKEN'},
    {'name': 'eia-residential-electricity',
     'displayName': 'EIA residential electricity price (DC/MD/VA)',
     'domainName': 'eia-api',
     'endpointPath': '/v2/electricity/retail-sales/data/'
                     '?frequency=monthly&data[0]=price'
                     '&facets[sectorid][]=RES&facets[stateid][]=DC'
                     '&facets[stateid][]=MD&facets[stateid][]=VA',
     'httpMethod': 'GET',
     'description': 'Residential ¢/kWh by state (plan Appendix B5). '
                    'Append api_key from env POLARI_EIA_API_KEY at '
                    'fetch time.',
     'persistData': True, 'polariClassName': 'EiaResElectricityRow',
     'authType': 'apikey', 'authConfig': 'env:POLARI_EIA_API_KEY'},
    {'name': 'bls-cpi-washington',
     'displayName': 'BLS CPI, Washington-Arlington-Alexandria',
     'domainName': 'bls-api',
     'endpointPath': '/publicAPI/v2/timeseries/data/CUURS35ASA0',
     'httpMethod': 'GET',
     'description': 'CPI all items, series CUURS35ASA0 (plan '
                    'Appendix B4). Optional key env '
                    'POLARI_BLS_API_KEY.',
     'persistData': True, 'polariClassName': 'BlsCpiWashingtonRow',
     'authType': 'apikey', 'authConfig': 'env:POLARI_BLS_API_KEY'},
    {'name': 'md-eviction-cases',
     'displayName': 'MD District Court eviction case data',
     'domainName': 'md-opendata',
     'endpointPath': '/resource/mvqb-b4hf.json',
     'httpMethod': 'GET',
     'description': 'THE regional standout: statewide case-level '
                    'eviction data since Jan 2023 (plan Appendix '
                    'C3).',
     'persistData': True, 'polariClassName': 'MdEvictionCaseRow',
     'authType': 'none'},
    {'name': 'moco-housing-violations',
     'displayName': 'Montgomery housing code violations',
     'domainName': 'moco-opendata',
     'endpointPath': '/resource/k9nj-z35d.json',
     'httpMethod': 'GET',
     'description': 'Code violations 2013-present, weekly (plan '
                    'Appendices A3/C3).',
     'persistData': True, 'polariClassName': 'MocoViolationRow',
     'authType': 'none'},
    {'name': 'moco-rental-licenses',
     'displayName': 'Montgomery housing licensing + registration',
     'domainName': 'moco-opendata',
     'endpointPath': '/resource/et5s-xste.json',
     'httpMethod': 'GET',
     'description': 'All rental licenses under County Code ch. 29 '
                    '(plan Appendix C3) — owner identity source.',
     'persistData': True, 'polariClassName': 'MocoRentalLicenseRow',
     'authType': 'none'},
    {'name': 'pg-housing-violations',
     'displayName': "Prince George's housing inspection violations",
     'domainName': 'pg-opendata',
     'endpointPath': '/resource/9hyf-46qb.json',
     'httpMethod': 'GET',
     'description': 'DPIE inspection violations (plan Appendix C3).',
     'persistData': True, 'polariClassName': 'PgViolationRow',
     'authType': 'none'},
    {'name': 'dc-basic-business-licenses',
     'displayName': 'DC Basic Business Licenses (rental categories)',
     'domainName': 'dc-opendata',
     'endpointPath': '/datasets/85bf98d3915f412c8a4de706f2d13513_0'
                     '.geojson',
     'httpMethod': 'GET',
     'description': 'Rental housing licenses with licensee identity '
                    '(plan Appendix C1). ArcGIS GeoJSON export.',
     'persistData': True, 'polariClassName': 'DcBblRow',
     'authType': 'none'},
    {'name': 'fairfax-dwelling-data',
     'displayName': 'Fairfax dwelling data (year built)',
     'domainName': 'fairfax-gis',
     'endpointPath': '/datasets/Fairfaxcountygis::tax-'
                     'administrations-real-estate-dwelling-data'
                     '.geojson',
     'httpMethod': 'GET',
     'description': 'Parcel-level structure attributes incl. YEAR '
                    'BUILT (plan Appendix C2).',
     'persistData': True, 'polariClassName': 'FairfaxDwellingRow',
     'authType': 'none'},
    {'name': 'osha-enforcement-construction',
     'displayName': 'OSHA enforcement (construction employers)',
     'domainName': 'dol-enforcement',
     'endpointPath': '/views/data_catalogs.php',
     'httpMethod': 'GET',
     'description': 'Bulk inspection/violation catalogs, NAICS 23 '
                    '(plan Appendix A2). Catalog page — the CSVs it '
                    'lists are the pull targets.',
     'persistData': False, 'polariClassName': '',
     'authType': 'none'},
]
