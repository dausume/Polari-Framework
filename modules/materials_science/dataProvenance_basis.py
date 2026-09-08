"""
@module materials_science.dataProvenance_basis

The dataProvenance object rows of the materials-science module, consolidated
(sap-2b, 2026-09-08) from the legacy one-class-per-file subpackage
`dataProvenance/` (dataProvenance.py, dataSource.py) into the standard <concept>_basis.py.
"""
from objectTreeDecorators import treeObject, treeObjectInit


# ---- from dataProvenance/dataProvenance.py
class DataProvenance(treeObject):
    """
    Credibility metadata container for any data point in the system.

    Attributes:
        version: Version string for this provenance record
        credibilityLevel: Overall credibility (verified, peer_reviewed,
            manufacturer_stated, community_consensus, unverified)
        sourceIds: Comma-separated list of DataSource IDs backing this record
        notes: Additional notes about data credibility
    """

    @treeObjectInit
    def __init__(self,
                 manager=None,
                 branch=None,
                 id=None,
                 version='',
                 credibilityLevel='unverified',
                 sourceIds='',
                 notes=''):
        treeObject.__init__(self, manager=manager, branch=branch, id=id)
        self.version = version
        self.credibilityLevel = credibilityLevel
        self.sourceIds = sourceIds
        self.notes = notes

    def __repr__(self):
        return f"DataProvenance(id='{getattr(self, 'id', '?')}', credibility='{getattr(self, 'credibilityLevel', '?')}')"


# ---- from dataProvenance/dataSource.py
class DataSource(treeObject):
    """
    An individual data source citation.

    Attributes:
        sourceType: Type of source (llm_generated, research_paper,
            manufacturer_datasheet, experimental_testing,
            community_measurement, personal_observation)
        sourceName: Name/title of the source
        sourceReference: URL, DOI, or ISBN reference
        sourceAuthor: Author(s) of the source
        sourceDate: Date of publication/measurement
        notes: Additional notes about this source
    """

    @treeObjectInit
    def __init__(self,
                 manager=None,
                 branch=None,
                 id=None,
                 sourceType='',
                 sourceName='',
                 sourceReference='',
                 sourceAuthor='',
                 sourceDate='',
                 notes=''):
        treeObject.__init__(self, manager=manager, branch=branch, id=id)
        self.sourceType = sourceType
        self.sourceName = sourceName
        self.sourceReference = sourceReference
        self.sourceAuthor = sourceAuthor
        self.sourceDate = sourceDate
        self.notes = notes

    def __repr__(self):
        return f"DataSource(id='{getattr(self, 'id', '?')}', type='{getattr(self, 'sourceType', '?')}', name='{getattr(self, 'sourceName', '?')}')"

