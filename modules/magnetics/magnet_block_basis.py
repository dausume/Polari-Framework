"""
@module magnetics.magnet_block_basis

mag-4: SLOT-MATRIX ASSEMBLY AS DATA (Dustin: "configure block sizes
(sometimes varying block sizes in one design) and then 'slot' them
into place to make a matrix that is solidified by a thin sol-gel
mortar which we selectively make to be magnetic or not").

- BlockSizeVariant = the block-geometry vocabulary (MIXED sizes in
  one layout are first-class, like masonry bonds).
- BlockLayoutDefinition + BlockPlacement = the slot grid: each
  placement names its slot (integer x/y/z), its variant, its
  MATERIAL (a Section-A catalog row — theoretical materials ride
  their watermark/gates), optional coil winding, and interlocks.
- JointMortarAssignment = SELECTIVE MORTAR PER JOINT: magnetic
  mortar (flux passes) or plain (flux fence). Field routing is the
  LAYOUT; containment is a boundary course of plain joints.

The reluctance network GENERATES from these rows (magnet_layout) —
mag-3 hand-authored circuits stay possible, the matrix is the
primary authoring surface.

@consumers magnetics.custom.magnet_layout, magnetics.magnet_api,
polariServer (registration + seed)
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/magnet_block/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

from objectTreeDecorators import treeObject, treeObjectInit

from magnetics.objects.magnet_block._shared import BLOCK_SHAPE_KINDS, SEED_BLOCK_LAYOUTS, SEED_BLOCK_PLACEMENTS, SEED_BLOCK_VARIANTS, SEED_JOINT_MORTARS  # noqa: F401
from magnetics.objects.magnet_block.BlockSizeVariant import BlockSizeVariant  # noqa: F401
from magnetics.objects.magnet_block.BlockLayoutDefinition import BlockLayoutDefinition  # noqa: F401
from magnetics.objects.magnet_block.BlockPlacement import BlockPlacement  # noqa: F401
from magnetics.objects.magnet_block.JointMortarAssignment import JointMortarAssignment  # noqa: F401
