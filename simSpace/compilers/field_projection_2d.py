"""
@cross-cutting
@module simSpace.compilers.field_projection_2d
@tags @xc:render-2d

`field`-kind State Projection in 2-D — fans a MATRIX-VALUED field row (an
FEM element field: one matrix row per element, [cx, cy, <scalars…>]) out
into per-cell OBJECTS coloured by ONE scalar column through the binding's
colour scale. The 2-D counterpart of `field_projection.emit_field_3d`
(which fans the wind grid into arrows): where 3-D has a vectors channel,
2-D has objects with a per-instance `colorOverride` — a field the object
model has carried since mag-fv, so no new snapshot channel and no new
renderer; only the d3 renderer learned to honour the override.

Binding shape (binding_json):

    kind: 'field', matrixField: '<json field of the row>',
    layout: {originCols: [0, 2], scalarCol: 2, sizeCol: <optional col of a per-cell size>},
    color:  {domain: [lo, hi], ramp: 'stress' | 'grey', unit: 'Pa', field: 'von Mises'},
    cellSize: <space units>  (uniform, when no sizeCol),
    visual:  {shapeRef: 'rectangle', styleRef: 'default'}

Emitted entries: one per cell, id `bindingName:className:cellIndex` (per-
CELL stable identity, as in 3-D), `colorOverride` = the ramp at the
clamped, normalised scalar, `userData.scalar` = the raw value and the
domain so a tooltip / legend can say what the colour means. A cell
whose scalar is not a number is emitted grey with `userData.refused`.

@consumers
  - simSpace.compilers.compile_2d (binding kind 'field')
"""

from typing import Dict, List, Optional

from .common import parse_json_safe, resolve_ref, instance_id, read_temporal_value

# A fixed, named ramp per binding — the colour is DATA (row scalar through the
# scale the binding declares), so a legend can be reconstructed from the binding.
RAMPS = {
    # blue → green → yellow → red: low stress cool, high stress hot
    'stress': [(0.0, (33, 102, 172)), (0.35, (67, 160, 71)), (0.7, (253, 216, 53)), (1.0, (198, 40, 40))],
    'grey': [(0.0, (235, 235, 235)), (1.0, (40, 40, 40))],
}


def ramp_color(ramp: str, t: float) -> str:
    stops = RAMPS.get(ramp) or RAMPS['grey']
    t = 0.0 if t < 0 else (1.0 if t > 1 else t)
    for (t0, c0), (t1, c1) in zip(stops, stops[1:]):
        if t <= t1:
            f = 0.0 if t1 == t0 else (t - t0) / (t1 - t0)
            r, g, b = (round(a + (b_ - a) * f) for a, b_ in zip(c0, c1))
            return '#%02x%02x%02x' % (r, g, b)
    r, g, b = stops[-1][1]
    return '#%02x%02x%02x' % (r, g, b)


def emit_field_2d(
    class_name: str,
    instances: Dict,
    binding: Dict,
    binding_name: str,
    override: Optional[Dict],
    warnings: List[str],
) -> List[Dict]:
    matrix_field = binding.get('matrixField')
    if not matrix_field:
        warnings.append(f"{class_name} field binding has no matrixField; skipping.")
        return []
    layout = binding.get('layout') or {}
    o0, o1 = (layout.get('originCols') or [0, 2])[:2]
    scalar_col = layout.get('scalarCol')
    size_col = layout.get('sizeCol')
    color = binding.get('color') or {}
    domain = color.get('domain') or [0.0, 1.0]
    try:
        lo, hi = float(domain[0]), float(domain[1])
    except (TypeError, ValueError, IndexError):
        warnings.append(f"{class_name} field binding colour domain malformed; using [0, 1].")
        lo, hi = 0.0, 1.0
    ramp = str(color.get('ramp') or 'grey')
    cell_size = binding.get('cellSize')
    visual = binding.get('visual') or {}
    shape_ref_cfg = visual.get('shapeRef') or 'rectangle'
    style_ref_cfg = visual.get('styleRef') or 'default'
    scene_shape = override.get('overrideShapeRef') if override else None
    scene_style = override.get('overrideStyleRef') if override else None

    out: List[Dict] = []
    iter_instances = instances.values() if isinstance(instances, dict) else instances
    for inst in iter_instances:
        cells = parse_json_safe(getattr(inst, matrix_field, '') or '[]', [])
        if not isinstance(cells, list):
            warnings.append(f"{class_name}.{matrix_field} is not a matrix; skipping instance.")
            continue
        inst_id = instance_id(inst)
        temporal_value = read_temporal_value(inst, binding)
        for idx, cell in enumerate(cells):
            if not isinstance(cell, (list, tuple)) or len(cell) < o1:
                continue
            try:
                position = [float(cell[o0]), float(cell[o0 + 1])]
            except (TypeError, ValueError):
                continue
            obj: Dict = {
                'id': f'{binding_name}:{class_name}:{idx}',
                'position': position,
                'shapeRef': scene_shape or resolve_ref(shape_ref_cfg, inst, 'rectangle'),
                'styleRef': scene_style or resolve_ref(style_ref_cfg, inst, 'default'),
                'classRef': {'className': class_name, 'instanceId': inst_id},
                'userData': {'bindingName': binding_name, 'cellIndex': idx},
            }
            scalar = None
            if scalar_col is not None and len(cell) > scalar_col:
                try:
                    scalar = float(cell[scalar_col])
                except (TypeError, ValueError):
                    scalar = None
            if scalar is None or scalar != scalar:
                obj['colorOverride'] = '#bdbdbd'
                obj['userData']['refused'] = 'no numeric scalar in column %s' % scalar_col
            else:
                t = 0.0 if hi == lo else (scalar - lo) / (hi - lo)
                obj['colorOverride'] = ramp_color(ramp, t)
                obj['userData']['scalar'] = scalar
                obj['userData']['domain'] = [lo, hi]
                obj['userData']['unit'] = color.get('unit', '')
                obj['userData']['field'] = color.get('field', '')
                obj['label'] = None
            size = None
            if size_col is not None and len(cell) > size_col:
                try:
                    size = float(cell[size_col])
                except (TypeError, ValueError):
                    size = None
            if size is None and cell_size is not None:
                try:
                    size = float(cell_size)
                except (TypeError, ValueError):
                    size = None
            if size is not None and size > 0:
                obj['scale'] = size
            if temporal_value is not None:
                obj['temporalValue'] = temporal_value
            out.append(obj)
    return out
