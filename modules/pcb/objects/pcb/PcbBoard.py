"""
@module pcb.objects.pcb.PcbBoard

PcbBoard — one class per file (design §7); pcb-0, the PCB arc (AI-Notes/plans/PCB_FROM_SCRATCH_PLAN.md §2).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class PcbBoard(treeObject):
    """What it is: The PHYSICAL BOARD as KiCad holds it (plan §2 `Board`; called PcbBoard beside brd-bo's BoardHardware,
    which it refines): the `.kicad_pcb` by sha256, copper layer count, the layer table and the stackup, the outline
    (Edge.Cuts bounding box), the board's own design rules (from the file's setup + the project's .kicad_pro), the fab rule
    set it is checked against, and counts (footprints, nets, track segments, vias, zones). Licence + its source on the row.
    """

    @treeObjectInit
    def __init__(self, name: str = '', board_definition: str = '', title: str = '', description: str = '', file: str = '', sha256: str = '',
                 format_version: str = '', generator: str = '', copper_layers: int = 0, layers_json: str = '[]',
                 stackup_json: str = '[]', thickness_mm: float = 0.0, width_mm: float = 0.0, height_mm: float = 0.0,
                 outline_json: str = '{}', design_rules_json: str = '{}', fab_rule_set: str = '', footprints: int = 0,
                 nets: int = 0, segments: int = 0, vias: int = 0, zones: int = 0, licence: str = '', licence_source: str = '',
                 provenance: str = '', notes: str = '', manager=None):
        self.name = name
        self.board_definition = board_definition  # a BoardDefinition name ('' = not a register device)
        self.title = title
        # what this board IS, one line, for whoever opens it cold (his browser pass, ecc83-pp naming fix): from the
        # file's own title block (company/comment fields) when it has prose, else a sibling SOURCE.json's licence +
        # package — never invented, '' when neither exists.
        self.description = description
        self.file = file
        self.sha256 = sha256
        self.format_version = format_version
        self.generator = generator
        self.copper_layers = copper_layers
        self.layers_json = layers_json  # [{id, name, type, user_name}]
        self.stackup_json = stackup_json  # [{layer, type, thickness, material}]
        self.thickness_mm = thickness_mm
        self.width_mm = width_mm  # Edge.Cuts bbox
        self.height_mm = height_mm  # Edge.Cuts bbox
        self.outline_json = outline_json  # {bbox, edge items}
        self.design_rules_json = design_rules_json  # the board's own rules (.kicad_pro net classes + setup)
        self.fab_rule_set = fab_rule_set  # FabRuleSet name
        self.footprints = footprints
        self.nets = nets
        self.segments = segments
        self.vias = vias
        self.zones = zones
        self.licence = licence
        self.licence_source = licence_source
        self.provenance = provenance
        self.notes = notes
