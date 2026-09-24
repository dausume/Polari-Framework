"""
@module tensormath.custom.fem_shapes

THE ELEMENTS AS SHAPES (tt-11): each P1 triangle of an FEM field becomes a `polygon` MathShapeDefinition (the
suite's own shape library carries the geometry — vertices, area, centroid, point-in-polygon) and, through
`mathshapes.custom.shape2d_bridge`, a `Shape2DDefinition` in SPACE units the 2-D renderer draws by `shapeRef`.
The `field` binding then references `<pattern>{i}` per cell, and the σ colour stays DATA on the object
(colorOverride): the plate is tiled with its own triangles, each painted by its stress — filled cells, through
the library, no polygon bolted onto the renderer.

    element_shapes(field_row) -> (math_shape_rows, shape2d_rows)     names: <field name>-el-<i>
"""
import json

from mathshapes.custom.shape2d_bridge import shape2d_from_polygon


def shape_name(field_name, i):
    return '%s-el-%d' % (field_name, i)


def element_shapes(field_row):
    """field_row: a FEMFieldState row or its seed dict (nodes_json, triangles_json, elements_json, name, case)."""
    g = (lambda k, d='': field_row.get(k, d)) if isinstance(field_row, dict) else (lambda k, d='': getattr(field_row, k, d))
    nodes = json.loads(g('nodes_json', '[]') or '[]'); tris = json.loads(g('triangles_json', '[]') or '[]'); elems = json.loads(g('elements_json', '[]') or '[]')
    fname, case = str(g('name')), str(g('case'))
    maths, shapes = [], []
    for i, t in enumerate(tris):
        verts = [[float(nodes[j][0]), float(nodes[j][1])] for j in t]
        area = float(elems[i][6]) if i < len(elems) and len(elems[i]) > 6 else None
        m = {'name': shape_name(fname, i), 'display_name': 'element %d of %s' % (i, case), 'family': 'primitive', 'primitive_kind': 'polygon',
             'quadric_matrix_json': '', 'csg_json': '', 'parameters_json': json.dumps({'vertices': verts, 'z': 0.0, 'thickness': 0.0, 'plane': 'xy', 'nodes': [int(j) for j in t]}),
             'bounds_json': '', 'notes': 'tt-11: P1 triangle %d of FEM case %s (nodes %s); area %s m² per the field row' % (i, case, list(t), area), 'provenance_id': ''}
        s = shape2d_from_polygon(m)
        if s is None:
            continue
        s['description'] = 'element %d of %s (%.4g m²): the triangle itself, in space units — the field binding paints it by σ' % (i, case, area or 0.0)
        maths.append(m); shapes.append(s)
    return maths, shapes
