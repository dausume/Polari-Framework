"""
@cross-cutting
@module simSpace.compilers.field_projection
@tags @xc:render-3d

`field`-kind State Projection — fans a MATRIX-VALUED field row (e.g. the
wind grid's `cells_json`, N×M with origin + vector columns per cell) out
into per-cell arrows. The projection kind STATE_PROJECTION_DESIGN.md
anticipated after `vector`.

Emitted entries ride the SAME snapshot `vectors` channel as single
`vector` projections — no frontend changes. Two deliberate differences:

  * KEY: `bindingName:className:cellIndex` — per-CELL stable identity
    (the cell's row index in the matrix, constant across timesteps), so
    the temporal collapse-by-key repositions each cell's arrow instead
    of collapsing the whole field to one arrow (the single-`vector`
    key) or trailing (a per-row key).

  * SPARSITY IS SCRUB-SAFE: a cell hidden at a step (decimation or the
    magnitude floor) still emits — with a ZERO vector. The frontend's
    snapshot-mode collapse keeps the latest entry ≤ currentTime per key;
    if hidden cells were simply omitted, their last visible arrow would
    linger. A zero-length entry instead trips the renderer's degenerate
    guard, which hides the arrow. Deterministic decimation (an integer
    hash of cell × step against a density knob) means scrubbing back
    replays the same arrows.

@consumers
  - simSpace.compilers.compile_3d (binding kind 'field')
@see /OVERLAP_MAP.md
"""

from typing import Dict, List, Optional

from .common import (
    parse_json_safe,
    resolve_ref,
    instance_id,
    read_temporal_value,
)

# Knuth-style multiplicative hash → [0, 1). Plain integer arithmetic so
# the visibility of (cell, step) is identical across processes/replays.
_HASH_MOD = 4294967296  # 2**32


def _decimation_hash(cell_index: int, step: int) -> float:
    h = (cell_index * 2654435761 + step * 97911 + 1013904223) % _HASH_MOD
    return h / _HASH_MOD


def emit_field_3d(
    class_name: str,
    instances: Dict,
    binding: Dict,
    binding_name: str,
    override: Optional[Dict],
    warnings: List[str],
) -> List[Dict]:
    """Emit per-cell arrows for every instance row of a `field` binding.
    Each instance is one timestep of the field; each matrix row is one
    cell — [<originCols> | <vectorCols>]."""
    matrix_field = binding.get('matrixField')
    if not matrix_field:
        warnings.append(
            f"{class_name} field binding has no matrixField; skipping."
        )
        return []

    layout = binding.get('layout') or {}
    o0, o1 = (layout.get('originCols') or [0, 3])[:2]
    v0, v1 = (layout.get('vectorCols') or [3, 6])[:2]

    visual = binding.get('visual') or {}
    style_ref_cfg = visual.get('styleRef') or 'matte-blue'
    scene_style_override = override.get('overrideStyleRef') if override else None
    try:
        scale = float(binding.get('scale', 1.0) or 1.0)
        head_scale = float(binding.get('headScale', 0.18) or 0.18)
    except (TypeError, ValueError):
        scale, head_scale = 1.0, 0.18

    decimation = binding.get('decimation') or {}
    try:
        density = float(decimation.get('density', 1.0))
        magnitude_min = float(decimation.get('magnitudeMin', 0.0) or 0.0)
    except (TypeError, ValueError):
        density, magnitude_min = 1.0, 0.0

    out: List[Dict] = []
    iter_instances = instances.values() if isinstance(instances, dict) else instances
    for inst in iter_instances:
        cells = parse_json_safe(getattr(inst, matrix_field, '') or '[]', None)
        if not isinstance(cells, list):
            warnings.append(
                f"{class_name}.{matrix_field} is not a JSON array on an "
                f"instance; skipping that row."
            )
            continue
        try:
            step = int(getattr(inst, 'step', 0) or 0)
        except (TypeError, ValueError):
            step = 0
        inst_id = instance_id(inst)
        style_ref = scene_style_override or resolve_ref(style_ref_cfg, inst, 'matte-blue')
        temporal_value = read_temporal_value(inst, binding)

        for idx, cell in enumerate(cells):
            if not isinstance(cell, (list, tuple)) or len(cell) < max(o1, v1):
                continue
            try:
                origin = [float(c or 0) for c in cell[o0:o1]]
                vec = [float(c or 0) for c in cell[v0:v1]]
            except (TypeError, ValueError):
                continue
            mag = sum(c * c for c in vec) ** 0.5
            visible = (
                mag >= magnitude_min
                and _decimation_hash(idx, step) < density
            )
            if not visible:
                # Zero vector = "this cell's arrow is OFF at this step",
                # scrub-safely (see module docstring).
                vec = [0.0, 0.0, 0.0]
            v: Dict = {
                'kind': 'vector',
                'key': f'{binding_name}:{class_name}:{idx}',
                'id': f'{binding_name}:{inst_id}:{idx}',
                'origin': origin,
                'vec': vec,
                'scale': scale,
                'headScale': head_scale,
                'styleRef': style_ref,
                'classRef': {'className': class_name, 'instanceId': inst_id},
            }
            if temporal_value is not None:
                v['temporalValue'] = temporal_value
            out.append(v)
    return out
