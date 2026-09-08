"""
@module magnetics.objects.magnet_block.BlockPlacement

Row class BlockPlacement of the magnetics module — one class per file (design §7), split
from magnet_block_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class BlockPlacement(treeObject):
    """One block slotted into the matrix. slot_json = {'x','y','z'}
    integers; adjacency = unit distance on one axis."""

    @treeObjectInit
    def __init__(self, name='', layout_name='', slot_json='{}',
                 variant_ref='', material_ref='', coil_json='{}',
                 is_prior=True, provenance_id='', notes='',
                 manager=None):
        self.name = name
        self.layout_name = layout_name
        self.slot_json = slot_json
        #: BlockSizeVariant.name.
        self.variant_ref = variant_ref
        #: MagneticMaterialOption.name — gates/watermarks ride the
        #: catalog row (a theoretical material simulates, refuses
        #: costing).
        self.material_ref = material_ref
        #: Optional winding on THIS block: {'turns': N, 'amps': I}.
        #: v1 rule: a wound block must have exactly TWO magnetic
        #: joints (a limb) — winding a junction block is ambiguous
        #: and refuses honestly.
        self.coil_json = coil_json
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
