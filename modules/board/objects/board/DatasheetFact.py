"""
@module board.objects.board.DatasheetFact

DatasheetFact — one class per file (design §7).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class DatasheetFact(treeObject):
    """What it is: One number or string taken from a vendor document, with provenance (plan §8a, derive-or-cite):
    the document, its revision, page/table (or line), and a URL. Our own boards later inherit facts with their sources.
    Related concepts: `BoardDefinition` (board), the limits a FirmwareBuild is checked against.
    """

    @treeObjectInit
    def __init__(self, name: str = '', board: str = '', fact_key: str = '', value: str = '', unit: str = '',
                 document: str = '', revision: str = '', page_table: str = '', url: str = '', notes: str = '',
                 manager=None):
        self.name = name  # '<board>:<fact key>'
        self.board = board
        self.fact_key = fact_key
        self.value = value
        self.unit = unit
        self.document = document
        self.revision = revision
        self.page_table = page_table
        self.url = url
        self.notes = notes
