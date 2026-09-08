"""
@module magnetics.objects.magnet_block.BlockLayoutDefinition

Row class BlockLayoutDefinition of the magnetics module — one class per file (design §7), split
from magnet_block_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class BlockLayoutDefinition(treeObject):
    """One slotted matrix design (2D layers stacked to 3D)."""

    @treeObjectInit
    def __init__(self, name='', display_name='', description='',
                 grid_json='{}', is_prior=True, provenance_id='',
                 notes='', manager=None):
        self.name = name
        self.display_name = display_name
        self.description = description
        #: {'cols': N, 'rows': N, 'layers': N} — documentation of
        #: the intended envelope; placements carry the actual slots.
        self.grid_json = grid_json
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
