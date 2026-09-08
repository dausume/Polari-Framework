"""
@module testing.objects.parity_probe.Acct1ParityProbe

Row class Acct1ParityProbe of the testing module — one class per file (design §7), split
from parity_probe_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class Acct1ParityProbe(treeObject):
    @treeObjectInit
    def __init__(self, name: str = '', count: int = 0,
                 ratio: float = 0.0, note: str = '', manager=None):
        self.name = name
        self.count = count
        self.ratio = ratio
        self.note = note
