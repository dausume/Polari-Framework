"""
@module dmvdata.objects.legal_sources.IndividualSource

Row class IndividualSource of the dmvdata module — one class per file (design §7), split
from legal_sources_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

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
