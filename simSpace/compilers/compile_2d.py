"""
@cross-cutting
@module simSpace.compilers.compile_2d
@tags @xc:render-2d

2D snapshot compiler. Walks freestanding shapes from the SimSpace
definition blob, then iterates enabled SimSpaceBindingDefinition rows
with dimensionality='2d' to emit one SimSpaceObject per matching
class instance.

@consumers
  - simSpace.sim_space_api (SimSpaceAPI route handler)
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
from simulations.run_scope import resolve_run_scope, row_in_run_scope


def compile_2d(
    manager,
    row,
    warnings: List[str],
    resolved_bindings: List[Dict],
    run_filter: Optional[str] = None,
) -> Tuple[List[Dict], List[Dict]]:
    """Returns (objects, connections) for a 2D SimSpace snapshot.

    `run_filter` (optional) restricts *SimState rows to those whose
    `simulation_run_ref` matches the given run name. Classes without
    `simulation_run_ref` (non-SimState bound classes, freestanding) are
    always emitted. Used by the snapshot endpoint's `?run=<name>` query
    param so a viewer can show one specific run's data without other
    runs' rows bleeding through."""
    objects: List[Dict] = []
    connections: List[Dict] = []

    # 1. Freestanding shapes from the definition blob.
    blob = parse_json_safe(getattr(row, 'definition', '') or '{}', {})
    if not isinstance(blob, dict):
        warnings.append("Definition JSON malformed — ignoring freestanding shapes.")
        blob = {}
    for entry in blob.get('freestanding') or []:
        if not isinstance(entry, dict):
            continue
        objects.append({
            'id': freestanding_id(entry),
            'label': entry.get('label'),
            'position': entry.get('position') or [0, 0],
            'rotation': entry.get('rotation'),
            'scale': entry.get('scale'),
            'shapeRef': entry.get('shapeRef') or 'circle',
            'styleRef': entry.get('styleRef') or 'default',
            'userData': entry.get('userData'),
        })

    # 2. Scene-level boundClasses overrides.
    override_by_class = load_bound_overrides(row, warnings)

    # Run scope: the requested run PLUS its coupled source runs —
    # resolved once, shared predicate with compile_3d +
    # equation_evaluation (they MUST agree).
    run_scope = resolve_run_scope(manager, run_filter)

    # 3. Walk SimSpaceBindingDefinition rows.
    for binding_row in iter_bindings(manager, '2d'):
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
            warnings.append(f"Class {class_name} bound but has no instances.")
            continue

        # Run filter — drop instances outside the run scope (the run
        # itself + its coupled source runs). Classes without a
        # simulation_run_ref attribute fall through unchanged (the
        # attribute simply isn't there for non-SimState bound classes).
        if run_filter:
            instances = {
                k: v for k, v in (instances.items() if isinstance(instances, dict) else [])
                if row_in_run_scope(v, run_scope)
            }
            if not instances:
                # Filtered everything out — quiet (the warning above
                # already covered the bound-but-no-instances case).
                continue

        binding_kind = binding.get('kind') or 'object'
        if binding_kind == 'connection':
            emitted_conns = _emit_connections(
                class_name, instances, binding, override, warnings, dim=2,
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
    """Emit one SimSpaceConnection per class instance per a connection-mode
    binding. Source/target are resolved through the shared position-spec
    helper, so endpoints can be per-row fields, vec3 fields, or constants."""
    source_spec = binding.get('source')
    target_spec = binding.get('target')
    if not source_spec or not target_spec:
        warnings.append(
            f"{class_name} connection binding missing source/target spec; skipping."
        )
        return []

    visual = binding.get('visual') or {}
    style_ref_cfg = visual.get('styleRef') or 'default'
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
            'styleRef': scene_style_override or resolve_ref(style_ref_cfg, inst, 'default'),
            'classRef': {'className': class_name, 'instanceId': inst_id},
        }
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
    """Emit one SimSpaceObject per class instance per the 2D binding."""
    out: List[Dict] = []
    pos_cfg = binding.get('position') or {}
    visual = binding.get('visual') or {}
    shape_ref_cfg = visual.get('shapeRef') or 'circle'
    style_ref_cfg = visual.get('styleRef') or 'default'
    scene_shape_override = override.get('overrideShapeRef') if override else None
    scene_style_override = override.get('overrideStyleRef') if override else None

    iter_instances = instances.values() if isinstance(instances, dict) else instances
    for inst in iter_instances:
        position = _resolve_position_2d(class_name, inst, pos_cfg, warnings)
        if position is None:
            continue
        inst_id = instance_id(inst)
        obj = {
            'id': f'{class_name}:{inst_id}',
            'label': getattr(inst, 'name', None) or getattr(inst, 'displayName', None),
            'position': position,
            'shapeRef': scene_shape_override or resolve_ref(shape_ref_cfg, inst, 'circle'),
            'styleRef': scene_style_override or resolve_ref(style_ref_cfg, inst, 'default'),
            'classRef': {'className': class_name, 'instanceId': inst_id},
        }
        # Attach the temporal value when the binding declares one — the
        # frontend scrubber filters visible objects by this field.
        temporal_value = read_temporal_value(inst, binding)
        if temporal_value is not None:
            obj['temporalValue'] = temporal_value
        out.append(obj)
    return out


def _resolve_position_2d(
    class_name: str,
    inst,
    pos_cfg: Dict,
    warnings: List[str],
) -> Optional[List[float]]:
    """Resolve a 2D position from either `{fields: {x, y}}` or `{vec3Field}`.
    Returns None when the binding's required fields are missing or the
    instance has non-numeric values."""
    kind = pos_cfg.get('kind')
    if kind == 'fields':
        fields = pos_cfg.get('fields') or {}
        x_field, y_field = fields.get('x'), fields.get('y')
        if not x_field or not y_field:
            warnings.append(
                f"{class_name} binding missing x/y field names; skipping instance."
            )
            return None
        try:
            return [
                float(getattr(inst, x_field, 0) or 0),
                float(getattr(inst, y_field, 0) or 0),
            ]
        except (TypeError, ValueError):
            warnings.append(
                f"{class_name}.{x_field}/{y_field} not numeric on an instance; skipping."
            )
            return None
    if kind == 'vec3':
        vec_field = pos_cfg.get('vec3Field')
        raw = getattr(inst, vec_field, None) if vec_field else None
        if isinstance(raw, (list, tuple)) and len(raw) >= 2:
            return [float(raw[0] or 0), float(raw[1] or 0)]
    return [0.0, 0.0]
