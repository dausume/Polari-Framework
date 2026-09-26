"""
@module computelod.objects.computelod.ComputeKind

Row class ComputeKind of the computelod module — one class per file. The class docstring is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit


class ComputeKind(treeObject):
    """A SPECIALIZATION WITHIN A RUNG (plan §F1): a kind never creates a rung — tensor-array is a microarchitecture kind, not a level. Seeded as rows so a new kind is data."""

    plain_words = ('A kind is a variety within a rung, such as a particular processor family or a particular logic cell '
                   'library. It refines a rung; it never adds a new one.')

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        description: str = '',
        rung: str = '',
        title: str = '',
        design_kind_ref: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.description = description
        self.rung = rung  # ComputeLOD.name
        self.title = title
        self.design_kind_ref = design_kind_ref  # the microchip subsystem kind this maps to, when one exists
        self.notes = notes
