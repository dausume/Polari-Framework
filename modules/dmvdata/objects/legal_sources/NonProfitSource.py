"""
@module dmvdata.objects.legal_sources.NonProfitSource

Row class NonProfitSource of the dmvdata module — one class per file (design §7), split
from legal_sources_basis.py (sap-2c). The class docstring below is the explanation.
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
