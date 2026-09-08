"""
@module dmvdata.legal_sources_basis

The NON-GOVERNMENT legal source types (Dustin 2026-07-16: "add
NonProfitSource, CompanySource, PoliticalGroupSource, and
IndividualSource, basically varying legal source types") — siblings
of `GovSource` sharing its common core (name, short name, full name,
websites, key knobs, endpoint links) plus per-type LEGAL-IDENTITY
fields that point at the OFFICIAL verification registry for that
legal form:

  NonProfitSource       -> IRS Tax Exempt Organization Search (EIN)
  CompanySource         -> SEC EDGAR / state corporate registry
  PoliticalGroupSource  -> FEC committee lookup
  IndividualSource      -> a Polari Contributor row (platform users)

One machinery, five tables: the glossary/term-origin/retrieval/
credibility functions in dmvdata.gov_sources_basis span every source kind
via its SOURCE_TABLES registry. Non-government sources are always
FRAMED as such in reports — they are never presented as official
statistic origins.

Seeds carry ONLY organizations the plan doc already references, and
never invent registry identifiers: an unknown EIN/FEC id stays ''
with the lookup URL pointing at the official search tool.

@consumers
  - dmvdata.gov_sources_basis (SOURCE_TABLES machinery)
  - polariServer (registration + seed, wired by the main session)
"""

from objectTreeDecorators import treeObject, treeObjectInit


class NonProfitSource(treeObject):
    """A nonprofit organization as a data source — verified against
    the IRS exempt-organization registry, never presented as an
    official statistic origin."""

    SOURCE_KIND = 'nonprofit'

    @treeObjectInit
    def __init__(self, name: str = '', short_name: str = '',
                 full_name: str = '', official_website: str = '',
                 data_portal_url: str = '',
                 requires_api_key: bool = False,
                 api_key_env: str = '',
                 api_endpoint_names_json: str = '[]',
                 # Legal identity: '' when not looked up — NEVER
                 # invented; the lookup URL is the act.
                 ein: str = '',
                 irs_subsection: str = '',
                 state_registered: str = '',
                 irs_lookup_url: str = 'https://apps.irs.gov/app/eos/',
                 funding_transparency_url: str = '',
                 description: str = '', notes: str = '',
                 manager=None):
        self.name = name
        self.short_name = short_name
        self.full_name = full_name
        self.official_website = official_website
        self.data_portal_url = data_portal_url
        self.requires_api_key = requires_api_key
        self.api_key_env = api_key_env
        self.api_endpoint_names_json = api_endpoint_names_json
        self.ein = ein
        self.irs_subsection = irs_subsection
        self.state_registered = state_registered
        self.irs_lookup_url = irs_lookup_url
        self.funding_transparency_url = funding_transparency_url
        self.description = description
        self.notes = notes


class CompanySource(treeObject):
    """A company as a data source — verified against SEC EDGAR or
    the state corporate registry."""

    SOURCE_KIND = 'company'

    @treeObjectInit
    def __init__(self, name: str = '', short_name: str = '',
                 full_name: str = '', official_website: str = '',
                 data_portal_url: str = '',
                 requires_api_key: bool = False,
                 api_key_env: str = '',
                 api_endpoint_names_json: str = '[]',
                 legal_name: str = '',
                 state_of_incorporation: str = '',
                 # SEC CIK or a state registry number — '' when not
                 # looked up, never invented.
                 registry_id: str = '',
                 registry_url: str =
                 'https://www.sec.gov/cgi-bin/browse-edgar',
                 ticker: str = '',  # '' when private.
                 industry: str = '',
                 description: str = '', notes: str = '',
                 manager=None):
        self.name = name
        self.short_name = short_name
        self.full_name = full_name
        self.official_website = official_website
        self.data_portal_url = data_portal_url
        self.requires_api_key = requires_api_key
        self.api_key_env = api_key_env
        self.api_endpoint_names_json = api_endpoint_names_json
        self.legal_name = legal_name
        self.state_of_incorporation = state_of_incorporation
        self.registry_id = registry_id
        self.registry_url = registry_url
        self.ticker = ticker
        self.industry = industry
        self.description = description
        self.notes = notes


POLITICAL_GROUP_KINDS = ('party', 'pac', 'campaign', 'advocacy')


class PoliticalGroupSource(treeObject):
    """A political group as a data source — positions/platforms are
    inherently interested documents; the FEC registry is the legal
    identity anchor for committees."""

    SOURCE_KIND = 'political-group'

    @treeObjectInit
    def __init__(self, name: str = '', short_name: str = '',
                 full_name: str = '', official_website: str = '',
                 data_portal_url: str = '',
                 requires_api_key: bool = False,
                 api_key_env: str = '',
                 api_endpoint_names_json: str = '[]',
                 # POLITICAL_GROUP_KINDS entry.
                 group_kind: str = 'advocacy',
                 # '' when not an FEC-registered committee (or not
                 # looked up) — never invented.
                 fec_committee_id: str = '',
                 fec_lookup_url: str =
                 'https://www.fec.gov/data/committees/',
                 jurisdiction_scope: str = 'national',
                 description: str = '', notes: str = '',
                 manager=None):
        self.name = name
        self.short_name = short_name
        self.full_name = full_name
        self.official_website = official_website
        self.data_portal_url = data_portal_url
        self.requires_api_key = requires_api_key
        self.api_key_env = api_key_env
        self.api_endpoint_names_json = api_endpoint_names_json
        self.group_kind = group_kind
        self.fec_committee_id = fec_committee_id
        self.fec_lookup_url = fec_lookup_url
        self.jurisdiction_scope = jurisdiction_scope
        self.description = description
        self.notes = notes


class IndividualSource(treeObject):
    """An individual person as a data source. When the person is a
    Polari user, contributor_name bridges to their Contributor row
    (and so to the attribution/credibility machinery)."""

    SOURCE_KIND = 'individual'

    @treeObjectInit
    def __init__(self, name: str = '', short_name: str = '',
                 full_name: str = '', official_website: str = '',
                 data_portal_url: str = '',
                 requires_api_key: bool = False,
                 api_key_env: str = '',
                 api_endpoint_names_json: str = '[]',
                 person_name: str = '',
                 affiliation: str = '',
                 credentials: str = '',
                 # '' or a Polari Contributor row name.
                 contributor_name: str = '',
                 description: str = '', notes: str = '',
                 manager=None):
        self.name = name
        self.short_name = short_name
        self.full_name = full_name
        self.official_website = official_website
        self.data_portal_url = data_portal_url
        self.requires_api_key = requires_api_key
        self.api_key_env = api_key_env
        self.api_endpoint_names_json = api_endpoint_names_json
        self.person_name = person_name
        self.affiliation = affiliation
        self.credentials = credentials
        self.contributor_name = contributor_name
        self.description = description
        self.notes = notes


class AcademicSource(treeObject):
    """One peer-reviewed publication as a source.

    The granularity is the ARTICLE, not the journal: "Environmental
    Health Perspectives" is not a claim, and a specific study with
    a specific design and sample size is. Citing the journal alone
    is how a contested finding acquires the authority of everything
    else the journal ever printed.

    `replication_status` exists because a study that failed to
    replicate is still a real citation - it just is not the same
    evidence it was on publication day, and a source registry that
    cannot express that will keep presenting it as though it were.
    """

    SOURCE_KIND = 'academic'

    @treeObjectInit
    def __init__(self, name: str = '', short_name: str = '',
                 full_name: str = '', official_website: str = '',
                 data_portal_url: str = '',
                 requires_api_key: bool = False,
                 api_key_env: str = '',
                 api_endpoint_names_json: str = '[]',
                 # The article itself.
                 authors: str = '', journal: str = '',
                 year: int = 0, volume_pages: str = '',
                 doi: str = '', pubmed_id: str = '',
                 # True only when the venue is peer reviewed; a
                 # preprint or a conference abstract is NOT, and
                 # saying so is the point of the field.
                 peer_reviewed: bool = True,
                 # 'randomized-crossover' | 'chamber-exposure' |
                 # 'observational-cohort' | 'systematic-review' |
                 # 'meta-analysis' | 'ice-core-reconstruction' | ...
                 study_design: str = '',
                 sample_size: int = 0,
                 # 'replicated' | 'failed-to-replicate' |
                 # 'contested' | 'not-attempted' | 'not-applicable'
                 replication_status: str = 'not-attempted',
                 # Names of other AcademicSource rows that tried.
                 replication_refs_json: str = '[]',
                 funding_disclosure: str = '',
                 conflicts_declared: str = '',
                 description: str = '', notes: str = '',
                 manager=None):
        self.name = name
        self.short_name = short_name
        self.full_name = full_name
        self.official_website = official_website
        self.data_portal_url = data_portal_url
        self.requires_api_key = requires_api_key
        self.api_key_env = api_key_env
        self.api_endpoint_names_json = api_endpoint_names_json
        self.authors = authors
        self.journal = journal
        self.year = year
        self.volume_pages = volume_pages
        self.doi = doi
        self.pubmed_id = pubmed_id
        self.peer_reviewed = peer_reviewed
        self.study_design = study_design
        self.sample_size = sample_size
        self.replication_status = replication_status
        self.replication_refs_json = replication_refs_json
        self.funding_disclosure = funding_disclosure
        self.conflicts_declared = conflicts_declared
        self.description = description
        self.notes = notes


class JournalisticSource(treeObject):
    """A press or trade article as a source - including one written
    by a credentialed expert.

    THE CREDENTIAL AND THE VENUE ARE SEPARATE FACTS. A physician
    writing in a magazine brings real expertise AND is not
    submitting to peer review, and both halves have to survive into
    the citation or the reader cannot judge it. So the author's
    credentials, the outlet, whether an editor reviewed it, and
    whether it is opinion are four different fields.

    `primary_sources_json` is the important one: good journalism
    REPORTS ON primary research, so wherever the underlying studies
    are known they are named, and a claim can be followed to the
    evidence rather than stopping at the person who repeated it.
    An article with no reachable primary source is not disqualified
    - it is marked as such, which is a different and more useful
    thing than being dropped.
    """

    SOURCE_KIND = 'journalistic'

    @treeObjectInit
    def __init__(self, name: str = '', short_name: str = '',
                 full_name: str = '', official_website: str = '',
                 data_portal_url: str = '',
                 requires_api_key: bool = False,
                 api_key_env: str = '',
                 api_endpoint_names_json: str = '[]',
                 outlet: str = '', author_name: str = '',
                 # 'MD', 'MD PhD', 'RN', '' — as STATED by the
                 # outlet. Never inferred from a byline.
                 author_credentials: str = '',
                 author_affiliation: str = '',
                 published_date: str = '', article_url: str = '',
                 # Was there editorial/fact-check review at all?
                 editorially_reviewed: bool = False,
                 is_opinion: bool = False,
                 # AcademicSource row names this article reports on.
                 primary_sources_json: str = '[]',
                 # True when the piece states a claim for which no
                 # primary source could be located. Recorded, not
                 # hidden.
                 unsourced_claims_noted: bool = False,
                 # WHO BENEFITS IF THE READER BELIEVES THIS. A
                 # vendor blog arguing that the thing its product
                 # measures is dangerous is not thereby wrong - but
                 # a citation that omits the interest is hiding
                 # something the reader would want. '' means none
                 # known; it does NOT mean none was looked for.
                 commercial_interest: str = '',
                 publisher_sells: str = '',
                 description: str = '', notes: str = '',
                 manager=None):
        self.name = name
        self.short_name = short_name
        self.full_name = full_name
        self.official_website = official_website
        self.data_portal_url = data_portal_url
        self.requires_api_key = requires_api_key
        self.api_key_env = api_key_env
        self.api_endpoint_names_json = api_endpoint_names_json
        self.outlet = outlet
        self.author_name = author_name
        self.author_credentials = author_credentials
        self.author_affiliation = author_affiliation
        self.published_date = published_date
        self.article_url = article_url
        self.editorially_reviewed = editorially_reviewed
        self.is_opinion = is_opinion
        self.primary_sources_json = primary_sources_json
        self.unsourced_claims_noted = unsourced_claims_noted
        self.commercial_interest = commercial_interest
        self.publisher_sells = publisher_sells
        self.description = description
        self.notes = notes


_NOT_OFFICIAL = ('NOT an official government source — a '
                 'non-government proxy, framed as such wherever it '
                 'is cited.')


#: Nonprofits the plan doc already references as flagged proxies.
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

#: Political groups as POSITION sources (platforms are position
#: documents, not statistics) — neutral, both major parties.
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

#: No company source is referenced by the plan yet — empty is the
#: honest seed (companies register at runtime or a later phase).
SEED_COMPANY_SOURCES = []

#: Individuals register at runtime, linked to their Contributor row
#: (contributor_name) — never seeded.
SEED_INDIVIDUAL_SOURCES = []
