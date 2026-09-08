"""
@module cntfet.objects.cnt_fields.FETFieldSample

Row class FETFieldSample of the cntfet module — one class per file (design §7), split
from cnt_fields_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit
from cntfet.objects.cnt_fields._shared import FIDELITY

class FETFieldSample(treeObject):
    """One cell of a field sample along the tube axis — the row the
    `FETFieldSample-3d` binding renders as a banded cube; vg_v is
    the scrubber's 'instant'. simulation_run_ref =
    'fet-fields:{device}:{field}' is the scene's row filter
    (?run=)."""

    @treeObjectInit
    def __init__(self, name='', device='', field='', vg_v=0.0,
                 vd_v=0.0, x_nm=0.0, pos_x=0.0, pos_y=0.0, pos_z=0.0,
                 cell_nm=0.0, cell_scene=0.0, value=0.0, band=-1,
                 band_label='', band_style='fet-band-none',
                 material='', simulation_run_ref='', fidelity=FIDELITY,
                 generated_at='', manager=None):
        self.name = name
        self.device = device
        self.field = field
        self.vg_v = vg_v
        self.vd_v = vd_v
        self.x_nm = x_nm
        self.pos_x = pos_x
        self.pos_y = pos_y
        self.pos_z = pos_z
        self.cell_nm = cell_nm
        self.cell_scene = cell_scene
        self.value = value
        self.band = band
        self.band_label = band_label
        self.band_style = band_style
        self.material = material
        self.simulation_run_ref = simulation_run_ref
        self.fidelity = fidelity
        self.generated_at = generated_at
