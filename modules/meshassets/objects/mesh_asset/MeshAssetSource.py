"""
@module meshassets.objects.mesh_asset.MeshAssetSource

Row class MeshAssetSource of the meshassets module — one class per file (design §7), split
from mesh_asset_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit
from meshassets.objects.mesh_asset._shared import VERIFICATION_METHODS

class MeshAssetSource(treeObject):
    """A PUBLISHER of assets (a site, a repo, a pack) plus the
    licence finding for it — established once, cited by every asset
    row beneath it."""

    @treeObjectInit
    def __init__(self, name='', display_name='', url='',
                 author='', license_spdx='NONE',
                 license_url='', license_statement='',
                 verification_method='not-checked',
                 verified_at='', approximation_valid=True,
                 formats_json='[]', is_prior=True,
                 provenance_id='', notes='', manager=None):
        self.name = name
        self.display_name = display_name
        self.url = url
        #: The CREDITED author — the 'A' of the TASL attribution
        #: (Title, Author, Source, Licence) that CC asks for. Blank
        #: where a licence needs attribution is a GAP the citation
        #: record REPORTS rather than papering over with the site
        #: name.
        self.author = author
        #: Canonical licence deed/text URL, so a citation can link
        #: the terms rather than just naming them.
        self.license_url = license_url
        #: SPDX id, or 'public-domain', or 'NONE' when the publisher
        #: declares nothing (which is a FINDING, not a blank).
        self.license_spdx = license_spdx
        #: The publisher's own words, quoted. A paraphrase is how
        #: "open source" ends up meaning nothing.
        self.license_statement = license_statement
        self.verification_method = (
            verification_method
            if verification_method in VERIFICATION_METHODS
            else 'not-checked')
        self.verified_at = verified_at
        #: FALSE for subjects where "close enough" is WRONG — gears
        #: being the case in hand: an approximate gear does not
        #: mesh. Reports refuse to offer such assets as stand-ins.
        self.approximation_valid = approximation_valid
        self.formats_json = formats_json
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
