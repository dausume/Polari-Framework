"""
@module techtree.objects.techtree.TechTreeDefinition

Row class TechTreeDefinition of the techtree module — one class per file (design §7), split
from techtree_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class TechTreeDefinition(treeObject):
    """One tech tree = one DOMAIN of technologies (tt-8): e.g.
    'Electronics / Microelectronics', 'Raw Supply Chain', 'Open
    Source Economy & Politics'. Configurable per org (B6): a
    business's tree is the set of technologies it depends on to do
    business. Trees flagged is_baseline are the OSEB's domain
    components — reaching the end of ALL of them, combined, is the
    Open Source Economic Baseline (baseline_report)."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        # Display title ('' = derive from name), e.g.
        # 'Electronics / Microelectronics'.
        title: str = '',
        # The org/business this tree belongs to ('' = unowned/shared).
        owner: str = '',
        description: str = '',
        is_active: bool = False,
        # This tree is one of the OSEB's domain components; the
        # baseline is the COMBINATION of all such trees complete.
        is_baseline: bool = False,
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.title = title
        self.owner = owner
        self.description = description
        self.is_active = is_active
        self.is_baseline = is_baseline
        self.notes = notes
