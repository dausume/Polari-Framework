"""
@module pcb.objects.pcb.FabricationExport

FabricationExport — one class per file (design §7); pcb-0, the PCB arc (AI-Notes/plans/PCB_FROM_SCRATCH_PLAN.md §2).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class FabricationExport(treeObject):
    """What it is: One FILE of a fabrication output set (plan §2 `FabricationOutput`): kind (gerber | drill | drill-map |
    pos | bom | netlist | svg | step | job), layer, file name + extension, sha256 + bytes, the board file sha it came from,
    the kicad-cli argv + version + the frozen source date (outputs are byte-stable), and the FAB's verdict on the name:
    accepted / not accepted / discrepancy (DKRed's page vs his screenshot), with the name the fab would take.
    """

    @treeObjectInit
    def __init__(self, name: str = '', board: str = '', export_set: str = '', kind: str = '', layer: str = '',
                 filename: str = '', extension: str = '', sha256: str = '', bytes: int = 0, board_sha256: str = '',
                 fab_rule_set: str = '', accepted: str = '', fab_name: str = '', naming_note: str = '', artifact_path: str = '',
                 artifact_url: str = '', engine_version: str = '', argv: str = '', source_date: str = '', at: str = '',
                 manager=None):
        self.name = name  # <board>:<set>:<file>
        self.board = board
        self.export_set = export_set  # protel | kicad-gbr | drill | assembly | layers | 3d
        self.kind = kind
        self.layer = layer  # F.Cu …
        self.filename = filename
        self.extension = extension
        self.sha256 = sha256
        self.bytes = bytes
        self.board_sha256 = board_sha256
        self.fab_rule_set = fab_rule_set
        self.accepted = accepted  # yes | no | discrepancy | n/a
        self.fab_name = fab_name  # the extension the fab lists for this layer
        self.naming_note = naming_note
        self.artifact_path = artifact_path  # relative to the module artifact dir
        self.artifact_url = artifact_url  # absolute when POLARI_PUBLIC_BASE_URL is set
        self.engine_version = engine_version
        self.argv = argv
        self.source_date = source_date
        self.at = at
