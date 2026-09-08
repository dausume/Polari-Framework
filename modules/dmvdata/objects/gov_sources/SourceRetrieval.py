"""
@module dmvdata.objects.gov_sources.SourceRetrieval

Row class SourceRetrieval of the dmvdata module — one class per file (design §7), split
from gov_sources_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class SourceRetrieval(treeObject):
    """One duplication event: this Polari instance copied data from
    a source — when, and through whom (group or individual)."""

    @treeObjectInit
    def __init__(self, name: str = '', source_name: str = '',
                 endpoint_name: str = '', what: str = '',
                 retrieved_at: str = '',
                 # The individual (Contributor name) who ran it.
                 retrieved_by: str = '',
                 # The ScoreGroup on whose behalf — '' means the
                 # individual acted alone.
                 retrieved_by_group: str = '',
                 row_count: int = 0,
                 # ALWAYS the redacted form for keyed endpoints.
                 provenance_url: str = '',
                 notes: str = '', manager=None):
        self.name = name
        self.source_name = source_name
        self.endpoint_name = endpoint_name
        self.what = what
        self.retrieved_at = retrieved_at
        self.retrieved_by = retrieved_by
        self.retrieved_by_group = retrieved_by_group
        self.row_count = row_count
        self.provenance_url = provenance_url
        self.notes = notes
