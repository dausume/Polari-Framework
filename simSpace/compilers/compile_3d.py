"""
@cross-cutting
@module simSpace.compilers.compile_3d
@tags @xc:render-3d

3D snapshot compiler — symmetric with compile_2d, with positions as
3-element vectors and defaults pointing at the 3D library
(cube / matte-blue) instead of 2D (circle / default).

@consumers
  - simSpace.sim_space_api
@see /OVERLAP_MAP.md
"""

from typing import Dict, List, Optional, Tuple

from .common import (
    parse_json_safe,
    resolve_ref,
    instance_id,
    load_bound_overrides,
    freestanding_id,
    iter_bindings,
    resolve_resolved_binding,
    read_temporal_value,
    resolve_position_spec,
    stamp_class_metadata,
)


def compile_3d(
    manager,
    row,
    warnings: List[str],
    resolved_bindings: List[Dict],
    run_filter: Optional[str] = None,
) -> Tuple[List[Dict], List[Dict]]:
    """Returns (objects, connections) for a 3D SimSpace snapshot. See
    compile_2d for the `run_filter` semantics — identical here."""
    objects: List[Dict] = []
    connections: List[Dict] = []

    # 1. Freestanding meshes from the definition blob.
    blob = parse_json_safe(getattr(row, 'definition', '') or '{}', {})
    if not isinstance(blob, dict):
        warnings.append("Definition JSON malformed — ignoring freestanding shapes.")
        blob = {}
    for entry in blob.get('freestanding') or []:
        if not isinstance(entry, dict):
            continue
        position = (entry.get('position') or [0, 0, 0])[:3]
        # Pad 2-element positions with z=0 so render code never panics.
        while len(position) < 3:
            position.append(0)
        objects.append({
            'id': freestanding_id(entry),
            'label': entry.get('label'),
            'position': position,
            'rotation': entry.get('rotation'),
            'scale': entry.get('scale'),
            'shapeRef': entry.get('shapeRef') or 'cube',
            'styleRef': entry.get('styleRef') or 'matte-blue',
            'userData': entry.get('userData'),
        })

    # 2. Scene-level boundClasses overrides.
    override_by_class = load_bound_overrides(row, warnings)

    # 3. Walk SimSpaceBindingDefinition rows for dimensionality='3d'.
    for binding_row in iter_bindings(manager, '3d'):
        class_name = getattr(binding_row, 'class_name', '')
        binding = parse_json_safe(getattr(binding_row, 'binding_json', '') or '{}', None)
        if binding is None or not isinstance(binding, dict):
            warnings.append(f"Binding JSON for {class_name} malformed; skipping.")
            continue
        stamp_class_metadata(manager, class_name, binding)

        override = override_by_class.get(class_name)
        if override is None and not binding.get('defaultVisible', False):
            continue

        instances = manager.objectTables.get(class_name, {}) or {}
        if not instances:
            warnings.append(f"Class {class_name} bound (3D) but has no instances.")
            continue

        if run_filter:
            instances = {
                k: v for k, v in (instances.items() if isinstance(instances, dict) else [])
                if (not hasattr(v, 'simulation_run_ref')
                    or getattr(v, 'simulation_run_ref', '') == run_filter)
            }
            if not instances:
                continue

        binding_kind = binding.get('kind') or 'object'
        if binding_kind == 'connection':
            emitted_conns = _emit_connections(
                class_name, instances, binding, override, warnings, dim=3,
            )
            connections.extend(emitted_conns)
            if emitted_conns:
                resolved_bindings.append(
                    resolve_resolved_binding(
                        class_name, binding, override, len(emitted_conns),
                    )
                )
        else:
            emitted = _emit_instances(class_name, instances, binding, override, warnings)
            objects.extend(emitted)
            if emitted:
                resolved_bindings.append(
                    resolve_resolved_binding(class_name, binding, override, len(emitted))
                )

    return objects, connections


def _emit_connections(
    class_name: str,
    instances: Dict,
    binding: Dict,
    override: Optional[Dict],
    warnings: List[str],
    dim: int,
) -> List[Dict]:
    """Emit one SimSpaceConnection per class instance per a 3D connection-mode
    binding. Symmetric with the 2D variant; dim=3 propagates through to the
    position-spec resolver."""
    source_spec = binding.get('source')
    target_spec = binding.get('target')
    if not source_spec or not target_spec:
        warnings.append(
            f"{class_name} connection binding missing source/target spec; skipping."
        )
        return []

    visual = binding.get('visual') or {}
    style_ref_cfg = visual.get('styleRef') or 'matte-blue'
    scene_style_override = override.get('overrideStyleRef') if override else None

    out: List[Dict] = []
    iter_instances = instances.values() if isinstance(instances, dict) else instances
    for inst in iter_instances:
        src = resolve_position_spec(class_name, inst, source_spec, dim, warnings)
        tgt = resolve_position_spec(class_name, inst, target_spec, dim, warnings)
        if src is None or tgt is None:
            continue
        inst_id = instance_id(inst)
        conn: Dict = {
            'id': f'{class_name}:{inst_id}',
            'sourcePosition': src,
            'targetPosition': tgt,
            'styleRef': scene_style_override or resolve_ref(style_ref_cfg, inst, 'matte-blue'),
            'classRef': {'className': class_name, 'instanceId': inst_id},
        }
        # Optional rod thickness + mesh — when present the 3D renderer draws
        # an oriented cylinder between the endpoints instead of a 1px line.
        thickness = visual.get('thickness')
        if thickness is not None:
            conn['thickness'] = thickness
        if visual.get('shapeRef'):
            conn['shapeRef'] = visual.get('shapeRef')
        temporal_value = read_temporal_value(inst, binding)
        if temporal_value is not None:
            conn['temporalValue'] = temporal_value
        out.append(conn)
    return out


def _emit_instances(
    class_name: str,
    instances: Dict,
    binding: Dict,
    override: Optional[Dict],
    warnings: List[str],
) -> List[Dict]:
    """Emit one SimSpaceObject per class instance per the 3D binding."""
    out: List[Dict] = []
    pos_cfg = binding.get('position') or {}
    visual = binding.get('visual') or {}
    shape_ref_cfg = visual.get('shapeRef') or 'cube'
    style_ref_cfg = visual.get('styleRef') or 'matte-blue'
    scene_shape_override = override.get('overrideShapeRef') if override else None
    scene_style_override = override.get('overrideStyleRef') if override else None

    iter_instances = instances.values() if isinstance(instances, dict) else instances
    for inst in iter_instances:
        position = _resolve_position_3d(class_name, inst, pos_cfg, warnings)
        if position is None:
            continue
        inst_id = instance_id(inst)
        obj = {
            'id': f'{class_name}:{inst_id}',
            'label': getattr(inst, 'name', None) or getattr(inst, 'displayName', None),
            'position': position,
            'shapeRef': scene_shape_override or resolve_ref(shape_ref_cfg, inst, 'cube'),
            'styleRef': scene_style_override or resolve_ref(style_ref_cfg, inst, 'matte-blue'),
            'classRef': {'className': class_name, 'instanceId': inst_id},
        }
        # Per-binding scale (uniform constant, a uniform field, or per-axis
        # fields). Lets a binding size a shared mesh (e.g. shrink the unit
        # sphere to a pendulum bob) without a dedicated mesh per size.
        scale = _resolve_scale_3d(binding.get('scale'), inst)
        if scale is not None:
            obj['scale'] = scale
        # Attach temporal value when bound — feeds the frontend scrubber.
        temporal_value = read_temporal_value(inst, binding)
        if temporal_value is not None:
            obj['temporalValue'] = temporal_value
        out.append(obj)
    return out


def _resolve_scale_3d(spec, inst):
    """Resolve a binding scale spec to a number (uniform) or [sx,sy,sz].
    Supports {kind:'constant',value}, {kind:'uniform',field}, and
    {kind:'per-axis',fields:{x,y,z}}. Returns None when unset/unresolvable."""
    if not isinstance(spec, dict):
        return None
    kind = spec.get('kind')
    try:
        if kind == 'constant':
            return float(spec.get('value'))
        if kind == 'uniform':
            f = spec.get('field')
            return float(getattr(inst, f, 1) or 1) if f else None
        if kind == 'per-axis':
            fs = spec.get('fields') or {}
            return [float(getattr(inst, fs.get(a), 1) or 1) for a in ('x', 'y', 'z')]
    except (TypeError, ValueError):
        return None
    return None


def _resolve_position_3d(
    class_name: str,
    inst,
    pos_cfg: Dict,
    warnings: List[str],
) -> Optional[List[float]]:
    """Resolve a 3D position. Three field names are required for
    kind='fields' — partial bindings skip the instance with a warning."""
    kind = pos_cfg.get('kind')
    if kind == 'fields':
        fields = pos_cfg.get('fields') or {}
        x_field, y_field, z_field = fields.get('x'), fields.get('y'), fields.get('z')
        # x/y required; z OPTIONAL — a 2-field binding places a planar (2D)
        # position into 3D at z = 0 (e.g. the pendulum, fixed in the X–Y plane).
        if not x_field or not y_field:
            warnings.append(
                f"{class_name} 3D binding needs x and y field names; skipping instance."
            )
            return None
        try:
            return [
                float(getattr(inst, x_field, 0) or 0),
                float(getattr(inst, y_field, 0) or 0),
                float(getattr(inst, z_field, 0) or 0) if z_field else 0.0,
            ]
        except (TypeError, ValueError):
            warnings.append(
                f"{class_name}.{x_field}/{y_field}/{z_field} not numeric on an instance; skipping."
            )
            return None
    if kind == 'vec3':
        vec_field = pos_cfg.get('vec3Field')
        raw = getattr(inst, vec_field, None) if vec_field else None
        if isinstance(raw, (list, tuple)) and len(raw) >= 3:
            return [float(raw[0] or 0), float(raw[1] or 0), float(raw[2] or 0)]
    return [0.0, 0.0, 0.0]
