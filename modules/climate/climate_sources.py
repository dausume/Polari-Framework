"""
@module climate.climate_sources

THE SOURCES, AS ROWS (CO2_HEALTH_PLAN.md §3). Every series this
app plots is fetched through an `APIEndpoint` row that names its
`GovSource`, so a number on a graph can always answer "who says
so, and how did it get here".

⚠ EVERY URL BELOW WAS FETCHED LIVE ON 2026-08-02 and returned the
real payload — byte counts and content signatures recorded on the
rows are what this machine actually observed, not what a model
remembered. `verifiedOn` carries that date. A citation row
pointing at a 404 is a lie with a footnote; federal portals move,
so re-verification is a maintenance task, not a one-off.

🔑 THE TRAP THAT SHAPED THESE ROWS. Two retired NHANES paths
(`/Nchs/Nhanes/<cycle>/<FILE>.XPT`, the pattern most of the
internet still cites) return **HTTP 200** with a 20905-byte CDC
"Page Not Found" HTML page — byte-identical for two different
files. Only the current `/Nchs/Data/Nhanes/Public/<year>/
DataFiles/<FILE>.xpt` form returns SAS XPORT. Every row therefore
carries `contentSignature` + `rejectSignature` + `minBytes`, and
the fetch path refuses on content, never on status alone.

@consumers climate.series_ingest, climate.climate_api, polariServer
"""

import json

from composition.seed_upsert import upsert_seed_pairs

PROV = 'co2-0'
VERIFIED = '2026-08-02'

#: What a decoy looks like. Both agencies serve their error pages
#: with a success status, so this is the only reliable tell.
HTML_DECOY = '<!DOCTYPE html'
#: SAS Transport (XPORT) files open with the library header.
XPORT_SIG = 'HEADER RECORD*******LIBRARY HEADER RECORD'
#: NOAA GML and NCEI paleo text archives open with a comment
#: banner (NCEI's is preceded by a UTF-8 BOM, which the payload
#: check strips before comparing).
TEXT_SIG = '#'


def _gov(name, acronym, full_name, agency, website, portal='',
         parent='', endpoints=(), description='', notes=''):
    return {'name': name, 'acronym': acronym,
            'full_name': full_name, 'agency': agency,
            'parent_source': parent, 'jurisdiction': 'federal',
            'official_website': website, 'data_portal_url': portal,
            'requires_api_key': False, 'api_key_env': '',
            'api_endpoint_names_json': json.dumps(list(endpoints)),
            'description': description, 'notes': notes}


#: The publishers. None of these need a key at the volumes this
#: app reads, which is why `requires_api_key` is False and
#: `api_key_env` is empty — an unused key knob is a liability.
SEED_CLIMATE_GOV_SOURCES = [
    _gov('noaa-gml', 'NOAA GML',
         'NOAA Global Monitoring Laboratory',
         'National Oceanic and Atmospheric Administration',
         'https://gml.noaa.gov',
         'https://gml.noaa.gov/ccgg/trends/',
         endpoints=('noaa-co2-annmean-mlo', 'noaa-co2-gr-mlo',
                    'noaa-co2-annmean-global',
                    'noaa-co2-gr-global'),
         description='The modern instrumental CO2 record: Mauna '
                     'Loa (1958-) and the globally averaged '
                     'marine surface series, plus the PUBLISHED '
                     'annual growth rate.',
         notes='The growth-rate files matter: they are the '
               'source\'s OWN velocity term. Preferring them to '
               'a difference of the levels means the velocity on '
               'the page is NOAA\'s, not ours - and where both '
               'exist, disagreement is a finding.'),
    _gov('noaa-ncei-paleo', 'NCEI Paleo',
         'NOAA National Centers for Environmental Information, '
         'Paleoclimatology',
         'National Oceanic and Atmospheric Administration',
         'https://www.ncei.noaa.gov/products/paleoclimatology',
         'https://www.ncei.noaa.gov/access/paleo-search/',
         parent='noaa-gml',
         endpoints=('ncei-antarctica-co2-composite',
                    'ncei-law-dome-co2'),
         description='Ice-core CO2 archives: the 800,000-year '
                     'Antarctic composite and the high-resolution '
                     'Law Dome record that overlaps the '
                     'instrumental era.',
         notes='This is the ONLY source on the page that reaches '
               'human prehistory. Its resolution is centuries to '
               'millennia, never annual - a chart that implies '
               'otherwise is lying about what an ice core is.'),
    _gov('cdc-nchs-nhanes', 'NHANES',
         'National Health and Nutrition Examination Survey',
         'Centers for Disease Control and Prevention / National '
         'Center for Health Statistics',
         'https://www.cdc.gov/nchs/nhanes/',
         'https://wwwn.cdc.gov/nchs/nhanes/',
         endpoints=('nhanes-biopro-xpt', 'nhanes-dpq-xpt'),
         description='The population measurement side: serum '
                     'bicarbonate (standard biochemistry profile) '
                     'and the PHQ-9 depression screener, both '
                     'published per 2-year cycle as SAS XPORT.',
         notes='Bicarbonate and PHQ-9 come from the SAME survey '
               'cycles and the same sampling frame, which is why '
               'they can be compared at all. RETIRED URL PATHS '
               'RETURN HTTP 200 WITH AN HTML ERROR PAGE - see the '
               'endpoint rows.'),
    _gov('cdc-nchs-vital', 'NCHS',
         'National Center for Health Statistics (vital statistics)',
         'Centers for Disease Control and Prevention',
         'https://www.cdc.gov/nchs/', 'https://data.cdc.gov',
         endpoints=('cdc-life-expectancy',),
         description='US life expectancy at birth by year, 1900 '
                     'onward, over the Socrata open-data API.',
         notes='The only true JSON API in this app\'s source set; '
               'everything else is a published file.'),
    _gov('niosh', 'NIOSH',
         'National Institute for Occupational Safety and Health',
         'Centers for Disease Control and Prevention',
         'https://www.cdc.gov/niosh/',
         description='Occupational exposure limits (REL/STEL) and '
                     'the IDLH value for carbon dioxide.',
         notes='Occupational limits protect healthy adults over a '
               'work shift. Reading them as safe-for-everyone-'
               'always is the single most common misuse of this '
               'number, and the threshold rows say so.'),
]


def _ep(name, display, source, url, path, fmt, signature,
        min_bytes, measures, cadence='annual', params='{}',
        citation='', license_note='', notes='', reject=HTML_DECOY):
    return {
        'name': name, 'displayName': display,
        'description': measures,
        'domainName': '', 'endpointPath': path, 'url': url,
        'httpMethod': 'GET', 'responseRootPath': '',
        'linkedProfileName': '', 'persistData': True,
        'polariClassName': 'AtmosphericObservation',
        'fetchIntervalMinutes': 0, 'isActive': True,
        'authType': 'none', 'authConfig': '',
        'responseFormat': fmt, 'contentSignature': signature,
        'rejectSignature': reject, 'minBytes': min_bytes,
        'paramsTemplate': params, 'fieldMapJson': '{}',
        'citationText': citation, 'licenseNote': license_note,
        'verifiedOn': VERIFIED,
    }


_NOAA = 'https://gml.noaa.gov/webdata/ccgg/trends/co2'
_NCEI = ('https://www.ncei.noaa.gov/pub/data/paleo/icecore/'
         'antarctica')
_NHANES = 'https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public'
_NOAA_CITE = ('Lan X, Tans P, Thoning K; NOAA Global Monitoring '
              'Laboratory. Trends in globally-averaged CO2. '
              'https://gml.noaa.gov/ccgg/trends/')
_NOAA_LICENSE = ('NOAA GML asks that data providers be credited '
                 'and, where the data are central to a '
                 'publication, that coauthorship be considered.')

SEED_CLIMATE_ENDPOINTS = [
    _ep('noaa-co2-annmean-mlo', 'Mauna Loa annual mean CO2',
        'noaa-gml', _NOAA, 'co2_annmean_mlo.txt', 'text',
        TEXT_SIG, 1000,
        'Annual mean CO2 mole fraction at Mauna Loa, 1959-, with '
        'the estimated annual uncertainty.',
        citation=_NOAA_CITE, license_note=_NOAA_LICENSE,
        notes='3696 bytes observed 2026-08-02; last row 2025 = '
              '427.35 +/- 0.12 ppm.'),
    _ep('noaa-co2-gr-mlo', 'Mauna Loa CO2 annual growth rate',
        'noaa-gml', _NOAA, 'co2_gr_mlo.txt', 'text', TEXT_SIG,
        1000,
        'NOAA\'s OWN annual CO2 growth rate at Mauna Loa - the '
        'velocity term, published rather than derived.',
        citation=_NOAA_CITE, license_note=_NOAA_LICENSE),
    _ep('noaa-co2-annmean-global', 'Global mean CO2 (annual)',
        'noaa-gml', _NOAA, 'co2_annmean_gl.txt', 'text', TEXT_SIG,
        1000,
        'Globally averaged marine surface annual mean CO2 - the '
        'cross-check on the single-station Mauna Loa record.',
        citation=_NOAA_CITE, license_note=_NOAA_LICENSE),
    _ep('noaa-co2-gr-global', 'Global CO2 annual growth rate',
        'noaa-gml', _NOAA, 'co2_gr_gl.txt', 'text', TEXT_SIG,
        1000,
        'Globally averaged annual CO2 growth rate.',
        citation=_NOAA_CITE, license_note=_NOAA_LICENSE),
    _ep('ncei-antarctica-co2-composite',
        'Antarctic ice-core CO2 composite (800 kyr)',
        'noaa-ncei-paleo', _NCEI,
        'antarctica2015co2composite.txt', 'text', TEXT_SIG, 10000,
        'CO2 from Antarctic ice cores spanning 800,000 years, as '
        'gas age (cal BP) with a 1-sigma uncertainty per point.',
        cadence='irregular',
        citation=('Bereiter B, Eggleston S, Schmitt J, '
                  'Nehrbass-Ahles C, Stocker TF, Fischer H, '
                  'Kipfstuhl S, Chappellaz J (2015). Revision of '
                  'the EPICA Dome C CO2 record from 800 to 600 kyr '
                  'before present. Geophysical Research Letters. '
                  'NOAA/WDS Paleoclimatology study 17975.'),
        license_note='NOAA asks that the publication, the online '
                     'resource and the access date all be cited.',
        notes='50236 bytes / 1901 data rows observed 2026-08-02; '
              'ages run -51 to 805669 cal BP (BP = before 1950).'),
    _ep('ncei-law-dome-co2', 'Law Dome CO2 (high resolution)',
        'noaa-ncei-paleo',
        'https://www.ncei.noaa.gov/pub/data/paleo/icecore/'
        'antarctica/law', 'law2006.txt', 'text',
        'Law Dome Ice Core', 10000,
        'Law Dome ice-core and firn CO2 - the high-resolution '
        'record across the industrial transition, which OVERLAPS '
        'the instrumental era and so validates the splice.',
        cadence='irregular',
        citation=('MacFarling Meure C, Etheridge D, Trudinger C, '
                  'Steele P, Langenfelds R, van Ommen T, Smith A, '
                  'Elkins J (2006). Law Dome CO2, CH4 and N2O ice '
                  'core records extended to 2000 years BP. '
                  'Geophysical Research Letters 33, L14810.'),
        notes='251543 bytes observed 2026-08-02. NOTE THE '
              'SIGNATURE: unlike every other archive here this '
              'file has NO "#" comment markers - it is prose '
              'followed by several stacked tables (CH4, CO2, N2O, '
              'Cape Grim, firn), so the generic text signature '
              'would have accepted it and the generic parser '
              'would have read the wrong columns. PARSER PENDING '
              'ON PURPOSE: the CO2 column must be identified from '
              'the file\'s own header prose before any ingest. '
              'Guessing a column in a health-adjacent study is '
              'exactly the failure this app refuses.'),
    _ep('nhanes-biopro-xpt',
        'NHANES standard biochemistry profile (XPORT)',
        'cdc-nchs-nhanes', _NHANES,
        '{year}/DataFiles/{file}.xpt', 'xport', XPORT_SIG, 100000,
        'Per-cycle serum biochemistry including bicarbonate '
        '(LBXSC3SI, mmol/L).',
        cadence='biennial',
        params=json.dumps({'year': '2017', 'file': 'BIOPRO_J'}),
        citation=('CDC/NCHS, National Health and Nutrition '
                  'Examination Survey, standard biochemistry '
                  'profile, per cycle.'),
        license_note='US federal public-domain data.',
        notes='2072000-3420640 bytes observed across cycles. THE '
              'PATH TEMPLATE MATTERS: the older '
              '/Nchs/Nhanes/<cycle>/<FILE>.XPT form returns HTTP '
              '200 with a 20905-byte HTML "Page Not Found" page, '
              'identical for every missing file. rejectSignature '
              'is what catches it.'),
    _ep('nhanes-dpq-xpt',
        'NHANES depression screener PHQ-9 (XPORT)',
        'cdc-nchs-nhanes', _NHANES,
        '{year}/DataFiles/{file}.xpt', 'xport', XPORT_SIG, 100000,
        'Per-cycle PHQ-9 depression screener responses - the '
        'stress/mental-health side, from the SAME cycles and '
        'sampling frame as the bicarbonate series.',
        cadence='biennial',
        params=json.dumps({'year': '2017', 'file': 'DPQ_J'}),
        citation=('CDC/NCHS, National Health and Nutrition '
                  'Examination Survey, mental health - depression '
                  'screener (DPQ), per cycle.'),
        license_note='US federal public-domain data.',
        notes='471760-560000 bytes observed. Same-survey pairing '
              'is what makes a bicarbonate/mood comparison worth '
              'attempting at all; it still does not make it '
              'causal.'),
    _ep('gcb-global-carbon-budget',
        'Global Carbon Budget 2025 v1.0 (workbook)',
        'global-carbon-project',
        'https://globalcarbonbudget.org/download',
        '2519/', 'binary', 'PK\x03\x04', 100000,
        'The annual global carbon budget workbook: emissions, '
        'atmospheric growth, and the ocean/land/cement sinks by '
        'year, 1959-2024.',
        citation=('Friedlingstein P et al. Global Carbon Budget '
                  '2025. Earth System Science Data. Global Carbon '
                  'Project, doi:10.18160/GCP-2025.'),
        license_note='CC BY 4.0; the Global Carbon Project asks '
                     'that the ESSD paper be cited.',
        reject='<!DOCTYPE',
        notes='480363 bytes observed 2026-08-02. THE PUBLISHED '
              'LINK carries a ?tmstv= cache-buster; it was tested '
              'WITHOUT it and returned byte-identical content, so '
              'the stable form is seeded. Content signature is the '
              'ZIP magic (an xlsx is a ZIP), which is also what '
              'catches an HTML error page served as 200. The '
              'sheet is read by climate.xlsx_reader - openpyxl is '
              'NOT installed and one file a year does not justify '
              'a new pin and an image rebuild.'),
    _ep('cdc-life-expectancy',
        'US life expectancy at birth, 1900-',
        'cdc-nchs-vital', 'https://data.cdc.gov/resource',
        'w9j2-ggv5.json', 'json', '[', 100,
        'Life expectancy at birth and age-adjusted death rates by '
        'year, race and sex.',
        params=json.dumps({'limit': '5000'}),
        citation=('CDC/NCHS. Death rates and life expectancy at '
                  'birth. data.cdc.gov dataset w9j2-ggv5.'),
        license_note='US federal public-domain data.',
        reject='<!DOCTYPE',
        notes='Socrata JSON; 1900 = 47.3 years observed '
              '2026-08-02. Life expectancy is here as CONTEXT for '
              'the human-history view, never as something to '
              'regress against CO2.'),
]


def seed_climate_sources(manager):
    """GovSource rows then the endpoints that name them.

    Both go through upsert_seed_pairs rather than the legacy
    insert-only pass: these rows gained fields (responseFormat,
    contentSignature, ...) after the class already existed, and
    insert-only seeding never converges a changed row - the
    ten-strikes gotcha.
    """
    from dmvdata.gov_sources import GovSource
    from polariApiProfiler.apiEndpoint import APIEndpoint
    return upsert_seed_pairs(manager, [
        ('GovSource', GovSource, SEED_CLIMATE_GOV_SOURCES),
        ('APIEndpoint', APIEndpoint, SEED_CLIMATE_ENDPOINTS),
    ], tag='ClimateSourceSeed')


def endpoint_by_name(manager, name):
    from composition.data_refs import rows
    for row in rows(manager, 'APIEndpoint'):
        if getattr(row, 'name', '') == name:
            return row
    return None


def source_catalog(manager):
    """Every climate source with the endpoints under it, for the
    page's citation section."""
    from composition.data_refs import rows
    eps = {}
    for row in rows(manager, 'APIEndpoint'):
        eps[getattr(row, 'name', '')] = row
    out = []
    for src in SEED_CLIMATE_GOV_SOURCES:
        names = json.loads(src['api_endpoint_names_json'] or '[]')
        out.append({
            'name': src['name'], 'acronym': src['acronym'],
            'fullName': src['full_name'], 'agency': src['agency'],
            'website': src['official_website'],
            'portal': src['data_portal_url'],
            'description': src['description'],
            'notes': src['notes'],
            'endpoints': [{
                'name': n,
                'displayName': getattr(eps.get(n), 'displayName', n),
                'citation': getattr(eps.get(n), 'citationText', ''),
                'verifiedOn': getattr(eps.get(n), 'verifiedOn', ''),
                'format': getattr(eps.get(n), 'responseFormat', ''),
            } for n in names],
        })
    return {'ok': True, 'sources': out, 'count': len(out),
            'note': 'every URL on these rows was fetched live on '
                    + VERIFIED + ' and returned the real payload; '
                    're-verification is a maintenance task, not a '
                    'one-off'}

#: endpoint name -> the source row that publishes it, ACROSS
#: registries. The GovSource rows carry their own endpoint lists,
#: but two publishers here are not governments (ASHRAE and the
#: Global Carbon Project are in the nonprofit registry), so a
#: gov-only lookup would leave the carbon budget ownerless. This
#: map is the single place that answers "who publishes this
#: endpoint" regardless of which registry the answer lives in.
ENDPOINT_SOURCE = {
    'noaa-co2-annmean-mlo': 'noaa-gml',
    'noaa-co2-gr-mlo': 'noaa-gml',
    'noaa-co2-annmean-global': 'noaa-gml',
    'noaa-co2-gr-global': 'noaa-gml',
    'ncei-antarctica-co2-composite': 'noaa-ncei-paleo',
    'ncei-law-dome-co2': 'noaa-ncei-paleo',
    'nhanes-biopro-xpt': 'cdc-nchs-nhanes',
    'nhanes-dpq-xpt': 'cdc-nchs-nhanes',
    'cdc-life-expectancy': 'cdc-nchs-vital',
    'gcb-global-carbon-budget': 'global-carbon-project-org',
}


def source_of_endpoint(endpoint_name):
    """Who publishes this endpoint, whatever registry they are in.
    Returns '' rather than guessing when the map has no entry."""
    return ENDPOINT_SOURCE.get(endpoint_name, '')

