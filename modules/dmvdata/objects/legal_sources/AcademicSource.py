"""
@module dmvdata.objects.legal_sources.AcademicSource

Row class AcademicSource of the dmvdata module — one class per file (design §7), split
from legal_sources_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

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
