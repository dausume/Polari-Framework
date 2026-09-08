"""
@module casting.objects.fill_sim.MoldFillSimState

Row class MoldFillSimState of the casting module — one class per file (design §7), split
from fill_sim_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class MoldFillSimState(treeObject):
    """One rendered voxel of one fill run at one recorded level —
    the WaxPrintSimState idiom (rows are 3D-viewable; the scene
    binding lands with cast-9)."""

    simulation_definition_name = 'mold-fill'

    @treeObjectInit
    def __init__(self, name: str = '', simulation_run_ref: str = '',
                 mold_ref: str = '', step: int = 0, time: float = 0.0,
                 pos_x: float = 0.0, pos_y: float = 0.0,
                 pos_z: float = 0.0,
                 # 0 empty · 1 filled · 2 channel · 3 trapped ·
                 # 4 unfed
                 render_state: int = 0,
                 # cell edge (cm) — the scene binding scales cubes
                 # by it so the voxel cloud is dimensionally true.
                 cell_cm: float = 0.0,
                 manager=None):
        self.name = name
        self.simulation_run_ref = simulation_run_ref
        self.mold_ref = mold_ref
        self.step = step
        self.time = time
        self.pos_x = pos_x
        self.pos_y = pos_y
        self.pos_z = pos_z
        self.render_state = render_state
        self.cell_cm = cell_cm
