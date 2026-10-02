"""
@module cmod.objects.cmod.CPort

CPort — one class per file (design §7).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class CPort(treeObject):
    """What it is: One PORT of an atom — a parameter or the return value, its direction (in | out | inout), its C type and
    AVR width, the Polari type it carries (int64 / double / bool / string / bytes / ref:<Type>), and the unit and meaning a
    POLARI_NODE annotation gave it; `source` says whether the direction was derived from the C or settled by the annotation.
    Related concepts: `CFunctionAtom`, `CGraph` (an edge joins an out port to an in port).
    """

    plain_words = 'A port is one input or output of a C building block — the value, its type and its unit.'

    @treeObjectInit
    def __init__(self, name: str = '', project: str = '', atom: str = '', port: str = '', position: int = 0,
                     direction: str = '', ctype: str = '', width_bytes: int = 0, polari_type: str = '', unit: str = '',
                     meaning: str = '', source: str = '', manager=None):
        self.name = name
        self.project = project
        self.atom = atom
        self.port = port
        self.position = position
        self.direction = direction
        self.ctype = ctype
        self.width_bytes = width_bytes
        self.polari_type = polari_type
        self.unit = unit
        self.meaning = meaning
        self.source = source
