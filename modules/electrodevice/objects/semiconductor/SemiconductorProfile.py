"""
@module electrodevice.objects.semiconductor.SemiconductorProfile

Row class SemiconductorProfile of the electrodevice module — one class per file (design §7), split
from semiconductor_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class SemiconductorProfile(treeObject):
    """One material variant's derived semiconductor character."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        material: str = '',
        # Claimed variant — the validator checks the DERIVED carrier
        # type against this claim.
        variant: str = 'intrinsic',
        # The executable msci DFT model + the pristine reference.
        sim_model: str = '',
        reference_model: str = '',
        # Derived (never hand-set):
        homo_ev: float = 0.0,
        lumo_ev: float = 0.0,
        gap_ev: float = 0.0,
        level_shift_ev: float = 0.0,
        carrier_type: str = '',
        derived_at: str = '',
        provenance_json: str = '{}',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.material = material
        self.variant = variant
        self.sim_model = sim_model
        self.reference_model = reference_model
        self.homo_ev = homo_ev
        self.lumo_ev = lumo_ev
        self.gap_ev = gap_ev
        self.level_shift_ev = level_shift_ev
        self.carrier_type = carrier_type
        self.derived_at = derived_at
        self.provenance_json = provenance_json
        self.notes = notes
