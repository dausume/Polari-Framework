"""
@cross-cutting
@module simSpace.compilers.common
@tags @xc:render-shared

Helpers shared between compile_2d and compile_3d:
  - parse_json_safe       — defensive JSON parsing
  - resolve_ref           — Shape/Material ref resolution (literal string
                            or {fromField: ...} per-instance lookup)
  - instance_id           — derives a stable id from a Polari instance
  - load_bound_overrides  — scene-level boundClasses override list
"""

import json
import uuid
from typing import Any, Dict, List, Optional


def parse_json_safe(text: str, default: Any) -> Any:
    """Tolerant JSON parse — returns `default` on malformed input."""
    if not text:
        return default
    try:
        return json.loads(text)
    except (ValueError, TypeError):
        return default


def resolve_ref(cfg: Any, inst: Any, default: str) -> str:
    """Resolve a shape/style/mesh/material reference:
      - bare string → use that name
      - {fromField: <fieldName>} → read the named field on `inst`
      - {fromField: <fieldName>, map: {<value>: <ref>}, default: <ref>}
        → read the field, look its VALUE up in the map (the per-phase
        appearance primitive: e.g. phase_solid 1.0 → 'wax-solid').
        Numeric field values match either their str form or their
        int-str form ('1.0' matches a '1' key), so binary flags map
        cleanly.
      - anything else → fall back to `default`
    """
    if isinstance(cfg, str):
        return cfg or default
    if isinstance(cfg, dict) and 'fromField' in cfg:
        v = getattr(inst, cfg['fromField'], None)
        value_map = cfg.get('map')
        if isinstance(value_map, dict):
            fallback = cfg.get('default') or default
            if v is None:
                return fallback
            if str(v) in value_map:
                return str(value_map[str(v)]) or fallback
            try:
                f = float(v)
                # Only integral values normalize ('1.0' → '1'); a 0.5
                # must NOT silently truncate onto the '0' key.
                if f.is_integer() and str(int(f)) in value_map:
                    return str(value_map[str(int(f))]) or fallback
            except (TypeError, ValueError):
                pass
            return fallback
        return str(v) if v else default
    return default




def instance_id(inst: Any) -> str:
    """Derive a stable instance id — accept any of `id`, `polariId`,
    `name` (in that order). Falls back to a fresh UUID if nothing's
    available (shouldn't happen in practice; defensive)."""
    for attr in ('id', 'polariId', 'name'):
        v = getattr(inst, attr, None)
        if v:
            return str(v)
    return str(uuid.uuid4())


def load_bound_overrides(row: Any, warnings: List[str]) -> Dict[str, Dict]:
    """Parse a SimSpaceDefinition row's `bound_classes_json` into a
    by-className lookup. Malformed JSON downgrades to an empty dict
    with a warning surfaced to the snapshot consumer."""
    raw = parse_json_safe(getattr(row, 'bound_classes_json', '') or '[]', [])
    if not isinstance(raw, list):
        warnings.append("bound_classes_json malformed — ignoring scene overrides.")
        return {}
    return {
        entry.get('className'): entry
        for entry in raw
        if isinstance(entry, dict) and entry.get('className')
    }


def freestanding_id(entry: Dict) -> str:
    """Id for a freestanding shape baked into a SimSpaceDefinition's
    `definition` blob. Honors a declared id, otherwise generates one
    stably prefixed for debugging."""
    return entry.get('id') or f'free-{uuid.uuid4().hex[:8]}'


def stamp_class_metadata(manager, class_name: str, binding: Dict) -> None:
    """Stamp class-level metadata onto a parsed binding dict so
    `resolve_resolved_binding` can surface it without re-querying the
    typing system. Currently picks up `simulation_definition_name` —
    if a binding's class is a `*SimState`, we want the snapshot's
    resolvedBindings to tell the frontend which simulation it
    belongs to (so the run panel can list runs without an extra
    discovery call)."""
    typing_obj = manager.objectTypingDict.get(class_name)
    cls = getattr(typing_obj, 'classDefinition', None) if typing_obj else None
    if cls is None:
        # Fallback: sample an existing instance for its class. Cheap
        # when the table has anything; harmless when empty.
        sample_table = manager.objectTables.get(class_name, {}) or {}
        for inst in sample_table.values():
            cls = inst.__class__
            break
    sim_def_name = getattr(cls, 'simulation_definition_name', '') if cls else ''
    if sim_def_name:
        binding['_simulationDefinitionName'] = sim_def_name


def iter_bindings(manager, dimensionality: str):
    """Yield SimSpaceBindingDefinition rows matching `dimensionality`
    and `enabled=True`. Tolerates missing table gracefully."""
    table = manager.objectTables.get('SimSpaceBindingDefinition', {}) or {}
    for row in table.values():
        if getattr(row, 'dimensionality', '') != dimensionality:
            continue
        if not getattr(row, 'enabled', False):
            continue
        if not getattr(row, 'class_name', ''):
            continue
        yield row


def resolve_resolved_binding(
    class_name: str,
    binding: Dict,
    override: Optional[Dict],
    emitted_count: int,
) -> Dict:
    """Build the snapshot's `resolvedBindings` entry — the legend-driving
    metadata returned alongside compiled objects. Includes temporal info
    when the binding declares it so the viewer knows to enable a scrubber."""
    kind = binding.get('kind') or 'object'
    visual = binding.get('visual') or {}
    shape_ref_cfg = visual.get('shapeRef')
    style_ref_cfg = visual.get('styleRef')

    entry: Dict = {
        'className': class_name,
        'instanceCount': emitted_count,
        'kind': kind,
        'shapeRef': (override or {}).get('overrideShapeRef')
                    or (shape_ref_cfg if isinstance(shape_ref_cfg, str) else '(per-instance)'),
        'styleRef': (override or {}).get('overrideStyleRef')
                    or (style_ref_cfg if isinstance(style_ref_cfg, str) else '(per-instance)'),
        # Temporal config — present when the binding declares one; absent
        # otherwise (frontend hides the scrubber when no resolvedBinding
        # has a temporal entry).
        'temporal': binding.get('temporal') or None,
        # Class-level simulation_definition_name when the bound class is a
        # `*SimState` class. Surfaces the participating simulation to the
        # frontend so the run panel can pick a SimulationRun without an
        # extra discovery roundtrip.
        'simulationDefinitionName': binding.get('_simulationDefinitionName'),
    }

    if kind == 'connection':
        # Endpoints summary for the legend — readable for both ends.
        entry['endpoints'] = {
            'source': _describe_position_spec(binding.get('source')),
            'target': _describe_position_spec(binding.get('target')),
        }
    else:
        pos_cfg = binding.get('position') or {}
        entry['positionFields'] = (
            (pos_cfg.get('fields') or None) if pos_cfg.get('kind') == 'fields' else None
        )
        entry['vec3Field'] = (
            pos_cfg.get('vec3Field') if pos_cfg.get('kind') == 'vec3' else None
        )

    return entry


def _describe_position_spec(spec: Optional[Dict]) -> str:
    """Render a position-spec as a human label for the legend."""
    if not isinstance(spec, dict):
        return '?'
    k = spec.get('kind')
    if k == 'fields':
        fields = spec.get('fields') or {}
        parts = [fields.get(ax) for ax in ('x', 'y', 'z') if fields.get(ax)]
        return '(' + ', '.join(parts) + ')' if parts else '(fields)'
    if k == 'vec3':
        return f"vec3:{spec.get('vec3Field', '?')}"
    if k == 'constant':
        val = spec.get('value') or []
        return '(' + ', '.join(str(v) for v in val) + ')'
    return '?'


def resolve_position_spec(
    class_name: str,
    inst,
    spec: Optional[Dict],
    dim: int,
    warnings: List[str],
) -> Optional[List[float]]:
    """Resolve a position spec (used for object position OR a connection
    endpoint) into a [x, y] (dim=2) or [x, y, z] (dim=3) list.

    Returns None if a required field is missing or non-numeric — callers
    should skip the instance in that case.
    """
    if not isinstance(spec, dict):
        return None
    kind = spec.get('kind')

    if kind == 'fields':
        fields = spec.get('fields') or {}
        x_field, y_field = fields.get('x'), fields.get('y')
        z_field = fields.get('z')
        # x/y are required; z is OPTIONAL in 3D — a 2-field binding embeds a
        # planar (2D) position into 3D at z = 0. Lets a 3D scene reuse a 2D
        # sim's x/y directly (e.g. the pendulum, fixed in the X–Y plane).
        if not x_field or not y_field:
            warnings.append(
                f"{class_name} binding needs x/y field names; skipping instance."
            )
            return None
        try:
            if dim == 3:
                return [
                    float(getattr(inst, x_field, 0) or 0),
                    float(getattr(inst, y_field, 0) or 0),
                    float(getattr(inst, z_field, 0) or 0) if z_field else 0.0,
                ]
            return [
                float(getattr(inst, x_field, 0) or 0),
                float(getattr(inst, y_field, 0) or 0),
            ]
        except (TypeError, ValueError):
            warnings.append(
                f"{class_name} position fields not numeric on an instance; skipping."
            )
            return None

    if kind == 'vec3':
        vec_field = spec.get('vec3Field')
        raw = getattr(inst, vec_field, None) if vec_field else None
        if isinstance(raw, (list, tuple)) and len(raw) >= dim:
            return [float(raw[i] or 0) for i in range(dim)]
        return None

    if kind == 'constant':
        val = spec.get('value') or []
        if not isinstance(val, (list, tuple)) or len(val) < dim:
            warnings.append(
                f"{class_name} connection constant endpoint short for {dim}D; padding with zeros."
            )
            padded = list(val) + [0.0] * dim
            return [float(padded[i] or 0) for i in range(dim)]
        return [float(val[i] or 0) for i in range(dim)]

    return None


def read_temporal_value(inst, binding: Dict) -> Optional[float]:
    """Read the temporal field value off an instance per the binding.
    Returns None when the binding has no temporal config or the field is
    missing / non-numeric. The value is surfaced to the frontend on each
    emitted SimSpaceObject so the scrubber can filter without re-querying."""
    temporal = binding.get('temporal') or None
    if not temporal:
        return None
    field = temporal.get('field')
    if not field:
        return None
    raw = getattr(inst, field, None)
    if raw is None:
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None
