"""
@module pcb.objects.pcb.DrcResult

DrcResult — one class per file (design §7); pcb-0, the PCB arc (AI-Notes/plans/PCB_FROM_SCRATCH_PLAN.md §2).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class DrcResult(treeObject):
    """What it is: One finding of a check (plan §2 `DRCResult`/`ERCResult`): kicad-cli's ERC / DRC / schematic-parity report
    items and Polari's own fab-rule checks, as rows — severity, rule, description, the items and where; the report's sha256
    and the engine version that produced it. A clean check is ONE row with severity 'none' (so a clean run is visible, not
    absent).
    """

    @treeObjectInit
    def __init__(self, name: str = '', board: str = '', kind: str = '', checker: str = '', severity: str = '', rule: str = '',
                 description: str = '', items_json: str = '[]', x_mm: float = 0.0, y_mm: float = 0.0, report_sha256: str = '',
                 engine_version: str = '', argv: str = '', source_date: str = '', at: str = '', manager=None):
        self.name = name
        self.board = board
        self.kind = kind  # erc | drc | parity | unconnected | fab-rule
        self.checker = checker  # kicad-cli 9.0.2 | polari fab rules
        self.severity = severity  # error | warning | info | none
        self.rule = rule  # the report's type (silk_edge_clearance, pin_not_connected …) or the FabRule
        self.description = description
        self.items_json = items_json  # [{description, pos}]
        self.x_mm = x_mm
        self.y_mm = y_mm
        self.report_sha256 = report_sha256
        self.engine_version = engine_version
        self.argv = argv
        self.source_date = source_date
        self.at = at
