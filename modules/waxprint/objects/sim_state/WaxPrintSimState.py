"""
@module waxprint.objects.sim_state.WaxPrintSimState

Row class WaxPrintSimState of the waxprint module — one class per file (design §7), split
from sim_state_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class WaxPrintSimState(treeObject):
    """One persisted build-height step of a wax-print run.

    Identity is composite on (simulation_run_ref, step); the runner names
    rows "<run>-wax-print-<step>". Membership in the wax-print simulation
    is declared by the class attribute.
    """

    simulation_definition_name = 'wax-print'

    # Config refs the no-code print-step reads (self.<ref>) to know which
    # rows to run the physics against — so the sim STEP is self-contained
    # no-code (WaxPrintOperation binds these into the print-step command).
    default_config_refs = {
        'assembly_ref': 'demo-auger-extruder',
        'feedstock_ref': 'mvw-natural-blend',
        'condition_ref': 'room-baseline',
    }

    default_initial_field_values = {
        'assembly_ref': 'demo-auger-extruder',
        'feedstock_ref': 'mvw-natural-blend',
        'condition_ref': 'room-baseline',
        'height_mm': 0.0,
        'substrate_temp_c': 22.0,
        'exit_temp_c': 0.0,
        'melt_fraction': 0.0,
        'nozzle_pressure_pa': 0.0,
        'voxel_xy_mm': 0.0,
        'voxel_z_mm': 0.0,
        'spread_mm': 0.0,
        'margin_mm': 0.0,
        't_solidify_s': 0.0,
        'warp_index': 0.0,
        'thermally_safe': 0.0,
        'printable': 0.0,
        'movements_viable': 0.0,
        'movements_total': 7.0,
        'resolution_ok': 0.0,
        # 0 = unsafe/unprintable, 1 = printable but coarse, 2 = printable +
        # meets the resolution target — drives the scene colour map.
        'render_state': 0.0,
        # render placement (mm — SimSpace3D world units), a stacked column
        'pos_x': 0.0,
        'pos_y': 0.0,
        'pos_z': 0.0,
    }

    field_save_policy = {k: 'core' for k in default_initial_field_values}

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        simulation_run_ref: str = '',
        step: int = 0,
        time: float = 0.0,
        assembly_ref: str = 'demo-auger-extruder',
        feedstock_ref: str = 'mvw-natural-blend',
        condition_ref: str = 'room-baseline',
        height_mm: float = 0.0,
        substrate_temp_c: float = 22.0,
        exit_temp_c: float = 0.0,
        melt_fraction: float = 0.0,
        nozzle_pressure_pa: float = 0.0,
        voxel_xy_mm: float = 0.0,
        voxel_z_mm: float = 0.0,
        spread_mm: float = 0.0,
        margin_mm: float = 0.0,
        t_solidify_s: float = 0.0,
        warp_index: float = 0.0,
        thermally_safe: float = 0.0,
        printable: float = 0.0,
        movements_viable: float = 0.0,
        movements_total: float = 7.0,
        resolution_ok: float = 0.0,
        render_state: float = 0.0,
        pos_x: float = 0.0,
        pos_y: float = 0.0,
        pos_z: float = 0.0,
        manager=None,
    ):
        self.name = name
        self.simulation_run_ref = simulation_run_ref
        self.step = step
        self.time = time
        self.assembly_ref = assembly_ref
        self.feedstock_ref = feedstock_ref
        self.condition_ref = condition_ref
        self.height_mm = height_mm
        self.substrate_temp_c = substrate_temp_c
        self.exit_temp_c = exit_temp_c
        self.melt_fraction = melt_fraction
        self.nozzle_pressure_pa = nozzle_pressure_pa
        self.voxel_xy_mm = voxel_xy_mm
        self.voxel_z_mm = voxel_z_mm
        self.spread_mm = spread_mm
        self.margin_mm = margin_mm
        self.t_solidify_s = t_solidify_s
        self.warp_index = warp_index
        self.thermally_safe = thermally_safe
        self.printable = printable
        self.movements_viable = movements_viable
        self.movements_total = movements_total
        self.resolution_ok = resolution_ok
        self.render_state = render_state
        self.pos_x = pos_x
        self.pos_y = pos_y
        self.pos_z = pos_z
