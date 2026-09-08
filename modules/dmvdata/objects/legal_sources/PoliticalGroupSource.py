"""
@module dmvdata.objects.legal_sources.PoliticalGroupSource

Row class PoliticalGroupSource of the dmvdata module — one class per file (design §7), split
from legal_sources_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

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
