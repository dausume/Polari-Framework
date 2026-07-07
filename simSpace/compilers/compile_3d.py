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
from .field_projection import emit_field_3d
from simulations.run_scope import resolve_run_scope, row_in_run_scope


def compile_3d(
    manager,
    row,
    warnings: List[str],
    resolved_bindings: List[Dict],
    run_filter: Optional[str] = None,
) -> Tuple[List[Dict], List[Dict], List[Dict]]:
    """Returns (objects, connections, vectors) for a 3D SimSpace snapshot.
    `vectors` are State-Projection arrows (viz-only projections of a real
    state's internal vector fields). See compile_2d for the `run_filter`
    semantics — identical here."""
    objects: List[Dict] = []
    connections: List[Dict] = []
    vectors: List[Dict] = []

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

    # Scene knob: freestandingOnly scenes render ONLY their baked
    # definition blob — no class bindings at all (selection spaces are
    # curated shelves, not data views; without this every defaultVisible
    # binding's rows would pour in).
    if blob.get('freestandingOnly'):
        return objects, connections, vectors

    # 2. Scene-level boundClasses overrides.
    override_by_class = load_bound_overrides(row, warnings)

    # Run scope: the requested run PLUS its coupled source runs (e.g. a
    # wind-forced pendulum run's wind-field run) — resolved once, shared
    # predicate with compile_2d + equation_evaluation (they MUST agree).
    run_scope = resolve_run_scope(manager, run_filter)

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
                if row_in_run_scope(v, run_scope)
            }
            if not instances:
                continue

        binding_kind = binding.get('kind') or 'object'
        binding_name = getattr(binding_row, 'name', '') or class_name
        if binding_kind == 'connection':
            emitted_conns = _emit_connections(
                class_name, instances, binding, override, warnings, dim=3,
                binding_name=binding_name,
            )
            connections.extend(emitted_conns)
            if emitted_conns:
                resolved_bindings.append(
                    resolve_resolved_binding(
                        class_name, binding, override, len(emitted_conns),
                    )
                )
        elif binding_kind == 'vector':
            emitted_vecs = _emit_vectors(
                class_name, instances, binding,
                getattr(binding_row, 'name', class_name), override, warnings,
            )
            vectors.extend(emitted_vecs)
            if emitted_vecs:
                resolved_bindings.append(
                    resolve_resolved_binding(
                        class_name, binding, override, len(emitted_vecs),
                    )
                )
        elif binding_kind == 'field':
            # Matrix-valued field row → per-cell arrows (same snapshot
            # `vectors` channel; per-cell stable keys + scrub-safe
            # sparsity live in the emitter).
            emitted_field = emit_field_3d(
                class_name, instances, binding,
                getattr(binding_row, 'name', class_name), override, warnings,
            )
            vectors.extend(emitted_field)
            if emitted_field:
                resolved_bindings.append(
                    resolve_resolved_binding(
                        class_name, binding, override, len(emitted_field),
                    )
                )
        else:
            emitted = _emit_instances(class_name, instances, binding, override, warnings,
                                      binding_name=binding_name)
            objects.extend(emitted)
            if emitted:
                resolved_bindings.append(
                    resolve_resolved_binding(class_name, binding, override, len(emitted))
                )

    return objects, connections, vectors


def _emit_connections(
    class_name: str,
    instances: Dict,
    binding: Dict,
    override: Optional[Dict],
    warnings: List[str],
    dim: int,
    binding_name: str = '',
) -> List[Dict]:
    """Emit one SimSpaceConnection per class instance per a 3D connection-mode
    binding. Symmetric with the 2D variant; dim=3 propagates through to the
    position-spec resolver. `binding_name` rides through userData so the
    frontend can keep two bindings on the SAME class on distinct render
    tracks (mirrors the vector emitter's `bindingName:className` keying)."""
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
        if binding_name:
            conn['userData'] = {'bindingName': binding_name}
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


def _emit_vectors(
    class_name: str,
    instances: Dict,
    binding: Dict,
    binding_name: str,
    override: Optional[Dict],
    warnings: List[str],
) -> List[Dict]:
    """Emit one State-Projection arrow per class instance per a 3D
    `vector`-kind binding: an arrow from `origin` (a point field-set) along
    `vector` (a free vector field-set), scaled. Viz-only — it reads the real
    state's own fields (e.g. the bob's fgrav/fnet) and owns NO simulation
    logic, so no companion *SimState class, rows, or dependency chain.

    `origin` and `vector` reuse the same field-set resolver positions use —
    a vector is just three resolved numbers, no pivot.

    `key` is `bindingName:className` — deliberately STABLE across timesteps.
    For temporal SimState projections each step is a distinct row (a distinct
    instanceId), so keying on instanceId would mint a fresh key every step and
    the frontend's collapse-by-key would keep them all → a trail of arrows.
    Keying on className instead collapses to one arrow per projection that the
    scrubber just repositions (mirrors how objects collapse by className), while
    `binding_name` keeps two projections on the SAME class distinct (gravity vs
    net). `id`/`classRef.instanceId` stay per-row for click-to-navigate."""
    origin_cfg = binding.get('origin') or {}
    vector_cfg = binding.get('vector') or {}
    if not origin_cfg or not vector_cfg:
        warnings.append(
            f"{class_name} vector binding missing origin/vector spec; skipping."
        )
        return []

    visual = binding.get('visual') or {}
    style_ref_cfg = visual.get('styleRef') or 'matte-blue'
    scene_style_override = override.get('overrideStyleRef') if override else None
    try:
        scale = float(binding.get('scale', 1.0) or 1.0)
        head_scale = float(binding.get('headScale', 0.18) or 0.18)
        min_length = float(binding.get('minLength', 0.0) or 0.0)
    except (TypeError, ValueError):
        scale, head_scale, min_length = 1.0, 0.18, 0.0

    out: List[Dict] = []
    iter_instances = instances.values() if isinstance(instances, dict) else instances
    for inst in iter_instances:
        origin = _resolve_position_3d(class_name, inst, origin_cfg, warnings)
        vec = _resolve_position_3d(class_name, inst, vector_cfg, warnings)
        if origin is None or vec is None:
            continue
        # Skip degenerate arrows — a zero/near-zero vector has no direction to
        # draw, and below `minLength` (post-scale) the user asked us not to.
        mag = (vec[0] ** 2 + vec[1] ** 2 + vec[2] ** 2) ** 0.5
        if mag * scale < max(min_length, 1e-9):
            continue
        inst_id = instance_id(inst)
        v: Dict = {
            'kind': 'vector',
            'key': f'{binding_name}:{class_name}',
            'id': f'{binding_name}:{inst_id}',
            'origin': origin,
            'vec': vec,
            'scale': scale,
            'headScale': head_scale,
            'styleRef': scene_style_override or resolve_ref(style_ref_cfg, inst, 'matte-blue'),
            'classRef': {'className': class_name, 'instanceId': inst_id},
        }
        temporal_value = read_temporal_value(inst, binding)
        if temporal_value is not None:
            v['temporalValue'] = temporal_value
        out.append(v)
    return out


def _emit_instances(
    class_name: str,
    instances: Dict,
    binding: Dict,
    override: Optional[Dict],
    warnings: List[str],
    binding_name: str = '',
) -> List[Dict]:
    """Emit one SimSpaceObject per class instance per the 3D binding.
    `binding_name` rides through userData so the frontend can keep two
    bindings on the SAME class on distinct render tracks."""
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
        if binding_name:
            obj['userData'] = {'bindingName': binding_name}
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
    Supports {kind:'constant',value}, {kind:'uniform',field[,factor]},
    and {kind:'per-axis',fields:{x,y,z}}. Returns None when unset/
    unresolvable. `factor` multiplies a field-driven uniform scale —
    e.g. a RADIUS field sizing the shared unit sphere (r=0.5) uses
    factor 2 so the rendered radius equals the field's metric value."""
    if not isinstance(spec, dict):
        return None
    kind = spec.get('kind')
    try:
        if kind == 'constant':
            return float(spec.get('value'))
        if kind == 'uniform':
            f = spec.get('field')
            if not f:
                return None
            factor = float(spec.get('factor', 1.0) or 1.0)
            raw = getattr(inst, f, None)
            if raw is None:
                return None
            # A genuine 0 stays 0 (e.g. ball_radius before the first
            # step: no ball exists yet, so nothing should render).
            return float(raw) * factor
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
    if kind == 'constant':
        val = pos_cfg.get('value') or []
        if isinstance(val, (list, tuple)) and len(val) >= 3:
            try:
                return [float(val[0] or 0), float(val[1] or 0),
                        float(val[2] or 0)]
            except (TypeError, ValueError):
                pass
    return [0.0, 0.0, 0.0]
