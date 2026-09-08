"""
@module magnetics.objects.magnet_block.BlockSizeVariant

Row class BlockSizeVariant of the magnetics module — one class per file (design §7), split
from magnet_block_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit
from magnetics.objects.magnet_block._shared import BLOCK_SHAPE_KINDS

class BlockSizeVariant(treeObject):
    """One block geometry in the vocabulary. dims_json per shape:
    brick/half-brick/tooth/bearing-seat {x_m, y_m, z_m};
    wedge {x_m, y_m, z_m} (half-brick volume, triangular section);
    arc-segment/disk-sector {r_in_m, r_out_m, angle_deg, thick_m}."""

    @treeObjectInit
    def __init__(self, name='', display_name='', shape_kind='brick',
                 dims_json='{}', interlock_json='[]',
                 is_prior=True, provenance_id='', notes='',
                 manager=None):
        self.name = name
        self.display_name = display_name
        self.shape_kind = (shape_kind
                           if shape_kind in BLOCK_SHAPE_KINDS
                           else 'brick')
        self.dims_json = dims_json
        #: JSON list of interlock features ('tongue-x', 'groove-x',
        #: 'dowel-pocket', ...) — dry-fit rigidity BEFORE mortar.
        self.interlock_json = interlock_json
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
