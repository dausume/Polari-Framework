"""
@module suiteapps.objects.suiteapps.SuiteContract

SuiteContract — an object class two parts pass between them through Polari.
"""
from objectTreeDecorators import treeObject, treeObjectInit


class SuiteContract(treeObject):
    """What it is: one seam inside a suite: the row CLASS one part produces
    and another consumes (a `SliceJob` from the slicer to the printer; a
    `MoldDefinition` from the mold step to the slicer), the direction, and
    the module that OWNS the class. Parts never hand each other files by
    path — they write rows the next part reads, so every step is on the
    tree and the provenance log.
    Related concepts: `SuitePart`, the owning module's objects.
    How it is derived: hand-declared per suite; `conform` checks the class
    exists in the owning module's manifest.
    """

    @treeObjectInit
    def __init__(self, name: str = '', suite: str = '', object_class: str = '', owner_module: str = '',
                 producer: str = '', consumer: str = '', description: str = '', notes: str = ''):
        self.name = name
        self.suite = suite
        self.object_class = object_class
        self.owner_module = owner_module
        self.producer = producer
        self.consumer = consumer
        self.description = description
        self.notes = notes
