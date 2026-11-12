"""
@module mathshapes.objects.shape.AnchoredOffset

Row class AnchoredOffset of the mathshapes module — one class per file (design §7).
ms-anchor (MECH_FREECAD_INTERCHANGE_PLAN §8.5). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class AnchoredOffset(treeObject):
    """An offset SOLID G(u, v, w) < 0 written in a ShapeAnchor's frame,
    composed with the parent shape by the existing CSG algebra
    (add → min, subtract → max(F, −G), intersect → max).

    Four modes: a planar SQUARE or DISK patch between the anchor plane
    (w = 0) and the offset plane (w = t) — degenerate quadrics, exact;
    CONFORM — the parent surface moved along the reference by t
    (exact for a plane-like reference and for a sphere, first-order
    `approx` elsewhere, see approx_reason); CUSTOM — any expression the
    person types in (u, v, w) with knobs, e.g. the thread
    |frac((w − (P/2π)·θ)/P) − ½| < h/P with θ = atan2(v, u).

    `offset_eq` lets t vary with position in the frame: '' keeps t
    constant; otherwise it is an expression t(u, v, w) (k·w a draft,
    A·sin(2πu/λ) a corrugation)."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        display_name: str = '',
        anchor_ref: str = '',
        mode: str = 'planar_square',
        t: float = 0.0,
        offset_eq: str = '',
        extent_json: str = '',
        surface_eq_ref: str = '',
        surface_eq_json: str = '',
        parameters_json: str = '{}',
        op: str = 'add',
        result_shape_ref: str = '',
        approx_reason: str = '',
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        #: unique key ('demo-m5-internal-thread').
        self.name = name
        self.display_name = display_name
        #: the ShapeAnchor whose frame this offset is written in.
        self.anchor_ref = anchor_ref
        #: OFFSET_MODES entry: planar_square | planar_disk | conform | custom.
        self.mode = mode
        #: the constant offset distance along the reference axis (cm);
        #: planar: the patch fills 0 ≤ w ≤ t; conform: the surface shift.
        self.t = t
        #: '' = t is constant; else an expression t(u, v, w) (+ knobs)
        #: in the frame — the "vary as it moves further from the normal".
        self.offset_eq = offset_eq
        #: size of the patch / bounds in the frame:
        #: planar_square {"side"}, planar_disk {"radius"},
        #: any mode may add {"u":[lo,hi],"v":[lo,hi],"w":[lo,hi]} clips.
        self.extent_json = extent_json
        #: custom mode: a MatrixEquationDefinition (by name) whose expr
        #: is G(u, v, w) in this frame; '' = use surface_eq_json.
        self.surface_eq_ref = surface_eq_ref
        #: custom mode, inline: {"expr": "...", "operands": {...}} —
        #: the same no-code shape as a MatrixEquationDefinition's
        #: operation/operands; operands may be numbers (knobs) or
        #: {"kind":"shapeGradient","ref":<shape>} (∇F at the point).
        self.surface_eq_json = surface_eq_json
        #: knobs by name (P, h, r, depth, ...), bound into every
        #: expression of this offset — the FreeCAD Spreadsheet twins.
        self.parameters_json = parameters_json
        #: OFFSET_OPS entry — how the result composes with the parent.
        self.op = op
        #: the MathShapeDefinition the tool emitted for the result
        #: (`<name>--result`, a csg node over parent + this solid);
        #: '' = not emitted (modes with no quadric row form).
        self.result_shape_ref = result_shape_ref
        #: '' when exact; else WHY the field is first-order only.
        self.approx_reason = approx_reason
        self.provenance_id = provenance_id
        self.notes = notes
