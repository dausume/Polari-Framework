"""
@module mathshapes.custom.shape2d_bridge

MATH SHAPE → 2-D SHAPE LIBRARY (tt-11). A `polygon` MathShapeDefinition (vertices in the plane) becomes a
`Shape2DDefinition` row the 2-D renderer can draw by `shapeRef`: `source='svg'`, the svg a single `<polygon>`
whose points are RELATIVE TO THE CENTROID (anchor center) and IN SPACE UNITS (`units='space'`), so the renderer
places it at the object's position and scales it with the view — the shape tiles the space instead of sitting
on it as a marker. Fill and stroke are NOT in the svg: they are the object's style/colorOverride (data), applied
by the renderer, so one shape row serves any field drawn on it.

    shape2d_from_polygon(shape_row_or_dict) -> Shape2DDefinition field dict | None (not a polygon)
"""
import json

from mathshapes.custom.shape_geometry import polygon_vertices, polygon_area_centroid


def _params(shape):
    raw = shape.get('parameters_json') if isinstance(shape, dict) else getattr(shape, 'parameters_json', '{}')
    try:
        p = json.loads(raw or '{}')
        return p if isinstance(p, dict) else {}
    except ValueError:
        return {}


def polygon_svg(verts, digits=6):
    """The svg for a polygon in space units around its centroid; y as in space (the renderer flips for math coords)."""
    _, (cx, cy) = polygon_area_centroid(verts)
    pts = ' '.join('%s,%s' % (round(x - cx, digits), round(y - cy, digits)) for x, y in verts)
    return '<polygon points="%s" vector-effect="non-scaling-stroke"/>' % pts


def shape2d_from_polygon(shape, name=None, category='math'):
    kind = shape.get('primitive_kind') if isinstance(shape, dict) else getattr(shape, 'primitive_kind', '')
    family = shape.get('family') if isinstance(shape, dict) else getattr(shape, 'family', '')
    if family != 'primitive' or kind != 'polygon':
        return None
    verts = polygon_vertices(_params(shape))
    if not verts:
        return None
    sname = shape.get('name') if isinstance(shape, dict) else getattr(shape, 'name', '')
    xs = [v[0] for v in verts]; ys = [v[1] for v in verts]
    return {'name': name or sname, 'description': 'the math shape %s (polygon, %d vertices) as a 2-D shape in SPACE units, anchored at its centroid' % (sname, len(verts)),
            'source': 'svg', 'builtin_name': '', 'svg_string': polygon_svg(verts), 'default_width': max(xs) - min(xs), 'default_height': max(ys) - min(ys),
            'anchor': 'center', 'category': category, 'units': 'space'}
