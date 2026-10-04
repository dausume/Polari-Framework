"""
@module hwnocode.objects.hwnocode.HardwareSubgraph

HardwareSubgraph — one class per file (design §7).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class HardwareSubgraph(treeObject):
    """What it is: the NODE KIND that puts a whole hardware subgraph on the solution canvas as ONE collapsed node (D-hn-1 ruled
    "subgraph"; plan §2c): it REFERENCES a cmod `CGraph` the way `SolutionInvocation` references another solution — the graph's
    rows, cmod's checker, its refusals and its byte-identical proof stay cmod's. On the canvas it expands into the CGraph's
    c-atom nodes (the c-atom overlay); `hn-split` renders it through the `cmod-glue` compiler (artifacts only — a C graph never
    runs in the engine, RULE 2). Placement: board (twin while no BoardInstance is attached).
    Related concepts: `HardwareSolution`, `CAtom`, `HardwareInterface`, cmod `CGraph`.
    """

    plain_words = 'A hardware subgraph is a whole firmware drawing shown as one block inside a bigger solution; open it to see its parts.'

    #: the palette metadata the canvas reads from GET /stateSpaceClasses (D-hn-2: the palette is data, not a static registry)
    statePalette = {
        'nodeKind': 'hardware-subgraph', 'displayName': 'Hardware Subgraph', 'category': 'Hardware', 'icon': 'developer_board',
        'color': '#6D4C41', 'placement': 'board', 'language': 'C', 'overlay': 'c-atom',
        'description': 'A cmod CGraph (firmware drawn from C atoms) as ONE node; expands into its atoms. Rendered by cmod-glue '
                       'into a plain C project that make alone builds — never run in the engine.',
        'displayFields': ['cgraph', 'board_definition'],
        'variables': [{'name': 'cgraph', 'displayName': 'CGraph', 'type': 'string', 'defaultValue': ''},
                      {'name': 'board_definition', 'displayName': 'Board', 'type': 'string', 'defaultValue': ''},
                      {'name': 'board_instance', 'displayName': 'Board instance', 'type': 'string', 'defaultValue': ''},
                      {'name': 'firmware_runtime', 'displayName': 'Firmware runtime', 'type': 'string', 'defaultValue': 'bare-c'}],
        'slots': {'inputs': 0, 'outputs': 1, 'outputLabels': ['frames']},
    }

    @treeObjectInit
    def __init__(self, name: str = '', cgraph: str = '', board_definition: str = '', board_instance: str = '',
                 firmware_runtime: str = 'bare-c', title: str = '', notes: str = '', manager=None):
        self.name = name
        self.cgraph = cgraph
        self.board_definition = board_definition
        self.board_instance = board_instance
        self.firmware_runtime = firmware_runtime
        self.title = title
        self.notes = notes
