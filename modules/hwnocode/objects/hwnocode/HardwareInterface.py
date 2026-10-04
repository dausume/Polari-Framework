"""
@module hwnocode.objects.hwnocode.HardwareInterface

HardwareInterface — one class per file (design §7).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class HardwareInterface(treeObject):
    """What it is: the `hw-interface` NODE KIND — the device ⇄ backend SPLIT POINT on the solution canvas (HARDWARE_NOCODE_PLAN.md
    §0, §2b rule 3): it names one grpcbridge `HardwareInterfaceBinding` (a Polari object row ↔ one board instance + its port or the
    twin's pty, on one bridge). Every edge that crosses board ⇄ backend must pass through one of these; frames come UP through it
    (the row updates) and commands go DOWN through it (a PUT of the row rides the Commands stream to the firmware). Placement:
    bridge (the generated Java bridge on the host). The binding stays grpcbridge's row; this node only refers to it.
    Related concepts: `HardwareSolution`, `HardwareSubgraph`, grpcbridge `HardwareInterfaceBinding` / `WireContract`.
    """

    plain_words = 'A hardware interface block is where a drawing crosses from the board to the server: one object row tied to one cable or simulated port.'

    statePalette = {
        'nodeKind': 'hw-interface', 'displayName': 'Hardware Interface', 'category': 'Hardware', 'icon': 'settings_input_hdmi',
        'color': '#00796B', 'placement': 'bridge', 'language': 'Java (generated bridge)', 'overlay': 'hw-interface',
        'description': 'One HardwareInterfaceBinding: an object row tied to a board instance and its port (or the twin\'s pty). '
                       'The ONLY place a solution may cross between the board and the backend.',
        'displayFields': ['binding', 'object_class'],
        'variables': [{'name': 'binding', 'displayName': 'Binding', 'type': 'string', 'defaultValue': ''},
                      {'name': 'object_class', 'displayName': 'Class', 'type': 'string', 'defaultValue': ''},
                      {'name': 'object_name', 'displayName': 'Row', 'type': 'string', 'defaultValue': ''},
                      {'name': 'board_instance', 'displayName': 'Board instance', 'type': 'string', 'defaultValue': ''},
                      {'name': 'port', 'displayName': 'Port / twin pty', 'type': 'string', 'defaultValue': ''}],
        'slots': {'inputs': 1, 'outputs': 1, 'inputLabels': ['device'], 'outputLabels': ['backend']},
    }

    @treeObjectInit
    def __init__(self, name: str = '', binding: str = '', object_class: str = '', object_name: str = '', bridge_name: str = '',
                 board_instance: str = '', port: str = '', interface_kind: str = '', notes: str = '', manager=None):
        self.name = name
        self.binding = binding
        self.object_class = object_class
        self.object_name = object_name
        self.bridge_name = bridge_name
        self.board_instance = board_instance
        self.port = port
        self.interface_kind = interface_kind
        self.notes = notes
