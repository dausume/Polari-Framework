"""
@module grpcbridge.objects.mapping.EnumMapping

EnumMapping — one class per file (design §7).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class EnumMapping(treeObject):
    """What it is: an object STATE ↔ small-integer table for one field of one class (grpc-j4): the ordered labels
    (labels[i] ↔ i + 1 on the wire) and the unknown slot 0 (an unmapped string encodes as 0 and decodes to
    `unknown_label`; also proto3's required zero). On the wire the field is ONE byte instead of a length-prefixed
    string; in the C header it becomes `enum` constants + a name table, in the bridge's proto an `enum`, in Java an
    enum with toWire/fromWire. The object's field (and the server's proto field) stays a string.
    Related concepts: `WireContract` (its hash covers these tables), c_twin wire v2.
    """

    @treeObjectInit
    def __init__(self, name: str = '', object_class: str = '', field: str = '', labels_json: str = '[]',
                 unknown_label: str = 'unknown', wire_type: str = 'u8', origin: str = 'person', notes: str = '',
                 manager=None):
        self.name = name  # e.g. SimRigState.status
        self.object_class = object_class
        self.field = field  # a string field of the class
        self.labels_json = labels_json  # ordered: ["boot", "ok", "commanded", "echoed", "fault"] → 1..5
        self.unknown_label = unknown_label  # what wire value 0 decodes to
        self.wire_type = wire_type  # u8 (≤ 255 labels)
        self.origin = origin
        self.notes = notes
