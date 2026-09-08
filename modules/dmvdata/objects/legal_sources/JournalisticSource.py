"""
@module dmvdata.objects.legal_sources.JournalisticSource

Row class JournalisticSource of the dmvdata module — one class per file (design §7), split
from legal_sources_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

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
