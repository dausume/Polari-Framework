"""
@cross-cutting
@module polariPeers.module_bundle
@tags @xc:bindings

Module bundle format — the canonical JSON shape of a Polari capability
module, shared by the exporter, the loader, and the modules API.

    {
      "manifest": {
        "name": ..., "version": <sha256[:16] of the canonical content>,
        "description": ...,
        "requiredClasses": {"<ClassName>": "<fieldsFingerprint>", ...},
        "dependsOn": ["<module name>", ...],
        "objectCounts": {"<ClassName>": n, ...}          # convenience
      },
      "objects": {"<ClassName>": [<seed-shaped row dicts>], ...}
    }

Design rules:
  * NO timestamps inside the hashed content — the version is a pure
    content hash, so re-exporting unchanged content yields the same
    version (git SHAs can replace it when a module lives in git).
  * Rows are serialized in the SEED-DICT shape: the class's __init__
    keyword parameters (minus `manager`), so a bundle is exactly what
    the seeding machinery already knows how to consume.
  * `requiredClasses` carry a fields fingerprint (hash of the __init__
    parameter names) — THIS pass declares classes as requirements and
    detects version mismatches; carrying classes as configuration is
    the next pass (classes-as-config).

@consumers
  - polariPeers.module_exporter / module_loader / peers_api
@see /OVERLAP_MAP.md
"""

import hashlib
import inspect
import json
from typing import Any, Dict, List, Optional

# Skipped __init__ parameters when serializing / fingerprinting.
_PARAM_SKIP = ('self', 'manager')

# Dependency-safe creation order for definition classes (mirrors the
# server's seeding order). Bundle classes NOT listed here are treated as
# *SimState row classes and load right after SimulationRun.
CLASS_LOAD_ORDER: List[str] = [
    'Mesh3DDefinition',
    # Textures BEFORE materials — materials reference them.
    'Texture3DDefinition',
    'Material3DDefinition',
    'MaterialPhaseAppearance',
    'MatrixDefinition',
    'MatrixEquationDefinition',
    'EquationDefinition',
    'SimulationDefinition',
    'SimulationRun',
    # (dynamic *SimState classes slot in here)
    'SimSpaceDefinition',
    'SimSpaceBindingDefinition',
    'SimSpaceEvaluationEquation',
    'SolutionDefinition',
    'SimulationExecutionSolution',
    'SolutionTestCase',
    'GraphDefinition',
    'InitialConditionInterfaceDefinition',
    'SimulationCouplingDefinition',
    'MultiScaleSimulationDefinition',
    # Displays reference graphs/scenes/components — last.
    'DisplayDefinition',
]


def resolve_class(manager, class_name: str):
    """The registered class for a name — typing registry first, then a
    sample instance's type. None when the class isn't present here."""
    typing_obj = (getattr(manager, 'objectTypingDict', {}) or {}).get(class_name)
    cls = getattr(typing_obj, 'classDefinition', None) if typing_obj else None
    if cls is not None:
        return cls
    table = (getattr(manager, 'objectTables', {}) or {}).get(class_name, {}) or {}
    for inst in table.values():
        return inst.__class__
    return None


def init_param_names(cls) -> List[str]:
    """The class's __init__ keyword parameters in declaration order,
    minus self/manager — the seed-dict field set."""
    try:
        sig = inspect.signature(cls.__init__)
    except (TypeError, ValueError):
        return []
    return [
        name for name, param in sig.parameters.items()
        if name not in _PARAM_SKIP
        and param.kind not in (inspect.Parameter.VAR_POSITIONAL,
                               inspect.Parameter.VAR_KEYWORD)
    ]


def class_fields_fingerprint(cls) -> str:
    """Version fingerprint of a class's field set — import refuses a
    bundle whose declared fingerprint doesn't match the local class, so
    mismatched class versions fail loudly instead of half-seeding."""
    names = ','.join(sorted(init_param_names(cls)))
    return hashlib.sha256(names.encode('utf-8')).hexdigest()[:16]


def serialize_row(cls, inst) -> Dict[str, Any]:
    """One instance → its seed-dict (constructible kwargs)."""
    out: Dict[str, Any] = {}
    for name in init_param_names(cls):
        if hasattr(inst, name):
            out[name] = getattr(inst, name)
    return out


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=False, default=str)


def make_bundle(
    name: str,
    description: str,
    required_classes: Dict[str, str],
    depends_on: List[str],
    objects: Dict[str, List[Dict[str, Any]]],
) -> Dict[str, Any]:
    """Assemble + version a bundle. Rows are sorted by their `name` per
    class for stable hashing regardless of table iteration order."""
    ordered_objects = {
        cls: sorted(rows, key=lambda r: str(r.get('name', '')))
        for cls, rows in sorted(objects.items())
        if rows
    }
    hashed_core = {
        'name': name,
        'description': description,
        'requiredClasses': dict(sorted(required_classes.items())),
        'dependsOn': sorted(depends_on),
        'objects': ordered_objects,
    }
    version = hashlib.sha256(
        canonical_json(hashed_core).encode('utf-8')
    ).hexdigest()[:16]
    return {
        'manifest': {
            'name': name,
            'version': version,
            'description': description,
            'requiredClasses': hashed_core['requiredClasses'],
            'dependsOn': hashed_core['dependsOn'],
            'objectCounts': {c: len(r) for c, r in ordered_objects.items()},
        },
        'objects': ordered_objects,
    }


def validate_bundle_shape(bundle: Any) -> Optional[str]:
    """Plain-language structural check; None when OK."""
    if not isinstance(bundle, dict):
        return 'A module bundle must be a JSON object.'
    manifest = bundle.get('manifest')
    if not isinstance(manifest, dict) or not manifest.get('name'):
        return "The bundle's manifest is missing or has no name."
    if not isinstance(bundle.get('objects'), dict):
        return "The bundle has no 'objects' section."
    if not isinstance(manifest.get('requiredClasses', {}), dict):
        return "The manifest's requiredClasses must be an object."
    return None


def load_order_for(bundle_classes: List[str]) -> List[str]:
    """Order the bundle's classes dependency-safely: known definition
    classes in CLASS_LOAD_ORDER; unknown (state) classes after
    SimulationRun; anything else appended at the end, sorted."""
    known = [c for c in CLASS_LOAD_ORDER if c in bundle_classes]
    state = sorted(c for c in bundle_classes if c not in CLASS_LOAD_ORDER)
    if 'SimulationRun' in known:
        cut = known.index('SimulationRun') + 1
        return known[:cut] + state + known[cut:]
    return state + known
