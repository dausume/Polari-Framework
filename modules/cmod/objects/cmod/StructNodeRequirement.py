"""
@module cmod.objects.cmod.StructNodeRequirement

StructNodeRequirement - one class per file (design section 7); bss-1 (AI-Notes/plans/BENCH_SOLUTION_SIM_PLAN.md section 2 "Node").
"""
from objectTreeDecorators import treeObject, treeObjectInit


class StructNodeRequirement(treeObject):
    """What it is: ONE END-STATE REQUIREMENT of a `StructNode`: a field of a mapped struct and what it must satisfy - `exact` (equals `value`),
    `range` (`value` = 'lo..hi', inclusive), `set` (`value` = comma-separated allowed values) or `written` (the field was written during the edge; its
    value is not judged: the boot node's init writes). An `exact` value of a non-enumerable field must be one of its `StructFieldSamples`, or the node is
    blocked in words (cmod.custom.bench_topology.blocks).
    Related concepts: `StructNode` (the parent), `StructObjectMap` (the struct and its fields), `StructFieldSamples`.
    """

    plain_words = 'One requirement says what one struct field must be for the bench to count as being at that node.'

    @treeObjectInit
    def __init__(self, name: str = '', node: str = '', object_map: str = '', field: str = '', kind: str = 'exact', value: str = '', notes: str = '',
                 manager=None):
        self.name = name              # '<node>:<field>'
        self.node = node              # a StructNode name
        self.object_map = object_map  # a StructObjectMap name (which struct)
        self.field = field            # the struct field
        self.kind = kind              # exact | range | set | written
        self.value = value            # '1' | '20..30' | 'armed,firing' | '' for written
        self.notes = notes
