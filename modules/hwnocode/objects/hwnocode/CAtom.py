"""
@module hwnocode.objects.hwnocode.CAtom

CAtom — one class per file (design §7).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class CAtom(treeObject):
    """What it is: the `c-atom` NODE KIND on the ONE canvas (D-hn-2; the overlay planned as cmod-3): one cmod `CFunctionAtom` (a C
    function of a normal C project, with ports derived by parsing) placed as a node — its sockets ARE the atom's `CPort` rows,
    `bindings` give literal or knob values to its in ports. In hn-0 a c-atom is rendered only as part of a `HardwareSubgraph`
    (cmod's CGraph rows); a loose c-atom on a solution canvas is placed on the board and refused at render with the reason.
    Placement: board (twin while no BoardInstance is attached). Never Python, never run in the engine (RULE 2).
    Related concepts: cmod `CFunctionAtom` / `CPort` / `CGraphNode`, `HardwareSubgraph`.
    """

    plain_words = 'A C atom block is one C function from a firmware project placed in a drawing, with its inputs and outputs as sockets.'

    statePalette = {
        'nodeKind': 'c-atom', 'displayName': 'C Atom', 'category': 'Hardware', 'icon': 'memory', 'color': '#5D4037',
        'placement': 'board', 'language': 'C', 'overlay': 'c-atom',
        'description': 'One C function of a normal C firmware project (cmod CFunctionAtom): ports, the registers it touches, '
                       'ISR-safety and its measured cost. Runs on the board only.',
        'displayFields': ['atom', 'stage'],
        'variables': [{'name': 'atom', 'displayName': 'Atom', 'type': 'string', 'defaultValue': ''},
                      {'name': 'stage', 'displayName': 'Stage', 'type': 'string', 'defaultValue': 'loop'},
                      {'name': 'bindings', 'displayName': 'Bindings', 'type': 'string', 'defaultValue': ''}],
        'slots': {'inputs': 1, 'outputs': 1, 'inputLabels': ['in'], 'outputLabels': ['out']},
    }

    @treeObjectInit
    def __init__(self, name: str = '', atom: str = '', stage: str = 'loop', bindings: str = '', notes: str = '', manager=None):
        self.name = name
        self.atom = atom
        self.stage = stage
        self.bindings = bindings
        self.notes = notes
