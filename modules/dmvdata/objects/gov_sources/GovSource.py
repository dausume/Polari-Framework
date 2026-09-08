"""
@module dmvdata.objects.gov_sources.GovSource

Row class GovSource of the dmvdata module — one class per file (design §7), split
from gov_sources_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class GovSource(treeObject):
    """One official government source — the glossary row."""

    @treeObjectInit
    def __init__(self, name: str = '', acronym: str = '',
                 full_name: str = '', agency: str = '',
                 # '' for a top-level agency; else the GovSource this
                 # product hangs under (ACS -> census-bureau).
                 parent_source: str = '',
                 jurisdiction: str = 'federal',
                 official_website: str = '',
                 data_portal_url: str = '',
                 # True when retrieving DATA requires a key; the env
                 # knob that supplies it lives in api_key_env (a
                 # POINTER, never a literal key — repos are public).
                 requires_api_key: bool = False,
                 api_key_env: str = '',
                 # JSON list of APIEndpoint row names that pull here.
                 api_endpoint_names_json: str = '[]',
                 description: str = '', notes: str = '',
                 manager=None):
        self.name = name
        self.acronym = acronym
        self.full_name = full_name
        self.agency = agency
        self.parent_source = parent_source
        self.jurisdiction = jurisdiction
        self.official_website = official_website
        self.data_portal_url = data_portal_url
        self.requires_api_key = requires_api_key
        self.api_key_env = api_key_env
        self.api_endpoint_names_json = api_endpoint_names_json
        self.description = description
        self.notes = notes
