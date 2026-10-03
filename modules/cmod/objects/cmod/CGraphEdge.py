"""
@module cmod.objects.cmod.CGraphEdge

CGraphEdge — one class per file (design §7).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class CGraphEdge(treeObject):
    """What it is: One EDGE of a `CGraph` (C_MODULARIZATION_PLAN.md §5). `data` joins an out port to an in port (a plain C
    assignment between locals typed from the ports); `field` writes an out port into a field of the class instance (the
    hwsim-nocode FieldRegisterBinding, with an optional scale / offset); `tick` schedules a node (or a field write) on a
    tick's period; `on-rx` drains a byte source into the parser; `on-command` runs an atom when the parser completes a frame
    of the class's msg_type; `calls` records that an atom calls another itself (checked against the atom's derived calls —
    the glue emits nothing for it). Data and field edges must form no cycle; every in port must be bound.
    Related concepts: `CGraph`, `CGraphNode`, `CPort`.
    """

    plain_words = 'A graph edge is one wire in a firmware drawing: a value going from one block to another, or a trigger saying when a block runs.'

    @treeObjectInit
    def __init__(self, name: str = '', graph: str = '', kind: str = 'data', from_node: str = '', from_port: str = '',
                     to_node: str = '', to_port: str = '', order: int = 0, scale: str = '', offset: str = '', ctype_from: str = '',
                     ctype_to: str = '', notes: str = '', manager=None):
        self.name = name            # <graph>#<n>
        self.graph = graph
        self.kind = kind            # data | field | tick | on-rx | on-command | calls
        self.from_node = from_node  # instance names inside the graph
        self.from_port = from_port
        self.to_node = to_node
        self.to_port = to_port
        self.order = order
        self.scale = scale          # field edges: an optional numeric literal (value * scale + offset)
        self.offset = offset
        self.ctype_from = ctype_from    # derived: the C types the edge joins
        self.ctype_to = ctype_to
        self.notes = notes
