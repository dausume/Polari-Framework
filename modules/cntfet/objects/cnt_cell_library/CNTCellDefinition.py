"""
@module cntfet.objects.cnt_cell_library.CNTCellDefinition

Row class CNTCellDefinition of the cntfet module — one class per file (design §7), split
from cnt_cell_library_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit
from cntfet.objects.cnt_cell_library._shared import fet_count

class CNTCellDefinition(treeObject):
    """One library cell VARIANT as a row (the no-code face of
    CELL_LIBRARY x DRIVES)."""

    @treeObjectInit
    def __init__(
        self,
        # 'cinv-x1', 'cnor2-x2', ...
        name: str = '',
        function: str = '',
        drive_strength: int = 1,
        fet_count: int = 0,
        inputs_json: str = '[]',
        output_pin: str = 'Y',
        liberty_function: str = '',
        unate: str = 'negative',
        # 'generated' (from CELL_LIBRARY) — a hand row would say
        # so here and the generator never touches it.
        origin: str = 'generated',
        status: str = 'defined',
        notes: str = '',
        is_prior: bool = True,
        manager=None,
    ):
        self.name = name
        self.function = function
        self.drive_strength = drive_strength
        self.fet_count = fet_count
        self.inputs_json = inputs_json
        self.output_pin = output_pin
        self.liberty_function = liberty_function
        self.unate = unate
        self.origin = origin
        self.status = status
        self.notes = notes
        self.is_prior = is_prior
