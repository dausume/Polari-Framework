"""
@module mathshapes.objects.shape.ShapeAnchor

Row class ShapeAnchor of the mathshapes module — one class per file (design §7).
ms-anchor (MECH_FREECAD_INTERCHANGE_PLAN §8.5, Dustin 2026-11-03: "that should be
its own unique tool inside math shapes"). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class ShapeAnchor(treeObject):
    """A point + frame PICKED on an existing math shape by a ray.

    The ray r(s) = o + s·d is marched along the shape's implicit field
    F until the first F = 0 crossing (bisection-refined); the normal is
    n = ∇F/|∇F| there (2Qp of the active quadric surface — itself a
    no-code row, `normal_eq_ref`). The REFERENCE toggle then picks one
    of four axes from (d, n), and the frame (a, b, c) is what every
    AnchoredOffset of this anchor is written in.

    ASSUMPTION awaiting Dustin's confirmation: 'tangent_toward'
    ("tangential, most toward us") is read as the VIEWER direction
    projected onto the tangent plane — t₁ = normalise(−d − (−d·n)n),
    the in-plane direction leaning at the viewer — and 'tangent_away'
    is its negative. When the ray is along the normal there is no
    'most toward' tangent; an arbitrary in-plane direction is used and
    the frame says so (`frame_json.note`)."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        display_name: str = '',
        shape_ref: str = '',
        ray_origin_json: str = '',
        ray_dir_json: str = '',
        hit_json: str = '',
        normal_json: str = '',
        normal_eq_ref: str = '',
        reference: str = 'toward',
        frame_json: str = '',
        basis: str = 'exact',
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        #: unique key ('demo-cylinder-top').
        self.name = name
        self.display_name = display_name
        #: the MathShapeDefinition this anchor sits on (by name).
        self.shape_ref = shape_ref
        #: [x, y, z] — where the pick ray starts (the page camera, or typed).
        self.ray_origin_json = ray_origin_json
        #: [dx, dy, dz] — the ray direction d (normalised on use).
        self.ray_dir_json = ray_dir_json
        #: [x, y, z] — p₀, the first F = 0 crossing along the ray;
        #: '' = not yet picked (undetermined).
        self.hit_json = hit_json
        #: [nx, ny, nz] — the OUTWARD unit normal n = ∇F/|∇F| at p₀.
        self.normal_json = normal_json
        #: the no-code row that IS this normal: `<shape>--grad`
        #: (MatrixEquationDefinition, ∇F = 2Qp of the active surface);
        #: '' when the shape has no equation form.
        self.normal_eq_ref = normal_eq_ref
        #: REFERENCE_MODES entry — which of the four axes is `a`.
        self.reference = reference
        #: {"a","b","c","origin","matrix"(16, world→local),"mode","note"}
        #: — the frame the offsets are written in; '' = undetermined.
        #: matrix · [x y z 1] = [u v w 1] with w ALONG the reference a
        #: and (u, v) along (b, c): §8.5's usage (w − t = 0 is the
        #: offset plane, the thread runs along w), kept over its
        #: one-line (·a, ·b, ·c) listing — a recorded deviation.
        self.frame_json = frame_json
        #: ANCHOR_BASES entry: 'exact' when the hit and normal come from
        #: the quadric field (bisection to 1e-12 on an exact F, 2Qp
        #: normal); 'sampled' when a finite-difference normal was used.
        self.basis = basis
        self.provenance_id = provenance_id
        self.notes = notes
