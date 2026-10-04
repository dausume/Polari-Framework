"""
@module pcb.objects.pcb.LandPattern

LandPattern — one class per file (design §7); pcb-0, the PCB arc (AI-Notes/plans/PCB_FROM_SCRATCH_PLAN.md §2).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class LandPattern(treeObject):
    """What it is: "Footprint planning" (plan §2): a land pattern's DIMENSIONS — pitch, pad size, drill, courtyard — each a
    DatasheetFact reference when derived by IPC-7351-style rules (a knob density = most | nominal | least; IPC-7351 is cited
    by clause, never copied). pcb-0 seeds only what the ingested board gives: the footprint's own pads AS DRAWN (no
    datasheet behind them — said in `undetermined`); the derivation and the comparison come at pcb-3.
    """

    @treeObjectInit
    def __init__(self, name: str = '', footprint: str = '', package: str = '', density: str = '', pitch_mm: float = 0.0,
                 pad_w_mm: float = 0.0, pad_h_mm: float = 0.0, drill_mm: float = 0.0, pad_shape: str = '', pads: int = 0,
                 courtyard_w_mm: float = 0.0, courtyard_h_mm: float = 0.0, facts_json: str = '{}', derivation: str = '',
                 compared_to: str = '', difference: str = '', undetermined: str = '', notes: str = '', manager=None):
        self.name = name  # <footprint>
        self.footprint = footprint  # Footprint row
        self.package = package
        self.density = density  # most | nominal | least | as-drawn
        self.pitch_mm = pitch_mm
        self.pad_w_mm = pad_w_mm
        self.pad_h_mm = pad_h_mm
        self.drill_mm = drill_mm
        self.pad_shape = pad_shape
        self.pads = pads
        self.courtyard_w_mm = courtyard_w_mm
        self.courtyard_h_mm = courtyard_h_mm
        self.facts_json = facts_json  # {field: DatasheetFact name}
        self.derivation = derivation  # the equation shown, or as-drawn
        self.compared_to = compared_to  # the KiCad footprint it was compared with
        self.difference = difference  # a finding, or none
        self.undetermined = undetermined
        self.notes = notes
