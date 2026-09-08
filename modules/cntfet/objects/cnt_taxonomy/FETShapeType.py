"""
@module cntfet.objects.cnt_taxonomy.FETShapeType

Row class FETShapeType of the cntfet module — one class per file (design §7), split
from cnt_taxonomy_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class FETShapeType(treeObject):
    """A FET gate SHAPE as a row: how many sides the gate couples,
    the electrostatic scale-length formula (data), and typical
    n_ss / DIBL priors."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        display_name: str = '',
        description: str = '',
        gate_coupling: str = 'single',
        scale_length_formula: str = '',
        scale_length_source: str = '',
        typical_n_ss: float = 1.0,
        typical_dibl_mv_per_v: float = 0.0,
        priors_source: str = '',
        materials_json: str = '[]',
        complementary_capable: bool = True,
        complementary_how: str = '',
        notes: str = '',
        origin: str = 'seeded',
        is_prior: bool = True,
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.description = description
        self.gate_coupling = gate_coupling
        self.scale_length_formula = scale_length_formula
        self.scale_length_source = scale_length_source
        self.typical_n_ss = typical_n_ss
        self.typical_dibl_mv_per_v = typical_dibl_mv_per_v
        self.priors_source = priors_source
        self.materials_json = materials_json
        self.complementary_capable = complementary_capable
        self.complementary_how = complementary_how
        self.notes = notes
        self.origin = origin
        self.is_prior = is_prior
