"""
@module dmvdata.objects.legal_sources.CompanySource

Row class CompanySource of the dmvdata module — one class per file (design §7), split
from legal_sources_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

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
