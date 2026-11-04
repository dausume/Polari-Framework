"""
@module mech.objects.catalog.DimensionSource

Row class DimensionSource of the mech module — one class per file (design §7).
mxc-1 (MECH_FREECAD_INTERCHANGE_PLAN §3.1; D-mxc-10: the licence field
names are MeshAssetSource's, so this is a sibling of that row, not a third
licence gate). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit


class DimensionSource(treeObject):
    """ONE IMPORTED TABLE: the upstream file every dimension in a family
    was read from, pinned to a commit and a sha256, with the licence
    finding stated in the publisher's own words. A family without a
    DimensionSource is a family whose numbers came from nowhere — the
    selftest refuses that."""

    @treeObjectInit
    def __init__(self, name='', display_name='', url='', commit='',
                 path='', sha256='', bytes=-1, fetched='',
                 license_spdx='NONE', license_url='',
                 license_statement='', verification_method='not-checked',
                 rows_imported=-1, rows_rejected_json='[]',
                 is_prior=True, provenance_id='', notes='',
                 manager=None):
        #: Composed key: '<library>:<file>' e.g. 'fasteners-wb:iso4762def.csv'.
        self.name = name
        self.display_name = display_name
        #: Repository / page the file was taken from (the blob URL at the
        #: pinned commit when there is one).
        self.url = url
        #: Full upstream commit sha the file was fetched at ('' = not a
        #: git source, e.g. the hand-entered drawer-slide table).
        self.commit = commit
        #: Path of the stored verbatim copy, relative to modules/mech/
        #: (custom/upstream/<source>/...). '' when nothing was fetched.
        self.path = path
        #: sha256 of the stored file; '' = none stored.
        self.sha256 = sha256
        #: Size of the stored file in bytes; -1 = none stored.
        self.bytes = bytes
        #: ISO date the fetch happened ('' = hand-entered).
        self.fetched = fetched
        #: SPDX id, or 'NONE' when the publisher declares nothing (a
        #: FINDING, not a blank) — MeshAssetSource's convention.
        self.license_spdx = license_spdx
        #: Canonical licence text URL / the copied LICENSE beside the file.
        self.license_url = license_url
        #: The publisher's own words, quoted — where the licence is STATED.
        self.license_statement = license_statement
        #: meshassets VERIFICATION_METHODS vocabulary: how the finding was
        #: made (e.g. 'license-file-read', 'not-checked').
        self.verification_method = verification_method
        #: How many dimension rows the importer took from this file
        #: (-1 = not an importer source).
        self.rows_imported = rows_imported
        #: [{'row', 'why'}] — rows the importer refused, by name, with why
        #: (e.g. bracketed non-preferred sizes "(M14)" are kept but
        #: flagged; out-of-scope sizes above M8 are not variants).
        self.rows_rejected_json = rows_rejected_json
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
